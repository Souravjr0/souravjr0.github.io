import { useRef, useMemo, useEffect, useCallback } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

/* ---- Neural Constellation with linking lines & cursor signal displacement ---- */
function NeuralConstellation({ count = 350, maxDist = 1.4 }) {
  const meshRef = useRef()
  const linesRef = useRef()
  const mouseTarget = useRef({ x: 0, y: 0 })
  const currentMouse = useRef({ x: 0, y: 0 })

  const { positions, velocities, origPos, material } = useMemo(() => {
    const pos = new Float32Array(count * 3)
    const vel = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)

    for (let i = 0; i < count; i++) {
      const x = (Math.random() - 0.5) * 12
      const y = (Math.random() - 0.5) * 8
      const z = (Math.random() - 0.5) * 6

      pos[i * 3] = x
      pos[i * 3 + 1] = y
      pos[i * 3 + 2] = z

      vel[i * 3] = (Math.random() - 0.5) * 0.003
      vel[i * 3 + 1] = (Math.random() - 0.5) * 0.003
      vel[i * 3 + 2] = (Math.random() - 0.5) * 0.003

      const t = Math.random()
      if (t < 0.4) {
        colors[i * 3] = 1.0; colors[i * 3 + 1] = 0.16; colors[i * 3 + 2] = 0.37 // Coral
      } else if (t < 0.8) {
        colors[i * 3] = 0.0; colors[i * 3 + 1] = 0.94; colors[i * 3 + 2] = 1.0 // Cyan
      } else {
        colors[i * 3] = 1.0; colors[i * 3 + 1] = 0.82; colors[i * 3 + 2] = 0.4 // Gold
      }
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))

    const mat = new THREE.PointsMaterial({
      size: 0.065,
      vertexColors: true,
      transparent: true,
      opacity: 0.9,
      blending: THREE.AdditiveBlending,
      sizeAttenuation: true,
      depthWrite: false,
    })

    return { positions: geo, velocities: vel, origPos: pos.slice(), material: mat }
  }, [count])

  // Buffer geometry for dynamic line connections between nearby nodes
  const lineGeo = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    const maxLines = count * 6
    const linePos = new Float32Array(maxLines * 6)
    geo.setAttribute('position', new THREE.BufferAttribute(linePos, 3))
    return geo
  }, [count])

  const lineMat = useMemo(() => new THREE.LineBasicMaterial({
    color: 0x00f0ff,
    transparent: true,
    opacity: 0.18,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  }), [])

  useFrame(({ clock, pointer }) => {
    const t = clock.getElapsedTime()
    const pos = positions.attributes.position.array

    mouseTarget.current.x = pointer.x * 5
    mouseTarget.current.y = pointer.y * 3.5

    currentMouse.current.x += (mouseTarget.current.x - currentMouse.current.x) * 0.05
    currentMouse.current.y += (mouseTarget.current.y - currentMouse.current.y) * 0.05

    const mx = currentMouse.current.x
    const my = currentMouse.current.y

    // Move nodes & deflect near pointer signal
    for (let i = 0; i < count; i++) {
      const ix = i * 3
      pos[ix] += velocities[ix]
      pos[ix + 1] += velocities[ix + 1]
      pos[ix + 2] += velocities[ix + 2]

      // Bounce bounds
      if (Math.abs(pos[ix]) > 6.5) velocities[ix] *= -1
      if (Math.abs(pos[ix + 1]) > 4.5) velocities[ix + 1] *= -1
      if (Math.abs(pos[ix + 2]) > 3.5) velocities[ix + 2] *= -1

      // Cursor signal field bending nearby nodes
      const dx = pos[ix] - mx
      const dy = pos[ix + 1] - my
      const distSq = dx * dx + dy * dy
      if (distSq < 2.5) {
        const force = (2.5 - distSq) * 0.02
        pos[ix] += dx * force
        pos[ix + 1] += dy * force
      }
    }
    positions.attributes.position.needsUpdate = true

    // Compute dynamic line links between close nodes
    if (linesRef.current) {
      const lineArray = lineGeo.attributes.position.array
      let lineIdx = 0

      for (let i = 0; i < count; i++) {
        for (let j = i + 1; j < count; j++) {
          const i1 = i * 3
          const i2 = j * 3
          const dx = pos[i1] - pos[i2]
          const dy = pos[i1 + 1] - pos[i2 + 1]
          const dz = pos[i1 + 2] - pos[i2 + 2]
          const dist = Math.sqrt(dx * dx + dy * dy + dz * dz)

          if (dist < maxDist && lineIdx < lineArray.length - 6) {
            lineArray[lineIdx++] = pos[i1]
            lineArray[lineIdx++] = pos[i1 + 1]
            lineArray[lineIdx++] = pos[i1 + 2]

            lineArray[lineIdx++] = pos[i2]
            lineArray[lineIdx++] = pos[i2 + 1]
            lineArray[lineIdx++] = pos[i2 + 2]
          }
        }
      }
      lineGeo.setDrawRange(0, lineIdx / 3)
      lineGeo.attributes.position.needsUpdate = true
    }

    if (meshRef.current) {
      meshRef.current.rotation.y = Math.sin(t * 0.1) * 0.1
    }
  })

  return (
    <>
      <points ref={meshRef} geometry={positions} material={material} />
      <lineSegments ref={linesRef} geometry={lineGeo} material={lineMat} />
    </>
  )
}

function SceneGroup() {
  const groupRef = useRef()

  useEffect(() => {
    const updatePosition = () => {
      if (groupRef.current) {
        const isDesktop = window.innerWidth >= 1024
        groupRef.current.position.x = isDesktop ? 1.5 : 0
      }
    }
    updatePosition()
    window.addEventListener('resize', updatePosition)
    return () => window.removeEventListener('resize', updatePosition)
  }, [])

  return (
    <group ref={groupRef}>
      <NeuralConstellation />
    </group>
  )
}

export default function HeroScene() {
  return (
    <Canvas
      camera={{ position: [0, 0, 7], fov: 50 }}
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
