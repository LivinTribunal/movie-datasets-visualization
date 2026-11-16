import { MEASURE_KEYS, type MeasureKey } from './measures'
import { MAX_COUNTRIES, YEAR_MAX, YEAR_MIN, defaults, type Sort } from '../state/store'
import { fmtImdb } from './format'

export type Values = ReturnType<typeof defaults>

export interface HashContext {
  imdb: Uint32Array
  nFamilies: number
  countries: Set<string>
  collections: Set<number>
}

const TAB = ['taste', 'ratings', 'franchises']
const SUBSET = ['notable', 'all']
const MONEY = ['usd2025', 'nominal']
const STORY = ['any', 'original', 'book', 'comic', 'true_story', 'stage', 'screen', 'other']
const STUDIO = ['any', 'major', 'independent']
const SOURCE = ['netflix', 'cinema', 'production']
const MAP_MODE = ['share', 'top', 'diff']
const TIMELINE = ['films', 'votes', 'revenue', 'netflix']
const FRANCHISE_Y = ['rating', 'revenue']

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b)

export function encodeHash(values: Values, base: Values, imdb: Uint32Array): string {
  const p = new URLSearchParams()
  const put = (key: string, differs: boolean, value: string) => {
    if (differs) p.set(key, value)
  }
  put('tab', values.tab !== base.tab, values.tab)
  put('yr', !same(values.yearRange, base.yearRange), values.yearRange.join('-'))
  put('g', values.family !== base.family, String(values.family))
  put('go', values.genreOnly !== base.genreOnly, values.genreOnly ? '1' : '0')
  put('sub', values.subset !== base.subset, values.subset)
  put('money', values.money !== base.money, values.money)
  put('st', values.story !== base.story, values.story)
  put('stu', values.studio !== base.studio, values.studio)
  put('src', values.source !== base.source, values.source)
  put('map', values.mapMode !== base.mapMode, values.mapMode)
  put('c', !same(values.countries, base.countries), values.countries.join('.'))
  put('tm', values.timelineMeasure !== base.timelineMeasure, values.timelineMeasure)
  put('x', values.x !== base.x, values.x)
  put('y', values.y !== base.y, values.y)
  put('size', values.size !== base.size, values.size ?? 'none')
  put('fr', values.franchise !== base.franchise, String(values.franchise))
  put('fy', values.franchiseY !== base.franchiseY, values.franchiseY)
  put('film', values.film !== base.film, values.film === null ? '' : fmtImdb(imdb[values.film]))
  put('sort', !same(values.sort, base.sort), `${values.sort.desc ? '-' : ''}${values.sort.key}`)
  put('cols', !same(values.columns, base.columns), values.columns.join('.'))
  return p.toString()
}

const oneOf = <T extends string>(list: readonly string[], v: string | null): T | undefined =>
  v !== null && list.includes(v) ? (v as T) : undefined

const isMeasure = (v: string): v is MeasureKey => (MEASURE_KEYS as string[]).includes(v)

function parseInt10(v: string | null): number | undefined {
  return v !== null && /^\d+$/.test(v) ? Number(v) : undefined
}

export function decodeHash(hash: string, ctx: HashContext): Partial<Values> {
  const p = new URLSearchParams(hash.replace(/^#/, ''))
  const out: Partial<Values> = {}

  const tab = oneOf<Values['tab']>(TAB, p.get('tab'))
  if (tab) out.tab = tab

  const yr = /^(\d+)-(\d+)$/.exec(p.get('yr') ?? '')
  if (yr) {
    const a = Number(yr[1])
    const b = Number(yr[2])
    if (a >= YEAR_MIN && b <= YEAR_MAX && a <= b) out.yearRange = [a, b]
  }
  const g = parseInt10(p.get('g'))
  if (g !== undefined && g < ctx.nFamilies) out.family = g
  const go = p.get('go')
  if (go === '1' || go === '0') out.genreOnly = go === '1'
  const sub = oneOf<Values['subset']>(SUBSET, p.get('sub'))
  if (sub) out.subset = sub
  const money = oneOf<Values['money']>(MONEY, p.get('money'))
  if (money) out.money = money
  const st = oneOf<Values['story']>(STORY, p.get('st'))
  if (st) out.story = st
  const stu = oneOf<Values['studio']>(STUDIO, p.get('stu'))
  if (stu) out.studio = stu
  const src = oneOf<Values['source']>(SOURCE, p.get('src'))
  if (src) out.source = src
  const map = oneOf<Values['mapMode']>(MAP_MODE, p.get('map'))
  if (map) out.mapMode = map
  const c = p.get('c')
  if (c) {
    const list = c.split('.')
    if (list.length <= MAX_COUNTRIES && list.every((iso2) => ctx.countries.has(iso2))) {
      out.countries = list
    }
  }
  const tm = oneOf<Values['timelineMeasure']>(TIMELINE, p.get('tm'))
  if (tm) out.timelineMeasure = tm
  const x = p.get('x')
  const y = p.get('y')
  const base = defaults()
  const hx = x !== null && isMeasure(x) ? x : undefined
  const hy = y !== null && isMeasure(y) ? y : undefined
  if ((hx ?? base.x) !== (hy ?? base.y)) {
    if (hx) out.x = hx
    if (hy) out.y = hy
  }
  const size = p.get('size')
  if (size === 'none') out.size = null
  else if (size !== null && isMeasure(size)) out.size = size
  const fr = parseInt10(p.get('fr'))
  if (fr !== undefined && ctx.collections.has(fr)) out.franchise = fr
  const fy = oneOf<Values['franchiseY']>(FRANCHISE_Y, p.get('fy'))
  if (fy) out.franchiseY = fy
  const film = /^tt(\d+)$/.exec(p.get('film') ?? '')
  if (film) {
    const row = ctx.imdb.indexOf(Number(film[1]))
    if (row >= 0) out.film = row
  }
  const sort = p.get('sort')
  if (sort) {
    const desc = sort.startsWith('-')
    const key = desc ? sort.slice(1) : sort
    if (key === 'title' || isMeasure(key)) out.sort = { key, desc } satisfies Sort
  }
  const cols = p.get('cols')
  if (cols) {
    const list = cols.split('.')
    if (list.every(isMeasure)) out.columns = list as MeasureKey[]
  }
  return out
}
