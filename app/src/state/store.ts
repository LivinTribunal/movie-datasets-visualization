import { create } from 'zustand'

export type Subset = 'notable' | 'working'

interface State {
  yearRange: [number, number]
  families: string[]
  subset: Subset
  selectedCountry: string | null
  selectedFilm: string | null
  hoveredFamily: string | null
  setYearRange: (r: [number, number]) => void
  setFamilies: (f: string[]) => void
  setSubset: (s: Subset) => void
  setSelectedCountry: (c: string | null) => void
  setSelectedFilm: (id: string | null) => void
  setHoveredFamily: (f: string | null) => void
  reset: () => void
}

const initial = {
  yearRange: [1900, 2026] as [number, number],
  families: [] as string[],
  subset: 'notable' as Subset,
  selectedCountry: null as string | null,
  selectedFilm: null as string | null,
  hoveredFamily: null as string | null,
}

export const useStore = create<State>()((set) => ({
  ...initial,
  setYearRange: (yearRange) => set({ yearRange }),
  setFamilies: (families) => set({ families }),
  setSubset: (subset) => set({ subset }),
  setSelectedCountry: (selectedCountry) => set({ selectedCountry }),
  setSelectedFilm: (selectedFilm) => set({ selectedFilm }),
  setHoveredFamily: (hoveredFamily) => set({ hoveredFamily }),
  reset: () => set(initial),
}))
