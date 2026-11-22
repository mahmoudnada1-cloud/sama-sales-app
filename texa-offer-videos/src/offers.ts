// بيانات العروض — كل قسم عنصر واحد. تعديل سعر هنا + إعادة الرندر = فيديو محدّث.
// المصدر: صفحات العروض على texadecore.store (آخر سحب: 2026-11-21).
// كل عنصر له مقطع صوت في public/<voDir>/ ومدة بالفريمات (30fps) = طول المقطع + هامش.

export type Clip = { vo: string; frames: number };

export type Tier = Clip & {
  label: string;
  note: string;
  highlight?: boolean; // يلوّن السطر الصغير بالأحمر
  prefix?: string; // نص قبل السعر مثل "يبدأ من"
  now: number;
  images: string[]; // 3 صور غرف: الأولى كبيرة والباقي صف تحتها
};

export type Offer = {
  id: string;
  voDir: string;
  music?: string;
  voDelay?: number; // فريمات قبل بداية الصوت في كل مشهد (الافتراضي 6)
  heroImage: string;
  heroDim?: number; // تعتيم صورة المشهد الأول (0–1) للصور الفاتحة
  roomImage: string;
  url: string;
  phone?: string; // رقم المبيعات (واتساب)
  coverFrames?: number; // عدد فريمات عرض الغلاف في بداية الفيديو
  cover?: { pill?: string; lead: string; name: string; from: number; note: string; image: string };
  hook: Clip & { badge: string; title: string; big: string; sub: string; bigAt: number; subAt: number };
  features?: { heading: string; items: (Clip & { title: string; sub?: string })[] };
  unit: string;
  tierBadge: string; // الشارة أعلى مشاهد الأسعار
  tiers: Tier[];
  tools: {
    calc?: Clip & { badge: string; title: string; length: string; width: string; result: string; note: string; fieldsAt: number; resultAt: number };
    planner?: Clip & { badge: string; title: string; accent: string; note: string };
    claim?: Clip & { title: string; accent: string };
  };
  service?: Clip & { title: string; accent: string; cities: string[]; shipping: string; shippingAt: number };
  outro: Clip & { lines: string[]; cta: string; extra?: string; pace?: number }; // pace يضغط توقيت ظهور السطور
};

const room = (k: string) => `parquet-spc/room-${k}.jpg`;
const ltr = (s: string) => `⁦${s}⁩`; // يثبّت اتجاه الأرقام والنسب داخل النص العربي

