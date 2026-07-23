import { useEffect, useRef } from 'react'
import { SKILL_CATEGORIES } from '../data/portfolio'
import { animate } from 'animejs'
import { EASE, DUR } from '../motion'

function SkillItem({ sk }) {
  const fillRef = useRef(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && fillRef.current) {
          animate(fillRef.current, {
            width: [`0%`, `${sk.level}%`],
            duration: DUR.slow,
            ease: EASE.out,
          })
          observer.disconnect()
        }
      },
      { threshold: 0.4 }
    )
    if (fillRef.current) observer.observe(fillRef.current)
    return () => observer.disconnect()
  }, [sk.level])

  return (
    <div className="skill-item">
      <div className="skill-item-header">
        <span className="skill-name">{sk.name}</span>
        <span className="skill-level-badge">{sk.label} ({sk.level}%)</span>
      </div>
      <div className="skill-progress-bar">
        <div ref={fillRef} className="skill-progress-fill" style={{ width: '0%' }} />
      </div>
    </div>
  )
}

export default function Skills() {
  return (
    <section id="skills" className="section-container">
      <div className="section-header">
        <div className="section-kicker">🧠 Living Technical Ecosystem</div>
        <h2 className="section-title">Tools, Frameworks &amp; Languages</h2>
        <p className="section-subtitle">
          Core technical competencies across Data Engineering, Machine Learning, and Web Technologies.
        </p>
      </div>

      <div className="skills-grid">
        {SKILL_CATEGORIES.map((cat) => (
          <div key={cat.id} className="skill-category-card">
            <div className="skill-kicker">{cat.kicker}</div>
            <h3 className="skill-cat-title">{cat.title}</h3>

            <div className="skill-list">
              {cat.skills.map((sk) => (
                <SkillItem key={sk.name} sk={sk} />
              ))}
            </div>

            <div className="skill-chips">
              {cat.chips.map((chip) => (
                <span key={chip} className="skill-chip">
                  {chip}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
