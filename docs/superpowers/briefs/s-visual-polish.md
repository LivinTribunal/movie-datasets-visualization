## Implementation brief: S visual polish (four slices, one design system)

Goal: the app works but looks like a wireframe. Make it look finished: calm surfaces,
clear type hierarchy, proper controls, quieter charts. No behaviour changes, no new
features, no new dependency. Every slice reads "Design system" and then its own section.

### Design system (tokens; slice S1 defines them in `app/src/index.css`, the others only use them)

```
--ink: #1d1d1f;  --ink-2: #424245;  --muted: #6e6e73;  --faint: #a1a1a6;
--page: #f5f5f7; --panel: #ffffff;  --fill: #f0f0f2;   --fill-2: #e8e8ed;
--grid: #ececf0; --line: rgba(0,0,0,.08);
--accent: #0071e3; --accent-soft: rgba(0,113,227,.12);
--radius-l: 14px; --radius-m: 9px; --radius-s: 6px;
--shadow-panel: 0 0 0 1px rgba(0,0,0,.04), 0 1px 2px rgba(0,0,0,.04), 0 8px 24px rgba(0,0,0,.05);
--shadow-pop: 0 0 0 1px rgba(0,0,0,.06), 0 4px 12px rgba(0,0,0,.10), 0 16px 40px rgba(0,0,0,.12);
--shadow-thumb: 0 0 0 .5px rgba(0,0,0,.08), 0 1px 3px rgba(0,0,0,.18);
--ease: cubic-bezier(.2,.8,.2,1);
```

- Type: `system-ui`, base 13px/1.4. App title 20px/700, `letter-spacing: -0.02em`.
  Panel title 14px/600, `-0.01em`. Labels above controls and table headers: 11px/500,
  `--muted`, `letter-spacing: .02em` (not uppercase). Chart tick text 11px `--muted`,
  axis titles 11px `--muted`. Numbers are tabular.
- Surfaces: page `--page`; a panel is `--panel`, `--radius-l`, `--shadow-panel`, no
  border. Floating things (tooltip, dropdown, map legend, dialog) use `--shadow-pop`.
- Chart ink: grid lines `--grid` 1px; axis baselines `--line`; "all films" grey is
  `#b4b8c0`; a selected franchise or pinned film is `--ink`; hover is `--accent`.
- Motion: only `transform`, `opacity`, `background-color`, `box-shadow`, 120–200 ms with
  `--ease`. Pressable things scale to .97 on `:active`. Everything inside
  `@media (prefers-reduced-motion: reduce)` drops transforms and keeps a short fade.
  Translucent surfaces fall back to solid under `prefers-reduced-transparency: reduce`.
- Focus: `outline: 2px solid var(--accent); outline-offset: 2px` on `:focus-visible`.
- Colour is still never the only cue; keep every text label, unit and note that exists.
- Keep every class name, role, aria attribute and text that `app/e2e/smoke.spec.ts`
  uses (`.area-a…g`, `.panel-note`, `.overlay`, `role="radio"`, `role="row"`, the card
  hint text, "share of <family>", "inside the scatter brush").

### S1 shell, controls, filter bar
Files: `app/src/index.css`, `app/src/components/{Panel,ChipGroup,Tooltip}.tsx`,
`app/src/views/FilterBar/{FilterBar,YearSlider}.tsx`, `app/src/views/FilterBar/search.css`,
`app/src/lib/measures.ts` (+ its test).
- Tokens above replace the old ones (keep the old names `--ink --muted --grid --panel
  --page --accent` valid).
- Layout: `.app` padding 12, gap 12; rows `auto minmax(300px,1fr) minmax(360px,1.2fr)
  minmax(290px,.9fr)`, `min-height: 100vh`, `height: 100vh` only above 1000 px height;
  below that the page scrolls. Keep the stacked layout under 900 px width.
