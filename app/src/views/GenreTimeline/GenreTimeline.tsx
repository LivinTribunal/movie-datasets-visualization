import { useMemo } from 'react'
import { familyList } from '../../lib/families'
import type { AppData } from '../../lib/types'
import { useStore } from '../../state/store'

export function GenreTimeline({ data }: { data: AppData }) {
  const { yearRange, subset, hoveredFamily, setHoveredFamily } = useStore()
  const { genreYear, genreFamilies } = data

  const rows = useMemo(() => {
    const sums = new Map<string, number>()
    const { subset: s, year, family, films } = genreYear.columns
    for (let i = 0; i < year.length; i++) {
      if (s[i] !== subset || year[i] < yearRange[0] || year[i] > yearRange[1]) continue
      sums.set(family[i], (sums.get(family[i]) ?? 0) + films[i])
    }
    return familyList(genreFamilies).map((f) => ({ ...f, films: sums.get(f.family) ?? 0 }))
  }, [genreYear, genreFamilies, yearRange, subset])

  return (
    <section className="panel">
      <h2>Genre timeline</h2>
      <p>Weighted film count per family, {yearRange[0]}–{yearRange[1]}</p>
      <ul>
        {rows.map((r) => (
          <li key={r.family} onMouseEnter={() => setHoveredFamily(r.family)}
            onMouseLeave={() => setHoveredFamily(null)}
            style={{ fontWeight: hoveredFamily === r.family ? 'bold' : 'normal' }}>
            <span className="swatch" style={{ background: r.colour }} />
            {r.family}: {Math.round(r.films).toLocaleString('en')}
          </li>
        ))}
      </ul>
    </section>
  )
}
