import type { FC, ReactNode } from 'react'

interface PanelProps {
  letter: string
  title: string
  tools?: ReactNode
  note?: ReactNode
  className?: string
  children?: ReactNode
}

export const Panel: FC<PanelProps> = ({ letter, title, tools, note, className, children }) => (
  <section className={className ? `panel ${className}` : 'panel'} aria-label={title}>
    <header className="panel-head">
      <span className="letter">{letter}</span>
      <h2>{title}</h2>
      {tools && <div className="panel-tools">{tools}</div>}
    </header>
    <div className="panel-body">{children}</div>
    {note && <p className="panel-note">{note}</p>}
  </section>
)
