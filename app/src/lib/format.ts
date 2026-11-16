import { isScore, type MeasureKey } from './measures'

const NO_DATA = 'no data'

const missing = (n: number | null | undefined): n is null | undefined =>
  n === null || n === undefined || Number.isNaN(n)

const INT = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })

export function fmtInt(n: number | null): string {
  return missing(n) ? NO_DATA : INT.format(n)
}

export function fmtMoney(n: number | null): string {
  if (missing(n)) return NO_DATA
  const abs = Math.abs(n)
  const sign = n < 0 ? '-' : ''
  const short = (v: number, unit: string) => `${sign}$${v >= 100 ? Math.round(v) : Number(v.toPrecision(2))}${unit}`
  if (abs >= 1e9) return short(abs / 1e9, 'B')
  if (abs >= 1e6) return short(abs / 1e6, 'M')
  if (abs >= 1e3) return short(abs / 1e3, 'K')
  return `${sign}$${Math.round(abs)}`
}

export function fmtScore(n: number | null): string {
  return missing(n) ? NO_DATA : String(Math.round(n))
}

export function fmtPct(n: number | null): string {
  if (missing(n)) return NO_DATA
  const pct = n * 100
  return Math.abs(pct) < 10 ? `${pct.toFixed(1)}%` : `${Math.round(pct)}%`
}

export function fmtRatio(n: number | null): string {
  if (missing(n)) return NO_DATA
  const a = Math.abs(n)
  // toFixed(1) would print 0.04 as 0.0
  const s = a >= 100 ? fmtInt(n) : a >= 1 ? String(+n.toFixed(1)) : String(+n.toPrecision(2))
  return `${s}×`
}

export function fmtValue(key: MeasureKey, value: number | null): string {
  if (isScore(key) || key === 'gap') return fmtScore(value)
  switch (key) {
    case 'budget':
    case 'revenue':
    case 'opening':
      return fmtMoney(value)
    case 'roi':
    case 'legs':
      return fmtRatio(value)
    case 'year':
      return missing(value) ? NO_DATA : String(Math.round(value))
    default:
      return fmtInt(value)
  }
}

export function fmtImdb(n: number): string {
  return `tt${String(n).padStart(7, '0')}`
}
