"""Schema and invariant checks for app/public/data/. `check()` returns error messages."""

import json
import struct
import zlib
from pathlib import Path

from movies import paths
from movies.export.pack import Pack, read_pack

SCHEMA: dict[str, list[str]] = {
    "countries.json": ["iso2", "iso_numeric", "name", "region", "subregion"],
    "genre_families.json": ["genre", "family", "family_order", "colour"],
}
_SHARES = {c: "f32" for c in ("coverage", "fuzzy_share", "estimated_share")}
_RATINGS = (
    "imdb_100",
    "tmdb_100",
    "tomatometer_100",
    "audience_100",
    "metascore_100",
    "mc_user_100",
    "letterboxd_100",
)
_MONEY = ("budget_usd", "budget_usd2025", "revenue_usd", "revenue_usd2025", "roi")
_EXTRA_MONEY = ("opening_usd", "opening_usd2025", "legs", "video_usd2025")
DETAIL_COLUMNS = {
    c: "str"
    for c in (
        "overview",
        "cast",
        "writers",
        "companies",
        "qid",
        "csfd_id",
        "filmaffinity_id",
        "allocine_id",
        "douban_id",
    )
}
DETAIL_LIMIT = 600_000
DICT_VALUES = {
    "story_source": {"original", "book", "comic", "true_story", "stage", "screen", "other", None},
    "story_source_src": {"numbers", "tmdb", None},
    "age_rating": {"G", "PG", "PG-13", "R", "NC-17", "NR", None},
    "studio": {
        "disney",
        "warner",
        "universal",
        "sony",
        "paramount",
        "fox",
        "lionsgate",
        "mgm",
        "independent",
        None,
    },
}
_KEYS = {"source": "dict", "country": "dict", "year": "u16"}
PACKS: dict[str, dict[str, str]] = {
    "films.pack": {
        "imdb": "u32",
        "tmdb_id": "u32",
        "year": "u16",
        "runtime": "u16",
        "imdb_votes": "u32",
        "genre_mask": "u32",
        "family_mask": "u8",
        "countries": "list",
        **dict.fromkeys(_MONEY, "f32"),
        "budget_src": "dict",
        "revenue_src": "dict",
        "flags": "u8",
        **dict.fromkeys(_RATINGS, "u16"),
        "gap": "i16",
        "mc_critic_reviews": "u16",
        "collection_id": "u32",
        "installment": "u8",
        "story_source": "dict",
        "story_source_src": "dict",
        "age_rating": "dict",
        "studio": "dict",
        "opening_usd": "f32",
        "opening_usd2025": "f32",
        "legs": "f32",
        "video_usd2025": "f32",
        "theaters": "u16",
        "oscar_wins": "u8",
        "oscar_noms": "u8",
    },
    "films_text.pack": {"title": "str", "director": "str"},
    "films_poster.pack": {"poster": "str"},
    "country_genre.pack": {**_KEYS, "genre": "u8", "score": "f32"},
    "country_year.pack": {**_KEYS, "entries": "u32", **_SHARES, "measure": "dict"},
    "imdb_genre_year.pack": {
        "year": "u16",
        "genre": "u8",
        "score": "f32",
        "entries": "u32",
        "shorts": "u32",
    },
    "franchises.pack": {
        "collection_id": "u32",
        "installment": "u8",
        "n_released": "u8",
        "tmdb_id": "u32",
        "film_row": "u32",
        "year": "u16",
        "family_mask": "u8",
        "imdb_100": "u16",
        "tomatometer_100": "u16",
        "audience_100": "u16",
        "imdb_100_vs_first": "i16",
        "revenue_usd2025": "f32",
        "revenue_vs_first": "f32",
        "title": "str",
    },
}
MB = 1_000_000
LIMITS: dict[str, int] = {
    "films.pack": 3_000_000,
    "films_text.pack": 1_200_000,
    "films_poster.pack": 2_000_000,
    "country_genre.pack": 1_000_000,
    "country_year.pack": 200_000,
    "franchises.pack": 200_000,
    "imdb_genre_year.pack": 100_000,
    "countries.topo.json": 900_000,
}
TOTAL_LIMIT = 12_000_000
STALE = ("films.json", "genre_year.json", "country_genre.json", "franchises.json")
OTHER_FILES = ("countries.topo.json", "meta.json")
SRC_VALUES = {"numbers", "tmdb", "wikidata", "wikipedia", None}
COUNTRY_SOURCES = {"netflix", "cinema", "production"}
MEASURES = {"chart_score", "admissions", "gross_usd", "films"}
NOTABLE_VOTES = 10_000


