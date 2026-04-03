// Register GSAP plugins
gsap.registerPlugin(ScrollTrigger);

// 1. Lenis Smooth Scroll Setup
const lenis = new Lenis({
  duration: 1.2,
  easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
  direction: 'vertical',
  gestureDirection: 'vertical',
  smooth: true,
  mouseMultiplier: 1,
  smoothTouch: false,
  touchMultiplier: 2,
});

function raf(time) {
  lenis.raf(time);
  requestAnimationFrame(raf);
}
requestAnimationFrame(raf);

// Update GSAP ScrollTrigger to use Lenis
lenis.on('scroll', ScrollTrigger.update);
gsap.ticker.add((time) => {
  lenis.raf(time * 1000);
});
gsap.ticker.lagSmoothing(0);


// 2. Custom Cursor Logic
const cursorDot = document.querySelector('.cursor-dot');
const cursorGlow = document.querySelector('.cursor-glow');
const magnetics = document.querySelectorAll('.magnetic');

if (window.innerWidth > 768) {
  // Move cursor
  window.addEventListener('mousemove', (e) => {
    if(cursorDot) gsap.to(cursorDot, { x: e.clientX, y: e.clientY, duration: 0.1, ease: "power2.out" });
    if(cursorGlow) gsap.to(cursorGlow, { x: e.clientX, y: e.clientY, duration: 0.8, ease: "power2.out" });
  });

  // Magnetic hover effects
  if (magnetics) {
    magnetics.forEach((elem) => {
      elem.addEventListener('mousemove', (e) => {
        const rect = elem.getBoundingClientRect();
        const h = rect.width / 2;
        const x = e.clientX - rect.left - h;
        const y = e.clientY - rect.top - rect.height / 2;
        
        gsap.to(elem, { x: x * 0.3, y: y * 0.3, duration: 0.4, ease: "power2.out" });
        if(cursorDot) cursorDot.classList.add('hover');
        if(cursorGlow) cursorGlow.classList.add('hover');
      });

      elem.addEventListener('mouseleave', () => {
        gsap.to(elem, { x: 0, y: 0, duration: 0.7, ease: "elastic.out(1, 0.3)" });
        if(cursorDot) cursorDot.classList.remove('hover');
        if(cursorGlow) cursorGlow.classList.remove('hover');
      });
    });
  }

  // General hover for a/button
  document.querySelectorAll('a, button, .gh-card, input, textarea').forEach(el => {
    if(!el.classList.contains('magnetic')) {
      el.addEventListener('mouseenter', () => {
        if(cursorDot) cursorDot.classList.add('hover');
        if(cursorGlow) cursorGlow.classList.add('hover');
      });
      el.addEventListener('mouseleave', () => {
        if(cursorDot) cursorDot.classList.remove('hover');
        if(cursorGlow) cursorGlow.classList.remove('hover');
      });
    }
  });
}


// 3. Three.js Background (Stars / abstract particles)
const canvas = document.querySelector('#webgl-canvas');
if (canvas) {
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x030305, 0.001);

    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 2000);
    camera.position.z = 500;

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Create Particles
    const geometry = new THREE.BufferGeometry();
    const particlesCount = 2000;
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
        size: 2,
        vertexColors: true,
        transparent: true,
        opacity: 0.8,
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
  tl.to('.loader-progress::after', {
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

// Parallax for skill items
if (window.innerWidth > 768) {
  gsap.utils.toArray('.skill-item').forEach((item, i) => {
    gsap.to(item, {
      yPercent: -50,
      rotation: Math.random() * 20 - 10,
      ease: "none",
      scrollTrigger: {
        trigger: ".skills-section",
        start: "top bottom",
        end: "bottom top",
        scrub: true
      }
    });
  });
}

// Word splitting effect workaround
const splitTexts = document.querySelectorAll('.split-text');
splitTexts.forEach(st => {
  gsap.from(st, {
    scrollTrigger: { trigger: st, start: "top 80%" },
    opacity: 0, x: -50, duration: 1, ease: "power3.out"
  });
});


// 6. Fetch GitHub Projects Dynamically
async function fetchGithubProjects() {
  const container = document.getElementById('github-projects');
  if(!container) return;

  try {
    // Specifically grabbing the 6 latest repos
    const response = await fetch('https://api.github.com/users/Souravjr0/repos?sort=updated&per_page=6');
    if (!response.ok) throw new Error('API Rate Limit or Network Issue');
    const repos = await response.json();
    
    container.innerHTML = '';
    
    repos.forEach((repo, i) => {
      const tech = repo.language ? repo.language : 'Tech Stack';
      const stars = repo.stargazers_count;
      const noDesc = "A visionary project bridging data and creativity. Explore the code architecture.";
      
      const cardHTML = `
        <a href="${repo.html_url}" target="_blank" class="gh-card glass reveal-projects">
          <div class="card-content">
            <h3 class="repo-name">${repo.name}</h3>
            <p class="repo-desc">${repo.description || noDesc}</p>
            <div class="repo-meta">
              <span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M12 8v4l3 3"></path></svg> ${tech}</span>
              <span>★ ${stars}</span>
            </div>
          </div>
        </a>
      `;
      container.insertAdjacentHTML('beforeend', cardHTML);
    });

    // Re-bind cursor triggers for new elements
    const newCards = document.querySelectorAll('.gh-card');
    if (window.innerWidth > 768) {
      newCards.forEach(el => {
        el.addEventListener('mouseenter', () => { if(cursorDot) cursorDot.classList.add('hover'); if(cursorGlow) cursorGlow.classList.add('hover'); });
        el.addEventListener('mouseleave', () => { if(cursorDot) cursorDot.classList.remove('hover'); if(cursorGlow) cursorGlow.classList.remove('hover'); });
        
        // Card tilt effect
        el.addEventListener('mousemove', (e) => {
          const rect = el.getBoundingClientRect();
          const x = e.clientX - rect.left;
          const y = e.clientY - rect.top;
          const centerX = rect.width / 2;
          const centerY = rect.height / 2;
          const rotateX = ((y - centerY) / centerY) * -10;
          const rotateY = ((x - centerX) / centerX) * 10;
          el.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;
        });
        el.addEventListener('mouseleave', () => {
          el.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)`;
        });
      });
    }

    gsap.from('.reveal-projects', {
      scrollTrigger: { trigger: '#projects', start: "top 70%" },
      y: 50, opacity: 0, duration: 0.8, stagger: 0.15, ease: "power2.out"
    });

  } catch (error) {
    container.innerHTML = '<p class="error" style="color:var(--text-dim);">Unable to fetch projects right now. You can check out my <a href="https://github.com/Souravjr0" style="color:var(--accent-neon);">GitHub Profile</a>.</p>';
  }
}

fetchGithubProjects();
