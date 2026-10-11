# Decision log

One entry per decision: what we decided, why, and what we rejected. Add new
entries at the bottom. When a decision changes, add a new entry that names
the one it replaces; do not edit the old entry.

---

### D1. App stack: React + TypeScript + Vite + D3, static site (2026-10-09)

- **Why**: the project needs 3+ linked views with brushing and selection
  between them. With D3 we control every view; React and a shared store
  handle the linking. A static build needs no server: we run it mainly
  locally and also publish it on free GitHub Pages, which gives us the
  deployed link for the submission.
- **Rejected**: Plotly Dash (needs a hosted server, and custom linking
  between views is awkward); Observable Framework (cross-view state is
  harder); Svelte (the team chose React).

### D2. Pipeline in Python, frozen snapshots (2026-10-09)

- **Why**: the main table has 1.25M rows. `polars` handles it in seconds.
  Scraping and fuzzy matching are easiest in Python. We freeze the data as
  of 2026-10-01 (Netflix up to 2026-09-27) so numbers do not change while we
  write the report.
- **Rejected**: daily refresh of the Kaggle data (numbers would change under
  us, with no benefit for the course).

### D3. Which data goes into git (2026-10-09)

- Committed: scrape results (`data/scraped/`), reference tables and hand
  fixes (`data/reference/`, `data/overrides/`), app data
  (`app/public/data/`).
- Not committed: raw downloads (`data/raw/`), the HTTP cache (`data/cache/`),
  intermediate files (`data/interim/`), course PDFs, and IS pages (they
  contain personal data).
- **Why**: scrapes take hours and are rate-limited, so a teammate should not
  have to repeat them. Raw Kaggle files are too large, and anyone can
  download them again. CI deploys from the committed app data without
  downloading anything.

### D4. Key and unit conventions (2026-10-09)

- Film key `imdb_id`; country key ISO-2; money in constant 2025 USD (nominal
  values kept as well); every rating rescaled to 0–100; a missing value is
  null, never 0.
- **Why**: one join key across all sources, one scale for comparing
  critics and audiences, and no silent zeros in the averages.

### D5. Money is enriched, never imputed (2026-10-09)

- Missing budgets and grosses are filled only with real values from other
  sources, and each value records its source. No mean or nearest-neighbour
  imputation.
- **Why**: an imputed box-office number would be a made-up fact about a
  real film, and the money coverage gap is itself something the views
  should show.

### D6. Two ways to count genres (2026-10-09)

- Fractional weight 1/n for shares and composition; full membership for
  distributions per genre.
- **Why**: shares must add up to 100 %, while a box plot of "Horror ROI"
  should contain every horror film.

### D7. Hosting: local first, public GitHub repo with Pages (2026-10-09)

- The repo is **public on Štefan's GitHub account**; Matúš and Emma join as
  collaborators. We run the app mainly locally and publish it on free
  GitHub Pages for the submission link.
- **Why**: free Pages needs a public repo. A static build runs the same way
  in both places.
- **Watch**: a public repo means the committed scrape results and app data
  are public too. Commit only derived scores and aggregates, never raw
  pages or review texts.
- **Rejected**: private repo with the Student Developer Pack (more setup,
  nothing to hide); a GitHub organisation (not needed for three people).

### D8. Design sheets on paper (2026-10-09)

- The Five Design Sheets are drawn on paper and scanned into
  `docs/design-sheets/`.
- **Why**: the FDS method is meant for fast hand sketching; tools slow
  brainstorming down.

### D9. Letterboxd included (2026-10-09)

- `letterboxd_avg` (0.5–5, rescaled ×20 to 0–100) is a third audience score
  next to the RT audience score and IMDb. It is scraped from
  `letterboxd.com/tmdb/{tmdb_id}` for the notable subset, under the usual
  scraping rules.
- **Why**: Letterboxd users are a different audience (cinephiles) from
  IMDb and RT users, which adds a contrast for T3.

### D10. Chart picks for sheet 1 (2026-10-10)

Options and their trade-offs are in `docs/design-sheets/sheet-1-options.md`.

| task | main view | second view | dropped |
|---|---|---|---|
| T1 | choropleth map | 100 % stacked bars (advanced view) | heatmap |
| T2 | scatter plot | hexbin (zoomed-out mode) | correlogram |
| T3 | scatter with y = x diagonal | ridgeline of the gap per genre | dumbbell, violin |
| T4 | 100 % stacked area (holds the time brush) | small-multiple lines (advanced view) | – |
| T5 | bubble chart | scatter small multiples per genre (advanced view) | heatmap |
| T6 | highlighted spaghetti lines | connected scatter (one franchise) | heatmap |

- **Why**: the team keeps one familiar chart as the default view per task and
  puts the denser or more precise chart behind an advanced view.
- **Watch**: a 100 % stacked area shows shares, not size. If users read it as
  "how big each genre is", T4 swaps it for the streamgraph.

### D11. Eight genre families (2026-10-11)

