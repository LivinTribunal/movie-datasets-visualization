import { memo, useCallback, useEffect, useMemo, useRef, type FC, type PointerEvent } from 'react'
import {
  brush as d3brush, line, pointer, quadtree, scaleLinear, scaleLog, select,
  type Quadtree, type ScaleContinuousNumeric,
} from 'd3'
import { axisLabel, isScore, MEASURES, type MeasureKey, type Money } from '../../lib/measures'
import { fmtValue } from '../../lib/format'
import { domainOf, radiusBucket, usable } from '../../lib/scatter'
import { useStore } from '../../state/store'
import type { AppData } from '../../lib/types'
import { HoverRing, HoverTip, type Geometry } from './HoverLayer'

const MARGIN = { left: 48, right: 24, top: 8, bottom: 36 }
const BUCKETS = 6
const R_MIN = 1.5
const R_MAX = 6
const R_PLAIN = 2.25
const GREY = '#b4b8c0'
const PICK_RADIUS = 10

interface PlotProps {
  data: AppData
  rows: Uint32Array
  xCol: Float64Array
  yCol: Float64Array
  xKey: MeasureKey
  yKey: MeasureKey
  sizeCol: Float64Array | null
  family: number
  franchise: number | null
  brush: [number, number, number, number] | null
  money: Money
  titles: (string | null)[] | null
  width: number
  height: number
}

function makeScale(key: MeasureKey, domain: [number, number], range: [number, number]): ScaleContinuousNumeric<number, number> {
  const s = MEASURES[key].scale === 'log' ? scaleLog() : scaleLinear()
  return s.domain(domain).range(range).nice()
}

function sprite(colour: string, radius: number, dpr: number): HTMLCanvasElement {
  const d = Math.max(1, Math.ceil(2 * radius * dpr))
  const c = document.createElement('canvas')
  c.width = d
  c.height = d
  const ctx = c.getContext('2d')
  if (ctx) {
    ctx.fillStyle = colour
    ctx.beginPath()
    ctx.arc(d / 2, d / 2, d / 2, 0, 2 * Math.PI)
    ctx.fill()
  }
  return c
}

export function bucketRadius(bucket: number): number {
  return R_MIN + ((R_MAX - R_MIN) * bucket) / (BUCKETS - 1)
}

