"""The published web page.

Day cards, each holding a poster per event. Assertions are on the text that
gets written, not on Event objects, because the page is what a browser and
GitHub Pages see.

Two things shape the signature. The page depends on the date it was built, so
`today` is passed in rather than read from the clock — a page that changed
every hour would make the scheduled job commit every hour. And everything the
feed does not carry — Pokémon artwork, weaknesses, infographics — arrives as
plain mappings, so this module never fetches anything and a missing entry is
never an error.
"""

import re
from datetime import date, datetime, timezone

import pytest

from pogocal.models import Event
from pogocal.web_build import render

TODAY = date(2026, 9, 10)

_STYLE_BLOCK = re.compile(r"<style>.*?</style>", re.S)


def markup(page: str) -> str:
    """The page without its stylesheet.

    The CSS is inlined, so every class name the page can draw also appears as a
    selector. A bare `"ribbon" in page` is true whether or not a ribbon was
    rendered — checking for absence has to look at the markup alone.
    """
    return _STYLE_BLOCK.sub("", page)


def event(name, start, end=None, kind=None, **kw):
    start = datetime.fromisoformat(start)
    return Event(
        event_id=kw.pop("event_id", None) or name.lower().replace(" ", "-"),
        name=name, start=start,
        end=datetime.fromisoformat(end) if end else start,
        source=kw.pop("source", "leekduck"), confidence="high",
        event_type=kind, **kw)


RAID_DAY = event("Staraptor Super Mega Raid Day", "2026-09-19T14:00:00",
                 "2026-09-19T17:00:00", "raid-day", event_id="staraptor-2026",
                 leekduck_url="https://leekduck.com/events/staraptor/")
COM_DAY = event("Gible Community Day Classic", "2026-09-12T14:00:00",
                "2026-09-12T17:00:00", "community-day", event_id="gible-cd")
SPOTLIGHT = event("Weedle Spotlight Hour", "2026-09-10T18:00:00",
                  "2026-09-10T19:00:00", "pokemon-spotlight-hour", event_id="spot")
SEASON = event("Twilight Trails", "2026-09-08T10:00:00",
               "2026-12-01T10:00:00", "season", event_id="season-24")
GBL = event("Great League: Mega Edition", "2026-09-15T20:00:00+00:00",
            "2026-09-22T20:00:00+00:00", "go-battle-league", event_id="gbl")

STARAPTOR = {"name": "Staraptor", "sprite": "https://img.invalid/staraptor.png",
             "types": ["normal", "flying"], "weaknesses": ["electric", "ice", "rock"]}


# --- what the page contains ----------------------------------------------


def test_the_page_is_html_and_names_itself():
    page = render([RAID_DAY], today=TODAY)
    assert "<title>" in page and "Pokémon GO" in page


def test_an_upcoming_event_gets_a_poster():
    assert "Staraptor Super Mega Raid Day" in render([RAID_DAY], today=TODAY)


def test_an_event_that_has_finished_is_gone():
    past = event("Water Festival", "2026-08-18T10:00:00", "2026-08-24T20:00:00", "event")
    page = render([past, RAID_DAY], today=TODAY)
    assert "Water Festival" not in page


def test_an_event_running_today_still_appears():
    running = event("Mega Squads", "2026-09-08T10:00:00", "2026-09-14T20:00:00", "event")
    assert "Mega Squads" in render([running], today=TODAY)


def test_events_are_grouped_into_days_in_order():
    page = render([RAID_DAY, COM_DAY], today=TODAY)
    assert page.index("Gible") < page.index("Staraptor")


def test_today_is_marked():
    assert "now" in render([SPOTLIGHT], today=TODAY)


# --- the page is not the calendar: it shows less --------------------------


def test_battle_league_is_left_off():
    """Twelve of the feed's events are league rotations. They stay in the
    calendar file and off the page, because the owner does not want them."""
    page = markup(render([GBL, RAID_DAY], today=TODAY))
    assert "Great League" not in page
    assert "Staraptor" in page


def test_only_the_global_wild_area_is_shown():
    sendai = event("Pokémon GO Wild Area 2026: Sendai", "2026-11-06T09:00:00",
                   "2026-11-08T18:00:00", "wild-area", event_id="wa-sendai")
    worldwide = event("Pokémon GO Wild Area 2026: Global", "2026-11-14T10:00:00",
                      "2026-11-16T18:00:00", "wild-area", event_id="wa-global")
    page = markup(render([sendai, worldwide], today=TODAY))
    assert "Sendai" not in page
    assert "Global" in page


