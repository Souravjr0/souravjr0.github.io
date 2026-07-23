export const NAV_LINKS = [
  { label: 'About', href: '#about' },
  { label: 'Workflow', href: '#workflow' },
  { label: 'Interactive Lab', href: '#lab' },
  { label: 'Services', href: '#services' },
  { label: 'Work', href: '#projects' },
  { label: 'Stack', href: '#skills' },
  { label: 'Contact', href: '#contact' },
]

export const HERO_BADGES = [
  { icon: '⚡', label: 'ML & Analytics', sub: '3+ Yrs Experience' },
  { icon: '🚀', label: 'Production Ready', sub: '15+ Pipelines Deployed' },
  { icon: '📍', label: 'Location', sub: 'Pune, India' },
]

export const STATS = [
  { value: 35, suffix: '%', label: 'Reporting Reduced', desc: 'Automated manual BI workflows' },
  { value: 40, suffix: '%', label: 'SEO Rankings Up', desc: 'Data-driven content strategy' },
  { value: 22, suffix: '%', label: 'Revenue Growth', desc: 'Predictive pricing optimization' },
  { value: 99, suffix: '.9%', label: 'Model Uptime', desc: 'Production MLOps reliability' },
]

export const METHODOLOGY = [
  {
    step: '01',
    phase: 'Discovery & Data Audit',
    title: 'Deconstructing the Problem',
    desc: 'Deep-dive analysis of raw data streams, business requirements, and operational bottlenecks to build quantifiable KPIs.',
    tags: ['Data Cleaning', 'EDA', 'KPI Mapping', 'SQL'],
    icon: '📊',
  },
  {
    step: '02',
    phase: 'Predictive Modeling',
    title: 'Architecting Intelligent Systems',
    desc: 'Designing custom Machine Learning algorithms, NLP agents, and statistical models tailored for high-accuracy forecasts.',
    tags: ['PyTorch', 'Scikit-Learn', 'Feature Eng', 'XGBoost'],
    icon: '🧠',
  },
  {
    step: '03',
    phase: 'Full-Stack Development',
    title: 'Building Interactive Interfaces',
    desc: 'Crafting responsive web applications, interactive dashboards, and WebGL visualizations with smooth 60fps animations.',
    tags: ['React', 'Three.js', 'FastAPI', 'GSAP'],
    icon: '⚡',
  },
  {
    step: '04',
    phase: 'Deployment & MLOps',
    title: 'Scaling & Continuous Care',
    desc: 'Containerizing services with Docker, deploying to AWS cloud infrastructure, and configuring real-time telemetry monitoring.',
    tags: ['Docker', 'AWS', 'CI/CD', 'Telemetry'],
    icon: '🌐',
  },
]

export const TERMINAL_COMMANDS = {
  help: `Available commands:
  - about          : View summary bio & background
  - skills         : Display core tech stack & proficiency
  - projects       : List featured open-source repositories & apps
  - run-ml-demo    : Simulate real-time predictive model inference
  - contact        : Fetch direct communication channels
  - clear          : Clear terminal screen`,

  about: `Sourav Biswas — Business & Data Analyst / AI & Full-Stack Developer
  Location : Pune, Maharashtra, India
  Focus    : Data Engineering, ML Pipelines, High-Impact Web Apps
  Status   : Available for freelance, remote contracts & strategic roles.`,

  skills: `=== TECHNICAL ECOSYSTEM ===
  • Data & Analytics  : Python (96%), SQL (92%), Pandas/NumPy (94%), Tableau
  • AI & Machine Learning: Scikit-learn (95%), PyTorch (88%), TensorFlow (90%), FastAPI
  • Web & Visuals     : React (86%), Three.js/WebGL, GSAP, Anime.js, CSS3/Tailwind`,

  projects: `=== FEATURED REPOSITORIES ===
  1. Claude Guardian [AI Safety Sandbox] -> github.com/souravjr0/Claude-guardian
  2. Zunes Wallet    [Web3 Crypto UI]   -> github.com/souravjr0/Zunes-wallet
  3. Cluely          [AI Interview Prep]-> github.com/souravjr0/Cluely
  4. Habit Tracker   [Browser App]      -> github.com/souravjr0/Habit-Tracker`,

  'run-ml-demo': `[INIT] Loading model checkpoint 'neural_forecast_v4.pkl'...
[DATA] Ingesting 10,000 real-time telemetry events...
[PROC] Feature vectorization complete (latency: 1.2ms)
[PRED] Confidence Score: 98.4% | Risk Index: LOW | Outcome: OPTIMIZED
[SUCCESS] Execution pipeline completed in 0.042 seconds! ✨`,

  contact: `=== GET IN TOUCH ===
  Email    : biswasmail631@gmail.com
  LinkedIn : linkedin.com/in/sourav-biswas-260b08201
  GitHub   : github.com/souravjr0
  Twitter  : x.com/Souravjr0`,
}

