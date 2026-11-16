# Movie Explorer: app design

Spec for building the app. It turns sheet 5 (variant A, the one Emma drew by
hand on 2026-11-16) into something an implementer can build without asking.
The board is `docs/design-sheets/sheet-5-canvas/sheet-5a.png`. Decisions made
here are D21 to D26 in `docs/decisions.md`.

Read order for an agent: §1 for the picture, the section of the slice you
build, then §9 for the rules every slice shares. Your brief quotes what you
need; you should not have to read this file end to end.

## 1. What we build

One screen, seven panels, one store. Every panel reads the store and writes
to it. Panels never talk to each other.

```
┌ F  filter bar: title · years · 8 genre chips · subset · money · source · search · about ┐
├──────────────────────────────┬──────────────────────────────┤
│ A  World map (SVG)           │ B  Genre timeline (SVG)      │
├──────────────────────────────┼──────────────────────────────┤
│ C  Film scatter (canvas)     │ D  Franchise lines (SVG)     │
├──────────────────────────────┴───────────────┬──────────────┤
│ E  Selection table (virtual rows)            │ G  Film card │
└──────────────────────────────────────────────┴──────────────┘
```

| Panel | Tasks | Reads | Writes |
|---|---|---|---|
| F filter bar | all | everything | years, genre, genreOnly, subset, money, source, countries, film, franchise |
| A world map | T1, X2 | years, genre, source, mapMode, countries | countries, genre (legend swatch), mapMode |
| B genre timeline | T4 | subset, countries, genre, years, timelineMeasure | years (brush), genre (click a band), timelineMeasure |
| C film scatter | T2, T3, T5, X1 | film filter, genre, x, y, size, money, franchise, film | brush, hoverFilm, film, x, y, size |
| D franchise lines | T6 | film filter, genre, franchise, franchiseY | franchise, franchiseY, hoverFilm |
| E selection table | T2, T3, T5 | film filter, brush, sort, columns, money | sort, columns, hoverFilm, film |
| G film card | all | hoverFilm, film, money | franchise (link), countries (link) |

Out of scope: tabs, small multiples, ridgelines, hexbins, scatter zoom, a
dark theme, mobile layouts below 900 px, X3 to X5.

## 2. Data files

The app is static. Its "backend" is the export stage: it writes files that
are cheap to download and need no parsing. `movies export` writes all of them
to `app/public/data/` and `movies validate` checks them in CI.

| File | Rows | Loaded | Limit |
|---|---|---|---|
| `films.pack` | every film of the working subset (56,431) | first | 3.0 MB |
| `films_text.pack` | same rows: title, director | after first paint | 1.2 MB |
| `films_poster.pack` | same rows: poster path | when the film card first shows a film | 2.0 MB |
| `country_genre.pack` | source × country × year × genre | first | 1.0 MB |
| `country_year.pack` | source × country × year | first | 0.2 MB |
| `franchises.pack` | one row per released part of a franchise | first | 0.2 MB |
| `countries.json`, `genre_families.json`, `meta.json` | as today (columnar JSON) | first | small |
| `countries.topo.json` | world-atlas **50m** (small countries exist in it) | with the map | 0.9 MB |

`films.json`, `genre_year.json`, `country_genre.json` and `franchises.json`
are removed. The genre timeline is computed in the browser from `films.pack`,
because it must follow the country filter.

### 2.1 Pack format `MXP1`

A `.pack` file is a gzip stream (written with `mtime=0`, so a re-run gives no
diff). The app fetches it as bytes and inflates it with
`DecompressionStream('gzip')`. If the first two bytes are not `1f 8b`, the
server already inflated it and the bytes are used as they are. This makes the
size independent of the host: `python -m http.server` compresses nothing, and
GitHub Pages compresses only text types.

Inflated layout, little-endian:

| Bytes | Content |
|---|---|
| 0–3 | ASCII `MXP1` |
| 4–7 | u32 `H`, the header length in bytes |
| 8 … 8+H | UTF-8 JSON header, padded with spaces so that `8 + H` is a multiple of 8 |
| 8+H … | column buffers in header order, each zero-padded to start at a multiple of 8 |

