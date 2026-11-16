import type { FC } from 'react'
import { ChipGroup } from '../../components/ChipGroup'
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
  { value: 'usd2025', label: '2025 USD' },
  { value: 'nominal', label: 'nominal' },
] as const
const SOURCE = [
  { value: 'netflix', label: 'Netflix' },
  { value: 'cinema', label: 'Cinema' },
  { value: 'production', label: 'Made here' },
] as const

const Group: FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div className="group">
    <span className="group-label">{label}</span>
    {children}
  </div>
)

export const FilterBar: FC<{ data: AppData }> = ({ data }) => {
  const family = useStore((s) => s.family)
  const genreOnly = useStore((s) => s.genreOnly)
  const subset = useStore((s) => s.subset)
  const money = useStore((s) => s.money)
  const source = useStore((s) => s.source)
  const countries = useStore((s) => s.countries)
  const setFamily = useStore((s) => s.setFamily)
  const setGenreOnly = useStore((s) => s.setGenreOnly)
  const setSubset = useStore((s) => s.setSubset)
  const setMoney = useStore((s) => s.setMoney)
  const setSource = useStore((s) => s.setSource)
  const toggleCountry = useStore((s) => s.toggleCountry)
  const setAbout = useStore((s) => s.setAbout)
  const reset = useStore((s) => s.reset)

  return (
    <header className="panel filter-bar area-f">
      <h1>Movie Explorer</h1>
      <Group label="years">
        <YearSlider />
      </Group>
      <Group label="genre">
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
      </Group>
      <Group label="films">
        <ChipGroup label="Film subset" value={subset} onChange={setSubset} options={[...SUBSET]} />
      </Group>
      <Group label="money">
        <ChipGroup label="Money" value={money} onChange={setMoney} options={[...MONEY]} />
      </Group>
      <Group label="map">
        <ChipGroup label="Map source" value={source} onChange={setSource} options={[...SOURCE]} />
      </Group>
      <Search data={data} />
      {countries.map((iso2) => {
        const name = data.countryByIso2.get(iso2)?.name ?? iso2
        return (
          <span key={iso2} className="country-chip">
            {name}
            <button type="button" aria-label={`Remove ${name}`} onClick={() => toggleCountry(iso2)}>
              ×
            </button>
          </span>
        )
      })}
      <button type="button" className="btn" onClick={reset}>
        Reset
      </button>
      <button type="button" className="btn" onClick={() => setAbout(true)}>
        About the data
      </button>
    </header>
  )
}