- Panel: padding 12px 14px 10px; head has the title and, after it, the letter as a
  small quiet tag (11px, `--faint`, no dark box); tools on the right; note 11.5px
  `--muted` with a top margin of 6.
- `ChipGroup`: two looks, chosen by the data, no new prop. Options with a `colour` →
  pills: 26px high, `--fill` background, 8px colour dot (round), selected = background
  `color-mix(in srgb, <colour> 16%, white)`, `box-shadow: inset 0 0 0 1.5px <colour>`,
  ink text, weight 600. Options without colour → a segmented control: track `--fill-2`,
  radius `--radius-m`, padding 2; each option 24px high, 0 10px; the selected one is a
  white thumb with `--shadow-thumb` and weight 600. Pass the colour to CSS through a
  `--c` custom property in `style`.
- `.btn`: 28px high, `--fill`, radius `--radius-m`, no border, hover `--fill-2`.
  `select`: `appearance: none`, same look as `.btn`, a chevron drawn with an inline SVG
  `background-image`, padding-right 24.
- Filter bar: a sticky translucent toolbar (`position: sticky; top: 0; z-index: 30`,
  `background: rgba(255,255,255,.72)`, `backdrop-filter: saturate(180%) blur(20px)`,
  `--radius-l`, `--shadow-panel`, padding 10px 14px). Row 1: title, then the search
  (flex 1, max 360, 30px high, `--fill`, radius `--radius-m`, a magnifier glyph as
  background SVG), country chips, then "Reset" and "About the data" pushed right.
  Row 2: the control groups in a row with `gap: 18px`, each group = its 11px label
  above its control (`.group` becomes a column). Order: years, genre, genre mode,
  films, money, map source.
- `YearSlider`: track 4px `--fill-2`, the range between the thumbs filled `--accent`
  (two CSS custom properties `--from`, `--to` in percent set from the component),
  thumbs 18px white circles with `--shadow-thumb` (both `::-webkit-slider-thumb` and
  `::-moz-range-thumb`), the two years printed as 13px/600 tabular at the ends. The
  upper thumb must stay grabbable when both thumbs meet (raise the z-index of the one
  last moved, or of the lower one when both are at the maximum).
- `Tooltip`: background `rgba(29,29,31,.92)`, `backdrop-filter: blur(12px)`, radius
  `--radius-m`, padding 7px 10px, 12px/1.35, `--shadow-pop`, max-width 320 with normal
  wrapping; fades in over 120 ms.
- Search dropdown (`search.css`): `--panel`, `--radius-m`, `--shadow-pop`, option rows
  30px, active row `--accent-soft`, group headings 11px `--muted`.
- `measures.ts`: add `short` to every measure (Tomatometer, Metascore, RT audience,
  IMDb, MC users, Letterboxd, TMDB, Gap, Budget, Box office, ROI, Votes, Year, Runtime)
  and a test that every key has one. Do not change `label`.

### S2 map and timeline
Files: `app/src/views/WorldMap/*`, `app/src/views/GenreTimeline/*`.
- Map: countries get a white 0.5px stroke (non-scaling). No-data hatch: `--fill`
  background with `--fill-2` lines, quieter than now. Selected country: 1.75px `--ink`
  outline. Hovered country: 1px `--accent` outline drawn on top (local hover state
  already exists). Zoom buttons: one vertical group top right, 28px squares on a white
  card with `--shadow-pop`, a hairline between them; "reset view" as a small `.btn`
  under it. Legend: a floating card bottom left (`rgba(255,255,255,.82)`,
  `backdrop-filter: blur(14px)`, `--radius-m`, `--shadow-pop`, padding 8px 10px, max
  width 240), ramp 8px high with radius 4, 11px text. Give the map 6px more inner
  padding so it does not touch the edges.
