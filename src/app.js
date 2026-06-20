import { APP_CONFIG } from "./config.js";
import { HttpSessionGateway } from "./gateway.js";
import { translate } from "./locale.js";
import { formatElapsed, PHASES, VOICE_STATES } from "./state.js";
import { VoiceCapture } from "./voice-capture.js";

const app = document.querySelector("#app");
const gateway = new HttpSessionGateway(APP_CONFIG);
const clampPercent = (value) => Math.min(100, Math.max(0, Number(value) || 0));
let themePreference = localStorage.getItem("live-therapy-theme") === "light" ? "light" : "dark";
let volumeLevel = clampPercent(localStorage.getItem("live-therapy-volume") ?? 70);
let tickTimer;
let timerPhase;
let topicFormOpen = false;
let volumePanelOpen = false;
let lastRenderedState;
const widgetState = { collapsed: false, x: null, y: null };
let dragState = null;
let voiceCapture = null;
let responseAudio = null;

function persona(state = gateway.getSnapshot()) {
  return state.persona ?? {
    display_name: APP_CONFIG.therapist.name,
    language: APP_CONFIG.therapist.language,
  };
}

function therapistName(state) {
  return persona(state).display_name ?? APP_CONFIG.therapist.name;
}

function therapistImageUrl(state) {
  return persona(state).image_url ?? APP_CONFIG.therapist.imageUrl;
}

function copy(state, key, variables = {}) {
  return translate(persona(state).language, key, { name: therapistName(state), ...variables });
}

function applyLocale(state) {
  const language = persona(state).language;
  document.documentElement.lang = language;
  document.title = copy(state, "documentTitle");
  document.querySelector('meta[name="description"]')?.setAttribute("content", copy(state, "description"));
  const skip = document.querySelector(".skip-link");
  if (skip) skip.textContent = copy(state, "skip");
}

