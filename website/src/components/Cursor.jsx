import { useEffect, useRef, useState } from 'react'

export default function Cursor() {
  const dotRef = useRef(null)
  const ringRef = useRef(null)
  const [visible, setVisible] = useState(false)
  const targetRef = useRef({ x: 0, y: 0 })
  const dotPos = useRef({ x: 0, y: 0 })
  const ringPos = useRef({ x: 0, y: 0 })

  useEffect(() => {
    const isDesktop = window.matchMedia('(hover: hover) and (pointer: fine)').matches && window.innerWidth >= 1024
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!isDesktop || prefersReducedMotion) return

    const dot = dotRef.current
    const ring = ringRef.current
    if (!dot || !ring) return

    const onMouseMove = (e) => {
      if (!visible) setVisible(true)
      targetRef.current = { x: e.clientX, y: e.clientY }
    }
    window.addEventListener('mousemove', onMouseMove)

    const lerp = (a, b, t) => a + (b - a) * t

    const animate = () => {
      const target = targetRef.current
      dotPos.current.x = lerp(dotPos.current.x, target.x, 0.5)
      dotPos.current.y = lerp(dotPos.current.y, target.y, 0.5)
      ringPos.current.x = lerp(ringPos.current.x, target.x, 0.12)
      ringPos.current.y = lerp(ringPos.current.y, target.y, 0.12)

      dot.style.transform = `translate(${dotPos.current.x}px, ${dotPos.current.y}px) translate(-50%, -50%)`
      ring.style.transform = `translate(${ringPos.current.x}px, ${ringPos.current.y}px) translate(-50%, -50%)`
      requestAnimationFrame(animate)
    }
    requestAnimationFrame(animate)

    // Hover effect on interactive elements
    const hoverable = document.querySelectorAll('a, button, .service-item, .skill-card, .project-card, input, textarea')
    const addHover = () => ring.classList.add('hovering')
    const removeHover = () => ring.classList.remove('hovering')
    hoverable.forEach((el) => {
      el.addEventListener('mouseenter', addHover)
      el.addEventListener('mouseleave', removeHover)
    })

    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      hoverable.forEach((el) => {
        el.removeEventListener('mouseenter', addHover)
        el.removeEventListener('mouseleave', removeHover)
      })
    }
  }, [visible])

  return (
    <>
      <div ref={dotRef} className="cursor-dot" style={{ opacity: visible ? 1 : 0 }} />
      <div ref={ringRef} className="cursor-ring" style={{ opacity: visible ? 1 : 0 }} />
    </>
  )
}
