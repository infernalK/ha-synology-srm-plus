/**
 * Loader for the Synology SRM Plus cards (see synology-srm-card.js).
 *
 * Some browsers (Firefox, Safari) can resolve the cards module without its
 * elements being defined, which leaves every card on "Configuration error"
 * until a manual refresh. This loader imports the cards under a URL unique to
 * each page load (no module or cache reuse), checks that the elements are
 * defined (retrying if not), then forces Lovelace to rebuild the cards that
 * stayed in error.
 */
(function () {
  "use strict";

  const CARDS_URL = "/synology_srm_plus/synology-srm-card.js";
  const PROBE_TAG = "synology-srm-router-card";
  const MAX_ATTEMPTS = 3;

  // Lovelace shows a card whose element wasn't defined yet as an error card
  // and normally rebuilds it once the element appears; do it ourselves in
  // case that didn't happen.
  function rebuildErrorCards() {
    const walk = (root) =>
      Array.from(root.querySelectorAll("*")).flatMap((el) => [
        el,
        ...(el.shadowRoot ? walk(el.shadowRoot) : []),
      ]);
    for (const el of walk(document)) {
      if (el.localName !== "hui-error-card") continue;
      const message = String((el._config && el._config.message) || "");
      if (!message.includes("Custom element doesn't exist: synology-srm-")) continue;
      el.dispatchEvent(new CustomEvent("ll-rebuild", { bubbles: true, composed: true }));
    }
  }

  async function load(attempt) {
    try {
      await import(`${CARDS_URL}?t=${Date.now()}-${attempt}`);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn("Synology SRM Plus: failed to load the cards", err);
    }
    if (customElements.get(PROBE_TAG)) {
      // Let Lovelace's own rebuild happen first, then catch the leftovers.
      setTimeout(rebuildErrorCards, 300);
      setTimeout(rebuildErrorCards, 2000);
      return;
    }
    if (attempt < MAX_ATTEMPTS) {
      setTimeout(() => load(attempt + 1), 1000 * attempt);
    }
  }

  load(1);
})();
