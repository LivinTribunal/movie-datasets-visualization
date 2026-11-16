import { useEffect, useRef, useState } from 'react'
import type { FC } from 'react'
import { Panel } from '../../components/Panel'
import { loadText, useLazy } from '../../lib/data'
import { fmtInt } from '../../lib/format'
import { useSize } from '../../lib/hooks'
import { MEASURE_KEYS, MEASURES, measureColumn, type MeasureKey } from '../../lib/measures'
import { brushedRows, scatterRows } from '../../lib/scatter'
import { columnMax, maskRows, sortRows, sortRowsByTitle, visibleWindow } from '../../lib/table'
import type { AppData } from '../../lib/types'
import { useFilmMask } from '../../state/selectors'
import { useStore } from '../../state/store'
import { Rows } from './Rows'
import './table.css'

const ROW_H = 24
const isLog = (key: MeasureKey) => MEASURES[key].scale === 'log'

function headerUnit(key: MeasureKey, money: 'usd2025' | 'nominal'): string {
  if (key === 'budget' || key === 'revenue') return money === 'usd2025' ? '2025 USD' : 'nominal USD'
  return MEASURES[key].unit
}

export const SelectionTable: FC<{ data: AppData }> = ({ data }) => {
  const x = useStore((s) => s.x)
  const y = useStore((s) => s.y)
  const money = useStore((s) => s.money)
  const brush = useStore((s) => s.brush)
  const sort = useStore((s) => s.sort)
  const columns = useStore((s) => s.columns)
  const pinned = useStore((s) => s.film)
  const setSort = useStore((s) => s.setSort)
  const setColumns = useStore((s) => s.setColumns)
  const mask = useFilmMask(data)
  const titles = useLazy(loadText)?.title ?? null
  const [ref, { width, height }] = useSize<HTMLDivElement>()
  const [scrollTop, setScrollTop] = useState(0)
  const scroller = useRef<HTMLDivElement | null>(null)
  const frame = useRef(0)

  const xCol = measureColumn(data.films, x, money)
  const yCol = measureColumn(data.films, y, money)
  const base = brush
    ? brushedRows(xCol, yCol, scatterRows(xCol, yCol, mask, isLog(x), isLog(y)).rows, brush)
    : maskRows(mask)

  const sortCol = sort.key === 'title' ? null : measureColumn(data.films, sort.key, money)
  const rows = sortCol
    ? sortRows(base, sortCol, sort.desc)
    : titles
      ? sortRowsByTitle(base, titles, sort.desc)
      : base

  useEffect(() => {
    if (scroller.current) scroller.current.scrollTop = 0
  }, [rows])

  useEffect(() => () => cancelAnimationFrame(frame.current), [])

  const cols = columns.map((k) => measureColumn(data.films, k, money))
  const maxima = columns.map((k, i) => (k === 'budget' || k === 'revenue' ? columnMax(cols[i], rows) : 0))
  const template = `minmax(200px, 2fr) repeat(${columns.length}, minmax(92px, 1fr))`

  const onScroll = () => {
    if (frame.current) return
    frame.current = requestAnimationFrame(() => {
      frame.current = 0
      if (scroller.current) setScrollTop(scroller.current.scrollTop)
    })
  }

  const clickHeader = (key: MeasureKey | 'title') =>
    setSort(sort.key === key ? { key, desc: !sort.desc } : { key, desc: true })

  const toggleColumn = (key: MeasureKey) => {
    const next = MEASURE_KEYS.filter((k) => (k === key ? !columns.includes(k) : columns.includes(k)))
    if (next.length > 0) setColumns(next)
  }

  const note = `${fmtInt(rows.length)} films ${brush ? 'inside the scatter brush' : 'pass the filters'} · bars share one scale per column`

  const tools = (
    <details className="columns-menu">
      <summary>columns</summary>
      <div className="columns-list">
        {MEASURE_KEYS.map((k) => (
          <label key={k}>
            <input type="checkbox" checked={columns.includes(k)} onChange={() => toggleColumn(k)} />
            {MEASURES[k].label}
          </label>
        ))}
      </div>
    </details>
  )

  const [start, end] = visibleWindow(scrollTop, height, ROW_H, rows.length)
  const ariaSort = (key: MeasureKey | 'title') =>
    sort.key === key ? (sort.desc ? 'descending' : 'ascending') : undefined
  const arrow = (key: MeasureKey | 'title') => (sort.key === key ? (sort.desc ? '▼' : '▲') : '')

  return (
    <Panel letter="E" title="Selection table" className="area-e" tools={tools} note={note}>
      <div ref={ref} className="table-wrap">
        {width > 0 && height > 0 && (
            <div ref={scroller} className="table-scroll" role="table" aria-label="Selected films" onScroll={onScroll}>
              <div role="rowgroup" className="thead">
                <div role="row" className="trow thead-row" style={{ gridTemplateColumns: template }}>
                  <div role="columnheader" aria-sort={ariaSort('title')} className="cell">
                    <button type="button" onClick={() => clickHeader('title')}>
                      <span>film</span> <span className="sort-arrow">{arrow('title')}</span>
                    </button>
                  </div>
                  {columns.map((k) => (
                    <div key={k} role="columnheader" aria-sort={ariaSort(k)} className="cell">
                      <button type="button" onClick={() => clickHeader(k)}>
                        <span>{MEASURES[k].label}</span>
                        <small>{headerUnit(k, money)}</small>
                        <span className="sort-arrow">{arrow(k)}</span>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
              {rows.length === 0 ? (
                <p className="stub">No films match. Clear the brush or widen the filters.</p>
              ) : (
                <div className="table-spacer" style={{ height: rows.length * ROW_H }}>
                  <div className="table-window" style={{ top: start * ROW_H }}>
                    <Rows
                      rows={rows} start={start} end={end} columns={columns} cols={cols} maxima={maxima}
                      titles={titles} data={data} pinned={pinned} template={template}
                    />
                  </div>
                </div>
              )}
            </div>
        )}
      </div>
    </Panel>
  )
}
