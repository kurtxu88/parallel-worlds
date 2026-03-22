#!/usr/bin/env python3
"""
O3 Game Designer - 分阶段版本
将游戏生成拆分为三个清晰的阶段，每个阶段都有明确的输入输出
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Literal
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI()

# Model configuration
O3_MODEL = "o3-2025-04-16"

# ========== 第一阶段：概念分析 ==========

class ReferenceWork(BaseModel):
    title: str
    media_type: str
    key_mechanics: List[str]
    narrative_style: str

class GameConceptAnalysis(BaseModel):
    """第一阶段输出：游戏概念分析"""
    user_intent: str
    emotional_core: str
    target_audience: str
    reference_works: List[ReferenceWork]
    core_concepts: List[str]
    unique_selling_points: List[str]
    game_mechanics_ideas: List[str]
    narrative_approach: str
    visual_style_suggestion: str

# ========== 第二阶段：故事与人物 ==========

class StoryBrief(BaseModel):
    """详细的故事梗概"""
    world_setting: str = Field(description="故事背景与世界观（300-500字）")
    character_relationships: str = Field(description="角色关系图（400-600字）")
    main_plot: str = Field(description="主线剧情（800-1200字）")
    emotional_storyline: str = Field(description="情感主线（400-600字）")
    theme_depth: str = Field(description="主题深度（300-500字）")
    innovation_highlights: str = Field(description="创新亮点（200-300字）")

class Character(BaseModel):
    """深度人物画像"""
    name: str
    character_type: str = Field(description="角色类型：protagonist(主角)、major_npc(重要NPC)、minor_npc(次要NPC)")
    basic_info: str = Field(description="基本档案（50-80字）")
    biography: str = Field(description="人物小传，包含过去、现在、将来（400-600字）")
    relationships: str = Field(description="人际关系网（200-300字）")
    growth_arc: str = Field(description="成长轨迹（150-250字）")
    character_function: str = Field(description="角色功能（50-100字）")
    inner_conflict: str = Field(description="内在冲突（100-150字）")
    key_dialogue_style: str = Field(description="对话风格（80-120字）")

class StoryAndCharacters(BaseModel):
    """第二阶段输出：故事与人物"""
    title: str
    genre: str
    story_brief: StoryBrief
    characters: List[Character]  # 4-10个角色

# ========== 第三阶段：游戏设计 ==========

class StoryFlag(BaseModel):
    id: str
    name: str
    description: str
    type: Literal["boolean", "counter", "value"]
    default_value: Union[bool, int, str]

class PrerequisiteCondition(BaseModel):
    flag_id: str
    operator: Literal["==", "!=", ">", "<", ">=", "<="]
    value: Union[bool, int, str]

class ChoiceConsequence(BaseModel):
    flag_id: str
    operation: Literal["set", "add", "subtract"]
    value: Union[bool, int, str]

class Choice(BaseModel):
    id: str
    choice_text: str
    internal_reasoning: str
    leads_to: str
    weight: Literal["major", "minor", "flavor"]
    prerequisites: List[PrerequisiteCondition] = Field(default_factory=list)
    consequences: List[ChoiceConsequence] = Field(default_factory=list)
    hidden: bool = False
    discovery_hint: Optional[str] = None



class SceneVariant(BaseModel):
    """场景的条件化叙事变体"""
    conditions: List[PrerequisiteCondition]
    narrative: str
    atmosphere: Optional[str] = None
    priority: int = Field(default=0)

class SceneContent(BaseModel):
    narrative: str
    atmosphere: str
    key_events: List[str]
    player_choices: List[Choice]
    hidden_choices: List[Choice] = Field(default_factory=list)
    variants: List[SceneVariant] = Field(default_factory=list)

class Scene(BaseModel):
    id: str
    episode: int
    type: Literal["normal", "ending", "hub", "emotional"]
    title: str
    description: str
    prerequisites: List[PrerequisiteCondition] = Field(default_factory=list)
    content: SceneContent
    merge_from: List[str] = Field(default_factory=list)

class EpilogueVariant(BaseModel):
    """结局的后续变体"""
    conditions: List[PrerequisiteCondition] = Field(description="触发此变体的条件")
    narrative: str = Field(description="后续故事描述，如'几年后...'")

class Ending(BaseModel):
    scene_id: str
    ending_type: str
    prerequisites: List[PrerequisiteCondition]
    description: str
    epilogue_variants: List[EpilogueVariant] = Field(
        default_factory=list,
        description="基于玩家历程的不同后续变体"
    )

class GameDesign(BaseModel):
    """第三阶段输出：游戏设计"""
    episodes: int
    total_scenes: int
    flags: List[StoryFlag]
    scenes: List[Scene]
    endings: List[Ending]

# ========== 分阶段生成器 ==========

class O3GameDesignerPhased:
    def __init__(self):
        self.client = client
        self.story_id = None
        self.concept_analysis = None
        self.story_and_characters = None
    
    def phase1_analyze_concept(self, seed: str, culture_language: str = "zh-CN") -> Optional[GameConceptAnalysis]:
        """第一阶段：概念分析"""
        print("🔍 第一阶段：概念分析...")
        
        if culture_language == "zh-CN":
            prompt = f"""你是一位专业的剧本创作分析师。请分析用户的创意需求，为互动电影剧本提供概念设计。

用户创意种子：{seed}

## 核心任务：分析如何创作一个精彩的故事

请按以下步骤进行深度分析：

1. **故事核心分析**：
   - 这个创意种子最吸引人的地方是什么？
   - 可以发展成什么样的精彩故事？
   - 主角会面临什么样的核心困境？
   - 观众为什么会关心这个故事？

2. **参考作品研究**（重点）：
   - 找出3-5个相关的优秀影视作品（**必须至少4部是电影/电视剧，最多1个故事游戏**）
   - **重点分析**：
     * 这些作品的故事为什么精彩？
     * 它们是如何抓住观众的？
     * 主角的动机有多强烈？
     * 冲突是如何步步升级的？
     * 最精彩的场景是什么？为什么？
   - 深入分析每个作品的：
     * 叙事结构（如何构建张力、制造冲突、推进剧情）
     * 角色塑造（人物弧线、内心世界、关系动态）
     * 主题表达（如何通过剧情传达深层含义）
     * 情感设计（如何触动观众的情感）
   - 提取可借鉴的叙事模式和互动机制

3. **故事潜力分析**：
   - 这个故事可以有哪些精彩的发展方向？
   - 主角可能面临哪些艰难选择？
   - 有哪些令人意想不到的转折？
   - 结局可以有哪些可能性？

4. **核心要素提炼**：
   - 故事的独特魅力（为什么观众会选择看这个故事？）
   - 情感核心（触动观众的是什么？）
   - 主题深度（故事想要探讨什么？）
   - 目标受众（谁会被这个故事吸引？）

