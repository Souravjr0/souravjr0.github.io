// ============================================================
//  SOURAV BISWAS PORTFOLIO — script.js (Redesign)
// ============================================================

gsap.registerPlugin(ScrollTrigger);

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const isDesktop = window.matchMedia('(hover: hover) and (pointer: fine)').matches && window.innerWidth >= 1024;
const useMotion = isDesktop && !prefersReducedMotion;

// ------- Loader -------
window.addEventListener('load', () => {
  const tl = gsap.timeline();
  tl.to('.loader-fill', { width: '100%', duration: 1.2, ease: 'power3.inOut' })
    .to('#loader', { yPercent: -100, duration: 0.8, ease: 'power4.inOut' })
    .add(() => {
      document.body.classList.remove('loading');
      document.getElementById('loader')?.remove();
    }, '-=0.3')
    .from('.hero-line', { y: 80, opacity: 0, duration: 1, stagger: 0.15, ease: 'power4.out' }, '-=0.4')
    .from('.reveal-fade', { opacity: 0, y: 16, duration: 0.8, stagger: 0.12, ease: 'power2.out' }, '-=0.6');
});

// ------- Custom Cursor (desktop only) -------
if (useMotion) {
  const dot  = document.querySelector('.cursor-dot');
  const glow = document.querySelector('.cursor-glow');
  window.addEventListener('mousemove', e => {
    if (dot)  gsap.to(dot,  { x: e.clientX, y: e.clientY, duration: 0.1, ease: 'power2.out' });
    if (glow) gsap.to(glow, { x: e.clientX, y: e.clientY, duration: 0.7, ease: 'power2.out' });
  });
  document.querySelectorAll('a, button, .service-card, .skill-card, .project-card, input, textarea').forEach(el => {
    el.addEventListener('mouseenter', () => dot?.classList.add('hover'));
    el.addEventListener('mouseleave', () => dot?.classList.remove('hover'));
  });
}

// ------- Hamburger Nav -------
(function () {
  const btn     = document.getElementById('hamburger');
  const links   = document.getElementById('nav-links');
  if (!btn || !links) return;
  const overlay = document.createElement('div');
  overlay.className = 'nav-overlay';
  document.body.appendChild(overlay);

  const open  = () => { links.classList.add('is-open'); btn.classList.add('is-open'); overlay.classList.add('is-visible'); btn.setAttribute('aria-expanded','true'); document.body.style.overflow='hidden'; };
  const close = () => { links.classList.remove('is-open'); btn.classList.remove('is-open'); overlay.classList.remove('is-visible'); btn.setAttribute('aria-expanded','false'); document.body.style.overflow=''; };

  btn.addEventListener('click', () => links.classList.contains('is-open') ? close() : open());
  overlay.addEventListener('click', close);
  links.querySelectorAll('a').forEach(a => a.addEventListener('click', close));
  document.addEventListener('keydown', e => e.key === 'Escape' && close());
})();

// ------- Scroll Progress -------
(function () {
  const bar = document.getElementById('scroll-progress');
  if (!bar) return;
  const update = () => {
    const d = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.width = (d > 0 ? (window.scrollY / d) * 100 : 0) + '%';
  };
  window.addEventListener('scroll', update, { passive: true });
  update();
})();

// ------- Nav scrolled state -------
(function () {
  const nav = document.getElementById('nav-header');
  if (!nav) return;
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 60);
  }, { passive: true });
})();

// ------- Active Nav Link -------
(function () {
  const sections = document.querySelectorAll('section[id]');
  const links    = document.querySelectorAll('.nav-link');
  if (!sections.length) return;
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const id = e.target.id;
        links.forEach(l => l.classList.toggle('is-active', l.getAttribute('href') === '#' + id));
      }
    });
  }, { rootMargin: '-40% 0px -55% 0px' });
  sections.forEach(s => obs.observe(s));
})();

// ------- Back to Top -------
(function () {
  const btn = document.getElementById('back-to-top');
  if (!btn) return;
  window.addEventListener('scroll', () => btn.classList.toggle('is-visible', window.scrollY > 600), { passive: true });
  btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
})();

// ------- Scroll Reveal (IntersectionObserver — works on mobile too) -------
(function () {
  const els = document.querySelectorAll('.reveal-up, .reveal-fade');
  const obs = new IntersectionObserver(entries => {
    entries.forEach((e, i) => {
      if (e.isIntersecting) {
        setTimeout(() => e.target.classList.add('visible'), i * 80);
        obs.unobserve(e.target);
      }
    });
  }, { threshold: 0.1 });
  els.forEach(el => obs.observe(el));
})();

// ------- Skill Bars -------
(function () {
  const rows = document.querySelectorAll('.skill-row');
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const fill = e.target.querySelector('.skill-fill');
        if (fill) fill.style.width = (e.target.dataset.level || 80) + '%';
        obs.unobserve(e.target);
      }
    });
  }, { threshold: 0.3 });
  rows.forEach(r => obs.observe(r));
})();

// ------- GSAP enhanced animations (desktop) -------
if (useMotion) {
  // Project cards tilt
  document.querySelectorAll('.project-card, .service-card').forEach(card => {
    card.addEventListener('mousemove', e => {
      const r = card.getBoundingClientRect();
      const x = e.clientX - r.left, y = e.clientY - r.top;
      const rx = ((y - r.height/2) / r.height) * -6;
      const ry = ((x - r.width/2)  / r.width)  *  6;
      card.style.transform = `perspective(800px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-8px)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
    });
  });
}

// ------- Contact Form -------
(function () {
  const form   = document.getElementById('contact-form');
  const status = document.getElementById('form-status');
  if (!form || !status) return;

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    btn.textContent = 'Sending...';
    btn.disabled = true;
    try {
      const res = await fetch(form.action, { method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' } });
      if (res.ok) {
        status.textContent = "Message sent! I'll reply within 24 hours.";
        status.style.color = '#7c9e9a';
        form.reset();
      } else { throw new Error(); }
    } catch {
      status.textContent = 'Something went wrong. Email me directly at biswasmail631@gmail.com';
      status.style.color = '#c97070';
    }
    status.classList.remove('hidden');
    btn.textContent = 'Send Message';
    btn.disabled = false;
    setTimeout(() => status.classList.add('hidden'), 8000);
  });
})();
