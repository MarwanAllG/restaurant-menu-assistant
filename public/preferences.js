(() => {
  let button;
  let panel;
  let requestId;
  let timeout;

  function close() {
    requestId = null;
    clearTimeout(timeout);
    if (panel) panel.hidden = true;
    if (button) button.setAttribute("aria-expanded", "false");
  }

  function show(content) {
    if (!panel) return;
    panel.textContent = content.replace(/\*\*/g, "");
    panel.hidden = false;
    button.setAttribute("aria-expanded", "true");
  }

  function mount() {
    const header = document.getElementById("header");
    if (!header || document.getElementById("preferences-button")) return;
    close();
    const container = document.createElement("div");
    container.id = "preferences-menu";
    button = document.createElement("button");
    button.id = "preferences-button";
    button.type = "button";
    button.textContent = "Remembered preferences";
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("aria-controls", "preferences-panel");
    panel = document.createElement("section");
    panel.id = "preferences-panel";
    panel.setAttribute("aria-label", "Remembered preferences");
    panel.setAttribute("aria-live", "polite");
    panel.hidden = true;
    button.addEventListener("click", () => {
      if (!panel.hidden) return close();
      show("Loading preferences…");
      requestId = crypto.randomUUID();
      window.postMessage({ type: "preferences:request", requestId }, window.location.origin);
      timeout = setTimeout(() => {
        requestId = null;
        show("Couldn’t load your preferences. Close this panel and try again.");
      }, 10000);
    });
    container.append(button, panel);
    header.lastElementChild.prepend(container);
  }

  window.addEventListener("message", (event) => {
    if (event.origin !== window.location.origin || event.source !== window) return;
    const data = event.data;
    if (!data || typeof data !== "object") return;
    if (data.type === "preferences:reset") close();
    if (data.type === "preferences:show" && typeof data.content === "string") {
      close();
      show(data.content);
    }
    if (data.type === "preferences:response" && requestId && data.requestId === requestId) {
      requestId = null;
      clearTimeout(timeout);
      if (typeof data.content === "string") show(data.content);
    }
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest("#preferences-menu")) close();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && panel && !panel.hidden) {
      close();
      button.focus();
    }
  });
  new MutationObserver(mount).observe(document.body, { childList: true, subtree: true });
  mount();
})();
