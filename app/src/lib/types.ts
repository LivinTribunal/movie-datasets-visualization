// Mirrors the packs written by `movies export` (app design spec §2). Property names are pack column names.

import type { DictColumn, ListColumn } from './pack'

export type MoneySrc = 'numbers' | 'tmdb' | 'wikidata' | 'wikipedia'

/** films.pack. Row index = film handle; rows `< notable` are the notable subset. */
export interface Films {
  rows: number
  notable: number
  /** Genre names; bit i of genre_mask. */
  genres: string[]
  /** Family names in family_order; bit i of family_mask. */
  families: string[]
  imdb: Uint32Array
  tmdb_id: Float64Array
  year: Float64Array
  runtime: Float64Array
  imdb_votes: Float64Array
  genre_mask: Uint32Array
  family_mask: Uint8Array
  countries: ListColumn
  budget_usd: Float64Array
  budget_usd2025: Float64Array
  revenue_usd: Float64Array
  revenue_usd2025: Float64Array
  roi: Float64Array
  budget_src: DictColumn
  revenue_src: DictColumn
  /** Bits: 0 budget converted, 1 revenue converted, 2 budget sources disagree, 3 revenue sources disagree, 4 fuzzy money match, 5 numbers_fuzzy (opening, theatres, legs, video: fuzzy title match). */
  flags: Uint8Array
  /** Dict order: original, book, comic, true_story, stage, screen, other. */
  story_source: DictColumn
  /** numbers | tmdb */
  story_source_src: DictColumn
  /** G, PG, PG-13, R, NC-17, NR */
  age_rating: DictColumn
  /** disney, warner, universal, sony, paramount, fox, lionsgate, mgm, independent */
  studio: DictColumn
  opening_usd: Float64Array
  opening_usd2025: Float64Array
  /** US gross ÷ opening weekend. */
  legs: Float64Array
  video_usd2025: Float64Array
  theaters: Float64Array
  oscar_wins: Float64Array
  oscar_noms: Float64Array
  imdb_100: Float64Array
  tmdb_100: Float64Array
  tomatometer_100: Float64Array
  audience_100: Float64Array
  metascore_100: Float64Array
  mc_user_100: Float64Array
  letterboxd_100: Float64Array
  gap: Float64Array
  mc_critic_reviews: Float64Array
  /** NaN when the film is not part of an exported franchise. */
  collection_id: Float64Array
  installment: Float64Array
}

/** One films_detail_{k}.pack shard: notable rows [shard_size * k, shard_size * (k + 1)). */
export interface FilmsDetail {
  rows: number
  overview: (string | null)[]
  cast: (string | null)[]
  writers: (string | null)[]
  companies: (string | null)[]
  qid: (string | null)[]
  csfd_id: (string | null)[]
  filmaffinity_id: (string | null)[]
  allocine_id: (string | null)[]
  douban_id: (string | null)[]
}

/** films_text.pack, same rows as Films. */
export interface FilmsText {
  rows: number
  title: (string | null)[]
  director: (string | null)[]
}

export interface CountryGenre {
  rows: number
  source: DictColumn
  country: DictColumn
  year: Uint16Array
  /** Index into Films.genres. */
  genre: Uint8Array
  score: Float64Array
}

export interface CountryYear {
  rows: number
  source: DictColumn
  country: DictColumn
  year: Uint16Array
  entries: Float64Array
  coverage: Float64Array
  fuzzy_share: Float64Array
  estimated_share: Float64Array
  measure: DictColumn
}

export interface Franchises {
  rows: number
  collection_id: Float64Array
  installment: Float64Array
  n_released: Float64Array
  tmdb_id: Float64Array
  /** NaN when the part is not in films.pack. */
  film_row: Float64Array
  year: Float64Array
  family_mask: Uint8Array
  imdb_100: Float64Array
  tomatometer_100: Float64Array
  audience_100: Float64Array
  imdb_100_vs_first: Float64Array
  revenue_usd2025: Float64Array
  revenue_vs_first: Float64Array
  title: (string | null)[]
  collections: Map<number, string>
}

export interface Country {
  iso2: string
  iso_numeric: string | null
  name: string
  region: string | null
  subregion: string | null
}

/** Array index in AppData.families = bit in Films.family_mask. */
export interface Family {
  name: string
  colour: string
  genres: string[]
}

export interface Meta {
  snapshots: Record<string, string>
  base_year: number
  counts: Record<string, number>
  notes: string[]
  attribution: string[]
  sources: Record<string, string>
  detail: { shard_size: number; shards: number }
}

export interface AppData {
  films: Films
  countryGenre: CountryGenre
  countryYear: CountryYear
  franchises: Franchises
  countries: Country[]
  countryByIso2: Map<string, Country>
  families: Family[]
  /** For each genre index (Films.genres), the index of its family in `families`. */
  genreFamily: Uint8Array
  meta: Meta
}
