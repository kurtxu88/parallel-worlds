#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Neo4j Direct Importer for O3 Games
Directly imports O3 game data to Neo4j without temporary files
Uses compound keys (story_id + id/name) to avoid conflicts between stories
"""

import json
from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase, Transaction
from datetime import datetime
import uuid


class Neo4jDirectImporter:
    """Direct importer for O3 games to Neo4j using Python driver"""
    
    def __init__(self, uri: str, username: str, password: str):
        """Initialize Neo4j connection"""
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.verify_connection()
    
    def close(self):
        """Close database connection"""
        self.driver.close()
    
    def verify_connection(self):
        """Verify database connection"""
        try:
            self.driver.verify_connectivity()
            print("✅ Connected to Neo4j database")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Neo4j: {str(e)}")
    
    def setup_database(self):
        """Setup database indexes and constraints
        
        注意：我们不使用UNIQUE约束，因为不同故事可能有相同的角色名/场景ID
        改用复合索引来提高查询性能
        """
        with self.driver.session() as session:
            # 1. 移除可能存在的旧约束（如果有）
            print("🔧 Setting up database...")
            
            # 先查询现有约束
            constraints = session.run("SHOW CONSTRAINTS").data()
            for constraint in constraints:
                if constraint.get('labelsOrTypes') == ['Character'] and 'name' in constraint.get('properties', []):
                    # 删除Character name约束
                    session.run(f"DROP CONSTRAINT {constraint['name']}")
                    print(f"  ✓ Removed constraint: {constraint['name']}")
            
            # 2. 创建复合索引（story_id + id/name）
            indexes = [
                # Story本身的唯一性
                "CREATE INDEX story_id_idx IF NOT EXISTS FOR (s:Story) ON (s.id)",
                
                # 场景的复合索引
                "CREATE INDEX scene_compound_idx IF NOT EXISTS FOR (n:Scene) ON (n.story_id, n.id)",
                "CREATE INDEX checkpoint_compound_idx IF NOT EXISTS FOR (n:Checkpoint) ON (n.story_id, n.id)",
                "CREATE INDEX ending_compound_idx IF NOT EXISTS FOR (n:Ending) ON (n.story_id, n.id)",
                "CREATE INDEX storynode_story_idx IF NOT EXISTS FOR (n:StoryNode) ON (n.story_id)",
                
                # 角色的复合索引（关键！）
                "CREATE INDEX character_compound_idx IF NOT EXISTS FOR (c:Character) ON (c.story_id, c.name)",
                
                # Flag的复合索引
                "CREATE INDEX flag_compound_idx IF NOT EXISTS FOR (f:Flag) ON (f.story_id, f.id)",
                
                
                
                # 其他有用的索引
                "CREATE INDEX scene_episode_idx IF NOT EXISTS FOR (n:Scene) ON (n.episode)",
                "CREATE INDEX storybrief_story_idx IF NOT EXISTS FOR (sb:StoryBrief) ON (sb.story_id)",
                "CREATE INDEX epilogue_story_idx IF NOT EXISTS FOR (ev:EpilogueVariant) ON (ev.story_id)",
                "CREATE INDEX concept_story_idx IF NOT EXISTS FOR (ca:ConceptAnalysis) ON (ca.story_id)",
                "CREATE INDEX reference_story_idx IF NOT EXISTS FOR (rw:ReferenceWork) ON (rw.story_id)",
            ]
            
            for index in indexes:
                try:
                    session.run(index)
                    print(f"  ✓ Created index: {index.split(' ')[2]}")
                except Exception as e:
                    # 索引可能已存在，忽略错误
                    pass
            
            print("✅ Database setup completed")
    
    def import_o3_game(self, o3_data: Dict[str, Any], filename: str) -> str:
        """Import O3 game data directly to Neo4j
        
        Returns:
            story_id: The unique identifier of the imported story
        """
        # Extract metadata
        metadata = o3_data.get('metadata', {})
        story_id = o3_data.get('story_id', str(uuid.uuid4()))
        
        print(f"\n📖 Importing O3 game: {metadata.get('title', 'Untitled')}")
        print(f"🆔 Story ID: {story_id}")
        
        # Setup database (创建索引等)
        self.setup_database()
        
        # 使用写事务导入数据
        with self.driver.session() as session:
            try:
                # 在单个事务中完成所有导入
                session.execute_write(self._import_story_transaction, story_id, filename, o3_data)
                print("✅ Import completed successfully!")
                
            except Exception as e:
                print(f"❌ Import failed: {str(e)}")
                raise
        
        # 显示统计信息
        self._show_statistics(story_id)
        
        return story_id
    
    def _import_story_transaction(self, tx: Transaction, story_id: str, filename: str, o3_data: Dict[str, Any]):
        """在事务中执行所有导入操作"""
        
        # 1. 删除该故事的现有数据
        self._delete_existing_story(tx, story_id)
        
        # 2. 创建Story元数据节点
        self._create_story_metadata(tx, story_id, filename, o3_data)
        
        # 3. 创建StoryBrief节点
        self._create_story_brief(tx, story_id, o3_data)
        
        # 4. 创建Character节点（使用story_id + name作为唯一标识）
        self._create_characters(tx, story_id, o3_data)
        
        # 5. 创建所有场景节点
        self._create_scenes(tx, story_id, o3_data)
        
        # 6. 创建场景间的关系（选择）
        self._create_relationships(tx, story_id, o3_data)
        
        # 7. 创建Flag节点
        self._create_flags(tx, story_id, o3_data)
        
        
        
        # 9. 创建结局变体
        self._create_epilogue_variants(tx, story_id, o3_data)
        
        # 10. 创建概念分析（如果有）
        self._create_concept_analysis(tx, story_id, o3_data)
        
        # 11. 创建质量报告（如果有）
        self._create_quality_report(tx, story_id, o3_data)
        
        # 12. 创建主要分支点
        self._create_major_branches(tx, story_id, o3_data)
        
        # 13. 更新Story节点的增强字段
        self._update_story_metadata_enhanced(tx, story_id, o3_data)
    
    def _delete_existing_story(self, tx: Transaction, story_id: str):
        """删除指定故事的所有现有数据"""
        # 检查是否存在
        result = tx.run("""
            MATCH (n {story_id: $story_id})
            RETURN count(n) as count
        """, story_id=story_id)
        
        count = result.single()['count']
        if count > 0:
            print(f"🗑️  Deleting {count} existing nodes for story {story_id}")
            
            # 删除所有带有此story_id的节点及其关系
            tx.run("""
                MATCH (n {story_id: $story_id})
                DETACH DELETE n
            """, story_id=story_id)
    
    def _create_story_metadata(self, tx: Transaction, story_id: str, filename: str, o3_data: Dict[str, Any]):
        """创建Story元数据节点"""
        metadata = o3_data.get('metadata', {})
        story_config = o3_data.get('story_config', {})
        scenes = o3_data.get('scenes', [])
        
        # 创建Story节点
        result = tx.run("""
            CREATE (s:Story {
                id: $story_id,
                story_id: $story_id,
                filename: $filename,
                title: $title,
                genre: $genre,
                culture_language: $culture_language,
                episodes: $episodes,
                total_scenes: $total_scenes,
                import_time: datetime()
            })
            RETURN s
        """, 
            story_id=story_id,
            filename=filename,
            title=metadata.get('title', 'Untitled'),
            genre=metadata.get('genre', 'Unknown'),
            culture_language=metadata.get('culture_language', 'zh-CN'),
            episodes=story_config.get('episodes', 6),
            total_scenes=len(scenes)
        )
        
        print(f"  ✓ Created Story metadata")
    
    def _create_story_brief(self, tx: Transaction, story_id: str, o3_data: Dict[str, Any]):
        """创建StoryBrief节点"""
        story_brief = o3_data.get('story_brief', {})
        
        if story_brief:
            tx.run("""
                CREATE (sb:StoryBrief {
                    story_id: $story_id,
                    world_setting: $world_setting,
                    character_relationships: $character_relationships,
                    main_plot: $main_plot,
                    emotional_storyline: $emotional_storyline,
                    theme_depth: $theme_depth,
                    innovation_highlights: $innovation_highlights
                })
            """, 
                story_id=story_id,
                world_setting=story_brief.get('world_setting', ''),
                character_relationships=story_brief.get('character_relationships', ''),
                main_plot=story_brief.get('main_plot', ''),
                emotional_storyline=story_brief.get('emotional_storyline', ''),
                theme_depth=story_brief.get('theme_depth', ''),
                innovation_highlights=story_brief.get('innovation_highlights', '')
            )
            
            print(f"  ✓ Created StoryBrief")
    
    def _create_characters(self, tx: Transaction, story_id: str, o3_data: Dict[str, Any]):
        """创建Character节点
        
        重要：使用story_id + name的组合来确保唯一性
        角色类型: protagonist(主角), major_npc(重要NPC), minor_npc(次要NPC)
        """
        characters = o3_data.get('characters', [])
        
        if characters:
            # 批量创建角色并建立与Story的关系
            tx.run("""
                MATCH (s:Story {id: $story_id})
                UNWIND $characters AS char
                CREATE (c:Character {
                    story_id: $story_id,
                    name: char.name,
                    character_type: COALESCE(char.character_type, 'major_npc'),
                    basic_info: char.basic_info,
                    biography: char.biography,
                    relationships: char.relationships,
                    growth_arc: char.growth_arc,
                    character_function: char.character_function,
                    inner_conflict: char.inner_conflict,
                    key_dialogue_style: char.key_dialogue_style
                })
                CREATE (s)-[:HAS_CHARACTER]->(c)
            """, 
                story_id=story_id,
                characters=characters
            )
            
            print(f"  ✓ Created {len(characters)} Characters")
    
    def _create_scenes(self, tx: Transaction, story_id: str, o3_data: Dict[str, Any]):
        """创建所有场景节点"""
        scenes = o3_data.get('scenes', [])
        critical_points = o3_data.get('critical_points', {})
        
        # 获取结局场景ID
        ending_ids = {e['scene_id'] for e in critical_points.get('endings', [])}
        
        for scene in scenes:
            scene_id = scene['id']
            
            # 确定节点标签
            if scene_id in ending_ids or scene.get('type') == 'ending':
                labels = 'StoryNode:Ending'
            elif scene.get('type') == 'hub':
                labels = 'StoryNode:Scene:Hub'
            elif scene.get('type') == 'emotional':
                labels = 'StoryNode:Scene:Emotional'
            else:
                labels = 'StoryNode:Scene'
            
            # 准备content数据
            content = scene.get('content', {})
            
            # 创建场景节点并建立与Story的关系
            tx.run(f"""
                MATCH (s:Story {{id: $story_id}})
                CREATE (n:{labels} {{
                    id: $scene_id,
                    story_id: $story_id,
                    title: $title,
                    description: $description,
                    episode: $episode,
                    type: $type,
                    narrative: $narrative,
                    atmosphere: $atmosphere,
                    key_events: $key_events,
                    merge_from: $merge_from,
                    content: $content
                }})
                CREATE (s)-[:HAS_SCENE]->(n)
            """,
                scene_id=scene_id,
                story_id=story_id,
                title=scene.get('title', ''),
                description=scene.get('description', ''),
                episode=scene.get('episode', 1),
                type=scene.get('type', 'normal'),
                narrative=content.get('narrative', ''),
                atmosphere=content.get('atmosphere', ''),
                key_events=json.dumps(content.get('key_events', []), ensure_ascii=False),
                merge_from=json.dumps(scene.get('merge_from', []), ensure_ascii=False),
                content=json.dumps(content, ensure_ascii=False)
            )
        
        print(f"  ✓ Created {len(scenes)} scenes")
    
    def _create_relationships(self, tx: Transaction, story_id: str, o3_data: Dict[str, Any]):
        """创建场景间的选择关系"""
        scenes = o3_data.get('scenes', [])
        
        # 收集所有关系数据
        relationships = []
        for scene in scenes:
            scene_id = scene['id']
            content = scene.get('content', {})
            
            # 处理玩家选择
            for i, choice in enumerate(content.get('player_choices', [])):
                if choice.get('leads_to'):
                    relationships.append({
                        'from_id': scene_id,
                        'to_id': choice['leads_to'],
                        'text': choice.get('choice_text', ''),
                        'choice_id': choice.get('id', f'choice_{i}'),
                        'weight': choice.get('weight', 'minor'),
                        'internal_reasoning': choice.get('internal_reasoning', ''),
                        'prerequisites': json.dumps(choice.get('prerequisites', []), ensure_ascii=False),
                        'consequences': json.dumps(choice.get('consequences', []), ensure_ascii=False),
                        'hidden': choice.get('hidden', False),
                        'discovery_hint': choice.get('discovery_hint', '')
                    })
        
        # 批量创建关系
        if relationships:
            tx.run("""
                UNWIND $rels AS rel
                MATCH (from:StoryNode {id: rel.from_id, story_id: $story_id})
                MATCH (to:StoryNode {id: rel.to_id, story_id: $story_id})
                CREATE (from)-[:PLAYER_CHOICE {
                    text: rel.text,
                    choice_id: rel.choice_id,
                    weight: rel.weight,
                    internal_reasoning: rel.internal_reasoning,
                    prerequisites: rel.prerequisites,
                    consequences: rel.consequences,
                    hidden: rel.hidden,
                    discovery_hint: rel.discovery_hint
                }]->(to)
            """, 
                story_id=story_id,
                rels=relationships
            )
            
            print(f"  ✓ Created {len(relationships)} choices")
    
    def _create_flags(self, tx: Transaction, story_id: str, o3_data: Dict[str, Any]):
        """创建Flag节点"""
        flags = o3_data.get('flags', [])
        
        if flags:
            tx.run("""
                MATCH (s:Story {id: $story_id})
                UNWIND $flags AS flag
                CREATE (f:Flag {
                    id: flag.id,
                    story_id: $story_id,
                    name: flag.name,
                    description: flag.description,
                    type: flag.type,
                    default_value: toString(flag.default_value)
                })
                CREATE (s)-[:HAS_FLAG]->(f)
            """, 
                story_id=story_id,
                flags=flags
            )
            
            print(f"  ✓ Created {len(flags)} flags")
    

    
    def _create_epilogue_variants(self, tx: Transaction, story_id: str, o3_data: Dict[str, Any]):
        """创建结局变体节点"""
        critical_points = o3_data.get('critical_points', {})
        endings = critical_points.get('endings', [])
        
        epilogue_count = 0
        for ending in endings:
            epilogue_variants = ending.get('epilogue_variants', [])
            
            for i, variant in enumerate(epilogue_variants):
                variant_id = f"{ending['scene_id']}_epilogue_{i}"
                
                # 创建EpilogueVariant节点
                tx.run("""
                    CREATE (ev:EpilogueVariant {
                        id: $variant_id,
                        story_id: $story_id,
                        ending_id: $ending_id,
                        conditions: $conditions,
                        narrative: $narrative
                    })
                """,
                    variant_id=variant_id,
                    story_id=story_id,
                    ending_id=ending['scene_id'],
                    conditions=json.dumps(variant.get('conditions', []), ensure_ascii=False),
                    narrative=variant.get('narrative', '')
                )
                
                # 创建从结局到变体的关系
                tx.run("""
                    MATCH (e:Ending {id: $ending_id, story_id: $story_id})
                    MATCH (ev:EpilogueVariant {id: $variant_id, story_id: $story_id})
                    CREATE (e)-[:HAS_EPILOGUE_VARIANT]->(ev)
                """,
                    ending_id=ending['scene_id'],
                    variant_id=variant_id,
                    story_id=story_id
                )
                
                epilogue_count += 1
        
        if epilogue_count > 0:
            print(f"  ✓ Created {epilogue_count} epilogue variants")
    
    def _create_concept_analysis(self, tx: Transaction, story_id: str, o3_data: Dict[str, Any]):
        """创建概念分析节点"""
        concept_analysis = o3_data.get('concept_analysis', {})
        
        if concept_analysis:
            # 创建ConceptAnalysis节点
            tx.run("""
                CREATE (ca:ConceptAnalysis {
                    story_id: $story_id,
                    user_intent: $user_intent,
                    emotional_core: $emotional_core,
                    target_audience: $target_audience,
                    narrative_approach: $narrative_approach,
                    visual_style_suggestion: $visual_style_suggestion,
                    core_concepts: $core_concepts,
                    unique_selling_points: $unique_selling_points,
                    game_mechanics_ideas: $game_mechanics_ideas
                })
            """,
                story_id=story_id,
                user_intent=concept_analysis.get('user_intent', ''),
                emotional_core=concept_analysis.get('emotional_core', ''),
                target_audience=concept_analysis.get('target_audience', ''),
                narrative_approach=concept_analysis.get('narrative_approach', ''),
                visual_style_suggestion=concept_analysis.get('visual_style_suggestion', ''),
                core_concepts=json.dumps(concept_analysis.get('core_concepts', []), ensure_ascii=False),
                unique_selling_points=json.dumps(concept_analysis.get('unique_selling_points', []), ensure_ascii=False),
                game_mechanics_ideas=json.dumps(concept_analysis.get('game_mechanics_ideas', []), ensure_ascii=False)
            )
            
            # 创建参考作品节点
            reference_works = concept_analysis.get('reference_works', [])
            if reference_works:
                tx.run("""
                    UNWIND $refs AS ref
                    CREATE (rw:ReferenceWork {
                        story_id: $story_id,
                        title: ref.title,
                        media_type: ref.media_type,
                        narrative_style: ref.narrative_style,
                        key_mechanics: $key_mechanics,
                        relevance: ref.relevance
                    })
                """,
                    story_id=story_id,
                    refs=reference_works,
                    key_mechanics=json.dumps([r.get('key_mechanics', []) for r in reference_works], ensure_ascii=False)
                )
                
                print(f"  ✓ Created ConceptAnalysis with {len(reference_works)} references")
    
    def _create_quality_report(self, tx: Transaction, story_id: str, o3_data: Dict[str, Any]):
        """创建质量报告节点（如果有）"""
        quality_report = o3_data.get('quality_report', {})
        
        if quality_report:
            # 提取嵌套的指标
            complexity = quality_report.get('complexity_analysis', {})
            coherence = quality_report.get('coherence_report', {})
            prereq_flow = quality_report.get('prerequisite_flow', {})
            replayability = quality_report.get('replayability_analysis', {})
            
            tx.run("""
                CREATE (qr:QualityReport {
                    story_id: $story_id,
                    total_paths: $total_paths,
                    average_path_length: $average_path_length,
                    max_branches_at_once: $max_branches_at_once,
                    choice_consequence_ratio: $choice_consequence_ratio,
                    scene_connectivity: $scene_connectivity,
                    narrative_consistency: $narrative_consistency,
                    hidden_content_percentage: $hidden_content_percentage,
                    gated_scenes_count: $gated_scenes_count,
                    meaningful_choices_ratio: $meaningful_choices_ratio,
                    unique_endings_count: $unique_endings_count,
                    overall_assessment: $overall_assessment
                })
            """,
                story_id=story_id,
                total_paths=complexity.get('total_paths', 0),
                average_path_length=complexity.get('average_path_length', 0),
                max_branches_at_once=complexity.get('max_branches_at_once', 0),
                choice_consequence_ratio=complexity.get('choice_consequence_ratio', 0),
                scene_connectivity=coherence.get('scene_connectivity', 0),
                narrative_consistency=coherence.get('narrative_consistency', 0),
                hidden_content_percentage=prereq_flow.get('hidden_content_percentage', 0),
                gated_scenes_count=prereq_flow.get('gated_scenes_count', 0),
                meaningful_choices_ratio=replayability.get('meaningful_choices_ratio', 0),
                unique_endings_count=replayability.get('unique_endings_count', 0),
                overall_assessment=quality_report.get('overall_assessment', '')
            )
            
            print(f"  ✓ Created QualityReport")
    
    def _create_major_branches(self, tx: Transaction, story_id: str, o3_data: Dict[str, Any]):
        """创建主要分支点节点"""
        critical_points = o3_data.get('critical_points', {})
        major_branches = critical_points.get('major_branches', [])
        
        if major_branches:
            tx.run("""
                UNWIND $branches AS branch
                CREATE (mb:MajorBranch {
                    story_id: $story_id,
                    scene_id: branch.scene_id,
                    branches_created: branch.branches_created,
                    significance: branch.significance
                })
            """,
                story_id=story_id,
                branches=major_branches
            )
            
            # 创建从场景到主要分支的关系
            tx.run("""
                UNWIND $branches AS branch
                MATCH (s:Scene {id: branch.scene_id, story_id: $story_id})
                MATCH (mb:MajorBranch {scene_id: branch.scene_id, story_id: $story_id})
                CREATE (s)-[:IS_MAJOR_BRANCH]->(mb)
            """,
                story_id=story_id,
                branches=major_branches
            )
            
            print(f"  ✓ Created {len(major_branches)} major branches")
    
    def _update_story_metadata_enhanced(self, tx: Transaction, story_id: str, o3_data: Dict[str, Any]):
        """更新Story节点的增强元数据"""
        story_config = o3_data.get('story_config', {})
        complexity_controls = story_config.get('complexity_controls', {})
        
        tx.run("""
            MATCH (s:Story {id: $story_id})
            SET s.branching_strategy = $branching_strategy,
                s.max_concurrent_branches = $max_concurrent_branches,
                s.branch_depth = $branch_depth,
                s.hub_episode = $hub_episode,
                s.endings_per_route = $endings_per_route
        """,
            story_id=story_id,
            branching_strategy=story_config.get('branching_strategy', 'endings_first'),
            max_concurrent_branches=complexity_controls.get('max_concurrent_branches', 3),
            branch_depth=complexity_controls.get('branch_depth', 4),
            hub_episode=str(complexity_controls.get('hub_episode', '3_or_4')),
            endings_per_route=complexity_controls.get('endings_per_route', 3)
        )
    
    def import_o3_game_from_file(self, filename: str) -> str:
        """从文件导入O3游戏数据的便利方法
        
        Args:
            filename: 游戏数据文件路径
            
        Returns:
            story_id: 导入的故事ID
        """
        with open(filename, 'r', encoding='utf-8') as f:
            game_data = json.load(f)
        
        return self.import_o3_game(game_data, filename)

    def _show_statistics(self, story_id: str):
        """显示导入统计信息"""
        print("\n📊 Import Statistics:")
        
        with self.driver.session() as session:
            # 统计各类节点
            stats = session.run("""
                MATCH (n {story_id: $story_id})
                WITH labels(n) as node_labels, count(n) as count
                UNWIND node_labels as label
                WITH label, sum(count) as total
                WHERE label <> 'StoryNode'
                RETURN label, total
                ORDER BY total DESC
            """, story_id=story_id).data()
            
            for stat in stats:
                print(f"  - {stat['label']}: {stat['total']} nodes")
            
            # 统计关系
            rel_count = session.run("""
                MATCH (n:StoryNode {story_id: $story_id})-[r:PLAYER_CHOICE]->()
                RETURN count(r) as count
            """, story_id=story_id).single()['count']
            
            print(f"  - Choices: {rel_count} relationships")
            
            # 统计剧集分布
            episode_stats = session.run("""
                MATCH (n:Scene {story_id: $story_id})
                RETURN n.episode as episode, count(n) as count
                ORDER BY episode
            """, story_id=story_id).data()
            
            if episode_stats:
                print("\n📊 Episode Distribution:")
                for stat in episode_stats:
                    print(f"  - Episode {stat['episode']}: {stat['count']} scenes")


# 使用示例
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # 获取Neo4j连接信息
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')
    
    if not neo4j_password:
        print("❌ Please set NEO4J_PASSWORD in .env file")
        exit(1)
    
    # 创建导入器
    importer = Neo4jDirectImporter(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        # 从文件导入游戏数据
        import sys
        if len(sys.argv) > 1:
            filename = sys.argv[1]
            
            # 使用便利方法直接从文件导入
            story_id = importer.import_o3_game_from_file(filename)
            print(f"\n✅ Successfully imported story: {story_id}")
        else:
            print("Usage: python neo4j_direct_importer.py <game_file.json>")
    
    finally:
        importer.close() 