Header: `{"rows": n, "meta": {…}, "columns": [{"name", "type", "offset", "length", …}]}`.
`offset` counts from the start of the data section (byte `8 + H`), `length`
is in bytes.

| `type` | Buffer | Extra header keys | Decoded as |
|---|---|---|---|
| `u8` `u16` `i16` `u32` `f32` | `n` values | `scale` (optional), `null` (optional raw sentinel; `f32` uses NaN) | `num()`: `Float64Array`, value × scale, NaN where missing. `raw()`: the typed array itself, for ids and bit masks |
| `dict` | `n` codes, `width` 1 or 2 bytes | `values: string[]`, `null` sentinel | `{codes, values}` |
| `list` | `n + 1` u32 offsets, then u16 codes | `values: string[]` | `{offsets, codes, values}` |
| `str` | `n + 1` u32 offsets, then UTF-8 bytes | – | `(string \| null)[]`; an empty string on the wire is null |

Missing stays missing: a sentinel exists only on the wire, the app sees NaN
or null. Ids are read with `raw()`, never `num()`.

### 2.2 `films.pack`

Rows are sorted by `imdb_votes` descending, then `imdb_id`. The notable
subset is therefore the first `meta.notable` rows, and "is notable" is
`row < meta.notable`. The row index is the film handle inside the app.
`meta`: `{"notable": 13080, "genres": [18 names in genre_families order], "families": [8 names in family_order]}`.

| Column | Type | Notes |
|---|---|---|
| `imdb` | u32 | digits of the IMDb id (`tt0111161` → 111161); shown zero-padded to 7 digits |
| `tmdb_id` | u32, null | |
| `year` | u16 | 1900–2026, never null in the working subset |
| `runtime` | u16, null | minutes |
| `imdb_votes` | u32 | |
| `genre_mask` | u32 | bit `i` = `meta.genres[i]` |
| `family_mask` | u8 | bit `i` = `meta.families[i]` |
| `countries` | list | production countries, ISO-2 |
| `budget_usd`, `budget_usd2025`, `revenue_usd`, `revenue_usd2025` | f32 | NaN = missing; nominal and constant 2025 USD |
| `roi` | f32 | revenue ÷ budget, only when the budget is at least $100k |
| `budget_src`, `revenue_src` | dict u8, null | `numbers`, `tmdb`, `wikidata`, `wikipedia` |
| `flags` | u8 | bit 0 budget converted from another currency, 1 revenue converted, 2 budget sources disagree, 3 revenue sources disagree, 4 money matched by a fuzzy title |
| `imdb_100`, `tmdb_100`, `tomatometer_100`, `audience_100`, `metascore_100`, `mc_user_100`, `letterboxd_100` | u16, scale 0.1, null 65535 | 0–100 |
| `gap` | i16, scale 0.1, null −32768 | audience − Tomatometer |
| `mc_critic_reviews` | u16, null | |
| `collection_id` | u32, null | set when the film is a part of an exported franchise |
| `installment` | u8, null | |

`films_text.pack` has the same rows: `title` (str), `director` (str, null).
`films_poster.pack` has the same rows and one column, `poster` (str, null;
the TMDB `poster_path`). Poster paths do not compress, so they stay out of
the file the table and the search wait for.

### 2.3 Country tables

`country_genre.pack`: `source` (dict: `netflix`, `cinema`, `production`),
`country` (dict, ISO-2), `year` (u16), `genre` (u8, index into
`meta.genres`), `score` (f32, ≥ 0). Sorted by source, country, year, genre.
There is no `share` column: the app sums `score` over the chosen years and
divides, so a share is always the share of the visible window.

`country_year.pack`: `source`, `country`, `year`, `entries` (u32, distinct
films behind the scores), `coverage`, `fuzzy_share`, `estimated_share` (f32,
0–1), `measure` (dict: `chart_score`, `admissions`, `gross_usd`, `films`).
Every source-country-year of one file is in the other.

| Source | Countries | Years | Score | Rows come from |
|---|---|---|---|---|
| `netflix` | 94 | 2021–2026 | Σ (11 − rank) × genre weight | `country_genre_netflix.parquet` (exists) |
| `cinema` | 36 European markets | 1996–2025 | admissions × genre weight | `country_genre_lumiere.parquet` (exists) |
| `cinema` | US | 1980–2024 | The Numbers domestic gross × genre weight, by release year | new, `country_genre_us.parquet` |
| `production` | every production country | 1900–2026 | genre weight of each working-subset film made there | new, `country_genre_production.parquet` |

