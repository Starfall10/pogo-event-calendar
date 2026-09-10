"""The pogocal command.

Each subcommand is one stage of the pipeline, runnable on its own. build is
the only one that works at M0; the others are named here so that typing them
explains itself rather than producing an argument error.
"""

import argparse
import logging
import sys

from typing import Any

from pogocal import config, discord_src, images, leekduck, pokeapi, reconcile, web_build
from pogocal.ics_build import render
from pogocal.models import Event

# Types where knowing what beats the Pokémon is worth the space. A Community
# Day is not a fight.
BATTLE_TYPES = frozenset({"raid-battles", "raid-hour", "raid-day",
                          "max-battles", "max-mondays"})

log = logging.getLogger("pogocal")


def build(with_links: bool = False) -> int:
    """Fetch the feed, render the calendar, write it to the published location.

    With with_links, also read the Discord channel and attach a link to every
    event a post announces. The links are recalculated from scratch each time
    rather than stored, so they cannot drift from what the channel says.
    """
    try:
        records = leekduck.fetch()
    except RuntimeError as error:
        log.error("%s", error)
        log.error("calendar not rebuilt; the previous file is left in place")
        return 1
    events = leekduck.parse(records)

    local_images: dict[str, str] = {}
    if with_links:
        sources = _attach_links(events)
        if sources:
            try:
                local_images = images.sync(sources)
            except OSError as error:
                log.warning("could not update the infographics: %s", error)

    calendar = render(events)
    page = web_build.render(events, images=local_images,
                            details=_details(records, events))

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

    page_path = config.OUTPUT_PATH.parent / "index.html"
    page_state = _write(page_path, page)

    state = "unchanged" if calendar == previous else "updated"
    relative = config.OUTPUT_PATH.relative_to(config.REPO_ROOT)
    floating = sum(1 for e in events if e.is_local_time)
    linked = sum(1 for e in events if e.discord_url)
    print(
        f"{relative}: {len(events)} events "
        f"({floating} floating, {len(events) - floating} fixed, "
        f"{linked} with an infographic), "
        f"{len(calendar)} bytes, {state}"
    )
    print(
        f"{page_path.relative_to(config.REPO_ROOT)}: {len(page)} bytes, "
        f"{page_state}, {len(local_images)} images on disk"
    )
    for event in sorted(events, key=lambda e: e.start.replace(tzinfo=None)):
        marker = "floating" if event.is_local_time else "fixed"
        print(f"  {event.start:%Y-%m-%d %H:%M}  {marker:8}  {event.name}")
    return 0


def poll() -> int:
    """Read new posts from the followed channel and move the cursor."""
    try:
        posts = discord_src.poll()
    except RuntimeError as error:
        log.error("%s", error)
        log.error("cursor not moved; the next run will try the same posts again")
        return 1

    if not posts:
        print("no new posts")
        return 0

    with_image = sum(1 for p in posts if p.image_url)
    print(f"{len(posts)} new posts ({with_image} with an image)")
    for post in posts:
        print(f"  {post.posted_at:%Y-%m-%d %H:%M}  {post.text[:60] or '<no text>'}")
        print(f"      {post.link}")
    return 0


def _details(records: list[dict[str, Any]],
             events: list[Event]) -> dict[str, dict[str, Any]]:
    """The Pokémon, bonuses and shiny flags the page shows on each poster.

    The feed carries rich detail for three kinds of event and nothing beyond a
    name for the rest. What is missing is filled from PokéAPI, which also
    supplies the weaknesses the feed has none of. Nothing here is fatal: an
    event with no detail simply renders without it.
    """
    by_id = {r.get("eventID"): r for r in records}
    details: dict[str, dict[str, Any]] = {}

    for event in events:
        record = by_id.get(event.event_id) or {}
        extra = record.get("extraData") or {}
        detail: dict[str, Any] = {}

        pokemon = _pokemon_from_feed(extra, event.event_type)
        if pokemon is None and event.event_type in BATTLE_TYPES:
            # No detail in the feed, but the title usually names somebody:
            # "Staraptor Super Mega Raid Day".
            species = pokeapi.species_in(event.name)
            described = pokeapi.describe(species) if species else None
            if described:
                pokemon = {"name": described["name"], "sprite": described["sprite"]}

        if pokemon:
            _enrich(pokemon, event.event_type)
            detail["pokemon"] = pokemon

        bonuses = _bonuses_from_feed(extra)
        if bonuses:
            detail["bonuses"] = bonuses

        if detail:
            details[event.event_id] = detail

    pokeapi.save()
    return details


