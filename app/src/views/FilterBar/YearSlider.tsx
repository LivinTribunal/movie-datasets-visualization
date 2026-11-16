import type { FC } from 'react'
import { YEAR_MAX, YEAR_MIN, useStore } from '../../state/store'

export const YearSlider: FC = () => {
  const [from, to] = useStore((s) => s.yearRange)
  const setYearRange = useStore((s) => s.setYearRange)
  return (
    <div className="year-slider">
      <span className="num">{from}</span>
      <div className="year-track">
        <input
          type="range"
          min={YEAR_MIN}
          max={YEAR_MAX}
          value={from}
          aria-label="From year"
          onChange={(e) => setYearRange([Math.min(Number(e.target.value), to), to])}
        />
        <input
          type="range"
          min={YEAR_MIN}
          max={YEAR_MAX}
          value={to}
          aria-label="To year"
          onChange={(e) => setYearRange([from, Math.max(Number(e.target.value), from)])}
        />
      </div>
      <span className="num">{to}</span>
    </div>
  )
}
