import type {
  AppData, Columnar, CountryGenreRow, CountryRow, FilmRow, GenreFamilyRow, GenreYearRow, Meta,
} from './types'

async function fetchJson<T>(file: string): Promise<T> {
  const res = await fetch(`data/${file}`)
  if (!res.ok) throw new Error(`Could not load data/${file}: HTTP ${res.status}`)
  return (await res.json()) as T
}

export async function loadData(): Promise<AppData> {
  const [films, genreYear, countryGenre, countries, genreFamilies, topo, meta] = await Promise.all([
    fetchJson<Columnar<FilmRow>>('films.json'),
    fetchJson<Columnar<GenreYearRow>>('genre_year.json'),
    fetchJson<Columnar<CountryGenreRow>>('country_genre.json'),
    fetchJson<Columnar<CountryRow>>('countries.json'),
    fetchJson<Columnar<GenreFamilyRow>>('genre_families.json'),
    fetchJson<unknown>('countries.topo.json'),
    fetchJson<Meta>('meta.json'),
  ])
  return { films, genreYear, countryGenre, countries, genreFamilies, topo, meta }
}
