import { useEffect, useRef, useState } from 'react'
import { animate, stagger } from 'animejs'

export default function CosmicMatrixStudio() {
  const [activeMode, setActiveMode] = useState('fused') // 'fused', 'water', 'solar', 'lava'
  const [gravity, setGravity] = useState(1)
  const [viscosity, setViscosity] = useState(1)
  const [heat, setHeat] = useState(1)
  const [speed, setSpeed] = useState(1)
  const [telemetry, setTelemetry] = useState('MULTIVERSE FUSION // SYSTEM ACTIVE')
  const stageRef = useRef(null)
  const sectionRef = useRef(null)
  const [visible, setVisible] = useState(false)

  // Only run the continuous physics loops while the section is on-screen.
  useEffect(() => {
    const el = sectionRef.current
    if (!el) return
    const io = new IntersectionObserver(
      ([entry]) => setVisible(entry.isIntersecting),
      { threshold: 0.05 }
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])

  const planets = [
    { id: 'mercury', name: 'Mercury', size: 14, distance: 75, speed: 2.2, color: '#ffd166' },
    { id: 'venus', name: 'Venus', size: 20, distance: 110, speed: 1.6, color: '#ff758c' },
    { id: 'earth', name: 'Earth', size: 24, distance: 155, speed: 1.2, color: '#00f0ff' },
    { id: 'mars', name: 'Mars', size: 18, distance: 195, speed: 0.9, color: '#ff2a5f' },
    { id: 'jupiter', name: 'Jupiter', size: 34, distance: 245, speed: 0.6, color: '#a259ff' },
    { id: 'saturn', name: 'Saturn', size: 28, distance: 295, speed: 0.4, color: '#00ff9d' },
  ]

  // Quantum Pulse Shockwave Handler
  const triggerQuantumPulse = () => {
    setTelemetry('QUANTUM SHOCKWAVE FIRED // MULTIVERSE RIPPLE')

    // 1. Water wave shockwave
    const waves = stageRef.current?.querySelectorAll('.fluid-wave-path')
    if (waves) {
      waves.forEach((w) => {
        const len = w.getTotalLength ? w.getTotalLength() : 400
        animate(w, {
          strokeDashoffset: [len, 0],
          strokeWidth: [2, 6, 2],
          duration: 1200 / speed,
          ease: 'inOutExpo',
        })
      })
    }

    // 2. Solar orbits expansion pulse
    animate('.celestial-planet-node', {
      scale: [1, 2.2, 1],
      opacity: [0.5, 1, 0.5],
      delay: stagger(60, { from: 'center' }),
      duration: 1000 / speed,
      ease: 'outElastic(1, .5)',
    })

    // 3. Thermal lava blobs morph surge
    animate('.lava-blob-path', {
      scale: [0.8, 1.4, 1],
      rotateZ: [0, 180, 360],
      duration: 1400 / speed,
      delay: stagger(100),
      ease: 'inOutSine',
    })

    // 4. Quantum particle burst
    animate('.quantum-particle-dot', {
      translateY: () => (Math.random() - 0.5) * 180 * gravity,
      translateX: () => (Math.random() - 0.5) * 180 * gravity,
      scale: [0.3, 1.8, 0.5],
      delay: stagger(30),
      duration: 1100 / speed,
      ease: 'outExpo',
    })

    setTimeout(() => setTelemetry('MULTIVERSE FUSION // SYSTEM ACTIVE'), 2500)
  }

  // Animate planetary orbits continuously (only while visible; revert old
  // instances on re-run so slider drags don't stack infinite loops).
  useEffect(() => {
    if (!visible) return
    const anims = planets.map((p) =>
      animate(`.planet-${p.id}`, {
        rotateZ: [0, 360],
        duration: (10000 / p.speed) / (speed * gravity),
        ease: 'linear',
        loop: true,
      })
    )
    return () => anims.forEach((a) => a.revert())
  }, [speed, gravity, visible])

  // Animate organic lava metablobs morphing continuously
  useEffect(() => {
    const blobPaths = [
      'M 50,15 Q 85,25 75,65 Q 55,95 25,75 Q 10,40 50,15 Z',
      'M 45,20 Q 90,40 65,80 Q 30,90 15,55 Q 25,15 45,20 Z',
      'M 55,10 Q 75,45 85,75 Q 40,85 20,60 Q 15,30 55,10 Z',
    ]

    if (!visible) return
    const blobs = stageRef.current?.querySelectorAll('.lava-blob-path')
    if (!blobs) return
    const anims = []
    blobs.forEach((b, idx) => {
      anims.push(
        animate(b, {
          d: [
            { value: blobPaths[0] },
            { value: blobPaths[1] },
            { value: blobPaths[2] },
            { value: blobPaths[0] },
          ],
          duration: (6000 / heat) / speed,
          delay: idx * 800,
          ease: 'inOutSine',
          loop: true,
        })
      )
    })
    return () => anims.forEach((a) => a.revert())
  }, [heat, speed, visible])

  return (
    <section id="multiverse" ref={sectionRef} className="section-container">
      <div className="section-header" style={{ textAlign: 'center' }}>
        <div className="section-kicker">🔮 Multiverse Physics Engine</div>
        <h2 className="section-title">Cosmic Neural Matrix &amp; Fusion Studio</h2>
        <p className="section-subtitle" style={{ margin: '12px auto 0' }}>
          A unified physics playground fusing <strong>Fluid Water Flow</strong>, <strong>Solar Gravity Orbits</strong>, <strong>Thermal Lava Morphing</strong>, and <strong>Quantum Kinetic Particles</strong>.
        </p>
      </div>

      <div className="multiverse-studio-box">
        {/* Top Telemetry & Mode Selector */}
        <div className="multiverse-hud-header">
          <div className="hud-telemetry-badge">
            <span className="hud-pulse-node" />
            <span>{telemetry}</span>
          </div>

          <div className="hud-mode-selector">
            {[
              { id: 'fused', label: '⚡ FUSED MULTIVERSE' },
              { id: 'water', label: '🌊 FLUID OCEAN' },
              { id: 'solar', label: '🪐 CELESTIAL ORBITS' },
              { id: 'lava', label: '🌋 THERMAL LAVA' },
            ].map((m) => (
              <button
                key={m.id}
                className={`mode-btn ${activeMode === m.id ? 'active' : ''}`}
                onClick={() => setActiveMode(m.id)}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>

        {/* Fused Interactive Stage Canvas */}
        <div
          ref={stageRef}
          className="multiverse-stage-canvas"
          onClick={triggerQuantumPulse}
        >
          {/* Layer 1: Fluid Water Wave Ocean */}
          {(activeMode === 'fused' || activeMode === 'water') && (
            <div className="layer-water-ocean">
              <svg className="fluid-water-svg" viewBox="0 0 800 300">
                <defs>
                  <linearGradient id="oceanGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#0055ff" stopOpacity="0.1" />
                  </linearGradient>
                </defs>
                <path
                  className="fluid-wave-path"
                  d="M0,150 Q200,80 400,150 T800,150 L800,300 L0,300 Z"
                  fill="url(#oceanGrad)"
                  stroke="var(--cyan)"
                  strokeWidth="2"
                />
                <path
                  className="fluid-wave-path"
                  d="M0,180 Q200,240 400,180 T800,180 L800,300 L0,300 Z"
                  fill="none"
                  stroke="var(--coral)"
                  strokeWidth="1.5"
                  strokeDasharray="6 6"
                />
              </svg>
            </div>
          )}

          {/* Layer 2: Celestial Solar System Orbits */}
          {(activeMode === 'fused' || activeMode === 'solar') && (
            <div className="layer-celestial-solar">
              {/* Central Pulsing Sun */}
              <div className="celestial-sun-core">
                <div className="sun-pulse-ring" />
                <span>☀️</span>
              </div>

              {/* Orbital Rings & Planets */}
              {planets.map((p) => (
                <div
                  key={p.id}
                  className={`celestial-orbit-track planet-${p.id}`}
                  style={{
                    width: `${p.distance * 2}px`,
                    height: `${p.distance * 2}px`,
                  }}
                >
                  <div
                    className="celestial-planet-node"
                    style={{
                      width: `${p.size}px`,
                      height: `${p.size}px`,
                      background: p.color,
                      boxShadow: `0 0 15px ${p.color}`,
                    }}
                    title={`${p.name} Orbit // Speed: ${p.speed}x`}
                  />
                </div>
              ))}
            </div>
          )}

          {/* Layer 3: Thermal Lava Lamp Metablobs */}
          {(activeMode === 'fused' || activeMode === 'lava') && (
            <div className="layer-thermal-lava">
              <svg className="lava-svg-container" viewBox="0 0 400 300">
                <defs>
                  <radialGradient id="lavaGrad" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#ff2a5f" stopOpacity="0.8" />
                    <stop offset="100%" stopColor="#ffd166" stopOpacity="0.2" />
                  </radialGradient>
                </defs>
                <path
                  className="lava-blob-path"
                  d="M 50,15 Q 85,25 75,65 Q 55,95 25,75 Q 10,40 50,15 Z"
                  fill="url(#lavaGrad)"
                  stroke="var(--coral)"
                  strokeWidth="2"
                />
                <path
                  className="lava-blob-path"
                  d="M 45,20 Q 90,40 65,80 Q 30,90 15,55 Q 25,15 45,20 Z"
                  fill="none"
                  stroke="var(--gold)"
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                />
              </svg>
            </div>
          )}

          {/* Layer 4: Quantum Kinetic Particles */}
          {activeMode === 'fused' && (
            <div className="layer-quantum-particles">
              {Array.from({ length: 24 }).map((_, i) => (
                <div key={i} className="quantum-particle-dot" />
              ))}
            </div>
          )}
        </div>

        {/* Multiverse Environment Slider Deck & Quantum Shockwave Trigger */}
        <div className="multiverse-controls-bar">
          <div className="slider-group">
            <label>GRAVITY: {gravity}x</label>
            <input
              type="range"
              min="0.5"
              max="2.5"
              step="0.1"
              value={gravity}
              onChange={(e) => setGravity(parseFloat(e.target.value))}
            />
          </div>

          <div className="slider-group">
            <label>VISCOSITY: {viscosity}x</label>
            <input
              type="range"
              min="0.5"
              max="2.5"
              step="0.1"
              value={viscosity}
              onChange={(e) => setViscosity(parseFloat(e.target.value))}
            />
          </div>

          <div className="slider-group">
            <label>HEAT: {heat}x</label>
            <input
              type="range"
              min="0.5"
              max="2.5"
              step="0.1"
              value={heat}
              onChange={(e) => setHeat(parseFloat(e.target.value))}
            />
          </div>

          <div className="slider-group">
            <label>SPEED: {speed}x</label>
            <input
              type="range"
              min="0.5"
              max="2.5"
              step="0.1"
              value={speed}
              onChange={(e) => setSpeed(parseFloat(e.target.value))}
            />
          </div>

          <button className="btn btn-primary pulse-shockwave-btn" onClick={triggerQuantumPulse}>
            Fire Quantum Shockwave 💥
          </button>
        </div>
      </div>
    </section>
  )
}
