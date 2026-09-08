"""Parsing the ScrapedDuck feed into Event records.

Every test here runs against tests/fixtures/events.min.json, a copy of the
real feed taken on 8 September 2026. Nothing in this file touches the network,
so the suite gives the same answer offline as it does at a desk.

The centre of it is the timezone rule. A trailing Z means one fixed moment
worldwide; no Z means the same clock time everywhere. Getting that backwards
puts 43 of the 55 events at the wrong time for anyone who travels.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pogocal.leekduck import parse, parse_record

FIXTURE = Path(__file__).parent / "fixtures" / "events.min.json"
RECORDS = json.loads(FIXTURE.read_text(encoding="utf-8"))


def record(**overrides) -> dict:
    """A well-formed feed record, with fields replaced as needed."""
    base = {
        "eventID": "test-event-2026",
        "name": "Test Event",
        "eventType": "event",
        "heading": "Event",
        "link": "https://leekduck.com/events/test-event-2026/",
        "image": "https://cdn.leekduck.com/assets/img/events/test.jpg",
        "start": "2026-09-19T14:00:00.000",
        "end": "2026-09-19T17:00:00.000",
        "extraData": {},
    }
    base.update(overrides)
    return base


# --- the timezone rule -------------------------------------------------------


def test_no_z_suffix_gives_a_floating_time():
    event = parse_record(record(start="2026-09-19T14:00:00.000",
                                end="2026-09-19T17:00:00.000"))
    assert event.start == datetime(2026, 9, 19, 14, 0)
    assert event.start.tzinfo is None
    assert event.is_local_time is True


def test_a_z_suffix_gives_a_fixed_time_in_utc():
    event = parse_record(record(start="2026-09-08T20:00:00.000Z",
                                end="2026-09-08T21:00:00.000Z"))
    assert event.start == datetime(2026, 9, 8, 20, 0, tzinfo=timezone.utc)
    assert event.start.tzinfo is not None
    assert event.is_local_time is False


def test_the_real_feed_splits_43_floating_and_12_fixed():
    events = parse(RECORDS)
    floating = [e for e in events if e.is_local_time]
    fixed = [e for e in events if not e.is_local_time]
    assert len(floating) == 43
    assert len(fixed) == 12
    # Every fixed event in this feed is a GO Battle League rotation.
    assert all(e.event_type == "go-battle-league" for e in fixed)


def test_the_staraptor_raid_day_matches_the_infographic():
    """The event the build plan was written around: 19 Sep, 2-5pm, floating."""
    events = {e.event_id: e for e in parse(RECORDS)}
    event = events["staraptor-super-mega-raid-day-2026"]
    assert event.name == "Staraptor Super Mega Raid Day"
    assert event.start == datetime(2026, 9, 19, 14, 0)
    assert event.end == datetime(2026, 9, 19, 17, 0)
    assert event.is_local_time is True


# --- the fields the feed provides --------------------------------------------


def test_the_whole_fixture_parses():
    assert len(parse(RECORDS)) == len(RECORDS) == 55


def test_the_feeds_own_identifier_is_used_unchanged():
    event = parse_record(record(eventID="community-day-october-2026"))
    assert event.event_id == "community-day-october-2026"


def test_name_type_and_link_are_carried_across():
    event = parse_record(record())
    assert event.name == "Test Event"
    assert event.event_type == "event"
    assert event.leekduck_url == "https://leekduck.com/events/test-event-2026/"


def test_the_heading_becomes_the_description():
    event = parse_record(record(heading="Raid Day"))
    assert "Raid Day" in event.summary_lines


def test_feed_events_are_authoritative_and_verified():
    event = parse_record(record())
    assert event.source == "leekduck"
    assert event.confidence == "high"


def test_no_discord_link_comes_from_the_feed():
    assert parse_record(record()).discord_url is None


# --- one bad record must not take the rest with it ---------------------------


@pytest.mark.parametrize(
    "broken, why",
    [
        ({"start": "not a date"}, "unparseable start"),
        ({"end": ""}, "empty end"),
        ({"start": "2026-09-19T17:00:00.000", "end": "2026-09-19T14:00:00.000"},
         "end before start"),
        ({"start": "2026-09-19T14:00:00.000", "end": "2026-09-19T17:00:00.000Z"},
         "start and end disagree about timezone"),
        ({"eventID": ""}, "no identifier"),
    ],
)
def test_a_broken_record_is_skipped_and_the_rest_survive(broken, why):
    records = [record(eventID="good-one"), record(**broken), record(eventID="good-two")]
    events = parse(records)
    assert [e.event_id for e in events] == ["good-one", "good-two"], why


def test_a_broken_record_is_logged_loudly(caplog):
    parse([record(start="not a date")])
    assert any(r.levelname in ("WARNING", "ERROR") for r in caplog.records)


def test_an_empty_feed_parses_to_nothing():
    assert parse([]) == []
