// Decorative generated art (DESIGN.md §6). Styling (.art, tones, ratio) lives in app.css.
import { artSvg, cityArt, type ArtResult, type Family } from "../lib/art";

interface WrapProps {
  art: ArtResult;
  family: string;
  ratio: string;
  className?: string;
}

function ArtBox({ art, family, ratio, className }: WrapProps) {
  // The SVG holds only numbers and constant strings (see lib/art.ts), so innerHTML is safe by construction.
  return (
    <div
      class={className ? `art ${className}` : "art"}
      data-family={family}
      aria-hidden="true"
      style={{ "--art-h": art.hue, "--art-shift": art.shift, "--art-ratio": ratio }}
      dangerouslySetInnerHTML={{ __html: art.svg }}
    />
  );
}

export function Art({ id, family, ratio = "16/10", class: className }: { id: string; family: Family; ratio?: string; class?: string }) {
  return <ArtBox art={artSvg({ id, family })} family={family} ratio={ratio} className={className} />;
}

export function CityArt({ slug, ratio = "16/10", class: className }: { slug: string; ratio?: string; class?: string }) {
  return <ArtBox art={cityArt(slug)} family="city" ratio={ratio} className={className} />;
}
