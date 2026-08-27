/**
 * Thin fetch() wrapper shared by every page. Adds the JWT (when present),
 * JSON-encodes bodies, and normalises errors so callers can just `await`.
 */
const NaviXApi = (() => {
  function authHeader() {
    const token = NaviXAuth.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async function handle(res) {
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        detail = body.detail || detail;
      } catch (e) {
        /* no JSON body */
      }
      const err = new Error(detail);
      err.status = res.status;
      throw err;
    }
    if (res.status === 204) return null;
    return res.json();
  }

  async function get(path) {
    const res = await fetch(path, { headers: { ...authHeader() } });
    return handle(res);
  }

  async function send(method, path, body) {
    const res = await fetch(path, {
      method,
      headers: { "Content-Type": "application/json", ...authHeader() },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    return handle(res);
  }

  async function post(path, body) {
    return send("POST", path, body);
  }
  async function put(path, body) {
    return send("PUT", path, body);
  }
  async function del(path) {
    const res = await fetch(path, { method: "DELETE", headers: { ...authHeader() } });
    return handle(res);
  }

  async function postForm(path, formData) {
    const res = await fetch(path, { method: "POST", headers: { ...authHeader() }, body: formData });
    return handle(res);
  }

  return { get, post, put, delete: del, postForm };
})();
