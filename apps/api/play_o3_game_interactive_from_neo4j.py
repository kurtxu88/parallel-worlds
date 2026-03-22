#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
O3 Interactive Screenplay Player - Neo4j Version
Play O3-generated interactive screenplays from Neo4j database with natural language interactions powered by GPT-4.1
"""

import os
import json
import re
from typing import Dict, List, Optional, Tuple, Generator, Any
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import glob
from neo4j import GraphDatabase
import time

class O3ScreenplayPlayer:
    """Interactive player for O3-generated screenplays from Neo4j"""
    
    def __init__(self):
        """Initialize the screenplay player with OpenAI GPT-4.1 and Neo4j"""
        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            timeout=30.0
        )
        self.model = "gpt-4.1-2025-04-14"  # Using same model as scene_microinteraction_director
        
        # Initialize Neo4j connection
        neo4j_uri = os.getenv('NEO4J_URI')
        neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
        neo4j_password = os.getenv('NEO4J_PASSWORD')
        
        if not neo4j_uri or not neo4j_password:
            raise ValueError("Neo4j credentials missing. Set NEO4J_URI and NEO4J_PASSWORD in .env file")
        
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        # Screenplay state
        self.screenplay_data = None
        self.current_scene = None
        self.story_flags = {}  # Track flag values
        self.conversation_history = []  # Full history (kept for save/load compatibility)
        self.scene_history = []  # Track visited scenes

        self.scene_interaction_count = 0  # Track interactions in current scene
        self.story_id = None  # Current story ID
        self.current_emotional_beat = 0  # Track emotional progression in scene
        
        # Simplified episode-based history management
        self.current_episode = None  # Current episode number
        self.episode_conversation_history = []  # History for current episode (includes cross-episode context)
        self.max_cross_episode_context = 6  # Keep important context when switching episodes
        
        # 剧本内容记录（不包含技术标识）
        self.screenplay_content_history = []  # 纯剧本内容，用于沉浸式体验
    
    def load_game(self, story_id: str):
        """Load a game from Neo4j by story ID"""
        self.story_id = story_id
        
        with self.driver.session() as session:
            # Load story metadata
            result = session.run("""
                MATCH (s:Story {id: $story_id})
                RETURN s
            """, story_id=story_id)
            
            story_record = result.single()
            if not story_record:
                raise ValueError(f"Story with ID {story_id} not found in Neo4j")
            
            story_node = dict(story_record['s'])
            
            # Load StoryBrief (if available)
            brief_result = session.run("""
                MATCH (sb:StoryBrief {story_id: $story_id})
                RETURN sb
            """, story_id=story_id)
            
            story_brief = None
            brief_record = brief_result.single()
            if brief_record:
                story_brief = dict(brief_record['sb'])
                del story_brief['story_id']  # Remove redundant field
            
            # Load Characters (if available)
            chars_result = session.run("""
                MATCH (c:Character {story_id: $story_id})
                RETURN c
                ORDER BY c.name
            """, story_id=story_id)
            
            characters = []
            for record in chars_result:
                char = dict(record['c'])
                del char['story_id']  # Remove redundant field
                characters.append(char)
            
            # Load all scenes for this story
            scenes_result = session.run("""
                MATCH (n:StoryNode {story_id: $story_id})
                WHERE 'Scene' IN labels(n) OR 'Checkpoint' IN labels(n) OR 'Ending' IN labels(n)
                RETURN n, labels(n) as node_labels
                ORDER BY n.episode, n.id
            """, story_id=story_id)
            
            scenes = []
            for record in scenes_result:
                node = dict(record['n'])
                labels = record['node_labels']
                
                # Parse JSON fields
                if 'content' in node and isinstance(node['content'], str):
                    node['content'] = json.loads(node['content'])
                
                # Determine type from labels
                if 'Ending' in labels:
                    node['type'] = 'ending'
                elif 'Checkpoint' in labels:
                    node['type'] = 'bottleneck'
                elif 'Hub' in labels:
                    node['type'] = 'hub'
                elif 'Emotional' in labels:
                    node['type'] = 'emotional'
                else:
                    node['type'] = 'normal'
                
                scenes.append(node)
            
            # Load flags from Flag nodes (not from scenes)
            flags_result = session.run("""
                MATCH (f:Flag {story_id: $story_id})
                RETURN f
                ORDER BY f.id
            """, story_id=story_id)
            
            flags = []
            for record in flags_result:
                flag_node = dict(record['f'])
                # Convert default_value back to proper type
                default_value = flag_node.get('default_value', 'false')
                if flag_node['type'] == 'boolean':
                    default_value = default_value.lower() == 'true'
                elif flag_node['type'] == 'counter':
                    default_value = int(default_value) if default_value.isdigit() else 0
                elif flag_node['type'] == 'value':
                    default_value = default_value  # Keep as string
                
                flags.append({
                    'id': flag_node['id'],
                    'name': flag_node['name'],
                    'description': flag_node.get('description', ''),
                    'type': flag_node['type'],
                    'default_value': default_value
                })
            

            
            # Load critical points (start scene, endings)
            # First get the start scene
            start_result = session.run("""
                MATCH (n:StoryNode {story_id: $story_id})
                WHERE n.episode = 1
                RETURN n.id as start_scene
                ORDER BY n.id
                LIMIT 1
            """, story_id=story_id)
            
            start_record = start_result.single()
            start_scene = start_record['start_scene'] if start_record else None
            
            # Then get endings with epilogue variants
            endings_result = session.run("""
                MATCH (e:Ending {story_id: $story_id})
                OPTIONAL MATCH (e)-[:HAS_EPILOGUE_VARIANT]->(ep:EpilogueVariant)
                WITH e, collect(DISTINCT {
                    conditions: ep.conditions,
                    narrative: ep.narrative
                }) as epilogue_variants
                RETURN collect(DISTINCT {
                    scene_id: e.id,
                    ending_type: e.title,
                    description: e.description,
                    epilogue_variants: epilogue_variants
                }) as endings
            """, story_id=story_id)
            
            endings_record = endings_result.single()
            endings = endings_record['endings'] if endings_record else []
            
            # Get episodes count from actual scenes
            episodes_result = session.run("""
                MATCH (n:StoryNode {story_id: $story_id})
                RETURN max(n.episode) as max_episode
            """, story_id=story_id)
            
            episodes_record = episodes_result.single()
            episodes = episodes_record['max_episode'] if episodes_record['max_episode'] else story_node.get('episodes', 5)
            
            # Construct screenplay_data structure with proper metadata
            self.screenplay_data = {
                'story_id': story_id,
                'metadata': {
                    'title': story_node.get('title', 'Untitled'),  # Use stored title
                    'genre': story_node.get('genre', 'Interactive Story'),  # Use stored genre
                    'culture_language': story_node.get('culture_language', 'en-US'),  # Use stored language
                    'filename': story_node.get('filename', '')  # Keep filename for reference
                },
                'story_config': {
                    'episodes': episodes,
                    'total_scenes': len(scenes),
                    'branching_strategy': story_node.get('branching_strategy', 'endings_first')
                },
                'story_brief': story_brief,  # Add story brief
                'characters': characters,    # Add characters
                'flags': flags,  # Use flags from Flag nodes
                'scenes': scenes,
                'critical_points': {
                    'start_scene': start_scene if start_scene else scenes[0]['id'] if scenes else 'S1',
                    'endings': endings
                },
                'concept_analysis': {
                    'emotional_core': story_brief.get('emotional_storyline', '') if story_brief else ''  # Extract from story brief
                }
            }
            
            # Initialize flags with their default values
            for flag in self.screenplay_data.get('flags', []):
                self.story_flags[flag['id']] = flag['default_value']
            
        print(f"\n🎬 Loaded: {self.screenplay_data['metadata']['title']}")
        print(f"📖 Genre: {self.screenplay_data['metadata']['genre']}")
        print(f"🌍 Language: {self.screenplay_data['metadata'].get('culture_language', 'en-US')}")
        print(f"🎬 Episodes: {self.screenplay_data['story_config']['episodes']}")
        print(f"🎯 Scenes: {self.screenplay_data['story_config']['total_scenes']}")
        print(f"🚩 Flags: {len(self.screenplay_data['flags'])}")
        print(f"🏁 Endings: {len(self.screenplay_data['critical_points']['endings'])}")
        
        # Show if we have enhanced content
        if story_brief:
            print(f"📚 Story Brief: ✓ (Total ~{sum([len(v) for v in story_brief.values() if isinstance(v, str)])} 字)")
        if characters:
            print(f"👥 Characters: {len(characters)} detailed profiles")
        
        # Count scene types
        scene_types = {}
        for scene in scenes:
            scene_type = scene.get('type', 'normal')
            scene_types[scene_type] = scene_types.get(scene_type, 0) + 1
        
        if scene_types:
            print(f"📊 Scene Types: " + ", ".join([f"{t}: {c}" for t, c in scene_types.items()]))
        
        return True  # 返回成功标志

    def start_game(self):
        """Start playing from the beginning"""
        start_scene_id = self.screenplay_data['critical_points']['start_scene']
        self.load_scene(start_scene_id)
    
    def load_scene(self, scene_id: str):
        """Load a specific scene"""
        # Find scene in the scenes list
        scene = next((s for s in self.screenplay_data['scenes'] if s['id'] == scene_id), None)
        if not scene:
            print(f"❌ Scene {scene_id} not found!")
            return
        
        # Check if we're switching episodes
        new_episode = scene.get('episode', 1)
        
        if self.current_episode is not None and new_episode != self.current_episode:
            # Episode transition: prepare cross-episode context
            cross_episode_context = self._prepare_cross_episode_context()
            
            # Create new episode history with context
            culture_language = self.screenplay_data['metadata'].get('culture_language', 'en-US')
            if culture_language == 'zh-CN':
                episode_marker = f"=== 第 {new_episode} 集 ==="
                screenplay_episode = f"\n\n第 {new_episode} 集\n\n"
            else:
                episode_marker = f"=== Episode {new_episode} ==="
                screenplay_episode = f"\n\nEpisode {new_episode}\n\n"
            
            episode_msg = {"role": "system", "content": episode_marker}
            
            # Reset episode history with cross-episode context
            self.episode_conversation_history = [
                *cross_episode_context,
                episode_msg
            ]
            
            # Add to full history and screenplay content
            self.conversation_history.append(episode_msg)
            self.screenplay_content_history.append(screenplay_episode)
        
        # Initialize current episode if not set
        if self.current_episode is None:
            self.current_episode = new_episode
        
        # Add scene transition marker (simplified)
        if self.current_scene:  # Not the first scene
            culture_language = self.screenplay_data['metadata'].get('culture_language', 'en-US')
            if culture_language == 'zh-CN':
                scene_marker = f"[场景：{scene['title']}]"
                screenplay_transition = f"\n\n[场景转换至：{scene['title']}]\n\n"
            else:
                scene_marker = f"[Scene: {scene['title']}]"
                screenplay_transition = f"\n\n[Transition to: {scene['title']}]\n\n"
            
            scene_msg = {"role": "system", "content": scene_marker}
            
            self.conversation_history.append(scene_msg)
            self.episode_conversation_history.append(scene_msg)
            self.screenplay_content_history.append(screenplay_transition)
        
        self.current_scene = scene
        self.current_episode = new_episode
        self.scene_history.append(scene_id)
        self.scene_interaction_count = 0  # Reset interaction count for new scene
        
        # Generate transition if this is not the first scene
        if len(self.scene_history) > 1:
            # Get previous scene
            prev_scene_id = self.scene_history[-2]
            prev_scene = next((s for s in self.screenplay_data['scenes'] if s['id'] == prev_scene_id), None)
            if prev_scene:
                self._generate_scene_transition(prev_scene, scene)
        
        # Display scene first (for all scenes including endings)
        self._display_scene()
    
    def _prepare_cross_episode_context(self) -> List[Dict]:
        """Prepare cross-episode context when switching episodes"""
        if len(self.episode_conversation_history) == 0:
            return []
        
        # Only keep the most important conversation messages, filter out system markers
        important_messages = []
        for msg in reversed(self.episode_conversation_history):
            if msg['role'] in ['user', 'assistant']:
                important_messages.insert(0, msg)
                if len(important_messages) >= self.max_cross_episode_context:
                    break
        
        # Add context marker if we have cross-episode history
        if important_messages:
            culture_language = self.screenplay_data['metadata'].get('culture_language', 'en-US')
            if culture_language == 'zh-CN':
                context_marker = "=== 上一集的剧情回顾 ==="
            else:
                context_marker = "=== Previous Episode Context ==="
            
            return [
                {"role": "system", "content": context_marker},
                *important_messages
            ]
        
        return important_messages
        
        # Then check if this is an ending
        if self._check_ending():
            return
    
    def _check_ending(self):
        """Check if current scene is an ending and handle it"""
        if self.current_scene.get('type') == 'ending':
            # Check both possible locations for endings
            endings = []
            
            # Try O3 Game Designer format first (critical_points.endings)
            if 'critical_points' in self.screenplay_data and 'endings' in self.screenplay_data['critical_points']:
                endings = self.screenplay_data['critical_points']['endings']
            # Fallback to direct endings field
            elif 'endings' in self.screenplay_data:
                endings = self.screenplay_data['endings']
            
            if endings:
                # Find the ending that matches this scene
                ending = None
                for e in endings:
                    # Match by scene_id or by ending_id
                    if e.get('scene_id') == self.current_scene['id'] or (self.current_scene.get('ending_id') and e.get('id') == self.current_scene.get('ending_id')):
                        ending = e
                        break
                
                if ending:
                    self.show_ending(ending)
                    return True
            else:
                # Fallback: treat as ending scene even without formal ending data
                culture_language = self.screenplay_data['metadata'].get('culture_language', 'en-US')
                print("\n" + "="*60)
                if culture_language == 'zh-CN':
                    print("🏁 结局已达成")
                else:
                    print("🏁 ENDING REACHED")
                print("="*60)
                
                # The scene content has already been displayed by _display_scene()
                # Just show the ending type if available
                if self.current_scene.get('ending_type'):
                    print(f"\n🎭 {self.current_scene['ending_type']}")
                
                # Show game statistics
                if culture_language == 'zh-CN':
                    print(f"\n📊 你的旅程：")
                    print(f"  访问场景数：{len(set(self.scene_history))}")
                    print(f"  做出选择数：{len(self.scene_history) - 1}")
                else:
                    print(f"\n📊 Your Journey:")
                    print(f"  Scenes visited: {len(set(self.scene_history))}")
                    print(f"  Total choices made: {len(self.scene_history) - 1}")
                
                if self.story_flags:
                    if culture_language == 'zh-CN':
                        print(f"\n🚩 最终状态：")
                    else:
                        print(f"\n🚩 Final Flags:")
                    for flag_id, value in self.story_flags.items():
                        flag_info = next((f for f in self.screenplay_data['flags'] if f['id'] == flag_id), None)
                        if flag_info:
                            print(f"  {flag_info['name']}: {value}")
                
                return True
        
        return False
    
    def _check_prerequisites(self, prerequisites: List[Dict]) -> bool:
        """Check if prerequisites are met"""
        for prereq in prerequisites:
            flag_id = prereq['flag_id']
            operator = prereq['operator']
            value = prereq['value']
            
            if flag_id not in self.story_flags:
                return False
            
            flag_value = self.story_flags[flag_id]
            
            if operator == '==':
                if flag_value != value:
                    return False
            elif operator == '!=':
                if flag_value == value:
                    return False
            elif operator == '>':
                if flag_value <= value:
                    return False
            elif operator == '<':
                if flag_value >= value:
                    return False
            elif operator == '>=':
                if flag_value < value:
                    return False
            elif operator == '<=':
                if flag_value > value:
                    return False
        
        return True
    
    def _apply_consequences(self, consequences: List[Dict]):
        """Apply choice consequences to flags"""
        for consequence in consequences:
            flag_id = consequence['flag_id']
            operation = consequence['operation']
            value = consequence['value']
            
            if operation == 'set':
                self.story_flags[flag_id] = value
            elif operation == 'add':
                self.story_flags[flag_id] = self.story_flags.get(flag_id, 0) + value
            elif operation == 'subtract':
                self.story_flags[flag_id] = self.story_flags.get(flag_id, 0) - value
    
    def _generate_scene_transition(self, from_scene: Dict, to_scene: Dict):
        """Generate a smooth transition between scenes"""
        try:
            # Get culture/language settings
            culture_language = self.screenplay_data['metadata'].get('culture_language', 'en-US')
            is_chinese = culture_language == 'zh-CN'
            
            # Extract additional context for better transitions
            from_atmosphere = from_scene.get('content', {}).get('atmosphere', '')
            to_atmosphere = to_scene.get('content', {}).get('atmosphere', '')
            from_episode = from_scene.get('episode', 1)
            to_episode = to_scene.get('episode', 1)
            
            # Check if this is an episode transition
            episode_change = from_episode != to_episode
            
            # Get concept analysis data for consistent tone and style
            concept_analysis = self.screenplay_data.get('concept_analysis', {})
            emotional_core = concept_analysis.get('emotional_core', '')
            visual_style = concept_analysis.get('visual_style_suggestion', '')
            
            if is_chinese:
                system_prompt = f"""你是一个场景转换导演。你的任务是创建流畅自然的过渡。

