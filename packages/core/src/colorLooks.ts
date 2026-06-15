export const HF_LOOK_ATTR = "data-hf-look";

export const HF_LOOK_COLOR_SPACE = "rec709";

export type HfLookPresetId =
  | "neutral"
  | "warm-clean"
  | "cool-clean"
  | "soft-boost"
  | "bright-pop"
  | "deep-contrast";

export type HfLookAdjustKey =
  | "exposure"
  | "contrast"
  | "highlights"
  | "shadows"
  | "whites"
  | "blacks"
  | "temperature"
  | "tint"
  | "saturation";

export type HfLookAdjust = Partial<Record<HfLookAdjustKey, number>>;

export interface HfLookLutRef {
  src: string;
  intensity?: number;
}

export interface HfLook {
  enabled?: boolean;
  preset?: HfLookPresetId | string | null;
  intensity?: number;
  adjust?: HfLookAdjust;
  lut?: HfLookLutRef | string | null;
  colorSpace?: typeof HF_LOOK_COLOR_SPACE | string;
}

export interface NormalizedHfLook {
  enabled: boolean;
  preset: HfLookPresetId | string | null;
  intensity: number;
  adjust: Record<HfLookAdjustKey, number>;
  lut: HfLookLutRef | null;
  colorSpace: typeof HF_LOOK_COLOR_SPACE | string;
}

export interface HfLookTarget {
  id?: string | null;
  hfId?: string | null;
  selector?: string | null;
  selectorIndex?: number | null;
}

export interface HfLookPreset {
  id: HfLookPresetId;
  label: string;
  adjust: Record<HfLookAdjustKey, number>;
}

const ADJUST_ZERO: Record<HfLookAdjustKey, number> = {
  exposure: 0,
  contrast: 0,
  highlights: 0,
  shadows: 0,
  whites: 0,
  blacks: 0,
  temperature: 0,
  tint: 0,
  saturation: 0,
};

export const HF_LOOK_ADJUST_KEYS: readonly HfLookAdjustKey[] = [
  "exposure",
  "contrast",
  "highlights",
  "shadows",
  "whites",
  "blacks",
  "temperature",
  "tint",
  "saturation",
];

export const HF_LOOK_PRESETS: readonly HfLookPreset[] = [
  {
    id: "neutral",
    label: "Neutral",
    adjust: { ...ADJUST_ZERO },
  },
  {
    id: "warm-clean",
    label: "Warm Clean",
    adjust: {
      ...ADJUST_ZERO,
      exposure: 0.05,
      contrast: 0.08,
      highlights: -0.08,
      shadows: 0.08,
      temperature: 0.16,
      saturation: 0.06,
    },
  },
  {
    id: "cool-clean",
    label: "Cool Clean",
    adjust: {
      ...ADJUST_ZERO,
      contrast: 0.06,
      highlights: -0.06,
      shadows: 0.06,
      temperature: -0.12,
      tint: 0.04,
      saturation: 0.04,
    },
  },
  {
    id: "soft-boost",
    label: "Soft Boost",
    adjust: {
      ...ADJUST_ZERO,
      exposure: 0.06,
      contrast: -0.04,
      highlights: -0.14,
      shadows: 0.16,
      saturation: 0.1,
    },
  },
  {
    id: "bright-pop",
    label: "Bright Pop",
    adjust: {
      ...ADJUST_ZERO,
      exposure: 0.12,
      contrast: 0.12,
      whites: 0.08,
      blacks: -0.04,
      saturation: 0.14,
    },
  },
  {
    id: "deep-contrast",
    label: "Deep Contrast",
    adjust: {
      ...ADJUST_ZERO,
      exposure: -0.03,
      contrast: 0.2,
      highlights: -0.08,
      shadows: -0.08,
      blacks: -0.12,
      saturation: 0.06,
    },
  },
];

const PRESETS_BY_ID = new Map<string, HfLookPreset>(
  HF_LOOK_PRESETS.map((preset) => [preset.id, preset]),
);

