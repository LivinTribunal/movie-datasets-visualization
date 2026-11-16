## Implementation brief: VF search and URL hash

Goal: the search box finds countries, franchises and films, and the whole view state is
kept in the URL hash so a link reproduces what the user sees.

Context:
- Read `_views-common.md` in this folder, then spec
  `docs/superpowers/specs/2026-11-16-movie-explorer-app-design.md` **§3 (state and "URL
  hash") and §5 "F. Filter bar"** (the search bullet).
- `app/src/views/FilterBar/Search.tsx` is a disabled stub rendered by `FilterBar` as
  `<Search data={data} />`. Keep that signature.
- `app/src/state/store.ts`: the values and defaults are in `initial()`. You may add one
  line there: `export const defaults = initial`. Change nothing else in it.
- `app/src/App.tsx` loads the data; `loadText()` gives the titles.
- `data.countries` (249 `{ iso2, name }`), `data.franchises.collections`
  (`Map<id, name>`, 605), `data.films.imdb` (Uint32Array of numeric ids; `fmtImdb`
  prints `tt0111161`), `data.families`, `MEASURE_KEYS`.

Files (yours only):
- `app/src/views/FilterBar/Search.tsx`, `search.css`
- `app/src/lib/search.ts`, `search.test.ts`
- `app/src/lib/hash.ts`, `hash.test.ts`
- `app/src/state/hashSync.ts`
- `app/src/App.tsx` (one effect), `app/src/state/store.ts` (the one export line)

Design:
1. `lib/search.ts` (pure)
   - `fold(s)`: lower case, diacritics stripped (`normalize('NFD')`, remove `\p{M}`).
   - `foldAll(titles)`, memoised: the folded titles, computed once.
   - `search(query, { countries, collections, folded, limit = 8 }) → { countries:
     Country[]; franchises: { id: number; name: string }[]; films: number[] }`.
     A query under 2 characters gives empty groups. At most 3 countries and 3
     franchises, names that start with the query before names that contain it. Films
     fill the rest of `limit`, scanned in row order (most voted first) with `includes`,
     stopping as soon as enough are found. `folded` null (titles not loaded) → no films.
2. `Search`: a combobox. `<input role="combobox" aria-expanded aria-controls
   aria-activedescendant>` and a listbox dropdown under it (absolute, above the panels,
   `z-index` 20) with group headings "countries", "franchises", "films"; a film row
   shows the title and the year. While titles load the film group says "loading
   titles…". Arrow keys move the active option, Enter picks, Escape and a click
   outside close. Picking: country → `toggleCountry`, franchise → `setFranchise`,
   film → `setFilm`; then the input is cleared. No result: "nothing found".
3. `lib/hash.ts` (pure)
   - `encodeHash(values, defaults, imdb) → string` (no leading `#`): `URLSearchParams`
     with only the fields that differ from the defaults. Keys: `yr` (`1990-2026`), `g`
     (family index), `go` (`1`), `sub`, `money`, `src`, `map`, `c` (ISO-2 joined by
     `.`), `tm`, `x`, `y`, `size` (`none` for null), `fr` (collection id), `fy`,
     `film` (`tt…` id of the pinned row), `sort` (`key` or `-key` for descending),
     `cols` (keys joined by `.`). Never `brush`, `hoverFilm`, `about`.
   - `decodeHash(hash, ctx) → Partial<Values>` with `ctx = { imdb, nFamilies,
     countries: Set<iso2>, collections: Set<id> }`: only valid fields are returned.
     Unknown keys, unknown enum values, an unknown country or franchise, a film id not
     in `imdb`, `x === y`, a family out of range, more than 6 countries, non-numeric
     years: that field is dropped, the rest still applies.
4. `state/hashSync.ts`: `startHashSync(data) → () => void`. On start it applies
   `decodeHash(location.hash)` with `useStore.setState`. It subscribes to the store and,
   debounced 300 ms, writes `history.replaceState(null, '', url)` where `url` keeps path
   and query and has `#…` only when the encoded string is not empty; it skips the write
   when the hash is unchanged. It listens to `hashchange` and applies the decoded
   state on top of the defaults. The returned function removes the subscription, the
   listener and the timer.
5. `App.tsx`: one `useEffect` that calls `startHashSync(data)` when the data is loaded
   and returns its cleanup.

Tests:
- `search.test.ts`: `fold` ("Amélie" → "amelie"); short query; prefix before substring;
  the caps of 3 and 3; films fill up to the limit in row order; null `folded`.
- `hash.test.ts`: defaults encode to an empty string; a full non-default state
  round-trips through `encodeHash` and `decodeHash`; each invalid case of Design 3 is
  dropped while a valid field next to it survives; the film is written as its `tt` id.

Out of scope: every panel, `index.css`, the rest of the store, the About dialog.

Verify (from `app/`):
- `npx vitest run src/lib/search.test.ts src/lib/hash.test.ts` → pass
- `npm run typecheck` and `npm run lint` → no errors (report errors in files that are not
  yours, do not fix them)
