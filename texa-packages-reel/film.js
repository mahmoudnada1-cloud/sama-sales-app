// Texa room packages: pure function of time. window.seek(t) paints frame t (see lib/motion.js).
// The supplied voice-over is the clock: every scene starts on a spoken phrase (seconds, VO delayed 0.5 s).
import * as M from './lib/motion.js';

const { W, H, E, lerp, clamp, spring, SPRING, wobble, font, text, fill, cover, rrect } = M;

const C = { navy: '#16213d', cream: '#faf9f7', orange: '#cc5500', steel: '#5b6b8c', white: '#ffffff' };
const DISPLAY = 'Display', UI = 'UI';
const PERIOD = 0.6;                       // beats.json: 100 bpm
const B = (t) => t / PERIOD;              // seconds -> beats (for HITS)

// Phrase onsets in film time (silences measured in the recording + 0.5 s cover hold).
const T = {
  cover: 0, hook: 0.5, room: 3.97, price: 5.7, pick: 8.93,
  items: [9.9, 10.85, 11.8, 12.75], one: 13.89,
  packs: 15.7, steps: [16.55, 17.4, 18.25, 19.1], taste: 18.06,
  stock: 20.21, end: 22.15,
};

const HITS = [
  [B(0.5), 'cover lifts', 'whoosh', { len: 0.45, from: 500, to: 2200 }],
  [B(0.62), 'hook line 1', 'pop', { pitch: 'A4' }],
  [B(1.5), 'hook line 2', 'pop', { pitch: 'D5' }],
  [B(2.3), 'hook line 3', 'pop', { pitch: 'F#5' }],
  [B(3.05), 'how much?', 'bell', { pitch: 'A5' }],
  [B(3.9), 'room plan', 'sub', { len: 0.5 }],
  [B(4.2), 'plan draws', 'tick'],
  [B(5.7), 'count starts', 'type', { n: 9, len: 0.85 }],
  [B(6.6), 'price lands', 'bell', { pitch: 'D6' }],
  [B(8.9), 'to products', 'whoosh', { len: 0.4, from: 2200, to: 700 }],
  [B(9.9), 'wall panel', 'click'],
  [B(10.85), 'floor', 'click'],
  [B(11.8), 'wallpaper', 'click'],
  [B(12.75), 'skirting', 'click'],
  [B(13.89), 'grid locks', 'thud'],
  [B(15.65), 'packages', 'whoosh', { len: 0.45, from: 600, to: 2400 }],
  [B(16.55), 'pack 2', 'tick'],
  [B(17.4), 'pack 3', 'tick'],
  [B(18.25), 'pack 4', 'tick'],
  [B(19.1), 'pack 5', 'tick'],
  [B(20.21), 'stock stamp', 'thud'],
  [B(22.1), 'end card', 'whoosh', { len: 0.4, from: 700, to: 2000 }],
  [B(22.35), 'logo', 'bell', { pitch: 'D6' }],
];

// ---------------------------------------------------------------- helpers
const sp = (t, t0, cfg = SPRING.snappy) => spring(t - t0, cfg);
const P = (t, a, b) => clamp((t - a) / (b - a));
const rtl = (ctx) => { ctx.direction = 'rtl'; };

// A line of Arabic revealed word by word: words are whole strings (shaping stays intact),
// laid out right-to-left around cx. times[i] = second the word lands.
function wordLine(ctx, t, words, times, cx, y, f, colors, rise = 70) {
  ctx.save(); rtl(ctx); ctx.font = f;
  const space = ctx.measureText(' ').width;
  const ws = words.map((w) => ctx.measureText(w).width);
  const total = ws.reduce((a, b) => a + b, 0) + space * (words.length - 1);
  let x = cx + total / 2;
  words.forEach((w, i) => {
    const k = sp(t, times[i], SPRING.bouncy);
    if (k > 0) {
      ctx.save();
      ctx.beginPath(); ctx.rect(0, y - 260, W, 300); ctx.clip();      // rises out of its own baseline
      ctx.globalAlpha = clamp(k * 3);
      text(ctx, w, x, y + (1 - k) * rise, f, Array.isArray(colors) ? colors[i] : colors, 'right');
      ctx.restore();
    }
    x -= ws[i] + space;
  });
  ctx.restore();
}

