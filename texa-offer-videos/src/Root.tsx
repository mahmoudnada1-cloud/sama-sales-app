import { Composition } from "remotion";
import { OfferReel, reelDuration } from "./OfferReel";
import { offers } from "./offers";

export const Root = () => (
  <>
    {offers.map((o) => (
      <Composition
        key={o.id}
        id={`offer-${o.id}`}
        component={OfferReel}
        width={1080}
        height={1920}
        fps={30}
        durationInFrames={reelDuration(o)}
        defaultProps={{ offer: o }}
      />
    ))}
  </>
);
