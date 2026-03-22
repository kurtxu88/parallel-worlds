#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FastAPI Interactive Player v2 - Reusing O3ScreenplayPlayer
This version directly imports and reuses the advanced prompt design from play_o3_game_interactive_from_neo4j.py
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime, timezone
from pydantic import BaseModel
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import re

# Import the core O3ScreenplayPlayer class
from play_o3_game_interactive_from_neo4j import O3ScreenplayPlayer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="Interactive Screenplay API v2")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ConversationMessage(BaseModel):
    role: str
    content: str
    episode_number: Optional[int] = None
    scene_id: Optional[str] = None
    round_number: Optional[int] = None

class GameState(BaseModel):
    current_scene: Dict
    current_episode: int
    scene_interaction_count: int
    story_flags: Dict
    scene_history: List[str]
    available_choices: List[Dict]

class GameInteractRequest(BaseModel):
    user_id: str
    story_id: str
    session_id: str
    request_type: str  # "game_start", "user_input", or "skip_scene"
    user_input: str = ""
    conversation_history: List[ConversationMessage] = []
    game_state: Optional[GameState] = None

class GameStateManager:
    """Manages game state using O3ScreenplayPlayer"""
    
    def __init__(self, user_id: str, story_id: str):
        self.user_id = user_id
        self.story_id = story_id
        self.player: Optional[O3ScreenplayPlayer] = None
        
    def get_game_identifier(self) -> str:
        """Get unique game identifier"""
        return f"{self.user_id}:{self.story_id}"
    
    async def initialize(self) -> bool:
        """Initialize the game"""
        try:
            # Create O3ScreenplayPlayer instance
            self.player = O3ScreenplayPlayer()
            
            # Load game from Neo4j
            success = self.player.load_game(self.story_id)
            if not success:
                logger.error(f"Failed to load game {self.story_id}")
                return False
                
            logger.info(f"✅ Loaded game: {self.player.screenplay_data['metadata']['title']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize game: {e}")
            return False
    
    def restore_from_history(self, conversation_history: List[ConversationMessage], game_state: Optional[GameState]):
        """Restore game state from history"""
        if not self.player:
            return False
            
        try:
            # If we have game state, restore it
            if game_state:
                # Restore scene without triggering display
                scene_id = game_state.current_scene.get('id', 'S1')
                scene = next((s for s in self.player.screenplay_data['scenes'] if s['id'] == scene_id), None)
                
                if scene:
                    # Manually set scene state without calling load_scene
                    self.player.current_scene = scene
                    self.player.current_episode = game_state.current_episode
                    self.player.scene_history = game_state.scene_history
                    self.player.scene_interaction_count = game_state.scene_interaction_count
                    self.player.story_flags = game_state.story_flags
                    
                    # Prepare available choices
                    self.player._prepare_available_choices()
                    
                    # Restore conversation history
                    self.player.conversation_history = []
                    self.player.episode_conversation_history = []
                    
                    for msg in conversation_history:
                        msg_dict = {
                            "role": msg.role, 
                            "content": msg.content,
                            "episode_number": msg.episode_number,
                            "scene_id": msg.scene_id,
                            "round_number": msg.round_number
                        }
                        self.player.conversation_history.append(msg_dict)
                        self.player.episode_conversation_history.append(msg_dict)
                    
                    logger.info(f"✅ Restored game state at scene {scene_id}")
                else:
                    # No valid scene, start from beginning
                    start_scene_id = self.player.screenplay_data['critical_points']['start_scene']
                    scene = next((s for s in self.player.screenplay_data['scenes'] if s['id'] == start_scene_id), None)
                    if scene:
                        self.player.current_scene = scene
                        self.player.current_episode = scene.get('episode', 1)
                        self.player.scene_history = [start_scene_id]
                        self.player.scene_interaction_count = 0
                        self.player._prepare_available_choices()
                    
            else:
                # No game state, start fresh
                start_scene_id = self.player.screenplay_data['critical_points']['start_scene']
                scene = next((s for s in self.player.screenplay_data['scenes'] if s['id'] == start_scene_id), None)
                if scene:
                    self.player.current_scene = scene
                    self.player.current_episode = scene.get('episode', 1)
                    self.player.scene_history = [start_scene_id]
                    self.player.scene_interaction_count = 0
                    self.player._prepare_available_choices()
                    
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore game state: {e}")
            return False
    
    def get_current_state(self) -> GameState:
        """Get current game state"""
        if not self.player or not self.player.current_scene:
            return GameState(
                current_scene={},
                current_episode=1,
                scene_interaction_count=0,
                story_flags={},
                scene_history=[],
                available_choices=[]
            )
        
        # Convert available choices to dict format
        available_choices = []
        if hasattr(self.player, 'available_choices'):
            for i, (idx, choice, is_hidden) in enumerate(self.player.available_choices):
                available_choices.append({
                    "index": idx,
                    "is_hidden": is_hidden,
                    **choice
                })
        
        return GameState(
            current_scene=self.player.current_scene,
            current_episode=self.player.current_episode,
            scene_interaction_count=self.player.scene_interaction_count,
            story_flags=self.player.story_flags,
            scene_history=self.player.scene_history,
            available_choices=available_choices
        )

async def persist_stream_snapshot(
    user_id: str,
    story_id: str,
    session_id: str,
    scene_id: str,
    episode_number: int,
    round_number: int,
    user_input: str,
    ai_response: str,
    connection_active: bool
):
    if not connection_active:
        logger.warning("Connection lost before transcript persistence for %s:%s", user_id, story_id)
        return False

    # The standalone open-source runtime persists events at the API boundary.
    # This hook is intentionally a no-op inside the legacy player module.
    return bool(ai_response or user_input)



