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
  document.querySelectorAll('a, button, .service-card, .skill-card, .project-card, .short-card, input, textarea').forEach(el => {
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
        status.style.color = '#d4508a';
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


// ------- Three.js Morphing Crystal Sphere + Orbiting Rings -------
if (isDesktop && !prefersReducedMotion && typeof THREE !== 'undefined') {
  const initThreeJS = () => {
    const canvas = document.getElementById('hero-canvas');
    if (!canvas) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });

    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));

    // --- Main morphing crystal (Icosahedron) ---
    const crystalGeom = new THREE.IcosahedronGeometry(2.2, 3);
    const crystalMat = new THREE.MeshBasicMaterial({
      color: 0x8B004A,
      wireframe: true,
      transparent: true,
      opacity: 0.22
    });
    const crystal = new THREE.Mesh(crystalGeom, crystalMat);
    // Store original positions for morphing
    const origPositions = crystalGeom.attributes.position.array.slice();

    // Inner solid glow core
    const coreGeom = new THREE.IcosahedronGeometry(1.6, 2);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0x8B004A,
      transparent: true,
      opacity: 0.06
    });
    const coreMesh = new THREE.Mesh(coreGeom, coreMat);
    crystal.add(coreMesh);

    // --- Orbiting particle ring 1 ---
    const ring1Group = new THREE.Group();
    const ring1Count = 80;
    const ring1Geom = new THREE.BufferGeometry();
    const ring1Pos = new Float32Array(ring1Count * 3);
    for (let i = 0; i < ring1Count; i++) {
      const angle = (i / ring1Count) * Math.PI * 2;
      ring1Pos[i * 3] = Math.cos(angle) * 3.8;
      ring1Pos[i * 3 + 1] = (Math.random() - 0.5) * 0.3;
      ring1Pos[i * 3 + 2] = Math.sin(angle) * 3.8;
    }
    ring1Geom.setAttribute('position', new THREE.BufferAttribute(ring1Pos, 3));
    const ring1Mat = new THREE.PointsMaterial({ size: 0.04, color: 0xd4508a, transparent: true, opacity: 0.7 });
    const ring1 = new THREE.Points(ring1Geom, ring1Mat);
    ring1Group.add(ring1);

    // --- Orbiting particle ring 2 (tilted) ---
    const ring2Group = new THREE.Group();
    const ring2Count = 60;
    const ring2Geom = new THREE.BufferGeometry();
    const ring2Pos = new Float32Array(ring2Count * 3);
    for (let i = 0; i < ring2Count; i++) {
      const angle = (i / ring2Count) * Math.PI * 2;
      ring2Pos[i * 3] = Math.cos(angle) * 4.5;
      ring2Pos[i * 3 + 1] = (Math.random() - 0.5) * 0.2;
      ring2Pos[i * 3 + 2] = Math.sin(angle) * 4.5;
    }
    ring2Geom.setAttribute('position', new THREE.BufferAttribute(ring2Pos, 3));
    const ring2Mat = new THREE.PointsMaterial({ size: 0.03, color: 0xF2EFE7, transparent: true, opacity: 0.35 });
    const ring2 = new THREE.Points(ring2Geom, ring2Mat);
    ring2Group.add(ring2);
    ring2Group.rotation.x = Math.PI * 0.35;
    ring2Group.rotation.z = Math.PI * 0.15;

    // --- Floating diamond shards ---
    const shardGroup = new THREE.Group();
    const shardCount = 12;
    for (let i = 0; i < shardCount; i++) {
      const shardGeom = new THREE.OctahedronGeometry(0.12 + Math.random() * 0.15, 0);
      const shardMat = new THREE.MeshBasicMaterial({
        color: i % 2 === 0 ? 0x8B004A : 0xd4508a,
        wireframe: true,
        transparent: true,
        opacity: 0.4 + Math.random() * 0.3
      });
      const shard = new THREE.Mesh(shardGeom, shardMat);
      const r = 4.5 + Math.random() * 3;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.random() * Math.PI;
      shard.position.set(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta),
        r * Math.cos(phi)
      );
      shard.userData = { speed: 0.3 + Math.random() * 0.8, offset: Math.random() * Math.PI * 2 };
      shardGroup.add(shard);
    }

    // --- Background dust ---
    const dustGeom = new THREE.BufferGeometry();
    const dustCount = 200;
    const dustPos = new Float32Array(dustCount * 3);
    for (let i = 0; i < dustCount * 3; i++) {
      dustPos[i] = (Math.random() - 0.5) * 30;
    }
    dustGeom.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
    const dustMat = new THREE.PointsMaterial({ size: 0.025, color: 0xF2EFE7, transparent: true, opacity: 0.25 });
    const dustMesh = new THREE.Points(dustGeom, dustMat);

    scene.add(crystal);
    scene.add(ring1Group);
    scene.add(ring2Group);
    scene.add(shardGroup);
    scene.add(dustMesh);

    camera.position.z = 8;
    crystal.position.x = 2.5;
    crystal.position.y = 0.3;
    ring1Group.position.copy(crystal.position);
    ring2Group.position.copy(crystal.position);
    shardGroup.position.copy(crystal.position);

    let mouseX = 0, mouseY = 0;
    const halfW = window.innerWidth / 2;
    const halfH = window.innerHeight / 2;

    document.addEventListener('mousemove', (e) => {
      mouseX = (e.clientX - halfW);
      mouseY = (e.clientY - halfH);
    });

    const clock = new THREE.Clock();

    const animate = () => {
      requestAnimationFrame(animate);
      if (window.scrollY > window.innerHeight + 50) return;

      const t = clock.getElapsedTime();
      const tx = mouseX * 0.0008;
      const ty = mouseY * 0.0008;

      // Morph crystal vertices
      const pos = crystalGeom.attributes.position.array;
      for (let i = 0; i < pos.length; i += 3) {
        const ox = origPositions[i], oy = origPositions[i + 1], oz = origPositions[i + 2];
        const noise = Math.sin(ox * 2.5 + t * 1.2) * Math.cos(oy * 2.5 + t * 0.8) * Math.sin(oz * 2.5 + t) * 0.15;
        pos[i] = ox + ox * noise;
        pos[i + 1] = oy + oy * noise;
        pos[i + 2] = oz + oz * noise;
      }
      crystalGeom.attributes.position.needsUpdate = true;

      crystal.rotation.y += 0.04 * (tx - crystal.rotation.y * 0.5) + 0.002;
      crystal.rotation.x += 0.04 * (ty - crystal.rotation.x * 0.5);

      ring1Group.rotation.y = t * 0.25;
      ring2Group.rotation.y = -t * 0.18;

      // Animate diamond shards
      shardGroup.children.forEach(s => {
        s.rotation.x += 0.01 * s.userData.speed;
        s.rotation.y += 0.015 * s.userData.speed;
        s.position.y += Math.sin(t * s.userData.speed + s.userData.offset) * 0.003;
      });

      dustMesh.rotation.y = t * 0.02;

      // Pulse core opacity
      coreMat.opacity = 0.04 + Math.sin(t * 1.5) * 0.03;

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

// ------- Shorts Video Playback -------
(function () {
  const cards = document.querySelectorAll('.short-card');
  cards.forEach(card => {
    const video = card.querySelector('video');
    if (!video) return;
    card.addEventListener('click', () => {
      if (video.paused) {
        // Pause all other videos first
        cards.forEach(c => {
          const v = c.querySelector('video');
          if (v && v !== video && !v.paused) {
            v.pause();
            c.classList.remove('playing');
          }
        });
        video.play();
        card.classList.add('playing');
      } else {
        video.pause();
        card.classList.remove('playing');
      }
    });
  });
})();