export const offers: Offer[] = [
  {
    id: "parquet-spc",
    voDir: "parquet-spc/vo",
    music: "parquet-spc/music.mp3",
    heroImage: "parquet-spc/bedroom.webp",
    roomImage: "parquet-spc/room.jpg",
    url: "texadecore.store",
    phone: "0591409002",
    coverFrames: 15,
    cover: { lead: "عروض", name: "باركيه SPC", from: 59, note: "السعر شامل الضريبة", image: room("t1a") },
    hook: {
      vo: "1", frames: 302,
      badge: "أقوى عروض باركيه SPC",
      title: "جدّد أرضية بيتك",
      big: `ضد الماء ${ltr("100%")} 💧`,
      sub: "تركيب كليك فوري.. بدون غراء ولا تكسير ولا حوسة!",
      bigAt: 110, subAt: 170,
    },
    features: {
      heading: "ليش باركيه SPC؟",
      items: [
        { vo: "2a", frames: 254, title: `مقاوم للماء ${ltr("100%")}`, sub: "ركّبه وأنت مرتاح في الصالة، المداخل، وحتى المطابخ" },
        { vo: "2b", frames: 201, title: "تركيب كليك نظيف", sub: "يركب فوق بلاطك القديم مباشرة بدون تكسير وترميم" },
        { vo: "2c", frames: 194, title: "فخامة الخشب الطبيعي", sub: "18 لون ونقشة عصرية مشمولة في العرض" },
      ],
    },
    unit: "ريال / م²",
    tierBadge: "عروض باركيه SPC",
    tiers: [
      { vo: "3a", frames: 191, label: "4 ألوان خشبية", note: "الأوفر سعراً", highlight: true, now: 59, images: [room("t1a"), room("t1b"), room("t1c")] },
      { vo: "3b", frames: 209, label: "3 نقشات مميزة", note: "لمسة فخمة ومختلفة", now: 90, images: [room("t3a"), room("t3b"), room("t3c")] },
      { vo: "3c", frames: 223, label: "11 لون ودرجة", note: "الأكثر طلباً وتنوعاً", now: 99, images: [room("t2a"), room("t2b"), room("t2c")] },
    ],
    tools: {
      calc: {
        vo: "4a", frames: 475,
        badge: "حاسبة الكميات 📐", title: "محتار كم متر تحتاج؟",
        length: "5 م", width: "4 م", result: "21.4 م²",
        note: `الكمية الدقيقة شاملة نسبة الهالك (${ltr("7%")})`,
        fieldsAt: 60, resultAt: 300,
      },
      planner: { vo: "4b", frames: 209, badge: "مخطط الغرفة 📱", title: "تبي تشوف الشكل", accent: "قبل تشتري؟", note: "جرّبه مجاناً من جوالك وصمّم غرفتك بنفسك" },
      claim: { vo: "4c", frames: 127, title: "سهّلناها عليك..", accent: "وبأقل الأسعار في السعودية" },
    },
    service: {
      vo: "5", frames: 273,
      title: "قياس وتركيب", accent: "احترافي 👷‍♂️",
      cities: ["الرياض", "جدة", "الدمام", "مكة", "المدينة"],
      shipping: "وشحن سريع لجميع مدن المملكة 🚚", shippingAt: 180,
    },
    outro: { vo: "6", frames: 276, lines: ["الأسعار شاملة الضريبة ✅", "العرض ساري حتى نفاد الكمية"], cta: "اطلب الآن من متجرنا" },
  },
  {
    // نسخة مختصرة 30 ثانية
    id: "parquet-spc-30",
    voDir: "parquet-spc/vo30",
    music: "parquet-spc/music.mp3",
    voDelay: 2,
    heroImage: "parquet-spc/bedroom.webp",
    roomImage: "parquet-spc/room.jpg",
    url: "texadecore.store",
    phone: "0591409002",
    coverFrames: 15,
    cover: { lead: "عروض", name: "باركيه SPC", from: 59, note: "السعر شامل الضريبة", image: room("t1a") },
    hook: {
      vo: "h", frames: 197,
      badge: "عروض باركيه SPC",
      title: "العروض وصلت!",
      big: `ضد الماء ${ltr("100%")} 💧`,
      sub: "تركيب كليك بدون غراء ولا تكسير",
      bigAt: 50, subAt: 95,
    },
    unit: "ريال / م²",
    tierBadge: "عروض باركيه SPC",
    tiers: [
      { vo: "p1", frames: 117, label: "4 ألوان خشبية", note: "الأوفر سعراً", highlight: true, now: 59, images: [room("t1a"), room("t1b"), room("t1c")] },
      { vo: "p2", frames: 85, label: "3 نقشات مميزة", note: "لمسة فخمة ومختلفة", now: 90, images: [room("t3a"), room("t3b"), room("t3c")] },
      { vo: "p3", frames: 102, label: "11 لون ودرجة", note: "الأكثر طلباً وتنوعاً", now: 99, images: [room("t2a"), room("t2b"), room("t2c")] },
    ],
    tools: {
      planner: { vo: "t", frames: 152, badge: "الحاسبة + مخطط الغرفة 📱", title: "احسب كميتك", accent: "وصمّم غرفتك", note: "مجاناً من جوالك" },
      claim: { vo: "c", frames: 105, title: "سهّلناها عليك..", accent: "وبأقل الأسعار في السعودية" },
    },
    outro: {
      vo: "o", frames: 157, pace: 0.4,
      lines: ["الأسعار شاملة الضريبة ✅", "العرض ساري حتى نفاد الكمية"],
      cta: "اطلب الآن من متجرنا",
      extra: "قياس وتركيب احترافي · شحن لكل مدن المملكة 🚚",
    },
  },
  {
    // النعلات — فوائدها غير الشكل + أقل سعر
    id: "skirting",
    voDir: "skirting/vo",
    music: "parquet-spc/music.mp3",
    voDelay: 2,
    heroImage: "skirting/corner.jpg",
    heroDim: 0.8,
    roomImage: "skirting/led.jpg",
    url: "texadecore.store",
    phone: "0591409002",
    coverFrames: 15,
    cover: { lead: "عروض", name: "النعلات", from: 14, note: "السعر شامل الضريبة", image: "skirting/corner.jpg" },
    hook: {
      vo: "h", frames: 138,
      badge: "النعلات",
      title: "النعلة مو بس شكل!",
      big: "لها فوايد كثير",
      sub: "غير الشكل الجمالي",
      bigAt: 50, subAt: 80,
    },
    features: {
      heading: "فوايد النعلة",
      items: [
        { vo: "f1", frames: 86, title: "تخفي الفجوة", sub: "بين الأرضية والجدار" },
        { vo: "f2", frames: 110, title: "تحمي الجدار", sub: "من المسح والكنس وخدوش الأثاث" },
        { vo: "f3", frames: 91, title: "ما تتأثر بالماء", sub: "مثل النعلة الخشبية" },
        { vo: "f4", frames: 119, title: "تركيب بالسيليكون", sub: "بدون مسامير ولا تكسير" },
      ],
    },
    unit: "ريال / م",
    tierBadge: "عروض النعلات",
    tiers: [
      { vo: "p", frames: 161, label: "أقل سعر في السعودية", note: "أكثر من 200 نعلة بكل المقاسات", prefix: "يبدأ من", now: 14, images: ["skirting/profile-a.jpg", "skirting/profile-b.jpg", "skirting/profile-c.jpg"] },
    ],
    tools: {},
    outro: {
      vo: "o", frames: 170, pace: 0.4,
      lines: ["الأسعار شاملة الضريبة ✅", "العرض ساري حتى نفاد الكمية"],
      cta: "اطلب الآن من متجرنا",
      extra: "تركيب احترافي · شحن لكل مدن المملكة 🚚",
    },
  },
  {
    // عروض ورق جدران مميزة (كتالوج NEOM) — 75 ريال للرول
    id: "wallpaper",
    voDir: "wallpaper/vo",
    music: "parquet-spc/music.mp3",
    voDelay: 2,
    heroImage: "wallpaper/storm.jpg",
    heroDim: 0.62,
    roomImage: "wallpaper/roughwood.jpg",
    url: "texadecore.store",
    phone: "0591409002",
    coverFrames: 15,
    cover: { lead: "عروض", name: "ورق الجدران", from: 75, note: "السعر شامل الضريبة", image: "wallpaper/storm.jpg" },
    hook: {
      vo: "h", frames: 144,
      badge: "عروض ورق جدران مميزة",
      title: "العروض وصلت!",
      big: "غيّر جدارك",
      sub: "في يوم واحد",
      bigAt: 55, subAt: 85,
    },
    features: {
      heading: "ورق جدران تكسا",
      items: [
        { vo: "f1", frames: 188, title: "ورق جدران كوري", sub: `رول كبير مقاس ${ltr("1.06 × 15.6")} م` },
        { vo: "f2", frames: 168, title: "26 تصميم", sub: "سادة، مموج، مودرن ومقلم" },
        { vo: "f3", frames: 96, title: "حاسبة الكميات 📐", sub: "احسب كم رول تحتاج قبل الطلب" },
      ],
    },
    unit: "ريال / رول",
    tierBadge: "عروض ورق جدران مميزة",
    tiers: [
      { vo: "p", frames: 131, label: "ورق جدران كوري", note: "سعر منخفض جديد", highlight: true, now: 75, images: ["wallpaper/dalton.jpg", "wallpaper/even.jpg", "wallpaper/deacon.jpg"] },
    ],
    tools: {},
    outro: {
      vo: "o", frames: 160, pace: 0.4,
      lines: ["الأسعار شاملة الضريبة ✅", "العرض ساري حتى نفاد الكمية"],
      cta: "اطلب الآن من متجرنا",
      extra: "قياس وتركيب احترافي · شحن لكل مدن المملكة 🚚",
    },
  },
];
