// تكسا في الذكاء الاصطناعي: pure function of time. window.seek(t) paints frame t (see lib/motion.js).
// Timing is in beats (u) on the measured grid; docs/shotlist.md is the plan this file follows.
import * as M from './lib/motion.js';

const { W, H, FORMAT, E, prog, lerp, clamp, springU, springKeys, SPRING, wobble, shake, font, fill, cover, rrect, bump } = M;

// Brand tokens (site identity, confirmed with the user). One accent: orange. Gold only on navy pills.
const C = { cream: '#faf9f7', navy: '#16213d', orange: '#cc5500', gold: '#e8b33d', grey: '#5b6478', line: '#eee6da', white: '#ffffff', green: '#16a34a', bubble: '#eef3fb', hl: '#ffe2cc' };
const FACE = 'Tj, TjL';
const S = FORMAT.safe, CX = S.x + S.w / 2;

// Every visual accent: [beat, label, sfx, opts]. sfx.mjs voices them.
const HITS = [
  [0, 'hook lands', 'impact'],
  [1, 'logo tile 1', 'pop', { pitch: 'A4' }],
  [2, 'logo tile 2', 'pop', { pitch: 'C5' }],
  [3, 'logo tile 3', 'pop', { pitch: 'E5' }],
  [4, 'hook line 2', 'click'],
  [5, 'word', 'tick'],
  [6, 'same name pill', 'thud'],
  [8, 'reveal riser ends / question', 'riser', { len: 0.9 }],
  [8, 'question in', 'whoosh', { len: 0.4 }],
  [9.4, 'pill word', 'pop', { pitch: 'D5' }],
  [12, 'shelf up', 'click'],
  [16, 'drop: chatgpt card', 'impact'],
  [16.6, 'typing', 'type', { len: 0.5, n: 7 }],
  [20, 'texa highlight', 'bell', { pitch: 'D6' }],
  [22, 'whip to perplexity', 'whoosh', { len: 0.4, from: 600, to: 2400 }],
  [22.6, 'typing', 'type', { len: 0.5, n: 7 }],
  [25, 'row 1', 'tick'],
  [25.5, 'row 2', 'tick'],
  [26, 'row 3 / highlight', 'bell', { pitch: 'E6' }],
  [28, 'whip to gemini', 'whoosh', { len: 0.4, from: 2400, to: 600 }],
  [28.6, 'typing', 'type', { len: 0.5, n: 7 }],
  [32, 'texa highlight', 'bell', { pitch: 'F#6' }],
  [34, 'check 1', 'pop', { pitch: 'A5' }],
  [35, 'check 2', 'pop', { pitch: 'C6' }],
  [36, 'check 3', 'pop', { pitch: 'E6' }],
  [37, 'headline punch', 'impact'],
  [42, 'logo forward', 'swell'],
  [44, 'positioning line', 'click'],
  [47, 'saudi', 'blip', { pitch: 'A5' }],
  [50, 'end card pill', 'impact'],
  [51.5, 'url', 'tick'],
  [54, 'last line', 'bell', { pitch: 'D6' }],
];

