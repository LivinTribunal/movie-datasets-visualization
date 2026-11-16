## Implementation brief: VD franchise lines

Goal: panel D shows every franchise as a line over its installments, relative to the first
film, with a median line, a selected franchise and a sentence that answers "do sequels get
worse".

Context:
- Read `_views-common.md` in this folder, then spec
  `docs/superpowers/specs/2026-11-16-movie-explorer-app-design.md` **§5 "D. Franchise
  lines"** and §6.
- `data.franchises` (2,584 rows, 605 franchises): one row per released part.
  `collection_id`, `installment` (1…n), `film_row` (row in `films`, NaN when the part is
  not there), `year`, `family_mask` (of that part), `imdb_100_vs_first` (IMDb points on
  the 0–100 scale minus the first film's; 0 at installment 1; NaN = no rating),
  `revenue_vs_first` (box office in 2025 USD divided by the first film's; NaN = no
  data), `title`, and `collections: Map<collection_id, name>`.
- Store: `franchise` (collection_id or null), `franchiseY` (`rating` | `revenue`),
  `family`, `setFranchise`, `setFranchiseY`, `setHoverFilm`. `useFilmMask(data)`.

Files (yours only):
- `app/src/views/Franchise/Franchise.tsx`, `Lines.tsx`, `franchise.css`
- `app/src/lib/franchise.ts`, `franchise.test.ts`

Design:
1. `lib/franchise.ts` (pure)
   - `MAX_K = 10`.
   - `Line = { id: number; familyMask: number; points: { k: number; v: number; row:
     number }[] }` where `row` is the row in `franchises` and `familyMask` is the mask of
     the franchise's first part.
   - `franchiseLines(fr, y, mask) → { lines: Line[]; cut: boolean }`, memoised. A
     franchise is kept when at least one part has a `film_row` that passes `mask`.
     Points: installments 1…`MAX_K` with a usable value (finite; above 0 for
     `revenue`), in installment order. `cut` is true when a kept franchise has a part
     after `MAX_K`. A franchise with fewer than 2 points is dropped.
   - `medianByInstallment(lines, minCount = 10) → { k: number; v: number }[]`: the median
     per installment over lines that have that point, only where at least `minCount` do.
   - `sequelStat(lines, baseline, familyBit) → { all: { below, total }, family: { below,
     total, franchises } }`: over points with `k ≥ 2`, how many are below the baseline
     (0 for rating, 1 for revenue); `family` counts only lines whose `familyMask` has
     the bit.
   - `nearestVertex(lines, px, py, xOf, yOf, maxDist) → { line: number; point: number } |
     null`: linear scan; 2,584 vertices need no index.
2. `Lines` (memoised): one `<path>` per franchise (`d3.line`), grey ones first
   (`#8c959f`, opacity 0.35), then the franchises of the selected family in its colour
   (opacity 0.6). It does not depend on hover or on the selected franchise.
3. `Franchise`
   - `tools`: `ChipGroup` "Y axis" with "rating" and "box office".
   - Margins: left 48, right 90 (room for the name label), top 8, bottom 34.
   - x: `scaleLinear` 1…`MAX_K`, ticks at the integers, label "installment".
   - y for `rating`: linear, symmetric `[-m, m]`, `m` the largest absolute value, nice;
     label "IMDb rating vs the first film (points on 0–100)". For `revenue`: `scaleLog`
     symmetric around 1, `[1/m, m]`, ticks through `fmtRatio`; label "box office vs the
     first film (×, log, 2025 USD)".
   - The baseline (0 or 1×) is a solid muted line; the median is a dashed 2 px ink line
     with the label "median" at its end.
   - The selected franchise: a 2.5 px ink line with dots and its name from
     `collections` at the last point (truncate to 14 characters with "…").
   - Pointer move: `nearestVertex` within 12 px → local state; show the hovered line in
     accent and a `Tooltip`: `Toy Story · #3 Toy Story 3 (2010) · −4 points vs #1` or
     `… · 1.3× the box office of #1`. Also `setHoverFilm(film_row)` when the part has
     one, and `setHoverFilm(null)` on leave.
   - Click on a vertex: `setFranchise(id)`, or `null` when it is already selected.
   - `note`: `62% of sequels are rated below #1 · Action & Adventure: 58% (212
     franchises)`; for revenue "earned less than #1". Add "· installments after #10 are
     not shown" when `cut`. A total of 0 gives "no data" for that part.
   - Empty state: "No franchise matches the filters."

Tests (`franchise.test.ts`, a hand-made table of three franchises):
- a franchise with no part passing the mask is dropped; one passing part keeps it whole;
- parts after installment 10 are cut and `cut` is set;
- NaN points are skipped, and for `revenue` a 0 is skipped;
- `medianByInstallment` respects `minCount` and takes the middle of an even count;
- `sequelStat` ignores installment 1 and counts the family separately;
- `nearestVertex` finds the closest vertex and returns null beyond `maxDist`.

Out of scope: every other panel, the store, `index.css`.

Verify (from `app/`):
- `npx vitest run src/lib/franchise.test.ts` → pass
- `npm run typecheck` and `npm run lint` → no errors (report errors in files that are not
  yours, do not fix them)
