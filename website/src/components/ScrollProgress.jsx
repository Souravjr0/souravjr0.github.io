import { useEffect, useState } from 'react'

export default function ScrollProgress() {
  const [width, setWidth] = useState('0%')

  useEffect(() => {
    const handleScroll = () => {
      const d = document.documentElement.scrollHeight - window.innerHeight
      setWidth(`${d > 0 ? (window.scrollY / d) * 100 : 0}%`)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return <div className="scroll-progress-bar" style={{ width }} />
}
