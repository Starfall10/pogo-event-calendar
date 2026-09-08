"""Reads the followed Discord channel.

Fetching and reading are kept apart, as in leekduck.py: everything except
fetch_messages() works on dictionaries and makes no call, so the whole of the
parsing is tested against saved payloads with no token and no network.

Two rules live here rather than anywhere else:

  * A message's CDN image URL expires in about 24 hours and must never be
    written into anything that is kept. What is kept is the deep link, which
    is permanent.
  * The cursor advances only past messages that were handled successfully, and
    stops at the first failure. A post the cursor has passed is unreachable
    forever, because nothing will ever ask for it again.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from pogocal import config, state

log = logging.getLogger(__name__)

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp")


@dataclass
class DiscordPost:
    """One post, reduced to the parts this project uses."""

    message_id: str
    posted_at: datetime
    text: str
    image_url: str | None
    link: str


def poll() -> list[DiscordPost]:
    """Read everything posted since the cursor, and move the cursor.

    Returns the posts that were read. Stops at the first message that cannot
    be read, leaving the cursor before it so the next run tries again.
    """
    guild_id = config.require("GUILD_ID")
    channel_id = config.require("CHANNEL_ID")

    after = state.load_cursor()
    messages = fetch_messages(after=after)
    if not messages:
        log.info("no new posts since %s", after or "the start")
        return []

    posts: list[DiscordPost] = []
    last_handled: str | None = None

    for message in oldest_first(messages):
        try:
            posts.append(parse_message(message, guild_id, channel_id))
        except (ValueError, TypeError, KeyError) as error:
            log.warning(
                "could not read message %s: %s. Stopping here; the cursor stays "
                "before it so the next run tries again.",
                (message or {}).get("id", "<no id>"), error,
            )
            break
        last_handled = message["id"]

    if last_handled:
        state.save_cursor(last_handled)
    log.info("read %d of %d new posts", len(posts), len(messages))
    return posts


def fetch_messages(after: str | None = None) -> list[dict[str, Any]]:
    """Fetch messages posted after the given id, newest first as the API sends
    them. Retries a few times, and honours a rate limit if one is returned."""
    token = config.require("DISCORD_BOT_TOKEN")
    channel_id = config.require("CHANNEL_ID")

    url = f"{config.DISCORD_API_BASE}/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {token}", "User-Agent": config.USER_AGENT}
    params: dict[str, Any] = {"limit": config.POLL_LIMIT}
    if after:
        params["after"] = after

    delay = config.HTTP_BACKOFF
    last_error: Exception | None = None

    for attempt in range(1, config.HTTP_RETRIES + 1):
        try:
            response = httpx.get(url, headers=headers, params=params,
                                 timeout=config.HTTP_TIMEOUT)
            if response.status_code == 429:
                wait = float(response.headers.get("Retry-After", delay))
                log.warning("rate limited by Discord; waiting %.1fs", wait)
                time.sleep(wait)
                continue
            response.raise_for_status()
            messages = response.json()
        except (httpx.HTTPError, ValueError) as error:
            last_error = error
            log.warning("message fetch attempt %d of %d failed: %s",
                        attempt, config.HTTP_RETRIES, error)
            if attempt < config.HTTP_RETRIES:
                time.sleep(delay)
                delay *= 2
            continue

        if not isinstance(messages, list):
            raise ValueError(
                f"Discord returned {type(messages).__name__}, expected a list"
            )
        return messages

    raise RuntimeError(
        f"Discord unreachable after {config.HTTP_RETRIES} attempts: {last_error}"
    ) from last_error


def oldest_first(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Discord returns newest first. Handled in that order, the cursor would
    finish pointing at the oldest message of the batch."""
    return sorted(messages, key=lambda m: int(m.get("id", 0)))


def parse_message(message: dict[str, Any], guild_id: str,
                  channel_id: str) -> DiscordPost:
    """Reduce one raw message to a DiscordPost. Raises if it cannot be read."""
    message_id = str(message.get("id") or "").strip()
    if not message_id.isdigit():
        raise ValueError(f"message has no usable id: {message.get('id')!r}")

    raw_time = message.get("timestamp")
    if not isinstance(raw_time, str):
        raise ValueError(f"message {message_id} has no timestamp")
    try:
        posted_at = datetime.fromisoformat(raw_time)
    except ValueError as error:
        raise ValueError(
            f"message {message_id} timestamp {raw_time!r} is unreadable: {error}"
        ) from error

    image_url = find_image_url(message)
    if image_url is None:
        log.warning(
            "message %s has no image: %d attachments, %d embeds",
            message_id, len(message.get("attachments") or []),
            len(message.get("embeds") or []),
        )

    return DiscordPost(
        message_id=message_id,
        posted_at=posted_at,
        text=(message.get("content") or "").strip(),
        image_url=image_url,
        link=permanent_link(guild_id, channel_id, message_id),
    )


def find_image_url(message: dict[str, Any]) -> str | None:
    """The image, wherever it turns up.

    An attachment first, then an embed's image, then an embed's thumbnail. In
    this channel it has always been an attachment, but a crossposted image can
    arrive either way and checking both costs nothing.

    The URL expires in about 24 hours. It may be read during a run; it must
    never be written into the calendar or into committed state.
    """
    for attachment in message.get("attachments") or []:
        url = attachment.get("url")
        if url and _looks_like_an_image(attachment.get("content_type"), url):
            return url

    for embed in message.get("embeds") or []:
        for key in ("image", "thumbnail"):
            url = (embed.get(key) or {}).get("url")
            if url:
                return url

    return None


def permanent_link(guild_id: str, channel_id: str, message_id: str) -> str:
    """The address of a post. Never expires, needs no token, opens the app."""
    return f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"


def _looks_like_an_image(content_type: str | None, url: str) -> bool:
    if content_type:
        return content_type.startswith("image/")
    return url.lower().split("?")[0].endswith(IMAGE_SUFFIXES)
