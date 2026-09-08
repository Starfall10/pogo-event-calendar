"""Matching a Discord post to the event it announces.

Every case here comes from the measurement of 25 real posts against 55 real
feed events on 8 September 2026. The dangerous ones are real: two Harvest
Festivals three days apart, and a post that scores 0.78 against an event two
months away.

The rule this file defends: a wrong match is worse than no match. An unmatched
event simply has no link. A wrongly matched one shows the wrong infographic and
nothing anywhere says so.
"""

import json
from datetime import date, datetime, timezone
from pathlib import Path

from pogocal import discord_src, reconcile
from pogocal.leekduck import parse
from pogocal.models import Event

FIXTURES = Path(__file__).parent / "fixtures"
FEED = parse(json.loads((FIXTURES / "events.min.json").read_text(encoding="utf-8")))
MESSAGES = json.loads((FIXTURES / "messages.json").read_text(encoding="utf-8"))
POSTS = [discord_src.parse_message(m, "222", "111")
         for m in discord_src.oldest_first(MESSAGES)]


def post(text: str, posted: str = "2026-09-08T07:53:29+00:00") -> discord_src.DiscordPost:
    return discord_src.DiscordPost(
        message_id="1546790566434705434",
        posted_at=datetime.fromisoformat(posted),
        text=text,
        image_url="https://cdn.discordapp.com/attachments/1/2/x.png",
        link="https://discord.com/channels/222/111/1546790566434705434",
    )


def event(name: str, start: str, event_id: str = "e") -> Event:
    return Event(event_id=event_id, name=name,
                 start=datetime.fromisoformat(start),
                 end=datetime.fromisoformat(start),
                 source="leekduck", confidence="high")


# --- slugs -------------------------------------------------------------------


def test_slug_ignores_case_and_punctuation():
    assert reconcile.slugify("Harvest Festival: Taken Over!") == "harvest festival taken over"


def test_slug_drops_words_that_appear_in_almost_every_name():
    assert reconcile.slugify("Pokemon GO Fest") == "fest"


def test_slug_folds_the_accent():
    """The feed writes Pokémon, the posts write Pokemon."""
    assert reconcile.slugify("Pokémon Horizons") == reconcile.slugify("Pokemon Horizons")


# --- reading the heading -----------------------------------------------------


def test_a_heading_splits_into_a_name_and_a_date():
    assert reconcile.heading(post("# Mega Staraptor Raid Day, September 19")) == (
        "Mega Staraptor Raid Day", date(2026, 9, 19))


def test_a_date_range_takes_the_first_date():
    assert reconcile.heading(post("# Harvest Festival, September 29-October 5")) == (
        "Harvest Festival", date(2026, 9, 29))


def test_a_post_with_no_heading_is_not_matchable():
    assert reconcile.heading(post("Twitch Drops for this weekend")) is None
    assert reconcile.heading(post("WEEKLY SCHEDULE")) is None
    assert reconcile.heading(post("https://pokemongo.com/news/x")) is None


def test_a_heading_with_no_comma_is_not_matchable():
    """Real post: '# Mega Finale - September 5th & September 6th'. One of 16.
    Left unmatched rather than special-cased."""
    assert reconcile.heading(post("# Mega Finale - September 5th & September 6th")) is None


def test_a_december_post_about_january_gets_the_next_year():
    assert reconcile.heading(post("# New Year Event, January 3",
                                  posted="2026-12-20T10:00:00+00:00")) == (
        "New Year Event", date(2027, 1, 3))


# --- matching ----------------------------------------------------------------


def test_an_exact_name_on_the_right_day_matches():
    events = [event("Mega Squads", "2026-09-08T10:00:00")]
    assert reconcile.match(post("# Mega Squads, September 8-14"), events) is events[0]


def test_a_near_name_two_months_away_does_not_match():
    """Scored 0.78 in the measurement — well above the threshold. The date
    filter is the only thing that stops it, and it must."""
    events = [event("October Community Day", "2026-10-11T14:00:00")]
    assert reconcile.match(post("# Nickit Community Day, August 16",
                                posted="2026-07-13T10:00:00+00:00"), events) is None


def test_the_right_harvest_festival_is_chosen():
    """Two real events, three days apart, similar names. On name alone the
    wrong one scores higher."""
    applin = event("Harvest Festival 2026: Applin Picking", "2026-09-29T10:00:00", "applin")
    taken = event("Harvest Festival: Taken Over", "2026-10-02T10:00:00", "taken")
    events = [applin, taken]
    assert reconcile.match(post("# Harvest Festival, September 29-October 5"), events) is applin
    assert reconcile.match(post("# Harvest Festival: Taken Over, October 2-5"), events) is taken


def test_a_name_below_the_threshold_does_not_match():
    events = [event("Mega Gyarados in Mega Raids", "2026-09-19T10:00:00")]
    assert reconcile.match(post("# Pokemon XP and Worlds 2026, September 19"), events) is None


def test_nothing_in_the_date_window_does_not_match():
    events = [event("Mega Squads", "2026-11-08T10:00:00")]
    assert reconcile.match(post("# Mega Squads, September 8-14"), events) is None


# --- attaching links ---------------------------------------------------------


def test_a_matched_event_gains_the_link_and_becomes_merged():
    events = [event("Mega Squads", "2026-09-08T10:00:00")]
    p = post("# Mega Squads, September 8-14")
    reconcile.attach(events, [p])
    assert events[0].discord_url == p.link
    assert events[0].source == "merged"


def test_an_unmatched_event_is_left_exactly_as_it_was():
    events = [event("Rattata Spotlight Hour", "2026-09-08T18:00:00")]
    reconcile.attach(events, [post("# Mega Squads, September 8-14")])
    assert events[0].discord_url is None
    assert events[0].source == "leekduck"


def test_the_newest_post_wins_when_two_match_the_same_event():
    events = [event("Mega Squads", "2026-09-08T10:00:00")]
    older = post("# Mega Squads, September 8-14", posted="2026-09-01T10:00:00+00:00")
    newer = post("# Mega Squads, September 8-14", posted="2026-09-07T10:00:00+00:00")
    newer.link = "https://discord.com/channels/222/111/999"
    reconcile.attach(events, [older, newer])
    assert events[0].discord_url == newer.link


def test_the_real_fixtures_match_exactly_the_seven_expected_events():
    """Measured 8 Sep 2026. If this number changes, the fixtures were refreshed
    or the matching rule moved; either way it wants looking at, not adjusting."""
    events = list(FEED)
    reconcile.attach(events, POSTS)
    linked = sorted(e.name for e in events if e.discord_url)
    assert linked == sorted([
        "Gible Community Day Classic",
        "Harvest Festival 2026: Applin Picking",
        "Harvest Festival: Taken Over",
        "Mega Squads",
        "Phantump Catch Mastery",
        "Pokémon Horizons: The Series Celebration Event",
        "Staraptor Super Mega Raid Day",
    ])


def test_the_other_events_keep_no_link():
    events = list(FEED)
    reconcile.attach(events, POSTS)
    assert sum(1 for e in events if e.discord_url) == 7
    assert sum(1 for e in events if e.source == "leekduck") == len(FEED) - 7
