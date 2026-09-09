"""Keeping local copies of the infographics.

The build plan's §1 said not to do this — "sidesteps mirroring someone else's
artwork". The owner reversed that on 9 Sep 2026, at full size. These tests
cover the consequences of the reversal rather than the decision itself.

Nothing here touches the network: the download itself is replaced in every
test. What is checked is the bookkeeping around it — stable names, not
fetching twice, surviving a failure, and removing what is no longer needed so
the published site stays under Pages' 1 GB cap.
"""

import logging

import pytest

from pogocal import config, images

CDN = "https://cdn.discordapp.com/attachments/1/2/SM_Stara_RD.png?ex=6aa1&is=1&hm=abc"


@pytest.fixture(autouse=True)
def image_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "IMAGE_DIR", tmp_path / "img")


@pytest.fixture
def no_network(monkeypatch):
    """Record what would have been fetched, fetch nothing."""
    fetched = []

    def fake(url, destination):
        fetched.append(url)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"PNG-ish bytes")

    monkeypatch.setattr(images, "download", fake)
    return fetched


# --- naming --------------------------------------------------------------


def test_the_name_comes_from_the_event_not_the_upload():
    """Stable, like the calendar's UID. A name taken from the uploaded
    filename would change when G47IX renames a file."""
    assert images.local_name("staraptor-2026", CDN) == "staraptor-2026.png"


def test_the_extension_survives_the_query_string():
    jpg = "https://cdn.discordapp.com/attachments/1/2/x.jpg?ex=6aa1&hm=abc"
    assert images.local_name("e", jpg) == "e.jpg"


def test_an_unrecognised_extension_falls_back_to_png():
    assert images.local_name("e", "https://example.invalid/thing") == "e.png"


def test_an_event_id_cannot_escape_the_image_directory():
    """Event ids come from someone else's feed."""
    assert "/" not in images.local_name("../../etc/passwd", CDN)


# --- fetching ------------------------------------------------------------


def test_a_missing_image_is_downloaded(no_network):
    result = images.sync({"staraptor-2026": CDN})
    assert no_network == [CDN]
    assert result == {"staraptor-2026": "img/staraptor-2026.png"}
    assert (config.IMAGE_DIR / "staraptor-2026.png").is_file()


def test_an_image_already_on_disk_is_not_fetched_again(no_network):
    images.sync({"staraptor-2026": CDN})
    no_network.clear()
    result = images.sync({"staraptor-2026": CDN})
    assert no_network == []
    assert result == {"staraptor-2026": "img/staraptor-2026.png"}


def test_the_returned_path_is_relative_to_the_published_folder(no_network):
    result = images.sync({"e": CDN})
    assert result["e"].startswith("img/")
    assert "cdn.discordapp.com" not in result["e"]


# --- one failure must not cost the rest ----------------------------------


def test_a_failed_download_is_skipped_and_the_others_still_arrive(monkeypatch, caplog):
    def flaky(url, destination):
        if "bad" in url:
            raise OSError("connection reset")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"ok")

    monkeypatch.setattr(images, "download", flaky)
    result = images.sync({"good": CDN, "bad": CDN.replace("SM_Stara_RD", "bad")})

    assert "good" in result
    assert "bad" not in result
    assert any(r.levelname in ("WARNING", "ERROR") for r in caplog.records)


def test_a_partly_written_file_is_not_left_behind(monkeypatch):
    """A download that dies halfway must not leave a truncated image that the
    next run mistakes for a complete one."""
    def dies(url, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"half")
        raise OSError("connection reset")

    monkeypatch.setattr(images, "download", dies)
    images.sync({"e": CDN})
    assert not (config.IMAGE_DIR / "e.png").exists()


# --- pruning, which is what keeps the site under Pages' 1 GB cap ---------


def test_an_image_whose_event_has_gone_is_deleted(no_network):
    images.sync({"old": CDN, "current": CDN})
    assert (config.IMAGE_DIR / "old.png").is_file()

    images.sync({"current": CDN})
    assert not (config.IMAGE_DIR / "old.png").exists()
    assert (config.IMAGE_DIR / "current.png").is_file()


def test_wanting_nothing_empties_the_directory(no_network):
    images.sync({"a": CDN, "b": CDN})
    assert images.sync({}) == {}
    assert list(config.IMAGE_DIR.glob("*")) == []


def test_pruning_says_what_it_removed(no_network, caplog):
    """Routine, so it is logged at INFO — which caplog has to be asked for."""
    images.sync({"old": CDN})
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="pogocal.images"):
        images.sync({})
    assert "old" in caplog.text


def test_nothing_at_all_is_not_an_error(no_network):
    assert images.sync({}) == {}
