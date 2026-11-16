import { decodeHash, encodeHash, type HashContext, type Values } from '../lib/hash'
import type { AppData } from '../lib/types'
import { defaults, useStore } from './store'

const DEBOUNCE_MS = 300

export function startHashSync(data: AppData): () => void {
  const ctx: HashContext = {
    imdb: data.films.imdb,
    nFamilies: data.families.length,
    countries: new Set(data.countries.map((c) => c.iso2)),
    collections: new Set(data.franchises.collections.keys()),
  }

  const apply = () => {
    const base: Partial<Values> = defaults()
    delete base.brush
    delete base.hoverFilm
    delete base.about
    useStore.setState({ ...base, ...decodeHash(location.hash, ctx) })
  }

  const write = () => {
    const encoded = encodeHash(useStore.getState(), defaults(), ctx.imdb)
    const hash = encoded ? `#${encoded}` : ''
    if (hash === location.hash) return
    history.replaceState(null, '', `${location.pathname}${location.search}${hash}`)
  }

  let timer: ReturnType<typeof setTimeout> | undefined
  const schedule = () => {
    clearTimeout(timer)
    timer = setTimeout(write, DEBOUNCE_MS)
  }

  apply()
  const unsubscribe = useStore.subscribe(schedule)
  window.addEventListener('hashchange', apply)
  return () => {
    unsubscribe()
    window.removeEventListener('hashchange', apply)
    clearTimeout(timer)
  }
}
