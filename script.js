// ============================================================
//  SOURAV BISWAS PORTFOLIO — script.js (Awwwards Redesign)
// ============================================================

const hasGSAP = typeof gsap !== 'undefined';

if (hasGSAP) {
  gsap.registerPlugin(ScrollTrigger);
}

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const isDesktop = window.matchMedia('(hover: hover) and (pointer: fine)').matches && window.innerWidth >= 1024;
const useMotion = isDesktop && !prefersReducedMotion;

// ------- Loader Control -------
const startLoaderAnimation = () => {
  const loader = document.getElementById('loader');
  if (!loader) return;

  if (hasGSAP) {
    const tl = gsap.timeline();
    tl.to('.loader-bar', { width: '100%', duration: 0.8, ease: 'power2.inOut' })
      .to(loader, { yPercent: -100, duration: 0.8, ease: 'power4.inOut' })
      .add(() => {
        document.body.classList.remove('loading');
        loader.remove();
      }, '-=0.3')
      // Hero entry animations
      .from('.status-badge', { opacity: 0, y: 15, duration: 0.6 }, '-=0.2')
      .from('.hero-title span', { y: 60, opacity: 0, duration: 0.8, stagger: 0.15, ease: 'power4.out' }, '-=0.4')
      .from('.hero-meta .meta-item', { opacity: 0, y: 15, duration: 0.6, stagger: 0.1 }, '-=0.4')
      .from('.hero-actions .btn', { opacity: 0, y: 15, duration: 0.6, stagger: 0.1 }, '-=0.4');
  } else {
    // Fallback if GSAP is not loaded
    document.body.classList.remove('loading');
    loader.remove();
    document.querySelectorAll('.reveal-up, .reveal-fade').forEach(el => {
      el.classList.add('visible');
      el.style.opacity = 1;
      el.style.transform = 'none';
    });
  }
};

// Check if document is already loaded to prevent loader lockup
if (document.readyState === 'complete') {
  startLoaderAnimation();
} else {
  window.addEventListener('load', startLoaderAnimation);
}

// ------- Custom Cursor -------
if (useMotion) {
  const cursor = document.querySelector('.custom-cursor');
  const glow = document.querySelector('.custom-cursor-glow');
  let cursorInitialized = false;

  window.addEventListener('mousemove', e => {
    // Save cursor position variables on document root for CSS text offset
    document.documentElement.style.setProperty('--mx', e.clientX + 'px');
    document.documentElement.style.setProperty('--my', e.clientY + 'px');

    if (!cursorInitialized) {
      if (hasGSAP) {
        gsap.set([cursor, glow], { opacity: 1 });
      } else {
        if (cursor) cursor.style.opacity = '1';
        if (glow) glow.style.opacity = '1';
      }
      cursorInitialized = true;
    }

    if (hasGSAP) {
      if (cursor) gsap.to(cursor, { x: e.clientX, y: e.clientY, duration: 0.08, ease: 'power2.out' });
      if (glow) gsap.to(glow, { x: e.clientX, y: e.clientY, duration: 0.35, ease: 'power2.out' });
    } else {
      if (cursor) {
        cursor.style.left = e.clientX + 'px';
        cursor.style.top = e.clientY + 'px';
      }
      if (glow) {
        glow.style.left = e.clientX + 'px';
        glow.style.top = e.clientY + 'px';
      }
    }
  });

  document.querySelectorAll('a, button, .cert-tab-btn, input, textarea, [data-category]').forEach(el => {
    el.addEventListener('mouseenter', () => {
      document.body.classList.add('cursor-hover');
    });
    el.addEventListener('mouseleave', () => {
      document.body.classList.remove('cursor-hover');
    });
  });

  // Highlight blocks get "VIEW" tag on cursor
  document.querySelectorAll('.metric-card, .story-highlight-card, .skills-block').forEach(el => {
    el.addEventListener('mouseenter', () => {
      document.body.classList.add('cursor-view');
    });
    el.addEventListener('mouseleave', () => {
      document.body.classList.remove('cursor-view');
    });
  });
} else {
  // Hide custom cursor elements on mobile/non-motion
  document.querySelector('.custom-cursor')?.remove();
  document.querySelector('.custom-cursor-glow')?.remove();
}

