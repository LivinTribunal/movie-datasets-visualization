import type { FC } from 'react'
import { ChipGroup } from '../../components/ChipGroup'
import { loadText, useLazy } from '../../lib/data'
import { fmtImdb } from '../../lib/format'
import type { AppData } from '../../lib/types'
import { useStore } from '../../state/store'
import { Search } from './Search'
import { YearSlider } from './YearSlider'

const TABS = [
  { value: 'taste', label: 'Taste by country' },
  { value: 'ratings', label: 'Money & ratings' },
  { value: 'franchises', label: 'Franchises' },
] as const

export const FilterBar: FC<{ data: AppData }> = ({ data }) => {
  const family = useStore((s) => s.family)
  const genreOnly = useStore((s) => s.genreOnly)
  const subset = useStore((s) => s.subset)
  const money = useStore((s) => s.money)
  const tab = useStore((s) => s.tab)
  const brush = useStore((s) => s.brush)
  const film = useStore((s) => s.film)
  const countries = useStore((s) => s.countries)
  const franchise = useStore((s) => s.franchise)
  const setFamily = useStore((s) => s.setFamily)
  const setGenreOnly = useStore((s) => s.setGenreOnly)
  const setSubset = useStore((s) => s.setSubset)
  const setMoney = useStore((s) => s.setMoney)
  const setTab = useStore((s) => s.setTab)
  const setBrush = useStore((s) => s.setBrush)
  const setFilm = useStore((s) => s.setFilm)
  const setFranchise = useStore((s) => s.setFranchise)
  const toggleCountry = useStore((s) => s.toggleCountry)
  const setAbout = useStore((s) => s.setAbout)
  const reset = useStore((s) => s.reset)
  const text = useLazy(loadText)
  const hasSelection = countries.length > 0 || franchise !== null || film !== null || brush !== null

  return (
    <header className="area-f">
      <div className="app-head">
        <h1>
          <img src="favicon.svg" alt="" width="16" height="16" />
          Movie Explorer
        </h1>
        <div className="tabs" role="tablist" aria-label="Workspace">
          {TABS.map((t) => (
            <button key={t.value} type="button" role="tab" aria-selected={tab === t.value} onClick={() => setTab(t.value)}>
              {t.label}
            </button>
          ))}
        </div>
        <div className="head-tools">
          <Search data={data} />
          <button type="button" className="text-btn" onClick={reset}>
            Reset
          </button>
          <button type="button" className="text-btn" onClick={() => setAbout(true)}>
            About
          </button>
        </div>
      </div>
      <div className="filter-strip">
        <div className="filter-row">
          <ChipGroup
            label="Genre family"
            value={family}
            onChange={setFamily}
            options={data.families.map((f, i) => ({ value: i, label: f.name, colour: f.colour }))}
          />
        </div>
        <div className="filter-row filter-row-2">
          <div className="filter-group">
            <span className="group-label">Years</span>
            <YearSlider />
          </div>
          <label className="check">
            <input type="checkbox" checked={genreOnly} onChange={(e) => setGenreOnly(e.target.checked)} />
            Only this genre
          </label>
          <label className="check">
            <input type="checkbox" checked={subset === 'all'} onChange={(e) => setSubset(e.target.checked ? 'all' : 'notable')} />
            Include films under 10,000 votes
          </label>
          <label className="filter-group">
            <span className="group-label">Money</span>
            <select value={money} onChange={(e) => setMoney(e.target.value as typeof money)}>
              <option value="usd2025">2025 USD</option>
              <option value="nominal">Nominal USD</option>
            </select>
          </label>
          <div className="selection">
            {hasSelection && <span>Selected:</span>}
            {countries.map((iso2) => {
              const name = data.countryByIso2.get(iso2)?.name ?? iso2
              return (
                <span key={iso2} className="sel-item">
                  <span title={name}>{name}</span>
                  <button type="button" aria-label={`Remove ${name}`} onClick={() => toggleCountry(iso2)}>
                    ×
                  </button>
                </span>
              )
            })}
            {franchise !== null && (
              <span className="sel-item">
                <button type="button" className="chip-name" onClick={() => setTab('franchises')}>
                  {data.franchises.collections.get(franchise) ?? 'franchise'}
                </button>
                <button type="button" aria-label="Clear franchise" onClick={() => setFranchise(null)}>
                  ×
                </button>
              </span>
            )}
            {film !== null && (
              <span className="sel-item">
                <button type="button" className="chip-name" onClick={() => setTab('ratings')}>
                  {text?.title[film] ?? fmtImdb(data.films.imdb[film])}
                </button>
                <button type="button" aria-label="Unpin film" onClick={() => setFilm(null)}>
                  ×
                </button>
              </span>
            )}
            {brush !== null && (
              <span className="sel-item">
                <span>Scatter brush</span>
                <button type="button" aria-label="Remove scatter brush" onClick={() => setBrush(null)}>
                  ×
                </button>
              </span>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
