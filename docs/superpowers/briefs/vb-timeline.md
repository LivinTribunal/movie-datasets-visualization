## Implementation brief: VB genre timeline

Goal: panel B is a 100 % stacked area of genre families over release year with a measure
switch and an x brush that sets the global year range.

Context:
- Read `_views-common.md` in this folder, then spec
  `docs/superpowers/specs/2026-11-16-movie-explorer-app-design.md` **§5 "B. Genre
  timeline"** and §6.
- Films: `data.films.year`, `genre_mask` (bit per genre; a film with n set bits counts 1/n
  per genre), `imdb_votes`, `revenue_usd2025` / `revenue_usd`. `data.genreFamily[g]` maps
  a genre bit to its family index. Use `useFilmMaskAllYears(data)`: the chart shows every
  year and the brush marks the window.
- Netflix: `data.countryGenre` rows with source `netflix` (years 2021–2026) and
  `data.countryYear` for `entries`. The store's `countries` are ISO-2 codes; for the
  Netflix measure they select chart countries (none selected = all).

Files (yours only):
- `app/src/views/GenreTimeline/GenreTimeline.tsx`, `timeline.css`
- `app/src/lib/timeline.ts`, `timeline.test.ts`

Design:
1. `lib/timeline.ts`
   - `Timeline = { years: number[]; shares: Float64Array[]; totals: Float64Array; films:
     Float64Array }`: `shares[f][i]` is family `f`'s share in `years[i]` (0 when the
     year's total is 0), `totals[i]` the summed measure, `films[i]` the number of films
     (or Netflix entries) behind the year.
   - `timelineFromFilms(films, mask, measure, money, genreFamily, nFamilies)` for
     `films` (each film counts 1), `votes` and `revenue` (a film without revenue is
     skipped and not counted in `films[i]`). Years 1900–2026, one slot each.
   - `timelineFromNetflix(countryGenre, countryYear, genreFamily, nFamilies, countries)`:
     only the years that have Netflix rows.
   - `familyAt(timeline, yearIndex, y01)`: the family whose band contains the stacked
     position `y01` in 0–1 (bands stack in family order from the bottom), or −1.
   - `THIN = 30`. Memoise the two builders.
2. `GenreTimeline`
   - `tools`: a native `<select aria-label="Measure">` with "releases", "IMDb votes",
     "box office", "Netflix chart score". y label: "share of releases (%)", "share of
     IMDb votes (%)", "share of box office (%)", "share of Netflix chart score (%)".
   - Scales: `scaleLinear` x over the timeline's years, y 0–1. Bands are `d3.area` paths
     from the cumulative shares, filled with the family colours, `defined` only where
     the year's total is above 0. x ticks every 10 years (every year for Netflix), y
     ticks 0, 25, 50, 75, 100 %.
   - The selected family's band is drawn again on top as an ink outline with no fill.
   - Years with `films < THIN` get a light hatch rectangle over the full height (pattern
     id `tl-thin`), and the legend line under the chart says "hatched: under 30 films".
   - Brush: `d3.brushX` in a `<g>` over the plot. On `end` from a user event with a
     selection: `setYearRange` with the rounded years. A user `end` with no selection is
     a click: select the family under the pointer with `familyAt`, then put the brush
     back on the store's range. An effect moves the brush whenever `yearRange` changes
     in the store, without re-emitting. A double-click sets 1900–2026. The brush is
     hidden for the Netflix measure when the store range does not overlap its years.
   - Pointer move over the plot: local state with year, family and position; the
     `Tooltip` says `Horror · 1999 · 6.2% of IMDb votes · 1,204 films that year`.
     Hit testing is computed with `familyAt`, not with DOM events on the paths, because
     the brush overlay sits on top.
   - `note`: "Each film counts 1/n in each of its n genres." plus, for `votes`, "Votes
     show popularity, not rating."
   - Empty state when no film passes the filter: "No films match the filters."

Tests (`timeline.test.ts`):
- a film with two genres of different families gives each half its measure;
- two genres of the same family give that family the whole film;
- shares of a year sum to 1, and a year without films has total 0 and shares 0;
- `revenue` skips films with NaN revenue and switches column with `money`;
- the mask is respected;
- `timelineFromNetflix` filters by country and returns only Netflix years;
- `familyAt` at the bottom, at a band edge and above the top.

Out of scope: every other panel, the store, `index.css`, the year slider in the filter bar.

Verify (from `app/`):
- `npx vitest run src/lib/timeline.test.ts` → pass
- `npm run typecheck` and `npm run lint` → no errors (report errors in files that are not
  yours, do not fix them)
