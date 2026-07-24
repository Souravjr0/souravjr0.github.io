import { useEffect } from 'react'
import { prefersReducedMotion } from '../motion'

// One coherent scroll entrance for every top-level section: add `.in-view`
// once it scrolls into view. Native IntersectionObserver — lighter than the
// GSAP ScrollTrigger reveal it replaces, and every section enters identically.
export function useSectionReveal(selector = '.section-container') {
  useEffect(() => {
    const els = document.querySelectorAll(selector)
    if (!els.length) return

    if (prefersReducedMotion()) {
      els.forEach((el) => el.classList.add('in-view'))
      return
    }

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('in-view')
            io.unobserve(e.target)
          }
        })
      },
      { threshold: 0.12, rootMargin: '0px 0px -8% 0px' }
    )
    els.forEach((el) => io.observe(el))
    return () => io.disconnect()
  }, [selector])
}
