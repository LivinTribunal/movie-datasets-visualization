import { useEffect, useState, type FC } from 'react'
import { loadPosters, useLazy } from '../../lib/data'

const BASE = 'https://image.tmdb.org/t/p/w185'
const DELAY_MS = 150

export const Poster: FC<{ row: number }> = ({ row }) => {
  const posters = useLazy(loadPosters)
  const [shown, setShown] = useState<{ row: number; failed: boolean } | null>(null)

  useEffect(() => {
    const t = setTimeout(() => setShown({ row, failed: false }), DELAY_MS)
    return () => clearTimeout(t)
  }, [row])

  const path = posters ? posters[row] : null
  const ready = shown !== null && shown.row === row && !shown.failed && path
  return (
    <div className="poster">
      {ready ? (
        <img
          src={`${BASE}${path}`}
          alt=""
          loading="lazy"
          width={92}
          height={138}
          onError={() => setShown({ row, failed: true })}
        />
      ) : (
        <span className="poster-empty">no poster</span>
      )}
    </div>
  )
}
