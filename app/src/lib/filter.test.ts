import { describe, expect, it } from 'vitest'
import { countMask, filmMask, type FilmFilter } from './filter'
import type { Films } from './types'

// Rows: 0 US 1990 drama; 1 FR 2000 comedy; 2 none 2005 action; 3 US+FR 2010 comedy+action.
const films = {
  rows: 4,
  notable: 2,
  year: Float64Array.from([1990, 2000, 2005, 2010]),
  family_mask: Uint8Array.from([0b001, 0b010, 0b100, 0b110]),
  countries: {
    offsets: Uint32Array.from([0, 1, 2, 2, 4]),
    codes: Uint16Array.from([0, 1, 0, 1]),
    values: ['US', 'FR'],
  },
  // story: book, original, null, book. studio: disney, independent, null, sony.
  story_source: { codes: Uint8Array.from([1, 0, 255, 1]), values: ['original', 'book'], nullCode: 255 },
  studio: { codes: Uint8Array.from([0, 1, 255, 2]), values: ['disney', 'independent', 'sony'], nullCode: 255 },
} as unknown as Films

const all: FilmFilter = { yearRange: null, subset: 'all', countries: [], genreOnly: false, family: 0, story: 'any', studio: 'any' }
const rows = (f: Partial<FilmFilter>) => Array.from(filmMask(films, { ...all, ...f }))

describe('filmMask', () => {
  it('passes every film with no constraint', () => {
    expect(rows({})).toEqual([1, 1, 1, 1])
  })
  it('keeps the year range inclusive and null means any year', () => {
    expect(rows({ yearRange: [2000, 2005] })).toEqual([0, 1, 1, 0])
    expect(rows({ yearRange: null })).toEqual([1, 1, 1, 1])
  })
  it('keeps the notable prefix', () => {
    expect(rows({ subset: 'notable' })).toEqual([1, 1, 0, 0])
  })
  it('matches any of the chosen countries', () => {
    expect(rows({ countries: ['FR'] })).toEqual([0, 1, 0, 1])
    expect(rows({ countries: ['US', 'FR'] })).toEqual([1, 1, 0, 1])
  })
  it('matches nothing for a country unknown to the pack', () => {
    expect(rows({ countries: ['ZZ'] })).toEqual([0, 0, 0, 0])
  })
  it('filters by family only when genreOnly is on', () => {
    expect(rows({ family: 2, genreOnly: false })).toEqual([1, 1, 1, 1])
    expect(rows({ family: 2, genreOnly: true })).toEqual([0, 0, 1, 1])
  })
  it('filters by story source and fails a null story', () => {
    expect(rows({ story: 'book' })).toEqual([1, 0, 0, 1])
    expect(rows({ story: 'original' })).toEqual([0, 1, 0, 0])
    expect(rows({ story: 'comic' })).toEqual([0, 0, 0, 0])
  })
  it('filters by studio group and fails a null studio', () => {
    expect(rows({ studio: 'major' })).toEqual([1, 0, 0, 1])
    expect(rows({ studio: 'independent' })).toEqual([0, 1, 0, 0])
  })
})

describe('countMask', () => {
  it('counts passing films', () => {
    expect(countMask(Uint8Array.from([1, 0, 1, 1]))).toBe(3)
  })
})
