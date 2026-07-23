import { useEffect, useRef } from 'react'
import HeroScene from './three/HeroScene'
import { HERO_BADGES } from '../data/portfolio'
import { useMagneticEffect } from '../hooks/useMagneticEffect'

function MagneticLink({ href, children, className = '' }) {
  const ref = useMagneticEffect()
  return (
    <a ref={ref} href={href} className={className}>
      {children}
    </a>
  )
}

function KineticTitle() {
  const containerRef = useRef(null)
  const mouse = useRef({ x: 0.5, y: 0.5 })

  useEffect(() => {
    const onMouseMove = (e) => {
      mouse.current = {
        x: e.clientX / window.innerWidth,
        y: e.clientY / window.innerHeight,
      }
    }
    window.addEventListener('mousemove', onMouseMove, { passive: true })
    return () => window.removeEventListener('mousemove', onMouseMove)
  }, [])

  return (
    <h1 ref={containerRef} className="hero-title-kinetic">
      Sourav Biswas
      <span style={{ color: 'var(--cyan)' }}>.</span>
    </h1>
  )
}

export default function Hero() {
  return (
    <section id="hero" className="hero-section">
      <div className="hero-canvas-container">
        <HeroScene />
      </div>

      <div className="hero-inner">
        <div className="hero-eyebrow">
          <span className="status-dot" />
          <span>Available for projects — Pune, India</span>
        </div>

        <div className="hero-title-wrapper">
          <KineticTitle />
        </div>

        <p className="hero-desc">
          Business &amp; Data Analyst / AI &amp; Full-Stack Developer turning raw data streams into high-impact predictive decisions and 60fps web applications.
        </p>

        <div className="hero-actions">
          <MagneticLink href="#projects" className="btn btn-primary">
            Explore Selected Work →
          </MagneticLink>
          <MagneticLink href="#lab" className="btn btn-outline">
            Interactive Lab ⚡
          </MagneticLink>
        </div>

        <div className="hero-badges-grid">
          {HERO_BADGES.map((b) => (
            <div key={b.label} className="hero-badge-card">
              <div className="hero-badge-icon">{b.icon}</div>
              <div>
                <div className="hero-badge-label">{b.label}</div>
                <div className="hero-badge-sub">{b.sub}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
