// Custom Cursor
const cursor = document.querySelector('.cursor');
const follower = document.querySelector('.cursor-follower');
const links = document.querySelectorAll('a, .magnetic-btn, .project-card');

document.addEventListener('mousemove', (e) => {
  gsap.to(cursor, { x: e.clientX, y: e.clientY, duration: 0, ease: 'power2.out' });
  gsap.to(follower, { x: e.clientX, y: e.clientY, duration: 0.15, ease: 'power2.out' });
});

links.forEach(link => {
  link.addEventListener('mouseenter', () => {
    cursor.classList.add('hovered');
    follower.classList.add('hovered');
  });
  link.addEventListener('mouseleave', () => {
    cursor.classList.remove('hovered');
    follower.classList.remove('hovered');
  });
});

// Magnetic Buttons
const magneticBtns = document.querySelectorAll('.magnetic-btn');
magneticBtns.forEach(btn => {
  btn.addEventListener('mousemove', (e) => {
    const rect = btn.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;
    gsap.to(btn, { x: x * 0.3, y: y * 0.3, duration: 0.3, ease: 'power2.out' });
  });
  btn.addEventListener('mouseleave', () => {
    gsap.to(btn, { x: 0, y: 0, duration: 0.5, ease: 'elastic.out(1, 0.3)' });
  });
});

// GSAP Animations
gsap.registerPlugin(ScrollTrigger);

// Hero Reveal
gsap.from('.reveal-text', {
  y: 100,
  opacity: 0,
  duration: 1.5,
  ease: 'power4.out',
  stagger: 0.2
});

// Scroll Reveals
const revealElements = document.querySelectorAll('.reveal-up');
revealElements.forEach((el) => {
  const delay = el.classList.contains('delay-1') ? 0.2 : el.classList.contains('delay-2') ? 0.4 : 0;
  gsap.from(el, {
    scrollTrigger: {
      trigger: el,
      start: 'top 85%',
      toggleActions: 'play none none reverse'
    },
    y: 50,
    opacity: 0,
    duration: 1,
    delay: delay,
    ease: 'power3.out'
  });
});

// Background Canvas Effect (Subtle Particles)
const canvas = document.getElementById('bg-canvas');
const ctx = canvas.getContext('2d');
let width, height;

function resize() {
  width = canvas.width = window.innerWidth;
  height = canvas.height = window.innerHeight;
}
window.addEventListener('resize', resize);
resize();

const particles = [];
for (let i = 0; i < 50; i++) {
  particles.push({
    x: Math.random() * width,
    y: Math.random() * height,
    size: Math.random() * 2 + 0.1,
    speedX: Math.random() * 0.5 - 0.25,
    speedY: Math.random() * 0.5 - 0.25,
    color: \gba(255, 255, 255, \)\
  });
}

function animateParticles() {
  ctx.clearRect(0, 0, width, height);
  particles.forEach(p => {
    p.x += p.speedX;
    p.y += p.speedY;

    if (p.x < 0 || p.x > width) p.speedX *= -1;
    if (p.y < 0 || p.y > height) p.speedY *= -1;

    ctx.beginPath();
    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
    ctx.fillStyle = p.color;
    ctx.fill();
  });
  requestAnimationFrame(animateParticles);
}
animateParticles();
