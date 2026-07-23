import { useEffect, useRef, useState } from 'react'
import { useIsTouchDevice } from '../hooks/useAnimev4'

export default function Cursor() {
  const dotRef = useRef(null)
  const ringRef = useRef(null)
  const [hovered, setHovered] = useState(false)
  const isTouch = useIsTouchDevice()

  useEffect(() => {
    if (isTouch) return

    let animationId
    let mouseX = -100
    let mouseY = -100
    let ringX = -100
    let ringY = -100

    const onMouseMove = (e) => {
      mouseX = e.clientX
      mouseY = e.clientY
      if (dotRef.current) {
        dotRef.current.style.transform = `translate3d(${mouseX}px, ${mouseY}px, 0)`
      }

      const target = e.target
      const isInteractive = target.closest('a, button, input, textarea, .terminal-chip, .metric-card, .project-card, .pipeline-card')
      setHovered(!!isInteractive)
    }

    const animateRing = () => {
      ringX += (mouseX - ringX) * 0.15
      ringY += (mouseY - ringY) * 0.15

      if (ringRef.current) {
        ringRef.current.style.transform = `translate3d(${ringX}px, ${ringY}px, 0)`
      }
      animationId = requestAnimationFrame(animateRing)
    }

    window.addEventListener('mousemove', onMouseMove, { passive: true })
    animationId = requestAnimationFrame(animateRing)

    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      cancelAnimationFrame(animationId)
    }
  }, [isTouch])

  if (isTouch) return null

  return (
    <>
      <div ref={dotRef} className="cursor-dot" />
      <div ref={ringRef} className={`cursor-ring ${hovered ? 'hovered' : ''}`} />
    </>
  )
}
