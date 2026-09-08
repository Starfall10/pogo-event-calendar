"""Reading the followed channel.

Runs against tests/fixtures/messages.json — 25 real posts, sanitised — plus
hand-built messages for shapes the real channel does not currently produce.
No network, no token.

The check that matters most is the last group: the cursor must never advance
past a message that failed, because nothing will ever look at that post again.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pogocal import config, discord_src, state

FIXTURE = Path(__file__).parent / "fixtures" / "messages.json"
MESSAGES = json.loads(FIXTURE.read_text(encoding="utf-8"))

# The fixture is newest-first, as the API returns it.
NEWEST = MESSAGES[0]


def message(**overrides) -> dict:
    """A minimal well-formed message, with fields replaced as needed."""
    base = {
        "id": "1546790566434705434",
        "timestamp": "2026-09-08T07:53:29.017000+00:00",
        "content": "# Mega Staraptor Raid Day, September 19",
        "attachments": [],
        "embeds": [],
        "webhook_id": "333333333333333333",
    }
    base.update(overrides)
    return base


def attachment(url="https://cdn.discordapp.com/attachments/1/2/x.png",
               content_type="image/png") -> dict:
    return {"url": url, "proxy_url": url, "content_type": content_type,
            "filename": "x.png", "width": 100, "height": 100}


# --- finding the image -------------------------------------------------------


def test_the_image_is_found_in_attachments():
    msg = message(attachments=[attachment()])
    assert discord_src.find_image_url(msg) == attachment()["url"]


def test_the_image_is_found_in_an_embed_when_there_is_no_attachment():
    msg = message(embeds=[{"image": {"url": "https://example.invalid/in-embed.png"}}])
    assert discord_src.find_image_url(msg) == "https://example.invalid/in-embed.png"


def test_an_embed_thumbnail_is_used_as_a_last_resort():
    msg = message(embeds=[{"thumbnail": {"url": "https://example.invalid/thumb.png"}}])
    assert discord_src.find_image_url(msg) == "https://example.invalid/thumb.png"


def test_an_attachment_beats_an_embed():
    msg = message(attachments=[attachment()],
                  embeds=[{"image": {"url": "https://example.invalid/in-embed.png"}}])
    assert discord_src.find_image_url(msg) == attachment()["url"]


def test_a_message_with_no_image_anywhere_returns_none():
    assert discord_src.find_image_url(message()) is None


def test_a_non_image_attachment_is_not_treated_as_the_image():
    msg = message(attachments=[attachment(url="https://example.invalid/notes.txt",
                                          content_type="text/plain")])
    assert discord_src.find_image_url(msg) is None


def test_every_real_message_in_the_fixture_has_an_image():
    missing = [m["id"] for m in MESSAGES if discord_src.find_image_url(m) is None]
    assert missing == []


# --- the permanent link ------------------------------------------------------


def test_the_permanent_link_has_all_three_parts():
    link = discord_src.permanent_link("222", "111", "999")
    assert link == "https://discord.com/channels/222/111/999"


def test_the_link_never_contains_an_expiring_cdn_url():
    """CDN links die in about 24 hours. The deep link is what survives."""
    post = discord_src.parse_message(NEWEST, guild_id="222", channel_id="111")
    assert "cdn.discordapp.com" not in post.link
    assert post.link == f"https://discord.com/channels/222/111/{NEWEST['id']}"


# --- reading one message -----------------------------------------------------


def test_a_real_message_parses():
    post = discord_src.parse_message(NEWEST, guild_id="222", channel_id="111")
    assert post.message_id == NEWEST["id"]
    assert post.text == NEWEST["content"]
    assert post.image_url is not None
    assert post.posted_at == datetime(2026, 9, 8, 7, 53, 29, 17000, tzinfo=timezone.utc)


def test_every_real_message_parses():
    posts = [discord_src.parse_message(m, guild_id="222", channel_id="111")
             for m in MESSAGES]
    assert len(posts) == 25
    assert all(p.posted_at.tzinfo is not None for p in posts)


def test_a_message_with_no_id_is_refused():
    with pytest.raises(ValueError):
        discord_src.parse_message(message(id=""), guild_id="222", channel_id="111")


def test_a_message_with_an_unreadable_timestamp_is_refused():
    with pytest.raises(ValueError):
        discord_src.parse_message(message(timestamp="whenever"),
                                  guild_id="222", channel_id="111")


# --- ordering ----------------------------------------------------------------


def test_messages_are_turned_oldest_first():
    """The API returns newest-first. Processed in that order, the cursor would
    end up pointing at the oldest message handled."""
    ordered = discord_src.oldest_first(MESSAGES)
    assert [m["id"] for m in ordered] == [m["id"] for m in reversed(MESSAGES)]
    assert int(ordered[0]["id"]) < int(ordered[-1]["id"])


# --- the cursor rule ---------------------------------------------------------


@pytest.fixture
def cursor_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(config, "CURSOR_PATH", tmp_path / "state" / "cursor.json")
    monkeypatch.setattr(config, "CURSOR_SEED_MESSAGE_ID", None)


def three_messages() -> list[dict]:
    return [message(id="100", attachments=[attachment()]),
            message(id="200", attachments=[attachment()]),
            message(id="300", attachments=[attachment()])]


def test_a_clean_poll_advances_the_cursor_to_the_newest(cursor_in_tmp, monkeypatch):
    monkeypatch.setattr(discord_src, "fetch_messages", lambda after=None: three_messages())
    posts = discord_src.poll()
    assert [p.message_id for p in posts] == ["100", "200", "300"]
    assert state.load_cursor() == "300"


def test_a_failure_stops_the_cursor_at_the_last_success(cursor_in_tmp, monkeypatch):
    """The failing post must remain reachable on the next run."""
    broken = three_messages()
    broken[1] = message(id="200", timestamp="whenever", attachments=[attachment()])
    monkeypatch.setattr(discord_src, "fetch_messages", lambda after=None: broken)

    posts = discord_src.poll()
    assert [p.message_id for p in posts] == ["100"]
    assert state.load_cursor() == "100"


def test_a_failure_on_the_very_first_message_leaves_the_cursor_alone(cursor_in_tmp, monkeypatch):
    broken = [message(id="100", timestamp="whenever")] + three_messages()[1:]
    monkeypatch.setattr(discord_src, "fetch_messages", lambda after=None: broken)

    assert discord_src.poll() == []
    assert state.load_cursor() is None


def test_a_poll_that_finds_nothing_leaves_the_cursor_alone(cursor_in_tmp, monkeypatch):
    state.save_cursor("500")
    monkeypatch.setattr(discord_src, "fetch_messages", lambda after=None: [])
    assert discord_src.poll() == []
    assert state.load_cursor() == "500"


def test_a_failure_is_logged_loudly(cursor_in_tmp, monkeypatch, caplog):
    broken = [message(id="100", timestamp="whenever")]
    monkeypatch.setattr(discord_src, "fetch_messages", lambda after=None: broken)
    discord_src.poll()
    assert any(r.levelname in ("WARNING", "ERROR") for r in caplog.records)
