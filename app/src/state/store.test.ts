import { beforeEach, describe, expect, it } from 'vitest'
import { useStore } from './store'

const s = () => useStore.getState()

describe('store', () => {
  beforeEach(() => s().reset())

  it('setX refuses the measure Y has, and a valid setX clears the brush', () => {
    s().setBrush([0, 1, 0, 1])
    s().setX('audience')
    expect(s().x).toBe('tomatometer')
    expect(s().brush).toEqual([0, 1, 0, 1])
    s().setX('imdb')
    expect(s().x).toBe('imdb')
    expect(s().brush).toBeNull()
  })

  it('setY refuses the measure X has and clears the brush', () => {
    s().setBrush([0, 1, 0, 1])
    s().setY('tomatometer')
    expect(s().y).toBe('audience')
    s().setY('gap')
    expect(s().y).toBe('gap')
    expect(s().brush).toBeNull()
  })

  it('refuses a seventh country and toggling removes', () => {
    for (const c of ['US', 'FR', 'DE', 'GB', 'IT', 'ES', 'PL']) s().toggleCountry(c)
    expect(s().countries).toEqual(['US', 'FR', 'DE', 'GB', 'IT', 'ES'])
    s().toggleCountry('FR')
    expect(s().countries).toEqual(['US', 'DE', 'GB', 'IT', 'ES'])
  })

  it('setYearRange clamps and orders', () => {
    s().setYearRange([1800, 2100])
    expect(s().yearRange).toEqual([1900, 2026])
    s().setYearRange([2010, 2000])
    expect(s().yearRange).toEqual([2000, 2010])
  })

  it('reset restores the defaults', () => {
    s().setFamily(3)
    s().setFilm(5)
    s().toggleCountry('US')
    s().reset()
    expect(s().family).toBe(0)
    expect(s().film).toBeNull()
    expect(s().countries).toEqual([])
    expect(s().yearRange).toEqual([1990, 2026])
  })
})
