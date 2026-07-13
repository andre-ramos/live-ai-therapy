import assert from "node:assert/strict";
import test from "node:test";

class FakeAppElement {
  constructor() {
    this.html = "";
    this.listeners = new Map();
  }

  set innerHTML(value) {
    this.html = value;
  }

  get innerHTML() {
    return this.html;
  }

  insertAdjacentHTML(_position, value) {
    this.html += value;
  }

  addEventListener(type, listener) {
    this.listeners.set(type, listener);
  }

  querySelector() {
    return null;
  }
}

function actionTarget(action) {
  const button = {
    dataset: { action },
    disabled: false,
    classList: { contains: () => false },
    closest(selector) {
      if (selector === "[data-action]") return button;
      return null;
    },
  };
  return button;
}

test("settings dialog clears history through the UI control", async () => {
  const app = new FakeAppElement();
  const fetchCalls = [];
  const originalDocument = globalThis.document;
  const originalWindow = globalThis.window;
  const originalLocalStorage = globalThis.localStorage;
  const originalFetch = globalThis.fetch;
  const originalRequestAnimationFrame = globalThis.requestAnimationFrame;
  const originalCancelAnimationFrame = globalThis.cancelAnimationFrame;

  globalThis.localStorage = {
    getItem: () => null,
    setItem: () => {},
  };
  globalThis.document = {
    title: "",
    documentElement: { dataset: {}, lang: "" },
    querySelector(selector) {
      if (selector === "#app") return app;
      return null;
    },
  };
  globalThis.window = {
    addEventListener: () => {},
  };
  globalThis.requestAnimationFrame = () => 1;
  globalThis.cancelAnimationFrame = () => {};
  globalThis.fetch = async (url, options = {}) => {
    fetchCalls.push({ url, method: options.method ?? "GET" });
    if (url === "/api/health") {
      return { ok: true, json: async () => ({ status: "ready", providers_ready: true }) };
    }
    if (url === "/api/persona") {
      return {
        ok: true,
        json: async () => ({
          id: "sandy",
          display_name: "Sandy",
          language: "pt-BR",
          image_url: "/api/persona/image?v=test",
        }),
      };
    }
    if (url === "/api/history" && options.method === "DELETE") {
      return { ok: true, status: 204, json: async () => ({}) };
    }
    throw new Error(`Unexpected request: ${options.method ?? "GET"} ${url}`);
  };

  try {
    await import(`../src/app.js?history-ui=${Date.now()}`);
    await Promise.resolve();
    await Promise.resolve();

    const click = app.listeners.get("click");
    assert.equal(typeof click, "function");

    await click({ target: actionTarget("open-settings") });
    assert.match(app.innerHTML, /Apagar todo o histórico/);
    assert.match(app.innerHTML, /data-action="confirm-reset-history"/);

    await click({ target: actionTarget("confirm-reset-history") });
    await new Promise((resolve) => setImmediate(resolve));
    await new Promise((resolve) => setImmediate(resolve));
    assert.ok(fetchCalls.some((call) => call.url === "/api/history" && call.method === "DELETE"));
  } finally {
    globalThis.document = originalDocument;
    globalThis.window = originalWindow;
    globalThis.localStorage = originalLocalStorage;
    globalThis.fetch = originalFetch;
    globalThis.requestAnimationFrame = originalRequestAnimationFrame;
    globalThis.cancelAnimationFrame = originalCancelAnimationFrame;
  }
});
