from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from db import (
    create_guest_user,
    create_story,
    get_public_story,
    get_or_create_settings,
    get_story,
    list_public_story_events,
    list_stories,
    list_story_events,
    retry_story,
    save_story_interaction,
    set_story_visibility,
    update_settings,
)
from fastapi_interactive_player_v2 import (
    ConversationMessage,
    GameState,
    GameStateManager,
    StreamingGamePlayer,
)


app = FastAPI(title="Parallel Worlds API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GuestSessionResponse(BaseModel):
    user_id: str


class StoryCreateRequest(BaseModel):
    user_input: str
    gender_preference: str = "male"
    culture_language: str = "en-US"
    is_public: bool = False


class SettingsUpdateRequest(BaseModel):
    language: Optional[str] = None
    theme: Optional[str] = None


class StoryVisibilityRequest(BaseModel):
    is_public: bool


class GameInteractRequest(BaseModel):
    user_id: str
    story_id: str
    session_id: str
    request_type: str
    user_input: str = ""
    conversation_history: list[ConversationMessage] = []
    game_state: Optional[GameState] = None


def require_user_id(x_user_id: str | None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
    return x_user_id


def ensure_story_access(user_id: str, story_id: str) -> dict:
    story = get_story(user_id, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@app.post("/api/session/guest", response_model=GuestSessionResponse)
async def create_guest_session():
    guest = create_guest_user()
    return {"user_id": str(guest["id"])}


@app.get("/api/settings")
async def read_settings(x_user_id: str | None = Header(default=None)):
    user_id = require_user_id(x_user_id)
    settings = get_or_create_settings(user_id)
    return settings


@app.put("/api/settings")
async def write_settings(
    payload: SettingsUpdateRequest,
    x_user_id: str | None = Header(default=None),
):
    user_id = require_user_id(x_user_id)
    settings = update_settings(user_id, payload.language, payload.theme)
    return settings


@app.get("/api/stories")
async def read_stories(x_user_id: str | None = Header(default=None)):
    user_id = require_user_id(x_user_id)
    return list_stories(user_id)


@app.post("/api/stories")
async def write_story(
    payload: StoryCreateRequest,
    x_user_id: str | None = Header(default=None),
):
    user_id = require_user_id(x_user_id)
    story = create_story(
        user_id=user_id,
        user_input=payload.user_input.strip(),
        gender_preference=payload.gender_preference,
        culture_language=payload.culture_language,
        is_public=payload.is_public,
    )
    return story


@app.get("/api/stories/{story_id}")
async def read_story(story_id: str, x_user_id: str | None = Header(default=None)):
    user_id = require_user_id(x_user_id)
    return ensure_story_access(user_id, story_id)


@app.post("/api/stories/{story_id}/retry")
async def retry_story_generation(
    story_id: str,
    x_user_id: str | None = Header(default=None),
):
    user_id = require_user_id(x_user_id)
    story = retry_story(user_id, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@app.patch("/api/stories/{story_id}/visibility")
async def write_story_visibility(
    story_id: str,
    payload: StoryVisibilityRequest,
    x_user_id: str | None = Header(default=None),
):
    user_id = require_user_id(x_user_id)
    story = set_story_visibility(user_id, story_id, payload.is_public)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@app.get("/api/stories/{story_id}/events")
async def read_story_events(
    story_id: str,
    x_user_id: str | None = Header(default=None),
):
    user_id = require_user_id(x_user_id)
    ensure_story_access(user_id, story_id)
    return list_story_events(user_id, story_id)


@app.get("/api/public/stories/{story_id}")
async def read_public_story(story_id: str):
    story = get_public_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Public story not found")
    return story


@app.get("/api/public/stories/{story_id}/events")
async def read_public_story_events(story_id: str):
    story = get_public_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Public story not found")
    return list_public_story_events(story_id)


@app.post("/api/game/interact")
async def game_interact(
    request: Request,
    game_request: GameInteractRequest,
    x_user_id: str | None = Header(default=None),
):
    user_id = require_user_id(x_user_id)
    if user_id != game_request.user_id:
        raise HTTPException(status_code=400, detail="User header/body mismatch")

    ensure_story_access(user_id, game_request.story_id)

    async def generate_response():
        connection_active = True
        full_response = ""

        try:
            game_state = GameStateManager(game_request.user_id, game_request.story_id)

            if not await game_state.initialize():
                yield "data: [ERROR] Failed to initialize game\n\n"
                return

            if not game_state.restore_from_history(
                game_request.conversation_history,
                game_request.game_state,
            ):
                yield "data: [ERROR] Failed to restore game state\n\n"
                return

            streaming_player = StreamingGamePlayer(game_state)

            async for chunk in streaming_player.process_input_stream(
                game_request.request_type,
                game_request.user_input,
                game_request.session_id,
                request,
            ):
                if chunk.startswith("data: [CONNECTION_LOST]"):
                    connection_active = False
                    break
                if chunk.startswith("data: [ERROR]"):
                    connection_active = False
                    yield chunk
                    return
                if chunk.startswith("data: [END]"):
                    yield chunk
                    break

                if not any(
                    chunk.startswith(f"data: [{tag}]")
                    for tag in ["SCENE_TRANSITION", "GAME_STATE", "GAME_START"]
                ):
                    full_response += chunk.replace("data: ", "").replace("\n\n", "")
                yield chunk

            if connection_active and full_response.strip():
                player = game_state.player
                current_scene_id = player.current_scene.get("id", "S1") if player.current_scene else "S1"
                current_episode = player.current_scene.get("episode", 1) if player.current_scene else 1
                current_round = getattr(player, "scene_interaction_count", 0)

                save_story_interaction(
                    user_id=game_request.user_id,
                    story_id=game_request.story_id,
                    session_id=game_request.session_id,
                    scene_id=current_scene_id,
                    episode_number=current_episode,
                    round_number=current_round,
                    user_input=game_request.user_input,
                    ai_response=full_response.strip(),
                )

            if game_state.player:
                game_state.player.close()

        except Exception as exc:
            yield f"data: [ERROR] {str(exc)}\n\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
