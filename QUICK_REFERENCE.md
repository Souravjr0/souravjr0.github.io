# 🎯 Customization Quick Reference

**Fast lookup guide** - Find what you need to change in 10 seconds!

---

## Find Your Section Quickly

### In VS Code:
```
Press Ctrl+F (Cmd+F on Mac)
Search for one of these:

<!-- ===== SKILLS PROFICIENCY ===== -->
<!-- ===== EXPERIENCE TIMELINE ===== -->
<!-- ===== CERTIFICATIONS ===== -->
<!-- ===== ACHIEVEMENTS STATS ===== -->
```

---

## 🔴 Find & Replace Examples

### Example 1: Update a Skill Card

**Find this:**
```html
<div class="skill-card">
  <h3>Machine Learning</h3>
  <p>Supervised & unsupervised learning, model selection, hyperparameter tuning, ensemble methods</p>
  <div class="skill-bar">
    <div class="skill-bar-fill" style="width: 92%; --delay: 0;"></div>
    <span class="skill-level">92%</span>
  </div>
  <div class="skill-tags">
    <span class="tag">Scikit-learn</span>
    <span class="tag">XGBoost</span>
  </div>
</div>
```

**Replace with your skill:**
```html
<div class="skill-card">
  <h3>Natural Language Processing</h3>
  <p>Text preprocessing, sentiment analysis, transformer models, fine-tuning language models, RAG systems</p>
  <div class="skill-bar">
    <div class="skill-bar-fill" style="width: 88%; --delay: 0;"></div>
    <span class="skill-level">88%</span>
  </div>
  <div class="skill-tags">
    <span class="tag">Transformers</span>
    <span class="tag">BERT</span>
    <span class="tag">LLMs</span>
  </div>
</div>
```

### Example 2: Update a Timeline Entry

**Find this:**
```html
<div class="timeline-item">
  <div class="timeline-marker"></div>
  <div class="timeline-content">
    <h3>Advanced ML Engineer</h3>
    <p class="timeline-date">2024 - Present</p>
    <p class="timeline-desc">Leading AI/ML initiatives, building production ML systems, and mentoring team members</p>
    <ul class="timeline-highlights">
      <li>Deployed 5+ models in production</li>
      <li>Reduced inference latency by 70%</li>
      <li>Mentored 3 junior engineers</li>
    </ul>
  </div>
</div>
```

**Replace with your experience:**
```html
<div class="timeline-item">
  <div class="timeline-marker"></div>
  <div class="timeline-content">
    <h3>ML Engineer at StartupXYZ</h3>
    <p class="timeline-date">July 2023 - Present</p>
    <p class="timeline-desc">Built recommendation engine processing 5M+ user interactions daily with 94% accuracy</p>
    <ul class="timeline-highlights">
      <li>Improved recommendation CTR by 35% via collaborative filtering</li>
      <li>Reduced model training time from 6h to 45min</li>
      <li>Set up real-time monitoring reducing model drift by 80%</li>
    </ul>
  </div>
</div>
```

### Example 3: Update a Certification

**Find this:**
```html
<div class="cert-card">
  <div class="cert-icon">📊</div>
  <h3>Google Cloud Professional Data Engineer</h3>
  <p>Managing and building data solutions on Google Cloud including BigQuery, Dataflow, Cloud Storage</p>
  <span class="cert-badge">Verified</span>
</div>
```

**Replace with your certification:**
```html
<div class="cert-card">
  <div class="cert-icon">🤖</div>
  <h3>DeepLearning.AI - LLM Application Developer</h3>
  <p>Building serverless LLM applications using Claude, RAG, function calling, and prompt engineering</p>
  <span class="cert-badge">Verified</span>
</div>
```

### Example 4: Update Statistics

**Find this:**
```html
<div class="stat-item">
  <div class="stat-number">20+</div>
  <div class="stat-label">Projects Completed</div>
</div>
```

**Replace with your number:**
```html
<div class="stat-item">
  <div class="stat-number">35+</div>
  <div class="stat-label">Data Science Projects</div>
</div>
```

---

## ⚡ Most Common Changes

### Change 1: Update Skill Percentage
- Find: `width: 92%` 
- Replace: `width: YOUR_PERCENT%`
- Also find: `<span class="skill-level">92%</span>`
- Replace: `<span class="skill-level">YOUR_PERCENT%</span>`

### Change 2: Update Skill Delay (to maintain cascade effect)
- 1st card: `--delay: 0;`
- 2nd card: `--delay: 0.1s;`
- 3rd card: `--delay: 0.2s;`
- 4th card: `--delay: 0.3s;`
- 5th card: `--delay: 0.4s;`
- 6th card: `--delay: 0.5s;`

### Change 3: Update Timeline Dates
- Find: `<p class="timeline-date">2020 - 2022</p>`
- Replace: `<p class="timeline-date">Jan 2020 - Dec 2022</p>`

### Change 4: Update Achievement Numbers
- Find: `<div class="stat-number">20+</div>`
- Replace: `<div class="stat-number">25+</div>`

---

## 🎨 Color/Style Changes

### If you want to change skill bar color:

**Find in style.css:**
```css
.skill-bar-fill {
  background: var(--grad);
```

