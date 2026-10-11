# Project plan: Movies, money, ratings and genre taste around the world

PV251 Visualization, autumn 2026, seminar group 5.
Team: Štefan Moravík, Matúš Buzgo, Emma Tomášová.

This is the working plan. The data-and-task analysis we handed in as HW1 is
`materials/project.md`. Decisions with their reasons go to `docs/decisions.md`.

---

## 1. Goal

Build one interactive web app in which a user can explore how **money**
(budget, box office, return on investment), **reception** (critics compared
with audiences) and **genre taste** (over time and per country, in cinemas
and on Netflix) relate to each other.

What the course requires (seminar syllabus, from IS):

- an interactive data visualization project for a team of 2–3 people
- **3+ linked views** with interactive features: filtering, selection,
  drill-down
- free choice of topic and technology
- design done with the **Five Design Sheets (FDS)** method as homework 2–4
- what we submit: source code, a **link to the deployed version**, a **video
  demo**, and a **short report** with motivation, data sources and
  preprocessing, design choices, interesting observations, screenshots,
  technologies used, who did what, and lessons learned
- **final deadline: 31 January 2027**, and ideally before we take the exam.
  The grade is not given without an accepted project. Excellent work earns
  up to +5 exam points; a late or incomplete homework costs −1 point each.

What we want for ourselves:

1. Every task below can be answered in the app, and the report names one
   concrete insight for each task.
2. The user is always told how the data was transformed: the lecture says
   *"We always have to inform the user that the data has been
   transformed!!!"* Imputed, converted and inflation-adjusted values are
   marked in the views.
3. The app is a fully static site (`app/dist`). We run it **mainly locally**
   (any static file server) and also publish it on **GitHub Pages** (free).
   Nothing in the app depends on either host.

## 2. Tasks

T1–T6 are the tasks from the submitted `materials/project.md`. X1–X5 are
extra tasks from our earlier draft.

| ID | Question | Action → Target | Status |
|---|---|---|---|
| **T1** | Which genres dominate cinemas and streaming in each country, and how do countries differ? | Discover/Compare → distribution over space, similarity | core |
| **T2** | Are commercially successful films also better rated, by critics, by audiences, or both? | Discover → correlation | core |
| **T3** | Where do critics and audiences disagree most ("critic darlings" vs "crowd pleasers"), and has the gap changed over time? | Locate/Identify → outliers, distribution, trend | core |
| **T4** | How has the popularity of genres changed over time? | Discover/Compare → trend | core |
| **T5** | Does a higher budget buy popularity and good ratings, and does this differ by genre? | Discover → correlation by genre | core |
| **T6** | Do sequels get worse? Which franchises are the exception? | Browse/Compare → trend within a series, outliers | core |
| X1 | Which genres earn the most and which have the best ROI? | Summarize/Compare → distribution, extremes | stretch, uses the same data as T2/T5 |
| X2 | Is the genre mix in cinemas the same as on Netflix, country by country? | Compare → similarity of two distributions | stretch, uses the same data as T1 |
| X3–X5 | Home bias vs Hollywood, release seasonality, director–actor network | – | only if time is left |

## 3. Timeline

Our seminars are on Mondays. Dates marked *(inferred)* are not published yet.
They assume each homework is due on the seminar day, like HW1 (Mon 5.10)
and HW2 (Mon 19.10).

| When | Course milestone | Data / pipeline | App |
|---|---|---|---|
| **done** | HW1, data and tasks (Mon 5.10) | Sources explored, sizes and coverage measured | – |
| **9.10 – 19.10** | **HW2: Sheet 1, brainstorm**, due **Mon 19.10** (Seminar 3: D3 demo) | Repo and CI set up. Download the static sources: TMDB+IMDb Kaggle, Clapper RT, The Numbers, Netflix TSV, CPI, FX rates, Natural Earth. Wikidata ID crosswalk. | Wireframe ideas go onto Sheet 1 |
| **19.10 – 2.11** | **HW3: Sheets 2–4**, three different designs, due Mon 2.11 *(inferred)*. Seminar 4: speed-dating | Core pipeline: subsets, cleaning, genres, money v1 (TMDB + The Numbers + Wikidata), ratings. Start the long scrapes (RT 2023+, TMDB collections, BOM by country, LUMIERE) in the background. | React + Vite + D3 skeleton, shared state store, data loader, deploy of an empty shell |
| **2.11 – 16.11** | **HW4: Sheet 5, final design**, due Mon 16.11 *(inferred)*. Seminar 5: presentations | Scrapes finished, fuzzy joins for Netflix and BOM, money v2 (Wikipedia, BOM), first full export of the app data. Validation in CI. | First real view: the film scatter (T2/T3/T5) on real data |
| **16.11 – 6.12** | Seminar 6: consultation, Mon 30.11 *(inferred)*. Bring a working prototype. | Fix data problems the views expose; add aggregates when a view needs them | Map (T1), genre timeline (T4), franchise view (T6), linking between all views |
| **7.12 – 20.12** | – | Freeze data v1.0 | Polish: colour-blind check, legends, data-transformation notes, performance, stretch tasks X1/X2 |
| **Jan 2027** | **Submit by Fri 15.1 (our target)**, hard deadline **31.1** | – | Video demo, report, screenshots, final deploy |

