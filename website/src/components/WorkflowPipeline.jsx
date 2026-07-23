import { METHODOLOGY } from '../data/portfolio'

export default function WorkflowPipeline() {
  return (
    <section id="workflow" className="section-container">
      <div className="section-header">
        <div className="section-kicker">🔄 Methodology &amp; Engineering</div>
        <h2 className="section-title">How Projects Come To Life</h2>
        <p className="section-subtitle">
          From raw data exploration to production ML pipelines and reactive full-stack web applications.
        </p>
      </div>

      <div className="pipeline-grid">
        {METHODOLOGY.map((item) => (
          <div key={item.step} className="pipeline-card">
            <div className="pipeline-step">
              <span>{item.step}</span>
              <span className="pipeline-icon">{item.icon}</span>
            </div>
            <div className="pipeline-phase">{item.phase}</div>
            <h3 className="pipeline-title">{item.title}</h3>
            <p className="pipeline-desc">{item.desc}</p>
            <div className="pipeline-tags">
              {item.tags.map((tag) => (
                <span key={tag} className="pipeline-tag">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
