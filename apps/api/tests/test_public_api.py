from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import BaseModel


API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def install_test_stubs() -> None:
    # The API module imports the runtime DB and gameplay modules at import time.
    # These lightweight stubs keep endpoint tests isolated from external services.
    db_stub = types.ModuleType("db")

    def _default_record(*args, **kwargs):
        return None

    db_stub.create_guest_user = _default_record
    db_stub.create_story = _default_record
    db_stub.get_public_story = _default_record
    db_stub.get_or_create_settings = _default_record
    db_stub.get_story = _default_record
    db_stub.list_public_stories = lambda limit=24: []
    db_stub.list_public_story_events = lambda story_id: []
    db_stub.list_stories = lambda user_id: []
    db_stub.list_story_events = lambda user_id, story_id: []
    db_stub.retry_story = _default_record
    db_stub.save_story_interaction = lambda **kwargs: None
    db_stub.set_story_visibility = _default_record
    db_stub.update_settings = _default_record
    sys.modules["db"] = db_stub

    gameplay_stub = types.ModuleType("fastapi_interactive_player_v2")

    class ConversationMessage(BaseModel):
        role: str = "user"
        content: str = ""

    class GameState(BaseModel):
        pass

    class GameStateManager:
        def __init__(self, *args, **kwargs):
            self.player = None

        async def initialize(self):
            return True

        def restore_from_history(self, *args, **kwargs):
            return True

    class StreamingGamePlayer:
        def __init__(self, *args, **kwargs):
            pass

        async def process_input_stream(self, *args, **kwargs):
            if False:
                yield ""

    gameplay_stub.ConversationMessage = ConversationMessage
    gameplay_stub.GameState = GameState
    gameplay_stub.GameStateManager = GameStateManager
    gameplay_stub.StreamingGamePlayer = StreamingGamePlayer
    sys.modules["fastapi_interactive_player_v2"] = gameplay_stub


install_test_stubs()

import main  # noqa: E402


def build_public_story(story_id: str = "story-1", is_public: bool = True) -> dict:
    return {
        "id": story_id,
        "story_id": story_id,
        "story_title": "Signal Market",
        "user_input": "A floating market keeps trading memories as currency.",
        "gender_preference": "female",
        "culture_language": "en-US",
        "is_public": is_public,
        "status": "completed",
        "error_message": None,
        "created_at": "2026-03-22T08:00:00Z",
        "updated_at": "2026-03-22T08:10:00Z",
        "last_entered_at": "2026-03-22T08:11:00Z",
        "event_count": 4,
        "preview_excerpt": "The market lights wake as the tide of memories rises."
    }


class PublicApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(main.app)

    def test_list_public_stories_passes_limit_to_storage_layer(self):
        with patch.object(main, "list_public_stories", return_value=[build_public_story()]) as mock_list:
            response = self.client.get("/api/public/stories?limit=9")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["id"], "story-1")
        mock_list.assert_called_once_with(9)

    def test_list_public_stories_rejects_invalid_limit(self):
        response = self.client.get("/api/public/stories?limit=0")

        self.assertEqual(response.status_code, 422)

    def test_update_story_visibility_forwards_user_and_payload(self):
        with patch.object(
            main,
            "set_story_visibility",
            return_value=build_public_story(is_public=True)
        ) as mock_visibility:
            response = self.client.patch(
                "/api/stories/story-1/visibility",
                headers={"X-User-Id": "guest-123"},
                json={"is_public": True}
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_public"])
        mock_visibility.assert_called_once_with("guest-123", "story-1", True)

    def test_update_story_visibility_returns_404_when_story_is_missing(self):
        with patch.object(main, "set_story_visibility", return_value=None):
            response = self.client.patch(
                "/api/stories/missing-story/visibility",
                headers={"X-User-Id": "guest-123"},
                json={"is_public": True}
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Story not found")

    def test_public_story_returns_404_when_story_is_not_public(self):
        with patch.object(main, "get_public_story", return_value=None):
            response = self.client.get("/api/public/stories/private-story")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Public story not found")

    def test_public_story_events_return_transcript_for_public_story(self):
        with patch.object(main, "get_public_story", return_value=build_public_story()) as mock_story:
            with patch.object(
                main,
                "list_public_story_events",
                return_value=[
                    {
                        "id": "event-1",
                        "story_id": "story-1",
                        "scene_id": "S1",
                        "episode_number": 1,
                        "round_number": 1,
                        "event_type": "ai_response",
                        "content": "A bell rings across the market.",
                        "created_at": "2026-03-22T08:12:00Z"
                    }
                ]
            ) as mock_events:
                response = self.client.get("/api/public/stories/story-1/events")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["event_type"], "ai_response")
        mock_story.assert_called_once_with("story-1")
        mock_events.assert_called_once_with("story-1")
