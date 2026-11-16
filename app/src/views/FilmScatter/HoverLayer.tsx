import type { FC } from 'react'
import { Tooltip } from '../../components/Tooltip'
import { fmtValue } from '../../lib/format'
import { MEASURES, type MeasureKey } from '../../lib/measures'
import { useStore } from '../../state/store'

export interface Geometry {
  xScale: (v: number) => number
  yScale: (v: number) => number
  xCol: Float64Array
  yCol: Float64Array
  left: number
  right: number
  top: number
  bottom: number
}

function position(g: Geometry, row: number | null): [number, number] | null {
  if (row === null) return null
  const px = g.xScale(g.xCol[row])
  const py = g.yScale(g.yCol[row])
  if (!Number.isFinite(px) || !Number.isFinite(py)) return null
  if (px < g.left || px > g.right || py < g.top || py > g.bottom) return null
  return [px, py]
}

export const HoverRing: FC<{ geometry: Geometry }> = ({ geometry }) => {
  const hover = useStore((s) => s.hoverFilm)
  const pinned = useStore((s) => s.film)
  const h = position(geometry, hover)
  const p = position(geometry, pinned)
  return (
    <g className="scatter-rings" pointerEvents="none">
      {p && <circle cx={p[0]} cy={p[1]} r={8} fill="none" stroke="#fff" strokeWidth={5.5} />}
      {p && <circle cx={p[0]} cy={p[1]} r={8} fill="none" stroke="var(--ink)" strokeWidth={2.5} />}
      {h && <circle cx={h[0]} cy={h[1]} r={8} fill="none" stroke="#fff" strokeWidth={4.5} />}
      {h && <circle cx={h[0]} cy={h[1]} r={8} fill="none" stroke="var(--ink)" strokeWidth={1.5} />}
    </g>
  )
}

interface HoverTipProps {
  geometry: Geometry
  xKey: MeasureKey
  yKey: MeasureKey
  year: Float64Array
  titles: (string | null)[] | null
  width: number
  height: number
}

export const HoverTip: FC<HoverTipProps> = ({ geometry, xKey, yKey, year, titles, width, height }) => {
  const hover = useStore((s) => s.hoverFilm)
  const pos = position(geometry, hover)
  if (hover === null || !pos) return null
  const title = titles ? (titles[hover] ?? 'untitled') : 'loading title…'
  return (
    <Tooltip x={pos[0]} y={pos[1]} width={width} height={height}>
      <strong>{title}</strong>
      <br />
      {fmtValue('year', year[hover])}
      <br />
      {MEASURES[xKey].label}: {fmtValue(xKey, geometry.xCol[hover])}
      <br />
      {MEASURES[yKey].label}: {fmtValue(yKey, geometry.yCol[hover])}
    </Tooltip>
  )
}
