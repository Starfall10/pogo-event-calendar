"""What the published calendar file must contain.

These assert on the *text* of the .ics output rather than on Event objects.
The timezone bug this project cares about most is invisible at the object
level — an Event can look perfect while the line written into the file says
something else — so the file is what gets checked.
"""

from datetime import datetime, timezone

from pogocal import config
from pogocal.ics_build import render
from pogocal.models import Event

# A Raid Day: 2-5pm local time, the same clock time everywhere on Earth.
RAID_DAY = Event(
    event_id="mega-staraptor-raid-day-2026-09-19",
    name="Mega Staraptor Raid Day",
    start=datetime(2026, 9, 19, 14, 0),
    end=datetime(2026, 9, 19, 17, 0),
    source="leekduck",
    confidence="high",
    event_type="raid-day",
    summary_lines=["Up to 5 additional daily Raid Passes from Gyms"],
    discord_url="https://discord.com/channels/1/2/3",
)

# A multi-day event, also floating.
HARVEST = Event(
    event_id="harvest-festival-2026",
    name="Harvest Festival",
    start=datetime(2026, 9, 29, 10, 0),
    end=datetime(2026, 10, 5, 20, 0),
    source="leekduck",
    confidence="high",
    event_type="event",
)

# A global event: one fixed moment, the same instant worldwide.
GLOBAL_EVENT = Event(
    event_id="go-fest-2026-global",
    name="GO Fest 2026: Global",
    start=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
    end=datetime(2026, 8, 2, 18, 0, tzinfo=timezone.utc),
    source="leekduck",
    confidence="high",
)


def unfold(ics: str) -> str:
    """Undo RFC 5545 line folding, which breaks any line over 75 octets by
    inserting CRLF and a space. Content assertions run against the unfolded
    text; the short DTSTART lines are checked raw."""
    return ics.replace("\r\n ", "")


# --- the timezone rule, which is the reason this file exists -----------------


def test_floating_event_is_written_with_no_timezone_marker():
    ics = render([RAID_DAY])
    assert "DTSTART:20260919T140000\r\n" in ics
    assert "DTEND:20260919T170000\r\n" in ics


def test_fixed_event_is_written_in_utc():
    ics = render([GLOBAL_EVENT])
    assert "DTSTART:20260801T100000Z\r\n" in ics
    assert "DTEND:20260802T180000Z\r\n" in ics


def test_no_named_timezone_appears_anywhere():
    ics = render([RAID_DAY, HARVEST, GLOBAL_EVENT])
    assert "TZID" not in ics
    assert "BEGIN:VTIMEZONE" not in ics


def test_multi_day_event_keeps_both_dates():
    ics = render([HARVEST])
    assert "DTSTART:20260929T100000\r\n" in ics
    assert "DTEND:20261005T200000\r\n" in ics


# --- identity, which is what stops the calendar filling with duplicates ------


def test_uid_is_derived_from_the_event_id():
    ics = unfold(render([RAID_DAY]))
    assert f"UID:{RAID_DAY.event_id}@{config.UID_DOMAIN}\r\n" in ics


def test_uid_is_identical_across_rebuilds():
    assert unfold(render([RAID_DAY])) == unfold(render([RAID_DAY]))


def test_sequence_comes_from_the_event_revision():
    ics = render([RAID_DAY])
    assert "SEQUENCE:0\r\n" in ics

    revised = Event(**{**RAID_DAY.__dict__, "revision": 3})
    assert "SEQUENCE:3\r\n" in render([revised])


# --- what the event carries --------------------------------------------------


def test_event_carries_its_name_description_and_link():
    ics = unfold(render([RAID_DAY]))
    assert "SUMMARY:Mega Staraptor Raid Day\r\n" in ics
    assert "Up to 5 additional daily Raid Passes from Gyms" in ics
    assert "URL:https://discord.com/channels/1/2/3\r\n" in ics


def test_every_event_appears_once():
    ics = render([RAID_DAY, HARVEST, GLOBAL_EVENT])
    assert ics.count("BEGIN:VEVENT") == 3
    assert ics.count("END:VEVENT") == 3


# --- calendar-level properties -----------------------------------------------


def test_calendar_announces_its_name_and_refresh_interval():
    ics = unfold(render([RAID_DAY]))
    assert f"X-WR-CALNAME:{config.CALENDAR_NAME}\r\n" in ics
    assert f"REFRESH-INTERVAL;VALUE=DURATION:{config.REFRESH_INTERVAL}\r\n" in ics
    assert f"X-PUBLISHED-TTL:{config.REFRESH_INTERVAL}\r\n" in ics
    assert f"PRODID:{config.PRODID}\r\n" in ics
    assert "VERSION:2.0\r\n" in ics


def test_no_alarms_are_ever_emitted():
    ics = render([RAID_DAY, HARVEST, GLOBAL_EVENT])
    assert "VALARM" not in ics


def test_an_empty_calendar_is_still_a_valid_calendar():
    ics = render([])
    assert ics.startswith("BEGIN:VCALENDAR")
    assert ics.rstrip().endswith("END:VCALENDAR")
    assert "BEGIN:VEVENT" not in ics
