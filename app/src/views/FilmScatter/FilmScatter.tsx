import { useMemo } from 'react'
import { filmIndices } from '../../lib/filter'
import type { AppData } from '../../lib/types'
import { useStore } from '../../state/store'

export function FilmScatter({ data }: { data: AppData }) {
  const { yearRange, families, subset, selectedCountry, selectedFilm, setSelectedFilm } = useStore()
  const { films } = data

  const matches = useMemo(
    () => filmIndices(films, { yearRange, families, subset, selectedCountry }),
    [films, yearRange, families, subset, selectedCountry],
  )
  const top = useMemo(() => {
    const votes = films.columns.imdb_votes
    return [...matches].sort((a, b) => (votes[b] ?? 0) - (votes[a] ?? 0)).slice(0, 10)
  }, [films, matches])

  return (
    <section className="panel">
      <h2>Film scatter</h2>
      <p>{matches.length.toLocaleString('en')} films match</p>
      <ul>
        {top.map((i) => {
          const id = films.columns.imdb_id[i]
          return (
            <li key={id} onClick={() => setSelectedFilm(id)}
              style={{ fontWeight: id === selectedFilm ? 'bold' : 'normal' }}>
              {films.columns.title[i]} ({films.columns.year[i]})
            </li>
          )
        })}
      </ul>
    </section>
  )
}
