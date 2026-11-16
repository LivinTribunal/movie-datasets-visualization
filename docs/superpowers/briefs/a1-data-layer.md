## Implementation brief: A1 app data layer

Goal: the app loads the new `.pack` data files into typed arrays, and has the store, the
film filter, the measure list and the formatters that every panel will use. The app still
builds and shows seven stub panels.

Context:
- Read `docs/superpowers/specs/2026-11-16-movie-explorer-app-design.md` **§2, §3 and §4**
  (lines ~45–240). They fix the pack byte layout, every column, the store fields with their
  defaults, the film filter and the measure table. Build exactly that.
- Today: `app/src/lib/data.ts` fetches columnar JSON (`fetchJson`, `loadData`),
  `app/src/lib/types.ts` mirrors the old JSON schema, `app/src/lib/filter.ts` has
  `filmIndices` over arrays, `app/src/state/store.ts` is a small zustand store, and
  `app/src/views/*` are placeholders that read the old shapes. All of that is replaced.
- The real `.pack` files do not exist yet; the pipeline slice writes them in parallel. Test
  against buffers you build in the tests.
- Node 22 and every current browser have `DecompressionStream` and `CompressionStream`.
- Vitest runs in the `node` environment (`app/vite.config.ts`). Test files sit next to the
  code as `*.test.ts`; mirror `app/src/lib/filter.test.ts`.

Files (yours only):
- `app/src/lib/pack.ts`, `pack.test.ts` (new)
- `app/src/lib/types.ts` (rewrite)
- `app/src/lib/data.ts` (rewrite)
- `app/src/lib/filter.ts`, `filter.test.ts` (rewrite)
- `app/src/lib/measures.ts`, `measures.test.ts` (new)
- `app/src/lib/format.ts`, `format.test.ts` (new)
- `app/src/lib/memo.ts` (new)
- `app/src/lib/families.ts`, `families.test.ts` (adapt or delete; see Design 3)
- `app/src/state/store.ts`, `store.test.ts` (rewrite, new test)
- `app/src/state/selectors.ts` (new)
- `app/src/App.tsx` and the six files under `app/src/views/` (stubs only; see Design 9)

Design:
1. `pack.ts`
   - `decodePack(bytes: ArrayBuffer): Pack` for inflated bytes, and
     `fetchPack(url): Promise<Pack>` that fetches, inflates with
     `DecompressionStream('gzip')` when the first two bytes are `1f 8b`, else uses the bytes
     as they are, and throws `Could not load <url>: HTTP <status>` on a bad response.
   - `Pack`: `rows`, `meta`, and typed readers that throw on an unknown column or a wrong
     type: `num(name): Float64Array` (scale applied, NaN where the raw value is the null
     sentinel or NaN), `raw(name)` (the typed array over the buffer: `Uint8Array`,
     `Uint16Array`, `Int16Array`, `Uint32Array` or `Float32Array`), `dict(name):
     DictColumn` (`{codes, values, nullCode}`), `list(name): ListColumn` (`{offsets, codes,
     values}`), `str(name): (string | null)[]`.
   - Bad magic throws `Not an MXP1 pack`.
2. `types.ts`: one interface per table whose property names are the pack column names:
   `Films` (plus `rows`, `notable`, `genres`, `families`), `FilmsText`, `CountryGenre`,
   `CountryYear`, `Franchises` (plus `collections: Map<number, string>`). Numbers a panel
   computes with are `Float64Array` (`num`); `imdb`, `genre_mask`, `family_mask`, `flags`,
   `year` of the country tables and `genre` are raw typed arrays; `collection_id`,
   `installment` and `film_row` are `Float64Array` with NaN for none. Also `Country`
   (`iso2, iso_numeric, name, region, subregion`), `Family` (`name, colour, genres:
   string[]`, array index = bit in `family_mask`), `Meta` (old keys plus `attribution:
   string[]`, `sources: Record<string, string>`), and
   `AppData { films, countryGenre, countryYear, franchises, countries: Country[],
   countryByIso2: Map<string, Country>, families: Family[], meta }`. No `any`.
3. Families: `AppData.families` is built in `data.ts` from `genre_families.json` in
   `family_order`. Keep `familyList` only if you use it for that; otherwise delete
   `families.ts` and its test.
4. `data.ts`
   - `loadData(): Promise<AppData>` fetches in parallel `data/films.pack`,
     `data/country_genre.pack`, `data/country_year.pack`, `data/franchises.pack`,
     `data/countries.json`, `data/genre_families.json`, `data/meta.json`. Relative URLs.
   - `loadText(): Promise<FilmsText>` (`data/films_text.pack`) and
     `loadTopo(): Promise<unknown>` (`data/countries.topo.json`): each fetches once and
     returns the same promise afterwards.
   - `useLazy<T>(load: () => Promise<T>): T | null`, a hook that returns null until the
     promise resolves. It may live in `data.ts`.
