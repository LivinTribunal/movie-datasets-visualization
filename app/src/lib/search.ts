import { memoLast } from './memo'
import type { Country } from './types'

export function fold(s: string): string {
  return s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()
}

export const foldAll = memoLast((titles: (string | null)[]): string[] =>
  titles.map((t) => (t === null ? '' : fold(t))),
)

export interface SearchResult {
  countries: Country[]
  franchises: { id: number; name: string }[]
  films: number[]
}

interface SearchContext {
  countries: Country[]
  collections: Map<number, string>
  /** Folded film titles in row order; null while the titles load. */
  folded: string[] | null
  limit?: number
}

const MAX_GROUP = 3

function best<T>(items: T[], name: (t: T) => string, q: string): T[] {
  const starts: T[] = []
  const contains: T[] = []
  for (const item of items) {
    const n = fold(name(item))
    if (n.startsWith(q)) starts.push(item)
    else if (n.includes(q)) contains.push(item)
  }
  return [...starts, ...contains].slice(0, MAX_GROUP)
}

export function search(query: string, ctx: SearchContext): SearchResult {
  const q = fold(query.trim())
  const result: SearchResult = { countries: [], franchises: [], films: [] }
  if (q.length < 2) return result
  const limit = ctx.limit ?? 8
  result.countries = best(ctx.countries, (c) => c.name, q)
  result.franchises = best(
    [...ctx.collections].map(([id, name]) => ({ id, name })),
    (f) => f.name,
    q,
  )
  const room = limit - result.countries.length - result.franchises.length
  if (ctx.folded) {
    for (let row = 0; row < ctx.folded.length && result.films.length < room; row++) {
      if (ctx.folded[row].includes(q)) result.films.push(row)
    }
  }
  return result
}