const ADJUST_LIMITS: Record<HfLookAdjustKey, { min: number; max: number }> = {
  exposure: { min: -2, max: 2 },
  contrast: { min: -1, max: 1 },
  highlights: { min: -1, max: 1 },
  shadows: { min: -1, max: 1 },
  whites: { min: -1, max: 1 },
  blacks: { min: -1, max: 1 },
  temperature: { min: -1, max: 1 },
  tint: { min: -1, max: 1 },
  saturation: { min: -1, max: 1 },
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(max, Math.max(min, value));
}

function clampUnit(value: unknown, fallback: number): number {
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(1, Math.max(0, parsed));
}

function readAdjustValue(value: unknown, key: HfLookAdjustKey): number {
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed)) return 0;
  const limit = ADJUST_LIMITS[key];
  return clamp(parsed, limit.min, limit.max);
}

function normalizePresetId(value: unknown): HfLookPresetId | string | null {
  if (value == null) return null;
  const preset = String(value).trim();
  return preset ? preset : null;
}

function normalizeLut(value: unknown): HfLookLutRef | null {
  if (value == null) return null;
  if (typeof value === "string") {
    const src = value.trim();
    return src ? { src, intensity: 1 } : null;
  }
  if (!isRecord(value)) return null;
  const rawSrc = value.src;
  if (typeof rawSrc !== "string" || rawSrc.trim() === "") return null;
  return {
    src: rawSrc.trim(),
    intensity: clampUnit(value.intensity, 1),
  };
}

function readLookObject(raw: unknown): Record<string, unknown> | null {
  if (typeof raw === "string") {
    const trimmed = raw.trim();
    if (!trimmed) return null;
    if (trimmed.startsWith("{")) {
      try {
        const parsed: unknown = JSON.parse(trimmed);
        return isRecord(parsed) ? parsed : null;
      } catch {
        return null;
      }
    }
    return { preset: trimmed, intensity: 1 };
  }
  return isRecord(raw) ? raw : null;
}

export function getHfLookPreset(id: string | null | undefined): HfLookPreset | null {
  if (!id) return null;
  return PRESETS_BY_ID.get(id) ?? null;
}

export function normalizeHfLook(raw: unknown): NormalizedHfLook | null {
  const look = readLookObject(raw);
  if (!look) return null;
  if (look.enabled === false) return null;

  const presetId = normalizePresetId(look.preset);
  const preset = getHfLookPreset(presetId);
  const presetAdjust = preset?.adjust ?? ADJUST_ZERO;
  const rawAdjust = isRecord(look.adjust) ? look.adjust : {};
  const adjust = HF_LOOK_ADJUST_KEYS.reduce<Record<HfLookAdjustKey, number>>(
    (result, key) => {
      result[key] = readAdjustValue(rawAdjust[key] ?? presetAdjust[key], key);
      return result;
    },
    { ...ADJUST_ZERO },
  );

  return {
    enabled: true,
    preset: presetId,
    intensity: clampUnit(look.intensity, 1),
    adjust,
    lut: normalizeLut(look.lut),
    colorSpace:
      typeof look.colorSpace === "string" && look.colorSpace.trim()
        ? look.colorSpace.trim()
        : HF_LOOK_COLOR_SPACE,
  };
}

export function parseHfLookAttribute(value: string | null | undefined): NormalizedHfLook | null {
  if (value == null) return null;
  return normalizeHfLook(value);
}

export function serializeHfLook(look: NormalizedHfLook | HfLook | null): string {
  const normalized = normalizeHfLook(look);
  if (!normalized) return "";
  return JSON.stringify({
    preset: normalized.preset,
    intensity: normalized.intensity,
    adjust: normalized.adjust,
    lut: normalized.lut,
    colorSpace: normalized.colorSpace,
  });
}

export function isHfLookActive(look: NormalizedHfLook | null): look is NormalizedHfLook {
  if (!look?.enabled) return false;
  if (look.intensity === 0) return false;
  if (look.lut && look.lut.intensity !== 0) return true;
  return HF_LOOK_ADJUST_KEYS.some((key) => Math.abs(look.adjust[key]) > 0.0001);
}
