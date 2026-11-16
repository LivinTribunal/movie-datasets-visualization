## Implementation brief: VC film scatter

Goal: panel C is a canvas scatter of films with selectable axes and size, a brush that
feeds the table, hover and pin, and the selected franchise drawn as a path.

Context:
- Read `_views-common.md` in this folder, then spec
  `docs/superpowers/specs/2026-11-16-movie-explorer-app-design.md` **§4, §5 "C. Film
  scatter"** and §7.
- Up to 56,431 films; rows are sorted by IMDb votes, most voted first. `useFilmMask(data)`
  gives the films that pass the filter. Store fields you use: `x`, `y`, `size`, `money`,
  `family`, `brush`, `franchise`, `film`, `hoverFilm` and their setters.
- `data.franchises` has one row per franchise part: `collection_id`, `installment`,
  `film_row` (NaN when the part is not in `films`).
- `loadText()` gives `title[row]`; use it through `useLazy`.

Files (yours only):
- `app/src/views/FilmScatter/FilmScatter.tsx`, `Plot.tsx`, `HoverLayer.tsx`, `scatter.css`
- `app/src/lib/scatter.ts`, `scatter.test.ts`

Design:
1. `lib/scatter.ts` (pure)
   - `usable(v, log)`: finite, and above 0 when `log`.
   - `scatterRows(xCol, yCol, mask, xLog, yLog) → { rows: Uint32Array; missingX: number;
     missingY: number }`, memoised: rows that pass the mask and have both values, in row
     order; `missingX` = passing films without a usable x; `missingY` = passing films with
     x but without y.
   - `domainOf(key, col, rows) → [number, number]`: `[0, 100]` for a score (`isScore`),
     the fixed `domain` when the measure has one, else the extent over `rows` (for a
     single value, pad it). The component makes it nice with the scale.
   - `brushedRows(xCol, yCol, rows, brush) → Uint32Array`: rows inside `[x0, x1, y0, y1]`
     inclusive. Panel E imports this later; keep the signature.
   - `radiusBucket(v, max, buckets)`: NaN → 0, else `sqrt(v / max)` mapped to
     `0 … buckets − 1`.
2. `FilmScatter` (controls and derivation)
   - `tools`: three native selects with `aria-label`s "X axis", "Y axis", "Size". Options
     are `MEASURE_KEYS` with `MEASURES[k].label`; the measure of the other axis is
     `disabled`. Size also has "none".
   - Under the header, inside the body: a row of four preset buttons (`PRESETS`, class
     `chip`, `aria-pressed` when x and y match) that call `setX` and `setY`. Setting a
     preset when the new x equals the current y must still work: set the axis that does
     not collide first.
   - `note`: `9,940 films · 3,140 hidden: no budget · 210 hidden: no IMDb rating` (parts
     with 0 are left out), built from `missingX`, `missingY` and the measure labels.
   - Empty state: "No films have both values under these filters."
3. `Plot` (memoised; props: data, rows, columns, measure keys, size column, family,
   franchise, brush, width, height)
   - Margins: left 48, right 12, top 8, bottom 36. Scales `scaleLinear` or `scaleLog` by
     `MEASURES[key].scale`, domain from `domainOf`, `.nice()`.
   - Base canvas: sized `width × devicePixelRatio`, scaled once. Points are stamped with
     `drawImage` from sprites drawn once per (colour, radius bucket): 6 buckets, radius
     1.5 to 7 px; size "none" uses 2.5 px. Draw order: grey (`#6e7781`,
     `globalAlpha` 0.35) for films outside the selected family, then the family colour
     (alpha 0.75); inside each pass iterate `rows` backwards so the most voted land on
     top. Redraw in an effect that depends on rows, columns, scales, size, family and
     size of the panel only.
   - After a redraw build `quadtree` over the pixel positions and keep it in a ref.
   - SVG over the canvas: grid lines and ticks (`scale.ticks(6)`, labels through
     `fmtValue`), axis titles from `axisLabel(key, money)`, the dashed `y = x` line when
     both keys are scores, the franchise path, the brush `<g>`.
   - Brush: `d3.brush` on a `<g>` over the plot area. `end` from a user event with a
     selection → `setBrush` in data units (inverted through the scales, ordered so
     `x0 ≤ x1`, `y0 ≤ y1`). `end` with no selection is a click: a point within 10 px →
     `setFilm(row)` (the same row again clears it), else `setBrush(null)`. An effect
     moves the brush rectangle when the store's `brush` or the scales change, without
     re-emitting (ignore events that have no `sourceEvent`).
   - Pointer move on the SVG (the brush overlay lets it bubble): throttle with
     `requestAnimationFrame`, find the nearest point within 10 px, call `setHoverFilm`
     only when the row changes; pointer leave → `setHoverFilm(null)`.
   - Franchise: the parts of the store's `franchise` with a `film_row` and both values,
     in installment order: an ink polyline, a small ink dot and the label `#k` per part.
     It is drawn whether or not the films pass the filter.
4. `HoverLayer` exports two small components that read `hoverFilm` and `film` from the
   store, so `Plot` never re-renders on hover:
   - `HoverRing` (SVG): an accent ring on the hovered film and an ink ring on the pinned
     one, when the film has both values.
   - `HoverTip` (HTML, uses `Tooltip`): title (or "loading title…"), year, then the x
     and y values with their labels and units through `fmtValue`.

Tests (`scatter.test.ts`):
- `scatterRows`: mask respected; NaN dropped; 0 and negatives dropped on a log axis and
  kept on a linear one; `missingX` and `missingY` counted as defined;
- `domainOf`: score, fixed domain, data extent, a single value;
- `brushedRows`: inclusive edges, empty result;
- `radiusBucket`: NaN, 0, max.

Out of scope: every other panel, the store, `index.css`, the table.

Verify (from `app/`):
- `npx vitest run src/lib/scatter.test.ts` → pass
- `npm run typecheck` and `npm run lint` → no errors (report errors in files that are not
  yours, do not fix them)
