import { SKILL_CATEGORIES } from '../data/portfolio'

export default function Skills() {
  return (
    <section id="skills" className="section-container">
      <div className="section-header">
        <div className="section-kicker">🧠 Technical Ecosystem</div>
        <h2 className="section-title">Tools, Frameworks &amp; Languages</h2>
        <p className="section-subtitle">
          Core technical competencies across Data Engineering, Machine Learning, and Web Technologies.
        </p>
      </div>

      <div className="skills-grid">
        {SKILL_CATEGORIES.map((cat) => (
          <div key={cat.id} className="skill-category-card">
            <div className="skill-kicker">{cat.kicker}</div>
            <h3 className="skill-cat-title">{cat.title}</h3>

            <div className="skill-list">
              {cat.skills.map((sk) => (
                <div key={sk.name} className="skill-item">
                  <div className="skill-item-header">
                    <span className="skill-name">{sk.name}</span>
                    <span className="skill-level-badge">{sk.label} ({sk.level}%)</span>
                  </div>
                  <div className="skill-progress-bar">
                    <div className="skill-progress-fill" style={{ width: `${sk.level}%` }} />
                  </div>
                </div>
              ))}
            </div>

            <div className="skill-chips">
              {cat.chips.map((chip) => (
                <span key={chip} className="skill-chip">
                  {chip}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
