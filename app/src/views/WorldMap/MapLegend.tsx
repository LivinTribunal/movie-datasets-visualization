import type { FC } from 'react'
import type { Family } from '../../lib/types'
import type { MapMode } from '../../state/store'
import { THIN } from '../../lib/countryShares'

interface MapLegendProps {
  mode: MapMode
  ramp: string[]
  lo: string
  hi: string
  unit: string
  families: Family[]
  family: number
  onFamily: (family: number) => void
}

export const MapLegend: FC<MapLegendProps> = ({ mode, ramp, lo, hi, unit, families, family, onFamily }) => (
  <div className="map-legend">
    {mode === 'top' ? (
      <div className="legend-families">
        {families.map((f, i) => (
          <button
            key={f.name}
            type="button"
            className="legend-family"
            aria-pressed={i === family}
            onClick={() => onFamily(i)}
          >
            <span className="swatch" style={{ background: f.colour }} />
            {f.name}
          </button>
        ))}
      </div>
    ) : (
      <div className="legend-ramp">
        <span className="legend-unit">{unit}</span>
        <div className="ramp" style={{ background: `linear-gradient(to right, ${ramp.join(', ')})` }} />
        <div className="ramp-labels">
          <span>{lo}</span>
          <span>{hi}</span>
        </div>
        {mode === 'diff' && (
          <div className="ramp-labels">
            <span>more on Netflix</span>
            <span>more in cinemas</span>
          </div>
        )}
        {mode === 'diff' && <span className="legend-unit">ignores the source control</span>}
      </div>
    )}
    <div className="legend-keys">
      <span className="key">
        <svg width="14" height="10" aria-hidden="true">
          <rect width="14" height="10" fill="url(#map-hatch)" stroke="var(--fill-2)" />
        </svg>
        no data
      </span>
      <span className="key">
        <svg width="14" height="10" aria-hidden="true">
          <rect width="14" height="10" fill="var(--panel)" stroke="var(--ink)" strokeDasharray="2 2" />
        </svg>
        under {THIN} entries
      </span>
    </div>
  </div>
)
