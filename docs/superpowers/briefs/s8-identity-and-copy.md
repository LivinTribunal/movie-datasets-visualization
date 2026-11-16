# S8: a look of its own, and plain copy

The polish pass (S1–S4) produced the stock generated-dashboard look: white
rounded cards with soft shadows on grey, pill chips, an Apple-blue accent,
letter badges, notes glued with middle dots. This pass replaces it (D30).

## The idea

1. **The only colour on the page is data.** Chrome is black, white and greys.
   Hue appears only where it encodes a genre family or a quantity. Selection,
   hover, brush and focus are ink, never blue.
2. **Poster type.** One family, Archivo variable (self-hosted through
   `@fontsource-variable/archivo`, with the width axis). Condensed bold
   (`font-stretch: 62%`, weight 700–800) for the app title, the tabs and panel
   titles, like the billing block on a film poster. Normal width for
   everything else. Fallback stack: `'Archivo Variable', 'Helvetica Neue', Arial, sans-serif`.
3. **A black marquee.** The top bar is a solid black band with white type,
   edge to edge. Under it runs a 4 px stripe in the selected genre's colour
   (`--family`, set as an inline custom property on `.app`).
4. **Flat panels.** White, 1 px border, 4 px radius, no shadow, no blur, no
   translucency. Only floating things (tooltip, menus, search list, map
   legend, dialog) cast a shadow.
5. **Copy says what the thing is**, in sentence case, as full sentences
   without `·` separators. No letter badges.

## Tokens (`app/src/index.css`, same names, new values)

```
--ink #141414   --ink-2 #3a3a3a   --muted #6b6b6b   --faint #9a9a9a
--page #efefef  --panel #fff      --fill #f1f1f1    --fill-2 #e2e2e2
--grid #ebebeb  --line rgba(0,0,0,.16)
--accent #141414   --accent-soft rgba(0,0,0,.07)
--radius-l 4px  --radius-m 3px  --radius-s 2px
--shadow-panel none   --shadow-thumb none
--shadow-pop 0 8px 24px rgba(0,0,0,.2)
--display: condensed Archivo (font-stretch 62%, weight 750, letter-spacing 0)
```

Controls: buttons, selects and the search field are white with a 1 px
`--line` border, 3 px radius, 28 px high; hover `--fill`. A button group
(`.chips.segmented`) is one bordered box with 1 px dividers; the selected
option is ink with white text. Genre chips: square 10 px swatch plus label,
no background; the selected one is filled with its family colour (`--c`),
text `#141414`, 3 px radius. Year slider: 2 px ink track, round 14 px ink
thumbs. Tooltip: `#000`, white text, 3 px radius, no blur, no fade-in.
Focus ring: 2 px ink, offset 2 px. Keep the reduced-motion rules; delete the
reduced-transparency ones that no longer apply.

## Slice A: chrome

Files: `app/package.json` (+lockfile, `npm i @fontsource-variable/archivo`),
`app/src/main.tsx`, `app/src/index.css`, `app/src/App.tsx`,
`app/src/components/{Panel,ChipGroup}.tsx`,
`app/src/views/FilterBar/{FilterBar,YearSlider,Search}.tsx`, `search.css`,
`app/src/views/About/{About.tsx,about.css}`, `app/e2e/smoke.spec.ts`.

- Import the font's width-axis CSS (`@fontsource-variable/archivo/wdth.css`;
  check `node_modules` for the exact file. If the package has no width axis,
  also install `@fontsource/archivo-narrow` weight 700 and use it for
  `--display`).
- `Panel`: drop the letter badge (keep the `letter` prop optional and unused
  so callers compile). Title in `--display`, 19 px.
- Header: `.marquee` (black band, full width, the logo, "Movie Explorer" in
  `--display` 24 px, tabs, search, then "Reset filters" and "About the data").
  Tabs are condensed uppercase words, 17 px, white at 55 % opacity, the
  selected one at 100 % with a 3 px white underline. Keep `role="tablist"` /
  `role="tab"`.
