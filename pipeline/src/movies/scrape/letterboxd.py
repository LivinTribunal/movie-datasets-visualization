"""Letterboxd: average rating and rating count of every notable film.

`https://letterboxd.com/imdb/{imdb_id}/` redirects to the film page; both hops are requests, at
most 1 per second per host (robots.txt allows /film/ and /imdb/). Every film page is cached
gzipped in data/cache/letterboxd/<imdb_id>.html.gz (a 404 as an empty <imdb_id>.missing) and the
parser reads only from that cache, so an interrupted run resumes and a re-run makes no request
for a film it has already seen. Any other HTTP error raises.
"""

import gzip
import json
import re
from pathlib import Path

import httpx
import polars as pl

from movies import paths
from movies.acquire.download import get_following, make_client

URL = "https://letterboxd.com/imdb/{}/"
OUT = "letterboxd.parquet"
CACHE_DIR = paths.CACHE / "letterboxd"
PROGRESS_EVERY = 500

SCHEMA = {
    "imdb_id": pl.String,
    "lb_slug": pl.String,
    "letterboxd_avg": pl.Float64,
    "letterboxd_ratings": pl.Int64,
}
FIELDS = [k for k in SCHEMA if k != "imdb_id"]

LD_JSON = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
CDATA = re.compile(r"/\*\s*<!\[CDATA\[\s*\*/|/\*\s*\]\]>\s*\*/")
SLUG = re.compile(r"/film/([^/]+)/")


def fetch(ids: list[str], cache_dir: Path, client: httpx.Client) -> None:
    """GET every id that is not cached yet; a 404 on either hop is cached as `.missing`."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    for n, imdb_id in enumerate(ids, 1):
        target = cache_dir / f"{imdb_id}.html.gz"
        missing = cache_dir / f"{imdb_id}.missing"
        if not target.exists() and not missing.exists():
            try:
                html = get_following(client, URL.format(imdb_id)).text
            except httpx.HTTPStatusError as err:
                # a 404, or a redirect with nowhere to go, is a page that is not there
                if err.response.status_code != 404 and not err.response.is_redirect:
                    raise
                missing.write_bytes(b"")
            else:
                part = target.with_suffix(".part")
                part.write_bytes(gzip.compress(html.encode()))
                part.replace(target)
        if n % PROGRESS_EVERY == 0 or n == len(ids):
            print(f"  {n}/{len(ids)}", flush=True)


def parse(html: str) -> dict:
    out: dict = dict.fromkeys(FIELDS)
    match = LD_JSON.search(html)
    if not match:
        return out
    try:
        data = json.loads(CDATA.sub("", match.group(1)))
    except json.JSONDecodeError:
        return out
    if not isinstance(data, dict):
        return out
    slug = SLUG.search(str(data.get("url", "")))
    out["lb_slug"] = slug.group(1) if slug else None
    rating = data.get("aggregateRating")
    if isinstance(rating, dict):
        value, count = rating.get("ratingValue"), rating.get("ratingCount")
        out["letterboxd_avg"] = float(value) if value is not None else None
        out["letterboxd_ratings"] = int(count) if count is not None else None
    return out


def build() -> Path:
    films = paths.INTERIM / "films.parquet"
    if not films.exists():
        raise RuntimeError(f"{films} is missing; run `movies join` first")
    # ponytail: notable subset only (~13k films x 2 hops, ~7 h at 1 req/s);
    # widen to the working subset if the rating tasks need it
    ids = sorted(
        pl.read_parquet(films, columns=["imdb_id", "notable"])
        .filter(pl.col("notable"))["imdb_id"]
        .unique()
        .to_list()
    )
    print(f"  {len(ids):,} notable films to fetch", flush=True)
    with make_client() as client:
        fetch(ids, CACHE_DIR, client)

    rows, n_missing = [], 0
    for imdb_id in ids:
        page = CACHE_DIR / f"{imdb_id}.html.gz"
        if page.exists():
            fields = parse(gzip.decompress(page.read_bytes()).decode())
        else:
            fields, n_missing = dict.fromkeys(FIELDS), n_missing + 1
        rows.append({"imdb_id": imdb_id, **fields})
    out_df = pl.DataFrame(rows, schema=SCHEMA).sort("imdb_id")
    paths.SCRAPED.mkdir(parents=True, exist_ok=True)
    out = paths.SCRAPED / OUT
    out_df.write_parquet(out)

    print(f"  {OUT}: {out_df.height:,} rows, {n_missing:,} missing (404)")
    for field in FIELDS:
        print(f"    {field}: {out_df[field].is_not_null().sum():,}")
    return out
