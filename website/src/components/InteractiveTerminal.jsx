import { useState, useRef, useEffect } from 'react'
import { TERMINAL_COMMANDS } from '../data/portfolio'

export default function InteractiveTerminal({ onOpenNeuralMap }) {
  const [input, setInput] = useState('')
  const [history, setHistory] = useState([
    {
      command: 'help',
      output: TERMINAL_COMMANDS.help,
    },
  ])
  const [cmdHistoryIndex, setCmdHistoryIndex] = useState(-1)
  const [isDemoRunning, setIsDemoRunning] = useState(false)
  const terminalEndRef = useRef(null)

  const handleCommand = (cmd) => {
    const cleanCmd = cmd.trim().toLowerCase()
    if (!cleanCmd) return

    if (cleanCmd === 'clear') {
      setHistory([])
      setInput('')
      return
    }

    if (cleanCmd === 'neural-map') {
      onOpenNeuralMap()
      setHistory((prev) => [
        ...prev,
        { command: cleanCmd, output: '[SYSTEM] Launching System Neural Topology Map overlay...' },
      ])
      setInput('')
      return
    }

    if (cleanCmd === 'run-ml-demo') {
      setIsDemoRunning(true)
      setHistory((prev) => [
        ...prev,
        {
          command: cleanCmd,
          output: `[INIT] Loading Neural Checkpoint 'v4.2.0_prod.pkl'...
[DATA] Ingesting 10,000 real-time feature vectors...
[TRANSFORM] PCA dimensionality reduction: 128D -> 12D
[INFERENCE] Running PyTorch CUDA pipeline...
[ACCURACY] Confidence Score: 98.6% || Loss: 0.014
[OUTPUT] Status: OPTIMIZED || Category: CLUSTER_A_PRIME
[SUCCESS] Inference completed in 42ms! ✨`,
        },
      ])
      setInput('')
      setTimeout(() => setIsDemoRunning(false), 2000)
      return
    }

    const output = TERMINAL_COMMANDS[cleanCmd] || `Command not found: '${cleanCmd}'. Type 'help' for available commands or 'neural-map' to open graph.`
    setHistory((prev) => [...prev, { command: cleanCmd, output }])
    setInput('')
    setCmdHistoryIndex(-1)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (history.length > 0) {
        const nextIdx = cmdHistoryIndex < history.length - 1 ? cmdHistoryIndex + 1 : cmdHistoryIndex
        setCmdHistoryIndex(nextIdx)
        setInput(history[history.length - 1 - nextIdx].command)
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (cmdHistoryIndex > 0) {
        const nextIdx = cmdHistoryIndex - 1
        setCmdHistoryIndex(nextIdx)
        setInput(history[history.length - 1 - nextIdx].command)
      } else if (cmdHistoryIndex === 0) {
        setCmdHistoryIndex(-1)
        setInput('')
      }
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    handleCommand(input)
  }

  useEffect(() => {
    // Scroll only the terminal's own container to its bottom — NOT
    // scrollIntoView, which also scrolls the window and yanks the whole
    // page down to the terminal on initial load.
    const body = terminalEndRef.current?.parentElement
    if (body) body.scrollTop = body.scrollHeight
  }, [history, isDemoRunning])

  return (
    <section id="lab" className="section-container">
      <div className="section-header" style={{ textAlign: 'center' }}>
        <div className="section-kicker">⚡ Interactive Developer Lab</div>
        <h2 className="section-title">Live Terminal &amp; Pipeline Command Center</h2>
        <p className="section-subtitle" style={{ margin: '12px auto 0' }}>
          Execute commands, test ML inference, or trigger the <strong>neural-map</strong> graph modal.
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
          <div style={{ fontSize: '0.8rem', color: 'var(--coral)', fontFamily: 'var(--mono)' }}>
            ● {isDemoRunning ? 'RUNNING INFERENCE' : 'ONLINE'}
          </div>
        </div>

        <div className="terminal-chips">
          {['help', 'about', 'skills', 'projects', 'run-ml-demo', 'neural-map', 'contact'].map((cmd) => (
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

          {isDemoRunning && (
            <div className="ml-demo-chart">
              <div className="chart-bar" style={{ width: '85%' }}>CONFIDENCE: 98.6%</div>
              <div className="chart-bar" style={{ width: '92%', background: 'var(--cyan)' }}>LATENCY: 42ms</div>
              <div className="chart-bar" style={{ width: '99%', background: 'var(--gold)' }}>MODEL ACCURACY: 99.2%</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="terminal-input-row">
            <span className="terminal-prompt">sourav@portfolio:~$</span>
            <input
              type="text"
              className="terminal-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type command ('help', 'run-ml-demo', 'neural-map', ↑/↓ history)..."
              autoComplete="off"
            />
          </form>
          <div ref={terminalEndRef} />
        </div>
      </div>
    </section>
  )
}
