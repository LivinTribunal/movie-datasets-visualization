import type { Films } from './types'

export type StoryCategory = 'original' | 'book' | 'comic' | 'true_story' | 'stage' | 'screen' | 'other'

export interface FilmFilter {
  yearRange: [number, number] | null
  subset: 'notable' | 'all'
  countries: string[]
  genreOnly: boolean
  family: number
  story: 'any' | StoryCategory
  studio: 'any' | 'major' | 'independent'
}

/** 1 = the film passes. */
export function filmMask(films: Films, f: FilmFilter): Uint8Array {
  const { year, family_mask, countries, story_source, studio } = films
  const out = new Uint8Array(films.rows)
  const end = f.subset === 'notable' ? Math.min(films.notable, films.rows) : films.rows
  const wanted = new Uint8Array(countries.values.length)
  for (const iso of f.countries) {
    const code = countries.values.indexOf(iso)
    if (code >= 0) wanted[code] = 1
  }
  const byCountry = f.countries.length > 0
  const familyBit = 1 << f.family
  const storyCode = f.story === 'any' ? -1 : story_source.values.indexOf(f.story)
  const indieCode = studio.values.indexOf('independent')
  for (let i = 0; i < end; i++) {
    if (f.yearRange && (year[i] < f.yearRange[0] || year[i] > f.yearRange[1])) continue
    if (f.genreOnly && (family_mask[i] & familyBit) === 0) continue
    if (f.story !== 'any' && story_source.codes[i] !== storyCode) continue
    if (f.studio !== 'any') {
      const code = studio.codes[i]
      if (code === studio.nullCode || (code === indieCode) !== (f.studio === 'independent')) continue
    }
    if (byCountry) {
      let hit = false
      for (let k = countries.offsets[i]; k < countries.offsets[i + 1]; k++) {
        if (wanted[countries.codes[k]]) { hit = true; break }
      }
      if (!hit) continue
    }
    out[i] = 1
  }
  return out
}

export function countMask(mask: Uint8Array): number {
  let n = 0
  for (let i = 0; i < mask.length; i++) n += mask[i]
  return n
}
