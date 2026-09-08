"""The Event record. Every stage of the pipeline either fills one of these or
reads one, so this module imports nothing from the rest of the package."""

from dataclasses import dataclass, field
from datetime import datetime

# Where an event's information came from, once reconciliation has run.
SOURCES = ("leekduck", "vision", "merged")

# Whether the dates can be trusted. "low" means no Leek Duck record matched,
# so the dates are the vision model's reading of an image and nothing has
# confirmed them.
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
