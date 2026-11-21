// بيانات العروض — كل قسم عنصر واحد. تعديل سعر هنا + إعادة الرندر = فيديو محدّث.
// المصدر: صفحات العروض على texadecore.store (آخر سحب: 2026-11-21).

export type Tier = {
  label: string; // مثال: "سماكة 5 ملم"
  note: string; // سطر صغير تحت العنوان
  was: number;
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
      { label: "سماكة 4 ملم", note: "4 ألوان خشبية", was: 73, now: 61, images: [spc(4), spc(5), spc(6), spc(7)] },
      { label: "سماكة 5 ملم", note: "11 لون — الأكثر تنوعاً", was: 146, now: 103, images: [spc(9), spc(11), spc(13), spc(3)] },
      { label: "سماكة 6 و 7 ملم", note: "3 تصاميم", was: 109, now: 90, images: [spc(0), spc(1), spc(2)] },
    ],
    url: "texadecore.store",
  },
];
