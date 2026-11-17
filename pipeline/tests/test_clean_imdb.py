import polars as pl

from movies.clean.imdb import clean

COLUMNS = ["tconst", "titleType", "isAdult", "startYear", "genres"]


def _raw(rows: list[tuple]) -> pl.LazyFrame:
    return pl.LazyFrame(rows, schema=dict.fromkeys(COLUMNS, pl.String), orient="row")


def test_keeps_movies_and_shorts_in_range_and_drops_the_rest():
    raw = _raw(
        [
            ("tt3", "movie", "0", "1950", "Drama,Crime"),
            ("tt1", "short", "0", "1900", "Short"),
            ("tt4", "tvSeries", "0", "2000", "Drama"),
            ("tt5", "tvMovie", "0", "2000", "Drama"),
            ("tt6", "movie", "1", "2000", "Adult"),
            ("tt7", "movie", "0", "1899", "Drama"),
            ("tt8", "movie", "0", "2027", "Drama"),
            ("tt9", "movie", "0", None, "Drama"),
        ]
    )
    out = clean(raw).collect()
    assert out["imdb_id"].to_list() == ["tt1", "tt3"]
    assert out["year"].dtype == pl.Int16
    assert out["genres"].to_list() == [["Short"], ["Drama", "Crime"]]


def test_null_genres_become_an_empty_list():
    out = clean(_raw([("tt1", "movie", "0", "2000", None)])).collect()
    assert out["genres"].to_list() == [[]]
