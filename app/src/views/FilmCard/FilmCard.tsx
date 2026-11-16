import type { FC } from 'react'
import { Panel } from '../../components/Panel'
import type { AppData } from '../../lib/types'

export const FilmCard: FC<{ data: AppData }> = () => (
  <Panel letter="G" title="Film card" className="area-g">
    <p className="stub">coming next</p>
  </Panel>
)