// ---------------------------------------------------------------- helpers
function T(ctx, str, x, y, size, weight, color, o = {}) {
  const { align = 'center', a = 1, sc = 1, dy = 0 } = o;
  if (a <= 0.003 || sc <= 0.003) return;
  ctx.save();
  ctx.globalAlpha *= clamp(a);
  ctx.translate(x, y + dy); ctx.scale(sc, sc);
  ctx.font = font(size, weight, FACE); ctx.fillStyle = color; ctx.textAlign = align; ctx.direction = 'rtl';
  ctx.fillText(str, 0, 0);
  ctx.restore();
}
function tw(ctx, str, size, weight) { ctx.font = font(size, weight, FACE); return ctx.measureText(str).width; }
// text inside a filled pill; returns nothing. (x,y) = centre x, text baseline.
function pill(ctx, str, x, y, size, weight, bg, fg, o = {}) {
  const { a = 1, sc = 1, padX = 0.42, r = 0.32 } = o;
  if (a <= 0.003 || sc <= 0.003) return;
  const w = tw(ctx, str, size, weight) + size * padX * 2, h = size * 1.42;
  ctx.save(); ctx.globalAlpha *= clamp(a);
  ctx.translate(x, y - size * 0.36); ctx.scale(sc, sc);
  rrect(ctx, -w / 2, -h / 2, w, h, size * r); ctx.fillStyle = bg; ctx.fill();
  ctx.font = font(size, weight, FACE); ctx.fillStyle = fg; ctx.textAlign = 'center'; ctx.direction = 'rtl';
  ctx.fillText(str, 0, size * 0.36);
  ctx.restore();
}
function shadowBox(ctx, x, y, w, h, r, o = {}) {
  ctx.save();
  ctx.shadowColor = 'rgba(22,33,61,0.16)'; ctx.shadowBlur = o.blur ?? 40; ctx.shadowOffsetY = o.off ?? 16;
  rrect(ctx, x, y, w, h, r); ctx.fillStyle = o.fill || C.white; ctx.fill();
  ctx.restore();
  if (o.stroke !== false) { rrect(ctx, x, y, w, h, r); ctx.strokeStyle = C.line; ctx.lineWidth = 2; ctx.stroke(); }
}
// white rounded tile with an image inside, centred on (cx, cy)
function tile(ctx, img, cx, cy, size, o = {}) {
  const { sc = 1, a = 1, pad = 0.17, rot = 0 } = o;
  if (sc <= 0.003 || a <= 0.003) return;
  ctx.save(); ctx.globalAlpha *= clamp(a);
  ctx.translate(cx, cy); ctx.rotate(rot); ctx.scale(sc, sc);
  shadowBox(ctx, -size / 2, -size / 2, size, size, size * 0.2);
  const p = size * pad;
  if (img) ctx.drawImage(img, -size / 2 + p, -size / 2 + p, size - 2 * p, size - 2 * p);
  ctx.restore();
}
function check(ctx, cx, cy, r, k) {
  if (k <= 0.003) return;
  ctx.save(); ctx.translate(cx, cy); ctx.scale(k, k);
  ctx.beginPath(); ctx.arc(0, 0, r, 0, M.TAU); ctx.fillStyle = C.green; ctx.fill();
  ctx.lineWidth = r * 0.24; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = '#fff';
  ctx.beginPath(); ctx.moveTo(-r * 0.42, r * 0.02); ctx.lineTo(-r * 0.1, r * 0.34); ctx.lineTo(r * 0.46, -r * 0.3); ctx.stroke();
  ctx.restore();
}
const LOGOS = ['gpt', 'ppx', 'gem'];
const ENG = [
  { key: 'gpt', name: 'ChatGPT' },
  { key: 'ppx', name: 'Perplexity' },
  { key: 'gem', name: 'Gemini' },
];

// The TEXA logo tile: lives at the top through the film, comes forward for the positioning shot.
function texaLogo(ctx, u, IMG) {
  const [y, size] = springKeys(u, [[0, [300, 190]], [42, [640, 400]], [50, [520, 300]]], SPRING.gentle);
  const k = springU(u, -0.6, SPRING.snappy);
  tile(ctx, IMG.texa, CX, y, size, { sc: clamp(k, 0, 1.2), pad: 0.1 });
}

