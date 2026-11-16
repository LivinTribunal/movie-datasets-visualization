import type { FC, ReactNode } from 'react'

interface TooltipProps {
  x: number
  y: number
  width?: number
  height?: number
  children: ReactNode
}

const OFFSET = 12

/** Place inside a `position: relative` parent. Flips left/up past the parent's middle. */
export const Tooltip: FC<TooltipProps> = ({ x, y, width, height, children }) => {
  if (children == null) return null
  const left = width !== undefined && x > width / 2
  const up = height !== undefined && y > height / 2
  const tx = left ? `calc(${x - OFFSET}px - 100%)` : `${x + OFFSET}px`
  const ty = up ? `calc(${y - OFFSET}px - 100%)` : `${y + OFFSET}px`
  return (
    <div className="tooltip" style={{ transform: `translate(${tx}, ${ty})` }}>
      {children}
    </div>
  )
}
