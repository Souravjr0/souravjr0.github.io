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
  document.querySelectorAll('.service-card').forEach(card => {
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


// ------- Three.js Interactive TorusKnot + Dust -------
if (isDesktop && !prefersReducedMotion && typeof THREE !== 'undefined') {
  const initThreeJS = () => {
    const canvas = document.getElementById('hero-canvas');
    if (!canvas) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));

    // Abstract Core
    const geometry = new THREE.TorusKnotGeometry(1.8, 0.6, 64, 12);
    const mat = new THREE.MeshBasicMaterial({ 
        color: 0xff5722, 
        wireframe: true, 
        transparent: true, 
        opacity: 0.18 
    });
    const coreMesh = new THREE.Mesh(geometry, mat);
    
    const innerGeom = new THREE.TorusKnotGeometry(1.75, 0.55, 64, 12);
    const innerMat = new THREE.MeshBasicMaterial({ color: 0x1e2128 });
    const innerMesh = new THREE.Mesh(innerGeom, innerMat);
    coreMesh.add(innerMesh);
    
    // Add particle dust
    const dustGeom = new THREE.BufferGeometry();
    const dustCount = 150;
    const dustPos = new Float32Array(dustCount * 3);
    for(let i=0; i<dustCount*3; i++){
        dustPos[i] = (Math.random() - 0.5) * 25;
    }
    dustGeom.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
    const dustMat = new THREE.PointsMaterial({ size: 0.04, color: 0x38bdf8, transparent: true, opacity: 0.5 });
    const dustMesh = new THREE.Points(dustGeom, dustMat);

    scene.add(coreMesh);
    scene.add(dustMesh);

    camera.position.z = 7;
    // Move slightly right and up so it balances the text
    coreMesh.position.x = 2;
    coreMesh.position.y = 0;

    let mouseX = 0;
    let mouseY = 0;
    const windowHalfX = window.innerWidth / 2;
    const windowHalfY = window.innerHeight / 2;

    document.addEventListener('mousemove', (event) => {
        mouseX = (event.clientX - windowHalfX);
        mouseY = (event.clientY - windowHalfY);
    });

    const clock = new THREE.Clock();

    const animate = () => {
        requestAnimationFrame(animate);
        // Pause rendering if scrolled past hero section to save CPU/GPU
        if (window.scrollY > window.innerHeight + 50) return;

        const t = clock.getElapsedTime();

        const targetX = mouseX * 0.001;
        const targetY = mouseY * 0.001;

        coreMesh.rotation.y += 0.05 * (targetX - coreMesh.rotation.y);
        coreMesh.rotation.x += 0.05 * (targetY - coreMesh.rotation.x);
        coreMesh.rotation.z += 0.001;
        
        dustMesh.rotation.y = t * 0.03;
        dustMesh.rotation.x = t * 0.01;

        renderer.render(scene, camera);
    };
    animate();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
  };
  initThreeJS();
}

// ------- Magnetic Buttons -------
if (useMotion) {
  document.querySelectorAll('.btn, .nav-logo').forEach(btn => {
    let rect;
    btn.addEventListener('mouseenter', () => {
      // Cache the bounding rect once on enter to avoid heavy layout recalculations
      rect = btn.getBoundingClientRect();
    });
    btn.addEventListener('mousemove', (e) => {
      if (!rect) return;
      const x = (e.clientX - rect.left - rect.width/2) * 0.3;
      const y = (e.clientY - rect.top - rect.height/2) * 0.3;
      gsap.to(btn, { x, y, duration: 0.4, ease: 'power2.out' });
    });
    btn.addEventListener('mouseleave', () => {
      rect = null;
      gsap.to(btn, { x: 0, y: 0, duration: 0.7, ease: 'elastic.out(1, 0.3)' });
    });
  });
}

// ------- Project Stacking Effect -------
window.addEventListener('load', () => {
  if (useMotion) {
    const cards = gsap.utils.toArray('.project-card');
    cards.forEach((card, i) => {
      if (i === cards.length - 1) return;
      gsap.to(card, {
        scale: 0.94,
        opacity: 0.4,
        ease: 'none',
        scrollTrigger: {
          trigger: cards[i + 1],
          start: 'top 85%',
          end: 'top 20%',
          scrub: true,
        }
      });
    });
  }
});

// ------- Text Scramble -------
class TextScramble {
  constructor(el) {
    this.el = el;
    this.chars = '!<>-_\\/[]{}—=+*^?#________';
    this.update = this.update.bind(this);
  }
  setText(newText) {
    const oldText = this.el.innerText;
    const length = Math.max(oldText.length, newText.length);
    const promise = new Promise((resolve) => this.resolve = resolve);
    this.queue = [];
    for (let i = 0; i < length; i++) {
      const from = oldText[i] || '';
      const to = newText[i] || '';
      const start = Math.floor(Math.random() * 40);
      const end = start + Math.floor(Math.random() * 40);
      this.queue.push({ from, to, start, end });
    }
    cancelAnimationFrame(this.frameRequest);
    this.frame = 0;
    this.update();
    return promise;
  }
  update() {
    let output = '';
    let complete = 0;
    for (let i = 0, n = this.queue.length; i < n; i++) {
      let { from, to, start, end, char } = this.queue[i];
      if (this.frame >= end) {
        complete++;
        output += to;
      } else if (this.frame >= start) {
        if (!char || Math.random() < 0.28) {
          char = this.randomChar();
          this.queue[i].char = char;
        }
        output += `<span class="scramble-char">${char}</span>`;
      } else {
        output += from;
      }
    }
    this.el.innerHTML = output;
    if (complete === this.queue.length) {
      this.resolve();
    } else {
      this.frameRequest = requestAnimationFrame(this.update);
      this.frame++;
    }
  }
  randomChar() {
    return this.chars[Math.floor(Math.random() * this.chars.length)];
  }
}

const statementEl = document.querySelector('.hero-statement');
if (statementEl && useMotion) {
    const originalHTML = statementEl.innerHTML;
    const originalText = statementEl.innerText;
    statementEl.innerHTML = '';
    const fx = new TextScramble(statementEl);
    
    setTimeout(() => {
        fx.setText(originalText).then(() => {
            statementEl.innerHTML = originalHTML; // restore br tags
        });
    }, 2400);
}
