"""Turns Event records into the text of an .ics file.

This is the only module that decides how a datetime becomes a line of text,
and therefore the only place the floating-versus-fixed distinction is acted
on. It reads Events and produces a string; it fetches nothing and writes
nothing to disk, so it can be run against saved data with no network.
"""

from datetime import datetime, timezone
from typing import Iterable

from icalendar import Calendar
from icalendar import Event as ICalComponent
from icalendar.prop import vText

from pogocal import config
from pogocal.models import Event

# DTSTAMP means "when this calendar object was written". A real timestamp
# would differ on every run, so every hourly rebuild would produce a changed
# file and a pointless commit. A fixed value keeps the output byte-identical
# when nothing has actually changed. Clients detect revisions from SEQUENCE,
# not from this.
DTSTAMP = datetime(2026, 1, 1, tzinfo=timezone.utc)


def render(events: Iterable[Event]) -> str:
    """Render events as the complete text of an .ics file."""
    calendar = Calendar()
    calendar.add("prodid", config.PRODID)
    calendar.add("version", "2.0")
    calendar.add("X-WR-CALNAME", config.CALENDAR_NAME)
    calendar.add("REFRESH-INTERVAL", _duration(config.REFRESH_INTERVAL))
    calendar.add("X-PUBLISHED-TTL", vText(config.REFRESH_INTERVAL))

    for event in sorted(events, key=_ordering):
        calendar.add_component(_component(event))

    return calendar.to_ical().decode("utf-8")


def _duration(value: str) -> vText:
    """A duration written as text, carrying the VALUE=DURATION parameter that
    tells a client to read it as a length of time rather than a string."""
    duration = vText(value)
    duration.params["VALUE"] = "DURATION"
    return duration


def _ordering(event: Event) -> tuple[datetime, str]:
    """A sort key, so the same events always come out in the same order.

    Naive and aware datetimes cannot be compared with each other, so the
    timezone is dropped for ordering purposes. This affects the order events
    appear in the file and nothing else — what gets written for each one is
    decided in _component below.
    """
    return (event.start.replace(tzinfo=None), event.event_id)


def _component(event: Event) -> ICalComponent:
    """One VEVENT block.

    The timezone rule is applied here, by doing nothing: a naive datetime is
    handed over naive and written without a marker, an aware one is handed
    over aware and written in UTC with a trailing Z. No timezone is ever
    attached, converted or stripped.
    """
    component = ICalComponent()
    component.add("uid", f"{event.event_id}@{config.UID_DOMAIN}")
    component.add("summary", event.name)
    component.add("dtstart", event.start)
    component.add("dtend", event.end)
    component.add("dtstamp", DTSTAMP)
    component.add("sequence", event.revision)

    description = _description(event)
    if description:
        component.add("description", description)

    link = event.discord_url or event.leekduck_url
    if link:
        component.add("url", link)

    return component


def _description(event: Event) -> str:
    """The event's notes, as Apple Calendar shows them.

    The first line matters most because it is what appears in the collapsed
    view. The fuller layout, with bonuses and ticket details in labelled
    groups, arrives with reconciliation at M4.
    """
    parts: list[str] = []
    if event.discord_url:
        parts.append(f"📱 Infographic: {event.discord_url}")
    if event.summary_lines:
        parts.append("\n".join(event.summary_lines))
    if event.leekduck_url:
        parts.append(f"📄 Details: {event.leekduck_url}")
    return "\n\n".join(parts)
