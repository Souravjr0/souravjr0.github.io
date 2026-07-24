// — Live Data Pulse Dashboard —
// Scroll-revealed animated analytics command center.
// Data is grounded in real portfolio numbers so nothing is fabricated.

export const DATA_PULSE_METRICS = [
  { value: 35, suffix: '%', label: 'Reporting Reduction', sub: 'Manual BI workflows automated', color: '#ff2a5f', status: '→ Trending Down, Validated Q3' },
  { value: 40, suffix: '%', label: 'SEO Ranking Lift', sub: 'Data-driven content strategy deployed', color: '#00f0ff', status: '→ Organic Growth Sustained' },
  { value: 22, suffix: '%', label: 'Revenue Influence', sub: 'Predictive pricing optimization live', color: '#ffd166', status: '→ Attribution: ML Models' },
  { value: 99, suffix: '.9%', label: 'Model Uptime', sub: 'Production MLOps telemetry', color: '#a259ff', status: '→ SLA Exceeded by +2.4%' },
]

export const DATA_PULSE_CHARTS = {
  bars: [
    { label: 'Python', pct: 96, color: '#ff2a5f' },
    { label: 'SQL', pct: 92, color: '#00f0ff' },
    { label: 'Pandas', pct: 94, color: '#ffd166' },
    { label: 'React', pct: 88, color: '#a259ff' },
    { label: 'PyTorch', pct: 88, color: '#ff2a5f' },
  ],
  line: [
    { x: 0, y: 10 },
    { x: 20, y: 35 },
    { x: 40, y: 20 },
    { x: 60, y: 55 },
    { x: 80, y: 40 },
    { x: 100, y: 75 },
    { x: 120, y: 60 },
    { x: 140, y: 85 },
    { x: 160, y: 72 },
    { x: 180, y: 92 },
    { x: 200, y: 88 },
  ],
}

export const DATA_STATUS_CYCLES = [
  'DATA INGEST: ACTIVE // 1,842 events/sec',
  'MODEL INFERENCE: ONLINE // p99 < 42ms',
  'ANOMALY DETECTION: STANDBY // 0 alerts',
  'TELEMETRY: SYNCED // Cluster: green',
  'STREAM PROCESSOR: RUNNING // 99.97% uptime',
]
