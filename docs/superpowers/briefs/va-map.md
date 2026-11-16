## Implementation brief: VA world map

Goal: panel A is a zoomable choropleth of genre taste per country with three modes, a
legend and a tooltip, and clicking a country filters the other panels.

Context:
- Read `_views-common.md` in this folder, then spec
  `docs/superpowers/specs/2026-11-16-movie-explorer-app-design.md` **§5 "A. World map"**
  and §6. Build what they say.
- `loadTopo()` returns world-atlas 50m TopoJSON. `topo.objects.countries` has 241
  geometries; `id` is the ISO numeric code as a 3-digit string (`"203"`), 5 geometries
  have no id, and `properties.name` is the English name. `Country.iso_numeric` in
  `data.countries` has the same 3-digit strings. Drop Antarctica (`"010"`).
- `data.countryGenre`: rows of (`source`, `country`, `year`, `genre`, `score`).
  `data.countryYear`: rows of (`source`, `country`, `year`, `entries`, `coverage`,
  `fuzzy_share`, `estimated_share`, `measure`). Sources are `netflix` (2021–2026),
  `cinema` (Europe 1996–2025 with measure `admissions`, US 1980–2024 with `gross_usd`)
  and `production` (1900–2026).
- New dependencies allowed in this slice only: `topojson-client` and
  `@types/topojson-client` (dev). Install them with npm from `app/`.

Files (yours only):
- `app/src/views/WorldMap/WorldMap.tsx`, `MapPaths.tsx`, `MapLegend.tsx`, `worldmap.css`
- `app/src/lib/countryShares.ts`, `countryShares.test.ts`
- `app/package.json`, `app/package-lock.json` (the two packages only)

Design:
1. `lib/countryShares.ts`
   - `countryStats(countryGenre, countryYear, genreFamily, nFamilies, source, yearRange)
     → Map<string, CountryStat>`, memoised. `CountryStat = { iso2, total, byFamily:
     Float64Array, entries, fuzzy, estimated, coverage, measure, years: [number, number] }`.
     It sums `score` per family over the rows of that source whose year is in range;
     `entries` is the sum over those years; `fuzzy`, `estimated` and `coverage` are means
     weighted by entries; `years` is the first and last year that had rows. A country
     with no row in the window is not in the map.
   - `share(stat, family)` = `byFamily[family] / total`. `topFamily(stat)` = index of the
     largest. `worldShares(stats, nFamilies)` = family shares of all countries' scores
     summed.
   - `shareDiff(cinema, netflix, family) → Map<string, number>`: cinema share minus
     Netflix share for countries present in both.
   - `THIN = 30`.
2. `MapPaths` (memoised): takes the features, the path generator output per feature, and
   per-country fill and class; renders one `<path>` per country. It does not depend on
   hover, so it re-renders only when data, mode or size change. Paths use
   `vector-effect: non-scaling-stroke`.
3. `WorldMap`
   - Projection `geoEqualEarth().fitSize([width, height], { type: 'Sphere' })`; path
     strings computed once per size (`useMemo`).
   - Zoom: `d3.zoom` on the `<svg>`, scale extent 1–12, translate extent the panel;
     the handler sets the `transform` attribute of one `<g>` through a ref. Remove D3's
     default double-click zoom; a double-click on a country zooms to its bounds
     (`path.bounds`). Buttons "+" and "−" (top right of the body, `aria-label`s "Zoom in",
     "Zoom out") scale by 1.6 and 1/1.6. A "reset view" button appears when zoomed.
   - Click on a country that has an ISO-2: `toggleCountry`. D3 zoom already swallows the
     click that ends a drag.
   - Fill per mode:
     - `share`: `scaleSequential(interpolateBlues)` on `[0, max share on screen]`.
     - `top`: the top family's `colour`.
     - `diff`: `scaleDiverging(interpolatePuOr)` on `[-m, 0, m]`, `m` the largest
       absolute difference. Uses `cinema` and `netflix` whatever `source` is.
     - No stat for the country: `fill="url(#map-hatch)"` (a `<pattern>` of 6 px diagonal
       lines in `--grid`, defined in this SVG).
     - `entries < THIN`: dotted outline (`stroke-dasharray`).
   - Selected countries are drawn again on top with a 2 px ink outline and no fill.
   - Mode chips (`ChipGroup`, "share of genre", "top genre", "cinema − streaming") go in
     the panel's `tools`.
   - Hover sets local state `{ iso2, x, y }`; the `Tooltip` shows the lines of the spec:
     country name, top genre, the selected family's share, the all-countries share, then
     "based on N entries, <years> · source: <label>", plus "estimated by LUMIERE: P%" when
     `estimated > 0` and "fuzzy title matches: P%" when `fuzzy > 0`. In `diff` mode it
     shows both shares and the difference in percentage points. A country without data
     says "no data in this source and window". Source labels: "Netflix Top 10",
     "cinema admissions (LUMIERE)" or "US box office (The Numbers)" by `measure`,
     "films produced here (TMDB)".
   - `note` of the panel: when the window has no row for the source, say why ("Netflix
     charts start in 2021", "Cinema data covers 1996–2025 (US from 1980)"); otherwise the
     count of countries with data.
4. `MapLegend` (bottom left, over the map): for `share` and `diff` a colour ramp drawn as
   a CSS `linear-gradient` from 7 samples of the scale, with end labels in % or
   percentage points and, for `diff`, the words "more on Netflix" and "more in cinemas";
   for `top` the eight family swatches as buttons that call `setFamily`. Always the hatch
   swatch "no data" and the dotted swatch "under 30 entries".
5. While the geometry loads the body shows "Loading map…".

Tests (`countryShares.test.ts`, small hand-made tables):
- sums scores per family over the year range only, and only for the source;
- a country without rows in the window is absent;
- `entries` is summed, `fuzzy` is the entries-weighted mean;
- `share`, `topFamily`, `worldShares`;
- `shareDiff` keeps only countries in both and has the right sign.

Out of scope: every other panel, the store, `index.css`, the search box.

Verify (from `app/`):
- `npx vitest run src/lib/countryShares.test.ts` → pass
- `npm run typecheck` and `npm run lint` → no errors (lint and typecheck cover the whole
  app; report errors in files that are not yours, do not fix them)
