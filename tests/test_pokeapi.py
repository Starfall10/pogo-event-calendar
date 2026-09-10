"""Pokémon detail: types, weaknesses, artwork.

The Leek Duck feed names the Pokémon in an event and says nothing about what it
is or what beats it. PokéAPI answers both, and every answer is cached in the
repository so a warm run makes no calls at all.

Nothing here touches the network — `fetch` is replaced in every test. What is
checked is the parsing, the weakness arithmetic and the caching, because those
are what can be wrong without anything failing.
"""

import json

import pytest

from pogocal import config, pokeapi

POKEMON = {
    "staraptor": {"name": "staraptor", "types": ["normal", "flying"],
                  "sprite": "https://img.invalid/staraptor.png"},
    "gible": {"name": "gible", "types": ["dragon", "ground"],
              "sprite": "https://img.invalid/gible.png"},
    "zamazenta": {"name": "zamazenta", "types": ["fighting"],
                  "sprite": "https://img.invalid/zamazenta.png"},
}
# Only the relations these tests need.
RELATIONS = {
    "normal": {"double": [], "half": [], "none": ["ghost"]},
    "flying": {"double": ["rock", "electric", "ice"], "half": ["grass", "fighting", "bug"],
               "none": ["ground"]},
    "dragon": {"double": ["ice", "dragon", "fairy"], "half": ["fire", "water", "grass", "electric"],
               "none": []},
    "ground": {"double": ["water", "grass", "ice"], "half": ["poison", "rock"],
               "none": ["electric"]},
    "fighting": {"double": ["flying", "psychic", "fairy"], "half": ["rock", "bug", "dark"],
                 "none": []},
}


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    """A fresh cache, and no network under any circumstances."""
    monkeypatch.setattr(config, "POKEAPI_CACHE", tmp_path / "pokeapi.json")
    pokeapi.reset()

    calls = []

    def fake(kind, key):
        calls.append((kind, key))
        if kind == "pokemon":
            if key not in POKEMON:
                raise LookupError(f"no such pokemon: {key}")
            return POKEMON[key]
        if key not in RELATIONS:
            raise LookupError(f"no such type: {key}")
        return RELATIONS[key]

    monkeypatch.setattr(pokeapi, "fetch", fake)
    return calls


# --- reading a name out of an event title --------------------------------


@pytest.mark.parametrize("title, expected", [
    ("Staraptor Super Mega Raid Day", "staraptor"),
    ("Dynamax Rhyhorn during Max Monday", "rhyhorn"),
    ("Gigantamax Cinderace Max Battle Day", "cinderace"),
    ("Mega Beedrill in Mega Raids", "beedrill"),
    ("Gible Community Day Classic", "gible"),
    ("Zamazenta (Hero of Many Battles) Raid Hour", "zamazenta"),
])
def test_the_pokemon_is_read_out_of_the_title(title, expected):
    assert pokeapi.species_in(title) == expected


def test_a_title_naming_no_pokemon_gives_nothing():
    """Three real events name nobody: Leek Duck has not announced them yet."""
    assert pokeapi.species_in("Super Mega Raid Day") is None
    assert pokeapi.species_in("Max Battle Day") is None


# --- weaknesses ----------------------------------------------------------


def test_a_single_type_takes_its_own_weaknesses():
    """Worst first, then alphabetically. Ties are broken by name rather than by
    the order PokéAPI happened to return, so the committed cache and the
    published page do not change if that order ever does."""
    assert pokeapi.describe("zamazenta")["weaknesses"] == ["fairy", "flying", "psychic"]


def test_two_types_combine():
    """Normal/flying: flying's weaknesses survive, and ghost is cancelled by
    normal's immunity rather than counting as a weakness."""
    assert pokeapi.describe("staraptor")["weaknesses"] == ["electric", "ice", "rock"]


def test_a_double_weakness_comes_first():
    """Gible is dragon/ground, so ice hits it twice over."""
    assert pokeapi.describe("gible")["weaknesses"][0] == "ice"


def test_what_one_type_resists_the_other_can_undo():
    """Ground is immune to electric; flying is weak to it. Neither cancels for
    Staraptor, but the arithmetic has to be multiplicative to get that right."""
    assert "electric" in pokeapi.describe("staraptor")["weaknesses"]
    assert "electric" not in pokeapi.describe("gible")["weaknesses"]


# --- what a caller gets --------------------------------------------------


def test_a_description_carries_the_name_types_and_artwork():
    described = pokeapi.describe("gible")
    assert described["name"] == "Gible"
    assert described["types"] == ["dragon", "ground"]
    assert described["sprite"] == "https://img.invalid/gible.png"


def test_an_unknown_pokemon_is_not_an_error():
    """A misparsed title costs one picture, not the run."""
    assert pokeapi.describe("notapokemon") is None


# --- the cache, which is the point ---------------------------------------


def test_asking_twice_only_calls_once(offline):
    pokeapi.describe("gible")
    before = len(offline)
    pokeapi.describe("gible")
    assert len(offline) == before


def test_the_cache_survives_being_written_and_read_back(offline):
    pokeapi.describe("gible")
    pokeapi.save()
    assert config.POKEAPI_CACHE.is_file()

    pokeapi.reset()
    offline.clear()
    assert pokeapi.describe("gible")["types"] == ["dragon", "ground"]
    assert offline == []


def test_a_failed_lookup_is_remembered_too(offline):
    """Otherwise every run retries the same three unannounced events."""
    pokeapi.describe("notapokemon")
    before = len(offline)
    pokeapi.describe("notapokemon")
    assert len(offline) == before


def test_a_damaged_cache_is_ignored_rather_than_fatal(offline, caplog):
    config.POKEAPI_CACHE.parent.mkdir(parents=True, exist_ok=True)
    config.POKEAPI_CACHE.write_text("{ not json")
    pokeapi.reset()
    assert pokeapi.describe("gible")["types"] == ["dragon", "ground"]


def test_saving_twice_writes_identical_bytes(offline):
    """The cache is committed. A dict order that wandered would make the
    scheduled job commit noise."""
    pokeapi.describe("gible"); pokeapi.describe("staraptor")
    pokeapi.save()
    first = config.POKEAPI_CACHE.read_bytes()
    pokeapi.save()
    assert config.POKEAPI_CACHE.read_bytes() == first
