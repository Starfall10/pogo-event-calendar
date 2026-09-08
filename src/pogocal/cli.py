"""The pogocal command.

Each subcommand is one stage of the pipeline, runnable on its own. build is
the only one that works at M0; the others are named here so that typing them
explains itself rather than producing an argument error.
"""

import argparse
import logging
import sys

from pogocal import config
from pogocal.ics_build import render
from pogocal.leekduck import fetch_events

log = logging.getLogger("pogocal")


def build() -> int:
    """Fetch the feed, render the calendar, write it to the published location."""
    try:
        events = fetch_events()
    except RuntimeError as error:
        log.error("%s", error)
        log.error("calendar not rebuilt; the previous file is left in place")
        return 1

    calendar = render(events)

    previous = None
    if config.OUTPUT_PATH.exists():
        # newline="" on the way in as well as out: reading in text mode
        # otherwise turns every CRLF into LF, and the comparison below then
        # reports a change on every run.
        with config.OUTPUT_PATH.open(encoding="utf-8", newline="") as handle:
            previous = handle.read()

    config.OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    # newline="" keeps Python from rewriting the CRLF line endings the
    # calendar format requires.
    with config.OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        handle.write(calendar)

    state = "unchanged" if calendar == previous else "updated"
    relative = config.OUTPUT_PATH.relative_to(config.REPO_ROOT)
    floating = sum(1 for e in events if e.is_local_time)
    print(
        f"{relative}: {len(events)} events "
        f"({floating} floating, {len(events) - floating} fixed), "
        f"{len(calendar)} bytes, {state}"
    )
    for event in sorted(events, key=lambda e: e.start.replace(tzinfo=None)):
        marker = "floating" if event.is_local_time else "fixed"
        print(f"  {event.start:%Y-%m-%d %H:%M}  {marker:8}  {event.name}")
    return 0


def not_yet(command: str, milestone: str) -> int:
    print(
        f"pogocal {command} arrives at {milestone}. Only 'build' works today.",
        file=sys.stderr,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pogocal",
        description="Publish Pokémon GO events as a subscribable calendar.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("build", help=f"rebuild {config.OUTPUT_PATH.name}")
    subcommands.add_parser("poll", help="fetch new Discord posts (M2)")
    subcommands.add_parser("run", help="poll then build (M5)")

    args = parser.parse_args(argv)
    # A person is watching this now; at M5 nobody is. Either way the warnings
    # from a skipped feed record have to reach somewhere they can be read.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.command == "build":
        return build()
    if args.command == "poll":
        return not_yet("poll", "M2")
    return not_yet("run", "M5")


if __name__ == "__main__":
    sys.exit(main())
