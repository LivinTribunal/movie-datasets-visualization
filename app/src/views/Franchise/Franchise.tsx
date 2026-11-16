import type { FC } from 'react'
import { Panel } from '../../components/Panel'
import type { AppData } from '../../lib/types'

export const Franchise: FC<{ data: AppData }> = () => (
  <Panel letter="D" title="Franchise lines" className="area-d">
    <p className="stub">coming next</p>
  </Panel>
)
