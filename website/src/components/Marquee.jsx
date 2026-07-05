export default function Marquee() {
  const items = [
    'Python', 'TensorFlow', 'SQL', 'PyTorch', 'AWS', 'React',
    'Three.js', 'GSAP', 'Docker', 'Pandas', 'Scikit-learn', 'FastAPI',
  ]

  return (
    <div className="marquee" aria-hidden="true">
      <div className="marquee-inner">
        {[...items, ...items].map((item, i) => (
          <span key={i}>
            {item}
            {i < items.length * 2 - 1 && <span className="mq-sep"> ✦ </span>}
          </span>
        ))}
      </div>
    </div>
  )
}
