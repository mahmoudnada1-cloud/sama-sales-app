import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/fonts";
import type { Clip, Offer, Tier } from "./offers";

const FONT = "Tajawal";
for (const w of ["500", "700", "900"]) {
  for (const subset of ["arabic", "latin"]) {
    loadFont({ family: FONT, url: staticFile(`fonts/tajawal-${subset}-${w}-normal.woff2`), weight: w });
  }
}

const C = { navy: "#1f2a44", cream: "#f6f1e8", copper: "#c0803d", gold: "#e3b877", white: "#ffffff" };

const sum = (xs: { frames: number }[]) => xs.reduce((n, x) => n + x.frames, 0);
const toolsClips = (o: Offer) => [o.tools.calc, o.tools.planner, o.tools.claim];
export const reelDuration = (o: Offer) =>
  o.hook.frames + sum(o.features.items) + sum(o.tiers) + sum(toolsClips(o)) + o.service.frames + o.outro.frames;

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

const VO_DELAY = 6; // فريمات قبل بداية الصوت في كل مشهد
const Vo: React.FC<{ offer: Offer; clip: Clip }> = ({ offer, clip }) => (
  <Sequence from={VO_DELAY}><Audio src={staticFile(`${offer.voDir}/${clip.vo}.mp3`)} /></Sequence>
);

const Hook: React.FC<{ offer: Offer }> = ({ offer }) => (
  <AbsoluteFill>
    <Backdrop src={offer.heroImage} dim={0.5} duration={offer.hook.frames} />
    <AbsoluteFill style={{ justifyContent: "flex-end", padding: "0 80px 300px" }}>
      <Rise delay={6}><Badge text={offer.hook.badge} /></Rise>
      <Rise delay={14}><div style={{ color: C.white, fontWeight: 900, fontSize: 120, lineHeight: 1.2, marginTop: 30, whiteSpace: "nowrap" }}>{offer.hook.title}</div></Rise>
      <Rise delay={110}><div style={{ color: C.gold, fontWeight: 900, fontSize: 104, lineHeight: 1.3, whiteSpace: "nowrap" }}>{offer.hook.big}</div></Rise>
      <Rise delay={170}><div style={{ color: C.white, fontWeight: 500, fontSize: 54, lineHeight: 1.45, marginTop: 24 }}>{offer.hook.sub}</div></Rise>
    </AbsoluteFill>
  </AbsoluteFill>
);

