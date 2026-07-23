import { useEffect, useRef } from 'react'

export function useMagneticEffect() {
  const ref = useRef(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const isDesktop = window.matchMedia('(hover: hover) and (pointer: fine)').matches && window.innerWidth >= 1024
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!isDesktop || prefersReduced) return

    const onMouseMove = (e) => {
      const rect = el.getBoundingClientRect()
      const x = e.clientX - rect.left - rect.width / 2
      const y = e.clientY - rect.top - rect.height / 2
      el.style.transform = `translate(${x * 0.25}px, ${y * 0.25}px)`
    }

    const onMouseLeave = () => {
      el.style.transform = 'translate(0px, 0px)'
      el.style.transition = 'transform 0.5s cubic-bezier(.34,1.56,.64,1)'
      setTimeout(() => { el.style.transition = '' }, 500)
    }

    el.addEventListener('mousemove', onMouseMove)
    el.addEventListener('mouseleave', onMouseLeave)

    return () => {
      el.removeEventListener('mousemove', onMouseMove)
      el.removeEventListener('mouseleave', onMouseLeave)
    }
  }, [])

  return ref
}
