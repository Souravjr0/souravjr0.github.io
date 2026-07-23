export default function Marquee() {
  const items = [
    'PYTHON DATA PIPELINES',
    'MACHINE LEARNING MODELS',
    '3D WEBGL VISUALS',
    'FASTAPI & BACKEND',
    'REACT & ANIME.JS',
    'TABLEAU BI DASHBOARDS',
    'DOCKER & MLOPS',
  ]

  return (
    <div className="marquee-container">
      <div className="marquee-content">
        {[...items, ...items, ...items].map((item, idx) => (
          <div key={idx} className="marquee-item">
            <span className="highlight">✦</span>
            <span>{item}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
