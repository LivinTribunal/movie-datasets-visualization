# X2: derive extras, export and validate (pipeline)

Spec: `docs/superpowers/specs/2026-11-16-extra-data-design.md` §2 and §3. The
dict value orders in §3 are a contract with the app. Decision D33.

Rules: mirror the nearest code (`derive/money.py`, `derive/ratings.py`,
`export/app.py`), minimal diff, polars, pure functions plus a `run()` that
does the I/O, no new dependency. No tree-changing git, no network, no
`make data`, no full suites. Verify with ruff on your files and `uv run
--project pipeline pytest <your test files>`. Stop after about 40 turns.

Another worker is adding the inputs at the same time (brief
`x1-acquire-clean.md`), so the real interim files do not have them yet. Work
from these column lists and build test frames in code:

- `films.parquet` gains `keywords` (list[str], lower-case), `companies`,
  `cast`, `writers` (list[str]), `overview` (str). It already has
  `certification_us`, `year`, `qid`, `numbers_key`, `numbers_match`
  (`exact`, `fuzzy`, `override`, null). Read `join/films.py` (`numbers_rows`,
  `_key`) for the key format; only keys from the metrics file count.
- `numbers_metrics.parquet` (`numbers_id` i32) gains `theaters_open`,
  `theaters_max` (i32), `legs`, `video_sales`, `domestic_share` (f64). It
  already has `opening_weekend`, `mpaa_rating`, `source`.
- `data/scraped/wikidata_extra.parquet`: `imdb_id, qid, oscar_wins,
  oscar_noms` (i16), `csfd_id, filmaffinity_id, allocine_id, douban_id`
  (str). It may be missing: then those columns are null and `run()` prints a
  note.

Files (only these): `pipeline/src/movies/derive/extras.py` (new),
`pipeline/src/movies/derive/__init__.py`, `pipeline/src/movies/export/app.py`,
`pipeline/src/movies/validate/app.py`, `data/reference/story_sources.csv`
(new), `data/reference/studios.csv` (new),
`pipeline/tests/test_derive_extras.py` (new),
`pipeline/tests/test_export_app.py`, `pipeline/tests/test_validate_app.py`,
`app/scripts/budget.mjs` (data limit 8 → 12 MB), `docs/data-dictionary.md`,
`DATASETS.md` (Wikidata row: the two new queries).

## derive/extras.py → `data/interim/extras.parquet`

`extras(films, metrics, wikidata_extra, cpi, story_map, studios)` returns one
row per `imdb_id` in `films`, columns as in spec §2.

- `story_sources.csv` (`origin,label,category`). List every The Numbers
  `Source` value from `data/raw/numbers_metrics/Top Movies (Cleaned Data).csv`
  and map each. Categories: `original` (Original Screenplay only), `book`
  (fiction or non-fiction book, short story, novel, children's, young adult,
  light novel, magazine or article), `comic` (comic, graphic novel, manga,
  webcomic), `true_story` (real life events, true story, biography, memoir,
  autobiography, real person), `stage` (play, musical, opera, ballet),
  `screen` (movie, remake, TV, short film, cartoon, anime, video game,
  spin-off, reboot, web series), `other` (toy, folk tale, legend, fairy tale,
  song, religious text, ride and the rest). TMDB keywords to map: based on
  novel or book, based on true story, biography, remake, based on comic,
  based on play or musical, based on manga, based on tv series, based on
  children's book, based on short story, based on young adult novel, based on
  video game, based on memoir or autobiography, spin off, based on movie,
  reboot, based on short film, based on toy, based on real person, based on
  graphic novel, based on myths, legends or folklore, based on fairy tale,
  based on song, poem or rhyme, live action remake, based on cartoon, based on
  magazine, newspaper or article, based on webcomic or webtoon, based on light
  novel, based on anime. `sequel` is not a story source. With several mapped
  keywords the first in the CSV's row order wins; put specific rows first.
- `studios.csv` (`company,studio`). disney: Walt Disney Pictures, Pixar,
  Marvel Studios, Lucasfilm Ltd., Touchstone Pictures, Walt Disney Animation
  Studios, Hollywood Pictures, Searchlight Pictures, 20th Century Studios.
  fox: 20th Century Fox, Fox Searchlight Pictures, Fox 2000 Pictures. warner:
  Warner Bros. Pictures, New Line Cinema, Warner Bros. Animation, DC Films,
  HBO Films, Castle Rock Entertainment. universal: Universal Pictures, Focus
  Features, Illumination, DreamWorks Animation, Working Title Films. sony:
  Columbia Pictures, TriStar Pictures, Screen Gems, Sony Pictures Animation,
  Sony Pictures Classics. paramount: Paramount Pictures, Paramount Animation,
  Nickelodeon Movies. lionsgate: Lionsgate, Summit Entertainment, Lions Gate
  Films. mgm: Metro-Goldwyn-Mayer, United Artists, Orion Pictures. Check the
  spellings against the TMDB `production_companies` values in
  `data/interim/tmdb.parquet`'s source CSV.
- CPI to 2025: same table and formula as `derive/money.py`
  (`interim/cpi.parquet`, `BASE_YEAR`); import the constant, do not copy it.
- Register the stage in `derive/__init__.py` after money.
- Tests: story source precedence (Numbers over TMDB, null when neither, first
  mapped keyword wins), age rating fallback and `Not Rated` → `NR`, studio
  (first listed company, `independent`, null), CPI scaling, the metrics join
  only for metrics keys, `numbers_fuzzy`, Oscar null vs 0.

## export/app.py

- Join `extras.parquet` in `films_table`; add the spec §3 columns to
  `FILM_COLUMNS` and `numbers_fuzzy` as the sixth entry of `FLAG_COLUMNS`.
- In `write_films` add the dict columns with the §3 value orders (constants
  next to `MONEY_SOURCES`) and the numeric columns.
- `write_detail(df, notable, out_dir)` writes `films_detail_{k}.pack` for rows
  `[1000k, min(1000k + 1000, notable))`, string columns in spec order, after
  deleting stale `films_detail_*.pack` files. `run()` calls it and adds
  `detail`, the three counts and the §3 notes to `meta.json`, and prints the
  shards' total size.

## validate/app.py

Add the new films columns to `SCHEMA`; for the shards check that every shard
listed by `meta.detail.shards` exists and has `shard_size` rows except the
last; check dict value sets, non-negative money, `oscar_noms >= oscar_wins`,
and a 600 KB limit per shard. Mirror the existing checks.

## Report

Files changed, test results, row counts of the two CSVs.
