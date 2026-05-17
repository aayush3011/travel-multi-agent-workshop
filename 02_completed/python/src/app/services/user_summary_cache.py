"""In-process TTL cache for user_summary point reads (perf spec §6.3)."""

from __future__ import annotations

import time
from typing import Optional

from agent_memory_toolkit.aio import AsyncCosmosMemoryClient

_CACHE: dict[str, tuple[float, Optional[dict]]] = {}
_TTL_SEC = 30


async def get_cached_user_summary(
    client: AsyncCosmosMemoryClient, user_id: str
) -> Optional[dict]:
    now = time.time()
    entry = _CACHE.get(user_id)
    if entry and (now - entry[0]) < _TTL_SEC:
        return entry[1]
    doc = await client.get_user_summary(user_id)
    _CACHE[user_id] = (now, doc)
    return doc


def invalidate_user_summary(user_id: str) -> None:
    _CACHE.pop(user_id, None)