function card(ctx, img, x, y, w, h, r, opts = {}) {
  ctx.save();
  ctx.shadowColor = 'rgba(22,33,61,0.22)'; ctx.shadowBlur = 40; ctx.shadowOffsetY = 18;
  rrect(ctx, x, y, w, h, r); ctx.fillStyle = C.white; ctx.fill();
  ctx.restore();
  if (img) cover(ctx, img, x, y, w, h, { radius: r, ...opts });
}

function logoChip(ctx, IMG, k, x = W - 72 - 150, y = 120, size = 150) {
  if (k <= 0) return;
  ctx.save();
  ctx.translate(x + size / 2, y + size / 2); ctx.scale(k, k); ctx.translate(-size / 2, -size / 2);
  ctx.shadowColor = 'rgba(0,0,0,0.16)'; ctx.shadowBlur = 24; ctx.shadowOffsetY = 8;
  rrect(ctx, 0, 0, size, size, size * 0.24); ctx.fillStyle = C.white; ctx.fill();
  ctx.shadowColor = 'transparent';
  if (IMG.logo) ctx.drawImage(IMG.logo, size * 0.1, size * 0.1, size * 0.8, size * 0.8);
  ctx.restore();
}

// ---------------------------------------------------------------- S0 cover + S1 hook   (0 .. 3.9)
function sceneHook(ctx, t, IMG) {
  fill(ctx, C.cream);
  // the room photo the question is about: rises in under the type, slow log push
  const kin = sp(t, 0.55, SPRING.gentle);
  const z = 1.0 * (1.14 / 1.0) ** P(t, 0.5, 3.9);
  const cy = lerp(H + 100, 1010, kin);
  card(ctx, IMG.floorOak, 90, cy, 900, 720, 44, { zoom: z, fy: 0.6 });
  // the feature wall slides over it from the left, overlapping
  const k2 = sp(t, 1.5, SPRING.gentle);
  if (k2 > 0) card(ctx, IMG.panelWood, lerp(-520, 60, k2), cy + 430, 470, 430, 36, { zoom: 1.05 });

  const f = font(124, 900, DISPLAY);
  wordLine(ctx, t, ['عارف', 'مع', 'تِكسا'], [0.62, 0.9, 1.08], W / 2, 430, f, [C.navy, C.navy, C.orange]);
  wordLine(ctx, t, ['تقدر', 'تجدّد'], [1.5, 1.85], W / 2, 580, f, C.navy);
  wordLine(ctx, t, ['غرفتك', 'كاملة'], [2.3, 2.62], W / 2, 730, f, C.navy);
  // "بكم؟" lands big in a pill with a squash
  const kb = sp(t, 3.05, SPRING.bouncy);
  if (kb > 0) {
    const q = 0.08 * wobble((t - 3.05) / PERIOD, 2.2, 5);
    ctx.save(); ctx.translate(W / 2, 900); ctx.scale(kb * (1 + q), kb * (1 - q));
    rrect(ctx, -230, -110, 460, 190, 95); ctx.fillStyle = C.orange; ctx.fill();
    rtl(ctx); text(ctx, 'بكم؟', 0, 38, font(140, 900, DISPLAY), C.white, 'center');
    ctx.restore();
  }
  logoChip(ctx, IMG, sp(t, 0.8, SPRING.bouncy));

  // cover board (frame 0 = the poster): lifts off like a sheet, hinge at the top
  const ex = E.inBack(P(t, 0.5, 0.95), 1.2);
  if (ex < 1) {
    ctx.save();
    ctx.translate(0, -ex * (H + 120));
    ctx.translate(W / 2, 0); ctx.rotate(-0.05 * ex); ctx.translate(-W / 2, 0);
    ctx.shadowColor = 'rgba(0,0,0,0.3)'; ctx.shadowBlur = 50 * (ex > 0 ? 1 : 0); ctx.shadowOffsetY = 20;
    ctx.drawImage(IMG.b1, 0, 0, W, H);
    ctx.restore();
  }
}

