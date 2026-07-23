export default function NeuralMapModal({ isOpen, onClose, onSelectSection }) {
  if (!isOpen) return null

  const nodes = [
    { id: 'hero', label: 'HERO // SIGNAL INGESTION', x: 50, y: 15, icon: '⚡' },
    { id: 'about', label: 'ABOUT // IMPACT METRICS', x: 25, y: 35, icon: '💡' },
    { id: 'workflow', label: 'WORKFLOW // PIPELINE ARCH', x: 75, y: 35, icon: '🔄' },
    { id: 'lab', label: 'LAB // INTERACTIVE TERMINAL', x: 35, y: 60, icon: '💻' },
    { id: 'services', label: 'SERVICES // SOLUTIONS', x: 65, y: 60, icon: '🛠️' },
    { id: 'projects', label: 'WORK // ORBITING INTEL', x: 20, y: 82, icon: '📁' },
    { id: 'skills', label: 'STACK // TECH ECOSYSTEM', x: 80, y: 82, icon: '🧠' },
    { id: 'contact', label: 'CONTACT // TRANSMISSION', x: 50, y: 92, icon: '📬' },
  ]

  const links = [
    { from: 'hero', to: 'about' },
    { from: 'hero', to: 'workflow' },
    { from: 'about', to: 'lab' },
    { from: 'workflow', to: 'services' },
    { from: 'lab', to: 'projects' },
    { from: 'services', to: 'skills' },
    { from: 'projects', to: 'contact' },
    { from: 'skills', to: 'contact' },
  ]

  return (
    <div className="neural-modal-overlay" onClick={onClose}>
      <div className="neural-modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="neural-modal-header">
          <div>
            <h3 style={{ fontFamily: 'var(--heading)', fontSize: '1.4rem', color: 'var(--text)' }}>
              🌐 System Neural Topology Map
            </h3>
            <div style={{ fontFamily: 'var(--mono)', fontSize: '0.8rem', color: 'var(--coral)' }}>
              CLICK ANY NODE TO ROUTE DIRECT SIGNAL
            </div>
          </div>
          <button className="btn btn-outline" onClick={onClose} style={{ padding: '6px 14px', fontSize: '0.8rem' }}>
            Close [✕]
          </button>
        </div>

        <div className="neural-graph-canvas">
          <svg className="neural-svg-links" width="100%" height="100%">
            {links.map((link, idx) => {
              const n1 = nodes.find((n) => n.id === link.from)
              const n2 = nodes.find((n) => n.id === link.to)
              if (!n1 || !n2) return null
              return (
                <line
                  key={idx}
                  x1={`${n1.x}%`}
                  y1={`${n1.y}%`}
                  x2={`${n2.x}%`}
                  y2={`${n2.y}%`}
                  stroke="var(--coral)"
                  strokeOpacity="0.3"
                  strokeWidth="2"
                  strokeDasharray="4 4"
                />
              )
            })}
          </svg>

          {nodes.map((node) => (
            <div
              key={node.id}
              className="neural-node-pin"
              style={{ left: `${node.x}%`, top: `${node.y}%` }}
              onClick={() => {
                onSelectSection(node.id)
                onClose()
              }}
            >
              <div className="neural-node-dot">
                <span>{node.icon}</span>
              </div>
              <div className="neural-node-label">{node.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
