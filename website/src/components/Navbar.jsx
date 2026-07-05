import { useState, useEffect, useCallback } from 'react'
import { NAV_LINKS } from '../data/portfolio'

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [activeSection, setActiveSection] = useState('')

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 60)
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    const sections = document.querySelectorAll('section[id]')
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) setActiveSection(e.target.id)
        })
      },
      { rootMargin: '-40% 0px -55% 0px' }
    )
    sections.forEach((s) => obs.observe(s))
    return () => obs.disconnect()
  }, [])

  const handleNavClick = useCallback((href) => {
    setMenuOpen(false)
    document.body.style.overflow = ''
    const el = document.querySelector(href)
    if (el) el.scrollIntoView({ behavior: 'smooth' })
  }, [])

  const toggleMenu = () => {
    setMenuOpen((prev) => {
      document.body.style.overflow = prev ? '' : 'hidden'
      return !prev
    })
  }

  return (
    <>
      <header className={`nav-header${scrolled ? ' scrolled' : ''}`}>
        <a href="#hero" className="nav-logo" onClick={(e) => { e.preventDefault(); handleNavClick('#hero') }}>
          Sourav<span className="logo-dot">.</span>
        </a>
        <nav className={`nav-links${menuOpen ? ' open' : ''}`} aria-label="Main navigation">
          {NAV_LINKS.map((link) => (
            <button
              key={link.href}
              className={`nav-link${activeSection === link.href.slice(1) ? ' active' : ''}${link.label === 'Contact' ? ' cta-nav' : ''}`}
              onClick={() => handleNavClick(link.href)}
            >
              {link.label}
            </button>
          ))}
        </nav>
        <button
          className={`hamburger${menuOpen ? ' open' : ''}`}
          onClick={toggleMenu}
          aria-label="Toggle menu"
          aria-expanded={menuOpen}
        >
          <span /><span /><span />
        </button>
      </header>
      <div className={`nav-overlay${menuOpen ? ' visible' : ''}`} onClick={() => { setMenuOpen(false); document.body.style.overflow = '' }} />
    </>
  )
}
