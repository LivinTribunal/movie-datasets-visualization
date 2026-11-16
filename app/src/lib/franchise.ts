import { memoLast } from './memo'
import type { Franchises } from './types'
import type { FranchiseY } from '../state/store'

export const MAX_K = 10
export const RATIO_MAX = 100

export interface LinePoint {
  k: number
  v: number
  /** Row in `franchises`. */
  row: number
}

export interface Line {
  id: number
  /** Family mask of the first part. */
  familyMask: number
  points: LinePoint[]
}

export interface Count {
  below: number
  total: number
}

export interface SequelStat {
  all: Count
  family: Count & { franchises: number }
}

const usable = (v: number, y: FranchiseY) => Number.isFinite(v) && (y === 'rating' || v > 0)

export const franchiseLines = memoLast((fr: Franchises, y: FranchiseY, mask: Uint8Array) => {
  const parts = new Map<number, number[]>()
  for (let i = 0; i < fr.rows; i++) {
    const list = parts.get(fr.collection_id[i])
    if (list) list.push(i)
    else parts.set(fr.collection_id[i], [i])
  }
  const values = y === 'rating' ? fr.imdb_100_vs_first : fr.revenue_vs_first
  const lines: Line[] = []
  let cut = false
  for (const [id, rows] of parts) {
    rows.sort((a, b) => fr.installment[a] - fr.installment[b])
    if (!rows.some((r) => mask[fr.film_row[r]] === 1)) continue
    if (rows.some((r) => fr.installment[r] > MAX_K)) cut = true
    const points: LinePoint[] = []
    for (const row of rows) {
      const k = fr.installment[row]
      if (k > MAX_K || !usable(values[row], y)) continue
      points.push({ k, v: values[row], row })
    }
    if (points.length < 2) continue
    lines.push({ id, familyMask: fr.family_mask[rows[0]], points })
  }
  return { lines, cut }
})

export function medianByInstallment(lines: Line[], minCount = 10): { k: number; v: number }[] {
  const byK: number[][] = []
  for (const line of lines) {
    for (const p of line.points) (byK[p.k] ??= []).push(p.v)
  }
  const out: { k: number; v: number }[] = []
  byK.forEach((vs, k) => {
    if (vs.length < minCount) return
    vs.sort((a, b) => a - b)
    const mid = vs.length >> 1
    out.push({ k, v: vs.length % 2 ? vs[mid] : (vs[mid - 1] + vs[mid]) / 2 })
  })
  return out
}

/** `familyBit` is the family index. */
export function sequelStat(lines: Line[], baseline: number, familyBit: number): SequelStat {
  const stat: SequelStat = { all: { below: 0, total: 0 }, family: { below: 0, total: 0, franchises: 0 } }
  for (const line of lines) {
    const inFamily = ((line.familyMask >> familyBit) & 1) === 1
    if (inFamily) stat.family.franchises++
    for (const p of line.points) {
      if (p.k < 2) continue
      const below = p.v < baseline ? 1 : 0
      stat.all.total++
      stat.all.below += below
      if (inFamily) {
        stat.family.total++
        stat.family.below += below
      }
    }
  }
  return stat
}

export function outsideCount(lines: Line[], lo: number, hi: number): number {
  let n = 0
  for (const line of lines) for (const p of line.points) if (p.v < lo || p.v > hi) n++
  return n
}

/** `yRange` limits the search to vertices whose y is inside it. */
export function nearestVertex(
  lines: Line[],
  px: number,
  py: number,
  xOf: (k: number) => number,
  yOf: (v: number) => number,
  maxDist: number,
  yRange?: [number, number],
): { line: number; point: number } | null {
  let best: { line: number; point: number } | null = null
  let bestD = maxDist * maxDist
  lines.forEach((line, li) => {
    line.points.forEach((p, pi) => {
      const dx = xOf(p.k) - px
      const vy = yOf(p.v)
      if (yRange && (vy < yRange[0] || vy > yRange[1])) return
      const dy = vy - py
      const d = dx * dx + dy * dy
      if (d <= bestD) {
        bestD = d
        best = { line: li, point: pi }
      }
    })
  })
  return best
}
