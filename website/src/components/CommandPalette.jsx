import { useState, useEffect } from 'react'

export default function CommandPalette({ isOpen, onClose, onSelectSection, onOpenNeuralMap, onToggleSurge }) {
  const [query, setQuery] = useState('')

  const commands = [
    { id: 'hero', label: 'Go to Hero Section', icon: '⚡', category: 'Navigation' },
    { id: 'about', label: 'Go to About & Impact', icon: '💡', category: 'Navigation' },
    { id: 'workflow', label: 'Go to Methodology & Pipeline', icon: '🔄', category: 'Navigation' },
    { id: 'multiverse', label: 'Launch Cosmic Multiverse Studio', icon: '🔮', category: 'Navigation' },
    { id: 'viewfinder', label: 'Go to Signal Telescope Viewfinder', icon: '🔭', category: 'Navigation' },
    { id: 'lab', label: 'Go to Interactive Terminal', icon: '💻', category: 'Navigation' },
    { id: 'services', label: 'Go to Specialized Services', icon: '🛠️', category: 'Navigation' },
    { id: 'projects', label: 'Go to Selected Projects', icon: '📁', category: 'Navigation' },
    { id: 'skills', label: 'Go to Technical Ecosystem', icon: '🧠', category: 'Navigation' },
    { id: 'contact', label: 'Go to Contact Hub', icon: '📬', category: 'Navigation' },
    { id: 'neural-map', label: 'Launch Neural Map Graph Overlay', icon: '🌐', category: 'Tools' },
    { id: 'surge-mode', label: 'Toggle Neural Surge Mode (Konami Boost)', icon: '⚡', category: 'System' },
  ]

  const filtered = commands.filter((c) =>
    c.label.toLowerCase().includes(query.toLowerCase()) ||
    c.id.toLowerCase().includes(query.toLowerCase())
  )

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        if (isOpen) onClose()
        else setQuery('')
      }
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const handleExecute = (cmd) => {
    if (cmd.id === 'neural-map') {
      onOpenNeuralMap()
    } else if (cmd.id === 'surge-mode') {
      onToggleSurge()
    } else {
      onSelectSection(cmd.id)
    }
    onClose()
  }

  return (
    <div className="cmd-palette-overlay" onClick={onClose}>
      <div className="cmd-palette-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="cmd-palette-header">
          <span className="cmd-icon">🔍</span>
          <input
            type="text"
            className="cmd-input"
            placeholder="Type a command or jump to section (e.g. 'multiverse', 'projects')..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
          <span className="cmd-badge">ESC to close</span>
        </div>

        <div className="cmd-palette-list">
          {filtered.length === 0 ? (
            <div className="cmd-empty">No matching signal commands found.</div>
          ) : (
            filtered.map((cmd) => (
              <div
                key={cmd.id}
                className="cmd-item"
                onClick={() => handleExecute(cmd)}
              >
                <span className="cmd-item-icon">{cmd.icon}</span>
                <span className="cmd-item-label">{cmd.label}</span>
                <span className="cmd-item-cat">{cmd.category}</span>
              </div>
            ))
          )}
        </div>

        <div className="cmd-palette-footer">
          <span>Pro tip: Press <kbd>⌘K</kbd> or <kbd>Ctrl+K</kbd> anytime to open Command Palette</span>
        </div>
      </div>
    </div>
  )
}
