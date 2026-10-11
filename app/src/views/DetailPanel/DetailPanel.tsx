import { format } from 'd3'
import type { AppData, FilmRow } from '../../lib/types'
import { useStore } from '../../state/store'

const usd = format('$.3s')

const SCORES = [
  ['imdb_100', 'IMDb'],
  ['tmdb_100', 'TMDB'],
  ['tomatometer_100', 'Tomatometer'],
  ['audience_100', 'Audience score'],
  ['metascore_100', 'Metascore'],
  ['mc_user_100', 'Metacritic users'],
  ['letterboxd_100', 'Letterboxd'],
  ['gap', 'Gap (audience − critics)'],
] as const

function Badge({ text }: { text: string }) {
  return <span className="badge">{text}</span>
}

export function DetailPanel({ data }: { data: AppData }) {
  const selectedFilm = useStore((s) => s.selectedFilm)
  const { films, meta } = data
  const i = selectedFilm ? films.columns.imdb_id.indexOf(selectedFilm) : -1
  const col = <K extends keyof FilmRow>(k: K): FilmRow[K] => films.columns[k][i]

  const money = (k: 'budget' | 'revenue') => {
    const v = col(`${k}_usd2025`)
    if (v === null) return <>n/a</>
    const src = col(`${k}_src`)
    return (
      <>
        {usd(v)}
        {src && <Badge text={src} />}
        {col(`${k}_converted`) && <Badge text="converted" />}
        {col(`${k}_disagree`) && <Badge text="sources disagree" />}
        {col('money_fuzzy') && src === 'numbers' && <Badge text="fuzzy match" />}
      </>
    )
  }

  return (
    <aside className="panel detail">
      <h2>{i < 0 ? 'Film details' : `${col('title')} (${col('year') ?? 'n/a'})`}</h2>
      {i < 0 ? (
        <p>Select a film to see its details.</p>
      ) : (
        <>
          <p>Genres: {col('genres').join(', ') || 'n/a'}</p>
          <ul>
            {SCORES.map(([k, label]) => (
              <li key={k}>
                {label}: {col(k) === null ? 'n/a' : col(k)?.toFixed(1)}
                {k === 'metascore_100' &&
                  col('mc_critic_reviews') !== null &&
                  ` (${col('mc_critic_reviews')} reviews)`}
              </li>
            ))}
            <li>Budget (2025 USD): {money('budget')}</li>
            <li>Revenue (2025 USD): {money('revenue')}</li>
          </ul>
        </>
      )}
      <h3>About the data</h3>
      <ul>
        {meta.notes.map((n) => <li key={n}>{n}</li>)}
      </ul>
    </aside>
  )
}
