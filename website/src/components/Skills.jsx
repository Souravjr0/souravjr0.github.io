import { useEffect, useRef } from 'react'
import { SKILL_CATEGORIES } from '../data/portfolio'

function SkillBar({ name, level, label }) {
  const fillRef = useRef(null)

  useEffect(() => {
    const fill = fillRef.current
    if (!fill) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          fill.style.width = `${level}%`
          observer.unobserve(entry.target)
        }
      },
      { threshold: 0.3 }
    )
    observer.observe(fill.parentElement)
    return () => observer.disconnect()
  }, [level])

  return (
    <div className="skill-row">
      <div className="skill-head">
        <span>{name}</span>
        <span>{label}</span>
      </div>
      <div className="skill-track">
        <div ref={fillRef} className="skill-fill" />
      </div>
    </div>
  )
}

export default function Skills() {
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
    <section id="skills" className="section" ref={sectionRef}>
      <div className="container">
        <span className="label reveal-up">Technical Stack</span>
        <h2 className="heading-lg reveal-up">Tools I Use.</h2>
        <div className="skills-grid">
          {SKILL_CATEGORIES.map((cat, i) => (
            <article key={i} className="skill-card reveal-up">
              <span className="skill-kicker">{cat.kicker}</span>
              <h3>{cat.title}</h3>
              <div className="skill-list">
                {cat.skills.map((skill) => (
                  <SkillBar key={skill.name} {...skill} />
                ))}
              </div>
              <div className="chip-row">
                {cat.chips.map((chip) => (
                  <span key={chip}>{chip}</span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
