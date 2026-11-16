import { memoLast } from './memo'
import type { CountryGenre, CountryYear } from './types'
import type { Source } from '../state/store'

export const THIN = 30

export interface CountryStat {
  iso2: string
  total: number
  byFamily: Float64Array
  entries: number
  fuzzy: number
  estimated: number
  coverage: number
  measure: string | null
  years: [number, number]
}

interface Acc {
  stat: CountryStat
  fuzzy: number
  estimated: number
  coverage: number
}

const dictAt = (col: { codes: ArrayLike<number>; values: string[] }, i: number): string => col.values[col.codes[i]]

/** Scores summed per family over the rows of one source inside the year range. */
export const countryStats = memoLast(
  (
    countryGenre: CountryGenre,
    countryYear: CountryYear,
    genreFamily: Uint8Array,
    nFamilies: number,
    source: Source,
    yearRange: [number, number],
  ): Map<string, CountryStat> => {
    const [from, to] = yearRange
    const accs = new Map<string, Acc>()
    const acc = (iso2: string, year: number): Acc => {
      let a = accs.get(iso2)
      if (!a) {
        a = {
          stat: {
            iso2, total: 0, byFamily: new Float64Array(nFamilies), entries: 0, fuzzy: 0, estimated: 0, coverage: 0,
            measure: null, years: [year, year],
          },
          fuzzy: 0, estimated: 0, coverage: 0,
        }
        accs.set(iso2, a)
      }
      a.stat.years = [Math.min(a.stat.years[0], year), Math.max(a.stat.years[1], year)]
      return a
    }
    for (let i = 0; i < countryYear.rows; i++) {
      const year = countryYear.year[i]
      if (year < from || year > to || dictAt(countryYear.source, i) !== source) continue
      const a = acc(dictAt(countryYear.country, i), year)
      const entries = countryYear.entries[i]
      if (!Number.isNaN(entries)) {
        a.stat.entries += entries
        a.fuzzy += entries * (countryYear.fuzzy_share[i] || 0)
        a.estimated += entries * (countryYear.estimated_share[i] || 0)
        a.coverage += entries * (countryYear.coverage[i] || 0)
      }
      a.stat.measure ??= dictAt(countryYear.measure, i)
    }
    for (let i = 0; i < countryGenre.rows; i++) {
      const year = countryGenre.year[i]
      if (year < from || year > to || dictAt(countryGenre.source, i) !== source) continue
      const score = countryGenre.score[i]
      if (Number.isNaN(score)) continue
      const a = acc(dictAt(countryGenre.country, i), year)
      a.stat.byFamily[genreFamily[countryGenre.genre[i]]] += score
      a.stat.total += score
    }
    const out = new Map<string, CountryStat>()
    for (const [iso2, a] of accs) {
      const e = a.stat.entries
      a.stat.fuzzy = e > 0 ? a.fuzzy / e : 0
      a.stat.estimated = e > 0 ? a.estimated / e : 0
      a.stat.coverage = e > 0 ? a.coverage / e : 0
      out.set(iso2, a.stat)
    }
    return out
  },
)

export const share = (stat: CountryStat, family: number): number =>
  stat.total > 0 ? stat.byFamily[family] / stat.total : NaN

export function topFamily(stat: CountryStat): number {
  let best = 0
  stat.byFamily.forEach((v, i) => {
    if (v > stat.byFamily[best]) best = i
  })
  return best
}

export function worldShares(stats: Map<string, CountryStat>, nFamilies: number): Float64Array {
  const sums = new Float64Array(nFamilies)
  let total = 0
  for (const s of stats.values()) {
    sums.forEach((_, i) => { sums[i] += s.byFamily[i] })
    total += s.total
  }
  return total > 0 ? sums.map((v) => v / total) : sums.fill(NaN)
}

/** Cinema share minus Netflix share, for countries present in both. */
export function shareDiff(
  cinema: Map<string, CountryStat>,
  netflix: Map<string, CountryStat>,
  family: number,
): Map<string, number> {
  const out = new Map<string, number>()
  for (const [iso2, c] of cinema) {
    const n = netflix.get(iso2)
    if (!n) continue
    const d = share(c, family) - share(n, family)
    if (!Number.isNaN(d)) out.set(iso2, d)
  }
  return out
}
