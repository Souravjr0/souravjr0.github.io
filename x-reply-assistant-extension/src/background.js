const SETTINGS_KEY = "settings";
const TOKENS_KEY = "oauthTokens";
const PKCE_KEY = "oauthPkce";
const RATE_STATE_KEY = "rateState";

const DEFAULT_SETTINGS = {
  x: {
    clientId: "",
    clientSecret: "",
    scopes:
      "tweet.read tweet.write users.read follows.read follows.write like.read like.write mute.read mute.write block.read block.write bookmark.read bookmark.write list.read list.write offline.access",
    authBaseUrl: "https://twitter.com/i/oauth2/authorize",
    tokenUrl: "https://api.twitter.com/2/oauth2/token",
    apiBaseUrl: "https://api.twitter.com/2"
  },
  llm: {
    provider: "openai",
    apiKey: "",
    baseUrl: "",
    model: "gpt-4.1-mini",
    temperature: 0.7,
    maxTokens: 200
  },
  behavior: {
    tone: "natural",
    maxPostsPerHour: 6,
    cooldownSeconds: 45,
    duplicateWindowMinutes: 30,
    requireConfirmBeforePost: true
  }
};

chrome.runtime.onInstalled.addListener(() => {
  ensureDefaultSettings().catch(() => undefined);
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message)
    .then((data) => sendResponse({ ok: true, data }))
    .catch((error) =>
      sendResponse({
        ok: false,
        error: error instanceof Error ? error.message : String(error)
      })
    );
  return true;
});

async function handleMessage(message) {
  switch (message?.type) {
    case "settings_get":
      return await getSettings();
    case "settings_set":
      return await saveSettings(message.settings);
    case "settings_reset":
      return await resetSettings();
    case "oauth_start":
      return await startOAuthFlow();
    case "oauth_disconnect":
      return await clearTokens();
    case "oauth_status":
      return await getOAuthStatus();
    case "llm_generate":
      return await generateReply(message.payload);
    case "llm_test":
      return await testLlmConnection();
    case "x_test":
      return await testXConnection();
    case "x_post_reply":
      return await postReply(message.payload);
    default:
      throw new Error("Unknown request type.");
  }
}

async function ensureDefaultSettings() {
  const stored = await chrome.storage.local.get(SETTINGS_KEY);
  if (!stored[SETTINGS_KEY]) {
    await chrome.storage.local.set({ [SETTINGS_KEY]: DEFAULT_SETTINGS });
  }
}

async function getSettings() {
  const stored = await chrome.storage.local.get(SETTINGS_KEY);
  return deepMerge(DEFAULT_SETTINGS, stored[SETTINGS_KEY] || {});
}

async function saveSettings(settings) {
  const normalized = normalizeSettings(settings);
  await chrome.storage.local.set({ [SETTINGS_KEY]: normalized });
  return normalized;
}

async function resetSettings() {
  await chrome.storage.local.set({ [SETTINGS_KEY]: DEFAULT_SETTINGS });
  return DEFAULT_SETTINGS;
}

async function getOAuthStatus() {
  const tokens = await getTokens();
  return {
    connected: Boolean(tokens?.access_token),
    expiresAt: tokens?.expires_at || null,
    scope: tokens?.scope || null
  };
}

async function clearTokens() {
  await chrome.storage.local.remove(TOKENS_KEY);
  return { cleared: true };
}