A country-year needs at least 20 films in `cinema` (rule D17) and at least 1
in `production`. A co-production counts in each of its countries.

### 2.4 `franchises.pack`

`collection_id` (u32), `installment` (u8), `n_released` (u8), `tmdb_id`
(u32), `film_row` (u32, null: the row in `films.pack` when the part is
there), `year` (u16), `family_mask` (u8, of the first part that has genres,
else 0), `imdb_100`, `tomatometer_100`, `audience_100` (u16 scale 0.1, null),
`imdb_100_vs_first` (i16 scale 0.1, null), `revenue_usd2025` and
`revenue_vs_first` (f32), `title` (str). Sorted by collection, installment.
`meta.collections` is `[[collection_id, name], …]`.

### 2.5 `meta.json`

As today, plus `attribution: string[]` (the lines of `DATASETS.md` §6) and
`sources: {netflix, cinema, production}` with one sentence each on what the
source covers and what it leaves out. The About dialog prints all of it.

## 3. State

One zustand store, `app/src/state/store.ts`. Components subscribe with a
selector per field, never to the whole store.

```ts
type Subset = 'notable' | 'all'
type Money = 'usd2025' | 'nominal'
type Source = 'netflix' | 'cinema' | 'production'
type MapMode = 'share' | 'top' | 'diff'
type TimelineMeasure = 'films' | 'votes' | 'revenue' | 'netflix'
type FranchiseY = 'rating' | 'revenue'

interface State {
  yearRange: [number, number]   // [1990, 2026]
  family: number                // index into meta.families; always one; 0 = Action & Adventure
  genreOnly: boolean            // false: the genre highlights. true: it also filters films
  subset: Subset                // 'notable'
  money: Money                  // 'usd2025'
  source: Source                // 'netflix'
  mapMode: MapMode              // 'share'
  countries: string[]           // ISO-2, at most 6
  timelineMeasure: TimelineMeasure   // 'votes'
  x: MeasureKey                 // 'tomatometer'
  y: MeasureKey                 // 'audience'
  size: MeasureKey | null       // 'votes'
  brush: [number, number, number, number] | null  // x0, x1, y0, y1 in data units
  franchise: number | null      // collection_id
  franchiseY: FranchiseY        // 'rating'
  film: number | null           // pinned film row
  hoverFilm: number | null
  sort: { key: MeasureKey | 'title'; desc: boolean }   // votes, desc
  columns: MeasureKey[]         // year, tomatometer, audience, gap, budget, revenue
  about: boolean
}
```

Rules the setters enforce:

- `setX` / `setY` refuse the measure the other axis has, and clear `brush`.
- `toggleCountry` adds or removes; a seventh country is refused.
- `setYearRange` clamps to 1900–2026 and keeps `from ≤ to`.
- `reset` restores the defaults.

**The film filter** is one function, `filmMask(films, {yearRange, subset,
countries, genreOnly, family})` → `Uint8Array`. A film passes when its year
is in range, it is in the subset, it has at least one production country in
`countries` (when any are chosen), and, when `genreOnly`, it is in the
selected family. C, D and E use it. B uses it without the year range.

Derived data is computed by pure functions in `app/src/lib/` and cached with
a last-arguments memo shared by all panels, so two panels that need the same
mask compute it once.

**URL hash.** Everything except `brush`, `hoverFilm` and `about` is written
to the hash (`replaceState`, debounced 300 ms) and read on load. A film is
written as its IMDb id, not its row.

## 4. Measures

`app/src/lib/measures.ts` is the single list the scatter axes, the size
control and the table columns use.

