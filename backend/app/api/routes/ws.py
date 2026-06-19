"""
WebSocket endpoint: WS /ws/{username}

Subscribes to the Redis pub/sub channel for a username and
forwards all progress events to the connected WebSocket client.

Closes automatically on "done" or "error" event.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis import asyncio as aioredis

from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

PROGRESS_CHANNEL = "codesense:progress:{username}"


@router.websocket("/ws/{username}")
async def ws_progress(websocket: WebSocket, username: str) -> None:
    await websocket.accept()
    channel = PROGRESS_CHANNEL.format(username=username.lower())
    logger.info(f"[ws] client connected for @{username}, channel={channel}")

    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)

    try:
        async for raw_message in pubsub.listen():
            # pubsub.listen() yields subscription confirmations first
            if raw_message["type"] != "message":
                continue

            data_str = raw_message["data"]
            try:
                await websocket.send_text(data_str)
            except WebSocketDisconnect:
                logger.info(f"[ws] client disconnected for @{username}")
                break

            # Close from server side after terminal events
            try:
                payload = json.loads(data_str)
                if payload.get("type") in ("done", "error"):
                    logger.info(f"[ws] terminal event '{payload['type']}' for @{username}, closing")
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
