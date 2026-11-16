import { describe, expect, it } from 'vitest'
import { fmtImdb, fmtInt, fmtMoney, fmtPct, fmtRatio, fmtScore, fmtValue } from './format'

describe('format', () => {
  it('formats each kind', () => {
    expect(fmtInt(1204)).toBe('1,204')
    expect(fmtMoney(2.9e9)).toBe('$2.9B')
    expect(fmtMoney(35e6)).toBe('$35M')
    expect(fmtMoney(850e3)).toBe('$850K')
    expect(fmtMoney(900)).toBe('$900')
    expect(fmtScore(77.4)).toBe('77')
    expect(fmtPct(0.213)).toBe('21%')
    expect(fmtPct(0.062)).toBe('6.2%')
    expect(fmtRatio(3.21)).toBe('3.2×')
    expect(fmtRatio(0.04)).toBe('0.04×')
    expect(fmtRatio(1)).toBe('1×')
    expect(fmtRatio(1638.2)).toBe('1,638×')
    expect(fmtImdb(111161)).toBe('tt0111161')
  })
  it('picks by measure', () => {
    expect(fmtValue('budget', 35e6)).toBe('$35M')
    expect(fmtValue('opening', 35e6)).toBe('$35M')
    expect(fmtValue('legs', 2.5)).toBe(fmtRatio(2.5))
    expect(fmtValue('tomatometer', 77.4)).toBe('77')
    expect(fmtValue('roi', 3.2)).toBe('3.2×')
    expect(fmtValue('votes', 1204)).toBe('1,204')
    expect(fmtValue('year', 1994)).toBe('1994')
  })
  it('says no data for NaN and null', () => {
    for (const f of [fmtInt, fmtMoney, fmtScore, fmtPct, fmtRatio]) {
      expect(f(NaN)).toBe('no data')
      expect(f(null)).toBe('no data')
    }
    expect(fmtValue('gap', NaN)).toBe('no data')
    expect(fmtValue('year', NaN)).toBe('no data')
  })
})
