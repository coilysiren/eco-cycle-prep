from functools import lru_cache

import httpx

from . import ssm

API_BASE = "https://discord.com/api/v10"
TIMEOUT = httpx.Timeout(15.0, connect=10.0)


@lru_cache(maxsize=1)
def _headers() -> dict[str, str]:
    token = ssm.get("/eco/discord-bot-token")
    return {"Authorization": f"Bot {token}"}


def get_messages(channel_id: str, limit: int = 100) -> list[dict]:
    """Most recent messages in a text channel, newest first."""
    r = httpx.get(
        f"{API_BASE}/channels/{channel_id}/messages",
        headers=_headers(),
        params={"limit": limit},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def get_active_forum_threads(guild_id: str, forum_channel_id: str) -> list[dict]:
    """Active threads (posts) under a forum channel."""
    r = httpx.get(
        f"{API_BASE}/guilds/{guild_id}/threads/active",
        headers=_headers(),
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return [t for t in r.json().get("threads", []) if t.get("parent_id") == forum_channel_id]


def post_message(channel_id: str, content: str, file_path: str | None = None) -> dict:
    url = f"{API_BASE}/channels/{channel_id}/messages"
    if file_path:
        from pathlib import Path

        p = Path(file_path)
        with p.open("rb") as f:
            data = f.read()
        files = {"files[0]": (p.name, data, "image/gif")}
        r = httpx.post(
            url, headers=_headers(), data={"content": content}, files=files, timeout=TIMEOUT
        )
    else:
        r = httpx.post(url, headers=_headers(), json={"content": content}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()
