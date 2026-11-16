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
  1913 (D18), so older films have nominal USD but no 2025 value.
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
- **Critic review minimum**: the PLAN's 20 critic reviews is not applied in
  derive. It would drop 39 % of the Metascores (5,628 of 9,154 left), and
  RT gives no review counts to apply it to. `films.json` carries
  `mc_critic_reviews` next to each Metascore, so a view can apply the
  minimum and the detail panel shows the count.
- **Cinema genre shares** come from LUMIERE admissions per market and year
  (the year of the admissions, not of the release). Each film adds
  `admissions × genre_weight` to its genres. The combined `GB_IE` market
  counts as GB, and only for film-years that have no GB row of their own.
  LUMIERE marks UK and Irish admissions as estimates, so each row carries
  `estimated_share`. A market-year with fewer than 20 films is dropped as
  too noisy. The shares cover notable films with a LUMIERE id only, never
  a market's whole box office, and the app has to say so.

### D18. CPI from 1913 (2026-10-11)

- **What**: inflation uses FRED `CPIAUCNS` (CPI-U, not seasonally
  adjusted, from 1913) instead of `CPIAUCSL` (seasonally adjusted, from
  1947). We use yearly means, and BLS computes its official annual CPI-U
  averages from the unadjusted series, so the adjustment changes nothing
  we use.
- **Why**: with `CPIAUCSL`, every film before 1947 had nominal USD and no
  2025 value. That was 506 budgets, among them *Gone with the Wind*,
  *Snow White* and *Bambi*. Films with a budget source but no
  `budget_usd2025` drop from 557 to 54, and revenues from 373 to 15. The
  rest are non-USD amounts from years with no World Bank rate (before
  1960, or Taiwan), and those stay null.

### D19. Rotten Tomatoes pages and Wikipedia infoboxes (2026-10-11)

robots.txt checked on 2026-10-11 with our User-Agent:

- **Rotten Tomatoes** allows `/m/` (only `/m/*/pictures` is disallowed).
  The film page embeds its scores in a `media-scorecard-json` script tag.
  We fetch films from 2023 on that have a film RT id (3,056; 11 more
  point at a TV episode and are skipped), because the
  Clapper dump stops in April 2023 and has a score for only 161 of them.
  Where a page has a score, it replaces Clapper's, value by value: a page
  with a Tomatometer but no audience score keeps Clapper's audience score.
  The audience score is the Popcornmeter RT shows first, which is the
  verified-ticket score when the film has one (`audience_score_type`
  says which). Clapper's older films mostly have the all-audience score,
  so the two are not exactly the same measure.
- **Wikipedia** disallows `/w/` for crawlers, which covers `api.php`, but
  allows article URLs, so we read `/wiki/{title}?action=raw` (raw
  wikitext). We fetch every notable film with an English article
  (12,923), including the ones that already have money. The infobox
  value then serves both as the last fallback and as a second opinion for
  the `*_disagree` flags, which catch wrong TMDB amounts. The parser
  takes the first item of the `budget` and `gross` fields. A range gives
  its upper bound, like the Wikidata pick that keeps the largest amount.
  A currency it cannot name gives null, and `wp_*_text` keeps the cleaned
  field so every value can be checked against its source text.

### D20. Wrong money amounts: a hand-checked skip list, no automatic rule (2026-10-12)

- **What**: `data/overrides/money.csv` lists single source values that are
  wrong (`imdb_id`, `field`, `source`, `note`). `derive money` treats each
  as missing, so the next source in the order fills in, and `*_src` names
  the source actually used. The list has 11 rows. We filled it by
  checking every notable film in the top and bottom 0.5% of ROI where two
  sources differ by 5× or more, and the note on each row gives both
  amounts.
- **Why not a rule**: we tested "drop TMDB when Wikipedia or Wikidata
  differs by 5× or more" on the full data. For notable films without a
  The Numbers value, it would have hit 37 budgets and 137 revenues. Most
  of those revenues are TMDB holding a single-territory gross, and the
  fallback sources have their own unit errors: Wikidata gives *KILL*
  (2024) a 478 M USD budget, and Wikipedia writes *The Beyond*'s lira
  gross with a £. So the rule would trade one set of wrong values for
  another. Most extreme ROIs are real, and two or more sources agree on
  them: *Blair Witch*, *Halloween*, *Rocky*, the Bruce Lee films, and
  *Obsession* (2026) at 0.75 M budget and 522 M gross.
- **What stays**: the `*_disagree` flags still mark every film whose
  sources differ by more than 1.25×. Netflix originals such as *Red
  Notice* keep their tiny theatrical gross: it is right, but their ROI
  means nothing, and the app should say so where ROI is shown.

