"""Metacritic: metascore and user score of every notable film with a Wikidata mc_id.

`https://www.metacritic.com/{mc_id}/` is fetched at most 1 request per second (robots.txt allows
/movie/). Every page is cached gzipped in data/cache/metacritic/<imdb_id>.html.gz (a 404 as an
empty <imdb_id>.missing) and the parser reads only from that cache, so an interrupted run resumes
and a re-run makes no request for a film it has already seen. Any other HTTP error raises.
"""

import gzip
import json
import re
from pathlib import Path

import httpx
import polars as pl

from movies import paths
from movies.acquire.download import get_following, make_client

URL = "https://www.metacritic.com/{}/"
OUT = "metacritic.parquet"
CACHE_DIR = paths.CACHE / "metacritic"
PROGRESS_EVERY = 500

SCHEMA = {
    "imdb_id": pl.String,
    "mc_id": pl.String,
    "metascore": pl.Int8,
    "mc_critic_reviews": pl.Int32,
    "mc_user_score": pl.Float64,
    "mc_user_ratings": pl.Int32,
}
FIELDS = [k for k in SCHEMA if k not in ("imdb_id", "mc_id")]

LD_JSON = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
USER_SCORE = re.compile(r'title="User score (\S+)')
USER_RATINGS = re.compile(r"Based on ([\d,]+) User Ratings?")


def fetch(items: list[tuple[str, str]], cache_dir: Path, client: httpx.Client) -> None:
    """GET every (imdb_id, mc_id) that is not cached yet; a 404 or bare 3xx is `.missing`."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    for n, (imdb_id, mc_id) in enumerate(items, 1):
        target = cache_dir / f"{imdb_id}.html.gz"
        missing = cache_dir / f"{imdb_id}.missing"
        if not target.exists() and not missing.exists():
            try:
                html = get_following(client, URL.format(mc_id)).text
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


def to_int(value: str | float | None) -> int | None:
    """83, "83" and "83.0" give 83; None and anything non-numeric ("tbd") give None."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def parse(html: str) -> dict:
    out: dict = dict.fromkeys(FIELDS)
    for block in LD_JSON.findall(html):
        try:
            rating = json.loads(block).get("aggregateRating")
        except (json.JSONDecodeError, AttributeError):
            continue
        # TV episode pages put the 0-10 user score in this block instead of a Metascore
        if (
            isinstance(rating, dict)
            and rating.get("ratingValue") is not None
            and "User" not in str(rating.get("name", ""))
        ):
            out["metascore"] = to_int(rating["ratingValue"])
            out["mc_critic_reviews"] = to_int(rating.get("reviewCount"))
            break
    # recommendation cards carry "User score" titles too: trust it only beside the rating count
    ratings = USER_RATINGS.search(html)
    score = USER_SCORE.search(html)
    if ratings and score:
        out["mc_user_ratings"] = int(ratings.group(1).replace(",", ""))
        try:
            out["mc_user_score"] = float(score.group(1))
        except ValueError:  # "tbd" or "null"
            out["mc_user_score"] = None
    return out


def build() -> Path:
    films = paths.INTERIM / "films.parquet"
    if not films.exists():
        raise RuntimeError(f"{films} is missing; run `movies join` first")
    # ponytail: notable subset only (~9.5k pages, ~2.6 h at 1 req/s);
    # widen to the working subset if the rating tasks need it
    ids_df = (
        pl.read_parquet(films, columns=["imdb_id", "notable", "mc_id"])
        .filter(pl.col("notable") & pl.col("mc_id").is_not_null())
        .with_columns(pl.col("mc_id").str.split("|").list.first())
        .select("imdb_id", "mc_id")
        .unique("imdb_id")
        .sort("imdb_id")
    )
    items = list(ids_df.iter_rows())
    print(f"  {len(items):,} notable films to fetch", flush=True)
    with make_client() as client:
        fetch(items, CACHE_DIR, client)

    rows, n_missing = [], 0
    for imdb_id, mc_id in items:
        page = CACHE_DIR / f"{imdb_id}.html.gz"
        if page.exists():
            fields = parse(gzip.decompress(page.read_bytes()).decode())
        else:
            fields, n_missing = dict.fromkeys(FIELDS), n_missing + 1
        rows.append({"imdb_id": imdb_id, "mc_id": mc_id, **fields})
    out_df = pl.DataFrame(rows, schema=SCHEMA).sort("imdb_id")
    paths.SCRAPED.mkdir(parents=True, exist_ok=True)
    out = paths.SCRAPED / OUT
    out_df.write_parquet(out)

    print(f"  {OUT}: {out_df.height:,} rows, {n_missing:,} missing (404)")
    for field in FIELDS:
        print(f"    {field}: {out_df[field].is_not_null().sum():,}")
    return out
