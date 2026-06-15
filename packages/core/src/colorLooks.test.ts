import { describe, expect, it } from "vitest";
import {
  HF_LOOK_COLOR_SPACE,
  isHfLookActive,
  normalizeHfLook,
  parseHfLookAttribute,
  serializeHfLook,
} from "./colorLooks";

describe("color looks", () => {
  it("parses preset shorthand", () => {
    const look = parseHfLookAttribute("warm-clean");
    expect(look?.preset).toBe("warm-clean");
    expect(look?.colorSpace).toBe(HF_LOOK_COLOR_SPACE);
    expect(look?.adjust.temperature).toBeGreaterThan(0);
    expect(isHfLookActive(look)).toBe(true);
  });

  it("merges manual adjustments over preset values", () => {
    const look = normalizeHfLook({
      preset: "warm-clean",
      intensity: 0.5,
      adjust: { temperature: -0.25, contrast: 0.2 },
    });
    expect(look?.intensity).toBe(0.5);
    expect(look?.adjust.temperature).toBe(-0.25);
    expect(look?.adjust.contrast).toBe(0.2);
    expect(look?.adjust.saturation).toBeGreaterThan(0);
  });

  it("clamps values to supported shader ranges", () => {
    const look = normalizeHfLook({
      intensity: 2,
      adjust: { exposure: 10, contrast: -5, saturation: 3 },
      lut: { src: "looks/test.cube", intensity: 3 },
    });
    expect(look?.intensity).toBe(1);
    expect(look?.adjust.exposure).toBe(2);
    expect(look?.adjust.contrast).toBe(-1);
    expect(look?.adjust.saturation).toBe(1);
    expect(look?.lut?.intensity).toBe(1);
  });

  it("returns null for disabled or invalid looks", () => {
    expect(normalizeHfLook({ enabled: false, preset: "warm-clean" })).toBeNull();
    expect(parseHfLookAttribute("{nope")).toBeNull();
    expect(parseHfLookAttribute("")).toBeNull();
  });

  it("serializes normalized looks for data-hf-look", () => {
    const look = normalizeHfLook({ adjust: { exposure: 0.25 } });
    const serialized = serializeHfLook(look);
    expect(serialized).toContain('"exposure":0.25');
    expect(parseHfLookAttribute(serialized)?.adjust.exposure).toBe(0.25);
  });

  it("treats zero global intensity as inactive even with LUT data", () => {
    const look = normalizeHfLook({
      intensity: 0,
      adjust: { exposure: 0.5 },
      lut: { src: "looks/test.cube", intensity: 1 },
    });
    expect(isHfLookActive(look)).toBe(false);
  });
});
