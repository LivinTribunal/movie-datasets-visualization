import type { MeasureKey, Money } from './measures'
import type { DictColumn } from './pack'
import type { Films } from './types'

export const SRC_LABEL: Record<string, string> = {
  numbers: 'The Numbers',
  tmdb: 'TMDB',
  wikidata: 'Wikidata',
  wikipedia: 'Wikipedia infobox',
}

export const SCORE_GROUPS: { title: string; keys: MeasureKey[] }[] = [
  { title: 'critics', keys: ['tomatometer', 'metascore'] },
  { title: 'audience', keys: ['audience', 'imdb', 'mc_user', 'letterboxd', 'tmdb'] },
]

export interface MoneyFact {
  value: number
  source: string | null
  converted: boolean
  disagree: boolean
}

export function filmGenres(films: Films, row: number): string[] {
  const mask = films.genre_mask[row]
  return films.genres.filter((_, i) => ((mask >>> i) & 1) === 1)
}

export function filmCountries(films: Films, row: number): string[] {
  const { offsets, codes, values } = films.countries
  return Array.from(codes.subarray(offsets[row], offsets[row + 1]), (c) => values[c])
}

const source = (col: DictColumn, row: number): string | null => {
  const code = col.codes[row]
  return code === col.nullCode ? null : col.values[code]
}

const bit = (films: Films, row: number, n: number) => ((films.flags[row] >>> n) & 1) === 1

export function moneyFacts(films: Films, row: number, money: Money) {
  const usd2025 = money === 'usd2025'
  const budget: MoneyFact = {
    value: (usd2025 ? films.budget_usd2025 : films.budget_usd)[row],
    source: source(films.budget_src, row),
    converted: bit(films, row, 0),
    disagree: bit(films, row, 2),
  }
  const revenue: MoneyFact = {
    value: (usd2025 ? films.revenue_usd2025 : films.revenue_usd)[row],
    source: source(films.revenue_src, row),
    converted: bit(films, row, 1),
    disagree: bit(films, row, 3),
  }
  return { budget, revenue, roi: films.roi[row] }
}

export const fuzzyMoney = (films: Films, row: number): boolean => bit(films, row, 4)

export const STORY_LABEL: Record<string, string> = {
  original: 'original screenplay',
  book: 'based on a book',
  comic: 'based on a comic',
  true_story: 'based on a true story',
  stage: 'based on a stage work',
  screen: 'based on a film or TV show',
  other: 'other source',
}

export const STUDIO_LABEL: Record<string, string> = {
  disney: 'Disney',
  warner: 'Warner Bros.',
  universal: 'Universal',
  sony: 'Sony',
  paramount: 'Paramount',
  fox: '20th Century Fox',
  lionsgate: 'Lionsgate',
  mgm: 'MGM',
  independent: 'independent',
}

/** The release facts that come from the extra sources; null / NaN when missing. */
export function releaseFacts(films: Films, row: number, money: Money) {
  return {
    age: source(films.age_rating, row),
    story: source(films.story_source, row),
    storySrc: source(films.story_source_src, row),
    studio: source(films.studio, row),
    opening: (money === 'usd2025' ? films.opening_usd2025 : films.opening_usd)[row],
    theaters: films.theaters[row],
    legs: films.legs[row],
    video: films.video_usd2025[row],
    wins: films.oscar_wins[row],
    noms: films.oscar_noms[row],
    fuzzy: bit(films, row, 5),
  }
}
