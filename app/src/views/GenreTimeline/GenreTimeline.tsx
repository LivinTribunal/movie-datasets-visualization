import { useEffect, useMemo, useRef, useState, type FC } from 'react'
import { area, brushX, pointer, scaleLinear, select, type BrushBehavior, type D3BrushEvent } from 'd3'
import { Panel } from '../../components/Panel'
import { Tooltip } from '../../components/Tooltip'
import { fmtInt, fmtPct } from '../../lib/format'
import { useSize } from '../../lib/hooks'
import {
  familyAt,
  SHORTS_UNTIL,
  THIN,
  timelineFromFilms,
  timelineFromImdb,
  timelineFromNetflix,
  type Timeline,
} from '../../lib/timeline'
import type { AppData } from '../../lib/types'
import { useFilmMaskAllYears } from '../../state/selectors'
import { useStore, YEAR_MAX, YEAR_MIN, type TimelineMeasure } from '../../state/store'
import './timeline.css'

const OPTIONS: { value: TimelineMeasure; label: string; yLabel: string; of: string; unit: string }[] = [
  { value: 'films', label: 'releases', yLabel: 'share of releases (%)', of: 'of releases', unit: 'films' },
  { value: 'votes', label: 'IMDb votes', yLabel: 'share of IMDb votes (%)', of: 'of IMDb votes', unit: 'films' },
  { value: 'revenue', label: 'box office', yLabel: 'share of box office (%)', of: 'of box office', unit: 'films' },
  {
    value: 'netflix',
    label: 'Netflix chart score',
    yLabel: 'share of Netflix chart score (%)',
    of: 'of Netflix chart score',
    unit: 'chart entries',
  },
  { value: 'imdb', label: 'all IMDb films', yLabel: 'share of IMDb films (%)', of: 'of IMDb films', unit: 'films' },
]

const MARGIN = { top: 8, right: 12, bottom: 22, left: 46 }
const Y_TICKS = [0, 0.25, 0.5, 0.75, 1]

interface Hover {
  px: number
  py: number
  year: number
  index: number
  family: number
}

function nearestIndex(years: number[], target: number): number {
  let best = 0
  for (let i = 1; i < years.length; i++) {
    if (Math.abs(years[i] - target) < Math.abs(years[best] - target)) best = i
  }
  return best
}