故事背景：
- 类型：{self.screenplay_data['metadata']['genre']}
- 情感核心：{emotional_core}
- 视觉风格：{visual_style}

转换要求：
- 简短（1-2句话）
- 保持叙事连贯性
- 体现时间、地点或情绪的转变
- 使用第二人称
- 符合故事的整体氛围和视觉风格
- 从"{from_atmosphere}"氛围过渡到"{to_atmosphere}"氛围
{"- 注意：这是跨章节转换，需要适当的时间跨度感" if episode_change else ""}"""
            else:
                system_prompt = f"""You are a scene transition director. Your task is to create smooth, natural transitions between scenes.

Story Context:
- Genre: {self.screenplay_data['metadata']['genre']}
- Emotional Core: {emotional_core}
- Visual Style: {visual_style}

Transition Requirements:
- Brief (1-2 sentences)
- Maintain narrative coherence
- Show passage of time, change of location, or emotional shift
- Use second person
- Match the game's overall atmosphere and visual style
- Transition from "{from_atmosphere}" atmosphere to "{to_atmosphere}" atmosphere
{"- Note: This is a cross-episode transition, convey appropriate time passage" if episode_change else ""}"""

            from_info = f"从场景：{from_scene['title']}（{from_scene['description']}）- {from_atmosphere}" if is_chinese else f"From Scene: {from_scene['title']} ({from_scene['description']}) - {from_atmosphere}"
            to_info = f"到场景：{to_scene['title']}（{to_scene['description']}）- {to_atmosphere}" if is_chinese else f"To Scene: {to_scene['title']} ({to_scene['description']}) - {to_atmosphere}"
            
            user_prompt = f"{from_info}\n→\n{to_info}"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,  # Slightly higher for variety
                max_tokens=200,
                stream=True
            )
            
            # Stream the transition
            print("\n" + "~"*60)
            for chunk in response:
                if chunk.choices[0].delta.content:
                    print(chunk.choices[0].delta.content, end='', flush=True)
            print("\n" + "~"*60)
            
            # Small pause for dramatic effect
            import time
            time.sleep(1)
            
        except Exception as e:
            # Silent fail - don't break the game flow
            pass
    
    def _display_scene(self):
        """Display the current scene"""
        # Check if this is an ending scene
        is_ending = self.current_scene.get('type') == 'ending'
        is_emotional = self.current_scene.get('type') == 'emotional'
        is_hub = self.current_scene.get('type') == 'hub'
        
        culture_language = self.screenplay_data['metadata'].get('culture_language', 'en-US')
        
        if is_ending:
            # Special display for ending scenes
            print("\n" + "✦"*60)
            print("═"*60)
            if culture_language == 'zh-CN':
                print(f"🎭 终章 - {self.current_scene['title']}")
                print(f"🎬 第 {self.current_scene['episode']} 集")
            else:
                print(f"🎭 Final Chapter - {self.current_scene['title']}")
                print(f"🎬 Episode {self.current_scene['episode']}")
            print("═"*60)
            print("✦"*60)
        elif is_emotional:
            # Special display for emotional scenes
            print("\n" + "💭"*60)
            print(f"💫 {self.current_scene['title']}")
            print(f"🎬 Episode {self.current_scene['episode']}")
            print("💭"*60)
        elif is_hub:
            # Special display for hub scenes
            print("\n" + "🔸"*60)
            print("⚡"*60)
            if culture_language == 'zh-CN':
                print(f"🎯 关键抉择 - {self.current_scene['title']}")
            else:
                print(f"🎯 Critical Choice - {self.current_scene['title']}")
            print(f"🎬 Episode {self.current_scene['episode']}")
            print("⚡"*60)
            print("🔸"*60)
        else:
            # Normal scene display
            print("\n" + "="*60)
            print(f"📍 {self.current_scene['title']}")
            print(f"🎬 Episode {self.current_scene['episode']}")
            print("="*60)
        
        # Prepare available choices for AI context (but don't display them)
        self._prepare_available_choices()
        
        # Use GPT to enhance the narrative (this will stream)
        self._enhance_narrative()
        

        
        # Special ending marker after the scene content
        if is_ending:
            print("\n" + "✦"*60)
        else:
            print()  # Ensure newline after streaming
    
    def _enhance_narrative(self) -> str:
        """Use GPT-4.1 to enhance the scene narrative with dramatic focus"""
        try:
            # Get culture/language settings
            culture_language = self.screenplay_data['metadata'].get('culture_language', 'en-US')
            is_chinese = culture_language == 'zh-CN'
            
            # Check scene type
            is_ending = self.current_scene.get('type') == 'ending'
            is_emotional = self.current_scene.get('type') == 'emotional'
            is_hub = self.current_scene.get('type') == 'hub'
            
            # Build global context from story_brief and characters
            global_context = ""
            
            # Add story brief context
            if self.screenplay_data.get('story_brief'):
                brief = self.screenplay_data['story_brief']
                if is_chinese:
                    global_context += "\n\n【全局故事背景】\n"
                    if brief.get('world_setting'):
                        global_context += f"\n世界设定：\n{brief['world_setting']}\n"
                    if brief.get('main_plot'):
                        global_context += f"\n主线剧情：\n{brief['main_plot']}\n"
                    if brief.get('theme_depth'):
                        global_context += f"\n核心主题：\n{brief['theme_depth']}\n"
                    if brief.get('innovation_highlights'):
                        global_context += f"\n创新亮点：\n{brief['innovation_highlights']}\n"
                else:
                    global_context += "\n\n[GLOBAL STORY CONTEXT]\n"
                    if brief.get('world_setting'):
                        global_context += f"\nWorld Setting:\n{brief['world_setting']}\n"
                    if brief.get('main_plot'):
                        global_context += f"\nMain Plot:\n{brief['main_plot']}\n"
                    if brief.get('theme_depth'):
                        global_context += f"\nCore Theme:\n{brief['theme_depth']}\n"
                    if brief.get('innovation_highlights'):
                        global_context += f"\nInnovation Highlights:\n{brief['innovation_highlights']}\n"
            
            # Add character context
            character_profiles = ""
            if self.screenplay_data.get('characters'):
                # Find characters mentioned in current scene
                scene_narrative = self.current_scene.get('content', {}).get('narrative', '')
                scene_title = self.current_scene.get('title', '')
                scene_desc = self.current_scene.get('description', '')
                scene_text = f"{scene_title} {scene_desc} {scene_narrative}"
                
                relevant_chars = []
                for char in self.screenplay_data['characters']:
                    char_name = char.get('name', '')
                    if char_name and char_name in scene_text:
                        relevant_chars.append(char)
                
                if relevant_chars:
                    if is_chinese:
                        character_profiles += "\n\n【场景相关人物】\n"
                        for char in relevant_chars:  # Use all relevant characters
                            character_profiles += f"\n{char['name']}：\n"
                            # 显示角色类型
                            char_type = char.get('character_type', 'major_npc')
                            type_labels = {
                                'protagonist': '主角',
                                'major_npc': '重要角色',
                                'minor_npc': '配角'
                            }
                            character_profiles += f"- 角色类型：{type_labels.get(char_type, char_type)}\n"
                            
                            if char.get('basic_info'):
                                character_profiles += f"- 基本信息：{char['basic_info']}\n"
                            if char.get('biography'):
                                character_profiles += f"- 人物背景：{char['biography']}\n"
                            if char.get('key_dialogue_style'):
                                character_profiles += f"- 对话风格：{char['key_dialogue_style']}\n"
                            # Add more depth for emotional scenes
                            if is_emotional and char.get('inner_conflict'):
                                character_profiles += f"- 内在冲突：{char['inner_conflict']}\n"
                            # Add growth arc for hub scenes
                            if is_hub and char.get('growth_arc'):
                                character_profiles += f"- 成长轨迹：{char['growth_arc']}\n"
                            # Add relationships for all scenes
                            if char.get('relationships'):
                                character_profiles += f"- 人际关系：{char['relationships']}\n"
                    else:
                        character_profiles += "\n\n[SCENE-RELEVANT CHARACTERS]\n"
                        for char in relevant_chars:
                            character_profiles += f"\n{char['name']}:\n"
                            # Display character type
                            char_type = char.get('character_type', 'major_npc')
                            type_labels = {
                                'protagonist': 'Protagonist',
                                'major_npc': 'Major Character',
                                'minor_npc': 'Supporting Character'
                            }
                            character_profiles += f"- Character Type: {type_labels.get(char_type, char_type)}\n"
                            
                            if char.get('basic_info'):
                                character_profiles += f"- Basic Info: {char['basic_info']}\n"
                            if char.get('biography'):
                                character_profiles += f"- Character Background: {char['biography']}\n"
                            if char.get('key_dialogue_style'):
                                character_profiles += f"- Dialogue Style: {char['key_dialogue_style']}\n"
                            # Add more depth for emotional scenes
                            if is_emotional and char.get('inner_conflict'):
                                character_profiles += f"- Inner Conflict: {char['inner_conflict']}\n"
                            # Add growth arc for hub scenes
                            if is_hub and char.get('growth_arc'):
                                character_profiles += f"- Growth Arc: {char['growth_arc']}\n"
                            # Add relationships for all scenes
                            if char.get('relationships'):
                                character_profiles += f"- Relationships: {char['relationships']}\n"
            
            # Build flag state context for AI
            flag_context = ""
            if self.screenplay_data.get('flags') and self.story_flags:
                changed_flags = []
                for flag in self.screenplay_data['flags']:
                    flag_id = flag['id']
                    current_value = self.story_flags.get(flag_id, flag['default_value'])
                    
                    # Only include flags that have changed from default
                    if current_value != flag['default_value']:
                        # Format value based on type
                        if flag['type'] == 'boolean':
                            value_text = "是" if current_value else "否" if is_chinese else "Yes" if current_value else "No"
                        else:
                            value_text = str(current_value)
                        
                        changed_flags.append({
                            'name': flag['name'],
                            'description': flag.get('description', ''),
                            'value': value_text,
                            'type': flag['type']
                        })
                
                if changed_flags:
                    if is_chinese:
                        flag_context = "\n\n当前剧情状态（用于调整角色行为和反应）：\n"
                        for fc in changed_flags:
                            flag_context += f"- {fc['name']}: {fc['value']}\n"
                            if fc['description']:
                                flag_context += f"  说明：{fc['description']}\n"
                    else:
                        flag_context = "\n\nCurrent Story States (use these to inform character behavior and reactions):\n"
                        for fc in changed_flags:
                            flag_context += f"- {fc['name']}: {fc['value']}\n"
                            if fc['description']:
                                flag_context += f"  Description: {fc['description']}\n"
            
            # Build dramatic choices context for the AI
            choices_context = ""
            if hasattr(self, 'available_choices'):
                choices_context = "\n\nDramatic Decision Points (for your awareness, DO NOT mention these directly):\n" if not is_chinese else "\n\n戏剧决定点（供你参考，不要直接提及）：\n"
                for i, (_, choice, _) in enumerate(self.available_choices, 1):
                    # Add priority indicators based on weight
                    if choice.get('weight') == 'major':
                        priority = "[关键转折]" if is_chinese else "[MAJOR TURNING POINT]"
                    elif choice.get('weight') == 'minor':
                        priority = "[情节发展]" if is_chinese else "[PLOT DEVELOPMENT]" 
                    else:
                        priority = "[角色塑造]" if is_chinese else "[CHARACTER MOMENT]"
                    
                    choices_context += f"{i}. {choice['choice_text']} {priority}\n"
                    if choice.get('internal_reasoning'):
                        choices_context += f"   内心动机：{choice['internal_reasoning']}\n" if is_chinese else f"   Inner Motivation: {choice['internal_reasoning']}\n"
                    if choice.get('consequences'):
                        consequences_text = self._format_consequences(choice['consequences'])
                        if consequences_text:
                            choices_context += f"   剧情影响：{consequences_text}\n" if is_chinese else f"   Story Impact: {consequences_text}\n"
            
            # Build key events context
            key_events_context = ""
            content = self.current_scene.get('content', {})
            if content.get('key_events'):
                key_events_context = "\n\n场景核心冲突：\n" if is_chinese else "\n\nCore Scene Conflicts:\n"
                for event in content['key_events']:
                    key_events_context += f"• {event}\n"
            
            # Get concept analysis data for consistent style
            concept_analysis = self.screenplay_data.get('concept_analysis', {})
            emotional_core = concept_analysis.get('emotional_core', '')
            narrative_approach = concept_analysis.get('narrative_approach', '')
            visual_style = concept_analysis.get('visual_style_suggestion', '')
            core_concepts = concept_analysis.get('core_concepts', [])
            
            
            

            
            # Special handling for different scene types
            if is_emotional:
                # Emotional progression scenes need special handling
                if is_chinese:
                    emotional_guidance = """
