## Implementation brief: A2 app shell and filter bar

Goal: the app shows the final one-screen layout with seven lettered panels and a working
filter bar. The six chart panels are still stubs, but every control in the bar reads and
writes the store.

Context:
- Read `docs/superpowers/specs/2026-11-16-movie-explorer-app-design.md` **§1, §5 "F. Filter
  bar" and §6**. They fix the layout, the bar's controls and the colours.
- Slice A1 is done. Use it, do not change it:
  - `app/src/state/store.ts`: `useStore` with the fields and actions of spec §3
    (`setYearRange`, `setFamily`, `setGenreOnly`, `setSubset`, `setMoney`, `setSource`,
    `toggleCountry`, `setAbout`, `reset`, …), `YEAR_MIN`, `YEAR_MAX`, `MAX_COUNTRIES`.
    Subscribe with one selector per field: `useStore((s) => s.family)`.
  - `app/src/lib/types.ts`: `AppData` with `families: Family[]` (`name`, `colour`,
    `genres`; the array index is the store's `family`), `countryByIso2`, `meta`.
  - `app/src/lib/data.ts`: `loadData()`.
- `app/src/App.tsx` loads the data and renders stub panels; each file under
  `app/src/views/` exports a stub component taking `{ data: AppData }`.
- `app/src/index.css` holds the old layout (`.app`, `.filter-bar`, `.grid`, `.panel`,
  `.swatch`, `.badge`, `.status`). Replace it.
- No CSS framework, no component library, no new dependency.

Files (yours only):
- `app/index.html`
- `app/src/index.css`
- `app/src/App.tsx`
- `app/src/components/Panel.tsx`, `ChipGroup.tsx`, `Tooltip.tsx` (new)
- `app/src/lib/hooks.ts` (new)
- `app/src/views/FilterBar/FilterBar.tsx`, `YearSlider.tsx` (new), `Search.tsx` (new stub)
- the six stub files `app/src/views/{WorldMap,GenreTimeline,FilmScatter,Franchise,SelectionTable,FilmCard}/*.tsx`
  (only to wrap them in `Panel`)

Design:
1. `index.css`: CSS custom properties on `:root` for the palette of spec §6 (`--ink`,
   `--muted`, `--grid`, `--panel`, `--page`, `--accent`), 13 px `system-ui`,
   `font-variant-numeric: tabular-nums` for `.num`, tables and SVG text.
2. Layout (`.app`): the whole page is one screen. A CSS grid of 12 columns and four rows:
   F spans the top; A and B six columns each; C and D six each; E eight and G four.
   `height: 100vh`, `min-height: 780px`, rows `auto minmax(0, 1fr) minmax(0, 1.15fr)
   minmax(0, 0.85fr)`, gap and padding 8 px. A panel never grows past its cell: panel
   bodies are `min-height: 0; overflow: hidden`. Below 900 px width everything stacks in
   one column with a fixed panel height of 360 px and the page scrolls.
3. `Panel({ letter, title, tools?, note?, className?, children })`: a `<section>` with a
   header (letter badge in ink, title as `<h2>`, `tools` on the right), a body that fills
   the rest (`flex: 1; min-height: 0; position: relative`), and an optional one-line `note`
   in muted text under the body. `aria-label` is the title.
4. `ChipGroup<T extends string | number>({ label, options, value, onChange })`:
   single-choice chips. `options` are `{ value, label, colour?, title? }`. Rendered as
   `<div role="radiogroup" aria-label>` of `<button role="radio" aria-checked>`. The
   selected chip is filled ink with white text. A chip with a `colour` shows a swatch
   square before its label, also when selected.
5. `Tooltip({ x, y, children })`: an absolutely positioned box inside a `position:
   relative` parent, moved with `transform: translate(...)`, `pointer-events: none`, kept
   inside the parent by flipping to the left or above when `x` or `y` is past the middle
   (it takes the parent size as optional props `width`, `height`). Renders nothing when
   `children` is null.
6. `lib/hooks.ts`: `useSize<T extends HTMLElement>(): [RefObject<T | null>, { width:
   number; height: number }]` with a `ResizeObserver`; sizes are rounded and start at 0.
7. `FilterBar`: one row that wraps, in this order:
   - title "Movie Explorer";
   - `YearSlider`: two overlapping `<input type="range">` (min 1900, max 2026) with the
     two years printed, calling `setYearRange` on input; thumbs cannot cross;
   - the eight family chips (`ChipGroup`, colour swatches, value = family index) and a
     second small `ChipGroup` "highlight / filter" for `genreOnly`;
   - subset `notable / all` (titles: "≥ 10,000 IMDb votes", "≥ 1,000 IMDb votes");
   - money `2025 USD / nominal`;
   - map source `Netflix / Cinema / Made here`;
   - `<Search data={data} />`: for now a disabled text input with the placeholder
     "country, film or franchise…" (a later slice replaces `Search.tsx`);
   - one removable chip per selected country (name from `countryByIso2`, a "×" button
     that calls `toggleCountry`);
   - buttons "Reset" (`reset`) and "About the data" (`setAbout(true)`).
   Every group has a short visible label ("years", "genre", "films", "money", "map").
8. `App.tsx`: keeps the loading and error states, now inside the `.app` grid so the page
   does not jump: while loading it shows the bar's title and "Loading data…". Renders
   `FilterBar` and the six panels in the grid areas.
9. Stubs: each of the six views renders `<Panel letter="A" title="World map">` (B "Genre
   timeline", C "Film scatter", D "Franchise lines", E "Selection table", G "Film card")
   with a muted "coming next" line. Keep their props.
10. `index.html`: title "Movie Explorer", a one-sentence meta description, and
    `<link rel="preload" href="data/films.pack" as="fetch" crossorigin="anonymous">`.

Tests: none in this slice. It has no logic outside the store, which A1 tests; the
architect checks the layout in a browser and a later slice adds the Playwright smoke test.
Do not add a DOM test library.

Constraints: TypeScript strict, functional components, no `any`, no inline styles except
dynamic colours and positions, ESLint clean, no `eslint-disable`. Buttons and inputs are
keyboard reachable with a visible focus ring in `--accent`. Colour is never the only cue:
every chip has a text label.

Out of scope: `app/src/lib/*` except `hooks.ts`, `app/src/state/`, real charts, the
search logic, the About dialog, the URL hash, anything under `pipeline/`.

Verify (from `app/`):
- `npm run typecheck` → no errors
- `npm run lint` → no errors
- `npm run build` → builds
