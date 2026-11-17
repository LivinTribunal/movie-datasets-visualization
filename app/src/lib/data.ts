import { useEffect, useState } from 'react'
import { fetchPack, type Pack } from './pack'
import type {
  AppData, Country, CountryDomestic, CountryGenre, CountryYear, Family, Films, FilmsDetail, FilmsText, Franchises, ImdbGenreYear, Meta,
} from './types'

async function fetchJson<T>(file: string): Promise<T> {
  const res = await fetch(`data/${file}`)
  if (!res.ok) throw new Error(`Could not load data/${file}: HTTP ${res.status}`)
  return (await res.json()) as T
}

type Columnar<T> = { columns: { [K in keyof T]: T[K][] } }

interface GenreFamilyRow { genre: string; family: string; family_order: number; colour: string }

function buildFilms(p: Pack): Films {
  return {
    rows: p.rows,
    notable: p.meta.notable as number,
    genres: p.meta.genres as string[],
    families: p.meta.families as string[],
    imdb: p.raw('imdb') as Uint32Array,
    tmdb_id: p.num('tmdb_id'),
    year: p.num('year'),
    runtime: p.num('runtime'),
    imdb_votes: p.num('imdb_votes'),
    genre_mask: p.raw('genre_mask') as Uint32Array,
    family_mask: p.raw('family_mask') as Uint8Array,
    countries: p.list('countries'),
    budget_usd: p.num('budget_usd'),
    budget_usd2025: p.num('budget_usd2025'),
    revenue_usd: p.num('revenue_usd'),
    revenue_usd2025: p.num('revenue_usd2025'),
    roi: p.num('roi'),
    budget_src: p.dict('budget_src'),
    revenue_src: p.dict('revenue_src'),
    flags: p.raw('flags') as Uint8Array,
    story_source: p.dict('story_source'),
    story_source_src: p.dict('story_source_src'),
    age_rating: p.dict('age_rating'),
    studio: p.dict('studio'),
    opening_usd: p.num('opening_usd'),
    opening_usd2025: p.num('opening_usd2025'),
    legs: p.num('legs'),
    video_usd2025: p.num('video_usd2025'),
    theaters: p.num('theaters'),
    oscar_wins: p.num('oscar_wins'),
    oscar_noms: p.num('oscar_noms'),
    imdb_100: p.num('imdb_100'),
    tmdb_100: p.num('tmdb_100'),
    tomatometer_100: p.num('tomatometer_100'),
    audience_100: p.num('audience_100'),
    metascore_100: p.num('metascore_100'),
    mc_user_100: p.num('mc_user_100'),
    letterboxd_100: p.num('letterboxd_100'),
    gap: p.num('gap'),
    mc_critic_reviews: p.num('mc_critic_reviews'),
    collection_id: p.num('collection_id'),
    installment: p.num('installment'),
  }
}

function buildFilmsText(p: Pack): FilmsText {
  return { rows: p.rows, title: p.str('title'), director: p.str('director') }
}

function buildFilmsDetail(p: Pack): FilmsDetail {
  return {
    rows: p.rows,
    overview: p.str('overview'),
    cast: p.str('cast'),
    writers: p.str('writers'),
    companies: p.str('companies'),
    qid: p.str('qid'),
    csfd_id: p.str('csfd_id'),
    filmaffinity_id: p.str('filmaffinity_id'),
    allocine_id: p.str('allocine_id'),
    douban_id: p.str('douban_id'),
  }
}

function buildCountryGenre(p: Pack): CountryGenre {
  return {
    rows: p.rows,
    source: p.dict('source'),
    country: p.dict('country'),
    year: p.raw('year') as Uint16Array,
    genre: p.raw('genre') as Uint8Array,
    score: p.num('score'),
  }
}

function buildCountryDomestic(p: Pack): CountryDomestic {
  return {
    rows: p.rows,
    country: p.dict('country'),
    year: p.raw('year') as Uint16Array,
    admissions: p.num('admissions'),
    national: p.num('national'),
  }
}

function buildImdbGenreYear(p: Pack): ImdbGenreYear {
  return {
    rows: p.rows,
    year: p.raw('year') as Uint16Array,
    genre: p.raw('genre') as Uint8Array,
    score: p.num('score'),
    entries: p.num('entries'),
    shorts: p.num('shorts'),
  }
}

function buildCountryYear(p: Pack): CountryYear {
  return {
    rows: p.rows,
    source: p.dict('source'),
    country: p.dict('country'),
    year: p.raw('year') as Uint16Array,
    entries: p.num('entries'),
    coverage: p.num('coverage'),
    fuzzy_share: p.num('fuzzy_share'),
    estimated_share: p.num('estimated_share'),
    measure: p.dict('measure'),
  }
}

