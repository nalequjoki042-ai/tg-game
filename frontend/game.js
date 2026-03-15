const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

const user = tg.initDataUnsafe?.user;
const tgId = user?.id || 0;
const firstName = user?.first_name || 'Guest';

document.getElementById('tg-user').textContent = `👤 ${firstName}`;

const WS_URL = `wss://${location.host}/ws?tg_id=${tgId}&first_name=${encodeURIComponent(firstName)}`;
let socket = null;

async function loadLeaderboard() {
  try {
    const res = await fetch('/leaderboard');
    const data = await res.json();
    renderLeaderboard(data);
  } catch (e) {
    console.error('[LB] Failed to load', e);
  }
}

function renderLeaderboard(players) {
  const list = document.getElementById('lb-list');
  list.innerHTML = '';
  if (!players.length) {
    list.innerHTML = '<li style="opacity:0.4;text-align:center;padding:8px">Никого нет</li>';
    return;
  }
  players.forEach((p, i) => {
    const li = document.createElement('li');
    li.className = 'lb-row' + (p.tg_id === tgId ? ' me' : '');
    li.innerHTML = `
      <span class="lb-rank">${i + 1}</span>
      <span class="lb-name">${p.first_name}</span>
      <span class="lb-score">${p.score}</span>
    `;
    list.appendChild(li);
  });
}

function connect() {
  socket = new WebSocket(WS_URL);

  socket.onopen = () => {
    setWsStatus(true);
    loadLeaderboard();
  };

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'state') {
      const score = data.payload?.player?.score ?? 0;
      document.getElementById('score-value').textContent = score;
      loadLeaderboard();
    }
  };

  socket.onclose = () => {
    setWsStatus(false);
    setTimeout(connect, 3000);
  };

  socket.onerror = (err) => { socket.close(); };
}

function setWsStatus(connected) {
  const el = document.getElementById('ws-status');
  el.className = connected ? 'badge badge--connected' : 'badge badge--disconnected';
  el.textContent = '● WS';
}

document.getElementById('btn-ping').addEventListener('click', () => {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'ping', ts: Date.now() }));
  }
});

connect();
