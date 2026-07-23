import { useRef, useMemo, useEffect, useCallback } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

/* ---- Fibonacci sphere with mouse interactivity & Anime.js signature palette ---- */
function FibonacciSphere({ count = 550, radius = 2.8 }) {
  const meshRef = useRef()
  const mouseTarget = useRef({ x: 0, y: 0 })
  const currentMouse = useRef({ x: 0, y: 0 })

  const { positions, origPos, material } = useMemo(() => {
    const pos = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    const phi = Math.PI * (3 - Math.sqrt(5))

    for (let i = 0; i < count; i++) {
      const y = 1 - (i / (count - 1)) * 2
      const rY = Math.sqrt(1 - y * y)
      const th = phi * i
      const r = radius + (Math.random() - 0.5) * 0.35

      pos[i * 3] = Math.cos(th) * rY * r
      pos[i * 3 + 1] = y * r
      pos[i * 3 + 2] = Math.sin(th) * rY * r

      const t = (y + 1) / 2
      // Neon Coral (#ff2a5f) -> Electric Cyan (#00f0ff) -> Solar Gold (#ffd166)
      if (t < 0.5) {
        const factor = t * 2
        colors[i * 3] = 1.0 - factor * 1.0 // 1.0 -> 0.0
        colors[i * 3 + 1] = 0.16 + factor * 0.78 // 0.16 -> 0.94
        colors[i * 3 + 2] = 0.37 + factor * 0.63 // 0.37 -> 1.0
      } else {
        const factor = (t - 0.5) * 2
        colors[i * 3] = factor * 1.0 // 0.0 -> 1.0
        colors[i * 3 + 1] = 0.94 - factor * 0.12 // 0.94 -> 0.82
        colors[i * 3 + 2] = 1.0 - factor * 0.6 // 1.0 -> 0.4
      }
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))

    const mat = new THREE.PointsMaterial({
      size: 0.05,
      vertexColors: true,
      transparent: true,
      opacity: 0.95,
      blending: THREE.AdditiveBlending,
      sizeAttenuation: true,
      depthWrite: false,
    })

    return { positions: geo, origPos: pos.slice(), material: mat }
  }, [count, radius])

  const noise = useCallback((x, y, z, t) =>
    Math.sin(x * 1.3 + t * 0.7) * Math.cos(y * 1.1 + t * 0.5) *
    Math.sin(z * 0.9 + t * 0.3) + Math.sin(x * 0.8 + z * 1.2 + t * 0.4) * 0.5,
  [])

  useFrame(({ clock, pointer }) => {
    const t = clock.getElapsedTime()
    const pos = positions.attributes.position.array

    mouseTarget.current.x = pointer.x * 0.3
    mouseTarget.current.y = -pointer.y * 0.2
    currentMouse.current.x += (mouseTarget.current.x - currentMouse.current.x) * 0.05
    currentMouse.current.y += (mouseTarget.current.y - currentMouse.current.y) * 0.05

    const mx = currentMouse.current.x
    const my = currentMouse.current.y
    const hb = 1.0 + Math.sin(t * 1.2) * Math.cos(t * 0.4) * 0.06

    for (let i = 0; i < count; i++) {
      const ix = i * 3
      const ox = origPos[ix], oy = origPos[ix + 1], oz = origPos[ix + 2]
      const nv = noise(ox * 0.5, oy * 0.5, oz * 0.5, t * 0.6) * 0.12
      const mouseInfluence = mx * (oz * 0.05) + my * (ox * 0.05)
      pos[ix] = ox * hb + ox * nv + mouseInfluence * 0.3
      pos[ix + 1] = oy * hb + oy * nv + mouseInfluence * 0.2
      pos[ix + 2] = oz * hb + oz * nv
    }
    positions.attributes.position.needsUpdate = true

    if (meshRef.current) {
      meshRef.current.rotation.y += 0.0012
      meshRef.current.rotation.x += my * 0.0003
    }
  })

  return <points ref={meshRef} geometry={positions} material={material} />
}

