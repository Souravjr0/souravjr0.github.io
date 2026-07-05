import { useRef, useMemo, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

function FibonacciSphere({ count = 300, radius = 2.6 }) {
  const meshRef = useRef()
  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    const phi = Math.PI * (3 - Math.sqrt(5))

    for (let i = 0; i < count; i++) {
      const y = 1 - (i / (count - 1)) * 2
      const rY = Math.sqrt(1 - y * y)
      const th = phi * i
      const r = radius + (Math.random() - 0.5) * 0.25

      pos[i * 3] = Math.cos(th) * rY * r
      pos[i * 3 + 1] = y * r
      pos[i * 3 + 2] = Math.sin(th) * rY * r

      // Gold gradient
      const t = (y + 1) / 2
      colors[i * 3] = 0.79 + t * 0.04
      colors[i * 3 + 1] = 0.66 + t * 0.15
      colors[i * 3 + 2] = 0.43 + t * 0.35
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    return geo
  }, [count, radius])

  const mat = useMemo(() => new THREE.PointsMaterial({
    size: 0.04,
    vertexColors: true,
    transparent: true,
    opacity: 0.85,
    blending: THREE.AdditiveBlending,
    sizeAttenuation: true,
  }), [])

  const origPos = useMemo(() => positions.attributes.position.array.slice(), [positions])

  const noise = (x, y, z, t) =>
    Math.sin(x * 1.3 + t * 0.7) * Math.cos(y * 1.1 + t * 0.5) *
    Math.sin(z * 0.9 + t * 0.3) + Math.sin(x * 0.8 + z * 1.2 + t * 0.4) * 0.5

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    const pos = positions.attributes.position.array
    const hb = 1.0 + Math.sin(t * 1.5) * Math.cos(t * 0.4) * 0.05

    for (let i = 0; i < count; i++) {
      const ix = i * 3
      const ox = origPos[ix], oy = origPos[ix + 1], oz = origPos[ix + 2]
      const nv = noise(ox * 0.5, oy * 0.5, oz * 0.5, t * 0.7) * 0.1
      pos[ix] = ox * hb + ox * nv
      pos[ix + 1] = oy * hb + oy * nv
      pos[ix + 2] = oz * hb + oz * nv
    }
    positions.attributes.position.needsUpdate = true
    meshRef.current.rotation.y += 0.0015
  })

  return <points ref={meshRef} geometry={positions} material={mat} />
}

function DustParticles() {
  const count = 1000
  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const u = Math.random(), v = Math.random()
      const th = u * 2 * Math.PI, ph = Math.acos(2 * v - 1)
      const r = 3.5 + Math.random() * 5
      pos[i * 3] = r * Math.sin(ph) * Math.cos(th)
      pos[i * 3 + 1] = r * Math.sin(ph) * Math.sin(th)
      pos[i * 3 + 2] = r * Math.cos(ph)
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    return geo
  }, [count])

  const mat = useMemo(() => new THREE.PointsMaterial({
    size: 0.012,
    color: 0xd4cfc6,
    transparent: true,
    opacity: 0.35,
    blending: THREE.AdditiveBlending,
    sizeAttenuation: true,
  }), [])

  return <points geometry={positions} material={mat} />
}

function GlowMesh() {
  const meshRef = useRef()
  const mat = useMemo(() => new THREE.MeshBasicMaterial({
    color: 0xc9a96e,
    transparent: true,
    opacity: 0.012,
    blending: THREE.AdditiveBlending,
  }), [])

  useFrame(({ clock }) => {
    const hb = 1.0 + Math.sin(clock.getElapsedTime() * 1.5) * Math.cos(clock.getElapsedTime() * 0.4) * 0.05
    meshRef.current.scale.setScalar(hb * 1.1)
  })

  return (
    <mesh ref={meshRef} material={mat}>
      <sphereGeometry args={[2.3, 32, 32]} />
    </mesh>
  )
}

function SceneGroup() {
  const groupRef = useRef()
  
  useFrame(({ clock }) => {
    // Auto-rotate main group
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.0015
    }
  })

  // Position based on viewport once and on resize
  useEffect(() => {
    const updatePosition = () => {
      if (groupRef.current) {
        const isDesktop = window.innerWidth >= 1024
        groupRef.current.position.x = isDesktop ? 2.2 : 0
        groupRef.current.position.z = isDesktop ? 0 : -1
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
    </group>
  )
}

export default function HeroScene() {
  return (
    <Canvas
      camera={{ position: [0, 0, 7.5], fov: 55 }}
      gl={{ alpha: true, antialias: true, pixelRatio: Math.min(window.devicePixelRatio, 1.5) }}
      style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}
    >
      <SceneGroup />
    </Canvas>
  )
}