### D21. Final design: sheet 5 variant A, one dashboard (2026-11-16)

- **What**: the app is one screen with seven panels (filter bar, world map,
  genre timeline, film scatter, franchise lines, selection table, film card)
  on one store. Emma drew it by hand as sheet 5 for HW4; the board is
  `docs/design-sheets/sheet-5-canvas/sheet-5a.png`. The build spec is
  `docs/superpowers/specs/2026-11-16-movie-explorer-app-design.md`.
- **Why**: every view filters every other view and nothing hides behind a
  tab, which is the plainest way to show linked views.
- **Rejected**: variant B, three tabs (more charts, but the linking is split
  across screens); variant C, three views (no franchise view of its own).
- **Watch**: the hand-drawn sheet carries our UČOs, so its photo stays out
  of the public repo.

### D22. Map sources: Netflix, Cinema, Made here (2026-11-16)

- **What**: the sheet's source switch reads "Netflix, box office,
  admissions". The app has `Netflix`, `Cinema` and `Made here`. Cinema is
  LUMIERE admissions for 36 European markets plus the United States from
  The Numbers domestic gross by release year. Made here is the genre mix of
  the working-subset films each country produced, from TMDB.
- **Why**: Box Office Mojo is closed to crawlers (D16), so there is no
  box-office source per country. Admissions and gross are both cinema
  demand, and a tooltip names which one a country has. Production covers
  the whole map and all years with data we already hold.
- **Watch**: the US cinema rows hold only films The Numbers lists (about
  150 to 230 a year from 1996 to 2019, fewer after). Production is what a
  country makes, not what it watches, and the legend says so.

### D23. App data as gzip column packs, all working-subset films (2026-11-16)

- **What**: tables go to the app as `.pack` files (format `MXP1` in the
  spec, §2.1): typed columns behind a JSON header, gzipped by the exporter
  and inflated in the browser. `films.pack` holds all 56,431 working-subset
  films, sorted by votes so the notable subset is a prefix. `genre_year.json`
  is gone: the timeline is computed in the browser.
- **Why**: the "all" subset and the country filter on the timeline need
  every film, and 56k rows of columnar JSON would be about 13 MB to parse.
  Typed arrays need no parsing and make each filter pass a tight loop.
  Compressing the file ourselves keeps the size the same on any static
  host; GitHub Pages compresses text types only.
- **Rejected**: Arrow or Parquet in the browser (a wasm or 200 KB reader
  for five small tables); pre-aggregated JSON per country (cannot serve a
  union of six countries without counting co-productions twice).

### D24. One selected genre that highlights, with an optional filter (2026-11-16)

- **What**: exactly one genre family is selected at any time. It colours the
  map, outlines its band in the timeline, colours its films in the scatter
  and tints its franchises. It filters films only when the user switches
  the chip toggle from "highlight" to "filter".
- **Why**: T5 asks whether a relation differs by genre, and that is read
  best against the grey cloud of all films. A filter alone would hide the
  comparison.

### D25. Posters are loaded from TMDB at run time (2026-11-16)

- **What**: the film card shows `image.tmdb.org/t/p/w185/<poster_path>`. The
  path comes from the TMDB snapshot. A missing or failed image shows a
  placeholder.
- **Why**: the sheet has a poster on the card, and 56k images cannot live
  in the repo. This is the only network request outside the app's own files
  and the app works without it.

### D26. No web worker; size budgets in CI (2026-11-16)

- **What**: filtering and aggregation run on the main thread over typed
  arrays, cached by their arguments. CI fails when the JavaScript passes
  200 KB gzipped or a data file passes its limit (spec §7).
- **Why**: one pass over 56k rows takes well under a millisecond, so a
  worker would only add message passing. The costs that matter are download
  size and needless re-renders, and a budget keeps both from creeping.

### D27. The franchise box-office axis is fixed at 0.01× to 100× (2026-11-16)

- **What**: in panel D the box-office ratio to the first film is drawn on a
  log axis from 0.01× to 100×. Lines that leave it are cut at the edge, and
  the note under the chart says how many values are outside.
- **Why**: the real ratios run from 0.0001× to 1,638× (21 of 996 sequel
  values are outside the fixed range). A data-driven axis spent most of its
  height on those few and squeezed the rest into a narrow band around 1×.

### D28. The map's share scale tops out at the largest well-covered country (2026-11-16)

- **What**: in "share of genre" mode the colour scale ends at the largest
  share among countries with at least 30 entries. A country under 30 entries
  (dotted outline) with a larger share takes the darkest colour, and the
  legend then reads "N % or more".
- **Why**: in the production source one country with a single film has a
  share of 100 %, which made every other country pale. The dotted outline
  already tells the reader that such a country rests on thin data.

