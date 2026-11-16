import { memoLast } from './memo'
import type { Money } from './measures'
import type { CountryGenre, CountryYear, Films } from './types'

export type FilmMeasure = 'films' | 'votes' | 'revenue'

export interface Timeline {
  years: number[]
  /** shares[f][i]: share of family f in years[i]; 0 when the year's total is 0. */
  shares: Float64Array[]
  totals: Float64Array
  /** Films (or Netflix entries) behind each year. */
  films: Float64Array
}

export const THIN = 30
const FIRST_YEAR = 1900
const LAST_YEAR = 2026

function emptySums(nYears: number, nFamilies: number): Float64Array[] {
  return Array.from({ length: nFamilies }, () => new Float64Array(nYears))
}

function toTimeline(years: number[], sums: Float64Array[], films: Float64Array): Timeline {
  const totals = new Float64Array(years.length)
  for (const s of sums) for (let i = 0; i < years.length; i++) totals[i] += s[i]
  const shares = sums.map((s) => {
    const out = new Float64Array(years.length)
    for (let i = 0; i < years.length; i++) out[i] = totals[i] > 0 ? s[i] / totals[i] : 0
    return out
  })
  return { years, shares, totals, films }
}

export const timelineFromFilms = memoLast(
  (
    films: Films,
    mask: Uint8Array,
    measure: FilmMeasure,
    money: Money,
    genreFamily: Uint8Array,
    nFamilies: number,
  ): Timeline => {
    const years = Array.from({ length: LAST_YEAR - FIRST_YEAR + 1 }, (_, i) => FIRST_YEAR + i)
    const sums = emptySums(years.length, nFamilies)
    const count = new Float64Array(years.length)
    const column =
      measure === 'votes' ? films.imdb_votes : money === 'usd2025' ? films.revenue_usd2025 : films.revenue_usd
    for (let r = 0; r < films.rows; r++) {
      if (!mask[r]) continue
      const yi = films.year[r] - FIRST_YEAR
      if (!(yi >= 0 && yi < years.length)) continue
      const bits = films.genre_mask[r]
      if (bits === 0) continue
      const value = measure === 'films' ? 1 : column[r]
      if (Number.isNaN(value)) continue
      let n = 0
      for (let g = 0; g < genreFamily.length; g++) n += (bits >>> g) & 1
      const part = value / n
      for (let g = 0; g < genreFamily.length; g++) {
        if ((bits >>> g) & 1) sums[genreFamily[g]][yi] += part
      }
      count[yi] += 1
    }
    return toTimeline(years, sums, count)
  },
)

export const timelineFromNetflix = memoLast(
  (
    countryGenre: CountryGenre,
    countryYear: CountryYear,
    genreFamily: Uint8Array,
    nFamilies: number,
    countries: string[],
  ): Timeline => {
    const netflixCode = (d: CountryGenre['source']) => d.values.indexOf('netflix')
    const cgCode = netflixCode(countryGenre.source)
    const cyCode = netflixCode(countryYear.source)
    const yearSet = new Set<number>()
    for (let i = 0; i < countryGenre.rows; i++) {
      if (countryGenre.source.codes[i] === cgCode) yearSet.add(countryGenre.year[i])
    }
    const years = [...yearSet].sort((a, b) => a - b)
    const at = new Map(years.map((y, i) => [y, i]))
    const keep = (c: string) => countries.length === 0 || countries.includes(c)
    const sums = emptySums(years.length, nFamilies)
    const entries = new Float64Array(years.length)
    for (let i = 0; i < countryGenre.rows; i++) {
      if (countryGenre.source.codes[i] !== cgCode) continue
      if (!keep(countryGenre.country.values[countryGenre.country.codes[i]])) continue
      const score = countryGenre.score[i]
      if (Number.isNaN(score)) continue
      const yi = at.get(countryGenre.year[i])
      if (yi === undefined) continue
      sums[genreFamily[countryGenre.genre[i]]][yi] += score
    }
    for (let i = 0; i < countryYear.rows; i++) {
      if (countryYear.source.codes[i] !== cyCode) continue
      if (!keep(countryYear.country.values[countryYear.country.codes[i]])) continue
      const yi = at.get(countryYear.year[i])
      if (yi === undefined || Number.isNaN(countryYear.entries[i])) continue
      entries[yi] += countryYear.entries[i]
    }
    return toTimeline(years, sums, entries)
  },
)

/** Family whose band holds stacked position y01 (0 = bottom, 1 = top) in the given year, or -1. */
export function familyAt(timeline: Timeline, yearIndex: number, y01: number): number {
  if (yearIndex < 0 || yearIndex >= timeline.years.length || !(y01 >= 0 && y01 <= 1)) return -1
  if (timeline.totals[yearIndex] <= 0) return -1
  let acc = 0
  let last = -1
  for (let f = 0; f < timeline.shares.length; f++) {
    const share = timeline.shares[f][yearIndex]
    if (share <= 0) continue
    last = f
    acc += share
    if (y01 < acc) return f
  }
  return last
}
