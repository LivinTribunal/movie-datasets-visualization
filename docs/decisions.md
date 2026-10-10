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

### D13. Historical countries map to their main successor (2026-10-11)

TMDB lists production countries that no longer exist. They map to their main
successor: Soviet Union → RU, Yugoslavia and Serbia and Montenegro → RS,
Czechoslovakia → CZ, East and West Germany → DE. The alias table marks these
rows, and the app says so where a country's films are listed.
