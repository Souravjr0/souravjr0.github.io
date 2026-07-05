// ============================================================
//  SOURAV BISWAS PORTFOLIO — script.js (Awwwards v2)
//  Production-grade: 60fps, zero console errors
// ============================================================

gsap.registerPlugin(ScrollTrigger);

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const isDesktop = window.matchMedia('(hover: hover) and (pointer: fine)').matches && window.innerWidth >= 1024;
const useMotion = !prefersReducedMotion;

// ============================================================
//  LOADER — Counting animation with progress bar
// ============================================================
(function () {
  const loader = document.getElementById('loader');
  const counter = document.getElementById('loader-counter');
  const fill = document.getElementById('loader-fill');
  if (!loader) return;

  const runLoader = () => {
    const obj = { val: 0 };
    const tl = gsap.timeline();

    tl.to(obj, {
      val: 100,
      duration: 1.4,
      ease: 'power2.inOut',
      onUpdate: () => {
        const v = Math.round(obj.val);
        if (counter) counter.textContent = v;
        if (fill) fill.style.width = v + '%';
      }
    })
    .to(loader, {
      yPercent: -100,
      duration: 0.9,
      ease: 'power4.inOut',
      delay: 0.15
    })
    .add(() => {
      document.body.classList.remove('loading');
      loader.remove();
      // Trigger hero entrance
      heroEntrance();
    }, '-=0.3');
  };

  if (document.readyState === 'complete') {
    runLoader();
  } else {
    window.addEventListener('load', runLoader);
  }
})();

// ============================================================
//  HERO ENTRANCE — Staggered reveal
// ============================================================
function heroEntrance() {
  if (!useMotion) {
    // No animation — just show everything
    document.querySelectorAll('.hero-badge-row, .hero-roles, .hero-statement, .hero-actions, .hero-scroll')
      .forEach(el => { el.style.opacity = 1; el.style.transform = 'none'; });
    return;
  }

  const tl = gsap.timeline({ defaults: { ease: 'power4.out' } });

  tl.from('.line-inner', {
    yPercent: 110,
    duration: 1.2,
    stagger: 0.12,
  })
  .from('.hero-badge-row', { opacity: 0, y: 20, duration: 0.8 }, '-=0.6')
  .from('.hero-roles', { opacity: 0, y: 20, duration: 0.8 }, '-=0.5')
  .from('.hero-statement', { opacity: 0, y: 20, duration: 0.8 }, '-=0.5')
  .from('.hero-actions', { opacity: 0, y: 20, duration: 0.8 }, '-=0.4')
  .from('.hero-scroll', { opacity: 0, y: 10, duration: 0.6 }, '-=0.3');
}

// ============================================================
//  CUSTOM CURSOR (Desktop only)
// ============================================================
if (isDesktop && useMotion) {
  const dot = document.getElementById('cursor-dot');
  const glow = document.getElementById('cursor-glow');
  let cursorReady = false;

  // Use quickTo for 60fps cursor tracking
  const xDot = gsap.quickTo(dot, 'x', { duration: 0.15, ease: 'power3.out' });
  const yDot = gsap.quickTo(dot, 'y', { duration: 0.15, ease: 'power3.out' });
  const xGlow = gsap.quickTo(glow, 'x', { duration: 0.6, ease: 'power3.out' });
  const yGlow = gsap.quickTo(glow, 'y', { duration: 0.6, ease: 'power3.out' });

  window.addEventListener('mousemove', e => {
    if (!cursorReady) {
      dot?.classList.add('visible');
      glow?.classList.add('visible');
      cursorReady = true;
    }
    xDot(e.clientX);
    yDot(e.clientY);
    xGlow(e.clientX);
    yGlow(e.clientY);
  });

  // Hover state on interactive elements
  document.querySelectorAll('a, button, .service-card, .skill-card, .project-card, input, textarea').forEach(el => {
    el.addEventListener('mouseenter', () => dot?.classList.add('hover'));
    el.addEventListener('mouseleave', () => dot?.classList.remove('hover'));
  });
} else {
  // Remove cursor elements on non-desktop
  document.getElementById('cursor-dot')?.remove();
  document.getElementById('cursor-glow')?.remove();
}

