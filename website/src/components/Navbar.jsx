import { NAV_LINKS } from '../data/portfolio'

export default function Navbar({ scrollTo }) {
  return (
    <header className="navbar">
      <div className="nav-inner">
        <a href="#hero" className="nav-logo">
          Sourav<span>.dev</span>
        </a>

        <nav className="nav-links">
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="nav-link"
              onClick={(e) => {
                if (scrollTo) {
                  e.preventDefault()
                  scrollTo(link.href)
                }
              }}
            >
              {link.label}
            </a>
          ))}
        </nav>
      </div>
    </header>
  )
}
