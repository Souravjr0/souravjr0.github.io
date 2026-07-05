import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { STATS, SOCIAL_LINKS } from '../data/portfolio'

function StatCounter({ value, suffix, label }) {
  const numRef = useRef(null)

  useEffect(() => {
    const el = numRef.current
    if (!el) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          const obj = { val: 0 }
          gsap.to(obj, {
            val: value,
            duration: 2.2,
            ease: 'power2.out',
            onUpdate: () => { el.textContent = Math.round(obj.val) },
          })
          observer.unobserve(el)
        }
      },
      { threshold: 0.5 }
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [value])

  return (
    <div className="stat">
      <span>
        <span ref={numRef} className="stat-num">0</span>
        <span className="stat-pct">{suffix}</span>
      </span>
      <span className="stat-label">{label}</span>
    </div>
  )
}

export default function About() {
  const sectionRef = useRef(null)

  useEffect(() => {
    const els = sectionRef.current?.querySelectorAll('.reveal-up')
    if (!els?.length) return

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const siblings = Array.from(entry.target.parentElement?.querySelectorAll('.reveal-up') || [])
            const idx = siblings.indexOf(entry.target)
            entry.target.style.transitionDelay = `${(idx >= 0 ? idx * 0.08 : 0)}s`
            entry.target.classList.add('visible')
            observer.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.08, rootMargin: '0px 0px -40px 0px' }
    )
    els.forEach((el) => observer.observe(el))
    return () => observer.disconnect()
  }, [])

  return (
    <section id="about" className="section" ref={sectionRef}>
      <div className="container">
        <div className="split-grid">
          <div className="split-left">
            <span className="label reveal-up">About</span>
            <h2 className="heading-lg reveal-up">
              I find the pattern<br />before I touch<br />the pixels.
            </h2>
          </div>
          <div className="split-right">
            <p className="body-text reveal-up">
              I'm Sourav — a Business &amp; Data Analyst who builds AI-driven systems and immersive digital
              experiences. My background as a national championship gold-medal footballer taught me discipline,
              team rhythm, and how to deliver under pressure.
            </p>
            <p className="body-text reveal-up">
              I've driven measurable outcomes at Amazon and Constrotech — from automating reporting pipelines
              to improving search rankings and scaling revenue. I treat every data point as a human decision
              waiting to be understood.
            </p>
            <div className="stat-row reveal-up">
              {STATS.map((stat, i) => (
                <StatCounter key={i} {...stat} />
              ))}
            </div>
            <div className="link-row reveal-up">
              {SOCIAL_LINKS.map((link) => (
                <a
                  key={link.label}
                  href={link.url}
                  target="_blank"
                  rel="noopener"
                  className="text-link"
                >
                  {link.label} ↗
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
