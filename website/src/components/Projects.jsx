import { PROJECTS } from '../data/portfolio'

function ProjectMotif({ id }) {
  if (id === 'claude-guardian') {
    return (
      <svg className="project-motif-svg" viewBox="0 0 100 100">
        <path d="M 50,15 L 85,30 V 60 L 50,85 L 15,60 V 30 Z" fill="none" stroke="var(--coral)" strokeWidth="2" />
        <circle cx="50" cy="50" r="15" fill="none" stroke="var(--cyan)" strokeWidth="2" strokeDasharray="3 3" />
      </svg>
    )
  }
  if (id === 'zunes-wallet') {
    return (
      <svg className="project-motif-svg" viewBox="0 0 100 100">
        <rect x="20" y="25" width="60" height="50" rx="8" fill="none" stroke="var(--cyan)" strokeWidth="2" />
        <circle cx="65" cy="50" r="6" fill="var(--coral)" />
        <line x1="10" y1="50" x2="20" y2="50" stroke="var(--cyan)" strokeWidth="2" />
      </svg>
    )
  }
  if (id === 'cluely') {
    return (
      <svg className="project-motif-svg" viewBox="0 0 100 100">
        <path d="M 15,50 Q 30,20 45,50 T 75,50 T 90,50" fill="none" stroke="var(--gold)" strokeWidth="2" />
        <circle cx="50" cy="50" r="25" fill="none" stroke="var(--coral)" strokeWidth="1.5" strokeDasharray="4 4" />
      </svg>
    )
  }
  return (
    <svg className="project-motif-svg" viewBox="0 0 100 100">
      <rect x="15" y="15" width="20" height="20" rx="4" fill="var(--coral)" opacity="0.8" />
      <rect x="40" y="15" width="20" height="20" rx="4" fill="var(--cyan)" opacity="0.6" />
      <rect x="65" y="15" width="20" height="20" rx="4" fill="var(--gold)" opacity="0.4" />
      <rect x="15" y="40" width="20" height="20" rx="4" fill="var(--cyan)" opacity="0.7" />
      <rect x="40" y="40" width="20" height="20" rx="4" fill="var(--coral)" opacity="0.9" />
    </svg>
  )
}

export default function Projects() {
  return (
    <section id="projects" className="section-container">
      <div className="section-header">
        <div className="section-kicker">📁 Orbiting Intelligence</div>
        <h2 className="section-title">Selected Projects &amp; Repositories</h2>
        <p className="section-subtitle">
          Open-source AI guardrails, Web3 crypto interfaces, and production analytics tools.
        </p>
      </div>

      <div className="projects-grid">
        {PROJECTS.map((proj) => (
          <div key={proj.id} className="project-card" style={{ background: proj.gradient }}>
            <ProjectMotif id={proj.id} />
            <span className="project-tag">{proj.tag}</span>
            <h3 className="project-title">{proj.title}</h3>
            <div className="project-subtitle">{proj.subtitle}</div>
            <p className="project-desc">{proj.description}</p>

            <ul className="project-highlights">
              {proj.highlights.map((h) => (
                <li key={h}>{h}</li>
              ))}
            </ul>

            <div className="project-footer">
              <div className="project-stack">
                {proj.stack.map((st) => (
                  <span key={st} className="pipeline-tag" style={{ color: proj.accentColor }}>
                    {st}
                  </span>
                ))}
              </div>
              <a
                href={proj.url}
                target="_blank"
                rel="noopener noreferrer"
                className="project-link"
              >
                <span>View Repository</span>
                <span className="arrow-travel">→</span>
              </a>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
