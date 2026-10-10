import type { Columnar, FilmRow } from './types'

export interface FilmFilter {
  yearRange: [number, number]
  families: string[]
  subset: 'notable' | 'working'
  selectedCountry: string | null
}

export function filmIndices(films: Columnar<FilmRow>, f: FilmFilter): number[] {
  const { year, notable, families, countries } = films.columns
  const out: number[] = []
  for (let i = 0; i < year.length; i++) {
    const y = year[i]
    if (y === null || y < f.yearRange[0] || y > f.yearRange[1]) continue
    if (f.subset === 'notable' && !notable[i]) continue
    if (f.families.length > 0 && !families[i].some((x) => f.families.includes(x))) continue
    if (f.selectedCountry !== null && !countries[i].includes(f.selectedCountry)) continue
    out.push(i)
  }
  return out
}
