# X1: extra columns in acquire and clean (pipeline)

Spec: `docs/superpowers/specs/2026-11-16-extra-data-design.md` §1. Decisions
D33, D34 in `docs/decisions.md`.

Rules: mirror the nearest code in the same file, minimal diff, polars, type
hints, no new dependency. Do not run git commands that change the tree. Do
not run anything that reaches the network, `movies acquire`, `make data` or
the full test suite. Verify with `uv run --project pipeline ruff check` /
`ruff format --check` on your files and `uv run --project pipeline pytest
<your test files>`. Stop after about 40 turns and report what is left.

Files (only these): `pipeline/src/movies/acquire/download.py`,
`pipeline/src/movies/acquire/wikidata.py`, `pipeline/src/movies/clean/tmdb.py`,
`pipeline/src/movies/clean/numbers.py`, `pipeline/src/movies/join/films.py`
(only if the new tmdb columns do not reach `films.parquet`),
`pipeline/tests/test_wikidata.py`, `pipeline/tests/test_clean_tmdb.py`,
`pipeline/tests/test_clean_numbers.py`, fixtures under
`pipeline/tests/fixtures/`, `.env.example`.

## 1. Request header contact (D34)

`download.py` builds its `USER_AGENT` constant with a contact that must move
out of the code. Read the contact from the `MOVIES_CONTACT` environment
variable, falling back to
`REPO_URL = "https://github.com/LivinTribunal/movie-datasets-visualization"`,
keeping the rest of the string as it is. Build the header inside
`make_client` so a value set after import still counts. Add
`MOVIES_CONTACT=` with a one-line comment to `.env.example`. After your edit
no contact other than the repo URL may be written anywhere in the code.

## 2. Wikidata: two more queries

In `acquire/wikidata.py` add `AWARDS_QUERY` and `EXTIDS_QUERY` to `QUERIES`
(kinds `awards`, `extids`). The cache file name includes a hash of each
query, so the existing `ids` and `money` caches stay valid and only the new
kinds will be fetched.

- awards: `?film wdt:P345 ?imdb`, then a UNION of `p:P166/ps:P166 ?award`
  (BIND "win" AS ?kind) and `p:P1411/ps:P1411 ?award` (BIND "nom"), keeping
  Academy Award categories: `?award (wdt:P31|wdt:P361) wd:Q19020`. Select
  `?imdb ?film ?award ?kind`. Note in a comment that the class pattern is
  checked on the real run against Titanic (tt0120338: 11 wins, 14
  nominations), The Shawshank Redemption (tt0111161: 0 / 7) and The Godfather
  (tt0068646: 3 / 11).
- extids: `?imdb ?film` plus OPTIONAL `wdt:P2529 ?csfd`, `wdt:P480 ?fa`,
  `wdt:P1265 ?allocine`, `wdt:P4529 ?douban`.
- Parsers `parse_awards(payload)` → tuples `(imdb, qid, award_qid, kind)` and
  `parse_extids(payload)` → dicts, mirroring `parse_ids`.
- `aggregate_extra(award_rows, extid_rows, id_rows) -> pl.DataFrame`: one row
  per imdb_id that has a QID in `id_rows`; columns `imdb_id, qid, oscar_wins,
  oscar_noms` (Int16, distinct award QIDs; noms counts the union of nominated
  and won, so noms ≥ wins; 0 when the film has a QID and no Oscar rows), and
  `csfd_id, filmaffinity_id, allocine_id, douban_id` (String; several values
  → the first after sorting). Sorted by imdb_id.
- `build()` also writes it to `paths.SCRAPED / EXTRA_OUT`
  (`"wikidata_extra.parquet"`), returns all three paths, and prints coverage
  per column like the existing lines.
- Tests: small JSON fixtures shaped like `sparql_ids.json`; cover the win/nom
  union, the 0 for a QID without awards, several ids → first sorted.

## 3. clean/tmdb.py

Add to the `parse` select (raw `keywords` is `|`-separated;
`production_companies`, `cast`, `writers` are `, `-separated):

- `keywords`: list[str] split on `"|"`, lower-cased, stripped, empties
  dropped, empty list → null.
- `companies`: `_names("production_companies")`, empty → null.
- `cast`: first 5 of `_names("cast")`; `writers`: first 3 of
  `_names("writers")`; empty → null.
- `overview`: stripped, `""` → null.

Check that the five columns reach `data/interim/films.parquet` through
`join/films.py`; if it selects columns explicitly, add them there. Extend
`tests/fixtures/tmdb_sample.csv` (keep it small) and `test_clean_tmdb.py`.

## 4. clean/numbers.py, `clean_metrics`

From `Top Movies (Cleaned Data).csv`:

- `theaters_open`, `theaters_max` (Int32) from "Theater counts", e.g.
  `"4,134 opening theaters/4,202 max. theaters, 9.2 weeks average run per
  theater"`; commas removed; 0 → null; text without the pattern → null.
- `legs` (Float64) from "Legs"; ≤ 0 → null.
- `video_sales` via `parse_usd` from "Total Est. Domestic Video Sales (USD)";
  add it to `MONEY`.
- `domestic_share` (Float64, percent) from "Domestic Share Percentage".

Extend `numbers_metrics_sample.csv` and `test_clean_numbers.py` with one row
that has all of these and one that has none.

## Report

Files changed, test results, and the text of the two new queries.
