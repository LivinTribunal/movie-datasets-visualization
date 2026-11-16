## Implementation brief: P1 country sources

Goal: `movies clean` keeps the TMDB poster path, and `movies derive --source genres`
also writes genre scores per country for two new sources (films produced per country, US
cinema gross), with an `entries` count on every country table.

Context:
- `pipeline/src/movies/derive/genres.py` has `film_genres`, `netflix_country_genre`,
  `lumiere_country_genre` and `run()`. Both country functions return the columns
  `country_iso2, year, genre, family, score, share, coverage, fuzzy_share, estimated_share`,
  sorted by `country_iso2, year, genre`. **Mirror `lumiere_country_genre`** for the two new
  functions: same `keys`, same totals-then-shares-then-join shape.
- `film_genres_df` has one row per film and genre: `imdb_id, genre, family, genre_weight`.
- `films.parquet` (the working subset, one row per `imdb_id`) has among others `imdb_id`,
  `year` (Int16, may be null), `production_countries` (List(String) of ISO-2, may be null),
  `numbers_domestic_gross` (Float64, USD, null when The Numbers has no row) and
  `numbers_match` (`exact`, `fuzzy`, `override` or null).
- `LUMIERE_MIN_FILMS = 20` drops noisy market-years.
- `pipeline/src/movies/clean/tmdb.py` line 13: `TEXT = [...]` lists text columns that
  `parse()` copies with blank → null. The raw CSV has a `poster_path` column, and so does the
  fixture `pipeline/tests/fixtures/tmdb_sample.csv`.
- The join stage passes every tmdb column through to `films.parquet`; do not touch it.

Files (yours only):
- `pipeline/src/movies/clean/tmdb.py`
- `pipeline/src/movies/derive/genres.py`
- `pipeline/tests/test_clean_tmdb.py`
- `pipeline/tests/test_derive_genres.py`

Design:
1. Clean: add `"poster_path"` to `TEXT`. Nothing else.
2. `entries`: every country table gets a last column `entries` (UInt32): the number of
   distinct films behind the scores of that country-year.
   - Netflix: distinct matched `imdb_id` in the country-year.
   - LUMIERE: distinct films of the market-year that have genres. The existing
     `films >= LUMIERE_MIN_FILMS` rule keeps counting all films, as today.
3. `production_country_genre(films, film_genres_df) -> pl.DataFrame`: explode
   `production_countries`, drop rows with a null year or country, join the genres. Per
   `(country_iso2, year, genre, family)`: `score` = sum of `genre_weight`. A co-production
   counts fully in each of its countries. `coverage` 1.0, `fuzzy_share` 0.0,
   `estimated_share` 0.0, `entries` = distinct films of the country-year, `share` as in the
   siblings. No minimum number of films.
4. `us_cinema_country_genre(films, film_genres_df, min_films=LUMIERE_MIN_FILMS)`: films with
   a non-null `year` and `numbers_domestic_gross > 0`. One country, `"US"`; the year is the
   release year. `score` = sum of gross × `genre_weight`. `coverage` = gross of films that
   have genres ÷ all gross of the year. `fuzzy_share` = gross of films with
   `numbers_match == "fuzzy"` that have genres ÷ all gross. `estimated_share` 0.0. `entries`
   = distinct films with genres. Years with fewer than `min_films` films are dropped.
5. Both new functions return the sibling columns in the sibling order plus `entries`, sorted
   the same way, with `year` as Int16.
6. `run()`: also write `country_genre_production.parquet` and `country_genre_us.parquet` to
   `paths.INTERIM`, and print one line each in the style of the existing prints (rows,
   countries, year range).
7. Update the module docstring to name the new outputs.

Tests (add to the existing files, mirror the neighbouring tests' fixtures):
- `test_clean_tmdb.py`: `poster_path` is kept, and a blank one is null.
- `test_netflix_entries_count_distinct_matched_films`
- `test_lumiere_entries_count_films_with_genres`
- `test_production_counts_a_coproduction_in_each_country`: a film with 2 genres and 2
  countries gives score 0.5 per genre in both countries, shares sum to 1, entries 1.
- `test_production_drops_null_year_and_null_country`
- `test_us_cinema_shares_are_gross_weighted`: two films in one year with different gross;
  call with `min_films=1`.
- `test_us_cinema_drops_years_under_min_films`
- `test_us_cinema_fuzzy_share_and_coverage`: one fuzzy film, one film without genres.

Constraints: polars only, pure functions, type hints, ruff line length 100. No new
dependency. Existing tests in both files must still pass (the new `entries` column must not
break their column assertions; update an assertion only if it lists all columns).

Out of scope: `export/`, `validate/`, `join/`, the CLI, docs, running `movies` commands on
real data.

Verify (from `pipeline/`):
- `uv run pytest tests/test_derive_genres.py tests/test_clean_tmdb.py -q` → all pass
- `uv run ruff check src/movies/derive/genres.py src/movies/clean/tmdb.py tests/test_derive_genres.py tests/test_clean_tmdb.py && uv run ruff format --check src tests`
