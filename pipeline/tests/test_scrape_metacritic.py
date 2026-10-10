import gzip

import httpx
import pytest

from movies.acquire import download
from movies.scrape import metacritic as mc

LD = (
    '<script type="application/ld+json">{"@type": "Movie", "aggregateRating": '
    '{"name": "Metascore", "ratingValue": 82, "reviewCount": 22}}</script>'
)
USER = '<span title="User score 9.3 out of 10">9.3</span> Based on 2,244 User Ratings'


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(download, "MIN_INTERVAL", 0)


def test_parse_full():
    got = mc.parse(f"<html>{LD}{USER}</html>")
    assert got == {
        "metascore": 82,
        "mc_critic_reviews": 22,
        "mc_user_score": 9.3,
        "mc_user_ratings": 2244,
    }


def test_parse_no_metascore():
    got = mc.parse(f"<html>{USER}</html>")
    assert got["metascore"] is None and got["mc_critic_reviews"] is None
    assert got["mc_user_score"] == 9.3


def test_parse_card_without_rating_count_is_ignored():
    got = mc.parse('<html><a title="User score 7.1 out of 10">7.1</a></html>')
    assert got["mc_user_score"] is None and got["mc_user_ratings"] is None


def test_parse_string_and_non_numeric_metascore():
    def ld(value: str) -> str:
        return (
            '<script type="application/ld+json">{"aggregateRating": '
            f'{{"ratingValue": {value}, "reviewCount": "22"}}}}</script>'
        )

    got = mc.parse(ld('"83.0"'))
    assert got["metascore"] == 83 and got["mc_critic_reviews"] == 22
    assert mc.parse(ld('"tbd"'))["metascore"] is None


def test_parse_tbd_and_singular():
    got = mc.parse('<a title="User score tbd out of 10"></a> Based on 1 User Rating')
    assert got["mc_user_score"] is None
    assert got["mc_user_ratings"] == 1


def test_parse_empty_page():
    assert set(mc.parse("<html></html>").values()) == {None}


def test_fetch_404_cached_as_missing_and_cached_skipped(tmp_path):
    (tmp_path / "tt1.html.gz").write_bytes(gzip.compress(b"x"))
    requested = []

    def handler(req: httpx.Request) -> httpx.Response:
        requested.append(req.url.path)
        if req.url.path == "/movie/gone/":
            return httpx.Response(404)
        return httpx.Response(200, text="<html>ok</html>")

    items = [("tt1", "movie/a"), ("tt2", "movie/gone"), ("tt3", "movie/b")]
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        mc.fetch(items, tmp_path, client)
    assert requested == ["/movie/gone/", "/movie/b/"]
    assert (tmp_path / "tt2.missing").exists()
    assert gzip.decompress((tmp_path / "tt3.html.gz").read_bytes()) == b"<html>ok</html>"


def test_fetch_redirect_without_location_cached_as_missing(tmp_path, monkeypatch):
    # Metacritic answers some moved pages with a bare 301 and a "Server Error" body
    monkeypatch.setattr(download, "MIN_INTERVAL", 0)

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(301, json={"error": True, "message": "Server Error"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        mc.fetch([("tt1", "movie/the-wizard-of-oz-1939")], tmp_path, client)
    assert (tmp_path / "tt1.missing").exists()
