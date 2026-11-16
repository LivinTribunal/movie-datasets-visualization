import { useCallback, useEffect, useMemo, useRef, useState, type FC, type MouseEvent } from 'react'
import {
  geoEqualEarth, geoPath, interpolateBlues, interpolatePuOr, scaleDiverging, scaleSequential, select, zoom,
  zoomIdentity, type ZoomBehavior,
} from 'd3'
import { feature } from 'topojson-client'
import type { Feature, FeatureCollection, Geometry } from 'geojson'
import type { GeometryCollection, Topology } from 'topojson-specification'
import { ChipGroup } from '../../components/ChipGroup'
import { Panel } from '../../components/Panel'
import { Tooltip } from '../../components/Tooltip'
import { THIN, countryStats, share, shareDiff, topFamily, worldShares, type CountryStat } from '../../lib/countryShares'
import { loadTopo, useLazy } from '../../lib/data'
import { fmtInt, fmtPct } from '../../lib/format'
import { useSize } from '../../lib/hooks'
import type { AppData } from '../../lib/types'
import { useStore, type MapMode } from '../../state/store'
import { MapLegend } from './MapLegend'
import { MapPaths, type MapShape } from './MapPaths'
import './worldmap.css'

const SOURCE = [
  { value: 'netflix', label: 'Netflix' },
  { value: 'cinema', label: 'Cinema' },
  { value: 'production', label: 'Made here' },
] as const
const MODES: { value: MapMode; label: string }[] = [
  { value: 'share', label: 'share of genre' },
  { value: 'top', label: 'top genre' },
  { value: 'diff', label: 'cinema − streaming' },
]

type CountryFeature = Feature<Geometry, { name: string }> & { id?: string }

interface Hover { iso2: string; x: number; y: number }

const ZOOM_STEP = 1.6
const RAMP_STEPS = 7
const ANTARCTICA = '010'

function sourceLabel(stat: CountryStat, source: string): string {
  if (source === 'netflix') return 'Netflix Top 10'
  if (source === 'production') return 'films produced here (TMDB)'
  return stat.measure === 'gross_usd' ? 'US box office (The Numbers)' : 'cinema admissions (LUMIERE)'
}

const yearsLabel = ([a, b]: [number, number]) => (a === b ? `${a}` : `${a}–${b}`)

function emptyNote(source: string, yearRange: [number, number]): string {
  if (source === 'netflix' && yearRange[1] < 2021) return 'Netflix charts start in 2021'
  if (source === 'cinema') return 'Cinema data covers 1996–2025 (US from 1980)'
  if (source === 'netflix') return 'Netflix charts cover 2021–2026'
  return 'No data in this window'
}

