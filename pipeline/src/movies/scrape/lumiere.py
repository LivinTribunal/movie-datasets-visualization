"""LUMIERE: admissions by market and year of every notable film with a Wikidata lumiere_id.

`https://lumiere.obs.coe.int/movie/{lumiere_id}` is fetched at most 1 request per second
(robots.txt allows /movie, disallows /work). Every page is cached gzipped in
data/cache/lumiere/<imdb_id>.html.gz (a 404 as an empty <imdb_id>.missing) and the parser reads
only from that cache, so an interrupted run resumes and a re-run makes no request for a film it
has already seen. Any other HTTP error raises. The output is long: one row per film x market x year.
"""

import gzip
import html as htmllib
import re
from pathlib import Path

import httpx
import polars as pl

from movies import paths
from movies.acquire.download import get_following, make_client

URL = "https://lumiere.obs.coe.int/movie/{}"
OUT = "lumiere.parquet"
CACHE_DIR = paths.CACHE / "lumiere"
PROGRESS_EVERY = 500

SCHEMA = {
    "imdb_id": pl.String,
    "lumiere_id": pl.String,
    "market": pl.String,
    "year": pl.Int16,
    "admissions": pl.Int64,
    "estimated": pl.Boolean,
}

PANE = re.compile(r'id="admissions".*?(<table.*?</table>)(.*)', re.S)
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL = re.compile(r"<t[hd][^>]*>(.*?)</t[hd]>", re.S)
TAG = re.compile(r"<[^>]+>")
ESTIMATED = re.compile(r"Estimated admissions for the following markets:\s*([^<]*)")


def fetch(items: list[tuple[str, str]], cache_dir: Path, client: httpx.Client) -> None:
    """GET every (imdb_id, lumiere_id) that is not cached yet; a 404 or bare 3xx is `.missing`."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    for n, (imdb_id, lumiere_id) in enumerate(items, 1):
        target = cache_dir / f"{imdb_id}.html.gz"
        missing = cache_dir / f"{imdb_id}.missing"
        if not target.exists() and not missing.exists():
            try:
                html = get_following(client, URL.format(lumiere_id)).text
            except httpx.HTTPStatusError as err:
                if err.response.status_code != 404 and not err.response.is_redirect:
                    raise
                missing.write_bytes(b"")
            else:
                part = target.with_suffix(".part")
                part.write_bytes(gzip.compress(html.encode()))
                part.replace(target)
        if n % PROGRESS_EVERY == 0 or n == len(items):
            print(f"  {n}/{len(items)}", flush=True)


def cells(row: str) -> list[str]:
    return [htmllib.unescape(TAG.sub("", c)).strip() for c in CELL.findall(row)]


def parse(html: str) -> list[dict]:
    """One row per market and year with admissions; `estimated` from the note under the table."""
    pane = PANE.search(html)
    if not pane:
        return []
    note = ESTIMATED.search(pane.group(2))
    estimated = {m.strip() for m in note.group(1).split(",")} if note else set()
    rows = [cells(r) for r in ROW.findall(pane.group(1))]
    if not rows:
        return []
    years = {i: int(h) for i, h in enumerate(rows[0]) if re.fullmatch(r"\d{4}", h)}
    out = []
    for row in rows[1:]:
        for i, year in years.items():
            digits = re.sub(r"\s", "", row[i]) if i < len(row) else ""
            if digits.isdigit():
                out.append(
                    {
                        "market": row[0],
                        "year": year,
                        "admissions": int(digits),
                        "estimated": row[0] in estimated,
                    }
                )
    return out


def build() -> Path:
    films = paths.INTERIM / "films.parquet"
    if not films.exists():
        raise RuntimeError(f"{films} is missing; run `movies join` first")
    # ponytail: notable subset only (~11.9k pages, ~3.3 h at 1 req/s);
    # widen to the working subset from 1996 (~29.7k ids) if T1 needs it
    ids_df = (
        pl.read_parquet(films, columns=["imdb_id", "notable", "lumiere_id"])
        .filter(pl.col("notable") & pl.col("lumiere_id").is_not_null())
        .with_columns(pl.col("lumiere_id").str.split("|").list.first())
        .select("imdb_id", "lumiere_id")
        .unique("imdb_id")
        .sort("imdb_id")
    )
    items = list(ids_df.iter_rows())
    print(f"  {len(items):,} notable films to fetch", flush=True)
    with make_client() as client:
        fetch(items, CACHE_DIR, client)

    rows, n_missing = [], 0
    for imdb_id, lumiere_id in items:
        page = CACHE_DIR / f"{imdb_id}.html.gz"
        if page.exists():
            parsed = parse(gzip.decompress(page.read_bytes()).decode())
            rows += [{"imdb_id": imdb_id, "lumiere_id": lumiere_id, **r} for r in parsed]
        else:
            n_missing += 1
    out_df = pl.DataFrame(rows, schema=SCHEMA).sort("imdb_id", "market", "year")
    paths.SCRAPED.mkdir(parents=True, exist_ok=True)
    out = paths.SCRAPED / OUT
    out_df.write_parquet(out)

    print(
        f"  {OUT}: {len(items) - n_missing:,} films fetched, "
        f"{out_df['imdb_id'].n_unique():,} with rows, {n_missing:,} missing (404), "
        f"{out_df.height:,} rows, {out_df['market'].n_unique():,} markets, "
        f"years {out_df['year'].min()}-{out_df['year'].max()}"
    )
    return out
