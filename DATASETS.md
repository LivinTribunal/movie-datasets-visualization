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
| `tmdb` | [TMDB + IMDb, "Ultimate 1Million Movies"](https://www.kaggle.com/datasets/alanvourch/tmdb-movies-daily-updates) (`TMDB_all_movies.csv`) | Kaggle **v1018 = 2026-10-01** (pinned; the dataset updates daily) | Apache 2.0 (data © TMDB / IMDb, non-commercial) | `data/raw/tmdb/` | the main film table: all tasks | 🔄 |
| `rt_clapper` | [Rotten Tomatoes, Clapper scrape](https://www.kaggle.com/datasets/andrezaza/clapper-massive-rotten-tomatoes-movies-and-reviews), `rotten_tomatoes_movies.csv` only | Kaggle v4 (scraped April 2023) | CC0 | `data/raw/rt_clapper/` | tomatometer + audience score: T2, T3, T5, T6 | 🔄 |
| `numbers_budgets` | [The Numbers budgets](https://www.kaggle.com/datasets/dahvid/movie-budgets-and-revenues) | Kaggle v1 | MIT | `data/raw/numbers_budgets/` | budget, domestic + worldwide gross: T2, T5, X1 | 🔄 |
| `numbers_metrics` | [The Numbers + metrics](https://www.kaggle.com/datasets/michaelmatta0/movies-ultimate-metrics-features-and-metadata) | Kaggle v1 | MIT | `data/raw/numbers_metrics/` | gross split, franchise, source, creative type: T5, T6 | 🔄 |
| `netflix` | [Netflix Top 10, all weeks by country](https://www.netflix.com/tudum/top10) (`all-weeks-countries.tsv`) | live file; **we use weeks up to 2026-09-27** (later weeks are dropped when cleaning) | Netflix public data | `data/raw/netflix/` | streaming genre taste: T1, T4, X2 | 🔄 |
| `cpi` | [FRED CPIAUCSL](https://fred.stlouisfed.org/series/CPIAUCSL) | live (monthly, from 1947) | public domain (BLS) | `data/raw/cpi/` | inflation adjustment to 2025 USD | 🔄 |
| `fx` | [World Bank PA.NUS.FCRF](https://data.worldbank.org/indicator/PA.NUS.FCRF) | live (yearly) | CC BY 4.0 | `data/raw/fx/` | converting non-USD money | 🔄 |
| `world_atlas` | [world-atlas@2](https://github.com/topojson/world-atlas) (Natural Earth), 50m + 110m | npm v2 | ISC / public domain | `data/raw/world_atlas/` | map geometry: T1, X2 | 🔄 |
| `rt_legacy` | [Rotten Tomatoes 2020 dataset](https://www.kaggle.com/datasets/stefanoleone992/rotten-tomatoes-movies-and-critic-reviews-dataset) | Kaggle v1 | CC0 | `data/raw/rt_legacy/` | fallback for films missing from Clapper | ➖ |

## 2. Wikidata ID crosswalk

| ID | Dataset | Version | Licence | Path | Used for | Status |
|---|---|---|---|---|---|---|
| `wikidata` | [Wikidata SPARQL](https://query.wikidata.org): for each IMDb ID (P345) in the working subset, the RT id (P1258), Metacritic id (P1712), LUMIERE id (P4282), English Wikipedia article, budget (P2130) and box office (P2142) with currency and qualifiers | live, queried 2026-10 | CC0 | `data/scraped/wikidata_ids.parquet`, `data/scraped/wikidata_money.parquet` | the hub that joins every other source; extra money values | 🔄 |

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
| `data/reference/countries.csv` | ISO-2, ISO-3, ISO numeric (to join world-atlas), English name, the name variants used by Netflix / BOM / LUMIERE, UN M49 region and subregion | ⏳ |
| `data/reference/genre_families.csv` | each of TMDB's 19 genres → one of ~8 colour families (decided in the design sheets) | ⏳ |
| `data/overrides/*.csv` | hand fixes for title matches, one file per source | ⏳ |

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
