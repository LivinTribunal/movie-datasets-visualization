# S9: take the design out

Two restyles (S1–S4 and S8) each read as "generated": first rounded shadowed
cards, pills and an Apple blue; then a black band with a vermilion stripe,
condensed uppercase poster type and black-filled buttons. Both added design.
This pass removes it (D31). The model is a plain analysis tool: a white page,
system font, charts separated by whitespace, native-looking controls, and
colour only in the data (D30's rule stays).

Test for every element: would a person building a research tool in a week
have bothered to style this? If not, it gets the browser's plain look.

## Tokens (`app/src/index.css`, same names)

```
--ink #1a1a1a  --ink-2 #444  --muted #6f6f6f  --faint #9b9b9b
--page #fff    --panel #fff  --fill #f2f2f2   --fill-2 #e4e4e4
--grid #ececec --line #d9d9d9
--accent #1a1a1a  --accent-soft #f0f0f0
--radius-l 0  --radius-m 3px  --radius-s 2px
--shadow-panel none  --shadow-thumb none
--shadow-pop 0 2px 8px rgba(0,0,0,.12)
font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; 13px/1.45
```

Delete `--display`, every `font-stretch`, every `text-transform: uppercase`,
and the Archivo dependency (`npm uninstall @fontsource-variable/archivo`,
remove its import in `main.tsx`).

## Layout

```
Movie Explorer   Taste by country  Money & ratings  Franchises      [search........]  Reset  About
--------------------------------------------------------------------------------------------------  (1px #d9d9d9)
■ Action & Adventure  ■ Sci-Fi & Fantasy  ■ Crime & Thriller  ...                (legend = genre picker)
Years 1990 ●──● 2026   [ ] Only this genre   [ ] Include films under 10,000 votes   Money [2025 USD ▾]
                                                             Selected: United States ×  Star Wars ×
--------------------------------------------------------------------------------------------------
Map title                    [Netflix ▾] [Share ▾]   |   Timeline title                 [IMDb votes ▾]
                                                     |
```

- Header: white, one line, 44 px, bottom 1px `--line`. Title 15 px weight
  600 with the 16 px favicon before it (no outline, no box). Tabs are plain
  text 13 px, `--muted`, the selected one `--ink` weight 600 with a 2 px ink
  underline flush with the header's bottom line. Search: 1 px `--line`
  border, 3 px radius, 28 px high, 260 px wide. "Reset" and "About" are text
  buttons (no border, no background, `--ink-2`, underline on hover).
- Filter area: white, padding 8px 16px, bottom 1px `--line`. No band, no
  stripe (delete `.family-stripe` and `--family`).
- Workspace: padding 16px, gap 0. Panels have no border, background or
  radius. Separate neighbouring panels with a 1px `--line` rule between them
  and 16 px padding on each side of the rule (use `border-left` on the right
  column's panels and `border-top` on panels in the second row of a column).
- Panel head: title 14 px weight 600, sentence case, `--ink`; tools on the
  right. Note: 12 px `--muted`.

## Controls

- **Genre picker = the legend.** Each option: 10 px square swatch, label in
  `--ink-2`, no background, no border, 24 px high, 4px 8px padding. Selected:
  label `--ink` weight 600 and a 2 px underline in the family colour under
  the label. Hover: label `--ink`. Keep `role="radio"` and the names.
- **Segmented groups (`.chips.segmented`)**: only where three or fewer short
  options are toggled often (franchise Rating / Box office, scatter presets).
  Look: 1 px `--line` box, 3 px radius, options 24 px high; selected option
  `--fill-2` background and `--ink` text weight 500 (never black fill).
- **Selects**: 28 px, 1 px `--line` border, 3 px radius, white, small chevron.
- **Checkboxes**: native `<input type="checkbox">` with `accent-color: var(--ink)`
  and a text label.
- **Buttons (`.btn`)**: 1 px `--line` border, white, 3 px radius, 26 px; hover `--fill`.
- **Year slider**: 2 px `--fill-2` track, ink range, 12 px round ink thumbs
  with a white 2 px ring.
- **Selection**: "Selected:" in `--muted`, then each item as plain text with
  a small "×" text button (`--muted`, hover `--ink`), separated by 12 px. No
  boxes. When nothing is selected, render nothing (the row keeps its height).
- **Tooltip**: white, 1 px `--line` border, 3 px radius, `--shadow-pop`,
  12 px `--ink`, first line weight 600.
- **Floating map legend, menus, search list, About dialog**: white, 1 px
  `--line` border, 3 px radius, `--shadow-pop`. Dialog scrim `rgba(0,0,0,.3)`.
- Focus ring: 2 px `#1a1a1a` outline, offset 1 px. Selection, hover rings and
  brushes stay ink/grey as now.

## Copy

Short, literal, the way an analyst labels a chart. No sentences addressed to
the reader, no instructions to click.

| Where | Now | Becomes |
|---|---|---|
| Filter: genre mode | Other genres Dimmed / Hidden | checkbox "Only this genre" (checked = `genreOnly`) |
| Filter: subset | Films with 10,000+ / 1,000+ votes | checkbox "Include films under 10,000 votes" (checked = `subset 'all'`) |
| Filter: money | Money in 2025 dollars / As reported | label "Money" + select "2025 USD" / "Nominal USD" |
| Selection empty | Nothing selected. Click a country… | nothing |
| Map title | Share of X on Netflix (etc.) | "{source}: share of {genre}" / "{source}: top genre" / "Cinema minus Netflix share of {genre}", source = "Netflix top 10" / "Cinema admissions" / "Films produced" |
| Map controls | two segmented groups | two selects: source (Netflix top 10, Cinema admissions, Films produced) and mode (Share of genre, Top genre, Cinema − Netflix) |
| Timeline title | Genre shares by year | "Genre share of {measure} by year" |
| Timeline note | sentences | "Films with n genres count 1/n per genre. Hatched: under 30 films." (+ " IMDb votes measure popularity." for votes) |
| Scatter title | Every film as a dot | "{Y label} vs {X label}" from `MEASURES` |
| Scatter note | 9,254 films. 1,414 more have no… | "9,254 films. Missing: 1,414 Tomatometer, 44 RT audience." (omit zero parts; omit "Missing:" when none) |
| Scatter presets | Critics vs audience … | keep the four, as now |
| Franchise title | Sequels against the first film | "Sequel {rating\|box office} relative to the first film" |
| Franchise note | 82% of sequels rate below … | "Below the first film: 82% of sequels; 76% in Action & Adventure (230 franchises). Only installments 1–10 shown." Box office: "Earned less than the first film: …" plus " 21 values outside 0.01×–100× are clipped." |
| Table title | 10,712 films | "Films (10,712)" / "Films in brush (1,519)" |
| Table note | Films inside the brush. Clear it… | brushed only: "Filtered by the scatter brush." |
| Card title | Film | "Film details" |
| Card empty | Hover a dot or a row… | "No film selected." |
| Card facts | 2005, 140 min, directed by George Lucas | keep |
| Map zoom reset | Reset view | "Reset zoom" |
| Scatter brush button | Clear brush | keep |
| Header buttons | Reset filters / About the data | "Reset" / "About" |

## Slices

**A, chrome**: `app/package.json` (+lock), `src/main.tsx`, `src/index.css`,
`src/App.tsx`, `src/components/{Panel,ChipGroup,Tooltip}.tsx`,
`src/views/FilterBar/*` (tsx, css), `src/views/About/*`, `e2e/smoke.spec.ts`.

**B, views**: `src/views/{WorldMap,GenreTimeline,FilmScatter,Franchise,SelectionTable,FilmCard}/*`.
B uses token names only, never edits `index.css`.

e2e strings to keep in sync (A updates the spec): `.area-a` contains
`/share of horror/i`; buttons "Zoom in" and "Reset zoom"; `.area-e .panel-note`
contains "scatter brush"; button "Remove scatter brush" in the filter area;
card empty text "No film selected."; `.area-g h3`; tabs by name; genre radios
by name.

Verify: `npx tsc --noEmit`, `npx eslint <changed files>`. No build, suites,
Playwright or tree-changing git.
