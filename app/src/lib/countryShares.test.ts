import { describe, expect, it } from 'vitest'
import { countryStats, share, shareDiff, THIN, topFamily, worldShares } from './countryShares'
import type { CountryGenre, CountryYear } from './types'

const dict = (values: string[], items: string[]) => ({
  codes: Uint8Array.from(items.map((s) => values.indexOf(s))),
  values,
  nullCode: 255,
})

// Genres 0,1 belong to family 0; genre 2 to family 1.
const genreFamily = Uint8Array.from([0, 0, 1])

const countryGenre = {
  rows: 6,
  source: dict(['netflix', 'cinema'], ['netflix', 'netflix', 'netflix', 'netflix', 'cinema', 'cinema']),
  country: dict(['CZ', 'DE', 'FR'], ['CZ', 'CZ', 'CZ', 'DE', 'CZ', 'FR']),
  year: Uint16Array.from([2021, 2022, 2022, 2021, 2021, 2021]),
  genre: Uint8Array.from([0, 1, 2, 0, 2, 0]),
  score: Float64Array.from([10, 20, 30, 5, 40, 8]),
} as unknown as CountryGenre

const countryYear = {
  rows: 4,
  source: dict(['netflix', 'cinema'], ['netflix', 'netflix', 'netflix', 'cinema']),
  country: dict(['CZ', 'DE', 'FR'], ['CZ', 'CZ', 'DE', 'CZ']),
  year: Uint16Array.from([2021, 2022, 2021, 2021]),
  entries: Float64Array.from([10, 30, 5, 50]),
  coverage: Float64Array.from([1, 1, 1, 1]),
  fuzzy_share: Float64Array.from([0, 0.4, 0, 0]),
  estimated_share: Float64Array.from([0, 0, 0, 0]),
  measure: dict(['count', 'admissions'], ['count', 'count', 'count', 'admissions']),
} as unknown as CountryYear

const stats = (source: 'netflix' | 'cinema', range: [number, number]) =>
  countryStats(countryGenre, countryYear, genreFamily, 2, source, range)

describe('countryStats', () => {
  it('sums scores per family over the year range, for one source only', () => {
    const cz = stats('netflix', [2021, 2022]).get('CZ')!
    expect(Array.from(cz.byFamily)).toEqual([30, 30])
    expect(cz.total).toBe(60)
    expect(Array.from(stats('netflix', [2022, 2022]).get('CZ')!.byFamily)).toEqual([20, 30])
  })
  it('leaves out countries without rows in the window', () => {
    expect(stats('netflix', [2022, 2022]).has('DE')).toBe(false)
    expect(stats('netflix', [2021, 2021]).has('FR')).toBe(false)
    expect(stats('netflix', [2000, 2010]).size).toBe(0)
  })
  it('sums entries and weights fuzzy by entries', () => {
    const cz = stats('netflix', [2021, 2022]).get('CZ')!
    expect(cz.entries).toBe(40)
    expect(cz.fuzzy).toBeCloseTo((30 * 0.4) / 40)
    expect(cz.years).toEqual([2021, 2022])
    expect(cz.entries >= THIN).toBe(true)
  })
})

describe('share helpers', () => {
  it('share and topFamily', () => {
    const cz = stats('netflix', [2022, 2022]).get('CZ')!
    expect(share(cz, 0)).toBeCloseTo(0.4)
    expect(topFamily(cz)).toBe(1)
  })
  it('worldShares sums scores of all countries', () => {
    const w = worldShares(stats('netflix', [2021, 2022]), 2)
    expect(w[0]).toBeCloseTo(35 / 65)
    expect(w[1]).toBeCloseTo(30 / 65)
  })
  it('shareDiff keeps countries in both sources, cinema minus netflix', () => {
    const d = shareDiff(stats('cinema', [2021, 2021]), stats('netflix', [2021, 2021]), 1)
    expect([...d.keys()]).toEqual(['CZ'])
    expect(d.get('CZ')).toBeCloseTo(1)
  })
})
