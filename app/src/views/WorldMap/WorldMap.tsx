import { useMemo } from 'react'
import { filmIndices } from '../../lib/filter'
import type { AppData } from '../../lib/types'
import { useStore } from '../../state/store'

export function WorldMap({ data }: { data: AppData }) {
  const { yearRange, subset, selectedCountry, setSelectedCountry } = useStore()
  const { films, countries, countryGenre } = data

  const sourceCounts = useMemo(() => {
    const seen = { netflix: new Set<string>(), lumiere: new Set<string>() }
    countryGenre.columns.source.forEach((s, i) => {
      if (s === 'netflix' || s === 'lumiere') seen[s].add(countryGenre.columns.country_iso2[i])
    })
    return { netflix: seen.netflix.size, lumiere: seen.lumiere.size }
  }, [countryGenre])
  const names = useMemo(
    () => new Map(countries.columns.iso2.map((c, i) => [c, countries.columns.name[i]])),
    [countries],
  )
  const top = useMemo(() => {
    const counts = new Map<string, number>()
    for (const i of filmIndices(films, { yearRange, subset, families: [], selectedCountry: null })) {
      for (const c of films.columns.countries[i]) counts.set(c, (counts.get(c) ?? 0) + 1)
    }
    return [...counts].sort((a, b) => b[1] - a[1]).slice(0, 10)
  }, [films, yearRange, subset])

  return (
    <section className="panel">
      <h2>World map</h2>
      <p>
        Netflix genre shares: {sourceCounts.netflix} countries · Cinema (LUMIERE, notable films only):{' '}
        {sourceCounts.lumiere} markets
      </p>
      <p>
        Selected: {selectedCountry ? (names.get(selectedCountry) ?? selectedCountry) : 'none'}{' '}
        {selectedCountry && <button type="button" onClick={() => setSelectedCountry(null)}>clear</button>}
      </p>
      <ul>
        {top.map(([c, n]) => (
          <li key={c} onClick={() => setSelectedCountry(c)}
            style={{ fontWeight: c === selectedCountry ? 'bold' : 'normal' }}>
            {names.get(c) ?? c}: {n} films
          </li>
        ))}
      </ul>
    </section>
  )
}
