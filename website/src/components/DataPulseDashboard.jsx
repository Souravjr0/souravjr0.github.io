import { useEffect, useRef, useState } from 'react'
import { animate, stagger } from 'animejs'
import { EASE, DUR } from '../motion'
import { DATA_PULSE_METRICS, DATA_PULSE_CHARTS, DATA_STATUS_CYCLES } from '../data/dataPulse'

/* ── Animated donut chart ── */
function DonutChart({ pct, label, color }) {
  const r = 32
  const circ = 2 * Math.PI * r
  const done = (pct / 100) * circ

  return (
    <svg width="80" height="80" viewBox="0 0 80 80" className="data-donut-svg">
      <circle cx="40" cy="40" r={r} fill="none" stroke="var(--bg-3)" strokeWidth="6" />
      <circle
        cx="40" cy="40" r={r}
        fill="none"
        stroke={color}
        strokeWidth="6"
        strokeDasharray={circ}
        strokeDashoffset={circ}
        strokeLinecap="round"
        transform="rotate(-90 40 40)"
        className="data-donut-fill"
        data-target={done}
      />
      <text x="40" y="40" textAnchor="middle" dominantBaseline="central" fill="var(--text)" fontSize="18" fontWeight="700" fontFamily="var(--heading)">
        {pct}
      </text>
      <text x="40" y="56" textAnchor="middle" dominantBaseline="central" fill="var(--text-dim)" fontSize="8" fontFamily="var(--mono)">
        {label}
      </text>
    </svg>
  )
}

/* ── Metric card with anime.js counter ── */
function PulseMetricCard({ metric, index }) {
  const cardRef = useRef(null)
  const numRef = useRef(null)
  const pulseRef = useRef(null)

  useEffect(() => {
    const el = cardRef.current
    if (!el) return
    const io = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return

      // Counter animation
      if (numRef.current) {
        const counter = { val: 0 }
        animate(counter, {
          val: metric.value,
          round: 1,
          duration: DUR.slow + 300,
          ease: EASE.out,
          onUpdate: () => {
            if (numRef.current) numRef.current.textContent = Math.round(counter.val)
          },
        })
      }

      // Card entrance
      animate(el, {
        opacity: [0, 1],
        translateY: [30, 0],
        duration: DUR.base,
        delay: index * 120,
        ease: EASE.out,
      })

      // Pulse ring on the dot
      if (pulseRef.current) {
        animate(pulseRef.current, {
          scale: [1, 2.5, 1],
          opacity: [0.6, 0, 0.6],
          duration: 2000,
          loop: true,
          ease: 'inOutSine',
        })
      }

      io.unobserve(el)
    }, { threshold: 0.2 })
    io.observe(el)
    return () => io.disconnect()
  }, [metric.value, index])

  return (
    <div ref={cardRef} className="pulse-metric-card">
      <div className="pulse-metric-header">
        <div className="pulse-status-dot-wrap">
          <span className="pulse-dot-ring" ref={pulseRef} />
          <span className="pulse-dot-core" style={{ background: metric.color }} />
        </div>
        <span className="pulse-metric-label">{metric.label}</span>
      </div>
      <div className="pulse-metric-value">
        <span ref={numRef} className="pulse-metric-num">0</span>
        <span className="pulse-metric-suffix">{metric.suffix}</span>
      </div>
      <div className="pulse-metric-sub">{metric.sub}</div>
      <div className="pulse-metric-status" style={{ color: metric.color }}>{metric.status}</div>
    </div>
  )
}

