(() => {
  const PANEL_ATTR = "data-xra-panel";
  const COMPOSER_ATTR = "data-xra-composer-id";
  const COMPOSER_SELECTOR =
    'div[contenteditable="true"][data-testid^="tweetTextarea_"]';

  init();

  function init() {
    observeComposer();
    setInterval(attachToComposer, 2000);
  }

  function observeComposer() {
    const observer = new MutationObserver(() => attachToComposer());
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function attachToComposer() {
    const composers = document.querySelectorAll(COMPOSER_SELECTOR);
    composers.forEach((composer) => {
      if (!composer.isConnected) return;
      if (!composer.getAttribute(COMPOSER_ATTR)) {
        composer.setAttribute(COMPOSER_ATTR, generateId());
      }
      const composerId = composer.getAttribute(COMPOSER_ATTR);
      const host = findPanelHost(composer);
      if (!host) return;
      if (host.querySelector(`[${PANEL_ATTR}][data-xra-for="${composerId}"]`)) {
        return;
      }
      const panel = createPanel(composerId);
      host.appendChild(panel);
    });
  }

  function createPanel(composerId) {
    const panel = document.createElement("div");
    panel.setAttribute(PANEL_ATTR, "true");
    panel.setAttribute("data-xra-for", composerId);
    panel.className = "xra-panel";

    panel.innerHTML = `
      <div class="xra-header">
        <div class="xra-title">Reply Assistant</div>
        <button class="xra-link" data-action="open-options">Settings</button>
      </div>
      <div class="xra-status" data-role="status">Loading status...</div>
      <textarea class="xra-textarea" data-role="draft" rows="3" placeholder="Generate a reply draft..."></textarea>
      <div class="xra-actions">
        <button class="xra-btn" data-action="generate">Generate</button>
        <button class="xra-btn" data-action="insert">Insert</button>
        <button class="xra-btn xra-primary" data-action="post">Post</button>
      </div>
    `;

    panel.addEventListener("click", onPanelClick);
    panel.addEventListener("click", stopEventPropagation);
    panel.addEventListener("keydown", stopEventPropagation);
    refreshStatus(panel).catch(() => undefined);
    return panel;
  }

  async function onPanelClick(event) {
    const button = event.target.closest("button");
    if (!button) return;
    const action = button.getAttribute("data-action");
    if (!action) return;

    const panel = button.closest(`div[${PANEL_ATTR}]`);
    const statusEl = panel.querySelector('[data-role="status"]');
    const draftEl = panel.querySelector('[data-role="draft"]');
    const composer = getComposerForPanel(panel);

    try {
      if (action === "open-options") {
        chrome.runtime.openOptionsPage();
        return;
      }
      if (action === "generate") {
        setStatus(statusEl, "Generating reply...");
        const context = getTweetContext(composer);
        const settings = await getSettings();
        const { system, prompt } = buildPrompt(context, settings);
        const reply = await sendMessage({
          type: "llm_generate",
          payload: { system, prompt }
        });
        draftEl.value = reply;
        setStatus(statusEl, "Draft ready.");
        return;
      }
      if (action === "insert") {
        insertIntoComposer(draftEl.value, composer);
        setStatus(statusEl, "Inserted into composer.");
        return;
      }
      if (action === "post") {
        const settings = await getSettings();
        if (settings.behavior.requireConfirmBeforePost) {
          const confirmed = window.confirm("Post this reply now?");
          if (!confirmed) {
            setStatus(statusEl, "Posting canceled.");
            return;
          }
        }
        const text = draftEl.value.trim();
        if (!text) {
          throw new Error("Draft is empty.");
        }
        await enforceGuardrails(text, settings.behavior);
        insertIntoComposer(text, composer);
        setStatus(statusEl, "Posting via X...");
        await wait(50);
        await clickPostButton(composer);
        await recordPost(text);
        setStatus(statusEl, "Reply posted via X UI.");
        return;
      }
    } catch (error) {
      setStatus(statusEl, error instanceof Error ? error.message : String(error));
    }
  }

  async function refreshStatus(panel) {
    const statusEl = panel.querySelector('[data-role="status"]');
    const settings = await getSettings();
    const llmConfigured = Boolean(settings.llm.apiKey);

    setStatus(
      statusEl,
      `LLM: ${llmConfigured ? settings.llm.provider : "missing key"} | Posting: X UI`
    );
  }

  function setStatus(el, text) {
    if (el) el.textContent = text;
  }

  function insertIntoComposer(text, composer) {
    if (!composer) throw new Error("Reply composer not found.");
    composer.focus();
    ensureSelection(composer);
    const inserted = document.execCommand("insertText", false, text);
    if (!inserted) {
      composer.textContent = text;
    }
    composer.dispatchEvent(
      new InputEvent("input", {
        bubbles: true,
        data: text,
        inputType: "insertText"
      })
    );
  }

  async function clickPostButton(composer) {
    if (!composer) throw new Error("Reply composer not found.");
    const form = composer?.closest("form");
    const button =
      form?.querySelector('[data-testid="tweetButtonInline"]') ||
      form?.querySelector('[data-testid="tweetButton"]') ||
      null;

    if (!button) {
      throw new Error("Post button not found. Open a full reply composer.");
    }
    if (button.disabled || button.getAttribute("aria-disabled") === "true") {
      throw new Error("Post button is disabled. Check your draft content.");
    }
    button.click();
  }

  function getTweetContext(composer) {
    let article = null;
    const scope =
      composer?.closest('div[role="dialog"]') ||
      composer?.closest("section") ||
      composer?.closest("main") ||
      document;
    article = scope.querySelector("article");

    const tweetText = article
      ? Array.from(article.querySelectorAll('[data-testid="tweetText"]'))
          .map((el) => el.innerText.trim())
          .filter(Boolean)
          .join("\n")
      : "";
    const author =
      article?.querySelector('[data-testid="User-Name"] span')?.innerText || "";

    const link =
      article?.querySelector('a[href*="/status/"]')?.getAttribute("href") || "";
    const match = link.match(/status\/(\d+)/);
    const tweetId = match ? match[1] : null;

    return { tweetText, author, tweetId };
  }

  function buildPrompt(context, settings) {
    const system =
      "You draft human-like replies for X. Follow X rules and avoid harassment, spam, or policy violations.";

    const guidance = [
      "Write a natural, specific reply that shows you understood the tweet.",
      "Prefer meaningful engagement over generic praise.",
      "Keep it concise: 1-2 sentences, no more than one emoji.",
      "Avoid hashtags, excessive mentions, or promotional language.",
      "If a question would genuinely advance the conversation, ask one short question."
    ];

    const algorithmHints = [
      "Favor authenticity, relevance, and respectful tone.",
      "Avoid repetition and low-effort responses."
    ];

    const prompt = [
      `Tweet author: ${context.author || "Unknown"}`,
      `Tweet text: ${context.tweetText || "Unavailable"}`,
      `Desired tone: ${settings.behavior.tone || "natural"}`,
      "Guidance:",
      ...guidance.map((line) => `- ${line}`),
      "Algorithm-informed hints:",
      ...algorithmHints.map((line) => `- ${line}`),
      "Reply draft:"
    ].join("\n");

    return { system, prompt };
  }

  async function getSettings() {
    return await sendMessage({ type: "settings_get" });
  }

  async function enforceGuardrails(text, behavior) {
    const state = await getRateState();
    const now = Date.now();

    if (behavior.cooldownSeconds) {
      const diff = now - (state.lastPostAt || 0);
      if (diff < behavior.cooldownSeconds * 1000) {
        const remaining = Math.ceil((behavior.cooldownSeconds * 1000 - diff) / 1000);
        throw new Error(`Cooldown active. Try again in ${remaining}s.`);
      }
    }

    const oneHourAgo = now - 60 * 60 * 1000;
    const recentPosts = state.posts.filter((timestamp) => timestamp > oneHourAgo);
    if (behavior.maxPostsPerHour && recentPosts.length >= behavior.maxPostsPerHour) {
      throw new Error("Hourly posting limit reached.");
    }

    const normalizedText = normalizeText(text);
    if (behavior.duplicateWindowMinutes) {
      const windowStart = now - behavior.duplicateWindowMinutes * 60 * 1000;
      const recentTexts = state.lastTexts.filter((entry) => entry.time > windowStart);
      if (recentTexts.some((entry) => entry.text === normalizedText)) {
        throw new Error("Duplicate reply detected within the configured window.");
      }
    }
  }

  async function recordPost(text) {
    const state = await getRateState();
    const now = Date.now();
    const normalizedText = normalizeText(text);
    state.posts = [...state.posts, now].slice(-200);
    state.lastPostAt = now;
    state.lastTexts = [{ time: now, text: normalizedText }, ...state.lastTexts].slice(
      0,
      50
    );
    await chrome.storage.session.set({ xraRateState: state });
  }

  async function getRateState() {
    const stored = await chrome.storage.session.get("xraRateState");
    return (
      stored.xraRateState || {
        posts: [],
        lastPostAt: 0,
        lastTexts: []
      }
    );
  }

  function normalizeText(text) {
    return text.toLowerCase().replace(/\s+/g, " ").trim();
  }

  function getComposerForPanel(panel) {
    const id = panel?.getAttribute("data-xra-for");
    if (!id) return null;
    return document.querySelector(`[${COMPOSER_ATTR}="${id}"]`);
  }

  function ensureSelection(composer) {
    const selection = window.getSelection();
    if (!selection) return;
    selection.removeAllRanges();
    const range = document.createRange();
    range.selectNodeContents(composer);
    range.collapse(false);
    selection.addRange(range);
  }

  function findPanelHost(composer) {
    return (
      composer.closest("form") ||
      composer.closest('[role="group"]') ||
      composer.parentElement
    );
  }

  function stopEventPropagation(event) {
    event.stopPropagation();
  }

  function wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function generateId() {
    const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
    let result = "xra-";
    for (let i = 0; i < 8; i += 1) {
      result += chars[Math.floor(Math.random() * chars.length)];
    }
    return result;
  }

  function sendMessage(message) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(message, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        if (!response) {
          reject(new Error("No response from background."));
          return;
        }
        if (!response.ok) {
          reject(new Error(response.error || "Request failed."));
          return;
        }
        resolve(response.data);
      });
    });
  }
})();
