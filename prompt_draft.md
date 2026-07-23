# Teamwork Project Prompt — Draft

> Status: Ready for launch — executing full implementation
> Goal: Build, verify, and deploy Interactive Animation Telescope & Signal Viewfinder

Interactive Animation Telescope & Signal Viewfinder component inspired by showcase animation engines, built with Anime.js v4, WebGL, and SVG path morphing.

Working directory: c:\Users\Sourav Biswas\Souravjr0\website

## Requirements

### R1. Interactive Telescope & Lens Viewfinder Widget
Create an interactive animation inspector widget featuring:
- 5 live Anime.js v4 motion presets (Grid Ripple, Geometric Morph, Kinetic Particle Burst, Vortex Orbital, Spring Motion Path).
- Telephoto Lens Controls (1x, 1.5x, 2.5x zoom inspection).
- Interactive Control Deck (Play/Pause, Speed 0.5x/1x/2x, Step, Replay).
- Live Code & Signal Telemetry Inspector showing real-time animation parameters.

### R2. Full Site & Architecture Integration
- Integrate into site layout (`#viewfinder`), Navbar, Command Palette (`⌘K`), and Terminal commands.
- Ensure 60fps performance, touch device optimizations, and reduced motion fallbacks.

## Acceptance Criteria

- [x] Zero compilation or bundling errors (`npm run build`).
- [x] Deployed live to `gh-pages` branch.
- [x] Source code committed and pushed to `main` and `Mcp-trade` git branches.
