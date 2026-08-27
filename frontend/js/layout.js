/**
 * Shared page chrome (public navbar, admin sidebar/topbar, footer, offline
 * banner, floating SOS button) injected via plain DOM APIs. This is a
 * static multi-page app (no framework/build step), so instead of copy-
 * pasting the same markup into every HTML file, each page includes an
 * empty `<div id="navix-navbar"></div>` etc. and calls the matching
 * NaviXLayout.render* function once on load.
 */
const NaviXLayout = (() => {
  const PUBLIC_LINKS = [
    { href: "/", key: "nav_home", label: "Home" },
    { href: "/find-help", key: "nav_find_help", label: "Find Help" },
    { href: "/navigation", key: "nav_navigation", label: "Navigation" },
    { href: "/lost-person", key: "nav_lost_person", label: "Lost Person" },
    { href: "/alerts", key: "nav_alerts", label: "Alerts" },
  ];

  function renderPublicNavbar(activePath) {
    const el = document.getElementById("navix-navbar");
    if (!el) return;
    const links = PUBLIC_LINKS.map(
      (l) => `<li class="nav-item"><a class="nav-link${activePath === l.href ? " active" : ""}" data-i18n="${l.key}" href="${l.href}">${l.label}</a></li>`
    ).join("");

    el.outerHTML = `
    <nav class="navbar navbar-expand-lg navix-navbar sticky-top">
      <div class="container-fluid px-3 px-lg-4">
        <a class="navbar-brand" href="/">NaviX<small>Connecting Every Step, Even Without Networks</small></a>
        <button class="navbar-toggler" style="border-color:#4a6386;" type="button" data-bs-toggle="collapse" data-bs-target="#navixNavMenu">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navixNavMenu">
          <ul class="navbar-nav me-auto mb-2 mb-lg-0 gap-lg-1">${links}</ul>
          <div class="d-flex gap-2 flex-wrap">
            <select id="navixLangSwitch" class="form-select form-select-sm" style="width:auto; min-height:auto;">
              <option value="en">English</option>
              <option value="hi">हिंदी</option>
              <option value="mr">मराठी</option>
            </select>
            <a class="btn btn-sm btn-volunteer" data-i18n="nav_volunteer_login" href="/volunteer/login">Volunteer Login</a>
            <a class="btn btn-sm btn-control-room" data-i18n="nav_control_room" href="/admin/login">Control Room</a>
          </div>
        </div>
      </div>
    </nav>
    <div class="offline-banner" data-i18n="offline_active">Offline Mode Active</div>
    <div id="navix-critical-banner"></div>`;

    const langSelect = document.getElementById("navixLangSwitch");
    if (langSelect) {
      langSelect.value = NaviXI18n.getLang();
      langSelect.addEventListener("change", () => NaviXI18n.loadLang(langSelect.value));
    }

    loadCriticalBanner();
  }

  async function loadCriticalBanner() {
    const target = document.getElementById("navix-critical-banner");
    if (!target) return;
    try {
      const announcements = await NaviXApi.get("/api/announcements/active");
      const critical = announcements.find((a) => a.priority === "critical");
      if (critical) {
        target.innerHTML = `<div class="critical-banner">⚠️ ${critical.title.toUpperCase()} — ${critical.message}</div>`;
      }
    } catch (e) {
      /* offline or server unreachable -- silently skip, cached page content still works */
    }
  }

  function renderFooter() {
    const el = document.getElementById("navix-footer");
    if (!el) return;
    el.outerHTML = `
    <footer class="navix-footer">
      <div><strong>NaviX</strong></div>
      <div data-i18n="footer_tagline">Connecting Every Step, Even Without Networks</div>
      <div class="mt-2 small">Built for large public gatherings — Wari · Kumbh Mela · Processions · Concerts</div>
    </footer>`;
  }

  function renderSosFab() {
    if (document.querySelector(".sos-fab")) return;
    const btn = document.createElement("a");
    btn.href = "/sos";
    btn.className = "sos-fab";
    btn.innerHTML = "SOS";
    document.body.appendChild(btn);
  }

  const ADMIN_LINKS = [
    { href: "/admin/dashboard", label: "Dashboard", icon: "🏠" },
    { href: "/admin/emergencies", label: "Emergencies", icon: "🆘" },
    { href: "/admin/volunteers", label: "Volunteers", icon: "🧭" },
    { href: "/admin/devices", label: "Devices", icon: "📡" },
    { href: "/admin/facilities", label: "Facilities", icon: "🏥" },
    { href: "/admin/lost-persons", label: "Lost Persons", icon: "🔍" },
    { href: "/admin/announcements", label: "Announcements", icon: "📢" },
    { href: "/admin/analytics", label: "Analytics", icon: "📊" },
    { href: "/developer/device-simulator", label: "Device Simulator", icon: "🛠️" },
  ];

  function renderAdminShell(activePath, pageTitle) {
    const sidebarEl = document.getElementById("navix-admin-sidebar");
    const topbarEl = document.getElementById("navix-admin-topbar");
    if (!sidebarEl || !topbarEl) return;

    const links = ADMIN_LINKS.map(
      (l) => `<a class="${activePath === l.href ? "active" : ""}" href="${l.href}"><span>${l.icon}</span><span class="label">${l.label}</span></a>`
    ).join("");

    sidebarEl.outerHTML = `
    <aside class="admin-sidebar" id="navix-admin-sidebar">
      <div class="d-flex align-items-center justify-content-between px-2 mb-3">
        <a href="/admin/dashboard" class="text-white text-decoration-none fw-bold">NaviX <span class="label">Control Room</span></a>
      </div>
      ${links}
    </aside>`;

    const user = NaviXAuth.getUser();
    topbarEl.outerHTML = `
    <div class="admin-topbar" id="navix-admin-topbar">
      <div class="d-flex align-items-center gap-2">
        <button class="btn btn-sm btn-outline-secondary d-md-none" id="navixSidebarToggle">☰</button>
        <h4 class="mb-0 section-title">${pageTitle}</h4>
      </div>
      <div class="d-flex align-items-center gap-2">
        <span class="text-navix-muted small">${user ? user.name : ""}</span>
        <button class="btn btn-sm btn-navix-outline" id="navixLogoutBtn" style="min-height:38px;">Logout</button>
      </div>
    </div>`;

    document.getElementById("navixLogoutBtn").addEventListener("click", () => NaviXAuth.logout("/admin/login"));
    const toggleBtn = document.getElementById("navixSidebarToggle");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => document.getElementById("navix-admin-sidebar").classList.toggle("open"));
    }
  }

  return { renderPublicNavbar, renderFooter, renderSosFab, renderAdminShell };
})();
