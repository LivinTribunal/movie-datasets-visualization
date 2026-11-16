import { useMemo, useState, type FC, type PointerEvent } from 'react'
import { line as d3line, scaleLinear, scaleLog } from 'd3'
import { ChipGroup } from '../../components/ChipGroup'
import { Panel } from '../../components/Panel'
import { Tooltip } from '../../components/Tooltip'
import { franchiseLines, MAX_K, medianByInstallment, nearestVertex, outsideCount, RATIO_MAX, sequelStat, type Count } from '../../lib/franchise'
import { fmtInt, fmtRatio } from '../../lib/format'
import { useSize } from '../../lib/hooks'
import type { AppData } from '../../lib/types'
import { useFilmMask } from '../../state/selectors'
import { useStore, type FranchiseY } from '../../state/store'
import { Lines } from './Lines'
import './franchise.css'

const M = { left: 60, right: 90, top: 8, bottom: 34 }
const HIT = 12
const Y_OPTIONS: { value: FranchiseY; label: string }[] = [
  { value: 'rating', label: 'Rating' },
  { value: 'revenue', label: 'Box office' },
]

const truncate = (s: string) => (s.length > 14 ? `${s.slice(0, 13)}…` : s)
const share = (c: Count) => (c.total === 0 ? 'no data' : `${Math.round((100 * c.below) / c.total)}%`)
const signed = (v: number) => `${v < 0 ? '−' : '+'}${Math.abs(Math.round(v))}`

