import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

test("ships local assets and secure browser voice capture", async () => {
  const [html, app, capture, config, styles] = await Promise.all([
    readFile(new URL("index.html", root), "utf8"),
    readFile(new URL("src/app.js", root), "utf8"),
    readFile(new URL("src/voice-capture.js", root), "utf8"),
    readFile(new URL("src/config.js", root), "utf8"),
    readFile(new URL("styles.css", root), "utf8"),
  ]);
  assert.match(html, /viewport-fit=cover/);
  assert.match(html, /app\.js\?v=20260620-empty-topics/);
  assert.match(capture, /getUserMedia/);
  assert.match(capture, /MediaRecorder/);
  assert.match(capture, /isSecureContext/);
  assert.doesNotMatch(capture, /video:\s*true/);
  assert.match(config, /\/api\/persona\/image/);
  assert.match(app, /persona\(state\)\.image_url/);
  assert.match(styles, /100dvh/);
  assert.match(styles, /safe-area-inset/);
  assert.match(styles, /prefers-reduced-motion/);
});

test("uses the HTTP API gateway and voice state machine", async () => {
  const [gateway, state] = await Promise.all([
    readFile(new URL("src/gateway.js", root), "utf8"),
    readFile(new URL("src/state.js", root), "utf8"),
  ]);
  assert.match(gateway, /\/api\/session\/start/);
  assert.match(gateway, /\/api\/persona/);
  assert.match(gateway, /\/api\/voice-turn/);
  assert.match(gateway, /FormData/);
  assert.match(state, /PROCESSING: "processing"/);
  assert.match(state, /SPEAKING: "speaking"/);
});

test("drives the interface from one persona language catalog", async () => {
  const [locale, gateway, state] = await Promise.all([
    readFile(new URL("src/locale.js", root), "utf8"),
    readFile(new URL("src/gateway.js", root), "utf8"),
    readFile(new URL("src/state.js", root), "utf8"),
  ]);
  assert.match(locale, /"pt-BR"/);
  assert.match(locale, /"en-US"/);
  assert.match(gateway, /JSON\.stringify\(\{\}\)/);
  assert.match(state, /persona/);
});

test("starts every new session without default topics", async () => {
  const { initialTopics } = await import(new URL("src/locale.js", root));
  assert.deepEqual(initialTopics("pt-BR"), []);
  assert.deepEqual(initialTopics("en-US"), []);
});

test("contains mobile, tablet, desktop, landscape and narrow-screen rules", async () => {
  const styles = await readFile(new URL("styles.css", root), "utf8");
  assert.match(styles, /min-width: 700px/);
  assert.match(styles, /min-width: 1100px/);
  assert.match(styles, /orientation: landscape/);
  assert.match(styles, /max-width: 359px/);
});

test("topic widget supports pointer, keyboard and collapse interactions", async () => {
  const [app, styles] = await Promise.all([
    readFile(new URL("src/app.js", root), "utf8"),
    readFile(new URL("styles.css", root), "utf8"),
  ]);
  assert.match(app, /data-drag-handle/);
  assert.match(app, /pointermove/);
  assert.match(app, /ArrowLeft/);
  assert.match(app, /toggle-topics/);
  assert.match(styles, /topics-panel--collapsed/);
});

test("uses the dark night-therapy design tokens", async () => {
  const [html, styles] = await Promise.all([
    readFile(new URL("index.html", root), "utf8"),
    readFile(new URL("styles.css", root), "utf8"),
  ]);
  assert.match(html, /theme-color" content="#0a0c10"/);
  assert.match(styles, /color-scheme: dark/);
  assert.match(styles, /--surface: #0a0c10/);
  assert.match(styles, /--primary: #d1c4e9/);
  assert.match(styles, /--accent: #ffcc80/);
});

test("supports theme, volume, microphone locking and meeting-end sound", async () => {
  const [app, styles] = await Promise.all([
    readFile(new URL("src/app.js", root), "utf8"),
    readFile(new URL("styles.css", root), "utf8"),
  ]);
  assert.doesNotMatch(app, /data-action="toggle-video"/);
  assert.match(app, /data-volume/);
  assert.match(app, /volumePanelOpen/);
  assert.match(app, /event\.key === "Escape"/);
  assert.match(app, /micLocked/);
  assert.match(app, /toggle-theme/);
  assert.match(app, /AudioContext/);
  assert.match(styles, /data-theme="light"/);
  assert.match(styles, /input::\-webkit-slider-thumb/);
  assert.match(styles, /volume-slider-panel/);
});

test("submits an active recording on mute and waits idle until unmuted", async () => {
  const [app, capture] = await Promise.all([
    readFile(new URL("src/app.js", root), "utf8"),
    readFile(new URL("src/voice-capture.js", root), "utf8"),
  ]);
  assert.match(capture, /if \(this\.recorder\?\.state === "recording"\) this\.#stopRecording\(\)/);
  assert.match(capture, /this\.onState\("idle"\)/);
  assert.match(capture, /this\.resume\(\)/);
  assert.match(app, /getSnapshot\(\)\.isMicMuted/);
  assert.match(app, /VOICE_STATES\.IDLE/);
});
