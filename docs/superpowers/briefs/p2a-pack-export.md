## Implementation brief: P2a pack writer and export v2

Goal: `movies export` writes the app's tables as `MXP1` pack files (`films.pack`,
`films_text.pack`, `country_genre.pack`, `country_year.pack`, `franchises.pack`) instead of
columnar JSON, with all working-subset films.

Context:
- Read `docs/superpowers/specs/2026-11-16-movie-explorer-app-design.md` **§2 only** (lines
  ~45–155). It fixes the byte layout and every column's name, type, scale and null sentinel.
  Build exactly that.
- `pipeline/src/movies/export/app.py` today: pure table functions (`films_table`,
  `genre_year`, `country_genre_table`, `franchises_table`), `to_columns`, `_write`,
  `_write_table`, and `run()` that reads `data/interim/*.parquet`. Keep this shape: pure
  functions build frames, only `run()` touches disk.
- Interim inputs `run()` may read (all exist after `movies derive`):
  - `films.parquet`: one row per working-subset film. Has `imdb_id` (`tt…`), `tmdb_id`,
    `title`, `director`, `poster_path`, `year`, `runtime`, `imdb_votes`, `notable`,
    `production_countries` (list of ISO-2 or null), `numbers_match`.
  - `money.parquet`: `imdb_id`, `budget_usd`, `budget_usd2025`, `revenue_usd`,
    `revenue_usd2025`, `roi`, `budget_src`, `revenue_src`, `budget_currency`,
    `revenue_currency`, `budget_disagree`, `revenue_disagree`.
  - `ratings.parquet`: `imdb_id`, the seven `*_100` columns, `gap`, `mc_critic_reviews`.
  - `film_genres.parquet`: `imdb_id, genre, family, genre_weight`.
  - `franchises.parquet`: `collection_id, collection_name, installment, n_released, tmdb_id,
    imdb_id (may be null), title, release_date, imdb_100, imdb_100_vs_first,
    tomatometer_100, audience_100, revenue_usd2025, revenue_vs_first` (and `_vs_prev`
    columns that are no longer exported).
  - `country_genre_netflix.parquet`, `country_genre_lumiere.parquet`,
    `country_genre_us.parquet`, `country_genre_production.parquet`: each
    `country_iso2, year, genre, family, score, share, coverage, fuzzy_share,
    estimated_share, entries`.
  - `data/reference/genre_families.csv` (`genre, family, family_order, colour`; row order is
    the genre order) and `countries.csv`.
- The project has no numpy. Pack bytes with the stdlib (`struct`, `gzip`, `json`).

Files (yours only):
- `pipeline/src/movies/export/pack.py` (new)
- `pipeline/src/movies/export/app.py`
- `pipeline/tests/test_pack.py` (new)
- `pipeline/tests/test_export_app.py`

Design:
1. `pack.py`
   - Column builders, each returning a small frozen dataclass `Col(header: dict, data: bytes)`:
     `num(name, series, type, *, scale=None, null=None)`,
     `dict_col(name, series, values, *, width=1, null=None)`,
     `list_col(name, series, values)`, `str_col(name, series)`.
   - `num`: with `scale`, the raw value is `round(value / scale)`. A null needs `null`
     (ints) or becomes NaN (`f32`); a null without a sentinel, or a value that does not fit
     the type or equals the sentinel, raises `ValueError` naming the column.
   - `dict_col` / `list_col`: a value missing from `values` raises `ValueError`. A null list
     is an empty list.
   - `str_col`: null is written as an empty string.
   - `write_pack(path, rows, meta, cols)`: lays out header and buffers as in §2.1, gzips
     with `mtime=0` and no file name in the gzip header, so two runs give identical bytes.
   - `read_pack(path) -> Pack` with `rows`, `meta`, `header` and `columns: dict[str, list]`
     decoded to plain Python (None for missing, scale applied, dict codes as strings, lists
     as `list[str]`). The validator and the tests use it.
