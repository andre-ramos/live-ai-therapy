import assert from "node:assert/strict";
import test from "node:test";
import { createInitialSession, formatElapsed, PHASES, reduceSession, VOICE_STATES } from "../src/state.js";

const topics = [{ id: "one", label: "One", completed: false }];

test("moves through connecting, live, completed and summary", () => {
  let state = createInitialSession(topics);
  state = reduceSession(state, { type: "CONNECTED", session: { session_id: "session_1" } });
  assert.equal(state.phase, PHASES.LIVE);
  assert.equal(state.voiceState, VOICE_STATES.LISTENING);
  state = reduceSession(state, { type: "END" });
  assert.equal(state.phase, PHASES.COMPLETED);
  state = reduceSession(state, { type: "SHOW_SUMMARY" });
  assert.equal(state.phase, PHASES.SUMMARY);
});

test("updates controls and topics without mutating previous state", () => {
  const initial = reduceSession(createInitialSession(topics), { type: "CONNECTED", session: { session_id: "session_1" } });
  const toggled = reduceSession(initial, { type: "TOGGLE_MIC" });
  const withTopic = reduceSession(toggled, { type: "TOGGLE_TOPIC", id: "one" });
  assert.notEqual(initial, toggled);
  assert.equal(toggled.isMicMuted, true);
  assert.equal(initial.topics[0].completed, false);
  assert.equal(withTopic.topics[0].completed, true);
});

test("tracks real voice states, responses and errors", () => {
  let state = reduceSession(createInitialSession(topics), { type: "CONNECTED", session: { session_id: "session_1" } });
  state = reduceSession(state, { type: "VOICE_STATE", value: VOICE_STATES.PROCESSING });
  assert.equal(state.voiceState, VOICE_STATES.PROCESSING);
  state = reduceSession(state, { type: "VOICE_RESPONSE", payload: { user_text: "Olá", assistant_text: "Como você está?" } });
  assert.equal(state.assistantText, "Como você está?");
  state = reduceSession(state, { type: "ERROR", message: "Falhou" });
  assert.equal(state.voiceState, VOICE_STATES.ERROR);
  assert.equal(state.error, "Falhou");
});

test("ignores blank topics and formats elapsed time", () => {
  const state = createInitialSession(topics);
  assert.equal(reduceSession(state, { type: "ADD_TOPIC", id: "x", label: "  " }), state);
  assert.equal(formatElapsed(125), "02:05");
});
