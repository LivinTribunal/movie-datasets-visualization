import { describe, expect, it } from 'vitest'
import { brushedRows, domainOf, radiusBucket, scatterRows } from './scatter'

const nan = NaN

describe('scatterRows', () => {
  const x = Float64Array.from([1, 2, nan, 4, 5, 0])
  const y = Float64Array.from([1, nan, 3, 4, 5, 6])

  it('respects the mask and drops NaN, counting what is missing', () => {
    const mask = Uint8Array.from([1, 1, 1, 1, 0, 1])
    const r = scatterRows(x, y, mask, false, false)
    expect([...r.rows]).toEqual([0, 3, 5])
    expect(r.missingX).toBe(1)
    expect(r.missingY).toBe(1)
  })

  it('drops zero and negatives on a log axis only', () => {
    const mask = Uint8Array.from([1, 1, 1, 1, 1, 1])
    expect([...scatterRows(x, y, mask, true, false).rows]).toEqual([0, 3, 4])
    expect(scatterRows(x, y, mask, true, false).missingX).toBe(2)
    expect([...scatterRows(x, y, mask, false, false).rows]).toEqual([0, 3, 4, 5])
  })
})

describe('domainOf', () => {
  const col = Float64Array.from([5, 20, 10])
  const rows = Uint32Array.from([0, 1, 2])

  it('uses 0-100 for a score', () => expect(domainOf('imdb', col, rows)).toEqual([0, 100]))
  it('uses the fixed domain of a measure', () => expect(domainOf('gap', col, rows)).toEqual([-100, 100]))
  it('uses the data extent otherwise', () => expect(domainOf('runtime', col, rows)).toEqual([5, 20]))
  it('pads a single value', () => {
    const one = Uint32Array.from([0])
    expect(domainOf('runtime', col, one)).toEqual([4, 6])
    expect(domainOf('budget', col, one)).toEqual([2.5, 10])
  })
})

describe('brushedRows', () => {
  const x = Float64Array.from([1, 2, 3, 4])
  const y = Float64Array.from([1, 2, 3, 4])
  const rows = Uint32Array.from([0, 1, 2, 3])

  it('includes the edges', () => expect([...brushedRows(x, y, rows, [2, 3, 2, 3])]).toEqual([1, 2]))
  it('returns nothing outside', () => expect(brushedRows(x, y, rows, [10, 11, 10, 11]).length).toBe(0))
})

describe('radiusBucket', () => {
  it('maps NaN to 0', () => expect(radiusBucket(NaN, 100, 6)).toBe(0))
  it('maps 0 to 0', () => expect(radiusBucket(0, 100, 6)).toBe(0))
  it('maps max to the last bucket', () => expect(radiusBucket(100, 100, 6)).toBe(5))
})
