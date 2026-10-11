// Mirrors SCHEMA in pipeline/src/movies/validate/app.py. Keep in sync.

export type Columnar<T> = { columns: { [K in keyof T]: T[K][] } }

export type MoneySrc = 'numbers' | 'tmdb' | 'wikidata'

export interface FilmRow {
  imdb_id: string
  tmdb_id: number | null
  title: string
  year: number | null
  notable: boolean
  genres: string[]
  families: string[]
  countries: string[]
  imdb_votes: number | null
  budget_usd2025: number | null
  revenue_usd2025: number | null
  budget_src: MoneySrc | null
  revenue_src: MoneySrc | null
  budget_converted: boolean
  revenue_converted: boolean
  budget_disagree: boolean
  revenue_disagree: boolean
  money_fuzzy: boolean
  roi: number | null
  imdb_100: number | null
  tmdb_100: number | null
  tomatometer_100: number | null
  audience_100: number | null
  metascore_100: number | null
  mc_user_100: number | null
  letterboxd_100: number | null
  gap: number | null
}

export interface GenreYearRow {
  subset: 'notable' | 'working'
  year: number
  genre: string
  family: string
  films: number
  votes: number | null
  revenue_usd2025: number | null
  revenue_films: number | null
}

export interface CountryGenreRow {
  source: string
  country_iso2: string
  year: number | null
  genre: string
  family: string
  share: number | null
  score: number | null
  coverage: number | null
  fuzzy_share: number | null
}

export interface CountryRow {
  iso2: string
  iso_numeric: string | null
  name: string
  region: string | null
  subregion: string | null
}

export interface GenreFamilyRow {
  genre: string
  family: string
  family_order: number
  colour: string
}

export interface FranchiseRow {
  collection_id: number
  collection_name: string
  installment: number
  n_released: number
  tmdb_id: number
  imdb_id: string | null
  title: string
  year: number
  imdb_100: number | null
  imdb_100_vs_prev: number | null
  imdb_100_vs_first: number | null
  tomatometer_100: number | null
  audience_100: number | null
  revenue_usd2025: number | null
  revenue_vs_prev: number | null
  revenue_vs_first: number | null
}

export interface Meta {
  snapshots: Record<string, string>
  base_year: number
  counts: Record<string, number>
  notes: string[]
}

export interface AppData {
  films: Columnar<FilmRow>
  genreYear: Columnar<GenreYearRow>
  countryGenre: Columnar<CountryGenreRow>
  countries: Columnar<CountryRow>
  genreFamilies: Columnar<GenreFamilyRow>
  franchises: Columnar<FranchiseRow>
  topo: unknown
  meta: Meta
}
