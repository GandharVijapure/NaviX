/**
 * Token storage + login/logout/role-guard helpers. Volunteers and admins
 * both use this; pilgrim pages never call it.
 */
const NaviXAuth = (() => {
  const TOKEN_KEY = "navix_token";
  const USER_KEY = "navix_user";

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function getUser() {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  }

  function setSession(tokenOut) {
    localStorage.setItem(TOKEN_KEY, tokenOut.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(tokenOut.user));
  }

  function logout(redirectTo) {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    if (redirectTo) window.location.href = redirectTo;
  }

  /** Redirects away if the logged-in user doesn't have `role`. Call at the
   * top of any protected page. */
  function requireRole(role, loginPath) {
    const user = getUser();
    if (!user || !getToken()) {
      window.location.href = loginPath;
      return null;
    }
    if (role === "admin" && user.role !== "admin") {
      window.location.href = loginPath;
      return null;
    }
    if (role === "volunteer" && !["volunteer", "admin"].includes(user.role)) {
      window.location.href = loginPath;
      return null;
    }
    return user;
  }

  return { getToken, getUser, setSession, logout, requireRole };
})();
