import assert from "node:assert/strict";
import test from "node:test";
import { VoiceCapture } from "../src/voice-capture.js";

test("mute stops the current recording before disabling the track", () => {
  const events = [];
  const capture = new VoiceCapture({
    onState: (state) => events.push(state),
    onUtterance: () => {},
    onError: () => {},
  });
  const track = {
    _enabled: true,
    set enabled(value) {
      events.push(`track:${value}`);
      this._enabled = value;
    },
    get enabled() { return this._enabled; },
  };
  capture.stream = { getAudioTracks: () => [track] };
  capture.paused = false;
  capture.recorder = {
    state: "recording",
    stop() {
      events.push("stop");
      this.state = "inactive";
    },
  };

  capture.setMuted(true);

  assert.deepEqual(events, ["stop", "track:false", "idle"]);
  assert.equal(capture.muted, true);
});

test("unmute resumes listening after a muted response left capture paused", () => {
  const originalCancel = globalThis.cancelAnimationFrame;
  const originalRequest = globalThis.requestAnimationFrame;
  globalThis.cancelAnimationFrame = () => {};
  globalThis.requestAnimationFrame = () => 1;
  try {
    const states = [];
    const track = { enabled: false };
    const capture = new VoiceCapture({
      onState: (state) => states.push(state),
      onUtterance: () => {},
      onError: () => {},
    });
    capture.stream = { getAudioTracks: () => [track] };
    capture.muted = true;
    capture.paused = true;

    capture.setMuted(false);

    assert.equal(track.enabled, true);
    assert.equal(capture.muted, false);
    assert.equal(capture.paused, false);
    assert.deepEqual(states, ["listening"]);
  } finally {
    globalThis.cancelAnimationFrame = originalCancel;
    globalThis.requestAnimationFrame = originalRequest;
  }
});
