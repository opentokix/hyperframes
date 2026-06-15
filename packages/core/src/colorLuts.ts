export type CubeLutVec3 = readonly [number, number, number];

export interface CubeLut3D {
  title: string | null;
  size: number;
  domainMin: CubeLutVec3;
  domainMax: CubeLutVec3;
  data: Float32Array;
}

export interface PackedCubeLut2D {
  width: number;
  height: number;
  data: Uint8Array;
}

export interface ParseCubeLutOptions {
  maxSize?: number;
}

export type BuiltinCubeLutId =
  | "clean-warm"
  | "clean-cool"
  | "soft-pop"
  | "natural-boost"
  | "muted-editorial"
  | "deep-contrast"
  | "vintage-fade"
  | "mono-soft"
  | "high-key";

export interface BuiltinCubeLutPreset {
  id: BuiltinCubeLutId;
  label: string;
  description: string;
}

export class CubeLutParseError extends Error {
  readonly lineNumber: number | null;

  constructor(message: string, lineNumber: number | null = null) {
    super(lineNumber == null ? message : `${message} at line ${lineNumber}`);
    this.name = "CubeLutParseError";
    this.lineNumber = lineNumber;
  }
}

const DEFAULT_DOMAIN_MIN: CubeLutVec3 = [0, 0, 0];
const DEFAULT_DOMAIN_MAX: CubeLutVec3 = [1, 1, 1];
const DEFAULT_MAX_SIZE = 64;
const DEFAULT_BUILTIN_LUT_SIZE = 17;
const BUILTIN_LUT_SRC_PREFIX = "hf:filter/";
const BUILTIN_LUT_CACHE = new Map<string, CubeLut3D>();

export const HF_BUILTIN_CUBE_LUTS: readonly BuiltinCubeLutPreset[] = [
  {
    id: "natural-boost",
    label: "Natural Boost",
    description: "Balanced contrast and color lift for Rec.709 footage.",
  },
  {
    id: "clean-warm",
    label: "Clean Warm",
    description: "Soft warmth with gentle contrast.",
  },
  {
    id: "clean-cool",
    label: "Clean Cool",
    description: "A cooler clean look for tech/product footage.",
  },
  {
    id: "soft-pop",
    label: "Soft Pop",
    description: "Brighter color with softened highlights.",
  },
  {
    id: "muted-editorial",
    label: "Muted Editorial",
    description: "Reduced saturation with controlled contrast.",
  },
  {
    id: "deep-contrast",
    label: "Deep Contrast",
    description: "Deeper blacks and stronger separation.",
  },
  {
    id: "vintage-fade",
    label: "Vintage Fade",
    description: "Lifted blacks, softer color, and warm highlights.",
  },
  {
    id: "mono-soft",
    label: "Mono Soft",
    description: "Soft black and white.",
  },
  {
    id: "high-key",
    label: "High Key",
    description: "Bright, airy, lower-contrast look.",
  },
];

const BUILTIN_IDS = new Set<string>(HF_BUILTIN_CUBE_LUTS.map((preset) => preset.id));

function stripComment(line: string): string {
  let inQuote = false;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') inQuote = !inQuote;
    if (char === "#" && !inQuote) return line.slice(0, i);
  }
  return line;
}

function parseFiniteNumber(value: string, lineNumber: number): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new CubeLutParseError(`Invalid number "${value}"`, lineNumber);
  }
  return parsed;
}

function parseVec3(parts: string[], keyword: string, lineNumber: number): CubeLutVec3 {
  if (parts.length !== 3) {
    throw new CubeLutParseError(`${keyword} expects three numbers`, lineNumber);
  }
  return [
    parseFiniteNumber(parts[0]!, lineNumber),
    parseFiniteNumber(parts[1]!, lineNumber),
    parseFiniteNumber(parts[2]!, lineNumber),
  ];
}

function parseSize(value: string | undefined, keyword: string, lineNumber: number): number {
  if (!value) throw new CubeLutParseError(`${keyword} expects a size`, lineNumber);
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 2) {
    throw new CubeLutParseError(`${keyword} must be an integer greater than 1`, lineNumber);
  }
  return parsed;
}

