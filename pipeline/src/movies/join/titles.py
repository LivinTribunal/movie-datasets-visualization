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


def normalise(title: str | None) -> str | None:
    """Fold case, accents, punctuation and a leading 'The' so titles compare equal."""
    if title is None:
        return None
    text = unicodedata.normalize("NFKD", title)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = text.replace("&", " and ").replace("'", "").replace("’", "")
    text = _NON_ALNUM.sub(" ", text).strip()
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


def match(left: pl.DataFrame, right: pl.DataFrame, *, min_score: float = 90.0) -> pl.DataFrame:
    """Return one row (key, imdb_id, method, score) per left key that matched a right film."""
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
    # block by year window so each title is only scored against films it could match
    pairs = []
    for (lo, hi), group in todo.group_by(["year_min", "year_max"]):
        choices = rights.filter(pl.col("year").is_between(lo, hi))["_norm"].unique().to_list()
        for norm in group["_norm"].unique().to_list():
            for choice, score, _ in process.extract(
                norm, choices, scorer=fuzz.token_sort_ratio, score_cutoff=min_score, limit=None
            ):
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