【特殊任务：情感递进场景】
这是一个专门深化情感的场景，需要：

1. 节奏放缓：
   - 给角色和观众时间消化之前的选择
   - 使用更多的停顿、沉默和眼神交流
   - 环境细节烘托内心状态

2. 情感深度：
   - 深入探索角色的内心世界
   - 展现选择带来的情感后果
   - 让角色表达平时隐藏的真实感受

3. 亲密时刻：
   - 创造二人独处或内心独白的空间
   - 使用更私密的对话方式
   - 触及角色的脆弱面

4. 细腻描写：
   - 注重微表情和小动作
   - 使用感官细节增强情感体验
   - 让沉默和留白产生力量
"""
                else:
                    emotional_guidance = """
[SPECIAL TASK: EMOTIONAL PROGRESSION SCENE]
This is a scene dedicated to deepening emotions, requiring:

1. Slowed Pace:
   - Give characters and audience time to digest previous choices
   - Use more pauses, silences, and eye contact
   - Environmental details enhance inner states

2. Emotional Depth:
   - Deeply explore characters' inner worlds
   - Show emotional consequences of choices
   - Let characters express usually hidden true feelings

3. Intimate Moments:
   - Create space for two-person scenes or inner monologues
   - Use more intimate dialogue styles
   - Touch on characters' vulnerable sides

