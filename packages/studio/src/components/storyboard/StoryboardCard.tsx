import { memo, useMemo, useCallback, useRef } from "react";

// ── Category color detection ─────────────────────────────────────────────────

type CardCategory = "vfx" | "transition" | "caption" | "social" | "default";

function detectCategory(path: string): CardCategory {
  const lower = path.toLowerCase();
  if (lower.includes("vfx")) return "vfx";
  if (lower.includes("transition")) return "transition";
  if (lower.includes("caption")) return "caption";
  if (lower.includes("social")) return "social";
  return "default";
}

const CATEGORY_COLORS: Record<CardCategory, { border: string; accent: string }> = {
  vfx: { border: "border-purple-500", accent: "bg-purple-500" },
  transition: { border: "border-blue-500", accent: "bg-blue-500" },
  caption: { border: "border-green-500", accent: "bg-green-500" },
  social: { border: "border-pink-500", accent: "bg-pink-500" },
  default: { border: "border-neutral-800", accent: "bg-neutral-600" },
};

// ── Detail level ─────────────────────────────────────────────────────────────

type DetailLevel = "minimal" | "compact" | "normal" | "full";

function getDetailLevel(zoom: number): DetailLevel {
  if (zoom < 0.15) return "minimal";
  if (zoom < 0.3) return "compact";
  if (zoom < 0.8) return "normal";
  return "full";
}

// ── Props ────────────────────────────────────────────────────────────────────

interface StoryboardCardProps {
  id: string;
  path: string;
  title: string;
  start: number;
  duration: number;
  x: number;
  y: number;
  width: number;
  height: number;
  isSelected: boolean;
  /** True when the playhead is within this card's time range. */
  isCurrent: boolean;
  projectId: string;
  zoom: number;
  /** Playback progress within this card's range, 0-100. */
  progress: number;
  onClick: () => void;
  onDragStart?: (id: string, offsetX: number, offsetY: number) => void;
  onContextMenu?: (id: string, clientX: number, clientY: number) => void;
}

export const StoryboardCard = memo(function StoryboardCard({
  id,
  title,
  duration,
  x,
  y,
  width,
  height,
  isSelected,
  isCurrent,
  projectId,
  path,
  zoom,
  progress,
  onClick,
  onDragStart,
  onContextMenu,
}: StoryboardCardProps) {
  const titleBarHeight = 32;
  const previewHeight = height - titleBarHeight;
  const detailLevel = getDetailLevel(zoom);
  const category = useMemo(() => detectCategory(path), [path]);
  const colors = CATEGORY_COLORS[category];

  const iframeSrc = useMemo(
    () => `/api/projects/${projectId}/preview/comp/${path}`,
    [projectId, path],
  );

  const showPreview = detailLevel === "normal" || detailLevel === "full";
  const showTitle = detailLevel !== "minimal";
  const showDuration = detailLevel === "normal" || detailLevel === "full";
  const showProgress = isCurrent && detailLevel !== "minimal";
  const iframeScale = previewHeight / 1080;

  // ── Drag handling ────────────────────────────────────────────────────────

  const pointerDownRef = useRef<{ x: number; y: number; moved: boolean } | null>(null);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    if (e.button !== 0) return;
    pointerDownRef.current = { x: e.clientX, y: e.clientY, moved: false };
  }, []);

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      const start = pointerDownRef.current;
      if (!start) return;
      const dx = Math.abs(e.clientX - start.x);
      const dy = Math.abs(e.clientY - start.y);
      if (!start.moved && (dx > 4 || dy > 4)) {
        start.moved = true;
        onDragStart?.(id, e.clientX - x * zoom, e.clientY - y * zoom);
      }
    },
    [id, x, y, zoom, onDragStart],
  );

  const handlePointerUp = useCallback(
    (e: React.PointerEvent) => {
      const start = pointerDownRef.current;
      pointerDownRef.current = null;
      if (start && !start.moved) {
        onClick();
      }
      void e;
    },
    [onClick],
  );

  const handleContextMenu = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      onContextMenu?.(id, e.clientX, e.clientY);
    },
    [id, onContextMenu],
  );

  // ── Border classes ───────────────────────────────────────────────────────

  const borderClass = isSelected
    ? "border-blue-500 shadow-[0_0_20px_rgba(59,130,246,0.2)]"
    : isCurrent
      ? `border-emerald-400 shadow-[0_0_16px_rgba(52,211,153,0.15)]`
      : `${colors.border} hover:border-neutral-600`;

  // ── Minimal: just a colored rectangle ────────────────────────────────────

  if (detailLevel === "minimal") {
    return (
      <div
        className="absolute cursor-pointer"
        style={{ left: x, top: y, width, height }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onContextMenu={handleContextMenu}
      >
        <div
          className={`h-full rounded-lg border-2 transition-colors ${borderClass}`}
          style={{
            backgroundColor:
              category === "default"
                ? "rgb(38 38 38)"
                : `color-mix(in srgb, ${
                    {
                      vfx: "#a855f7",
                      transition: "#3b82f6",
                      caption: "#22c55e",
                      social: "#ec4899",
                      default: "#525252",
                    }[category]
                  } 15%, rgb(38 38 38))`,
          }}
        />
      </div>
    );
  }

  return (
    <div
      className="absolute cursor-pointer transition-all duration-150"
      style={{ left: x, top: y, width, height }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onContextMenu={handleContextMenu}
    >
      <div
        className={`h-full rounded-xl overflow-hidden border-2 transition-colors ${borderClass}`}
        style={{ transformOrigin: "center center" }}
      >
        {/* Preview area */}
        <div
          className="relative bg-neutral-900 overflow-hidden"
          style={{ height: showTitle ? previewHeight : height }}
        >
          {showPreview ? (
            <iframe
              src={iframeSrc}
              title={title}
              loading="lazy"
              style={{
                width: 1920,
                height: 1080,
                transform: `scale(${iframeScale})`,
                transformOrigin: "top left",
                border: "none",
                pointerEvents: "none",
              }}
              sandbox="allow-scripts allow-same-origin"
            />
          ) : (
            <div className="h-full w-full bg-neutral-800/60 flex items-center justify-center">
              {/* Compact: show title in the center instead of title bar */}
              {detailLevel === "compact" && (
                <span className="text-[10px] font-medium text-neutral-400 truncate px-2 text-center">
                  {title}
                </span>
              )}
            </div>
          )}

          {/* Category accent dot */}
          {category !== "default" && detailLevel !== "compact" && (
            <div
              className={`absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full ${colors.accent}`}
            />
          )}

          {/* Playback progress bar */}
          {showProgress && (
            <div
              className="absolute bottom-0 left-0 h-0.5 bg-emerald-400 transition-all"
              style={{ width: `${progress}%` }}
            />
          )}
        </div>

        {/* Title bar — only for normal/full detail */}
        {showTitle && detailLevel !== "compact" && (
          <div
            className="flex items-center gap-2 px-2 bg-neutral-900/95 border-t border-neutral-800"
            style={{ height: titleBarHeight }}
          >
            <span className="text-[10px] font-medium text-neutral-300 truncate flex-1">
              {title}
            </span>
            {showDuration && (
              <span className="text-[9px] text-neutral-600 tabular-nums flex-shrink-0">
                {duration.toFixed(1)}s
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
});
