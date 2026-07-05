// ============================================================
//  SOURAV BISWAS — Premium Portfolio JS
//  Gold + Cream palette | 60fps | Zero errors
// ============================================================

gsap.registerPlugin(ScrollTrigger);

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const isDesktop = window.matchMedia('(hover: hover) and (pointer: fine)').matches && window.innerWidth >= 1024;
const useMotion = !prefersReducedMotion;

// ============================================================
//  LOADER
// ============================================================
(function () {
  const loader = document.getElementById('loader');
  const counter = document.getElementById('loader-counter');
  const fill = document.getElementById('loader-fill');
  if (!loader) return;

  const run = () => {
    const obj = { val: 0 };
    const tl = gsap.timeline();
    tl.to(obj, {
      val: 100, duration: 1.6, ease: 'power2.inOut',
      onUpdate: () => {
        const v = Math.round(obj.val);
        if (counter) counter.textContent = v;
        if (fill) fill.style.width = v + '%';
      }
    })
    .to(loader, { yPercent: -100, duration: 1, ease: 'power4.inOut', delay: 0.2 })
    .add(() => {
      document.body.classList.remove('loading');
      loader.remove();
      heroEntrance();
    }, '-=0.4');
  };

  if (document.readyState === 'complete') run();
  else window.addEventListener('load', run);
})();

// ============================================================
//  HERO ENTRANCE
// ============================================================
function heroEntrance() {
  if (!useMotion) {
    document.querySelectorAll('.hero-eyebrow, .hero-desc, .hero-actions, .hero-scroll-cue')
      .forEach(el => { el.style.opacity = 1; el.style.transform = 'none'; });
    return;
  }
  const tl = gsap.timeline({ defaults: { ease: 'power4.out' } });
  tl.from('.line-inner', { yPercent: 120, duration: 1.3, stagger: 0.12 })
    .from('.hero-eyebrow', { opacity: 0, y: 20, duration: 0.8 }, '-=0.7')
    .from('.hero-desc', { opacity: 0, y: 20, duration: 0.8 }, '-=0.5')
    .from('.hero-actions', { opacity: 0, y: 20, duration: 0.8 }, '-=0.4')
    .from('.hero-scroll-cue', { opacity: 0, duration: 0.6 }, '-=0.3');
}

// ============================================================
//  CURSOR — Dot + Ring (GSAP quickTo)
// ============================================================
if (isDesktop && useMotion) {
  const dot = document.getElementById('cursor-dot');
  const ring = document.getElementById('cursor-ring');
  let ready = false;

  const xD = gsap.quickTo(dot, 'x', { duration: 0.12, ease: 'power3.out' });
  const yD = gsap.quickTo(dot, 'y', { duration: 0.12, ease: 'power3.out' });
  const xR = gsap.quickTo(ring, 'x', { duration: 0.5, ease: 'power3.out' });
  const yR = gsap.quickTo(ring, 'y', { duration: 0.5, ease: 'power3.out' });

  window.addEventListener('mousemove', e => {
    if (!ready) { dot?.classList.add('visible'); ring?.classList.add('visible'); ready = true; }
    xD(e.clientX); yD(e.clientY);
    xR(e.clientX); yR(e.clientY);
  });

  document.querySelectorAll('a, button, .service-item, .skill-card, .project-card, input, textarea').forEach(el => {
    el.addEventListener('mouseenter', () => { dot?.classList.add('hover'); ring?.classList.add('hover'); });
    el.addEventListener('mouseleave', () => { dot?.classList.remove('hover'); ring?.classList.remove('hover'); });
  });
} else {
  document.getElementById('cursor-dot')?.remove();
  document.getElementById('cursor-ring')?.remove();
}

// ============================================================
//  NAV
// ============================================================
(function () {
  const btn = document.getElementById('hamburger');
  const links = document.getElementById('nav-links');
  if (!btn || !links) return;
  const overlay = document.createElement('div');
  overlay.className = 'nav-overlay';
  document.body.appendChild(overlay);

  const open = () => { links.classList.add('is-open'); btn.classList.add('is-open'); overlay.classList.add('is-visible'); btn.setAttribute('aria-expanded','true'); document.body.style.overflow='hidden'; };
  const close = () => { links.classList.remove('is-open'); btn.classList.remove('is-open'); overlay.classList.remove('is-visible'); btn.setAttribute('aria-expanded','false'); document.body.style.overflow=''; };

  btn.addEventListener('click', () => links.classList.contains('is-open') ? close() : open());
  overlay.addEventListener('click', close);
  links.querySelectorAll('a').forEach(a => a.addEventListener('click', close));
  document.addEventListener('keydown', e => e.key === 'Escape' && close());
})();