5. **叙事策略**：
   - **叙事框架选择**：
     * 线性vs非线性
     * 单视角vs多视角
     * 时序安排（顺叙、倒叙、插叙）
   - **叙事节奏设计**：
     * 如何控制信息释放速度
     * 悬念与解答的时机
     * 高潮与缓冲的配比
   - **互动叙事特色**：
     * 观众选择如何影响叙事
     * 选择的意义层次（表层vs深层）
     * 分支收束的艺术
   - **情感体验曲线**：
     * 目标情感状态
     * 情感转折点设计
     * 观众共情机制

6. **视觉风格建议**：
   - 整体视觉基调
   - 关键场景的视觉想象
   - 与故事主题的呼应

请以结构化的方式输出你的分析结果。记住：我们在创作一部可以互动的电影，不是游戏。"""
        else:
            prompt = f"""You are a professional screenplay concept analyst. Please analyze the user's creative request and provide concept design for an interactive film script.

User's creative seed: {seed}

## Core Task: Analyze how to create a compelling story

Please conduct in-depth analysis following these steps:

1. **Story Core Analysis**:
   - What's most compelling about this creative seed?
   - What kind of fascinating story can it develop into?
   - What core dilemma will the protagonist face?
   - Why would the audience care about this story?

2. **Reference Works Research** (Critical):
   - Find 3-5 relevant excellent film/TV works (**must include at least 4 movies/TV shows, maximum 1 story game**)
   - **Key Analysis**:
     * Why are these stories compelling?
     * How do they capture the audience?
     * How strong is the protagonist's motivation?
     * How does conflict escalate?
     * What are the most memorable scenes? Why?
   - Deep analyze each work's:
     * Narrative structure (how they build tension, create conflict, advance plot)
     * Character development (character arcs, inner worlds, relationship dynamics)
     * Thematic expression (how they convey deeper meaning through story)
     * Emotional design (how they touch audience emotions)
   - Extract applicable narrative patterns and interaction mechanics

3. **Story Potential Analysis**:
   - What exciting directions could this story take?
   - What difficult choices might the protagonist face?
   - What unexpected twists are possible?
   - What different endings could there be?

4. **Core Elements Extraction**:
   - Story's unique appeal (Why would audiences choose this story?)
   - Emotional core (What touches the audience?)
   - Thematic depth (What does the story explore?)
   - Target audience (Who will be attracted to this story?)

5. **Narrative Strategy**:
   - **Narrative Framework Selection**:
     * Linear vs. non-linear
     * Single perspective vs. multiple perspectives
     * Temporal arrangement (chronological, flashback, parallel)
   - **Narrative Pacing Design**:
     * How to control information release speed
     * Timing of suspense and revelation
     * Balance of climax and relief
   - **Interactive Narrative Features**:
     * How audience agency affects narrative
     * Layers of choice meaning (surface vs. deep)
     * Art of branch convergence
   - **Emotional Experience Curve**:
     * Target emotional states
     * Emotional turning point design
     * Audience empathy mechanisms

6. **Visual Style Suggestions**:
   - Overall visual tone
   - Visual imagination of key scenes
   - Connection with story theme

