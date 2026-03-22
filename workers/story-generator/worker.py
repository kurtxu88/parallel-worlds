import asyncio
import logging
import os

from dotenv import load_dotenv

from db import claim_pending_story, mark_story_completed, mark_story_failed
from o3_game_designer_phased import O3GameDesignerPhased


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("parallel_worlds_worker")

POLL_INTERVAL_SECONDS = int(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "5"))


async def process_story(story: dict) -> None:
    story_id = str(story["story_id"])
    designer = O3GameDesignerPhased()

    try:
        logger.info("Generating story %s", story_id)
        game_data = await asyncio.to_thread(
            designer.generate_complete_game,
            story.get("gender_preference", "male"),
            story["user_input"],
            story.get("culture_language", "en-US"),
            story_id,
        )

        if not game_data or "story_id" not in game_data:
            raise RuntimeError("Generator returned no story_id")

        title = game_data.get("metadata", {}).get("title")
        mark_story_completed(story_id, title)
        logger.info("Completed story %s", story_id)
    except Exception as exc:
        logger.exception("Story generation failed for %s", story_id)
        mark_story_failed(story_id, str(exc))


async def main() -> None:
    logger.info("Parallel Worlds story worker started")

    while True:
        story = claim_pending_story()
        if not story:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            continue

        await process_story(story)


if __name__ == "__main__":
    asyncio.run(main())
