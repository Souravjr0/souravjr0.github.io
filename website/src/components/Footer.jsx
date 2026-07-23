export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div>
          © {new Date().getFullYear()} Sourav Biswas. Built with React, Three.js &amp; Anime.js.
        </div>
        <div>
          <a href="#hero" style={{ color: 'var(--cyan)' }}>
            Back to Top ↑
          </a>
        </div>
      </div>
    </footer>
  )
}