// ---------------------------------------------------------------- S1+S2 hook   (u 0..8)
function sceneHook(ctx, u, IMG) {
  // line block lifts when line 2 arrives
  const lift = springU(u, 4, SPRING.gentle);
  const y0 = lerp(620, 520, lift);
  // "سألنا 3 برامج" with the number counting as tiles land
  const n = u < 1.95 ? 1 : u < 2.95 ? 2 : 3;
  const k0 = springU(u, -0.35, SPRING.bouncy);
  const sizeA = lerp(118, 84, lift);
  T(ctx, `سألنا ${u < 1 ? '3' : n} برامج`, CX, y0, sizeA, 900, C.navy, { sc: 0.6 + 0.4 * k0, a: k0 * 3 });
  const k1 = springU(u, 0.25, SPRING.bouncy);
  T(ctx, 'ذكاء اصطناعي', CX, y0 + sizeA * 1.25, sizeA, 900, C.orange, { sc: 0.6 + 0.4 * k1, a: k1 * 3 });
  // the three engine tiles: fall and settle one per beat, then tuck up small
  const rowY = lerp(1010, 300 + 0 * lift, 0);
  LOGOS.forEach((key, i) => {
    const u0 = 1 + i - 0.18;
    const k = springU(u, u0, SPRING.bouncy);
    if (k <= 0) return;
    const [ty, ts] = springKeys(u, [[0, [1010, 230]], [4, [lerp(520, 520, 1) + 330, 150]]], SPRING.gentle);
    const gap = ts * 1.18;
    const x = CX + (i - 1) * gap;
    const q = 0.1 * wobble((u - (1 + i)) * 0.5, 2.6, 6);
    ctx.save(); ctx.translate(x, ty + ts / 2); ctx.scale(1 + q, 1 - q); ctx.translate(-x, -(ty + ts / 2));
    tile(ctx, IMG[key], x, ty - (1 - Math.min(k, 1.15)) * 700, ts, { a: k * 4 });
    ctx.restore();
  });
  // line 2: words land per half beat
  const y2 = 1100;
  const w = (uu) => springU(u, uu, SPRING.snappy);
  T(ctx, 'عن عروض بديل الشيبورد…', CX, y2, 70, 700, C.grey, { a: w(4) * 3, dy: (1 - w(4)) * 50 });
  T(ctx, 'وكلهم جابوا', CX, y2 + 130, 104, 900, C.navy, { a: w(5) * 3, dy: (1 - w(5)) * 60 });
  const kp = springU(u, 6, SPRING.bouncy);
  pill(ctx, 'نفس الاسم 👀', CX, y2 + 290, 104, 900, C.orange, C.white, { sc: kp, a: kp * 3 });
  // hidden name bar: pulses, still secret
  const kb = springU(u, 6.5, SPRING.snappy);
  if (kb > 0) {
    const bw = 520 * kb, bh = 92, by = y2 + 370;
    const pulse = 1 + 0.03 * Math.sin(u * Math.PI * 2);
    ctx.save(); ctx.translate(CX, by + bh / 2); ctx.scale(pulse, pulse);
    rrect(ctx, -bw / 2, -bh / 2, bw, bh, 26); ctx.fillStyle = C.navy; ctx.fill();
    if (kb > 0.6) for (let i = 0; i < 9; i++) {
      const a = 0.25 + 0.2 * Math.sin(u * 3 + i * 1.7);
      rrect(ctx, -bw / 2 + 34 + i * 52, -14, 36, 28, 8); ctx.fillStyle = `rgba(232,179,61,${a})`; ctx.fill();
    }
    ctx.restore();
  }
}

// ---------------------------------------------------------------- S3 the need   (u 8..16)
function sceneNeed(ctx, u, IMG) {
  const w = (uu, cfg = SPRING.snappy) => springU(u, uu, cfg);
  const y = 560;
  T(ctx, 'تدوّر على', CX, y, 112, 900, C.navy, { a: w(8) * 3, dy: (1 - w(8)) * 70 });
  const kp = w(9.4, SPRING.bouncy);
  pill(ctx, 'بديل شيبورد', CX, y + 170, 112, 900, C.orange, C.white, { sc: kp, a: kp * 3 });
  T(ctx, 'بسعر أقل', CX, y + 350, 112, 900, C.navy, { a: w(11) * 3, dy: (1 - w(11)) * 70 });
  T(ctx, 'وجودة تجمّل؟', CX, y + 510, 112, 900, C.navy, { a: w(12.6) * 3, dy: (1 - w(12.6)) * 70 });
  // real product shelf from the site, panning
  const ks = w(11.6, SPRING.gentle);
  if (ks > 0 && IMG.shelf) {
    const cw = S.w, ch = 330, cx = S.x, cy = lerp(H + 40, 1150, ks);
    shadowBox(ctx, cx, cy, cw, ch, 30);
    const fx = lerp(0.95, 0.1, prog(u, 11.6, 16.5));
    cover(ctx, IMG.shelf, cx + 8, cy + 8, cw - 16, ch - 16, { fx, fy: 0.46, zoom: 2.35, radius: 24 });
  }
}

