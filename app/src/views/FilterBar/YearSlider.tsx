import { useState, type CSSProperties, type FC } from 'react'
import { YEAR_MAX, YEAR_MIN, useStore } from '../../state/store'

export const YearSlider: FC = () => {
  const [from, to] = useStore((s) => s.yearRange)
  const setYearRange = useStore((s) => s.setYearRange)
  const [last, setLast] = useState<'from' | 'to'>('to')
  const span = YEAR_MAX - YEAR_MIN
  const style = {
    '--from': ((from - YEAR_MIN) / span) * 100,
    '--to': ((to - YEAR_MIN) / span) * 100,
  } as CSSProperties
  const top = from === YEAR_MAX && to === YEAR_MAX ? 'from' : last
  return (
    <div className="year-slider">
      <span className="num">{from}</span>
      <div className="year-track" style={style}>
        <input
          type="range"
          min={YEAR_MIN}
          max={YEAR_MAX}
          value={from}
          aria-label="From year"
          className={top === 'from' ? 'is-top' : undefined}
          onChange={(e) => {
            setLast('from')
            setYearRange([Math.min(Number(e.target.value), to), to])
          }}
        />
        <input
          type="range"
          min={YEAR_MIN}
          max={YEAR_MAX}
          value={to}
          aria-label="To year"
          className={top === 'to' ? 'is-top' : undefined}
          onChange={(e) => {
            setLast('to')
            setYearRange([from, Math.max(Number(e.target.value), from)])
          }}
        />
      </div>
      <span className="num">{to}</span>
    </div>
  )
}
