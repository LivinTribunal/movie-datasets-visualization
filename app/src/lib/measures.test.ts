import { describe, expect, it } from 'vitest'
import { axisLabel, isScore, MEASURE_KEYS, measureColumn, MEASURES } from './measures'
import type { Films } from './types'

describe('measures', () => {
  it('has an entry for every key', () => {
    expect(MEASURE_KEYS).toHaveLength(14)
    for (const k of MEASURE_KEYS) expect(MEASURES[k].label).toBeTruthy()
  })
  it('switches the money columns', () => {
    const films = {
      budget_usd: Float64Array.of(1), budget_usd2025: Float64Array.of(2),
      revenue_usd: Float64Array.of(3), revenue_usd2025: Float64Array.of(4),
      tomatometer_100: Float64Array.of(5),
    } as unknown as Films
    expect(measureColumn(films, 'budget', 'usd2025')[0]).toBe(2)
    expect(measureColumn(films, 'budget', 'nominal')[0]).toBe(1)
    expect(measureColumn(films, 'revenue', 'usd2025')[0]).toBe(4)
    expect(measureColumn(films, 'revenue', 'nominal')[0]).toBe(3)
    expect(measureColumn(films, 'tomatometer', 'nominal')[0]).toBe(5)
  })
  it('builds axis labels', () => {
    expect(axisLabel('budget', 'usd2025')).toBe('budget (2025 USD, log)')
    expect(axisLabel('budget', 'nominal')).toBe('budget (nominal USD, log)')
    expect(axisLabel('tomatometer', 'usd2025')).toBe('critics (Tomatometer) (0–100)')
  })
  it('knows the seven scores', () => {
    expect(MEASURE_KEYS.filter(isScore)).toHaveLength(7)
    expect(isScore('gap')).toBe(false)
  })
})
