# Candidate datasets (researched 2026-11-16)

Shortlist from three research passes (country coverage, money and ratings,
franchises and context). Nothing here is acquired yet; add a row to
`DATASETS.md` and an entry in `decisions.md` when one is. "Local" means the
raw file is already in `data/raw/` and only the pipeline has to read more
columns.

## Take first (no download, no new licence)

| Source | Adds | Join | Note |
|---|---|---|---|
| TMDB+IMDb Kaggle file, unused columns (local) | keywords (96 % of notable films; "sequel", "remake", "based on novel or book"), US age rating (69 %), production companies (99.5 %), cast, writers, overview | `imdb_id` | keywords are user-entered; major vs independent needs a hand-made reference CSV |
| The Numbers metrics, unused columns (local) | opening weekend, theatre counts, legs, estimated home-video sales; `Source` (original, book, comic, real events…), `Creative Type`, `Production Method`, `Franchise` | existing title ±1 year match (D14) | about 6.5k films, the ones with money; video sales are estimates and must say so |
| Wikidata, more properties on the crosswalk query | series order (P179 + P1545), follows/followed by (P155/P156), based on (P144), fine genres (P136), awards (P166, P1411), per-territory box office (P2142 + P3005), ids for ČSFD, FilmAffinity, AlloCiné, Douban | QID | CC0; count each property first, coverage is the unknown |

## Worth a download

| Source | Adds | Join | Access, licence | Risk |
|---|---|---|---|---|
| Wikimedia per-country pageviews (`country_project_page`) | interest per reader country for every region, 2015 onwards; a proxy, not viewing | Wikidata QID | static daily files, about 20 MB a day | noise and release thresholds drop small countries; must be labelled "Wikipedia interest" |
| KOBIS open API (KOFIC, South Korea) | admissions and gross per film, daily and weekly | KOBIS code, then title + year | free key | Korean-title matching |
| ANCINE open data (Brazil), INCAA (Argentina) | admissions and gross per film | original title + year | bulk files, open government data | years and columns not confirmed |
| DLu/oscar_data | Oscar nominations and wins per film | IMDb id | one CSV, BSD-2 | US-centric |
| OMDb API | Metascore and Tomatometer for films with no Wikidata RT/Metacritic id | IMDb id | free key, 1,000 requests a day, CC BY-NC | about 4 days for the notable gaps; take scores only, not its box office (D16) |
| MovieLens 32M | a fourth audience score, 87k films to 2023 | IMDb and TMDB ids | 239 MB zip, research use | commit only per-film mean and count; ask about redistribution |
| TMDB API (`release_dates`, `credits`, `watch/providers`) | release dates and type per country, person ids and gender, current streaming availability | TMDB id | existing key | 56k calls is about 16 hours; breaks the fixed snapshot unless decided |
| Netflix "What We Watched" report | hours viewed for the whole catalogue, global only, half-yearly from 2023 | title + year fuzzy | xlsx on the page | needs the Netflix title matcher |

## Looked at and dropped

Box Office Mojo (D16) · FlixPatrol and OpusData (paid) · JustWatch charts
(access by request form only) · uNoGS (capped) · ČSFD (bot protection) ·
Douban (no dump with IMDb ids) · Bechdel test (API returns 410) · UNESCO UIS
(country totals only, stale) · Maoyan/EntGroup (commercial) · Google Trends
(API is application-only) · BFI and CNC (LUMIERE already covers them) ·
CinemaScore (no bulk file).