// ---------------------------------------------------------------- S2 room 5x5 + price   (3.9 .. 8.9)
function scenePrice(ctx, t, IMG) {
  fill(ctx, C.navy);
  const up = sp(t, 5.55, SPRING.gentle);                 // plan moves up when the price arrives
  const side = lerp(680, 470, up), cx = W / 2 + 30, cy = lerp(900, 600, up);
  const x0 = cx - side / 2, y0 = cy - side / 2;
  // floor plan outline draws itself (stroke grows around the square)
  const d = E.outCubic(P(t, 4.0, 4.9));
  ctx.save();
  ctx.lineWidth = 10; ctx.strokeStyle = C.cream; ctx.lineJoin = 'round'; ctx.lineCap = 'round';
  ctx.setLineDash([side * 4 * d, side * 4]);
  ctx.strokeRect(x0, y0, side, side);
  ctx.setLineDash([]);
  // parquet planks fill the plan
  const pf = E.outCubic(P(t, 4.5, 5.4));
  if (pf > 0) {
    ctx.save(); ctx.beginPath(); ctx.rect(x0 + 5, y0 + 5, side - 10, (side - 10) * pf); ctx.clip();
    ctx.globalAlpha = 0.9; cover(ctx, IMG.floorOak, x0 + 5, y0 + 5, side - 10, side - 10, { zoom: 1.6, fy: 0.9 });
    ctx.restore();
  }
  ctx.restore();
  // dimension labels
  const kd = sp(t, 4.25, SPRING.bouncy);
  if (kd > 0) {
    const fs = lerp(110, 80, up);
    ctx.save(); ctx.direction = 'ltr';
    ctx.globalAlpha = clamp(kd * 2);
    text(ctx, '5 م', cx, y0 - 34 - (1 - kd) * 40, font(fs, 900, DISPLAY), C.cream, 'center');
    ctx.translate(x0 - 40 - (1 - kd) * 40, cy); ctx.rotate(-Math.PI / 2);
    text(ctx, '5 م', 0, 0, font(fs, 900, DISPLAY), C.cream, 'center');
    ctx.restore();
  }
  // price block
  const kl = sp(t, 5.6, SPRING.snappy);
  if (kl > 0) {
    ctx.save(); rtl(ctx); ctx.globalAlpha = clamp(kl * 2);
    text(ctx, 'بأقل من', W / 2, 1010 + (1 - kl) * 60, font(110, 900, DISPLAY), C.cream, 'center');
    ctx.restore();
  }
  const kn = sp(t, 5.75, SPRING.snappy);
  if (kn > 0) {
    const cnt = E.outExpo(P(t, 5.75, 6.6));
    const n = Math.round(3399 * cnt);
    const str = n >= 1000 ? `${Math.floor(n / 1000)},${String(n % 1000).padStart(3, '0')}` : String(n);
    const land = 0.06 * wobble((t - 6.6) / PERIOD, 2.4, 5);
    const fz = font(270, 900, DISPLAY);
    ctx.save(); ctx.direction = 'ltr';
    ctx.translate(W / 2 + 75, 1270); ctx.scale(kn * (1 + land), kn * (1 - land));
    ctx.font = fz; const wn = ctx.measureText('3,399').width;
    text(ctx, str, 0, 0, fz, C.orange, 'center');
    if (IMG.riyalW) ctx.drawImage(IMG.riyalW, -wn / 2 - 160, -180, 136, 165);
    ctx.restore();
  }
  const kv = sp(t, 7.3, SPRING.gentle);
  if (kv > 0) {
    ctx.save(); rtl(ctx); ctx.globalAlpha = clamp(kv * 2);
    text(ctx, 'قيمة المنتجات · شاملة الضريبة', W / 2, 1410 + (1 - kv) * 40, font(58, 700, UI), '#cdd6e8', 'center');
    ctx.restore();
  }
  logoChip(ctx, IMG, 1);
}

