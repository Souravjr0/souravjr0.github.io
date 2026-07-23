import { useEffect, useState } from 'react'

export function useIsTouchDevice() {
  const [isTouch, setIsTouch] = useState(false)

  useEffect(() => {
    const checkTouch = () => {
      setIsTouch(
        'ontouchstart' in window ||
          navigator.maxTouchPoints > 0 ||
          window.innerWidth < 768
      )
    }
    checkTouch()
    window.addEventListener('resize', checkTouch)
    return () => window.removeEventListener('resize', checkTouch)
  }, [])

  return isTouch
}

export function usePrefersReducedMotion() {
  const [reducedMotion, setReducedMotion] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    setReducedMotion(mediaQuery.matches)

    const onChange = (e) => setReducedMotion(e.matches)
    mediaQuery.addEventListener('change', onChange)
    return () => mediaQuery.removeEventListener('change', onChange)
  }, [])

  return reducedMotion
}
