import { PROJECTS } from '../data/portfolio'

export default function Projects() {
  return (
    <section id="projects" className="section projects-section">
      <div className="container projects-header">
        <span className="label">Selected Work</span>
        <h2 className="heading-lg">Projects.</h2>
      </div>
      <div className="projects-track">
        {PROJECTS.map((project, i) => (
          <article key={i} className="project-card">
            <div className="pc-cover" style={{ background: project.gradient }} />
            <div className="pc-body">
              <span className="pc-tag">{project.tag}</span>
              <h3>{project.title}</h3>
              <p>{project.description}</p>
              <div className="pc-stack">
                {project.stack.map((tech) => (
                  <span key={tech}>{tech}</span>
                ))}
              </div>
              <a href={project.url} target="_blank" rel="noopener" className="pc-link">
                View ↗
              </a>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
