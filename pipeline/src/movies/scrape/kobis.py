"""KOBIS: official South Korean box office, admissions per year, as a cinema market.

The Korean Film Council's yearly box office page (robots.txt allows everything) is fetched at most
1 request per second: a GET for the session cookie and CSRF token, then per year one POST for the
top 50 films and one for the Excel export (an HTML table with every film, used only for the year
total). Pages are cached gzipped in data/cache/kobis/ and the parsers read only from the cache, so
an interrupted run resumes. Films are matched to IMDb through Wikidata P8921 (KOBIS film ID); the
rest of each year's admissions go in one "other films" row so coverage is measured against the
true yearly total. Top-50 films P8921 does not link get a second chance: their Korean title is
looked up as an exact Wikidata label (batched SPARQL, cached) and accepted only when a release
year (P577) of the candidate is within 1 year of the KOBIS release date and exactly one IMDb id
survives. So `title` matches use label + year; they are not fuzzy. `match` records how each film
was linked (`p8921`, `title` or null). No edition suffix is stripped: the colons in the titles
are part of the Korean titles and no re-release suffixes occur in the data.
Output is long: one row per year x top-50 film, plus one remainder row a year.
"""

import gzip
import hashlib
import html as htmllib
import json
import re
from pathlib import Path

import httpx
import polars as pl

from movies import paths
from movies.acquire.download import make_client, request

URL = "https://www.kobis.or.kr/kobis/business/stat/offc/findYearlyBoxOfficeList.do"
SPARQL = "https://query.wikidata.org/sparql"
QUERY = "SELECT ?kobis ?imdb WHERE { ?f wdt:P8921 ?kobis ; wdt:P345 ?imdb . }"
LABEL_BATCH = 100
OUT = "kobis.parquet"
CACHE_DIR = paths.CACHE / "kobis"
YEARS = range(2004, 2026)
OTHER = "other films"

SCHEMA = {
    "kobis_code": pl.String,
    "title_ko": pl.String,
    "imdb_id": pl.String,
    "match": pl.String,
    "year": pl.Int16,
    "admissions": pl.Int64,
}

TOKEN = re.compile(r'name="CSRFToken"\s+value="([^"]+)"')
CODE = re.compile(r"mstView\('movie','(\d+)'\)")
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL = re.compile(r"<t[hd][^>]*>(.*?)</t[hd]>", re.S)
TAG = re.compile(r"<[^>]+>")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def cells(row: str) -> list[str]:
    return [htmllib.unescape(TAG.sub("", c)).strip() for c in CELL.findall(row)]


def to_int(text: str) -> int | None:
    digits = re.sub(r"[\s,]", "", text)
    return int(digits) if digits.isdigit() else None


def parse_top(html: str) -> list[dict]:
    """Top-50 rows: rank, Korean title, release date, admissions and the KOBIS movie code."""
    out = []
    for row in ROW.findall(html):
        code = CODE.search(row)
        c = cells(row)
        if not code or len(c) < 6:
            continue
        rank, admissions = to_int(c[0]), to_int(c[5])
        if rank is None or admissions is None:
            continue
        release = c[2] if DATE.fullmatch(c[2]) else None
        out.append(
            {
                "kobis_code": code.group(1),
                "title_ko": c[1],
                "release_date": release,
                "admissions": admissions,
                "rank": rank,
            }
        )
    return out


def parse_total(html: str) -> int:
    """Sum of the 관객수 (admissions) column over the data rows of the Excel export."""
    rows = [cells(r) for r in ROW.findall(html)]
    header = next(r for r in rows if "관객수" in r)
    col = header.index("관객수")
    values = (to_int(r[col]) for r in rows[rows.index(header) + 1 :] if len(r) > col)
    return sum(v for v in values if v is not None)


def parse_p8921(payload: dict) -> dict[str, str]:
    """KOBIS code -> IMDb id from a SPARQL result; the first sorted IMDb id if there are several."""
    pairs: dict[str, list[str]] = {}
    for b in payload["results"]["bindings"]:
        pairs.setdefault(b["kobis"]["value"], []).append(b["imdb"]["value"])
    return {k: sorted(v)[0] for k, v in pairs.items()}


def parse_labels(payload: dict) -> dict[str, list[tuple[str, int | None]]]:
    """Korean label -> [(IMDb id, P577 year or None)] from a SPARQL result."""
    out: dict[str, list[tuple[str, int | None]]] = {}
    for b in payload["results"]["bindings"]:
        date = b.get("date", {}).get("value", "")
        year = int(date[:4]) if re.match(r"\d{4}-", date) else None
        out.setdefault(b["l"]["value"], []).append((b["imdb"]["value"], year))
    return out


def pick_by_title(
    rows: list[dict], candidates: dict[str, list[tuple[str, int | None]]]
) -> tuple[dict[str, str], int]:
    """KOBIS code -> IMDb id for rows whose label has exactly one candidate released within 1 year
    of the KOBIS release date; also the number of ambiguous rows (several candidates survive)."""
    picked: dict[str, str] = {}
    ambiguous = 0
    for r in rows:
        if not r["release_date"]:
            continue
        year = int(r["release_date"][:4])
        ids = {
            imdb
            for imdb, y in candidates.get(r["title_ko"], [])
            if y is not None and abs(y - year) <= 1
        }
        if len(ids) == 1:
            picked[r["kobis_code"]] = next(iter(ids))
        elif ids:
            ambiguous += 1
    return picked, ambiguous


