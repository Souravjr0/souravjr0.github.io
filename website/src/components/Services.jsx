import { SERVICES } from '../data/portfolio'

export default function Services() {
  return (
    <section id="services" className="section-container">
      <div className="section-header">
        <div className="section-kicker">🛠️ Specialized Services</div>
        <h2 className="section-title">Core Capabilities &amp; Solutions</h2>
        <p className="section-subtitle">
          Tailored analytics pipelines, AI model deployments, and web interfaces crafted to solve real-world problems.
        </p>
      </div>

      <div className="services-grid">
        {SERVICES.map((s) => (
          <div key={s.id} className="service-card" style={{ background: s.gradient }}>
            <div className="service-num">{s.id} // CAPABILITY</div>
            <h3 className="service-title">{s.title}</h3>
            <p className="service-desc">{s.description}</p>
            <ul className="service-checklist">
              {s.checklist.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <div className="service-tags">
              {s.tags.map((t) => (
                <span key={t} className="pipeline-tag" style={{ color: s.accentColor, borderColor: 'var(--border)' }}>
                  {t}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
