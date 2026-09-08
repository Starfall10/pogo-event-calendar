"""Matching a Discord post to the event it announces.

A post never creates an event. Every event comes from the Leek Duck feed; a
matched post only adds a link to the infographic announcing it. So this stage
can make the calendar richer and cannot make it wrong about dates.

It can still be wrong about links, and that is the failure to avoid. An
unmatched event simply has no link. A wrongly matched one shows the wrong
infographic, and nothing anywhere says so. When in doubt, do not match.

The rule, in order, from §5 of the build plan:

  1. filter the feed to events starting within a day of the date in the post
  2. compare names on their slugs
  3. accept the best, if it clears the threshold

Step 1 does most of the work. Measured on 8 Sep 2026, two posts scored 0.78 and
0.65 against events two months away — both above the threshold, both wrong, both
stopped by the date filter alone.
"""

import logging
import re
import unicodedata
from datetime import date
from difflib import SequenceMatcher

from pogocal import config
from pogocal.discord_src import DiscordPost
from pogocal.models import Event

log = logging.getLogger(__name__)

MONTHS = {
    name: number
    for number, name in enumerate(
        ("january", "february", "march", "april", "may", "june", "july",
         "august", "september", "october", "november", "december"), start=1)
}

# "September 19", "October 2-5", "September 29-October 5" — the first date is
# the one that matters; the feed's start is what it gets compared against.
FIRST_DATE = re.compile(r"([A-Za-z]+)\s+(\d{1,2})")

# A post that announces an event is written "# Name, Date". Anything else in
# the channel — a season link, a Twitch post, "WEEKLY SCHEDULE" — announces no
# event and matches nothing, which is correct.
HEADING_MARKER = "# "

# A month this far behind the posting month means the post is looking into next
# year: a December post about January. The only case that actually goes wrong.
YEAR_ROLLOVER_MONTHS = 6


def attach(events: list[Event], posts: list[DiscordPost]) -> list[Event]:
    """Give each event the link to the post announcing it, where one is found.

    Modifies the events in place and returns them. Posts are handled oldest
    first, so if two match the same event the newer link wins — a repost is
    usually a correction or an updated graphic.
    """
    matched = 0
    for post in sorted(posts, key=lambda p: p.posted_at):
        event = match(post, events)
        if event is None:
            continue
        event.discord_url = post.link
        event.source = "merged"
        matched += 1

    log.info("%d of %d posts matched an event", matched, len(posts))
    return events


def match(post: DiscordPost, events: list[Event]) -> Event | None:
    """The event this post announces, or None if nothing is close enough."""
    parsed = heading(post)
    if parsed is None:
        return None
    name, announced_for = parsed

    wanted = slugify(name)
    candidates = [
        event for event in events
        if abs((event.start.date() - announced_for).days)
        <= config.MATCH_DATE_WINDOW_DAYS
    ]
    if not candidates:
        log.debug("no feed event near %s for %r", announced_for, name)
        return None

    scored = sorted(
        ((SequenceMatcher(None, wanted, slugify(event.name)).ratio(), event)
         for event in candidates),
        key=lambda pair: -pair[0],
    )
    best, event = scored[0]

    if best < config.NAME_SIMILARITY_THRESHOLD:
        log.debug("closest to %r was %r at %.2f, below %.2f",
                  name, event.name, best, config.NAME_SIMILARITY_THRESHOLD)
        return None

    runners_up = [s for s, _ in scored[1:]
                  if s >= config.NAME_SIMILARITY_THRESHOLD]
    if runners_up:
        log.warning(
            "%r matched %r at %.2f, but %d other event(s) also cleared the "
            "threshold (best %.2f). Taking the highest.",
            name, event.name, best, len(runners_up), runners_up[0])

    log.debug("%r -> %r at %.2f", name, event.name, best)
    return event


def heading(post: DiscordPost) -> tuple[str, date] | None:
    """The name and date a post announces, or None if it announces neither."""
    text = (post.text or "").strip()
    if not text.startswith(HEADING_MARKER):
        return None

    first_line = text.splitlines()[0][len(HEADING_MARKER):].strip()
    # Split on the last comma: an event name may contain one, the date does not
    # begin with one. "# Mega Finale - September 5th" has no comma at all and
    # is left unmatched rather than special-cased.
    name, separator, date_part = first_line.rpartition(",")
    if not separator:
        return None

    announced_for = _first_date(date_part, post.posted_at.year,
                                post.posted_at.month)
    if announced_for is None:
        return None
    return name.strip(), announced_for


def slugify(text: str) -> str:
    """Reduce a name to the part worth comparing.

    Accents folded, because the feed writes "Pokémon" and the posts write
    "Pokemon". Punctuation dropped. Words that appear in nearly every name
    removed, since they inflate every score equally.
    """
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    words = re.sub(r"[^a-z0-9]+", " ", folded.lower()).split()
    return " ".join(w for w in words if w not in config.SLUG_STOPWORDS)


def _first_date(text: str, posted_year: int, posted_month: int) -> date | None:
    """The first date written in a heading, given the year the post was made."""
    found = FIRST_DATE.search(text)
    if not found:
        return None
    month = MONTHS.get(found.group(1).lower())
    if month is None:
        return None

    year = posted_year
    if month < posted_month - YEAR_ROLLOVER_MONTHS:
        year += 1
    try:
        return date(year, month, int(found.group(2)))
    except ValueError:
        return None
