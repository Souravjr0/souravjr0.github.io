import { useEffect, useRef, useState } from 'react'
import HeroScene from './three/HeroScene'
import { HERO_BADGES } from '../data/portfolio'
import { useMagneticEffect } from '../hooks/useMagneticEffect'
import { useIsTouchDevice } from '../hooks/useAnimev4'

function MagneticLink({ href, children, className = '' }) {
  const ref = useMagneticEffect()
  return (
    <a ref={ref} href={href} className={className}>
      {children}
    </a>
  )
}

function MagneticStatCard({ badge }) {
  const cardRef = useRef(null)
  const isTouch = useIsTouchDevice()

  const handleMouseMove = (e) => {
    if (isTouch || !cardRef.current) return
    const rect = cardRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left - rect.width / 2
    const y = e.clientY - rect.top - rect.height / 2
    const rotateX = (-y / rect.height) * 12
    const rotateY = (x / rect.width) * 12
    cardRef.current.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-4px)`
  }

  const handleMouseLeave = () => {
    if (!cardRef.current) return
    cardRef.current.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px)`
  }

  return (
    <div
      ref={cardRef}
      className="hero-badge-card"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{ transition: 'transform 0.2s ease-out' }}
    >
      <div className="hero-badge-icon">{badge.icon}</div>
      <div>
        <div className="hero-badge-label">{badge.label}</div>
        <div className="hero-badge-sub">{badge.sub}</div>
      </div>
    </div>
  )
}

export default function Hero() {
  const [fpsText, setFpsText] = useState('SIGNAL: STABLE // 60 FPS')

  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY
      if (scrollY < 100) setFpsText('SIGNAL: STABLE // 60 FPS')
      else if (scrollY < 600) setFpsText('SIGNAL: PROCESSING // 60 FPS')
      else setFpsText('SIGNAL: DEEP INGEST // 60 FPS')
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <section id="hero" className="hero-section">
      <div className="hero-canvas-container">
        <HeroScene />
      </div>

      <div className="hero-inner">
        <div className="hero-eyebrow">
          <span className="status-dot" />
          <span>Available for projects — Pune, India</span>
          <span style={{ marginLeft: '12px', color: 'var(--coral)', fontFamily: 'var(--mono)', fontSize: '0.78rem' }}>
            [{fpsText}]
          </span>
        </div>

        <div className="hero-title-wrapper">
          <h1 className="hero-title-kinetic">
            <span>Sourav </span>
            <span className="shimmer-text">Biswas</span>
            <span style={{ color: 'var(--coral)' }}>.</span>
          </h1>
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
            <MagneticStatCard key={b.label} badge={b} />
          ))}
        </div>
      </div>
    </section>
  )
}
