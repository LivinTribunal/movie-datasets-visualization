import { useEffect, useRef, type FC } from 'react'
import { fmtInt } from '../../lib/format'
import type { AppData } from '../../lib/types'
import { useStore } from '../../state/store'
import './about.css'

const SOURCE_LABEL: Record<string, string> = { netflix: 'Netflix', cinema: 'Cinema', production: 'Made here' }
const LABEL: Record<string, string> = {
  tmdb_imdb: 'TMDB and IMDb',
  netflix: 'Netflix Top 10 up to',
  films: 'films (at least 1,000 IMDb votes)',
  notable: 'notable films (at least 10,000 IMDb votes)',
  with_budget: 'films with a budget',
  with_revenue: 'films with box office',
  with_gap: 'films with a critic and an audience score',
  netflix_countries: 'countries with Netflix charts',
  cinema_markets: 'cinema markets',
  production_countries: 'countries that produced a film',
  franchises: 'franchises with 3 or more released films',
}
const readable = (key: string) => LABEL[key] ?? key.replace(/_/g, ' ')

export const About: FC<{ data: AppData }> = ({ data }) => {
  const open = useStore((s) => s.about)
  const setAbout = useStore((s) => s.setAbout)
  const ref = useRef<HTMLDialogElement>(null)
  const { snapshots, base_year, counts, notes, attribution, sources } = data.meta

  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (open && !d.open) d.showModal()
    if (!open && d.open) d.close()
  }, [open])

  return (
    <dialog ref={ref} className="about" onClose={() => setAbout(false)}>
      <h2>About the data</h2>
      <p>
        Snapshots:{' '}
        {Object.entries(snapshots).map(([k, v]) => `${readable(k)} ${v}`).join(' · ')}. Money in 2025 USD uses
        CPI to the base year {base_year}.
      </p>
      <table>
        <tbody>
          {Object.entries(counts).map(([k, v]) => (
            <tr key={k}>
              <th scope="row">{readable(k)}</th>
              <td>{fmtInt(v)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3>Map sources</h3>
      <ul>
        {Object.entries(sources).map(([k, v]) => (
          <li key={k}>
            <strong>{SOURCE_LABEL[k] ?? k}:</strong> {v}
          </li>
        ))}
      </ul>
      <h3>How the data was transformed</h3>
      <ul>
        {notes.map((n) => (
          <li key={n}>{n}</li>
        ))}
      </ul>
      <h3>Attribution</h3>
      <ul>
        {attribution.map((a) => (
          <li key={a}>{a}</li>
        ))}
      </ul>
      <button type="button" onClick={() => setAbout(false)}>
        Close
      </button>
    </dialog>
  )
}
