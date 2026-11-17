import { useCallback, useEffect, useState, type FC } from 'react'
import { Panel } from '../../components/Panel'
import { loadDetail, loadText, useLazy } from '../../lib/data'
import { filmCountries, filmGenres, fuzzyMoney, moneyFacts, releaseFacts, SCORE_GROUPS, SRC_LABEL, STORY_LABEL, STUDIO_LABEL, type MoneyFact } from '../../lib/film'
import { fmtImdb, fmtInt, fmtMoney, fmtRatio, fmtScore } from '../../lib/format'
import { measureColumn, MEASURES } from '../../lib/measures'
import type { AppData, FilmsDetail } from '../../lib/types'
import { useStore } from '../../state/store'
import { Poster } from './Poster'
import './filmcard.css'

const present = (v: number) => !Number.isNaN(v)

const LINKS: { key: 'qid' | 'csfd_id' | 'filmaffinity_id' | 'allocine_id' | 'douban_id'; name: string; url: (id: string) => string }[] = [
  { key: 'qid', name: 'Wikidata', url: (id) => `https://www.wikidata.org/wiki/${id}` },
  { key: 'csfd_id', name: 'ČSFD', url: (id) => `https://www.csfd.cz/film/${id}/` },
  { key: 'filmaffinity_id', name: 'FilmAffinity', url: (id) => `https://www.filmaffinity.com/en/film${id}.html` },
  { key: 'allocine_id', name: 'AlloCiné', url: (id) => `https://www.allocine.fr/film/fichefilm_gen_cfilm=${id}.html` },
  { key: 'douban_id', name: 'Douban', url: (id) => `https://movie.douban.com/subject/${id}/` },
]

/** The detail shard entry for a row; null until it loads, and for rows outside the shards. */
function useDetail(row: number, meta: AppData['meta']): { shard: FilmsDetail; index: number } | null {
  const [state, setState] = useState<{ row: number; value: { shard: FilmsDetail; index: number } | null } | null>(null)
  const load = useCallback(() => (row < 0 ? Promise.resolve(null) : loadDetail(row, meta)), [row, meta])
  useEffect(() => {
    let live = true
    load().then((value) => { if (live) setState({ row, value }) }, () => { /* the card shows no about group */ })
    return () => { live = false }
  }, [load, row])
  return state?.row === row ? state.value : null
}

const signed = (v: number) => (Number.isNaN(v) ? 'no data' : `${v < 0 ? '−' : '+'}${Math.abs(Math.round(v))} points`)

