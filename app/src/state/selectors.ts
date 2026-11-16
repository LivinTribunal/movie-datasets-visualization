import { filmMask } from '../lib/filter'
import { memoLast } from '../lib/memo'
import type { AppData, Films } from '../lib/types'
import { useStore } from './store'

type Subset = 'notable' | 'all'

// One memo per variant, module-level, so every caller shares the cached mask.
const withYears = memoLast(
  (films: Films, yearRange: [number, number], subset: Subset, countries: string[], genreOnly: boolean, family: number) =>
    filmMask(films, { yearRange, subset, countries, genreOnly, family }),
)
const allYears = memoLast((films: Films, subset: Subset, countries: string[], family: number) =>
  filmMask(films, { yearRange: null, subset, countries, genreOnly: false, family }),
)

/** Film mask for the current filters. Panels C, D and E use it. */
export function useFilmMask(data: AppData): Uint8Array {
  const yearRange = useStore((s) => s.yearRange)
  const subset = useStore((s) => s.subset)
  const countries = useStore((s) => s.countries)
  const genreOnly = useStore((s) => s.genreOnly)
  const family = useStore((s) => s.family)
  return withYears(data.films, yearRange, subset, countries, genreOnly, family)
}

/** Same without the year range and without genreOnly. Panel B uses it. */
export function useFilmMaskAllYears(data: AppData): Uint8Array {
  const subset = useStore((s) => s.subset)
  const countries = useStore((s) => s.countries)
  const family = useStore((s) => s.family)
  return allYears(data.films, subset, countries, family)
}
