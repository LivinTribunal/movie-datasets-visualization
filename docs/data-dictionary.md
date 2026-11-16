# Data dictionary: extra film columns (D33)

Columns added to `films.pack` by `movies derive extras` and `movies export`. Dict values keep the
order listed here; the app relies on it. Missing is null, never `0`.

| Column | Type | Meaning | Source |
|---|---|---|---|
| `story_source` | dict | `original, book, comic, true_story, stage, screen, other`; null when neither source says | The Numbers `Source`, else the first mapped TMDB keyword (`data/reference/story_sources.csv`) |
| `story_source_src` | dict | `numbers, tmdb` | as above |
| `age_rating` | dict | `G, PG, PG-13, R, NC-17, NR` | TMDB `certification_us`, else The Numbers MPAA rating (`Not Rated` is `NR`) |
| `studio` | dict | `disney, warner, universal, sony, paramount, fox, lionsgate, mgm, independent` | group of the first listed production company (`data/reference/studios.csv`); null without companies |
| `opening_usd`, `opening_usd2025` | f32 | US opening weekend, nominal and CPI-adjusted to 2025 USD | The Numbers metrics, matched films only |
| `legs` | f32 | domestic gross divided by opening weekend | The Numbers metrics |
| `video_usd2025` | f32 | estimated US home-video sales, CPI to 2025 USD | The Numbers metrics (an estimate) |
| `theaters` | u16 | widest US release, in theatres | The Numbers metrics |
| `oscar_wins`, `oscar_noms` | u8 | distinct Academy Award categories won, and nominated or won; 0 for a film with a Wikidata item and no statements, null without an item | Wikidata |
| flag bit 5 `numbers_fuzzy` | bit | the film's The Numbers metrics row is a fuzzy title match and gives at least one of the values above | |

`films_detail_{k}.pack` holds `overview, cast, writers, companies (first 3), qid, csfd_id,
filmaffinity_id, allocine_id, douban_id` as strings for rows `[1000k, 1000k + 1000)` of the notable
films. `meta.json` has `detail: {shard_size, shards}`.
