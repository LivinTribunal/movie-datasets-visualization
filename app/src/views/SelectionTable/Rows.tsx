import { memo } from 'react'
import type { CSSProperties, FC, KeyboardEvent } from 'react'
import { interpolatePuOr } from 'd3'
import { fmtImdb, fmtValue } from '../../lib/format'
import { isScore, type MeasureKey } from '../../lib/measures'
import { cellKind } from '../../lib/table'
import type { AppData } from '../../lib/types'
import { useStore } from '../../state/store'

interface RowsProps {
  rows: Uint32Array
  start: number
  end: number
  columns: MeasureKey[]
  cols: Float64Array[]
  maxima: number[]
  titles: (string | null)[] | null
  data: AppData
  pinned: number | null
  template: string
}

const clamp01 = (v: number) => Math.max(0, Math.min(1, v))

function gapText(v: number): string {
  const r = Math.round(v)
  return r > 0 ? `+${r}` : r < 0 ? `−${-r}` : '0'
}

interface CellProps { kind: 'bar' | 'gap' | 'plain'; k: MeasureKey; v: number; max: number }

const Cell: FC<CellProps> = ({ kind, k, v, max }) => {
  if (Number.isNaN(v)) return <div role="cell" className="cell cell-num cell-missing">no data</div>
  if (kind === 'gap') {
    const style: CSSProperties = {
      background: interpolatePuOr(clamp01(0.5 + v / 120)),
      color: Math.abs(v) > 35 ? '#fff' : undefined,
    }
    return <div role="cell" className="cell cell-num cell-gap" style={style}>{gapText(v)}</div>
  }
  if (kind === 'bar') {
    const scaleMax = isScore(k) ? 100 : max
    const width = scaleMax > 0 ? clamp01(v / scaleMax) * 100 : 0
    return (
      <div role="cell" className="cell cell-num cell-bar">
        <span className="cell-bar-fill" style={{ width: `${width}%` }} />
        <span className="cell-bar-text">{fmtValue(k, v)}</span>
      </div>
    )
  }
  return <div role="cell" className="cell cell-num">{fmtValue(k, v)}</div>
}

export const Rows: FC<RowsProps> = memo(({ rows, start, end, columns, cols, maxima, titles, data, pinned, template }) => {
  const setFilm = useStore((s) => s.setFilm)
  const setHoverFilm = useStore((s) => s.setHoverFilm)
  const { families, films } = data

  const items = []
  for (let i = start; i < end; i++) {
    const row = rows[i]
    const title = titles?.[row] ?? null
    const label = title ?? fmtImdb(films.imdb[row])
    const mask = films.family_mask[row]
    const swatches = []
    for (let f = 0; f < families.length && swatches.length < 3; f++) {
      if (mask & (1 << f)) {
        swatches.push(
          <span key={f} className="swatch" style={{ background: families[f].colour }} title={families[f].name} />,
        )
      }
    }
    const toggle = () => setFilm(pinned === row ? null : row)
    items.push(
      <div
        key={row}
        role="row"
        className="trow"
        style={{ gridTemplateColumns: template }}
        tabIndex={0}
        aria-selected={pinned === row}
        onPointerEnter={() => setHoverFilm(row)}
        onClick={toggle}
        onKeyDown={(e: KeyboardEvent) => {
          if (e.key === 'Enter') toggle()
        }}
      >
        <div role="cell" className="cell cell-film">
          <span className="swatches">{swatches}</span>
          <span className="cell-title" title={label}>{label}</span>
        </div>
        {columns.map((k, c) => (
          <Cell key={k} kind={cellKind(k)} k={k} v={cols[c][row]} max={maxima[c]} />
        ))}
      </div>,
    )
  }

  return (
    <div role="rowgroup" className="tbody" onPointerLeave={() => setHoverFilm(null)}>
      {items}
    </div>
  )
})
Rows.displayName = 'Rows'