const icons = {
  phone: '<svg viewBox="0 0 24 24"><path d="M6.6 10.8c1.5 3 3.9 5.4 6.9 6.9l2.3-2.3c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1v3.6c0 .6-.4 1-1 1C10.6 21.4 2.6 13.4 2.6 3.6c0-.6.4-1 1-1h3.6c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.4 0 .8-.3 1.1l-1.9 2.5Z"/></svg>',
  mic: '<svg viewBox="0 0 24 24"><path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.9V21H8v2h8v-2h-3v-3.1A7 7 0 0 0 19 11h-2Z"/></svg>',
  micOff: '<svg viewBox="0 0 24 24"><path d="m4.3 3 16.7 16.7-1.3 1.3-4.1-4.1a7 7 0 0 1-2.6 1V21h3v2H8v-2h3v-3.1A7 7 0 0 1 5 11h2a5 5 0 0 0 7.1 4.5l-1.5-1.5H12a3 3 0 0 1-3-3V10L3 4.3 4.3 3ZM9.1 5.3 15 11.2V5a3 3 0 0 0-5.9.3ZM17 11h2c0 1.2-.3 2.3-.8 3.3l-1.5-1.5c.2-.6.3-1.2.3-1.8Z"/></svg>',
  volume: '<svg viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3Zm13.5 3a4.5 4.5 0 0 0-2.5-4v8a4.5 4.5 0 0 0 2.5-4ZM14 3.2v2.1a7 7 0 0 1 0 13.4v2.1a9 9 0 0 0 0-17.6Z"/></svg>',
  settings: '<svg viewBox="0 0 24 24"><path d="M19.4 13a7.8 7.8 0 0 0 .1-1 7.8 7.8 0 0 0-.1-1l2.1-1.6-2-3.5-2.5 1a7 7 0 0 0-1.7-1L15 3h-4l-.4 2.7a7 7 0 0 0-1.7 1l-2.5-1-2 3.5L6.5 11a7.8 7.8 0 0 0-.1 1 7.8 7.8 0 0 0 .1 1l-2.1 1.6 2 3.5 2.5-1a7 7 0 0 0 1.7 1L11 21h4l.4-2.7a7 7 0 0 0 1.7-1l2.5 1 2-3.5L19.4 13ZM13 17h-2l-.3-2a5 5 0 0 1-1.4-.8l-1.8.7-1-1.7L8 12a4.7 4.7 0 0 1 0-1.6L6.4 9.2l1-1.7 1.9.7a5 5 0 0 1 1.4-.8l.3-2h2l.3 2a5 5 0 0 1 1.4.8l1.8-.7 1 1.7-1.6 1.2a4.7 4.7 0 0 1 0 1.6l1.6 1.2-1 1.7-1.8-.7a5 5 0 0 1-1.4.8L13 17Zm-1-2.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z"/></svg>',
  more: '<svg viewBox="0 0 24 24"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg>',
  notes: '<svg viewBox="0 0 24 24"><path d="M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2Zm0 16H5V5h14v14ZM7 7h10v2H7V7Zm0 4h10v2H7v-2Zm0 4h7v2H7v-2Z"/></svg>',
  check: '<svg viewBox="0 0 24 24"><path d="m9 16.2-4.2-4.2-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2Z"/></svg>',
  lock: '<svg viewBox="0 0 24 24"><path d="M18 8h-1V6a5 5 0 0 0-10 0v2H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10a2 2 0 0 0-2-2ZM9 6a3 3 0 0 1 6 0v2H9V6Zm9 14H6V10h12v10Z"/></svg>',
  arrow: '<svg viewBox="0 0 24 24"><path d="m13 5-1.4 1.4 4.6 4.6H4v2h12.2l-4.6 4.6L13 19l7-7-7-7Z"/></svg>',
  sun: '<svg viewBox="0 0 24 24"><path d="M6.8 4.8 5.4 3.4 4 4.8l1.4 1.4 1.4-1.4ZM4 11H1v2h3v-2Zm9-10h-2v3h2V1Zm6.6 2.4-1.4 1.4 1.4 1.4L21 4.8l-1.4-1.4ZM20 11v2h3v-2h-3Zm-8-5a6 6 0 1 0 0 12 6 6 0 0 0 0-12Zm0 10a4 4 0 1 1 0-8 4 4 0 0 1 0 8Zm5.2 3.2 1.4 1.4 1.4-1.4-1.4-1.4-1.4 1.4ZM11 20v3h2v-3h-2Zm-7-1.2 1.4 1.4 1.4-1.4-1.4-1.4L4 18.8Z"/></svg>',
  moon: '<svg viewBox="0 0 24 24"><path d="M12.3 2a9.8 9.8 0 1 0 9.7 11.1 8 8 0 0 1-9.7-11.1Zm-.1 18A7.8 7.8 0 0 1 9.3 4.9 10 10 0 0 0 19.1 15a7.8 7.8 0 0 1-6.9 5Z"/></svg>',
};

