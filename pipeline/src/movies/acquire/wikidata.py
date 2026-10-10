"""Wikidata crosswalk: IMDb id -> QID, RT / Metacritic / LUMIERE ids, enwiki title, and money.

Batches of IMDb ids go to the SPARQL endpoint (at most 1 request per second). Every raw response
is cached in data/cache/wikidata/ first and the parsers read only from that cache, so a re-run
makes no request for a batch it has already seen.
"""

import hashlib
import json
import re
import time
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import polars as pl

from movies import paths
from movies.acquire.download import make_client, request

ENDPOINT = "https://query.wikidata.org/sparql"
BATCH_SIZE = 200
MIN_INTERVAL = 1.0  # seconds between requests
TIMEOUT = 120.0  # WDQS aborts slow queries after 60 s; leave room for its error reply
MIN_VOTES = 1000
USD = "Q4917"

TMDB_CSV = "tmdb/TMDB_all_movies.csv"
IDS_OUT = "wikidata_ids.parquet"
MONEY_OUT = "wikidata_money.parquet"

IDS_QUERY = """
SELECT ?imdb ?film ?rt ?mc ?lumiere ?title WHERE {
  VALUES ?imdb { __IDS__ }
  ?film wdt:P345 ?imdb .
  OPTIONAL { ?film wdt:P1258 ?rt }
  OPTIONAL { ?film wdt:P1712 ?mc }
  OPTIONAL { ?film wdt:P4282 ?lumiere }
  OPTIONAL {
    ?article schema:about ?film ;
             schema:isPartOf <https://en.wikipedia.org/> ;
             schema:name ?title .
  }
}
"""

MONEY_QUERY = """
SELECT ?imdb ?film ?prop ?amount ?unit ?time ?place WHERE {
  VALUES ?imdb { __IDS__ }
  ?film wdt:P345 ?imdb .
  VALUES (?prop ?p ?psv) {
    ("budget" p:P2130 psv:P2130)
    ("box_office" p:P2142 psv:P2142)
  }
  ?film ?p ?st .
  ?st ?psv ?v .
  ?st wikibase:rank ?rank .
  FILTER(?rank != wikibase:DeprecatedRank)
  ?v wikibase:quantityAmount ?amount ;
     wikibase:quantityUnit ?unit .
  OPTIONAL { ?st pq:P585 ?time }
  OPTIONAL { ?st pq:P3005 ?place }
}
"""

IDS_COLUMNS = ["qid", "rt_id", "mc_id", "lumiere_id", "enwiki_title"]
MONEY_SCHEMA = {
    "imdb_id": pl.String,
    "qid": pl.String,
    "property": pl.String,
    "amount": pl.Float64,
    "unit_qid": pl.String,
    "point_in_time": pl.Date,
    "place_qid": pl.String,
}


def batches(ids: list[str], size: int = BATCH_SIZE) -> Iterator[list[str]]:
    for i in range(0, len(ids), size):
        yield ids[i : i + size]


def batch_key(batch: list[str]) -> str:
    return hashlib.sha1("\n".join(sorted(batch)).encode()).hexdigest()


def load_imdb_ids(csv: Path) -> list[str]:
    """Released films with >= 1000 IMDb votes and a well-formed IMDb id, sorted and unique."""
    names = pl.scan_csv(csv, infer_schema_length=0).collect_schema().names()
    for col in ("status", "imdb_id", "imdb_votes"):
        if col not in names:
            raise RuntimeError(f"{csv.name} has no column {col!r}; columns: {names}")
    lf = pl.scan_csv(csv, infer_schema_length=0).select(
        "status", "imdb_id", pl.col("imdb_votes").cast(pl.Float64, strict=False)
    )
    out = (
        lf.filter(
            (pl.col("status") == "Released")
            & (pl.col("imdb_votes") >= MIN_VOTES)
            & pl.col("imdb_id").str.contains(r"^tt\d+$")
        )
        .select("imdb_id")
        .unique()
        .sort("imdb_id")
        .collect()
    )
    return out["imdb_id"].to_list()


def _values(batch: list[str]) -> str:
    return " ".join(f'"{i}"' for i in batch)


def _val(binding: dict, key: str) -> str | None:
    cell = binding.get(key)
    return cell["value"] if cell else None


def _qid(uri: str | None) -> str | None:
    """`http://www.wikidata.org/entity/Q42` -> `Q42`; anything else (e.g. unknown value) -> None."""
    if uri is None:
        return None
    tail = uri.rsplit("/", 1)[-1]
    return tail if re.fullmatch(r"Q\d+", tail) else None


