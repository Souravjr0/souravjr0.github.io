import { useEffect, useRef, useState } from 'react'
import { METHODOLOGY } from '../data/portfolio'
import { animate } from 'animejs'
import { EASE, DUR } from '../motion'

export default function WorkflowPipeline() {
  const [activeStep, setActiveStep] = useState(0)
  const containerRef = useRef(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          // Sequential step activation
          animate('.pipeline-card', {
            opacity: [0.3, 1],
            translateY: [20, 0],
            duration: DUR.base,
            delay: (el, i) => i * 200,
            ease: EASE.out,
          })
          observer.disconnect()
        }
      },
      { threshold: 0.3 }
    )
    if (containerRef.current) observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

  return (
    <section id="workflow" ref={containerRef} className="section-container">
      <div className="section-header">
        <div className="section-kicker">🔄 Methodology &amp; Engineering</div>
        <h2 className="section-title">How Projects Come To Life</h2>
        <p className="section-subtitle">
          From raw data exploration to production ML pipelines and reactive full-stack web applications.
        </p>
      </div>

      <div className="pipeline-grid">
        {METHODOLOGY.map((item, idx) => {
          const isActive = activeStep === idx
          return (
            <div
              key={item.step}
              className={`pipeline-card ${isActive ? 'active-pipeline' : ''}`}
              onMouseEnter={() => setActiveStep(idx)}
            >
              <div className="pipeline-step">
                <span>{item.step}</span>
                <span className="pipeline-icon">{item.icon}</span>
              </div>
              <div className="pipeline-phase">{item.phase}</div>
              <h3 className="pipeline-title">{item.title}</h3>
              <p className="pipeline-desc">{item.desc}</p>

              <div className="pipeline-tags">
                {item.tags.map((tag) => (
                  <span key={tag} className="pipeline-tag">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
