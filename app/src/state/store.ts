import { create } from 'zustand'
import type { MeasureKey, Money } from '../lib/measures'

export type { Money }
export type Subset = 'notable' | 'all'
export type Source = 'netflix' | 'cinema' | 'production'
export type MapMode = 'share' | 'top' | 'diff'
export type TimelineMeasure = 'films' | 'votes' | 'revenue' | 'netflix'
export type FranchiseY = 'rating' | 'revenue'
export type Brush = [number, number, number, number]
export type Sort = { key: MeasureKey | 'title'; desc: boolean }

export const YEAR_MIN = 1900
export const YEAR_MAX = 2026
export const MAX_COUNTRIES = 6

interface Values {
  yearRange: [number, number]
  /** Index into meta.families; always one. */
  family: number
  /** false: the genre highlights. true: it also filters films. */
  genreOnly: boolean
  subset: Subset
  money: Money
  source: Source
  mapMode: MapMode
  /** ISO-2, at most MAX_COUNTRIES. */
  countries: string[]
  timelineMeasure: TimelineMeasure
  x: MeasureKey
  y: MeasureKey
  size: MeasureKey | null
  /** x0, x1, y0, y1 in data units. */
  brush: Brush | null
  /** collection_id */
  franchise: number | null
  franchiseY: FranchiseY
  /** Pinned film row. */
  film: number | null
  hoverFilm: number | null
  sort: Sort
  columns: MeasureKey[]
  about: boolean
}

interface Actions {
  setYearRange: (r: [number, number]) => void
  setFamily: (family: number) => void
  setGenreOnly: (genreOnly: boolean) => void
  setSubset: (subset: Subset) => void
  setMoney: (money: Money) => void
  setSource: (source: Source) => void
  setMapMode: (mapMode: MapMode) => void
  toggleCountry: (iso2: string) => void
  setTimelineMeasure: (m: TimelineMeasure) => void
  setX: (x: MeasureKey) => void
  setY: (y: MeasureKey) => void
  setSize: (size: MeasureKey | null) => void
  setBrush: (brush: Brush | null) => void
  setFranchise: (id: number | null) => void
  setFranchiseY: (y: FranchiseY) => void
  setFilm: (row: number | null) => void
  setHoverFilm: (row: number | null) => void
  setSort: (sort: Sort) => void
  setColumns: (columns: MeasureKey[]) => void
  setAbout: (about: boolean) => void
  reset: () => void
}

export type State = Values & Actions

const initial = (): Values => ({
  yearRange: [1990, 2026],
  family: 0,
  genreOnly: false,
  subset: 'notable',
  money: 'usd2025',
  source: 'netflix',
  mapMode: 'share',
  countries: [],
  timelineMeasure: 'votes',
  x: 'tomatometer',
  y: 'audience',
  size: 'votes',
  brush: null,
  franchise: null,
  franchiseY: 'rating',
  film: null,
  hoverFilm: null,
  sort: { key: 'votes', desc: true },
  columns: ['year', 'tomatometer', 'audience', 'gap', 'budget', 'revenue'],
  about: false,
})

const clampYear = (y: number) => Math.min(YEAR_MAX, Math.max(YEAR_MIN, y))

export const useStore = create<State>()((set) => ({
  ...initial(),
  setYearRange: ([a, b]) => {
    const from = clampYear(a)
    const to = clampYear(b)
    set({ yearRange: [Math.min(from, to), Math.max(from, to)] })
  },
  setFamily: (family) => set({ family }),
  setGenreOnly: (genreOnly) => set({ genreOnly }),
  setSubset: (subset) => set({ subset }),
  setMoney: (money) => set({ money }),
  setSource: (source) => set({ source }),
  setMapMode: (mapMode) => set({ mapMode }),
  toggleCountry: (iso2) =>
    set((s) => {
      if (s.countries.includes(iso2)) return { countries: s.countries.filter((c) => c !== iso2) }
      if (s.countries.length >= MAX_COUNTRIES) return {}
      return { countries: [...s.countries, iso2] }
    }),
  setTimelineMeasure: (timelineMeasure) => set({ timelineMeasure }),
  setX: (x) => set((s) => (x === s.y ? {} : { x, brush: null })),
  setY: (y) => set((s) => (y === s.x ? {} : { y, brush: null })),
  setSize: (size) => set({ size }),
  setBrush: (brush) => set({ brush }),
  setFranchise: (franchise) => set({ franchise }),
  setFranchiseY: (franchiseY) => set({ franchiseY }),
  setFilm: (film) => set({ film }),
  setHoverFilm: (hoverFilm) => set({ hoverFilm }),
  setSort: (sort) => set({ sort }),
  setColumns: (columns) => set({ columns }),
  setAbout: (about) => set({ about }),
  reset: () => set(initial()),
}))
