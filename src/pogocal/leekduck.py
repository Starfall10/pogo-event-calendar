"""Reads the ScrapedDuck feed and turns it into Event records.

This is the first stage that touches the network. Fetching and parsing are
kept apart on purpose: parse() works on a list of dictionaries and never makes
a call, which is what lets the whole of it be tested against a saved copy of
the feed with no internet.

Leek Duck is authoritative for dates and times. Everything this module
produces is marked confidence="high" for that reason.
"""

import logging
import time
from datetime import datetime
from typing import Any

import httpx

from pogocal import config
from pogocal.models import Event

log = logging.getLogger(__name__)


def fetch_events(url: str | None = None) -> list[Event]:
    """The whole stage: fetch the feed and parse it."""
    return parse(fetch(url))


def fetch(url: str | None = None) -> list[dict[str, Any]]:
    """Fetch the raw feed, retrying a few times before giving up.

    A scheduled job nobody is watching must not hang on a quiet connection,
    and must not fail the whole run because one request was unlucky.
    """
    url = url or config.LEEKDUCK_FEED_URL
    delay = config.HTTP_BACKOFF
    last_error: Exception | None = None

    for attempt in range(1, config.HTTP_RETRIES + 1):
        try:
            response = httpx.get(url, timeout=config.HTTP_TIMEOUT)
            response.raise_for_status()
            records = response.json()
        except (httpx.HTTPError, ValueError) as error:
            last_error = error
            log.warning(
                "feed fetch attempt %d of %d failed: %s",
                attempt, config.HTTP_RETRIES, error,
            )
            if attempt < config.HTTP_RETRIES:
                time.sleep(delay)
                delay *= 2
            continue

        if not isinstance(records, list):
            raise ValueError(
                f"feed returned {type(records).__name__}, expected a list"
            )
        if not records:
            log.error("feed returned zero events — this is almost never right")
        else:
            log.info("feed returned %d events", len(records))
        return records

    raise RuntimeError(
        f"feed unreachable after {config.HTTP_RETRIES} attempts: {last_error}"
    ) from last_error


def parse(records: list[dict[str, Any]]) -> list[Event]:
    """Turn feed records into Events, skipping any that cannot be read.

    One malformed record must never cost the other fifty-four. The feed
    belongs to somebody else and can change shape without warning.
    """
    events: list[Event] = []
    skipped = 0

    for record in records:
        try:
            events.append(parse_record(record))
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            skipped += 1
            log.warning(
                "skipped feed record %r: %s",
                (record or {}).get("eventID", "<no eventID>"), error,
            )

    if skipped:
        log.warning("%d of %d feed records could not be read",
                    skipped, len(records))
    return events


def parse_record(record: dict[str, Any]) -> Event:
    """Turn one feed record into an Event. Raises if the record is unusable."""
    event_id = (record.get("eventID") or "").strip()
    if not event_id:
        raise ValueError("record has no eventID")

    heading = (record.get("heading") or "").strip()

    return Event(
        event_id=event_id,
        name=(record.get("name") or "").strip() or event_id,
        start=_timestamp(record.get("start"), "start"),
        end=_timestamp(record.get("end"), "end"),
        source="leekduck",
        confidence="high",
        event_type=(record.get("eventType") or None),
        summary_lines=[heading] if heading else [],
        leekduck_url=(record.get("link") or None),
    )


def _timestamp(raw: Any, field: str) -> datetime:
    """Read one feed timestamp, and with it decide the kind of time it is.

    This is the only place in the project where that decision is made. The
    feed's convention and Python's own parsing agree, so the rule needs no
    code of its own:

        "2026-09-08T20:00:00.000Z"  -> aware datetime  -> fixed, written in UTC
        "2026-09-19T14:00:00.000"   -> naive datetime  -> floating local time

    Nothing here attaches, converts or strips a timezone. The marker in the
    feed is carried through to the calendar file untouched.
    """
    if not raw or not isinstance(raw, str):
        raise ValueError(f"{field} is missing or not a string: {raw!r}")
    try:
        return datetime.fromisoformat(raw)
    except ValueError as error:
        raise ValueError(f"{field} {raw!r} is not a timestamp: {error}") from error
