import { useEffect, useRef, useState, type RefObject } from 'react'

export interface Size {
  width: number
  height: number
}

/** Ref plus the rounded content size of the element it is attached to; 0 until measured. */
export function useSize<T extends HTMLElement>(): [RefObject<T | null>, Size] {
  const ref = useRef<T | null>(null)
  const [size, setSize] = useState<Size>({ width: 0, height: 0 })
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      setSize((s) => {
        const next = { width: Math.round(width), height: Math.round(height) }
        return s.width === next.width && s.height === next.height ? s : next
      })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, size]
}