export const GenreTimeline: FC<{ data: AppData }> = ({ data }) => {
  const measure = useStore((s) => s.timelineMeasure)
  const setMeasure = useStore((s) => s.setTimelineMeasure)
  const money = useStore((s) => s.money)
  const countries = useStore((s) => s.countries)
  const family = useStore((s) => s.family)
  const yearRange = useStore((s) => s.yearRange)
  const setFamily = useStore((s) => s.setFamily)
  const setYearRange = useStore((s) => s.setYearRange)
  const mask = useFilmMaskAllYears(data)
  const [ref, { width, height }] = useSize<HTMLDivElement>()
  const brushGroup = useRef<SVGGElement | null>(null)
  const brushApi = useRef<BrushBehavior<unknown> | null>(null)
  const [hover, setHover] = useState<Hover | null>(null)

  const option = OPTIONS.find((o) => o.value === measure) ?? OPTIONS[1]
  const nFamilies = data.families.length
  const timeline: Timeline =
    measure === 'netflix'
      ? timelineFromNetflix(data.countryGenre, data.countryYear, data.genreFamily, nFamilies, countries)
      : measure === 'imdb'
        ? timelineFromImdb(data.imdbGenreYear, data.genreFamily, nFamilies)
        : timelineFromFilms(data.films, mask, measure, money, data.genreFamily, nFamilies)

  const iw = Math.max(0, width - MARGIN.left - MARGIN.right)
  const ih = Math.max(0, height - MARGIN.top - MARGIN.bottom)
  const { years } = timeline
  const hasData = timeline.totals.some((t) => t > 0)
  const x = useMemo(
    () => scaleLinear([years[0] ?? YEAR_MIN, years[years.length - 1] ?? YEAR_MAX], [0, iw]),
    [years, iw],
  )
  const y = useMemo(() => scaleLinear([0, 1], [ih, 0]), [ih])
  const bands = useMemo(() => {
    const lower = new Float64Array(years.length)
    const idx = years.map((_, i) => i)
    return timeline.shares.map((share) => {
      const base = Float64Array.from(lower)
      for (let i = 0; i < lower.length; i++) lower[i] += share[i]
      const top = Float64Array.from(lower)
      return area<number>()
        .x((i) => x(years[i]))
        .y0((i) => y(base[i]))
        .y1((i) => y(top[i]))
        .defined((i) => timeline.totals[i] > 0)(idx)
    })
  }, [timeline, years, x, y])

  const [from, to] = yearRange
  const overlaps = years.length > 0 && to >= years[0] && from <= years[years.length - 1]
  const ready = iw > 0 && ih > 0 && hasData

  const indexAt = (px: number) => nearestIndex(years, x.invert(px))

  useEffect(() => {
    const g = brushGroup.current
    if (!g || !ready) return
    const brush = brushX<unknown>().extent([
      [0, 0],
      [iw, ih],
    ])
    let down: [number, number] | null = null
    const client = (e: MouseEvent | TouchEvent): [number, number] => {
      const t = 'changedTouches' in e ? e.changedTouches[0] : e
      return [t.clientX, t.clientY]
    }
    brush.on('start', (event: D3BrushEvent<unknown>) => {
      down = event.sourceEvent ? client(event.sourceEvent) : null
    })
    brush.on('end', (event: D3BrushEvent<unknown>) => {
      if (!event.sourceEvent) return
      const [cx, cy] = client(event.sourceEvent)
      // a move under 3 px is a click, even when d3 still reports a selection
      const click = down !== null && Math.hypot(cx - down[0], cy - down[1]) < 3
      if (event.selection && !click) {
        const [a, b] = event.selection as [number, number]
        setYearRange([Math.round(x.invert(a)), Math.round(x.invert(b))])
        return
      }
      const [px, py] = pointer(event.sourceEvent, g)
      const f = familyAt(timeline, nearestIndex(years, x.invert(px)), (ih - py) / ih)
      if (f >= 0) setFamily(f)
      place()
    })
    const place = () => {
      const [a, b] = useStore.getState().yearRange
      const last = years[years.length - 1]
      if (b < years[0] || a > last) select(g).call(brush.move, null)
      else select(g).call(brush.move, [x(Math.max(a, years[0])), x(Math.min(b, last))])
    }
    const sel = select(g)
    sel.call(brush)
    sel.on('dblclick.reset', () => setYearRange([YEAR_MIN, YEAR_MAX]))
    brushApi.current = brush
    place()
    return () => {
      sel.on('.brush', null).on('dblclick.reset', null)
      sel.selectAll('*').remove()
      brushApi.current = null
    }
  }, [ready, iw, ih, x, years, timeline, setFamily, setYearRange])

  useEffect(() => {
    const g = brushGroup.current
    const brush = brushApi.current
    if (!g || !brush) return
    const last = years[years.length - 1]
    if (!overlaps) select(g).call(brush.move, null)
    else select(g).call(brush.move, [x(Math.max(from, years[0])), x(Math.min(to, last))])
  }, [from, to, overlaps, x, years, ready, timeline])

  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const g = brushGroup.current
    if (!g) return
    const [px, py] = pointer(e, g)
    if (px < 0 || px > iw || py < 0 || py > ih) {
      setHover(null)
      return
    }
    const index = indexAt(px)
    setHover({ px, py, year: years[index], index, family: familyAt(timeline, index, (ih - py) / ih) })
  }

  const step = years.length > 1 ? iw / (years.length - 1) : iw
  const xTicks = measure === 'netflix' ? years : years.filter((v) => v % 10 === 0)

  let tip: string | null = null
  if (hover) {
    if (timeline.totals[hover.index] <= 0) tip = `${hover.year} · no data`
    else if (hover.family >= 0) {
      const share = timeline.shares[hover.family][hover.index]
      tip = `${data.families[hover.family].name} · ${hover.year} · ${fmtPct(share)} ${option.of} · ${fmtInt(timeline.films[hover.index])} ${option.unit} that year`
    }
  }

  return (
    <Panel
      letter="B"
      title="Genre timeline"
      className="area-b"
      tools={
        <select
          className="tl-measure"
          aria-label="Measure"
          value={measure}
          onChange={(e) => {
            const next = OPTIONS.find((o) => o.value === e.target.value)
            if (next) setMeasure(next.value)
          }}
        >
          {OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      }
      note={
        <>
          Each film counts 1/n in each of its n genres.
          {measure === 'votes' && ' Votes show popularity, not rating.'}
          {measure === 'imdb' &&
            ' Every film on IMDb; the filters above do not apply. Short films count before 1920, features only after.'}
          {` Hatched: under ${THIN} films.`}
        </>
      }
    >
      <div className="timeline">
        <div className="tl-chart" ref={ref}>
          {width > 0 && height > 0 && !hasData && (
            <p className="tl-empty">
              {measure === 'netflix' ? 'No Netflix data for these countries.' : 'No films match the filters.'}
            </p>
          )}
          {ready && (
            <svg width={width} height={height} onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
              <defs>
                <pattern id="tl-thin" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                  <rect width="5" height="5" fill="#fff" opacity="0.5" />
                  <line x1="0" y1="0" x2="0" y2="5" stroke="#fff" strokeWidth="1" opacity="0.6" />
                </pattern>
              </defs>
              <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
                <g className={hover && hover.family >= 0 ? 'tl-bands hovering' : 'tl-bands'} pointerEvents="none">
                  {bands.map((d, f) => (
                    <path
                      key={f}
                      d={d ?? undefined}
                      className={hover?.family === f ? 'tl-band is-hover' : 'tl-band'}
                      fill={data.families[f].colour}
                      fillOpacity={0.9}
                      stroke="#fff"
                      strokeWidth={0.5}
                    />
                  ))}
                </g>
                {years.map((yr, i) =>
                  timeline.films[i] < THIN ? (
                    <rect
                      key={yr}
                      x={Math.max(0, x(yr) - step / 2)}
                      width={Math.min(iw, x(yr) + step / 2) - Math.max(0, x(yr) - step / 2)}
                      y={0}
                      height={ih}
                      fill="url(#tl-thin)"
                      pointerEvents="none"
                    />
                  ) : null,
                )}
                {measure === 'imdb' && (
                  <g pointerEvents="none">
                    <line className="tl-break" x1={x(SHORTS_UNTIL)} x2={x(SHORTS_UNTIL)} y1={0} y2={ih} />
                    <text className="tl-break-label" x={x(SHORTS_UNTIL) - 4} y={10} textAnchor="end">
                      with shorts
                    </text>
                    <text className="tl-break-label" x={x(SHORTS_UNTIL) + 4} y={10}>
                      features only
                    </text>
                  </g>
                )}
                {bands[family] && (
                  <path d={bands[family] ?? undefined} fill="none" stroke="var(--ink)" strokeWidth={1.25} strokeLinejoin="round" pointerEvents="none" />
                )}
                <g className="tl-axis" pointerEvents="none">
                  {Y_TICKS.map((t) => (
                    <g key={t} transform={`translate(0,${y(t)})`}>
                      {t > 0 && t < 1 && <line className="tl-grid" x2={iw} />}
                      <text x={-6} dy="0.32em" textAnchor="end">
                        {t * 100}%
                      </text>
                    </g>
                  ))}
                  {xTicks.map((t) => (
                    <g key={t} transform={`translate(${x(t)},${ih})`}>
                      <line y2={4} />
                      <text y={16} textAnchor="middle">
                        {t}
                      </text>
                    </g>
                  ))}
                  <text className="tl-ylabel" transform={`translate(${-MARGIN.left + 10},${ih / 2}) rotate(-90)`} textAnchor="middle">
                    {option.yLabel}
                  </text>
                </g>
                <g ref={brushGroup} className="tl-brush" />
              </g>
            </svg>
          )}
          {ready && tip && hover && (
            <Tooltip x={hover.px + MARGIN.left} y={hover.py + MARGIN.top} width={width} height={height}>
              {tip}
            </Tooltip>
          )}
        </div>
      </div>
    </Panel>
  )
}