// ------- Hamburger Nav -------
(function () {
  const btn = document.getElementById('hamburger');
  const links = document.getElementById('nav-links');
  if (!btn || !links) return;

  const open = () => {
    links.classList.add('is-open');
    btn.classList.add('is-open');
    btn.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
  };
  const close = () => {
    links.classList.remove('is-open');
    btn.classList.remove('is-open');
    btn.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  };

  btn.addEventListener('click', () => links.classList.contains('is-open') ? close() : open());
  links.querySelectorAll('a').forEach(a => a.addEventListener('click', close));
  document.addEventListener('keydown', e => e.key === 'Escape' && close());
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

// ------- Certifications filtering -------
(function () {
  const tabs = document.querySelectorAll('.cert-tab-btn');
  const cards = document.querySelectorAll('.cert-card');
  if (!tabs.length || !cards.length) return;

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const filter = tab.dataset.filter;

      cards.forEach(card => {
        if (filter === 'all' || card.dataset.category === filter) {
          if (hasGSAP) {
            gsap.to(card, { opacity: 1, scale: 1, duration: 0.4, display: 'block' });
          } else {
            card.style.opacity = '1';
            card.style.transform = 'scale(1)';
            card.style.display = 'block';
          }
        } else {
          if (hasGSAP) {
            gsap.to(card, { opacity: 0, scale: 0.9, duration: 0.3, display: 'none' });
          } else {
            card.style.opacity = '0';
            card.style.transform = 'scale(0.9)';
            card.style.display = 'none';
          }
        }
      });
    });
  });
})();

// ------- Skills filling animation (GSAP triggered) -------
window.addEventListener('load', () => {
  if (!hasGSAP) return;
  document.querySelectorAll('.skill-row').forEach(row => {
    const level = row.dataset.level || '80';
    const bar = row.querySelector('.skill-progress-bar');
    if (!bar) return;

    gsap.to(bar, {
      width: level + '%',
      scrollTrigger: {
        trigger: row,
        start: 'top 92%',
        ease: 'power2.out',
        toggleActions: 'play none none none'
      }
    });
  });
});

// ------- GSAP reveal animations -------
if (hasGSAP) {
  if (useMotion) {
    document.querySelectorAll('.reveal-up').forEach((el) => {
      gsap.from(el, {
        y: 40,
        opacity: 0,
        duration: 0.8,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: el,
          start: 'top 88%',
          toggleActions: 'play none none none'
        }
      });
    });
  } else {
    document.querySelectorAll('.reveal-up, .reveal-fade').forEach(el => {
      el.classList.add('visible');
      el.style.opacity = 1;
      el.style.transform = 'none';
    });
  }
}

