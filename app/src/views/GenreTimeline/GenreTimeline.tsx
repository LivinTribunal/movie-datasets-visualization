import type { FC } from 'react'
import { Panel } from '../../components/Panel'
import type { AppData } from '../../lib/types'

export const GenreTimeline: FC<{ data: AppData }> = () => (
  <Panel letter="B" title="Genre timeline" className="area-b">
    <p className="stub">coming next</p>
  </Panel>
)
