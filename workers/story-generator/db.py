import os
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


def claim_pending_story() -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE stories
                SET status = 'generating',
                    updated_at = NOW()
                WHERE id = (
                    SELECT id
                    FROM stories
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id,
                          story_id,
                          user_id,
                          user_input,
                          gender_preference,
                          culture_language,
                          status
                """
            )
            story = cur.fetchone()
        conn.commit()
    return story


def mark_story_completed(story_id: str, title: str | None) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE stories
                SET status = 'completed',
                    story_title = %s,
                    error_message = NULL,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (title, story_id),
            )
        conn.commit()


def mark_story_failed(story_id: str, error_message: str, status: str = "failed") -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE stories
                SET status = %s,
                    error_message = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (status, error_message, story_id),
            )
        conn.commit()