async function startOAuthFlow() {
  const settings = await getSettings();
  if (!settings.x.clientId) {
    throw new Error("Missing X client ID in settings.");
  }

  const redirectUri = chrome.identity.getRedirectURL("x-oauth");
  const codeVerifier = generateRandomString(96);
  const codeChallenge = await sha256Base64Url(codeVerifier);
  const state = generateRandomString(32);

  await chrome.storage.local.set({
    [PKCE_KEY]: { codeVerifier, state, redirectUri }
  });

  const authUrl = new URL(settings.x.authBaseUrl);
  authUrl.searchParams.set("response_type", "code");
  authUrl.searchParams.set("client_id", settings.x.clientId);
  authUrl.searchParams.set("redirect_uri", redirectUri);
  authUrl.searchParams.set("scope", settings.x.scopes);
  authUrl.searchParams.set("state", state);
  authUrl.searchParams.set("code_challenge", codeChallenge);
  authUrl.searchParams.set("code_challenge_method", "S256");

  const redirectResponse = await chrome.identity.launchWebAuthFlow({
    url: authUrl.toString(),
    interactive: true
  });

  const returned = new URL(redirectResponse);
  const returnedState = returned.searchParams.get("state");
  const code = returned.searchParams.get("code");
  const error = returned.searchParams.get("error");

  if (error) {
    throw new Error(`OAuth error: ${error}`);
  }
  if (!code) {
    throw new Error("OAuth code missing in redirect.");
  }

  const pkce = (await chrome.storage.local.get(PKCE_KEY))[PKCE_KEY];
  if (!pkce || pkce.state !== returnedState) {
    throw new Error("OAuth state mismatch.");
  }

  const tokenData = await exchangeCodeForToken(code, pkce.codeVerifier, pkce.redirectUri);
  await chrome.storage.local.remove(PKCE_KEY);
  await saveTokens(tokenData);
  return { connected: true, scope: tokenData.scope };
}

async function exchangeCodeForToken(code, codeVerifier, redirectUri) {
  const settings = await getSettings();
  const body = new URLSearchParams();
  body.set("grant_type", "authorization_code");
  body.set("client_id", settings.x.clientId);
  body.set("code", code);
  body.set("redirect_uri", redirectUri);
  body.set("code_verifier", codeVerifier);

  const headers = { "Content-Type": "application/x-www-form-urlencoded" };
  if (settings.x.clientSecret) {
    headers.Authorization = `Basic ${btoa(
      `${settings.x.clientId}:${settings.x.clientSecret}`
    )}`;
  }

  const response = await fetch(settings.x.tokenUrl, {
    method: "POST",
    headers,
    body
  });
  const json = await response.json();
  if (!response.ok) {
    throw new Error(json?.error_description || json?.error || "Token exchange failed.");
  }
  return json;
}

async function refreshTokenIfNeeded() {
  const tokens = await getTokens();
  if (!tokens?.access_token) {
    throw new Error("Not connected to X. Please run OAuth first.");
  }
  if (!tokens.expires_at || tokens.expires_at > Date.now() + 60000) {
    return tokens;
  }
  if (!tokens.refresh_token) {
    return tokens;
  }

  const settings = await getSettings();
  const body = new URLSearchParams();
  body.set("grant_type", "refresh_token");
  body.set("refresh_token", tokens.refresh_token);
  body.set("client_id", settings.x.clientId);

  const headers = { "Content-Type": "application/x-www-form-urlencoded" };
  if (settings.x.clientSecret) {
    headers.Authorization = `Basic ${btoa(
      `${settings.x.clientId}:${settings.x.clientSecret}`
    )}`;
  }

  const response = await fetch(settings.x.tokenUrl, {
    method: "POST",
    headers,
    body
  });
  const json = await response.json();
  if (!response.ok) {
    throw new Error(json?.error_description || json?.error || "Token refresh failed.");
  }
  await saveTokens(json);
  return await getTokens();
}

async function saveTokens(tokenData) {
  const expiresIn = Number(tokenData.expires_in || 0);
  const tokenPayload = {
    ...tokenData,
    expires_at: expiresIn ? Date.now() + Math.max(expiresIn - 60, 0) * 1000 : null
  };
  await chrome.storage.local.set({ [TOKENS_KEY]: tokenPayload });
  return tokenPayload;
}

async function getTokens() {
  const stored = await chrome.storage.local.get(TOKENS_KEY);
  return stored[TOKENS_KEY] || null;
}

