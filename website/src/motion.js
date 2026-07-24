// Shared motion vocabulary — one easing family + duration scale so every
// section animates with the same feel. Mirrors the CSS custom props in
// index.css (--ease-out / --dur-*). Import these instead of hand-typing eases.

export const EASE = {
  out: 'cubicBezier(0.16, 1, 0.3, 1)', // signature entrance curve
  inOut: 'cubicBezier(0.65, 0, 0.35, 1)', // transitions / loops
  spring: 'outElastic(1, 0.6)', // playful accents — use sparingly
}

export const DUR = {
  fast: 400,
  base: 700,
  slow: 1100,
}

export const STAGGER = 60 // ms base step for staggered groups

export const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches
