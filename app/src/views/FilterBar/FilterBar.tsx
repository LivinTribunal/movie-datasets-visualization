import { useEffect, useRef } from 'react'
import type { FC } from 'react'
import { ChipGroup } from '../../components/ChipGroup'
import { loadText, useLazy } from '../../lib/data'
import { fmtImdb } from '../../lib/format'
import type { AppData } from '../../lib/types'
import { defaults, useStore } from '../../state/store'
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
const SKIP = new Set(['tab', 'hoverFilm', 'about'])
const TABS = [
  { value: 'taste', label: 'Taste by country' },
  { value: 'ratings', label: 'Money & ratings' },
  { value: 'franchises', label: 'Franchises' },
] as const

const FiltersMenu: FC = () => {
  const subset = useStore((s) => s.subset)
  const money = useStore((s) => s.money)
  const story = useStore((s) => s.story)
  const studio = useStore((s) => s.studio)
  const genreOnly = useStore((s) => s.genreOnly)
  const setSubset = useStore((s) => s.setSubset)
  const setMoney = useStore((s) => s.setMoney)
  const setStory = useStore((s) => s.setStory)
  const setStudio = useStore((s) => s.setStudio)
  const setGenreOnly = useStore((s) => s.setGenreOnly)
  const menu = useRef<HTMLDetailsElement | null>(null)
  const n = [subset !== 'notable', money !== 'usd2025', story !== 'any', studio !== 'any', genreOnly].filter(Boolean).length

  useEffect(() => {
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (!menu.current) return
      if (e instanceof KeyboardEvent ? e.key === 'Escape' : !menu.current.contains(e.target as Node)) {
        menu.current.open = false
      }
    }
    document.addEventListener('pointerdown', close, true)
    document.addEventListener('keydown', close)
    return () => {
      document.removeEventListener('pointerdown', close, true)
      document.removeEventListener('keydown', close)
    }
  }, [])

  return (
    <details ref={menu} className="filters-menu">
      <summary className="btn">
        More filters
        {n > 0 && <span className="badge">{n}</span>}
      </summary>
      <div className="filters-list">
        <div className="filters-row">
          <span className="group-label">Films</span>
          <ChipGroup label="Film subset" value={subset} onChange={setSubset} options={[...SUBSET]} />
        </div>
        <div className="filters-row">
          <span className="group-label">Money</span>
          <ChipGroup label="Money" value={money} onChange={setMoney} options={[...MONEY]} />
        </div>
        <div className="filters-row">
          <span className="group-label">Story</span>
          <select aria-label="Story source" value={story} onChange={(e) => setStory(e.target.value as typeof story)}>
            {STORY.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
        <div className="filters-row">
          <span className="group-label">Studio</span>
          <ChipGroup label="Studio" value={studio} onChange={setStudio} options={[...STUDIO]} />
        </div>
        <div className="filters-row">
          <span className="group-label">Genre</span>
          <ChipGroup
            label="Genre highlight or filter"
            value={genreOnly ? 'filter' : 'highlight'}
            onChange={(v) => setGenreOnly(v === 'filter')}
            options={GENRE_MODE}
          />
        </div>
      </div>
    </details>
  )
}

export const FilterBar: FC<{ data: AppData }> = ({ data }) => {
  const family = useStore((s) => s.family)
  const tab = useStore((s) => s.tab)
  const brush = useStore((s) => s.brush)
  const film = useStore((s) => s.film)
  const countries = useStore((s) => s.countries)
  const franchise = useStore((s) => s.franchise)
  const setFamily = useStore((s) => s.setFamily)
  const setTab = useStore((s) => s.setTab)
  const setBrush = useStore((s) => s.setBrush)
  const setFilm = useStore((s) => s.setFilm)
  const setFranchise = useStore((s) => s.setFranchise)
  const toggleCountry = useStore((s) => s.toggleCountry)
  const setAbout = useStore((s) => s.setAbout)
  const reset = useStore((s) => s.reset)
  const text = useLazy(loadText)
  const changed = useStore((s) => {
    const d = defaults() as unknown as Record<string, unknown>
    const cur = s as unknown as Record<string, unknown>
    return Object.keys(d).some((k) => !SKIP.has(k) && JSON.stringify(cur[k]) !== JSON.stringify(d[k]))
  })
  const hasSelection = countries.length > 0 || franchise !== null || film !== null || brush !== null

  return (
    <header className="filter-bar area-f">
      <div className="toolbar">
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
        <div className="toolbar-spacer" />
        <Search data={data} />
        <button type="button" className="btn icon-btn" aria-label="About" title="About this app" onClick={() => setAbout(true)}>
          ?
        </button>
      </div>
      <div className="legend-strip">
        <div className="strip-group">
          <span className="group-label">Years</span>
          <YearSlider />
        </div>
        <span className="strip-divider" aria-hidden="true" />
        <div className="strip-group">
          <span className="group-label">Genre</span>
          <ChipGroup
            label="Genre family"
            value={family}
            onChange={setFamily}
            options={data.families.map((f, i) => ({ value: i, label: f.name, colour: f.colour }))}
          />
        </div>
        <FiltersMenu />
        <div className="strip-end">
          {hasSelection && (
            <div className="selection">
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
            </div>
          )}
          {changed && (
            <button type="button" className="btn-text" onClick={reset}>
              Reset
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
