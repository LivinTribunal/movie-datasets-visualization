import { useEffect, useState } from 'react'
import { loadData } from './lib/data'
import type { AppData } from './lib/types'
import { FilmCard } from './views/FilmCard/FilmCard'
import { FilmScatter } from './views/FilmScatter/FilmScatter'
import { FilterBar } from './views/FilterBar/FilterBar'
import { SelectionTable } from './views/SelectionTable/SelectionTable'
import { Franchise } from './views/Franchise/Franchise'
import { GenreTimeline } from './views/GenreTimeline/GenreTimeline'
import { WorldMap } from './views/WorldMap/WorldMap'

export default function App() {
  const [data, setData] = useState<AppData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData().then(setData, (e: unknown) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  if (!data) {
    return (
      <div className="app">
        <header className="panel filter-bar area-f">
          <h1>Movie Explorer</h1>
          <p className="status">{error ? `Error: ${error}` : 'Loading data…'}</p>
        </header>
      </div>
    )
  }

  return (
    <div className="app">
      <FilterBar data={data} />
      <WorldMap data={data} />
      <GenreTimeline data={data} />
      <FilmScatter data={data} />
      <Franchise data={data} />
      <SelectionTable data={data} />
      <FilmCard data={data} />
    </div>
  )
}
