import json

import httpx
import pytest

from movies.acquire import download
from movies.scrape import tmdb_collections as tc

COLLECTION = {"id": 10, "name": "Star Wars Collection", "poster_path": None, "backdrop_path": None}


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(download, "MIN_INTERVAL", 0)


def run_fetch(ids, cache_dir, handler, key="SECRETKEY"):
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        tc.fetch(ids, cache_dir, key, client)


def test_parse():
    got = tc.parse({"id": 11, "belongs_to_collection": COLLECTION})
    assert got == {"tmdb_id": 11, "collection_id": 10, "collection_name": "Star Wars Collection"}
    nulls = {"collection_id": None, "collection_name": None}
    assert tc.parse({"id": 12, "belongs_to_collection": None}) == {"tmdb_id": 12, **nulls}
    assert tc.parse({"id": 13, "not_found": True}) == {"tmdb_id": 13, **nulls}


def test_fetch_caches_skips_and_handles_404(tmp_path):
    (tmp_path / "1.json").write_text(json.dumps({"id": 1, "belongs_to_collection": None}))
    requested = []

    def handler(req: httpx.Request) -> httpx.Response:
        requested.append(req.url.path)
        if req.url.path.endswith("/3"):
            return httpx.Response(404, json={"status_code": 34})
        return httpx.Response(200, json={"id": 2, "belongs_to_collection": COLLECTION})

    run_fetch([1, 2, 3], tmp_path, handler)
    assert requested == ["/3/movie/2", "/3/movie/3"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["1.json", "2.json", "3.json"]
    assert json.loads((tmp_path / "3.json").read_text()) == {"id": 3, "not_found": True}
    assert tc.parse(json.loads((tmp_path / "2.json").read_text()))["collection_id"] == 10


def test_key_is_a_query_param_and_never_cached(tmp_path):
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req.url.params.get("api_key"))
        return httpx.Response(200, json={"id": 5, "belongs_to_collection": None})

    run_fetch([5], tmp_path, handler)
    assert seen == ["SECRETKEY"]
    for p in tmp_path.iterdir():
        assert "SECRETKEY" not in p.name
        assert "SECRETKEY" not in p.read_text()


def test_error_message_does_not_leak_the_key(tmp_path):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"status_message": "Invalid API key"})

    with pytest.raises(RuntimeError) as err:
        run_fetch([5], tmp_path, handler)
    assert "401" in str(err.value)
    assert "SECRETKEY" not in str(err.value)
    assert err.value.__cause__ is None and err.value.__suppress_context__


def test_api_key_missing(monkeypatch):
    monkeypatch.delenv("TMDB_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="TMDB_API_KEY"):
        tc.api_key()


def test_parse_parts_null_date_for_empty_string():
    payload = {
        "id": 10,
        "name": "Star Wars Collection",
        "parts": [
            {"id": 11, "title": "A", "release_date": "1977-05-25"},
            {"id": 12, "title": "B", "release_date": ""},
        ],
    }
    got = tc.parse_parts(payload)
    assert [(p["tmdb_id"], p["release_date"]) for p in got] == [(11, "1977-05-25"), (12, None)]
    assert got[0]["collection_id"] == 10 and got[0]["collection_name"] == "Star Wars Collection"
    assert tc.parse_parts({"id": 9, "not_found": True}) == []


def test_collection_fetch_uses_its_endpoint_and_hides_the_key(tmp_path):
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/3/collection/10"
        return httpx.Response(500)

    with pytest.raises(RuntimeError) as err:
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            tc.fetch([10], tmp_path, "SECRETKEY", client, tc.COLLECTION_ENDPOINT, "collection")
    assert "500" in str(err.value) and "collection 10" in str(err.value)
    assert "SECRETKEY" not in str(err.value)
