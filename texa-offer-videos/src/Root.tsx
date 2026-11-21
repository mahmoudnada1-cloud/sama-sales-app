import { Composition, Still } from "remotion";
import { Cover, OfferReel, reelDuration } from "./OfferReel";
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
    {offers.filter((o) => o.cover).map((o) => (
      <Still key={o.id} id={`cover-${o.id}`} component={Cover} width={1080} height={1920} defaultProps={{ offer: o }} />
    ))}
  </>
);
