"""The cursor: which Discord post was last processed.

This is the project's only memory. The job keeps no machine of its own, so
what it knows between runs is whatever is committed to the repository.

Two rules, both enforced here:

  * The file is written atomically, so a process that dies mid-write cannot
    leave a half-written cursor behind.
  * The file contains the message id and nothing else. No timestamp, no run
    counter. An hourly job that found nothing new must produce a byte-identical
    file, or M5 commits noise every hour.

The third rule — that the cursor never advances past a message that failed —
belongs to the caller, in discord_src.py, because only the caller knows whether
the work succeeded.
"""

import json
import logging
import os

from pogocal import config

log = logging.getLogger(__name__)

CURSOR_KEY = "last_message_id"


def load_cursor() -> str | None:
    """The message id to poll after, or None to start from the newest post.

    Falls back to the seed only when no cursor file exists. Once the file is
    there it wins: the seed is a starting point, not a setting.
    """
    path = config.CURSOR_PATH
    if not path.is_file():
        seed = config.CURSOR_SEED_MESSAGE_ID
        if seed:
            log.info("no cursor file; starting from seed message %s", seed)
        else:
            log.info("no cursor file and no seed; starting from the newest post")
        return seed

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as error:
        raise RuntimeError(
            f"cursor file {path} could not be read: {error}. Fix or delete it. "
            f"Deleting means the next run starts from the seed and reprocesses "
            f"everything after it."
        ) from error

    message_id = data.get(CURSOR_KEY) if isinstance(data, dict) else None
    if not isinstance(message_id, str) or not message_id.isdigit():
        raise RuntimeError(
            f"cursor file {path} has no usable {CURSOR_KEY!r}: {data!r}"
        )
    return message_id


def save_cursor(message_id: str) -> None:
    """Record the last successfully processed message id."""
    if not isinstance(message_id, str) or not message_id.strip().isdigit():
        raise ValueError(f"not a Discord message id: {message_id!r}")
    message_id = message_id.strip()

    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    # Sorted keys and a trailing newline, so the bytes depend only on the
    # value. Written to a neighbouring file first and moved into place, which
    # os.replace does atomically: readers see either the old file or the new
    # one, never a truncated one.
    payload = json.dumps({CURSOR_KEY: message_id}, indent=2, sort_keys=True) + "\n"
    temporary = config.CURSOR_PATH.with_suffix(".json.tmp")
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, config.CURSOR_PATH)
    log.info("cursor now at message %s", message_id)