`data/reference/genre_families.csv` groups TMDB's 18 film genres ("TV Movie"
is excluded) into 8 families, one Okabe–Ito colour each:

| family | genres |
|---|---|
| Action & Adventure | Action, Adventure, War, Western |
| Sci-Fi & Fantasy | Science Fiction, Fantasy |
| Crime & Thriller | Crime, Thriller, Mystery |
| Horror | Horror |
| Comedy | Comedy |
| Drama & Romance | Drama, Romance, History, Music |
| Family & Animation | Animation, Family |
| Documentary | Documentary |

- **Why**: the lecture allows 6–12 colour categories and Okabe–Ito has 8.
  Horror keeps its own family because T3 expects it to differ. Music joins
  Drama & Romance because 69 % of Music films in the working subset are also
  Drama, Romance or Comedy, and only 22 % are documentaries. Documentary is
  grey, so it reads as "not fiction".
- **Watch**: the team can regroup on the design sheets; only this file
  changes.

### D12. Wikidata money keeps rank and date precision (2026-10-11)

The money query also returns the statement rank (`preferred` / `normal`) and
the precision of the point-in-time qualifier. A film with several budgets
uses the preferred one. The cache file name now includes a hash of the query,
so a changed query can never reuse old replies.
- **Watch**: the rank rarely decides. Of the 1,431 film-and-property pairs
  with several amounts, only 33 mark one as preferred. The others differ by
  place (worldwide or one country) or currency, so the money step picks by
  place and currency first and uses the rank as a tie-break.

### D13. Historical countries map to their main successor (2026-10-11)

TMDB lists production countries that no longer exist. They map to their main
successor: Soviet Union → RU, Yugoslavia and Serbia and Montenegro → RS,
Czechoslovakia → CZ, East and West Germany → DE. The alias table marks these
rows, and the app says so where a country's films are listed.

### D14. Title matching for The Numbers and Netflix (2026-10-11)

The Numbers and Netflix Top 10 have no IMDb id, so `movies join` matches them
to TMDB by title. Titles are normalised first: accents, case, punctuation, a
trailing `(...)` and a leading "The" are dropped, and the numerals II to X and
two to ten become digits. An exact match on the normalised title or original
title comes first, then rapidfuzz `token_sort_ratio` ≥ 90. Each match keeps
`method` (exact, fuzzy, override) and `score`, so the app can mark fuzzy ones.

- **Year windows**: a Numbers row matches films released within ±1 year of
  its release date. A Netflix title matches any film released no later than
  the year of its first chart week, but a fuzzy match must be at most 2 years
  older than that year.
  Without that limit about half of the fuzzy Netflix matches were older films
  one letter away ("Devara" → "Devar", 1966).
- **Numbers in titles**: a fuzzy match is rejected when both titles carry
  numbers and they differ ("The Expendables 4" is not "The Expendables 2").
  A number on one side only is allowed, because The Numbers writes
  "Jaws 4: The Revenge" where TMDB writes "Jaws: The Revenge".
- **Ties**: among exact matches the film with the most votes wins; among
  fuzzy ones the highest score, then the most votes. A film matched by several
  Numbers rows ranks them override, exact, fuzzy, then the metrics file
  before the budgets file, and takes each value from the first row that has it.
- **Century**: the metrics file stores films from before 1927 a century late
  (Ben-Hur 1925 as 2025). A metrics year that equals a budgets year of the
  same title plus 100 takes the budgets year.
- **Netflix candidates** are TMDB films with status Released, an IMDb id and
  ≥ 100 IMDb votes. Netflix originals in small markets often have fewer votes
  than the 1,000 of the working subset.
- **Overrides**: `data/overrides/numbers.csv` (key `metrics:<id>` or
  `budgets:<rank>`) and `data/overrides/netflix.csv` (key = Netflix title)
  hold hand fixes, each checked against TMDB. An empty `imdb_id` removes a
  wrong match. Rows whose note starts with `agent-checked:` (266 Numbers,
  83 Netflix, added 2026-10-11) were chosen by language-model agents from the
  4 closest TMDB titles in the year window, then checked by a script (the id
  must be one of the candidates, the year rule must hold) and read by hand.
  Agents skipped titles they were unsure of, and 5 of their 354 picks were
  dropped on review.
- **Watch**: a spot check still finds a few wrong films among the 49 fuzzy
  Netflix matches. All 49 together carry 0.2 % of the chart score, and the app
  marks them as fuzzy.

### D15. Derive rules for money, ratings and genres (2026-10-11)

`movies derive` writes `money.parquet`, `ratings.parquet`,
`film_genres.parquet` and `country_genre_netflix.parquet` to `data/interim/`.
Choices the PLAN left open:

- **Money order**: budget from The Numbers, then TMDB, then Wikidata; revenue
  from The Numbers worldwide gross, then TMDB, then Wikidata box office. The
  first source with a value wins, per field, and `budget_src` /
  `revenue_src` name it. Box Office Mojo is not used (its robots.txt blocks
  all crawlers) and Wikipedia infoboxes are not parsed yet.
