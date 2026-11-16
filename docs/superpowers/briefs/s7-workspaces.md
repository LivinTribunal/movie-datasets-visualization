# S7: three workspaces instead of one long page

Decision D29. The seven panels no longer share one page. A tab switch picks
one of three workspaces; each fills the viewport under the top bar, with no
page scroll on a laptop. State stays in the one store, so a filter or a
selection made in one workspace still holds in the others, and the selection
chips in the filter row show it everywhere.

Rules: mirror the nearest code, minimal diff, no new dependency. No git
commands that change the tree. Verify only with `npx tsc --noEmit`,
`npx eslint <changed files>` and
`npx vitest run src/lib/hash.test.ts src/state/store.test.ts`. Do not run the
build or Playwright.

## Files

`app/src/App.tsx`, `app/src/index.css`, `app/src/state/store.ts`,
`app/src/state/store.test.ts`, `app/src/lib/hash.ts`, `app/src/lib/hash.test.ts`,
`app/src/views/FilterBar/FilterBar.tsx`, `app/src/views/FilterBar/Search.tsx`,
`app/src/views/WorldMap/WorldMap.tsx`, `app/src/views/SelectionTable/table.css`,
`app/e2e/smoke.spec.ts`.

## Store and hash

- `export type Tab = 'taste' | 'ratings' | 'franchises'`; value `tab`, default
  `'taste'`; action `setTab`.
- `reset` keeps the current tab: `set((s) => ({ ...initial(), tab: s.tab }))`.
- Hash key `tab`, written only when it differs from the default, decoded with
  `oneOf` like `sub`. Add one encode/decode case to `hash.test.ts`.

## Shell (`App.tsx`, `index.css`)

```
.app            grid, rows: auto auto minmax(0, 1fr); height 100vh; min-height 680px
  FilterBar     renders the top bar and the filter row (two siblings or one
                header with two rows; keep class `area-f` on the header)
  main.workspace[data-tab]   grid, 12 columns, 2 rows, gap 12px
```

Only the active workspace's panels are mounted. `main` gets `key={tab}` and a
150 ms opacity fade-in (none under `prefers-reduced-motion`).

| tab | label | panels (grid-column / grid-row) |
|---|---|---|
| `taste` | Taste by country | WorldMap 1–7 / 1–2 · GenreTimeline 8–12 / 1 · SelectionTable 8–12 / 2 |
| `ratings` | Money & ratings | FilmScatter 1–8 / 1 · SelectionTable 1–8 / 2 · FilmCard 9–12 / 1–2 |
| `franchises` | Franchises | Franchise 1–7 / 1–2 · FilmScatter 8–12 / 1 · FilmCard 8–12 / 2 |

Rows: `taste` and `franchises` use `minmax(0, 1fr) minmax(0, 1fr)`; `ratings`
uses `minmax(0, 3fr) minmax(0, 2fr)`. Place panels with the existing
`area-a … area-g` classes scoped by `.workspace[data-tab='…']`; delete the old
`.app` row template and the old `area-*` column rules. About stays mounted
outside `main`.

At `max-width: 900px`: `.app` height auto, `main` is a flex column, each panel
420 px high.

## Top bar and filter row (`FilterBar.tsx`)

Top bar, one line, wraps when narrow:
`h1 Movie Explorer` · tabs · `Search` · spacer · subset · money · Reset · About.

- Tabs: `<div className="tabs" role="tablist" aria-label="Workspace">` with
  three `<button role="tab" aria-selected>`; look like the segmented control
  but 32 px high, 13 px, weight 600 when selected, padding 0 14px.
- Subset and money are the existing `ChipGroup`s, without the `Group` label
  above (they keep their `label` prop for the aria-label and their `title`s;
  give the two money options titles "inflation-adjusted to 2025 USD" and
  "as reported, not adjusted").

Filter row (class `filter-row-groups`, inside the same translucent bar):
`years` · `genre` · `genre mode` groups as today, then, pushed right with
`margin-left: auto` and allowed to wrap, the **selection chips**, shown only
when something is selected, after a muted `selection` group label:

- one `.country-chip` per country (existing);
- franchise chip (existing); its name is a button that calls
  `setTab('franchises')`;
- pinned film chip: title from `useLazy(loadText)?.title[film]`, falling back
  to `fmtImdb(data.films.imdb[film])`; the name is a button that calls
  `setTab('ratings')`; `×` (`aria-label="Unpin film"`) calls `setFilm(null)`;
- brush chip: text `scatter brush`, `×` (`aria-label="Clear brush"`) calls
  `setBrush(null)`.

Chip-name buttons look like plain text (no border, no background, inherit
font, cursor pointer). The **map source** group leaves the filter bar.

## Map source (`WorldMap.tsx`)

The `Map source` ChipGroup (Netflix / Cinema / Made here, store `source` /
`setSource`) moves into the map panel's `tools`, before the mode chips.
`.panel-head` may wrap (`flex-wrap: wrap; row-gap: 6px`) for every panel.

## Search (`Search.tsx`)

After a pick: a franchise also calls `setTab('franchises')`; a film calls
`setTab('ratings')` when the current tab is `taste`. A country changes no tab.

## Table in a narrow panel (`table.css`)

In `taste` the table is 5 columns wide and scrolls sideways. Keep the film
column in view: `.cell-film` and the first header cell get
`position: sticky; left: 0; z-index: 1; background: var(--panel)` (the hover
and selected row backgrounds must still show: set the same background on the
sticky cell for `:hover` and `[aria-selected='true']`).

## e2e (`e2e/smoke.spec.ts`)

Rewrite the one test for the new shell, same style and stubs:

1. load: tab "Taste by country" selected; `.area-a`, `.area-b`, `.area-e`
   visible; `.area-c` not attached.
2. click genre `Horror`: map legend says "share of Horror".
3. click "Zoom in" on the map: a "reset view" button appears.
4. tab "Money & ratings": `.area-c canvas` count 1, `.area-e`, `.area-g`
   visible; brush the scatter as today → table note contains
   "inside the scatter brush" and a `scatter brush` chip is shown.
5. click the second table row → card title non-empty, URL matches `/film=tt/`
   and `/tab=ratings/`.
6. tab "Franchises": `.area-d`, `.area-c`, `.area-g` visible.
7. second page with the same URL: the Franchises tab is selected and the card
   shows the same title.
8. no console errors.
