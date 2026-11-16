import { useEffect, useMemo, useRef, useState, type FC, type KeyboardEvent } from 'react'
import { loadText, useLazy } from '../../lib/data'
import { foldAll, search } from '../../lib/search'
import type { AppData } from '../../lib/types'
import { useStore } from '../../state/store'
import './search.css'

type Item =
  | { kind: 'country'; key: string; label: string; iso2: string }
  | { kind: 'franchise'; key: string; label: string; id: number }
  | { kind: 'film'; key: string; label: string; sub: string; row: number }

export const Search: FC<{ data: AppData }> = ({ data }) => {
  const toggleCountry = useStore((s) => s.toggleCountry)
  const setFranchise = useStore((s) => s.setFranchise)
  const setFilm = useStore((s) => s.setFilm)
  const setTab = useStore((s) => s.setTab)
  const text = useLazy(loadText)
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const box = useRef<HTMLDivElement>(null)

  const folded = useMemo(() => (text ? foldAll(text.title) : null), [text])
  const result = useMemo(
    () => search(query, { countries: data.countries, collections: data.franchises.collections, folded }),
    [query, data, folded],
  )
  const items = useMemo<Item[]>(
    () => [
      ...result.countries.map((c): Item => ({ kind: 'country', key: `c-${c.iso2}`, label: c.name, iso2: c.iso2 })),
      ...result.franchises.map((f): Item => ({ kind: 'franchise', key: `f-${f.id}`, label: f.name, id: f.id })),
      ...result.films.map((row): Item => ({
        kind: 'film',
        key: `m-${row}`,
        label: text?.title[row] ?? '',
        sub: Number.isNaN(data.films.year[row]) ? '' : String(data.films.year[row]),
        row,
      })),
    ],
    [result, text, data],
  )

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const show = open && query.trim().length >= 2
  const optionId = (i: number) => `search-opt-${i}`

  const pick = (item: Item) => {
    if (item.kind === 'country') toggleCountry(item.iso2)
    else if (item.kind === 'franchise') {
      setFranchise(item.id)
      setTab('franchises')
    } else {
      setFilm(item.row)
      if (useStore.getState().tab === 'taste') setTab('ratings')
    }
    setQuery('')
    setOpen(false)
  }

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      setOpen(true)
      if (items.length) setActive((a) => (a + (e.key === 'ArrowDown' ? 1 : items.length - 1)) % items.length)
    } else if (e.key === 'Enter' && show && items[active]) {
      e.preventDefault()
      pick(items[active])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  const renderGroup = (kind: Item['kind'], heading: string, empty?: string) => {
    const rows = items.map((item, i) => ({ item, i })).filter(({ item }) => item.kind === kind)
    if (!rows.length && !empty) return null
    return (
      <>
        <li role="presentation" className="search-group">{heading}</li>
        {rows.map(({ item, i }) => (
          <li
            key={item.key}
            id={optionId(i)}
            role="option"
            aria-selected={i === active}
            className="search-option"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => pick(item)}
            onMouseEnter={() => setActive(i)}
          >
            <span>{item.label}</span>
            {item.kind === 'film' && <span className="search-sub">{item.sub}</span>}
          </li>
        ))}
        {!rows.length && empty && <li role="presentation" className="search-empty">{empty}</li>}
      </>
    )
  }

  return (
    <div className="search-box" ref={box}>
      <input
        className="search"
        type="text"
        role="combobox"
        aria-label="Search"
        aria-expanded={show}
        aria-controls="search-list"
        aria-activedescendant={show && items[active] ? optionId(active) : undefined}
        aria-autocomplete="list"
        placeholder="country, film or franchise…"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          setActive(0)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
      />
      {show && (
        <ul id="search-list" role="listbox" className="search-list">
          {renderGroup('country', 'countries')}
          {renderGroup('franchise', 'franchises')}
          {renderGroup('film', 'films', folded ? undefined : 'loading titles…')}
          {folded && !items.length && <li role="presentation" className="search-empty">nothing found</li>}
        </ul>
      )}
    </div>
  )
}
