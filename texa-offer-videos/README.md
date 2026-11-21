# فيديوهات عروض تكسا ديكور

قالب Remotion واحد (`src/OfferReel.tsx`) وبيانات كل قسم في `src/offers.ts`.
كل عنصر في `offers` ينتج فيديو طولي 1080×1920 باسم `offer-<id>`.

```bash
npm install
npm run studio                 # معاينة وتعديل مباشر
npm run render:parquet-spc     # يخرج out/parquet-spc.mp4
```

لتحديث سعر: عدّل `was` / `now` في `src/offers.ts` وأعد الرندر.
صور المنتجات في `public/<id>/` مأخوذة من texadecore.store.
