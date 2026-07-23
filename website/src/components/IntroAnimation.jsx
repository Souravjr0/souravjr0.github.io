import { useEffect, useRef, useState } from 'react'
import { animate, stagger } from 'animejs'

export default function IntroAnimation({ onComplete }) {
  const [percent, setPercent] = useState(0)
  const containerRef = useRef(null)
  const svgRef = useRef(null)

  useEffect(() => {
    // 1. Percentage counter animation
    const counter = { val: 0 }
    animate(counter, {
      val: 100,
      round: 1,
      duration: 1800,
      ease: 'inOutQuad',
      onUpdate: () => {
        setPercent(Math.round(counter.val))
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
          duration: 1600,
          ease: 'inOutSine',
          delay: i * 200,
        })
      })
    }

    // 3. Kinetic text reveal
    animate('.intro-char', {
      translateY: [60, 0],
      opacity: [0, 1],
      rotateZ: [10, 0],
      duration: 1000,
      delay: stagger(35, { start: 200 }),
      ease: 'outElastic(1, .6)',
    })

    // 4. Curtain exit animation
    const timer = setTimeout(() => {
      animate('.intro-curtain', {
        translateY: ['0%', '-100%'],
        duration: 900,
        delay: stagger(80),
        ease: 'inOutExpo',
        onComplete: () => {
          if (onComplete) onComplete()
        },
      })
    }, 2200)

    return () => clearTimeout(timer)
  }, [onComplete])

  const titleText = 'SOURAV BISWAS'

  return (
    <div ref={containerRef} className="intro-overlay">
      <div className="intro-curtain-container">
        <div className="intro-curtain" />
        <div className="intro-curtain" />
        <div className="intro-curtain" />
      </div>

      <div className="intro-content">
        <svg
          ref={svgRef}
          width="120"
          height="120"
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

        <div className="intro-subtitle">DATA ANALYST // FULL-STACK // AI ARCHITECT</div>

        <div className="intro-progress-bar">
          <div className="intro-progress-fill" style={{ width: `${percent}%` }} />
        </div>

        <div className="intro-percent">{percent}%</div>
      </div>
    </div>
  )
}
