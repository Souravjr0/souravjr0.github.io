import { useState, useRef, useEffect } from 'react'
import { TERMINAL_COMMANDS } from '../data/portfolio'

export default function InteractiveTerminal() {
  const [input, setInput] = useState('')
  const [history, setHistory] = useState([
    {
      command: 'help',
      output: TERMINAL_COMMANDS.help,
    },
  ])
  const terminalEndRef = useRef(null)

  const handleCommand = (cmd) => {
    const cleanCmd = cmd.trim().toLowerCase()
    if (!cleanCmd) return

    if (cleanCmd === 'clear') {
      setHistory([])
      setInput('')
      return
    }

    const output = TERMINAL_COMMANDS[cleanCmd] || `Command not found: '${cleanCmd}'. Type 'help' for available commands.`
    setHistory((prev) => [...prev, { command: cleanCmd, output }])
    setInput('')
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    handleCommand(input)
  }

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history])

  return (
    <section id="lab" className="section-container">
      <div className="section-header" style={{ textAlign: 'center' }}>
        <div className="section-kicker">⚡ Interactive Developer Lab</div>
        <h2 className="section-title">Live Terminal &amp; Pipeline Playground</h2>
        <p className="section-subtitle" style={{ margin: '12px auto 0' }}>
          Test real-time commands, inspect skill blueprints, or simulate predictive ML inference directly in the browser terminal.
        </p>
      </div>

      <div className="terminal-window">
        <div className="terminal-header">
          <div className="terminal-dots">
            <span className="dot dot-red" />
            <span className="dot dot-yellow" />
            <span className="dot dot-green" />
          </div>
          <div className="terminal-title">sourav@dev-box:~ (zsh)</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--emerald)', fontFamily: 'var(--mono)' }}>● ONLINE</div>
        </div>

        <div className="terminal-chips">
          {Object.keys(TERMINAL_COMMANDS).map((cmd) => (
            <button
              key={cmd}
              className="terminal-chip"
              onClick={() => handleCommand(cmd)}
            >
              $ {cmd}
            </button>
          ))}
          <button className="terminal-chip" onClick={() => handleCommand('clear')} style={{ color: '#ef4444' }}>
            $ clear
          </button>
        </div>

        <div className="terminal-body">
          {history.map((item, idx) => (
            <div key={idx} style={{ marginBottom: '16px' }}>
              <div className="terminal-input-row" style={{ marginBottom: '6px' }}>
                <span className="terminal-prompt">sourav@portfolio:~$</span>
                <span style={{ color: 'var(--text)', fontWeight: 600 }}>{item.command}</span>
              </div>
              <div className="terminal-output">{item.output}</div>
            </div>
          ))}

          <form onSubmit={handleSubmit} className="terminal-input-row">
            <span className="terminal-prompt">sourav@portfolio:~$</span>
            <input
              type="text"
              className="terminal-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type command ('help', 'run-ml-demo', 'skills')..."
              autoComplete="off"
            />
          </form>
          <div ref={terminalEndRef} />
        </div>
      </div>
    </section>
  )
}
