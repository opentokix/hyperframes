---
title: "feat: Per-property-group keyframe tracks"
status: active
created: 2026-06-11
type: feat
depth: deep
origin: null
---

## Summary

Replace the bundled percentage-keyframe model (one GSAP tween per element, all properties in each keyframe) with per-property-group tweens. Each studio operation (drag, resize, rotate) creates and edits only its own group's tween, eliminating cross-property contamination. Existing compositions remain readable; first keyframe edit splits legacy tweens into property groups.

---

## Problem Frame

The current keyframe architecture bundles all animated properties (`x`, `y`, `scale`, `width`, `height`, `rotation`, `opacity`, `transformOrigin`) into a single GSAP tween with percentage keyframes. This causes:

1. **Cross-property contamination**: dragging (x/y) captures and overwrites scale; resizing captures and overwrites position; runtime reads bleed transient values from other properties into keyframes
2. **Backfill wars**: adding a new property at one keyframe requires filling it at all others — the "correct" fill value is unknowable without per-property interpolation context
3. **GSAP sparse-property hold behavior**: properties present in some keyframes but not others hold their last value instead of interpolating, producing unexpected visual results
4. **Normalization impossibility**: no single normalization strategy works because different properties have different identity values, different interpolation domains (numeric vs string), and different user expectations

Professional animation tools (After Effects, CapCut, Premiere) solve this with per-property keyframe tracks. Each property group has independent timing, easing, and keyframes. Editing one property never touches another.

---

## Requirements

- **R1**: Drag commits write only to a position-group tween (`x`, `y`, `xPercent`, `yPercent`)
- **R2**: Resize commits write only to a scale-group tween (`scale`, `scaleX`, `scaleY`) or size-group tween (`width`, `height`) depending on context
- **R3**: Rotation commits write only to a rotation-group tween (`rotation`, `skewX`, `skewY`)
- **R4**: Each property group has independent keyframe timing — position keyframes at t=1,3 don't force scale keyframes at the same times
- **R5**: Legacy compositions (single tween with mixed properties) continue to parse and render correctly
- **R6**: First keyframe edit on a legacy tween splits it into property groups automatically
- **R7**: Animation IDs encode the property group: `#box-to-0-position`, `#box-from-500-scale`
- **R8**: Timeline diamonds show per-group keyframes (the existing `TimelinePropertyRows` component handles individual property display)
- **R9**: Undo/redo works correctly across property-group splits and per-group edits
- **R10**: The parser, serializer, server mutations, tween cache, and all intercepts are property-group aware

---

## Key Technical Decisions

### KTD1: Property Group Definitions

| Group | Properties | Identity | Intercept |
|-------|-----------|----------|-----------|
| `position` | `x`, `y`, `xPercent`, `yPercent` | 0 | Drag |
| `scale` | `scale`, `scaleX`, `scaleY` | 1 | Resize (when tween animates scale) |
| `size` | `width`, `height` | CSS value | Resize (when no scale in tween) |
| `rotation` | `rotation`, `skewX`, `skewY` | 0 | Rotate |
| `visual` | `opacity`, `autoAlpha` | 1 | Property panel |
| `transform` | `transformOrigin` | "50% 50%" | Stays with the group it was authored in |
| `other` | everything else | varies | Property panel |

`transformOrigin` is NOT its own group — it stays attached to whichever group's tween originally authored it (typically scale or the legacy mixed tween). This avoids creating a separate tween for a non-interpolatable string property.

### KTD2: ID Format Change

Current: `#box-to-500` (selector-method-positionMs)
New: `#box-to-500-position` (selector-method-positionMs-group)

The group suffix is appended after the position key. Duplicate handling (`-2`, `-3`) comes after the group. This makes IDs stable across property-group edits and unambiguous for mutation routing.

### KTD3: Legacy Split Strategy — Lazy (Split on First Edit)

When a user performs a keyframe edit (drag/resize/rotate/property-panel) on a legacy single-tween composition, the system:
1. Reads the existing tween's properties
2. Partitions them into property groups
3. Replaces the single tween with multiple group tweens at the same position
4. Continues with the edit on the correct group tween

This is a single atomic `replace-with-property-groups` server mutation. The file is not modified until the user actually edits.

### KTD4: Cache Continues to Merge for Diamond Display

The `keyframeCache` continues to merge all property-group tweens into a single keyframe stream per element for the timeline diamond view. This matches the current UX — one row of diamonds per element in the collapsed view. The expanded `TimelinePropertyRows` already extracts per-property diamonds.

A new `propertyGroup` field on each cached keyframe entry tracks which group it belongs to, enabling the property rows to show group-level diamonds.

