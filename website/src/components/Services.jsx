import { SERVICES } from '../data/portfolio'

export default function Services() {
  return (
    <section id="services" className="section">
      <div className="container">
        <span className="label">Services</span>
        <h2 className="heading-lg">What I Build.</h2>
        <div className="services-list">
          {SERVICES.map((service) => (
            <div key={service.id} className="service-item">
              <span className="service-idx">{service.id}</span>
              <div className="service-content">
                <h3>{service.title}</h3>
                <p>{service.description}</p>
              </div>
              <div className="service-tags">
                {service.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