4. Delicate Description:
   - Focus on micro-expressions and small gestures
   - Use sensory details to enhance emotional experience
   - Let silence and space create power
"""
            elif is_hub:
                # Hub scenes need to emphasize the weight of choice
                if is_chinese:
                    hub_guidance = """
【特殊任务：Hub场景】
这是故事的关键分岔点，需要：

1. 选择的重量：
   - 明确展示每个选择的价值观冲突
   - 让角色充分理解选择的后果
   - 没有"正确"答案，只有不同的道路

2. 戏剧张力：
   - 将之前积累的矛盾推向顶点
   - 多方势力在此交汇
   - 时间压力或外部危机

3. 角色立场：
   - 每个重要角色都表明立场
   - 展现他们对主角选择的期待或压力
   - 揭示隐藏的动机和秘密
"""
                else:
                    hub_guidance = """
[SPECIAL TASK: HUB SCENE]
This is the story's key branching point, requiring:

1. Weight of Choice:
   - Clearly show value conflicts in each choice
   - Let characters fully understand consequences
   - No "correct" answer, only different paths

2. Dramatic Tension:
   - Push accumulated conflicts to their peak
   - Multiple forces converge here
   - Time pressure or external crisis

3. Character Positions:
   - Each important character declares their position
   - Show their expectations or pressure on protagonist's choice
   - Reveal hidden motivations and secrets
"""
            elif is_ending:
                if is_chinese:
                    ending_guidance = """
【特殊任务：结局场景】
这是故事的终章，需要特殊的戏剧处理：

1. 仪式感呈现：
   - 使用更加诗意和隽永的语言
   - 加入视觉化的意象（光影、色彩、声音）
   - 营造"落幕"的氛围

2. 情感升华：
   - 将整个故事的情感主题推向顶峰
   - 角色获得顿悟或转变
   - 留下深刻的情感印记

3. 故事钩子：
   - 在结尾埋下引人深思的问题
   - 暗示未来的可能性
   - 或者留下某个未解之谜
   - 让观众在离开后仍在思考

4. 呈现技巧：
   - 最后一句话要特别有力量
   - 可以使用时间跳跃（"多年后..."）
   - 或者视角转换（从另一个角度看这个结局）
   - 考虑使用象征性的物品或动作

示例钩子类型：
- 循环式：故事回到开始，但一切已不同
- 悬念式：揭示一个改变一切的秘密
- 哲思式：提出一个关于人性的问题
- 希望式：黑暗中的一束光
- 反转式：最后时刻的意外真相
"""
                else:
                    ending_guidance = """
[SPECIAL TASK: ENDING SCENE]
This is the story's finale, requiring special dramatic treatment:

1. Ceremonial Presentation:
   - Use more poetic and lasting language
   - Include visual imagery (light/shadow, colors, sounds)
   - Create a "curtain falling" atmosphere

2. Emotional Elevation:
   - Push the story's emotional theme to its peak
   - Characters achieve epiphany or transformation
   - Leave a deep emotional imprint

3. Story Hook:
   - Plant thought-provoking questions at the end
   - Hint at future possibilities
   - Or leave an unsolved mystery
   - Keep the audience thinking after they leave

4. Presentation Techniques:
   - Make the last line especially powerful
   - Consider time jumps ("Years later...")
   - Or perspective shifts (seeing the ending from another angle)
   - Use symbolic objects or actions

Hook Types:
- Circular: Story returns to beginning, but everything has changed
- Suspense: Reveal a secret that changes everything
- Philosophical: Pose a question about human nature
- Hope: A ray of light in darkness
- Reversal: Last-moment unexpected truth
"""
            else:
                ending_guidance = ""
            
            # Combine all special guidance
            special_guidance = ""
            if is_emotional:
                special_guidance = emotional_guidance
            elif is_hub:
                special_guidance = hub_guidance
            elif is_ending:
                special_guidance = ending_guidance
            
            if is_chinese:
                system_prompt = f"""你是一个互动剧本的场景导演，负责推进戏剧化的场景发展。

【核心原则】
- 全程使用第二人称"你"指代主角，永远不要使用主角的名字
- 其他角色说话时，通过动作描述来标识说话者，而非使用"角色名："的格式
- 所有提供的context信息仅供你理解和参考，绝对不要直接输出给玩家
- 不要显示任何选择列表或元信息

【正确的对话格式】
✓ 正确：
宋维森冷笑一声。
"你太天真了，这个圈子不是这么玩的。"

✗ 错误：
宋维森："你太天真了，这个圈子不是这么玩的。"

你的职责是：
1. 将玩家的输入转化为充满戏剧张力的场景发展
2. 让每个角色的回应都推进冲突或揭示性格
3. 保持对话的锋芒和潜台词
4. 当玩家的行动明确对应某个预设选择时，在内容末尾添加"CHOICE_SELECTED: [数字]"

当前场景信息：
- 标题：{self.current_scene['title']}
- 描述：{self.current_scene.get('description', '')}
- 章节：{self.current_scene['episode']}
- 场景类型：{self.current_scene.get('type', 'normal')}
- 当前互动次数：{self.scene_interaction_count}
- 情感节拍：{self.current_emotional_beat}/5

剧本背景：
- 标题：{self.screenplay_data['metadata']['title']}
- 类型：{self.screenplay_data['metadata']['genre']}
- 情感核心：{emotional_core}
{choices_context}
{global_context}
{character_profiles}
{key_events_context}

【重要：以上选择列表仅供你理解玩家可能的行动方向，不要向玩家显示这些选项】

互动处理原则：
- 玩家说话 → NPC要有个性化的回应，不能只是信息传递
- 玩家行动 → 要引发角色反应，推进戏剧冲突
- 玩家犹豫 → 通过其他角色施压，制造紧迫感
- 每个回应都要让情况变得更复杂或更清晰

对话处理：玩家正在说话，确保NPC的回应有性格、有目的、有冲突。

重要准则：
- 保持回应简洁有力（最多2-3段）
- 始终使用第二人称"你"
- 让对话推进剧情，不要空转
- 只有当玩家行动明确对应编号选择时才输出CHOICE_SELECTED
- 如果玩家尝试逃避冲突，让其他角色把冲突带回来
- 通过场景暗示选择的存在，而非直接列举
- 群体场景中，让不同角色表达不同立场

场景节奏控制：
- 每2-3轮对话要有一个小的情感转折
- 不要让场景陷入重复循环
- 适时通过外部事件推进（如新角色进入、时间压力等）

绝对禁止：
- 不要输出选择列表
- 不要使用【】或（）等技术标记
- 不要显示"请选择"之类的提示
- 不要在叙述中使用主角名字
- 不要用"角色名："的格式

记住：这是剧本创作，不是游戏设计。创造自然流畅的戏剧体验。"""
            else:
                system_prompt = f"""You are directing a scene in an interactive screenplay, responsible for advancing dramatic scene development.

[CORE PRINCIPLES]
- Always use second person "you" to refer to the protagonist, never use the protagonist's name
- When other characters speak, identify speakers through action descriptions, not "Character:" format
- All provided context information is for your understanding only - NEVER output it directly to the player
- Don't display any choice lists or meta-information

[CORRECT DIALOGUE FORMAT]
✓ Correct:
Song Weisen smirks coldly.
"You're too naive. That's not how this industry works."

✗ Wrong:
Song Weisen: "You're too naive. That's not how this industry works."

Your role is to:
1. Transform player input into dramatically compelling scene progression
2. Make every character response advance conflict or reveal character
3. Maintain sharp dialogue with subtext
4. When player action clearly aligns with a preset choice, add "CHOICE_SELECTED: [number]" at the end

Current Scene Information:
- Title: {self.current_scene['title']}
- Description: {self.current_scene.get('description', '')}
- Episode: {self.current_scene['episode']}
- Scene Type: {self.current_scene.get('type', 'normal')}
- Current Interactions: {self.scene_interaction_count}
- Emotional Beat: {self.current_emotional_beat}/5

Screenplay Context:
- Title: {self.screenplay_data['metadata']['title']}
- Genre: {self.screenplay_data['metadata']['genre']}
- Emotional Core: {emotional_core}
{choices_context}
{global_context}
{character_profiles}
{key_events_context}

[IMPORTANT: The choice list above is only for you to understand possible player action directions, DO NOT display these options to the player]

Interaction Principles:
- Player speaks → NPCs must respond with personality, not just information
- Player acts → Must trigger character reactions that advance conflict
- Player hesitates → Other characters apply pressure, create urgency
- Every response must complicate or clarify the situation

Dialogue Processing: Player is speaking, ensure NPC responses have character, purpose, and conflict

