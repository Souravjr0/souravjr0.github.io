export default function BackgroundShapes() {
  return (
    <div
      style={{
        position: 'fixed',
        top: 0, left: 0,
        width: '100%', height: '100%',
        zIndex: 0,
        pointerEvents: 'none',
        overflow: 'hidden',
      }}
      aria-hidden="true"
    >
      {/* Wireframe icosahedron-like decorative shape */}
      <div
        style={{
          position: 'absolute',
          top: '15%', left: '5%',
          width: 'clamp(120px, 18vw, 280px)',
          height: 'clamp(120px, 18vw, 280px)',
          borderRadius: '30% 70% 70% 30% / 30% 30% 70% 70%',
          border: '1px solid rgba(255,42,95,0.06)',
          opacity: 0.5,
          transform: 'rotate(25deg)',
          animation: 'floatShape 20s ease-in-out infinite',
        }}
      />
      {/* Wireframe octahedron-like decorative shape */}
      <div
        style={{
          position: 'absolute',
          bottom: '20%', right: '3%',
          width: 'clamp(100px, 14vw, 200px)',
          height: 'clamp(100px, 14vw, 200px)',
          borderRadius: '60% 40% 30% 70% / 60% 30% 70% 40%',
          border: '1px solid rgba(0,240,255,0.05)',
          opacity: 0.4,
          transform: 'rotate(-15deg)',
          animation: 'floatShape 25s ease-in-out infinite reverse',
        }}
      />
      {/* Ring-like decorative shape */}
      <div
        style={{
          position: 'absolute',
          top: '50%', left: '50%',
          width: 'clamp(180px, 25vw, 350px)',
          height: 'clamp(180px, 25vw, 350px)',
          borderRadius: '50%',
          border: '1px solid rgba(162,89,255,0.05)',
          opacity: 0.3,
          transform: 'translate(-50%, -50%)',
          animation: 'floatShape 30s ease-in-out infinite 5s',
        }}
      />
      <style>{`
        @keyframes floatShape {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          33% { transform: translateY(-20px) rotate(5deg); }
          66% { transform: translateY(15px) rotate(-3deg); }
        }
      `}</style>
    </div>
  )
}