const Features: React.FC<{ offer: Offer }> = ({ offer }) => {
  const items = offer.features.items;
  let t = 0;
  const starts = items.map((it) => { const from = t; t += it.frames; return from; });
  return (
    <AbsoluteFill>
      <Backdrop src={offer.roomImage} dim={0.72} blur={6} duration={sum(items)} />
      <AbsoluteFill style={{ justifyContent: "center", padding: "0 70px", gap: 36 }}>
        <Rise><div style={{ color: C.gold, fontWeight: 700, fontSize: 64, marginBottom: 16 }}>{offer.features.heading}</div></Rise>
        {items.map((f, i) => (
          <Rise key={f.title} delay={starts[i] + (i === 0 ? 40 : 4)}>
            <div style={{ background: "rgba(255,255,255,0.96)", borderRadius: 36, padding: "40px 46px", display: "flex", alignItems: "center", gap: 32 }}>
              <div style={{ width: 92, height: 92, borderRadius: 46, background: C.copper, color: C.white, fontWeight: 900, fontSize: 54, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{i + 1}</div>
              <div>
                <div style={{ color: C.navy, fontWeight: 900, fontSize: 62, lineHeight: 1.25 }}>{f.title}</div>
                <div style={{ color: "#5b6478", fontWeight: 500, fontSize: 40, lineHeight: 1.4, marginTop: 8 }}>{f.sub}</div>
              </div>
            </div>
          </Rise>
        ))}
      </AbsoluteFill>
      {items.map((f, i) => <Sequence key={f.vo} from={starts[i]} durationInFrames={f.frames}><Vo offer={offer} clip={f} /></Sequence>)}
    </AbsoluteFill>
  );
};

const TierScene: React.FC<{ offer: Offer; tier: Tier; index: number }> = ({ offer, tier, index }) => {
  const frame = useCurrentFrame();
  const pricePop = useIn(18, 12);
  return (
    <AbsoluteFill style={{ background: C.cream, padding: "200px 70px 0" }}>
      <Rise>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Badge text="عروض باركيه SPC" />
          <div style={{ color: C.navy, fontWeight: 700, fontSize: 44 }}>{index + 1} / {offer.tiers.length}</div>
        </div>
      </Rise>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 22, marginTop: 50 }}>
        {tier.images.map((src, i) => {
          const p = spring({ frame: frame - 4 - i * 4, fps: 30, config: { damping: 200 } });
          return (
            <div key={src} style={{ gridColumn: i === 0 ? "span 2" : undefined, height: i === 0 ? 540 : 300,  borderRadius: 30, overflow: "hidden", opacity: p, transform: `scale(${0.9 + p * 0.1})`, boxShadow: "0 12px 30px rgba(31,42,68,0.18)" }}>
              <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            </div>
          );
        })}
      </div>
      <Rise delay={14} style={{ marginTop: 50 }}>
        <div style={{ color: C.navy, fontWeight: 700, fontSize: 74, lineHeight: 1.2 }}>{tier.label}</div>
        <div style={{ color: tier.highlight ? "#d0312d" : "#5b6478", fontWeight: tier.highlight ? 700 : 500, fontSize: 42, marginTop: 6 }}>{tier.note}</div>
      </Rise>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 40 }}>
        <div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 20, opacity: Math.min(1, pricePop), transform: `scale(${0.6 + pricePop * 0.4})`, transformOrigin: "right center" }}>
            <div style={{ color: C.copper, fontWeight: 700, fontSize: 180, lineHeight: 1 }}>{tier.now}</div>
            <div style={{ color: C.navy, fontWeight: 500, fontSize: 48 }}>{offer.unit}</div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Tools: React.FC<{ offer: Offer }> = ({ offer }) => {
  const { calc, planner, claim } = offer.tools;
  const card: React.CSSProperties = { background: C.white, borderRadius: 40, padding: "50px 54px", boxShadow: "0 16px 40px rgba(31,42,68,0.14)" };
  const field: React.CSSProperties = { background: C.cream, borderRadius: 24, padding: "24px 34px", display: "flex", justifyContent: "space-between", color: C.navy, fontWeight: 700, fontSize: 48 };
  return (
    <AbsoluteFill style={{ background: C.cream }}>
      <Sequence durationInFrames={calc.frames}>
        <AbsoluteFill style={{ justifyContent: "center", padding: "0 70px" }}>
          <Rise><Badge text={calc.badge} /></Rise>
          <Rise delay={6}><div style={{ color: C.navy, fontWeight: 900, fontSize: 96, lineHeight: 1.2, marginTop: 30 }}>{calc.title}</div></Rise>
          <Rise delay={calc.fieldsAt} style={{ marginTop: 50 }}>
            <div style={{ ...card, display: "flex", flexDirection: "column", gap: 22 }}>
              <div style={field}><span>طول الغرفة</span><span>{calc.length}</span></div>
              <div style={field}><span>عرض الغرفة</span><span>{calc.width}</span></div>
              <Rise delay={calc.resultAt}>
                <div style={{ background: C.navy, borderRadius: 24, padding: "30px 34px", display: "flex", justifyContent: "space-between", alignItems: "center", color: C.white, fontWeight: 700, fontSize: 48 }}>
                  <span>تحتاج</span><span style={{ color: C.gold, fontWeight: 900, fontSize: 84 }}>{calc.result}</span>
                </div>
                <div style={{ color: "#5b6478", fontWeight: 500, fontSize: 38, marginTop: 20 }}>{calc.note}</div>
              </Rise>
            </div>
          </Rise>
        </AbsoluteFill>
        <Vo offer={offer} clip={calc} />
      </Sequence>
      <Sequence from={calc.frames} durationInFrames={planner.frames}>
        <AbsoluteFill style={{ justifyContent: "center", padding: "0 70px" }}>
          <Rise><Badge text={planner.badge} /></Rise>
          <Rise delay={6}><div style={{ color: C.navy, fontWeight: 900, fontSize: 96, lineHeight: 1.2, marginTop: 30 }}>{planner.title}<br /><span style={{ color: C.copper }}>{planner.accent}</span></div></Rise>
          <Rise delay={50} style={{ marginTop: 44 }}>
            <div style={{ ...card, padding: 0, overflow: "hidden" }}><Img src={staticFile("brand/planner.jpg")} style={{ width: "100%", display: "block" }} /></div>
          </Rise>
          <Rise delay={64}><div style={{ color: "#5b6478", fontWeight: 700, fontSize: 44, lineHeight: 1.4, marginTop: 34 }}>{planner.note}</div></Rise>
        </AbsoluteFill>
        <Vo offer={offer} clip={planner} />
      </Sequence>
      <Sequence from={calc.frames + planner.frames} durationInFrames={claim.frames}>
        <AbsoluteFill style={{ background: C.navy, justifyContent: "center", padding: "0 70px" }}>
          <Rise><div style={{ color: C.white, fontWeight: 900, fontSize: 112, lineHeight: 1.25 }}>{claim.title}</div></Rise>
          <Rise delay={36}><div style={{ color: C.gold, fontWeight: 900, fontSize: 88, lineHeight: 1.3, marginTop: 36 }}>{claim.accent}</div></Rise>
        </AbsoluteFill>
        <Vo offer={offer} clip={claim} />
      </Sequence>
    </AbsoluteFill>
  );
};