/* ── Animated bar chart (anime.js width) ── */
function BarChart() {
  const containerRef = useRef(null)
  const barsRef = useRef([])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const io = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return

      animate(barsRef.current, {
        width: (el) => `${el.dataset.target}%`,
        duration: DUR.slow,
        delay: stagger(80),
        ease: EASE.out,
      })

      io.unobserve(el)
    }, { threshold: 0.2 })
    io.observe(el)
    return () => io.disconnect()
  }, [])

  return (
    <div ref={containerRef} className="data-bar-chart">
      <div className="chart-title-group">
        <span className="chart-title-icon">📊</span>
        <div>
          <div className="chart-title">Technical Proficiency</div>
          <div className="chart-subtitle">Self-assessed vs peer-reviewed baselines</div>
        </div>
      </div>
      <div className="bar-chart-grid">
        {DATA_PULSE_CHARTS.bars.map((b, i) => (
          <div key={b.label} className="bar-row">
            <span className="bar-label">{b.label}</span>
            <div className="bar-track">
              <div
                ref={(el) => (barsRef.current[i] = el)}
                className="bar-fill"
                style={{
                  width: '0%',
                  background: `linear-gradient(90deg, ${b.color}, ${b.color}88)`,
                  boxShadow: `0 0 12px ${b.color}44`,
                }}
                data-target={b.pct}
              />
            </div>
            <span className="bar-pct">{b.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── SVG line chart drawn on scroll (GSAP) ── */
function LineChart() {
  const pathRef = useRef(null)
  const containerRef = useRef(null)
  const [progress, setProgress] = useState(0)

  const points = DATA_PULSE_CHARTS.line
  const maxX = 200
  const maxY = 100
  const svgW = 400
  const svgH = 200

  const d = points
    .map((p, i) => {
      const x = (p.x / maxX) * svgW
      const y = svgH - (p.y / maxY) * svgH
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`
    })
    .join(' ')

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const io = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return
        const scrollPct = Math.min(1, Math.max(0, (1 - entry.boundingClientRect.top / window.innerHeight) * 2))

        if (pathRef.current) {
          const len = pathRef.current.getTotalLength()
          animate(pathRef.current, {
            strokeDashoffset: [len, 0],
            duration: DUR.slow + 400,
            ease: EASE.out,
          })
        }

        // Animate progress label
        animate('.line-chart-progress-val', {
          innerText: [0, 92],
          round: 1,
          duration: DUR.slow + 400,
          ease: EASE.out,
        })

        io.unobserve(el)
      },
      { threshold: 0.1 }
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])

  return (
    <div ref={containerRef} className="data-line-chart">
      <div className="chart-title-group">
        <span className="chart-title-icon">📈</span>
        <div>
          <div className="chart-title">Model Accuracy Over Time</div>
          <div className="chart-subtitle">Production validation across 10 checkpoints</div>
        </div>
      </div>
      <div className="line-chart-viewport">
        <svg viewBox="0 0 400 200" className="line-chart-svg">
          {/* Grid lines */}
          {[0, 25, 50, 75, 100].map((v) => {
            const y = svgH - (v / maxY) * svgH
            return (
              <line key={v} x1="0" y1={y} x2={svgW} y2={y} stroke="var(--bg-3)" strokeWidth="1" strokeDasharray="4 4" />
            )
          })}
          {/* Fill area */}
          <path
            d={`${d} L ${svgW} ${svgH} L 0 ${svgH} Z`}
            fill="url(#lineGrad)"
            opacity="0.15"
          />
          {/* Main line */}
          <path
            ref={pathRef}
            d={d}
            fill="none"
            stroke="var(--coral)"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="line-chart-path"
            style={{ strokeDasharray: 10000, strokeDashoffset: 10000 }}
          />
          {/* Data dots */}
          {points.map((p, i) => {
            const x = (p.x / maxX) * svgW
            const y = svgH - (p.y / maxY) * svgH
            return (
              <circle
                key={i}
                cx={x}
                cy={y}
                r={0}
                fill="var(--bg)"
                stroke="var(--coral)"
                strokeWidth="2.5"
                className={`line-chart-dot dot-${i}`}
              />
            )
          })}
          <defs>
            <linearGradient id="lineGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="var(--coral)" stopOpacity="0.3" />
              <stop offset="100%" stopColor="var(--coral)" stopOpacity="0" />
            </linearGradient>
          </defs>
        </svg>
        <div className="line-chart-current">
          <span className="line-chart-progress-label">CURRENT ACCURACY</span>
          <span className="line-chart-progress-val">0</span>
          <span style={{ color: 'var(--coral)', fontSize: '1.2rem' }}>%</span>
        </div>
      </div>
    </div>
  )
}

/* ── Stream particle effect (CSS animated dots) ── */
function DataStreamParticles() {
  return (
    <div className="data-stream-particles" aria-hidden="true">
      {Array.from({ length: 16 }).map((_, i) => (
        <div
          key={i}
          className="stream-particle"
          style={{
            left: `${(i / 16) * 100}%`,
            animationDelay: `${i * 0.3}s`,
          }}
        />
      ))}
    </div>
  )
}

/* ── Status ticker that cycles through messages ── */
function StatusTicker() {
  const [msg, setMsg] = useState(DATA_STATUS_CYCLES[0])
  const idxRef = useRef(0)

  useEffect(() => {
    const interval = setInterval(() => {
      idxRef.current = (idxRef.current + 1) % DATA_STATUS_CYCLES.length
      setMsg(DATA_STATUS_CYCLES[idxRef.current])
    }, 4000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="pulse-ticker">
      <span className="ticker-dot" />
      <span className="ticker-text">{msg}</span>
    </div>
  )
}

/* ── Donut chart row (3 proficiency donuts) ── */
function DonutRow() {
  const donuts = [
    { pct: 94, label: 'PYTHON', color: 'var(--coral)' },
    { pct: 92, label: 'SQL', color: 'var(--cyan)' },
    { pct: 90, label: 'ML/AI', color: 'var(--gold)' },
  ]
  const containerRef = useRef(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const io = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return
      const svgs = el.querySelectorAll('.data-donut-fill')
      animate(svgs, {
        strokeDashoffset: (el) => {
          const total = 2 * Math.PI * 32
          return [total, total - parseFloat(el.dataset.target)]
        },
        duration: DUR.slow,
        delay: stagger(150),
        ease: EASE.out,
      })
      animate(el.querySelectorAll('.line-chart-dot'), {
        r: [0, 4.5],
        duration: 400,
        delay: stagger(100),
        ease: 'outExpo',
      })
      io.unobserve(el)
    }, { threshold: 0.2 })
    io.observe(el)
    return () => io.disconnect()
  }, [])

  return (
    <div ref={containerRef} className="data-donut-row">
      {donuts.map((d) => (
        <DonutChart key={d.label} {...d} />
      ))}
    </div>
  )
}

/* ── Main export ── */
export default function DataPulseDashboard() {
  return (
    <section id="data-pulse" className="section-container">
      {/* Section header */}
      <div className="section-header">
        <div className="section-kicker">📡 Live Data Pulse</div>
        <h2 className="section-title">Real-Time Analytics Command Center</h2>
        <p className="section-subtitle" style={{ margin: '12px auto 0' }}>
          Live metrics from production pipelines, model accuracy telemetry, and streaming data ingestion — rendered at 60fps.
        </p>
      </div>

      {/* Status ticker */}
      <StatusTicker />

      {/* Dashboard grid */}
      <div className="pulse-dashboard-grid">
        {/* Metric cards */}
        <div className="pulse-metrics-row">
          {DATA_PULSE_METRICS.map((metric, i) => (
            <PulseMetricCard key={metric.label} metric={metric} index={i} />
          ))}
        </div>

        {/* Charts row: bar chart left, donuts right */}
        <div className="pulse-charts-row">
          <BarChart />
          <div className="pulse-charts-right">
            <DonutRow />
            <div className="pulse-donut-gloss">
              <div className="chart-title-group">
                <span className="chart-title-icon">⚡</span>
                <div>
                  <div className="chart-title">Signal Quality</div>
                  <div className="chart-subtitle">Tech stack proficiency confidence</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Line chart */}
        <LineChart />
      </div>

      {/* Stream particles along the bottom */}
      <DataStreamParticles />

      {/* HUD overlay stamp */}
      <div className="pulse-hud-stamp">
        <span>DATA OPS // 60FPS RENDER</span>
        <span className="hud-stamp-dot" />
        <span>STREAMING: {new Date().getFullYear()}</span>
      </div>
    </section>
  )
}
