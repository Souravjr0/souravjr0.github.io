import { useEffect, useRef } from 'react'
import HeroScene from './three/HeroScene'

export default function Hero() {
  const descRef = useRef(null)

  useEffect(() => {
    const isReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (isReduced || !descRef.current) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          const el = entry.target
          const origText = el.innerText
          const chars = '!<>-_\\/[]{}—=+*^?#________'
          let frame = 0
          let queue = []

          for (let i = 0; i < origText.length; i++) {
            const start = Math.floor(Math.random() * 40)
            const end = start + Math.floor(Math.random() * 40)
            queue.push({ from: '', to: origText[i], start, end, char: '' })
          }

          el.innerHTML = ''
          const update = () => {
            let output = ''
            let complete = 0
            for (let i = 0; i < queue.length; i++) {
              const item = queue[i]
              if (frame >= item.end) { complete++; output += item.to }
              else if (frame >= item.start) {
                if (!item.char || Math.random() < 0.28) {
                  item.char = chars[Math.floor(Math.random() * chars.length)]
                }
                output += `<span style="color:var(--gold)">${item.char}</span>`
              } else { output += item.from }
            }
            el.innerHTML = output
            if (complete < queue.length) { frame++; requestAnimationFrame(update) }
            else { el.textContent = origText }
          }
          requestAnimationFrame(update)
          observer.unobserve(el)
        }
      },
      { threshold: 0.5 }
    )
    observer.observe(descRef.current)
    return () => observer.disconnect()
  }, [])

  return (
    <section id="hero" className="hero-section">
      <div className="hero-canvas-container">
        <HeroScene />
      </div>
      <div className="hero-inner">
        <div className="hero-eyebrow">
          <span className="status-dot" />
          <span>Available for projects — Pune, India</span>
        </div>
        <h1 className="hero-title">
          <span className="hero-line"><span className="hero-line-inner" style={{ display: 'block', willChange: 'transform' }}>Sourav</span></span>
          <span className="hero-line"><span className="hero-line-inner" style={{ display: 'block', willChange: 'transform' }}>Biswas<span className="title-accent">.</span></span></span>
        </h1>
        <div className="hero-bottom">
          <p ref={descRef} className="hero-desc">
            Business &amp; Data Analyst turning raw data into strategic decisions that move the needle.
          </p>
          <div className="hero-actions">
            <a href="#projects" className="btn btn-primary">Selected Work</a>
            <a href="#contact" className="btn btn-outline">Get in Touch</a>
          </div>
        </div>
      </div>
      <div className="hero-scroll-cue">
        <span className="scroll-line" />
        <span className="scroll-text">Scroll</span>
      </div>
    </section>
  )
}
