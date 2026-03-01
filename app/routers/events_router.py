"""GESTIMA — Server-Sent Events (SSE)

Globální SSE stream pro real-time push notifikace napříč celou aplikací.
Jeden endpoint, všechny event typy. Klienti filtrují podle `type` v payloadu.

Event typy:
  tier_change  — { job, suffix, tier }
  (rozšiřitelné o další typy)
"""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.dependencies import get_current_user
from app.models import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stream")
async def event_stream(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """SSE stream — pushne všechny eventy připojeným klientům v reálném čase."""
    from app.services.event_bus import subscribe, unsubscribe

    q = subscribe()

    async def generate():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=30)
                    yield f"data: {json.dumps(msg)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            unsubscribe(q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
