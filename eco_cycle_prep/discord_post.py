"""High-level Discord post helpers for Sirens server communications.

All posts here go through the sirens-echo bot (SSM param
`/sirens-echo/discord-bot-token`). The eco-sirens bot (`/eco/discord-bot-token`,
owned by DiscordLink) is intentionally not used here: it auto-posts
server-status embeds and bridges in-game chat, and mixing the two bots in
one channel blurs what's automated vs. manual.

Channel aliases let callers say `post_content("general-public", ...)` instead
of juggling SSM parameter names. Add new aliases here rather than inlining
parameter paths at call sites.
"""

from __future__ import annotations

from typing import Optional

import httpx

from . import discord_rest, ssm

CHANNEL_ALIASES: dict[str, str] = {
    "general-public": "/discord/channel/general-public",
    "eco-status": "/discord/channel/server-status-feed",
}

# Color used by DiscordLink for the Server Started / Server Stopped embeds.
# Matching it keeps manual restart notices visually consistent with the feed.
STATUS_EMBED_COLOR = 7506394


def resolve_channel(alias: str) -> str:
    """Resolve a friendly channel alias to a Discord channel ID via SSM."""
    if alias not in CHANNEL_ALIASES:
        known = ", ".join(sorted(CHANNEL_ALIASES))
        raise ValueError(f"unknown channel alias {alias!r}. known: {known}")
    return ssm.get(CHANNEL_ALIASES[alias])


def post_content(channel: str, body: str) -> dict:
    """Post a plain-content message to a named channel."""
    return discord_rest.post_message(resolve_channel(channel), body)


def post_embed(
    channel: str,
    title: str,
    description: Optional[str] = None,
    color: int = STATUS_EMBED_COLOR,
) -> dict:
    """Post a single-embed message with optional description."""
    channel_id = resolve_channel(channel)
    embed: dict = {"title": title, "color": color}
    if description:
        embed["description"] = description
    r = httpx.post(
        f"{discord_rest.API_BASE}/channels/{channel_id}/messages",
        headers=discord_rest._headers(),
        json={"embeds": [embed]},
        timeout=discord_rest.TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def restart_notice(reason: Optional[str] = None) -> dict:
    """Post the pre-restart heads-up embed to #eco-status.

    Mirrors DiscordLink's Server Started / Server Stopped format: title-only
    (or title + one-line description), matching color, two-space emoji
    spacing. Call this immediately before restarting kai-server.
    """
    return post_embed(
        "eco-status",
        title="Server Restarting  :arrows_counterclockwise:",
        description=reason,
    )


def next_8am_pt() -> int:
    """Unix timestamp for the upcoming 8:00 AM in America/Los_Angeles.

    Returns today's 8am PT if the current local time is before 8am,
    otherwise tomorrow's 8am PT. Uses zoneinfo so daylight-savings is handled
    correctly (tzdata is declared as a Windows dep in pyproject.toml).
    """
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    pt = ZoneInfo("America/Los_Angeles")
    now = datetime.now(pt)
    today_8 = now.replace(hour=8, minute=0, second=0, microsecond=0)
    target = today_8 if now < today_8 else today_8 + timedelta(days=1)
    return int(target.timestamp())


def restart_schedule_footer(unix_ts: Optional[int] = None) -> str:
    """Standard footer line for patch notes about changes that need a restart.

    Renders with Discord's native <t:...:F> and <t:...:R> tags so every reader
    sees the time in their own locale alongside a live relative ("in an hour",
    "in 4 hours"). Pass an explicit `unix_ts` to override the default of the
    next 8:00 AM PT.

    Returns a single line; callers paste it as its own paragraph above the
    `[repo / component]` sign-off.
    """
    ts = unix_ts if unix_ts is not None else next_8am_pt()
    return (
        f"These changes will go live at 8am PT "
        f"(<t:{ts}:F>, <t:{ts}:R>) unless players request an earlier restart."
    )


# Emoji for the ops-notice embed. Distinct from DiscordLink's
# :white_check_mark: / :x: so ops traces are visually separable from the
# auto-feed while still using the same title-only embed format.
OPS_NOTICE_EMOJI = ":arrow_forward:"


def ops_notice(command_text: str) -> dict:
    """Post the literal invoke-command text to #eco-status before running it.

    Use this as the first step of any task that modifies real server state.
    The purpose is an audit trail: the channel log should show what was run
    and when, in a format that sits cleanly alongside DiscordLink's
    Server Started / Server Stopped embeds.

    The format mirrors DiscordLink exactly: title-only embed, matching color,
    two-space spacing before the emoji shortcode. The command string is the
    title, verbatim.

    The caller is responsible for redacting secrets (tokens, passwords, raw
    SSM values) from `command_text` before passing it in. The string is
    posted as-is. Common pattern: replace a sensitive value with `***`.

    Discord embed titles cap at 256 characters. For commands approaching
    that length, truncate or split into multiple notices rather than
    letting the API reject the post.
    """
    if len(command_text) > 240:
        command_text = command_text[:237] + "..."
    title = f"{command_text}  {OPS_NOTICE_EMOJI}"
    return post_embed("eco-status", title=title, description=None)