function buildFranchises(p: Pack): Franchises {
  return {
    rows: p.rows,
    collection_id: p.num('collection_id'),
    installment: p.num('installment'),
    n_released: p.num('n_released'),
    tmdb_id: p.num('tmdb_id'),
    film_row: p.num('film_row'),
    year: p.num('year'),
    family_mask: p.raw('family_mask') as Uint8Array,
    imdb_100: p.num('imdb_100'),
    tomatometer_100: p.num('tomatometer_100'),
    audience_100: p.num('audience_100'),
    imdb_100_vs_first: p.num('imdb_100_vs_first'),
    revenue_usd2025: p.num('revenue_usd2025'),
    revenue_vs_first: p.num('revenue_vs_first'),
    title: p.str('title'),
    collections: new Map(p.meta.collections as [number, string][]),
  }
}

function buildCountries(c: Columnar<Country>): Country[] {
  const { iso2, iso_numeric, name, region, subregion } = c.columns
  return iso2.map((code, i) => ({
    iso2: code, iso_numeric: iso_numeric[i], name: name[i], region: region[i], subregion: subregion[i],
  }))
}

/** Families in family_order; array index = bit in family_mask. */
function buildFamilies(gf: Columnar<GenreFamilyRow>): Family[] {
  const { genre, family, family_order, colour } = gf.columns
  const byName = new Map<string, { order: number; family: Family }>()
  family.forEach((name, i) => {
    let entry = byName.get(name)
    if (!entry) {
      entry = { order: family_order[i], family: { name, colour: colour[i], genres: [] } }
      byName.set(name, entry)
    }
    entry.family.genres.push(genre[i])
  })
  return [...byName.values()].sort((a, b) => a.order - b.order).map((e) => e.family)
}

export async function loadData(): Promise<AppData> {
  const [films, countryGenre, countryYear, countryDomestic, imdbGenreYear, franchises, countries, genreFamilies, meta] = await Promise.all([
    fetchPack('data/films.pack'),
    fetchPack('data/country_genre.pack'),
    fetchPack('data/country_year.pack'),
    fetchPack('data/country_domestic.pack'),
    fetchPack('data/imdb_genre_year.pack'),
    fetchPack('data/franchises.pack'),
    fetchJson<Columnar<Country>>('countries.json'),
    fetchJson<Columnar<GenreFamilyRow>>('genre_families.json'),
    fetchJson<Meta>('meta.json'),
  ])
  const countryList = buildCountries(countries)
  const filmTable = buildFilms(films)
  const families = buildFamilies(genreFamilies)
  return {
    films: filmTable,
    countryGenre: buildCountryGenre(countryGenre),
    countryYear: buildCountryYear(countryYear),
    countryDomestic: buildCountryDomestic(countryDomestic),
    imdbGenreYear: buildImdbGenreYear(imdbGenreYear),
    franchises: buildFranchises(franchises),
    countries: countryList,
    countryByIso2: new Map(countryList.map((c) => [c.iso2, c])),
    families,
    genreFamily: Uint8Array.from(filmTable.genres, (g) => families.findIndex((f) => f.genres.includes(g))),
    meta,
  }
}

let textPromise: Promise<FilmsText> | null = null
let topoPromise: Promise<unknown> | null = null
let posterPromise: Promise<(string | null)[]> | null = null

export function loadText(): Promise<FilmsText> {
  textPromise ??= fetchPack('data/films_text.pack').then(buildFilmsText)
  return textPromise
}

/** TMDB poster paths, same rows as Films (films_poster.pack). */
export function loadPosters(): Promise<(string | null)[]> {
  posterPromise ??= fetchPack('data/films_poster.pack').then((p) => p.str('poster'))
  return posterPromise
}

const detailShards = new Map<number, Promise<FilmsDetail>>()

/** The detail shard that holds a notable film row, and the row's index inside it. Null for rows outside the shards. */
export async function loadDetail(row: number, meta: Meta): Promise<{ shard: FilmsDetail; index: number } | null> {
  const { shard_size, shards } = meta.detail
  if (row >= shards * shard_size) return null
  const k = Math.floor(row / shard_size)
  let promise = detailShards.get(k)
  if (!promise) {
    promise = fetchPack(`data/films_detail_${k}.pack`).then(buildFilmsDetail)
    detailShards.set(k, promise)
  }
  return { shard: await promise, index: row - k * shard_size }
}

export function loadTopo(): Promise<unknown> {
  topoPromise ??= fetchJson<unknown>('countries.topo.json')
  return topoPromise
}

/** Returns null until the promise resolves. Pass a stable loader such as loadText. */
export function useLazy<T>(load: () => Promise<T>): T | null {
  const [value, setValue] = useState<T | null>(null)
  useEffect(() => {
    let live = true
    load().then((v) => { if (live) setValue(v) }, () => { /* the panel shows its own empty state */ })
    return () => { live = false }
  }, [load])
  return value
}