// ---------------------------------------------------------------- S4-6 the three answers   (u 16..34)
const Q = 'عروض بديل الشيبورد';
function cardBody(ctx, i, lu, x, y, w) {
  // lu = local beats since this card's start. Returns the body height drawn.
  const R = x + w - 44, Lx = x + 44;
  const line = (k, uu) => springU(lu + 0, uu, SPRING.snappy) * 1;
  const A = 1.9;   // answer starts
  const on = (j) => { const k = springU(lu, A + j * 0.28, SPRING.snappy); return k; };
  const hlK = prog(lu, 4, 4.5);          // highlight at +4 beats
  const hl = (str, cx, by, size, k, align = 'center') => {
    const tw_ = tw(ctx, str, size, 900), pw = tw_ + 36, ph = size * 1.42;
    const px = align === 'right' ? cx - pw : cx - pw / 2;
    rrect(ctx, px, by - size * 1.02, pw, ph, 14);
    ctx.fillStyle = M.mix(C.hl, C.orange, k); ctx.fill();
    const pop = 1 + 0.08 * bump(lu, 4.25, 0.5);
    T(ctx, str, px + pw / 2, by, size, 900, M.mix(C.orange, C.white, k), { sc: pop });
    return pw;
  };
  let yy = y;
  if (i === 0) {
    let k = on(0);
    if (k > 0) {
      ctx.save(); ctx.globalAlpha *= clamp(k * 3); ctx.translate(0, (1 - k) * 30);
      const size = 40;
      const pw = tw(ctx, 'تِكسا للديكور', size, 900) + 36;
      T(ctx, '🔥 عروض بديل الشيبورد من', R, yy + 52, size, 900, C.navy, { align: 'right' });
      const lead = tw(ctx, '🔥 عروض بديل الشيبورد من', size, 900);
      hl('تِكسا للديكور', R - lead - 18, yy + 52, size, hlK, 'right');
      ctx.restore();
    }
    yy += 110;
    k = on(1); T(ctx, 'لماذا تختار بديل الشيبورد من تِكسا؟', R, yy + 40, 40, 700, C.navy, { align: 'right', a: k * 3, dy: (1 - k) * 30 });
    yy += 84;
    ['مقاس اللوح 120 × 290 سم.', 'تشكيلة ألوان وتشطيبات.', 'خيارات مناسبة لتجديد جدران المجالس.'].forEach((s, j) => {
      k = on(2 + j);
      T(ctx, '•  ' + s, R - 6, yy + 40, 40, 500, '#2a2f3a', { align: 'right', a: k * 3, dy: (1 - k) * 30 });
      yy += 72;
    });
    k = on(5);
    T(ctx, 'عروض بديل الشيبورد – متجر تِكسا للديكور ↗', R, yy + 46, 36, 700, '#1558d6', { align: 'right', a: k * 3 });
    yy += 80;
  } else if (i === 1) {
    let k = on(0); T(ctx, 'عروض مميزة', R, yy + 52, 48, 900, C.navy, { align: 'right', a: k * 3, dy: (1 - k) * 30 });
    yy += 96;
    k = on(1);
    if (k > 0) {
      ctx.save(); ctx.globalAlpha *= clamp(k * 3);
      rrect(ctx, Lx, yy, w - 88, 76, 14); ctx.fillStyle = '#f4f1ec'; ctx.fill();
      T(ctx, 'المتجر', R - 20, yy + 52, 38, 900, C.navy, { align: 'right' });
      T(ctx, 'العرض', R - 330, yy + 52, 38, 900, C.navy, { align: 'right' });
      ctx.restore();
    }
    yy += 92;
    ['بديل شيبورد بيج لاتيه', 'بديل شيبورد بيج كاتشي', 'ألوان بني وخشبي وسادة'].forEach((s, j) => {
      k = on(2 + j);
      if (k > 0) {
        ctx.save(); ctx.globalAlpha *= clamp(k * 3); ctx.translate((1 - k) * -40, 0);
        const hk = prog(lu, 3 + j * 0.5, 3.3 + j * 0.5);
        const pwid = tw(ctx, 'تكسا ديكور', 38, 900) + 36;
        rrect(ctx, R - 12 - pwid, yy + 12, pwid, 62, 14); ctx.fillStyle = M.mix(C.hl, C.orange, hk); ctx.fill();
        T(ctx, 'تكسا ديكور', R - 12 - pwid / 2, yy + 56, 38, 900, M.mix(C.orange, C.white, hk), { sc: 1 + 0.1 * bump(lu, 3.15 + j * 0.5, 0.4) });
        T(ctx, s, R - 330, yy + 56, 38, 500, '#2a2f3a', { align: 'right' });
        ctx.fillStyle = C.line; ctx.fillRect(Lx, yy + 86, w - 88, 2);
        ctx.restore();
      }
      yy += 90;
    });
    k = on(5);
    if (k > 0) {
      ctx.save(); ctx.globalAlpha *= clamp(k * 3);
      rrect(ctx, R - 250, yy + 14, 250, 54, 12); ctx.fillStyle = '#f0f0f0'; ctx.fill();
      T(ctx, 'texadecore', R - 125, yy + 52, 32, 500, '#555');
      ctx.restore();
    }
    yy += 84;
  } else {
    let k = on(0); T(ctx, 'أبرز العروض في السوق السعودي', R, yy + 52, 44, 900, C.navy, { align: 'right', a: k * 3, dy: (1 - k) * 30 });
    yy += 110;
    k = on(1);
    if (k > 0) {
      ctx.save(); ctx.globalAlpha *= clamp(k * 3); ctx.translate(0, (1 - k) * 30);
      const pw = hl('تكسا ديكور:', R - 30, yy + 46, 42, hlK, 'right');
      T(ctx, '•', R, yy + 46, 42, 500, '#888', { align: 'right' });
      T(ctx, 'عروض على الألواح', R - 30 - pw - 16, yy + 46, 42, 500, '#2a2f3a', { align: 'right' });
      ctx.restore();
    }
    yy += 78;
    k = on(2); T(ctx, 'القماشية والخشبية والرخامية…', R - 30, yy + 46, 42, 500, '#2a2f3a', { align: 'right', a: k * 3, dy: (1 - k) * 30 });
    yy += 96;
    k = on(3);
    if (k > 0) {
      ctx.save(); ctx.globalAlpha *= clamp(k * 3);
      rrect(ctx, R - 360, yy + 6, 360, 58, 14); ctx.fillStyle = '#f0f0f0'; ctx.fill();
      T(ctx, 'تكسا ديكور Texa Decor', R - 180, yy + 46, 32, 500, '#555');
      ctx.restore();
    }
    yy += 84;
  }
  return yy - y;
}
const CARD_H = [800, 850, 640];
function drawCard(ctx, i, u, IMG) {
  const u0 = 16 + i * 6, lu = u - u0;
  if (lu < -0.6 || lu > 6.6) return;
  const eng = ENG[i];
  // enter: first card slams up from below on the drop, the others whip in from the right.
  // exit: whip out to the left while the next one is already on screen.
  const kin = springU(u, u0 - 0.28, i === 0 ? SPRING.bouncy : SPRING.snappy);
  const pout = E.inCubic(prog(u, u0 + 5.72, u0 + 6.25));
  const w = S.w, h = CARD_H[i], x0 = S.x, y0 = 550;
  let dx = 0, dy = 0;
  if (i === 0) dy = (1 - kin) * 1500; else dx = (1 - kin) * (W + 100);
  dx -= pout * (W + 200) * (i < 2 ? 1 : 0);
  let sc = 1, aOut = 1;
  if (i === 2) { sc = 1 - 0.35 * pout; dy -= pout * 240; aOut = 1 - pout; }
  // label above
  const lk = springU(u, u0 - 0.1, SPRING.snappy);
  ctx.save(); ctx.globalAlpha *= clamp(lk * 3) * (1 - prog(u, u0 + 5.6, u0 + 5.95));
  const nameW = tw(ctx, eng.name, 76, 900), askW = tw(ctx, 'اسأل ', 76, 700);
  const tot = nameW + askW, lx = CX + tot / 2;
  T(ctx, 'اسأل', lx, 500 + (1 - lk) * 30, 76, 700, C.navy, { align: 'right' });
  ctx.direction = 'ltr';
  ctx.font = font(76, 900, FACE); ctx.fillStyle = C.orange; ctx.textAlign = 'left'; ctx.direction = 'ltr';
  ctx.fillText(eng.name, CX - tot / 2, 500 + (1 - lk) * 30);
  ctx.restore();

  ctx.save();
  ctx.globalAlpha *= aOut;
  ctx.translate(x0 + w / 2 + dx, y0 + h / 2 + dy); ctx.scale(sc, sc); ctx.translate(-(x0 + w / 2), -(y0 + h / 2));
  if (i === 0) { const q = 0.03 * wobble((u - u0) * 0.5, 2.4, 6); ctx.translate(x0 + w / 2, y0 + h); ctx.scale(1 + q, 1 - q); ctx.translate(-(x0 + w / 2), -(y0 + h)); }
  shadowBox(ctx, x0, y0, w, h, 40);
  // header: engine logo + name
  if (IMG[eng.key]) ctx.drawImage(IMG[eng.key], x0 + 44, y0 + 34, 76, 76);
  ctx.font = font(50, 900, FACE); ctx.fillStyle = '#111'; ctx.textAlign = 'left'; ctx.direction = 'ltr';
  ctx.fillText(eng.name, x0 + 140, y0 + 90);
  ctx.fillStyle = C.line; ctx.fillRect(x0 + 44, y0 + 136, w - 88, 2);
  // typed query bubble, right-aligned
  const n = Math.floor(clamp((lu - 0.5) / 1.1) * Q.length);
  const typed = Q.slice(0, n);
  const bw = Math.max(110, tw(ctx, typed, 44, 700) + 76), bh = 92, bx = x0 + w - 44 - bw, by = y0 + 164;
  rrect(ctx, bx, by, bw, bh, 34); ctx.fillStyle = C.bubble; ctx.fill();
  T(ctx, typed, bx + bw - 38, by + 62, 44, 700, C.navy, { align: 'right' });
  if (n < Q.length && lu > 0.2) { ctx.fillStyle = C.navy; ctx.fillRect(bx + 26, by + 22, 4, 48); }
  // thinking dots
  if (lu > 1.55 && lu < 1.95) for (let d = 0; d < 3; d++) { ctx.beginPath(); ctx.arc(x0 + w - 70 - d * 34, by + bh + 46 + Math.sin(lu * 14 - d) * 8, 9, 0, M.TAU); ctx.fillStyle = '#bbb'; ctx.fill(); }
  const bodyH = cardBody(ctx, i, lu, x0, by + bh + 14, w);
  const ks = springU(lu, 3.4, SPRING.snappy);
  T(ctx, 'مقتطف من الإجابة', x0 + 44, y0 + h - 30, 26, 500, '#9a9a9a', { align: 'left', a: ks * 3 });
  ctx.restore();

  // navy/gold tag under the card
  const kt = springU(u, u0 + 4.2, SPRING.bouncy);
  const ta = 1 - prog(u, u0 + 5.6, u0 + 5.95);
  pill(ctx, 'تكسا ديكور قدّامك ✓', CX, 1470, 58, 900, C.navy, C.gold, { sc: kt, a: kt * 3 * ta, padX: 0.7, r: 0.4 });
}

