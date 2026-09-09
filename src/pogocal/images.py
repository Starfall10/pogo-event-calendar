"""Local copies of the infographics.

The build plan's §1 ruled this out — "sidesteps mirroring someone else's
artwork". The owner reversed that on 9 September 2026, choosing full size. The
artwork is credited by G47IX wherever it is shown.

Two things follow from that decision and are handled here:

  * A Discord CDN url expires in about 24 hours, so the page cannot reference
    one. The file is fetched once and served from this repository instead.
  * GitHub Pages stops publishing a site over 1 GB. At roughly 7 MB an
    infographic that is about a year away, so images for events that have
    finished are deleted on every run. Git history still keeps every version;
    only the published site stays small.

Nothing here is fatal. An infographic that cannot be fetched costs that one
picture, and the page, the calendar and the rest of the images are unaffected.
"""

import logging
import os
import re
from pathlib import Path

import httpx

from pogocal import config

log = logging.getLogger(__name__)

KNOWN_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp")
UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")

# Enough for a 7 MB image on a slow connection, and short enough that a
# scheduled run cannot hang on one file.
DOWNLOAD_TIMEOUT = 60.0


def sync(wanted: dict[str, str]) -> dict[str, str]:
    """Make the image directory hold exactly the wanted images.

    Takes event id -> source url. Returns event id -> path relative to the
    published folder, for the events whose image is on disk afterwards.
    """
    config.IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    resolved: dict[str, str] = {}
    keep: set[str] = set()

    for event_id, url in sorted(wanted.items()):
        name = local_name(event_id, url)
        destination = config.IMAGE_DIR / name

        if not destination.is_file():
            try:
                download(url, destination)
            except Exception as error:
                # A half-written file would be mistaken for a complete one by
                # every later run, so the failure is cleaned up after.
                destination.unlink(missing_ok=True)
                log.warning("could not fetch the infographic for %s: %s",
                            event_id, error)
                continue
            log.info("fetched %s (%.1f MB)", name,
                     destination.stat().st_size / 1_048_576)

        keep.add(name)
        resolved[event_id] = f"{config.IMAGE_DIR.name}/{name}"

    _prune(keep)
    return resolved


def local_name(event_id: str, source_url: str) -> str:
    """The filename an event's infographic is kept under.

    Derived from the event, never from the uploaded filename: G47IX renaming a
    file must not orphan the copy and fetch it again. Event ids come from
    somebody else's feed, so anything that could climb out of the directory is
    stripped.
    """
    stem = UNSAFE.sub("-", event_id).strip("-.") or "event"
    path = source_url.split("?", 1)[0].lower()
    suffix = next((s for s in KNOWN_SUFFIXES if path.endswith(s)), ".png")
    return f"{stem}{suffix}"


def download(url: str, destination: Path) -> None:
    """Fetch one image, and leave nothing behind if it goes wrong.

    Written to a neighbouring file and moved into place, so a run that dies
    mid-download cannot leave a truncated image that later runs treat as done.
    """
    response = httpx.get(url, timeout=DOWNLOAD_TIMEOUT, follow_redirects=True)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("image/"):
        raise ValueError(f"expected an image, got {content_type!r}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    try:
        temporary.write_bytes(response.content)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _prune(keep: set[str]) -> None:
    """Remove images no longer wanted, so the published site stays small."""
    if not config.IMAGE_DIR.is_dir():
        return
    for path in sorted(config.IMAGE_DIR.iterdir()):
        if path.is_file() and path.name not in keep:
            log.info("removing %s; its event has finished", path.name)
            path.unlink()
