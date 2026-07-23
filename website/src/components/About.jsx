import { useEffect, useRef } from 'react'
import { STATS } from '../data/portfolio'
import { animate } from 'animejs'
import { EASE, DUR } from '../motion'

function SparklineSVG({ color = '#ff2a5f' }) {
  return (
    <svg viewBox="0 0 100 30" className="metric-sparkline">
      <path
        d="M0 25 Q20 5 40 18 T80 10 T100 5"
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeOpacity="0.4"
      />
    </svg>
  )
}

function MetricModule({ stat }) {
  const numRef = useRef(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && numRef.current) {
          const counter = { val: 0 }
          animate(counter, {
            val: stat.value,
            round: 1,
            duration: DUR.slow,
            ease: EASE.out,
            onUpdate: () => {
              if (numRef.current) numRef.current.textContent = Math.round(counter.val)
            },
          })
          observer.disconnect()
        }
      },
      { threshold: 0.5 }
    )
    if (numRef.current) observer.observe(numRef.current)
    return () => observer.disconnect()
  }, [stat.value])

  return (
    <div className="metric-card">
      <SparklineSVG color={stat.value > 50 ? 'var(--cyan)' : 'var(--coral)'} />
      <div className="metric-val">
        <span ref={numRef}>0</span>
        <span style={{ fontSize: '1.8rem', color: 'var(--coral)' }}>{stat.suffix}</span>
      </div>
      <div className="metric-label">{stat.label}</div>
      <div className="metric-desc">{stat.desc}</div>
      <div className="metric-trace">
        <span>RAW DATA</span> → <span>MODEL FIT</span> → <span style={{ color: 'var(--coral)' }}>IMPACT</span>
      </div>
    </div>
  )
}

export default function About() {
  return (
    <section id="about" className="section-container">
      <div className="section-header">
        <div className="section-kicker">💡 About &amp; Data Impact</div>
        <h2 className="section-title">Bridging Analytics &amp; Full-Stack Engineering</h2>
      </div>

      <div className="about-grid">
        <div className="about-bio-card">
          <h3 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: '16px', color: 'var(--text)' }}>
            Empowering organizations with data-driven precision.
          </h3>
          <p className="about-paragraph">
            I specialize in transforming complex, unstructured datasets into intuitive dashboards, predictive Machine Learning models, and scalable full-stack web applications.
          </p>
          <p className="about-paragraph">
            Whether optimizing reporting infrastructure for executive decision-makers or architecting real-time WebGL interfaces, my work focuses on measurable performance, speed, and reliability.
          </p>
        </div>

        <div className="metrics-grid">
          {STATS.map((stat) => (
            <MetricModule key={stat.label} stat={stat} />
          ))}
        </div>
      </div>
    </section>
  )
}