// ============================================================
//  HAMBURGER NAV
// ============================================================
(function () {
  const btn = document.getElementById('hamburger');
  const links = document.getElementById('nav-links');
  if (!btn || !links) return;

  const overlay = document.createElement('div');
  overlay.className = 'nav-overlay';
  document.body.appendChild(overlay);

  const open = () => {
    links.classList.add('is-open');
    btn.classList.add('is-open');
    overlay.classList.add('is-visible');
    btn.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
  };
  const close = () => {
    links.classList.remove('is-open');
    btn.classList.remove('is-open');
    overlay.classList.remove('is-visible');
    btn.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  };

  btn.addEventListener('click', () => links.classList.contains('is-open') ? close() : open());
  overlay.addEventListener('click', close);
  links.querySelectorAll('a').forEach(a => a.addEventListener('click', close));
  document.addEventListener('keydown', e => e.key === 'Escape' && close());
})();

// ============================================================
//  SCROLL PROGRESS
// ============================================================
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

// ============================================================
//  NAV SCROLLED STATE
// ============================================================
(function () {
  const nav = document.getElementById('nav-header');
  if (!nav) return;
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 60);
  }, { passive: true });
})();

// ============================================================
//  ACTIVE NAV LINK
// ============================================================
(function () {
  const sections = document.querySelectorAll('section[id]');
  const links = document.querySelectorAll('.nav-link');
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

// ============================================================
//  BACK TO TOP
// ============================================================
(function () {
  const btn = document.getElementById('back-to-top');
  if (!btn) return;
  window.addEventListener('scroll', () => btn.classList.toggle('is-visible', window.scrollY > 600), { passive: true });
  btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
})();

// ============================================================
//  SCROLL REVEAL — IntersectionObserver (works everywhere)
// ============================================================
(function () {
  const els = document.querySelectorAll('.reveal-up');
  if (!els.length) return;

  if (!useMotion) {
    // Skip animation, show everything
    els.forEach(el => {
      el.classList.add('visible');
      el.style.opacity = 1;
      el.style.transform = 'none';
    });
    return;
  }

  const obs = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        // Add stagger delay based on sibling index
        const parent = entry.target.parentElement;
        const siblings = parent ? Array.from(parent.querySelectorAll('.reveal-up')) : [];
        const idx = siblings.indexOf(entry.target);
        const delay = idx >= 0 ? idx * 0.08 : 0;

        entry.target.style.transitionDelay = delay + 's';
        entry.target.classList.add('visible');
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

  els.forEach(el => obs.observe(el));
})();

// ============================================================
//  SKILL BARS — Animated fill on scroll
// ============================================================
(function () {
  const rows = document.querySelectorAll('.skill-row');
  if (!rows.length) return;
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

// ============================================================
//  COUNTER ANIMATION — Animated numbers in About stats
// ============================================================
(function () {
  const nums = document.querySelectorAll('.stat-num[data-count]');
  if (!nums.length) return;

  const obs = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const target = parseInt(el.dataset.count, 10);
        const obj = { val: 0 };

        gsap.to(obj, {
          val: target,
          duration: 2,
          ease: 'power2.out',
          onUpdate: () => { el.textContent = Math.round(obj.val); }
        });

        obs.unobserve(el);
      }
    });
  }, { threshold: 0.5 });

  nums.forEach(n => obs.observe(n));
})();

// ============================================================
//  SERVICE CARD 3D TILT (Desktop only)
// ============================================================
if (isDesktop && useMotion) {
  document.querySelectorAll('.service-card').forEach(card => {
    card.addEventListener('mousemove', e => {
      const r = card.getBoundingClientRect();
      const x = e.clientX - r.left, y = e.clientY - r.top;
      const rx = ((y - r.height / 2) / r.height) * -8;
      const ry = ((x - r.width / 2) / r.width) * 8;
      gsap.to(card, {
        rotateX: rx, rotateY: ry,
        transformPerspective: 800,
        duration: 0.4, ease: 'power2.out'
      });
    });
    card.addEventListener('mouseleave', () => {
      gsap.to(card, {
        rotateX: 0, rotateY: 0,
        duration: 0.7, ease: 'elastic.out(1, 0.5)'
      });
    });
  });
}

