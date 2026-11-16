import { memo } from 'react'
import { line as d3line, type ScaleLinear, type ScaleLogarithmic } from 'd3'
import type { Line } from '../../lib/franchise'

interface LinesProps {
  lines: Line[]
  x: ScaleLinear<number, number>
  y: ScaleLinear<number, number> | ScaleLogarithmic<number, number>
  familyBit: number
  colour: string
}

export const Lines = memo(function Lines({ lines, x, y, familyBit, colour }: LinesProps) {
  const path = d3line<{ k: number; v: number }>()
    .x((p) => x(p.k))
    .y((p) => y(p.v))
  const inFamily = (l: Line) => ((l.familyMask >> familyBit) & 1) === 1
  return (
    <g fill="none" strokeWidth={1}>
      {lines
        .filter((l) => !inFamily(l))
        .map((l) => (
          <path key={l.id} d={path(l.points) ?? ''} stroke="#b4b8c0" strokeOpacity={0.28} />
        ))}
      {lines.filter(inFamily).map((l) => (
        <path key={l.id} d={path(l.points) ?? ''} stroke={colour} strokeOpacity={0.45} />
      ))}
    </g>
  )
})