Important Guidelines:
- Keep responses concise and powerful (2-3 paragraphs max)
- Always use second person "you"
- Make dialogue advance plot, don't spin wheels
- Only output CHOICE_SELECTED when player action clearly maps to numbered choice
- If player tries to avoid conflict, have other characters bring it back
- Suggest choices through scene context, not direct listing
- In group scenes, let different characters express different positions

Scene Rhythm Control:
- Every 2-3 dialogue exchanges needs small emotional reversal
- Don't let scenes fall into repetitive loops
- Use external events to push forward (new character enters, time pressure, etc.)

Absolutely Prohibited:
- Don't output choice lists
- Don't use [] or () technical markers
- Don't show "Please choose" type prompts
- Don't use protagonist's name in narration
- Don't use "Character:" format

Remember: This is screenplay writing, not game design. Create a natural, fluid dramatic experience."""

            # Different prompt based on whether this is initial scene or continuation
            if self.scene_interaction_count == 0:
                # Check if we have previous episode context to reference
                has_previous_episode = self.current_episode > 1
                
                # Special handling for ending scenes
                if is_ending:
                    if is_chinese:
                        user_prompt = f"""开始结局场景。这是故事的终章，需要：
1. 立即营造落幕的氛围
2. 使用诗意和隽永的语言
3. 让角色获得某种顿悟或转变
4. 在结尾留下引人深思的钩子（问题、暗示或未解之谜）

基于以下内容创作结局，让它既有戏剧张力又有深远意味：
{content.get('narrative', '场景描述缺失')}"""
                    else:
                        user_prompt = f"""Start the ending scene. This is the story's finale, requiring:
1. Immediately create a curtain-falling atmosphere
2. Use poetic and lasting language
3. Characters achieve epiphany or transformation
4. Leave a thought-provoking hook at the end (question, hint, or mystery)

Based on this content, craft an ending that's both dramatically compelling and meaningfully resonant:
{content.get('narrative', 'Scene description missing')}"""
                elif is_chinese:
                    if has_previous_episode:
                        user_prompt = f"""开始场景。这是第{self.current_episode}集的开始。
                        
上一集的情况：主角经历了重要事件，可以适当引用或暗示，但不要详细回顾。

基于以下内容创作，但要让它充满戏剧张力：
{content.get('narrative', '场景描述缺失')}"""
                    else:
                        user_prompt = f"""开始场景。立即建立戏剧情境，展现角色之间的关系和冲突。如果场景中有其他角色，让他们说话。
                
基于以下内容创作，但要让它充满戏剧张力：
{content.get('narrative', '场景描述缺失')}"""
                else:
                    if has_previous_episode:
                        user_prompt = f"""Start the scene. This is the beginning of Episode {self.current_episode}.
                        
Previous episode context: The protagonist experienced important events, which can be referenced or alluded to, but don't recap in detail.

Based on this content, but make it dramatically compelling:
{content.get('narrative', 'Scene description missing')}"""
                    else:
                        user_prompt = f"""Start the scene. Immediately establish the dramatic situation, showing character relationships and conflict. If there are other characters present, make them speak.