function validateDomain(domainMin: CubeLutVec3, domainMax: CubeLutVec3): void {
  if (
    domainMax[0] <= domainMin[0] ||
    domainMax[1] <= domainMin[1] ||
    domainMax[2] <= domainMin[2]
  ) {
    throw new CubeLutParseError("DOMAIN_MAX values must be greater than DOMAIN_MIN values");
  }
}

function parseTitle(line: string): string | null {
  const quoted = /^TITLE\s+"([^"]*)"\s*$/i.exec(line);
  if (quoted) return quoted[1] ?? null;
  const bare = /^TITLE\s+(.+)\s*$/i.exec(line);
  return bare ? (bare[1] ?? "").trim() || null : null;
}

function isNumericDataLine(token: string): boolean {
  return /^[+-]?(?:\d|\.\d)/.test(token);
}

export function parseCubeLut(input: string, options: ParseCubeLutOptions = {}): CubeLut3D {
  const maxSize = options.maxSize ?? DEFAULT_MAX_SIZE;
  let title: string | null = null;
  let domainMin: CubeLutVec3 = DEFAULT_DOMAIN_MIN;
  let domainMax: CubeLutVec3 = DEFAULT_DOMAIN_MAX;
  let lut1dSize: number | null = null;
  let lut3dSize: number | null = null;
  const rows: number[] = [];

  const lines = input.replace(/^\uFEFF/, "").split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const lineNumber = i + 1;
    const line = stripComment(lines[i] ?? "").trim();
    if (!line) continue;
    const parts = line.split(/\s+/);
    const keyword = (parts[0] ?? "").toUpperCase();
    const rest = parts.slice(1);

    if (keyword === "TITLE") {
      title = parseTitle(line);
      continue;
    }
    if (keyword === "DOMAIN_MIN") {
      domainMin = parseVec3(rest, keyword, lineNumber);
      continue;
    }
    if (keyword === "DOMAIN_MAX") {
      domainMax = parseVec3(rest, keyword, lineNumber);
      continue;
    }
    if (keyword === "LUT_1D_SIZE") {
      lut1dSize = parseSize(rest[0], keyword, lineNumber);
      continue;
    }
    if (keyword === "LUT_3D_SIZE") {
      lut3dSize = parseSize(rest[0], keyword, lineNumber);
      if (lut3dSize > maxSize) {
        throw new CubeLutParseError(`LUT_3D_SIZE ${lut3dSize} exceeds max ${maxSize}`, lineNumber);
      }
      continue;
    }

    if (!isNumericDataLine(keyword)) {
      if (keyword.startsWith("LUT_")) {
        throw new CubeLutParseError(`Unsupported cube keyword ${keyword}`, lineNumber);
      }
      continue;
    }
    if (!lut3dSize) {
      if (lut1dSize) {
        throw new CubeLutParseError("1D cube LUTs are not supported yet", lineNumber);
      }
      throw new CubeLutParseError("LUT data appears before LUT_3D_SIZE", lineNumber);
    }
    if (parts.length !== 3) {
      throw new CubeLutParseError("LUT data rows must contain three numbers", lineNumber);
    }
    rows.push(
      parseFiniteNumber(parts[0]!, lineNumber),
      parseFiniteNumber(parts[1]!, lineNumber),
      parseFiniteNumber(parts[2]!, lineNumber),
    );
  }

  if (lut1dSize && lut3dSize) {
    throw new CubeLutParseError("Mixed 1D and 3D cube LUTs are not supported yet");
  }
  if (!lut3dSize) {
    if (lut1dSize) throw new CubeLutParseError("1D cube LUTs are not supported yet");
    throw new CubeLutParseError("Missing LUT_3D_SIZE");
  }
  validateDomain(domainMin, domainMax);

  const expectedRows = lut3dSize * lut3dSize * lut3dSize;
  if (rows.length !== expectedRows * 3) {
    throw new CubeLutParseError(
      `Expected ${expectedRows} LUT rows for size ${lut3dSize}, found ${rows.length / 3}`,
    );
  }

  return {
    title,
    size: lut3dSize,
    domainMin,
    domainMax,
    data: new Float32Array(rows),
  };
}

