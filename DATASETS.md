# Datasets

Every dataset the project uses: where it comes from, which version we use,
how we get it, where it lives in the repo, and what it is for. The rules for
using it (keys, units, missing values) are in `AGENTS.md`. Decisions are in
`docs/decisions.md`.

- `uv run --project pipeline movies acquire` downloads every **static**
  source into `data/raw/` and records version, size and checksum in
  `data/sources.lock.json`.
- **Scraped** sources are collected by `movies scrape` (not written yet).
  The parsed results go to `data/scraped/` and are committed, so nobody has
  to scrape twice.
- Status: ✅ downloaded · 🔄 in progress · ⏳ not started · ➖ optional, not
  used by default.

## 1. Static downloads

| ID | Dataset | Version / snapshot | Licence | Path | Used for | Status |
|---|---|---|---|---|---|---|
| `tmdb` | [TMDB + IMDb, "Ultimate 1Million Movies"](https://www.kaggle.com/datasets/alanvourch/tmdb-movies-daily-updates) (`TMDB_all_movies.csv`) | Kaggle **v1018 = 2026-10-01** (pinned; the dataset updates daily) | Apache 2.0 (data © TMDB / IMDb, non-commercial) | `data/raw/tmdb/` | the main film table: all tasks | ✅ 791.7 MB, 1,252,007 rows |
| `rt_clapper` | [Rotten Tomatoes, Clapper scrape](https://www.kaggle.com/datasets/andrezaza/clapper-massive-rotten-tomatoes-movies-and-reviews), `rotten_tomatoes_movies.csv` only | Kaggle v4 (scraped April 2023) | CC0 | `data/raw/rt_clapper/` | tomatometer + audience score: T2, T3, T5, T6 | ✅ 17.4 MB, 143,258 rows |
| `numbers_budgets` | [The Numbers budgets](https://www.kaggle.com/datasets/dahvid/movie-budgets-and-revenues) | Kaggle v1 | MIT | `data/raw/numbers_budgets/` | budget, domestic + worldwide gross: T2, T5, X1 | ✅ 0.5 MB, 6,518 rows |
| `numbers_metrics` | [The Numbers + metrics](https://www.kaggle.com/datasets/michaelmatta0/movies-ultimate-metrics-features-and-metadata) | Kaggle v1 | MIT | `data/raw/numbers_metrics/` | gross split, franchise, source, creative type: T5, T6 | ✅ 10.4 MB, 6,569 rows (cleaned and raw files) |
| `netflix` | [Netflix Top 10, all weeks by country](https://www.netflix.com/tudum/top10) (`all-weeks-countries.tsv`) | live file; **we use weeks up to 2026-09-27** (later weeks are dropped when cleaning); fetched with a browser User-Agent because Netflix serves an HTML page to the descriptive one | Netflix public data | `data/raw/netflix/` | streaming genre taste: T1, T4, X2 | ✅ 32.6 MB, 512,200 rows (films + TV), weeks 2021-07-04 to 2026-10-04, 94 countries |
| `cpi` | [FRED CPIAUCSL](https://fred.stlouisfed.org/series/CPIAUCSL) | live (monthly, from 1947) | public domain (BLS) | `data/raw/cpi/` | inflation adjustment to 2025 USD | ✅ 956 monthly rows |
| `fx` | [World Bank PA.NUS.FCRF](https://data.worldbank.org/indicator/PA.NUS.FCRF) | live (yearly) | CC BY 4.0 | `data/raw/fx/` | converting non-USD money | ✅ 4.6 MB, 17,490 country-years (12,630 with a value) |
| `world_atlas` | [world-atlas@2](https://github.com/topojson/world-atlas) (Natural Earth), 50m + 110m | npm v2 | ISC / public domain | `data/raw/world_atlas/` | map geometry: T1, X2 | ✅ 0.9 MB |
| `countries_iso` | [ISO-3166 countries with regional codes](https://github.com/lukes/ISO-3166-Countries-with-Regional-Codes) (`all.csv`): ISO-2, ISO-3, ISO numeric, UN M49 region and subregion | commit 145f1ad | CC BY-SA 4.0 | `data/raw/countries_iso/` | builds `data/reference/countries.csv` | ✅ 249 countries |
| `rt_legacy` | [Rotten Tomatoes 2020 dataset](https://www.kaggle.com/datasets/stefanoleone992/rotten-tomatoes-movies-and-critic-reviews-dataset) | Kaggle v1 | CC0 | `data/raw/rt_legacy/` | fallback for films missing from Clapper | ➖ |

## 2. Wikidata ID crosswalk

| ID | Dataset | Version | Licence | Path | Used for | Status |
|---|---|---|---|---|---|---|
| `wikidata` | [Wikidata SPARQL](https://query.wikidata.org): for each IMDb ID (P345) of a Released film with ≥ 1,000 IMDb votes (any year, so a superset of the working subset), the RT id (P1258), Metacritic id (P1712), LUMIERE id (P4282), English Wikipedia article, budget (P2130) and box office (P2142) with currency and qualifiers | live, queried 2026-10 | CC0 | `data/scraped/wikidata_ids.parquet`, `data/scraped/wikidata_money.parquet` | the hub that joins every other source; extra money values | ✅ 53,904 films, 12,446 money rows (with statement rank and date precision, re-queried 2026-10-11) |

Crosswalk result (queried 2026-10-09). Of the 56,601 IMDb IDs sent (Released,
≥ 1,000 votes, no year filter), 53,904 (95.2 %) matched a Wikidata item. Of the matched films:

| Column | Films with a value | Share |
|---|---|---|
| `qid` | 53,904 | 100 % |
| `enwiki_title` | 48,783 | 90.5 % |
| `lumiere_id` | 42,377 | 78.6 % |
| `rt_id` | 39,296 | 72.9 % |
| `mc_id` | 15,960 | 29.6 % |

Money: budget for 5,702 films (5,748 rows, 4,750 in USD), box office for
4,881 films (6,692 rows, 5,938 in USD). Non-USD values are converted in the
clean stage, never imputed.

## 3. Scraped sources (planned)

All of these follow the scraping rules in `AGENTS.md`: at most 1 request per
second, a cache first, resumable, non-commercial academic use. Several of
these sites restrict automated access in their terms, so we keep to a low
rate and commit only derived numbers, never page contents.

| ID | Source | Key | Scope | Gives | Used for | Needs | Status |
|---|---|---|---|---|---|---|---|
| `rt_recent` | Rotten Tomatoes film pages (embedded JSON) | Wikidata P1258 | films from 2023 on in the working subset with an RT id (~2.8k) | critics score, audience score (Popcornmeter), review counts | T3 for recent films | crosswalk | ⏳ |
| `metacritic` | Metacritic film pages | Wikidata P1712 | notable subset with an id (~10k) | Metascore, user score, review counts | T2, T3 (second critic/audience pair) | crosswalk | ⏳ |
| `letterboxd` | `letterboxd.com/tmdb/{tmdb_id}` | TMDB id | notable subset (~13k) | average rating, number of ratings | T3 (cinephile audience) | – | ⏳ |
| `wikipedia` | English Wikipedia infobox (raw wikitext through the MediaWiki API) | enwiki title from the crosswalk | notable films missing budget or gross (~4k) | `budget`, `gross` text, parsed | money coverage | crosswalk | ⏳ |
| `bom_title` | `boxofficemojo.com/title/{imdb_id}` | IMDb id | notable films missing revenue (~4k) | domestic, international, worldwide gross | money coverage | – | ⏳ |
| `bom_country` | `boxofficemojo.com/year/{year}/?area={ISO2}` | title + year (fuzzy) | ~97 markets × years | yearly gross per film per market, theatres, distributor | T1, T4, X2 | – | ⏳ |
| `lumiere` | [LUMIERE](https://lumiere.obs.coe.int) film pages | Wikidata P4282 | notable films released after 1996 (~89 % have an id) | admissions per European market per year | T1, T4, X2 | crosswalk | ⏳ |
| `tmdb_collections` | TMDB API `/movie/{id}` | TMDB id | notable subset (~13k calls) | `belongs_to_collection` (franchises) | T6 | `TMDB_API_KEY` in `.env` | ⏳ |
| `pageviews` | Wikimedia Pageviews API | Wikipedia titles per language | – | monthly views per language edition | – | – | ➖ |

## 4. Reference tables (hand-made, committed)

| File | Contents | Status |
|---|---|---|
| `data/reference/countries.csv` | ISO-2, ISO-3, ISO numeric (to join world-atlas), English name, UN M49 region and subregion, and the other names sources use (`country_aliases.csv`; historical states map to their main successor, D13). Built by `movies reference`. Every Netflix code and every TMDB production country resolves. | ✅ 250 rows |
| `data/reference/genre_families.csv` | each of TMDB's 18 film genres → one of 8 colour families with an Okabe–Ito colour (D11) | ✅ proposal, the team may regroup |
| `data/overrides/*.csv` | hand fixes for title matches, one file per source (D14) | ✅ numbers 334, netflix 105 |

## 5. How the sources join

```
                 Wikidata (QID)  ── P1258 ──> Rotten Tomatoes (Clapper, recent scrape)
                      │          ── P1712 ──> Metacritic
   TMDB+IMDb ── imdb_id          ── P4282 ──> LUMIERE (admissions per market)
   (main table)       │          ── enwiki ─> Wikipedia infobox
        │             └── imdb_id ─────────> Box Office Mojo title pages
        ├── tmdb_id ──> Letterboxd, TMDB API (collections)
        └── title + year (fuzzy) ──> The Numbers, Netflix Top 10, BOM by country
   countries: ISO-2 via data/reference/countries.csv ──> world-atlas (ISO numeric)
```

## 6. Attribution we must show in the app and the report

- "This product uses the TMDB API but is not endorsed or certified by TMDB."
- IMDb ratings and votes come from IMDb data via the TMDB+IMDb Kaggle
  dataset; non-commercial use.
- Wikidata (CC0), Wikipedia (CC BY-SA 4.0), World Bank (CC BY 4.0), Natural
  Earth (public domain), FRED / BLS (public domain), Netflix Top 10, Rotten
  Tomatoes, Metacritic, Letterboxd, Box Office Mojo, The Numbers, LUMIERE
  (European Audiovisual Observatory): named as sources in the app's "About
  the data" panel.

## Clean stage

`movies clean` writes one typed Parquet per source to `data/interim/`
(gitignored). Counts from the run on 2026-10-11:

| File | Rows | What cleaning changed |
|---|---|---|
| `tmdb.parquet` | 1,252,005 (689,411 with an IMDb id) | 0 budget, revenue and runtime → null; 28,539 budgets under $1,000 → null and flagged in `budget_under_1000`; future dates → null; 2 duplicate IMDb ids dropped; production countries as ISO-2 |
| `rt_clapper.parquet` | 142,052 | 1,206 duplicate RT ids dropped (the fullest row kept); box office strings like `$31.4M` → USD |
| `numbers_budgets.parquet`, `numbers_metrics.parquet` | 6,518 and 6,569 | `$0` gross → null; dates parsed; ids like `1,000` parsed (they were null before); in the metrics file two-digit years after 2026-10-01 moved back a century (`15-Dec-39` is 1939, not 2039) |
| `netflix.parquet` | 255,170 | films only, weeks up to 2026-09-27, `score = 11 − rank` |
| `cpi.parquet` | 80 years | yearly mean of the monthly index, `months` shows a partial year |
| `fx.parquet` | 12,537 (213 countries) | World Bank aggregates and empty values dropped, ISO-3 → ISO-2 |

## Join stage

`movies join` links the cleaned sources to TMDB films and writes two files to
`data/interim/` (D14). Counts from the run on 2026-10-11:

| Output | Rows | How it links |
|---|---|---|
| `films.parquet` | 56,431 films in the working subset (Released, 1900–2026, ≥ 1,000 IMDb votes), 13,080 notable (≥ 10,000) | the main table, one row per `imdb_id` |
| RT (Clapper) columns | 35,263 films linked, 22,744 with a tomatometer | Wikidata RT id; the row with a tomatometer wins; an RT id Wikidata gives to two films goes to the one closest to RT's release year |
| Numbers columns | 6,034 films with a budget, 5,086 of them notable | title within ±1 year: of 12,825 rows from both files, 11,527 exact, 126 fuzzy, 334 override; each value comes from the best-matched row that has it |
| `netflix_titles.parquet` | 8,716 Netflix film titles: 7,608 exact, 49 fuzzy, 100 override, 959 unmatched | title, released no later than the year of the first chart week; matched titles hold 98.1 % of the chart score |

`numbers_match` / `numbers_match_score` and the Netflix `method` / `score`
columns say how each value was linked, so the app can mark fuzzy matches.
