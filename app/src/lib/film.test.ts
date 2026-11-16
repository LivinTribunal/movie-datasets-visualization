import { describe, expect, it } from 'vitest'
import { filmCountries, filmGenres, fuzzyMoney, moneyFacts } from './film'
import type { Films } from './types'

const NaNs = (n: number) => new Float64Array(n).fill(NaN)

function films(): Films {
  return {
    rows: 3,
    notable: 3,
    genres: ['Action', 'Comedy', 'Drama'],
    families: [],
    imdb: Uint32Array.from([1, 2, 3]),
    tmdb_id: NaNs(3),
    year: NaNs(3),
    runtime: NaNs(3),
    imdb_votes: NaNs(3),
    genre_mask: Uint32Array.from([0b101, 0b010, 0]),
    family_mask: new Uint8Array(3),
    countries: { offsets: Uint32Array.from([0, 2, 3, 3]), codes: Uint16Array.from([0, 1, 1]), values: ['US', 'GB'] },
    budget_usd: Float64Array.from([10, NaN, 30]),
    budget_usd2025: Float64Array.from([100, NaN, 300]),
    revenue_usd: Float64Array.from([20, 40, NaN]),
    revenue_usd2025: Float64Array.from([200, 400, NaN]),
    roi: Float64Array.from([2, NaN, NaN]),
    budget_src: { codes: Uint8Array.from([0, 2, 1]), values: ['numbers', 'tmdb', ''], nullCode: 2 },
    revenue_src: { codes: Uint8Array.from([1, 3, 3]), values: ['numbers', 'wikidata', 'wikipedia', ''], nullCode: 3 },
    flags: Uint8Array.from([0b10101, 0b01010, 0]),
    imdb_100: NaNs(3),
    tmdb_100: NaNs(3),
    tomatometer_100: NaNs(3),
    audience_100: NaNs(3),
    metascore_100: NaNs(3),
    mc_user_100: NaNs(3),
    letterboxd_100: NaNs(3),
    gap: NaNs(3),
    mc_critic_reviews: NaNs(3),
    collection_id: NaNs(3),
    installment: NaNs(3),
  }
}

describe('filmGenres and filmCountries', () => {
  it('reads genre bits', () => {
    expect(filmGenres(films(), 0)).toEqual(['Action', 'Drama'])
    expect(filmGenres(films(), 1)).toEqual(['Comedy'])
    expect(filmGenres(films(), 2)).toEqual([])
  })

  it('reads list rows', () => {
    expect(filmCountries(films(), 0)).toEqual(['US', 'GB'])
    expect(filmCountries(films(), 1)).toEqual(['GB'])
    expect(filmCountries(films(), 2)).toEqual([])
  })
})

describe('moneyFacts', () => {
  it('uses the money mode column and flag bits', () => {
    const a = moneyFacts(films(), 0, 'usd2025')
    expect(a.budget).toEqual({ value: 100, source: 'numbers', converted: true, disagree: true })
    expect(a.revenue).toEqual({ value: 200, source: 'wikidata', converted: false, disagree: false })
    expect(a.roi).toBe(2)
    const n = moneyFacts(films(), 0, 'nominal')
    expect(n.budget.value).toBe(10)
    expect(n.revenue.value).toBe(20)
  })

  it('reads the other flag bits and a null source', () => {
    const b = moneyFacts(films(), 1, 'nominal')
    expect(b.budget).toMatchObject({ source: null, converted: false, disagree: false })
    expect(b.budget.value).toBeNaN()
    expect(b.revenue).toEqual({ value: 40, source: null, converted: true, disagree: true })
  })
})

describe('fuzzyMoney', () => {
  it('reads bit 4', () => {
    expect(fuzzyMoney(films(), 0)).toBe(true)
    expect(fuzzyMoney(films(), 1)).toBe(false)
  })
})
