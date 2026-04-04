// Register GSAP plugins
gsap.registerPlugin(ScrollTrigger);

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const isDesktop = window.matchMedia('(hover: hover) and (pointer: fine)').matches && window.innerWidth >= 1024;
const useEnhancedMotion = isDesktop && !prefersReducedMotion;

let appHeightRaf = null;
function updateAppHeight() {
  const viewportHeight = window.visualViewport ? window.visualViewport.height : window.innerHeight;
  document.documentElement.style.setProperty('--app-height', `${viewportHeight * 0.01}px`);
}

function scheduleAppHeightUpdate() {
  if (appHeightRaf) cancelAnimationFrame(appHeightRaf);
  appHeightRaf = requestAnimationFrame(() => {
    updateAppHeight();
    appHeightRaf = null;
  });
}

updateAppHeight();
window.addEventListener('resize', scheduleAppHeightUpdate, { passive: true });
window.addEventListener('orientationchange', scheduleAppHeightUpdate);
if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', scheduleAppHeightUpdate, { passive: true });
}

// 1. Lenis Smooth Scroll Setup
let lenis = null;
if (useEnhancedMotion) {
  lenis = new Lenis({
    duration: 1.2,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    direction: 'vertical',
    gestureDirection: 'vertical',
    smooth: true,
    mouseMultiplier: 1,
    smoothTouch: false,
    touchMultiplier: 2,
  });

  // Keep ScrollTrigger in sync with Lenis without a second RAF loop.
  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add((time) => {
    lenis.raf(time * 1000);
  });
  gsap.ticker.lagSmoothing(0);
}


// 2. Custom Cursor Logic
const cursorDot = document.querySelector('.cursor-dot');
const cursorGlow = document.querySelector('.cursor-glow');
const magnetics = document.querySelectorAll('.magnetic');

function setCursorHoverState(active) {
  if (!cursorDot || !cursorGlow) return;
  cursorDot.classList.toggle('hover', active);
  cursorGlow.classList.toggle('hover', active);
}

function bindHoverTargets(elements) {
  elements.forEach((el) => {
    if (el.dataset.hoverBound === 'true') return;
    el.dataset.hoverBound = 'true';

    el.addEventListener('mouseenter', () => setCursorHoverState(true));
    el.addEventListener('mouseleave', () => setCursorHoverState(false));
  });
}

function bindMagneticMotion(elements) {
  if (!useEnhancedMotion) return;

  elements.forEach((elem) => {
    if (elem.dataset.magneticBound === 'true') return;
    elem.dataset.magneticBound = 'true';

    elem.addEventListener('mousemove', (e) => {
      const rect = elem.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;

      gsap.to(elem, { x: x * 0.3, y: y * 0.3, duration: 0.4, ease: 'power2.out' });
      setCursorHoverState(true);
    });

    elem.addEventListener('mouseleave', () => {
      gsap.to(elem, { x: 0, y: 0, duration: 0.7, ease: 'elastic.out(1, 0.3)' });
      setCursorHoverState(false);
    });
  });
}

if (useEnhancedMotion) {
  // Move cursor
  window.addEventListener('mousemove', (e) => {
    if(cursorDot) gsap.to(cursorDot, { x: e.clientX, y: e.clientY, duration: 0.1, ease: "power2.out" });
    if(cursorGlow) gsap.to(cursorGlow, { x: e.clientX, y: e.clientY, duration: 0.8, ease: "power2.out" });
  });

  // Magnetic hover effects
  bindMagneticMotion(magnetics);

  // General hover for a/button
  bindHoverTargets(document.querySelectorAll('a, button, .project-card, .case-card, .experiment-card, .skill-card, .about-card, .story-card, .story-mini, .studio-note, input, textarea'));
}


