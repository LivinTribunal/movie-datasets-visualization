import { familyList } from '../../lib/families'
import type { AppData } from '../../lib/types'
import { useStore } from '../../state/store'

export function FilterBar({ data }: { data: AppData }) {
  const { yearRange, families, subset, hoveredFamily } = useStore()
  const { setYearRange, setFamilies, setSubset, reset } = useStore.getState()
  const list = familyList(data.genreFamilies)

  const toggle = (f: string) =>
    setFamilies(families.includes(f) ? families.filter((x) => x !== f) : [...families, f])

  return (
    <header className="filter-bar">
      <label>
        Years{' '}
        <input type="number" value={yearRange[0]} min={1900} max={yearRange[1]}
          onChange={(e) => setYearRange([Number(e.target.value), yearRange[1]])} />
        {' – '}
        <input type="number" value={yearRange[1]} min={yearRange[0]} max={2026}
          onChange={(e) => setYearRange([yearRange[0], Number(e.target.value)])} />
      </label>
      {list.map(({ family, colour }) => (
        <label key={family} style={{ fontWeight: hoveredFamily === family ? 'bold' : 'normal' }}>
          <input type="checkbox" checked={families.includes(family)} onChange={() => toggle(family)} />
          <span className="swatch" style={{ background: colour }} />
          {family}
        </label>
      ))}
      <label>
        <input type="checkbox" checked={subset === 'notable'}
          onChange={(e) => setSubset(e.target.checked ? 'notable' : 'working')} />
        Notable only (≥ 10,000 votes)
      </label>
      <button type="button" onClick={reset}>Reset</button>
    </header>
  )
}