const PlotImpl: FC<PlotProps> = ({
  data, rows, xCol, yCol, xKey, yKey, sizeCol, family, franchise, brush, money, titles, width, height,
}) => {
  const setBrush = useStore((s) => s.setBrush)
  const setFilm = useStore((s) => s.setFilm)
  const setHoverFilm = useStore((s) => s.setHoverFilm)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const svgRef = useRef<SVGSVGElement>(null)
  const brushRef = useRef<SVGGElement>(null)
  const tree = useRef<Quadtree<number> | null>(null)
  const brushBehaviour = useRef<ReturnType<typeof d3brush<unknown>> | null>(null)

  const right = width - MARGIN.right
  const bottom = height - MARGIN.bottom
  const xScale = useMemo(
    () => makeScale(xKey, domainOf(xKey, xCol, rows), [MARGIN.left, right]),
    [xKey, xCol, rows, right],
  )
  const yScale = useMemo(
    () => makeScale(yKey, domainOf(yKey, yCol, rows), [bottom, MARGIN.top]),
    [yKey, yCol, rows, bottom],
  )
  const geometry = useMemo<Geometry>(
    () => ({ xScale, yScale, xCol, yCol, left: MARGIN.left, right, top: MARGIN.top, bottom }),
    [xScale, yScale, xCol, yCol, right, bottom],
  )

  const latest = useRef({ xScale, yScale, rows, brush })
  useEffect(() => {
    latest.current = { xScale, yScale, rows, brush }
  })

  const familyColour = data.families[family]?.colour ?? GREY
  const familyMask = data.films.family_mask

  useEffect(() => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return
    const dpr = window.devicePixelRatio || 1
    canvas.width = Math.round(width * dpr)
    canvas.height = Math.round(height * dpr)
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, width, height)

    let max = 0
    if (sizeCol) for (const r of rows) if (sizeCol[r] > max) max = sizeCol[r]
    const n = rows.length
    const px = new Float32Array(n)
    const py = new Float32Array(n)
    const radius = new Float32Array(n)
    for (let k = 0; k < n; k++) {
      const r = rows[k]
      px[k] = xScale(xCol[r])
      py[k] = yScale(yCol[r])
      radius[k] = sizeCol ? bucketRadius(radiusBucket(sizeCol[r], max, BUCKETS)) : R_PLAIN
    }

    const sprites = new Map<string, HTMLCanvasElement>()
    const stamp = (colour: string, k: number) => {
      const rad = radius[k]
      const key = `${colour}|${rad}`
      let s = sprites.get(key)
      if (!s) {
        s = sprite(colour, rad, dpr)
        sprites.set(key, s)
      }
      ctx.drawImage(s, px[k] - rad, py[k] - rad, 2 * rad, 2 * rad)
    }
    const inFamily = (k: number) => ((familyMask[rows[k]] >> family) & 1) === 1

    ctx.globalAlpha = 0.3
    for (let k = n - 1; k >= 0; k--) if (!inFamily(k)) stamp(GREY, k)
    ctx.globalAlpha = 0.55
    for (let k = n - 1; k >= 0; k--) if (inFamily(k)) stamp(familyColour, k)
    ctx.globalAlpha = 1

    tree.current = quadtree<number>()
      .x((k) => px[k])
      .y((k) => py[k])
      .addAll(Array.from({ length: n }, (_, k) => k))
  }, [rows, xCol, yCol, xScale, yScale, sizeCol, family, familyColour, familyMask, width, height])

  const nearest = useCallback((x: number, y: number): number | null => {
    const k = tree.current?.find(x, y, PICK_RADIUS)
    return k === undefined ? null : latest.current.rows[k]
  }, [])

  useEffect(() => {
    const g = brushRef.current
    if (!g) return
    let down: [number, number] | null = null
    const client = (e: MouseEvent | TouchEvent): [number, number] => {
      const t = 'changedTouches' in e ? e.changedTouches[0] : e
      return [t.clientX, t.clientY]
    }
    const b = d3brush<unknown>()
      .extent([[MARGIN.left, MARGIN.top], [right, bottom]])
      .on('start', (event) => {
        down = event.sourceEvent ? client(event.sourceEvent) : null
      })
      .on('end', (event) => {
        const src: MouseEvent | TouchEvent | null = event.sourceEvent
        if (!src) return
        const { xScale: xs, yScale: ys, brush: cur } = latest.current
        const sel: [[number, number], [number, number]] | null = event.selection
        const [cx, cy] = client(src)
        // a move under 3 px is a click, even when d3 still reports a selection
        const click = down !== null && Math.hypot(cx - down[0], cy - down[1]) < 3
        if (sel && !click) {
          const xa = xs.invert(sel[0][0])
          const xb = xs.invert(sel[1][0])
          const ya = ys.invert(sel[0][1])
          const yb = ys.invert(sel[1][1])
          setBrush([Math.min(xa, xb), Math.max(xa, xb), Math.min(ya, yb), Math.max(ya, yb)])
          return
        }
        const svg = svgRef.current
        const [x, y] = svg ? pointer(src, svg) : [NaN, NaN]
        const row = nearest(x, y)
        if (row !== null) setFilm(useStore.getState().film === row ? null : row)
        else if (cur) {
          const [px, py] = [xs.invert(x), ys.invert(y)]
          const inside = px >= cur[0] && px <= cur[1] && py >= cur[2] && py <= cur[3]
          if (!inside) setBrush(null)
        }
        // redraw the store's brush: d3 may have erased or shrunk its rectangle
        const now = useStore.getState().brush
        select(g).call(
          b.move,
          now ? [[xs(now[0]), ys(now[3])], [xs(now[1]), ys(now[2])]] : null,
        )
      })
    brushBehaviour.current = b
    select(g).call(b)
    return () => {
      select(g).on('.brush', null)
    }
  }, [right, bottom, setBrush, setFilm, nearest])

  useEffect(() => {
    const g = brushRef.current
    const b = brushBehaviour.current
    if (!g || !b) return
    select(g).call(
      b.move,
      brush ? [[xScale(brush[0]), yScale(brush[3])], [xScale(brush[1]), yScale(brush[2])]] : null,
    )
  }, [brush, xScale, yScale, right, bottom])

  const frame = useRef<number | null>(null)
  const pending = useRef<[number, number] | null>(null)
  useEffect(() => () => {
    if (frame.current !== null) cancelAnimationFrame(frame.current)
  }, [])

  const onMove = (e: PointerEvent<SVGSVGElement>) => {
    const svg = svgRef.current
    if (!svg) return
    pending.current = pointer(e.nativeEvent, svg)
    if (frame.current !== null) return
    frame.current = requestAnimationFrame(() => {
      frame.current = null
      const p = pending.current
      if (!p) return
      const row = nearest(p[0], p[1])
      if (useStore.getState().hoverFilm !== row) setHoverFilm(row)
    })
  }
  const onLeave = () => {
    pending.current = null
    if (frame.current !== null) {
      cancelAnimationFrame(frame.current)
      frame.current = null
    }
    setHoverFilm(null)
  }

  const franchisePoints = useMemo(() => {
    if (franchise === null) return []
    const f = data.franchises
    const xLog = MEASURES[xKey].scale === 'log'
    const yLog = MEASURES[yKey].scale === 'log'
    const parts: { installment: number; row: number }[] = []
    for (let i = 0; i < f.rows; i++) {
      if (f.collection_id[i] !== franchise) continue
      const row = f.film_row[i]
      if (Number.isNaN(row) || !usable(xCol[row], xLog) || !usable(yCol[row], yLog)) continue
      parts.push({ installment: f.installment[i], row })
    }
    return parts.sort((a, b) => a.installment - b.installment)
  }, [data.franchises, franchise, xKey, yKey, xCol, yCol])

  const xTicks = xScale.ticks(6)
  const yTicks = yScale.ticks(6)
  const path = line<{ row: number }>()
    .x((p) => xScale(xCol[p.row]))
    .y((p) => yScale(yCol[p.row]))
  const diagonal = isScore(xKey) && isScore(yKey)

  return (
    <>
      <canvas ref={canvasRef} className="scatter-canvas" style={{ width, height }} />
      <svg ref={svgRef} className="scatter-svg" width={width} height={height} onPointerMove={onMove} onPointerLeave={onLeave}>
        <g className="scatter-grid">
          {xTicks.map((t) => (
            <g key={`x${t}`}>
              <line x1={xScale(t)} x2={xScale(t)} y1={MARGIN.top} y2={bottom} />
              <text x={xScale(t)} y={bottom + 14} textAnchor="middle">{fmtValue(xKey, t)}</text>
            </g>
          ))}
          {yTicks.map((t) => (
            <g key={`y${t}`}>
              <line x1={MARGIN.left} x2={right} y1={yScale(t)} y2={yScale(t)} />
              <text x={MARGIN.left - 6} y={yScale(t)} dy="0.32em" textAnchor="end">{fmtValue(yKey, t)}</text>
            </g>
          ))}
        </g>
        <text className="scatter-title" x={(MARGIN.left + right) / 2} y={height - 6} textAnchor="middle">
          {axisLabel(xKey, money)}
        </text>
        <text
          className="scatter-title"
          transform={`translate(11 ${(MARGIN.top + bottom) / 2}) rotate(-90)`}
          textAnchor="middle"
        >
          {axisLabel(yKey, money)}
        </text>
        {diagonal && (
          <line
            className="scatter-diagonal"
            x1={xScale(0)} y1={yScale(0)} x2={xScale(100)} y2={yScale(100)}
          />
        )}
        <g ref={brushRef} className="scatter-brush" />
        {franchisePoints.length > 0 && (
          <g className="scatter-franchise" pointerEvents="none">
            <path d={path(franchisePoints) ?? undefined} fill="none" stroke="#fff" strokeWidth={4.5} strokeLinejoin="round" />
            <path d={path(franchisePoints) ?? undefined} fill="none" stroke="var(--ink)" strokeWidth={1.5} strokeLinejoin="round" />
            {franchisePoints.map((p) => (
              <g key={p.row}>
                <circle cx={xScale(xCol[p.row])} cy={yScale(yCol[p.row])} r={3} fill="var(--ink)" stroke="#fff" strokeWidth={1.5} />
                <text x={xScale(xCol[p.row]) + 5} y={yScale(yCol[p.row]) - 5}>#{p.installment}</text>
              </g>
            ))}
          </g>
        )}
        <HoverRing geometry={geometry} />
      </svg>
      <HoverTip
        geometry={geometry} xKey={xKey} yKey={yKey} year={data.films.year}
        titles={titles} width={width} height={height}
      />
    </>
  )
}

export const Plot = memo(PlotImpl)