const LogoChip: React.FC = () => (
  <div style={{ position: "absolute", top: 56, left: 56, width: 132, height: 132, borderRadius: 30, overflow: "hidden", boxShadow: "0 8px 24px rgba(0,0,0,0.25)" }}>
    <Img src={staticFile("brand/logo.png")} style={{ width: "100%", height: "100%" }} />
  </div>
);

const Service: React.FC<{ offer: Offer }> = ({ offer }) => {
  const sv = offer.service;
  return (
    <AbsoluteFill>
      <Backdrop src={offer.roomImage} dim={0.78} blur={4} duration={sv.frames} />
      <AbsoluteFill style={{ justifyContent: "center", padding: "0 80px" }}>
        <Rise><div style={{ color: C.white, fontWeight: 900, fontSize: 104, lineHeight: 1.2 }}>{sv.title}<br /><span style={{ color: C.gold }}>{sv.accent}</span></div></Rise>
        <div style={{ display: "flex", flexWrap: "nowrap", gap: 12, marginTop: 50 }}>
          {sv.cities.map((c, i) => (
            <Rise key={c} delay={70 + i * 18}>
              <div style={{ border: `3px solid ${C.gold}`, color: C.white, fontWeight: 700, fontSize: 42, padding: "12px 26px", borderRadius: 999 }}>{c}</div>
            </Rise>
          ))}
        </div>
        <Rise delay={sv.shippingAt}><div style={{ color: C.white, fontWeight: 700, fontSize: 56, marginTop: 60 }}>{sv.shipping}</div></Rise>
      </AbsoluteFill>
      <Vo offer={offer} clip={sv} />
    </AbsoluteFill>
  );
};

const Outro: React.FC<{ offer: Offer }> = ({ offer }) => {
  const p = useIn(0, 14);
  return (
    <AbsoluteFill style={{ background: C.cream, alignItems: "center", justifyContent: "center", padding: 80, textAlign: "center" }}>
      <div style={{ width: 380, height: 380, borderRadius: 56, overflow: "hidden", transform: `scale(${p})`, boxShadow: "0 20px 50px rgba(31,42,68,0.18)" }}>
        <Img src={staticFile("brand/logo.png")} style={{ width: "100%", height: "100%" }} />
      </div>
      <Rise delay={12}><div style={{ color: C.navy, fontWeight: 700, fontSize: 60, marginTop: 56 }}>{offer.outro.lines[0]}</div></Rise>
      <Rise delay={60}><div style={{ color: C.navy, fontWeight: 900, fontSize: 76, marginTop: 22, lineHeight: 1.3 }}>{offer.outro.lines[1]}</div></Rise>
      <Rise delay={130}><div style={{ color: C.copper, fontWeight: 700, fontSize: 56, marginTop: 50 }}>{offer.outro.cta}</div></Rise>
      <Rise delay={150}>
        <div style={{ background: C.navy, color: C.white, fontWeight: 700, fontSize: 64, padding: "26px 64px", borderRadius: 999, marginTop: 24, direction: "ltr" }}>{offer.url}</div>
      </Rise>
      <Vo offer={offer} clip={offer.outro} />
    </AbsoluteFill>
  );
};

export const OfferReel: React.FC<{ offer: Offer }> = ({ offer }) => {
  const { durationInFrames } = useVideoConfig();
  let t = 0;
  const at = (d: number) => { const from = t; t += d; return from; };
  const featuresFrames = sum(offer.features.items);
  const toolsFrames = sum(toolsClips(offer));
  const outroFrom = durationInFrames - offer.outro.frames;
  return (
    <AbsoluteFill style={{ fontFamily: `${FONT}, "Noto Color Emoji"`, direction: "rtl", background: C.navy }}>
      {offer.music ? (
        <Audio src={staticFile(offer.music)} volume={(f) => 0.16 * interpolate(f, [0, 20, durationInFrames - 45, durationInFrames], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      ) : null}
      <Sequence from={at(offer.hook.frames)} durationInFrames={offer.hook.frames}><Hook offer={offer} /><Vo offer={offer} clip={offer.hook} /></Sequence>
      <Sequence from={at(featuresFrames)} durationInFrames={featuresFrames}><Features offer={offer} /></Sequence>
      {offer.tiers.map((tier, i) => (
        <Sequence key={tier.label} from={at(tier.frames)} durationInFrames={tier.frames}><TierScene offer={offer} tier={tier} index={i} /><Vo offer={offer} clip={tier} /></Sequence>
      ))}
      <Sequence from={at(toolsFrames)} durationInFrames={toolsFrames}><Tools offer={offer} /></Sequence>
      <Sequence from={at(offer.service.frames)} durationInFrames={offer.service.frames}><Service offer={offer} /></Sequence>
      <Sequence from={at(offer.outro.frames)} durationInFrames={offer.outro.frames}><Outro offer={offer} /></Sequence>
      <Sequence durationInFrames={outroFrom}><LogoChip /></Sequence>
    </AbsoluteFill>
  );
};
