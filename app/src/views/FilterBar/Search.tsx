import type { FC } from 'react'
import type { AppData } from '../../lib/types'

export const Search: FC<{ data: AppData }> = () => (
  <input
    className="search"
    type="text"
    disabled
    placeholder="country, film or franchise…"
    aria-label="Search"
  />
)