// Scroll progress
(function () {
  const bar = document.getElementById('scroll-progress');
  if (!bar) return;
  window.addEventListener('scroll', () => {
    const d = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.width = (d > 0 ? (window.scrollY / d) * 100 : 0) + '%';
  }, { passive: true });
})();

// Nav scrolled
(function () {
  const nav = document.getElementById('nav-header');
  if (!nav) return;
  window.addEventListener('scroll', () => nav.classList.toggle('scrolled', window.scrollY > 60), { passive: true });
})();

// Active nav link
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

// Back to top
(function () {
  const btn = document.getElementById('back-to-top');
  if (!btn) return;
  window.addEventListener('scroll', () => btn.classList.toggle('is-visible', window.scrollY > 600), { passive: true });
  btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
})();

// ============================================================
//  SCROLL REVEAL
// ============================================================
(function () {
  const els = document.querySelectorAll('.reveal-up');
  if (!els.length) return;
  if (!useMotion) {
    els.forEach(el => { el.classList.add('visible'); el.style.opacity = 1; el.style.transform = 'none'; });
    return;
  }
  const obs = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const parent = entry.target.parentElement;
        const siblings = parent ? Array.from(parent.querySelectorAll('.reveal-up')) : [];
        const idx = siblings.indexOf(entry.target);
        entry.target.style.transitionDelay = (idx >= 0 ? idx * 0.08 : 0) + 's';
        entry.target.classList.add('visible');
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });
  els.forEach(el => obs.observe(el));
})();

// ============================================================
//  SKILL BARS
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
//  COUNTER ANIMATION
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
          val: target, duration: 2.2, ease: 'power2.out',
          onUpdate: () => { el.textContent = Math.round(obj.val); }
        });
        obs.unobserve(el);
      }
    });
  }, { threshold: 0.5 });
  nums.forEach(n => obs.observe(n));
})();

// ============================================================
//  MAGNETIC BUTTONS
// ============================================================
if (isDesktop && useMotion) {
  document.querySelectorAll('.btn, .nav-logo').forEach(btn => {
    let rect;
    btn.addEventListener('mouseenter', () => { rect = btn.getBoundingClientRect(); });
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
//  HORIZONTAL SCROLL PROJECTS
// ============================================================
window.addEventListener('load', () => {
  if (!useMotion) return;
  const track = document.getElementById('projects-track');
  if (!track) return;

  const getScrollAmount = () => {
    return -(track.scrollWidth - window.innerWidth);
  };

  gsap.to(track, {
    x: getScrollAmount,
    ease: 'none',
    scrollTrigger: {
      trigger: '.projects-section',
      start: 'top top',
      end: () => '+=' + (track.scrollWidth - window.innerWidth),
      scrub: 1,
      pin: true,
      invalidateOnRefresh: true,
      anticipatePin: 1,
    }
  });
});

// ============================================================
//  SERVICE ITEM HOVER EXPAND
// ============================================================
if (isDesktop && useMotion) {
  document.querySelectorAll('.service-item').forEach(item => {
    item.addEventListener('mouseenter', () => {
      gsap.to(item, { paddingLeft: '1.5rem', duration: 0.4, ease: 'power2.out' });
    });
    item.addEventListener('mouseleave', () => {
      gsap.to(item, { paddingLeft: '0rem', duration: 0.4, ease: 'power2.out' });
    });
  });
}

// ============================================================
//  TEXT SCRAMBLE
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
      if (this.frame >= end) { complete++; output += to; }
      else if (this.frame >= start) {
        if (!char || Math.random() < 0.28) { char = this.randomChar(); this.queue[i].char = char; }
        output += `<span class="scramble-char">${char}</span>`;
      } else { output += from; }
    }
    this.el.innerHTML = output;
    if (complete === this.queue.length) this.resolve();
    else { this.frameRequest = requestAnimationFrame(this.update); this.frame++; }
  }
  randomChar() { return this.chars[Math.floor(Math.random() * this.chars.length)]; }
}

