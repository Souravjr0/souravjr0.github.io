import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// Enables the JS-gated scroll-reveal state; without JS, sections stay visible.
document.documentElement.classList.add('has-js')

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