// ---------------------------------------------------------------- S7 payoff   (u 34..42)
function scenePayoff(ctx, u, IMG) {
  const out = E.inCubic(prog(u, 41.5, 42.1));
  ctx.save(); ctx.globalAlpha *= 1 - out; ctx.translate(0, -out * 120);
  LOGOS.forEach((key, i) => {
    const k = springU(u, 33.7 + i * 0.12, SPRING.bouncy);
    const x = CX + (i - 1) * 250, y = 640;
    tile(ctx, IMG[key], x, y, 210, { sc: Math.min(k, 1.2), a: k * 4 });
    const kc = springU(u, 34 + i, SPRING.bouncy);
    check(ctx, x + 78, y + 78, 36, Math.min(kc, 1.3));
  });
  const k0 = springU(u, 34.1, SPRING.snappy);
  T(ctx, 'وين ما تبحث وتسأل…', CX, 900, 68, 700, C.grey, { a: k0 * 3, dy: (1 - k0) * 40 });
  ctx.save(); shake(ctx, u, 37, 16);
  const k1 = springU(u, 36.85, SPRING.bouncy);
  T(ctx, 'تلقى', CX, 1050, 120, 900, C.navy, { sc: 0.5 + 0.5 * k1, a: k1 * 4 });
  const k2 = springU(u, 37, SPRING.bouncy);
  pill(ctx, 'تكسا ديكور', CX, 1230, 132, 900, C.orange, C.white, { sc: k2, a: k2 * 4 });
  const k3 = springU(u, 37.9, SPRING.bouncy);
  T(ctx, 'قدّامك', CX, 1420, 120, 900, C.navy, { sc: 0.5 + 0.5 * k3, a: k3 * 4 });
  ctx.restore();
  ctx.restore();
}

