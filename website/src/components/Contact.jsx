import { useState } from 'react'
import { CONTACT_INFO, SOCIAL_LINKS } from '../data/portfolio'

export default function Contact() {
  const [copied, setCopied] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const copyEmail = () => {
    navigator.clipboard.writeText(CONTACT_INFO.email)
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  const handleSubmit = (e) => {
    // Formspree native submission allows standard submit; if handling via state:
    setSubmitted(true)
  }

  return (
    <section id="contact" className="section-container">
      <div className="section-header" style={{ textAlign: 'center' }}>
        <div className="section-kicker">📬 Transmission Zone</div>
        <h2 className="section-title">Start a Conversation</h2>
        <p className="section-subtitle" style={{ margin: '12px auto 0' }}>
          Have a project in mind, an analytics challenge, or an opportunity to explore? Get in touch!
        </p>
      </div>

      <div className="contact-card">
        <div className="contact-grid">
          <div>
            <h3 className="contact-info-title">Contact Channels</h3>
            <p className="contact-info-desc">
              {CONTACT_INFO.availability}
            </p>

            <div className="contact-details-list">
              <div className="contact-detail-item">
                <span className="contact-icon">📧</span>
                <div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Direct Email</div>
                  <div style={{ fontWeight: 600 }}>{CONTACT_INFO.email}</div>
                </div>
                <button
                  onClick={copyEmail}
                  className="pipeline-tag"
                  style={{ marginLeft: 'auto', cursor: 'pointer', color: 'var(--coral)' }}
                >
                  {copied ? '✓ Copied to Clipboard' : 'Copy'}
                </button>
              </div>

              <div className="contact-detail-item">
                <span className="contact-icon">📍</span>
                <div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Base Location</div>
                  <div style={{ fontWeight: 600 }}>{CONTACT_INFO.location}</div>
                </div>
              </div>

              <div style={{ marginTop: '20px', display: 'flex', gap: '12px' }}>
                {SOCIAL_LINKS.map((soc) => (
                  <a
                    key={soc.label}
                    href={soc.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-outline"
                    style={{ padding: '10px 18px', fontSize: '0.85rem' }}
                  >
                    {soc.label} ↗
                  </a>
                ))}
              </div>
            </div>
          </div>

          <form action={CONTACT_INFO.formspree} method="POST" onSubmit={handleSubmit}>
            {submitted && (
              <div className="transmission-success-banner">
                ⚡ SIGNAL TRANSMITTED // MESSAGE LOCKED
              </div>
            )}
            <div className="form-group">
              <label className="form-label">Your Name</label>
              <input type="text" name="name" className="form-input" placeholder="e.g. Sarah Jenkins" required />
            </div>

            <div className="form-group">
              <label className="form-label">Your Email</label>
              <input type="email" name="email" className="form-input" placeholder="sarah@company.com" required />
            </div>

            <div className="form-group">
              <label className="form-label">Message</label>
              <textarea name="message" className="form-textarea" placeholder="Tell me about your project or goal..." required />
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>
              Send Transmission ✨
            </button>
          </form>
        </div>
      </div>
    </section>
  )
}
