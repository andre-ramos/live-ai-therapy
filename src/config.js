export const APP_CONFIG = Object.freeze({
  therapist: {
    name: "Sandy",
    language: "pt-BR",
    role: "virtual_psychological_support_assistant",
    approaches: ["CBT", "ACT", "CFT"],
    imageUrl: "/api/persona/image",
    imageAlt: "Sandy sorrindo em um consultório acolhedor",
  },
  sessionDurationSeconds: 50 * 60,
  vad: {
    minimumRecordingMs: 500,
    silenceDurationMs: 1000,
    maximumRecordingMs: 45000,
    postPlaybackDelayMs: 500,
  },
});
