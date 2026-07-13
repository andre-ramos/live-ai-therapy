export const PHASES = Object.freeze({
  CONNECTING: "connecting",
  LIVE: "live",
  COMPLETED: "completed",
  SUMMARY: "summary",
});

export const VOICE_STATES = Object.freeze({
  IDLE: "idle",
  LISTENING: "listening",
  RECORDING: "recording",
  PROCESSING: "processing",
  SPEAKING: "speaking",
  ERROR: "error",
});

function normalizeTopicLabel(value) {
  return String(value).trim().replace(/\s+/g, " ");
}

function mergeTopics(existingTopics, labels = []) {
  const seen = new Set(existingTopics.map((topic) => normalizeTopicLabel(topic.label).toLowerCase()));
  const additions = [];
  for (const rawLabel of labels) {
    const label = normalizeTopicLabel(rawLabel);
    const key = label.toLowerCase();
    if (!label || seen.has(key)) continue;
    seen.add(key);
    additions.push({ id: `topic-auto-${existingTopics.length + additions.length + 1}-${Date.now()}`, label, completed: false });
  }
  return additions.length ? [...existingTopics, ...additions] : existingTopics;
}

export function createInitialSession(topics, persona = null) {
  return {
    phase: PHASES.CONNECTING,
    serverReady: false,
    providersReady: false,
    isStartingSession: false,
    persona,
    sessionId: null,
    elapsedSeconds: 0,
    voiceState: VOICE_STATES.IDLE,
    isSpeaking: false,
    isMicMuted: false,
    topics: topics.map((topic) => ({ ...topic })),
    endReason: null,
    transcript: "",
    assistantText: "",
    error: null,
    summary: null,
    memories: [],
  };
}

export function reduceSession(state, action) {
  switch (action.type) {
    case "SERVER_READY":
      return {
        ...state,
        serverReady: true,
        providersReady: Boolean(action.health?.providers_ready),
        persona: action.persona ?? state.persona,
        topics: action.topics ?? state.topics,
        error: null,
      };
    case "STARTING_SESSION":
      return {
        ...state,
        isStartingSession: true,
        error: null,
      };
    case "CONNECTED":
      return {
        ...state,
        phase: PHASES.LIVE,
        isStartingSession: false,
        sessionId: action.session.session_id,
        persona: {
          ...(state.persona ?? {}),
          id: action.session.persona_id,
          display_name: action.session.psychologist_name,
          version: action.session.persona_version,
          language: action.session.language,
          approaches: action.session.selected_approaches,
        },
        assistantText: action.session.assistant_text ?? "",
        voiceState: VOICE_STATES.IDLE,
        error: null,
      };
    case "TICK":
      return state.phase === PHASES.LIVE ? { ...state, elapsedSeconds: state.elapsedSeconds + 1 } : state;
    case "VOICE_STATE":
      return {
        ...state,
        voiceState: action.value,
        isSpeaking: action.value === VOICE_STATES.SPEAKING,
        error: action.value === VOICE_STATES.ERROR ? state.error : null,
      };
    case "VOICE_RESPONSE":
      return {
        ...state,
        transcript: action.payload.user_text,
        assistantText: action.payload.assistant_text,
        topics: mergeTopics(state.topics, action.payload.topics_to_add),
      };
    case "SET_ASSISTANT_TEXT":
      return {
        ...state,
        assistantText: action.value,
      };
    case "ERROR":
      return {
        ...state,
        isStartingSession: false,
        voiceState: VOICE_STATES.ERROR,
        isSpeaking: false,
        error: action.message,
      };
    case "TOGGLE_MIC":
      return state.phase === PHASES.LIVE ? { ...state, isMicMuted: !state.isMicMuted } : state;
    case "TOGGLE_TOPIC":
      return { ...state, topics: state.topics.map((topic) => topic.id === action.id ? { ...topic, completed: !topic.completed } : topic) };
    case "ADD_TOPIC": {
      const label = action.label.trim();
      if (!label) return state;
      const topics = mergeTopics(state.topics, [label]);
      return topics === state.topics ? state : { ...state, topics };
    }
    case "END":
      return { ...state, phase: PHASES.COMPLETED, voiceState: VOICE_STATES.IDLE, isSpeaking: false, endReason: action.reason ?? "completed" };
    case "SET_SUMMARY":
      return action.payload.session_id === state.sessionId
        ? { ...state, summary: action.payload.summary, memories: action.payload.memories ?? [] }
        : state;
    case "SHOW_SUMMARY":
      return state.phase === PHASES.COMPLETED ? { ...state, phase: PHASES.SUMMARY } : state;
    case "BACK_TO_COMPLETED":
      return state.phase === PHASES.SUMMARY ? { ...state, phase: PHASES.COMPLETED } : state;
    case "RESET":
      return createInitialSession(action.topics, action.persona ?? state.persona);
    default:
      return state;
  }
}

export function formatElapsed(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
  const seconds = (totalSeconds % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}