| Key | Label | Unit | Scale | Column |
|---|---|---|---|---|
| `tomatometer` | critics (Tomatometer) | 0–100 | linear, fixed 0–100 | `tomatometer_100` |
| `metascore` | critics (Metascore) | 0–100 | linear | `metascore_100` |
| `audience` | audience (Rotten Tomatoes) | 0–100 | linear | `audience_100` |
| `imdb` | IMDb rating | 0–100 | linear | `imdb_100` |
| `mc_user` | Metacritic users | 0–100 | linear | `mc_user_100` |
| `letterboxd` | Letterboxd | 0–100 | linear | `letterboxd_100` |
| `tmdb` | TMDB rating | 0–100 | linear | `tmdb_100` |
| `gap` | gap, audience − critics | points | linear, fixed −100…100 | `gap` |
| `budget` | budget | 2025 USD or nominal USD | log | `budget_usd2025` / `budget_usd` |
| `revenue` | box office | 2025 USD or nominal USD | log | `revenue_usd2025` / `revenue_usd` |
| `roi` | ROI, box office ÷ budget | × | log | `roi` |
| `votes` | IMDb votes | count | log | `imdb_votes` |
| `year` | release year | year | linear | `year` |
| `runtime` | runtime | minutes | linear | `runtime` |

An axis label is `label (unit, log)` or `label (unit)`, for example
`budget (2025 USD, log)`. Log and data-driven domains come from the films
that pass the filter, made nice. Scatter presets: *critics vs audience*
(tomatometer, audience), *revenue vs critics* (revenue, tomatometer),
*budget vs rating* (budget, imdb), *ROI* (budget, roi).

## 5. Panels

Shared behaviour: each panel is a `Panel` with its letter, a title and a
toolbar slot. Charts size themselves from the panel with a `ResizeObserver`.
Every tooltip names what the number is, its unit and how many entries it
rests on.

### F. Filter bar

- Title "Movie Explorer". Year range as a two-thumb slider with the numbers
  shown; it mirrors the brush in B.
- Eight genre chips in family order, each with its colour swatch. One is
  always selected. The chips are also the colour legend for the whole page.
  Next to them a toggle: "highlight" or "filter" (`genreOnly`).
- Subset: `notable` (≥ 10,000 IMDb votes) or `all` (≥ 1,000).
- Money: `2025 USD` or `nominal`.
- Source for the map: `Netflix`, `Cinema`, `Made here`.
- Search "country, film or franchise…": at most 8 results, grouped. A country
  toggles in `countries`, a film is pinned (`film`), a franchise is selected.
  Film titles arrive with `films_text.pack`; until then the film group says
  "loading titles…". Films are scanned in row order, so the most voted match
  comes first.
- Chips for the selected countries with a remove button each, a Reset
  button and an "About the data" button.

### A. World map

- Equal Earth projection, 50m geometry, joined to `countries.json` through
  `iso_numeric`. Paths are computed once per panel size. Zoom and pan change
  one group transform (`d3.zoom`, scale 1 to 12): scroll, drag, the + and −
  buttons. A double-click on a country zooms to its bounds.
- A click that is not a drag toggles the country in `countries` (at most 6).
  Selected countries get a thick ink outline.
- Scores are summed over the years of `yearRange` that the source has.
- Modes, switched in the panel header:
  - **share of genre** (default): share of the selected family in that
    country, sequential Blues, domain 0 to the largest share on screen.
  - **top genre**: the family with the largest share, in its family colour.
    Clicking a legend swatch selects that family.
  - **cinema − streaming**: share of the selected family in `cinema` minus
    its share in `netflix`, in percentage points, diverging PuOr around 0.
    Only countries that have both sources get a colour. This mode ignores
    the `source` control and says so in the legend.
- No data for a country in this source and window: hatched, never a scale
  colour. Fewer than 30 entries in the window: dotted outline.
- If the window misses the source entirely (Netflix before 2021), every
  country is hatched and a line says "Netflix charts start in 2021".
- Tooltip, as on the sheet: `Czechia · top genre: Drama & Romance · selected
  (Action & Adventure): 21 % · all countries: 19 % · based on 412 entries,
  2021–2026 · source: Netflix Top 10`. It adds "estimated by LUMIERE" for
  estimated admissions and the fuzzy-matched share when it is above 0.
- Legend: the colour ramp with its unit, the hatch swatch "no data", the
  dotted swatch "under 30 entries".

### B. Genre timeline

- 100 % stacked area, one band per family, x = release year 1900–2026. The
  selected family's band has an ink outline. Clicking a band selects it.
