import type { FC } from 'react'
import { Panel } from '../../components/Panel'
import type { AppData } from '../../lib/types'

export const WorldMap: FC<{ data: AppData }> = () => (
  <Panel letter="A" title="World map" className="area-a">
    <p className="stub">coming next</p>
  </Panel>
)
