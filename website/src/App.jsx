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
import CommandPalette from './components/CommandPalette'
import NeuralMapModal from './components/NeuralMapModal'
import { useScrollAnimations } from './hooks/useScrollAnimations'
import { useLenisScroll } from './hooks/useLenisScroll'

export default function App() {
  const [showIntro, setShowIntro] = useState(true)
  const [cmdPaletteOpen, setCmdPaletteOpen] = useState(false)
  const [neuralMapOpen, setNeuralMapOpen] = useState(false)
  const [surgeMode, setSurgeMode] = useState(false)
  const { scrollTo } = useLenisScroll()

  useScrollAnimations()

  // Konami Code Easter Egg (↑ ↑ ↓ ↓ ← → ← → b a)
  useEffect(() => {
    const konamiCode = [
      'ArrowUp',
      'ArrowUp',
      'ArrowDown',
      'ArrowDown',
      'ArrowLeft',
      'ArrowRight',
      'ArrowLeft',
      'ArrowRight',
      'b',
      'a',
    ]
    let index = 0

    const handleKeyDown = (e) => {
      if (e.key === konamiCode[index]) {
        index++
        if (index === konamiCode.length) {
          setSurgeMode((prev) => !prev)
          index = 0
        }
      } else {
        index = 0
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const handleSelectSection = (id) => {
    if (scrollTo) scrollTo(`#${id}`)
  }

  return (
    <div className={`app-root ${surgeMode ? 'surge-active' : ''}`}>
      {showIntro && <IntroAnimation onComplete={() => setShowIntro(false)} />}
      <ScrollProgress />
      <Cursor />
      <Navbar
        scrollTo={scrollTo}
        onOpenCmdPalette={() => setCmdPaletteOpen(true)}
      />
      <BackgroundShapes />
      <main>
        <Hero />
        <Marquee />
        <About />
        <WorkflowPipeline />
        <InteractiveTerminal onOpenNeuralMap={() => setNeuralMapOpen(true)} />
        <Services />
        <Projects />
        <Skills />
        <Contact />
      </main>
      <Footer />
      <BackToTop />

      <CommandPalette
        isOpen={cmdPaletteOpen}
        onClose={() => setCmdPaletteOpen(false)}
        onSelectSection={handleSelectSection}
        onOpenNeuralMap={() => setNeuralMapOpen(true)}
        onToggleSurge={() => setSurgeMode(!surgeMode)}
      />

      <NeuralMapModal
        isOpen={neuralMapOpen}
        onClose={() => setNeuralMapOpen(false)}
        onSelectSection={handleSelectSection}
      />
    </div>
  )
}
