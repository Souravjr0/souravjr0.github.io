import { useEffect, useRef, useState } from 'react'
import { animate, stagger } from 'animejs'
import { usePrefersReducedMotion } from '../hooks/useAnimev4'

export default function IntroAnimation({ onComplete }) {
  const [percent, setPercent] = useState(0)
  const [statusText, setStatusText] = useState('INITIALIZING NEURAL PIPELINE...')
  const reducedMotion = usePrefersReducedMotion()
  const svgRef = useRef(null)

  useEffect(() => {
    if (reducedMotion) {
      if (onComplete) onComplete()
      return
    }

    // 1. Asset & Module verification simulation
    const statusLogs = [
      'INITIALIZING NEURAL PIPELINE...',
      'LOADING THREE.JS SHADERS...',
      'INGESTING DATA MODELS...',
      'VERIFYING MLOPS TELEMETRY...',
      'SYSTEM ONLINE // SIGNAL STABLE',
    ]

    const counter = { val: 0 }
    animate(counter, {
      val: 100,
      round: 1,
      duration: 1800,
      ease: 'inOutQuad',
      onUpdate: () => {
        const val = Math.round(counter.val)
        setPercent(val)
        const idx = Math.min(Math.floor((val / 100) * statusLogs.length), statusLogs.length - 1)
        setStatusText(statusLogs[idx])
      },
    })

    // 2. SVG path drawing animation
    const paths = svgRef.current?.querySelectorAll('path')
    if (paths && paths.length > 0) {
      paths.forEach((path) => {
        const len = path.getTotalLength()
        path.style.strokeDasharray = len
        path.style.strokeDashoffset = len
      })

      paths.forEach((path, i) => {
        const len = path.getTotalLength()
        animate(path, {
          strokeDashoffset: [len, 0],
          duration: 1500,
          ease: 'inOutSine',
          delay: i * 180,
        })
      })
    }

    // 3. Kinetic blur-to-sharp text reveal
    animate('.intro-char', {
      translateY: [40, 0],
      opacity: [0, 1],
      filter: ['blur(12px)', 'blur(0px)'],
      duration: 900,
      delay: stagger(40, { start: 150 }),
      ease: 'outExpo',
    })

    // 4. Curtain exit transition
    const timer = setTimeout(() => {
      animate('.intro-curtain', {
        translateY: ['0%', '-100%'],
        duration: 800,
        delay: stagger(70),
        ease: 'inOutExpo',
        onComplete: () => {
          if (onComplete) onComplete()
        },
      })
    }, 2200)

    return () => clearTimeout(timer)
  }, [onComplete, reducedMotion])

  if (reducedMotion) return null

  const titleText = 'SOURAV BISWAS'

  return (
    <div className="intro-overlay">
      <div className="intro-curtain-container">
        <div className="intro-curtain" />
        <div className="intro-curtain" />
        <div className="intro-curtain" />
      </div>

      <div className="intro-content">
        <svg
          ref={svgRef}
          width="110"
          height="110"
          viewBox="0 0 100 100"
          className="intro-svg"
        >
          <path
            d="M 50,10 L 90,30 L 90,70 L 50,90 L 10,70 L 10,30 Z"
            fill="none"
            stroke="#ff2a5f"
            strokeWidth="3"
          />
          <path
            d="M 50,25 L 75,38 L 75,62 L 50,75 L 25,62 L 25,38 Z"
            fill="none"
            stroke="#00f0ff"
            strokeWidth="2"
          />
          <path
            d="M 50,40 L 60,46 L 60,54 L 50,60 L 40,54 L 40,46 Z"
            fill="none"
            stroke="#ffd166"
            strokeWidth="2"
          />
        </svg>

        <div className="intro-title">
          {titleText.split('').map((char, index) => (
            <span key={index} className="intro-char">
              {char === ' ' ? '\u00A0' : char}
            </span>
          ))}
        </div>

        <div className="intro-subtitle">{statusText}</div>

        <div className="intro-progress-bar">
          <div className="intro-progress-fill" style={{ width: `${percent}%` }} />
        </div>

        <div className="intro-percent">{percent}%</div>
      </div>
    </div>
  )
}