export const FilmCard: FC<{ data: AppData }> = ({ data }) => {
  const pinned = useStore((s) => s.film)
  const hover = useStore((s) => s.hoverFilm)
  const money = useStore((s) => s.money)
  const countries = useStore((s) => s.countries)
  const franchise = useStore((s) => s.franchise)
  const setFilm = useStore((s) => s.setFilm)
  const toggleCountry = useStore((s) => s.toggleCountry)
  const setFranchise = useStore((s) => s.setFranchise)
  const text = useLazy(loadText)

  const row = hover ?? pinned
  const detail = useDetail(row ?? -1, data.meta)
  if (row === null) {
    return (
      <Panel title="Film" className="area-g">
        <p className="filmcard-hint">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect x="3" y="4" width="18" height="16" rx="2" />
            <path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4" />
          </svg>
          Hover a point or a table row to see a film. Click to pin it.
        </p>
      </Panel>
    )
  }

  const films = data.films
  const title = text?.title[row] ?? fmtImdb(films.imdb[row])
  const director = text?.director[row]
  const year = films.year[row]
  const runtime = films.runtime[row]
  const facts = [
    Number.isNaN(year) ? 'year: no data' : String(year),
    Number.isNaN(runtime) ? 'runtime: no data' : `${fmtInt(runtime)} min`,
    ...(director ? [director] : []),
  ]
  const genres = filmGenres(films, row)
  const iso = filmCountries(films, row)
  const collection = films.collection_id[row]
  const unit = money === 'usd2025' ? '2025 USD' : 'nominal USD'
  const m = moneyFacts(films, row, money)
  const fuzzy = fuzzyMoney(films, row)
  const gap = films.gap[row]
  const rel = releaseFacts(films, row, money)
  const hasRelease = !!(rel.age || rel.story || rel.studio) ||
    [rel.opening, rel.theaters, rel.legs, rel.video, rel.noms].some(present)
  const about = detail && {
    overview: detail.shard.overview[detail.index],
    cast: detail.shard.cast[detail.index],
    writers: detail.shard.writers[detail.index],
    companies: detail.shard.companies[detail.index],
    links: LINKS.flatMap((l) => {
      const id = detail.shard[l.key][detail.index]
      return id ? [{ name: l.name, href: l.url(id) }] : []
    }),
  }
  const hasAbout = !!about && !!(about.overview || about.cast || about.writers || about.companies || about.links.length)
  const releaseRow = (label: string, value: string, badges: (string | false)[] = []) => (
    <div className="fc-money" key={label}>
      <span className="fc-label">{label}</span>
      <span className="fc-value">{value}</span>
      <span className="fc-badges">
        {badges.map((b) => b && <span className="fc-badge" key={b}>{b}</span>)}
      </span>
    </div>
  )

  const moneyRow = (label: string, f: MoneyFact) => (
    <div className="fc-money" key={label}>
      <span className="fc-label">{label}</span>
      <span className="fc-value">
        {fmtMoney(f.value)} <span className="fc-unit">{unit}</span>
      </span>
      <span className="fc-badges">
        {money === 'usd2025' && <span className="fc-badge">inflation-adjusted</span>}
        {f.source && <span className="fc-badge">source: {SRC_LABEL[f.source] ?? f.source}</span>}
        {f.converted && <span className="fc-badge">converted from another currency</span>}
        {f.disagree && <span className="fc-badge">sources disagree</span>}
        {fuzzy && <span className="fc-badge">fuzzy title match</span>}
      </span>
    </div>
  )

  return (
    <Panel title="Film" className="area-g">
      <div className="filmcard">
        <div className="fc-head">
          <Poster row={row} />
          <div className="fc-info">
            <h3>{title}</h3>
            <p>{facts.join(' · ')}</p>
            <p>{genres.length ? genres.join(', ') : 'genres: no data'}</p>
            <p>
              {fmtInt(films.imdb_votes[row])} IMDb votes ·{' '}
              <a href={`https://www.imdb.com/title/${fmtImdb(films.imdb[row])}/`} target="_blank" rel="noreferrer">
                IMDb page
              </a>
            </p>
            {pinned === row && (
              <p>
                <span className="fc-badge">pinned</span>{' '}
                <button type="button" className="fc-btn" onClick={() => setFilm(null)}>
                  unpin
                </button>
              </p>
            )}
          </div>
        </div>

        <div className="fc-chips">
          {iso.map((c) => (
            <button
              key={c}
              type="button"
              className="fc-btn"
              title={data.countryByIso2.get(c)?.name ?? c}
              aria-pressed={countries.includes(c)}
              onClick={() => toggleCountry(c)}
            >
              {data.countryByIso2.get(c)?.name ?? c}
            </button>
          ))}
          {!Number.isNaN(collection) && (
            <button
              type="button"
              className="fc-btn"
              aria-pressed={franchise === collection}
              onClick={() => setFranchise(franchise === collection ? null : collection)}
            >
              {data.franchises.collections.get(collection) ?? 'Franchise'} · #{fmtInt(films.installment[row])}
            </button>
          )}
        </div>

        {SCORE_GROUPS.map((g) => (
          <section key={g.title} className={`fc-group fc-${g.title}`}>
            <h4>{g.title} (0–100)</h4>
            {g.keys.map((k) => {
              const v = measureColumn(films, k, money)[row]
              return (
                <div className="fc-score" key={k}>
                  <span className="fc-label">
                    {MEASURES[k].label}
                    {k === 'metascore' && !Number.isNaN(films.mc_critic_reviews[row]) &&
                      ` (${fmtInt(films.mc_critic_reviews[row])} reviews)`}
                  </span>
                  {Number.isNaN(v) ? (
                    <span className="fc-value">no data</span>
                  ) : (
                    <>
                      <span className="fc-bar">
                        <span style={{ width: `${Math.min(100, Math.max(0, v))}%` }} />
                      </span>
                      <span className="fc-value">{fmtScore(v)}</span>
                    </>
                  )}
                </div>
              )
            })}
          </section>
        ))}
        <p className="fc-gap">gap (audience − critics): {signed(gap)}</p>

        <section className="fc-group">
          <h4>money</h4>
          {moneyRow('budget', m.budget)}
          {moneyRow('box office', m.revenue)}
          <div className="fc-money">
            <span className="fc-label">ROI, box office ÷ budget</span>
            <span className="fc-value">{fmtRatio(m.roi)}</span>
          </div>
        </section>

        {hasRelease && (
          <section className="fc-group">
            <h4>release</h4>
            {rel.age && releaseRow('age rating (US)', rel.age)}
            {rel.story && releaseRow('story source', STORY_LABEL[rel.story] ?? rel.story, [rel.storySrc === 'tmdb' && 'from TMDB keywords'])}
            {rel.studio && releaseRow('studio', STUDIO_LABEL[rel.studio] ?? rel.studio)}
            {present(rel.opening) &&
              releaseRow('opening weekend, US', `${fmtMoney(rel.opening)} ${unit}`, [
                money === 'usd2025' && 'inflation-adjusted', 'US only', 'source: The Numbers', rel.fuzzy && 'fuzzy title match',
              ])}
            {present(rel.theaters) && releaseRow('widest release', `${fmtInt(rel.theaters)} theatres`)}
            {present(rel.legs) && releaseRow('legs, US gross ÷ opening', fmtRatio(rel.legs))}
            {present(rel.video) && releaseRow('home video', `${fmtMoney(rel.video)} 2025 USD`, ['estimate'])}
            {present(rel.noms) &&
              releaseRow(
                'Oscars',
                rel.noms === 0 ? 'none' : `${fmtInt(rel.wins)} wins of ${fmtInt(rel.noms)} nominations`,
                ['Wikidata'],
              )}
          </section>
        )}

        {about && hasAbout && (
          <section className="fc-group fc-about">
            <h4>about</h4>
            {about.overview && <p>{about.overview}</p>}
            {about.cast && <p><span className="fc-label">cast</span> {about.cast}</p>}
            {about.writers && <p><span className="fc-label">written by</span> {about.writers}</p>}
            {about.companies && <p><span className="fc-label">companies</span> {about.companies}</p>}
            {about.links.length > 0 && (
              <p>
                <span className="fc-label">links</span>{' '}
                {about.links.map((l, i) => (
                  <span key={l.name}>
                    {i > 0 && ' · '}
                    <a href={l.href} target="_blank" rel="noreferrer">{l.name}</a>
                  </span>
                ))}
              </p>
            )}
          </section>
        )}
      </div>
    </Panel>
  )
}
