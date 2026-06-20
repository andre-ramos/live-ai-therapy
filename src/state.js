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

export function createInitialSession(topics, persona = null) {
  return {
    phase: PHASES.CONNECTING,
    serverReady: false,
    providersReady: false,
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
    case "CONNECTED":
      return {
        ...state,
        phase: PHASES.LIVE,
        sessionId: action.session.session_id,
        persona: {
          ...(state.persona ?? {}),
          id: action.session.persona_id,
          display_name: action.session.psychologist_name,
          version: action.session.persona_version,
          language: action.session.language,
          approaches: action.session.selected_approaches,
        },
        voiceState: VOICE_STATES.LISTENING,
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
      };
    case "ERROR":
      return { ...state, voiceState: VOICE_STATES.ERROR, isSpeaking: false, error: action.message };
    case "TOGGLE_MIC":
      return state.phase === PHASES.LIVE ? { ...state, isMicMuted: !state.isMicMuted } : state;
    case "TOGGLE_TOPIC":
      return { ...state, topics: state.topics.map((topic) => topic.id === action.id ? { ...topic, completed: !topic.completed } : topic) };
    case "ADD_TOPIC": {
      const label = action.label.trim();
      return label ? { ...state, topics: [...state.topics, { id: action.id, label, completed: false }] } : state;
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
