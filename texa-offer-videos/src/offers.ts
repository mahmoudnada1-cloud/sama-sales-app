// بيانات العروض — كل قسم عنصر واحد. تعديل سعر هنا + إعادة الرندر = فيديو محدّث.
// المصدر: صفحات العروض على texadecore.store (آخر سحب: 2026-11-21).
// مدد المشاهد (frames @30fps) مضبوطة على مقاطع التعليق الصوتي في public/<id>/vo/.

export type Tier = {
  label: string; // عنوان الشريحة
  note: string; // سطر صغير تحت العنوان
  highlight?: boolean; // يلوّن السطر الصغير بالأحمر
  now: number;
  images: string[]; // 3 صور غرف: الأولى كبيرة والباقي صف تحتها
  frames: number; // مدة المشهد
};

export type Offer = {
  id: string;
  badge: string;
  hook: string[]; // سطور العنوان الرئيسي
  hookSub: string;
  heroImage: string; // صورة طولية للمشهد الأول
  roomImage: string; // خلفية المشاهد التالية
  features: { title: string; sub: string; at: number }[]; // at = فريم ظهور البطاقة
  unit: string;
  tiers: Tier[];
  url: string;
  voDir: string; // مجلد مقاطع الصوت: 1 هوك، 2 مميزات، 3 أسعار، 4 أدوات، 5 خدمة، 6 ختام
  frames: { hook: number; features: number; tools: number; toolsSplit: [number, number]; service: number; outro: number };
};

const room = (k: string) => `parquet-spc/room-${k}.jpg`;

export const offers: Offer[] = [
  {
    id: "parquet-spc",
    badge: "عروض باركيه SPC",
    hook: ["أرضية ضد الماء", "⁦100%⁩"],
    hookSub: "تركيب كليك… بدون غراء ولا تكسير",
    heroImage: "parquet-spc/bedroom.webp",
    roomImage: "parquet-spc/room.jpg",
    features: [
      { title: "ضد الماء ⁦100%⁩", sub: "للمطابخ والحمامات والمداخل", at: 6 },
      { title: "تركيب كليك", sub: "بدون غراء ولا كسر وترميم", at: 60 },
      { title: "مظهر خشبي فاخر", sub: "18 لون ونقشة ضمن العروض", at: 132 },
    ],
    unit: "ريال / م²",
    tiers: [
      { label: "4 ألوان خشبية", note: "الأوفر سعراً", highlight: true, now: 59, images: [room("t1a"), room("t1b"), room("t1c")], frames: 106 },
      { label: "11 لون ودرجة", note: "الأكثر تنوعاً", now: 99, images: [room("t2a"), room("t2b"), room("t2c")], frames: 102 },
      { label: "3 نقشات مميزة", note: "لمسة مختلفة للأرضية", now: 90, images: [room("t3a"), room("t3b"), room("t3c")], frames: 112 },
    ],
    url: "texadecore.store",
    voDir: "parquet-spc/vo",
    frames: { hook: 160, features: 208, tools: 365, toolsSplit: [135, 250], service: 146, outro: 150 },
  },
];
