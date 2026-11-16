import { memo, type FC, type MouseEvent } from 'react'

export interface MapShape {
  key: string
  iso2: string | null
  d: string
  fill: string
  thin: boolean
}

interface MapPathsProps {
  shapes: MapShape[]
  onHover: (iso2: string | null, e: MouseEvent) => void
  onClick: (iso2: string) => void
  onDoubleClick: (key: string) => void
}

export const MapPaths: FC<MapPathsProps> = memo(({ shapes, onHover, onClick, onDoubleClick }) => (
  <>
    {shapes.map((s) => (
      <path
        key={s.key}
        d={s.d}
        fill={s.fill}
        className={s.thin ? 'country thin' : 'country'}
        onMouseMove={(e) => onHover(s.iso2, e)}
        onMouseLeave={(e) => onHover(null, e)}
        onClick={() => s.iso2 && onClick(s.iso2)}
        onDoubleClick={() => onDoubleClick(s.key)}
      />
    ))}
  </>
))
MapPaths.displayName = 'MapPaths'
