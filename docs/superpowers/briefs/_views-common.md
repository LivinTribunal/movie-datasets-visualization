## Shared context for every view brief (waves 3 and 4)

Read this once, then your own brief.

What exists (do not change it; if it is wrong, stop and report):
- `app/src/state/store.ts`: `useStore`. Read one field per selector,
  `useStore((s) => s.family)`, and actions the same way. Fields and actions are those of
  spec §3. Exports `YEAR_MIN`, `YEAR_MAX`, the union types (`Source`, `MapMode`,
  `TimelineMeasure`, `FranchiseY`, `Brush`, `Sort`).
- `app/src/state/selectors.ts`: `useFilmMask(data)` → `Uint8Array` (1 = the film passes
  years, subset, countries and, when on, the genre filter); `useFilmMaskAllYears(data)`.
- `app/src/lib/types.ts`: `AppData { films, countryGenre, countryYear, franchises,
  countries, countryByIso2, families, genreFamily, meta }`. Table columns are typed arrays
  named like the pack columns of spec §2. Numbers are `Float64Array` with NaN = missing.
  `families[i]` is `{ name, colour, genres }` and `i` is both the store's `family` and the
  bit in `family_mask`. `genreFamily[g]` is the family index of genre `g`.
  `DictColumn` is `{ codes, values, nullCode }`: the string of row `i` is
  `values[codes[i]]`. `ListColumn` is `{ offsets, codes, values }`: row `i` holds
  `codes[offsets[i] … offsets[i+1]]`.
- `app/src/lib/measures.ts`: `MeasureKey`, `MEASURES`, `MEASURE_KEYS`,
  `measureColumn(films, key, money)`, `axisLabel(key, money)`, `isScore(key)`, `PRESETS`.
- `app/src/lib/format.ts`: `fmtInt`, `fmtMoney`, `fmtScore`, `fmtPct`, `fmtRatio`,
  `fmtValue(key, value)`, `fmtImdb`. All return `no data` for NaN.
- `app/src/lib/memo.ts`: `memoLast(fn)`. Wrap every aggregation in it at module level, so a
  re-render with the same inputs costs nothing.
- `app/src/lib/data.ts`: `loadText()`, `loadTopo()`, `loadPosters()`, `useLazy(loader)`.
- `app/src/lib/hooks.ts`: `useSize<T>()` → `[ref, { width, height }]` (0 until measured;
  render nothing while it is 0).
- `app/src/components/Panel.tsx` (`letter`, `title`, `tools`, `note`, `className`),
  `ChipGroup.tsx` (`label`, `options: { value, label, colour?, title? }[]`, `value`,
  `onChange`), `Tooltip.tsx` (`x`, `y`, `width`, `height`, children; put it inside the
  panel body, which is `position: relative`).
- CSS variables in `app/src/index.css`: `--ink`, `--muted`, `--grid`, `--panel`, `--page`,
  `--accent`. Each view keeps the grid-area class its stub has (`area-a` … `area-g`).

Rules:
- Your view's styles go in a CSS file in your view folder, imported by the component.
  Do not edit `index.css`.
- D3 comes from the installed `d3` package with named imports
  (`import { scaleLinear } from 'd3'`). D3 does the maths; React renders the SVG. Use a D3
  selection only where D3 needs to own DOM (`brush`, `zoom`), inside `useEffect` with a ref.
- Pure logic (aggregation, hit testing, domains) lives in your one `lib/` file with Vitest
  cases. Components stay thin.
- Mouse-move state stays local to your view or goes to `hoverFilm`. Never put per-frame
  state in the store. Split a memoised child off (`React.memo`) wherever hover would
  otherwise re-render hundreds of SVG nodes.
- A chart never shows a number without its unit, and every tooltip says how many entries
  or films the number rests on, when it is an aggregate.
- Missing is "no data", never 0.
- No new dependency unless your brief names it. No `any`, no `eslint-disable`.
- Other implementers are working in the same tree. Never run a git command that changes
  it (`stash`, `checkout`, `restore`, `add`, `commit`). Touch only your Files.