export const WorldMap: FC<{ data: AppData }> = ({ data }) => {
  const yearRange = useStore((s) => s.yearRange)
  const family = useStore((s) => s.family)
  const source = useStore((s) => s.source)
  const mapMode = useStore((s) => s.mapMode)
  const selected = useStore((s) => s.countries)
  const setMapMode = useStore((s) => s.setMapMode)
  const setSource = useStore((s) => s.setSource)
  const setFamily = useStore((s) => s.setFamily)
  const toggleCountry = useStore((s) => s.toggleCountry)

  const topo = useLazy(loadTopo)
  const [bodyRef, { width, height }] = useSize<HTMLDivElement>()
  const svgRef = useRef<SVGSVGElement | null>(null)
  const gRef = useRef<SVGGElement | null>(null)
  const zoomRef = useRef<ZoomBehavior<SVGSVGElement, unknown> | null>(null)
  const [zoomed, setZoomed] = useState(false)
  const [hover, setHover] = useState<Hover | null>(null)

  const nFamilies = data.families.length
  const stats = useMemo(
    () => countryStats(data.countryGenre, data.countryYear, data.genreFamily, nFamilies, source, yearRange),
    [data, nFamilies, source, yearRange],
  )
  const cinema = useMemo(
    () => (mapMode === 'diff'
      ? countryStats(data.countryGenre, data.countryYear, data.genreFamily, nFamilies, 'cinema', yearRange)
      : null),
    [data, nFamilies, mapMode, yearRange],
  )
  const netflix = useMemo(
    () => (mapMode === 'diff'
      ? countryStats(data.countryGenre, data.countryYear, data.genreFamily, nFamilies, 'netflix', yearRange)
      : null),
    [data, nFamilies, mapMode, yearRange],
  )
  const diffs = useMemo(() => (cinema && netflix ? shareDiff(cinema, netflix, family) : null), [cinema, netflix, family])
  const world = useMemo(() => worldShares(stats, nFamilies), [stats, nFamilies])

  const features = useMemo(() => {
    if (!topo) return []
    const t = topo as Topology
    const fc = feature(t, t.objects.countries as GeometryCollection<{ name: string }>) as FeatureCollection<
      Geometry,
      { name: string }
    >
    return (fc.features as CountryFeature[]).filter((f) => f.id !== ANTARCTICA)
  }, [topo])

  const iso2ByNumeric = useMemo(() => {
    const m = new Map<string, string>()
    for (const c of data.countries) if (c.iso_numeric) m.set(c.iso_numeric, c.iso2)
    return m
  }, [data.countries])

  const path = useMemo(() => {
    if (width === 0 || height === 0 || features.length === 0) return null
    const projection = geoEqualEarth().fitExtent(
      [[10, 10], [width - 10, height - 10]],
      { type: 'FeatureCollection', features },
    )
    return geoPath(projection)
  }, [width, height, features])

  const geometry = useMemo(() => {
    if (!path) return []
    return features.map((f, i) => ({
      key: f.id ?? `x${i}`,
      iso2: f.id ? (iso2ByNumeric.get(f.id) ?? null) : null,
      d: path(f) ?? '',
      feature: f,
    }))
  }, [features, path, iso2ByNumeric])

  const colouring = useMemo(() => {
    const values = new Map<string, number>()
    if (mapMode === 'share') {
      for (const [iso2, s] of stats) {
        const v = share(s, family)
        if (!Number.isNaN(v)) values.set(iso2, v)
      }
    } else if (mapMode === 'diff' && diffs) {
      for (const [iso2, v] of diffs) values.set(iso2, v)
    }
    // The scale tops out at the largest value among countries with enough entries;
    // a thin country (dotted outline) may exceed it and then takes the darkest colour.
    let max = 0
    let maxAll = 0
    for (const [iso2, v] of values) {
      maxAll = Math.max(maxAll, Math.abs(v))
      if (mapMode !== 'share' || (stats.get(iso2)?.entries ?? 0) >= THIN) max = Math.max(max, Math.abs(v))
    }
    max = max || maxAll || 0.01
    const clipped = maxAll > max
    const colour: (iso2: string) => string | null = (iso2) => {
      if (mapMode === 'top') {
        const s = stats.get(iso2)
        return s && s.total > 0 ? data.families[topFamily(s)].colour : null
      }
      const v = values.get(iso2)
      if (v === undefined) return null
      return mapMode === 'share' ? scaleSequential(interpolateBlues).domain([0, max])(v) : diffScale(max)(v)
    }
    const ramp = Array.from({ length: RAMP_STEPS }, (_, i) => {
      const t = i / (RAMP_STEPS - 1)
      return mapMode === 'diff' ? diffScale(max)(-max + 2 * max * t) : scaleSequential(interpolateBlues).domain([0, max])(max * t)
    })
    return { colour, ramp, max, clipped }
  }, [mapMode, stats, diffs, family, data.families])

  const shapes: MapShape[] = useMemo(
    () => geometry.map((g) => {
      const fill = g.iso2 ? colouring.colour(g.iso2) : null
      const thin = g.iso2 !== null && (mapMode === 'diff'
        ? Math.min(cinema?.get(g.iso2)?.entries ?? Infinity, netflix?.get(g.iso2)?.entries ?? Infinity) < THIN
        : (stats.get(g.iso2)?.entries ?? Infinity) < THIN)
      return { key: g.key, iso2: g.iso2, d: g.d, fill: fill ?? 'url(#map-hatch)', thin }
    }),
    [geometry, colouring, mapMode, stats, cinema, netflix],
  )

  const ready = path !== null && features.length > 0

  useEffect(() => {
    const svg = svgRef.current
    if (!svg || !ready || width === 0 || height === 0) return
    const behaviour = zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, 12])
      .extent([[0, 0], [width, height]])
      .translateExtent([[0, 0], [width, height]])
      .on('zoom', (e) => {
        gRef.current?.setAttribute('transform', e.transform.toString())
        // zooming in then out leaves float dust in the transform
        setZoomed(Math.abs(e.transform.k - 1) > 1e-3 || Math.abs(e.transform.x) > 0.5 || Math.abs(e.transform.y) > 0.5)
      })
    const sel = select(svg)
    sel.call(behaviour).on('dblclick.zoom', null)
    zoomRef.current = behaviour
    return () => {
      sel.on('.zoom', null)
    }
  }, [width, height, ready])

  const zoomBy = (k: number) => {
    const svg = svgRef.current
    if (svg && zoomRef.current) select(svg).transition().duration(200).call(zoomRef.current.scaleBy, k)
  }
  const resetZoom = () => {
    const svg = svgRef.current
    if (svg && zoomRef.current) select(svg).transition().duration(300).call(zoomRef.current.transform, zoomIdentity)
  }

  const onHover = useCallback((iso2: string | null, e: MouseEvent) => {
    if (!iso2) return setHover(null)
    const box = bodyRef.current?.getBoundingClientRect()
    if (box) setHover({ iso2, x: e.clientX - box.left, y: e.clientY - box.top })
  }, [bodyRef])

  const onDoubleClick = useCallback((key: string) => {
    const svg = svgRef.current
    const g = geometry.find((x) => x.key === key)
    if (!svg || !zoomRef.current || !path || !g) return
    const [[x0, y0], [x1, y1]] = path.bounds(g.feature)
    const k = Math.min(12, 0.9 / Math.max((x1 - x0) / width, (y1 - y0) / height))
    const t = zoomIdentity.translate(width / 2 - (k * (x0 + x1)) / 2, height / 2 - (k * (y0 + y1)) / 2).scale(k)
    select(svg).transition().duration(500).call(zoomRef.current.transform, t)
  }, [geometry, path, width, height])

  const tooltip = useMemo(() => {
    if (!hover) return null
    const country = data.countryByIso2.get(hover.iso2)
    const name = country?.name ?? hover.iso2
    const familyName = data.families[family].name
    if (mapMode === 'diff') {
      const c = cinema?.get(hover.iso2)
      const n = netflix?.get(hover.iso2)
      if (!c || !n) return <><b>{name}</b><br />no data in this source and window</>
      const d = share(c, family) - share(n, family)
      return (
        <>
          <b>{name}</b><br />
          {familyName}: {fmtPct(share(c, family))} in cinemas, {fmtPct(share(n, family))} on Netflix<br />
          difference: {d >= 0 ? '+' : '−'}{(Math.abs(d) * 100).toFixed(1)} percentage points<br />
          based on {fmtInt(c.entries)} cinema and {fmtInt(n.entries)} Netflix entries
        </>
      )
    }
    const s = stats.get(hover.iso2)
    if (!s) return <><b>{name}</b><br />no data in this source and window</>
    return (
      <>
        <b>{name}</b> · top genre: {data.families[topFamily(s)].name}<br />
        selected ({familyName}): {fmtPct(share(s, family))} · all countries: {fmtPct(world[family])}<br />
        based on {fmtInt(s.entries)} entries, {yearsLabel(s.years)} · source: {sourceLabel(s, source)}
        {s.estimated > 0 && <><br />estimated by LUMIERE: {Math.round(s.estimated * 100)}%</>}
        {s.fuzzy > 0 && <><br />fuzzy title matches: {Math.round(s.fuzzy * 100)}%</>}
      </>
    )
  }, [hover, data, family, mapMode, stats, cinema, netflix, world, source])

  const nWithData = mapMode === 'diff' ? (diffs?.size ?? 0) : stats.size
  const note = nWithData === 0 ? emptyNote(mapMode === 'diff' ? 'cinema' : source, yearRange) : `${nWithData} countries with data`

  const rampLabels = mapMode === 'diff'
    ? { lo: `−${(colouring.max * 100).toFixed(0)} pp`, hi: `+${(colouring.max * 100).toFixed(0)} pp`, unit: 'cinema share − Netflix share (percentage points)' }
    : { lo: '0%', hi: `${fmtPct(colouring.max)}${colouring.clipped ? ' or more' : ''}`, unit: `share of ${data.families[family].name} (% of genre score)` }

  return (
    <Panel
      letter="A"
      title="World map"
      className="area-a"
      note={note}
      tools={
        <>
          <ChipGroup label="Map source" options={[...SOURCE]} value={source} onChange={setSource} />
          <ChipGroup label="Map mode" options={MODES} value={mapMode} onChange={setMapMode} />
        </>
      }
    >
      <div ref={bodyRef} className="worldmap">
        {!ready && <p className="stub">Loading map…</p>}
        {ready && (
          <>
            <svg ref={svgRef} width={width} height={height}>
              <defs>
                <pattern id="map-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                  <rect width="6" height="6" fill="var(--fill)" />
                  <line x1="0" y1="0" x2="0" y2="6" stroke="var(--fill-2)" strokeWidth="1.5" />
                </pattern>
              </defs>
              <g ref={gRef}>
                <MapPaths shapes={shapes} onHover={onHover} onClick={toggleCountry} onDoubleClick={onDoubleClick} />
                {geometry.filter((g) => g.iso2 && selected.includes(g.iso2)).map((g) => (
                  <path key={g.key} d={g.d} className="country-selected" />
                ))}
                {hover && geometry.filter((g) => g.iso2 === hover.iso2).map((g) => (
                  <path key={g.key} d={g.d} className="country-hover" />
                ))}
              </g>
            </svg>
            <div className="map-zoom">
              <div className="map-zoom-group">
                <button type="button" aria-label="Zoom in" onClick={() => zoomBy(ZOOM_STEP)}>+</button>
                <button type="button" aria-label="Zoom out" onClick={() => zoomBy(1 / ZOOM_STEP)}>−</button>
              </div>
              {zoomed && <button type="button" className="btn" onClick={resetZoom}>reset view</button>}
            </div>
            <MapLegend
              mode={mapMode}
              ramp={colouring.ramp}
              lo={rampLabels.lo}
              hi={rampLabels.hi}
              unit={rampLabels.unit}
              families={data.families}
              family={family}
              onFamily={setFamily}
            />
            {hover && <Tooltip x={hover.x} y={hover.y} width={width} height={height}>{tooltip}</Tooltip>}
          </>
        )}
      </div>
    </Panel>
  )
}

const diffScale = (m: number) => scaleDiverging(interpolatePuOr).domain([-m, 0, m])
