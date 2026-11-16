import type { FC } from 'react'
import { Panel } from '../../components/Panel'
import { loadText, useLazy } from '../../lib/data'
import { fmtInt } from '../../lib/format'
import { MEASURE_KEYS, MEASURES, measureColumn, PRESETS, type MeasureKey } from '../../lib/measures'
import { scatterRows } from '../../lib/scatter'
import type { AppData } from '../../lib/types'
import { useFilmMask } from '../../state/selectors'
import { useStore } from '../../state/store'
import { Plot } from './Plot'
import { useSize } from '../../lib/hooks'
import './scatter.css'

const isLog = (key: MeasureKey) => MEASURES[key].scale === 'log'

function hiddenNote(rows: number, missingX: number, missingY: number, xKey: MeasureKey, yKey: MeasureKey): string {
  const parts = [`${fmtInt(rows)} films`]
  if (missingX > 0) parts.push(`${fmtInt(missingX)} hidden: no ${MEASURES[xKey].label}`)
  if (missingY > 0) parts.push(`${fmtInt(missingY)} hidden: no ${MEASURES[yKey].label}`)
  return parts.join(' · ')
}

export const FilmScatter: FC<{ data: AppData }> = ({ data }) => {
  const x = useStore((s) => s.x)
  const y = useStore((s) => s.y)
  const size = useStore((s) => s.size)
  const money = useStore((s) => s.money)
  const family = useStore((s) => s.family)
  const brush = useStore((s) => s.brush)
  const franchise = useStore((s) => s.franchise)
  const setX = useStore((s) => s.setX)
  const setY = useStore((s) => s.setY)
  const setSize = useStore((s) => s.setSize)
  const mask = useFilmMask(data)
  const titles = useLazy(loadText)?.title ?? null
  const [ref, { width, height }] = useSize<HTMLDivElement>()

  const xCol = measureColumn(data.films, x, money)
  const yCol = measureColumn(data.films, y, money)
  const sizeCol = size ? measureColumn(data.films, size, money) : null
  const { rows, missingX, missingY } = scatterRows(xCol, yCol, mask, isLog(x), isLog(y))

  const applyPreset = (px: MeasureKey, py: MeasureKey) => {
    if (px === y && py === x) {
      const spare = MEASURE_KEYS.find((k) => k !== px && k !== py)
      if (spare) setX(spare)
      setY(py)
      setX(px)
    } else if (px === y) {
      setY(py)
      setX(px)
    } else {
      setX(px)
      setY(py)
    }
  }

  const tools = (
    <>
      <select aria-label="X axis" value={x} onChange={(e) => setX(e.target.value as MeasureKey)}>
        {MEASURE_KEYS.map((k) => (
          <option key={k} value={k} disabled={k === y}>{MEASURES[k].label}</option>
        ))}
      </select>
      <select aria-label="Y axis" value={y} onChange={(e) => setY(e.target.value as MeasureKey)}>
        {MEASURE_KEYS.map((k) => (
          <option key={k} value={k} disabled={k === x}>{MEASURES[k].label}</option>
        ))}
      </select>
      <select
        aria-label="Size"
        value={size ?? ''}
        onChange={(e) => setSize(e.target.value === '' ? null : (e.target.value as MeasureKey))}
      >
        <option value="">size: none</option>
        {MEASURE_KEYS.map((k) => (
          <option key={k} value={k}>size: {MEASURES[k].label}</option>
        ))}
      </select>
    </>
  )

  return (
    <Panel
      letter="C"
      title="Film scatter"
      className="area-c"
      tools={tools}
      note={hiddenNote(rows.length, missingX, missingY, x, y)}
    >
      <div className="scatter">
        <div className="scatter-presets">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              type="button"
              className="chip"
              aria-pressed={p.x === x && p.y === y}
              onClick={() => applyPreset(p.x, p.y)}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div ref={ref} className="scatter-plot">
          {rows.length === 0 ? (
            <p className="stub">No films have both values under these filters.</p>
          ) : (
            width > 0 &&
            height > 0 && (
              <Plot
                data={data} rows={rows} xCol={xCol} yCol={yCol} xKey={x} yKey={y} sizeCol={sizeCol}
                family={family} franchise={franchise} brush={brush} money={money} titles={titles}
                width={width} height={height}
              />
            )
          )}
        </div>
      </div>
    </Panel>
  )
}
