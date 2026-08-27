/**
 * IndexedDB wrapper for NaviX's offline-first data (spec sections 8/94).
 * localStorage is still used for lightweight preferences (language, UI
 * state) -- this module is for structured application data that needs to
 * survive a full offline session and be queried/synced later.
 *
 * Object stores:
 *   facilities          -- last-downloaded facility directory
 *   announcements       -- last-downloaded active announcements
 *   route_data          -- downloaded routes (by route id) for waypoint nav
 *   last_known_location -- single record, the user's last GPS fix
 *   lost_person_reports -- last-downloaded public lost-person list (read cache)
 *   pending_sos         -- SOS reports created offline, waiting to sync
 *   pending_reports     -- lost-person reports created offline, waiting to sync
 *   app_metadata        -- misc key/value bookkeeping (e.g. cache timestamps)
 */
const NaviXDB = (() => {
  const DB_NAME = "navix-offline";
  const DB_VERSION = 1;
  const STORES = [
    "facilities", "announcements", "route_data", "last_known_location",
    "lost_person_reports", "pending_sos", "pending_reports", "app_metadata",
  ];

  let dbPromise = null;

  function open() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      if (!("indexedDB" in window)) {
        reject(new Error("IndexedDB not supported in this browser"));
        return;
      }
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        STORES.forEach((name) => {
          if (!db.objectStoreNames.contains(name)) {
            const keyPath = name === "last_known_location" || name === "app_metadata" ? "key" : "id";
            db.createObjectStore(name, { keyPath, autoIncrement: keyPath === "id" && name.startsWith("pending") });
          }
        });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    return dbPromise;
  }

  async function tx(storeName, mode) {
    const db = await open();
    const transaction = db.transaction(storeName, mode);
    return transaction.objectStore(storeName);
  }

  /** Replace an entire store's contents with `items` (array of objects with an `id`). */
  async function replaceAll(storeName, items) {
    const db = await open();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(storeName, "readwrite");
      const store = transaction.objectStore(storeName);
      store.clear();
      items.forEach((item) => store.put(item));
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
    });
  }

  async function getAll(storeName) {
    const store = await tx(storeName, "readonly");
    return new Promise((resolve, reject) => {
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  }

  async function put(storeName, item) {
    const store = await tx(storeName, "readwrite");
    return new Promise((resolve, reject) => {
      const req = store.put(item);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async function get(storeName, key) {
    const store = await tx(storeName, "readonly");
    return new Promise((resolve, reject) => {
      const req = store.get(key);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async function remove(storeName, key) {
    const store = await tx(storeName, "readwrite");
    return new Promise((resolve, reject) => {
      const req = store.delete(key);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  }

  // --- Convenience helpers used across pages -------------------------------

  async function setMetadata(key, value) {
    return put("app_metadata", { key, value, at: new Date().toISOString() });
  }

  async function getMetadata(key) {
    const row = await get("app_metadata", key);
    return row ? row.value : null;
  }

  async function saveFacilities(facilities) {
    await replaceAll("facilities", facilities);
    await setMetadata("facilities_updated_at", new Date().toISOString());
  }

  async function saveAnnouncements(announcements) {
    await replaceAll("announcements", announcements);
    await setMetadata("announcements_updated_at", new Date().toISOString());
  }

  async function saveLastKnownLocation(loc) {
    return put("last_known_location", { key: "current", ...loc, at: new Date().toISOString() });
  }

  async function getLastKnownLocation() {
    return get("last_known_location", "current");
  }

  async function queuePendingSos(sosPayload) {
    // client_request_id is generated once here and stays stable through retries.
    const record = { ...sosPayload, client_request_id: sosPayload.client_request_id || crypto.randomUUID(), queued_at: new Date().toISOString() };
    await put("pending_sos", record);
    return record;
  }

  async function queuePendingReport(reportPayload) {
    const record = { ...reportPayload, client_request_id: reportPayload.client_request_id || crypto.randomUUID(), queued_at: new Date().toISOString() };
    await put("pending_reports", record);
    return record;
  }

  return {
    open, replaceAll, getAll, put, get, remove,
    setMetadata, getMetadata,
    saveFacilities, saveAnnouncements,
    saveLastKnownLocation, getLastKnownLocation,
    queuePendingSos, queuePendingReport,
  };
})();