def _pokemon_from_feed(extra: dict[str, Any], event_type: str | None):
    """The Pokémon the feed names, for the three kinds that carry one."""
    if event_type == "pokemon-spotlight-hour":
        spotlight = extra.get("spotlight") or {}
        first = (spotlight.get("list") or [None])[0] or spotlight
        if first.get("name"):
            return {"name": first["name"], "sprite": first.get("image"),
                    "shiny": bool(first.get("canBeShiny"))}
    if event_type == "community-day":
        spawns = (extra.get("communityday") or {}).get("spawns") or []
        if spawns:
            shinies = {s.get("name") for s in
                       (extra.get("communityday") or {}).get("shinies") or []}
            return {"name": spawns[0]["name"], "sprite": spawns[0].get("image"),
                    "shiny": spawns[0]["name"] in shinies}
    if event_type == "raid-battles":
        bosses = (extra.get("raidbattles") or {}).get("bosses") or []
        if bosses:
            return {"name": bosses[0]["name"], "sprite": bosses[0].get("image"),
                    "shiny": bool(bosses[0].get("canBeShiny"))}
    return None


def _enrich(pokemon: dict[str, Any], event_type: str | None) -> None:
    """Add what PokéAPI knows: better artwork, and weaknesses where it is a
    fight. Leaves the feed's own values in place if the lookup finds nothing."""
    species = pokeapi.species_in(pokemon["name"])
    described = pokeapi.describe(species) if species else None
    if not described:
        return
    if described.get("sprite"):
        pokemon["sprite"] = described["sprite"]
    if event_type in BATTLE_TYPES:
        pokemon["weaknesses"] = described["weaknesses"]


def _bonuses_from_feed(extra: dict[str, Any]) -> list[dict[str, str]]:
    """Bonuses, in the feed's own wording and with its own icons."""
    bonuses = [
        {"text": b["text"], "icon": b.get("image", "")}
        for b in (extra.get("communityday") or {}).get("bonuses") or []
        if b.get("text")
    ]
    spotlight_bonus = (extra.get("spotlight") or {}).get("bonus")
    if spotlight_bonus:
        bonuses.append({"text": spotlight_bonus, "icon": ""})
    return bonuses


def _write(path, text: str) -> str:
    """Write a published file, reporting whether it changed.

    newline="" both ways: reading in text mode would turn CRLF into LF and the
    comparison would report a change on every run.
    """
    previous = None
    if path.exists():
        with path.open(encoding="utf-8", newline="") as handle:
            previous = handle.read()

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    return "unchanged" if text == previous else "updated"


def _attach_links(events: list[Event]) -> dict[str, str]:
    """Read the channel and attach infographic links. Never fatal.

    A calendar with correct times and no links is worth publishing. One with
    neither is not, so anything that goes wrong here is reported and stepped
    over.

    Returns event id -> the image url of the post that announced it, for the
    events that matched one. Those urls expire in about 24 hours: they are
    fetched during this run and never written anywhere.
    """
    try:
        guild_id = config.require("GUILD_ID")
        channel_id = config.require("CHANNEL_ID")
        messages = discord_src.fetch_messages(after=None)
    except RuntimeError as error:
        log.warning("%s", error)
        log.warning("publishing without infographic links")
        return {}

    posts = []
    for message in discord_src.oldest_first(messages):
        try:
            posts.append(discord_src.parse_message(message, guild_id, channel_id))
        except (ValueError, TypeError, KeyError) as error:
            log.warning("skipped message %s: %s",
                        (message or {}).get("id", "<no id>"), error)

    reconcile.attach(events, posts)

    by_link = {post.link: post for post in posts}
    return {
        event.event_id: by_link[event.discord_url].image_url
        for event in events
        if event.discord_url
        and event.discord_url in by_link
        and by_link[event.discord_url].image_url
    }


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
    subcommands.add_parser(
        "build", help=f"rebuild {config.OUTPUT_PATH.name} from the feed alone")
    subcommands.add_parser("poll", help="read new posts from the Discord channel")
    subcommands.add_parser(
        "run", help="rebuild with infographic links (what the Action runs)")

    args = parser.parse_args(argv)
    # A person is watching this now; at M5 nobody is. Either way the warnings
    # from a skipped feed record have to reach somewhere they can be read.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.command == "build":
        return build()
    if args.command == "poll":
        return poll()
    return build(with_links=True)


if __name__ == "__main__":
    sys.exit(main())
