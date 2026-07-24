import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// Enables the JS-gated scroll-reveal state; without JS, sections stay visible.
document.documentElement.classList.add('has-js')

// Start every load at the top; don't let the browser restore a mid-page
// scroll position (fights Lenis smooth scroll on reload).
if ('scrollRestoration' in history) history.scrollRestoration = 'manual'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