- **Floors**: a budget under $1,000 or a revenue under $10,000 counts as
  missing in that source, and the next source is tried. The small revenues
  were re-release grosses (12 Angry Men at $379) or unit errors (TMDB's 7 for
  Memoir of a Snail). For Wikidata the floor applies to the nominal amount
  before a statement is picked, and again after conversion.
- **Wikidata pick**: only worldwide or place-less box office counts (a US
  figure is domestic). Among the rest: USD first, then preferred rank, then
  the latest date, then the largest amount (D12).
- **Currency**: `data/reference/currencies.csv` maps each Wikidata currency
  to the country whose World Bank rate it uses, with the years that rate is
  valid (EUR uses Germany's rate from 1999; DEM, FRF, ITL, ESP, FIM and GRD
  use their country's rate up to the euro). Amounts are divided by that
  rate in the release year. No rate (Taiwan is not in the World Bank data,
  no 2026 rates yet, nothing before 1960) gives a null USD value and the
  nominal amount stays.
- **Inflation**: `*_usd2025 = *_usd × CPI(2025) / CPI(year)`. CPI starts in
  1947, so older films have nominal USD but no 2025 value.
- **Disagreement**: `*_disagree` is true when at least two sources have a
  USD value and the largest is more than 1.25 times the smallest.
- **ROI** = revenue / budget, only when the USD budget is at least $100,000.
  `profit_usd2025` = revenue minus budget in 2025 USD.
- **TMDB rating** is null under 50 TMDB votes, where an average is noise.
  The PLAN's minimum of 20 critic reviews cannot be applied yet: the RT
  dataset has no review counts. Its audience scores are all from before the
  Popcornmeter (April 2023 snapshot), so no `rt_audience_era` column is
  needed for it.
- **Genres**: "TV Movie" is dropped before `genre_weight = 1/n` is computed.
  A TMDB genre missing from `genre_families.csv` stops the run.
- **Netflix genre shares** per country and year: each chart row adds
  `score × genre_weight` to its film's genres. `coverage` is the share of
  chart score whose title matched a film with genres, and `fuzzy_share` the
  part of it matched by title similarity. A country-year with no matched
  title has no rows (the map draws it hatched).
- **Watch**: a few TMDB pairs give implausible ROI (Fist of Fury, $100k
  budget and $100M revenue, ROI 1,000). The floors do not catch them, and
  the app should show the source of every money point.

### D16. Which sites we scrape (2026-10-11)

robots.txt checked on 2026-10-11 with our User-Agent:

- **Box Office Mojo** answers `User-agent: * / Disallow: /`, so `bom_title`
  and `bom_country` are dropped. Cinema grosses per country now come only
  from LUMIERE (European admissions, `/movie` allowed), and revenue gaps stay
  gaps. T1's cinema side is therefore Europe only.
- **Metacritic** allows `/movie/`. The page has the Metascore and its critic
  review count in JSON-LD. The user score is read from the "User score X out
  of 10" text, and only when the page also says "Based on N User Ratings",
  because recommendation cards further down carry the same text.
- **Letterboxd** allows `/imdb/` and `/film/`. `/imdb/{imdb_id}/` redirects
  to the film page; the redirect is followed by hand so both hops keep to one
  request per second. The rating is Letterboxd's weighted average (0.5–5).
- Pages are cached gzipped (about 120 KB for Metacritic and 40 KB for
  Letterboxd), and a 404 leaves an empty `.missing` marker so a re-run skips
  it. Only the parsed numbers go to `data/scraped/`.

### D17. Franchises, the extra scores and cinema genre shares (2026-10-11)

- **Franchises** are TMDB collections. `/3/collection/{id}` lists every
  part, including parts outside our film table. A part counts once it was
  released by the TMDB snapshot (2026-10-01), and a collection needs at
  least three released parts to be a franchise. Installments are numbered
  by release date, then TMDB id. `imdb_100_vs_prev` and `_vs_first` are
  differences in points; `revenue_vs_prev` and `_vs_first` are ratios of
  2025 USD revenue. A part we have no ratings or money for keeps its
  installment number with null values, so the numbering has no gaps.
- **Metacritic and Letterboxd scores** join on `imdb_id`. `metascore_100`
  is the Metascore as is, `mc_user_100` the user score × 10 and
  `letterboxd_100` the average × 20. The Metacritic user score is null
  under 10 user ratings, where a few votes (often review-bombing) decide
  it. Letterboxd shows an average only once a film has enough ratings, so
  it gets no threshold of ours. `gap` stays audience score minus
  Tomatometer.
- **Cinema genre shares** come from LUMIERE admissions per market and year
  (the year of the admissions, not of the release). Each film adds
  `admissions × genre_weight` to its genres. The combined `GB_IE` market
  counts as GB, and only for film-years that have no GB row of their own.
  LUMIERE marks UK and Irish admissions as estimates, so each row carries
  `estimated_share`. A market-year with fewer than 20 films is dropped as
  too noisy. The shares cover notable films with a LUMIERE id only, never
  a market's whole box office, and the app has to say so.