Please output your analysis in a structured format. Remember: we're creating an interactive film, not a game."""

        try:
            response = self.client.beta.chat.completions.parse(
                model=O3_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format=GameConceptAnalysis,
                max_completion_tokens=15000  # 增加到15000，给更充分的分析空间
            )
            
            self.concept_analysis = response.choices[0].message.parsed
            
            if self.concept_analysis:
                print("✅ 概念分析完成！")
                print(f"📌 用户意图：{self.concept_analysis.user_intent}")
                print(f"💫 情感核心：{self.concept_analysis.emotional_core}")
                print(f"🎯 目标受众：{self.concept_analysis.target_audience}")
                print(f"📚 参考作品：{len(self.concept_analysis.reference_works)} 个")
                print(f"💡 核心概念：{len(self.concept_analysis.core_concepts)} 个")
                
                # 保存第一阶段结果
                self._save_phase_result("phase1_concept", self.concept_analysis.model_dump())
                
                return self.concept_analysis
            
        except Exception as e:
            print(f"❌ 概念分析失败：{e}")
            
        return None
    
    def phase2_create_story(self, gender: str, concept: GameConceptAnalysis, culture_language: str = "zh-CN") -> Optional[StoryAndCharacters]:
        """第二阶段：创作故事与人物"""
        print("\n📖 第二阶段：故事与人物创作...")
        
        gender_zh = "女性" if gender == "female" else "男性"
        
        # 格式化概念分析供参考
        concept_summary = f"""
用户意图：{concept.user_intent}
情感核心：{concept.emotional_core}
目标受众：{concept.target_audience}
核心概念：{', '.join(concept.core_concepts)}
叙事方式：{concept.narrative_approach}

参考作品：
"""
        for ref in concept.reference_works:
            concept_summary += f"- 《{ref.title}》（{ref.media_type}）：{ref.narrative_style}\n"
        
        if culture_language == "zh-CN":
            prompt = f"""你是一位资深的剧本作家。基于以下概念分析，创作一个精彩的互动电影剧本故事。

## 概念分析总结
{concept_summary}

主角性别：{gender_zh}

## 创作任务

### 一、故事梗概创作（story_brief）- 必须达到3000-6000字

你需要创作一个极其详细的故事梗概，包含以下所有部分：

1. **world_setting（故事背景与世界观）300-500字**：
   - 具体的时间、地点、社会环境
   - 这个世界的规则、文化、氛围
   - 与现实世界的差异点（如果有）
   - 主要场景的详细描述（公司、家、城市等）
   - 时代背景对人物的影响
   - 社会阶层、经济状况、文化特征

2. **character_relationships（角色关系图）400-600字**：
   - 详细描述所有主要角色之间的关系网络
   - 包括：血缘关系、职场关系、情感关系、利益关系
   - 关系的历史背景和形成过程
   - 关系的动态变化轨迹
   - 潜在的冲突点和合作点
   - 关系如何推动剧情发展
   - 秘密、误解、背叛等关系要素

3. **main_plot（主线剧情）800-1200字**：
   - 完整的故事梗概，从开端到结局
   - 起承转合的详细描述
   - 主要情节点和转折
   - 核心冲突的发展过程
   - 各个关键场景的概述
   - 不同选择路径的主要差异
   - 伏笔的设置和回收
   - 高潮场景的详细构想

4. **emotional_storyline（情感主线）400-600字**：
   - 主角的情感变化曲线
   - 从故事开始到结束的心理历程
   - 主要人物关系的情感发展
   - 关键情感爆发点
   - 内心冲突与外部冲突的呼应
   - 情感转折的触发事件
   - 最终的情感归宿和成长

5. **theme_depth（主题深度）300-500字**：
   - 故事要探讨的核心问题
   - 不同角度的主题呈现
   - 通过剧情如何深化主题
   - 主题的现实意义和普世价值
   - 与当代社会的关联
   - 留给观众的思考空间
   - 主题如何通过人物选择体现

6. **innovation_highlights（创新亮点）200-300字**：
   - 与同类故事的差异化
   - 独特的叙事手法
   - 创新的互动机制
   - 令人惊喜的设计元素
   - 视觉或情感上的创新点

### 二、深度人物画像（characters）- 4-10个角色，每个1000-1500字

创造一组立体丰满的角色，每个角色都必须包含以下所有信息：

**必须包含的角色类型**：
- 1个主角（深度刻画）：character_type = "protagonist"
- 1个主要对立角色（不是纯粹反派）：character_type = "major_npc"
- 1个导师/引导者角色：character_type = "major_npc"
- 2-3个重要配角（推动剧情）：character_type = "major_npc"
- 1-2个功能性角色（营造氛围）：character_type = "minor_npc"

**每个角色必须包含**：

1. **name**：符合背景设定的名字

2. **character_type**：
   - "protagonist"（主角）：故事的核心人物，承载主要的情感弧线和选择
   - "major_npc"（重要NPC）：推动剧情发展、与主角有深度关系的关键角色
   - "minor_npc"（次要NPC）：功能性角色，用于营造氛围或提供特定信息

3. **basic_info（基本档案）50-80字**：
   - 年龄、性别、职业
   - 外貌特征（身高、体型、穿衣风格）
   - 性格标签（3-5个形容词）
   - 第一印象

4. **biography（人物小传，包含过去、现在、将来）400-600字**：
   
   **过去部分（150-200字）**：
   - 详细的童年经历和原生家庭的影响
   - 求学时期的重要事件
   - 早期职业经历
   - 过去的重要关系（初恋、导师、朋友）
   - 曾经的理想和挫折
   - 形成现在世界观的关键时刻
   
   **现在部分（150-200字）**：
   - 目前的生活状态（居住地、工作、日常作息）
   - 社交圈子和兴趣爱好
   - 内心的焦虑和欲望
   - 当前面临的困境
   - 对其他角色的看法
   - 日常的行为模式
   
   **将来部分（100-150字）**：
   - 在不同故事路径中的不同结局
   - 最好的可能性vs最坏的可能性
   - 成长和改变的轨迹
   - 与其他角色关系的最终状态
   - 主题在这个角色身上的体现

5. **relationships（人际关系网）200-300字**：
   - 与每个其他主要角色的具体关系
   - 关系的历史和现状
   - 潜在的冲突和合作
   - 关系在故事中如何变化
   - 这些关系如何影响他们的选择

6. **growth_arc（成长轨迹）150-250字**：
   - 故事开始时的状态
   - 遭遇的挑战和考验
   - 关键的成长时刻
   - 内在的改变过程
   - 最终的蜕变或毁灭

7. **character_function（角色功能）50-100字**：
   - 在故事结构中的作用
   - 如何推动剧情
   - 象征意义
   - 与主题的关系

8. **inner_conflict（内在冲突）100-150字**：
   - 欲望vs恐惧
   - 理想vs现实
   - 责任vs自由
   - 具体的内心挣扎场景

9. **key_dialogue_style（对话风格）80-120字**：
    - 说话方式（直接/委婉/幽默/严肃）
    - 常用词汇和句式
    - 口头禅或标志性表达
    - 语言如何反映性格
    - 不同情境下的语言变化

## 创作原则

1. **故事优先**：先构思一个精彩的故事，再考虑互动元素
2. **情感真实**：每个角色都要有真实的情感和动机
3. **冲突驱动**：用角色之间的冲突推动剧情
4. **主题统一**：所有元素都要服务于核心主题
5. **细节丰富**：通过细节让世界和人物活起来

记住：你在创作一部电影剧本，不是游戏剧情。每个场景都应该有画面感，每个角色都应该立体可信。"""
        else:
            prompt = f"""You are an experienced screenplay writer. Based on the following concept analysis, create a compelling interactive film script story.

## Concept Analysis Summary
{concept_summary}

Protagonist Gender: {gender}

## Creative Tasks

### I. Story Synopsis Creation (story_brief) - Must reach 3000-6000 words total

Create an extremely detailed story synopsis including all the following parts:

1. **world_setting (Story Background & World) 300-500 words**:
   - Specific time, place, and social environment
   - Rules, culture, and atmosphere of this world
   - Differences from the real world (if any)
   - Detailed descriptions of main locations
   - How the era affects the characters
   - Social hierarchy, economic conditions, cultural features

2. **character_relationships (Character Relationship Map) 400-600 words**:
   - Detailed description of relationship networks between all major characters
   - Including: blood relations, workplace relations, emotional relations, interest relations
   - Historical background and formation of relationships
   - Dynamic trajectories of relationships
   - Potential conflict and cooperation points
   - How relationships drive the plot
   - Secrets, misunderstandings, betrayals

3. **main_plot (Main Storyline) 800-1200 words**:
   - Complete story synopsis from beginning to end
   - Detailed description of story structure
   - Major plot points and turning points
   - Development process of core conflicts
   - Overview of key scenes
   - Main differences between different choice paths
   - Setup and payoff of foreshadowing
   - Detailed conception of climax scenes

4. **emotional_storyline (Emotional Storyline) 400-600 words**:
   - Protagonist's emotional change curve
   - Psychological journey from beginning to end
   - Emotional development of major relationships
   - Key emotional explosion points
   - Echoes between inner and external conflicts
   - Triggering events for emotional turns
   - Final emotional destination and growth

5. **theme_depth (Theme Depth) 300-500 words**:
   - Core questions the story explores
   - Theme presentation from different angles
   - How the plot deepens the theme
   - Real-world significance and universal values
   - Connection with contemporary society
   - Space for audience reflection
   - How theme manifests through character choices

6. **innovation_highlights (Innovation Highlights) 200-300 words**:
   - Differentiation from similar stories
   - Unique narrative techniques
   - Innovative interaction mechanisms
   - Surprising design elements
   - Visual or emotional innovations

### II. Deep Character Portraits (characters) - 4-10 characters, 1000-1500 words each

Create a group of three-dimensional characters. Each character must include all the following information:

**Required Character Types**:
- 1 protagonist (deeply portrayed): character_type = "protagonist"
- 1 main opposing character (not pure villain): character_type = "major_npc"
- 1 mentor/guide character: character_type = "major_npc"
- 2-3 important supporting characters: character_type = "major_npc"
- 1-2 functional characters: character_type = "minor_npc"

**Each Character Must Include**:

1. **name**: Name fitting the background setting

2. **character_type**:
   - "protagonist": Core character of the story, carrying main emotional arc and choices
   - "major_npc": Key character who drives plot development and has deep relationships with protagonist
   - "minor_npc": Functional character for atmosphere or specific information

3. **basic_info (Basic Profile) 50-80 words**:
   - Age, gender, occupation
   - Physical features
   - Personality tags
   - First impression

4. **biography (Character Biography, including past, present, future) 400-600 words**:
   
   **Past section (150-200 words)**:
   - Detailed childhood experiences and family influences
   - Important events during education
   - Early career experiences
   - Important past relationships (first love, mentors, friends)
   - Past ideals and setbacks
   - Key moments that shaped current worldview
   
   **Present section (150-200 words)**:
   - Current living situation (residence, work, daily routine)
   - Social circles and hobbies
   - Inner anxieties and desires
   - Current difficulties faced
   - Views on other characters
   - Daily behavioral patterns
   
   **Future section (100-150 words)**:
   - Different endings in different story paths
   - Best possibilities vs worst possibilities
   - Growth and change trajectory
   - Final state of relationships with other characters
   - How theme manifests through this character

5. **relationships (Character Relationship Network) 200-300 words**:
   - Specific relationships with each other major character
   - History and current status of relationships
   - Potential conflicts and cooperation
   - How relationships change in the story
   - How these relationships influence their choices

6. **growth_arc (Character Growth Arc) 150-250 words**:
   - State at the beginning of the story
   - Challenges and trials encountered
   - Key growth moments
   - Internal change process
   - Final transformation or destruction

7. **character_function (Character Function) 50-100 words**:
   - Role in story structure
   - How they drive the plot
   - Symbolic meaning
   - Relationship to theme

8. **inner_conflict (Inner Conflict) 100-150 words**:
   - Desire vs fear
   - Ideal vs reality
   - Responsibility vs freedom
   - Specific internal struggle scenarios

9. **key_dialogue_style (Dialogue Style) 80-120 words**:

## Creative Principles

1. **Story First**: Create a compelling story before considering interactive elements
2. **Emotional Truth**: Every character must have real emotions and motivations
3. **Conflict-Driven**: Use character conflicts to drive the plot
4. **Thematic Unity**: All elements must serve the core theme
5. **Rich Details**: Bring the world and characters to life through details

Remember: You're creating a film script, not a game plot. Every scene should be cinematic, every character should be believable."""

        try:
            response = self.client.beta.chat.completions.parse(
                model=O3_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format=StoryAndCharacters,
                max_completion_tokens=40000  # 增加到40000，确保能完整生成所有角色
            )
            
            self.story_and_characters = response.choices[0].message.parsed
            
            if self.story_and_characters:
                print("✅ 故事创作完成！")
                print(f"📕 标题：{self.story_and_characters.title}")
                print(f"🎭 类型：{self.story_and_characters.genre}")
                print(f"👥 角色：{len(self.story_and_characters.characters)} 个")
                
                # 计算故事梗概字数
                brief = self.story_and_characters.story_brief
                total_words = sum([
                    len(brief.world_setting),
                    len(brief.character_relationships),
                    len(brief.main_plot),
                    len(brief.emotional_storyline),
                    len(brief.theme_depth),
                    len(brief.innovation_highlights)
                ])
                print(f"📝 故事梗概：约 {total_words} 字")
                
                # 保存第二阶段结果
                self._save_phase_result("phase2_story", self.story_and_characters.model_dump())
                
                return self.story_and_characters
            
        except Exception as e:
            print(f"❌ 故事创作失败：{e}")
            
        return None
    
    def phase3_design_game(self, story: StoryAndCharacters, concept: GameConceptAnalysis, culture_language: str = "zh-CN") -> Optional[GameDesign]:
        """第三阶段：游戏设计"""
        print("\n🎮 第三阶段：互动剧本场景设计...")
        
        # 准备故事摘要
        story_summary = f"""
标题：{story.title}
类型：{story.genre}
主线剧情：{story.story_brief.main_plot}
主要角色：{', '.join([c.name for c in story.characters])}
"""
        
        if culture_language == "zh-CN":
            prompt = f"""你是一位资深的互动剧本设计师。基于以下故事，创作具体的剧本场景。

## 故事摘要
{story_summary}

## 创作任务：设计25-30个剧本场景

### 一、架构要求（Hub-Spoke 模式）

1. **整体结构**：
   - 第1-2集：共享主线，建立世界观和人物
   - 第3或4集：设置1个Hub场景（关键选择点）
   - Hub之后：A/B/C三条独立路线
   - **第4-5集**：路线发展期，每条路线6-8个场景
   - **第6集**：结局前的高潮铺垫（2-3个场景）+ 结局
   - **重要**：在每条路线中插入2-3个情感递进场景

2. **Hub场景设计**：
   - 必须是故事的重大转折点
   - 选择要体现价值观冲突
   - 每个选择都要合理且吸引人
   - 通过设置ending_route标志锁定路线
   - **关键要求**：Hub的3个选择必须指向3个不同的场景作为各路线起点
     - 第一个选择 → S[x] (A路线起点)
     - 第二个选择 → S[y] (B路线起点) 
     - 第三个选择 → S[z] (C路线起点)
   - Hub可以在第3集或第4集，根据故事节奏决定

3. **第4-6集节奏设计（重要）**：
   - **第4集**：
     * 如果Hub在第3集：路线确立后的"新常态"
     * 如果Hub在第4集：前半集铺垫冲突，后半集做出选择
     * 展现选择后的直接后果
     * 建立新的人物关系动态
   
   - **第5集**：路线深化期
     * 外部压力逐步增大
     * 内心矛盾不断激化
     * 关键人物关系面临多重考验
     * 铺设本路线的终极冲突
   
   - **第6集前半段**：最后的试炼
     * **"静-动"对照场景**：在激烈冲突前先有一个安静的情感积累
     * 示例：
       - A线：彩排前的独处时刻→彩排中的意外危机
       - B线：拍摄间隙的内心独白→镜头前的精神崩溃
       - C线：首映前的私密对话→观众反应的残酷真相
     * 这种对比让情感落差更强烈
   
   - **第6集后半段**：高潮与结局
     * 所有矛盾爆发的最高点
     * 做出最终的重大选择
     * 情感的最终归宿

4. **标志驱动的情感系统**：
   - 使用Flag系统记录玩家的选择和情感状态
   - 关键场景通过改变Flag值来影响后续剧情
   - 标志可以是：关系状态、心理状态、成就解锁、知晓秘密等
   - **标志的丰富应用**：
     * 影响角色对话的态度和内容
     * 解锁隐藏选项或特殊场景变体
     * 决定结局的多样性和epilogue_variants的触发

5. **情感递进场景设计**：
   - 在关键剧情点之间插入专门的情感场景
   - **特别是第5集中段和第6集初**，需要情感缓冲和积累
   - 这些场景重点不在推进剧情，而在深化情感
   - 设计方向：
     * 给角色们二人空间来处理情感
     * 通过环境和氛围烘托内心状态
     * 让未说出口的话产生张力
     * 在平凡时刻展现深刻情感
     * 浪漫的表白或者暗示，或者一些肢体接触
   - 让玩家有时间消化选择的影响，建立更深的共情

### 二、场景创作要求

**每个场景必须包含**：

1. **基本信息**：
   - id: 使用S1, S2, S3...格式（严格按顺序编号）
   - episode: 所属集数（1-6）
   - type: normal/hub/ending/emotional
   - title: 场景标题（吸引人）
   - description: 场景的戏剧前提或情感目标（50-100字）

2. **场景内容（content）**：
   - **narrative（200-500字）**：
     * 开场3句话内建立张力或情感基调
     * 使用第二人称叙事
     * 包含视觉、听觉、情感细节
     * 有完整的微型故事结构
     * 暗含伏笔或呼应
     * **第5-6集的场景要特别注重情感密度**
   
   - **atmosphere**：场景的情感氛围
   
   - **key_events**：3-5个关键事件
     * 不只是动作，包括情感转折
     * 推进剧情或深化人物
   
   - **player_choices**：玩家选择
     * choice_text: 表面的行动选择
     * internal_reasoning: 揭示深层含义、价值冲突、长远影响
     * **leads_to: 必须指向实际存在的场景ID（如S1, S2, S3...，绝不使用ENDGAME、END_SCENE等虚拟ID）**
     * consequences: 对标志的影响

**关键要求**：
- **所有leads_to必须使用实际场景ID**：如S1、S2、S20等，不能使用虚拟ID
- **结局场景也使用Sx格式**：最后的结局场景可以是S20、S25等，但必须是实际定义的场景
- **场景ID连续性**：从S1开始连续编号，不跳号

### 三、剧本质量要求

1. **戏剧冲突**：
   - 每个场景都要有明确的冲突（外在或内在）
   - 人物vs人物、人物vs自我、人物vs环境
   - 冲突要推进故事或深化角色
   - **第5-6集的冲突要呈递进式升级**

2. **角色互动**：
   - 至少30%的场景有3人以上互动
   - 通过对话展现性格
   - 关系在互动中发生变化
   - **情感场景重点刻画二人深度对话或独白**

3. **情感真实**：
   - 角色反应符合其性格设定
   - 情感转折要有铺垫
   - 避免功能性NPC式对话
   - **让每个角色都有自己的情感弧线**
   - **第5-6集要让情感达到饱和状态**

4. **场景转换**：
   - 使用时间/空间/情绪过渡
   - 承接前序选择的影响
   - 自然流畅，像电影剪辑
   - **情感递进场景后要有"余韵"**

5. **电影式共情技巧**：
   - 使用特写镜头般的细节描写
   - 环境氛围烘托内心状态
   - 通过小动作展现大情感
   - 留白让玩家自行体会
   - **"静-动"对照增强情感冲击力**

### 四、标志系统设计

**必须包含的核心标志**：
- **ending_route**: 枚举类型(A/B/C)，在Hub场景设置，决定结局路线

**建议包含的通用标志**（可根据故事调整）：
- **intimacy**: 数值0-100，亲密度影响
- **fame**: 数值0-100，知名度影响
- **trust**: 数值0-100，信任度影响  
- **scandal**: 数值0-100，争议度影响
- **pressure**: 数值0-100，压力值（第5-6集重要）

**自由创建的故事专属标志**：
- 根据你的故事需要，自由创建其他标志
- 例如：
  * 关系类：relationship_[角色名] (追踪与特定角色的关系值)
  * 情感类：emotional_state (主角的情感状态)
  * 认知类：knows_[秘密名] (是否知晓某个秘密)
  * 成就类：achievement_[成就名] (是否达成某个成就)
- 标志应该服务于故事，而不是机械地套用模板

### 五、结局设计（重要）

**结局场景必须包含**：
1. **主线结局**：根据ending_route(A/B/C)展现不同的故事结局
2. **结局场景ID格式**：使用标准的Sx格式（如S20、S25等），不使用虚拟ID
3. **epilogue_variants（后续变体）**：
   - 基于玩家的整体历程（关系值、成就标志、情感状态等）
   - 展现不同的"几年后"或"后续发展"
   - 思路：
     * 根据多个标志的组合展现不同的人生轨迹
     * 体现内在价值（如信任、关系）与外在成就的对比
     * 让之前的选择和Flag变化在结局中产生意想不到的影响
   - 让玩家感受到：每个小选择都在塑造最终的人生图景

**Flag系统与结局的关联**：
- 关键Flag可以在结局中产生深远影响
- 让早期的选择通过Flag累积在结局中展现意想不到的影响
- 通过epilogue_variants体现Flag组合的长期效果

### 六、自检要求

生成完成后，确保：
✓ 有且仅有1个type="hub"的场景
✓ Hub场景在第3或4集
✓ Hub场景设置了ending_route
✓ **Hub场景的3个选择指向3个不同的场景（不能都指向同一个场景）**
✓ 每条路线在第4-5集有适量场景（共6-8个）
✓ 第6集有2-3个高潮铺垫场景+结局
✓ 每条路线有2-3个情感递进场景
✓ 第6集前半段有"静-动"对照设计
✓ Flag系统设计合理，能够记录玩家选择的累积效果
✓ 每个结局都有2-3个epilogue_variants
✓ 关键Flag在结局中产生有意义的影响
✓ 所有场景都有完整叙事
✓ 场景之间转换自然
✓ **所有选择的leads_to都指向实际存在的场景ID**
✓ 第5-6集的情感密度和剧情张力明显提升
✓ 整体有"通关爽感"也有"电影式共情"

记住：你在写剧本，不是设计游戏。每个场景都应该像电影场景一样精彩，每个情感时刻都应该让观众心动，每个结局都应该让人回味无穷。特别是第5-6集，要让观众感受到故事正在走向不可避免的高潮，而不是匆忙收尾。"""
        else:
            prompt = f"""You are an experienced interactive screenplay designer. Based on the following story, create specific screenplay scenes.

## Story Summary
{story_summary}

## Creative Task: Design 25-30 Screenplay Scenes

### I. Architecture Requirements (Hub-Spoke Pattern)

1. **Overall Structure**:
   - Episodes 1-2: Shared mainline, establish world and characters
   - Episode 3 or 4: Set 1 Hub scene (key choice point)
   - After Hub: A/B/C three independent routes
   - **Episodes 4-5**: Route development period, 6-8 scenes per route
   - **Episode 6**: High climax prelude (2-3 scenes) + ending
   - **Important**: Insert 2-3 emotional progression scenes in each route

2. **Hub Scene Design**:
   - Must be a major turning point in the story
   - Choices should reflect value conflicts
   - Each choice must be reasonable and compelling
   - Lock route by setting ending_route flag
   - **Key Requirement**: Hub's 3 choices must point to 3 different scenes as starting points for each route
     - First choice → S[x] (A route starting point)
     - Second choice → S[y] (B route starting point)
     - Third choice → S[z] (C route starting point)
   - Hub can be in episode 3 or 4, depending on story rhythm

3. **Episode 4-6 Rhythm Design (Important)**:
   - **Episode 4**:
     * If Hub is in episode 3: "New normal" after route establishment
     * If Hub is in episode 4: First half builds conflict, second half makes choice
     * Show direct consequences of choice
     * Establish new character relationship dynamics
   
   - **Episode 5**: Route deepening period
     * External pressure gradually increases
     * Inner conflicts continuously intensify
     * Key character relationships face multiple tests
     * Lay the ultimate conflict of this route
   
   - **Episode 6 first half**: Final trial
     * **"Static-Dynamic" contrast scene**: A quiet emotional buildup before a fierce conflict
     * Examples:
       - A route: Alone time before rehearsal → Unexpected crisis during rehearsal
       - B route: Inner monologue during shooting break → Mental breakdown on camera
       - C route: Private conversation before premiere → Cruel truth of audience reaction
     * This contrast creates a stronger emotional drop
   
   - **Episode 6 second half**: Climax and ending
     * All conflicts reach their peak
     * Make the final major choice
     * Final emotional destination

4. **Flag-Driven Emotional System**:
   - Use Flag system to record player choices and emotional states
   - Key scenes influence subsequent plot through changing Flag values
   - Flags can be: relationship status, psychological state, achievements unlocked, secrets known, etc.
   - **Rich Flag Applications**:
     * Influence character dialogue attitudes and content
     * Unlock hidden options or special scene variants
     * Determine ending diversity and epilogue_variants triggers

5. **Emotional Progression Scene Design**:
   - Insert dedicated emotional scenes between key plot points
   - **Especially mid-Episode 5 and early Episode 6**, emotional buffer and buildup are needed
   - These scenes focus on deepening emotions, not advancing plot
   - Design directions:
     * Give characters two-person space to process emotions
     * Use environment and atmosphere to enhance inner states
     * Let unspoken words create tension
     * Show profound emotions in ordinary moments
     * Romantic confessions or hints, or physical contact
   - Give players time to digest the impact of their choices and build deeper empathy

### II. Scene Creation Requirements

**Each Scene Must Include**:

1. **Basic Information**:
   - id: Use S1, S2, S3... format (strictly sequential numbering)
   - episode: Episode number (1-6)
   - type: normal/hub/ending/emotional
   - title: Scene title (compelling)
   - description: Scene's dramatic premise or emotional goal (50-100 words)

2. **Scene Content**:
   - **narrative (200-500 words)**:
     * Establish tension or emotional tone within first 3 sentences
     * Use second-person narration
     * Include visual, auditory, emotional details
     * Complete micro-story structure
     * Hidden foreshadowing or callbacks
     * **Scenes in Episodes 5-6 must pay special attention to emotional density**
   
   - **atmosphere**: Scene's emotional atmosphere
   
   - **key_events**: 3-5 key events
     * Not just actions, include emotional turns
     * Advance plot or deepen characters
   
   - **player_choices**: Player choices
     * choice_text: Surface action choice
     * internal_reasoning: Reveal deeper meaning, value conflicts, long-term implications
     * **leads_to: Must point to actual existing scene IDs (like S1, S2, S3..., never use virtual IDs like ENDGAME, END_SCENE)**
     * consequences: Effects on flags

**Key Requirements**:
- **All leads_to must use actual scene IDs**: Like S1, S2, S20 etc., never use virtual IDs
- **Ending scenes also use Sx format**: Final ending scenes can be S20, S25 etc., but must be actually defined scenes
- **Scene ID continuity**: Sequential numbering from S1, no gaps

### III. Screenplay Quality Requirements

1. **Dramatic Conflict**:
   - Every scene must have clear conflict (external or internal)
   - Character vs character, character vs self, character vs environment
   - Conflict must advance story or deepen characters
   - **Conflicts in Episodes 5-6 must be progressively escalating**

2. **Character Interaction**:
   - At least 30% of scenes have 3+ character interactions
   - Reveal personality through dialogue
   - Relationships change through interaction
   - **Emotional scenes focus on deep dialogue or monologue between two characters**

3. **Emotional Truth**:
   - Character reactions match their personality
   - Emotional turns must be set up
   - Avoid functional NPC-style dialogue
   - **Let each character have their own emotional arc**
   - **Emotions in Episodes 5-6 should reach saturation**

4. **Scene Transitions**:
   - Use time/space/emotional transitions
   - Follow from previous choices
   - Natural flow, like film editing
   - **Emotional progression scenes must have "afterglow"**

5. **Cinematic Empathy Techniques**:
   - Use detail-rich descriptions like close-ups
   - Environment atmosphere conveys inner state
   - Show big emotions through small actions
   - Leave room for players to experience on their own
   - **"Static-Dynamic" contrast enhances emotional impact**

### IV. Flag System Design

**Required Core Flags**:
- **ending_route**: Enum type (A/B/C), set at Hub scene, determines ending route

**Suggested Common Flags** (adjust based on story):
- **intimacy**: Value 0-100, intimacy impact
- **fame**: Value 0-100, popularity impact
- **trust**: Value 0-100, trust level impact
- **scandal**: Value 0-100, controversy impact
- **pressure**: Value 0-100, pressure value (important in Episodes 5-6)

**Story-Specific Flags** (create freely):
- Create other flags based on your story needs
- Examples:
  * Relationship: relationship_[character_name] (track relationship with specific characters)
  * Emotional: emotional_state (protagonist's emotional state)
  * Knowledge: knows_[secret_name] (whether a secret is known)
  * Achievement: achievement_[achievement_name] (whether an achievement is unlocked)
- Flags should serve the story, not mechanically follow templates

### V. Ending Design (Important)

**Ending scenes must include**:
1. **Main ending**: Different story endings based on ending_route (A/B/C)
2. **Ending scene ID format**: Use standard Sx format (like S20, S25 etc.), not virtual IDs
3. **epilogue_variants (follow-up variants)**:
   - Based on player's overall journey (relationship values, achievement flags, emotional states, etc.)
   - Show different "years later" or "subsequent developments"
   - Approach:
     * Show different life trajectories based on multiple flag combinations
     * Contrast inner values (trust, relationships) with external achievements
     * Let earlier choices and Flag changes have unexpected impacts in the ending
   - Let players feel: every small choice shapes the final life picture

**Flag System-Ending Connection**:
- Key Flags can have profound impacts in the ending
- Let early choices through Flag accumulation show unexpected impacts in the ending
- Reflect long-term effects of Flag combinations through epilogue_variants

### VI. Self-Check Requirements

After generation, ensure:
✓ Exactly 1 scene with type="hub"
✓ Hub scene is in episode 3 or 4
✓ Hub scene sets ending_route
✓ **Hub scene's 3 choices point to 3 different scenes (cannot all point to the same scene)**
✓ Each route has reasonable scenes in Episodes 4-5 (total 6-8)
✓ Episode 6 has 2-3 high climax prelude scenes + ending
✓ Each route has 2-3 emotional progression scenes
✓ Episode 6 first half has "Static-Dynamic" contrast design
✓ Flag system designed reasonably, capable of recording cumulative effects of player choices
✓ Each ending has 2-3 epilogue_variants
✓ Key Flags have meaningful impacts in the endings
✓ All scenes have complete narrative
✓ Natural transitions between scenes
✓ **All choice leads_to point to actually existing scene IDs**
✓ Emotional density and plot tension in Episodes 5-6 significantly improved
✓ Overall has "game-finishing satisfaction" and "cinematic empathy"

Remember: You're writing a screenplay, not designing a game. Every scene should be as compelling as a film scene, every emotional moment should move the audience, and every ending should be memorable. Especially Episodes 5-6, make the audience feel that the story is heading towards an inevitable climax, not a rushed ending."""
        
        try:
            response = self.client.beta.chat.completions.parse(
                model=O3_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format=GameDesign,
                max_completion_tokens=100000  # 保持100000，这是最新的改动
            )
            
            game_design = response.choices[0].message.parsed
            
            if game_design:
                print("✅ 游戏设计完成！")
                print(f"📊 统计：")
                print(f"   章节数：{game_design.episodes}")
                print(f"   场景数：{len(game_design.scenes)} / {game_design.total_scenes}")
                print(f"   标志数：{len(game_design.flags)}")
                print(f"   结局数：{len(game_design.endings)}")
                
                # 验证Hub场景
                hub_scenes = [s for s in game_design.scenes if s.type == "hub"]
                print(f"   Hub场景：{len(hub_scenes)} 个")
                
                # 保存第三阶段结果
                self._save_phase_result("phase3_design", game_design.model_dump())
                
                return game_design
            
        except Exception as e:
            print(f"❌ 游戏设计失败：{e}")
            
        return None
    
    def _validate_game_design(self, design: GameDesign) -> List[str]:
        """验证游戏设计，返回错误列表"""
        errors = []
        
        # 1. 检查非结局场景是否有选择
        for scene in design.scenes:
            if scene.type != "ending" and len(scene.content.player_choices) == 0:
                errors.append(f"场景 {scene.id} ({scene.title}) 是非结局场景但没有任何选择")
        
        # 2. 构建场景可达性图
        scene_ids = {scene.id for scene in design.scenes}
        scenes_with_incoming = set()
        
        for scene in design.scenes:
            for choice in scene.content.player_choices:
                if choice.leads_to:
                    scenes_with_incoming.add(choice.leads_to)
        
        # 检查不可达场景（除了起始场景）
        unreachable = scene_ids - scenes_with_incoming - {"S1"}  # S1是起始场景
        for scene_id in unreachable:
            scene = next(s for s in design.scenes if s.id == scene_id)
            errors.append(f"场景 {scene_id} ({scene.title}) 无法从任何其他场景到达")
        
        # 3. 验证Hub场景
        hub_scenes = [s for s in design.scenes if s.type == "hub"]
        if len(hub_scenes) != 1:
            errors.append(f"应该有且仅有1个Hub场景，但找到了 {len(hub_scenes)} 个")
        
        hub_route_mapping = {}  # 记录Hub的哪个选择对应哪条路线
        
        if hub_scenes:
            hub = hub_scenes[0]
            if hub.episode not in [3, 4]:  # Hub可以在第3或第4集
                errors.append(f"Hub场景应该在第3或4集，但实际在第 {hub.episode} 集")
            
            # 检查Hub场景是否设置ending_route，并记录映射关系
            sets_route = False
            for choice in hub.content.player_choices:
                for consequence in choice.consequences:
                    if consequence.flag_id == "ending_route":
                        sets_route = True
                        # 记录这个选择leads_to的场景属于哪条路线
                        if choice.leads_to:
                            hub_route_mapping[choice.leads_to] = consequence.value
                        break
            if not sets_route:
                errors.append("Hub场景没有设置ending_route标志")
        
        # 4. 使用图遍历来推断场景属于哪条路线
        # 构建场景图
        scene_graph = {scene.id: [] for scene in design.scenes}
        scene_dict = {scene.id: scene for scene in design.scenes}
        
        for scene in design.scenes:
            for choice in scene.content.player_choices:
                if choice.leads_to:
                    scene_graph[scene.id].append(choice.leads_to)
        
        # 从Hub场景的每个选择出发，使用BFS标记可达的场景
        route_scenes = {"A": set(), "B": set(), "C": set()}
        
        if hub_scenes and hub_route_mapping:
            from collections import deque
            
            for start_scene_id, route in hub_route_mapping.items():
                if route not in ["A", "B", "C"]:
                    continue
                    
                # BFS遍历
                queue = deque([start_scene_id])
                visited = set()
                
                while queue:
                    current = queue.popleft()
                    if current in visited:
                        continue
                    visited.add(current)
                    
                    # 只统计第4集及以后的场景
                    if current in scene_dict and scene_dict[current].episode >= 4:
                        route_scenes[route].add(current)
                    
                    # 继续遍历
                    if current in scene_graph:
                        for next_scene in scene_graph[current]:
                            if next_scene not in visited:
                                queue.append(next_scene)
        
        # 如果没有找到Hub或者Hub没有正确设置路线，尝试使用prerequisites方式（作为备选）
        if not any(route_scenes.values()):
            for scene in design.scenes:
                if scene.episode >= 4:  # 第4-6集是路线场景
                    # 检查场景的prerequisites中是否有ending_route条件
                    for prereq in scene.prerequisites:
                        if prereq.flag_id == "ending_route" and prereq.value in ["A", "B", "C"]:
                            route_scenes[prereq.value].add(scene.id)
        
        # 验证每条路线的场景数量
        for route, route_scene_ids in route_scenes.items():
            scenes = [scene_dict[sid] for sid in route_scene_ids if sid in scene_dict]
            
            # 第4-5集的场景（不包括第6集）
            ep45_scenes = [s for s in scenes if s.episode in [4, 5]]
            ep6_scenes = [s for s in scenes if s.episode == 6]
            
            # 第4-5集总共应该有4-8个场景（放宽到4个）
            if len(ep45_scenes) < 4:
                errors.append(f"路线 {route} 在第4-5集只有 {len(ep45_scenes)} 个场景，建议至少4个")
            elif len(ep45_scenes) > 10:
                errors.append(f"路线 {route} 在第4-5集有 {len(ep45_scenes)} 个场景，可能过多")
            
            # 第6集验证：至少要有1个场景，如果只有1个必须是结局场景
            if len(ep6_scenes) == 0:
                errors.append(f"路线 {route} 在第6集没有任何场景")
            elif len(ep6_scenes) == 1:
                # 如果只有1个场景，检查是否是结局场景
                single_scene = ep6_scenes[0]
                if single_scene.type != "ending":
                    errors.append(f"路线 {route} 在第6集只有1个场景但不是结局场景（类型是 {single_scene.type}）")
                # 如果是结局场景，那就没问题，可以留给player进行特别增强
            elif len(ep6_scenes) > 4:
                errors.append(f"路线 {route} 在第6集有 {len(ep6_scenes)} 个场景，可能过多")
        
        # 5. 检查是否有孤立的选择（leads_to指向不存在的场景）
        for scene in design.scenes:
            for choice in scene.content.player_choices:
                if choice.leads_to and choice.leads_to not in scene_ids:
                    errors.append(f"场景 {scene.id} 的选择指向不存在的场景 {choice.leads_to}")
        
        return errors
    
    def phase3_design_game_with_validation(self, story: StoryAndCharacters, concept: GameConceptAnalysis, 
                                         culture_language: str = "zh-CN", max_retries: int = 3) -> Optional[GameDesign]:
        """带验证的第三阶段设计，如果发现错误会重试"""
        for attempt in range(max_retries):
            if attempt > 0:
                print(f"\n🔄 第 {attempt + 1} 次尝试生成第三阶段...")
            
            # 运行phase 3
            game_design = self.phase3_design_game(story, concept, culture_language)
            
            if not game_design:
                continue
            
            # 验证设计
            errors = self._validate_game_design(game_design)
            
            if not errors:
                print("✅ 游戏设计验证通过！")
                return game_design
            
            print(f"\n❌ 发现 {len(errors)} 个设计问题：")
            for i, error in enumerate(errors, 1):
                print(f"   {i}. {error}")
            
            if attempt < max_retries - 1:
                print("\n即将重新生成...")
                import time
                time.sleep(2)  # 短暂延迟避免API限制
        
        print(f"\n❌ 经过 {max_retries} 次尝试仍未生成有效设计")
        return None
    
    def generate_complete_game(self, gender: str, seed: str, culture_language: str = "zh-CN", story_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """完整的三阶段生成流程"""
        print(f"🎮 O3 Game Designer - 分阶段版本")
        print(f"📝 种子: {seed}")
        print(f"👤 性别: {gender}")
        print(f"🌍 语言: {culture_language}")
        print("=" * 60)
        
        # 确保输出目录存在
        os.makedirs('generated_games', exist_ok=True)
        
        # 使用传入的story_id或生成新的
        self.story_id = story_id or str(uuid.uuid4())
        print(f"🆔 Story ID: {self.story_id}")
        
        # 第一阶段：概念分析
        concept = self.phase1_analyze_concept(seed, culture_language)
        if not concept:
            print("❌ 第一阶段失败，终止生成")
            return None
        
        # 第二阶段：故事与人物
        story = self.phase2_create_story(gender, concept, culture_language)
        if not story:
            print("❌ 第二阶段失败，终止生成")
            return None
        
        # 第三阶段：游戏设计
        game_design = self.phase3_design_game_with_validation(story, concept, culture_language)
        if not game_design:
            print("❌ 第三阶段失败，终止生成")
            return None
        
        # 组装完整的游戏数据
        complete_game = self._assemble_complete_game(concept, story, game_design, culture_language)
        
        # 保存完整游戏
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"generated_games/game_phased_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(complete_game, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 完整游戏已保存至: {filename}")
        
        # 自动导入到 Neo4j（如果配置了环境变量）
        self._import_to_neo4j(complete_game, filename)
        
        return complete_game
    
    def _assemble_complete_game(self, concept: GameConceptAnalysis, story: StoryAndCharacters, design: GameDesign, culture_language: str) -> Dict[str, Any]:
        """组装三个阶段的结果为完整游戏"""
        
        # 自动识别 Hub 场景作为主要分支点
        major_branches = []
        for scene in design.scenes:
            if scene.type == "hub":
                major_branches.append({
                    "scene_id": scene.id,
                    "branches_created": len(scene.content.player_choices),
                    "significance": f"Hub场景 - {scene.title}"
                })
        
        return {
            "story_id": self.story_id,
            "metadata": {
                "title": story.title,
                "genre": story.genre,
                "culture_language": culture_language,
                "inspiration_analysis": {
                    "user_intent": concept.user_intent,
                    "reference_works": [r.model_dump() for r in concept.reference_works],
                    "extracted_patterns": [],
                    "design_rationale": concept.narrative_approach,
                    "core_concepts": concept.core_concepts
                }
            },
            "story_config": {
                "episodes": design.episodes,
                "total_scenes": design.total_scenes,
                "branching_strategy": "endings_first",
                "complexity_controls": {
                    "max_concurrent_branches": 3,
                    "branch_depth": 4,
                    "hub_episode": "3_or_4",
                    "endings_per_route": 3,
                    "episode_structure": {
                        "ep1-2": "shared_mainline",
                        "ep3-4": "hub_divergence_flexible",
                        "ep4-5": "route_development_6-8_scenes",
                        "ep6": "climax_and_ending_3-4_scenes"
                    }
                }
            },
            "story_brief": story.story_brief.model_dump(),
            "characters": [c.model_dump() for c in story.characters],
            "flags": [f.model_dump() for f in design.flags],
            "critical_points": {
                "start_scene": "S1",
                "endings": [e.model_dump() for e in design.endings],
                "major_branches": major_branches
            },
            "scenes": [s.model_dump() for s in design.scenes],
            "concept_analysis": concept.model_dump()
        }
    
    def _save_phase_result(self, phase_name: str, data: Dict[str, Any]):
        """保存每个阶段的结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"generated_games/{phase_name}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 {phase_name} 已保存至: {filename}")
    
    def _import_to_neo4j(self, game_data: Dict[str, Any], filename: str):
        """自动导入游戏到 Neo4j（如果配置了环境变量）"""
        try:
            # Use direct Neo4j importer
            from neo4j_direct_importer import Neo4jDirectImporter
        
            # Get Neo4j credentials
            neo4j_uri = os.getenv('NEO4J_URI')
            neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
            neo4j_password = os.getenv('NEO4J_PASSWORD')
        
            if neo4j_uri and neo4j_password:
                print("\n🔄 正在导入游戏到 Neo4j...")
                
                importer = Neo4jDirectImporter(neo4j_uri, neo4j_user, neo4j_password)
                try:
                    story_id = importer.import_o3_game(game_data, filename)
                    print(f"✅ 成功导入到 Neo4j，Story ID: {story_id}")
                    print(f"   运行以下命令开始游戏：python play_o3_game_interactive_from_neo4j.py")
                finally:
                    importer.close()
            else:
                print("\n⚠️  未找到 Neo4j 配置，跳过导入。")
                print("   设置 NEO4J_URI 和 NEO4J_PASSWORD 环境变量以启用自动导入。")
                
        except Exception as e:
            print(f"\n⚠️  导入 Neo4j 失败：{str(e)}")
            print("   游戏文件已成功保存。")

# 测试
if __name__ == "__main__":
    designer = O3GameDesignerPhased()
    # 允许我自己输入性别，种子，文化语言
    gender = input("请输入性别: ")
    seed = input("请输入种子: ")
    culture_language = input("请输入文化语言: ")
    designer.generate_complete_game(
        gender,
        seed,
        culture_language,
        "zh-CN"
    ) 