**Options to try:**
```css
/* Blue gradient */
background: linear-gradient(45deg, #3B82F6, #0EA5E9);

/* Purple gradient */
background: linear-gradient(45deg, #8B5CF6, #D946EF);

/* Green gradient */
background: linear-gradient(45deg, #10B981, #14B8A6);

/* Orange gradient */
background: linear-gradient(45deg, #F97316, #FB923C);

/* Single color */
background: #6AD3F7;
```

---

## 📋 Verification Checklist

After each change, verify:

- [ ] Closing tags match (`</div>` for `<div>`)
- [ ] Quotes are matched (`""` or `''`)
- [ ] All percentage signs have `%` sign
- [ ] All delays follow pattern (0, 0.1s, 0.2s, etc.)
- [ ] No extra/missing commas in HTML attributes
- [ ] Emoji characters display correctly
- [ ] Text isn't cut off (reasonable length)
- [ ] Links work (if you added any)

**How to verify:**
1. Save file (Ctrl+S)
2. Open website in browser
3. Scroll to see your new content
4. Check layout looks good
5. Test on mobile (Ctrl+Shift+M in Chrome)

---

## 🚨 Common Mistakes to Avoid

### ❌ Mistake 1: Unmatched Quotes
```html
<!-- WRONG -->
<h3>My Skill Name</h3>  <!-- Missing closing quote -->
<p class="timeline-date>2024</p>

<!-- RIGHT -->
<h3>My Skill Name</h3>
<p class="timeline-date">2024</p>
```

### ❌ Mistake 2: Forgetting Closing Tags
```html
<!-- WRONG -->
<div class="skill-card">
  <h3>Skill Name
</div>

<!-- RIGHT -->
<div class="skill-card">
  <h3>Skill Name</h3>
</div>
```

### ❌ Mistake 3: Breaking the Cascade
```html
<!-- WRONG - breaks animation delay pattern -->
<div class="skill-bar">
  <div class="skill-bar-fill" style="width: 85%; --delay: 0.7s;"></div>
</div>

<!-- RIGHT - keeps it in order -->
<div class="skill-bar">
  <div class="skill-bar-fill" style="width: 85%; --delay: 0.2s;"></div>
</div>
```

### ❌ Mistake 4: Changing Percentages > 100%
```html
<!-- WRONG -->
<span class="skill-level">150%</span>

<!-- RIGHT -->
<span class="skill-level">95%</span>
```

---

## 🆘 If Something Breaks

### Step 1: Undo
```
Press Ctrl+Z (Cmd+Z) to undo your last change
```

### Step 2: Check for errors
```
1. Look for red squiggly lines (syntax errors)
2. Check VS Code "Problems" tab (Ctrl+Shift+M)
3. Make sure all tags are closed
```

### Step 3: Compare with original
```
1. Open the template from CUSTOMIZATION_GUIDE.md
2. Compare your code line-by-line
3. Fix any mismatches
```

### Step 4: Test in browser
```
1. Save file (Ctrl+S)
2. Open GitHub Pages URL
3. Hard refresh (Ctrl+Shift+R)
4. Check if it looks right
```

---

## 📱 Test Checklist

After customizing, test on:

- [ ] **Desktop**: Full width browser
- [ ] **Mobile**: Shrink browser to 375px width
- [ ] **Tablet**: 768px width
- [ ] **Different browsers**: Chrome, Firefox, Safari
- [ ] **Different devices**: Phone, iPad, laptop

**Quick mobile test:**
1. Open your website
2. Press F12 to open Developer Tools
3. Click device toolbar icon (or Ctrl+Shift+M)
4. Select iPhone SE or similar
5. Scroll and check animations work

---

## 🎯 Next Steps

1. **Read CUSTOMIZATION_GUIDE.md** for detailed instructions
2. **Make your first change** (update one skill)
3. **Test in browser** (go to your portfolio, hard refresh)
4. **Keep going** (update all sections)
5. **Push to GitHub** (git add ., git commit, git push)
6. **Watch it live** (refresh your portfolio in 1-2 minutes)

---

## 🆕 Adding New Cards

### To add a 7th skill:
1. Copy the entire `<div class="skill-card">` block
2. Paste it at the end of the skills-grid
3. Update the content AND the `--delay` value
4. New card delay should be: `--delay: 0.5s;`

### To add a 5th timeline entry:
1. Copy the entire `<div class="timeline-item">` block
2. Paste it at the end of the timeline
3. Update the date, title, and achievements
4. Animation will automatically apply!

### To add a 7th certification:
1. Copy the entire `<div class="cert-card">` block
2. Paste it at the end of certifications-grid
3. Update emoji, title, and description
4. It will automatically animate on scroll!

---

## 📞 Quick Reference Summary

| What | Where | How |
|------|-------|-----|
| Change skill % | In `width: 92%` and `>92%<` | Update both numbers |
| Change timeline dates | In `<p class="timeline-date">` | Update the date range |
| Change achievement #s | In `<div class="stat-number">` | Update the number |
| Change skill tags | In `<span class="tag">` | Update each tag |
| Add new skill | Copy skill-card block | Paste and customize |
| Add new timeline | Copy timeline-item block | Paste and customize |
| Remove section | Select entire block | Delete and save |
| Change colors | In style.css | Update background/gradient |

---

Keep this handy! Happy customizing! 🎉
