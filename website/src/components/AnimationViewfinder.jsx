import { useEffect, useRef, useState } from 'react'
import { animate, stagger } from 'animejs'

export default function AnimationViewfinder() {
  const [activePreset, setActivePreset] = useState('grid-ripple')
  const [zoomLevel, setZoomLevel] = useState(1)
  const [isPlaying, setIsPlaying] = useState(true)
  const [speed, setSpeed] = useState(1)
  const [showCode, setShowCode] = useState(false)
  const canvasContainerRef = useRef(null)

  const presets = [
    { id: 'grid-ripple', label: 'Grid Ripple Stagger', icon: '🌐' },
    { id: 'shape-morph', label: 'SVG Geometric Morph', icon: '💎' },
    { id: 'kinetic-burst', label: 'Kinetic Particle Burst', icon: '💥' },
    { id: 'vortex-orbit', label: 'Vortex Orbit Ring', icon: '🌀' },
    { id: 'spring-path', label: 'Spring Motion Path', icon: '⚡' },
  ]

  const codeSnippets = {
    'grid-ripple': `// Anime.js v4 Grid Matrix Ripple
animate('.grid-node', {
  scale: [1, 2.2, 1],
  opacity: [0.4, 1, 0.4],
  backgroundColor: ['#ff2a5f', '#00f0ff', '#ffd166'],
  delay: stagger(45, { from: 'center', grid: [8, 8] }),
  duration: 1200 / speed,
  ease: 'inOutSine',
  loop: true
});`,
    'shape-morph': `// Anime.js v4 SVG Path Morphing & Dash Offset
animate('.morph-path', {
  strokeDashoffset: [1000, 0],
  stroke: ['#ff2a5f', '#00f0ff', '#ffd166'],
  duration: 1600 / speed,
  ease: 'inOutExpo',
  loop: true
});`,
    'kinetic-burst': `// Anime.js v4 Kinetic Particle Burst & Spring Physics
animate('.burst-particle', {
  translateX: () => (Math.random() - 0.5) * 240,
  translateY: () => (Math.random() - 0.5) * 240,
  scale: [0, 1.5, 0],
  rotateZ: () => Math.random() * 360,
  delay: stagger(20),
  duration: 1000 / speed,
  ease: 'outElastic(1, .5)'
});`,
    'vortex-orbit': `// Anime.js v4 Orbital Vortex Rotation
animate('.vortex-ring', {
  rotateZ: [0, 360],
  scale: [0.8, 1.2, 0.8],
  duration: 3000 / speed,
  ease: 'linear',
  loop: true
});`,
    'spring-path': `// Anime.js v4 Spring Motion Path Trajectory
animate('.spring-tracer', {
  translateX: [0, 150, -150, 0],
  translateY: [-80, 80, -80, 0],
  duration: 2000 / speed,
  ease: 'outBounce',
  loop: true
});`,
  }

  // Preset 1: Grid Ripple Animation
  const triggerGridRipple = () => {
    animate('.viewfinder-grid-dot', {
      scale: [1, 2.2, 1],
      opacity: [0.3, 1, 0.3],
      delay: stagger(40, { from: 'center', grid: [8, 8] }),
      duration: 1200 / speed,
      ease: 'inOutSine',
    })
  }

  // Trigger preset animation on change or play
  useEffect(() => {
    if (!isPlaying) return

    if (activePreset === 'grid-ripple') {
      triggerGridRipple()
    } else if (activePreset === 'shape-morph') {
      const paths = canvasContainerRef.current?.querySelectorAll('path')
      if (paths) {
        paths.forEach((p, idx) => {
          const len = p.getTotalLength ? p.getTotalLength() : 300
          p.style.strokeDasharray = len
          p.style.strokeDashoffset = len
          animate(p, {
            strokeDashoffset: [len, 0],
            duration: 1600 / speed,
            delay: idx * 250,
            ease: 'inOutExpo',
          })
        })
      }
    } else if (activePreset === 'kinetic-burst') {
      animate('.burst-item', {
        translateX: () => (Math.random() - 0.5) * 220,
        translateY: () => (Math.random() - 0.5) * 220,
        scale: [0.2, 1.4, 0.8],
        rotateZ: () => Math.random() * 360,
        delay: stagger(25),
        duration: 1100 / speed,
        ease: 'outElastic(1, .5)',
      })
    } else if (activePreset === 'vortex-orbit') {
      animate('.vortex-orbit-ring', {
        rotateZ: [0, 360],
        duration: 4000 / speed,
        ease: 'linear',
      })
    } else if (activePreset === 'spring-path') {
      animate('.spring-node', {
        translateY: [-60, 60, -60],
        translateX: [-80, 80, -80],
        scale: [0.8, 1.5, 0.8],
        delay: stagger(100),
        duration: 2000 / speed,
        ease: 'outElastic(1, .6)',
      })
    }
  }, [activePreset, isPlaying, speed])

  return (
    <section id="viewfinder" className="section-container">
      <div className="section-header" style={{ textAlign: 'center' }}>
        <div className="section-kicker">🔭 Signal Telescope &amp; Viewfinder</div>
        <h2 className="section-title">Interactive Motion Telephoto Inspector</h2>
        <p className="section-subtitle" style={{ margin: '12px auto 0' }}>
          Inspect live Anime.js v4 motion presets, adjust lens zoom levels, and examine real-time animation parameters.
        </p>
      </div>

      <div className="viewfinder-frame">
        {/* Telescope Viewfinder Header & HUD Controls */}
        <div className="viewfinder-hud-bar">
          <div className="hud-left">
            <span className="hud-status-dot" />
            <span className="hud-text">TELESCOPE: ACTIVE // LENS: {zoomLevel}x FOCAL</span>
          </div>

          <div className="hud-center-presets">
            {presets.map((p) => (
              <button
                key={p.id}
                className={`hud-preset-btn ${activePreset === p.id ? 'active' : ''}`}
                onClick={() => setActivePreset(p.id)}
              >
                <span>{p.icon}</span>
                <span className="preset-name">{p.label}</span>
              </button>
            ))}
          </div>

          <div className="hud-right-zoom">
            <span className="zoom-label">ZOOM:</span>
            {[1, 1.5, 2.5].map((z) => (
              <button
                key={z}
                className={`zoom-btn ${zoomLevel === z ? 'active' : ''}`}
                onClick={() => setZoomLevel(z)}
              >
                {z}x
              </button>
            ))}
          </div>
        </div>

        {/* Viewfinder Canvas & Lens Reticle Overlay */}
        <div
          ref={canvasContainerRef}
          className="viewfinder-viewport"
          style={{ transform: `scale(${zoomLevel})`, transition: 'transform 0.4s ease-out' }}
          onClick={() => {
            if (activePreset === 'grid-ripple') triggerGridRipple()
          }}
        >
          {/* Animated SVG Reticle Crosshair */}
          <svg className="viewfinder-reticle-svg" viewBox="0 0 400 400">
            <circle cx="200" cy="200" r="180" fill="none" stroke="var(--coral)" strokeWidth="1" strokeOpacity="0.25" />
            <circle cx="200" cy="200" r="140" fill="none" stroke="var(--cyan)" strokeWidth="1" strokeDasharray="6 6" strokeOpacity="0.3" />
            <line x1="200" y1="20" x2="200" y2="380" stroke="var(--coral)" strokeWidth="1" strokeOpacity="0.2" />
            <line x1="20" y1="200" x2="380" y2="200" stroke="var(--coral)" strokeWidth="1" strokeOpacity="0.2" />
            <circle cx="200" cy="200" r="6" fill="var(--coral)" />
          </svg>

          {/* Preset 1: Grid Ripple */}
          {activePreset === 'grid-ripple' && (
            <div className="viewfinder-grid-matrix">
              {Array.from({ length: 64 }).map((_, i) => (
                <div key={i} className="viewfinder-grid-dot" />
              ))}
            </div>
          )}

          {/* Preset 2: Shape Morph */}
          {activePreset === 'shape-morph' && (
            <div className="viewfinder-svg-stage">
              <svg width="220" height="220" viewBox="0 0 100 100">
                <path d="M 50,10 L 90,30 L 90,70 L 50,90 L 10,70 L 10,30 Z" fill="none" stroke="#ff2a5f" strokeWidth="2.5" />
                <path d="M 50,20 L 80,35 L 80,65 L 50,80 L 20,65 L 20,35 Z" fill="none" stroke="#00f0ff" strokeWidth="2" />
                <path d="M 50,30 L 70,40 L 70,60 L 50,70 L 30,60 L 30,40 Z" fill="none" stroke="#ffd166" strokeWidth="2" />
              </svg>
            </div>
          )}

          {/* Preset 3: Kinetic Burst */}
          {activePreset === 'kinetic-burst' && (
            <div className="viewfinder-burst-stage">
              {['S', 'O', 'U', 'R', 'A', 'V', '⚡', 'AI', 'ML', '3D'].map((char, i) => (
                <div key={i} className="burst-item">
                  {char}
                </div>
              ))}
            </div>
          )}

          {/* Preset 4: Vortex Orbit */}
          {activePreset === 'vortex-orbit' && (
            <div className="viewfinder-vortex-stage">
              <div className="vortex-orbit-ring ring-1" />
              <div className="vortex-orbit-ring ring-2" />
              <div className="vortex-orbit-ring ring-3" />
            </div>
          )}

          {/* Preset 5: Spring Motion Path */}
          {activePreset === 'spring-path' && (
            <div className="viewfinder-spring-stage">
              {[1, 2, 3, 4, 5].map((n) => (
                <div key={n} className="spring-node">
                  ✦
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Viewfinder Deck & Code Inspector Toggle */}
        <div className="viewfinder-deck-bar">
          <div className="deck-controls">
            <button className="btn btn-outline" onClick={() => setIsPlaying(!isPlaying)}>
              {isPlaying ? 'Pause ⏸' : 'Play ▶'}
            </button>
            <button className="btn btn-outline" onClick={() => triggerGridRipple()}>
              Replay ↺
            </button>
            <div className="speed-selector">
              <span>SPEED:</span>
              {[0.5, 1, 2].map((s) => (
                <button
                  key={s}
                  className={`speed-btn ${speed === s ? 'active' : ''}`}
                  onClick={() => setSpeed(s)}
                >
                  {s}x
                </button>
              ))}
            </div>
          </div>

          <button
            className="btn btn-primary"
            onClick={() => setShowCode(!showCode)}
            style={{ fontSize: '0.85rem' }}
          >
            {showCode ? 'Hide Code' : 'Inspect Code 💻'}
          </button>
        </div>

        {/* Live Code Snippet & Parameter Inspector */}
        {showCode && (
          <div className="viewfinder-code-drawer">
            <div className="code-drawer-header">
              <span>ANIMATION PARAMETERS // ANIME.JS V4</span>
              <span style={{ color: 'var(--cyan)' }}>EASING: {activePreset === 'kinetic-burst' ? 'outElastic' : 'inOutExpo'}</span>
            </div>
            <pre className="code-snippet-box">
              <code>{codeSnippets[activePreset]}</code>
            </pre>
          </div>
        )}
      </div>
    </section>
  )
}
