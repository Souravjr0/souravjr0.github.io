import { STATS } from '../data/portfolio'

export default function About() {
  return (
    <section id="about" className="section-container">
      <div className="section-header">
        <div className="section-kicker">💡 About &amp; Impact</div>
        <h2 className="section-title">Bridging Analytics &amp; Full-Stack Engineering</h2>
      </div>

      <div className="about-grid">
        <div className="about-bio-card">
          <h3 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: '16px', color: 'var(--text)' }}>
            Empowering organizations with data-driven precision.
          </h3>
          <p className="about-paragraph">
            I specialize in transforming complex, unstructured datasets into intuitive dashboards, predictive Machine Learning models, and scalable full-stack web applications.
          </p>
          <p className="about-paragraph">
            Whether optimizing reporting infrastructure for executive decision-makers or architecting real-time WebGL interfaces, my work focuses on measurable performance, speed, and reliability.
          </p>
        </div>

        <div className="metrics-grid">
          {STATS.map((stat) => (
            <div key={stat.label} className="metric-card">
              <div className="metric-val">
                {stat.value}
                <span style={{ fontSize: '1.8rem', color: 'var(--cyan)' }}>{stat.suffix}</span>
              </div>
              <div className="metric-label">{stat.label}</div>
              <div className="metric-desc">{stat.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
