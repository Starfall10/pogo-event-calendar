"""The cursor: the record of which Discord post was last processed.

Small file, three failure modes that all matter. Lose the cursor and the next
run reprocesses the channel. Advance it past a message that failed and that
post is unreachable forever, because nothing will ever look at it again. Write
a timestamp into it and the scheduled job commits a changed file every run.
"""

import json

import pytest

from pogocal import config, state


@pytest.fixture(autouse=True)
def cursor_in_tmp(tmp_path, monkeypatch):
    """Point the cursor at a temporary file, never the real one."""
    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(config, "CURSOR_PATH", tmp_path / "state" / "cursor.json")
    monkeypatch.setattr(config, "CURSOR_SEED_MESSAGE_ID", None)


# --- where a run starts ------------------------------------------------------


def test_with_no_cursor_and_no_seed_there_is_no_starting_point():
    assert state.load_cursor() is None


def test_with_no_cursor_the_seed_is_used(monkeypatch):
    monkeypatch.setattr(config, "CURSOR_SEED_MESSAGE_ID", "1546790566434705434")
    assert state.load_cursor() == "1546790566434705434"


def test_the_saved_cursor_beats_the_seed(monkeypatch):
    """The seed is a starting point, not a setting. Once the file exists it wins."""
    monkeypatch.setattr(config, "CURSOR_SEED_MESSAGE_ID", "1111111111111111111")
    state.save_cursor("2222222222222222222")
    assert state.load_cursor() == "2222222222222222222"


# --- writing -----------------------------------------------------------------


def test_saving_then_loading_returns_the_same_id():
    state.save_cursor("1546790566434705434")
    assert state.load_cursor() == "1546790566434705434"


def test_saving_creates_the_state_directory():
    assert not config.STATE_DIR.exists()
    state.save_cursor("1546790566434705434")
    assert config.CURSOR_PATH.is_file()


def test_saving_the_same_id_twice_writes_identical_bytes():
    """No timestamp, no counter. A scheduled run that found nothing new must not
    produce a changed file, or the job commits noise every time it fires."""
    state.save_cursor("1546790566434705434")
    first = config.CURSOR_PATH.read_bytes()
    state.save_cursor("1546790566434705434")
    assert config.CURSOR_PATH.read_bytes() == first


def test_a_later_save_replaces_the_earlier_one():
    state.save_cursor("1111111111111111111")
    state.save_cursor("2222222222222222222")
    assert state.load_cursor() == "2222222222222222222"
    assert json.loads(config.CURSOR_PATH.read_text())["last_message_id"] == "2222222222222222222"


def test_an_id_that_is_not_a_snowflake_is_refused():
    for bad in ("", "   ", "not-an-id", "12.5", None):
        with pytest.raises(ValueError):
            state.save_cursor(bad)


# --- a damaged cursor file fails loudly, it does not reset silently ----------


def test_unreadable_json_raises_rather_than_starting_over():
    config.STATE_DIR.mkdir(parents=True)
    config.CURSOR_PATH.write_text("{ this is not json")
    with pytest.raises(RuntimeError, match="cursor"):
        state.load_cursor()


def test_json_without_the_expected_key_raises():
    config.STATE_DIR.mkdir(parents=True)
    config.CURSOR_PATH.write_text('{"something_else": "1"}')
    with pytest.raises(RuntimeError, match="cursor"):
        state.load_cursor()
