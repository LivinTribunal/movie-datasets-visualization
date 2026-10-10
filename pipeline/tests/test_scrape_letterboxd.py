import gzip

import httpx
import pytest

from movies.acquire import download
from movies.scrape import letterboxd as lb

LD = (
    '<script type="application/ld+json">\n/* <![CDATA[ */\n'
    '{"@type": "Movie", "url": "https://letterboxd.com/film/finding-nemo/", '
    '"aggregateRating": {"ratingValue": 4.6, "ratingCount": 3168978}}\n/* ]]> */\n</script>'
)
FILM = f"<html>{LD}</html>"


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(download, "MIN_INTERVAL", 0)


def test_parse_cdata_wrapped():
    assert lb.parse(FILM) == {
        "lb_slug": "finding-nemo",
        "letterboxd_avg": 4.6,
        "letterboxd_ratings": 3168978,
    }


def test_parse_without_aggregate_rating():
    html = '<script type="application/ld+json">{"url": "https://letterboxd.com/film/x/"}</script>'
    assert lb.parse(html) == {"lb_slug": "x", "letterboxd_avg": None, "letterboxd_ratings": None}


def test_parse_json_ld_list_is_all_null():
    html = '<script type="application/ld+json">[{"url": "x"}]</script>'
    assert set(lb.parse(html).values()) == {None}


def test_parse_no_json_ld():
    assert set(lb.parse("<html></html>").values()) == {None}


def test_fetch_follows_redirect_caches_and_skips(tmp_path):
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req.url.path)
        if req.url.path == "/imdb/tt1/":
            return httpx.Response(302, headers={"Location": "https://letterboxd.com/film/a/"})
        if req.url.path == "/film/a/":
            return httpx.Response(200, text=FILM)
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        lb.fetch(["tt1", "tt2"], tmp_path, client)
        assert calls == ["/imdb/tt1/", "/film/a/", "/imdb/tt2/"]
        assert gzip.decompress((tmp_path / "tt1.html.gz").read_bytes()).decode() == FILM
        assert (tmp_path / "tt2.missing").exists()
        lb.fetch(["tt1", "tt2"], tmp_path, client)
    assert len(calls) == 3


def test_fetch_404_on_second_hop(tmp_path):
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.startswith("/imdb/"):
            return httpx.Response(301, headers={"Location": "/film/gone/"})
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        lb.fetch(["tt9"], tmp_path, client)
    assert (tmp_path / "tt9.missing").exists()
