/**
 * Offline sync manager (spec section 9). Listens for online/offline and
 * syncs anything queued in IndexedDB once connectivity returns:
 *   1. pending SOS reports  -> POST /api/emergencies (idempotent via client_request_id)
 *   2. pending lost-person reports -> POST /api/lost-persons (idempotent)
 *   3. fresh facilities, announcements, route summaries downloaded for offline cache
 *
 * Dispatches a `navix:sync-status` CustomEvent with {phase, detail} so pages
 * can show "Connection restored — syncing data..." / "Data synchronized."
 */
const NaviXSync = (() => {
  let syncing = false;

  function announce(phase, detail) {
    window.dispatchEvent(new CustomEvent("navix:sync-status", { detail: { phase, detail } }));
  }

  async function syncPendingSos() {
    const pending = await NaviXDB.getAll("pending_sos");
    for (const item of pending) {
      try {
        const { queued_at, ...payload } = item;
        await NaviXApi.post("/api/emergencies", payload);
        await NaviXDB.remove("pending_sos", item.id);
      } catch (e) {
        console.warn("NaviX sync: SOS retry failed, will retry later", e);
        // Leave it queued -- next online event retries it.
      }
    }
    return pending.length;
  }

  async function syncPendingReports() {
    const pending = await NaviXDB.getAll("pending_reports");
    for (const item of pending) {
      try {
        const { queued_at, ...fields } = item;
        const formData = new FormData();
        Object.entries(fields).forEach(([k, v]) => {
          if (v !== null && v !== undefined) formData.set(k, v);
        });
        await NaviXApi.postForm("/api/lost-persons", formData);
        await NaviXDB.remove("pending_reports", item.id);
      } catch (e) {
        console.warn("NaviX sync: lost-person report retry failed, will retry later", e);
      }
    }
    return pending.length;
  }

  async function downloadFreshData() {
    try {
      const loc = (await NaviXDB.getLastKnownLocation()) || NaviXGeo.FALLBACK;
      const facilities = await NaviXApi.get(`/api/facilities/nearby?lat=${loc.lat || loc.latitude}&lon=${loc.lon || loc.longitude}&limit=200`);
      await NaviXDB.saveFacilities(facilities);
    } catch (e) { /* stay on cached copy */ }

    try {
      const announcements = await NaviXApi.get("/api/announcements/active");
      await NaviXDB.saveAnnouncements(announcements);
    } catch (e) { /* stay on cached copy */ }

    try {
      const routes = await NaviXApi.get("/api/routes");
      await NaviXDB.setMetadata("route_summaries", routes);
    } catch (e) { /* stay on cached copy */ }
  }

  async function runSync() {
    if (syncing || !navigator.onLine) return;
    syncing = true;
    announce("syncing", "Connection restored — syncing data...");
    try {
      const sosCount = await syncPendingSos();
      const reportCount = await syncPendingReports();
      await downloadFreshData();
      announce("done", sosCount + reportCount > 0 ? "Data synchronized." : "Data synchronized.");
    } catch (e) {
      announce("error", "Sync incomplete — will retry.");
    } finally {
      syncing = false;
    }
  }

  function init() {
    window.addEventListener("online", runSync);
    // Also try once on load in case we're already online with stale data.
    if (navigator.onLine) runSync();
  }

  document.addEventListener("DOMContentLoaded", init);
  return { runSync, syncPendingSos, syncPendingReports, downloadFreshData };
})();