async function postReply(payload) {
  if (!payload?.text || !payload?.tweetId) {
    throw new Error("Missing tweet ID or reply text.");
  }
  const settings = await getSettings();
  if (settings.behavior.requireConfirmBeforePost && !payload?.confirmed) {
    throw new Error("Posting requires confirmation.");
  }
  await enforceGuardrails(payload.text, settings.behavior);
  const tokens = await refreshTokenIfNeeded();

  const response = await fetch(`${settings.x.apiBaseUrl}/tweets`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${tokens.access_token}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      text: payload.text,
      reply: { in_reply_to_tweet_id: payload.tweetId }
    })
  });

  const json = await response.json();
  if (!response.ok) {
    throw new Error(json?.detail || json?.title || "Posting failed.");
  }

  await recordPost(payload.text);
  return json;
}

async function testXConnection() {
  const settings = await getSettings();
  const tokens = await refreshTokenIfNeeded();
  const response = await fetch(`${settings.x.apiBaseUrl}/users/me`, {
    headers: { Authorization: `Bearer ${tokens.access_token}` }
  });
  const json = await response.json();
  if (!response.ok) {
    throw new Error(json?.detail || "X connection test failed.");
  }
  return json;
}

async function generateReply(payload) {
  const settings = await getSettings();
  const provider = settings.llm.provider;
  if (!settings.llm.apiKey) {
    throw new Error("Missing LLM API key in settings.");
  }
  if (provider === "custom" && !settings.llm.baseUrl) {
    throw new Error("Custom provider requires a base URL.");
  }

  const request = {
    prompt: payload?.prompt || "",
    system: payload?.system || "",
    temperature: settings.llm.temperature,
    maxTokens: settings.llm.maxTokens,
    model: settings.llm.model
  };

  if (!request.prompt) {
    throw new Error("Prompt is empty.");
  }

  if (provider === "anthropic") {
    return await callAnthropic(settings.llm, request);
  }
  if (provider === "google") {
    return await callGemini(settings.llm, request);
  }

  return await callOpenAiCompatible(settings.llm, request);
}

async function testLlmConnection() {
  const settings = await getSettings();
  return await generateReply({
    prompt: "Reply with the single word OK.",
    system: "You are a concise assistant."
  });
}

async function callOpenAiCompatible(llmSettings, request) {
  const provider = llmSettings.provider;
  let baseUrl = llmSettings.baseUrl?.trim();
  if (!baseUrl) {
    if (provider === "nvidia") {
      baseUrl = "https://integrate.api.nvidia.com/v1";
    } else {
      baseUrl = "https://api.openai.com/v1";
    }
  }

  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${llmSettings.apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model: request.model,
      messages: [
        { role: "system", content: request.system },
        { role: "user", content: request.prompt }
      ],
      temperature: request.temperature,
      max_tokens: request.maxTokens
    })
  });

  const json = await response.json();
  if (!response.ok) {
    throw new Error(json?.error?.message || "LLM request failed.");
  }
  const content = json?.choices?.[0]?.message?.content?.trim();
  if (!content) {
    throw new Error("LLM response was empty.");
  }
  return content;
}

async function callAnthropic(llmSettings, request) {
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": llmSettings.apiKey,
      "anthropic-version": "2023-06-01",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model: request.model || "claude-3-5-sonnet-20240620",
      max_tokens: request.maxTokens,
      temperature: request.temperature,
      system: request.system,
      messages: [{ role: "user", content: request.prompt }]
    })
  });

  const json = await response.json();
  if (!response.ok) {
    throw new Error(json?.error?.message || "Anthropic request failed.");
  }
  const content = json?.content?.[0]?.text?.trim();
  if (!content) {
    throw new Error("LLM response was empty.");
  }
  return content;
}

async function callGemini(llmSettings, request) {
  const model = request.model || "gemini-1.5-pro";
  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(
      model
    )}:generateContent?key=${encodeURIComponent(llmSettings.apiKey)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [
          {
            role: "user",
            parts: [{ text: `${request.system}\n\n${request.prompt}` }]
          }
        ],
        generationConfig: {
          temperature: request.temperature,
          maxOutputTokens: request.maxTokens
        }
      })
    }
  );

  const json = await response.json();
  if (!response.ok) {
    throw new Error(json?.error?.message || "Gemini request failed.");
  }
  const content = json?.candidates?.[0]?.content?.parts?.[0]?.text?.trim();
  if (!content) {
    throw new Error("LLM response was empty.");
  }
  return content;
}

