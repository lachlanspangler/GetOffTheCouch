import { describe, expect, it } from "vitest";
import { vibes } from "../src/lib/vibes";
import { ev } from "./helpers";

describe("vibes", () => {
  it("counts nearby events by family and ranks neighborhoods", () => {
    const here = { lat: 44.95, lon: -93.3 };
    const evs = [
      ev({ category: "trivia_games.trivia", location: here, price: { currency: "USD", is_free: true } }),
      ev({ category: "trivia_games.karaoke", location: here }),
      ev({ category: "music.concert", location: here }),
      ev({ category: "music.concert", location: { lat: 45.2, lon: -93.0 } }), // far away
    ];
    const [a, b] = vibes(evs, [{ name: "Elsewhere", lat: 46, lon: -94 }, { name: "Uptown", ...here }]);
    expect(a.name).toBe("Uptown");
    expect(a.total).toBe(3);
    expect(a.top[0]).toEqual({ family: "trivia_games", n: 2 });
    expect(a.free).toBe(1);
    expect(b.total).toBe(0);
  });
});
