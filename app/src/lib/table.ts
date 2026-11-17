import { memoLast } from './memo'
import { fold } from './search'
import { isScore, type MeasureKey } from './measures'

/** Rows where the mask is 1, in row order. */
export const maskRows = memoLast((mask: Uint8Array): Uint32Array => {
  const out: number[] = []
  for (let i = 0; i < mask.length; i++) if (mask[i]) out.push(i)
  return Uint32Array.from(out)
})

/** Sorted copy of rows by a numeric column; NaN last in both directions, ties keep row order. */
export const sortRows = memoLast((rows: Uint32Array, col: Float64Array, desc: boolean): Uint32Array => {
  const out = Uint32Array.from(rows)
  return out.sort((a, b) => {
    const va = col[a]
    const vb = col[b]
    const na = Number.isNaN(va)
    const nb = Number.isNaN(vb)
    if (na || nb) return na === nb ? a - b : na ? 1 : -1
    if (va === vb) return a - b
    return desc ? vb - va : va - vb
  })
})

const COLLATOR = new Intl.Collator('en', { sensitivity: 'base' })

/** Sorted copy of rows by title; null titles last in both directions, ties keep row order. */
export const sortRowsByTitle = memoLast(
  (rows: Uint32Array, titles: (string | null)[], desc: boolean): Uint32Array => {
    const out = Uint32Array.from(rows)
    return out.sort((a, b) => {
      const ta = titles[a]
      const tb = titles[b]
      if (ta === null || tb === null) return ta === tb ? a - b : ta === null ? 1 : -1
      const c = COLLATOR.compare(ta, tb)
      if (c === 0) return a - b
      return desc ? -c : c
    })
  },
)

/** Rows whose folded title contains the folded query, in input order; same array when the query is blank. */
export const filterByTitle = memoLast((rows: Uint32Array, folded: string[], query: string): Uint32Array => {
  const q = fold(query.trim())
  if (q === '') return rows
  return rows.filter((r) => folded[r].includes(q))
})

/** Largest finite value of col over rows; 0 when there is none. */
export function columnMax(col: Float64Array, rows: Uint32Array): number {
  let max = 0
  let seen = false
  for (const r of rows) {
    const v = col[r]
    if (!Number.isFinite(v)) continue
    if (!seen || v > max) max = v
    seen = true
  }
  return seen ? max : 0
}

/** Half-open range [start, end) of rows to render. */
export function visibleWindow(
  scrollTop: number,
  viewHeight: number,
  rowHeight: number,
  count: number,
  overscan = 8,
): [number, number] {
  const first = Math.floor(scrollTop / rowHeight)
  const last = Math.ceil((scrollTop + viewHeight) / rowHeight)
  const start = Math.max(0, Math.min(count, first - overscan))
  const end = Math.max(start, Math.min(count, last + overscan))
  return [start, end]
}

export function cellKind(key: MeasureKey): 'bar' | 'gap' | 'plain' {
  if (key === 'gap') return 'gap'
  if (isScore(key) || key === 'budget' || key === 'revenue') return 'bar'
  return 'plain'
}
