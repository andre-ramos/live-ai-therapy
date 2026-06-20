import { createInitialSession, reduceSession } from "./state.js";
import { initialTopics, translate } from "./locale.js";

export class SessionGateway {
  connect() { throw new Error("connect() must be implemented"); }
  start() { throw new Error("start() must be implemented"); }
  end() { throw new Error("end() must be implemented"); }
  voiceTurn() { throw new Error("voiceTurn() must be implemented"); }
  subscribe() { throw new Error("subscribe() must be implemented"); }
  dispatch() { throw new Error("dispatch() must be implemented"); }
}

export class HttpSessionGateway extends SessionGateway {
  #state;
  #listeners = new Set();
  #abortController = new AbortController();

  constructor(config, fetchImplementation = globalThis.fetch.bind(globalThis)) {
    super();
    this.config = config;
    this.fetch = fetchImplementation;
    this.#state = createInitialSession(initialTopics(config.therapist.language), {
      id: "sandy",
      display_name: config.therapist.name,
      language: config.therapist.language,
      role: config.therapist.role,
      approaches: config.therapist.approaches,
    });
  }

  getSnapshot() {
    return this.#state;
  }

  subscribe(listener) {
    this.#listeners.add(listener);
    listener(this.#state);
    return () => this.#listeners.delete(listener);
  }

  dispatch(action) {
    const nextState = reduceSession(this.#state, action);
    if (nextState === this.#state) return;
    this.#state = nextState;
    this.#listeners.forEach((listener) => listener(this.#state));
  }

  async connect() {
    try {
      const [healthResponse, personaResponse] = await Promise.all([
        this.fetch("/api/health", { signal: this.#abortController.signal }),
        this.fetch("/api/persona", { signal: this.#abortController.signal }),
      ]);
      if (!healthResponse.ok || !personaResponse.ok) {
        throw new Error(translate(this.#state.persona?.language, "serverUnavailable"));
      }
      const [health, persona] = await Promise.all([healthResponse.json(), personaResponse.json()]);
      this.dispatch({ type: "SERVER_READY", health, persona, topics: initialTopics(persona.language) });
    } catch (error) {
      if (error.name !== "AbortError") this.dispatch({
        type: "ERROR",
        message: error.message || translate(this.#state.persona?.language, "localServerError"),
      });
    }
  }

  async start() {
    const response = await this.fetch("/api/session/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
      signal: this.#abortController.signal,
    });
    const payload = await parseResponse(response);
    this.dispatch({ type: "CONNECTED", session: payload });
    return payload;
  }

  async voiceTurn(audioBlob) {
    const sessionId = this.#state.sessionId;
    if (!sessionId) throw new Error(translate(this.#state.persona?.language, "sessionNotStarted"));
    const form = new FormData();
    form.append("session_id", sessionId);
    form.append("client_timestamp", new Date().toISOString());
    form.append("audio", audioBlob, audioBlob.type.includes("mp4") ? "utterance.m4a" : "utterance.webm");
    const response = await this.fetch("/api/voice-turn", {
      method: "POST",
      body: form,
      signal: this.#abortController.signal,
    });
    const payload = await parseResponse(response);
    this.dispatch({ type: "VOICE_RESPONSE", payload });
    return payload;
  }

  async end() {
    if (!this.#state.sessionId) return null;
    const response = await this.fetch(`/api/session/${encodeURIComponent(this.#state.sessionId)}/end`, {
      method: "POST",
      signal: this.#abortController.signal,
    });
    const payload = await parseResponse(response);
    this.dispatch({ type: "SET_SUMMARY", payload });
    return payload;
  }

  disconnect() {
    this.#abortController.abort();
  }

  reset() {
    this.#abortController.abort();
    this.#abortController = new AbortController();
    const language = this.#state.persona?.language ?? this.config.therapist.language;
    this.dispatch({ type: "RESET", topics: initialTopics(language), persona: this.#state.persona });
    this.connect();
  }
}

async function parseResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.message || translate("pt-BR", "requestFailed"));
    error.code = payload.code;
    error.retryable = Boolean(payload.retryable);
    throw error;
  }
  return payload;
}