### KTD5: Serializer Outputs Multiple Tweens Per Element

The serializer already iterates an array of `GsapAnimation` objects. With per-property-group tweens, each element produces multiple entries sorted by position. The serializer handles this naturally — no structural change needed, just awareness that multiple tweens at the same position for the same selector is now intentional.

---

## High-Level Technical Design

```
User Action (drag/resize/rotate)
    │
    ▼
Intercept (gsapRuntimeBridge.ts)
    │ Identifies property group from action type
    │ Finds or creates the group-specific tween
    ▼
Mutation (commitMutation → server)
    │ Routes to group tween by ID (#box-to-0-position)
    │ add-keyframe / replace-with-keyframes / convert-to-keyframes
    ▼
Parser (gsapParser.ts)
    │ Assigns group-aware IDs
    │ Groups animations by (selector, group) for cache
    ▼
Tween Cache (useGsapTweenCache.ts)
    │ Merges per-group keyframes into per-element stream
    │ Preserves group tag on each keyframe
    ▼
Timeline UI (TimelineClipDiamonds.tsx)
    │ Collapsed: all diamonds merged (current behavior)
    │ Expanded: per-property-group rows
```

**Legacy split flow:**

```
User edits legacy tween
    │
    ▼
Intercept detects single mixed tween (no group suffix in ID)
    │
    ▼
Server: split-into-property-groups mutation
    │ Reads all properties from the tween
    │ Partitions into groups per KTD1
    │ Removes original tween
    │ Adds one tween per non-empty group
    │ Returns new IDs
    ▼
Intercept continues with edit on the correct group tween
```

---

## Scope Boundaries

### In Scope
- Property group definitions and type changes
- Parser group-aware ID generation
- Server `split-into-property-groups` mutation
- All three intercepts (drag/resize/rotate) routing to correct group
- Tween cache group tracking
- `replace-with-keyframes` and `add-keyframe` group awareness
- Legacy split-on-first-edit
- Property panel edits routing to correct group
- Enable keyframes routing to correct group

### Deferred to Follow-Up Work
- Per-property-group sub-track rows in timeline UI (the existing `TimelinePropertyRows` already shows per-property diamonds — group-level grouping is a UI enhancement)
- Gesture recording property-group awareness
- Per-group easing UI (different ease per property group)
- Keyframe copy/paste across property groups

### Outside This Plan's Identity
- Changes to how compositions are authored by hand (the HTML format is additive — new tweens are valid GSAP)
- Changes to the rendering engine or player
- Changes to the linter rules

---

## Implementation Units

### U1. Property Group Type Definitions and Constants

**Goal**: Define the property group taxonomy as types and constants shared across parser and studio.

**Requirements**: R1, R2, R3, R7, R10

**Dependencies**: None

**Files**:
- `packages/core/src/parsers/gsapConstants.ts` — add `PROPERTY_GROUPS` map and `PropertyGroupName` type
- `packages/core/src/parsers/gsapSerialize.ts` — add `propertyGroup?: PropertyGroupName` to `GsapAnimation`
- `packages/core/src/parsers/gsapParser.test.ts` — property group classification tests

**Approach**: Define a `PROPERTY_GROUPS: Record<PropertyGroupName, Set<string>>` constant mapping group names to their property sets. Add a `classifyPropertyGroup(propName: string): PropertyGroupName` function. Add `propertyGroup` as an optional field on `GsapAnimation` — set during parsing based on the tween's property set.

**Patterns to follow**: Existing `SUPPORTED_PROPS` in `gsapConstants.ts`

**Test scenarios**:
- `classifyPropertyGroup("x")` returns `"position"`, `"scale"` for scale, `"rotation"` for rotation, `"visual"` for opacity, `"other"` for unknown props
- A tween with only `{x, y}` gets `propertyGroup: "position"`
- A mixed tween with `{x, y, scale, opacity}` gets `propertyGroup: undefined` (legacy mixed)
- A tween with `{scale, transformOrigin}` gets `propertyGroup: "scale"` (transformOrigin follows the group)

**Verification**: Types compile, constant is importable from both core and studio

---

### U2. Parser: Group-Aware ID Generation

**Goal**: `assignStableIds` produces IDs with a group suffix for non-legacy tweens.

**Requirements**: R7, R10

**Dependencies**: U1

**Files**:
- `packages/core/src/parsers/gsapParser.ts` — update `assignStableIds`, `tweenCallToAnimation`
- `packages/core/src/parsers/gsapParser.test.ts` — ID generation tests