async function enforceGuardrails(text, behavior) {
  const now = Date.now();
  const rateState = (await chrome.storage.session.get(RATE_STATE_KEY))[RATE_STATE_KEY] || {
    posts: [],
    lastPostAt: 0,
    lastTexts: []
  };

  if (behavior.cooldownSeconds) {
    const diff = now - (rateState.lastPostAt || 0);
    if (diff < behavior.cooldownSeconds * 1000) {
      const remaining = Math.ceil((behavior.cooldownSeconds * 1000 - diff) / 1000);
      throw new Error(`Cooldown active. Try again in ${remaining}s.`);
    }
  }

  const oneHourAgo = now - 60 * 60 * 1000;
  const recentPosts = rateState.posts.filter((timestamp) => timestamp > oneHourAgo);
  if (behavior.maxPostsPerHour && recentPosts.length >= behavior.maxPostsPerHour) {
    throw new Error("Hourly posting limit reached.");
  }

  const normalizedText = normalizeText(text);
  if (behavior.duplicateWindowMinutes) {
    const windowStart = now - behavior.duplicateWindowMinutes * 60 * 1000;
    const recentTexts = rateState.lastTexts.filter((entry) => entry.time > windowStart);
    if (recentTexts.some((entry) => entry.text === normalizedText)) {
      throw new Error("Duplicate reply detected within the configured window.");
    }
  }
}

async function recordPost(text) {
  const now = Date.now();
  const rateState = (await chrome.storage.session.get(RATE_STATE_KEY))[RATE_STATE_KEY] || {
    posts: [],
    lastPostAt: 0,
    lastTexts: []
  };
  const normalizedText = normalizeText(text);
  rateState.posts = [...rateState.posts, now].slice(-200);
  rateState.lastPostAt = now;
  rateState.lastTexts = [
    { time: now, text: normalizedText },
    ...rateState.lastTexts
  ].slice(0, 50);
  await chrome.storage.session.set({ [RATE_STATE_KEY]: rateState });
}

function normalizeText(text) {
  return text.toLowerCase().replace(/\s+/g, " ").trim();
}

function normalizeSettings(settings) {
  const merged = deepMerge(DEFAULT_SETTINGS, settings || {});
  merged.behavior.maxPostsPerHour = clampNumber(merged.behavior.maxPostsPerHour, 1, 60);
  merged.behavior.cooldownSeconds = clampNumber(merged.behavior.cooldownSeconds, 0, 3600);
  merged.behavior.duplicateWindowMinutes = clampNumber(
    merged.behavior.duplicateWindowMinutes,
    0,
    1440
  );
  merged.llm.temperature = clampNumber(merged.llm.temperature, 0, 2);
  merged.llm.maxTokens = clampNumber(merged.llm.maxTokens, 50, 2000);
  merged.x.scopes = (merged.x.scopes || "").trim();
  merged.llm.baseUrl = (merged.llm.baseUrl || "").trim();
  return merged;
}

function clampNumber(value, min, max) {
  const num = Number(value);
  if (Number.isNaN(num)) return min;
  return Math.min(Math.max(num, min), max);
}

function deepMerge(base, override) {
  if (!override) return structuredClone(base);
  const output = Array.isArray(base) ? [...base] : { ...base };
  Object.keys(base).forEach((key) => {
    if (base[key] && typeof base[key] === "object" && !Array.isArray(base[key])) {
      output[key] = deepMerge(base[key], override[key] || {});
    } else {
      output[key] = override[key] !== undefined ? override[key] : base[key];
    }
  });
  Object.keys(override || {}).forEach((key) => {
    if (output[key] === undefined) {
      output[key] = override[key];
    }
  });
  return output;
}

function generateRandomString(length) {
  const charset =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
  const values = crypto.getRandomValues(new Uint8Array(length));
  return Array.from(values, (v) => charset[v % charset.length]).join("");
}

async function sha256Base64Url(input) {
  const data = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", data);
  const bytes = Array.from(new Uint8Array(digest));
  const b64 = btoa(String.fromCharCode(...bytes));
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