// ------- Three.js Organic "Neural Heartbeat" Particle Field -------
if (useMotion && typeof THREE !== 'undefined') {
  const initThreeJS = () => {
    const canvas = document.getElementById('hero-canvas');
    if (!canvas) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });

    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));

    // Groups
    const mainGroup = new THREE.Group();
    scene.add(mainGroup);

    // --- Dynamic Neural Hubs (200 nodes connected by dynamic lines) ---
    const hubCount = 200;
    const hubGeometry = new THREE.BufferGeometry();
    const hubPositions = new Float32Array(hubCount * 3);
    const hubOffsets = [];
    const hubSpeeds = [];

    for (let i = 0; i < hubCount; i++) {
      // Sphere coordinate distribution
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const r = 2.2 + Math.random() * 0.6; // Spherical band thickness

      hubPositions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      hubPositions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      hubPositions[i * 3 + 2] = r * Math.cos(phi);

      hubOffsets.push(Math.random() * Math.PI * 2);
      hubSpeeds.push(0.4 + Math.random() * 0.8);
    }

    hubGeometry.setAttribute('position', new THREE.BufferAttribute(hubPositions, 3));
    
    // Save original position copies for math morphs
    const origHubPositions = hubPositions.slice();

    const hubMaterial = new THREE.PointsMaterial({
      size: 0.04,
      color: 0xff2a85, // Cyber Magenta
      transparent: true,
      opacity: 0.85
    });

    const hubs = new THREE.Points(hubGeometry, hubMaterial);
    mainGroup.add(hubs);

    // --- Connections lines ---
    const maxConnections = 500;
    const lineGeometry = new THREE.BufferGeometry();
    const linePositions = new Float32Array(maxConnections * 2 * 3); // max * 2 points * 3 coordinates
    const lineColors = new Float32Array(maxConnections * 2 * 3);

    lineGeometry.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
    lineGeometry.setAttribute('color', new THREE.BufferAttribute(lineColors, 3));

    // Semi-transparent connection material
    const lineMaterial = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.22,
      blending: THREE.AdditiveBlending
    });

    const networkLines = new THREE.LineSegments(lineGeometry, lineMaterial);
    mainGroup.add(networkLines);

    // --- Ambient Halo Dust (1,000 drifting stars) ---
    const dustCount = 800;
    const dustGeometry = new THREE.BufferGeometry();
    const dustPositions = new Float32Array(dustCount * 3);

    for (let i = 0; i < dustCount; i++) {
      // Wider distribution
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const r = 3.2 + Math.random() * 4.8;

      dustPositions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      dustPositions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      dustPositions[i * 3 + 2] = r * Math.cos(phi);
    }

    dustGeometry.setAttribute('position', new THREE.BufferAttribute(dustPositions, 3));
    const dustMaterial = new THREE.PointsMaterial({
      size: 0.018,
      color: 0x00f0ff, // Electric Cyan
      transparent: true,
      opacity: 0.45
    });

    const dustParticles = new THREE.Points(dustGeometry, dustMaterial);
    mainGroup.add(dustParticles);

    // Position camera
    camera.position.z = 7.5;

    // Reposition scene elements depending on viewport width
    const handleResize = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);

      // Desktop: Shift WebGL right to fit next to Hero text. Mobile: Centered
      if (w >= 1024) {
        mainGroup.position.set(2.4, 0.15, 0);
      } else {
        mainGroup.position.set(0, 0, -1);
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);

    // Mouse interactive tracking
    let targetMouseX = 0, targetMouseY = 0;
    let mouseX = 0, mouseY = 0;

    document.addEventListener('mousemove', (e) => {
      targetMouseX = (e.clientX - window.innerWidth / 2) / (window.innerWidth / 2);
      targetMouseY = (e.clientY - window.innerHeight / 2) / (window.innerHeight / 2);
    });

    // Scroll trigger interaction
    if (hasGSAP) {
      gsap.to(mainGroup.rotation, {
        y: Math.PI * 1.5,
        scrollTrigger: {
          trigger: 'body',
          start: 'top top',
          end: 'bottom bottom',
          scrub: 1
        }
      });

      gsap.to(camera.position, {
        z: 5.5,
        scrollTrigger: {
          trigger: '#about',
          start: 'top bottom',
          end: 'bottom top',
          scrub: 1
        }
      });
    }

    const clock = new THREE.Clock();

    const animate = () => {
      requestAnimationFrame(animate);

      // Don't render WebGL if scrolled far out of view for performance
      if (window.scrollY > window.innerHeight * 1.5) return;

      const t = clock.getElapsedTime();

      // Lerp mouse coordinates to smooth out lags
      mouseX += (targetMouseX - mouseX) * 0.08;
      mouseY += (targetMouseY - mouseY) * 0.08;

      // Pulse rhythm factor (Calm, organic heartbeat simulation)
      const heartbeat = 1.0 + Math.sin(t * 1.8) * Math.cos(t * 0.6) * 0.08;

      // Animate core hub nodes
      const pos = hubGeometry.attributes.position.array;
      for (let i = 0; i < hubCount; i++) {
        const idx = i * 3;
        const ox = origHubPositions[idx];
        const oy = origHubPositions[idx + 1];
        const oz = origHubPositions[idx + 2];

        // Complex noise-like ripple math morphing
        const offset = hubOffsets[i];
        const speed = hubSpeeds[i];
        const ripple = Math.sin(t * speed + offset) * 0.06;

        // Apply heartbeat pulse + noise ripple
        pos[idx] = ox * heartbeat + ox * ripple;
        pos[idx + 1] = oy * heartbeat + oy * ripple;
        pos[idx + 2] = oz * heartbeat + oz * ripple;

        // Mouse magnetic attraction effect
        // Project mouse coordinate shifts to 3D positions
        const dx = pos[idx] + mainGroup.position.x - (mouseX * 4);
        const dy = pos[idx + 1] + mainGroup.position.y - (-mouseY * 3);
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 1.4) {
          const force = (1.4 - dist) * 0.15;
          pos[idx] -= dx * force;
          pos[idx + 1] -= dy * force;
        }
      }
      hubGeometry.attributes.position.needsUpdate = true;

      // --- Dynamic connection line drawing ---
      let lineIndex = 0;
      const positions = networkLines.geometry.attributes.position.array;
      const colors = networkLines.geometry.attributes.color.array;

      // Optimize by comparing squared distance first to avoid heavy Math.sqrt calls
      const limit = 1.35;
      const limitSq = limit * limit;

      for (let i = 0; i < hubCount; i++) {
        for (let j = i + 1; j < hubCount; j++) {
          if (lineIndex >= maxConnections) break;

          const idxA = i * 3;
          const idxB = j * 3;

          const dx = pos[idxA] - pos[idxB];
          const dy = pos[idxA + 1] - pos[idxB + 1];
          const dz = pos[idxA + 2] - pos[idxB + 2];
          
          const distSq = dx * dx + dy * dy + dz * dz;

          // Connect if particles are close
          if (distSq < limitSq) {
            const dist = Math.sqrt(distSq);
            const linePosIndex = lineIndex * 6;
            
            // Point A
            positions[linePosIndex] = pos[idxA];
            positions[linePosIndex + 1] = pos[idxA + 1];
            positions[linePosIndex + 2] = pos[idxA + 2];

            // Point B
            positions[linePosIndex + 3] = pos[idxB];
            positions[linePosIndex + 4] = pos[idxB + 1];
            positions[linePosIndex + 5] = pos[idxB + 2];

            // Calculate colors (Gradient shift between Magenta & Cyan depending on distance)
            const lineColorIndex = lineIndex * 6;
            const alpha = 1.0 - (dist / limit); // closer -> brighter

            // Point A color (Magenta bias)
            colors[lineColorIndex] = 1.0 * alpha; // R
            colors[lineColorIndex + 1] = 0.16 * alpha; // G
            colors[lineColorIndex + 2] = 0.52 * alpha; // B

            // Point B color (Cyan bias)
            colors[lineColorIndex + 3] = 0.0 * alpha;
            colors[lineColorIndex + 4] = 0.94 * alpha;
            colors[lineColorIndex + 5] = 1.0 * alpha;

            lineIndex++;
          }
        }
      }

      // Reset rest of the unused line values to 0 to prevent trail artifacts
      for (let i = lineIndex; i < maxConnections; i++) {
        const linePosIndex = i * 6;
        positions[linePosIndex] = 0;
        positions[linePosIndex + 1] = 0;
        positions[linePosIndex + 2] = 0;
        positions[linePosIndex + 3] = 0;
        positions[linePosIndex + 4] = 0;
        positions[linePosIndex + 5] = 0;
      }

      networkLines.geometry.attributes.position.needsUpdate = true;
      networkLines.geometry.attributes.color.needsUpdate = true;

      // Gentle continuous spin of the outer dust cloud
      dustParticles.rotation.y = t * 0.015;
      dustParticles.rotation.x = t * 0.008;

      // Mouse-influence tilt
      mainGroup.rotation.x = mouseY * 0.12;
      mainGroup.rotation.y += 0.0025;

      renderer.render(scene, camera);
    };
    animate();
  };

  initThreeJS();
}

