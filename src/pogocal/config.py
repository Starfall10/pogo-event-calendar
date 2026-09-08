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

# Where the record of what has already been processed lives. Committed, so it
# survives between runs of a job that keeps no machine of its own.
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