The last week before each homework deadline belongs to the design sheet. Data
work runs in parallel because the scrapes take days of wall-clock time.

## 4. Data pipeline

### 4.1 Sources and how we get them

| Source | Gives us | How we get it | Size |
|---|---|---|---|
| TMDB + IMDb (Kaggle, `alanvourch/tmdb-movies-daily-updates`) | main film table | Kaggle CLI, frozen snapshot of **2026-10-01** | 1.25M rows, ~790 MB |
| Wikidata SPARQL | **ID crosswalk**: IMDb → RT (P1258), Metacritic (P1712), LUMIERE (P4282), enwiki; budget P2130, box office P2142 | batched SPARQL queries | ~60k films |
| Rotten Tomatoes, Clapper (Kaggle) | tomatometer and audience score up to April 2023 | Kaggle CLI | 143k titles |
| Rotten Tomatoes pages | scores for films from 2023 on | scrape (embedded JSON) | ~2.8k films |
| Metacritic pages | Metascore and user score | scrape | ~10k films |
| Letterboxd | average rating, a third audience score | scrape `letterboxd.com/imdb/{imdb_id}` | ~13k films (notable subset) |
| The Numbers (2 Kaggle scrapes) | budget, domestic and worldwide gross, franchise, source | Kaggle CLI | 6.5k films |
| English Wikipedia infobox | budget and gross for notable films that miss them | MediaWiki API (raw wikitext) | ~4k films |
| Box Office Mojo title pages | worldwide gross for films without revenue | scrape | ~4k films |
| Box Office Mojo by country | yearly gross per market (T1, T4, X2) | scrape `year/{y}/?area={ISO2}` | ~97 markets × years |
| LUMIERE | admissions per film per European market per year | scrape through the LUMIERE ID | notable films after 1996 |
| Netflix Top 10 | weekly film ranks in 94 countries | `all-weeks-countries.tsv` | 255k film rows |
| TMDB API `/movie/{id}` | `belongs_to_collection` (franchises) | API key, notable subset | ~13k calls |
| FRED `CPIAUCSL`, World Bank `PA.NUS.FCRF` | inflation, exchange rates | CSV download | small |
| Natural Earth / `world-atlas` | country shapes | npm package / TopoJSON | small |