// ---------------------------------------------------------------- S3 products + S4 grid   (8.9 .. 15.65)
const ITEMS = [
  { key: 'panelWood', role: 'جدار مميز', name: 'بديل شيبورد خشبي', fy: 0.5 },
  { key: 'floorOak', role: 'أرضية باركيه', name: 'باركيه SPC بلوط فاتح', fy: 0.7 },
  { key: 'wallOff', role: 'ورق جدران', name: 'ورق جدران أوف وايت', fy: 0.5 },
  { key: 'skirt', role: 'نعلة', name: 'نعلة فايبر فضي', fy: 0.5 },
];
const BIG = { x: 90, y: 470, w: 900, h: 1010 };
const CELL = (i) => {                       // RTL grid like the board: wall TL, floor TR, paper BR, skirting BL
  const col = [0, 1, 1, 0][i], row = [0, 0, 1, 1][i];
  return { x: 100 + col * 460, y: 500 + row * 590, w: 420, h: 460 };
};
function sceneProducts(ctx, t, IMG) {
  fill(ctx, C.cream);
  // title swaps on the phrase
  const ko = sp(t, T.one, SPRING.snappy);
  const k1 = sp(t, T.pick, SPRING.bouncy);
  ctx.save(); rtl(ctx);
  if (ko < 1) { ctx.globalAlpha = clamp(k1 * 3) * (1 - clamp(ko * 2)); text(ctx, 'اختار باقتك', W / 2, 400 + (1 - k1) * 60 - ko * 80, font(128, 900, DISPLAY), C.navy, 'center'); }
  if (ko > 0) { ctx.globalAlpha = clamp(ko * 2); text(ctx, 'كلها من مكان واحد', W / 2, 400 + (1 - ko) * 80, font(112, 900, DISPLAY), C.orange, 'center'); }
  ctx.restore();

  ITEMS.forEach((it, i) => {
    const tin = T.items[i], tout = i < 3 ? T.items[i + 1] : T.one;
    const kin = sp(t, tin, SPRING.snappy);
    if (kin <= 0) return;
    const kout = i < 3 ? sp(t, tout, SPRING.snappy) : 0;       // whip: slides out left as the next slides in
    const kg = sp(t, T.one + i * 0.06, SPRING.gentle);         // then everything gathers into the grid
    const z = 1.0 * (1.22 / 1.0) ** P(t, tin, tout);           // log-space push on each product
    const c = CELL(i);
    const bx = BIG.x + (1 - kin) * W - kout * W;
    const x = lerp(bx, c.x, kg), y = lerp(BIG.y, c.y, kg), w = lerp(BIG.w, c.w, kg), h = lerp(BIG.h, c.h, kg);
    if (x > W || x + w < 0) return;
    card(ctx, IMG[it.key], x, y, w, h, lerp(48, 30, kg), { zoom: lerp(z, 1, kg), fy: it.fy });
    // label rides with the card
    ctx.save(); rtl(ctx);
    const lx = x + w / 2;
    if (kg < 1) {
      ctx.globalAlpha = (1 - clamp(kg * 2.5));
      text(ctx, it.role, lx, y + h + 110, font(96, 900, DISPLAY), C.orange, 'center');
      text(ctx, it.name, lx, y + h + 190, font(54, 700, UI), C.navy, 'center');
    }
    if (kg > 0.4) {
      ctx.globalAlpha = clamp((kg - 0.4) * 3);
      text(ctx, it.role, lx, y + h + 72, font(56, 900, DISPLAY), C.navy, 'center');
    }
    ctx.restore();
  });
  logoChip(ctx, IMG, 1);
}

