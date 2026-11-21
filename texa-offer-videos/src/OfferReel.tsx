import React from "react";
import {
  AbsoluteFill,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/fonts";
import type { Offer, Tier } from "./offers";

const FONT = "Tajawal";
for (const w of ["500", "700", "900"]) {
  for (const subset of ["arabic", "latin"]) {
    loadFont({ family: FONT, url: staticFile(`fonts/tajawal-${subset}-${w}-normal.woff2`), weight: w });
  }
}

const C = { navy: "#1f2a44", cream: "#f6f1e8", copper: "#c0803d", gold: "#e3b877", white: "#ffffff" };

// مدد المشاهد بالفريمات (30fps)
const D = { hook: 105, features: 135, tier: 90, service: 80, outro: 110 };
export const reelDuration = (o: Offer) => D.hook + D.features + D.tier * o.tiers.length + D.service + D.outro;

const useIn = (delay = 0, damping = 200) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - delay, fps, config: { damping } });
};

const Rise: React.FC<{ delay?: number; children: React.ReactNode; style?: React.CSSProperties }> = ({ delay = 0, children, style }) => {
  const p = useIn(delay);
  return <div style={{ opacity: p, transform: `translateY(${(1 - p) * 60}px)`, ...style }}>{children}</div>;
};

const Backdrop: React.FC<{ src: string; dim?: number; blur?: number; duration: number }> = ({ src, dim = 0.55, blur = 0, duration }) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, duration], [1.06, 1.18]);
  return (
    <AbsoluteFill>
      <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${scale})`, filter: blur ? `blur(${blur}px)` : undefined }} />
      <AbsoluteFill style={{ background: `linear-gradient(180deg, rgba(31,42,68,${dim * 0.6}) 0%, rgba(31,42,68,${dim}) 55%, rgba(20,27,45,${Math.min(1, dim + 0.35)}) 100%)` }} />
    </AbsoluteFill>
  );
};

const Badge: React.FC<{ text: string }> = ({ text }) => (
  <div style={{ display: "inline-block", background: C.copper, color: C.white, fontWeight: 700, fontSize: 46, padding: "16px 40px", borderRadius: 999 }}>{text}</div>
);

const Hook: React.FC<{ offer: Offer }> = ({ offer }) => (
  <AbsoluteFill>
    <Backdrop src={offer.heroImage} dim={0.5} duration={D.hook} />
    <AbsoluteFill style={{ justifyContent: "flex-end", padding: "0 80px 300px" }}>
      <Rise delay={6}><Badge text={offer.badge} /></Rise>
      {offer.hook.map((line, i) => (
        <Rise key={line} delay={14 + i * 8}>
          <div style={{ color: i === offer.hook.length - 1 ? C.gold : C.white, fontWeight: 900, fontSize: i === offer.hook.length - 1 ? 220 : 118, whiteSpace: "nowrap", lineHeight: 1.15, marginTop: i === 0 ? 30 : 0 }}>{line}</div>
        </Rise>
      ))}
      <Rise delay={38}>
        <div style={{ color: C.white, fontWeight: 500, fontSize: 58, marginTop: 30 }}>{offer.hookSub}</div>
      </Rise>
    </AbsoluteFill>
  </AbsoluteFill>
);

const Features: React.FC<{ offer: Offer }> = ({ offer }) => (
  <AbsoluteFill>
    <Backdrop src={offer.roomImage} dim={0.72} blur={6} duration={D.features} />
    <AbsoluteFill style={{ justifyContent: "center", padding: "0 80px", gap: 40 }}>
      <Rise><div style={{ color: C.gold, fontWeight: 700, fontSize: 60, marginBottom: 20 }}>ليش SPC؟</div></Rise>
      {offer.features.map((f, i) => (
        <Rise key={f.title} delay={12 + i * 22}>
          <div style={{ background: "rgba(255,255,255,0.96)", borderRadius: 36, padding: "44px 50px", display: "flex", alignItems: "center", gap: 36 }}>
            <div style={{ width: 96, height: 96, borderRadius: 48, background: C.copper, color: C.white, fontWeight: 900, fontSize: 56, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{i + 1}</div>
            <div>
              <div style={{ color: C.navy, fontWeight: 900, fontSize: 70, lineHeight: 1.2 }}>{f.title}</div>
              <div style={{ color: "#5b6478", fontWeight: 500, fontSize: 44, marginTop: 6 }}>{f.sub}</div>
            </div>
          </div>
        </Rise>
      ))}
    </AbsoluteFill>
  </AbsoluteFill>
);

const TierScene: React.FC<{ offer: Offer; tier: Tier; index: number }> = ({ offer, tier, index }) => {
  const frame = useCurrentFrame();
  const pricePop = useIn(24, 12);
  return (
    <AbsoluteFill style={{ background: C.cream, padding: "200px 70px 0" }}>
      <Rise>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Badge text={offer.badge} />
          <div style={{ color: C.navy, fontWeight: 700, fontSize: 44 }}>{index + 1} / {offer.tiers.length}</div>
        </div>
      </Rise>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 22, marginTop: 50 }}>
        {tier.images.map((src, i) => {
          const p = spring({ frame: frame - 4 - i * 4, fps: 30, config: { damping: 200 } });
          return (
            <div key={src} style={{ gridColumn: tier.images.length === 3 && i === 2 ? "span 2" : undefined, height: 420, borderRadius: 30, overflow: "hidden", opacity: p, transform: `scale(${0.9 + p * 0.1})`, boxShadow: "0 12px 30px rgba(31,42,68,0.18)" }}>
              <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            </div>
          );
        })}
      </div>
      <Rise delay={14} style={{ marginTop: 50 }}>
        <div style={{ color: C.navy, fontWeight: 900, fontSize: 96, lineHeight: 1.1 }}>{tier.label}</div>
        <div style={{ color: "#5b6478", fontWeight: 500, fontSize: 46, marginTop: 8 }}>{tier.note}</div>
      </Rise>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 40 }}>
        <div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 20, opacity: Math.min(1, pricePop), transform: `scale(${0.6 + pricePop * 0.4})`, transformOrigin: "right center" }}>
            <div style={{ color: C.copper, fontWeight: 900, fontSize: 260, lineHeight: 1 }}>{tier.now}</div>
            <div style={{ color: C.navy, fontWeight: 700, fontSize: 54 }}>{offer.unit}</div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const CITIES = ["الرياض", "جدة", "الدمام", "مكة", "المدينة"];

const Service: React.FC<{ offer: Offer }> = ({ offer }) => (
  <AbsoluteFill>
    <Backdrop src={offer.roomImage} dim={0.78} blur={4} duration={D.service} />
    <AbsoluteFill style={{ justifyContent: "center", padding: "0 80px" }}>
      <Rise><div style={{ color: C.white, fontWeight: 900, fontSize: 104, lineHeight: 1.2 }}>قياس وتركيب<br /><span style={{ color: C.gold }}>احترافي</span></div></Rise>
      <div style={{ display: "flex", flexWrap: "nowrap", gap: 12, marginTop: 50 }}>
        {CITIES.map((c, i) => (
          <Rise key={c} delay={10 + i * 5}>
            <div style={{ border: `3px solid ${C.gold}`, color: C.white, fontWeight: 700, fontSize: 42, padding: "12px 26px", borderRadius: 999 }}>{c}</div>
          </Rise>
        ))}
      </div>
      <Rise delay={40}><div style={{ color: C.white, fontWeight: 700, fontSize: 60, marginTop: 60 }}>+ شحن لكل مدن المملكة</div></Rise>
    </AbsoluteFill>
  </AbsoluteFill>
);

const Outro: React.FC<{ offer: Offer }> = ({ offer }) => {
  const p = useIn(0, 14);
  return (
    <AbsoluteFill style={{ background: C.cream, alignItems: "center", justifyContent: "center", padding: 80, textAlign: "center" }}>
      <div style={{ width: 420, height: 420, borderRadius: 60, overflow: "hidden", transform: `scale(${p})`, boxShadow: "0 20px 50px rgba(31,42,68,0.18)" }}>
        <Img src={staticFile("brand/logo.png")} style={{ width: "100%", height: "100%" }} />
      </div>
      <Rise delay={12}><div style={{ color: C.navy, fontWeight: 900, fontSize: 84, marginTop: 60, lineHeight: 1.25 }}>العرض ساري<br />حتى نفاذ الكمية</div></Rise>
      <Rise delay={22}><div style={{ color: "#5b6478", fontWeight: 500, fontSize: 44, marginTop: 18 }}>الأسعار شاملة الضريبة</div></Rise>
      <Rise delay={34}>
        <div style={{ background: C.navy, color: C.white, fontWeight: 700, fontSize: 64, padding: "26px 64px", borderRadius: 999, marginTop: 60, direction: "ltr" }}>{offer.url}</div>
      </Rise>
    </AbsoluteFill>
  );
};

export const OfferReel: React.FC<{ offer: Offer }> = ({ offer }) => {
  let t = 0;
  const at = (d: number) => { const from = t; t += d; return from; };
  return (
    <AbsoluteFill style={{ fontFamily: FONT, direction: "rtl", background: C.navy }}>
      <Sequence from={at(D.hook)} durationInFrames={D.hook}><Hook offer={offer} /></Sequence>
      <Sequence from={at(D.features)} durationInFrames={D.features}><Features offer={offer} /></Sequence>
      {offer.tiers.map((tier, i) => (
        <Sequence key={tier.label} from={at(D.tier)} durationInFrames={D.tier}><TierScene offer={offer} tier={tier} index={i} /></Sequence>
      ))}
      <Sequence from={at(D.service)} durationInFrames={D.service}><Service offer={offer} /></Sequence>
      <Sequence from={at(D.outro)} durationInFrames={D.outro}><Outro offer={offer} /></Sequence>
    </AbsoluteFill>
  );
};