5. `filter.ts`: `filmMask(films, f): Uint8Array` (1 = passes) and `countMask(mask)`.
   `FilmFilter = { yearRange: [number, number] | null; subset: 'notable' | 'all';
   countries: string[]; genreOnly: boolean; family: number }`. A film passes when its year
   is inside `yearRange` (inclusive; null = any year), `row < films.notable` for `notable`,
   it has at least one production country in `countries` (an empty list = any country; an
   ISO-2 unknown to the pack matches nothing), and, when `genreOnly`, bit `family` is set
   in `family_mask`.
6. `measures.ts`: `MeasureKey` (the 14 keys of §4), `MEASURES: Record<MeasureKey,
   { label, unit, scale: 'linear' | 'log', domain?: [number, number] }>`,
   `MEASURE_KEYS` in table order, `measureColumn(films, key, money): Float64Array`
   (`budget` and `revenue` pick `_usd2025` or `_usd`), `axisLabel(key, money)` giving
   `budget (2025 USD, log)`, `critics (Tomatometer) (0–100)`, `budget (nominal USD, log)`,
   `isScore(key)` (the seven 0–100 scores), and `PRESETS` (the four of §4 with a label).
7. `format.ts`: `fmtInt` (1,204), `fmtMoney` ($2.9B, $35M, $850K, $900), `fmtScore` (77),
   `fmtPct` (0.213 → `21%`, under 10% one decimal: `6.2%`), `fmtRatio` (3.2×),
   `fmtValue(key, value)` that picks by measure, and every one returns `no data` for NaN
   or null. `fmtImdb(n)` → `tt0111161`.
8. `store.ts`: the `State` of §3 with those defaults and these actions: `setYearRange`,
   `setFamily`, `setGenreOnly`, `setSubset`, `setMoney`, `setSource`, `setMapMode`,
   `toggleCountry`, `setTimelineMeasure`, `setX`, `setY`, `setSize`, `setBrush`,
   `setFranchise`, `setFranchiseY`, `setFilm`, `setHoverFilm`, `setSort`, `setColumns`,
   `setAbout`, `reset`. Enforce the four setter rules of §3. Export the union types.
   `memo.ts`: `memoLast(fn)` caches the last call, comparing arguments with `Object.is`.
   `selectors.ts`: `useFilmMask(data)` (store fields → memoised `filmMask`, shared by all
   callers) and `useFilmMaskAllYears(data)` (same without the year range and without
   `genreOnly`).
9. Stubs: `App.tsx` keeps its loading and error states and calls the new `loadData`. Each
   existing view file becomes a stub that renders `<section className="panel"><h2>…</h2>
   </section>` with its title and takes `{ data: AppData }`. Rename
   `views/DetailPanel/DetailPanel.tsx` to `views/FilmCard/FilmCard.tsx` (`FilmCard`) and
   add `views/SelectionTable/SelectionTable.tsx`. The next slice builds the real shell.

Tests:
- `pack.test.ts`: a helper builds an MXP1 buffer per §2.1. Cases: each numeric type with
  scale and null → `num`; `raw` returns the exact integers for a u32 above 2^24; `dict`,
  `list` (with an empty list) and `str` (null, non-ASCII); a column whose offset is 8
  inside the data section decodes right; bad magic throws; `fetchPack` inflates a gzipped
  buffer and also accepts a plain one (stub `fetch` with `vi.stubGlobal`).
- `filter.test.ts`: year range inclusive and null; notable prefix; any-of countries, an
  unknown country matches nothing; `genreOnly` on and off; `countMask`.
- `measures.test.ts`: `measureColumn` switches money columns; `axisLabel` for a log money
  measure in both modes and for a score; every key in `MEASURE_KEYS` has an entry.
- `format.test.ts`: one case per formatter, and NaN → `no data` for each.
- `store.test.ts`: `setX` refuses Y's measure and a valid `setX` clears the brush; a
  seventh country is refused and toggling removes; `setYearRange` clamps and orders;
  `reset` restores defaults.

Constraints: TypeScript strict, no `any`, no new dependency, named imports only, ESLint
clean. Relative data URLs. No `eslint-disable`.

Out of scope: real panels, CSS, `components/`, the URL hash, aggregations for single
panels, anything under `pipeline/`.

Verify (from `app/`):
- `npx vitest run src/lib src/state` → all pass
- `npm run typecheck` → no errors
- `npm run lint` → no errors
