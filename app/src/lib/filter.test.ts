import { describe, expect, it } from 'vitest'
import { filmIndices, type FilmFilter } from './filter'
import type { Columnar, FilmRow } from './types'

const films = {
  columns: {
    year: [1990, 2000, null, 2010],
    notable: [true, false, true, true],
    families: [['Drama'], ['Comedy'], ['Drama'], ['Comedy', 'Action']],
    countries: [['US'], ['FR'], ['US'], ['US', 'FR']],
  },
} as unknown as Columnar<FilmRow>

const all: FilmFilter = {
  yearRange: [1900, 2026], families: [], subset: 'working', selectedCountry: null,
}

describe('filmIndices', () => {
  it('excludes null years', () => {
    expect(filmIndices(films, all)).toEqual([0, 1, 3])
  })
  it('keeps the year range inclusive', () => {
    expect(filmIndices(films, { ...all, yearRange: [2000, 2010] })).toEqual([1, 3])
  })
  it('keeps only notable films in the notable subset', () => {
    expect(filmIndices(films, { ...all, subset: 'notable' })).toEqual([0, 3])
  })
  it('keeps films sharing a family', () => {
    expect(filmIndices(films, { ...all, families: ['Action'] })).toEqual([3])
  })
  it('keeps films from the selected country', () => {
    expect(filmIndices(films, { ...all, selectedCountry: 'FR' })).toEqual([1, 3])
  })
})
