import { describe, expect, it } from 'vitest'
import { domesticShares } from './domestic'
import type { CountryDomestic } from './types'

const values = ['CZ', 'DE']
const d = {
  rows: 5,
  country: { codes: Uint8Array.from([0, 0, 0, 1, 1]), values, nullCode: 255 },
  year: Uint16Array.from([2005, 2006, 2007, 2005, 2006]),
  admissions: Float64Array.from([10, 90, 100, 50, 50]),
  national: Float64Array.from([5, 9, 80, 5, 5]),
} as unknown as CountryDomestic

describe('domesticShares', () => {
  it('sums over the range, not a mean of yearly shares', () => {
    const cz = domesticShares(d, [2005, 2006]).get('CZ')
    expect(cz?.share).toBeCloseTo(14 / 100)
    expect(cz?.admissions).toBe(100)
  })

  it('ignores rows outside the range and counts rows as years', () => {
    const m = domesticShares(d, [2006, 2007])
    expect(m.get('CZ')).toMatchObject({ years: 2 })
    expect(m.get('CZ')?.share).toBeCloseTo(89 / 190)
    expect(m.get('DE')?.years).toBe(1)
  })

  it('drops a country with rows only outside the range', () => {
    const m = domesticShares(d, [2007, 2008])
    expect(m.has('DE')).toBe(false)
    expect(m.has('CZ')).toBe(true)
  })
})