Based on this content, but make it dramatically compelling:
{content.get('narrative', 'Scene description missing')}"""
            else:
                # For ongoing scenes, maintain continuity
                if is_ending:
                    if is_chinese:
                        user_prompt = "继续推进结局场景。记住要留下引人深思的钩子，让最后一句话特别有力量。"
                    else:
                        user_prompt = "Continue the ending scene. Remember to leave a thought-provoking hook, make the last line especially powerful."
                elif is_chinese:
                    user_prompt = "继续场景，保持戏剧张力。"
                else:
                    user_prompt = "Continue the scene, maintaining dramatic tension."
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,  # Low temperature for consistent dramatic beats
                max_tokens=1000,
                stream=True  # Enable streaming
            )
            
            # Collect streamed response
            full_response = ""
            print()  # New line before streaming
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    print(content, end='', flush=True)  # Stream to console
            
            # Update emotional beat counter
            self.current_emotional_beat = (self.current_emotional_beat + 1) % 6
            
            return full_response
            
        except Exception as e:
            # Fallback to original narrative
            content = self.current_scene.get('content', {})
            return content.get('narrative', '场景描述缺失')
    
    def _format_consequences(self, consequences):
        """Format consequences for display in prompts"""
        if not consequences:
            return ""
        
        formatted = []
        for consequence in consequences:
            flag_id = consequence.get('flag_id', '')
            operation = consequence.get('operation', '')
            value = consequence.get('value', '')
            
            # Find flag name
            flag_name = flag_id
            for flag in self.screenplay_data.get('flags', []):
                if flag['id'] == flag_id:
                    flag_name = flag['name']
                    break
            
            if operation == 'add':
                formatted.append(f"{flag_name}+{value}")
            elif operation == 'subtract':
                formatted.append(f"{flag_name}-{value}")
            elif operation == 'set':
                formatted.append(f"{flag_name}={value}")
        
        return ", ".join(formatted)
    
    def _prepare_available_choices(self):
        """Prepare available choices for AI context"""
        available_choices = []
        
        # Get content safely
        content = self.current_scene.get('content', {})
        
        # Load choice details from Neo4j relationships for better metadata
        choice_metadata = {}
        if self.story_id and self.current_scene:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (from:StoryNode {id: $scene_id, story_id: $story_id})-[r:PLAYER_CHOICE]->(to:StoryNode)
                    RETURN to.id as leads_to, r.text as choice_text, r.weight as weight, 
                           r.internal_reasoning as reasoning, r.type as choice_type,
                           r.discovery_hint as discovery_hint
                """, scene_id=self.current_scene['id'], story_id=self.story_id)
                
                for record in result:
                    choice_metadata[record['choice_text']] = {
                        'weight': record['weight'] or 'minor',
                        'internal_reasoning': record['reasoning'] or '',
                        'type': record['choice_type'],
                        'discovery_hint': record['discovery_hint'] or ''
                    }
        
        # Debug output for troubleshooting
        if os.getenv('DEBUG_CHOICES', '').lower() == 'true':
            print(f"\n[DEBUG] Scene {self.current_scene['id']} - {self.current_scene['title']}")
            print(f"[DEBUG] Scene type: {self.current_scene.get('type', 'normal')}")
            print(f"[DEBUG] Content type: {type(content)}")
            print(f"[DEBUG] Has player_choices: {'player_choices' in content}")
            if 'player_choices' in content:
                print(f"[DEBUG] Number of choices: {len(content.get('player_choices', []))}")
                for i, choice in enumerate(content.get('player_choices', [])):
                    print(f"[DEBUG] Choice {i+1}: {choice.get('choice_text', 'No text')}")
            
            # Special check for bottleneck scenes
            if self.current_scene.get('type') == 'bottleneck':
                print(f"[DEBUG] This is a BOTTLENECK scene")
                print(f"[DEBUG] Merge from: {self.current_scene.get('merge_from', [])}")
                print(f"[DEBUG] Scene interaction count: {self.scene_interaction_count}")
        
        # Regular choices
        for i, choice in enumerate(content.get('player_choices', [])):
            if self._check_prerequisites(choice.get('prerequisites', [])):
                # Enhance choice with metadata from Neo4j if available
                choice_text = choice.get('choice_text', '')
                if choice_text in choice_metadata:
                    # Merge Neo4j metadata into choice
                    choice['weight'] = choice_metadata[choice_text].get('weight', choice.get('weight', 'minor'))
                    choice['internal_reasoning'] = choice_metadata[choice_text].get('internal_reasoning', choice.get('internal_reasoning', ''))
                
                available_choices.append((i, choice, False))
        
        # Hidden choices
        for i, choice in enumerate(content.get('hidden_choices', [])):
            if self._check_prerequisites(choice.get('prerequisites', [])):
                # Check if player has discovered it
                if self._check_discovery_hint(choice):
                    # Enhance choice with metadata from Neo4j if available
                    choice_text = choice.get('choice_text', '')
                    if choice_text in choice_metadata and choice_metadata[choice_text]['type'] == 'HIDDEN_CHOICE':
                        choice['weight'] = choice_metadata[choice_text].get('weight', choice.get('weight', 'minor'))
                        choice['internal_reasoning'] = choice_metadata[choice_text].get('internal_reasoning', choice.get('internal_reasoning', ''))
                        choice['discovery_hint'] = choice_metadata[choice_text].get('discovery_hint', choice.get('discovery_hint', ''))
                    
                    available_choices.append((len(content.get('player_choices', [])) + i, choice, True))
        
        self.available_choices = available_choices
    
    def _check_discovery_hint(self, choice: Dict) -> bool:
        """Check if a hidden choice should be revealed"""
        # For now, always reveal hidden choices if prerequisites are met
        # Could be enhanced with more complex discovery logic
        return True
    

    
    def process_input(self, player_input: str) -> Optional[str]:
        """Process player input using natural language understanding"""
        # Always use natural language processing
        return self._process_natural_language(player_input)
    
    def _process_natural_language(self, player_input: str) -> Optional[str]:
        """Use GPT to process natural language input with dramatic focus"""
        try:
            # Add player input to both histories (保留旧格式用于兼容性)
            user_msg = {"role": "user", "content": player_input}
            self.conversation_history.append(user_msg)  # Keep full history for compatibility
            self.episode_conversation_history.append(user_msg)  # Episode history
            
            # 添加到纯剧本内容历史（沉浸式体验）
            self.screenplay_content_history.append(player_input)
            
            # Increment interaction count
            self.scene_interaction_count += 1
            
            # Get culture/language settings
            culture_language = self.screenplay_data['metadata'].get('culture_language', 'en-US')
            is_chinese = culture_language == 'zh-CN'
            
            # Build global context from story_brief and characters
            global_context = ""
            
            # Add story brief context
            if self.screenplay_data.get('story_brief'):
                brief = self.screenplay_data['story_brief']
                if is_chinese:
                    global_context += "\n\n【全局故事背景】\n"
                    if brief.get('world_setting'):
                        global_context += f"\n世界设定：\n{brief['world_setting']}\n"
                    if brief.get('character_relationships'):
                        global_context += f"\n人物关系：\n{brief['character_relationships']}\n"
                    if brief.get('emotional_storyline'):
                        global_context += f"\n情感主线：\n{brief['emotional_storyline']}\n"
                else:
                    global_context += "\n\n[GLOBAL STORY CONTEXT]\n"
                    if brief.get('world_setting'):
                        global_context += f"\nWorld Setting:\n{brief['world_setting']}\n"
                    if brief.get('character_relationships'):
                        global_context += f"\nCharacter Relationships:\n{brief['character_relationships']}\n"
                    if brief.get('emotional_storyline'):
                        global_context += f"\nEmotional Storyline:\n{brief['emotional_storyline']}\n"
            
            # Add relevant character profiles for current scene
            character_context = ""
            if self.screenplay_data.get('characters'):
                # Find characters mentioned in current scene
                scene_text = f"{self.current_scene.get('title', '')} {self.current_scene.get('description', '')} {self.current_scene.get('content', {}).get('narrative', '')}"
                
                relevant_chars = []
                for char in self.screenplay_data['characters']:
                    if char.get('name') and char['name'] in scene_text:
                        relevant_chars.append(char)
                
                if relevant_chars:
                    if is_chinese:
                        character_context += "\n\n【当前场景人物】\n"
                        for char in relevant_chars:
                            character_context += f"\n{char['name']}：\n"
                            # 显示角色类型
                            char_type = char.get('character_type', 'major_npc')
                            type_labels = {
                                'protagonist': '主角',
                                'major_npc': '重要角色',
                                'minor_npc': '配角'
                            }
                            character_context += f"- 角色类型：{type_labels.get(char_type, char_type)}\n"
                            
                            if char.get('inner_conflict'):
                                character_context += f"- 内心冲突：{char['inner_conflict']}\n"
                            if char.get('relationships'):
                                character_context += f"- 人物关系：{char['relationships']}\n"
                            if char.get('biography'):
                                character_context += f"- 人物背景：{char['biography']}\n"
                            if char.get('character_function'):
                                character_context += f"- 角色功能：{char['character_function']}\n"
                    else:
                        character_context += "\n\n[CURRENT SCENE CHARACTERS]\n"
                        for char in relevant_chars:
                            character_context += f"\n{char['name']}:\n"
                            # Display character type
                            char_type = char.get('character_type', 'major_npc')
                            type_labels = {
                                'protagonist': 'Protagonist',
                                'major_npc': 'Major Character',
                                'minor_npc': 'Supporting Character'
                            }
                            character_context += f"- Character Type: {type_labels.get(char_type, char_type)}\n"
                            
                            if char.get('inner_conflict'):
                                character_context += f"- Inner Conflict: {char['inner_conflict']}\n"
                            if char.get('relationships'):
                                character_context += f"- Relationships: {char['relationships']}\n"
                            if char.get('biography'):
                                character_context += f"- Character Background: {char['biography']}\n"
                            if char.get('character_function'):
                                character_context += f"- Character Function: {char['character_function']}\n"
            
            # Build dramatic choices context for the AI
            choices_context = ""
            if self.available_choices:
                choices_context = "\n\n可用的戏剧决定点（含优先级）：\n" if is_chinese else "\n\nAvailable Dramatic Decision Points (with priority):\n"
                for i, (_, choice, _) in enumerate(self.available_choices, 1):
                    # Add priority indicators based on weight
                    if choice.get('weight') == 'major':
                        priority = "[关键转折]" if is_chinese else "[MAJOR TURNING POINT]"
                    elif choice.get('weight') == 'minor':
                        priority = "[情节发展]" if is_chinese else "[PLOT DEVELOPMENT]" 
                    else:
                        priority = "[角色塑造]" if is_chinese else "[CHARACTER MOMENT]"
                    
                    choices_context += f"{i}. {choice['choice_text']} {priority}\n"
                    if choice.get('internal_reasoning'):
                        choices_context += f"   内心动机：{choice['internal_reasoning']}\n" if is_chinese else f"   Inner Motivation: {choice['internal_reasoning']}\n"
                    if choice.get('consequences'):
                        consequences_text = self._format_consequences(choice['consequences'])
                        if consequences_text:
                            choices_context += f"   剧情影响：{consequences_text}\n" if is_chinese else f"   Story Impact: {consequences_text}\n"
            
            # Build key events context
            key_events_context = ""
            content = self.current_scene.get('content', {})
            if content.get('key_events'):
                key_events_context = "\n\n场景核心冲突：\n" if is_chinese else "\n\nCore Scene Conflicts:\n"
                for event in content['key_events']:
                    key_events_context += f"• {event}\n"
            
            # Get emotional core
            concept_analysis = self.screenplay_data.get('concept_analysis', {})
            emotional_core = concept_analysis.get('emotional_core', '')
            
           
            
            # Check if this is dialogue input
            is_dialogue = (player_input.startswith('"') or player_input.startswith('"') or 
                          "说" in player_input or "告诉" in player_input or "问" in player_input or
                          "say" in player_input.lower() or "tell" in player_input.lower() or "ask" in player_input.lower())
            
            if is_chinese:
                system_prompt = f"""你是一个互动剧本的场景导演，负责推进戏剧化的场景发展。

【核心原则 - 用户主导权】
- 全程使用第二人称"你"指代主角，永远不要使用主角的名字
- 其他角色说话时，通过动作描述来标识说话者，而非使用"角色名："的格式
- 所有提供的context信息仅供你理解和参考，绝对不要直接输出给玩家
- 不要显示任何选择列表或元信息
- 【重要】不要替用户做决定！你的职责是描述情境，让用户自己选择如何回应

【正确的对话格式】
✓ 正确：
宋维森冷笑一声。
"你太天真了，这个圈子不是这么玩的。"

✗ 错误：
宋维森："你太天真了，这个圈子不是这么玩的。"

你的职责是：
1. 将玩家的输入转化为充满戏剧张力的场景发展
2. 让每个角色的回应都推进冲突或揭示性格
3. 保持对话的锋芒和潜台词
4. 【新规则】只有当玩家明确表达要执行某个具体行动时，才考虑输出"CHOICE_SELECTED: [数字]"
5. 当玩家输入模糊或探索性时，继续剧情对话，不要擅自做决定

当前场景信息：
- 标题：{self.current_scene['title']}
- 描述：{self.current_scene.get('description', '')}
- 章节：{self.current_scene['episode']}
- 场景类型：{self.current_scene.get('type', 'normal')}
- 当前互动次数：{self.scene_interaction_count}
- 情感节拍：{self.current_emotional_beat}/5

剧本背景：
- 标题：{self.screenplay_data['metadata']['title']}
- 类型：{self.screenplay_data['metadata']['genre']}
- 情感核心：{emotional_core}
{choices_context}
{global_context}
{character_context}
{key_events_context}

【重要：以上选择列表仅供你理解玩家可能的行动方向，不要向玩家显示这些选项，也不要擅自为玩家选择】

【用户主导权原则】
- 玩家说话/询问 → 角色自然回应，继续对话，不要结束场景
- 玩家表达犹豫/思考 → 让其他角色施压或提供信息，但不替玩家做决定
- 玩家输入模糊 → 继续推进对话和情境，让玩家有更多信息来做决定
- 玩家明确表达行动意图 → 才考虑匹配预设选择

【决定识别标准】
只有当玩家输入包含以下明确意图时，才输出CHOICE_SELECTED：
- 明确的行动词：如"我决定..."、"我选择..."、"我要..."
- 具体的执行语句：如"走向..."、"拿起..."、"告诉他..."
- 绝对不要把探索性对话、询问、表达情感等当作决定

互动处理原则：
- 玩家说话 → NPC要有个性化的回应，不能只是信息传递
- 玩家行动 → 要引发角色反应，推进戏剧冲突
- 玩家犹豫 → 通过其他角色施压，制造紧迫感，但让玩家自己决定
- 每个回应都要让情况变得更复杂或更清晰

{"对话处理：玩家正在说话，确保NPC的回应有性格、有目的、有冲突。继续对话，不要急于推进到下个场景。" if is_dialogue else ""}

重要准则：
- 保持回应简洁有力（最多2-3段）
- 始终使用第二人称"你"
- 让对话推进剧情，不要空转
- 【新规则】只有玩家明确表达决定时，才输出CHOICE_SELECTED
- 如果玩家尝试逃避冲突，让其他角色把冲突带回来，但仍让玩家自己选择
- 通过场景暗示选择的存在，但不要替玩家做选择
- 群体场景中，让不同角色表达不同立场，形成压力

场景节奏控制：
- 每2-3轮对话要有一个小的情感转折
- 不要让场景陷入重复循环
- 适时通过外部事件推进（如新角色进入、时间压力等）
- 但始终让玩家保持选择权

绝对禁止：
- 不要输出选择列表
- 不要使用【】或（）等技术标记
- 不要显示"请选择"之类的提示
- 不要在叙述中使用主角名字
- 不要用"角色名："的格式
- 【新增】不要替玩家做决定或假设玩家的想法
- 【新增】不要把模糊输入直接转化为具体选择

记住：你是剧本导演，不是代理人。创造情境让玩家做决定，而不是替玩家做决定。"""
            else:
                system_prompt = f"""You are directing a scene in an interactive screenplay, responsible for advancing dramatic scene development.

[CORE PRINCIPLES - USER AGENCY]
- Always use second person "you" to refer to the protagonist, never use the protagonist's name
- When other characters speak, identify speakers through action descriptions, not "Character:" format
- All provided context information is for your understanding only - NEVER output it directly to the player
- Don't display any choice lists or meta-information
- [IMPORTANT] Don't make decisions for the user! Your job is to describe situations, let users choose how to respond

[CORRECT DIALOGUE FORMAT]
✓ Correct:
Song Weisen smirks coldly.
"You're too naive. That's not how this industry works."

✗ Wrong:
Song Weisen: "You're too naive. That's not how this industry works."

Your role is to:
1. Transform player input into dramatically compelling scene progression
2. Make every character response advance conflict or reveal character
3. Maintain sharp dialogue with subtext
4. [NEW RULE] Only output "CHOICE_SELECTED: [number]" when player clearly expresses intent to take a specific action
5. When player input is ambiguous or exploratory, continue story dialogue without making decisions for them

Current Scene Information:
- Title: {self.current_scene['title']}
- Description: {self.current_scene.get('description', '')}
- Episode: {self.current_scene['episode']}
- Scene Type: {self.current_scene.get('type', 'normal')}
- Current Interactions: {self.scene_interaction_count}
- Emotional Beat: {self.current_emotional_beat}/5

Screenplay Context:
- Title: {self.screenplay_data['metadata']['title']}
- Genre: {self.screenplay_data['metadata']['genre']}
- Emotional Core: {emotional_core}
{choices_context}
{global_context}
{character_context}
{key_events_context}

[IMPORTANT: The choice list above is only for you to understand possible player action directions, DO NOT display these options to players, and DO NOT make choices for them]

[USER AGENCY PRINCIPLES]
- Player speaks/asks → Characters respond naturally, continue dialogue, don't end scene
- Player expresses hesitation/thinking → Other characters apply pressure or provide info, but don't decide for player
- Player input is ambiguous → Continue advancing dialogue and situation, let player get more info to decide
- Player clearly expresses action intent → Only then consider matching preset choices

[DECISION RECOGNITION CRITERIA]
Only output CHOICE_SELECTED when player input contains clear intent like:
- Explicit action words: "I decide...", "I choose...", "I will..."
- Specific execution statements: "Walk toward...", "Pick up...", "Tell him..."
- Never treat exploratory dialogue, questions, or emotional expressions as decisions

Interaction Principles:
- Player speaks → NPCs must respond with personality, not just information
- Player acts → Must trigger character reactions that advance conflict
- Player hesitates → Other characters apply pressure, create urgency, but let player decide
- Every response must complicate or clarify the situation

{"Dialogue Processing: Player is speaking, ensure NPC responses have character, purpose, and conflict. Continue dialogue, don't rush to next scene." if is_dialogue else ""}

Important Guidelines:
- Keep responses concise and powerful (2-3 paragraphs max)
- Always use second person "you"
- Make dialogue advance plot, don't spin wheels
- [NEW RULE] Only output CHOICE_SELECTED when player clearly expresses a decision
- If player tries to avoid conflict, have other characters bring it back, but still let player choose
- Suggest choices through scene context, but don't make choices for player
- In group scenes, let different characters express different positions, create pressure

Scene Rhythm Control:
- Every 2-3 dialogue exchanges needs small emotional reversal
- Don't let scenes fall into repetitive loops
- Use external events to push forward (new character enters, time pressure, etc.)
- But always maintain player agency

Absolutely Prohibited:
- Don't output choice lists
- Don't use [] or () technical markers
- Don't show "Please choose" type prompts
- Don't use protagonist's name in narration
- Don't use "Character:" format
- [NEW] Don't make decisions for players or assume their thoughts
- [NEW] Don't convert ambiguous input directly into specific choices

Remember: You are a screenplay director, not an agent. Create situations for players to decide, don't decide for them."""

            # Simplified message building
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add history with dramatic context
            if self.episode_conversation_history:
                # Check if we have actual dialogue history (not just system messages)
                dialogue_history = [msg for msg in self.episode_conversation_history if msg['role'] in ['user', 'assistant']]
                if dialogue_history:
                    culture_language = self.screenplay_data['metadata'].get('culture_language', 'en-US')
                    
                    # Build dramatic history without technical labels
                    if culture_language == 'zh-CN':
                        history_marker = "=== 当前近期剧情 ==="
                        history_content = history_marker + "\n\n"
                    else:
                        history_marker = "=== Recent Story Development  ==="
                        history_content = history_marker + "\n\n"
                    
                    # Combine dialogue history into a narrative flow
                    for msg in dialogue_history:
                        if msg['role'] == 'user':
                            if culture_language == 'zh-CN':
                                history_content += f"用户输入 → {msg['content']}\n\n"
                            else:
                                history_content += f"User Input → {msg['content']}\n\n"
                        elif msg['role'] == 'assistant':
                            if culture_language == 'zh-CN':
                                history_content += f"剧本片段 → {msg['content']}\n\n"
                            else:
                                history_content += f"Script Segment → {msg['content']}\n\n"
                    
                    messages.append({"role": "system", "content": history_content.strip()})
                
                # Add any system messages (like episode transitions)
                system_messages = [msg for msg in self.episode_conversation_history if msg['role'] == 'system']
                messages.extend(system_messages)
            
            # Debug: Show complete prompt if requested
            if os.getenv('SHOW_PROMPT', '').lower() == 'true':
                print(f"\n🔍 LLM收到的完整prompt - 第 {self.scene_interaction_count} 轮:")
                print(f"总消息数: {len(messages)}")
                print(f"总字符数: {sum(len(msg['content']) for msg in messages)}")
                print(f"\n{'='*80}")
                
                for i, msg in enumerate(messages):
                    role = msg['role']
                    content = msg['content']
                    print(f"\n{i+1}. 【{role.upper()}】")
                    print(content)
                    if i < len(messages) - 1:  # 不是最后一条消息
                        print(f"{'='*80}")
                
                print(f"\n{'='*80}")
                print("发送给LLM...")
                print(f"{'='*80}")
            
            # Get AI response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,  # Low temperature for consistent dramatic beats
                max_tokens=1000,
                stream=True  # Enable streaming
            )
            
            # Collect streamed response
            full_response = ""
            print()  # New line before streaming
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    print(content, end='', flush=True)  # Stream to console
            
            # Update emotional beat
            self.current_emotional_beat = (self.current_emotional_beat + 1) % 6
            
            # Check for choice selection (improved regex to handle edge cases)
            choice_match = re.search(r'CHOICE_SELECTED:\s*(\d+)', full_response)
            selected_choice = None
            if choice_match:
                selected_choice = int(choice_match.group(1))
                # Remove only the choice marker and trailing junk chars, preserve important content
                display_response = re.sub(r'CHOICE_SELECTED:\s*\d+[^\w\s]*\s*', '', full_response).strip()
                # Clean up any double spaces left by removal
                display_response = re.sub(r'\s+', ' ', display_response).strip()
                
                # 获取实际的选择文本并加入历史记录
                if 1 <= selected_choice <= len(self.available_choices):
                    _, choice, _ = self.available_choices[selected_choice - 1]
                    choice_text = choice.get('text', f'Choice {selected_choice}')
                    
                    # 根据语言添加选择信息到显示响应中
                    culture_language = self.screenplay_data['metadata'].get('culture_language', 'en-US')
                    is_chinese = culture_language == 'zh-CN'
                    
                    if is_chinese:
                        display_response += f"\n\n【玩家选择】{choice_text}"
                    else:
                        display_response += f"\n\n[Player chose: {choice_text}]"
            else:
                display_response = full_response
            
            # Add AI response to history (without choice marker)
            assistant_msg = {"role": "assistant", "content": display_response}
            self.conversation_history.append(assistant_msg)  # Keep full history for compatibility
            self.episode_conversation_history.append(assistant_msg)  # Episode history
            
            # 添加到纯剧本内容历史（沉浸式体验）
            self.screenplay_content_history.append(display_response)
            
            # If a choice was selected, process it
            if selected_choice and 1 <= selected_choice <= len(self.available_choices):
                _, choice, _ = self.available_choices[selected_choice - 1]
                
                # Apply consequences
                if 'consequences' in choice:
                    self._apply_consequences(choice['consequences'])
                
                return choice.get('leads_to')
            
            return None
            
        except Exception as e:
            print(f"\n[Error processing input: {e}]")
            return None
    
    def show_ending(self, ending: Dict):
        """Display an ending with enhanced dramatic presentation"""
        culture_language = self.screenplay_data['metadata'].get('culture_language', 'en-US')
        
        print("\n" + "✨"*60)
        print("="*60)
        
        if culture_language == 'zh-CN':
            print("🏁 结局已达成 🏁")
        else:
            print("🏁 ENDING REACHED 🏁")
        
        print("="*60)
        print(f"\n🎭 {ending['ending_type']}")
        print(f"📖 {ending['description']}")
        
        # Check for epilogue variants
        epilogue_variants = ending.get('epilogue_variants', [])
        if epilogue_variants:
            # Find matching epilogue based on current state
            for variant in epilogue_variants:
                if isinstance(variant, dict) and 'conditions' in variant:
                    if self._check_prerequisites(variant.get('conditions', [])):
                        # Found a matching epilogue
                        print("\n" + "~"*60)
                        if culture_language == 'zh-CN':
                            print("【尾声】")
                        else:
                            print("[EPILOGUE]")
                        print("~"*60)
                        print(f"\n{variant.get('narrative', '')}")
                        
                        break
        
        # Add a dramatic pause
        import time
        time.sleep(1)
        
        # Show story reflection
        print("\n" + "─"*60)
        if culture_language == 'zh-CN':
            print("✦ 故事回响 ✦")
            print("─"*60)
            
            # Add a poetic reflection based on ending type
            if "理想" in ending['ending_type'] or "梦想" in ending['ending_type']:
                print("\n「有些梦想，即使破碎，也会在灵魂深处开出花来。」")
            elif "现实" in ending['ending_type'] or "妥协" in ending['ending_type']:
                print("\n「生活教会我们低头，但也教会我们在平凡中寻找光芒。」")
            elif "复仇" in ending['ending_type'] or "背叛" in ending['ending_type']:
                print("\n「当信任的镜子碎裂，每一片都映照着不同的真相。」")
            else:
                print("\n「每一个结局，都是另一个故事的开始。」")
        else:
            print("✦ Story Echoes ✦")
            print("─"*60)
            
            # Add a poetic reflection based on ending type
            if "ideal" in ending['ending_type'].lower() or "dream" in ending['ending_type'].lower():
                print("\n「Some dreams, even when shattered, bloom in the depths of the soul.」")
            elif "reality" in ending['ending_type'].lower() or "compromise" in ending['ending_type'].lower():
                print("\n「Life teaches us to bow, but also to find light in the ordinary.」")
            elif "revenge" in ending['ending_type'].lower() or "betrayal" in ending['ending_type'].lower():
                print("\n「When the mirror of trust shatters, each piece reflects a different truth.」")
            else:
                print("\n「Every ending is the beginning of another story.」")
        
        print("\n" + "─"*60)
        
        if culture_language == 'zh-CN':
            print(f"\n📊 你的旅程：")
            print(f"  访问场景数：{len(set(self.scene_history))}")
            print(f"  做出选择数：{len(self.scene_history) - 1}")
        else:
            print(f"\n📊 Your Journey:")
            print(f"  Scenes visited: {len(set(self.scene_history))}")
            print(f"  Total choices made: {len(self.scene_history) - 1}")
        
        if self.story_flags:
            if culture_language == 'zh-CN':
                print(f"\n🚩 最终状态：")
            else:
                print(f"\n🚩 Final Flags:")
            for flag_id, value in self.story_flags.items():
                flag_info = next((f for f in self.screenplay_data['flags'] if f['id'] == flag_id), None)
                if flag_info:
                    print(f"  {flag_info['name']}: {value}")
        
        print("\n" + "✨"*60)
    
    def close(self):
        """Close Neo4j connection"""
        if hasattr(self, 'driver'):
            self.driver.close()
    
    def save_game(self, filename: str = None):
        """Save current game state"""
        if not filename:
            filename = f"save_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        save_data = {
            'game_file': self.screenplay_data.get('story_id', 'unknown'),
            'current_scene': self.current_scene['id'] if self.current_scene else None,
            'flags': self.story_flags,
            'scene_history': self.scene_history,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        culture_language = self.screenplay_data['metadata'].get('culture_language', 'en-US')
        if culture_language == 'zh-CN':
            print(f"\n💾 游戏已保存到：{filename}")
        else:
            print(f"\n💾 Game saved to: {filename}")
    
    def load_save(self, filename: str):
        """Load a saved game state"""
        with open(filename, 'r', encoding='utf-8') as f:
            save_data = json.load(f)
        
        self.story_flags = save_data['flags']
        self.scene_history = save_data['scene_history']
        
        if save_data['current_scene']:
            self.load_scene(save_data['current_scene'])
        
        print(f"\n💾 Game loaded from: {filename}")
    
    def get_screenplay_content(self) -> str:
        """获取纯剧本内容，不包含任何技术标识"""
        return "\n".join(self.screenplay_content_history)
    
    def save_screenplay_transcript(self, filename: str = None):
        """保存纯剧本内容到文件"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"screenplay_transcript_{timestamp}.txt"
        
        content = self.get_screenplay_content()
        
        # 添加剧本信息头
        culture_language = self.screenplay_data['metadata'].get('culture_language', 'en-US')
        if culture_language == 'zh-CN':
            header = f"""剧本：{self.screenplay_data['metadata']['title']}