def assemble(
    year: int,
    top: list[dict],
    total: int,
    p8921: dict[str, str],
    by_title: dict[str, str] | None = None,
) -> list[dict]:
    """Top-50 rows with IMDb ids (null if unmatched) plus the remainder as "other films"."""
    by_title = by_title or {}
    rows = [
        {
            "kobis_code": t["kobis_code"],
            "title_ko": t["title_ko"],
            "imdb_id": p8921.get(t["kobis_code"]) or by_title.get(t["kobis_code"]),
            "match": "p8921"
            if t["kobis_code"] in p8921
            else "title"
            if t["kobis_code"] in by_title
            else None,
            "year": year,
            "admissions": t["admissions"],
        }
        for t in top
    ]
    rest = total - sum(t["admissions"] for t in top)
    rows.append(
        {
            "kobis_code": None,
            "title_ko": OTHER,
            "imdb_id": None,
            "match": None,
            "year": year,
            "admissions": rest,
        }
    )
    return rows


def write_gz(target: Path, text: str) -> None:
    part = target.with_suffix(".part")
    part.write_bytes(gzip.compress(text.encode()))
    part.replace(target)


def read_gz(target: Path) -> str:
    return gzip.decompress(target.read_bytes()).decode()


def fetch(years: range, cache_dir: Path, client: httpx.Client) -> None:
    """POST every year page that is not cached yet; the CSRF token is fetched once, lazily."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    token: str | None = None
    for year in years:
        for kind, search in (("top", "search"), ("all", "excel")):
            target = cache_dir / f"{kind}_{year}.html.gz"
            if target.exists():
                continue
            if token is None:
                match = TOKEN.search(request(client, "GET", URL).text)
                if not match:
                    raise RuntimeError("no CSRFToken on the KOBIS yearly box office page")
                token = match.group(1)
            form = {
                "CSRFToken": token,
                "loadEnd": "0",
                "searchType": search,
                "sSearchYearFrom": str(year),
                "sMultiMovieYn": "",
                "sRepNationCd": "",
                "sMovName": "",
            }
            write_gz(target, request(client, "POST", URL, data=form).text)
        print(f"  fetched {year}", flush=True)


def fetch_p8921(cache_dir: Path, client: httpx.Client) -> dict[str, str]:
    target = cache_dir / "wikidata_p8921.json"
    if not target.exists():
        resp = request(
            client,
            "GET",
            SPARQL,
            params={"query": QUERY},
            headers={"Accept": "application/sparql-results+json"},
        )
        target.write_text(json.dumps(resp.json()))
    return parse_p8921(json.loads(target.read_text()))


def label_query(titles: list[str]) -> str:
    values = " ".join('"' + t.replace("\\", "\\\\").replace('"', '\\"') + '"@ko' for t in titles)
    return (
        f"SELECT ?l ?imdb ?date WHERE {{ VALUES ?l {{ {values} }} "
        "?f rdfs:label ?l ; wdt:P345 ?imdb . OPTIONAL { ?f wdt:P577 ?date } }"
    )


def fetch_labels(
    titles: list[str], cache_dir: Path, client: httpx.Client
) -> dict[str, list[tuple[str, int | None]]]:
    """Look titles up as exact Korean Wikidata labels, LABEL_BATCH per cached query."""
    titles = sorted(set(titles))
    out: dict[str, list[tuple[str, int | None]]] = {}
    for i in range(0, len(titles), LABEL_BATCH):
        batch = titles[i : i + LABEL_BATCH]
        key = hashlib.sha256("\n".join(batch).encode()).hexdigest()[:16]
        target = cache_dir / f"wikidata_labels_{key}.json"
        if not target.exists():
            resp = request(
                client,
                "POST",
                SPARQL,
                data={"query": label_query(batch)},
                headers={"Accept": "application/sparql-results+json"},
            )
            target.write_text(json.dumps(resp.json()))
        for label, found in parse_labels(json.loads(target.read_text())).items():
            out.setdefault(label, []).extend(found)
    return out


def build() -> Path:
    with make_client() as client:
        fetch(YEARS, CACHE_DIR, client)
        p8921 = fetch_p8921(CACHE_DIR, client)
        tops = {y: parse_top(read_gz(CACHE_DIR / f"top_{y}.html.gz")) for y in YEARS}
        todo = [t for top in tops.values() for t in top if t["kobis_code"] not in p8921]
        labels = fetch_labels([t["title_ko"] for t in todo], CACHE_DIR, client)
    by_title, ambiguous = pick_by_title(todo, labels)
    print(f"  title matches: {len(by_title)} of {len(todo)} unlinked, {ambiguous} ambiguous")

    rows: list[dict] = []
    for year in YEARS:
        top = tops[year]
        if not top:
            raise RuntimeError(f"KOBIS {year}: the top-50 page has no rows")
        total = parse_total(read_gz(CACHE_DIR / f"all_{year}.html.gz"))
        year_rows = assemble(year, top, total, p8921, by_title)
        rows += year_rows
        top_sum = sum(t["admissions"] for t in top)
        matched = sum(r["admissions"] for r in year_rows if r["imdb_id"])
        print(
            f"  {year}: total {total:,}, top {len(top)} {top_sum / total:.0%}, "
            f"matched {matched / total:.0%}"
        )
    out_df = pl.DataFrame(rows, schema=SCHEMA).sort("year", "kobis_code", nulls_last=True)
    paths.SCRAPED.mkdir(parents=True, exist_ok=True)
    out = paths.SCRAPED / OUT
    out_df.write_parquet(out)
    print(f"  {OUT}: {out_df.height:,} rows, years {YEARS[0]}-{YEARS[-1]}")
    return out
