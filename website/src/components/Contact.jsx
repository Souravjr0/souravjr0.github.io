import { useState } from 'react'
import { CONTACT_INFO } from '../data/portfolio'

export default function Contact() {
  const [status, setStatus] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    const form = e.target
    try {
      const res = await fetch(CONTACT_INFO.formspree, {
        method: 'POST',
        body: new FormData(form),
        headers: { Accept: 'application/json' },
      })
      if (res.ok) {
        setStatus("Sent. I'll reply within 24 hours.")
        form.reset()
      } else throw new Error()
    } catch {
      setStatus('Error. Email me directly at biswasmail631@gmail.com')
    }
    setSubmitting(false)
    setTimeout(() => setStatus(''), 8000)
  }

  return (
    <section id="contact" className="section">
      <div className="container">
        <div className="split-grid">
          <div className="split-left">
            <span className="label">Contact</span>
            <h2 className="heading-lg">Let's work<br />together.</h2>
            <div className="contact-meta">
              <div className="cm-item">
                <span className="cm-label">Email</span>
                <a href={`mailto:${CONTACT_INFO.email}`} className="cm-value">
                  {CONTACT_INFO.email}
                </a>
              </div>
              <div className="cm-item">
                <span className="cm-label">LinkedIn</span>
                <a href={CONTACT_INFO.linkedin} target="_blank" rel="noopener" className="cm-value">
                  sourav-biswas ↗
                </a>
              </div>
              <div className="cm-item">
                <span className="cm-label">Status</span>
                <span className="cm-status">
                  <span className="status-dot" />
                  Available
                </span>
              </div>
            </div>
          </div>
          <div className="split-right">
            <form onSubmit={handleSubmit} className="contact-form">
              <div className="form-row">
                <div className="form-field">
                  <label htmlFor="c-name">Name</label>
                  <input id="c-name" type="text" name="name" required placeholder="Your name" />
                </div>
                <div className="form-field">
                  <label htmlFor="c-email">Email</label>
                  <input id="c-email" type="email" name="email" required placeholder="your@email.com" />
                </div>
              </div>
              <div className="form-field">
                <label htmlFor="c-msg">Message</label>
                <textarea id="c-msg" name="message" rows="5" required placeholder="Tell me about your project..." />
              </div>
              <button type="submit" className="btn btn-primary btn-full" disabled={submitting}>
                {submitting ? 'Sending...' : 'Send Message'}
              </button>
              {status && (
                <div className="form-status visible" style={{ color: status.includes('Error') ? '#c97070' : 'var(--gold)' }}>
                  {status}
                </div>
              )}
            </form>
          </div>
        </div>
      </div>
    </section>
  )
}
