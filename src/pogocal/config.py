"""Every tunable value in the project. Nothing here is imported for its
behaviour — only for its values, so this module never imports anything else
from the package.

Values that differ between machines — the Discord token and the three IDs —
come from .env, which is gitignored. Everything else is a constant here.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# This file is <root>/src/pogocal/config.py, so the third parent up is <root>.
# It resolves correctly because the package is installed in editable mode and
# still lives in the working tree; a copy installed elsewhere would not find
# the repository this way.
REPO_ROOT = Path(__file__).resolve().parents[2]

# Reads .env into the environment if it exists. It does not overwrite variables
# that are already set, so the GitHub Action's secrets win over any .env that
# might be lying around in a checkout.
load_dotenv(REPO_ROOT / ".env")

# GitHub Pages serves the /docs folder of the main branch. The calendar is
# written straight into the published location rather than copied there later.
OUTPUT_PATH = REPO_ROOT / "docs" / "pogo.ics"

# The name Apple Calendar shows in its sidebar, via X-WR-CALNAME.
CALENDAR_NAME = "Pokémon GO"

# Identifies the software that produced the file. RFC 5545 requires it and
# nothing reads it; it appears in the file as PRODID.
PRODID = "-//pogo-event-calendar//pogocal//EN"

# How often a subscribed client should re-fetch the file: 1440 minutes, one
# day. Apple Calendar treats this as a hint and its own Auto-refresh setting
# wins, so this is a floor on how stale a client should let itself get, not a
# guarantee.
REFRESH_INTERVAL = "PT1440M"

# Appended to each event's own identifier to build the ICS UID. It makes the
# identifier unique beyond this calendar, which is what UID is for.
UID_DOMAIN = "pogo-event-calendar"

# The Leek Duck event feed, published by ScrapedDuck. Around 55 events at a
# time; past events drop off, so anything worth keeping has to be kept here.
LEEKDUCK_FEED_URL = (
    "https://raw.githubusercontent.com/bigfoott/ScrapedDuck/data/events.min.json"
)

# Seconds to wait on a network call before giving up. Without a timeout a
# hung connection hangs the whole run, and the run is a scheduled job nobody
# is watching.
HTTP_TIMEOUT = 30.0

# How many times to retry a failed fetch before letting the error out. The
# feed is a static file on somebody else's server; a single failure is far
# more likely to be a blip than a real outage.
HTTP_RETRIES = 3

# Seconds to wait after a failed attempt, doubling each time: 1s, then 2s,
# then 4s. Short enough not to stall an hourly job, long enough to outlast a
# momentary failure.
HTTP_BACKOFF = 1.0

# Where `pogocal poll` records the last message it reported. Local and
# gitignored: the published calendar does not depend on it, because links are
# recomputed from the channel on every run rather than stored.
STATE_DIR = REPO_ROOT / "state"
CURSOR_PATH = STATE_DIR / "cursor.json"

DISCORD_API_BASE = "https://discord.com/api/v10"

# Discord asks bots to identify themselves. Nothing enforces it; it is how
# somebody on their side would work out what a misbehaving client is.
USER_AGENT = "pogo-event-calendar (https://github.com/Starfall10/pogo-event-calendar)"

# Messages per request. 100 is the API's maximum, and one request an hour is
# far more than a channel posting a few times a week will ever need.
POLL_LIMIT = 100

# Read once, on the very first run, when no cursor file exists yet. Optional:
# with nothing set, the first run starts from the channel's newest post.
CURSOR_SEED_MESSAGE_ID = os.getenv("CURSOR_SEED_MESSAGE_ID", "").strip() or None


# --- the published web page --------------------------------------------------

# Local copies of the infographics, served by GitHub Pages alongside the
# calendar. Images for events that have finished are deleted on each run:
# Pages stops publishing a site over 1 GB, and at roughly 7 MB an infographic
# that cap is about a year away without pruning.
IMAGE_DIR = OUTPUT_PATH.parent / "img"

# What the page offers people to subscribe to.
CALENDAR_URL = "https://starfall10.github.io/pogo-event-calendar/pogo.ics"


# --- matching a Discord post to a Leek Duck event ----------------------------
#
# Measured against tests/fixtures/ on 8 Sep 2026: 25 real posts, 55 real feed
# events. The numbers below come from that run, not from judgement.

# How close two names must be, by difflib.SequenceMatcher on the slugs.
#
# In the measurement the closest correct match scored 0.62 — "Harvest Festival"
# against the feed's "Harvest Festival 2026: Applin Picking" — and the highest
# scoring wrong candidate that survived the date filter scored 0.42. Raising
# this to 0.65 would silently drop that event's link.
NAME_SIMILARITY_THRESHOLD = 0.6

# How far apart the date in the post and the event's start may be.
#
# The date comes from the post's text, not from when it was posted: events are
# announced 0 to 38 days ahead, so the posting time says almost nothing about
# when the event runs. Widening this to 2 days changed no result, so it stays
# at the tightest value that works.
#
# This filter, not the name score, is what prevents wrong matches. Two examples
# from the measurement, both of which clear the similarity threshold on name
# alone and are both wrong:
#
#   "Nickit Community Day"  -> "October Community Day"  0.78, 55 days apart
#   "Mega Starmie Raid Day" -> "Super Mega Raid Day"    0.65, 70 days apart
MATCH_DATE_WINDOW_DAYS = 1

# Dropped from both names before comparing. They appear in almost every event
# name on one side or the other and carry no distinguishing information, so
# leaving them in inflates every score equally and flattens the gap between a
# right answer and a wrong one.
SLUG_STOPWORDS = ("pokemon", "pokémon", "go")


def require(name: str) -> str:
    """Fetch a required setting, or fail with the name of what is missing.

    Read at the point of use rather than at import, so that stages needing no
    credentials — building the calendar, and the whole test suite — keep
    working on a machine with no .env at all.
    """
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is not set. Copy .env.example to .env and fill it in "
            f"(see .claude/plans/steps.md, M2 steps 2.1-2.3). In the GitHub "
            f"Action it comes from repository secrets."
        )
    return value
