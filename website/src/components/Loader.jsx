import { useEffect, useRef, useState } from 'react'

export default function Loader({ onComplete }) {
  const [count, setCount] = useState(0)
  const [visible, setVisible] = useState(true)
  const startTime = useRef(Date.now())

  useEffect(() => {
    const duration = 1600
    const animate = () => {
      const elapsed = Date.now() - startTime.current
      const progress = Math.min(elapsed / duration, 1)
      // Ease in-out quad
      const eased = progress < 0.5
        ? 2 * progress * progress
        : 1 - Math.pow(-2 * progress + 2, 2) / 2
      setCount(Math.round(eased * 100))

      if (progress < 1) {
        requestAnimationFrame(animate)
      } else {
        setTimeout(() => {
          setVisible(false)
          if (onComplete) onComplete()
        }, 400)
      }
    }
    requestAnimationFrame(animate)
  }, [onComplete])

  if (!visible) return null

  return (
    <div className="loader">
      <div className="loader-counter">{count}</div>
      <div className="loader-bar">
        <span className="loader-fill" style={{ width: `${count}%` }} />
      </div>
    </div>
  )
}