function clampUnit(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

function toByte(value: number): number {
  return Math.round(clampUnit(value) * 255);
}

export function packCubeLutToRgba8(lut: CubeLut3D): PackedCubeLut2D {
  const size = lut.size;
  const width = size * size;
  const height = size;
  const packed = new Uint8Array(width * height * 4);

  for (let b = 0; b < size; b++) {
    for (let g = 0; g < size; g++) {
      for (let r = 0; r < size; r++) {
        const lutIndex = ((b * size + g) * size + r) * 3;
        const pixelIndex = (g * width + b * size + r) * 4;
        packed[pixelIndex] = toByte(lut.data[lutIndex] ?? 0);
        packed[pixelIndex + 1] = toByte(lut.data[lutIndex + 1] ?? 0);
        packed[pixelIndex + 2] = toByte(lut.data[lutIndex + 2] ?? 0);
        packed[pixelIndex + 3] = 255;
      }
    }
  }

  return { width, height, data: packed };
}

export function getBuiltinCubeLutSrc(id: BuiltinCubeLutId): string {
  return `${BUILTIN_LUT_SRC_PREFIX}${id}`;
}

export function resolveBuiltinCubeLutId(src: string): BuiltinCubeLutId | null {
  const trimmed = src.trim();
  const id = trimmed.startsWith(BUILTIN_LUT_SRC_PREFIX)
    ? trimmed.slice(BUILTIN_LUT_SRC_PREFIX.length)
    : trimmed;
  return BUILTIN_IDS.has(id) ? (id as BuiltinCubeLutId) : null;
}

function lumaOf([r, g, b]: CubeLutVec3): number {
  return r * 0.2126 + g * 0.7152 + b * 0.0722;
}

function mix(a: number, b: number, amount: number): number {
  return a * (1 - amount) + b * amount;
}

function mixVec(a: CubeLutVec3, b: CubeLutVec3, amount: number): CubeLutVec3 {
  return [mix(a[0], b[0], amount), mix(a[1], b[1], amount), mix(a[2], b[2], amount)];
}

function applyExposure(color: CubeLutVec3, stops: number): CubeLutVec3 {
  const gain = 2 ** stops;
  return [color[0] * gain, color[1] * gain, color[2] * gain];
}

function applyContrast(color: CubeLutVec3, amount: number): CubeLutVec3 {
  const gain = Math.max(0, 1 + amount);
  return [
    (color[0] - 0.5) * gain + 0.5,
    (color[1] - 0.5) * gain + 0.5,
    (color[2] - 0.5) * gain + 0.5,
  ];
}

function applySaturation(color: CubeLutVec3, amount: number): CubeLutVec3 {
  const y = lumaOf(color);
  const gain = Math.max(0, 1 + amount);
  return [mix(y, color[0], gain), mix(y, color[1], gain), mix(y, color[2], gain)];
}

function applyTemperature(color: CubeLutVec3, temperature: number, tint = 0): CubeLutVec3 {
  return [
    color[0] + temperature * 0.08 + tint * 0.04,
    color[1] - tint * 0.08,
    color[2] - temperature * 0.08 + tint * 0.04,
  ];
}

function applyFade(color: CubeLutVec3, amount: number): CubeLutVec3 {
  return [
    color[0] * (1 - amount) + amount * 0.08,
    color[1] * (1 - amount) + amount * 0.08,
    color[2] * (1 - amount) + amount * 0.08,
  ];
}

function applyHighlightRollOff(color: CubeLutVec3, amount: number): CubeLutVec3 {
  return [
    color[0] - Math.max(0, color[0] - 0.72) * amount,
    color[1] - Math.max(0, color[1] - 0.72) * amount,
    color[2] - Math.max(0, color[2] - 0.72) * amount,
  ];
}

function applySplitTone(
  color: CubeLutVec3,
  shadows: CubeLutVec3,
  highlights: CubeLutVec3,
  amount: number,
): CubeLutVec3 {
  const y = clampUnit(lumaOf(color));
  const shadowMask = 1 - y;
  const highlightMask = y;
  const shadowToned = mixVec(
    color,
    [color[0] * shadows[0], color[1] * shadows[1], color[2] * shadows[2]],
    amount * shadowMask,
  );
  return mixVec(
    shadowToned,
    [
      shadowToned[0] * highlights[0],
      shadowToned[1] * highlights[1],
      shadowToned[2] * highlights[2],
    ],
    amount * highlightMask,
  );
}

function applyBuiltinLook(id: BuiltinCubeLutId, input: CubeLutVec3): CubeLutVec3 {
  let color = input;
  switch (id) {
    case "clean-warm":
      color = applyExposure(color, 0.04);
      color = applyContrast(color, 0.07);
      color = applyTemperature(color, 0.16);
      color = applySaturation(color, 0.04);
      color = applyHighlightRollOff(color, 0.12);
      break;
    case "clean-cool":
      color = applyExposure(color, 0.02);
      color = applyContrast(color, 0.06);
      color = applyTemperature(color, -0.14, 0.03);
      color = applySaturation(color, 0.03);
      break;
    case "soft-pop":
      color = applyExposure(color, 0.07);
      color = applyHighlightRollOff(color, 0.22);
      color = applyContrast(color, 0.06);
      color = applySaturation(color, 0.12);
      break;
    case "natural-boost":
      color = applyExposure(color, 0.03);
      color = applyContrast(color, 0.09);
      color = applySaturation(color, 0.08);
      color = applyHighlightRollOff(color, 0.08);
      break;
    case "muted-editorial":
      color = applyContrast(color, 0.1);
      color = applySaturation(color, -0.16);
      color = applySplitTone(color, [0.96, 1, 1.06], [1.04, 1, 0.96], 0.12);
      break;
    case "deep-contrast":
      color = applyExposure(color, -0.03);
      color = applyContrast(color, 0.2);
      color = applySaturation(color, 0.04);
      color = applyFade(color, -0.04);
      break;
    case "vintage-fade":
      color = applyFade(color, 0.18);
      color = applyContrast(color, -0.06);
      color = applyTemperature(color, 0.14, -0.02);
      color = applySaturation(color, -0.14);
      color = applySplitTone(color, [0.98, 1, 1.08], [1.08, 1.02, 0.9], 0.16);
      break;
    case "mono-soft": {
      const y = lumaOf(color);
      color = [y, y, y];
      color = applyContrast(color, 0.04);
      color = applyFade(color, 0.05);
      break;
    }
    case "high-key":
      color = applyExposure(color, 0.14);
      color = applyHighlightRollOff(color, 0.28);
      color = applyContrast(color, -0.08);
      color = applySaturation(color, -0.03);
      break;
  }
  return [clampUnit(color[0]), clampUnit(color[1]), clampUnit(color[2])];
}

export function createBuiltinCubeLut(
  id: BuiltinCubeLutId,
  size = DEFAULT_BUILTIN_LUT_SIZE,
): CubeLut3D {
  const cacheKey = `${id}:${size}`;
  const cached = BUILTIN_LUT_CACHE.get(cacheKey);
  if (cached) return cached;
  if (!Number.isInteger(size) || size < 2 || size > DEFAULT_MAX_SIZE) {
    throw new CubeLutParseError(`Built-in LUT size must be between 2 and ${DEFAULT_MAX_SIZE}`);
  }

  const data = new Float32Array(size * size * size * 3);
  let offset = 0;
  for (let b = 0; b < size; b++) {
    for (let g = 0; g < size; g++) {
      for (let r = 0; r < size; r++) {
        const color = applyBuiltinLook(id, [r / (size - 1), g / (size - 1), b / (size - 1)]);
        data[offset++] = color[0];
        data[offset++] = color[1];
        data[offset++] = color[2];
      }
    }
  }

  const preset = HF_BUILTIN_CUBE_LUTS.find((entry) => entry.id === id);
  const lut: CubeLut3D = {
    title: preset?.label ?? id,
    size,
    domainMin: DEFAULT_DOMAIN_MIN,
    domainMax: DEFAULT_DOMAIN_MAX,
    data,
  };
  BUILTIN_LUT_CACHE.set(cacheKey, lut);
  return lut;
}

export function getBuiltinCubeLut(src: string): CubeLut3D | null {
  const id = resolveBuiltinCubeLutId(src);
  return id ? createBuiltinCubeLut(id) : null;
}
