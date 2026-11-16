import type { FC } from 'react'
import { ChipGroup } from '../../components/ChipGroup'
import { loadText, useLazy } from '../../lib/data'
import { fmtImdb } from '../../lib/format'
import type { AppData } from '../../lib/types'
import { useStore } from '../../state/store'
import { Search } from './Search'
import { YearSlider } from './YearSlider'

const GENRE_MODE = [
  { value: 'highlight', label: 'Dimmed', title: 'Films of other genres are dimmed' },
  { value: 'filter', label: 'Hidden', title: 'Films of other genres are hidden' },
]
const SUBSET = [
  { value: 'notable', label: '10,000+ votes', title: '≥ 10,000 IMDb votes' },
  { value: 'all', label: '1,000+ votes', title: '≥ 1,000 IMDb votes' },
] as const
const MONEY = [
  { value: 'usd2025', label: '2025 dollars', title: 'inflation-adjusted to 2025 USD' },
  { value: 'nominal', label: 'As reported', title: 'as reported, not adjusted' },
] as const
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
      <div className="marquee">
        <h1>
          <img src="favicon.svg" alt="" width="24" height="24" />
          Movie Explorer
        </h1>
        <div className="tabs" role="tablist" aria-label="Workspace">
          {TABS.map((t) => (
            <button key={t.value} type="button" role="tab" aria-selected={tab === t.value} onClick={() => setTab(t.value)}>
              {t.label}
            </button>
          ))}
        </div>
        <div className="marquee-tools">
          <Search data={data} />
          <button type="button" className="btn" onClick={reset}>
            Reset filters
          </button>
          <button type="button" className="btn" onClick={() => setAbout(true)}>
            About the data
          </button>
        </div>
      </div>
      <div className="family-stripe" />
      <div className="filter-strip">
        <div className="filter-row">
          <ChipGroup
            label="Genre family"
            value={family}
            onChange={setFamily}
            options={data.families.map((f, i) => ({ value: i, label: f.name, colour: f.colour }))}
          />
          <div className="filter-group">
            <span className="group-label">Other genres</span>
            <ChipGroup
              label="Other genres"
              value={genreOnly ? 'filter' : 'highlight'}
              onChange={(v) => setGenreOnly(v === 'filter')}
              options={GENRE_MODE}
            />
          </div>
        </div>
        <div className="filter-row filter-row-2">
          <div className="filter-group">
            <span className="group-label">Years</span>
            <YearSlider />
          </div>
          <div className="filter-group">
            <span className="group-label">Films with</span>
            <ChipGroup label="Films with" value={subset} onChange={setSubset} options={[...SUBSET]} />
          </div>
          <div className="filter-group">
            <span className="group-label">Money in</span>
            <ChipGroup label="Money in" value={money} onChange={setMoney} options={[...MONEY]} />
          </div>
          <div className="selection">
            {!hasSelection && <span className="selection-hint">Nothing selected. Click a country, a dot, a row or a line.</span>}
            {countries.map((iso2) => {
              const name = data.countryByIso2.get(iso2)?.name ?? iso2
              return (
                <span key={iso2} className="country-chip">
                  <span title={name}>{name}</span>
                  <button type="button" aria-label={`Remove ${name}`} onClick={() => toggleCountry(iso2)}>
                    ×
                  </button>
                </span>
              )
            })}
            {franchise !== null && (
              <span className="country-chip">
                <button type="button" className="chip-name" onClick={() => setTab('franchises')}>
                  {data.franchises.collections.get(franchise) ?? 'franchise'}
                </button>
                <button type="button" aria-label="Clear franchise" onClick={() => setFranchise(null)}>
                  ×
                </button>
              </span>
            )}
            {film !== null && (
              <span className="country-chip">
                <button type="button" className="chip-name" onClick={() => setTab('ratings')}>
                  {text?.title[film] ?? fmtImdb(data.films.imdb[film])}
                </button>
                <button type="button" aria-label="Unpin film" onClick={() => setFilm(null)}>
                  ×
                </button>
              </span>
            )}
            {brush !== null && (
              <span className="country-chip">
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
