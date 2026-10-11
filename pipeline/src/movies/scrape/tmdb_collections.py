"""TMDB collections: the franchise (collection) of every notable film, for task T6.

`/3/movie/{tmdb_id}` is fetched at most 1 request per second. Every raw reply is cached in
data/cache/tmdb_movie/<tmdb_id>.json first and the parser reads only from that cache, so an
interrupted run resumes and a re-run makes no request for an id it has already seen. The API key
is sent as a query parameter and is never written to the cache or printed.
"""

import json
import os
from pathlib import Path

import httpx
import polars as pl

from movies import paths
from movies.acquire.download import make_client, request

ENDPOINT = "https://api.themoviedb.org/3/movie/{}"
COLLECTION_ENDPOINT = "https://api.themoviedb.org/3/collection/{}"
OUT = "tmdb_collections.parquet"
PARTS_OUT = "tmdb_collection_parts.parquet"
CACHE_DIR = paths.CACHE / "tmdb_movie"
COLLECTION_CACHE_DIR = paths.CACHE / "tmdb_collection"
PROGRESS_EVERY = 500

SCHEMA = {
    "imdb_id": pl.String,
    "tmdb_id": pl.Int64,
    "collection_id": pl.Int64,
    "collection_name": pl.String,
}
PARTS_SCHEMA = {
    "collection_id": pl.Int64,
    "collection_name": pl.String,
    "tmdb_id": pl.Int64,
    "title": pl.String,
    "release_date": pl.Date,
}


def api_key() -> str:
    key = os.environ.get("TMDB_API_KEY", "")
    if not key:
        raise RuntimeError("TMDB_API_KEY is not set; load it with `set -a; . ./.env; set +a`")
    return key


def fetch(
    ids: list[int],
    cache_dir: Path,
    key: str,
    client: httpx.Client,
    endpoint: str = ENDPOINT,
    label: str = "movie",
) -> None:
    """GET every id that is not cached yet; a 404 is cached as `not_found`, other errors raise.

    The error raised never carries the url, so the key cannot reach a log.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    for n, tmdb_id in enumerate(ids, 1):
        target = cache_dir / f"{tmdb_id}.json"
        if not target.exists():
            try:
                payload = request(
                    client, "GET", endpoint.format(tmdb_id), params={"api_key": key}
                ).json()
            except httpx.HTTPStatusError as err:
                status = err.response.status_code
                if status != 404:
                    # httpx's message holds the full url, api_key included
                    raise RuntimeError(f"TMDB answered {status} for {label} {tmdb_id}") from None
                payload = {"id": tmdb_id, "not_found": True}
            part = target.with_suffix(".part")
            part.write_text(json.dumps(payload))
            part.replace(target)
        if n % PROGRESS_EVERY == 0 or n == len(ids):
            print(f"  {n}/{len(ids)}", flush=True)


def parse(payload: dict) -> dict:
    coll = None if payload.get("not_found") else payload.get("belongs_to_collection")
    return {
        "tmdb_id": payload["id"],
        "collection_id": coll["id"] if coll else None,
        "collection_name": coll["name"] if coll else None,
    }


def parse_parts(payload: dict) -> list[dict]:
    """The parts of one cached collection reply; an empty release date becomes null."""
    if payload.get("not_found"):
        return []
    return [
        {
            "collection_id": payload["id"],
            "collection_name": payload["name"],
            "tmdb_id": part["id"],
            "title": part.get("title"),
            "release_date": part.get("release_date") or None,
        }
        for part in payload.get("parts", [])
    ]


def build_parts(collection_ids: list[int], client: httpx.Client, key: str) -> Path:
    fetch(collection_ids, COLLECTION_CACHE_DIR, key, client, COLLECTION_ENDPOINT, "collection")
    rows = [
        part
        for i in collection_ids
        for part in parse_parts(json.loads((COLLECTION_CACHE_DIR / f"{i}.json").read_text()))
    ]
    df = (
        pl.DataFrame(rows, schema={**PARTS_SCHEMA, "release_date": pl.String})
        .with_columns(pl.col("release_date").str.to_date("%Y-%m-%d", strict=False))
        .select(list(PARTS_SCHEMA))
        .sort("collection_id", "release_date", "tmdb_id")
    )
    out = paths.SCRAPED / PARTS_OUT
    df.write_parquet(out)
    print(f"  {PARTS_OUT}: {len(collection_ids):,} collections fetched, {df.height:,} parts")
    return out


def build() -> Path:
    films = paths.INTERIM / "films.parquet"
    if not films.exists():
        raise RuntimeError(f"{films} is missing; run `movies join` first")
    # ponytail: notable subset only (~13k calls, ~3.6 h at 1 req/s);
    # widen to the working subset if T6 needs it
    ids_df = (
        pl.read_parquet(films, columns=["imdb_id", "tmdb_id", "notable"])
        .filter(pl.col("notable") & pl.col("tmdb_id").is_not_null())
        .select("imdb_id", "tmdb_id")
        .unique("tmdb_id")
    )
    ids = sorted(ids_df["tmdb_id"].to_list())
    print(f"  {len(ids):,} notable films to fetch", flush=True)
    key = api_key()
    with make_client() as client:
        fetch(ids, CACHE_DIR, key, client)

    rows = [parse(json.loads((CACHE_DIR / f"{i}.json").read_text())) for i in ids]
    parsed = pl.DataFrame(rows, schema={k: v for k, v in SCHEMA.items() if k != "imdb_id"})
    out_df = (
        ids_df.join(parsed, on="tmdb_id", how="left").select(list(SCHEMA)).sort("tmdb_id")
    ).cast(SCHEMA)
    paths.SCRAPED.mkdir(parents=True, exist_ok=True)
    out = paths.SCRAPED / OUT
    out_df.write_parquet(out)

    with_coll = out_df["collection_id"].is_not_null().sum()
    print(f"  {OUT}: {out_df.height:,} rows, {with_coll:,} in a collection")
    collection_ids = sorted(out_df["collection_id"].drop_nulls().unique().to_list())
    print(f"    distinct collections: {len(collection_ids):,}")
    with make_client() as client:
        build_parts(collection_ids, client, key)
    return out