// ---------------------------------------------------------------- S5-7 packages carousel + stock stamp   (15.65 .. 22.1)
const BOARDS = ['b1', 'b2', 'b3', 'b4', 'b5'];
function scenePacks(ctx, t, IMG) {
  fill(ctx, C.navy);
  // header: swaps on the second phrase, leaves for the stamp
  const ka = sp(t, T.packs, SPRING.bouncy), kb = sp(t, T.taste, SPRING.snappy), kc = sp(t, T.stock, SPRING.snappy);
  ctx.save(); rtl(ctx);
  if (kb < 1) {
    ctx.globalAlpha = clamp(ka * 3) * (1 - clamp(kb * 2));
    text(ctx, 'باقات مميزة', W / 2, 330 + (1 - ka) * 60 - kb * 70, font(120, 900, DISPLAY), C.cream, 'center');
    text(ctx, 'من تِكسا للديكور', W / 2, 440 + (1 - ka) * 60 - kb * 70, font(76, 900, DISPLAY), C.orange, 'center');
  }
  if (kb > 0 && kc < 1) {
    ctx.globalAlpha = clamp(kb * 2) * (1 - clamp(kc * 2));
    text(ctx, 'تنسيق جاهز', W / 2, 330 + (1 - kb) * 70 - kc * 70, font(120, 900, DISPLAY), C.cream, 'center');
    text(ctx, 'يناسب ذوقك', W / 2, 440 + (1 - kb) * 70 - kc * 70, font(96, 900, DISPLAY), C.orange, 'center');
  }
  ctx.restore();

  // coverflow of the five real boards; the focus steps one board at a time
  let c = 0; T.steps.forEach((s) => { c += sp(t, s, SPRING.snappy); });
  const enter = sp(t, 15.65, SPRING.gentle);
  const drop = sp(t, T.stock, SPRING.gentle);
  const order = BOARDS.map((k, i) => i).sort((a, b) => Math.abs(b - c) - Math.abs(a - c));   // far first
  order.forEach((i) => {
    const d = i - c, ad = Math.min(2, Math.abs(d));
    const s = (0.6 - 0.09 * ad) * lerp(0.7, 1, enter) * lerp(1, 0.86, drop);
    const x = W / 2 + d * 500, y = lerp(H + 700, 1060, enter) + ad * 26 + drop * 70;
    ctx.save();
    ctx.translate(x, y); ctx.rotate(d * 0.035); ctx.scale(s, s);
    ctx.shadowColor = 'rgba(0,0,0,0.45)'; ctx.shadowBlur = 60; ctx.shadowOffsetY = 26;
    rrect(ctx, -W / 2, -H / 2, W, H, 60); ctx.fillStyle = C.cream; ctx.fill();
    ctx.shadowColor = 'transparent';
    rrect(ctx, -W / 2, -H / 2, W, H, 60); ctx.clip();
    ctx.drawImage(IMG[BOARDS[i]], -W / 2, -H / 2, W, H);
    ctx.fillStyle = `rgba(22,33,61,${0.42 * Math.min(1, ad) + 0.5 * drop})`; ctx.fillRect(-W / 2, -H / 2, W, H);
    ctx.restore();
  });

  // "until stock lasts" stamps down over the boards
  const ks = sp(t, T.stock, SPRING.bouncy);
  if (ks > 0) {
    const sc = lerp(1.9, 1, ks);
    ctx.save(); ctx.translate(W / 2, 980); ctx.rotate(-0.06); ctx.scale(sc, sc); ctx.globalAlpha = clamp(ks * 4);
    ctx.shadowColor = 'rgba(0,0,0,0.4)'; ctx.shadowBlur = 40; ctx.shadowOffsetY = 16;
    rrect(ctx, -440, -150, 880, 300, 150); ctx.fillStyle = C.orange; ctx.fill();
    ctx.shadowColor = 'transparent'; rtl(ctx);
    text(ctx, 'العرض', 0, -22, font(72, 900, DISPLAY), '#ffe6d6', 'center');
    text(ctx, 'حتى نفاذ الكمية', 0, 82, font(100, 900, DISPLAY), C.white, 'center');
    ctx.restore();
  }
  logoChip(ctx, IMG, 1);
}

