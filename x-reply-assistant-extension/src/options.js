const elements = {
  llmProvider: document.getElementById("llmProvider"),
  llmApiKey: document.getElementById("llmApiKey"),
  llmBaseUrl: document.getElementById("llmBaseUrl"),
  llmModel: document.getElementById("llmModel"),
  llmTemperature: document.getElementById("llmTemperature"),
  llmMaxTokens: document.getElementById("llmMaxTokens"),
  tone: document.getElementById("tone"),
  maxPostsPerHour: document.getElementById("maxPostsPerHour"),
  cooldownSeconds: document.getElementById("cooldownSeconds"),
  duplicateWindowMinutes: document.getElementById("duplicateWindowMinutes"),
  requireConfirmBeforePost: document.getElementById("requireConfirmBeforePost"),
  save: document.getElementById("save"),
  reset: document.getElementById("reset"),
  status: document.getElementById("status"),
  llmTest: document.getElementById("llmTest")
};

init().catch((error) => setStatus(error.message || String(error)));

async function init() {
  elements.save.addEventListener("click", () => safeAction(saveSettings));
  elements.reset.addEventListener("click", () => safeAction(resetSettings));
  elements.llmTest.addEventListener("click", () => safeAction(testLlm));
  await loadSettings();
}

async function loadSettings() {
  const settings = await sendMessage({ type: "settings_get" });
  elements.llmProvider.value = settings.llm.provider || "openai";
  elements.llmApiKey.value = settings.llm.apiKey || "";
  elements.llmBaseUrl.value = settings.llm.baseUrl || "";
  elements.llmModel.value = settings.llm.model || "";
  elements.llmTemperature.value = settings.llm.temperature;
  elements.llmMaxTokens.value = settings.llm.maxTokens;
  elements.tone.value = settings.behavior.tone || "natural";
  elements.maxPostsPerHour.value = settings.behavior.maxPostsPerHour;
  elements.cooldownSeconds.value = settings.behavior.cooldownSeconds;
  elements.duplicateWindowMinutes.value = settings.behavior.duplicateWindowMinutes;
  elements.requireConfirmBeforePost.checked =
    settings.behavior.requireConfirmBeforePost;
  setStatus("Settings loaded.");
}

async function saveSettings() {
  const settings = collectSettings();
  await sendMessage({ type: "settings_set", settings });
  setStatus("Settings saved.");
}

async function resetSettings() {
  await sendMessage({ type: "settings_reset" });
  await loadSettings();
  setStatus("Settings reset to defaults.");
}

async function testLlm() {
  setStatus("Testing LLM...");
  const reply = await sendMessage({ type: "llm_test" });
  setStatus(`LLM OK: ${reply}`);
}

function collectSettings() {
  return {
    llm: {
      provider: elements.llmProvider.value,
      apiKey: elements.llmApiKey.value.trim(),
      baseUrl: elements.llmBaseUrl.value.trim(),
      model: elements.llmModel.value.trim(),
      temperature: Number(elements.llmTemperature.value),
      maxTokens: Number(elements.llmMaxTokens.value)
    },
    behavior: {
      tone: elements.tone.value.trim() || "natural",
      maxPostsPerHour: Number(elements.maxPostsPerHour.value),
      cooldownSeconds: Number(elements.cooldownSeconds.value),
      duplicateWindowMinutes: Number(elements.duplicateWindowMinutes.value),
      requireConfirmBeforePost: elements.requireConfirmBeforePost.checked
    }
  };
}

function setStatus(text) {
  elements.status.textContent = text;
}

async function safeAction(action) {
  try {
    await action();
  } catch (error) {
    setStatus(error instanceof Error ? error.message : String(error));
  }
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
