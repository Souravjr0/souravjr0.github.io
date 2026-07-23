import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

export function useScrollAnimations() {
  const heroTl = useRef(null)
  const horizontalTl = useRef(null)
  const sectionTls = useRef([])

  useEffect(() => {
    ScrollTrigger.refresh()
    
    // Hero entrance timeline
    const hero = document.querySelector('.hero-section')
    if (hero) {
      const tl = gsap.timeline({ defaults: { ease: 'power4.out' } })
      tl.from('.hero-title-kinetic', { opacity: 0, y: 80, duration: 1.4 }, 0.2)
        .from('.hero-eyebrow', { opacity: 0, y: 24, duration: 0.8 }, 0)
        .from('.hero-desc', { opacity: 0, y: 24, duration: 0.8 }, '-=0.4')
        .from('.hero-actions', { opacity: 0, y: 20, duration: 0.8 }, '-=0.3')
        .from('.hero-scroll-cue', { opacity: 0, duration: 0.6 }, '-=0.2')
      heroTl.current = tl
    }

    // Horizontal scroll projects
    const track = document.querySelector('.projects-track')
    if (track) {
      const getScrollAmount = () => -(track.scrollWidth - window.innerWidth + 40)
      const tl = gsap.to(track, {
        x: getScrollAmount,
        ease: 'none',
        scrollTrigger: {
          trigger: '.projects-section',
          start: 'top top',
          end: () => '+=' + Math.max(0, track.scrollWidth - window.innerWidth + 40),
          scrub: 1.2,
          pin: true,
          invalidateOnRefresh: true,
          anticipatePin: 1,
        },
      })
      horizontalTl.current = tl
    }

    // Section reveal animations
    const sections = document.querySelectorAll('.section-reveal')
    sections.forEach((section, i) => {
      const items = section.querySelectorAll('.reveal-item')
      if (items.length) {
        const tl = gsap.from(items, {
          scrollTrigger: {
            trigger: section,
            start: 'top 85%',
            toggleActions: 'play none none reverse',
          },
          opacity: 0,
          y: 40,
          duration: 0.9,
          stagger: 0.08,
          ease: 'power3.out',
        })
        sectionTls.current.push(tl)
      }
    })

    // Parallax sections
    const parallaxEls = document.querySelectorAll('.parallax-slow')
    parallaxEls.forEach((el) => {
      gsap.to(el, {
        yPercent: -15,
        ease: 'none',
        scrollTrigger: {
          trigger: el.parentElement,
          start: 'top bottom',
          end: 'bottom top',
          scrub: 1.5,
        },
      })
    })

    ScrollTrigger.refresh()

    const handleResize = () => ScrollTrigger.refresh()
    window.addEventListener('resize', handleResize)

    return () => {
      ScrollTrigger.getAll().forEach((st) => st.kill())
      sectionTls.current.forEach((tl) => tl.kill())
      window.removeEventListener('resize', handleResize)
    }
  }, [])

  return { heroTl, horizontalTl }
}