// ---------------------------------------------------------------- S8 positioning   (u 42..50)
function scenePosition(ctx, u, IMG) {
  const out = E.inCubic(prog(u, 49.5, 50.05));
  // real shelf strip drifting behind, low
  if (IMG.shelf) {
    const ks = springU(u, 42.2, SPRING.gentle);
    ctx.save(); ctx.globalAlpha *= 0.9 * clamp(ks) * (1 - out);
    const cy = lerp(H, 1270, clamp(ks));
    shadowBox(ctx, S.x, cy, S.w, 230, 26);
    cover(ctx, IMG.shelf, S.x + 6, cy + 6, S.w - 12, 218, { fx: lerp(0.15, 0.9, prog(u, 42, 50.5)), fy: 0.62, zoom: 2.4, radius: 22 });
    ctx.restore();
  }
  ctx.save(); ctx.globalAlpha *= 1 - out;
  const k0 = springU(u, 42.1, SPRING.bouncy);
  T(ctx, 'تكسا ديكور', CX, 975, 116, 900, C.navy, { sc: 0.6 + 0.4 * k0, a: k0 * 4 });
  const k1 = springU(u, 44, SPRING.snappy);
  pill(ctx, 'وجهتك الأولى', CX, 1110, 78, 900, C.orange, C.white, { sc: k1, a: k1 * 4 });
  const k2 = springU(u, 45.3, SPRING.snappy);
  T(ctx, 'لبديل الشيبورد في السعودية', CX, 1215, 64, 700, C.navy, { a: k2 * 3, dy: (1 - k2) * 40 });
  ctx.restore();
}

