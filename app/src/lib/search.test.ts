import { describe, expect, it } from 'vitest'
import { fold, search } from './search'
import type { Country } from './types'

const country = (iso2: string, name: string): Country =>
  ({ iso2, iso_numeric: '0', name, region: '', subregion: '' }) as Country
const countries = [
  country('FR', 'France'),
  country('GF', 'French Guiana'),
  country('PF', 'French Polynesia'),
  country('TF', 'French Southern Territories'),
  country('AF', 'Afghanistan, Central France'),
]
const collections = new Map([
  [1, 'The Matrix Collection'],
  [2, 'Matrix Reloaded Saga'],
  [3, 'Matrix Three'],
  [4, 'Matrix Four'],
  [5, 'Alt Matrix'],
])
const folded = ['the matrix', 'amelie', 'matrix revolutions', 'x', 'matrix reloaded', 'matrix 4', 'matrix 5']

describe('fold', () => {
  it('lowercases and strips diacritics', () => expect(fold('Amélie')).toBe('amelie'))
})

describe('search', () => {
  it('returns empty groups for a short query', () => {
    expect(search('a', { countries, collections, folded })).toEqual({ countries: [], franchises: [], films: [] })
  })

  it('puts prefix matches before substring matches and caps groups at 3', () => {
    const r = search('fr', { countries, collections, folded: null })
    expect(r.countries.map((c) => c.iso2)).toEqual(['FR', 'GF', 'PF'])
    const m = search('matrix', { countries, collections, folded: null })
    expect(m.franchises.map((f) => f.id)).toEqual([2, 3, 4])
  })

  it('finds the substring match when no prefix matches', () => {
    expect(search('central', { countries, collections, folded: null }).countries.map((c) => c.iso2)).toEqual(['AF'])
    expect(search('alt', { countries, collections, folded: null }).franchises.map((f) => f.id)).toEqual([5])
  })

  it('fills the rest of the limit with films in row order', () => {
    expect(search('matrix', { countries, collections, folded }).films).toEqual([0, 2, 4, 5, 6])
    expect(search('matrix', { countries, collections, folded, limit: 5 }).films).toEqual([0, 2])
  })

  it('finds films without diacritics', () => {
    expect(search('amélie', { countries, collections, folded }).films).toEqual([1])
  })

  it('gives no films while the titles are not loaded', () => {
    expect(search('matrix', { countries, collections, folded: null }).films).toEqual([])
  })
})
