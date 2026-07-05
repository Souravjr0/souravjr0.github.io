import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

export function useScrollAnimations() {
  const heroTl = useRef(null)
  const horizontalTl = useRef(null)

  useEffect(() => {
    // Hero entrance timeline
    const hero = document.querySelector('.hero-section')
    if (hero) {
      const tl = gsap.timeline({ defaults: { ease: 'power4.out' } })
      tl.from('.hero-line-inner', { yPercent: 120, duration: 1.3, stagger: 0.12 })
        .from('.hero-eyebrow', { opacity: 0, y: 20, duration: 0.8 }, '-=0.7')
        .from('.hero-desc', { opacity: 0, y: 20, duration: 0.8 }, '-=0.5')
        .from('.hero-actions', { opacity: 0, y: 20, duration: 0.8 }, '-=0.4')
        .from('.hero-scroll-cue', { opacity: 0, duration: 0.6 }, '-=0.3')
      heroTl.current = tl
    }

    // Horizontal scroll projects
    const track = document.querySelector('.projects-track')
    if (track) {
      const getScrollAmount = () => -(track.scrollWidth - window.innerWidth)
      const tl = gsap.to(track, {
        x: getScrollAmount,
        ease: 'none',
        scrollTrigger: {
          trigger: '.projects-section',
          start: 'top top',
          end: () => '+=' + (track.scrollWidth - window.innerWidth),
          scrub: 1,
          pin: true,
          invalidateOnRefresh: true,
          anticipatePin: 1,
        },
      })
      horizontalTl.current = tl
    }

    ScrollTrigger.refresh()

    const handleResize = () => ScrollTrigger.refresh()
    window.addEventListener('resize', handleResize)

    return () => {
      ScrollTrigger.getAll().forEach((st) => st.kill())
      window.removeEventListener('resize', handleResize)
    }
  }, [])

  return { heroTl, horizontalTl }
}