// ---------------------------------------------------------------- S8 end card   (22.1 ..)
function sceneEnd(ctx, t, IMG) {
  fill(ctx, C.cream);
  const kl = sp(t, 22.3, SPRING.bouncy);
  if (kl > 0) logoChip(ctx, IMG, kl, W / 2 - 170, 470, 340);
  const k1 = sp(t, 22.25, SPRING.bouncy), k2 = sp(t, 22.6, SPRING.snappy), k3 = sp(t, 22.85, SPRING.snappy), k4 = sp(t, 23.1, SPRING.gentle);
  ctx.save(); rtl(ctx);
  if (k1 > 0) { ctx.globalAlpha = clamp(k1 * 3); text(ctx, 'تواصل معنا الحين', W / 2, 1020 + (1 - k1) * 70, font(118, 900, DISPLAY), C.navy, 'center'); }
  ctx.restore();
  if (k2 > 0) {
    ctx.save(); ctx.direction = 'ltr'; ctx.globalAlpha = clamp(k2 * 3);
    text(ctx, '0591409002', W / 2, 1200 + (1 - k2) * 60, font(140, 900, DISPLAY), C.orange, 'center');
    ctx.restore();
  }
  if (k3 > 0) {
    ctx.save(); ctx.translate(W / 2, 1350); ctx.scale(k3, k3);
    rrect(ctx, -330, -62, 660, 124, 62); ctx.fillStyle = C.navy; ctx.fill();
    ctx.direction = 'ltr'; text(ctx, 'texadecore.store', 0, 20, font(60, 700, UI), C.white, 'center');
    ctx.restore();
  }
  if (k4 > 0) {
    ctx.save(); rtl(ctx); ctx.globalAlpha = clamp(k4 * 2);
    text(ctx, 'وفّر مع تِكسا للديكور', W / 2, 1530 + (1 - k4) * 40, font(64, 900, DISPLAY), C.steel, 'center');
    ctx.restore();
  }
}

// push transition: scene A slides up and out as scene B follows from below, both on screen
function push(ctx, t, t0, len, A, Bs) {
  const p = E.inOutCubic(P(t, t0, t0 + len));
  ctx.save(); ctx.translate(0, -p * H); A(); ctx.restore();
  ctx.save(); ctx.translate(0, (1 - p) * H); ctx.beginPath(); ctx.rect(0, 0, W, H); ctx.clip(); Bs(); ctx.restore();
}

M.film({
  fonts: [font(100, 900, DISPLAY), font(40, 700, UI)],
  samples: 8,
  images: {
    logo: 'assets/logo.png', riyalW: 'assets/p/riyal-white.png',
    floorOak: 'assets/p/floor-oak.jpg', panelWood: 'assets/p/panel-wood-oak.jpg',
    wallOff: 'assets/p/wall-offwhite.webp', skirt: 'assets/p/skirt-silver.jpg',
    b1: 'assets/b/d1-warm-wood.jpg', b2: 'assets/b/d2-gray-modern.jpg', b3: 'assets/b/d3-light-lux.jpg',
    b4: 'assets/b/d4-beige-japandi.jpg', b5: 'assets/b/d5-navy-bold.jpg',
  },
  hits: HITS,
  draw(ctx, u, t, IMG) {
    const X = 0.4;                                    // transition length (s)
    if (t < 3.7) sceneHook(ctx, t, IMG);
    else if (t < 3.7 + X) push(ctx, t, 3.7, X, () => sceneHook(ctx, t, IMG), () => scenePrice(ctx, t, IMG));
    else if (t < 8.6) scenePrice(ctx, t, IMG);
    else if (t < 8.6 + X) push(ctx, t, 8.6, X, () => scenePrice(ctx, t, IMG), () => sceneProducts(ctx, t, IMG));
    else if (t < 15.4) sceneProducts(ctx, t, IMG);
    else if (t < 15.4 + X) push(ctx, t, 15.4, X, () => sceneProducts(ctx, t, IMG), () => scenePacks(ctx, t, IMG));
    else if (t < 21.9) scenePacks(ctx, t, IMG);
    else if (t < 21.9 + X) push(ctx, t, 21.9, X, () => scenePacks(ctx, t, IMG), () => sceneEnd(ctx, t, IMG));
    else sceneEnd(ctx, t, IMG);
  },
});
