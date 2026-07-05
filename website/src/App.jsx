import { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import Loader from './components/Loader'
import Cursor from './components/Cursor'
import Hero from './components/Hero'
import Marquee from './components/Marquee'
import About from './components/About'
import Services from './components/Services'
import Projects from './components/Projects'
import Skills from './components/Skills'
import Contact from './components/Contact'
import Footer from './components/Footer'
import ScrollProgress from './components/ScrollProgress'
import BackToTop from './components/BackToTop'
import BackgroundShapes from './components/three/BackgroundShapes'
import { useScrollAnimations } from './hooks/useScrollAnimations'

export default function App() {
  const [loading, setLoading] = useState(true)

  useScrollAnimations()

  useEffect(() => {
    const isReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (isReduced) setLoading(false)
  }, [])

  return (
    <>
      {loading && <Loader onComplete={() => setLoading(false)} />}
      <ScrollProgress />
      <Cursor />
      <Navbar />
      <BackgroundShapes />
      <main>
        <Hero />
        <Marquee />
        <About />
        <Services />
        <Projects />
        <Skills />
        <Contact />
      </main>
      <Footer />
      <BackToTop />
    </>
  )
}
