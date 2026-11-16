import { useEffect, useState } from 'react'
import { useStore } from './state/store'
import { loadData } from './lib/data'
import type { AppData } from './lib/types'
import { startHashSync } from './state/hashSync'
import { About } from './views/About/About'
import { FilmCard } from './views/FilmCard/FilmCard'
import { FilmScatter } from './views/FilmScatter/FilmScatter'
import { FilterBar } from './views/FilterBar/FilterBar'
import { SelectionTable } from './views/SelectionTable/SelectionTable'
import { Franchise } from './views/Franchise/Franchise'
import { GenreTimeline } from './views/GenreTimeline/GenreTimeline'
import { WorldMap } from './views/WorldMap/WorldMap'

export default function App() {
  const [data, setData] = useState<AppData | null>(null)
  const tab = useStore((s) => s.tab)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData().then(setData, (e: unknown) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  useEffect(() => (data ? startHashSync(data) : undefined), [data])

  if (!data) {
    return (
      <div className="app">
        <header className="panel filter-bar area-f">
          <h1>
          <img src="favicon.svg" alt="" width="24" height="24" />
          Movie Explorer
        </h1>
          <p className="status">{error ? `Error: ${error}` : 'Loading data…'}</p>
        </header>
      </div>
    )
  }

  return (
    <div className="app">
      <FilterBar data={data} />
      <main key={tab} className="workspace" data-tab={tab}>
        {tab === 'taste' && (
          <>
            <WorldMap data={data} />
            <GenreTimeline data={data} />
            <SelectionTable data={data} />
          </>
        )}
        {tab === 'ratings' && (
          <>
            <FilmScatter data={data} />
            <SelectionTable data={data} />
            <FilmCard data={data} />
          </>
        )}
        {tab === 'franchises' && (
          <>
            <Franchise data={data} />
            <FilmScatter data={data} />
            <FilmCard data={data} />
          </>
        )}
      </main>
      <About data={data} />
    </div>
  )
}
