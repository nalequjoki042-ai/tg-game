const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); }

const TG_USER = tg?.initDataUnsafe?.user;
const MY_ID   = TG_USER?.id || Math.floor(Math.random()*100000);
const MY_NAME = TG_USER?.first_name || 'Hero';

const W = window.innerWidth;
const H = window.innerHeight;

// ─── WebSocket ───────────────────────────────────────────────
let ws = null;
let mySlot = -1;          // 0,1,2
const players = {};       // slotIndex -> {name, hp, atk, alive}
let bossHp = 1000;
const BOSS_MAX_HP = 1000;

function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws?tg_id=${MY_ID}&first_name=${encodeURIComponent(MY_NAME)}`);
  ws.onopen    = () => send({ type: 'arena_join' });
  ws.onmessage = (e) => handleMsg(JSON.parse(e.data));
  ws.onclose   = () => setTimeout(connectWS, 2000);
}

function send(obj) {
  if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
}

function handleMsg(msg) {
  if (msg.type === 'arena_state') {
    mySlot  = msg.my_slot ?? mySlot;
    bossHp  = msg.boss_hp ?? bossHp;
    if (msg.players) {
      msg.players.forEach(p => { players[p.slot] = p; });
    }
    if (game?.scene?.isActive('Arena')) {
      game.scene.getScene('Arena').syncState();
    }
  }
  if (msg.type === 'pong') {}
}

// ─── Phaser Scene ────────────────────────────────────────────
class ArenaScene extends Phaser.Scene {
  constructor() { super('Arena'); }

  preload() {
    // Генерируем все текстуры кодом
    const mk = (key, fn) => { const g = this.make.graphics({add:false}); fn(g); g.generateTexture(key,g.width||64,g.height||64); g.destroy(); };

    // Фон плитка
    const bg = this.make.graphics({add:false});
    bg.fillStyle(0x1a0a2e); bg.fillRect(0,0,64,64);
    bg.fillStyle(0x2a1a3e,0.5); bg.fillRect(0,0,32,32); bg.fillRect(32,32,32,32);
    bg.generateTexture('tile',64,64); bg.destroy();

    // Юнит игрока
    const ug = this.make.graphics({add:false});
    ug.fillStyle(0x6366f1); ug.fillRect(8,20,24,28);
    ug.fillStyle(0xfbbf24); ug.fillCircle(20,14,12);
    ug.fillStyle(0x4f46e5); ug.fillRect(0,28,8,20); ug.fillRect(32,28,8,20);
    ug.fillStyle(0x312e81); ug.fillRect(8,48,12,8); ug.fillRect(22,48,12,8);
    ug.generateTexture('unit',40,56); ug.destroy();

    // Босс
    const boss = this.make.graphics({add:false});
    boss.fillStyle(0x7f1d1d); boss.fillRect(0,40,120,80);
    boss.fillStyle(0xef4444); boss.fillCircle(60,40,40);
    boss.fillStyle(0xfef08a); boss.fillCircle(40,30,10); boss.fillCircle(80,30,10);
    boss.fillStyle(0x000); boss.fillRect(30,45,60,10);
    boss.fillStyle(0xffffff); boss.fillRect(34,47,10,6); boss.fillRect(50,47,10,6); boss.fillRect(66,47,10,6);
    // рога
    boss.fillStyle(0x7f1d1d);
    boss.fillTriangle(20,10,35,40,5,40);
    boss.fillTriangle(100,10,115,40,85,40);
    boss.generateTexture('boss',120,120); boss.destroy();

    // Ячейка слота
    const slot = this.make.graphics({add:false});
    slot.lineStyle(2,0x6366f1,0.8); slot.strokeRoundedRect(0,0,100,130,12);
    slot.fillStyle(0x1e1b4b,0.6); slot.fillRoundedRect(0,0,100,130,12);
    slot.generateTexture('slot',100,130); slot.destroy();

    // Частица
    const pt = this.make.graphics({add:false});
    pt.fillStyle(0xef4444); pt.fillCircle(4,4,4);
    pt.generateTexture('spark',8,8); pt.destroy();

    const pt2 = this.make.graphics({add:false});
    pt2.fillStyle(0x22c55e); pt2.fillCircle(4,4,4);
    pt2.generateTexture('heal',8,8); pt2.destroy();
  }

  create() {
    this.fogGraphics   = null;
    this.bossSprite    = null;
    this.bossHpBar     = null;
    this.slotObjs      = [];   // [{bg, unit, nameT, hpT, atkT, hpBtn, atkBtn}]
    this.dmgTexts      = [];

    this.drawBackground();
    this.drawBoss();
    this.drawSlots();
    this.drawFog();
    this.drawHUD();
    this.startBossPulse();
    this.startAutoAttack();

    connectWS();
  }

  // ── Фон ──────────────────────────────────────────────────────
  drawBackground() {
    for (let x=0; x<W; x+=64)
      for (let y=0; y<H; y+=64)
        this.add.image(x+32,y+32,'tile').setAlpha(0.8);

    // Виньетка
    const vg = this.add.graphics();
    vg.fillGradientStyle(0x000000,0x000000,0x000000,0x000000,0.9,0.9,0,0);
    vg.fillRect(0,0,W,H*0.15);
    vg.fillGradientStyle(0x000000,0x000000,0x000000,0x000000,0,0,0.9,0.9);
    vg.fillRect(0,H*0.85,W,H*0.15);
  }

  // ── Босс ─────────────────────────────────────────────────────
  drawBoss() {
    const bx = W/2, by = H*0.28;

    // Аура
    this.bossAura = this.add.graphics();
    this.updateBossAura();

    this.bossSprite = this.add.image(bx, by, 'boss').setScale(1.4);

    // HP бар фон
    const barW = 200, barH = 18;
    const barX = bx - barW/2, barY = by + 90;
    this.add.graphics().fillStyle(0x1f2937).fillRoundedRect(barX-2,barY-2,barW+4,barH+4,6);
    this.bossHpBg = this.add.graphics();
    this.bossHpBg.fillStyle(0x374151).fillRoundedRect(barX,barY,barW,barH,4);
    this.bossHpFill = this.add.graphics();
    this.bossHpLabel = this.add.text(bx, barY+barH+8, '💀 BOSS', {
      fontSize:'13px', fill:'#ef4444', fontFamily:'monospace', stroke:'#000', strokeThickness:3
    }).setOrigin(0.5,0);
    this.updateBossHpBar();
  }

  updateBossAura() {
    if (!this.bossAura) return;
    this.bossAura.clear();
    const ratio = bossHp / BOSS_MAX_HP;
    const color = ratio > 0.5 ? 0xef4444 : ratio > 0.25 ? 0xf97316 : 0xfbbf24;
    this.bossAura.fillStyle(color, 0.08);
    this.bossAura.fillCircle(W/2, H*0.28, 110);
    this.bossAura.fillStyle(color, 0.05);
    this.bossAura.fillCircle(W/2, H*0.28, 150);
  }

  updateBossHpBar() {
    if (!this.bossHpFill) return;
    const barW=200, barH=18, bx=W/2, by=H*0.28;
    const barX=bx-barW/2, barY=by+90;
    const ratio = Math.max(0, bossHp/BOSS_MAX_HP);
    const color = ratio>0.5 ? 0x22c55e : ratio>0.25 ? 0xf97316 : 0xef4444;
    this.bossHpFill.clear();
    this.bossHpFill.fillStyle(color).fillRoundedRect(barX,barY,barW*ratio,barH,4);
    this.bossHpLabel?.setText(`💀 BOSS  ${bossHp} / ${BOSS_MAX_HP}`);
    this.updateBossAura();
  }

  startBossPulse() {
    this.tweens.add({
      targets: this.bossSprite,
      scaleX: 1.45, scaleY: 1.35,
      duration: 900, yoyo: true, repeat: -1, ease: 'Sine.easeInOut'
    });
  }

  // ── Слоты ────────────────────────────────────────────────────
  drawSlots() {
    const slotW=100, slotH=130;
    const totalW = slotW*3 + 20*2;
    const startX = (W - totalW)/2;
    const y = H*0.72;

    for (let i=0; i<3; i++) {
      const x = startX + i*(slotW+20);
      const cx = x + slotW/2;

      const bg = this.add.image(cx, y+slotH/2, 'slot').setAlpha(0.9);
      const unit = this.add.image(cx, y+30, 'unit').setAlpha(0.3).setScale(0.85);

      const nameT = this.add.text(cx, y+62, '[ пусто ]', {
        fontSize:'11px', fill:'#6b7280', fontFamily:'monospace'
      }).setOrigin(0.5);

      const hpT = this.add.text(cx, y+78, '', {
        fontSize:'11px', fill:'#22c55e', fontFamily:'monospace'
      }).setOrigin(0.5);

      const atkT = this.add.text(cx, y+92, '', {
        fontSize:'11px', fill:'#f97316', fontFamily:'monospace'
      }).setOrigin(0.5);

      // Кнопки — только для своего слота
      const hpBtn = this.add.text(cx-16, y+112, '❤️', {
        fontSize:'16px'
      }).setOrigin(0.5).setAlpha(0).setInteractive({useHandCursor:true});

      const atkBtn = this.add.text(cx+16, y+112, '⚔️', {
        fontSize:'16px'
      }).setOrigin(0.5).setAlpha(0).setInteractive({useHandCursor:true});

      hpBtn.on('pointerdown', () => this.addStat('hp'));
      atkBtn.on('pointerdown', () => this.addStat('atk'));

      this.slotObjs.push({bg, unit, nameT, hpT, atkT, hpBtn, atkBtn, x:cx, y});
    }
  }

  addStat(type) {
    send({ type: 'arena_stat', stat: type });
    // Локальный эффект
    const slot = this.slotObjs[mySlot];
    if (!slot) return;
    const color = type==='hp' ? '#22c55e' : '#f97316';
    const icon  = type==='hp' ? '+HP ❤️' : '+ATK ⚔️';
    this.spawnFloatText(slot.x, slot.y+50, icon, color);
    if (type==='hp') {
      this.add.particles(slot.x, slot.y+30, 'heal', {
        speed:60, lifespan:500, quantity:5, emitting:false
      }).emitParticleAt(slot.x, slot.y+30);
    }
  }

  // ── Туман ────────────────────────────────────────────────────
  drawFog() {
    this.fogGraphics = this.add.graphics().setDepth(50);
    this.updateFog();
    // Анимируем туман
    this.fogOffset = 0;
    this.time.addEvent({
      delay: 50,
      callback: () => { this.fogOffset += 0.3; this.updateFog(); },
      loop: true
    });
  }

  updateFog() {
    if (!this.fogGraphics) return;
    this.fogGraphics.clear();
    // Несколько слоёв тумана с разной прозрачностью
    const layers = [
      { alpha: 0.13, freq: 0.008, amp: 18 },
      { alpha: 0.09, freq: 0.012, amp: 12 },
      { alpha: 0.07, freq: 0.005, amp: 25 },
    ];
    layers.forEach(({alpha, freq, amp}, li) => {
      this.fogGraphics.fillStyle(0x7c3aed, alpha);
      const off = this.fogOffset * (li+1) * 0.4;
      // Рисуем волнистые полосы тумана
      for (let y=0; y<H; y+=60) {
        const points = [];
        for (let x=0; x<=W; x+=20) {
          const dy = Math.sin((x+off)*freq + li*2) * amp;
          points.push(x, y+dy);
        }
        points.push(W, y+60, 0, y+60);
        this.fogGraphics.fillPoints(
          points.reduce((acc,v,i)=>{ if(i%2===0) acc.push({x:points[i],y:points[i+1]}); return acc; },[]),
          true
        );
      }
    });
  }

  // ── HUD ──────────────────────────────────────────────────────
  drawHUD() {
    // Заголовок
    this.add.text(W/2, 18, '⚔️  BOSS ARENA', {
      fontSize:'18px', fill:'#ef4444', fontFamily:'monospace',
      stroke:'#000', strokeThickness:4
    }).setOrigin(0.5).setDepth(60);

    this.connTxt = this.add.text(W-10, 10, '●', {
      fontSize:'14px', fill:'#ef4444', fontFamily:'monospace'
    }).setOrigin(1,0).setDepth(60);

    this.slotTxt = this.add.text(10, 10, '', {
      fontSize:'12px', fill:'#a78bfa', fontFamily:'monospace'
    }).setDepth(60);
  }

  // ── Синхронизация ─────────────────────────────────────────────
  syncState() {
    // WS статус
    this.connTxt?.setStyle({fill: ws?.readyState===1 ? '#22c55e':'#ef4444'});
    this.slotTxt?.setText(mySlot>=0 ? `Слот ${mySlot+1}` : 'Ожидание...');

    // Обновить HP бар босса
    this.updateBossHpBar();

    // Обновить слоты
    for (let i=0; i<3; i++) {
      const obj = this.slotObjs[i];
      if (!obj) continue;
      const p = players[i];
      const isMe = i === mySlot;

      if (p) {
        obj.unit.setAlpha(1);
        obj.bg.setTint(isMe ? 0xa78bfa : 0xffffff);
        obj.nameT.setText(p.name || `P${i+1}`).setStyle({fill: isMe?'#a78bfa':'#e5e7eb'});
        obj.hpT.setText(`❤️ ${p.hp}`);
        obj.atkT.setText(`⚔️ ${p.atk}`);
        obj.hpBtn.setAlpha(isMe ? 1 : 0);
        obj.atkBtn.setAlpha(isMe ? 1 : 0);
      } else {
        obj.unit.setAlpha(0.25);
        obj.bg.clearTint();
        obj.nameT.setText('[ пусто ]').setStyle({fill:'#6b7280'});
        obj.hpT.setText('');
        obj.atkT.setText('');
        obj.hpBtn.setAlpha(0);
        obj.atkBtn.setAlpha(0);
      }
    }
  }

  // ── Атака босса ───────────────────────────────────────────────
  startAutoAttack() {
    this.time.addEvent({
      delay: 2500,
      callback: () => {
        if (mySlot < 0) return;
        // Визуальная атака — линия от босса к случайному слоту
        const targets = Object.keys(players).map(Number);
        if (!targets.length) return;
        const t = targets[Math.floor(Math.random()*targets.length)];
        const slot = this.slotObjs[t];
        if (!slot) return;
        this.showBossAttack(slot.x, slot.y+30);
        send({ type: 'arena_boss_attack', target_slot: t });
      },
      loop: true
    });
  }

  showBossAttack(tx, ty) {
    const line = this.add.graphics().setDepth(40);
    line.lineStyle(3, 0xef4444, 0.9);
    line.strokeLineShape(new Phaser.Geom.Line(W/2, H*0.28+60, tx, ty));
    this.tweens.add({ targets:line, alpha:0, duration:400, onComplete:()=>line.destroy() });
    this.cameras.main.shake(120, 0.006);
    this.spawnFloatText(tx, ty-20, '-DMG 💀', '#ef4444');
  }

  spawnFloatText(x, y, txt, color='#fff') {
    const t = this.add.text(x, y, txt, {
      fontSize:'14px', fill:color, fontFamily:'monospace',
      stroke:'#000', strokeThickness:3
    }).setOrigin(0.5).setDepth(70);
    this.tweens.add({ targets:t, y:y-50, alpha:0, duration:900, onComplete:()=>t.destroy() });
  }

  update() {
    // Подсветка своего слота
    if (mySlot >= 0 && this.slotObjs[mySlot]) {
      const obj = this.slotObjs[mySlot];
      const pulse = 0.7 + 0.3*Math.sin(this.time.now/400);
      obj.bg.setAlpha(pulse);
    }
  }
}

// ─── Запуск ──────────────────────────────────────────────────
const game = new Phaser.Game({
  type: Phaser.AUTO,
  width: W,
  height: H,
  parent: 'game-container',
  transparent: true,
  physics: { default:'arcade', arcade:{gravity:{y:0},debug:false} },
  scene: [ArenaScene]
});
