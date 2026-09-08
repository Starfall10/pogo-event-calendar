"""The Event record. Every stage of the pipeline either fills one of these or
reads one, so this module imports nothing from the rest of the package."""

from dataclasses import dataclass, field
from datetime import datetime

# Where an event's information came from.
#
#   "leekduck"  a feed event, with no Discord post matched to it
#   "merged"    a feed event that also carries a link to the post announcing it
#
# There is no "discord" value, and there cannot be one: a post never creates an
# event. Every event in this calendar comes from the feed, and a matched post
# only adds a link to it. A value nothing can produce is vocabulary that misleads
# whoever reads this next.
#
# "vision" was removed on 8 Sep 2026 with the withdrawal of paid API use.
SOURCES = ("leekduck", "merged")

# Whether the event's dates can be trusted.
#
# Nothing produces "low" any more. Every date comes from Leek Duck, so there is
# no such thing here as an unverified date. Kept, always "high", because a
# reconciliation that had to choose between several plausible posts may yet want
# to record that it was not certain — see the note in reconcile.py.
CONFIDENCE_LEVELS = ("high", "low")


@dataclass
class Event:
    """One calendar event, in the form every stage agrees on.

    The timezone rule lives in the datetimes themselves:

        naive datetime  -> floating local time, the same clock time everywhere
        aware datetime  -> a fixed moment, written to the calendar in UTC

    Almost every Pokémon GO event is the first kind. Nothing in this project
    ever attaches a named timezone.
    """

    event_id: str
    name: str
    start: datetime
    end: datetime
    source: str
    confidence: str
    event_type: str | None = None
    summary_lines: list[str] = field(default_factory=list)
    discord_url: str | None = None
    leekduck_url: str | None = None
    revision: int = 0

    def __post_init__(self) -> None:
        start_is_aware = self.start.tzinfo is not None
        end_is_aware = self.end.tzinfo is not None
        if start_is_aware != end_is_aware:
            raise ValueError(
                f"{self.event_id}: start and end disagree about time — "
                f"start is {'aware' if start_is_aware else 'naive'}, "
                f"end is {'aware' if end_is_aware else 'naive'}. "
                "Both must be naive (floating) or both aware (fixed)."
            )
        if self.end < self.start:
            raise ValueError(
                f"{self.event_id}: end {self.end} is before start {self.start}"
            )
        if self.source not in SOURCES:
            raise ValueError(
                f"{self.event_id}: source {self.source!r} is not one of {SOURCES}"
            )
        if self.confidence not in CONFIDENCE_LEVELS:
            raise ValueError(
                f"{self.event_id}: confidence {self.confidence!r} is not one of "
                f"{CONFIDENCE_LEVELS}"
            )

    @property
    def is_local_time(self) -> bool:
        """True when the event runs at the same clock time everywhere.

        Derived from the datetime rather than stored, so it cannot disagree
        with the value it describes.
        """
        return self.start.tzinfo is None
