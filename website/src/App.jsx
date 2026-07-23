import { useState, useEffect } from 'react'
import IntroAnimation from './components/IntroAnimation'
import Navbar from './components/Navbar'
import Cursor from './components/Cursor'
import Hero from './components/Hero'
import Marquee from './components/Marquee'
import About from './components/About'
import WorkflowPipeline from './components/WorkflowPipeline'
import InteractiveTerminal from './components/InteractiveTerminal'
import Services from './components/Services'
import Projects from './components/Projects'
import Skills from './components/Skills'
import Contact from './components/Contact'
import Footer from './components/Footer'
import ScrollProgress from './components/ScrollProgress'
import BackToTop from './components/BackToTop'
import BackgroundShapes from './components/three/BackgroundShapes'
import { useScrollAnimations } from './hooks/useScrollAnimations'
import { useLenisScroll } from './hooks/useLenisScroll'

export default function App() {
  const [showIntro, setShowIntro] = useState(true)
  const { scrollTo } = useLenisScroll()

  useScrollAnimations()

  useEffect(() => {
    const isReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (isReduced) setShowIntro(false)
  }, [])

  return (
    <>
      {showIntro && <IntroAnimation onComplete={() => setShowIntro(false)} />}
      <ScrollProgress />
      <Cursor />
      <Navbar scrollTo={scrollTo} />
      <BackgroundShapes />
      <main>
        <Hero />
        <Marquee />
        <About />
        <WorkflowPipeline />
        <InteractiveTerminal />
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
