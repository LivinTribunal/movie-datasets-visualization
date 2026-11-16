# S5 / S6: interaction fixes after the click-through audit

Found on 2026-11-16 by driving every control with a real mouse (Playwright,
1440×820) against the `visual-polish` build. Each item below failed or was
unreachable. Two slices with disjoint files.

Rules for both slices: mirror the nearest code in the same file, minimal diff,
no new dependency, no refactor. Do not run git commands that change the tree.
Do not run the full test suites, the build or the e2e test; `npx tsc --noEmit`
and `npx eslint <your files>` only. Design tokens are in `app/src/index.css`.

## S5 charts (WorldMap, GenreTimeline, FilmScatter)

Files: `views/WorldMap/WorldMap.tsx`, `views/WorldMap/worldmap.css`,
`views/GenreTimeline/GenreTimeline.tsx`, `views/FilmScatter/Plot.tsx`,
`views/FilmScatter/FilmScatter.tsx`, `views/FilmScatter/scatter.css`.

1. **Map zoom never attaches.** The zoom effect depends on `[width, height]`
   but the `<svg>` only mounts once `ready` (topojson loaded). When the size is
   measured first, the effect ran with `svgRef.current === null` and never
   re-ran: the + / − buttons, wheel, drag and double-click zoom all do nothing.
   Add `ready` to the effect's dependencies (move the `ready` const above it).
2. **Map legend swallows clicks** on the countries under it (South America).
   `.map-legend { pointer-events: none }`, `.legend-family { pointer-events: auto }`.
3. **Timeline: a click inside the brushed year range does not pick the genre**
   (d3 treats it as a zero-length drag of the selection, so `event.selection`
   is still set). In the brush, record the pointer position on `start`
   (`event.sourceEvent` client coordinates) and on `end` treat a move under
   3 px as a click, before looking at `event.selection`: pick the family with
   `familyAt` exactly as the existing no-selection branch does, then `place()`
   so the brush shows the store's year range again, and return. Drags keep the
   existing behaviour. A click must never change the year range.
4. **Scatter: clicks and the brush disagree.** Today a click on a point inside
   the brush does nothing, and a click outside it lets d3 erase the brush
   rectangle while the store (and the table) still hold the brush. Same
   click detection as item 3 (`start` position, < 3 px on `end`). On a click:
   - a point within `PICK_RADIUS` → toggle the pinned film (existing code),
     brush unchanged;
   - no point, click inside the current brush rectangle → nothing;
   - no point, outside → `setBrush(null)`.
   After every click, redraw the brush rectangle from the store's brush
   (`b.move` with the same pixel conversion the `[brush, xScale, yScale]`
   effect uses; keep the store brush reachable through the `latest` ref).
   Real drags keep the existing behaviour.
5. **No visible way to clear the brush.** In `FilmScatter.tsx`, when `brush`
   is set, show `<button type="button" className="btn">clear brush</button>`
   at the right end of `.scatter-presets` (flex, `margin-left: auto`);
   it calls `setBrush(null)`.
6. **Axis selects cut their labels** ("critics (Tomatomete"). Drop the
   `max-width: 150px` on `.panel-tools select` in `scatter.css`; let the three
   selects shrink only when the panel is too narrow (`min-width: 0`,
   `flex: 0 1 auto`, `text-overflow: ellipsis`) and let `.area-c .panel-head`
   wrap (`flex-wrap: wrap`, `row-gap: 6px`).

## S6 chrome (table, card, about, filter bar, layout)

Files: `views/SelectionTable/SelectionTable.tsx`, `views/SelectionTable/table.css`,
`views/About/About.tsx`, `views/About/about.css`, `views/FilmCard/FilmCard.tsx`,
`views/FilmCard/filmcard.css`, `views/FilterBar/FilterBar.tsx`, `index.css`.

1. **Columns menu is clipped** by the panel (5 of 14 checkboxes unreachable)
   and never closes. `.columns-list { max-height: 240px; overflow-y: auto }`.
   Close the `<details>` on a `mousedown` outside it and on Escape: mirror the
   outside-click effect in `views/FilterBar/Search.tsx` with a ref on the
   `<details>` and `ref.current.open = false`. Style `summary` as a quiet
   button (padding 4px 8px, radius `--radius-s`, hover `--fill`, no default
   marker, a small chevron is fine).
2. **Table header.** "Year year" repeats itself: render the `<small>` unit
   only when it is non-empty and differs from the label, case-insensitively.
   Header buttons must not spill into the next column: `min-width: 0;
   overflow: hidden` and ellipsis on the label span; the unit `<small>` hides
   first (`flex-shrink` high) when the column is narrow. Header text of numeric
   columns stays right-aligned over the numbers. "film" → "Film".
3. **Bottom row too short** on a laptop (6 table rows at 820 px). In
   `index.css` change the last grid row from `minmax(290px, 0.9fr)` to
   `minmax(380px, 0.9fr)`.
4. **About dialog.** Clicking the backdrop closes it (`onClick` on the
   `<dialog>`: if `e.target === e.currentTarget` then `setAbout(false)`).
   The Close button gets `className="btn"`; add a second, icon-only close
   button (`×`, `aria-label="Close"`, class `about-x`) pinned top-right
   (`position: sticky; top: 0; float: right` or absolute in a relative
   wrapper; 28 px round, `--fill` background). Keep the bottom button's
   visible text "Close".
5. **Film card.**
   - The franchise button toggles: `setFranchise(franchise === collection ? null : collection)`
     with `aria-pressed`; read `franchise` from the store.
   - `.fc-btn[aria-pressed='true']` gets the accent look
     (`background: var(--accent-soft); color: var(--accent)`), check it exists.
   - Long country names ("United Kingdom of Great Britain and Northern
     Ireland"): `.fc-chips .fc-btn { max-width: 100%; overflow: hidden;
     text-overflow: ellipsis; white-space: nowrap }` and a `title` with the
     full name.
   - The IMDb link is browser-default blue underline: colour `var(--accent)`,
     no underline until hover.
   - `.filmcard` must scroll inside the panel body when it does not fit
     (`position: absolute; inset: 0; overflow-y: auto`), check it does.
6. **Selected franchise is invisible in the filter bar.** In `FilterBar.tsx`,
   after the country chips, when `franchise !== null` render one more
   `.country-chip` with the collection name
   (`data.franchises.collections.get(franchise) ?? 'franchise'`) and a
   `×` button (`aria-label="Clear franchise"`) calling `setFranchise(null)`.
   Country chips: same ellipsis rule as the card (`max-width: 220px`, `title`).

## Not in scope

The hash format, the store shape, data files, pipeline, any new feature.
