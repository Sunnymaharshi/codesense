"""
WebSocket endpoint: WS /ws/{username}

FastAPI's CORSMiddleware does NOT cover WebSockets.
We manually check the Origin header and reject unknown origins.
"""

import asyncio
import json
import logging
from urllib.parse import urlparse

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from redis import asyncio as aioredis
from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.profile import Developer, IndexStatus

router = APIRouter()
logger = logging.getLogger(__name__)

PROGRESS_CHANNEL = "codesense:progress:{username}"


def _origin_allowed(origin: str | None) -> bool:
    """Allow requests from configured CORS origins + no-origin (curl/Postman)."""
    if origin is None:
        return True  # no Origin header = same-origin or non-browser client

    allowed = [o.strip().rstrip("/") for o in settings.CORS_ORIGINS.split(",")]
    parsed = urlparse(origin)
    origin_clean = f"{parsed.scheme}://{parsed.netloc}"
    return origin_clean in allowed


@router.websocket("/ws/{username}")
async def ws_progress(websocket: WebSocket, username: str) -> None:
    origin = websocket.headers.get("origin")

    if not _origin_allowed(origin):
        logger.warning(f"[ws] rejected origin={origin}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    channel = PROGRESS_CHANNEL.format(username=username.lower())
    logger.info(f"[ws] accepted connection for @{username}, channel={channel}")

    # Catch the race where "done" was published before we subscribed.
    # Send current DB state immediately so the frontend doesn't wait forever.
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Developer).where(Developer.github_username == username.lower())
        )
        developer = result.scalar_one_or_none()
        if developer and developer.index_status == IndexStatus.done:
            await websocket.send_text(json.dumps({
                "type": "done",
                "repos_done": 0,
                "repos_total": 0,
                "synthetic": True,
            }))
            # If AI analysis already ran, also send agent_done so the frontend
            # doesn't open a 90s wait window after the synthetic done event.
            if developer.skill_scores is not None:
                await websocket.send_text(json.dumps({"type": "agent_done", "synthetic": True}))
            logger.info(f"[ws] sent synthetic done for @{username} (already indexed)")

    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)

    try:
        async for raw_message in pubsub.listen():
            if raw_message["type"] != "message":
                continue

            data_str = raw_message["data"]
            try:
                await websocket.send_text(data_str)
            except WebSocketDisconnect:
                logger.info(f"[ws] client disconnected for @{username}")
                break

            try:
                payload = json.loads(data_str)
                if payload.get("type") in ("agent_done", "agent_error", "error"):
                    logger.info(f"[ws] terminal event for @{username}, closing")
                    await websocket.close()
                    break
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        logger.info(f"[ws] client disconnected for @{username}")
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await redis.close()
