/**
 * NaviX service worker -- app-shell + "recently accessed data" caching
 * (spec section 7). Deliberately does NOT try to cache OpenStreetMap tiles:
 * those need live network access and this file says so rather than
 * pretending otherwise. What it does cache:
 *   - the app shell (HTML pages, CSS, JS, icons)
 *   - the last successful /api/facilities* and /api/announcements/active
 *     responses, so a pilgrim who lost signal can still see nearby
 *     facilities and current alerts they already loaded once.
 */
const CACHE_VERSION = "navix-v1";
const SHELL_CACHE = `${CACHE_VERSION}-shell`;
const DATA_CACHE = `${CACHE_VERSION}-data`;

const APP_SHELL = [
  "/",
  "/find-help",
  "/navigation",
  "/sos",
  "/alerts",
  "/facilities",
  "/lost-person",
  "/offline.html",
  "/manifest.json",
  "/css/style.css",
  "/js/api.js",
  "/js/auth.js",
  "/js/ws.js",
  "/js/geo.js",
  "/js/map.js",
  "/js/i18n.js",
  "/js/pwa-register.js",
  "/icons/icon.svg",
];

const CACHEABLE_API_PREFIXES = ["/api/facilities", "/api/announcements/active"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => !k.startsWith(CACHE_VERSION)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function isCacheableApi(url) {
  return CACHEABLE_API_PREFIXES.some((prefix) => url.pathname.startsWith(prefix));
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle same-origin GET requests; let everything else (POST/PUT,
  // cross-origin CDN assets, WebSocket upgrade) go straight to the network.
  if (request.method !== "GET" || url.origin !== self.location.origin) return;

  // Page navigations: network-first, cache fallback, offline.html last resort.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((res) => {
          const copy = res.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put(request, copy));
          return res;
        })
        .catch(() => caches.match(request).then((cached) => cached || caches.match("/offline.html")))
    );
    return;
  }

  // Cacheable read-only API data: network-first, falling back to the last
  // cached copy when offline.
  if (isCacheableApi(url)) {
    event.respondWith(
      fetch(request)
        .then((res) => {
          const copy = res.clone();
          caches.open(DATA_CACHE).then((cache) => cache.put(request, copy));
          return res;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // App-shell static assets: cache-first for speed, refresh in background.
  if (APP_SHELL.includes(url.pathname) || url.pathname.startsWith("/css/") || url.pathname.startsWith("/js/") || url.pathname.startsWith("/icons/")) {
    event.respondWith(
      caches.match(request).then((cached) => {
        const network = fetch(request)
          .then((res) => {
            caches.open(SHELL_CACHE).then((cache) => cache.put(request, res.clone()));
            return res;
          })
          .catch(() => cached);
        return cached || network;
      })
    );
  }
});