**Approach**: In `tweenCallToAnimation`, classify the tween's property group. In `assignStableIds`, append `-{group}` to the base ID when `propertyGroup` is set. Legacy mixed tweens keep the current ID format for backward compatibility.

**Test scenarios**:
- Single-property-group tween: `#box-to-0-position`, `#box-from-500-scale`
- Legacy mixed tween: `#box-to-0` (no group suffix)
- Multiple groups at same position: `#box-to-0-position`, `#box-to-0-scale` (no count suffix needed since groups differ)
- Duplicate same-group same-position: `#box-to-0-position`, `#box-to-0-position-2`

**Verification**: Existing golden tests updated to include group suffixes where applicable; new tests for group ID format

---

### U3. Server: `split-into-property-groups` Mutation

**Goal**: Atomic server mutation that splits a legacy mixed tween into per-property-group tweens.

**Requirements**: R5, R6, R10

**Dependencies**: U1, U2

**Files**:
- `packages/core/src/parsers/gsapParser.ts` — add `splitIntoPropertyGroups` function
- `packages/core/src/studio-api/routes/files.ts` — add `split-into-property-groups` mutation type
- `packages/core/src/parsers/gsapParser.test.ts` — split tests

**Approach**: Given an animation ID, read the tween's properties (flat or keyframed). Partition properties into groups per KTD1. For each non-empty group, create a new tween with only that group's properties, preserving the original position, duration, ease, and method. For keyframed tweens, each group's keyframes contain only the group's properties. Remove the original tween and insert the group tweens. Return the new IDs.

**Test scenarios**:
- Split flat `to({x:100, y:50, scale:1.5, rotation:45})` → position tween `{x:100, y:50}` + scale tween `{scale:1.5}` + rotation tween `{rotation:45}`
- Split keyframed tween: each group gets only its properties per keyframe; keyframes with no properties for a group are omitted
- Split `from({scale:0.5, opacity:0})` → scale tween `from({scale:0.5})` + visual tween `from({opacity:0})`
- Single-group tween (already pure): no split, return same ID
- Preserve original position, duration, ease, extras on each group tween

**Verification**: Round-trip: split then serialize produces valid GSAP that visually matches the original

---

### U4. Intercepts Route to Correct Property Group

**Goal**: Drag/resize/rotate intercepts find or create the correct property-group tween, splitting legacy tweens on first edit.

**Requirements**: R1, R2, R3, R6

**Dependencies**: U1, U2, U3

**Files**:
- `packages/studio/src/hooks/gsapRuntimeBridge.ts` — update `tryGsapDragIntercept`, `tryGsapResizeIntercept`, `tryGsapRotationIntercept`
- `packages/studio/src/hooks/gsapDragCommit.ts` — update `commitGsapPositionFromDrag`, remove mixed-property reads
- `packages/studio/src/hooks/gsapRuntimeReaders.ts` — scope `readAllAnimatedProperties` to group

**Approach**: Each intercept:
1. Checks if the element has a group-specific tween (e.g., `animations.find(a => a.propertyGroup === "position")`)
2. If yes: edit that tween's keyframes
3. If no but a legacy mixed tween exists: call `split-into-property-groups` first, then edit the newly created group tween
4. If no tween at all: create a new group-specific tween

`readAllAnimatedProperties` gains a `group?: PropertyGroupName` parameter to scope which properties it reads. This eliminates cross-group contamination at the reader level.

Drag sends only `{x, y}`. Resize sends only `{width, height}` or `{scale}`. Rotate sends only `{rotation}`. No `runtimeProps` spread.

**Test scenarios**:
- Drag on element with group tweens: only position tween modified
- Resize on element with group tweens: only scale/size tween modified
- Drag on legacy mixed tween: split first, then position group edited
- Drag on element with no animation: creates position-group tween
- Resize on element with from({scale:0.5}): splits, then scale group edited

**Verification**: After drag, diff shows only position properties changed; scale/rotation/size untouched

---

### U5. Tween Cache Group Awareness

**Goal**: Cache tracks property group per keyframe while maintaining merged diamond display.

**Requirements**: R4, R8, R10

**Dependencies**: U1, U2

**Files**:
- `packages/studio/src/player/store/playerStore.ts` — add `propertyGroup` to keyframe cache entry
- `packages/studio/src/hooks/useGsapTweenCache.ts` — group tag on cached keyframes
- `packages/studio/src/hooks/gsapKeyframeCacheHelpers.ts` — preserve group in cache writes

