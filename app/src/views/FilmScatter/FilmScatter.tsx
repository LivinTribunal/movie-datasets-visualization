import type { FC } from 'react'
import { Panel } from '../../components/Panel'
import type { AppData } from '../../lib/types'

export const FilmScatter: FC<{ data: AppData }> = () => (
  <Panel letter="C" title="Film scatter" className="area-c">
    <p className="stub">coming next</p>
  </Panel>
)
