import datetime
import json
from pathlib import Path

from movies.acquire import wikidata

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_batching_450_ids_at_200():
    ids = [f"tt{i:07d}" for i in range(450)]
    assert [len(b) for b in wikidata.batches(ids, 200)] == [200, 200, 50]


def test_batch_key_ignores_order():
    assert wikidata.batch_key(["tt2", "tt1"]) == wikidata.batch_key(["tt1", "tt2"])


def test_cache_path_depends_on_query_not_id_order():
    d = Path("cache")
    a = wikidata.cache_path(d, "money", "SELECT 1", ["tt2", "tt1"])
    assert a == wikidata.cache_path(d, "money", "SELECT 1", ["tt1", "tt2"])
    assert a != wikidata.cache_path(d, "money", "SELECT 2", ["tt1", "tt2"])
    assert a.name.startswith("money_")


def test_parse_ids_joins_multi_values_and_keeps_nulls():
    df = wikidata.aggregate_ids(wikidata.parse_ids(load("sparql_ids.json")))
    rows = {r["imdb_id"]: r for r in df.iter_rows(named=True)}
    assert df.columns == ["imdb_id", "qid", "rt_id", "mc_id", "lumiere_id", "enwiki_title"]
    assert rows["tt0000001"] == {
        "imdb_id": "tt0000001",
        "qid": "Q100",
        "rt_id": "m/first_film",
        "mc_id": "movie/first-film",
        "lumiere_id": "1234",
        "enwiki_title": "First Film",
    }
    assert rows["tt0000002"]["rt_id"] == "m/second_film|m/second_film_alt"
    assert rows["tt0000002"]["mc_id"] is None
    assert rows["tt0000003"] == {
        "imdb_id": "tt0000003",
        "qid": "Q300",
        "rt_id": None,
        "mc_id": None,
        "lumiere_id": None,
        "enwiki_title": None,
    }


def test_parse_money_floats_qids_and_null_qualifiers():
    rows = wikidata.parse_money(load("sparql_money.json"))
    assert rows[0] == (
        "tt0000001",
        "Q100",
        "budget",
        15000000.0,
        "Q4917",
        None,
        None,
        "preferred",
        None,
    )
    assert rows[1] == (
        "tt0000001",
        "Q100",
        "box_office",
        42500000.5,
        "Q4917",
        datetime.date(1999, 6, 1),
        "Q30",
        "normal",
        11,
    )
    assert isinstance(rows[0][3], float)