// ------- Interactive Magnet Hover Effects -------
if (useMotion && hasGSAP) {
  document.querySelectorAll('.btn, .nav-logo').forEach(btn => {
    let rect;
    btn.addEventListener('mouseenter', () => {
      rect = btn.getBoundingClientRect();
    });
    btn.addEventListener('mousemove', (e) => {
      if (!rect) return;
      const x = (e.clientX - rect.left - rect.width / 2) * 0.35;
      const y = (e.clientY - rect.top - rect.height / 2) * 0.35;
      gsap.to(btn, { x, y, duration: 0.3, ease: 'power2.out' });
    });
    btn.addEventListener('mouseleave', () => {
      rect = null;
      gsap.to(btn, { x: 0, y: 0, duration: 0.6, ease: 'elastic.out(1.1, 0.4)' });
    });
  });
}

// ------- Contact Form Submission Handler -------
(function () {
  const form = document.getElementById('contact-form');
  const status = document.getElementById('form-status');
  if (!form || !status) return;

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    btn.textContent = 'Sending Message...';
    btn.disabled = true;

    try {
      const res = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { Accept: 'application/json' }
      });

      if (res.ok) {
        status.textContent = "Thank you! Your message has been sent. I'll get back to you shortly.";
        status.style.color = 'var(--secondary)';
        status.style.borderColor = 'rgba(0, 240, 255, 0.2)';
        form.reset();
      } else {
        throw new Error();
      }
    } catch {
      status.textContent = 'Oops! Something went wrong. Please email directly at biswasmail631@gmail.com';
      status.style.color = 'var(--primary)';
      status.style.borderColor = 'rgba(255, 42, 133, 0.2)';
    }

    status.classList.remove('hidden');
    btn.textContent = 'Send Message';
    btn.disabled = false;

    setTimeout(() => status.classList.add('hidden'), 7000);
  });
})();