def _day(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:  # unknown value, or years Python cannot hold
        return None


def parse_ids(payload: dict) -> list[dict[str, str | None]]:
    rows = []
    for b in payload["results"]["bindings"]:
        rows.append(
            {
                "imdb_id": _val(b, "imdb"),
                "qid": _qid(_val(b, "film")),
                "rt_id": _val(b, "rt"),
                "mc_id": _val(b, "mc"),
                "lumiere_id": _val(b, "lumiere"),
                "enwiki_title": _val(b, "title"),
            }
        )
    return rows


def aggregate_ids(rows: list[dict[str, str | None]]) -> pl.DataFrame:
    """One row per imdb_id; several values of a property are kept as a sorted `|`-joined string."""
    acc: dict[str, dict[str, set[str]]] = {}
    for r in rows:
        cols = acc.setdefault(r["imdb_id"] or "", {c: set() for c in IDS_COLUMNS})
        for c in IDS_COLUMNS:
            if r[c] is not None:
                cols[c].add(r[c])
    data = {"imdb_id": sorted(acc)}
    for c in IDS_COLUMNS:
        data[c] = ["|".join(sorted(acc[i][c])) or None for i in data["imdb_id"]]
    return pl.DataFrame(data, schema=dict.fromkeys(["imdb_id", *IDS_COLUMNS], pl.String))


def parse_money(payload: dict) -> list[tuple]:
    """Tuples in MONEY_SCHEMA order; amounts as floats, entities as bare QIDs, absent -> None."""
    rows = []
    for b in payload["results"]["bindings"]:
        try:
            amount = float(b["amount"]["value"])
        except (KeyError, ValueError):
            continue
        rows.append(
            (
                _val(b, "imdb"),
                _qid(_val(b, "film")),
                _val(b, "prop"),
                amount,
                _qid(_val(b, "unit")),
                _day(_val(b, "time")),
                _qid(_val(b, "place")),
            )
        )
    return rows


def _sort_key(row: tuple) -> tuple:
    return tuple("" if v is None else str(v) for v in row)


def fetch_batches(ids: list[str], cache_dir: Path) -> None:
    """Query both SPARQL queries for every batch; skip any batch already in the cache."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    last = 0.0
    all_batches = list(batches(ids))
    with make_client(timeout=TIMEOUT) as client:
        for n, batch in enumerate(all_batches, 1):
            key = batch_key(batch)
            for kind, template in (("ids", IDS_QUERY), ("money", MONEY_QUERY)):
                target = cache_dir / f"{kind}_{key}.json"
                if target.exists():
                    continue
                wait = MIN_INTERVAL - (time.monotonic() - last)
                if wait > 0:
                    time.sleep(wait)
                resp = request(
                    client,
                    "POST",
                    ENDPOINT,
                    data={"query": template.replace("__IDS__", _values(batch))},
                    headers={"Accept": "application/sparql-results+json"},
                )
                last = time.monotonic()
                payload = resp.json()
                if "results" not in payload:
                    raise RuntimeError(f"unexpected SPARQL reply for batch {n} ({kind})")
                part = target.with_suffix(".part")
                part.write_text(json.dumps(payload))
                part.replace(target)
            if n % 10 == 0 or n == len(all_batches):
                print(f"  batch {n}/{len(all_batches)}", flush=True)


def _pct(n: int, total: int) -> str:
    return f"{n:,} ({100 * n / total:.1f}%)" if total else "0"


def build() -> list[Path]:
    """Run the whole crosswalk; returns the two Parquet files written."""
    csv = paths.RAW / TMDB_CSV
    if not csv.exists():
        raise RuntimeError(f"{csv} is missing; run `movies acquire --source tmdb` first")
    ids = load_imdb_ids(csv)
    print(f"  {len(ids):,} IMDb ids to query (Released, >= {MIN_VOTES} votes)", flush=True)
    cache_dir = paths.CACHE / "wikidata"
    fetch_batches(ids, cache_dir)

    id_rows: list[dict[str, str | None]] = []
    money_rows: set[tuple] = set()
    for batch in batches(ids):
        key = batch_key(batch)
        id_rows += parse_ids(json.loads((cache_dir / f"ids_{key}.json").read_text()))
        money_rows |= set(parse_money(json.loads((cache_dir / f"money_{key}.json").read_text())))

    ids_df = aggregate_ids(id_rows)
    money_df = pl.DataFrame(sorted(money_rows, key=_sort_key), schema=MONEY_SCHEMA, orient="row")
    paths.SCRAPED.mkdir(parents=True, exist_ok=True)
    out = [paths.SCRAPED / IDS_OUT, paths.SCRAPED / MONEY_OUT]
    ids_df.write_parquet(out[0])
    money_df.write_parquet(out[1])

    n = ids_df.height
    print(f"  {IDS_OUT}: {n:,} rows of {len(ids):,} queried ({_pct(n, len(ids))})")
    for c in IDS_COLUMNS:
        have = ids_df[c].is_not_null().sum()
        multi = ids_df[c].str.contains(r"\|").sum()
        print(f"    {c}: present {_pct(have, n)}; several values {multi:,}")
    print(f"  {MONEY_OUT}: {money_df.height:,} rows")
    for prop, g in money_df.group_by("property", maintain_order=True):
        usd = (g["unit_qid"] == USD).sum()
        print(f"    {prop[0]}: {g.height:,} rows, {g['imdb_id'].n_unique():,} films, USD {usd:,}")
    return out
