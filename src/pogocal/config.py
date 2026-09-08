"""Every tunable value in the project. Nothing here is imported for its
behaviour — only for its values, so this module never imports anything else
from the package."""

from pathlib import Path

# This file is <root>/src/pogocal/config.py, so the third parent up is <root>.
# It resolves correctly because the package is installed in editable mode and
# still lives in the working tree; a copy installed elsewhere would not find
# the repository this way.
REPO_ROOT = Path(__file__).resolve().parents[2]

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
