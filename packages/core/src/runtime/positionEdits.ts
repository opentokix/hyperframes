// fallow-ignore-file code-duplication
// (splitTopLevelWhitespace intentionally mirrors the studio-side copies in
// manualEditsDom.ts / manualEditsRenderScript.ts — this module ships inside
// the self-contained runtime bundle and cannot import studio code.)
/**
 * Editor position edits (SDK `moveElement`) applied at render time.
 *
 * The SDK's `moveElement` writes `data-x` / `data-y` plus a captured baseline
 * (`data-hf-edit-base-x` / `data-hf-edit-base-y` — the values before the first
 * edit). The runtime renders the edit as the DELTA between the two, via the
 * independent CSS `translate` longhand, so it composes additively with any
 * position the composition itself produces (GSAP tweens, `tl.set`, CSS).
 *
 * Why `translate` and why after timeline bind: GSAP folds a `translate` that
 * is present when it FIRST parses an element into its cached transform (and
 * an absolute tween then discards it on the animated axis — the per-axis loss
 * bug). A `translate` set AFTER that parse is never read, cleared, or baked
 * by GSAP 3.x on subsequent seeks, so a single application at bind time holds
 * for the whole timeline. Known limitation: a tween created lazily at runtime
 * that first-parses a marked element after this ran will fold the edit.
 */

export const EDIT_BASE_X_ATTR = "data-hf-edit-base-x";
export const EDIT_BASE_Y_ATTR = "data-hf-edit-base-y";
export const EDIT_ORIGINAL_TRANSLATE_ATTR = "data-hf-edit-original-translate";

const num = (value: string | null): number => {
  const n = value === null ? Number.NaN : parseFloat(value);
  return Number.isFinite(n) ? n : 0;
};

/** Split "10px 20px" / "calc(1px + 2px) 3px" on top-level whitespace only. */
const splitTopLevelWhitespace = (value: string): string[] => {
  const parts: string[] = [];
  let depth = 0;
  let current = "";
  for (const char of value.trim()) {
    if (char === "(") depth += 1;
    if (char === ")") depth = Math.max(0, depth - 1);
    if (/\s/.test(char) && depth === 0) {
      if (current) parts.push(current);
      current = "";
    } else {
      current += char;
    }
  }
  if (current) parts.push(current);
  return parts;
};

const PX_VALUE = /^-?(?:\d+(?:\.\d+)?|\.\d+)px$/;

/** Sum two lengths — numerically when both are plain px, via calc() otherwise. */
const addLengths = (a: string, b: string): string => {
  if (PX_VALUE.test(a) && PX_VALUE.test(b)) return `${parseFloat(a) + parseFloat(b)}px`;
  return `calc(${a} + ${b})`;
};

/** Compose the edit delta with the element's pre-edit translate value. */
export const composeTranslate = (original: string, x: string, y: string): string => {
  if (!original || original === "none") return `${x} ${y}`;
  const [ox, oy, oz] = splitTopLevelWhitespace(original);
  if (ox === undefined) return `${x} ${y}`;
  if (oy === undefined) return `${addLengths(ox, x)} ${y}`;
  const z = oz === undefined ? "" : ` ${oz}`;
  return `${addLengths(ox, x)} ${addLengths(oy, y)}${z}`;
};

const readCurrentTranslate = (el: HTMLElement): string => {
  const inline = el.style.getPropertyValue("translate").trim();
  if (inline) return inline === "none" ? "" : inline;
  try {
    const view = el.ownerDocument.defaultView;
    const computed = view ? view.getComputedStyle(el).getPropertyValue("translate").trim() : "";
    return computed === "none" ? "" : computed;
  } catch {
    return "";
  }
};

/**
 * Apply one element's position edit. Idempotent — the pre-edit translate is
 * captured exactly once (into EDIT_ORIGINAL_TRANSLATE_ATTR, empty string
 * meaning "none") on first application, and every application recomputes from
 * that baseline.
 */
export function applyPositionEditToElement(el: HTMLElement): void {
  const dx = num(el.getAttribute("data-x")) - num(el.getAttribute(EDIT_BASE_X_ATTR));
  const dy = num(el.getAttribute("data-y")) - num(el.getAttribute(EDIT_BASE_Y_ATTR));
  if (!el.hasAttribute(EDIT_ORIGINAL_TRANSLATE_ATTR)) {
    el.setAttribute(EDIT_ORIGINAL_TRANSLATE_ATTR, readCurrentTranslate(el));
  }
  const original = el.getAttribute(EDIT_ORIGINAL_TRANSLATE_ATTR) ?? "";
  el.style.setProperty("translate", composeTranslate(original, `${dx}px`, `${dy}px`));
}

/**
 * Apply all pending position edits in the document. Returns the number of
 * elements updated.
 */
export function applyPositionEdits(doc: Document): number {
  const marked = doc.querySelectorAll(`[${EDIT_BASE_X_ATTR}], [${EDIT_BASE_Y_ATTR}]`);
  let applied = 0;
  for (let i = 0; i < marked.length; i++) {
    const el = marked[i];
    if (!(el instanceof HTMLElement)) continue;
    applyPositionEditToElement(el);
    applied += 1;
  }
  return applied;
}
