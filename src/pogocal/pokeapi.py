"""Pokémon detail — types, weaknesses, artwork — from PokéAPI.

The Leek Duck feed names the Pokémon in an event and says nothing else about
it. PokéAPI has the rest, free and without a key.

Every answer is cached in the repository, including the failures. A warm run
makes no calls at all, which is what stops the page depending on a third
service being up.

Nothing here is fatal. A Pokémon that cannot be identified costs one picture
and one row of weakness icons.
"""

import json
import logging
import re
from typing import Any

import httpx

from pogocal import config

log = logging.getLogger(__name__)

_cache: dict[str, Any] | None = None
_dirty = False

# Anything a real species name would never contain, plus the parenthesised
# forms the feed uses: "Zamazenta (Hero of Many Battles)".
_BRACKETS = re.compile(r"\(.*?\)")
_LETTERS = re.compile(r"[^A-Za-z ]+")


def species_in(title: str) -> str | None:
    """The Pokémon an event title is about, or None if it names nobody.

    "Staraptor Super Mega Raid Day" -> "staraptor". Three real events name
    nobody at all, because Leek Duck has not announced them yet, and those
    must come back empty rather than guessing at a leftover word.
    """
    words = _LETTERS.sub(" ", _BRACKETS.sub(" ", title or "")).lower().split()
    for word in words:
        if len(word) > 2 and word not in config.TITLE_NOISE:
            return word
    return None


def describe(species: str) -> dict[str, Any] | None:
    """Everything known about one Pokémon, or None if it is not one."""
    record = _remember(f"pokemon:{species}", lambda: fetch("pokemon", species))
    if record is None:
        return None
    return {
        "name": record["name"].replace("-", " ").title(),
        "types": record["types"],
        "sprite": record["sprite"],
        "weaknesses": weaknesses(record["types"]),
    }


def weaknesses(types: list[str]) -> list[str]:
    """What beats a Pokémon of these types, worst first.

    Multiplied rather than unioned, so a resistance on one type can undo a
    weakness on the other: ground is immune to electric, flying is weak to it,
    and a dragon/ground Pokémon ends up with no electric weakness at all.
    Pokémon GO has no immunities, so one is treated as a heavy resistance.
    """
    multiplier: dict[str, float] = {}
    for kind in types:
        relations = _remember(f"type:{kind}", lambda k=kind: fetch("type", k))
        if relations is None:
            continue
        for attacker in relations["double"]:
            multiplier[attacker] = multiplier.get(attacker, 1.0) * 2
        for attacker in relations["half"]:
            multiplier[attacker] = multiplier.get(attacker, 1.0) * 0.5
        for attacker in relations["none"]:
            multiplier[attacker] = multiplier.get(attacker, 1.0) * 0.39

    beats = [(m, a) for a, m in multiplier.items() if m > 1]
    beats.sort(key=lambda pair: (-pair[0], pair[1]))
    return [attacker for _m, attacker in beats]


def fetch(kind: str, key: str) -> dict[str, Any]:
    """The only thing here that touches the network. Raises if there is no
    such Pokémon or type."""
    response = httpx.get(f"{config.POKEAPI_BASE}/{kind}/{key}",
                         timeout=config.POKEAPI_TIMEOUT, follow_redirects=True)
    if response.status_code == 404:
        raise LookupError(f"PokéAPI has no {kind} called {key!r}")
    response.raise_for_status()
    payload = response.json()

    if kind == "pokemon":
        artwork = (payload.get("sprites", {}).get("other", {})
                   .get("official-artwork", {}).get("front_default"))
        return {
            "name": payload["name"],
            "types": [t["type"]["name"] for t in payload["types"]],
            "sprite": artwork or payload.get("sprites", {}).get("front_default"),
        }

    relations = payload["damage_relations"]
    return {
        "double": [t["name"] for t in relations["double_damage_from"]],
        "half": [t["name"] for t in relations["half_damage_from"]],
        "none": [t["name"] for t in relations["no_damage_from"]],
    }


def save() -> None:
    """Write the cache, if anything new was learned."""
    global _dirty
    if not _dirty:
        return
    config.POKEAPI_CACHE.parent.mkdir(parents=True, exist_ok=True)
    # Sorted, so the committed file depends on what is known and not on the
    # order it was asked for. This file is committed; a wandering key order
    # would make the scheduled job commit noise.
    config.POKEAPI_CACHE.write_text(
        json.dumps(_load(), indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8")
    _dirty = False


def reset() -> None:
    """Forget everything held in memory. For tests, and for a cache that was
    edited on disk while a process was running."""
    global _cache, _dirty
    _cache, _dirty = None, False


def _load() -> dict[str, Any]:
    global _cache
    if _cache is None:
        _cache = {}
        if config.POKEAPI_CACHE.is_file():
            try:
                _cache = json.loads(config.POKEAPI_CACHE.read_text(encoding="utf-8"))
            except (ValueError, OSError) as error:
                log.warning("ignoring unreadable PokéAPI cache %s: %s",
                            config.POKEAPI_CACHE, error)
                _cache = {}
    return _cache


def _remember(key: str, lookup) -> Any:
    """Answer from the cache, or ask once and keep the answer.

    A failure is cached as None too. Three events in the feed name a Pokémon
    that does not exist yet, and without this every run would ask again.
    """
    global _dirty
    cache = _load()
    if key in cache:
        return cache[key]
    try:
        cache[key] = lookup()
    except (LookupError, httpx.HTTPError, ValueError, KeyError) as error:
        log.info("no PokéAPI answer for %s: %s", key, error)
        cache[key] = None
    _dirty = True
    return cache[key]
