const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

const user = tg.initDataUnsafe?.user;
document.getElementById('tg-user').textContent =
  user ? `👤 ${user.first_name}` : '👤 Guest';

const WS_URL = `wss://${location.host}/ws`;
let socket = null;

function connect() {
  socket = new WebSocket(WS_URL);

  socket.onopen = () => {
    setWsStatus(true);
    console.log('[WS] Connected');
  };

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('[WS] Message:', data);
    if (data.type === 'pong') {
      document.getElementById('ping-result').textContent =
        `✅ Pong received! Server is alive.`;
    }
  };

  socket.onclose = () => {
    setWsStatus(false);
    console.log('[WS] Disconnected. Reconnecting in 3s...');
    setTimeout(connect, 3000);
  };

  socket.onerror = (err) => {
    console.error('[WS] Error:', err);
    socket.close();
  };
}

function setWsStatus(connected) {
  const el = document.getElementById('ws-status');
  el.className = connected ? 'badge badge--connected' : 'badge badge--disconnected';
  el.textContent = connected ? '● WS' : '● WS';
}

document.getElementById('btn-ping').addEventListener('click', () => {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'ping', ts: Date.now() }));
  } else {
    document.getElementById('ping-result').textContent = '❌ Not connected';
  }
});

connect();
