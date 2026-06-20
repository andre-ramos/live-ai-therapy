const DEFAULTS = Object.freeze({
  minimumRecordingMs: 500,
  silenceDurationMs: 1000,
  maximumRecordingMs: 45000,
});

export class VoiceCapture {
  constructor({ onState, onUtterance, onError, settings = {} }) {
    this.onState = onState;
    this.onUtterance = onUtterance;
    this.onError = onError;
    this.settings = { ...DEFAULTS, ...settings };
    this.messages = {
      secureMicrophone: "O microfone exige uma conexão HTTPS segura.",
      unsupportedCapture: "Este navegador não oferece captura de voz compatível.",
      ...(settings.messages ?? {}),
    };
    this.stream = null;
    this.context = null;
    this.analyser = null;
    this.recorder = null;
    this.animationFrame = null;
    this.recordingStartedAt = 0;
    this.lastVoiceAt = 0;
    this.noiseFloor = 0.008;
    this.paused = true;
    this.muted = false;
    this.manualOnly = false;
    this.chunks = [];
  }

  static isSupported() {
    return Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder && (window.AudioContext || window.webkitAudioContext));
  }

  async enable() {
    if (!window.isSecureContext && !["localhost", "127.0.0.1"].includes(location.hostname)) {
      throw new Error(this.messages.secureMicrophone);
    }
    if (!VoiceCapture.isSupported()) {
      this.manualOnly = true;
      throw new Error(this.messages.unsupportedCapture);
    }
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      video: false,
    });
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    this.context = new AudioContextClass();
    await this.context.resume();
    this.analyser = this.context.createAnalyser();
    this.analyser.fftSize = 1024;
    this.analyser.smoothingTimeConstant = 0.2;
    this.context.createMediaStreamSource(this.stream).connect(this.analyser);
    this.paused = false;
    this.onState("listening");
    this.#monitor();
  }

  setMuted(muted) {
    if (muted) {
      if (this.recorder?.state === "recording") this.#stopRecording();
      this.muted = true;
      this.stream?.getAudioTracks().forEach((track) => { track.enabled = false; });
      this.onState("idle");
      return;
    }

    this.muted = false;
    this.stream?.getAudioTracks().forEach((track) => { track.enabled = true; });
    this.resume();
  }

  pause() {
    this.paused = true;
    if (this.recorder?.state === "recording") this.#stopRecording(false);
  }

  resume() {
    if (!this.stream || this.muted) return;
    this.paused = false;
    this.onState("listening");
    this.#monitor();
  }

  startManual() {
    if (!this.paused && !this.muted) this.#startRecording();
  }

  stopManual() {
    if (this.recorder?.state === "recording") this.#stopRecording();
  }

  async destroy() {
    this.paused = true;
    cancelAnimationFrame(this.animationFrame);
    this.stream?.getTracks().forEach((track) => track.stop());
    if (this.context && this.context.state !== "closed") await this.context.close();
    this.stream = null;
    this.context = null;
  }

  #monitor() {
    cancelAnimationFrame(this.animationFrame);
    const sample = () => {
      if (this.paused || this.muted || !this.analyser) return;
      const values = new Float32Array(this.analyser.fftSize);
      this.analyser.getFloatTimeDomainData(values);
      const rms = Math.sqrt(values.reduce((sum, value) => sum + value * value, 0) / values.length);
      const now = performance.now();
      if (!this.recorder || this.recorder.state === "inactive") {
        this.noiseFloor = this.noiseFloor * 0.96 + Math.min(rms, 0.025) * 0.04;
        const threshold = Math.max(0.032, this.noiseFloor * 2.8);
        if (rms > threshold) this.#startRecording();
      } else {
        const threshold = Math.max(0.025, this.noiseFloor * 2.1);
        if (rms > threshold) this.lastVoiceAt = now;
        const duration = now - this.recordingStartedAt;
        if (duration >= this.settings.maximumRecordingMs
          || (duration >= this.settings.minimumRecordingMs && now - this.lastVoiceAt >= this.settings.silenceDurationMs)) {
          this.#stopRecording();
        }
      }
      this.animationFrame = requestAnimationFrame(sample);
    };
    this.animationFrame = requestAnimationFrame(sample);
  }

  #startRecording() {
    if (!this.stream || this.paused || this.muted || this.recorder?.state === "recording") return;
    try {
      const mimeType = ["audio/webm;codecs=opus", "audio/mp4", "audio/webm"]
        .find((type) => MediaRecorder.isTypeSupported(type));
      this.chunks = [];
      this.recorder = mimeType ? new MediaRecorder(this.stream, { mimeType }) : new MediaRecorder(this.stream);
      this.recorder.addEventListener("dataavailable", (event) => {
        if (event.data.size) this.chunks.push(event.data);
      });
      this.recorder.addEventListener("stop", () => {
        if (!this.chunks.length) return;
        const blob = new Blob(this.chunks, { type: this.recorder.mimeType || "audio/webm" });
        this.chunks = [];
        if (blob.size > 0) this.onUtterance(blob);
      }, { once: true });
      this.recorder.start(200);
      this.recordingStartedAt = performance.now();
      this.lastVoiceAt = this.recordingStartedAt;
      this.onState("recording");
    } catch (error) {
      this.manualOnly = true;
      this.onError(error);
    }
  }

  #stopRecording(submit = true) {
    if (!this.recorder || this.recorder.state !== "recording") return;
    if (!submit) this.chunks = [];
    this.recorder.stop();
  }
}