// ---------------------------------------------------------------- S9 end card   (u 50..)
function sceneEnd(ctx, u) {
  const k0 = springU(u, 50, SPRING.bouncy);
  pill(ctx, 'اطلب الحين', CX, 890, 104, 900, C.navy, C.gold, { sc: k0, a: k0 * 4, padX: 0.8, r: 0.42 });
  const k1 = springU(u, 51.5, SPRING.snappy);
  ctx.save(); ctx.globalAlpha *= clamp(k1 * 3);
  ctx.font = font(70, 700, FACE); ctx.fillStyle = C.navy; ctx.textAlign = 'center'; ctx.direction = 'ltr';
  ctx.fillText('texadecore.store', CX, 1070 + (1 - k1) * 40);
  ctx.restore();
  const k2 = springU(u, 54, SPRING.bouncy);
  T(ctx, 'وخلي ديكورك غير', CX, 1260, 104, 900, C.orange, { sc: 0.6 + 0.4 * k2, a: k2 * 4 });
  // underline swipe
  const ku = E.outQuint(prog(u, 54.4, 55.4));
  if (ku > 0) { const lw = 560 * ku; rrect(ctx, CX - lw / 2, 1296, lw, 12, 6); ctx.fillStyle = C.gold; ctx.fill(); }
}

M.film({
  fonts: [font(100, 900, FACE), font(60, 700, FACE), font(40, 500, FACE), font(100, 900, 'Tj'), font(60, 700, 'Tj'), font(40, 500, 'Tj'), font(100, 900, 'TjL'), font(60, 700, 'TjL'), font(40, 500, 'TjL')],
  images: { texa: 'assets/logo/texa.png', gpt: 'assets/logo/chatgpt.svg', ppx: 'assets/logo/perplexity.svg', gem: 'assets/logo/gemini.svg', shelf: 'assets/shots/section_03_x.png' },
  hits: HITS,
  samples: 8,
  draw(ctx, u, t, IMG) {
    fill(ctx, C.cream);
    if (u < 8.3) {
      ctx.save();
      const o = E.inCubic(prog(u, 7.75, 8.2));
      ctx.globalAlpha = 1 - o; ctx.translate(0, -o * 160);
      sceneHook(ctx, u, IMG);
      ctx.restore();
    }
    if (u >= 7.8 && u < 16.3) {
      ctx.save();
      const o = E.inCubic(prog(u, 15.7, 16.2));
      ctx.globalAlpha = 1 - o; ctx.translate(0, -o * 200);
      sceneNeed(ctx, u, IMG);
      ctx.restore();
    }
    if (u >= 15.4 && u < 35) for (let i = 0; i < 3; i++) drawCard(ctx, i, u, IMG);
    if (u >= 33.6 && u < 42.2) scenePayoff(ctx, u, IMG);
    if (u >= 42 && u < 50.1) scenePosition(ctx, u, IMG);
    if (u >= 49.9) sceneEnd(ctx, u);
    texaLogo(ctx, u, IMG);
  },
});
