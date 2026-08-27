/**
 * WebSocket client with auto-reconnect. Pages register handlers per event
 * name; NaviX broadcasts {"event": "...", "data": {...}} envelopes (see
 * backend/websocket_manager.py).
 */
const NaviXSocket = (() => {
  let socket = null;
  const handlers = {};
  let reconnectDelay = 1500;

  function connect() {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${proto}://${window.location.host}/ws`);

    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        (handlers[msg.event] || []).forEach((fn) => fn(msg.data));
        (handlers["*"] || []).forEach((fn) => fn(msg));
      } catch (e) {
        console.warn("NaviX WS: bad message", e);
      }
    };

    socket.onclose = () => {
      setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 1.5, 15000);
    };

    socket.onopen = () => {
      reconnectDelay = 1500;
    };
  }

  function on(event, fn) {
    handlers[event] = handlers[event] || [];
    handlers[event].push(fn);
  }

  connect();
  return { on };
})();
