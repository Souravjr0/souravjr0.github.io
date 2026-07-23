import { useState, useEffect } from 'react'
import { NAV_LINKS } from '../data/portfolio'

export default function Navbar({ scrollTo, onOpenCmdPalette }) {
  const [scrolled, setScrolled] = useState(false)
  const [activeSection, setActiveSection] = useState('hero')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [scrollPercent, setScrollPercent] = useState(0)

  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY
      setScrolled(scrollY > 40)

      const winHeight = document.documentElement.scrollHeight - window.innerHeight
      if (winHeight > 0) {
        setScrollPercent(Math.min(100, Math.max(0, (scrollY / winHeight) * 100)))
      }

      // Section tracking
      const sections = NAV_LINKS.map((l) => l.href.substring(1))
      for (let i = sections.length - 1; i >= 0; i--) {
        const el = document.getElementById(sections[i])
        if (el) {
          const rect = el.getBoundingClientRect()
          if (rect.top <= 250) {
            setActiveSection(sections[i])
            break
          }
        }
      }
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <header className={`navbar ${scrolled ? 'navbar-scrolled' : ''}`}>
      <div className="nav-inner">
        <a href="#hero" className="nav-logo">
          Sourav<span>.dev</span>
        </a>

        <nav className="nav-links desktop-only">
          {NAV_LINKS.map((link) => {
            const id = link.href.substring(1)
            const isActive = activeSection === id
            return (
              <a
                key={link.label}
                href={link.href}
                className={`nav-link ${isActive ? 'active' : ''}`}
                onClick={(e) => {
                  if (scrollTo) {
                    e.preventDefault()
                    scrollTo(link.href)
                  }
                }}
              >
                {link.label}
              </a>
            )
          })}

          <button
            onClick={onOpenCmdPalette}
            className="cmd-trigger-btn"
            title="Open Command Palette (⌘K)"
          >
            ⌘K
          </button>
        </nav>

        <button
          className="mobile-toggle"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle Navigation"
        >
          {mobileOpen ? '✕' : '☰'}
        </button>

        {/* Scroll progress beam running inside navbar */}
        <div className="nav-progress-beam" style={{ width: `${scrollPercent}%` }} />
      </div>

      {/* Mobile full-screen menu overlay */}
      {mobileOpen && (
        <div className="mobile-menu-overlay">
          <div className="mobile-menu-header">
            <span className="nav-logo">Sourav<span>.dev</span></span>
            <button className="mobile-toggle" onClick={() => setMobileOpen(false)}>✕</button>
          </div>
          <div className="mobile-menu-links">
            {NAV_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="mobile-menu-link"
                onClick={() => {
                  setMobileOpen(false)
                  if (scrollTo) scrollTo(link.href)
                }}
              >
                {link.label}
              </a>
            ))}
            <button
              onClick={() => {
                setMobileOpen(false)
                onOpenCmdPalette()
              }}
              className="btn btn-primary"
              style={{ marginTop: '20px' }}
            >
              Command Palette (⌘K)
            </button>
          </div>
        </div>
      )}
    </header>
  )
}
