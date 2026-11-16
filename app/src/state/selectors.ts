import { filmMask } from '../lib/filter'
import { memoLast } from '../lib/memo'
import type { AppData, Films } from '../lib/types'
import { useStore, type Story, type Studio } from './store'

type Subset = 'notable' | 'all'

// One memo per variant, module-level, so every caller shares the cached mask.
const withYears = memoLast(
  (films: Films, yearRange: [number, number], subset: Subset, countries: string[], genreOnly: boolean, family: number, story: Story, studio: Studio) =>
    filmMask(films, { yearRange, subset, countries, genreOnly, family, story, studio }),
)
const allYears = memoLast((films: Films, subset: Subset, countries: string[], family: number, story: Story, studio: Studio) =>
  filmMask(films, { yearRange: null, subset, countries, genreOnly: false, family, story, studio }),
)

/** Film mask for the current filters. Panels C, D and E use it. */
export function useFilmMask(data: AppData): Uint8Array {
  const yearRange = useStore((s) => s.yearRange)
  const subset = useStore((s) => s.subset)
  const countries = useStore((s) => s.countries)
  const genreOnly = useStore((s) => s.genreOnly)
  const family = useStore((s) => s.family)
  const story = useStore((s) => s.story)
  const studio = useStore((s) => s.studio)
  return withYears(data.films, yearRange, subset, countries, genreOnly, family, story, studio)
}

/** Same without the year range and without genreOnly (story and studio still filter). Panel B uses it. */
export function useFilmMaskAllYears(data: AppData): Uint8Array {
  const subset = useStore((s) => s.subset)
  const countries = useStore((s) => s.countries)
  const family = useStore((s) => s.family)
  const story = useStore((s) => s.story)
  const studio = useStore((s) => s.studio)
  return allYears(data.films, subset, countries, family, story, studio)
}
