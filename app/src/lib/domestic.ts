import { memoLast } from './memo'
import type { CountryDomestic } from './types'

export interface DomesticStat {
  share: number
  admissions: number
  years: number
}

/** Σ national / Σ admissions per country over the rows inside the year range (inclusive). */
export const domesticShares = memoLast(
  (d: CountryDomestic, yearRange: [number, number]): Map<string, DomesticStat> => {
    const [from, to] = yearRange
    const acc = new Map<string, { admissions: number; national: number; years: number }>()
    for (let i = 0; i < d.rows; i++) {
      const year = d.year[i]
      if (year < from || year > to) continue
      const iso2 = d.country.values[d.country.codes[i]]
      const a = acc.get(iso2) ?? { admissions: 0, national: 0, years: 0 }
      a.admissions += d.admissions[i]
      a.national += d.national[i]
      a.years += 1
      acc.set(iso2, a)
    }
    const out = new Map<string, DomesticStat>()
    for (const [iso2, a] of acc) {
      if (a.admissions > 0) out.set(iso2, { share: a.national / a.admissions, admissions: a.admissions, years: a.years })
    }
    return out
  },
)
