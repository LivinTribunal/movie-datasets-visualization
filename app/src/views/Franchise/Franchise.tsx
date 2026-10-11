import { useMemo } from 'react'
import { filmIndices } from '../../lib/filter'
import type { AppData } from '../../lib/types'
import { useStore } from '../../state/store'

export function Franchise({ data }: { data: AppData }) {
  const { yearRange, subset, families, selectedCountry } = useStore()
  const { films, franchises } = data

  const total = useMemo(() => new Set(franchises.columns.collection_id).size, [franchises])
  const top = useMemo(() => {
    const shown = new Set(
      filmIndices(films, { yearRange, subset, families, selectedCountry }).map(
        (i) => films.columns.imdb_id[i],
      ),
    )
    const { collection_id, collection_name, n_released, installment, imdb_id, imdb_100_vs_first } =
      franchises.columns
    const rows = new Map<number, { name: string; n: number; change: number | null; match: boolean }>()
    for (let i = 0; i < collection_id.length; i++) {
      const row = rows.get(collection_id[i]) ?? {
        name: collection_name[i], n: n_released[i], change: null, match: false,
      }
      const id = imdb_id[i]
      if (id !== null && shown.has(id)) row.match = true
      if (installment[i] === 2) row.change = imdb_100_vs_first[i]
      rows.set(collection_id[i], row)
    }
    return [...rows]
      .filter(([, r]) => r.match)
      .sort((a, b) => b[1].n - a[1].n)
      .slice(0, 10)
  }, [films, franchises, yearRange, subset, families, selectedCountry])

  return (
    <section className="panel">
      <h2>Franchises</h2>
      <p>{total} franchises (≥ 3 released films)</p>
      <ul>
        {top.map(([id, r]) => (
          <li key={id}>
            {r.name}: {r.n} films, IMDb change from film 1 to film 2:{' '}
            {r.change === null ? 'n/a' : `${r.change > 0 ? '+' : ''}${r.change.toFixed(1)} points`}
          </li>
        ))}
      </ul>
    </section>
  )
}