### D29. Three workspaces instead of one page (2026-11-16)

- **What**: the app shows one of three workspaces, picked with tabs in the top
  bar: *Taste by country* (map, genre timeline, film table), *Money & ratings*
  (scatter, film table, film card) and *Franchises* (franchise lines, scatter,
  film card). Each has three linked views and fills the window without page
  scroll. Filters and selections live in the one store and carry across tabs;
  chips in the filter row show the selected countries, franchise, pinned film
  and scatter brush in every workspace. The tab is part of the URL hash.
- **Why**: seven panels on one page needed scrolling on a laptop, so the views
  that answer one question were never on screen together and each chart was
  small. Grouping by question (T1/T4/X2, T2/T3/T5/X1, T6) keeps linked views
  side by side and large. The map source control moved into the map panel
  because it changes nothing else.

### D30. Chrome in black and white, colour only for data (2026-11-16)

- **What**: the interface uses black, white and greys. Hue appears only where
  it encodes a genre family or a quantity. Selection, hover and brush are
  ink. Titles and tabs are set in condensed Archivo (self-hosted), the top bar
  is a black band with a stripe in the selected genre's colour, and panels are
  flat with a border instead of shadowed cards. Panel titles say what the
  chart shows and notes are full sentences.
- **Why**: the first restyle looked like every generated dashboard (rounded
  shadowed cards, pills, a blue accent), and the blue competed with two of the
  eight genre colours. With no chrome colour, any colour the reader sees is
  data, which is the lecture's rule for colour taken to its end.

### D31. Plain controls and system type; D30's black band and poster type dropped (2026-11-16)

- **What**: white page, system font, no panel boxes (neighbouring views are
  split by a thin rule), native-looking selects and checkboxes, the genre
  legend doubles as the genre picker. Chart titles are literal ("Audience
  (Rotten Tomatoes) vs critics (Tomatometer)"). D30's rule that colour is
  reserved for data stays.
- **Why**: both earlier restyles added a visual identity and both read as
  machine-made to the team. A plain tool keeps attention on the charts, and
  each control looks like what it does.

### D32. Back to the #30 look; D30 and D31 reverted (2026-11-16)

- **What**: the app's files under `app/` are restored to the state after
  PR #30 (visual polish and three workspaces): rounded panels, the blue accent,
  segmented controls and that version's copy. D30's black band and poster type
  and D31's plain controls are both gone.
- **Why**: the team compared the three looks side by side and liked the #30
  one best. Both later restyles were meant to look less generic, and to the
  team both looked more generic. The controls work the same in all three, so
  nothing functional is lost.

### D33. Extra film data: story source, studio, release numbers, Oscars, external ids (2026-11-16)

- **What**: the unused TMDB and The Numbers columns and two more Wikidata
  queries go into the app (spec `2026-11-16-extra-data-design.md`). Story
  source and studio become filters, opening weekend, widest release, legs and
  Oscar nominations become measures, and the rest shows on the film card.
  Per-film text (overview, cast, links) for notable films ships in shards of
  1,000 rows that the card fetches on demand. The data size budget rises from
  8 to 12 MB.
- **Why**: all three sources were already local or already queried, so they
  add coverage with no new licence or scraper. Story source and studio answer
  a new question for T2/T5 (do adaptations or majors earn or score more), and
  the release numbers explain box office better than budget alone. The text
  is too large for the first load, so it is split and fetched lazily; the
  first load stays the same size.
- **Rules kept**: a missing story source is null, never "original"; Oscar
  counts are null without a Wikidata item; home-video sales are labelled as
  estimates; opening weekend is US only and says so.
- **Oscar counting** (found on the real run): counts are Wikidata
  statements, not distinct award categories, so The Godfather's three Best
  Supporting Actor nominations count three times (3 wins of 11, as the
  Academy counts). Per category, nominations = max(nomination statements,
  win statements), because Wikidata sometimes lists a win without the
  nomination (The Return of the King has 11 wins but 10 nomination
  statements). Checked on Titanic 11/14, Shawshank 0/7, The Godfather 3/11,
  Godfather II 6/11, Ben-Hur 11/12, All About Eve 6/14, La La Land 6/14 and
  The Return of the King 11/11. The awards query also needs the WDQS hint
  `hint:optimizer "None"`: without it a 200-id batch times out (502, then
  429).

### D34. Scraper contact comes from `MOVIES_CONTACT` (2026-11-16)

- **What**: the User-Agent contact is read from the `MOVIES_CONTACT`
  environment variable (put it in `.env`). Without it the UA names the
  repository URL.
- **Why**: a personal e-mail address hard-coded in a public repo is sent with
  every request whoever runs the code. The repository URL still lets a site
  owner reach us, which is what the scraping rules ask for.
