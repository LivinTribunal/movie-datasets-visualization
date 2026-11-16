import { describe, expect, it } from 'vitest'
import type { CountryGenre, CountryYear, Films } from './types'
import { familyAt, timelineFromFilms, timelineFromNetflix } from './timeline'

// Genres 0,1 -> family 0; genre 2 -> family 1. Years 1900.. so row year 1901 is index 1.
const genreFamily = Uint8Array.from([0, 0, 1])
const nan = Number.NaN
const films = {
  rows: 4,
  year: Float64Array.from([1900, 1900, 1901, 1901]),
  genre_mask: Uint32Array.from([0b101, 0b011, 0b100, 0b001]),
  imdb_votes: Float64Array.from([100, 50, 10, 30]),
  revenue_usd: Float64Array.from([10, nan, 4, 6]),
  revenue_usd2025: Float64Array.from([20, nan, 8, 12]),
} as unknown as Films
const all = Uint8Array.from([1, 1, 1, 1])
const build = (mask = all, measure: 'films' | 'votes' | 'revenue' = 'votes', money: 'usd2025' | 'nominal' = 'usd2025') =>
  timelineFromFilms(films, mask, measure, money, genreFamily, 2)

describe('timelineFromFilms', () => {
  it('splits a film over the families of its genres', () => {
    const t = build(Uint8Array.from([1, 0, 0, 0]))
    expect(t.shares[0][0]).toBeCloseTo(0.5)
    expect(t.shares[1][0]).toBeCloseTo(0.5)
  })
  it('gives one family the whole film when both genres share it', () => {
    const t = build(Uint8Array.from([0, 1, 0, 0]))
    expect(t.shares[0][0]).toBe(1)
    expect(t.shares[1][0]).toBe(0)
  })
  it('sums shares to 1 and leaves empty years at 0', () => {
    const t = build()
    expect(t.shares[0][0] + t.shares[1][0]).toBeCloseTo(1)
    expect(t.totals[5]).toBe(0)
    expect(t.shares[0][5]).toBe(0)
    expect(t.shares[1][5]).toBe(0)
    expect(t.films[0]).toBe(2)
  })
  it('skips films without revenue and follows the money mode', () => {
    const t = build(all, 'revenue', 'usd2025')
    expect(t.films[0]).toBe(1)
    expect(t.totals[0]).toBe(20)
    expect(build(all, 'revenue', 'nominal').totals[0]).toBe(10)
  })
  it('respects the mask', () => {
    const t = build(Uint8Array.from([0, 0, 1, 0]), 'films')
    expect(t.films[0]).toBe(0)
    expect(t.films[1]).toBe(1)
    expect(t.shares[1][1]).toBe(1)
  })
})

describe('timelineFromNetflix', () => {
  const cg = {
    rows: 4,
    source: { codes: Uint8Array.from([0, 0, 1, 0]), values: ['netflix', 'cinema'], nullCode: 255 },
    country: { codes: Uint8Array.from([0, 1, 0, 1]), values: ['US', 'FR'], nullCode: 255 },
    year: Uint16Array.from([2021, 2022, 2000, 2022]),
    genre: Uint8Array.from([0, 2, 0, 0]),
    score: Float64Array.from([3, 1, 9, 1]),
  } as unknown as CountryGenre
  const cy = {
    rows: 3,
    source: { codes: Uint8Array.from([0, 0, 0]), values: ['netflix'], nullCode: 255 },
    country: { codes: Uint8Array.from([0, 1, 1]), values: ['US', 'FR'], nullCode: 255 },
    year: Uint16Array.from([2021, 2022, 2022]),
    entries: Float64Array.from([10, 20, 5]),
  } as unknown as CountryYear

  it('keeps only Netflix years and sums all countries by default', () => {
    const t = timelineFromNetflix(cg, cy, genreFamily, 2, [])
    expect(t.years).toEqual([2021, 2022])
    expect(t.shares[0][1]).toBeCloseTo(0.5)
    expect(t.films[1]).toBe(25)
  })
  it('filters by country', () => {
    const t = timelineFromNetflix(cg, cy, genreFamily, 2, ['FR'])
    expect(t.years).toEqual([2021, 2022])
    expect(t.totals[0]).toBe(0)
    expect(t.shares[0][1]).toBeCloseTo(0.5)
    expect(t.films[1]).toBe(25)
    const us = timelineFromNetflix(cg, cy, genreFamily, 2, ['US'])
    expect(us.totals[0]).toBe(3)
    expect(us.films[0]).toBe(10)
  })
})

describe('familyAt', () => {
  const t = build(Uint8Array.from([1, 0, 0, 0]), 'films')
  it('finds the band from the bottom, at the edge and above the top', () => {
    expect(familyAt(t, 0, 0)).toBe(0)
    expect(familyAt(t, 0, 0.25)).toBe(0)
    expect(familyAt(t, 0, 0.5)).toBe(1)
    expect(familyAt(t, 0, 1)).toBe(1)
    expect(familyAt(t, 0, 1.2)).toBe(-1)
    expect(familyAt(t, 5, 0.5)).toBe(-1)
  })
})