类型：{self.screenplay_data['metadata']['genre']}
时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

=====================================

"""
        else:
            header = f"""Screenplay: {self.screenplay_data['metadata']['title']}
Genre: {self.screenplay_data['metadata']['genre']}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

=====================================

"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(header + content)
        
        if culture_language == 'zh-CN':
            print(f"\n📝 剧本内容已保存到：{filename}")
        else:
            print(f"\n📝 Screenplay transcript saved to: {filename}")

def select_game() -> Optional[str]:
    """Let player select a game from Neo4j"""
    # Load environment variables
    load_dotenv()
    
    # Get Neo4j connection
    neo4j_uri = os.getenv('NEO4J_URI')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')
    
    if not neo4j_uri or not neo4j_password:
        print("❌ Neo4j credentials missing. Set NEO4J_URI and NEO4J_PASSWORD in .env file")
        return None
    
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        with driver.session() as session:
            # Get all stories from Neo4j
            result = session.run("""
                MATCH (s:Story)
                OPTIONAL MATCH (scene:StoryNode {story_id: s.id})
                WITH s, count(DISTINCT scene) as scene_count, 
                     max(scene.episode) as max_episode
                RETURN s.id as id, 
                       s.filename as filename, 
                       s.import_time as import_time,
                       scene_count,
                       max_episode
                ORDER BY s.import_time DESC
                LIMIT 10
            """)
            
            stories = []
            for record in result:
                stories.append({
                    'id': record['id'],
                    'filename': record['filename'],
                    'import_time': record['import_time'],
                    'scene_count': record['scene_count'],
                    'episodes': record['max_episode'] or 'Unknown'
                })
            
            if not stories:
                print("❌ No games found in Neo4j database")
                return None
            
            print("\n🎮 Available Games in Neo4j:")
            print("="*80)
            
            for i, story in enumerate(stories, 1):
                print(f"\n{i}. 🌟 {story['filename']}")
                print(f"   🆔 Story ID: {story['id']}")
                print(f"   🎬 Episodes: {story['episodes']}")
                print(f"   🎯 Total Scenes: {story['scene_count']}")
                print(f"   📅 Import Time: {story['import_time']}")
            
            try:
                choice = int(input("\nSelect game number (or 0 to cancel): "))
                if 1 <= choice <= len(stories):
                    return stories[choice - 1]['id']
            except ValueError:
                pass
            
            return None
            
    finally:
        driver.close()