# --- the long-running things become ribbons -------------------------------


def test_something_running_for_months_is_a_ribbon_not_a_poster():
    """A season is not on any particular day, so repeating it inside fourteen
    day cards says nothing."""
    page = markup(render([SEASON], today=TODAY))
    assert '<div class="ribbon"' in page
    assert "Twilight Trails" in page


def test_a_ribbon_counts_down_in_days():
    assert "82 days" in render([SEASON], today=TODAY)


def test_a_short_event_stays_a_poster():
    page = markup(render([COM_DAY], today=TODAY))
    assert "Gible Community Day Classic" in page
    assert '<div class="ribbon"' not in page


# --- Pokémon detail, where it is known ------------------------------------


def test_a_poster_shows_the_pokemon_and_its_weaknesses():
    page = render([RAID_DAY], today=TODAY,
                  details={"staraptor-2026": {"pokemon": STARAPTOR}})
    assert "https://img.invalid/staraptor.png" in page
    assert "Staraptor" in page
    for weakness in ("electric", "ice", "rock"):
        assert weakness in page


def test_weaknesses_are_drawn_as_type_symbols():
    page = render([RAID_DAY], today=TODAY,
                  details={"staraptor-2026": {"pokemon": STARAPTOR}})
    assert "<svg" in page
    assert "#dcae00" in page          # the electric colour, from type_icons


def test_an_event_with_no_pokemon_still_renders():
    """Three real events name nobody yet, and most events never will."""
    page = render([RAID_DAY, COM_DAY], today=TODAY, details={})
    assert "Staraptor Super Mega Raid Day" in page
    assert "Gible Community Day Classic" in page


def test_a_shiny_is_marked_only_when_the_feed_says_so():
    shiny = {"pokemon": dict(STARAPTOR, shiny=True)}
    marked = markup(render([RAID_DAY], today=TODAY, details={"staraptor-2026": shiny}))
    plain = markup(render([RAID_DAY], today=TODAY,
                          details={"staraptor-2026": {"pokemon": STARAPTOR}}))
    assert '<span class="spark"' in marked
    assert '<span class="spark"' not in plain


def test_bonuses_are_listed_with_the_feeds_own_icons_and_wording():
    detail = {"bonuses": [{"text": "3× Catch XP",
                           "icon": "https://cdn.invalid/xp.png"}]}
    page = render([COM_DAY], today=TODAY, details={"gible-cd": detail})
    assert "3× Catch XP" in page
    assert "https://cdn.invalid/xp.png" in page


# --- links ----------------------------------------------------------------


def test_the_infographic_is_shown_where_one_was_matched():
    page = render([RAID_DAY], today=TODAY, images={"staraptor-2026": "img/star.png"})
    assert "img/star.png" in page
    assert "G47IX" in page


def test_no_expiring_cdn_url_ever_reaches_the_page():
    linked = event("Staraptor Super Mega Raid Day", "2026-09-19T14:00:00",
                   "2026-09-19T17:00:00", "raid-day", event_id="staraptor-2026",
                   discord_url="https://discord.com/channels/2/1/9", source="merged")
    page = render([linked], today=TODAY, images={"staraptor-2026": "img/star.png"})
    assert "cdn.discordapp.com" not in page


def test_the_page_offers_the_calendar_to_subscribe_to():
    assert "pogo.ics" in render([RAID_DAY], today=TODAY)


# --- safety and stability -------------------------------------------------


def test_a_name_with_html_in_it_is_escaped():
    nasty = event("Fire & Ice <script>alert(1)</script>", "2026-09-20T10:00:00")
    page = render([nasty], today=TODAY)
    assert "<script>alert(1)</script>" not in page
    assert "Fire &amp; Ice" in page


def test_the_same_day_renders_identical_bytes():
    a = render([RAID_DAY, COM_DAY, SEASON], today=TODAY)
    b = render([RAID_DAY, COM_DAY, SEASON], today=TODAY)
    assert a == b


def test_an_empty_feed_still_renders_a_page():
    page = render([], today=TODAY)
    assert "<title>" in page