- Timeline: bands at `fill-opacity: .9` with a 0.5px white stroke between them; the
  selected band outline 1.25px `--ink`, `stroke-linejoin: round`; other bands drop to
  `.55` opacity while a family is hovered (local state, CSS class). Thin years: replace
  the heavy stripes with a white wash (`fill: #fff; opacity: .5`) plus a fine pattern
  (white 1px lines every 5px, opacity .6); keep the "hatched: under 30 films" line but
  put it into the panel note. Brush selection: `fill: var(--accent)` at .08,
  `stroke: var(--accent)` 1px, radius 3; handles as 4px-wide rounded `--accent` bars.
  Axes: tick text 11px `--muted`, no axis line on y, grid lines at 25/50/75 % in
  `rgba(255,255,255,.35)` over the bands.

### S3 scatter and franchise
Files: `app/src/views/FilmScatter/*`, `app/src/views/Franchise/*`.
- Scatter: grey points `#b4b8c0` at alpha .30, family colour at .55, radii 1.5–6 px
  (plain 2.25). Grid `--grid`, tick text 11px `--muted`, axis titles 11px `--muted`.
  The `y = x` line `--faint`, dash 3 3. Brush selection as in S2 (accent, .08 fill).
  Hover ring 1.5px `--accent` with a 3px white halo under it; pinned ring `--ink`.
  Franchise path 1.5px `--ink` with white 3px halo under it and `#k` labels 11px/600
  with a white text halo (`paint-order: stroke`). Preset buttons use the segmented look
  (they are not a `ChipGroup`; mirror its CSS classes: wrap them in `.chips.segmented`
  and keep `aria-pressed`).
- Franchise: grey lines `#b4b8c0` at .28, 1px; family lines at .45, 1px; hovered line
  2px `--accent`; selected 2.25px `--ink` with 3px dots (white 1.5px stroke); median
  1.5px `--ink-2`, dash 4 3, label 11px. Baseline `--line`. Tick text and titles as in
  the scatter. The name label of the selected franchise gets the white text halo.

### S4 table, card, about
Files: `app/src/views/SelectionTable/*`, `app/src/views/FilmCard/*`, `app/src/views/About/*`.
- Table: header 11px/500 `--muted`, one line per header using `MEASURES[k].short`
  (unit after it in `--faint`), sticky with `rgba(255,255,255,.86)` and
  `backdrop-filter: blur(10px)`, a hairline `--line` under it. Rows 30px, hairline
  `--grid` between rows, hover `--page`, pinned row `--accent-soft` with a 3px
  `--accent` bar on the left. In-cell bars: a 4px rounded bar at the bottom of the
  cell (`--fill-2` track is not drawn; the bar is `#c7c7cc`, `--accent` at .55 in the
  sorted column), number above it. Gap cells keep PuOr but as a rounded pill
  (radius `--radius-s`, margin 4px 6px) not a full cell. Family swatches: 7px round
  dots. The columns menu is a popover card (`--shadow-pop`, `--radius-m`) with 28px
  rows. Update `ROW_H` if it is a constant.
- Card: poster radius 8 with `--shadow-pop`; title 17px/650 `-0.015em`; meta line
  12.5px `--muted`; section headings 11px/500 `--muted` (not uppercase); score rows:
  label 12px, bar 6px high fully rounded, track `--fill`, fill `--ink-2` for critics
  and `--accent` for audience, value 12px/600 tabular right aligned; badges are 20px
  pills on `--fill` 11px; country and franchise buttons use `.btn` sizing at 24px.
  The hint is centred, `--muted`, with a small outline icon above it (inline SVG).
- About: dialog radius 16, `--shadow-pop`, padding 22px 24px, `::backdrop`
  `rgba(0,0,0,.28)` with `backdrop-filter: blur(6px)`; it opens with opacity 0→1 and
  scale .98→1 over 180 ms (`@starting-style`), section headings 13px/600, body 13px
  with 1.5 line height, the counts table with hairlines.

### Verify (from `app/`, every slice)
- `npm run typecheck` and `npm run lint` → no errors (errors in files of other slices
  may be work in progress: report, do not fix)
- your slice's existing Vitest file(s) if you touched logic → pass
