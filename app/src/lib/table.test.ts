import { describe, expect, it } from 'vitest'
import { cellKind, columnMax, filterByTitle, maskRows, sortRows, sortRowsByTitle, visibleWindow } from './table'

const u32 = (...n: number[]) => Uint32Array.from(n)

describe('maskRows', () => {
  it('lists rows where the mask is 1', () => {
    expect(Array.from(maskRows(Uint8Array.from([0, 1, 1, 0, 1])))).toEqual([1, 2, 4])
    expect(Array.from(maskRows(Uint8Array.from([0, 0])))).toEqual([])
  })
})

describe('sortRows', () => {
  const col = Float64Array.from([5, NaN, 5, 1, 9])
  const rows = u32(0, 1, 2, 3, 4)
  it('ascending: NaN last, ties keep row order', () => {
    expect(Array.from(sortRows(rows, col, false))).toEqual([3, 0, 2, 4, 1])
  })
  it('descending: NaN still last, ties keep row order', () => {
    expect(Array.from(sortRows(rows, col, true))).toEqual([4, 0, 2, 3, 1])
  })
  it('does not change the input', () => {
    sortRows(rows, col, true)
    expect(Array.from(rows)).toEqual([0, 1, 2, 3, 4])
  })
})

describe('sortRowsByTitle', () => {
  const titles = ['Zorro', null, 'Éclair', 'apple', 'Eclair']
  const rows = u32(0, 1, 2, 3, 4)
  it('sorts accented titles with the collator and puts null last', () => {
    expect(Array.from(sortRowsByTitle(rows, titles, false))).toEqual([3, 2, 4, 0, 1])
  })
  it('descending keeps null last', () => {
    expect(Array.from(sortRowsByTitle(rows, titles, true))).toEqual([0, 2, 4, 3, 1])
  })
})

describe('columnMax', () => {
  it('ignores NaN', () => {
    expect(columnMax(Float64Array.from([3, NaN, 7, 2]), u32(0, 1, 2, 3))).toBe(7)
  })
  it('is 0 with no finite value', () => {
    expect(columnMax(Float64Array.from([NaN, NaN]), u32(0, 1))).toBe(0)
    expect(columnMax(Float64Array.from([4]), u32())).toBe(0)
  })
})

describe('visibleWindow', () => {
  it('starts at 0 at the top', () => {
    expect(visibleWindow(0, 240, 24, 1000)).toEqual([0, 18])
  })
  it('adds overscan in the middle', () => {
    expect(visibleWindow(2400, 240, 24, 1000)).toEqual([92, 118])
  })
  it('clamps at the end', () => {
    expect(visibleWindow(23760, 240, 24, 1000)).toEqual([982, 1000])
  })
  it('covers all rows when fewer than fit', () => {
    expect(visibleWindow(0, 240, 24, 5)).toEqual([0, 5])
  })
  it('is empty for no rows', () => {
    expect(visibleWindow(0, 240, 24, 0)).toEqual([0, 0])
  })
})

describe('cellKind', () => {
  it('classifies measures', () => {
    expect(cellKind('tomatometer')).toBe('bar')
    expect(cellKind('imdb')).toBe('bar')
    expect(cellKind('budget')).toBe('bar')
    expect(cellKind('revenue')).toBe('bar')
    expect(cellKind('gap')).toBe('gap')
    expect(cellKind('roi')).toBe('plain')
    expect(cellKind('votes')).toBe('plain')
    expect(cellKind('year')).toBe('plain')
  })
})

describe('filterByTitle', () => {
  const folded = ['amelie', 'the matrix', 'matrix reloaded', 'heat']
  const rows = u32(0, 1, 2, 3)
  it('returns the same array for an empty or blank query', () => {
    expect(filterByTitle(rows, folded, '')).toBe(rows)
    expect(filterByTitle(rows, folded, '   ')).toBe(rows)
  })
  it('folds case and diacritics', () => {
    expect(Array.from(filterByTitle(rows, folded, 'AMÉLIE'))).toEqual([0])
  })
  it('keeps input order', () => {
    expect(Array.from(filterByTitle(u32(2, 1), folded, 'matrix'))).toEqual([2, 1])
  })
  it('returns nothing when no title matches', () => {
    expect(filterByTitle(rows, folded, 'zzz')).toHaveLength(0)
  })
})