- Measure dropdown, and the y label always says what is stacked:
  - `films`: share of releases
  - `votes` (default): share of IMDb votes. This is popularity, not rating.
  - `revenue`: share of box office
  - `netflix`: share of Netflix chart score, 2021–2026 only; the x axis
    shrinks to those years and the country filter means the chart country.
- Each film adds its measure × 1/n to each of its n genres (D6).
- Films pass the film filter without the year range. `genreOnly` is ignored
  here, or the chart would be one band.
- An x brush sets `yearRange`. The brush follows the store, so the slider in
  F moves it. Double-click clears it to 1900–2026.
- A year with fewer than 30 films behind it is covered by a light "thin
  data" hatch. A year with none has no area.
- Tooltip: `Horror · 1999 · 6.2 % of IMDb votes · 1,204 films that year`.

### C. Film scatter

- Canvas for the points, SVG on top for axes, the brush, labels and rings.
- X ▾, Y ▾ and size ▾ list every measure. The measure used by the other
  axis is greyed out. Size may be "none". Preset chips set X and Y.
- Points are films that pass the film filter and have both values. Grey
  points for all, the selected family in its colour drawn on top. Notable
  films are drawn last. A line under the chart says how many are missing:
  `9,940 films · 3,140 hidden: no budget`.
- Points are stamped from pre-drawn sprites (one per colour and radius
  bucket) so alpha adds up and density shows. The base canvas is redrawn
  only when the filter, the axes, the size, the family, the money mode or
  the panel size change. Hover and selection draw on the SVG.
- When both axes are 0–100 scores, a dashed `y = x` line is drawn.
- Brush (`d3.brush`): on release, the rectangle goes to the store in data
  units. E then lists the films inside. A click on empty space clears it.
- Hover: nearest point within 10 px (`d3.quadtree`, rebuilt after each base
  redraw) sets `hoverFilm` and shows a tooltip with title, year and both
  values. A click pins the film.
- A selected franchise is drawn on the same axes: its parts joined in
  installment order by an ink line, each part labelled `#1`, `#2`, …

### D. Franchise lines

- x = installment 1 to 10. Longer franchises are cut at 10 and a note says
  so. Y ▾: `rating` = IMDb points relative to the first film (linear,
  symmetric), `revenue` = box office relative to the first film as a ratio
  (log, 2025 USD, "1×" at the baseline).
- One thin line per franchise that has at least one part passing the film
  filter. Franchises of the selected family are tinted in its colour, the
  others are grey. A dashed ink line shows the median per installment where
  at least 10 franchises have a value. The baseline (±0 or 1×) is drawn.
- The selected franchise is a thick ink line with dots and its name at the
  end. Hovering picks the nearest vertex and shows franchise, film, `#k`
  and the value; clicking selects, clicking again clears.
- Under the chart: `62 % of sequels are rated below #1 · Action & Adventure:
  58 % (212 franchises)`.

### E. Selection table

- Rows: the films inside the brush, or every film that passes the filter
  when there is no brush. The header says which and how many.
- Columns: film (title, with family swatches), then the measures in
  `columns`. Scores and money are in-cell bars on one shared scale per
  column; `gap` is a cell shaded on PuOr with the number in it. A
  "columns ▾" menu adds and removes measures. Clicking a header sorts.
- Rows are virtual: fixed height, only the visible window is in the DOM.
- Hovering a row sets `hoverFilm`, clicking pins the film. The pinned row
  is marked.

### G. Film card

- Shows the hovered film, else the pinned one, else a hint.
- Poster from `https://image.tmdb.org/t/p/w185` + `poster`;
  `films_poster.pack` is fetched the first time the card shows a film. A
  placeholder when the path is missing, not loaded yet or the image fails. Nothing else in the app needs the
  network.
- Title, year, runtime, director, genres, production countries (click to
  toggle the country filter), franchise and installment (click to select).
- Every score as a labelled bar, critics and audience grouped; the
  Metascore shows its review count.
- Budget, box office and ROI in the chosen money mode, each with its unit
  and a source badge. Badges for "converted from another currency",
  "sources disagree" and "fuzzy title match". Missing values say "no data",
  never 0.

### About the data

A dialog: snapshot dates, counts, every note in `meta.notes`, what each map
source covers, and the attribution lines. It is how the app meets the
lecture rule on transformed data, together with the labels and badges above.

