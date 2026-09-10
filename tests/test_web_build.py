"""The published web page.

Same shape as test_ics_build.py: assert on the text that gets written, not on
the objects, because the page is what a browser and GitHub Pages actually see.

The page depends on the date it is built, which the calendar file does not.
That is why render() takes `today` rather than reading the clock: a page that
changes with the clock would make the scheduled job commit on every run.
"""

from datetime import date, datetime, timezone

import pytest

from pogocal.models import Event
from pogocal.web_build import render

TODAY = date(2026, 9, 9)


def event(name, start, end=None, event_id=None, **kw):
    start = datetime.fromisoformat(start)
    return Event(
        event_id=event_id or name.lower().replace(" ", "-"),
        name=name,
        start=start,
        end=datetime.fromisoformat(end) if end else start,
        source=kw.pop("source", "leekduck"),
        confidence="high",
        **kw,
    )


RAID_DAY = event("Staraptor Super Mega Raid Day", "2026-09-19T14:00:00",
                 "2026-09-19T17:00:00", event_type="raid-day",
                 summary_lines=["Raid Day"],
                 discord_url="https://discord.com/channels/2/1/9",
                 leekduck_url="https://leekduck.com/events/staraptor/",
                 source="merged")
GBL = event("Twilight Trails", "2026-09-15T20:00:00+00:00",
            "2026-09-15T21:00:00+00:00", event_type="go-battle-league")
PAST = event("Water Festival", "2026-08-18T10:00:00", "2026-08-24T20:00:00")
TODAYS = event("Mega Squads", "2026-09-08T10:00:00", "2026-09-14T20:00:00",
               event_type="event")


# --- what appears --------------------------------------------------------


def test_the_page_is_html_with_a_title():
    page = render([RAID_DAY], today=TODAY)
    assert "<title>" in page
    assert "Pokémon GO" in page


def test_an_upcoming_event_appears():
    page = render([RAID_DAY], today=TODAY)
    assert "Staraptor Super Mega Raid Day" in page


def test_an_event_that_has_finished_does_not_appear():
    page = render([PAST, RAID_DAY], today=TODAY)
    assert "Water Festival" not in page
    assert "Staraptor Super Mega Raid Day" in page


def test_an_event_running_now_still_appears():
    """It started before today and has not ended. Still worth showing."""
    page = render([TODAYS], today=TODAY)
    assert "Mega Squads" in page


def test_events_are_grouped_by_month_in_order():
    october = event("Harvest Festival: Taken Over", "2026-10-02T10:00:00",
                    "2026-10-05T20:00:00")
    page = render([october, RAID_DAY], today=TODAY)
    assert page.index("September 2026") < page.index("October 2026")
    assert page.index("Staraptor") < page.index("Harvest Festival")


# --- the distinction this project is built on ----------------------------


def test_a_floating_event_is_marked_local():
    page = render([RAID_DAY], today=TODAY)
    assert "14:00–17:00" in page
    assert "local time" in page


def test_a_fixed_event_is_marked_utc():
    page = render([GBL], today=TODAY)
    assert "UTC" in page
    assert "20:00" in page


def test_both_kinds_are_explained_on_the_page():
    page = render([RAID_DAY, GBL], today=TODAY)
    assert "same clock time everywhere" in page


# --- links ---------------------------------------------------------------


def test_a_matched_event_links_to_its_infographic():
    page = render([RAID_DAY], today=TODAY)
    assert "https://discord.com/channels/2/1/9" in page


def test_an_unmatched_event_has_no_infographic_link():
    """The word itself appears in the header count and the footer credit, so
    the check is for the link element, not the word."""
    page = render([GBL], today=TODAY)
    assert 'class="lk ig"' not in page
    assert "discord.com/channels" not in page


def test_the_page_offers_the_calendar_to_subscribe_to():
    page = render([RAID_DAY], today=TODAY)
    assert "pogo.ics" in page


def test_no_expiring_cdn_url_ever_reaches_the_page():
    """Discord image URLs die in about 24 hours. Same rule as the calendar."""
    page = render([RAID_DAY, GBL], today=TODAY)
    assert "cdn.discordapp.com" not in page


# --- infographics --------------------------------------------------------
#
# The images are hosted by this repository, at full size, because the owner
# asked for that on 9 Sep 2026. It reverses the build plan's §1 non-goal
# ("keeping copies of the images"). Two consequences that shape these tests:
# an event with no local copy must still render, and the page must reference
# the local file rather than the Discord CDN, whose URLs expire.


def test_an_event_with_a_local_image_shows_it():
    page = render([RAID_DAY], today=TODAY,
                  images={RAID_DAY.event_id: "img/staraptor.png"})
    assert "img/staraptor.png" in page
    assert "<img" in page


def test_the_image_is_behind_a_disclosure_so_the_list_stays_dense():
    """49 events. Opening them one at a time keeps the page scannable, and
    nothing loads until asked."""
    page = render([RAID_DAY], today=TODAY,
                  images={RAID_DAY.event_id: "img/staraptor.png"})
    assert "<details" in page
    assert "<summary" in page


def test_an_image_is_not_fetched_until_it_is_opened():
    page = render([RAID_DAY], today=TODAY,
                  images={RAID_DAY.event_id: "img/staraptor.png"})
    assert 'loading="lazy"' in page


def test_an_event_with_no_local_image_still_renders():
    """Most events have none, and a matched event may not have been downloaded
    yet. Neither is an error."""
    page = render([RAID_DAY, GBL], today=TODAY, images={})
    assert "Staraptor Super Mega Raid Day" in page
    assert "Twilight Trails" in page
    assert "<img" not in page


def test_the_page_never_references_the_discord_cdn_for_an_image():
    """The local copy is what gets shown. The CDN url expires in about a day."""
    page = render([RAID_DAY], today=TODAY,
                  images={RAID_DAY.event_id: "img/staraptor.png"})
    assert "cdn.discordapp.com" not in page


def test_the_artwork_is_credited_where_it_is_shown():
    page = render([RAID_DAY], today=TODAY,
                  images={RAID_DAY.event_id: "img/staraptor.png"})
    assert "G47IX" in page


def test_images_are_optional_and_default_to_none():
    """build, which never touches Discord, calls render without them."""
    assert "Staraptor" in render([RAID_DAY], today=TODAY)


# --- safety and stability ------------------------------------------------


def test_a_name_with_html_in_it_is_escaped():
    nasty = event("Fire & Ice <script>alert(1)</script>", "2026-09-20T10:00:00")
    page = render([nasty], today=TODAY)
    assert "<script>alert(1)</script>" not in page
    assert "Fire &amp; Ice" in page


def test_the_same_day_renders_identical_bytes():
    """The scheduled job commits on any change. A page that differs between two
    runs on the same day would commit noise."""
    assert render([RAID_DAY, GBL], today=TODAY) == render([RAID_DAY, GBL], today=TODAY)


def test_an_empty_calendar_still_renders_a_page():
    page = render([], today=TODAY)
    assert "<title>" in page
    assert "0" in page