export const SERVICES = [
  {
    id: '01',
    title: 'Data Analytics & BI',
    description:
      'End-to-end analytics pipelines, real-time dashboards, and reporting automation that surface actionable insights for executive decisions.',
    checklist: ['Automated BI Dashboards', 'Statistical EDA & Cohort Analysis', 'Custom SQL ETL Pipelines'],
    tags: ['Python', 'SQL', 'Tableau', 'Pandas'],
    gradient: 'linear-gradient(135deg, rgba(0, 240, 255, 0.12), rgba(112, 0, 255, 0.05))',
    accentColor: '#00f0ff',
  },
  {
    id: '02',
    title: 'AI & Machine Learning',
    description:
      'Predictive analytics, NLP agents, and computer vision algorithms trained, evaluated, and deployed with robust monitoring pipelines.',
    checklist: ['Predictive Classification & Regression', 'LLM Guardrails & Prompt Safety', 'Model Evaluation & Optimization'],
    tags: ['PyTorch', 'TensorFlow', 'Scikit-Learn', 'MLOps'],
    gradient: 'linear-gradient(135deg, rgba(112, 0, 255, 0.12), rgba(0, 255, 157, 0.05))',
    accentColor: '#7000ff',
  },
  {
    id: '03',
    title: 'Interactive Web Apps',
    description:
      'Full-stack React applications, portfolio experiences, and product landing pages powered by Three.js WebGL, Anime.js, and smooth scroll.',
    checklist: ['High-Performance React Frameworks', '3D WebGL Canvas & Particle FX', 'Kinetic Typography & Smooth Scroll'],
    tags: ['React', 'Three.js', 'Anime.js', 'GSAP'],
    gradient: 'linear-gradient(135deg, rgba(0, 255, 157, 0.12), rgba(0, 240, 255, 0.05))',
    accentColor: '#00ff9d',
  },
  {
    id: '04',
    title: 'API Integration & Cloud',
    description:
      'High-throughput REST/GraphQL APIs, microservice containers, and cloud deployments built for reliability and zero-downtime scaling.',
    checklist: ['FastAPI & Node.js Backend', 'Docker Containerization', 'AWS Cloud Infrastructure'],
    tags: ['FastAPI', 'Docker', 'AWS', 'REST APIs'],
    gradient: 'linear-gradient(135deg, rgba(0, 240, 255, 0.10), rgba(112, 0, 255, 0.10))',
    accentColor: '#00f0ff',
  },
]