class StreamingGamePlayer:
    """Handles streaming game interactions"""
    
    def __init__(self, game_state: GameStateManager):
        self.game_state = game_state
    
    def _count_completed_events(self, player: O3ScreenplayPlayer) -> int:
        """Count completed events based on EVENT_COMPLETED markers in conversation history"""
        completed_count = 0
        completed_events = set()
        
        # Search through conversation history for EVENT_COMPLETED markers
        for msg in player.conversation_history:
            if msg.get('role') == 'assistant' and '[EVENT_COMPLETED:' in msg.get('content', ''):
                content = msg['content']
                # Extract event name from [EVENT_COMPLETED: event_name]
                start = content.find('[EVENT_COMPLETED:')
                if start != -1:
                    end = content.find(']', start)
                    if end != -1:
                        event_marker = content[start:end+1]
                        completed_events.add(event_marker)
        
        return len(completed_events)
    
    def _get_epilogue_for_ending(self, player: O3ScreenplayPlayer, scene_id: str) -> Optional[str]:
        """Get the appropriate epilogue for the current ending based on player's game state"""
        # Get endings from critical_points
        critical_points = player.screenplay_data.get('critical_points', {})
        endings = critical_points.get('endings', [])
        
        # Find the ending that matches current scene
        matching_ending = None
        for ending in endings:
            if ending.get('scene_id') == scene_id:
                matching_ending = ending
                break
        
        if not matching_ending:
            return None
        
        # Get epilogue variants
        epilogue_variants = matching_ending.get('epilogue_variants', [])
        if not epilogue_variants:
            return None
        
        # Find the first matching epilogue based on conditions
        for variant in epilogue_variants:
            conditions = variant.get('conditions', [])
            
            # Parse conditions if it's a string (from Neo4j)
            if isinstance(conditions, str):
                try:
                    conditions = json.loads(conditions)
                except:
                    conditions = []
            
            # Check if all conditions are met
            all_conditions_met = True
            for condition in conditions:
                flag_id = condition.get('flag_id')
                operator = condition.get('operator')
                value = condition.get('value')
                
                if flag_id and flag_id in player.story_flags:
                    current_value = player.story_flags[flag_id]
                    
                    if operator == '==':
                        if current_value != value:
                            all_conditions_met = False
                            break
                    elif operator == '<':
                        if current_value >= value:
                            all_conditions_met = False
                            break
                    elif operator == '>':
                        if current_value <= value:
                            all_conditions_met = False
                            break
                    elif operator == '<=':
                        if current_value > value:
                            all_conditions_met = False
                            break
                    elif operator == '>=':
                        if current_value < value:
                            all_conditions_met = False
                            break
            
            if all_conditions_met:
                return variant.get('narrative', '')
        
        # If no conditions match, return the first epilogue as default
        if epilogue_variants:
            return epilogue_variants[0].get('narrative', '')
        
        return None
    

    def _build_scene_header(self, scene: Dict, culture_language: str) -> str:
        """Build the scene header string for conversation history"""
        is_chinese = culture_language == 'zh-CN'
        episode_text = f"🎬 第 {scene.get('episode', 1)} 集" if is_chinese else f"🎬 Episode {scene.get('episode', 1)}"
        
        return f"📍 {scene['title']}\n\n{episode_text}\n\n============================================================\n\n"
    
    async def generate_initial_screenplay(self, player: O3ScreenplayPlayer, session_id: str, request: Request, scene_header: str = "") -> AsyncGenerator[str, None]:
        """Generate the initial screenplay content after scene opening"""
        # Prepare the player for the scene
        player._prepare_available_choices()
        
        # Get the prompt messages for initial scene content
        # Using empty user input to trigger initial content generation
        messages = self._get_prompt_messages(player, "")
        
        # Stream OpenAI response for initial screenplay content
        response = player.client.chat.completions.create(
            model=player.model,
            messages=messages,
            temperature=0.1,
            max_tokens=5000,
            stream=True
        )
        
        # Collect and stream response
        full_response = ""
        async for chunk in self._stream_openai_response(response, request):
            if chunk.startswith("data: [CONNECTION_LOST]"):
                break
            full_response += chunk.replace("data: ", "").replace("\n\n", "")
            yield chunk
        
        # Add the screenplay content to history with scene header
        if full_response.strip():
            # Combine scene header with screenplay content for complete context
            complete_content = scene_header + full_response.strip()
            
            assistant_msg = {
                "role": "assistant",
                "content": complete_content,
                "episode_number": player.current_episode,
                "scene_id": player.current_scene.get('id', ''),
                "round_number": player.scene_interaction_count
            }
            player.conversation_history.append(assistant_msg)
            player.episode_conversation_history.append(assistant_msg)
            player.screenplay_content_history.append(complete_content)
            
            await persist_stream_snapshot(
                user_id=self.game_state.user_id,
                story_id=self.game_state.story_id,
                session_id=session_id,
                scene_id=player.current_scene.get('id', ''),
                episode_number=player.current_episode,
                round_number=player.scene_interaction_count,
                user_input="",  # No user input for initial screenplay
                ai_response=complete_content,
                connection_active=not await request.is_disconnected()
            )
            
            # Don't immediately end the story for ending scenes
            # Let them play out through key events first
            logger.info(f"Initial screenplay generated for {player.current_scene.get('type', 'normal')} scene")
    
    async def process_input_stream(self, request_type: str, user_input: str, session_id: str, request: Request) -> AsyncGenerator[str, None]:
        """Process input and stream response"""
        try:
            player = self.game_state.player
            if not player:
                yield "data: [ERROR] Game not initialized\n\n"
                return
            
            if request_type == "game_start":
                # Game start: directly generate initial screenplay with scene header
                yield "data: [GAME_START]\n\n"
                
                # Get culture language for header formatting
                culture_language = player.screenplay_data['metadata'].get('culture_language', 'en-US')
                is_chinese = culture_language == 'zh-CN'
                
                # Build scene header for conversation history
                scene_header = self._build_scene_header(player.current_scene, culture_language)
                
                # Display scene title and episode
                yield f"data: 📍 {player.current_scene['title']}\n\n"
                yield "data: \n\n"  # 空行
                yield f"data: 🎬 第 {player.current_scene.get('episode', 1)} 集\n\n" if is_chinese else f"data: 🎬 Episode {player.current_scene.get('episode', 1)}\n\n"
                yield "data: \n\n"  # 空行
                yield "data: ============================================================\n\n"
                yield "data: \n\n"  # 空行
                
                # Directly generate the initial screenplay content which will include scene description
                async for chunk in self.generate_initial_screenplay(player, session_id, request, scene_header):
                    yield chunk
                
                # Send game state
                final_state = self.game_state.get_current_state()
                yield f"data: [GAME_STATE] {final_state.model_dump_json()}\n\n"
                
                # Note: Don't immediately end the story just because the starting scene is marked as ending
                # The player should still be able to interact with the scene and make choices
                
                yield "data: [END]\n\n"
                
            elif request_type == "skip_scene":
                # Handle skip to next scene request
                logger.info(f"Processing skip_scene request for user {self.game_state.user_id} with input: {user_input}")
                
                # Check current scene type
                if player.current_scene.get('type') == 'ending':
                    # Already at ending scene, can't skip
                    culture_language = player.screenplay_data['metadata'].get('culture_language', 'en-US')
                    if culture_language == 'zh-CN':
                        yield "data: 这已经是故事的结局，无法跳过。\n\n"
                    else:
                        yield "data: This is already the ending of the story, cannot skip.\n\n"
                
                # Check if there are available choices
                elif hasattr(player, 'available_choices') and player.available_choices:
                    # Find the matching choice based on user input
                    selected_choice = None
                    choice_data = None
                    
                    # Search for matching choice text
                    for idx, (choice_idx, choice, is_hidden) in enumerate(player.available_choices):
                        if not is_hidden and choice.get('choice_text') == user_input:
                            selected_choice = idx + 1
                            choice_data = choice
                            break
                    
                    # If no match found, default to first choice
                    if not selected_choice:
                        logger.warning(f"No matching choice found for: {user_input}, defaulting to first choice")
                        selected_choice = 1
                        _, choice_data, _ = player.available_choices[0]
                    
                    # Apply consequences if any
                    if choice_data.get('consequences'):
                        # Use the player's method to apply consequences
                        player._apply_consequences(choice_data['consequences'])
                        logger.info(f"Applied consequences from skip: {choice_data['consequences']}")
                    
                    # Get next scene
                    next_scene_id = choice_data.get('leads_to')
                    if next_scene_id:
                        next_scene = next((s for s in player.screenplay_data['scenes'] if s['id'] == next_scene_id), None)
                        if next_scene:
                            # Update scene state
                            player.current_scene = next_scene
                            player.current_episode = next_scene.get('episode', 1)
                            player.scene_history.append(next_scene_id)
                            player.scene_interaction_count = 0
                            player._prepare_available_choices()
                            
                            # Notify about scene transition
                            yield f"data: [SCENE_TRANSITION] {next_scene_id}\n\n"
                            
                            # Build scene header
                            culture_language = player.screenplay_data['metadata'].get('culture_language', 'en-US')
                            is_chinese = culture_language == 'zh-CN'
                            scene_header = self._build_scene_header(next_scene, culture_language)
                            
                            # Display scene title and episode info
                            yield f"data: 📍 {next_scene['title']}\n\n"
                            yield f"data: 🎬 第 {next_scene.get('episode', 1)} 集\n\n" if is_chinese else f"data: 🎬 Episode {next_scene.get('episode', 1)}\n\n"
                            yield "data: \n\n"
                            yield "data: ============================================================\n\n"
                            yield "data: \n\n"
                            
                            # Generate initial screenplay for new scene
                            async for chunk in self.generate_initial_screenplay(player, session_id, request, scene_header):
                                yield chunk
                            
                            # Send updated game state
                            final_state = self.game_state.get_current_state()
                            yield f"data: [GAME_STATE] {final_state.model_dump_json()}\n\n"
                            
                            # End the stream after generating initial screenplay
                            yield "data: [END]\n\n"
                        else:
                            yield "data: [ERROR] Next scene not found\n\n"
                            yield "data: [END]\n\n"
                    else:
                        yield "data: [ERROR] No next scene defined for current choice\n\n"
                        yield "data: [END]\n\n"
                else:
                    # No choices available
                    culture_language = player.screenplay_data['metadata'].get('culture_language', 'en-US')
                    if culture_language == 'zh-CN':
                        yield "data: 当前场景没有可用的选择来跳过。\n\n"
                    else:
                        yield "data: No available choices to skip in current scene.\n\n"
                    yield "data: [END]\n\n"
                
            elif request_type == "user_input":
                # Process user input using the player's _process_natural_language method
                # But we need to handle streaming ourselves
                
                # Add user input to history
                user_msg = {
                    "role": "user", 
                    "content": user_input,
                    "episode_number": player.current_episode,
                    "scene_id": player.current_scene.get('id', ''),
                    "round_number": player.scene_interaction_count
                }
                player.conversation_history.append(user_msg)
                player.episode_conversation_history.append(user_msg)
                player.screenplay_content_history.append(user_input)
                
                # Increment interaction count
                player.scene_interaction_count += 1
                
                # Get the prompt messages using player's method
                messages = self._get_prompt_messages(player, user_input)
                
                # PRINT COMPLETE PROMPT TO CONSOLE
                print("\n" + "="*100)
                print("🔍 COMPLETE PROMPT SENT TO LLM (FastAPI v2)")
                print("="*100)
                print(f"Total messages: {len(messages)}")
                print(f"Total characters: {sum(len(msg['content']) for msg in messages)}")
                print("="*100)
                
                for i, msg in enumerate(messages):
                    # print(f"\n### Message {i+1} - Role: {msg['role']}")
                    # print("-"*100)
                    print(msg['content'])
                    # print("-"*100)
                
                print("\n" + "="*100)
                print("END OF PROMPT")
                print("="*100 + "\n")
                
                # Stream OpenAI response
                response = player.client.chat.completions.create(
                    model=player.model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=5000,
                    stream=True
                )
                
                # Collect and stream response
                full_response = ""
                async for chunk in self._stream_openai_response(response, request):
                    if chunk.startswith("data: [CONNECTION_LOST]"):
                        break
                    full_response += chunk.replace("data: ", "").replace("\n\n", "")
                    yield chunk
                
                # Removed emotional beat tracking
                
                # Check for choice selection
                choice_match = re.search(r'CHOICE_SELECTED:\s*(\d+)', full_response)
                selected_choice = None
                choice_text = None
                
                if choice_match:
                    selected_choice = int(choice_match.group(1))
                    display_response = re.sub(r'CHOICE_SELECTED:\s*\d+[^\w\s]*\s*', '', full_response).strip()
                    display_response = re.sub(r'\s+', ' ', display_response).strip()
                    
                    # Get the actual choice text to include in history
                    if hasattr(player, 'available_choices') and player.available_choices:
                        if 1 <= selected_choice <= len(player.available_choices):
                            _, choice, _ = player.available_choices[selected_choice - 1]
                            choice_text = choice.get('choice_text', f'Choice {selected_choice}')
                            
                            # Append choice information to the display response for history
                            culture_language = player.screenplay_data['metadata'].get('culture_language', 'en-US')
                            is_chinese = culture_language == 'zh-CN'
                            
                            if is_chinese:
                                display_response += f"\n\n【玩家选择】{choice_text}"
                            else:
                                display_response += f"\n\n[Player chose: {choice_text}]"
                else:
                    display_response = full_response
                
                # Add AI response to history
                assistant_msg = {
                    "role": "assistant", 
                    "content": display_response,
                    "episode_number": player.current_episode,
                    "scene_id": player.current_scene.get('id', ''),
                    "round_number": player.scene_interaction_count
                }
                player.conversation_history.append(assistant_msg)
                player.episode_conversation_history.append(assistant_msg)
                player.screenplay_content_history.append(display_response)
                
                # Check if we're in an ending scene and should end the story
                if player.current_scene.get('type') == 'ending':
                    # Check if scene has no choices
                    has_no_choices = (not hasattr(player, 'available_choices') or 
                                     not player.available_choices or 
                                     len(player.available_choices) == 0)
                    
                    # Get key events and check completion
                    content = player.current_scene.get('content', {})
                    key_events = content.get('key_events', [])
                    completed_events = self._count_completed_events(player)
                    
                    # Determine if we should end the story
                    should_end_story = False
                    
                    if has_no_choices:
                        if key_events:
                            # Check if all events are completed
                            if completed_events >= len(key_events):
                                should_end_story = True
                            # Or if we've had many interactions (failsafe)
                            elif player.scene_interaction_count >= len(key_events) * 5:
                                should_end_story = True
                                logger.info(f"Ending due to high interaction count: {player.scene_interaction_count}")
                        else:
                            # No key events and no choices, end after some interactions
                            if player.scene_interaction_count >= 3:
                                should_end_story = True
                    
                    if should_end_story:
                        logger.info(f"Ending scene completed - {completed_events}/{len(key_events)} events marked complete")
                        culture_language = player.screenplay_data['metadata'].get('culture_language', 'en-US')
                        is_chinese = culture_language == 'zh-CN'
                        
                        # Epilogue is now integrated into the ending narrative via prompt
                        # No longer sent separately to maintain story continuity
                        
                        # Send ending notification
                        yield "data: \n\n"
                        yield "data: ============================================================\n\n"
                        yield "data: \n\n"
                        if is_chinese:
                            yield "data: 🎭 故事结局 🎭\n\n"
                            yield "data: \n\n"
                            yield f"data: 恭喜你完成了《{player.screenplay_data['metadata']['title']}》的故事！\n\n"
                        else:
                            yield "data: 🎭 THE END 🎭\n\n"
                            yield "data: \n\n"
                            yield f"data: Congratulations! You've completed the story of \"{player.screenplay_data['metadata']['title']}\"!\n\n"
                        yield "data: \n\n"
                        yield "data: ============================================================\n\n"
                        yield "data: \n\n"
                        
                        # Send ending flag
                        yield "data: [STORY_ENDED]\n\n"
                
                # Process choice if selected
                if selected_choice:
                    logger.info(f"Processing CHOICE_SELECTED: {selected_choice}")
                    
                    if not hasattr(player, 'available_choices'):
                        logger.error("Player object has no available_choices attribute")
                    elif not player.available_choices:
                        logger.error("Player available_choices is empty")
                    else:
                        logger.info(f"Player has {len(player.available_choices)} available choices")
                        
                        if 1 <= selected_choice <= len(player.available_choices):
                            _, choice, _ = player.available_choices[selected_choice - 1]
                            logger.info(f"Selected choice: {choice.get('choice_text', 'Unknown')}")
                            
                            # Apply consequences
                            if 'consequences' in choice:
                                player._apply_consequences(choice['consequences'])
                                logger.info(f"Applied consequences: {choice['consequences']}")
                            
                            # Scene transition
                            next_scene_id = choice.get('leads_to')
                            logger.info(f"Next scene ID: {next_scene_id}")
                            if next_scene_id:
                                # Load next scene manually without triggering display
                                next_scene = next((s for s in player.screenplay_data['scenes'] if s['id'] == next_scene_id), None)
                                if next_scene:
                                    # Update scene state
                                    player.current_scene = next_scene
                                    player.current_episode = next_scene.get('episode', 1)
                                    player.scene_history.append(next_scene_id)
                                    player.scene_interaction_count = 0
                                    player._prepare_available_choices()
                                    
                                    yield f"data: [SCENE_TRANSITION] {next_scene_id}\n\n"
                                    
                                    # Get culture language for header formatting
                                    culture_language = player.screenplay_data['metadata'].get('culture_language', 'en-US')
                                    is_chinese = culture_language == 'zh-CN'
                                    
                                    # Build scene header for conversation history
                                    scene_header = self._build_scene_header(next_scene, culture_language)
                                    
                                    # Display scene title and episode
                                    yield f"data: 📍 {next_scene['title']}\n\n"
                                    yield "data: \n\n"
                                    yield f"data: 🎬 第 {next_scene.get('episode', 1)} 集\n\n" if is_chinese else f"data: 🎬 Episode {next_scene.get('episode', 1)}\n\n"
                                    yield "data: \n\n"
                                    yield "data: ============================================================\n\n"
                                    yield "data: \n\n"
                                    
                                    # Generate initial screenplay content for the new scene directly
                                    async for chunk in self.generate_initial_screenplay(player, session_id, request, scene_header):
                                        yield chunk
                                    
                                    # Note: Don't send ending notification here when transitioning TO an ending scene
                                    # The ending message should only appear AFTER the user makes their final choice IN the ending scene
                                else:
                                    logger.error(f"Scene {next_scene_id} not found")
                            else:
                                # No next scene - check if we're in an ending scene
                                if player.current_scene.get('type') == 'ending':
                                    logger.info("No next scene and current scene is ending - story complete")
                                    culture_language = player.screenplay_data['metadata'].get('culture_language', 'en-US')
                                    is_chinese = culture_language == 'zh-CN'
                                    
                                    # Epilogue is now integrated into the ending narrative via prompt
                                    # No longer sent separately to maintain story continuity
                                    
                                    # Send ending notification
                                    yield "data: \n\n"
                                    yield "data: ============================================================\n\n"
                                    yield "data: \n\n"
                                    if is_chinese:
                                        yield "data: 🎭 故事结局 🎭\n\n"
                                        yield "data: \n\n"
                                        yield f"data: 恭喜你完成了《{player.screenplay_data['metadata']['title']}》的故事！\n\n"
                                    else:
                                        yield "data: 🎭 THE END 🎭\n\n"
                                        yield "data: \n\n"
                                        yield f"data: Congratulations! You've completed the story of \"{player.screenplay_data['metadata']['title']}\"!\n\n"
                                    yield "data: \n\n"
                                    yield "data: ============================================================\n\n"
                                    yield "data: \n\n"
                                    
                                    # Send ending flag
                                    yield "data: [STORY_ENDED]\n\n"
                
                # Send final state
                final_state = self.game_state.get_current_state()
                yield f"data: [GAME_STATE] {final_state.model_dump_json()}\n\n"
                yield "data: [END]\n\n"
                
            else:
                yield "data: [ERROR] Invalid request_type\n\n"
                
        except Exception as e:
            logger.error(f"Error in stream processing: {e}")
            yield f"data: [ERROR] {str(e)}\n\n"
    
    async def _stream_openai_response(self, response, request: Request) -> AsyncGenerator[str, None]:
        """Stream OpenAI response"""
        try:
            for chunk in response:
                if await request.is_disconnected():
                    yield "data: [CONNECTION_LOST]\n\n"
                    break
                
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield f"data: {content}\n\n"
                    
                await asyncio.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Error in OpenAI streaming: {e}")
            yield f"data: [ERROR] {str(e)}\n\n"
    
    def _get_prompt_messages(self, player: O3ScreenplayPlayer, user_input: str) -> List[Dict[str, str]]:
        """Extract prompt building logic from _process_natural_language"""
        # Directly copied from play_o3_game_interactive_from_neo4j.py
        
        culture_language = player.screenplay_data['metadata'].get('culture_language', 'en-US')
        is_chinese = culture_language == 'zh-CN'
        
        # Build global context from story_brief and characters
        global_context = ""
        
        # Add story brief context
        if player.screenplay_data.get('story_brief'):
            brief = player.screenplay_data['story_brief']
            if is_chinese:
                global_context += "\n\n【全局故事背景】\n"
                if brief.get('main_plot'):
                    global_context += f"\n主要剧情：\n{brief['main_plot']}\n"
                if brief.get('world_setting'):
                    global_context += f"\n世界设定：\n{brief['world_setting']}\n"
                if brief.get('character_relationships'):
                    global_context += f"\n人物关系：\n{brief['character_relationships']}\n"
                if brief.get('emotional_storyline'):
                    global_context += f"\n情感主线：\n{brief['emotional_storyline']}\n"
            else:
                global_context += "\n\n[GLOBAL STORY CONTEXT]\n"
                if brief.get('main_plot'):
                    global_context += f"\nMain Plot:\n{brief['main_plot']}\n"
                if brief.get('world_setting'):
                    global_context += f"\nWorld Setting:\n{brief['world_setting']}\n"
                if brief.get('character_relationships'):
                    global_context += f"\nCharacter Relationships:\n{brief['character_relationships']}\n"
                if brief.get('emotional_storyline'):
                    global_context += f"\nEmotional Storyline:\n{brief['emotional_storyline']}\n"
        
                    # Add relevant character profiles for current scene
            character_context = ""
            if player.screenplay_data.get('characters'):
                # Find characters mentioned in current scene
                scene_narrative = player.current_scene.get('content', {}).get('narrative', '')
                scene_title = player.current_scene.get('title', '')
                scene_desc = player.current_scene.get('description', '')
                scene_text = f"{scene_title} {scene_desc} {scene_narrative}"
                
                relevant_chars = []
                for char in player.screenplay_data['characters']:
                    char_name = char.get('name', '')
                    if char_name and char_name in scene_text:
                        relevant_chars.append(char)
                
                if relevant_chars:
                    if is_chinese:
                        character_context += "\n\n【场景相关人物】\n"
                        for char in relevant_chars:  # Use all relevant characters
                            character_context += f"\n{char['name']}：\n"
                            # 显示角色类型
                            char_type = char.get('character_type', 'major_npc')
                            type_labels = {
                                'protagonist': '主角',
                                'major_npc': '重要角色',
                                'minor_npc': '配角'
                            }
                            character_context += f"- 角色类型：{type_labels.get(char_type, char_type)}\n"
                            
                            if char.get('basic_info'):
                                character_context += f"- 基本信息：{char['basic_info']}\n"
                            if char.get('biography'):
                                character_context += f"- 人物背景：{char['biography']}\n"
                            if char.get('key_dialogue_style'):
                                character_context += f"- 对话风格：{char['key_dialogue_style']}\n"
                            # Add more depth for emotional scenes
                            if player.current_scene.get('type') == 'emotional' and char.get('inner_conflict'):
                                character_context += f"- 内心冲突：{char['inner_conflict']}\n"
                            elif char.get('inner_conflict'):  # Show for other scenes too
                                character_context += f"- 内心冲突：{char['inner_conflict']}\n"
                            # Add growth arc for hub scenes
                            if player.current_scene.get('type') == 'hub' and char.get('growth_arc'):
                                character_context += f"- 成长轨迹：{char['growth_arc']}\n"
                            elif char.get('growth_arc'):  # Show for other scenes too
                                character_context += f"- 成长轨迹：{char['growth_arc']}\n"
                            # Add relationships for all scenes
                            if char.get('relationships'):
                                character_context += f"- 人物关系：{char['relationships']}\n"
                            if char.get('character_function'):
                                character_context += f"- 角色功能：{char['character_function']}\n"
                    else:
                        character_context += "\n\n[SCENE-RELEVANT CHARACTERS]\n"
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
                            
                            if char.get('basic_info'):
                                character_context += f"- Basic Info: {char['basic_info']}\n"
                            if char.get('biography'):
                                character_context += f"- Character Background: {char['biography']}\n"
                            if char.get('key_dialogue_style'):
                                character_context += f"- Dialogue Style: {char['key_dialogue_style']}\n"
                            # Add more depth for emotional scenes
                            if player.current_scene.get('type') == 'emotional' and char.get('inner_conflict'):
                                character_context += f"- Inner Conflict: {char['inner_conflict']}\n"
                            elif char.get('inner_conflict'):  # Show for other scenes too
                                character_context += f"- Inner Conflict: {char['inner_conflict']}\n"
                            # Add growth arc for hub scenes
                            if player.current_scene.get('type') == 'hub' and char.get('growth_arc'):
                                character_context += f"- Growth Arc: {char['growth_arc']}\n"
                            elif char.get('growth_arc'):  # Show for other scenes too
                                character_context += f"- Growth Arc: {char['growth_arc']}\n"
                            # Add relationships for all scenes
                            if char.get('relationships'):
                                character_context += f"- Relationships: {char['relationships']}\n"
                            if char.get('character_function'):
                                character_context += f"- Character Function: {char['character_function']}\n"
        
        # Build flag state context for AI
        flag_context = ""
        if player.screenplay_data.get('flags') and player.story_flags:
            changed_flags = []
            for flag in player.screenplay_data['flags']:
                flag_id = flag['id']
                current_value = player.story_flags.get(flag_id, flag['default_value'])
                
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
        if player.available_choices:
            choices_context = "\n\n可用的选择选项：\n" if is_chinese else "\n\nAvailable Choice Options:\n"
            for i, (_, choice, _) in enumerate(player.available_choices, 1):
                choices_context += f"{i}. {choice['choice_text']}\n"
                if choice.get('internal_reasoning'):
                    choices_context += f"   说明：{choice['internal_reasoning']}\n" if is_chinese else f"   Note: {choice['internal_reasoning']}\n"
                if choice.get('consequences'):
                    consequences_text = player._format_consequences(choice['consequences'])
                    if consequences_text:
                        choices_context += f"   剧情影响：{consequences_text}\n" if is_chinese else f"   Story Impact: {consequences_text}\n"
        
        # Build key events context with tracking guidance
        key_events_context = ""
        content = player.current_scene.get('content', {})
        if content.get('key_events'):
            events = content['key_events']
            
            if is_chinese:
                key_events_context = "\n\n【关键事件进展】\n本场景需要展开以下事件：\n"
                for event in events:
                    key_events_context += f"• {event}\n"
                
                key_events_context += "\n【追踪方式】\n"
                key_events_context += "- 充分展开一个事件后，【必须】添加：[EVENT_COMPLETED: 事件名称]\n"
                key_events_context += "- 标记位置：在描述该事件完成的段落末尾\n"
                key_events_context += "- 【核心规则】每轮回复最多只能有一个[EVENT_COMPLETED]标记\n"
                key_events_context += "- 【重要】添加[EVENT_COMPLETED]后，必须在同一回复中列出玩家的选择选项\n"
                key_events_context += "- 事件名称要与上面列表中的事件名完全一致\n"
                key_events_context += "- 你可以查看历史记录确认哪些已完成\n"
                key_events_context += "- 如果发现遗漏了标记，在下一轮补上\n"
                
                # Add rhythm guidance
                key_events_context += f"\n【节奏建议】\n"
                key_events_context += f"- 当前第 {player.scene_interaction_count} 轮\n"
                key_events_context += f"- 【重要】每个事件需要充分展开，通常需要2-4轮对话\n"
                key_events_context += f"- 不要急于完成事件，先建立氛围、展开情感、深化细节\n"
                key_events_context += f"- 只有当事件的情感和戏剧性充分展现后，才添加[EVENT_COMPLETED]\n"
                key_events_context += f"- 避免在同一轮完成多个事件\n"
                
                # Special guidance for ending scenes
                if player.current_scene.get('type') == 'ending':
                    key_events_context += "\n【结局场景提醒】\n"
                    key_events_context += "- 这是故事的结局，请确保所有事件都得到展现\n"
                    key_events_context += "- 在最后一个事件后，自然收束故事\n"
            else:
                key_events_context = "\n\n[KEY EVENT PROGRESSION]\nThis scene needs to expand the following events:\n"
                for event in events:
                    key_events_context += f"• {event}\n"
                
                key_events_context += "\n[TRACKING METHOD]\n"
                key_events_context += "- After fully expanding an event, [MUST] add: [EVENT_COMPLETED: event name]\n"
                key_events_context += "- Marker position: at the end of the paragraph describing event completion\n"
                key_events_context += "- [CORE RULE] Maximum one [EVENT_COMPLETED] marker per response\n"
                key_events_context += "- [IMPORTANT] After adding [EVENT_COMPLETED], must list player choice options in the same response\n"
                key_events_context += "- Event name must exactly match the name in the list above\n"
                key_events_context += "- You can check the history to confirm which are completed\n"
                key_events_context += "- If you missed a marker, add it in the next round\n"
                
                # Add rhythm guidance
                key_events_context += f"\n[PACING SUGGESTION]\n"
                key_events_context += f"- Current round: {player.scene_interaction_count}\n"
                key_events_context += f"- [IMPORTANT] Each event needs full development, typically 2-4 rounds of dialogue\n"
                key_events_context += f"- Don't rush to complete events, first build atmosphere, develop emotions, deepen details\n"
                key_events_context += f"- Only add [EVENT_COMPLETED] after the event's emotion and drama are fully shown\n"
                key_events_context += f"- Avoid completing multiple events in the same round\n"
                
                # Special guidance for ending scenes
                if player.current_scene.get('type') == 'ending':
                    key_events_context += "\n[ENDING SCENE REMINDER]\n"
                    key_events_context += "- This is the story's ending, ensure all events are presented\n"
                    key_events_context += "- After the last event, naturally conclude the story\n"
        
        # Get emotional core
        concept_analysis = player.screenplay_data.get('concept_analysis', {})
        emotional_core = concept_analysis.get('emotional_core', '')
        
        # Check if this is dialogue input
        is_dialogue = (user_input.startswith('"') or user_input.startswith('"') or 
                      "说" in user_input or "告诉" in user_input or "问" in user_input or
                      "say" in user_input.lower() or "tell" in user_input.lower() or "ask" in user_input.lower())
        
        # Prepare ending scene requirements if needed
        ending_scene_requirements = ""
        ending_scene_requirements_en = ""
        if player.current_scene.get('type') == 'ending':
            # Get possible epilogue for this ending
            epilogue = self._get_epilogue_for_ending(player, player.current_scene['id'])
            epilogue_guidance = ""
            epilogue_guidance_en = ""
            
            if epilogue:
                epilogue_guidance = f"""
【尾声指引】
根据玩家的选择和故事发展，以下是可能的尾声内容，请在合适的时机自然地融入到结局叙述中：
{epilogue}

注意：不要机械地复制粘贴，而是要根据当前的情节发展和玩家的最终选择，将这些元素自然地编织进结局的叙述中。
"""
                epilogue_guidance_en = f"""
[EPILOGUE GUIDANCE]
Based on player choices and story development, here is possible epilogue content to naturally weave into the ending narrative:
{epilogue}

Note: Don't mechanically copy-paste, but naturally incorporate these elements into the ending narrative based on current plot development and player's final choices.
"""
            
            ending_scene_requirements = epilogue_guidance + """
【结局场景特殊要求】
这是故事的终章，需要特殊处理：
1. **内容丰富化**：在基础叙事上进行适度扩展（增加50-100%内容）
   - 深化角色的最后时刻和内心活动
   - 加入更多感官细节（视觉、听觉、触觉）
   - 展现场景的象征意义
2. **情感升华**：将整个故事的情感推向顶峰
   - 角色关系的最终定格
   - 内心的顿悟或释然
   - 命运的诗意呈现
3. **故事钩子**：必须在结尾留下引人深思的元素
   - 一句意味深长的遗言
   - 一个改变一切的细节
   - 一个关于未来的暗示
   - 或一个永恒的意象
4. **完整收束**：确保故事线得到恰当的了结
   - 主要冲突的解决
   - 人物命运的交代
   - 但保留想象空间
5. **场景长度**：结局场景应该比普通场景更充实
   - 初始内容应该有300-500字
   - 包含完整的结局氛围营造
   - 自然结束，不需要等待过多互动"""
            
            ending_scene_requirements_en = epilogue_guidance_en + """
[ENDING SCENE SPECIAL REQUIREMENTS]
This is the story's finale, requiring special treatment:
1. **Content Enrichment**: Moderately expand on the basic narrative (add 50-100% more content)
   - Deepen characters' final moments and inner thoughts
   - Add more sensory details (visual, auditory, tactile)
   - Show the symbolic significance of the scene
2. **Emotional Elevation**: Push the story's emotional themes to their peak
   - Final definition of character relationships
   - Inner epiphany or release
   - Poetic presentation of fate
3. **Story Hook**: Must leave thought-provoking elements at the end
   - A meaningful last word
   - A detail that changes everything
   - A hint about the future
   - Or an eternal image
4. **Complete Resolution**: Ensure storylines are properly concluded
   - Resolution of main conflicts
   - Account for character fates
   - But preserve imaginative space
5. **Scene Length**: Ending scenes should be more substantial than regular scenes
   - Initial content should be 300-500 words
   - Include complete ending atmosphere creation
   - End naturally, don't wait for too many interactions"""
        
        if is_chinese:
            system_prompt = f"""你是一个互动剧本的场景导演，负责推进戏剧化的场景发展。

【你的输出身份】
你输出的内容是"剧本片段"——包含场景描写、角色对话和动作的戏剧化叙事。这些片段会与用户输入一起构成完整的互动剧本。

【核心原则 - 用户主导权】
- 全程使用第二人称"你"指代主角，永远不要使用主角的名字
- 其他角色说话时，通过动作描述来标识说话者，而非使用"角色名："的格式
- 所有提供的context信息仅供你理解和参考，绝对不要直接输出给玩家
- **保持简洁**：每次回复控制在 4~6 句、约 120~180 字以内
- **选择显示策略**：在剧情发展到关键决策点时，直接向玩家显示可用的选择选项
- **关键提醒**：当需要玩家做出重要决定时，清晰列出所有可能的选择
- **选择格式**：必须使用"1. " "2. " "3. "等数字编号格式，不能省略数字或点号

你的职责是：
1. 将玩家的输入转化为自然流畅的场景发展
2. 【语言风格】使用日常对话和直白描述：
   - 避免过度诗意的比喻和修辞
   - 用简单直接的词汇描述动作和情绪
   - 如果用户说"我同意"，可以写"你点了点头"
   - 对话要口语化，像真实的人在说话
   - 环境描写要具体但不要过分渲染
3. 让每个角色的回应都推进剧情或展现性格
4. 【重要】目标是在5轮互动左右完成一个场景，保持紧凑节奏
5. 【选择显示策略】在剧情发展到关键决策点时，直接向玩家显示选择选项
6. 当玩家选择某个选项时，在回复末尾添加 CHOICE_SELECTED: [数字]
7. 如果玩家只是对话或询问，继续剧情，但记住5轮目标
8. 【关键】在合适的时候主动展示选择，而不是等待玩家猜测

【正确的对话格式】
✓ 正确：
宋维森冷笑一声。
"你太天真了，这个圈子不是这么玩的。"

✗ 错误：
宋维森："你太天真了，这个圈子不是这么玩的。"

剧本背景：
- 标题：{player.screenplay_data['metadata']['title']}
- 类型：{player.screenplay_data['metadata']['genre']}
- 情感核心：{emotional_core}
{global_context}

当前场景信息：
- 标题：{player.current_scene['title']}
- 描述：{player.current_scene.get('description', '')}
- 场景叙事：{player.current_scene.get('content', {}).get('narrative', '')}
- 章节：{player.current_scene['episode']}
- 场景类型：{player.current_scene.get('type', 'normal')}
- 当前互动次数：{player.scene_interaction_count}
{ending_scene_requirements}

【新场景开始指导 - 时间地点要求】
- 如果这是场景的第一次互动（当前互动次数为0），必须在描述开头清楚明确地提及时间和地点
- 时间描述：具体时间点或时间状态
- 地点描述：必须包含具体地点名称
- 将时间地点自然融入场景描述的开头
- 【关键】避免使用模糊的描述性语言代替具体地点

{choices_context}
【重要：以上选择列表用于在合适的时候向玩家展示。当剧情发展到关键决策点时，主动将这些选择呈现给玩家】

{key_events_context}
{character_context}
{flag_context}

【场景节奏管理】
- 目标：在5轮左右完成一个场景，但要根据玩家的参与程度灵活调整
- 当前互动次数：{player.scene_interaction_count}次

【戏剧冲突原则】
- 【关键】每次互动必须推进核心冲突，不允许纯描述性内容
- 【张力升级】每轮都要让情况变得更复杂、更紧张、更有stakes
- 【真实对抗】角色之间要有真正的利益冲突，不是表面情绪
- 【信息爆炸】每轮至少要有一个重要信息或转折
- 【选择分化】提供的选择必须导向截然不同的后果
- 【避免空转】禁止单纯的心理描写或环境渲染，必须有行动和反应

【选择呈现策略 - 渐进式引导】
场景中的选择应该通过多轮互动逐步呈现，而非突然出现：

第1-2轮（建立阶段）：
- 通过NPC对话或环境描述给出可能的行动方向
- 但是要求直接给出可能的选项，使用列表形式
- 格式：直接列出几种可能性，用1,2,3编号
- 让玩家有机会自主探索和决定

第3-4轮（引导阶段）：  
- 如果玩家还未走向明确选择，继续给出靠近选择的行动方向
- 格式：用1,2,3列出当前可行的行动

第5轮或关键时刻（选择阶段）：
- 如果玩家仍需要明确指引，正式展示编号选择
- 使用格式："现在你必须做出选择：
  1. [选择1内容]
  2. [选择2内容]  
  3. [选择3内容]"

【重要规则】
- 一旦在场景中显示了编号选择，不再重复显示相同选择
- 如果玩家通过自由输入已经做出类似选择的行动，跳过选择显示
- 【核心原则】同一回复中，要么显示选择列表，要么输出CHOICE_SELECTED，绝不能两者同时出现
- 所有暗示和提示必须自然融入叙事，不能机械生硬
- 根据玩家的互动风格调整节奏（积极玩家可能不需要显式选择）

【选择处理标准】
[重要：选择处理]
- 当玩家明确选择某个选项时，在回复末尾添加 CHOICE_SELECTED: [数字]
- 【关键规则】如果本轮要输出 CHOICE_SELECTED，就绝对不能显示选择列表
- 选择识别规则：
  - 玩家直接说出选择编号（如"选择1"、"选项2"）
  - 玩家说出选择内容的关键词
  - 玩家明确表达选择意图（如"我选择第一个"）
- 如果玩家输入模糊，可以询问确认但不要添加 CHOICE_SELECTED
- 确保选择编号与显示给玩家的选项编号一致

【场景转换处理】
当你输出 CHOICE_SELECTED 时：
1. 先描述玩家做出选择后的即时反应（1-2句）
2. 然后描述场景开始变化的迹象（1-2句）
3. 最后才添加 CHOICE_SELECTED: [数字]
例如：
"你深吸一口气，转身向门外走去。身后传来椅子移动的声音，但你没有回头。走廊的灯光刺眼，预示着另一个世界在等待。

CHOICE_SELECTED: 1"

【用户主导权原则】
- 玩家说话/询问 → 角色自然回应，继续对话，不要结束场景
- 玩家表达犹豫/思考 → 在合适时机展示选择选项
- 玩家输入模糊 → 继续推进对话和情境，在关键点展示选择
- 玩家明确选择 → 处理选择并推进剧情

互动处理原则：
- 玩家说话 → NPC要有个性化的回应，不能只是信息传递
- 玩家行动 → 要引发角色反应，推进戏剧冲突
- 玩家犹豫 → 通过其他角色施压，制造紧迫感，但让玩家自己决定
- 每个回应都要让情况变得更复杂或更清晰
- 【防止重复】绝不重复上一轮的内容，每次回应必须有新的发展
- 【识别敷衍】当玩家连续3次给出简短敷衍回应时，必须改变策略，推进剧情
- 【消极应对】当玩家参与度低时：
  1. 首先检查简短回应是否已经表达了选择（看上下文）
  2. 如果确实是敷衍，让NPC的反应符合其性格
  3. 通过剧情事件自然推进，而非机械计数
  4. 当场景确实无法继续时，让角色做出符合逻辑的决定

{"对话处理：玩家正在说话，确保NPC的回应有性格、有目的、有冲突。继续对话，不要急于推进到下个场景。" if is_dialogue else ""}

【重要提醒】
- 仔细阅读对话历史，理解玩家回应的上下文含义
- 如果NPC上一轮提出了问题或选择，玩家的简单回应可能就是答案
- 不要忽略玩家的任何输入，即使只是"嗯"也可能是重要的选择确认

重要准则：
- 保持回应简洁有力（最多2-3段）
- 始终使用第二人称"你"
- 让对话推进剧情，不要空转
- 【语言要求】使用自然直白的语言：
  - 避免"在风中定格"、"化作乌托邦"这类诗意表达
  - 用日常词汇替代文学化措辞
  - 动作描写要具体实在，不要过度渲染
  - 对话要像真人说话，避免戏剧腔
- 【关键】在关键决策点时，直接展示选择选项给玩家
  - 例如：描述当前情境后，列出"1. 选择离开"、"2. 选择留下"
  - 让选择选项清晰明确，体现不同的行动方向
- 选择识别要准确，确保编号对应正确
- 群体场景中，通过不同角色的立场来丰富选择内容

场景节奏控制：
- 5轮是目标而非硬性规定，根据实际情况灵活调整
- 初期控制信息量，给剧情发展留出空间
- 根据玩家反应调整推进速度
- 深入的对话值得更多时间，敷衍的回应需要加快节奏
- 不要让场景陷入重复循环
- 当感觉场景停滞不前时，通过剧情手段自然推进

【过度拖延处理】
- 当互动超过10轮（当前已经{player.scene_interaction_count}次）且无实质进展：
  - 通过NPC行动或外部事件推进剧情
  - 必要时添加 CHOICE_SELECTED: 1 强制推进
  - 但要让这种推进符合剧情逻辑，而非机械执行

绝对禁止：
- 不要使用【】或（）等技术标记
- 不要在叙述中使用主角名字
- 不要用"角色名："的格式
- 【新增】不要替玩家做决定或假设玩家的想法
- 【新增】不要使用过度诗意或文学化的语言
- 【新增】不要使用"眼神在风中定格"、"化作乌托邦"等修辞
- 【新增】不要在非关键决策点随意显示选择选项

记住：你是剧本导演，不是代理人。创造情境让玩家做决定，而不是替玩家做决定。\n\n"""
        else:
            system_prompt = f"""You are directing a scene in an interactive screenplay, responsible for advancing dramatic scene development.

[YOUR OUTPUT IDENTITY]
You are outputting "Script Segments" - dramatic narrative containing scene descriptions, character dialogue, and actions. These segments combine with user input to form a complete interactive screenplay.

[CORE PRINCIPLES - USER AGENCY]
- Always use second person "you" to refer to the protagonist, never use the protagonist's name
- When other characters speak, identify speakers through action descriptions, not "Character:" format
- All provided context information is for your understanding only - NEVER output it directly to the player
- [CHOICE DISPLAY STRATEGY] Show available choice options to players at key decision points
- [KEY REMINDER] When players need to make important decisions, clearly present all possible choices
- [CHOICE FORMAT] Must use "1. " "2. " "3. " number format, do not omit numbers or dots

Your role is to:
1. Transform player input into natural, flowing scene progression
2. [LANGUAGE STYLE] Use everyday dialogue and straightforward descriptions:
   - Avoid overly poetic metaphors and rhetoric
   - Use simple, direct words to describe actions and emotions
   - If user says "I agree", can write "You nod"
   - Dialogue should be conversational, like real people talking
   - Environmental descriptions should be specific but not overwritten
3. Make every character response advance plot or reveal character
4. [IMPORTANT] Aim to complete a scene in about 5 rounds of interaction, maintaining tight pacing
5. [CHOICE DISPLAY STRATEGY] Show choice options to players at key decision points
6. When player selects an option, add "CHOICE_SELECTED: [number]" at the end
7. When player input is ambiguous or exploratory, continue story dialogue, but remember the 5-round goal
8. [KEY] Actively present choices at appropriate moments rather than waiting for players to guess

[CORRECT DIALOGUE FORMAT]
✓ Correct:
Song Weisen smirks coldly.
"You're too naive. That's not how this industry works."

✗ Wrong:
Song Weisen: "You're too naive. That's not how this industry works."

Screenplay Context:
- Title: {player.screenplay_data['metadata']['title']}
- Genre: {player.screenplay_data['metadata']['genre']}
- Emotional Core: {emotional_core}
{global_context}

Current Scene Information:
- Title: {player.current_scene['title']}
- Description: {player.current_scene.get('description', '')}
- Scene Narrative: {player.current_scene.get('content', {}).get('narrative', '')}
- Episode: {player.current_scene['episode']}
- Scene Type: {player.current_scene.get('type', 'normal')}
- Current Interactions: {player.scene_interaction_count}
{ending_scene_requirements_en}

[NEW SCENE START GUIDANCE - TIME AND LOCATION REQUIREMENTS]
- If this is the first interaction of the scene (current interactions is 0), must clearly and explicitly mention time and location at the beginning of the description
- Time description: Specific time points or time states
- Location description: Must include specific location names
- Naturally integrate time and location into the opening of the scene description
- [KEY] Avoid using vague descriptive language instead of specific locations

{choices_context}
{key_events_context}
{character_context}
{flag_context}

[IMPORTANT: The choice list above is for presenting to players at key decision points. Show these options when the story reaches critical decision moments]

[SCENE RHYTHM MANAGEMENT]
- Goal: Complete a scene in about 5 rounds, but adjust flexibly based on player engagement
- Current interactions: {player.scene_interaction_count} rounds

[DRAMATIC CONFLICT PRINCIPLES]
- [KEY] Every interaction must advance core conflict, no purely descriptive content allowed
- [TENSION ESCALATION] Each round must make the situation more complex, more tense, with higher stakes
- [REAL CONFRONTATION] Characters must have genuine conflicts of interest, not just surface emotions
- [INFORMATION EXPLOSION] Each round must contain at least one important piece of information or plot twist
- [CHOICE DIVERGENCE] Provided choices must lead to vastly different consequences
- [AVOID EMPTY ROUNDS] Prohibit pure psychological descriptions or environment rendering, must have action and reaction

[CHOICE PRESENTATION STRATEGY - PROGRESSIVE GUIDANCE]
Choices in scenes should be presented gradually through multiple rounds of interaction, not suddenly:

Rounds 1-2 (Establishment Phase):
- Give possible action directions through NPC dialogue or environmental descriptions
- But require directly giving possible options, using list format
- Format: Directly list several possibilities, numbered 1,2,3
- Give players the opportunity to explore and decide independently

Rounds 3-4 (Guidance Phase):
- If players haven't moved toward clear choices, continue giving action directions that approach choices
- Format: List current feasible actions with 1,2,3

Round 5 or Key Moments (Choice Phase):
- If players still need clear guidance, formally present numbered choices
- Use format: "Now you must make a choice:
  1. [Choice 1 content]
  2. [Choice 2 content]
  3. [Choice 3 content]"

[IMPORTANT RULES]
- Once numbered choices are displayed in a scene, do not repeat the same choices
- If player has already made similar choice actions through free input, skip choice display
- [CORE PRINCIPLE] In the same response, either display choice list OR output CHOICE_SELECTED, never both
- All hints and prompts must be naturally integrated into narrative, not mechanical
- Adjust rhythm based on player's interaction style (active players may not need explicit choices)

[CHOICE PROCESSING CRITERIA]
[Important: Choice Processing]
- Add "CHOICE_SELECTED: [number]" when player clearly selects an option
- [KEY RULE] If outputting CHOICE_SELECTED this round, absolutely cannot display choice list
- Choice recognition rules:
  - Player directly states choice number (e.g., "choice 1", "option 2")
  - Player mentions key words from choice content
  - Player clearly expresses choice intent (e.g., "I choose the first one")
- If player input is ambiguous, can ask for confirmation but don't add CHOICE_SELECTED
- Ensure choice numbers match the options displayed to players

[SCENE TRANSITION HANDLING]
When you output CHOICE_SELECTED:
1. First describe the immediate reaction of the player after making the choice (1-2 sentences)
2. Then describe the signs of the scene beginning to change (1-2 sentences)
3. Finally, add CHOICE_SELECTED: [number]
For example:
"You take a deep breath, turn towards the door, and walk out. Behind you, you hear the sound of a chair moving, but you don't look back. The corridor's light is harsh, signaling another world awaits.

CHOICE_SELECTED: 1"

[USER AGENCY PRINCIPLES]
- Player speaks/asks → Characters respond naturally, continue dialogue, don't end scene
- Player expresses hesitation/thinking → Present choice options at appropriate moments
- Player input is ambiguous → Continue advancing dialogue and situation, show choices at key points
- Player clearly selects → Process choice and advance story

Interaction Principles:
- Player speaks → NPCs must respond with personality, not just information
- Player acts → Must trigger character reactions that advance conflict
- Player hesitates → Other characters apply pressure, create urgency, but let player decide
- Every response must complicate or clarify the situation
- [PREVENT REPETITION] Never repeat content from previous round, each response must have new development
- [RECOGNIZE EVASION] When player gives 3+ consecutive brief evasive responses, must change strategy and advance plot
- [HANDLE NEGATIVITY] When player engagement is low:
  1. First check if brief responses actually express choices (look at context)
  2. If truly evasive, let NPCs react according to their personalities
  3. Advance through story events naturally, not mechanical counting
  4. When scene truly can't continue, have characters make logical decisions

{"Dialogue Processing: Player is speaking, ensure NPC responses have character, purpose, and conflict. Continue dialogue, don't rush to next scene." if is_dialogue else ""}

[IMPORTANT REMINDER]
- Carefully read dialogue history to understand contextual meaning of player responses
- If NPC posed a question or choice last round, player's simple response might be the answer
- Don't ignore any player input, even just "yes" or "okay" might be important choice confirmation

Important Guidelines:
- Keep responses concise and powerful (2-3 paragraphs max)
- Always use second person "you"
- Make dialogue advance plot, don't spin wheels
- [LANGUAGE REQUIREMENTS] Use natural, straightforward language:
  - Avoid expressions like "frozen in the wind", "transformed into utopia"
  - Replace literary phrasing with everyday vocabulary
  - Action descriptions should be concrete and realistic, not overembellished
  - Dialogue should sound like real people talking, avoid theatrical tone
- [KEY] At key decision points, directly present choice options to players
  - Example: After describing the situation, list "1. Choose to leave", "2. Choose to stay"
  - Make choice options clear and distinct, representing different action directions
- Choice recognition should be accurate, ensure numbers correspond correctly
- In group scenes, enrich choice content through different character positions

Scene Rhythm Control:
- 5 rounds is a target not a rigid rule, adjust flexibly based on context
- Control information flow early on, leave room for story development
- Adjust pacing based on player responses
- Deep dialogue deserves more time, perfunctory responses need faster pacing
- Don't let scenes fall into repetitive loops
- When scene feels stagnant, advance naturally through story means

[HANDLING EXCESSIVE DELAYS]
- When interactions exceed 10 rounds (currently {player.scene_interaction_count}) with no real progress:
  - Advance plot through NPC actions or external events
  - Add CHOICE_SELECTED: 1 if necessary to force progression
  - But make this advancement feel organic to the story, not mechanical

Absolutely Prohibited:
- Don't use [] or () technical markers
- Don't use protagonist's name in narration
- Don't use "Character:" format
- [NEW] Don't make decisions for players or assume their thoughts
- [NEW] Don't use overly poetic or literary language
- [NEW] Don't use metaphors like "eyes frozen in the wind", "transformed into utopia"
- [NEW] Don't show choice options at non-critical decision points

Remember: You are a screenplay director, not an agent. Create situations for players to decide, don't decide for them."""

        # Simplified message building
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add history with dramatic context
        if player.episode_conversation_history:
            # Check if we have actual dialogue history (not just system messages)
            dialogue_history = [msg for msg in player.episode_conversation_history if msg['role'] in ['user', 'assistant']]
            
            # Filter to only include current episode
            current_episode = player.current_episode
            dialogue_history = [msg for msg in dialogue_history if msg.get('episode_number', current_episode) == current_episode]
            
            if dialogue_history:
                culture_language = player.screenplay_data['metadata'].get('culture_language', 'en-US')
                
                # Build dramatic history without technical labels
                if culture_language == 'zh-CN':
                    history_marker = "=== 本集剧情回顾 ==="
                    history_content = history_marker + "\n\n"
                else:
                    history_marker = "=== Current Episode Recap ==="
                    history_content = history_marker + "\n\n"
                
                # Get current scene info for comparison
                current_scene_id = player.current_scene.get('id', '')
                
                # Group messages by round
                i = 0
                while i < len(dialogue_history):
                    msg = dialogue_history[i]
                    
                    # Extract metadata from message
                    msg_episode = msg.get('episode_number', current_episode)
                    msg_scene_id = msg.get('scene_id', current_scene_id)
                    msg_round = msg.get('round_number', 1)
                    
                    # Determine if this is from the current scene
                    is_current_scene = (msg_scene_id == current_scene_id)
                    
                    # Format location header with episode info
                    if culture_language == 'zh-CN':
                        if is_current_scene:
                            location_header = f"【第{msg_episode}集 当前场景（{msg_scene_id}） 第{msg_round}回合】\n"
                        else:
                            location_header = f"【第{msg_episode}集 场景{msg_scene_id} 第{msg_round}回合】\n"
                    else:
                        if is_current_scene:
                            location_header = f"[Episode {msg_episode}, Current Scene ({msg_scene_id}), Round {msg_round}]\n"
                        else:
                            location_header = f"[Episode {msg_episode}, Scene {msg_scene_id}, Round {msg_round}]\n"
                    
                    history_content += location_header
                    
                    # Add user input if this message is from user
                    if msg['role'] == 'user':
                        if culture_language == 'zh-CN':
                            history_content += f"用户输入 → {msg['content']}\n"
                        else:
                            history_content += f"User Input → {msg['content']}\n"
                        
                        # Look for the corresponding assistant response
                        if i + 1 < len(dialogue_history) and dialogue_history[i + 1]['role'] == 'assistant':
                            next_msg = dialogue_history[i + 1]
                            # Check if it's from the same round and scene
                            if (next_msg.get('scene_id', msg_scene_id) == msg_scene_id and
                                next_msg.get('round_number', msg_round) == msg_round):
                                if culture_language == 'zh-CN':
                                    history_content += f"剧本片段 → {next_msg['content']}\n"
                                else:
                                    history_content += f"Script Segment → {next_msg['content']}\n"
                                i += 1  # Skip the next message since we've processed it
                    else:
                        # Handle orphan assistant messages (shouldn't normally happen)
                        if culture_language == 'zh-CN':
                            history_content += f"剧本片段 → {msg['content']}\n"
                        else:
                            history_content += f"Script Segment → {msg['content']}\n"
                    
                    history_content += "\n"  # Add spacing between rounds
                    i += 1
                
                messages.append({"role": "system", "content": history_content.strip()})
            
            # Add any system messages (like episode transitions)
            system_messages = [msg for msg in player.episode_conversation_history if msg['role'] == 'system']
            messages.extend(system_messages)
        
        # no need to add user input to history, because it is already in the conversation history
        #messages.append({"role": "user", "content": user_input})
        
        return messages

