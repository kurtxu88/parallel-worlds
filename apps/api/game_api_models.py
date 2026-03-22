#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Game API Data Models - Pydantic models for FastAPI game interaction
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class ConversationMessage(BaseModel):
    """对话消息模型"""
    role: str = Field(..., description="消息角色: user/assistant")
    content: str = Field(..., description="消息内容")
    timestamp: Optional[datetime] = Field(None, description="时间戳")

class GameState(BaseModel):
    """游戏状态模型"""
    current_scene: Optional[Dict[str, Any]] = Field(None, description="当前场景数据")
    current_episode: Optional[int] = Field(None, description="当前章节")
    scene_interaction_count: Optional[int] = Field(0, description="场景交互次数")
    story_flags: Optional[Dict[str, Any]] = Field({}, description="故事标志位")
    scene_history: Optional[List[str]] = Field([], description="访问过的场景历史")
    available_choices: Optional[List[Dict]] = Field([], description="当前可用选择")

class GameInteractRequest(BaseModel):
    """游戏交互请求模型"""
    user_id: str = Field(..., description="用户ID")
    story_id: str = Field(..., description="故事ID")
    request_type: str = Field(..., description="请求类型: game_start/user_input")
    user_input: str = Field("", description="用户输入（游戏开始时可为空）")
    session_id: str = Field(..., description="游戏会话ID")
    conversation_history: List[ConversationMessage] = Field([], description="对话历史")
    game_state: Optional[GameState] = Field(None, description="当前游戏状态")

class GameInteractResponse(BaseModel):
    """游戏交互响应模型"""
    success: bool = Field(..., description="请求是否成功")
    message: str = Field(..., description="响应消息")
    new_game_state: Optional[GameState] = Field(None, description="更新后的游戏状态")
    saved_to_database: bool = Field(False, description="是否已保存到数据库")

class StreamChunk(BaseModel):
    """流式响应块模型"""
    type: str = Field(..., description="块类型: content/state/error/end")
    content: str = Field("", description="内容")
    game_state: Optional[GameState] = Field(None, description="游戏状态更新")
    
class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: bool = Field(True, description="是否为错误")
    message: str = Field(..., description="错误消息")
    code: Optional[str] = Field(None, description="错误代码") 