// 3. Three.js Background (Stars / abstract particles)
const canvas = document.querySelector('#webgl-canvas');
if (canvas && useEnhancedMotion) {
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x030305, 0.001);

    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 2000);
  camera.position.z = 500;

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Create Particles
    const geometry = new THREE.BufferGeometry();
    const particlesCount = 400;
    const posArray = new Float32Array(particlesCount * 3);
    const colorsArray = new Float32Array(particlesCount * 3);

    const color1 = new THREE.Color(0x00f0ff); // neon
    const color2 = new THREE.Color(0x8a2be2); // purple

    for(let i = 0; i < particlesCount * 3; i+=3) {
        // Random position in a sphere-like distribution
        const x = (Math.random() - 0.5) * 2000;
        const y = (Math.random() - 0.5) * 2000;
        const z = (Math.random() - 0.5) * 2000;
        posArray[i] = x;
        posArray[i+1] = y;
        posArray[i+2] = z;

        // Mix colors
        const mixColor = color1.clone().lerp(color2, Math.random());
        colorsArray[i] = mixColor.r;
        colorsArray[i+1] = mixColor.g;
        colorsArray[i+2] = mixColor.b;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colorsArray, 3));

    const material = new THREE.PointsMaterial({
      size: 1.8,
        vertexColors: true,
        transparent: true,
      opacity: 0.75,
        blending: THREE.AdditiveBlending
    });

    const particlesMesh = new THREE.Points(geometry, material);
    scene.add(particlesMesh);

    // Mouse interaction for ThreeJS
    let mouseX = 0;
    let mouseY = 0;
    window.addEventListener('mousemove', (event) => {
      mouseX = (event.clientX / window.innerWidth) - 0.5;
      mouseY = (event.clientY / window.innerHeight) - 0.5;
    });

    const clock = new THREE.Clock();
    function animateThree() {
        const elapsedTime = clock.getElapsedTime();
        
        // Slow rotation
        particlesMesh.rotation.y = elapsedTime * 0.05;
        particlesMesh.rotation.x = elapsedTime * 0.02;

        // Mouse parallax
        camera.position.x += (mouseX * 200 - camera.position.x) * 0.05;
        camera.position.y += (-mouseY * 200 - camera.position.y) * 0.05;
        camera.lookAt(scene.position);

        renderer.render(scene, camera);
        requestAnimationFrame(animateThree);
    }
    animateThree();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
}

// 4. Initial Loader Animation
window.addEventListener('load', () => {
  const tl = gsap.timeline();

  // Progress bar animation mock
  tl.to('.loader-fill', {
    width: '100%',
    duration: 1.5,
    ease: "power3.inOut"
  })
  .to('.loader', {
    yPercent: -100,
    duration: 1,
    ease: "power4.inOut"
  })
  .add(() => {
    document.body.classList.remove('loading');
    setTimeout(() => {
      const loader = document.querySelector('.loader');
      if (loader) loader.remove();
    }, 1000);
  }, "-=0.5")

  // Hero reveals
  .from('.line', {
    y: 100,
    opacity: 0,
    duration: 1,
    stagger: 0.2,
    ease: "power4.out"
  }, "-=0.5")
  .from('.reveal-fade', {
    opacity: 0,
    y: 20,
    duration: 1,
    ease: "power2.out",
    stagger: 0.2
  }, "-=0.5");
});


// 5. Scroll Animations
if (useEnhancedMotion) {
  gsap.utils.toArray('.reveal-up').forEach(el => {
    gsap.from(el, {
      scrollTrigger: {
        trigger: el,
        start: "top 85%",
      },
      y: 60,
      opacity: 0,
      duration: 1,
      ease: "power3.out"
    });
  });

  const splitTexts = document.querySelectorAll('.split-text');
  splitTexts.forEach(st => {
    gsap.from(st, {
      scrollTrigger: { trigger: st, start: "top 80%" },
      opacity: 0, x: -50, duration: 1, ease: "power3.out"
    });
  });

  gsap.utils.toArray('.skill-row').forEach((row) => {
    const fill = row.querySelector('.skill-fill');
    if (!fill) return;

    const targetLevel = Number(row.dataset.level || 0);
    gsap.fromTo(fill, {
      width: '0%'
    }, {
      width: `${targetLevel}%`,
      duration: 1.2,
      ease: 'power3.out',
      scrollTrigger: {
        trigger: row,
        start: 'top 85%'
      }
    });
  });
}

