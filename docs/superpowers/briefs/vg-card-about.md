## Implementation brief: VG film card and About dialog

Goal: panel G shows everything we know about the hovered or pinned film, with every
transformed value labelled, and an "About the data" dialog explains the sources.

Context:
- Read `_views-common.md` in this folder, then spec
  `docs/superpowers/specs/2026-11-16-movie-explorer-app-design.md` **§5 "G. Film card"
  and "About the data"**, §6 and §9.
- Store: `film` (pinned row), `hoverFilm`, `money`, `about`, `countries`, and
  `setFilm`, `toggleCountry`, `setFranchise`, `setAbout`.
- Film columns (`data.films`, see `lib/types.ts`): `imdb` (number; `fmtImdb` gives
  `tt0111161`), `year`, `runtime`, `imdb_votes`, `genre_mask` (bit i = `films.genres[i]`),
  `countries` (ListColumn of ISO-2), money columns, `roi`, `budget_src` and `revenue_src`
  (DictColumn; `codes[row] === nullCode` means none; values `numbers`, `tmdb`,
  `wikidata`, `wikipedia`), `flags` (bit 0 budget converted from another currency, 1
  revenue converted, 2 budget sources disagree, 3 revenue sources disagree, 4 fuzzy
  title match to The Numbers), the seven `*_100` scores, `gap`, `mc_critic_reviews`,
  `collection_id` and `installment` (NaN = not in a franchise).
  `data.franchises.collections.get(id)` is the franchise name.
- `loadText()` → `{ title, director }`; `loadPosters()` → poster paths (`/abc.jpg` or
  null). Both through `useLazy`. `data.meta` has `snapshots`, `base_year`, `counts`,
  `notes`, `attribution`, `sources` (`netflix`, `cinema`, `production` sentences).

Files (yours only):
- `app/src/views/FilmCard/FilmCard.tsx`, `Poster.tsx`, `filmcard.css`
- `app/src/views/About/About.tsx`, `about.css`
- `app/src/lib/film.ts`, `film.test.ts`

Design:
1. `lib/film.ts` (pure)
   - `filmGenres(films, row) → string[]`; `filmCountries(films, row) → string[]` (ISO-2).
   - `SRC_LABEL`: `numbers` → "The Numbers", `tmdb` → "TMDB", `wikidata` → "Wikidata",
     `wikipedia` → "Wikipedia infobox".
   - `moneyFacts(films, row, money) → { budget: MoneyFact; revenue: MoneyFact; roi:
     number }` with `MoneyFact = { value: number; source: string | null; converted:
     boolean; disagree: boolean }`, value from the column of the money mode;
     `fuzzyMoney(films, row)` for bit 4.
   - `SCORE_GROUPS`: critics = `tomatometer`, `metascore`; audience = `audience`,
     `imdb`, `mc_user`, `letterboxd`, `tmdb` (MeasureKeys).
2. `FilmCard`: shows `hoverFilm ?? film`. Nothing chosen: the hint "Hover a point or a
   table row to see a film. Click to pin it." The panel body scrolls when it is short.
   - Header: `Poster` on the left (92 × 138), then title (or `fmtImdb` until titles
     load), `year · runtime min · director`, genres, IMDb votes, a link "IMDb page"
     (`https://www.imdb.com/title/<tt id>/`, `target="_blank" rel="noreferrer"`).
     When the shown film is the pinned one: a "pinned" badge and an "unpin" button.
   - Production countries as chip buttons (name from `countryByIso2`, `aria-pressed`
     when in the filter) that call `toggleCountry`. Franchise as a button
     `Toy Story Collection · #3` that calls `setFranchise(id)`.
   - Scores: two groups titled "critics" and "audience"; each score is a row with its
     label (`MEASURES[k].label`), a bar on 0–100 and the number; a missing score says
     "no data" with no bar. Metascore adds `(N reviews)`. Under them `gap (audience −
     critics): +12 points` with an explicit sign, or "no data".
   - Money: rows for budget, box office and ROI. Value through `fmtMoney` with the unit
     "2025 USD" or "nominal USD"; in 2025 USD mode the row has the badge "inflation-
     adjusted". Badges: `source: The Numbers`, "converted from another currency",
     "sources disagree", and on both money rows "fuzzy title match" when bit 4 is set.
     ROI through `fmtRatio`. Missing is "no data", never 0.
3. `Poster({ row })`: rendered only when a film is shown, so `films_poster.pack` is
   fetched on first use. It waits 150 ms after `row` settles before it sets the image
   URL (hover moves fast), `https://image.tmdb.org/t/p/w185` + path, `alt=""`,
   `loading="lazy"`, fixed size. A grey placeholder box with the text "no poster" while
   loading, when the path is null and on `onError`.
4. `About({ data })`: a native `<dialog>` opened with `showModal()` when the store's
   `about` is true and closed otherwise; its `close` event calls `setAbout(false)`.
   Content, in this order: title "About the data"; snapshot dates and the base year of
   the USD; the counts as a small table with readable labels; "Map sources" (the three
   `meta.sources` sentences, labelled Netflix, Cinema, Made here); "How the data was
   transformed" (every string of `meta.notes` as a list); "Attribution"
   (`meta.attribution`); a "Close" button. Max width 720 px, scrolls inside.

Tests (`film.test.ts`, a three-film hand-made `Films`): `filmGenres`, `filmCountries`,
`moneyFacts` in both money modes with each flag bit and with a null source, `fuzzyMoney`.

Out of scope: every other panel, the store, `index.css`, `App.tsx` (the architect mounts
`<About data={data} />` there).

Verify (from `app/`):
- `npx vitest run src/lib/film.test.ts` → pass
- `npm run typecheck` and `npm run lint` → no errors (report errors in files that are not
  yours, do not fix them)
