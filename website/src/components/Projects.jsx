import { PROJECTS } from '../data/portfolio'

export default function Projects() {
  return (
    <section id="projects" className="section-container">
      <div className="section-header">
        <div className="section-kicker">📁 Featured Engineering</div>
        <h2 className="section-title">Selected Projects &amp; Repositories</h2>
        <p className="section-subtitle">
          Open-source AI guardrails, Web3 crypto interfaces, and production analytics tools.
        </p>
      </div>

      <div className="projects-grid">
        {PROJECTS.map((proj) => (
          <div key={proj.id} className="project-card" style={{ background: proj.gradient }}>
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
                View Repository ↗
              </a>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