2. `app.py`
   - `films_table(films, money, ratings, film_genres, franchises)`: every film, sorted by
     `imdb_votes` descending then `imdb_id`. Carries the spec's columns in logical form
     (`genres` and `families` as lists; the five flags as booleans, computed as today:
     `_converted`, the `*_disagree` columns, `money_fuzzy`) plus `title`, `director`,
     `poster`, `notable`. `collection_id` and `installment` come from `franchises` by
     `imdb_id`.
   - `write_films(df, genres, families, countries, core_path, text_path)`: builds
     `genre_mask`, `family_mask`, `flags` and writes both packs with `meta` as in §2.2.
     `imdb` is the integer after `tt`.
   - `country_tables(sources)`: `sources` is a list of `(source, measure, frame)`; the
     `cinema` source appears twice (LUMIERE with `admissions`, US with `gross_usd`).
     Returns the `country_genre` and `country_year` frames of §2.3. `genre` is the index in
     the genre order.
   - `franchises_table(franchises, films_out, film_genres)`: adds `film_row` (the row of the
     part's `imdb_id` in `films_out`, else null), `year` from `release_date`, and
     `family_mask` from the first part, in installment order, that has genres (0 if none).
     Drops the `_vs_prev` columns. `meta.collections` is `[[id, name], …]` sorted by id.
   - `run()`: writes the five packs, `countries.json` and `genre_families.json` as today,
     copies `countries-50m.json` (not 110m) to `countries.topo.json`, and writes
     `meta.json` with the existing keys plus `attribution` (the three bullets of
     `DATASETS.md` §6 as plain strings) and `sources` (one sentence per map source:
     what it covers and what it leaves out, in the tone of `NOTES`). Counts: `films`,
     `notable`, `with_budget`, `with_revenue`, `with_gap`, `netflix_countries`,
     `cinema_markets`, `production_countries`, `franchises`. A missing optional input
     (`country_genre_lumiere`, `_us`, `_production`) is skipped with a printed line, as the
     LUMIERE file is today.
   - Delete `genre_year`, and stop writing `films.json`, `genre_year.json`,
     `country_genre.json`, `franchises.json`; `run()` removes those four files if they exist.
   - `SCHEMA` is still imported from `movies.validate.app` for the two JSON tables only.
   - Each written file prints its name and size, as `_write` does.

Tests:
- `test_pack.py`: one round-trip test per column type (`u8`, `u16` with scale and null,
  `i16` with scale and null, `u32`, `f32` with NaN, `dict` with null, `list` with an empty
  list, `str` with null and non-ASCII); every buffer offset is a multiple of 8; two writes
  of the same input are byte-identical; `num` raises on a null without a sentinel and on an
  out-of-range value; `dict_col` raises on an unknown value.
- `test_export_app.py`: rewrite for the new functions, keeping the `FILMS`, `MONEY`,
  `RATINGS`, `FILM_GENRES`, `FRANCHISES` fixtures (extend them with the new columns). Keep
  the module-level names: another test file imports them. Cases: films sort by votes and
  the notable ones form a prefix; masks and flags have the right bits; nominal and 2025
  money are both kept; a film outside every franchise has null `collection_id`;
  `country_tables` gives one `country_year` row per source-country-year with the right
  `measure`, and the US rows land in `cinema`; `franchises_table` sets `film_row`, `year`
  and `family_mask`; `write_films` then `read_pack` returns the same values.

Constraints: stdlib and polars only; pure functions; type hints; ruff line length 100.
Deterministic output: sorted rows, no timestamps.

Out of scope: `validate/` and `tests/test_validate_app.py` (they break until slice P2b;
do not run or fix them), `derive/`, the CLI, docs, running `movies export` on real data.

Verify (from `pipeline/`):
- `uv run pytest tests/test_pack.py tests/test_export_app.py -q` → all pass
- `uv run ruff check src/movies/export tests/test_pack.py tests/test_export_app.py && uv run ruff format --check src/movies/export tests/test_pack.py tests/test_export_app.py`
