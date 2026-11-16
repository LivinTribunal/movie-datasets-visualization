# Extra film data: design (2026-11-16)

Adds the "take first" rows of `docs/dataset-candidates.md` to the app:
unused columns of the TMDB+IMDb file and of The Numbers metrics file (both are
local already), and a third and fourth Wikidata query (Oscars, external ids).
Decisions: D33 (what is added and how it is shown), D34 (the scraper contact
moves to an environment variable).

## 1. Interim data (pipeline)

| File | New columns | From |
|---|---|---|
| `interim/tmdb.parquet` → `films.parquet` | `keywords` list[str] (raw split on `"|"`), `companies` list[str] (split on `", "`), `cast` list[str] (first 5), `writers` list[str] (first 3), `overview` str | TMDB CSV |
| `interim/numbers_metrics.parquet` | `theaters_open` i32, `theaters_max` i32, `legs` f64, `video_sales` f64 (USD), `domestic_share` f64 (percent) | "Theater counts" (`"4,134 opening theaters/4,202 max. theaters, …"`), "Legs", "Total Est. Domestic Video Sales (USD)", "Domestic Share Percentage" |
| `scraped/wikidata_extra.parquet` (new, committed) | `imdb_id`, `qid`, `oscar_wins` i16, `oscar_noms` i16, `csfd_id`, `filmaffinity_id`, `allocine_id`, `douban_id` (str) | Wikidata P166/P1411 (award class Academy Awards Q19020), P2529, P480, P1265, P4529 |
| `interim/extras.parquet` (new, `movies derive`) | one row per `imdb_id`; see §2 | the three above + reference CSVs |

Empty strings and empty lists become null. Zero video sales, opening weekend or
theatre count means unknown and becomes null.

## 2. Derived columns (`derive/extras.py`)

- `story_source`: one of `original`, `book`, `comic`, `true_story`, `stage`,
  `screen`, `other`, or null. The Numbers `Source` first, else the first TMDB
  keyword that maps to a category. Neither says anything → null, never
  `original`. Both mappings live in `data/reference/story_sources.csv`
  (`origin,label,category`; `origin` is `numbers` or `tmdb`).
  `story_source_src` is `numbers` or `tmdb`.
- `age_rating`: `G`, `PG`, `PG-13`, `R`, `NC-17`, `NR`, or null. TMDB
  `certification_us` first, else The Numbers `mpaa_rating` mapped to the same
  set (`Not Rated` → `NR`, anything else unknown → null).
- `studio`: group of the first company in `companies` listed in
  `data/reference/studios.csv` (`company,studio`), groups `disney`, `warner`,
  `universal`, `sony`, `paramount`, `fox`, `lionsgate`, `mgm`. A film with
  companies but none listed → `independent`. No companies → null.
- `opening_usd`, `opening_usd2025`: The Numbers opening weekend (US, USD),
  CPI to 2025 by release year (same CPI table and rule as `derive/money.py`).
- `theaters`: `theaters_max`. `legs`: The Numbers value. `video_usd2025`: total
  estimated US home-video sales, CPI to 2025.
- These five come only from a film's matched The Numbers metrics row
  (`films.numbers_key` starting `metrics:`). `numbers_fuzzy` is true when that
  match is fuzzy and at least one of them is present.
- `oscar_wins`, `oscar_noms`: from `wikidata_extra`. `oscar_noms` counts
  nomination statements, per category at least the win statements, so it is
  ≥ `oscar_wins` (D33). A film with a
  QID but no Academy Award statements gets 0; a film without a QID gets null.
- Detail text: `overview`, `cast`, `writers`, `companies` (first 3), `qid`,
  `csfd_id`, `filmaffinity_id`, `allocine_id`, `douban_id`. Lists are joined
  with `", "`; several ids keep the first after sorting.

## 3. Export

`films.pack` gains, per row: `story_source`, `story_source_src`, `age_rating`,
`studio` (dict columns, null 255), `opening_usd`, `opening_usd2025`, `legs`,
`video_usd2025` (f32), `theaters` (u16, null 65535), `oscar_wins`,
`oscar_noms` (u8, null 255), and flag bit 5 `numbers_fuzzy`.

Dict value orders (the app relies on them):
- story_source: `original, book, comic, true_story, stage, screen, other`
- story_source_src: `numbers, tmdb`
- age_rating: `G, PG, PG-13, R, NC-17, NR`
- studio: `disney, warner, universal, sony, paramount, fox, lionsgate, mgm, independent`

`films_detail_{k}.pack`, k = 0…⌈notable / 1000⌉ − 1, holds rows
`[1000k, 1000k + 1000)` of the notable films only, with string columns
`overview, cast, writers, companies, qid, csfd_id, filmaffinity_id,
allocine_id, douban_id`. The app fetches one shard when a card first shows a
film from it. `meta.json` gains `detail: {shard_size: 1000, shards: n}`,
counts `with_opening`, `with_story_source`, `with_oscars`, and notes for every
new transformed value (CPI on opening weekend and video sales, video sales are
estimates, story source from keywords, studio groups, Oscar counts from
Wikidata).

The data size budget goes from 8 to 12 MB (D33): the first load is unchanged,
the shards are fetched one at a time.

## 4. App

- **Measures** (`lib/measures.ts`): `opening` (opening weekend, US, log,
  follows the money toggle), `theaters` (widest release, theatres, linear),
  `legs` (domestic gross ÷ opening weekend, ×, log), `oscar_noms` (Oscar
  nominations, count, linear). They appear in the scatter axis and size
  selects and as table columns, like every measure.
- **Filters** (store, hash, `lib/filter.ts`, filter bar): `story`
  (`any` or one of the seven categories; hash `st`) and `studio` (`any`,
  `major`, `independent`; hash `stu`). A film with a null value fails any
  filter other than `any`. They filter the same views `genreOnly` filters.
- **Film card**: a "release" group (age rating, story source with "(from TMDB
  keywords)" when `story_source_src` is `tmdb`, studio, opening weekend with
  the money badges plus "US only", widest release, legs, home video with an
  "estimate" badge, Oscars "N wins of M nominations (Wikidata)"), and for
  notable films an "about" group from the detail shard: overview, cast,
  writers, companies, links to Wikidata, ČSFD, FilmAffinity, AlloCiné and
  Douban when the id exists.

## 5. Not done

Wikidata series order (P179/P1545), `based on` (P144), fine genres and
per-territory box office: the franchise view keeps TMDB collections and the
map keeps its three sources. The downloads in the second table of
`dataset-candidates.md` stay candidates.
