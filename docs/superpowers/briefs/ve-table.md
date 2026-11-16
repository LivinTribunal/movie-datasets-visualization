## Implementation brief: VE selection table

Goal: panel E lists the films inside the scatter brush (or every film that passes the
filters), with sortable measure columns drawn as in-cell bars, virtual rows, and hover
and pin linked to the other panels.

Context:
- Read `_views-common.md` in this folder, then spec
  `docs/superpowers/specs/2026-11-16-movie-explorer-app-design.md` **§5 "E. Selection
  table"** and §6.
- `app/src/lib/scatter.ts` has `scatterRows(xCol, yCol, mask, xLog, yLog)` (rows with
  both axis values) and `brushedRows(xCol, yCol, rows, brush)`. Panel C calls them the
  same way (`views/FilmScatter/FilmScatter.tsx`); call them with the same arguments so
  the memo is shared.
- Store: `brush`, `x`, `y`, `money`, `sort` (`{ key: MeasureKey | 'title', desc }`),
  `columns` (`MeasureKey[]`), `film`, and `setSort`, `setColumns`, `setFilm`,
  `setHoverFilm`. `useFilmMask(data)`.
- Titles: `useLazy(loadText)` → `{ title, director }`, null until loaded.
- Up to 56,431 rows. Never render them all.

Files (yours only):
- `app/src/views/SelectionTable/SelectionTable.tsx`, `Rows.tsx`, `table.css`
- `app/src/lib/table.ts`, `table.test.ts`

Design:
1. `lib/table.ts` (pure)
   - `maskRows(mask) → Uint32Array` (rows where the mask is 1), memoised.
   - `sortRows(rows, col, desc) → Uint32Array`, memoised: a sorted copy; NaN always
     last, ties keep row order.
   - `sortRowsByTitle(rows, titles, desc)`, memoised: `Intl.Collator` compare, null
     last.
   - `columnMax(col, rows)`: the largest finite value, 0 when none.
   - `visibleWindow(scrollTop, viewHeight, rowHeight, count, overscan = 8) → [start,
     end)`.
   - `cellKind(key) → 'bar' | 'gap' | 'plain'`: scores, `budget`, `revenue` are `bar`;
     `gap` is `gap`; the rest `plain`.
2. `SelectionTable`
   - Rows: with a brush, `brushedRows` of the scatter rows; else `maskRows(mask)`. Then
     sorted by `sort` (title sort waits for the titles; until then it keeps row order).
   - Panel `note`: `412 films inside the scatter brush` or `9,940 films pass the
     filters`, then `· bars share one scale per column`.
   - `tools`: a `<details class="columns-menu">` with the summary "columns" and one
     checkbox per `MEASURE_KEYS` entry (`MEASURES[k].label`), wired to `setColumns`
     in `MEASURE_KEYS` order. At least one column stays checked.
   - Layout: a scroll container (`overflow: auto`, fills the body) holding a sticky
     header row and a spacer of `count × ROW_H` px (`ROW_H = 24`) in which `Rows` is
     absolutely positioned at `start × ROW_H`. Header and rows are CSS grids with the
     same `grid-template-columns: minmax(200px, 2fr) repeat(n, minmax(92px, 1fr))`,
     set through a style prop.
   - Header cells are buttons: label, the unit in muted small text (`2025 USD` or
     `nominal USD` for money by the money mode, else `MEASURES[k].unit`), and "▲" or
     "▼" on the sorted column. A click sets that key, descending first; a second click
     flips. `aria-sort` on the sorted one. The first column is "film" (key `title`).
   - `scrollTop` lives in local state, updated in a `requestAnimationFrame`-throttled
     scroll handler. When the rows change, scroll back to the top.
   - Roles: `role="table"` on the container, `rowgroup`, `row`, `columnheader`, `cell`.
3. `Rows` (memoised; props: rows, start, end, columns, column arrays, maxima, titles,
   data, pinned film)
   - One grid row per visible film, `key` = film row.
   - Film cell: up to three family swatches (`families[i].colour`, `title` = name) for
     the bits of `family_mask`, then the title (`fmtImdb(imdb)` until titles load),
     ellipsis on overflow, full title in `title`.
   - `bar` cell: the number through `fmtValue`, right aligned, over a bar whose width is
     `value / scaleMax`: 100 for scores, `columnMax` of the listed rows for money. The
     bar is `--grid` grey; the cell of a missing value shows muted "no data" and no bar.
   - `gap` cell: background `interpolatePuOr` at `0.5 + gap / 120` clamped to 0–1
     (orange = audience higher), text with an explicit sign (`+12`, `−8`); white text
     when the absolute gap is above 35.
   - `plain` cell: `fmtValue`, right aligned.
   - Pointer enter on a row → `setHoverFilm(row)`; pointer leave of the whole list →
     `setHoverFilm(null)`. Click → `setFilm(row)`, the same row again clears it. The
     pinned row has `aria-selected` and an ink bar on its left edge. Rows are focusable
     (`tabIndex={0}`) and Enter pins.
   - Empty state: "No films match. Clear the brush or widen the filters."

Tests (`table.test.ts`):
- `maskRows`; `sortRows` ascending and descending with NaN last in both and stable ties;
- `sortRowsByTitle` with a null and with accented titles;
- `columnMax` with NaN and with no finite value;
- `visibleWindow` at the top, in the middle, at the end and with fewer rows than fit;
- `cellKind`.

Out of scope: every other panel, the store, `index.css`, `lib/scatter.ts`.

Verify (from `app/`):
- `npx vitest run src/lib/table.test.ts` → pass
- `npm run typecheck` and `npm run lint` → no errors (report errors in files that are not
  yours, do not fix them)