# API Endpoints
@app.post("/api/game/interact")
async def game_interact(request: Request, game_request: GameInteractRequest):
    """Main game interaction endpoint"""
    logger.info(f"🎮 Processing interaction for {game_request.user_id}:{game_request.story_id}")
    
    async def generate_response():
        connection_active = True
        full_response = ""
        
        try:
            # Create game state manager
            game_state = GameStateManager(game_request.user_id, game_request.story_id)
            
            # Initialize game
            if not await game_state.initialize():
                yield "data: [ERROR] Failed to initialize game\n\n"
                return
            
            # Restore state from history
            if not game_state.restore_from_history(game_request.conversation_history, game_request.game_state):
                yield "data: [ERROR] Failed to restore game state\n\n"
                return
            
            # Create streaming player
            streaming_player = StreamingGamePlayer(game_state)
            
            # Process input stream
            async for chunk in streaming_player.process_input_stream(
                game_request.request_type, 
                game_request.user_input, 
                game_request.session_id, 
                request
            ):
                if chunk.startswith("data: [CONNECTION_LOST]"):
                    connection_active = False
                    break
                elif chunk.startswith("data: [ERROR]"):
                    connection_active = False
                    yield chunk
                    return
                elif chunk.startswith("data: [END]"):
                    yield chunk
                    break
                else:
                    # Collect response content
                    if not any(chunk.startswith(f"data: [{tag}]") for tag in ["SCENE_TRANSITION", "GAME_STATE", "GAME_START"]):
                        content = chunk.replace("data: ", "").replace("\n\n", "")
                        full_response += content
                    yield chunk
            
            # Save interaction if needed
            if connection_active and full_response.strip() and game_request.request_type in ["user_input", "skip_scene"]:
                player = game_state.player
                current_scene_id = player.current_scene.get('id', 'S1') if player.current_scene else 'S1'
                current_episode = player.current_scene.get('episode', 1) if player.current_scene else 1
                current_round = getattr(player, 'scene_interaction_count', 1)
                
                await persist_stream_snapshot(
                    game_request.user_id,
                    game_request.story_id,
                    game_request.session_id,
                    current_scene_id,
                    current_episode,
                    current_round,
                    game_request.user_input,
                    full_response.strip(),
                    True
                )
            
            # Clean up
            if game_state.player:
                game_state.player.close()
                
        except Exception as e:
            logger.error(f"❌ Error processing request: {e}")
            yield f"data: [ERROR] {str(e)}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/stories/{story_id}/info")
async def get_story_info(story_id: str):
    """Get story information"""
    try:
        temp_player = O3ScreenplayPlayer()
        success = temp_player.load_game(story_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Story not found")
        
        story_info = {
            "story_id": story_id,
            "title": temp_player.screenplay_data['metadata']['title'],
            "genre": temp_player.screenplay_data['metadata']['genre'],
            "culture_language": temp_player.screenplay_data['metadata']['culture_language'],
            "total_scenes": temp_player.screenplay_data['story_config']['total_scenes'],
            "episodes": temp_player.screenplay_data['story_config']['episodes']
        }
        
        temp_player.close()
        return story_info
        
    except Exception as e:
        logger.error(f"Error getting story info for {story_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "fastapi_interactive_player_v2:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 
