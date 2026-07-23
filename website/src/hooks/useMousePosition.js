import { useEffect, useRef } from 'react'

export function useMousePosition() {
  const pos = useRef({ x: 0.5, y: 0.5 })

  useEffect(() => {
    const onMouseMove = (e) => {
      pos.current = {
        x: e.clientX / window.innerWidth,
        y: e.clientY / window.innerHeight,
      }
    }
    window.addEventListener('mousemove', onMouseMove, { passive: true })
    return () => window.removeEventListener('mousemove', onMouseMove)
  }, [])

  return pos
}
