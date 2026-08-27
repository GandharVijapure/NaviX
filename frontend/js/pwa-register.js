/**
 * Registers the service worker and drives the "Offline Mode Active" banner
 * (spec section 7). Included on every page via a single <script> tag.
 */
(function () {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/service-worker.js").catch((err) => {
        console.warn("NaviX service worker registration failed", err);
      });
    });
  }

  function updateOfflineState() {
    document.body.classList.toggle("navix-offline", !navigator.onLine);
  }
  window.addEventListener("online", updateOfflineState);
  window.addEventListener("offline", updateOfflineState);
  document.addEventListener("DOMContentLoaded", updateOfflineState);
})();
