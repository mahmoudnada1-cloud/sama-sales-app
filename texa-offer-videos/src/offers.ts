// بيانات العروض — كل قسم عنصر واحد. تعديل سعر هنا + إعادة الرندر = فيديو محدّث.
// المصدر: صفحات العروض على texadecore.store (آخر سحب: 2026-11-21).

export type Tier = {
  label: string; // عنوان الشريحة
  note: string; // سطر صغير تحت العنوان
  now: number;
  images: string[]; // مسارات داخل public/
};

export type Offer = {
  id: string;
  badge: string;
  hook: string[]; // سطور العنوان الرئيسي
  hookSub: string;
  heroImage: string; // صورة طولية للمشهد الأول
  roomImage: string; // خلفية المشاهد التالية
  features: { title: string; sub: string }[];
  unit: string;
  tiers: Tier[];
  url: string;
};

const spc = (n: number) => `parquet-spc/p${String(n).padStart(2, "0")}.webp`;

export const offers: Offer[] = [
  {
    id: "parquet-spc",
    badge: "عروض باركيه SPC",
    hook: ["أرضية ضد الماء", "⁦100%⁩"],
    hookSub: "تركيب كليك… بدون غراء ولا تكسير",
    heroImage: "parquet-spc/bedroom.webp",
    roomImage: "parquet-spc/room.jpg",
    features: [
      { title: "ضد الماء ⁦100%⁩", sub: "للمطابخ والحمامات والمداخل" },
      { title: "تركيب كليك", sub: "بدون غراء ولا كسر وترميم" },
      { title: "مظهر خشبي فاخر", sub: "18 لون ونقشة ضمن العروض" },
    ],
    unit: "ريال / م²",
    tiers: [
      { label: "4 ألوان خشبية", note: "الأوفر سعراً", now: 59, images: [spc(4), spc(5), spc(6), spc(7)] },
      { label: "11 لون ودرجة", note: "الأكثر تنوعاً", now: 103, images: [spc(9), spc(11), spc(13), spc(3)] },
      { label: "3 نقشات مميزة", note: "لمسة مختلفة للأرضية", now: 90, images: [spc(0), spc(1), spc(2)] },
    ],
    url: "texadecore.store",
  },
];