function attachTiltInteractions(selector) {
  if (!useEnhancedMotion) return;

  document.querySelectorAll(selector).forEach((card) => {
    if (card.dataset.tiltBound === 'true') return;
    card.dataset.tiltBound = 'true';

    card.addEventListener('mousemove', (event) => {
      const rect = card.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const rotateX = ((y - centerY) / centerY) * -8;
      const rotateY = ((x - centerX) / centerX) * 8;

      card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-8px) scale3d(1.01, 1.01, 1.01)`;
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0) scale3d(1, 1, 1)';
    });
  });
}

attachTiltInteractions('.project-card, .case-card, .experiment-card');


// 6. Fetch GitHub Projects Dynamically
async function fetchGithubProjects() {
  const container = document.getElementById('github-projects');
  if(!container) return;

  const projectProfiles = {
    'demand-forecasting-mlops': {
      title: 'Demand Forecasting MLOps Pipeline',
      summary: 'An end-to-end forecasting system that turns synthetic data into a usable pipeline with lag features, evaluation, artifacts, and a FastAPI face.',
      stack: ['Python', 'Pandas', 'Scikit-learn', 'FastAPI']
    },
    'news-topic-classifier': {
      title: 'Multilingual News Topic Classifier',
      summary: 'A compact NLP build that classifies articles with TF-IDF and Linear SVM, wrapped in a Streamlit demo.',
      stack: ['Python', 'NLP', 'Scikit-learn', 'Streamlit']
    },
    'defect-detection-cv': {
      title: 'Industrial Defect Detection',
      summary: 'A computer vision study using synthetic imagery, edge features, and SVM classification to detect defects quickly.',
      stack: ['OpenCV', 'NumPy', 'Scikit-learn', 'Python']
    },
    'customer-segmentation-dashboard': {
      title: 'Customer Segmentation Dashboard',
      summary: 'A clustering dashboard that turns customer behavior into clear segments and interactive insight.',
      stack: ['Python', 'Pandas', 'Plotly', 'Streamlit']
    }
  };

  function formatRepoName(name) {
    return name
      .split('-')
      .map(part => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');
  }

  try {
    // Specifically grabbing the 6 latest repos
    const response = await fetch('https://api.github.com/users/Souravjr0/repos?sort=updated&per_page=6');
    if (!response.ok) throw new Error('API Rate Limit or Network Issue');
    const repos = await response.json();
    
    container.innerHTML = '';
    
    repos.forEach((repo, i) => {
      const profile = projectProfiles[repo.name] || {
        title: formatRepoName(repo.name),
        summary: repo.description || 'A GitHub build from my portfolio, shaped to solve a concrete data, AI, or automation problem.',
        stack: repo.language ? [repo.language, 'GitHub'] : ['GitHub']
      };
      const tech = repo.language ? repo.language : 'Tech Stack';
      const stars = repo.stargazers_count;
      const updatedAt = new Date(repo.updated_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
      const stackHTML = profile.stack.map((item) => `<span>${item}</span>`).join('');
      
      const cardHTML = `
        <article class="project-card glass reveal-projects">
          <div class="project-card-inner">
            <p class="repo-label">Selected Work</p>
            <h3 class="repo-name">${profile.title}</h3>
            <p class="repo-desc">${profile.summary}</p>
            <div class="project-tags">${stackHTML}</div>
            <div class="project-meta-row">
              <div class="repo-meta">
                <span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M12 8v4l3 3"></path></svg> ${tech}</span>
                <span>★ ${stars}</span>
                <span>${updatedAt}</span>
              </div>
              <a href="${repo.html_url}" target="_blank" rel="noreferrer" class="project-link magnetic">Open Work</a>
            </div>
          </div>
        </article>
      `;
      container.insertAdjacentHTML('beforeend', cardHTML);
    });

    // Re-bind cursor triggers for new elements
    bindHoverTargets(container.querySelectorAll('.project-card, .project-link'));
    bindMagneticMotion(container.querySelectorAll('.project-link.magnetic'));
    attachTiltInteractions('.project-card, .case-card');

    if (useEnhancedMotion) {
      gsap.from('.reveal-projects', {
        scrollTrigger: { trigger: '#projects', start: "top 70%" },
        y: 50, opacity: 0, duration: 0.8, stagger: 0.15, ease: "power2.out"
      });
    }

  } catch (error) {
    container.innerHTML = '<p class="error" style="color:var(--text-dim);">Unable to fetch projects right now. You can check out my <a href="https://github.com/Souravjr0" style="color:var(--accent-neon);">GitHub Profile</a>.</p>';
  }
}

fetchGithubProjects();