// ============================================================
//  MAGNETIC BUTTONS (Desktop only)
// ============================================================
if (isDesktop && useMotion) {
  document.querySelectorAll('.btn, .nav-logo').forEach(btn => {
    let rect;
    btn.addEventListener('mouseenter', () => {
      rect = btn.getBoundingClientRect();
    });
    btn.addEventListener('mousemove', e => {
      if (!rect) return;
      const x = (e.clientX - rect.left - rect.width / 2) * 0.3;
      const y = (e.clientY - rect.top - rect.height / 2) * 0.3;
      gsap.to(btn, { x, y, duration: 0.4, ease: 'power2.out' });
    });
    btn.addEventListener('mouseleave', () => {
      rect = null;
      gsap.to(btn, { x: 0, y: 0, duration: 0.7, ease: 'elastic.out(1, 0.3)' });
    });
  });
}

// ============================================================
//  PROJECT STACKING SCROLL EFFECT
// ============================================================
window.addEventListener('load', () => {
  if (!useMotion) return;
  const cards = gsap.utils.toArray('.project-card');
  if (!cards.length) return;

  cards.forEach((card, i) => {
    if (i === cards.length - 1) return;
    gsap.to(card, {
      scale: 0.93,
      opacity: 0.35,
      ease: 'none',
      scrollTrigger: {
        trigger: cards[i + 1],
        start: 'top 85%',
        end: 'top 15%',
        scrub: true,
      }
    });
  });
});