const descEl = document.getElementById('hero-desc');
if (descEl && useMotion) {
  const origHTML = descEl.innerHTML;
  const origText = descEl.innerText;
  setTimeout(() => {
    descEl.innerHTML = '';
    const fx = new TextScramble(descEl);
    fx.setText(origText).then(() => { descEl.innerHTML = origHTML; });
  }, 3000);
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
    btn.textContent = 'Sending...'; btn.disabled = true;
    try {
      const res = await fetch(form.action, { method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' } });
      if (res.ok) { status.textContent = "Sent. I'll reply within 24 hours."; status.style.color = 'var(--gold)'; form.reset(); }
      else throw new Error();
    } catch { status.textContent = 'Error. Email me directly at biswasmail631@gmail.com'; status.style.color = '#c97070'; }
    status.classList.remove('hidden');
    btn.textContent = 'Send Message'; btn.disabled = false;
    setTimeout(() => status.classList.add('hidden'), 8000);
  });
})();

// ============================================================
//  THREE.JS — Gold Particle Sphere
// ============================================================
if (isDesktop && !prefersReducedMotion && typeof THREE !== 'undefined') {
  const canvas = document.getElementById('hero-canvas');
  if (canvas) {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));

    const group = new THREE.Group();
    scene.add(group);

    // Noise function
    const noise = (x, y, z, t) =>
      Math.sin(x * 1.3 + t * 0.7) * Math.cos(y * 1.1 + t * 0.5) *
      Math.sin(z * 0.9 + t * 0.3) + Math.sin(x * 0.8 + z * 1.2 + t * 0.4) * 0.5;

    // Hub particles — Fibonacci sphere
    const N = 280;
    const hubGeo = new THREE.BufferGeometry();
    const hubPos = new Float32Array(N * 3);
    const hubCol = new Float32Array(N * 3);
    const phi_g = Math.PI * (3 - Math.sqrt(5));
    const R = 2.6;

    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2;
      const rY = Math.sqrt(1 - y * y);
      const th = phi_g * i;
      const r = R + (Math.random() - 0.5) * 0.25;
      hubPos[i * 3] = Math.cos(th) * rY * r;
      hubPos[i * 3 + 1] = y * r;
      hubPos[i * 3 + 2] = Math.sin(th) * rY * r;

      // Gold gradient: warm gold → pale ivory
      const t = (y + 1) / 2;
      hubCol[i * 3] = 0.79 + t * 0.04;     // R
      hubCol[i * 3 + 1] = 0.66 + t * 0.15; // G
      hubCol[i * 3 + 2] = 0.43 + t * 0.35; // B
    }

    hubGeo.setAttribute('position', new THREE.BufferAttribute(hubPos, 3));
    hubGeo.setAttribute('color', new THREE.BufferAttribute(hubCol, 3));
    const origPos = hubPos.slice();

    const hubMat = new THREE.PointsMaterial({
      size: 0.04, vertexColors: true, transparent: true,
      opacity: 0.85, blending: THREE.AdditiveBlending
    });
    group.add(new THREE.Points(hubGeo, hubMat));

    // Connection lines
    const MAX_LINES = 550;
    const lineGeo = new THREE.BufferGeometry();
    const lP = new Float32Array(MAX_LINES * 6);
    const lC = new Float32Array(MAX_LINES * 6);
    lineGeo.setAttribute('position', new THREE.BufferAttribute(lP, 3));
    lineGeo.setAttribute('color', new THREE.BufferAttribute(lC, 3));
    const lineMat = new THREE.LineBasicMaterial({
      vertexColors: true, transparent: true, opacity: 0.14, blending: THREE.AdditiveBlending
    });
    const lines = new THREE.LineSegments(lineGeo, lineMat);
    group.add(lines);

    // Dust
    const D = 1000;
    const dGeo = new THREE.BufferGeometry();
    const dP = new Float32Array(D * 3);
    for (let i = 0; i < D; i++) {
      const u = Math.random(), v = Math.random();
      const th = u * 2 * Math.PI, ph = Math.acos(2 * v - 1);
      const r = 3.5 + Math.random() * 5;
      dP[i * 3] = r * Math.sin(ph) * Math.cos(th);
      dP[i * 3 + 1] = r * Math.sin(ph) * Math.sin(th);
      dP[i * 3 + 2] = r * Math.cos(ph);
    }
    dGeo.setAttribute('position', new THREE.BufferAttribute(dP, 3));
    const dust = new THREE.Points(dGeo, new THREE.PointsMaterial({
      size: 0.012, color: 0xd4cfc6, transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending
    }));
    group.add(dust);

    // Glow
    const glowMesh = new THREE.Mesh(
      new THREE.SphereGeometry(2.3, 32, 32),
      new THREE.MeshBasicMaterial({ color: 0xc9a96e, transparent: true, opacity: 0.012, blending: THREE.AdditiveBlending })
    );
    group.add(glowMesh);

    camera.position.z = 7.5;

    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
      group.position.set(window.innerWidth >= 1024 ? 2.2 : 0, 0.1, window.innerWidth >= 1024 ? 0 : -1);
    };
    onResize();
    window.addEventListener('resize', onResize);

    let tMX = 0, tMY = 0, mX = 0, mY = 0;
    document.addEventListener('mousemove', e => {
      tMX = (e.clientX - window.innerWidth / 2) / (window.innerWidth / 2);
      tMY = (e.clientY - window.innerHeight / 2) / (window.innerHeight / 2);
    });

    gsap.to(camera.position, {
      z: 5, scrollTrigger: { trigger: '#about', start: 'top bottom', end: 'bottom top', scrub: 1 }
    });
    gsap.to(group.rotation, {
      y: Math.PI * 2, scrollTrigger: { trigger: 'body', start: 'top top', end: 'bottom bottom', scrub: 1 }
    });

    const clock = new THREE.Clock();

    const animate = () => {
      requestAnimationFrame(animate);
      if (window.scrollY > window.innerHeight * 1.5) return;

      const t = clock.getElapsedTime();
      mX += (tMX - mX) * 0.06;
      mY += (tMY - mY) * 0.06;

      const hb = 1.0 + Math.sin(t * 1.5) * Math.cos(t * 0.4) * 0.05;
      const pos = hubGeo.attributes.position.array;

      for (let i = 0; i < N; i++) {
        const ix = i * 3;
        const ox = origPos[ix], oy = origPos[ix + 1], oz = origPos[ix + 2];
        const nv = noise(ox * 0.5, oy * 0.5, oz * 0.5, t * 0.7) * 0.1;
        pos[ix] = ox * hb + ox * nv;
        pos[ix + 1] = oy * hb + oy * nv;
        pos[ix + 2] = oz * hb + oz * nv;

        const dx = pos[ix] + group.position.x - mX * 4;
        const dy = pos[ix + 1] + group.position.y + mY * 3;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d < 1.6) { const f = (1.6 - d) * 0.1; pos[ix] -= dx * f; pos[ix + 1] -= dy * f; }
      }
      hubGeo.attributes.position.needsUpdate = true;

      // Lines
      let li = 0;
      const limSq = 1.35 * 1.35, lim = 1.35;
      for (let i = 0; i < N && li < MAX_LINES; i++) {
        for (let j = i + 1; j < N && li < MAX_LINES; j++) {
          const ax = i * 3, bx = j * 3;
          const dx = pos[ax] - pos[bx], dy = pos[ax + 1] - pos[bx + 1], dz = pos[ax + 2] - pos[bx + 2];
          const dSq = dx * dx + dy * dy + dz * dz;
          if (dSq < limSq) {
            const d = Math.sqrt(dSq), a = 1 - d / lim, k = li * 6;
            lP[k] = pos[ax]; lP[k + 1] = pos[ax + 1]; lP[k + 2] = pos[ax + 2];
            lP[k + 3] = pos[bx]; lP[k + 4] = pos[bx + 1]; lP[k + 5] = pos[bx + 2];
            // Gold → ivory
            lC[k] = 0.79 * a; lC[k + 1] = 0.66 * a; lC[k + 2] = 0.43 * a;
            lC[k + 3] = 0.83 * a; lC[k + 4] = 0.81 * a; lC[k + 5] = 0.78 * a;
            li++;
          }
        }
      }
      for (let i = li; i < MAX_LINES; i++) { const k = i * 6; lP[k]=lP[k+1]=lP[k+2]=lP[k+3]=lP[k+4]=lP[k+5]=0; }
      lines.geometry.attributes.position.needsUpdate = true;
      lines.geometry.attributes.color.needsUpdate = true;

      dust.rotation.y = t * 0.01;
      dust.rotation.x = t * 0.005;
      group.rotation.x = mY * 0.08;
      group.rotation.y += 0.0015;
      glowMesh.scale.setScalar(hb * 1.1);

      renderer.render(scene, camera);
    };
    animate();
  }
}