def _load_table(data_dir: Path, name: str, errors: list[str]) -> dict[str, list] | None:
    path = data_dir / name
    if not path.exists():
        errors.append(f"{name}: file missing")
        return None
    try:
        cols = json.loads(path.read_text())["columns"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        errors.append(f"{name}: unreadable ({e})")
        return None
    if list(cols) != SCHEMA[name]:
        errors.append(f"{name}: columns {list(cols)} != expected {SCHEMA[name]}")
        return None
    if len({len(v) for v in cols.values()}) > 1:
        errors.append(f"{name}: columns have unequal lengths")
        return None
    return cols


def _load_pack(
    data_dir: Path, name: str, errors: list[str], expected: dict[str, str] | None = None
) -> Pack | None:
    path = data_dir / name
    if not path.exists():
        errors.append(f"{name}: file missing")
        return None
    try:
        pack = read_pack(path)
    except (OSError, EOFError, ValueError, KeyError, TypeError, struct.error, zlib.error) as e:
        errors.append(f"{name}: unreadable ({e})")
        return None
    got = {c["name"]: c["type"] for c in pack.header["columns"]}
    expected = PACKS[name] if expected is None else expected
    if list(got.items()) != list(expected.items()):
        errors.append(f"{name}: columns {list(got.items())} != expected {list(expected.items())}")
        return None
    return pack


def _outside(values: list, lo: float, hi: float) -> bool:
    return any(v is not None and not lo <= v <= hi for v in values)


def _negative(values: list) -> bool:
    return any(v is not None and v < 0 for v in values)


def _family_names(fam: dict[str, list]) -> list[str]:
    return [f for _, f in sorted(set(zip(fam["family_order"], fam["family"], strict=True)))]


def _check_films(
    p: Pack,
    fam: dict[str, list] | None,
    countries: set | None,
    franchise_ids: set | None,
    errors: list[str],
) -> None:
    c, n = p.columns, p.rows

    def err(msg: str) -> None:
        errors.append(f"films.pack: {msg}")

    if len(set(c["imdb"])) != n:
        err("duplicate imdb")
    if any(v is None for v in c["year"]):
        err("year has nulls")
    if _outside(c["year"], 1900, 2026):
        err("year outside 1900-2026")
    votes = c["imdb_votes"]
    if any(a < b for a, b in zip(votes, votes[1:], strict=False)):
        err("imdb_votes increases down the rows")
    notable = p.meta.get("notable")
    if not isinstance(notable, int) or not 0 < notable <= n:
        err(f"meta.notable {notable!r} outside 1..{n}")
    else:
        if votes[notable - 1] < NOTABLE_VOTES:
            err(f"last notable row has fewer than {NOTABLE_VOTES} votes")
        if notable < n and votes[notable] >= NOTABLE_VOTES:
            err(f"row after the notable rows has {NOTABLE_VOTES} votes or more")
    for col in _RATINGS:
        if _outside(c[col], 0, 100):
            err(f"{col} outside 0-100")
    if _outside(c["gap"], -100, 100):
        err("gap outside -100..100")
    for col in _MONEY + _EXTRA_MONEY + ("theaters",):
        if _negative(c[col]):
            err(f"negative {col}")
    for col in ("budget_src", "revenue_src"):
        bad = set(c[col]) - SRC_VALUES
        if bad:
            err(f"bad {col} {sorted(bad, key=str)}")
    for col, allowed in DICT_VALUES.items():
        bad = set(c[col]) - allowed
        if bad:
            err(f"bad {col} {sorted(bad, key=str)}")
    if any(
        w is not None and (m is None or m < w)
        for w, m in zip(c["oscar_wins"], c["oscar_noms"], strict=True)
    ):
        err("oscar_noms under oscar_wins")
    if any(
        (a is None) != (b is None) for a, b in zip(c["oscar_wins"], c["oscar_noms"], strict=True)
    ):
        err("oscar_wins is null for a different set of films than oscar_noms")
    if countries is not None:
        unknown = {x for v in c["countries"] for x in v} - countries
        if unknown:
            err(f"unknown country {sorted(unknown)}")
    if fam is not None:
        genres, families = fam["genre"], _family_names(fam)
        if p.meta.get("genres") != genres:
            err("meta.genres differs from the genre column of genre_families.json")
        if p.meta.get("families") != families:
            err("meta.families differs from the families of genre_families.json in family_order")
        if any(m >> len(genres) for m in c["genre_mask"]):
            err("genre_mask has a bit beyond the genre list")
        bit = [1 << families.index(f) for f in fam["family"]]
        for gm, fm in zip(c["genre_mask"], c["family_mask"], strict=True):
            if fm != sum({bit[i] for i in range(len(genres)) if gm >> i & 1}):
                err("family_mask differs from the families of genre_mask")
                break
    if any(
        (a is None) != (b is None)
        for a, b in zip(c["installment"], c["collection_id"], strict=True)
    ):
        err("installment is null for a different set of films than collection_id")
    if franchise_ids is not None:
        unknown = {v for v in c["collection_id"] if v is not None} - franchise_ids
        if unknown:
            err(f"collection_id not in franchises.pack {sorted(unknown)[:5]}")


def _check_franchises(p: Pack, films: Pack | None, errors: list[str]) -> None:
    c = p.columns

    def err(msg: str) -> None:
        errors.append(f"franchises.pack: {msg}")

    pairs = list(zip(c["installment"], c["n_released"], strict=True))
    if any(i < 1 or i > n for i, n in pairs):
        err("installment outside 1..n_released")
    if any(n < 3 for n in c["n_released"]):
        err("n_released under 3")
    for col in ("imdb_100", "tomatometer_100", "audience_100"):
        if _outside(c[col], 0, 100):
            err(f"{col} outside 0-100")
    parts: dict[int, list[int]] = {}
    for cid, i in zip(c["collection_id"], c["installment"], strict=True):
        parts.setdefault(cid, []).append(i)
    n_of = dict(zip(c["collection_id"], c["n_released"], strict=True))
    if any(sorted(i) != list(range(1, n_of[cid] + 1)) for cid, i in parts.items()):
        err("installments are not exactly 1..n_released")
    if any(
        i == 1 and v is not None and v != 0
        for i, v in zip(c["installment"], c["imdb_100_vs_first"], strict=True)
    ):
        err("imdb_100_vs_first not 0 at installment 1")
    if _negative(c["revenue_vs_first"]):
        err("negative revenue_vs_first")
    if films is not None:
        for row, cid in zip(c["film_row"], c["collection_id"], strict=True):
            if row is not None and (
                row >= films.rows or films.columns["collection_id"][row] != cid
            ):
                err("film_row is not a row of films.pack in this collection")
                break
    named = {x[0] for x in p.meta.get("collections", []) if isinstance(x, list) and x}
    if set(c["collection_id"]) - named:
        err("collection_id without a name in meta.collections")


def _check_countries(
    cg: Pack | None,
    cy: Pack | None,
    fam: dict[str, list] | None,
    countries: set | None,
    errors: list[str],
) -> None:
    for name, p in (("country_genre.pack", cg), ("country_year.pack", cy)):
        if p is None:
            continue
        c = p.columns
        keys = list(zip(c["source"], c["country"], c["year"], strict=True))
        if name == "country_genre.pack":
            keys = list(zip(keys, c["genre"], strict=True))
        if len(set(keys)) != len(keys):
            errors.append(f"{name}: duplicate key")
        if set(c["source"]) - COUNTRY_SOURCES:
            errors.append(f"{name}: unknown source {sorted(set(c['source']) - COUNTRY_SOURCES)}")
        if countries is not None and set(c["country"]) - countries:
            errors.append(f"{name}: unknown country {sorted(set(c['country']) - countries)}")
    if cg is not None:
        c = cg.columns
        if fam is not None and any(g >= len(fam["genre"]) for g in c["genre"]):
            errors.append("country_genre.pack: genre beyond the genre list")
        if _negative(c["score"]):
            errors.append("country_genre.pack: negative score")
    if cy is not None:
        c = cy.columns
        for col in _SHARES:
            if _outside(c[col], 0, 1):
                errors.append(f"country_year.pack: {col} outside 0-1")
        if any(
            f is not None and v is not None and f > v + 1e-6
            for f, v in zip(c["fuzzy_share"], c["coverage"], strict=True)
        ):
            errors.append("country_year.pack: fuzzy_share exceeds coverage")
        if any(e is None or e < 1 for e in c["entries"]):
            errors.append("country_year.pack: entries under 1")
        unknown = set(c["measure"]) - MEASURES
        if unknown:
            errors.append(f"country_year.pack: unknown measure {sorted(unknown, key=str)}")
    if cg is not None and cy is not None:
        gk = set(zip(cg.columns["source"], cg.columns["country"], cg.columns["year"], strict=True))
        yk = set(zip(cy.columns["source"], cy.columns["country"], cy.columns["year"], strict=True))
        if gk != yk:
            errors.append("country_genre.pack / country_year.pack: different source-country-years")


def _check_imdb(p: Pack | None, fam: dict[str, list] | None, errors: list[str]) -> None:
    if p is None:
        return
    c = p.columns
    name = "imdb_genre_year.pack"
    if _outside(c["year"], 1900, 2026):
        errors.append(f"{name}: year outside 1900-2026")
    if fam is not None and any(g >= len(fam["genre"]) for g in c["genre"]):
        errors.append(f"{name}: genre beyond the genre list")
    if any(s is None or s <= 0 for s in c["score"]):
        errors.append(f"{name}: score not above 0")
    if any(e is None or e < 1 for e in c["entries"]):
        errors.append(f"{name}: entries under 1")
    rows = list(zip(c["year"], c["entries"], c["shorts"], strict=True))
    if any(s > e for _, e, s in rows):
        errors.append(f"{name}: shorts exceed entries")
    if any(y >= 1920 and s > 0 for y, _, s in rows):
        errors.append(f"{name}: shorts from 1920 on")
    keys = list(zip(c["year"], c["genre"], strict=True))
    if len(set(keys)) != len(keys):
        errors.append(f"{name}: duplicate key")


def _check_meta(data_dir: Path, errors: list[str]) -> None:
    path = data_dir / "meta.json"
    if not path.exists():
        return
    try:
        meta = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        errors.append(f"meta.json: unreadable ({e})")
        return
    if not isinstance(meta, dict):
        errors.append("meta.json: not an object")
        return
    for key in ("snapshots", "base_year", "counts", "notes", "attribution", "sources"):
        if key not in meta:
            errors.append(f"meta.json: missing {key}")
    if "attribution" in meta and not (
        isinstance(meta["attribution"], list) and meta["attribution"]
    ):
        errors.append("meta.json: attribution is empty")
    sources = meta.get("sources")
    if "sources" in meta and not (isinstance(sources, dict) and set(sources) == COUNTRY_SOURCES):
        errors.append(f"meta.json: sources keys are not {sorted(COUNTRY_SOURCES)}")


def _check_detail(data_dir: Path, notable: int | None, errors: list[str]) -> None:
    path = data_dir / "meta.json"
    try:
        detail = json.loads(path.read_text()).get("detail")
    except (OSError, ValueError, AttributeError):
        return  # _check_meta reports it
    if not (
        isinstance(detail, dict)
        and isinstance(detail.get("shard_size"), int)
        and isinstance(detail.get("shards"), int)
        and detail["shard_size"] > 0
    ):
        errors.append("meta.json: detail is not {shard_size, shards}")
        return
    size, shards = detail["shard_size"], detail["shards"]
    total = 0
    for k in range(shards):
        name = f"films_detail_{k}.pack"
        pack = _load_pack(data_dir, name, errors, DETAIL_COLUMNS)
        if pack is None:
            continue
        total += pack.rows
        if pack.rows != size and not (k == shards - 1 and 0 < pack.rows < size):
            errors.append(f"{name}: {pack.rows} rows, expected {size}")
    if notable is not None and total != notable:
        errors.append(f"films_detail_*.pack: {total} rows != {notable} notable films")


def _sizes(data_dir: Path) -> tuple[list[str], float]:
    errors = []
    limits = LIMITS | {p.name: DETAIL_LIMIT for p in data_dir.glob("films_detail_*.pack")}
    for name, limit in limits.items():
        path = data_dir / name
        if path.exists() and path.stat().st_size > limit:
            size = path.stat().st_size
            errors.append(f"{name}: {size / MB:.2f} MB over the {limit / MB:.1f} MB limit")
    total = sum(f.stat().st_size for f in data_dir.iterdir() if f.is_file())
    if total > TOTAL_LIMIT:
        errors.append(f"app data: {total / MB:.2f} MB over the {TOTAL_LIMIT / MB:.1f} MB limit")
    return errors, total / MB


def check(data_dir: Path) -> list[str]:
    errors: list[str] = []
    for name in OTHER_FILES:
        if not (data_dir / name).exists():
            errors.append(f"{name}: file missing")
    t = {name: _load_table(data_dir, name, errors) for name in SCHEMA}
    p = {name: _load_pack(data_dir, name, errors) for name in PACKS}
    fam, ctry = t["genre_families.json"], t["countries.json"]
    countries = set(ctry["iso2"]) if ctry else None
    films, franchises = p["films.pack"], p["franchises.pack"]
    if films:
        franchise_ids = set(franchises.columns["collection_id"]) if franchises else None
        _check_films(films, fam, countries, franchise_ids, errors)
        for name in ("films_text.pack", "films_poster.pack"):
            other = p[name]
            if other and other.rows != films.rows:
                errors.append(f"{name}: {other.rows} rows != {films.rows} rows of films.pack")
    for name in ("films_text.pack", "films_poster.pack"):
        other = p[name]
        if other and "title" in other.columns and any(v is None for v in other.columns["title"]):
            errors.append(f"{name}: title has nulls")
    _check_detail(data_dir, films.meta.get("notable") if films else None, errors)
    if franchises:
        _check_franchises(franchises, films, errors)
    _check_countries(p["country_genre.pack"], p["country_year.pack"], fam, countries, errors)
    _check_imdb(p["imdb_genre_year.pack"], fam, errors)
    _check_meta(data_dir, errors)
    size_errors, _ = _sizes(data_dir)
    errors += size_errors
    for name in STALE:
        if (data_dir / name).exists():
            errors.append(f"{name}: stale file, `movies export` removes it")
    return errors


def run() -> None:
    errors = check(paths.APP_DATA)
    if errors:
        print("\n".join(errors))
        raise SystemExit(1)
    _, total = _sizes(paths.APP_DATA)
    print(f"app data valid: {len(SCHEMA) + len(PACKS) + len(OTHER_FILES)} files, {total:.2f} MB")