// ============================================================
//  TEXT SCRAMBLE — Hero statement
// ============================================================
class TextScramble {
  constructor(el) {
    this.el = el;
    this.chars = '!<>-_\\/[]{}—=+*^?#________';
    this.update = this.update.bind(this);
  }
  setText(newText) {
    const oldText = this.el.innerText;
    const length = Math.max(oldText.length, newText.length);
    const promise = new Promise(resolve => this.resolve = resolve);
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

// Apply text scramble to hero statement after loader completes
const statementEl = document.getElementById('hero-statement');
if (statementEl && useMotion) {
  const originalHTML = statementEl.innerHTML;
  const originalText = statementEl.innerText;

  // Wait for loader to finish + hero entrance
  setTimeout(() => {
    statementEl.innerHTML = '';
    const fx = new TextScramble(statementEl);
    fx.setText(originalText).then(() => {
      statementEl.innerHTML = originalHTML;
    });
  }, 2800);
}

// ============================================================
//  CONTACT FORM
// ============================================================
(function () {
  const form = document.getElementById('contact-form');
  const status = document.getElementById('form-status');
  if (!form || !status) return;

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    btn.textContent = 'Sending...';
    btn.disabled = true;

    try {
      const res = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { Accept: 'application/json' }
      });
      if (res.ok) {
        status.textContent = "Message sent! I'll reply within 24 hours.";
        status.style.color = 'var(--cyan)';
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

// ============================================================
//  THREE.JS — Living Data Organism (Particle Sphere)
// ============================================================
if (isDesktop && !prefersReducedMotion && typeof THREE !== 'undefined') {
  const initThreeJS = () => {
    const canvas = document.getElementById('hero-canvas');
    if (!canvas) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });

    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));

    const mainGroup = new THREE.Group();
    scene.add(mainGroup);

    // --- Simple 3D noise function (no imports needed) ---
    const noise3D = (x, y, z, t) => {
      return Math.sin(x * 1.3 + t * 0.7) * Math.cos(y * 1.1 + t * 0.5) *
             Math.sin(z * 0.9 + t * 0.3) +
             Math.sin(x * 0.8 + z * 1.2 + t * 0.4) * 0.5;
    };

    // --- Hub Particles (300 nodes on a sphere) ---
    const hubCount = 300;
    const hubGeometry = new THREE.BufferGeometry();
    const hubPositions = new Float32Array(hubCount * 3);
    const hubColors = new Float32Array(hubCount * 3);

    // Fibonacci sphere distribution for even spacing
    const goldenAngle = Math.PI * (3 - Math.sqrt(5));
    const sphereRadius = 2.5;

    for (let i = 0; i < hubCount; i++) {
      const y = 1 - (i / (hubCount - 1)) * 2; // y goes from 1 to -1
      const radiusAtY = Math.sqrt(1 - y * y);
      const theta = goldenAngle * i;

      const r = sphereRadius + (Math.random() - 0.5) * 0.3;
      hubPositions[i * 3] = Math.cos(theta) * radiusAtY * r;
      hubPositions[i * 3 + 1] = y * r;
      hubPositions[i * 3 + 2] = Math.sin(theta) * radiusAtY * r;

      // Color gradient: orange at bottom, transitioning to cyan at top
      const t = (y + 1) / 2; // 0 (bottom) to 1 (top)
      hubColors[i * 3] = 1.0 - t * 0.6;       // R: 1.0 -> 0.4
      hubColors[i * 3 + 1] = 0.34 + t * 0.4;  // G: 0.34 -> 0.74
      hubColors[i * 3 + 2] = 0.14 + t * 0.83;  // B: 0.14 -> 0.97
    }

    hubGeometry.setAttribute('position', new THREE.BufferAttribute(hubPositions, 3));
    hubGeometry.setAttribute('color', new THREE.BufferAttribute(hubColors, 3));

    const origHubPositions = hubPositions.slice();

    const hubMaterial = new THREE.PointsMaterial({
      size: 0.04,
      vertexColors: true,
      transparent: true,
      opacity: 0.9,
      blending: THREE.AdditiveBlending
    });

    const hubs = new THREE.Points(hubGeometry, hubMaterial);
    mainGroup.add(hubs);

    // --- Connection Lines ---
    const maxConnections = 600;
    const lineGeometry = new THREE.BufferGeometry();
    const linePositions = new Float32Array(maxConnections * 6);
    const lineColors = new Float32Array(maxConnections * 6);

    lineGeometry.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
    lineGeometry.setAttribute('color', new THREE.BufferAttribute(lineColors, 3));

    const lineMaterial = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.18,
      blending: THREE.AdditiveBlending
    });

    const networkLines = new THREE.LineSegments(lineGeometry, lineMaterial);
    mainGroup.add(networkLines);

    // --- Ambient Dust Cloud (1200 particles) ---
    const dustCount = 1200;
    const dustGeometry = new THREE.BufferGeometry();
    const dustPositions = new Float32Array(dustCount * 3);

    for (let i = 0; i < dustCount; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2 * Math.PI;
      const phi = Math.acos(2 * v - 1);
      const r = 3.5 + Math.random() * 5;

      dustPositions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      dustPositions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      dustPositions[i * 3 + 2] = r * Math.cos(phi);
    }

    dustGeometry.setAttribute('position', new THREE.BufferAttribute(dustPositions, 3));
    const dustMaterial = new THREE.PointsMaterial({
      size: 0.015,
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.4,
      blending: THREE.AdditiveBlending
    });

    const dustParticles = new THREE.Points(dustGeometry, dustMaterial);
    mainGroup.add(dustParticles);

    // --- Inner Glow Sphere ---
    const glowGeometry = new THREE.SphereGeometry(2.2, 32, 32);
    const glowMaterial = new THREE.MeshBasicMaterial({
      color: 0xff5722,
      transparent: true,
      opacity: 0.015,
      blending: THREE.AdditiveBlending
    });
    const glowSphere = new THREE.Mesh(glowGeometry, glowMaterial);
    mainGroup.add(glowSphere);

    // Camera position
    camera.position.z = 7.5;

    // Responsive positioning
    const handleResize = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);

      if (w >= 1024) {
        mainGroup.position.set(2.2, 0.1, 0);
      } else {
        mainGroup.position.set(0, 0, -1);
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);

    // Mouse tracking
    let targetMouseX = 0, targetMouseY = 0;
    let mouseX = 0, mouseY = 0;

    document.addEventListener('mousemove', e => {
      targetMouseX = (e.clientX - window.innerWidth / 2) / (window.innerWidth / 2);
      targetMouseY = (e.clientY - window.innerHeight / 2) / (window.innerHeight / 2);
    });

    // GSAP scroll-linked camera zoom
    gsap.to(camera.position, {
      z: 5,
      scrollTrigger: {
        trigger: '#about',
        start: 'top bottom',
        end: 'bottom top',
        scrub: 1
      }
    });

    // Scroll-linked rotation
    gsap.to(mainGroup.rotation, {
      y: Math.PI * 2,
      scrollTrigger: {
        trigger: 'body',
        start: 'top top',
        end: 'bottom bottom',
        scrub: 1
      }
    });

    const clock = new THREE.Clock();

    const animate = () => {
      requestAnimationFrame(animate);

      // Performance: skip rendering if scrolled past hero
      if (window.scrollY > window.innerHeight * 1.5) return;

      const t = clock.getElapsedTime();

      // Smooth mouse interpolation
      mouseX += (targetMouseX - mouseX) * 0.06;
      mouseY += (targetMouseY - mouseY) * 0.06;

      // Organic heartbeat pulse
      const heartbeat = 1.0 + Math.sin(t * 1.5) * Math.cos(t * 0.4) * 0.06;

      // Animate hub particles with noise displacement
      const pos = hubGeometry.attributes.position.array;
      for (let i = 0; i < hubCount; i++) {
        const idx = i * 3;
        const ox = origHubPositions[idx];
        const oy = origHubPositions[idx + 1];
        const oz = origHubPositions[idx + 2];

        // Noise-based displacement
        const noiseVal = noise3D(ox * 0.5, oy * 0.5, oz * 0.5, t * 0.8) * 0.12;

        pos[idx] = ox * heartbeat + ox * noiseVal;
        pos[idx + 1] = oy * heartbeat + oy * noiseVal;
        pos[idx + 2] = oz * heartbeat + oz * noiseVal;

        // Mouse gravity attraction
        const dx = pos[idx] + mainGroup.position.x - (mouseX * 4);
        const dy = pos[idx + 1] + mainGroup.position.y - (-mouseY * 3);
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 1.6) {
          const force = (1.6 - dist) * 0.12;
          pos[idx] -= dx * force;
          pos[idx + 1] -= dy * force;
        }
      }
      hubGeometry.attributes.position.needsUpdate = true;

      // --- Dynamic connection lines ---
      let lineIndex = 0;
      const lPos = networkLines.geometry.attributes.position.array;
      const lCol = networkLines.geometry.attributes.color.array;
      const limitSq = 1.4 * 1.4;
      const limit = 1.4;

      for (let i = 0; i < hubCount && lineIndex < maxConnections; i++) {
        for (let j = i + 1; j < hubCount && lineIndex < maxConnections; j++) {
          const ax = i * 3, bx = j * 3;
          const dx = pos[ax] - pos[bx];
          const dy = pos[ax + 1] - pos[bx + 1];
          const dz = pos[ax + 2] - pos[bx + 2];
          const distSq = dx * dx + dy * dy + dz * dz;

          if (distSq < limitSq) {
            const d = Math.sqrt(distSq);
            const alpha = 1.0 - (d / limit);
            const li = lineIndex * 6;

            lPos[li] = pos[ax]; lPos[li + 1] = pos[ax + 1]; lPos[li + 2] = pos[ax + 2];
            lPos[li + 3] = pos[bx]; lPos[li + 4] = pos[bx + 1]; lPos[li + 5] = pos[bx + 2];

            // Gradient: orange (A) → cyan (B)
            lCol[li] = 1.0 * alpha; lCol[li + 1] = 0.34 * alpha; lCol[li + 2] = 0.14 * alpha;
            lCol[li + 3] = 0.22 * alpha; lCol[li + 4] = 0.74 * alpha; lCol[li + 5] = 0.97 * alpha;

            lineIndex++;
          }
        }
      }

      // Clear unused line positions
      for (let i = lineIndex; i < maxConnections; i++) {
        const li = i * 6;
        lPos[li] = lPos[li + 1] = lPos[li + 2] = 0;
        lPos[li + 3] = lPos[li + 4] = lPos[li + 5] = 0;
      }

      networkLines.geometry.attributes.position.needsUpdate = true;
      networkLines.geometry.attributes.color.needsUpdate = true;

      // Dust cloud gentle spin
      dustParticles.rotation.y = t * 0.012;
      dustParticles.rotation.x = t * 0.006;

      // Mouse-influence tilt on main group
      mainGroup.rotation.x = mouseY * 0.1;
      mainGroup.rotation.y += 0.002;

      // Glow sphere pulse
      glowSphere.scale.setScalar(heartbeat * 1.1);

      renderer.render(scene, camera);
    };

    animate();
  };

  initThreeJS();
}