function icon(name) {
  return `<span class="icon" aria-hidden="true">${icons[name]}</span>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[character]);
}

function applyTheme() {
  document.documentElement.dataset.theme = themePreference;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", themePreference === "dark" ? "#0a0c10" : "#f6faff");
}

function themeControl(state) {
  const nextTheme = copy(state, themePreference === "dark" ? "themeLight" : "themeDark");
  return `<button class="icon-button theme-toggle" type="button" data-action="toggle-theme" aria-label="${copy(state, "switchTheme", { theme: nextTheme })}" title="${copy(state, "themeTitle", { theme: nextTheme })}">${icon(themePreference === "dark" ? "sun" : "moon")}</button>`;
}

function therapistHeader(state, options = {}) {
  const status = options.status ?? (state.phase === PHASES.LIVE ? formatElapsed(state.elapsedSeconds) : copy(state, "sessionEnded"));
  return `
    <header class="topbar ${options.centered ? "topbar--centered" : ""}">
      <div class="therapist-identity">
        <img src="${escapeHtml(therapistImageUrl(state))}" alt="" class="avatar avatar--small" />
        <div>
          <strong>${escapeHtml(therapistName(state))}</strong>
          <span class="identity-status">${status}</span>
        </div>
      </div>
      <div class="topbar-actions">${themeControl(state)}${options.action ?? ""}</div>
    </header>`;
}

function controlBar(state, disabled = false) {
  const micLocked = !disabled && [VOICE_STATES.PROCESSING, VOICE_STATES.SPEAKING].includes(state.voiceState);
  const micDisabled = disabled || micLocked;
  return `
    <nav class="control-bar" aria-label="${copy(state, "sessionControls")}">
      <div class="volume-popover">
        <button class="icon-button volume-trigger" type="button" data-action="toggle-volume" aria-expanded="${volumePanelOpen}" aria-controls="volume-slider-panel" aria-label="${copy(state, volumePanelOpen ? "volumeClose" : "volumeOpen")}" ${disabled ? "disabled" : ""}>${icon("volume")}</button>
        <div id="volume-slider-panel" class="volume-slider-panel" ${volumePanelOpen && !disabled ? "" : "hidden"}>
          <label class="volume-control" style="--volume-level:${volumeLevel}%">
            <span>${copy(state, "volume")}</span>
            <input type="range" data-volume min="0" max="100" step="1" value="${volumeLevel}" aria-label="${copy(state, "sessionVolume", { value: volumeLevel })}" />
            <output>${volumeLevel}%</output>
          </label>
        </div>
      </div>
      <button class="icon-button ${state.isMicMuted ? "icon-button--danger" : "icon-button--active"} ${micLocked ? "icon-button--locked" : ""}" type="button" data-action="toggle-mic" aria-pressed="${state.isMicMuted}" aria-label="${micLocked ? copy(state, "micLocked") : copy(state, state.isMicMuted ? "micEnable" : "micDisable")}" title="${micLocked ? copy(state, "waitForVoice") : copy(state, "microphone")}" ${micDisabled ? "disabled" : ""}>${icon(state.isMicMuted ? "micOff" : "mic")}${micLocked ? `<span class="control-lock">${icon("lock")}</span>` : ""}</button>
      <button class="icon-button" type="button" aria-label="${copy(state, "settings")}" ${disabled ? "disabled" : ""}>${icon("settings")}</button>
      <button class="icon-button" type="button" aria-label="${copy(state, "moreOptions")}" ${disabled ? "disabled" : ""}>${icon("more")}</button>
    </nav>`;
}

function connectingView(state) {
  const status = copy(state, state.serverReady ? "localReady" : "connecting");
  return `
    <div class="app-shell">
      ${therapistHeader(state, { status: `<span class="status-dot"></span>${status}` })}
      <main id="main-content" class="connecting-main">
        <div class="ambient-photo" aria-hidden="true"><img src="${escapeHtml(therapistImageUrl(state))}" alt="" /></div>
        <section class="connecting-card" aria-labelledby="connecting-title">
          <div class="connection-avatar"><span class="connection-ring"></span><img src="${escapeHtml(therapistImageUrl(state))}" alt="" /><span class="sync-mark" aria-hidden="true">↻</span></div>
          <div>
            <h1 id="connecting-title">${copy(state, "sessionWith")}</h1>
            <p>${copy(state, "microphoneNotice")}</p>
          </div>
          <p class="session-disclaimer">${copy(state, "disclaimer")}</p>
          ${state.error ? `<p class="inline-error" role="alert">${escapeHtml(state.error)}</p>` : ""}
          <button class="button start-session-button" data-action="start-session" type="button" ${state.serverReady ? "" : "disabled"}>${icon("mic")} ${copy(state, "startSession")}</button>
          ${state.serverReady && !state.providersReady ? `<p class="setup-warning">${copy(state, "providerWarning")}</p>` : ""}
        </section>
      </main>
      ${controlBar(state, true)}
    </div>`;
}

function topicList(state) {
  const items = state.topics.map((topic) => `
    <li>
      <label class="topic-item">
        <input type="checkbox" data-topic-id="${topic.id}" ${topic.completed ? "checked" : ""} />
        <span class="custom-check">${icon("check")}</span>
        <span class="topic-label">${escapeHtml(topic.label)}</span>
      </label>
    </li>`).join("");
  const positioned = Number.isFinite(widgetState.x) && Number.isFinite(widgetState.y);
  const positionStyle = positioned ? `left:${widgetState.x}px;top:${widgetState.y}px;right:auto;bottom:auto;transform:none;` : "";
  return `
    <aside class="topics-panel ${widgetState.collapsed ? "topics-panel--collapsed" : ""}" style="${positionStyle}" aria-labelledby="topics-title">
      <div class="topics-heading" data-drag-handle tabindex="0" role="button" aria-label="${copy(state, "moveTopics")}">
        <h2 id="topics-title">${icon("notes")} ${copy(state, "sessionTopics")}</h2>
        <div class="topics-heading-actions">
          <span class="drag-mark" aria-hidden="true">⠿</span>
          <button class="panel-toggle" type="button" data-action="toggle-topics" aria-expanded="${!widgetState.collapsed}" aria-label="${copy(state, widgetState.collapsed ? "expandTopics" : "minimizeTopics")}">${widgetState.collapsed ? "+" : "−"}</button>
        </div>
      </div>
      <div class="topics-content" ${widgetState.collapsed ? "hidden" : ""}>
        <ul>${items}</ul>
        ${topicFormOpen ? `
        <form class="new-topic-form" data-form="new-topic">
          <label for="new-topic" class="sr-only">${copy(state, "newTopic")}</label>
          <input id="new-topic" name="topic" maxlength="80" autocomplete="off" placeholder="${copy(state, "newTopicPlaceholder")}" required />
          <button class="button button--compact" type="submit">${copy(state, "add")}</button>
          <button class="text-button" type="button" data-action="close-topic">${copy(state, "cancel")}</button>
        </form>` : `<button class="add-topic" type="button" data-action="open-topic"><span aria-hidden="true">＋</span> ${copy(state, "newTopic")}</button>`}
      </div>
    </aside>`;
}

function liveView(state) {
  const end = `<button class="button button--danger button--compact" data-action="end" type="button">${icon("phone")} ${copy(state, "end")}</button>`;
  return `
    <div class="app-shell app-shell--live">
      ${therapistHeader(state, { action: end })}
      <main id="main-content" class="session-main">
        <section class="therapist-stage" aria-label="${copy(state, "sessionStage")}">
          <img src="${escapeHtml(therapistImageUrl(state))}" alt="${copy(state, "imageAlt")}" />
          <div class="photo-wash" aria-hidden="true"></div>
          <div class="speaking-pill ${state.isSpeaking ? "" : "speaking-pill--listening"}" role="status">
            <span class="voice-dot"><span></span></span>
            ${voiceStatusLabel(state)}
          </div>
          ${state.error ? `<div class="voice-error" role="alert">${escapeHtml(state.error)} <button type="button" data-action="retry-listening">${copy(state, "retry")}</button></div>` : ""}
          ${state.assistantText ? `<div class="voice-transcript" aria-live="polite"><strong>${escapeHtml(therapistName(state))}</strong><p>${escapeHtml(state.assistantText)}</p></div>` : ""}
          ${topicList(state)}
        </section>
      </main>
      ${controlBar(state)}
    </div>`;
}

function completedView(state) {
  const cancelled = state.endReason === "cancelled";
  const completedTopics = state.topics.filter((topic) => topic.completed);
  const displayTopics = completedTopics.length ? completedTopics : state.topics.slice(0, 1);
  return `
    <div class="app-shell completed-shell">
      ${therapistHeader(state, { centered: true, status: copy(state, cancelled ? "sessionCancelled" : "sessionEnded") })}
      <main id="main-content" class="completed-main">
        <div class="soft-glow soft-glow--one"></div><div class="soft-glow soft-glow--two"></div>
        <section class="completion-content" aria-labelledby="completion-title">
          <div class="success-mark">${icon("check")}</div>
          <h1 id="completion-title">${copy(state, cancelled ? "sessionCancelled" : "sessionEnded")}</h1>
          <p>${copy(state, cancelled ? "cancelledMessage" : "completedMessage")}</p>
          <div class="summary-card">
            <h2>${icon("notes")} ${copy(state, "completedTopics")}</h2>
            <ul>${displayTopics.map((topic, index) => `<li style="--delay:${index * 80 + 100}ms">${icon("check")}<span>${escapeHtml(topic.label)}</span></li>`).join("")}</ul>
            <blockquote>${copy(state, "closingQuote")}</blockquote>
          </div>
          <div class="completion-actions">
            <button class="button" type="button" data-action="summary">${copy(state, "detailedSummary")} ${icon("arrow")}</button>
            <button class="button button--secondary" type="button" data-action="reset">${copy(state, "backHome")}</button>
          </div>
        </section>
      </main>
      <footer class="privacy-note">${icon("lock")} ${copy(state, "privacyNote")}</footer>
    </div>`;
}

function summaryView(state) {
  const completedCount = state.topics.filter((topic) => topic.completed).length;
  return `
    <div class="app-shell summary-shell">
      ${therapistHeader(state, { centered: true, status: copy(state, "sessionSummary") })}
      <main id="main-content" class="detail-main">
        <section class="detail-card" aria-labelledby="detail-title">
          <button class="text-button back-button" type="button" data-action="back-completed">${copy(state, "back")}</button>
          <p class="eyebrow">${copy(state, "sessionLabel")}</p>
          <h1 id="detail-title">${copy(state, "yourSummary")}</h1>
          <p class="detail-intro">${escapeHtml(state.summary || copy(state, "summaryPending"))}</p>
          <div class="metric-row"><div><strong>${formatElapsed(state.elapsedSeconds)}</strong><span>${copy(state, "sessionTime")}</span></div><div><strong>${completedCount}/${state.topics.length}</strong><span>${copy(state, "topicsCompleted")}</span></div></div>
          <div class="detail-section"><h2>${copy(state, "topics")}</h2><ul>${state.topics.map((topic) => `<li>${icon(topic.completed ? "check" : "notes")}<span><strong>${escapeHtml(topic.label)}</strong><small>${copy(state, topic.completed ? "completed" : "later")}</small></span></li>`).join("")}</ul></div>
          <div class="reflection"><h2>${copy(state, "reflectionTitle")}</h2><p>${copy(state, "reflection")}</p></div>
          <button class="button" type="button" data-action="reset">${copy(state, "finishAndHome")} ${icon("arrow")}</button>
        </section>
      </main>
    </div>`;
}

function syncTimers(state) {
  if (timerPhase === state.phase) return;
  timerPhase = state.phase;
  clearInterval(tickTimer);
  if (state.phase === PHASES.LIVE) {
    tickTimer = setInterval(() => gateway.dispatch({ type: "TICK" }), 1000);
  }
}

function voiceStatusLabel(state) {
  const labels = {
    [VOICE_STATES.IDLE]: copy(state, state.isMicMuted ? "micOffStatus" : "readyStatus"),
    [VOICE_STATES.LISTENING]: copy(state, "listeningStatus"),
    [VOICE_STATES.RECORDING]: copy(state, "recordingStatus"),
    [VOICE_STATES.PROCESSING]: copy(state, "processingStatus"),
    [VOICE_STATES.SPEAKING]: copy(state, "speakingStatus"),
    [VOICE_STATES.ERROR]: copy(state, "errorStatus"),
  };
  return labels[state.voiceState] ?? copy(state, "activeStatus");
}

function playMeetingEndSound() {
  if (volumeLevel <= 0) return;
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) return;
  const context = new AudioContextClass();
  const master = context.createGain();
  const now = context.currentTime;
  master.gain.setValueAtTime((volumeLevel / 100) * 0.22, now);
  master.connect(context.destination);
  [659.25, 523.25, 392].forEach((frequency, index) => {
    const start = now + index * 0.13;
    const oscillator = context.createOscillator();
    const envelope = context.createGain();
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(frequency, start);
    envelope.gain.setValueAtTime(0.0001, start);
    envelope.gain.exponentialRampToValueAtTime(0.7, start + 0.025);
    envelope.gain.exponentialRampToValueAtTime(0.0001, start + 0.22);
    oscillator.connect(envelope).connect(master);
    oscillator.start(start);
    oscillator.stop(start + 0.23);
  });
  window.setTimeout(() => context.close(), 800);
}

function isTimerOnlyUpdate(previous, next) {
  return previous
    && previous.phase === PHASES.LIVE
    && next.phase === PHASES.LIVE
    && previous.elapsedSeconds !== next.elapsedSeconds
    && previous.isSpeaking === next.isSpeaking
    && previous.isMicMuted === next.isMicMuted
    && previous.voiceState === next.voiceState
    && previous.error === next.error
    && previous.assistantText === next.assistantText
    && previous.topics === next.topics;
}

function clampWidgetPosition() {
  const panel = app.querySelector(".topics-panel");
  const stage = app.querySelector(".therapist-stage");
  if (!panel || !stage || !Number.isFinite(widgetState.x) || !Number.isFinite(widgetState.y)) return;
  const maxX = Math.max(8, stage.clientWidth - panel.offsetWidth - 8);
  const maxY = Math.max(8, stage.clientHeight - panel.offsetHeight - 8);
  widgetState.x = Math.min(Math.max(8, widgetState.x), maxX);
  widgetState.y = Math.min(Math.max(8, widgetState.y), maxY);
  panel.style.left = `${widgetState.x}px`;
  panel.style.top = `${widgetState.y}px`;
  panel.style.right = "auto";
  panel.style.bottom = "auto";
  panel.style.transform = "none";
}

function initializeWidgetPosition(panel, stage) {
  if (Number.isFinite(widgetState.x) && Number.isFinite(widgetState.y)) return;
  const panelRect = panel.getBoundingClientRect();
  const stageRect = stage.getBoundingClientRect();
  widgetState.x = panelRect.left - stageRect.left;
  widgetState.y = panelRect.top - stageRect.top;
}

function render(state) {
  applyLocale(state);
  if (isTimerOnlyUpdate(lastRenderedState, state)) {
    const status = app.querySelector(".identity-status");
    if (status) status.textContent = formatElapsed(state.elapsedSeconds);
    lastRenderedState = state;
    return;
  }
  const activeElement = document.activeElement?.dataset?.action;
  if (state.phase === PHASES.CONNECTING) app.innerHTML = connectingView(state);
  if (state.phase === PHASES.LIVE) app.innerHTML = liveView(state);
  if (state.phase === PHASES.COMPLETED) app.innerHTML = completedView(state);
  if (state.phase === PHASES.SUMMARY) app.innerHTML = summaryView(state);
  syncTimers(state);
  lastRenderedState = state;
  if (activeElement) app.querySelector(`[data-action="${activeElement}"]`)?.focus({ preventScroll: true });
  if (topicFormOpen) app.querySelector("#new-topic")?.focus();
  requestAnimationFrame(clampWidgetPosition);
}

function createVoiceCapture() {
  return new VoiceCapture({
    settings: {
      minimumRecordingMs: APP_CONFIG.vad.minimumRecordingMs,
      silenceDurationMs: APP_CONFIG.vad.silenceDurationMs,
      maximumRecordingMs: APP_CONFIG.vad.maximumRecordingMs,
      messages: {
        secureMicrophone: copy(gateway.getSnapshot(), "secureMicrophone"),
        unsupportedCapture: copy(gateway.getSnapshot(), "unsupportedCapture"),
      },
    },
    onState: (value) => gateway.dispatch({ type: "VOICE_STATE", value }),
    onUtterance: handleUtterance,
    onError: (error) => gateway.dispatch({ type: "ERROR", message: error.message }),
  });
}

async function handleUtterance(blob) {
  voiceCapture?.pause();
  gateway.dispatch({ type: "VOICE_STATE", value: VOICE_STATES.PROCESSING });
  try {
    const response = await gateway.voiceTurn(blob);
    if (gateway.getSnapshot().phase !== PHASES.LIVE) return;
    if (response.audio_url) {
      gateway.dispatch({ type: "VOICE_STATE", value: VOICE_STATES.SPEAKING });
      await playAssistantAudio(response.audio_url);
    }
    await new Promise((resolve) => setTimeout(resolve, APP_CONFIG.vad.postPlaybackDelayMs));
    if (gateway.getSnapshot().isMicMuted) {
      gateway.dispatch({ type: "VOICE_STATE", value: VOICE_STATES.IDLE });
    } else {
      gateway.dispatch({ type: "VOICE_STATE", value: VOICE_STATES.LISTENING });
      voiceCapture?.resume();
    }
  } catch (error) {
    if (gateway.getSnapshot().phase === PHASES.LIVE) {
      gateway.dispatch({ type: "ERROR", message: error.message || copy(gateway.getSnapshot(), "voiceFailed") });
    }
  }
}

function playAssistantAudio(url) {
  responseAudio?.pause();
  responseAudio = new Audio(url);
  responseAudio.volume = volumeLevel / 100;
  return new Promise((resolve, reject) => {
    responseAudio.addEventListener("ended", resolve, { once: true });
    responseAudio.addEventListener("error", () => reject(new Error(copy(gateway.getSnapshot(), "playbackFailed"))), { once: true });
    responseAudio.play().catch(reject);
  });
}

app.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  const action = button?.dataset.action;
  const insideVolume = event.target.closest(".volume-popover");
  if (volumePanelOpen && !insideVolume && action !== "toggle-volume") {
    volumePanelOpen = false;
    if (!button) {
      render(gateway.getSnapshot());
      return;
    }
  }
  if (!button) return;
  if (action === "start-session") {
    button.disabled = true;
    voiceCapture = createVoiceCapture();
    try {
      await voiceCapture.enable();
      await gateway.start();
    } catch (error) {
      await voiceCapture.destroy();
      voiceCapture = null;
      gateway.dispatch({ type: "ERROR", message: error.message || copy(gateway.getSnapshot(), "startFailed") });
    }
    return;
  }
  if (action === "toggle-volume") {
    volumePanelOpen = !volumePanelOpen;
    render(gateway.getSnapshot());
    return;
  }
  if (action === "toggle-mic") {
    const muted = !gateway.getSnapshot().isMicMuted;
    gateway.dispatch({ type: "TOGGLE_MIC" });
    voiceCapture?.setMuted(muted);
  }
  if (action === "retry-listening") {
    gateway.dispatch({ type: "VOICE_STATE", value: VOICE_STATES.LISTENING });
    voiceCapture?.resume();
  }
  if (action === "toggle-theme") {
    themePreference = themePreference === "dark" ? "light" : "dark";
    localStorage.setItem("live-therapy-theme", themePreference);
    applyTheme();
    render(gateway.getSnapshot());
  }
  if (action === "end") {
    volumePanelOpen = false;
    playMeetingEndSound();
    responseAudio?.pause();
    await voiceCapture?.destroy();
    gateway.dispatch({ type: "END", reason: "completed" });
    gateway.end().catch(() => {});
  }
  if (action === "cancel") {
    volumePanelOpen = false;
    playMeetingEndSound();
    gateway.dispatch({ type: "END", reason: "cancelled" });
  }
  if (action === "summary") gateway.dispatch({ type: "SHOW_SUMMARY" });
  if (action === "back-completed") gateway.dispatch({ type: "BACK_TO_COMPLETED" });
  if (action === "toggle-topics") {
    widgetState.collapsed = !widgetState.collapsed;
    topicFormOpen = widgetState.collapsed ? false : topicFormOpen;
    render(gateway.getSnapshot());
  }
  if (action === "reset") {
    topicFormOpen = false;
    volumePanelOpen = false;
    widgetState.collapsed = false;
    widgetState.x = null;
    widgetState.y = null;
    responseAudio = null;
    voiceCapture = null;
    gateway.reset();
  }
  if (action === "open-topic" || action === "close-topic") {
    topicFormOpen = action === "open-topic";
    render(gateway.getSnapshot());
  }
});

app.addEventListener("input", (event) => {
  if (!event.target.matches("[data-volume]")) return;
  volumeLevel = clampPercent(event.target.value);
  if (responseAudio) responseAudio.volume = volumeLevel / 100;
  localStorage.setItem("live-therapy-volume", String(volumeLevel));
  event.target.setAttribute("aria-label", copy(gateway.getSnapshot(), "sessionVolume", { value: volumeLevel }));
  event.target.closest(".volume-control")?.style.setProperty("--volume-level", `${volumeLevel}%`);
  const output = event.target.closest(".volume-control")?.querySelector("output");
  if (output) output.textContent = `${volumeLevel}%`;
});

app.addEventListener("pointerdown", (event) => {
  const handle = event.target.closest("[data-drag-handle]");
  if (!handle || event.target.closest("button")) return;
  const panel = handle.closest(".topics-panel");
  const stage = panel?.closest(".therapist-stage");
  if (!panel || !stage) return;
  initializeWidgetPosition(panel, stage);
  const stageRect = stage.getBoundingClientRect();
  dragState = {
    pointerId: event.pointerId,
    panel,
    stage,
    offsetX: event.clientX - stageRect.left - widgetState.x,
    offsetY: event.clientY - stageRect.top - widgetState.y,
  };
  panel.classList.add("topics-panel--dragging");
  handle.setPointerCapture(event.pointerId);
  event.preventDefault();
});

app.addEventListener("pointermove", (event) => {
  if (!dragState || dragState.pointerId !== event.pointerId) return;
  const stageRect = dragState.stage.getBoundingClientRect();
  const maxX = Math.max(8, dragState.stage.clientWidth - dragState.panel.offsetWidth - 8);
  const maxY = Math.max(8, dragState.stage.clientHeight - dragState.panel.offsetHeight - 8);
  widgetState.x = Math.min(Math.max(8, event.clientX - stageRect.left - dragState.offsetX), maxX);
  widgetState.y = Math.min(Math.max(8, event.clientY - stageRect.top - dragState.offsetY), maxY);
  dragState.panel.style.left = `${widgetState.x}px`;
  dragState.panel.style.top = `${widgetState.y}px`;
  dragState.panel.style.right = "auto";
  dragState.panel.style.bottom = "auto";
  dragState.panel.style.transform = "none";
});

function finishDrag(event) {
  if (!dragState || dragState.pointerId !== event.pointerId) return;
  dragState.panel.classList.remove("topics-panel--dragging");
  dragState = null;
}

app.addEventListener("pointerup", finishDrag);
app.addEventListener("pointercancel", finishDrag);

app.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && volumePanelOpen) {
    volumePanelOpen = false;
    render(gateway.getSnapshot());
    app.querySelector('[data-action="toggle-volume"]')?.focus();
    event.preventDefault();
    return;
  }
  const handle = event.target.closest("[data-drag-handle]");
  if (!handle || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
  const panel = handle.closest(".topics-panel");
  const stage = panel?.closest(".therapist-stage");
  if (!panel || !stage) return;
  initializeWidgetPosition(panel, stage);
  const distance = event.shiftKey ? 24 : 8;
  if (event.key === "ArrowLeft") widgetState.x -= distance;
  if (event.key === "ArrowRight") widgetState.x += distance;
  if (event.key === "ArrowUp") widgetState.y -= distance;
  if (event.key === "ArrowDown") widgetState.y += distance;
  clampWidgetPosition();
  event.preventDefault();
});

window.addEventListener("resize", clampWidgetPosition);

app.addEventListener("change", (event) => {
  if (event.target.matches("[data-topic-id]")) gateway.dispatch({ type: "TOGGLE_TOPIC", id: event.target.dataset.topicId });
});

app.addEventListener("submit", (event) => {
  if (!event.target.matches('[data-form="new-topic"]')) return;
  event.preventDefault();
  const data = new FormData(event.target);
  gateway.dispatch({ type: "ADD_TOPIC", id: `topic-${Date.now()}`, label: String(data.get("topic")) });
  topicFormOpen = false;
  render(gateway.getSnapshot());
});

window.addEventListener("beforeunload", () => {
  voiceCapture?.destroy();
  gateway.disconnect();
});
applyTheme();
gateway.subscribe(render);
gateway.connect();
