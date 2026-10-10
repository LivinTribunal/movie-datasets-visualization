"""Match rows without IMDb ids (The Numbers, Netflix) to TMDB films by title and year window.

Exact match on the normalised title first, then rapidfuzz for what is left. Every match carries
its `method` and `score`, because fuzzy-matched values must be shown as such in the app.
"""

import re
import unicodedata

import polars as pl
from rapidfuzz import fuzz, process

MATCH_COLUMNS = ["key", "imdb_id", "method", "score"]
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_NON_DIGIT = re.compile(r"\D")
_TRAILING_PAREN = re.compile(r"\s*\([^()]*\)\s*$")  # "RRR (Hindi)", "Death Wish (2018)"
# "Blade II", "Chapter Two" -> 2; "I" and "one" stay words ("I, Robot", "One Day")
_ROMAN = "ii iii iv v vi vii viii ix x".split()
_WORDS = "two three four five six seven eight nine ten".split()
_NUMERALS = {
    w: str(n) for n, pair in enumerate(zip(_ROMAN, _WORDS, strict=True), start=2) for w in pair
}


def normalise(title: str | None) -> str | None:
    """Fold case, accents, punctuation, numerals, a trailing (...) and a leading 'The'."""
    if title is None:
        return None
    text = unicodedata.normalize("NFKD", _TRAILING_PAREN.sub("", title) or title)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = text.replace("&", " and ").replace("'", "").replace("’", "")
    text = " ".join(_NUMERALS.get(w, w) for w in _NON_ALNUM.sub(" ", text).split())
    text = text.removeprefix("the ")
    return text or None


def normalise_expr(col: str) -> pl.Expr:
    return pl.col(col).map_elements(normalise, return_dtype=pl.String)


def _in_window(df: pl.DataFrame) -> pl.DataFrame:
    return df.filter(pl.col("year").is_between(pl.col("year_min"), pl.col("year_max")))


def _best(df: pl.DataFrame, by: list[str], descending: list[bool]) -> pl.DataFrame:
    """One row per key, ranked by `by` (votes nulls last, imdb_id as the final tie-break)."""
    return (
        df.sort(by, descending=descending, nulls_last=True)
        .unique("key", keep="first", maintain_order=True)
        .select(MATCH_COLUMNS)
    )


def match(
    left: pl.DataFrame,
    right: pl.DataFrame,
    *,
    min_score: float = 90.0,
    fuzzy_years: int | None = None,
) -> pl.DataFrame:
    """Return one row (key, imdb_id, method, score) per left key that matched a right film.

    A fuzzy match may not carry different numbers ("Expendables 4" is not "Expendables 2", but
    "Jaws 4: The Revenge" is "Jaws: The Revenge"). With `fuzzy_years`, fuzzy matching only
    considers films released at most that many years before `year_max`.
    """
    lefts = left.select("key", "year_min", "year_max", _norm=normalise_expr("title")).drop_nulls(
        "_norm"
    )
    rights = (
        pl.concat(
            right.select("imdb_id", "year", "imdb_votes", _norm=normalise_expr(c))
            for c in ("title", "original_title")
        )
        .drop_nulls(["_norm", "year"])
        .unique()
    )

    exact = _in_window(lefts.join(rights, on="_norm")).with_columns(
        method=pl.lit("exact"), score=pl.lit(100.0)
    )
    exact = _best(exact, ["imdb_votes", "imdb_id"], [True, False])

    todo = lefts.join(exact.select("key"), on="key", how="anti")
    if fuzzy_years is not None:
        todo = todo.with_columns(
            year_min=pl.max_horizontal("year_min", pl.col("year_max") - fuzzy_years)
        )
    # block by year window so each title is only scored against films it could match
    pairs = []
    for (lo, hi), group in todo.group_by(["year_min", "year_max"]):
        choices = rights.filter(pl.col("year").is_between(lo, hi))["_norm"].unique().to_list()
        for norm in group["_norm"].unique().to_list():
            for choice, score, _ in process.extract(
                norm, choices, scorer=fuzz.token_sort_ratio, score_cutoff=min_score, limit=None
            ):
                numbers = {_NON_DIGIT.sub("", norm), _NON_DIGIT.sub("", choice)} - {""}
                if len(numbers) < 2:
                    pairs.append((norm, choice, float(score)))
    scored = pl.DataFrame(
        pairs, schema={"_norm": pl.String, "_rnorm": pl.String, "_score": pl.Float64}, orient="row"
    )
    fuzzy = _in_window(
        todo.join(scored, on="_norm").join(rights.rename({"_norm": "_rnorm"}), on="_rnorm")
    )
    fuzzy = _best(
        fuzzy.with_columns(method=pl.lit("fuzzy")).rename({"_score": "score"}),
        ["score", "imdb_votes", "imdb_id"],
        [True, True, False],
    )

    return pl.concat([exact, fuzzy]).select(
        pl.col("key"),
        pl.col("imdb_id"),
        pl.col("method"),
        pl.col("score").cast(pl.Float64),
    )


def apply_overrides(matches: pl.DataFrame, overrides: pl.DataFrame) -> pl.DataFrame:
    """Hand fixes win: an override replaces the match for its key; null imdb_id removes it."""
    kept = matches.join(overrides.select("key"), on="key", how="anti")
    fixed = overrides.filter(pl.col("imdb_id").is_not_null()).select(
        pl.col("key"),
        pl.col("imdb_id"),
        method=pl.lit("override"),
        score=pl.lit(None, dtype=pl.Float64),
    )
    return pl.concat([kept.select(MATCH_COLUMNS), fixed.cast(dict(kept.schema))])
