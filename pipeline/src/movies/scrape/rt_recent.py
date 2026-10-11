"""Rotten Tomatoes: fresh critic and audience scores of films from 2023 on.

The Clapper RT dump is from April 2023, so newer films have no score in it. Every film page
`https://www.rottentomatoes.com/{rt_id}` embeds its scores in a `media-scorecard-json` script tag.
Requests are at most 1 per second per host (robots.txt allows /m/). Every page is cached gzipped
in data/cache/rt_recent/<imdb_id>.html.gz (a 404 as an empty <imdb_id>.missing) and the parser
reads only from that cache, so an interrupted run resumes and a re-run makes no request for a
film it has already seen. Any other HTTP error raises.
"""

import gzip
import json
import re
from pathlib import Path

import httpx
import polars as pl

from movies import paths
from movies.acquire.download import get_following, make_client

URL = "https://www.rottentomatoes.com/{}"
OUT = "rt_recent.parquet"
CACHE_DIR = paths.CACHE / "rt_recent"
PROGRESS_EVERY = 500
RT_FROM_YEAR = 2023

SCHEMA = {
    "imdb_id": pl.String,
    "rt_id": pl.String,
    "tomatometer": pl.Int8,
    "rt_critic_reviews": pl.Int32,
    "audience_score": pl.Int8,
    "audience_score_type": pl.String,
    "audience_ratings_band": pl.String,
}
FIELDS = [k for k in SCHEMA if k not in ("imdb_id", "rt_id")]

SCORECARD = re.compile(r'<script[^>]*id="media-scorecard-json"[^>]*>(.*?)</script>', re.S)


def to_int(value: str | float | None) -> int | None:
    """83, "83" and "83.0" give 83; None and anything non-numeric ("") give None."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def fetch(items: list[tuple[str, str]], cache_dir: Path, client: httpx.Client) -> None:
    """GET every (imdb_id, rt_id) that is not cached yet; a 404 is cached as `.missing`."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    for n, (imdb_id, rt_id) in enumerate(items, 1):
        target = cache_dir / f"{imdb_id}.html.gz"
        missing = cache_dir / f"{imdb_id}.missing"
        if not target.exists() and not missing.exists():
            try:
                html = get_following(client, URL.format(rt_id)).text
            except httpx.HTTPStatusError as err:
                # a 404, or a redirect with nowhere to go, is a page that is not there
                if err.response.status_code != 404 and not err.response.is_redirect:
                    raise
                missing.write_bytes(b"")
            else:
                part = target.with_suffix(".part")
                part.write_bytes(gzip.compress(html.encode()))
                part.replace(target)
        if n % PROGRESS_EVERY == 0 or n == len(items):
            print(f"  {n}/{len(items)}", flush=True)


def parse(html: str) -> dict:
    out: dict = dict.fromkeys(FIELDS)
    match = SCORECARD.search(html)
    if not match:
        return out
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return out
    if not isinstance(data, dict):
        return out
    critics, audience = data.get("criticsScore"), data.get("audienceScore")
    if isinstance(critics, dict):
        out["tomatometer"] = to_int(critics.get("score"))
        out["rt_critic_reviews"] = to_int(critics.get("reviewCount"))
    if isinstance(audience, dict):
        out["audience_score"] = to_int(audience.get("score"))
        out["audience_score_type"] = audience.get("scoreType") or None
        out["audience_ratings_band"] = audience.get("bandedRatingCount") or None
    return out


def build() -> Path:
    films = paths.INTERIM / "films.parquet"
    if not films.exists():
        raise RuntimeError(f"{films} is missing; run `movies join` first")
    ids_df = (
        pl.read_parquet(films, columns=["imdb_id", "year", "rt_id"])
        .filter((pl.col("year") >= RT_FROM_YEAR) & pl.col("rt_id").is_not_null())
        .with_columns(pl.col("rt_id").str.split("|").list.first())
        .select("imdb_id", "rt_id")
        .unique("imdb_id")
        .sort("imdb_id")
    )
    items = list(ids_df.iter_rows())
    print(f"  {len(items):,} films from {RT_FROM_YEAR} to fetch", flush=True)
    with make_client() as client:
        fetch(items, CACHE_DIR, client)

    rows, n_missing = [], 0
    for imdb_id, rt_id in items:
        page = CACHE_DIR / f"{imdb_id}.html.gz"
        if page.exists():
            fields = parse(gzip.decompress(page.read_bytes()).decode())
        else:
            fields, n_missing = dict.fromkeys(FIELDS), n_missing + 1
        rows.append({"imdb_id": imdb_id, "rt_id": rt_id, **fields})
    out_df = pl.DataFrame(rows, schema=SCHEMA).sort("imdb_id")
    paths.SCRAPED.mkdir(parents=True, exist_ok=True)
    out = paths.SCRAPED / OUT
    out_df.write_parquet(out)

    print(f"  {OUT}: {out_df.height:,} rows, {n_missing:,} missing (404)")
    for field in FIELDS:
        print(f"    {field}: {out_df[field].is_not_null().sum():,}")
    return out
