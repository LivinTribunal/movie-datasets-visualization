"""Schema and invariant checks for app/public/data/. `check()` returns error messages."""

import json
import re
from pathlib import Path

from movies import paths

SCHEMA: dict[str, list[str]] = {
    "films.json": [
        "imdb_id", "tmdb_id", "title", "year", "notable", "genres", "families", "countries",
        "imdb_votes", "budget_usd2025", "revenue_usd2025", "budget_src", "revenue_src",
        "budget_converted", "revenue_converted", "budget_disagree", "revenue_disagree",
        "money_fuzzy", "roi", "imdb_100", "tmdb_100", "tomatometer_100", "audience_100", "gap",
    ],
    "genre_year.json": [
        "subset", "year", "genre", "family", "films", "votes", "revenue_usd2025", "revenue_films",
    ],
    "country_genre.json": [
        "source", "country_iso2", "year", "genre", "family", "share", "score", "coverage",
        "fuzzy_share",
    ],
    "countries.json": ["iso2", "iso_numeric", "name", "region", "subregion"],
    "genre_families.json": ["genre", "family", "family_order", "colour"],
    "franchises.json": [
        "collection_id", "collection_name", "installment", "n_released", "tmdb_id", "imdb_id",
        "title", "year", "imdb_100", "imdb_100_vs_prev", "imdb_100_vs_first", "tomatometer_100",
        "audience_100", "revenue_usd2025", "revenue_vs_prev", "revenue_vs_first",
    ],
}  # fmt: skip
OTHER_FILES = ("countries.topo.json", "meta.json")
SRC_VALUES = {"numbers", "tmdb", "wikidata", None}
IMDB_ID = re.compile(r"^tt\d+$")


def _load(data_dir: Path, name: str, errors: list[str]) -> dict[str, list] | None:
    path = data_dir / name
    if not path.exists():
        errors.append(f"{name}: file missing")
        return None
    cols = json.loads(path.read_text())["columns"]
    if list(cols) != SCHEMA[name]:
        errors.append(f"{name}: columns {list(cols)} != expected {SCHEMA[name]}")
        return None
    if len({len(v) for v in cols.values()}) > 1:
        errors.append(f"{name}: columns have unequal lengths")
        return None
    return cols


def _outside(values: list, lo: float, hi: float) -> bool:
    return any(v is not None and not lo <= v <= hi for v in values)


def check(data_dir: Path) -> list[str]:
    errors: list[str] = []
    for name in OTHER_FILES:
        if not (data_dir / name).exists():
            errors.append(f"{name}: file missing")
    t = {name: _load(data_dir, name, errors) for name in SCHEMA}
    fam_t, ctry_t = t["genre_families.json"], t["countries.json"]
    families = set(fam_t["family"]) if fam_t else None
    countries = set(ctry_t["iso2"]) if ctry_t else None

    def check_refs(name: str, col: str, known: set | None, what: str, nested: bool = False):
        if known is None or t[name] is None:
            return
        vals = t[name][col]
        used = {x for v in vals for x in (v or [])} if nested else set(vals)
        if used - known:
            errors.append(f"{name}: unknown {what} {sorted(used - known)}")

    films = t["films.json"]
    if films:
        ids = films["imdb_id"]
        if len(set(ids)) != len(ids):
            errors.append("films.json: duplicate imdb_id")
        if any(not IMDB_ID.match(i or "") for i in ids):
            errors.append("films.json: imdb_id does not match tt<digits>")
        for col in ("genres", "families", "countries"):
            if any(v is None for v in films[col]):
                errors.append(f"films.json: {col} has nulls (use [] for none)")
        if _outside(films["year"], 1900, 2026):
            errors.append("films.json: year outside 1900-2026")
        for col in SCHEMA["films.json"]:
            if col.endswith("_100") and _outside(films[col], 0, 100):
                errors.append(f"films.json: {col} outside 0-100")
        if _outside(films["gap"], -100, 100):
            errors.append("films.json: gap outside -100..100")
        for col in ("budget_usd2025", "revenue_usd2025", "roi"):
            if any(v is not None and v < 0 for v in films[col]):
                errors.append(f"films.json: negative {col}")
        for col in ("budget_src", "revenue_src"):
            bad = set(films[col]) - SRC_VALUES
            if bad:
                errors.append(f"films.json: bad {col} {sorted(bad, key=str)}")
    fr = t["franchises.json"]
    if fr:
        if any(
            i is None or i < 1 or i > n
            for i, n in zip(fr["installment"], fr["n_released"], strict=True)
        ):
            errors.append("franchises.json: installment outside 1..n_released")
        if any(n is None or n < 3 for n in fr["n_released"]):
            errors.append("franchises.json: n_released under 3")
        for col in ("imdb_100", "tomatometer_100", "audience_100"):
            if _outside(fr[col], 0, 100):
                errors.append(f"franchises.json: {col} outside 0-100")
        if any(i is not None and not IMDB_ID.match(i) for i in fr["imdb_id"]):
            errors.append("franchises.json: imdb_id does not match tt<digits>")
    check_refs("films.json", "families", families, "family", nested=True)
    check_refs("films.json", "countries", countries, "country", nested=True)
    check_refs("genre_year.json", "family", families, "family")
    check_refs("country_genre.json", "family", families, "family")
    check_refs("country_genre.json", "country_iso2", countries, "country")

    cg = t["country_genre.json"]
    if cg:
        sums: dict[tuple, float] = {}
        keys = list(zip(cg["source"], cg["country_iso2"], cg["year"], strict=True))
        for k, s in zip(keys, cg["share"], strict=True):
            sums[k] = sums.get(k, 0.0) + (s or 0.0)
        bad_sums = [k for k, s in sums.items() if abs(s - 1) > 1e-3]
        if bad_sums:
            errors.append(f"country_genre.json: shares do not sum to 1 for {bad_sums[:5]}")
        for col in ("coverage", "fuzzy_share"):
            if _outside(cg[col], 0, 1):
                errors.append(f"country_genre.json: {col} outside 0-1")
        if any(f > c + 1e-9 for f, c in zip(cg["fuzzy_share"], cg["coverage"], strict=True)):
            errors.append("country_genre.json: fuzzy_share exceeds coverage")
    return errors


def run() -> None:
    errors = check(paths.APP_DATA)
    if errors:
        print("\n".join(errors))
        raise SystemExit(1)
    print(f"app data valid: {len(SCHEMA) + len(OTHER_FILES)} files")
