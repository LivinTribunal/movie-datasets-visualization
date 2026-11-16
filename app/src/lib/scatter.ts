import { extent } from 'd3'
import { memoLast } from './memo'
import { isScore, MEASURES, type MeasureKey } from './measures'
import type { Brush } from '../state/store'

export function usable(v: number, log: boolean): boolean {
  return Number.isFinite(v) && (!log || v > 0)
}

export interface ScatterRows {
  rows: Uint32Array
  missingX: number
  missingY: number
}

/** Films that pass the mask and have both values, in row order, plus how many lack each. */
export const scatterRows = memoLast(
  (xCol: Float64Array, yCol: Float64Array, mask: Uint8Array, xLog: boolean, yLog: boolean): ScatterRows => {
    const rows: number[] = []
    let missingX = 0
    let missingY = 0
    for (let i = 0; i < mask.length; i++) {
      if (!mask[i]) continue
      if (!usable(xCol[i], xLog)) missingX++
      else if (!usable(yCol[i], yLog)) missingY++
      else rows.push(i)
    }
    return { rows: Uint32Array.from(rows), missingX, missingY }
  },
)

export function domainOf(key: MeasureKey, col: Float64Array, rows: Uint32Array): [number, number] {
  if (isScore(key)) return [0, 100]
  const { domain, scale } = MEASURES[key]
  if (domain) return domain
  const [lo, hi] = extent(rows, (r) => col[r])
  if (lo === undefined || hi === undefined) return [0, 1]
  if (lo === hi) return scale === 'log' ? [lo / 2, hi * 2] : [lo - 1, hi + 1]
  return [lo, hi]
}

/** Rows whose x and y lie inside brush = [x0, x1, y0, y1], edges included. */
export function brushedRows(xCol: Float64Array, yCol: Float64Array, rows: Uint32Array, brush: Brush): Uint32Array {
  const [x0, x1, y0, y1] = brush
  const out: number[] = []
  for (const r of rows) {
    const x = xCol[r]
    const y = yCol[r]
    if (x >= x0 && x <= x1 && y >= y0 && y <= y1) out.push(r)
  }
  return Uint32Array.from(out)
}

/** Bucket 0 … buckets − 1 for a radius that grows with sqrt(v / max); NaN gives 0. */
export function radiusBucket(v: number, max: number, buckets: number): number {
  if (!Number.isFinite(v) || !(max > 0)) return 0
  const t = Math.sqrt(Math.max(0, Math.min(v, max)) / max)
  return Math.min(buckets - 1, Math.floor(t * buckets))
}
