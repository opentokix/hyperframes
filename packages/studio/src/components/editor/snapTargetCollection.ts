// fallow-ignore-file code-duplication
import type { DomEditSelection } from "./domEditing";
import type { DomEditContextOptions } from "./domEditingTypes";
import { collectDomEditLayerItems } from "./domEditingLayers";
import {
  isElementVisibleForOverlay,
  selectionCacheKey,
  toOverlayRect,
  type OverlayRect,
} from "./domEditOverlayGeometry";
import {
  extractSnapTargets,
  buildCompositionSnapTarget,
  buildGridSnapEdges,
  type SnapTarget,
  type SnapEdge,
} from "./snapEngine";
import { readStudioUiPreferences } from "../../utils/studioUiPreferences";

export interface SnapContext {
  targets: SnapTarget[];
  compositionTarget: SnapTarget | null;
  gridEdges: { x: SnapEdge[]; y: SnapEdge[] } | null;
  snapEnabled: boolean;
}

function readPositiveDimension(value: string | null): number | null {
  if (!value) return null;
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

// fallow-ignore-next-line complexity
export function collectSnapContext(input: {
  overlayEl: HTMLDivElement;
  iframe: HTMLIFrameElement;
  excludeKeys: Set<string>;
  activeCompositionPath: string | null;
}): SnapContext {
  const prefs = readStudioUiPreferences();
  const snapEnabled = prefs.snapEnabled ?? true;

  const doc = input.iframe.contentDocument;
  if (!doc) {
    return { targets: [], compositionTarget: null, gridEdges: null, snapEnabled };
  }

  const root = doc.querySelector<HTMLElement>("[data-composition-id]") ?? doc.documentElement;
  const rootRect = root?.getBoundingClientRect();
  const declaredWidth = readPositiveDimension(root?.getAttribute("data-width") ?? null);
  const declaredHeight = readPositiveDimension(root?.getAttribute("data-height") ?? null);
  const rootWidth = declaredWidth ?? rootRect?.width;
  const rootHeight = declaredHeight ?? rootRect?.height;

  if (!rootWidth || !rootHeight || !rootRect) {
    return { targets: [], compositionTarget: null, gridEdges: null, snapEnabled };
  }

  const iframeRect = input.iframe.getBoundingClientRect();
  const overlayRect = input.overlayEl.getBoundingClientRect();
  const rootScaleX = iframeRect.width / rootWidth;
  const rootScaleY = iframeRect.height / rootHeight;

  const compositionOverlayRect: OverlayRect = {
    left: iframeRect.left - overlayRect.left,
    top: iframeRect.top - overlayRect.top,
    width: iframeRect.width,
    height: iframeRect.height,
    editScaleX: rootScaleX,
    editScaleY: rootScaleY,
  };
  const compositionTarget = buildCompositionSnapTarget(compositionOverlayRect);

  const options: DomEditContextOptions = {
    activeCompositionPath: input.activeCompositionPath,
    isMasterView: true,
  };
  const layerItems = collectDomEditLayerItems(root, options);

  const rects: Array<{ left: number; top: number; width: number; height: number }> = [];
  const ids: string[] = [];

  for (const item of layerItems) {
    const key = item.key;
    if (input.excludeKeys.has(key)) continue;

    if (!isElementVisibleForOverlay(item.element)) continue;

    const rect = toOverlayRect(input.overlayEl, input.iframe, item.element);
    if (!rect) continue;

    rects.push(rect);
    ids.push(key);
  }

  const targets = extractSnapTargets(rects, ids);

  let gridEdges: { x: SnapEdge[]; y: SnapEdge[] } | null = null;
  const gridSpacing = prefs.gridSpacing ?? 50;
  const snapToGrid = prefs.snapToGrid ?? false;
  if (snapToGrid && gridSpacing > 0) {
    gridEdges = buildGridSnapEdges(compositionOverlayRect, gridSpacing, rootScaleX);
  }

  return { targets, compositionTarget, gridEdges, snapEnabled };
}

export function buildExcludeKeys(input: {
  selection?: DomEditSelection | null;
  groupSelections?: DomEditSelection[];
}): Set<string> {
  const keys = new Set<string>();
  if (input.selection) {
    keys.add(selectionCacheKey(input.selection));
  }
  if (input.groupSelections) {
    for (const sel of input.groupSelections) {
      keys.add(selectionCacheKey(sel));
    }
  }
  return keys;
}
