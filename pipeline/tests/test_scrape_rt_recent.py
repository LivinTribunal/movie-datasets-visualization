import gzip

import httpx
import pytest

from movies.acquire import download
from movies.scrape import rt_recent as rt

CARD = (
    '<script id="media-scorecard-json"\n            data-json="mediaScorecard"\n'
    '            type="application/json">'
    '{"audienceScore":{"bandedRatingCount":"250+ Verified Ratings","reviewCount":129,'
    '"score":"64","scoreType":"VERIFIED"},'
    '"criticsScore":{"ratingCount":97,"reviewCount":97,"score":"63"}}</script>'
)
FILM = f"<html>{CARD}</html>"


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(download, "MIN_INTERVAL", 0)


def test_parse_full_scorecard():
    assert rt.parse(FILM) == {
        "tomatometer": 63,
        "rt_critic_reviews": 97,
        "audience_score": 64,
        "audience_score_type": "VERIFIED",
        "audience_ratings_band": "250+ Verified Ratings",
    }


def test_parse_empty_critics_score_keeps_audience():
    html = (
        '<script id="media-scorecard-json" type="application/json">'
        '{"audienceScore":{"score":"64","scoreType":"ALL"},"criticsScore":{"score":""}}</script>'
    )
    out = rt.parse(html)
    assert out["tomatometer"] is None
    assert out["audience_score"] == 64
    assert out["audience_score_type"] == "ALL"


def test_parse_no_scorecard():
    assert set(rt.parse("<html></html>").values()) == {None}


def test_parse_bad_json():
    html = '<script id="media-scorecard-json" type="application/json">{oops</script>'
    assert set(rt.parse(html).values()) == {None}


def test_fetch_caches_gzipped_page_and_skips_cached(tmp_path):
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req.url.path)
        return httpx.Response(200, text=FILM)

    items = [("tt1", "m/a")]
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        rt.fetch(items, tmp_path, client)
        rt.fetch(items, tmp_path, client)
    assert calls == ["/m/a"]
    assert gzip.decompress((tmp_path / "tt1.html.gz").read_bytes()).decode() == FILM


def test_fetch_404_is_missing(tmp_path):
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404))) as client:
        rt.fetch([("tt9", "m/gone")], tmp_path, client)
    assert (tmp_path / "tt9.missing").exists()
