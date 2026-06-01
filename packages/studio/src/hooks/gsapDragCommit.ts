/**
 * Pure helpers for GSAP-aware drag persistence. When an element has a GSAP
 * tween controlling x/y, these functions compute the new GSAP position from
 * the studio offset delta and dispatch the correct GSAP script mutation.
 */
import type { GsapAnimation } from "@hyperframes/core/gsap-parser";
import type { DomEditSelection } from "../components/editor/domEditingTypes";
import { clearStudioPathOffset } from "../components/editor/manualEdits";

/** Callbacks for writing GSAP position changes via the script mutation API. */
export interface GsapPositionCommitCallbacks {
  commitMutation: (
    selection: DomEditSelection,
    mutation: Record<string, unknown>,
    options: { label: string; coalesceKey?: string; softReload?: boolean },
  ) => Promise<void>;
}

/**
 * Find the GSAP animation that controls position (x/y) for an element.
 * Skips from() tweens (CSS position is the target; standard offset handles it).
 * Skips set() tweens — prefers to()/fromTo()/keyframed tweens when both exist.
 */
// fallow-ignore-next-line complexity
export function findGsapPositionAnimation(animations: GsapAnimation[]): GsapAnimation | null {
  if (animations.length === 0) return null;
  // Only intercept keyframed tweens — flat tweens (to/from/fromTo/set) are
  // handled correctly by the standard CSS offset path which persists inline
  // styles. Keyframed tweens need the GSAP path for auto-keyframing.
  for (const anim of animations) {
    if (!anim.keyframes) continue;
    const hasPosition = anim.keyframes.keyframes.some(
      (kf) => "x" in kf.properties || "y" in kf.properties,
    );
    if (hasPosition) return anim;
  }
  return null;
}

/**
 * Read the current GSAP x/y values for an animation at a given playhead
 * percentage. For flat tweens, reads from properties. For keyframe tweens,
 * finds the nearest keyframe values at or before the percentage.
 */
// fallow-ignore-next-line complexity
function readGsapPositionAtPercentage(
  anim: GsapAnimation,
  percentage: number,
): { x: number; y: number } {
  if (anim.keyframes) {
    let x = 0;
    let y = 0;
    for (const kf of anim.keyframes.keyframes) {
      if (kf.percentage <= percentage) {
        if ("x" in kf.properties) x = Number(kf.properties.x) || 0;
        if ("y" in kf.properties) y = Number(kf.properties.y) || 0;
      }
    }
    return { x, y };
  }
  return {
    x: Number(anim.properties.x) || 0,
    y: Number(anim.properties.y) || 0,
  };
}

/**
 * Compute the playhead percentage within an element's local timeline.
 * Returns a value clamped to [0, 100].
 */
function computeElementPercentage(
  currentTime: number,
  dataAttributes: Record<string, string> | undefined,
): number {
  const elStart = Number.parseFloat(dataAttributes?.start ?? "0");
  const elDuration = Number.parseFloat(dataAttributes?.duration ?? "1");
  if (elDuration <= 0) return 0;
  const raw = ((currentTime - elStart) / elDuration) * 100;
  return Math.max(0, Math.min(100, raw));
}

/**
 * Commit a position drag to GSAP script instead of CSS. The `studioOffset`
 * is the delta from the element's GSAP-positioned location — added to the
 * current GSAP x/y values to produce the new GSAP position.
 *
 * For fromTo() tweens, shifts both from and to properties by the same delta
 * so the entire animation path moves uniformly.
 */
// fallow-ignore-next-line complexity
export function commitGsapPositionDrag(
  selection: DomEditSelection,
  anim: GsapAnimation,
  studioOffset: { x: number; y: number },
  currentTime: number,
  callbacks: GsapPositionCommitCallbacks,
): void {
  const pct = computeElementPercentage(currentTime, selection.dataAttributes);
  const currentPos = readGsapPositionAtPercentage(anim, pct);
  const newX = Math.round(currentPos.x + studioOffset.x);
  const newY = Math.round(currentPos.y + studioOffset.y);

  // Only keyframed tweens reach this point (flat tweens use the CSS offset path).
  const clampedPct = Math.max(0, Math.min(100, Math.round(pct)));
  void callbacks.commitMutation(
    selection,
    {
      type: "add-keyframe",
      animationId: anim.id,
      percentage: clampedPct,
      properties: { x: newX, y: newY } as Record<string, number | string>,
    },
    {
      label: `Move layer (keyframe ${clampedPct}%)`,
      coalesceKey: `gsap-drag:${anim.id}:kf:${clampedPct}`,
      softReload: true,
    },
  );

  clearStudioPathOffset(selection.element);
}
