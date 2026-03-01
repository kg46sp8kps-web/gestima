"""In-process pub/sub pro SSE broadcast (single-worker)."""

import asyncio
import json
import logging
from typing import Any, Dict, Set

logger = logging.getLogger(__name__)

_subscribers: Set[asyncio.Queue] = set()


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=64)
    _subscribers.add(q)
    logger.debug("SSE subscriber added (%d total)", len(_subscribers))
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    _subscribers.discard(q)
    logger.debug("SSE subscriber removed (%d total)", len(_subscribers))


def broadcast(event_type: str, data: Dict[str, Any]) -> None:
    msg = {"type": event_type, **data}
    for q in list(_subscribers):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            pass  # slow client — drop
