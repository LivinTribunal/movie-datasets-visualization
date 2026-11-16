import { describe, expect, it } from 'vitest'
import { franchiseLines, medianByInstallment, nearestVertex, outsideCount, sequelStat, type Line } from './franchise'
import type { Franchises } from './types'

interface Part {
  c: number
  k: number
  film: number
  rating: number
  rev: number
  mask?: number
}

function table(parts: Part[]): Franchises {
  const f = (g: (p: Part) => number) => Float64Array.from(parts.map(g))
  return {
    rows: parts.length,
    collection_id: f((p) => p.c),
    installment: f((p) => p.k),
    n_released: f(() => NaN),
    tmdb_id: f(() => NaN),
    film_row: f((p) => p.film),
    year: f(() => 2000),
    family_mask: Uint8Array.from(parts.map((p) => p.mask ?? 1)),
    imdb_100: f(() => NaN),
    tomatometer_100: f(() => NaN),
    audience_100: f(() => NaN),
    imdb_100_vs_first: f((p) => p.rating),
    revenue_usd2025: f(() => NaN),
    revenue_vs_first: f((p) => p.rev),
    title: parts.map(() => null),
    collections: new Map(),
  }
}

const parts: Part[] = [
  { c: 1, k: 1, film: 0, rating: 0, rev: 1 },
  { c: 1, k: 2, film: 1, rating: -5, rev: 0.5 },
  { c: 1, k: 3, film: 2, rating: NaN, rev: 0 },
  { c: 2, k: 1, film: 3, rating: 0, rev: 1, mask: 2 },
  { c: 2, k: 2, film: 4, rating: 4, rev: 2, mask: 2 },
  ...Array.from({ length: 12 }, (_, i) => ({ c: 3, k: i + 1, film: 5 + i, rating: i, rev: 1 + i })),
]

describe('franchiseLines', () => {
  it('drops a franchise with no part passing the mask, keeps one passing part whole', () => {
    const mask = new Uint8Array(20)
    mask[1] = 1
    const { lines } = franchiseLines(table(parts), 'rating', mask)
    expect(lines.map((l) => l.id)).toEqual([1])
    expect(lines[0].points.map((p) => p.k)).toEqual([1, 2])
  })

  it('cuts after installment 10 and sets cut', () => {
    const mask = new Uint8Array(20).fill(1)
    const { lines, cut } = franchiseLines(table(parts), 'rating', mask)
    expect(cut).toBe(true)
    expect(lines.find((l) => l.id === 3)?.points.length).toBe(10)
    const small = franchiseLines(table(parts.slice(0, 5)), 'rating', mask)
    expect(small.cut).toBe(false)
  })

  it('skips NaN, and a 0 for revenue', () => {
    const mask = new Uint8Array(20).fill(1)
    const t = table(parts.slice(0, 3))
    expect(franchiseLines(t, 'rating', mask).lines[0].points.map((p) => p.k)).toEqual([1, 2])
    expect(franchiseLines(t, 'revenue', mask).lines[0].points.map((p) => p.k)).toEqual([1, 2])
    const zero = table([...parts.slice(0, 2), { c: 1, k: 3, film: 2, rating: 1, rev: 0 }])
    expect(franchiseLines(zero, 'revenue', mask).lines[0].points.length).toBe(2)
    expect(franchiseLines(zero, 'rating', mask).lines[0].points.length).toBe(3)
  })
})

const mk = (id: number, familyMask: number, vs: number[]): Line => ({
  id,
  familyMask,
  points: vs.map((v, i) => ({ k: i + 1, v, row: i })),
})

describe('medianByInstallment', () => {
  it('respects minCount and takes the middle of an even count', () => {
    const lines = [mk(1, 1, [0, 1, 9]), mk(2, 1, [0, 3]), mk(3, 1, [0, 5]), mk(4, 1, [0, 7])]
    expect(medianByInstallment(lines, 4)).toEqual([
      { k: 1, v: 0 },
      { k: 2, v: 4 },
    ])
    expect(medianByInstallment(lines, 5)).toEqual([])
  })
})

describe('sequelStat', () => {
  it('ignores installment 1 and counts the family separately', () => {
    const lines = [mk(1, 1, [0, -1, 2]), mk(2, 2, [0, -3])]
    expect(sequelStat(lines, 0, 0)).toEqual({
      all: { below: 2, total: 3 },
      family: { below: 1, total: 2, franchises: 1 },
    })
  })
})

describe('nearestVertex', () => {
  const lines = [mk(1, 1, [0, 1]), mk(2, 1, [0, 3])]
  const xOf = (k: number) => k * 10
  const yOf = (v: number) => v * 10
  it('finds the closest vertex', () => {
    expect(nearestVertex(lines, 21, 28, xOf, yOf, 12)).toEqual({ line: 1, point: 1 })
  })
  it('returns null beyond maxDist', () => {
    expect(nearestVertex(lines, 100, 100, xOf, yOf, 12)).toBeNull()
  })
})

describe('outsideCount', () => {
  it('counts points below lo or above hi', () => {
    expect(outsideCount([mk(1, 1, [0.001, 1, 500]), mk(2, 1, [0.01, 100])], 0.01, 100)).toBe(2)
  })
})

describe('nearestVertex bounds', () => {
  it('skips vertices outside the y range', () => {
    const lines = [mk(1, 1, [0, 1])]
    const args = [lines, 20, 10, (k: number) => k * 10, (v: number) => v * 10, 12] as const
    expect(nearestVertex(...args)).toEqual({ line: 0, point: 1 })
    expect(nearestVertex(...args, [0, 5])).toBeNull()
  })
})