- Under the stripe, a white filter strip (bottom border, no card):
  row 1 genre chips; row 2, each with a short muted sentence-case label to its
  left: "Years" slider, "Other genres" [Dimmed | Hidden] (was highlight /
  filter), "Films with" [10,000+ votes | 1,000+ votes] (was notable / all),
  "Money in" [2025 dollars | As reported] (was 2025 USD / nominal); the
  selection chips sit at the right end of row 2 (`margin-left: auto`), and
  row 2 has a fixed min-height so selecting never moves the layout. When
  nothing is selected show muted "Nothing selected. Click a country, a dot,
  a row or a line." Selection chips: 1 px ink border, white, 3 px radius.
- Remove the `filter-bar` panel/sticky/translucent styles. `.app` padding 0;
  the workspace gets 12 px padding. Keep the ≤900 px stack.
- About: flat white dialog, 4 px radius, `--shadow-pop`, plain scrim
  `rgba(0,0,0,.45)` without blur; title in `--display`.
- e2e: update names that changed (tabs keep their names; "About the data",
  "Reset filters"). Slice B changes these strings, so match them:
  empty card text "Hover a dot or a row to see a film", table note
  "inside the brush", map legend still contains "share of Horror" in lower
  or sentence case (use a case-insensitive regex).

## Slice B: views

Files: everything under `app/src/views/{WorldMap,GenreTimeline,FilmScatter,Franchise,SelectionTable,FilmCard}/`
(tsx and css). Do not touch `index.css`; use the tokens above by name.

Styling: remove every `backdrop-filter`, translucent background, blue, and
panel-level shadow; floating elements use `--shadow-pop` and 3 px radius.
Brushes: ink outline 1 px, fill `rgba(0,0,0,.06)`. Scatter hover ring ink
1.5 px, pinned ring ink 2.5 px (both keep the white halo). Table: selected
row `--accent-soft` with a 3 px ink bar; sorted column bar ink at 55 %;
header labels sentence case. Card: links ink and underlined; score bars keep
their two greys/ink (critics `--ink-2`, audience `--ink`), no blue.
Stop passing `letter` to `Panel`.

Copy:

| Where | Now | Becomes |
|---|---|---|
| Map title | World map | by mode and source: "Share of {genre} on Netflix" / "… in cinemas" / "… among films made there"; "Top genre on Netflix" (etc.); "{genre}: cinemas minus Netflix" |
| Map controls | share of genre / top genre / cinema − streaming; Made here | Share / Top genre / Cinemas − Netflix; Netflix / Cinemas / Made there |
| Timeline title | Genre timeline | Genre shares by year |
| Timeline note | three fragments | "A film in n genres counts 1/n in each. Hatched years have under 30 films." plus, for votes, "Votes measure popularity, not rating." |
| Scatter title | Film scatter | Every film as a dot |
| Scatter note | "9,254 films · 1,414 hidden: no critics (Tomatometer) · …" | "9,254 films. 1,414 more have no {x short} and 44 no {y short}." (drop a clause when its count is 0) |
| Franchise title | Franchise lines | Sequels against the first film |
| Franchise note | dotted fragments | "82% of sequels rate below the first film (76% in Action & Adventure, 230 franchises). Films after the 10th are not shown." Same pattern for box office ("earn less than"), and "N values outside 0.01×–100× run off the chart." |
| Table title | Selection table | "10,712 films" (the count), or "1,586 films inside the brush" |
| Table note | "… pass the filters · bars share one scale per column" | none when unbrushed |
| Card title | Film card | Film |
| Card empty | Hover a point or a table row… | "Hover a dot or a row to see a film. Click to pin it." |
| Card facts | "2005 · 140 min · George Lucas" | "2005, 140 min, directed by George Lucas" |
| Tooltips | "A · B · C" strings | bold first line (name), then one plain line per fact, e.g. "54% of releases in 1952" / "15 films that year" |
| Columns menu | columns | Columns |

Every other `·` used to join facts in these views becomes a sentence or a
line break. Units, "no data", the transformed-data badges and the
tooltip facts themselves stay.

## Verify

`npx tsc --noEmit`, `npx eslint <changed files>`. No build, no test suites,
no Playwright, no git commands that change the tree.
