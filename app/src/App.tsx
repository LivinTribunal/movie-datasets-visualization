import { useEffect, useState } from 'react'
import { loadData } from './lib/data'
import type { AppData } from './lib/types'
import { DetailPanel } from './views/DetailPanel/DetailPanel'
import { FilmScatter } from './views/FilmScatter/FilmScatter'
import { FilterBar } from './views/FilterBar/FilterBar'
import { Franchise } from './views/Franchise/Franchise'
import { GenreTimeline } from './views/GenreTimeline/GenreTimeline'
import { WorldMap } from './views/WorldMap/WorldMap'

export default function App() {
  const [data, setData] = useState<AppData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData().then(setData, (e: unknown) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  if (error) return <p className="status">Error: {error}</p>
  if (!data) return <p className="status">Loading data…</p>

  return (
    <div className="app">
      <FilterBar data={data} />
      <main className="grid">
        <WorldMap data={data} />
        <GenreTimeline data={data} />
        <FilmScatter data={data} />
        <Franchise />
      </main>
      <DetailPanel data={data} />
    </div>
  )
}
