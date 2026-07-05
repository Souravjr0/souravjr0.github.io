import { SOCIAL_LINKS } from '../data/portfolio'

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <span className="footer-copy">&copy; {new Date().getFullYear()} Sourav Biswas</span>
        <nav className="footer-links">
          {SOCIAL_LINKS.map((link) => (
            <a key={link.label} href={link.url} target="_blank" rel="noopener">
              {link.label}
            </a>
          ))}
          <a href="mailto:biswasmail631@gmail.com">Email</a>
        </nav>
      </div>
    </footer>
  )
}