**Approach**: Each keyframe in the cache gets a `propertyGroup?: PropertyGroupName` tag. The merge logic in `useGsapAnimationsForElement` preserves the group from the source animation. Diamond rendering continues to show all keyframes merged. The expanded `TimelinePropertyRows` can filter by group.

**Test scenarios**:
- Cache entry for element with position + scale groups: keyframes have correct group tags
- Diamond display shows union of all group keyframes
- Property rows filter correctly by group
- `tweenPercentage` preserved per-group for correct server targeting

**Verification**: Diamonds render at correct positions; property panel shows correct values per group

---

### U6. Property Panel and Enable-Keyframes Group Routing

**Goal**: Property panel edits and enable-keyframes toggle route to the correct property group.

**Requirements**: R1, R2, R3, R10

**Dependencies**: U1, U4

**Files**:
- `packages/studio/src/hooks/useAnimatedPropertyCommit.ts` — route by property group
- `packages/studio/src/hooks/useEnableKeyframes.ts` — create group-specific tweens
- `packages/studio/src/components/editor/PropertyPanel.tsx` — display group-aware keyframe nav

**Approach**: `commitAnimatedProperty` classifies the edited property into a group and targets that group's tween. `useEnableKeyframes` creates a group-specific tween when enabling keyframes for a property. The keyframe navigation diamonds in PropertyPanel use the group-tagged cache entries to show correct state per property.

**Test scenarios**:
- Edit opacity in property panel: only visual-group tween touched
- Enable keyframes on scale: creates scale-group tween, not mixed tween
- Keyframe diamond state (active/inactive/ghost) per property reflects the correct group

**Verification**: Property edits don't affect other property groups; keyframe nav shows correct per-property state

---

### U7. Remove Normalization and Backfill Workarounds

**Goal**: Remove the workarounds that were needed because of bundled keyframes.

**Requirements**: R1, R2, R3, R4

**Dependencies**: U4, U5

**Files**:
- `packages/core/src/parsers/gsapParser.ts` — remove `normalizeKeyframeProperties`
- `packages/studio/src/hooks/gsapDragCommit.ts` — remove backfillDefaults for x/y
- `packages/studio/src/hooks/gsapRuntimeBridge.ts` — remove SIZE_PROPS exclusion, IDENTITY_ONE backfill

**Approach**: With per-property-group tweens, each tween only contains its own properties. No cross-property backfill is needed. The normalization function, identity-value backfill, and width/height exclusion logic are all artifacts of the bundled model and can be removed.

**Test scenarios**:
- Drag adds keyframe with only `{x, y}` — no scale/width/height backfilled
- Resize adds keyframe with only `{width, height}` — no x/y/scale backfilled
- No `normalizeKeyframeProperties` call in any mutation path

**Verification**: Diff shows removed complexity; keyframe files contain only the properties the user explicitly set

---

### U8. Golden Test Refresh and Integration Tests

**Goal**: Update all golden snapshot tests and add integration tests for the property-group flows.

**Requirements**: All

**Dependencies**: U1-U7

**Files**:
- `packages/core/src/parsers/gsapParser.test.ts` — update existing tests, add group tests
- `packages/core/src/parsers/gsapParser.golden.test.ts` — refresh snapshots
- `packages/core/src/parsers/__goldens__/*.js` — updated golden files
- `packages/studio/src/utils/globalTimeCompiler.test.ts` — verify unchanged

**Approach**: Refresh all golden snapshots with the new group-aware ID format. Add integration tests that exercise: legacy split → group edit → verify file output. Add round-trip tests: parse → split → serialize → parse → verify.

**Test scenarios**:
- Golden snapshots match new ID format with group suffixes
- Legacy composition parses with `propertyGroup: undefined` (mixed)
- Split + edit + serialize produces valid GSAP
- Round-trip preserves all animation properties across splits
- Position resolution (`resolvedStart`) still correct after split

**Verification**: `bun test` passes all parser, golden, and compiler tests

---

## Open Questions

1. **Should `extras` (stagger, yoyo, repeat) be duplicated across all group tweens or kept on only one?** Current plan: keep on the "primary" group (the one with the most keyframes). Revisit if this causes GSAP playback issues.

2. **How should `fromTo()` split work?** Each group gets its own `fromTo()` with only the group's from/to properties. If a group has no fromProperties, it becomes a `to()` instead.

---

## Sources & Research

- GSAP percentage keyframes empirical tests (run in this session via browser DevTools)
- GSAP official docs: https://gsap.com/resources/keyframes/
- `keyframes-trace-investigation.md` — 6 root causes analysis
- `studio-keyframes-bug-audit.md` — 2026-06-10 audit findings
- Session debugging with `sdk-test.html` reference composition
