import { useEffect, useState } from 'react'

export default function BackToTop() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const handleScroll = () => setVisible(window.scrollY > 600)
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <button
      className="back-to-top"
      style={{
        position: 'fixed',
        bottom: '2rem',
        right: '2rem',
        width: 44,
        height: 44,
        borderRadius: '50%',
        background: 'var(--bg-2)',
        border: '1px solid var(--border)',
        color: 'var(--gold)',
        fontSize: '1.1rem',
        cursor: 'pointer',
        zIndex: 500,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(16px)',
        transition: 'opacity .3s, transform .3s, border-color .3s',
        pointerEvents: visible ? 'auto' : 'none',
      }}
      onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
      aria-label="Back to top"
    >
      ↑
    </button>
  )
}