/* ---- Dust particles ---- */
function DustParticles() {
  const ref = useRef()
  const count = 1200
  const { geometry, material } = useMemo(() => {
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const u = Math.random(), v = Math.random()
      const th = u * 2 * Math.PI, ph = Math.acos(2 * v - 1)
      const r = 4 + Math.random() * 6
      pos[i * 3] = r * Math.sin(ph) * Math.cos(th)
      pos[i * 3 + 1] = r * Math.sin(ph) * Math.sin(th)
      pos[i * 3 + 2] = r * Math.cos(ph)
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    const mat = new THREE.PointsMaterial({
      size: 0.016,
      color: 0xff2a5f,
      transparent: true,
      opacity: 0.35,
      blending: THREE.AdditiveBlending,
      sizeAttenuation: true,
      depthWrite: false,
    })
    return { geometry: geo, material: mat }
  }, [])

  useFrame(({ pointer }) => {
    if (ref.current) {
      ref.current.rotation.x += (-pointer.y * 0.01 - ref.current.rotation.x) * 0.02
      ref.current.rotation.y += (-pointer.x * 0.01 - ref.current.rotation.y) * 0.02
    }
  })

  return <points ref={ref} geometry={geometry} material={material} />
}

/* ---- Pulsing glow sphere ---- */
function GlowMesh() {
  const meshRef = useRef()
  const mat = useMemo(() => new THREE.MeshBasicMaterial({
    color: 0xff2a5f,
    transparent: true,
    opacity: 0.025,
    blending: THREE.AdditiveBlending,
  }), [])

  useFrame(({ clock }) => {
    const pulse = 1.0 + Math.sin(clock.getElapsedTime() * 1.5) * 0.06
    meshRef.current.scale.setScalar(pulse * 1.15)
  })

  return (
    <mesh ref={meshRef} material={mat}>
      <sphereGeometry args={[2.5, 32, 32]} />
    </mesh>
  )
}

/* ---- Orbiting ring lines ---- */
function OrbitalRings() {
  const ring1 = useRef()
  const ring2 = useRef()

  const ringGeo = useMemo(() => {
    const pts = []
    const segments = 64
    for (let i = 0; i <= segments; i++) {
      const theta = (i / segments) * Math.PI * 2
      pts.push(Math.cos(theta) * 3.2, Math.sin(theta) * 3.2, 0)
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3))
    return geo
  }, [])

  const ringMat = useMemo(() => new THREE.LineBasicMaterial({
    color: 0x00f0ff,
    transparent: true,
    opacity: 0.22,
    depthWrite: false,
  }), [])

  useFrame(({ clock }) => {
    if (ring1.current) {
      ring1.current.rotation.x = Math.sin(clock.getElapsedTime() * 0.2) * 0.8
      ring1.current.rotation.z = clock.getElapsedTime() * 0.1
    }
    if (ring2.current) {
      ring2.current.rotation.y = Math.sin(clock.getElapsedTime() * 0.3) * 0.6
      ring2.current.rotation.x = Math.PI / 3
    }
  })

  return (
    <>
      <line ref={ring1} geometry={ringGeo} material={ringMat} />
      <line ref={ring2} geometry={ringGeo} material={ringMat} />
    </>
  )
}

function SceneGroup() {
  const groupRef = useRef()

  useFrame(() => {
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.0008
    }
  })

  useEffect(() => {
    const updatePosition = () => {
      if (groupRef.current) {
        const isDesktop = window.innerWidth >= 1024
        groupRef.current.position.x = isDesktop ? 2.4 : 0
        groupRef.current.position.z = isDesktop ? 0 : -1.5
      }
    }
    updatePosition()
    window.addEventListener('resize', updatePosition)
    return () => window.removeEventListener('resize', updatePosition)
  }, [])

  return (
    <group ref={groupRef}>
      <FibonacciSphere />
      <DustParticles />
      <GlowMesh />
      <OrbitalRings />
    </group>
  )
}

export default function HeroScene() {
  return (
    <Canvas
      camera={{ position: [0, 0, 8], fov: 50 }}
      gl={{
        alpha: true,
        antialias: true,
        pixelRatio: Math.min(window.devicePixelRatio, 1.5),
        powerPreference: 'high-performance',
      }}
      dpr={[1, 1.5]}
      style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}
    >
      <SceneGroup />
    </Canvas>
  )
}