## 6. Colour and type

- Families: the eight Okabe–Ito colours in `genre_families.json`. A family
  is never told by colour alone: chips, legends and tooltips carry its name.
- Sequential: ColorBrewer Blues. Diverging: PuOr. No red–green, no rainbow.
- Ink `#1f2328`, muted `#656d76`, grid `#d8dce1`, panel `#fff`, page
  `#f6f7f9`, accent for hover and focus `#0969da`. A selected franchise or
  film uses ink, not a hue, so it cannot be mistaken for a genre.
- Hatch for "no data": a 6 px diagonal pattern in grid colour.
- `system-ui` font, 13 px base, tabular numbers in tables and axes.
- CSS custom properties in `index.css`; no CSS framework.

## 7. Performance

Budgets, checked in CI:

| What | Limit |
|---|---|
| JavaScript, gzipped | 200 KB |
| CSS, gzipped | 20 KB |
| Each data file | the limits in §2 (validator) |
| All of `app/public/data` | 8 MB |

How the design meets them:

- No worker. A filter pass over 56,431 rows of typed arrays is well under a
  millisecond, so a worker would add message passing and nothing else. The
  slow parts are the download and inflate, which the browser does off the
  main thread already.
- `index.html` preloads `films.pack`. The first-load files are fetched in
  parallel; the map geometry and the titles follow after first paint.
- Components subscribe to single store fields. `hoverFilm` is read only by
  the card and the two hover rings, so moving the mouse re-renders nothing
  else.
- Canvas and zoom changes go through refs and `requestAnimationFrame`,
  never through React state per frame.
- Named imports from `d3`, so the bundle carries only what is used.

## 8. Testing and CI

- **pytest**: the pack writer round-trips every column type; each export
  table on small frames; the validator rejects each broken invariant.
- **Vitest**: pack decoding against hand-built buffers, the film filter,
  every aggregation, measures and formatters, the hash round-trip.
- **Playwright** (one smoke file, Chromium): the app loads with no console
  error; all seven panels render; picking a genre chip changes the map
  legend; a brush in the scatter changes the table's row count; clicking a
  table row fills the card.
- **CI jobs**: `pipeline` (ruff, pytest, validate), `app` (lint, typecheck,
  vitest, build, budgets), `e2e` (build, preview, Playwright).
- **Deploy**: `deploy.yml` builds `app/dist` on every push to `main` and
  publishes it with GitHub Pages (`build_type: workflow`).

## 9. Rules for every slice

- The store is the only link between panels.
- Missing is NaN or null in the app and is shown as "no data".
- Any transformed value is labelled where it is shown (unit and year of the
  USD, source badge, fuzzy and estimated marks, hidden counts).
- Money axes are log and say so. Every axis has its unit.
- Relative URLs only (`data/…`), `base: './'`, no host features.
- Mirror the nearest existing file. No new dependency without a line in the
  brief that names it.

## 10. Slices

Each slice has a brief in `docs/superpowers/briefs/`. Slices in one wave own
disjoint files and run in parallel; a wave is one pull request.

| Wave | Slice | Owns | Needs |
|---|---|---|---|
| 1 | P1 country sources | `clean/tmdb.py`, `derive/genres.py`, their tests | – |
| 1 | P2 pack export | `export/`, `validate/`, their tests | P1's output schemas (in the brief) |
| 2 | A1 data layer | `app/src/lib/`, `app/src/state/` | §2, §3, §4 |
| 2 | A2 shell | `App.tsx`, `index.css`, `components/`, `views/FilterBar` | A1 |
| 3 | VA map · VB timeline · VC scatter · VD franchise | one `views/` folder each plus one `lib/` file each | A1, A2 |
| 4 | VE table · VG card and About · VF search and hash | one folder each | A1, A2 |
| 5 | Q e2e, budgets, deploy | `.github/workflows/`, `app/e2e/`, `app/scripts/` | all |

After wave 5 the app is deployed. Then, only if time is left: cinema data
outside Europe and the US from Wikipedia's lists of weekly number-one films
per country. It is a go only if a probe of ten countries finds the lists
complete from 2015 on and parseable without per-page special cases.
