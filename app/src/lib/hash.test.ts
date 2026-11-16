import { describe, expect, it } from 'vitest'
import { decodeHash, encodeHash, type HashContext, type Values } from './hash'
import { defaults } from '../state/store'

const imdb = Uint32Array.from([111161, 68646, 468569])
const ctx: HashContext = {
  imdb,
  nFamilies: 8,
  countries: new Set(['US', 'FR', 'DE', 'CZ', 'SK', 'PL', 'IT']),
  collections: new Set([10, 20]),
}
const decode = (s: string) => decodeHash(s, ctx)

describe('encodeHash', () => {
  it('encodes the defaults to an empty string', () => {
    expect(encodeHash(defaults(), defaults(), imdb)).toBe('')
  })

  it('writes the pinned film as its tt id and ignores brush, hover and about', () => {
    const v: Values = { ...defaults(), film: 1, brush: [1, 2, 3, 4], hoverFilm: 2, about: true }
    expect(encodeHash(v, defaults(), imdb)).toBe('film=tt0068646')
  })
})

describe('story and studio', () => {
  it('writes st and stu only when they differ and ignores unknown values', () => {
    expect(encodeHash({ ...defaults(), story: 'book', studio: 'major' }, defaults(), imdb)).toBe('st=book&stu=major')
    expect(decode('st=comic&stu=independent')).toEqual({ story: 'comic', studio: 'independent' })
    expect(decode('st=bogus&stu=bogus')).toEqual({})
  })
})

describe('round trip', () => {
  it('restores a full non-default state', () => {
    const v: Values = {
      ...defaults(),
      tab: 'franchises',
      yearRange: [1950, 2000],
      family: 3,
      genreOnly: true,
      subset: 'all',
      money: 'nominal',
      story: 'true_story',
      studio: 'independent',
      source: 'cinema',
      mapMode: 'diff',
      countries: ['US', 'FR'],
      timelineMeasure: 'films',
      x: 'imdb',
      y: 'budget',
      size: null,
      franchise: 20,
      franchiseY: 'revenue',
      film: 2,
      sort: { key: 'year', desc: false },
      columns: ['year', 'gap'],
    }
    const hash = encodeHash(v, defaults(), imdb)
    const { brush, hoverFilm, about, ...expected } = v
    expect(decode(`#${hash}`)).toEqual(expected)
    expect([brush, hoverFilm, about]).toEqual([null, null, false])
  })

  it('writes the tab only when it is not the default', () => {
    expect(encodeHash({ ...defaults(), tab: 'ratings' }, defaults(), imdb)).toBe('tab=ratings')
    expect(decode('tab=franchises')).toEqual({ tab: 'franchises' })
    expect(decode('tab=bogus')).toEqual({})
  })

  it('round-trips a descending sort', () => {
    const v: Values = { ...defaults(), sort: { key: 'title', desc: true } }
    expect(decode(encodeHash(v, defaults(), imdb))).toEqual({ sort: { key: 'title', desc: true } })
  })
})

describe('decodeHash drops invalid fields only', () => {
  it.each([
    ['unknown key', 'zzz=1&sub=all'],
    ['unknown enum', 'map=bogus&sub=all'],
    ['unknown country', 'c=US.XX&sub=all'],
    ['too many countries', 'c=US.FR.DE.CZ.SK.PL.IT&sub=all'],
    ['unknown franchise', 'fr=99&sub=all'],
    ['unknown film', 'film=tt9999999&sub=all'],
    ['x equals y', 'x=imdb&y=imdb&sub=all'],
    ['family out of range', 'g=8&sub=all'],
    ['non-numeric years', 'yr=abc-def&sub=all'],
  ])('%s', (_name, hash) => {
    expect(decode(hash)).toEqual({ subset: 'all' })
  })

  it('drops x when it equals the default y', () => {
    expect(decode('x=audience')).toEqual({})
  })
})
