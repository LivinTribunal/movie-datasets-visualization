## Implementation brief: P2b validator for the pack files

Goal: `movies validate` checks the new app data (six `.pack` files, three JSON files, the
map geometry) against the spec and fails CI on a broken invariant or an oversized file.

Context:
- Read `docs/superpowers/specs/2026-11-16-movie-explorer-app-design.md` **§2 only**. It is
  the contract the validator enforces: file list with size limits, pack columns with types,
  and the meaning of each.
- `pipeline/src/movies/validate/app.py` today checks the old columnar JSON: `SCHEMA`,
  `_load`, `_outside`, `check(data_dir) -> list[str]`, `run()`. Keep that shape: `check`
  collects error strings like `films.pack: year outside 1900-2026` and never raises.
- `pipeline/src/movies/export/pack.py` has `read_pack(path) -> Pack` with `rows`, `meta`,
  `header` (`header["columns"]` is a list of `{"name", "type", …}`) and `columns:
  dict[str, list]` decoded to Python values (None = missing, scale applied, `dict` columns
  as strings, `list` columns as `list[str]`).
- `pipeline/src/movies/export/app.py` has the writers the tests use to build a valid
  directory: `films_table(films, money, ratings, film_genres, franchises)`,
  `write_films(df, genres, families, countries, core_path, text_path, poster_path)`,
  `country_tables(sources, genres)`, `write_country_tables(country_genre, country_year,
  genres, countries, genre_path, year_path)`, `franchises_table(...)`,
  `write_franchises(...)`, `to_columns`. Read their signatures before you write the tests.
  `app.py` imports `SCHEMA` from the validator for `countries.json` and
  `genre_families.json`: keep those two entries.
- `pipeline/tests/test_export_app.py` exports the fixtures `FILMS`, `MONEY`, `RATINGS`,
  `FILM_GENRES`, `FRANCHISES`. The current `tests/test_validate_app.py` builds a valid
  directory from them in `tmp_path`, then breaks one thing per test. Keep that pattern.
- In the country packs the `source` and `country` dictionaries are sorted alphabetically.

Files (yours only):
- `pipeline/src/movies/validate/app.py`
- `pipeline/tests/test_validate_app.py`

Design:
1. Constants
   - `SCHEMA`: only `countries.json` and `genre_families.json`.
   - `PACKS: dict[str, dict[str, str]]`: for each of the six packs, column name → type, in
     spec order. `check` compares names, order and types with the pack header.
   - `LIMITS: dict[str, int]` in bytes: `films.pack` 3.0 MB, `films_text.pack` 1.2 MB, `films_poster.pack` 2.0 MB,
     `country_genre.pack` 1.0 MB, `country_year.pack` 0.2 MB, `franchises.pack` 0.2 MB,
     `countries.topo.json` 0.9 MB (1 MB = 1,000,000 bytes). `TOTAL_LIMIT` = 8 MB for the
     whole directory.
   - `STALE = ("films.json", "genre_year.json", "country_genre.json", "franchises.json")`:
     a stale file is an error.
2. Loading: a missing or unreadable file is one error and its checks are skipped; a pack
   with wrong columns is one error and its checks are skipped. Nothing raises.
3. Checks, each one error string naming the file:
   - **films.pack**: `imdb` unique; `year` has no nulls and is in 1900–2026; `imdb_votes`
     never increases down the rows; `0 < meta.notable ≤ rows`, the last notable row has at
     least 10,000 votes and the next row, if any, fewer; the seven `*_100` columns in
     0–100; `gap` in −100…100; the four money columns and `roi` not negative; `budget_src`
     and `revenue_src` in `numbers, tmdb, wikidata, wikipedia` or null; every country in
     `countries.json`; `meta.genres` equals the `genre` column of `genre_families.json` in
     order and `meta.families` its distinct families in `family_order`; `genre_mask` has no
     bit beyond the genre list; `family_mask` equals the families of the genres in
     `genre_mask`; `installment` is null exactly when `collection_id` is null; every
     non-null `collection_id` is a collection of `franchises.pack`.
   - **films_text.pack**, **films_poster.pack**: same number of rows as `films.pack`; no
     null `title`.
   - **franchises.pack**: the existing franchise checks, ported (installments exactly
     1…`n_released`, `n_released ≥ 3`, ratings in 0–100, `imdb_100_vs_first` is 0 at
     installment 1 when set, `revenue_vs_first` not negative); `film_row`, when set, is a
     row of `films.pack` whose `collection_id` is this collection; every `collection_id`
     has a name in `meta.collections`.
   - **country_genre.pack / country_year.pack**: `source` in `netflix, cinema,
     production`; countries in `countries.json`; `genre` below the genre count; `score` not
     negative; no duplicate key in either file; both files hold the same set of
     (source, country, year); `coverage`, `fuzzy_share`, `estimated_share` in 0–1;
     `fuzzy_share ≤ coverage`; `entries ≥ 1`; `measure` in `chart_score, admissions,
     gross_usd, films`.
   - **meta.json**: has `snapshots`, `base_year`, `counts`, `notes`, a non-empty
     `attribution` list, and `sources` with exactly the three source keys.
   - **sizes**: each file within `LIMITS`, the directory within `TOTAL_LIMIT`; the message
     gives the size and the limit in MB.
   - **stale files**: each one present is an error.
4. `run()`: as today, prints the errors and exits 1, or prints
   `app data valid: <n> files, <total> MB`.

Tests (`test_validate_app.py`, rewritten): a fixture builds a valid directory with the
real writers, then one test per rule above breaks exactly that rule and asserts the error
text names the file and the rule. Break a pack by rebuilding it from an edited frame, not by
patching bytes. Sizes: monkeypatch `LIMITS` / `TOTAL_LIMIT` down. Keep
`test_valid_dir_has_no_errors`, `test_missing_file` and `test_wrong_columns`.

Constraints: stdlib and polars only; `check` is a pure function of the directory; type
hints; ruff line length 100. No `# noqa`.

Out of scope: `export/`, `derive/`, `tests/test_export_app.py`, the CLI, docs, the real
`app/public/data` (the architect runs `movies validate` on it).

Verify (from `pipeline/`):
- `uv run pytest tests/test_validate_app.py -q` → all pass
- `uv run ruff check src/movies/validate tests/test_validate_app.py && uv run ruff format --check src/movies/validate tests/test_validate_app.py`
