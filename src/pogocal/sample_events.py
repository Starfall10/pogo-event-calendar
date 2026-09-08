"""Two hand-written events, so M0 can publish a real calendar before any
source of real data exists.

This is scaffolding. It is deleted at M1, when leekduck.py starts producing
Events from the ScrapedDuck feed and the calendar stops being made up. Nothing
here is imported by the tests — they define their own events — so removing this
file breaks nothing but the M0 build.

The two shapes it needs to demonstrate come from the build plan's M0: one
floating afternoon event, and one that spans several days.
"""

from datetime import datetime

from pogocal.models import Event

SAMPLE_EVENTS = [
    Event(
        event_id="sample-raid-day-2026-09-19",
        name="Sample Raid Day",
        start=datetime(2026, 9, 19, 14, 0),
        end=datetime(2026, 9, 19, 17, 0),
        source="leekduck",
        confidence="high",
        event_type="raid-day",
        summary_lines=[
            "This is a placeholder event from M0, not a real Raid Day.",
            "It runs 2-5pm local time, which is what a floating event means:",
            "the same clock time wherever you are.",
        ],
        leekduck_url="https://leekduck.com/events/",
    ),
    Event(
        event_id="sample-multi-day-event-2026-09-29",
        name="Sample Multi-Day Event",
        start=datetime(2026, 9, 29, 10, 0),
        end=datetime(2026, 10, 5, 20, 0),
        source="leekduck",
        confidence="high",
        event_type="event",
        summary_lines=[
            "This is a placeholder event from M0, not a real event.",
            "It starts at 10am on 29 September and ends at 8pm on 5 October.",
        ],
        leekduck_url="https://leekduck.com/events/",
    ),
]
