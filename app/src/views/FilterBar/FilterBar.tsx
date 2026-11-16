import type { FC } from 'react'
import { ChipGroup } from '../../components/ChipGroup'
import { loadText, useLazy } from '../../lib/data'
import { fmtImdb } from '../../lib/format'
import type { AppData } from '../../lib/types'
import { useStore } from '../../state/store'
import { Search } from './Search'
import { YearSlider } from './YearSlider'

const GENRE_MODE = [
  { value: 'highlight', label: 'highlight', title: 'The genre only highlights films' },
  { value: 'filter', label: 'filter', title: 'The genre also filters films' },
]
const SUBSET = [
  { value: 'notable', label: 'notable', title: '≥ 10,000 IMDb votes' },
  { value: 'all', label: 'all', title: '≥ 1,000 IMDb votes' },
] as const
const MONEY = [
  { value: 'usd2025', label: '2025 USD', title: 'inflation-adjusted to 2025 USD' },
  { value: 'nominal', label: 'nominal', title: 'as reported, not adjusted' },
] as const
const STUDIO = [
  { value: 'any', label: 'any', title: 'any studio' },
  { value: 'major', label: 'major', title: 'Disney, Warner Bros., Universal, Sony, Paramount, 20th Century Fox, Lionsgate or MGM' },
  { value: 'independent', label: 'indie', title: 'any other studio' },
] as const
const STORY = [
  ['any', 'any story'], ['original', 'original'], ['book', 'book'], ['comic', 'comic'],
  ['true_story', 'true story'], ['stage', 'stage'], ['screen', 'film/TV'], ['other', 'other'],
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
  const story = useStore((s) => s.story)
  const studio = useStore((s) => s.studio)
  const setStory = useStore((s) => s.setStory)
  const setStudio = useStore((s) => s.setStudio)
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
    <header className="panel filter-bar area-f">
      <div className="filter-row">
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
        <Search data={data} />
        <div className="filter-spacer">
          <YearSlider />
          <ChipGroup label="Film subset" value={subset} onChange={setSubset} options={[...SUBSET]} />
          <ChipGroup label="Money" value={money} onChange={setMoney} options={[...MONEY]} />
          <select aria-label="Story source" value={story} onChange={(e) => setStory(e.target.value as typeof story)}>
            {STORY.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <ChipGroup label="Studio" value={studio} onChange={setStudio} options={[...STUDIO]} />
          <button type="button" className="btn" onClick={reset}>
            Reset
          </button>
          <button type="button" className="btn" onClick={() => setAbout(true)}>
            About
          </button>
        </div>
      </div>
      <div className="filter-row filter-row-groups">
          <ChipGroup
            label="Genre family"
            value={family}
            onChange={setFamily}
            options={data.families.map((f, i) => ({ value: i, label: f.name, colour: f.colour }))}
          />
          <ChipGroup
            label="Genre highlight or filter"
            value={genreOnly ? 'filter' : 'highlight'}
            onChange={(v) => setGenreOnly(v === 'filter')}
            options={GENRE_MODE}
          />
        <div className="selection">
          <span className="group-label">selection</span>
          {!hasSelection && <span className="selection-hint">nothing yet: click a country, a point, a table row or a franchise line</span>}
          <>
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
                <span>scatter brush</span>
                <button type="button" aria-label="Clear brush" onClick={() => setBrush(null)}>
                  ×
                </button>
              </span>
            )}
          </>
        </div>
      </div>
    </header>
  )
}