def main():
    """Main screenplay interaction loop"""
    print("🎬 O3 Interactive Screenplay Player - Neo4j Version")
    print("="*60)
    print("Powered by GPT-4.1 for natural dialogue understanding")
    print("Data loaded from Neo4j graph database")
    print("="*60)
    
    # Load environment variables
    load_dotenv()
    
    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("\n❌ OpenAI API key not found!")
        print("Please set OPENAI_API_KEY in your .env file")
        return
    
    # Select screenplay
    story_id = select_game()
    if not story_id:
        return
    
    # Initialize player
    player = O3ScreenplayPlayer()
    player.load_game(story_id)
    
    # Screenplay loop
    print("\n" + "="*60)
    print("🎬 开始互动剧本" if player.screenplay_data['metadata'].get('culture_language', 'en-US') == 'zh-CN' else "🎬 Starting Interactive Screenplay")
    print("="*60)
    
    # Show tips in appropriate language
    culture_language = player.screenplay_data['metadata'].get('culture_language', 'en-US')
    if culture_language == 'zh-CN':
        print("\n提示：")
        print("- 像角色一样说话和行动")
        print("- 输入对话时可以加引号，如：\"我不相信你\"")
        print("- 描述动作时直接输入，如：我走向窗边")
        print("- 剧本会根据你的选择发展出不同的剧情")
        print("- 输入 'save' 保存进度")
        print("- 输入 'transcript' 保存纯剧本内容")
        print("- 输入 'quit' 退出")
    else:
        print("\nTips:")
        print("- Speak and act as your character would")
        print("- For dialogue, you can use quotes: \"I don't believe you\"")
        print("- For actions, just describe: I walk to the window")
        print("- The screenplay will evolve based on your choices")
        print("- Type 'save' to save your progress")
        print("- Type 'transcript' to save screenplay transcript")
        print("- Type 'quit' to exit")
    print("="*60)
    
    player.start_game()
    
    while True:
        try:
            # Get language for prompts
            culture_language = player.screenplay_data['metadata'].get('culture_language', 'en-US')
            
            # More dramatic prompts based on scene interaction count
            if player.scene_interaction_count == 0:
                prompt_text = "\n[场景开始] > " if culture_language == 'zh-CN' else "\n[Scene begins] > "
            elif player.scene_interaction_count < 3:
                prompt_text = "\n你如何回应？> " if culture_language == 'zh-CN' else "\nHow do you respond? > "
            elif player.scene_interaction_count < 6:
                prompt_text = "\n你的决定？> " if culture_language == 'zh-CN' else "\nYour decision? > "
            else:
                prompt_text = "\n[关键时刻] > " if culture_language == 'zh-CN' else "\n[Critical moment] > "
            
            player_input = input(prompt_text).strip()
            
            if player_input.lower() == 'quit':
                save_prompt = "退出前保存吗？(y/n): " if culture_language == 'zh-CN' else "Save before quitting? (y/n): "
                if input(save_prompt).lower() == 'y':
                    player.save_game()
                break
            
            elif player_input.lower() == 'save':
                player.save_game()
                continue
            
            elif player_input.lower() == 'transcript':
                player.save_screenplay_transcript()
                continue
            
            elif player_input.lower() == 'help':
                if culture_language == 'zh-CN':
                    print("\n📚 互动指南：")
                    print("  角色对话示例：")
                    print("  - \"你到底想要什么？\"")
                    print("  - \"我知道你的秘密\"")
                    print("  角色动作示例：")
                    print("  - 我缓缓站起身")
                    print("  - 我怒视着他")
                    print("  命令：")
                    print("  - 'save' - 保存剧本进度")
                    print("  - 'transcript' - 保存纯剧本内容")
                    print("  - 'quit' - 退出")
                else:
                    print("\n📚 Interaction Guide:")
                    print("  Character dialogue examples:")
                    print("  - \"What do you really want?\"")
                    print("  - \"I know your secret\"")
                    print(" Character action examples:")
                    print("  - I slowly stand up")
                    print("  - I glare at him")
                    print(" Commands:")
                    print("  - 'save' - Save screenplay progress")
                    print("  - 'transcript' - Save screenplay transcript")
                    print("  - 'quit' - Exit")
                continue
            
            # Process input
            next_scene_id = player.process_input(player_input)
            
            if next_scene_id:
                # Scene transition
                continue_prompt = "\n[场景转换，按回车键继续...]" if culture_language == 'zh-CN' else "\n[Scene transition, press Enter to continue...]"
                input(continue_prompt)
                player.load_scene(next_scene_id)
            
        except KeyboardInterrupt:
            print("\n\n🎬 感谢参与这个故事！" if culture_language == 'zh-CN' else "\n\n🎬 Thanks for being part of this story!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            continue
    
    # Close Neo4j connection
    player.close()

if __name__ == "__main__":
    main() 