export const Franchise: FC<{ data: AppData }> = ({ data }) => {
  const mask = useFilmMask(data)
  const family = useStore((s) => s.family)
  const franchise = useStore((s) => s.franchise)
  const y = useStore((s) => s.franchiseY)
  const setFranchise = useStore((s) => s.setFranchise)
  const setFranchiseY = useStore((s) => s.setFranchiseY)
  const setHoverFilm = useStore((s) => s.setHoverFilm)
  const [ref, { width, height }] = useSize<HTMLDivElement>()
  const [hover, setHover] = useState<{ line: number; point: number } | null>(null)

  const fr = data.franchises
  const { lines, cut } = franchiseLines(fr, y, mask)
  const median = useMemo(() => medianByInstallment(lines), [lines])
  const baseline = y === 'rating' ? 0 : 1
  const stat = sequelStat(lines, baseline, family)
  const f = data.families[family]

  const innerW = Math.max(0, width - M.left - M.right)
  const innerH = Math.max(0, height - M.top - M.bottom)
  const xScale = useMemo(() => scaleLinear().domain([1, MAX_K]).range([0, innerW]), [innerW])
  const yScale = useMemo(() => {
    if (y === 'revenue') return scaleLog().domain([1 / RATIO_MAX, RATIO_MAX]).clamp(false).range([innerH, 0])
    let m = 0
    for (const l of lines) for (const p of l.points) m = Math.max(m, Math.abs(p.v))
    return scaleLinear().domain([-(m || 1), m || 1]).nice().range([innerH, 0])
  }, [lines, y, innerH])

  const hovered = hover ? lines[hover.line] : null
  const hoveredPoint = hovered && hover ? hovered.points[hover.point] : null
  const selected = lines.find((l) => l.id === franchise) ?? null
  const path = d3line<{ k: number; v: number }>()
    .x((p) => xScale(p.k))
    .y((p) => yScale(p.v))

  const locate = (e: PointerEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    return { px: e.clientX - r.left - M.left, py: e.clientY - r.top - M.top }
  }
  const onMove = (e: PointerEvent<SVGSVGElement>) => {
    const { px, py } = locate(e)
    const hit = nearestVertex(lines, px, py, xScale, yScale, HIT, [0, innerH])
    setHover(hit)
    const row = hit ? lines[hit.line].points[hit.point].row : null
    const filmRow = row === null ? NaN : fr.film_row[row]
    setHoverFilm(Number.isNaN(filmRow) ? null : filmRow)
  }
  const onLeave = () => {
    setHover(null)
    setHoverFilm(null)
  }
  const onClick = () => {
    if (!hovered) return
    setFranchise(hovered.id === franchise ? null : hovered.id)
  }

  const tip = () => {
    if (!hovered || !hoveredPoint) return null
    const row = hoveredPoint.row
    const name = fr.collections.get(hovered.id) ?? 'franchise'
    const k = hoveredPoint.k
    const film = `#${k} ${fr.title[row] ?? 'untitled'} (${Number.isNaN(fr.year[row]) ? 'no data' : fr.year[row]})`
    let what: string
    if (k === 1) what = 'the first film'
    else if (y === 'rating') what = `${signed(hoveredPoint.v)} points vs #1`
    else what = `${fmtRatio(hoveredPoint.v)} the box office of #1`
    return (
      <>
        <b>{name}</b><br />
        {film}<br />
        {what}
      </>
    )
  }

  const yTicks = y === 'rating' ? yScale.ticks(6) : [0.01, 0.1, 1, 10, 100]
  const yFmt = (v: number) => (y === 'rating' ? (v > 0 ? `+${v}` : String(v)) : fmtRatio(v))
  const medianEnd = median.length ? median[median.length - 1] : null
  const lastSel = selected ? selected.points[selected.points.length - 1] : null
  const outside = y === 'revenue' ? outsideCount(lines, 1 / RATIO_MAX, RATIO_MAX) : 0
  const what = y === 'rating' ? 'rate below' : 'earn less than'

  const note = (
    <>
      {share(stat.all)} of sequels {what} the first film ({share(stat.family)} in {f.name}, {fmtInt(stat.family.franchises)} franchises).
      {cut && ' Films after the 10th are not shown.'}
      {outside > 0 && ` ${fmtInt(outside)} values outside 0.01×–100× run off the chart.`}
    </>
  )

  return (
    <Panel
      title="Sequels against the first film"
      className="area-d"
      tools={<ChipGroup label="Y axis" options={Y_OPTIONS} value={y} onChange={setFranchiseY} />}
      note={note}
    >
      <div className="franchise-chart" ref={ref}>
        {width > 0 && height > 0 && lines.length === 0 && (
          <p className="franchise-empty">No franchise matches the filters.</p>
        )}
        {width > 0 && height > 0 && lines.length > 0 && (
          <>
            <svg width={width} height={height} onPointerMove={onMove} onPointerLeave={onLeave} onClick={onClick}>
              <defs>
                <clipPath id="fr-clip">
                  <rect x={0} y={0} width={innerW} height={innerH} />
                </clipPath>
              </defs>
              <g transform={`translate(${M.left},${M.top})`}>
                <g className="grid">
                  {yTicks.map((t) => (
                    <g key={t} transform={`translate(0,${yScale(t)})`}>
                      <line x1={0} x2={innerW} />
                      <text x={-6} dy="0.32em" textAnchor="end">
                        {yFmt(t)}
                      </text>
                    </g>
                  ))}
                </g>
                {Array.from({ length: MAX_K }, (_, i) => i + 1).map((k) => (
                  <text key={k} x={xScale(k)} y={innerH + 14} textAnchor="middle">
                    {k}
                  </text>
                ))}
                <text className="axis-label" x={innerW / 2} y={innerH + 29} textAnchor="middle">
                  installment
                </text>
                <text className="axis-label" transform={`translate(-48,${innerH / 2}) rotate(-90)`} textAnchor="middle">
                  {y === 'rating' ? 'IMDb rating vs the first film (points on 0–100)' : 'box office vs the first film (×, log, 2025 USD)'}
                </text>
                <line x1={0} x2={innerW} y1={yScale(baseline)} y2={yScale(baseline)} stroke="var(--line)" />
                <g clipPath="url(#fr-clip)">
                  <Lines lines={lines} x={xScale} y={yScale} familyBit={family} colour={f.colour} />
                  {median.length > 1 && (
                  <path d={path(median) ?? ''} fill="none" stroke="var(--ink-2)" strokeWidth={1.5} strokeDasharray="4 3" />
                  )}
                </g>
                {medianEnd && (
                  <text x={xScale(medianEnd.k) + 6} y={yScale(medianEnd.v)} dy="0.32em">
                    median
                  </text>
                )}
                {selected && lastSel && (
                  <g>
                    <g clipPath="url(#fr-clip)">
                      <path d={path(selected.points) ?? ''} fill="none" stroke="var(--ink)" strokeWidth={2.25} />
                      {selected.points.map((p) => (
                        <circle key={p.k} cx={xScale(p.k)} cy={yScale(p.v)} r={3} fill="var(--ink)" stroke="#fff" strokeWidth={1.5} />
                      ))}
                    </g>
                    <text x={xScale(lastSel.k) + 6} y={yScale(lastSel.v)} dy="0.32em" className="halo">
                      {truncate(fr.collections.get(selected.id) ?? '')}
                    </text>
                  </g>
                )}
                {hovered && hoveredPoint && (
                  <g pointerEvents="none">
                    <path d={path(hovered.points) ?? ''} fill="none" stroke="var(--ink)" strokeWidth={2} />
                    <circle cx={xScale(hoveredPoint.k)} cy={yScale(hoveredPoint.v)} r={4} fill="var(--ink)" />
                  </g>
                )}
              </g>
            </svg>
            {hovered && hoveredPoint && (
              <Tooltip
                x={M.left + xScale(hoveredPoint.k)}
                y={M.top + yScale(hoveredPoint.v)}
                width={width}
                height={height}
              >
                {tip()}
              </Tooltip>
            )}
          </>
        )}
      </div>
    </Panel>
  )
}
