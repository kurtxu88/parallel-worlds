import os
import uuid
from contextlib import contextmanager
from typing import Any, Generator

import psycopg
from psycopg.rows import dict_row


DEFAULT_DATABASE_URL = "postgresql://parallel_worlds:parallel_worlds@localhost:5432/parallel_worlds"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


@contextmanager
def get_connection() -> Generator[psycopg.Connection[Any], None, None]:
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def create_guest_user() -> dict[str, Any]:
    user_id = uuid.uuid4()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO guest_users (id)
                VALUES (%s)
                RETURNING id, created_at
                """,
                (user_id,),
            )
            guest = cur.fetchone()
            cur.execute(
                """
                INSERT INTO user_settings (user_id, language, theme)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
                """,
                (user_id, "en-US", "system"),
            )
        conn.commit()
    return guest


def ensure_guest_user(user_id: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO guest_users (id)
                VALUES (%s)
                ON CONFLICT (id) DO NOTHING
                """,
                (user_id,),
            )
            cur.execute(
                """
                INSERT INTO user_settings (user_id, language, theme)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
                """,
                (user_id, "en-US", "system"),
            )
        conn.commit()


def get_or_create_settings(user_id: str) -> dict[str, Any]:
    ensure_guest_user(user_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, language, theme, created_at, updated_at
                FROM user_settings
                WHERE user_id = %s
                """,
                (user_id,),
            )
            settings = cur.fetchone()
        conn.commit()
    return settings


def update_settings(user_id: str, language: str | None, theme: str | None) -> dict[str, Any]:
    current = get_or_create_settings(user_id)
    next_language = language or current["language"]
    next_theme = theme or current["theme"]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE user_settings
                SET language = %s,
                    theme = %s,
                    updated_at = NOW()
                WHERE user_id = %s
                RETURNING user_id, language, theme, created_at, updated_at
                """,
                (next_language, next_theme, user_id),
            )
            settings = cur.fetchone()
        conn.commit()
    return settings


def list_stories(user_id: str) -> list[dict[str, Any]]:
    ensure_guest_user(user_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id,
                       s.story_id,
                       s.user_id,
                       s.story_title,
                       s.user_input,
                       s.gender_preference,
                       s.culture_language,
                       s.status,
                       s.error_message,
                       s.created_at,
                       s.updated_at,
                       (
                         SELECT MAX(created_at)
                         FROM story_events e
                         WHERE e.story_id = s.id
                       ) AS last_entered_at
                FROM stories s
                WHERE s.user_id = %s
                ORDER BY s.created_at DESC
                """,
                (user_id,),
            )
            stories = cur.fetchall()
        conn.commit()
    return stories


def create_story(
    user_id: str,
    user_input: str,
    gender_preference: str,
    culture_language: str,
) -> dict[str, Any]:
    ensure_guest_user(user_id)
    story_id = uuid.uuid4()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO stories (
                    id,
                    story_id,
                    user_id,
                    user_input,
                    gender_preference,
                    culture_language,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id,
                          story_id,
                          user_id,
                          story_title,
                          user_input,
                          gender_preference,
                          culture_language,
                          status,
                          error_message,
                          created_at,
                          updated_at
                """,
                (
                    story_id,
                    story_id,
                    user_id,
                    user_input,
                    gender_preference,
                    culture_language,
                    "pending",
                ),
            )
            story = cur.fetchone()
        conn.commit()
    return story


def get_story(user_id: str, story_id: str) -> dict[str, Any] | None:
    ensure_guest_user(user_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id,
                       s.story_id,
                       s.user_id,
                       s.story_title,
                       s.user_input,
                       s.gender_preference,
                       s.culture_language,
                       s.status,
                       s.error_message,
                       s.created_at,
                       s.updated_at,
                       (
                         SELECT MAX(created_at)
                         FROM story_events e
                         WHERE e.story_id = s.id
                       ) AS last_entered_at
                FROM stories s
                WHERE s.id = %s
                  AND s.user_id = %s
                """,
                (story_id, user_id),
            )
            story = cur.fetchone()
        conn.commit()
    return story


def retry_story(user_id: str, story_id: str) -> dict[str, Any] | None:
    ensure_guest_user(user_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE stories
                SET status = 'pending',
                    error_message = NULL,
                    story_title = NULL,
                    updated_at = NOW()
                WHERE id = %s
                  AND user_id = %s
                RETURNING id,
                          story_id,
                          user_id,
                          story_title,
                          user_input,
                          gender_preference,
                          culture_language,
                          status,
                          error_message,
                          created_at,
                          updated_at
                """,
                (story_id, user_id),
            )
            story = cur.fetchone()
        conn.commit()
    return story


def list_story_events(user_id: str, story_id: str) -> list[dict[str, Any]]:
    ensure_guest_user(user_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id,
                       user_id,
                       story_id,
                       session_id,
                       scene_id,
                       episode_number,
                       round_number,
                       event_type,
                       content,
                       created_at
                FROM story_events
                WHERE story_id = %s
                  AND user_id = %s
                ORDER BY created_at ASC
                """,
                (story_id, user_id),
            )
            events = cur.fetchall()
        conn.commit()
    return events


def save_story_interaction(
    user_id: str,
    story_id: str,
    session_id: str,
    scene_id: str,
    episode_number: int,
    round_number: int,
    user_input: str,
    ai_response: str,
) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            if user_input.strip():
                cur.execute(
                    """
                    INSERT INTO story_events (
                        user_id,
                        story_id,
                        session_id,
                        scene_id,
                        episode_number,
                        round_number,
                        event_type,
                        content
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        story_id,
                        session_id,
                        scene_id,
                        episode_number,
                        round_number,
                        "user_input",
                        user_input,
                    ),
                )

            if ai_response.strip():
                cur.execute(
                    """
                    INSERT INTO story_events (
                        user_id,
                        story_id,
                        session_id,
                        scene_id,
                        episode_number,
                        round_number,
                        event_type,
                        content
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        story_id,
                        session_id,
                        scene_id,
                        episode_number,
                        round_number,
                        "ai_response",
                        ai_response,
                    ),
                )

            cur.execute(
                """
                UPDATE stories
                SET updated_at = NOW()
                WHERE id = %s
                  AND user_id = %s
                """,
                (story_id, user_id),
            )
        conn.commit()