Links:
[TMDB+IMDb](https://www.kaggle.com/datasets/alanvourch/tmdb-movies-daily-updates) ·
[Clapper RT](https://www.kaggle.com/datasets/andrezaza/clapper-massive-rotten-tomatoes-movies-and-reviews) ·
[older RT, fallback until 2020](https://www.kaggle.com/datasets/stefanoleone992/rotten-tomatoes-movies-and-critic-reviews-dataset) ·
[The Numbers budgets](https://www.kaggle.com/datasets/dahvid/movie-budgets-and-revenues) ·
[The Numbers + metrics](https://www.kaggle.com/datasets/michaelmatta0/movies-ultimate-metrics-features-and-metadata) ·
[Netflix Top 10](https://www.netflix.com/tudum/top10) ·
[LUMIERE](https://lumiere.obs.coe.int) ·
[Wikidata SPARQL](https://query.wikidata.org) ·
[FRED CPIAUCSL](https://fred.stlouisfed.org/series/CPIAUCSL) ·
[World Bank FX](https://data.worldbank.org/indicator/PA.NUS.FCRF) ·
[world-atlas](https://github.com/topojson/world-atlas)

Scrape URL patterns: RT and Metacritic pages through the Wikidata IDs
(P1258, P1712); `boxofficemojo.com/title/{imdb_id}`;
`boxofficemojo.com/year/{year}/?area={ISO2}`; LUMIERE through P4282;
`letterboxd.com/imdb/{imdb_id}`.

### 4.2 Pipeline stages

```
acquire  →  data/raw/        downloads, never edited by hand
scrape   →  data/cache/      one cached HTTP response per URL (so re-runs are free)
         →  data/scraped/    parsed scrape results, committed (slow to rebuild)
clean    →  data/interim/    one tidy Parquet per source, typed, with keys normalised
join     →  data/interim/films.parquet   one row per film, every value with its source
derive   →  money in constant USD, ROI, normalised ratings, gaps, genre weights
export   →  app/public/data/  small files the app loads (committed)
validate →  schema and invariant checks, also run in CI
```

### 4.3 Preprocessing rules

These are proposals until they are in `docs/decisions.md`.

**Subsets**
- *Working subset*: `status == Released`, release year 1900–2026, IMDb votes
  ≥ 1,000. About 56.6k films. Used for genre trends (T4) and for T3.
- *Notable subset*: IMDb votes ≥ 10,000. About 13.1k films. Used for the money
  tasks (T2, T5, T6, X1), because only there is money coverage good enough
  (~79 % budget, ~88 % revenue after enrichment).

**Keys**
- The film key is `imdb_id` (`tt\d+`). The TMDB `id` is kept as a secondary
  key. Wikidata is the hub that links all other IDs.
- The country key is ISO 3166-1 alpha-2. Every source's country name or code
  is mapped through one table, `data/reference/countries.csv`, which also
  holds the UN M49 region (for the region → country hierarchy).
- Matching by title (Netflix, BOM by country, The Numbers): normalise the
  title (case, accents, punctuation, leading "The"), match exactly on
  title + year (±1 year), then use `rapidfuzz` with a score of at least 90,
  and when several films match take the one with the most votes. Hand fixes
  go to `data/overrides/*.csv`. The match rate per source is reported. The
  rules as built, including the Netflix year window, are in D14.

**Missing values and cleaning** (lecture 3)
- TMDB stores unknown budget, revenue and runtime as `0`. We recode them to
  null. A missing value is never stored as 0 or as a sentinel value.
- **We do not impute money** with means or neighbours, because that would
  invent box office. Missing stays missing and the views show coverage
  instead. Enrichment from other sources is not imputation: it is a real
  value with its source recorded.
- Budgets under $1,000 (172 films) are unit errors and become null, unless
  another source gives a value.
- Remove duplicate `imdb_id`s and invalid or future dates.

**Money**
- Each money field is taken from the first source that has it, in a fixed
  order, and its source is stored in `budget_src` and `revenue_src`.
  Proposed order. Budget: The Numbers → TMDB → Wikidata → Wikipedia.
  Revenue: The Numbers worldwide → BOM worldwide → TMDB → Wikidata →
  Wikipedia.
- When two sources differ by more than 25 %, the film gets a flag (for
  the report and for spot checks).
- Non-USD values are converted at the release-year average exchange rate,
  then everything is adjusted with CPI to **constant 2025 USD**. Nominal
  values are kept too.
- `profit = revenue − budget`; `roi = revenue / budget`, only when
  budget ≥ $100k. ROI uses a log scale in the views.

**Ratings**
- Everything is rescaled to 0–100: IMDb ×10, TMDB ×10, Metacritic user ×10,
  Letterboxd ×20.
- Critics: `tomatometer` (main), `metascore` (second).
  Audience: `audience_score` (main), `imdb_rating`, `mc_user_score`,
  `letterboxd_avg`.
- `gap = audience − critics` on the RT pair, diverging around 0.
- Minimum review counts: at least 20 critic reviews, and the audience count
  is above a threshold we set once we see the distribution.
- `rt_audience_era`: whether the audience score was taken before or after
  RT switched to the verified "Popcornmeter" (May 2024). The T3 trend
  view shows this as a break.

**Genres** (multi-valued: 2.3 genres per film on average)
- *Fractional* counting: each genre of a film gets weight 1/n, so the shares
  add up to 100 %. Used for composition: stacked areas, map shares,
  country genre mix.
- *Membership* counting: a film counts fully in each of its genres. Used for
  distributions per genre: box plots of ROI or rating per genre.
- TMDB has 19 genres, too many for distinct colours (the lecture says 6–12
  categories at most). We group them into about 8 **genre families** for
  colour. Single genres are shown on highlight and in tooltips. The grouping
  is decided in the design sheets.
- "TV Movie" is excluded.

**Country popularity**
- Netflix: films only. Score = Σ(11 − rank) per film, country and week, a
  rank-weighted count of weeks in the chart. Summed into genre shares per
  country and year.
- BOM by country: genre share of gross per country and year. Each chart has
  at most 200 films, and we warn about markets with few films (India and
  China in some years).
- LUMIERE: genre share of admissions per European market and year. It is
  joined through the LUMIERE ID, so no fuzzy matching is needed.
- X2: the cinema-vs-streaming difference per country is the Jensen–Shannon
  distance between the two genre-share vectors.

**Franchises**
- `belongs_to_collection` from the TMDB API. Installment number = order by
  release date. Only collections with at least 3 released films are kept.
- Per film, its change from the previous installment and from the first
  film, for rating and for real revenue.

### 4.4 What the app loads

Rough targets: under ~15 MB in total, under 5 MB gzipped for the first load.

| File | Rows | Used by |
|---|---|---|
| `films.json` (columnar) | notable films + films with both RT scores (~25k) | scatter, details, franchise |
| `genre_year.json` | year × genre × metric (fractional) | genre timeline |
| `country_genre.json` | source × country × year × genre share | map, country panel |
| `franchises.json` | one row per released part of a collection, with its installment number | franchise view |
| `countries.topo.json` | world geometry | map |
| `meta.json` | snapshot dates, coverage stats, match rates, notes on transformations | "About the data" panel |

## 5. Visualization (starting point for the design sheets)

This is a **draft for brainstorming**, not the final design. The FDS sheets
decide the final one.

One-page dashboard. At the top, a global filter bar: year range, genre
families, notable or working subset, nominal or real USD. Below it four
linked views and a detail panel.

| View | Tasks | Idea | Interaction |
|---|---|---|---|
| **V1 World map** | T1, X2 | Choropleth with three modes: *share of the selected genre* (sequential), *top genre* (categorical families), *cinema vs streaming difference* (sequential). A source switch: Netflix / box office / LUMIERE. Countries without data are hatched, not left blank. | Clicking a country filters the other views to that country's charts and opens a genre-mix bar chart for the country |
| **V2 Genre timeline** | T4 | Normalised stacked area or small-multiple lines per genre family. Metric switch: releases / IMDb votes / real box office / Netflix chart weight. | Brushing on x sets the global year range. Hovering a genre highlights it everywhere. |
| **V3 Film scatter** | T2, T3, T5, X1 | Canvas scatter with ~25k points and preset axes: *budget vs rating*, *revenue vs critics*, *critics vs audience* (diagonal reference line, colour = gap on a diverging scale, the biggest outliers labelled). Log scale for money. | Brush to select, zoom, hover for the detail panel. The selection is highlighted in V2 and V4. |
| **V4 Franchise view** | T6 | Lines per franchise: x = installment number, y = rating or revenue relative to the first film. A median band shows the "typical sequel". | Search or pick a franchise. Franchises that go up are flagged. |
| Detail panel | all | Film card: all scores, money with source badges, genres, countries, franchise | Opened from any view |

Encoding rules from the lectures:
- Position comes first. Colour is for categories (≤ 8 genre families) or
  for one sequential or diverging quantity.
- Diverging palettes are never red–green; we use PuOr or RdBu. Everything is
  checked with a colour-blindness simulator, and categories are also encoded
  a second way (label, shape or position).
- No rainbow scales and no 3D.
- Every axis says what it shows: "budget (2025 USD, log)", "ROI (log)".

## 6. Repository, tooling and CI

See `AGENTS.md` for the layout and commands.

- **Pipeline**: Python 3.12 with `uv`, `polars` (and `duckdb` where SQL is
  easier), `httpx` with a cache and rate limit, `rapidfuzz`; checked with
  `ruff` and `pytest`.
- **App**: React + TypeScript + Vite + D3 (D3 for scales, shapes, geo,
  brushing and zoom; React renders SVG; canvas for the scatter). `zustand`
  holds the state shared by the linked views. Checked with ESLint, `tsc`
  and Vitest.
- **CI (GitHub Actions)**, on every push and PR:
  1. `pipeline`: `ruff check`, `ruff format --check`, `pytest` on small
     fixture data (no network), then `validate` on the committed app data
     (schema, unique keys, value ranges, genre shares add up to 1, files
     under the size limit).
  2. `app`: `npm ci`, lint, type check, `vitest`, `vite build`.
  3. `deploy` (only on `main`): publish `app/dist` to GitHub Pages (free
     tier). The build uses relative paths (`base: './'`), so the same
     `dist/` folder runs locally (`npm run preview`, `python -m http.server`),
     which is how we mainly use it. For the submission we also attach a
     zip of `dist/` with a one-line start script, in case the Pages link is
     down.
- CI never downloads or scrapes data. The full rebuild runs locally
  (`make data`), and the outputs that are slow to rebuild (scrapes and app
  data) are committed.

## 7. Suggested split of work

Three areas of about equal size; we assign people when we next meet.

- **Data**: acquire, crosswalk, money, ratings, joins, validation.
- **Scrapers and country data**: RT, Metacritic, Letterboxd, BOM, LUMIERE, Netflix
  matching, the country reference table.
- **App and design**: FDS sheets, React shell, views, linking; the report
  and video at the end (shared).

## 8. Open questions

None right now. Open questions are asked in chat and their answers recorded
in `docs/decisions.md`.
