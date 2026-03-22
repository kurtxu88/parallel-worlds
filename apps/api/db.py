import os
import uuid
from contextlib import contextmanager
from typing import Any, Generator

import psycopg
from psycopg.rows import dict_row


DEFAULT_DATABASE_URL = "postgresql://parallel_worlds:parallel_worlds@localhost:5432/parallel_worlds"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
_story_schema_ready = False


def ensure_story_schema() -> None:
    global _story_schema_ready

    if _story_schema_ready:
        return

    conn = psycopg.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                ALTER TABLE stories
                ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_stories_is_public
                ON stories (is_public)
                """
            )
        conn.commit()
    finally:
        conn.close()

    _story_schema_ready = True


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
    ensure_story_schema()
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
                       s.is_public,
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
    is_public: bool,
) -> dict[str, Any]:
    ensure_story_schema()
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
                    is_public,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id,
                          story_id,
                          user_id,
                          story_title,
                          user_input,
                          gender_preference,
                          culture_language,
                          is_public,
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
                    is_public,
                    "pending",
                ),
            )
            story = cur.fetchone()
        conn.commit()
    return story


def get_story(user_id: str, story_id: str) -> dict[str, Any] | None:
    ensure_story_schema()
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
                       s.is_public,
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
    ensure_story_schema()
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
                          is_public,
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
    ensure_story_schema()
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
    ensure_story_schema()
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


def set_story_visibility(user_id: str, story_id: str, is_public: bool) -> dict[str, Any] | None:
    ensure_story_schema()
    ensure_guest_user(user_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE stories s
                SET is_public = %s,
                    updated_at = NOW()
                WHERE s.id = %s
                  AND s.user_id = %s
                RETURNING s.id,
                          s.story_id,
                          s.user_id,
                          s.story_title,
                          s.user_input,
                          s.gender_preference,
                          s.culture_language,
                          s.is_public,
                          s.status,
                          s.error_message,
                          s.created_at,
                          s.updated_at,
                          (
                            SELECT MAX(created_at)
                            FROM story_events e
                            WHERE e.story_id = s.id
                          ) AS last_entered_at
                """,
                (is_public, story_id, user_id),
            )
            story = cur.fetchone()
        conn.commit()
    return story


def get_public_story(story_id: str) -> dict[str, Any] | None:
    ensure_story_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id,
                       s.story_id,
                       s.story_title,
                       s.user_input,
                       s.gender_preference,
                       s.culture_language,
                       s.is_public,
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
                  AND s.is_public = TRUE
                """,
                (story_id,),
            )
            story = cur.fetchone()
        conn.commit()
    return story


def list_public_stories(limit: int = 24) -> list[dict[str, Any]]:
    ensure_story_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id,
                       s.story_id,
                       s.story_title,
                       s.user_input,
                       s.gender_preference,
                       s.culture_language,
                       s.is_public,
                       s.status,
                       s.error_message,
                       s.created_at,
                       s.updated_at,
                       event_stats.last_entered_at,
                       COALESCE(event_stats.event_count, 0) AS event_count,
                       preview.preview_excerpt
                FROM stories s
                LEFT JOIN LATERAL (
                    SELECT MAX(e.created_at) AS last_entered_at,
                           COUNT(*) AS event_count
                    FROM story_events e
                    WHERE e.story_id = s.id
                ) event_stats
                  ON TRUE
                LEFT JOIN LATERAL (
                    SELECT e.content AS preview_excerpt
                    FROM story_events e
                    WHERE e.story_id = s.id
                      AND e.event_type = 'ai_response'
                    ORDER BY e.created_at DESC
                    LIMIT 1
                ) preview
                  ON TRUE
                WHERE s.is_public = TRUE
                ORDER BY COALESCE(event_stats.last_entered_at, s.updated_at) DESC,
                         s.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            stories = cur.fetchall()
        conn.commit()
    return stories


def list_public_story_events(story_id: str) -> list[dict[str, Any]]:
    ensure_story_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT e.id,
                       e.story_id,
                       e.scene_id,
                       e.episode_number,
                       e.round_number,
                       e.event_type,
                       e.content,
                       e.created_at
                FROM story_events e
                JOIN stories s
                  ON s.id = e.story_id
                WHERE e.story_id = %s
                  AND s.is_public = TRUE
                ORDER BY e.created_at ASC
                """,
                (story_id,),
            )
            events = cur.fetchall()
        conn.commit()
    return events
