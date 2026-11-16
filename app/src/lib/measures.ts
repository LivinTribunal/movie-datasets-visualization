import type { Films } from './types'

export type MeasureKey =
  | 'tomatometer' | 'metascore' | 'audience' | 'imdb' | 'mc_user' | 'letterboxd' | 'tmdb'
  | 'gap' | 'budget' | 'revenue' | 'roi' | 'votes' | 'year' | 'runtime'

export type Money = 'usd2025' | 'nominal'

export interface Measure {
  label: string
  unit: string
  scale: 'linear' | 'log'
  domain?: [number, number]
}

export const MEASURES: Record<MeasureKey, Measure> = {
  tomatometer: { label: 'critics (Tomatometer)', unit: '0–100', scale: 'linear', domain: [0, 100] },
  metascore: { label: 'critics (Metascore)', unit: '0–100', scale: 'linear' },
  audience: { label: 'audience (Rotten Tomatoes)', unit: '0–100', scale: 'linear' },
  imdb: { label: 'IMDb rating', unit: '0–100', scale: 'linear' },
  mc_user: { label: 'Metacritic users', unit: '0–100', scale: 'linear' },
  letterboxd: { label: 'Letterboxd', unit: '0–100', scale: 'linear' },
  tmdb: { label: 'TMDB rating', unit: '0–100', scale: 'linear' },
  gap: { label: 'gap, audience − critics', unit: 'points', scale: 'linear', domain: [-100, 100] },
  budget: { label: 'budget', unit: '2025 USD or nominal USD', scale: 'log' },
  revenue: { label: 'box office', unit: '2025 USD or nominal USD', scale: 'log' },
  roi: { label: 'ROI, box office ÷ budget', unit: '×', scale: 'log' },
  votes: { label: 'IMDb votes', unit: 'count', scale: 'log' },
  year: { label: 'release year', unit: 'year', scale: 'linear' },
  runtime: { label: 'runtime', unit: 'minutes', scale: 'linear' },
}

export const MEASURE_KEYS = Object.keys(MEASURES) as MeasureKey[]

type NumColumn = { [K in keyof Films]: Films[K] extends Float64Array ? K : never }[keyof Films]

const COLUMN: Record<Exclude<MeasureKey, 'budget' | 'revenue'>, NumColumn> = {
  tomatometer: 'tomatometer_100',
  metascore: 'metascore_100',
  audience: 'audience_100',
  imdb: 'imdb_100',
  mc_user: 'mc_user_100',
  letterboxd: 'letterboxd_100',
  tmdb: 'tmdb_100',
  gap: 'gap',
  roi: 'roi',
  votes: 'imdb_votes',
  year: 'year',
  runtime: 'runtime',
}

export function measureColumn(films: Films, key: MeasureKey, money: Money): Float64Array {
  if (key === 'budget') return money === 'usd2025' ? films.budget_usd2025 : films.budget_usd
  if (key === 'revenue') return money === 'usd2025' ? films.revenue_usd2025 : films.revenue_usd
  return films[COLUMN[key]]
}

export function axisLabel(key: MeasureKey, money: Money): string {
  const { label, unit, scale } = MEASURES[key]
  const u = key === 'budget' || key === 'revenue' ? (money === 'usd2025' ? '2025 USD' : 'nominal USD') : unit
  return `${label} (${u}${scale === 'log' ? ', log' : ''})`
}

/** The seven 0–100 scores. */
export function isScore(key: MeasureKey): boolean {
  return MEASURES[key].unit === '0–100'
}

export const PRESETS: { label: string; x: MeasureKey; y: MeasureKey }[] = [
  { label: 'critics vs audience', x: 'tomatometer', y: 'audience' },
  { label: 'revenue vs critics', x: 'revenue', y: 'tomatometer' },
  { label: 'budget vs rating', x: 'budget', y: 'imdb' },
  { label: 'ROI', x: 'budget', y: 'roi' },
]
