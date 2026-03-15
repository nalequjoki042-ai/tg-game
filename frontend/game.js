const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

const user = tg.initDataUnsafe?.user;
const tgId = user?.id || 0;
const firstName = user?.first_name || 'Guest';

document.getElementById('tg-user').textContent = `👤 ${firstName}`;

const WS_URL = `wss://${location.host}/ws?tg_id=${tgId}&first_name=${encodeURIComponent(firstName)}`;
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
      document.getElementById('ping-result').textContent = `✅ Pong! Server alive.`;
    }

    if (data.type === 'state') {
      const p = data.payload?.player;
      if (p) {
        document.getElementById('ping-result').textContent =
          `🎮 ${p.first_name} | Score: ${p.score}`;
      }
    }
  };

  socket.onclose = () => {
    setWsStatus(false);
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
  el.textContent = '● WS';
}

document.getElementById('btn-ping').addEventListener('click', () => {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'ping', ts: Date.now() }));
  } else {
    document.getElementById('ping-result').textContent = '❌ Not connected';
  }
});

connect();