export const PROJECTS = [
  {
    id: 'claude-guardian',
    tag: 'AI Safety & Security',
    title: 'Claude Guardian',
    subtitle: 'LLM Prompt Injection & Jailbreak Defense Sandbox',
    description:
      'An automated evaluation framework designed to audit Large Language Models against adversary prompt injections, hallucination exploits, and jailbreak vectors in real-time.',
    highlights: ['99.2% Threat Detection Rate', 'Automated Adversary Benchmarks', 'Zero-Latency Inspection Hook'],
    stack: ['Python', 'AI Safety', 'LLM Benchmarks', 'FastAPI'],
    url: 'https://github.com/souravjr0/Claude-guardian',
    demoUrl: 'https://github.com/souravjr0/Claude-guardian',
    gradient: 'linear-gradient(135deg, rgba(0, 240, 255, 0.15), rgba(112, 0, 255, 0.08))',
    accentColor: '#00f0ff',
  },
  {
    id: 'zunes-wallet',
    tag: 'Web3 & Fintech',
    title: 'Zunes Wallet',
    subtitle: 'Decentralized Ethereum Assets Hub',
    description:
      'A sleek, high-security Web3 crypto wallet dashboard featuring real-time ERC-20 token tracking, visual transaction history, and seamless wallet connectivity.',
    highlights: ['Multi-Chain Portfolio View', 'Sub-Second Gas Fee Estimation', 'Responsive Glassmorphism UI'],
    stack: ['Ethereum', 'Web3.js', 'React', 'UI Design'],
    url: 'https://github.com/souravjr0/Zunes-wallet',
    demoUrl: 'https://github.com/souravjr0/Zunes-wallet',
    gradient: 'linear-gradient(135deg, rgba(112, 0, 255, 0.15), rgba(0, 255, 157, 0.08))',
    accentColor: '#7000ff',
  },
  {
    id: 'cluely',
    tag: 'AI Productivity',
    title: 'Cluely',
    subtitle: 'Smart AI Interview Simulator & Feedback Engine',
    description:
      'An interactive AI interview preparation coach that evaluates audio and text responses, offering instant granular feedback on communication clarity and technical accuracy.',
    highlights: ['Real-time Sentiment Analysis', 'Custom Technical Question Banks', 'Instant Score Breakdown'],
    stack: ['Python', 'NLP', 'React', 'Tailwind'],
    url: 'https://github.com/souravjr0/Cluely',
    demoUrl: 'https://github.com/souravjr0/Cluely',
    gradient: 'linear-gradient(135deg, rgba(0, 255, 157, 0.15), rgba(0, 240, 255, 0.08))',
    accentColor: '#00ff9d',
  },
  {
    id: 'habit-tracker',
    tag: 'Browser App',
    title: 'Habit Tracker',
    subtitle: 'Zero-Latency Local Growth System',
    description:
      'A minimal, privacy-first habit building application with local storage persistence, streak heatmaps, and customizable routine analytics.',
    highlights: ['100% Local Privacy', 'GitHub-Style Activity Heatmap', 'Offline-First PWA Support'],
    stack: ['JavaScript', 'LocalStorage', 'CSS Grid', 'PWA'],
    url: 'https://github.com/souravjr0/Habit-Tracker',
    demoUrl: 'https://github.com/souravjr0/Habit-Tracker',
    gradient: 'linear-gradient(135deg, rgba(0, 240, 255, 0.10), rgba(0, 255, 157, 0.10))',
    accentColor: '#00f0ff',
  },
]

export const SKILL_CATEGORIES = [
  {
    id: 'data-analytics',
    kicker: 'Data Engineering & Insight',
    title: 'Reading patterns in high-dimensional noise',
    skills: [
      { name: 'Python', level: 96, label: 'Expert' },
      { name: 'SQL', level: 92, label: 'Advanced' },
      { name: 'Pandas & NumPy', level: 94, label: 'Expert' },
      { name: 'Tableau & BI', level: 88, label: 'Proficient' },
    ],
    chips: ['Matplotlib', 'Seaborn', 'Plotly', 'ETL Pipelines', 'EDA', 'Cohort Analysis'],
  },
  {
    id: 'ai-ml',
    kicker: 'Artificial Intelligence',
    title: 'Architecting models that learn & predict',
    skills: [
      { name: 'Scikit-learn', level: 95, label: 'Expert' },
      { name: 'TensorFlow', level: 90, label: 'Advanced' },
      { name: 'PyTorch', level: 88, label: 'Advanced' },
      { name: 'FastAPI Backend', level: 86, label: 'Solid' },
    ],
    chips: ['Hugging Face', 'OpenCV', 'Docker', 'AWS S3/EC2', 'Model Fine-tuning', 'MLOps'],
  },
  {
    id: 'web-motion',
    kicker: 'Creative & Motion Web',
    title: 'Giving interfaces a dynamic visual pulse',
    skills: [
      { name: 'React.js', level: 88, label: 'Advanced' },
      { name: 'JavaScript (ES6+)', level: 92, label: 'Expert' },
      { name: 'Anime.js & GSAP', level: 90, label: 'Advanced' },
      { name: 'Three.js / WebGL', level: 82, label: 'Proficient' },
    ],
    chips: ['HTML5/CSS3', 'Vite', 'Responsive Design', 'Tailwind', 'Glassmorphism UI', 'Git/GitHub'],
  },
]

export const SOCIAL_LINKS = [
  { label: 'GitHub', url: 'https://github.com/souravjr0', icon: 'github' },
  { label: 'LinkedIn', url: 'https://www.linkedin.com/in/sourav-biswas-260b08201', icon: 'linkedin' },
  { label: 'Twitter', url: 'https://x.com/Souravjr0', icon: 'twitter' },
]

export const CONTACT_INFO = {
  email: 'biswasmail631@gmail.com',
  linkedin: 'https://www.linkedin.com/in/sourav-biswas-260b08201',
  location: 'Pune, Maharashtra, India',
  availability: 'Open for remote opportunities & high-impact projects',
  formspree: 'https://formspree.io/f/mgopdjol',
}
