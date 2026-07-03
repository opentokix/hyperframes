import { describe, expect, it } from "vitest";
import { mkdtempSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { cleanSnapshotDir, computeSnapshotTimes, tailFrameTime } from "./snapshot.js";

describe("tailFrameTime", () => {
  it("backs off ~3% of duration so the final frame isn't the blank exact-end", () => {
    // Verified on the V4 3D artifact: t=8.0 of an 8s clip rendered blank white,
    // t=7.76 rendered the final hero. 8 - 8*0.03 = 7.76.
    expect(tailFrameTime(8)).toBeCloseTo(7.76, 5);
  });

  it("uses a 50ms floor for short clips", () => {
    expect(tailFrameTime(1)).toBeCloseTo(0.95, 5); // 1 - 0.05 (floor beats 3%)
  });

  it("never goes negative", () => {
    expect(tailFrameTime(0)).toBe(0);
  });
});

describe("computeSnapshotTimes (FINDING [7]: tail is always captured)", () => {
  it("default frames: last point is the readable tail, never exact duration", () => {
    const { times, appendedTail } = computeSnapshotTimes(8, { frames: 5 });
    expect(times).toHaveLength(5);
    expect(times[0]).toBe(0);
    expect(times[times.length - 1]).toBeCloseTo(7.76, 5);
    expect(times[times.length - 1]).toBeLessThan(8); // not the blank exact-end
    expect(appendedTail).toBe(false);
  });

  it("single frame samples the midpoint", () => {
    expect(computeSnapshotTimes(8, { frames: 1 }).times).toEqual([4]);
  });

  it("explicit --at: keeps the user's times AND appends an end-of-timeline frame", () => {
    const { times, appendedTail } = computeSnapshotTimes(8, { frames: 5, at: [1, 2, 3] });
    expect(times.slice(0, 3)).toEqual([1, 2, 3]);
    expect(times[times.length - 1]).toBeCloseTo(7.76, 5);
    expect(appendedTail).toBe(true);
  });

  it("explicit --at: does not double-add when the user already sampled the tail", () => {
    const { times, appendedTail } = computeSnapshotTimes(8, { frames: 5, at: [1, 7.76] });
    expect(times).toEqual([1, 7.76]);
    expect(appendedTail).toBe(false);
  });

  it("explicit --at: a sample at exact duration counts as the tail (no append)", () => {
    const { appendedTail } = computeSnapshotTimes(8, { frames: 5, at: [1, 8] });
    expect(appendedTail).toBe(false);
  });

  it("respects includeEnd:false opt-out for --at", () => {
    const { times, appendedTail } = computeSnapshotTimes(8, {
      frames: 5,
      at: [1, 2],
      includeEnd: false,
    });
    expect(times).toEqual([1, 2]);
    expect(appendedTail).toBe(false);
  });
});

// Regression: every `snapshot` run unconditionally wiped the output
// directory's existing .png/.jpg files before capturing new ones, so two
// consecutive runs with different --at sets clobbered each other with no
// way to opt out. cleanSnapshotDir is now a separate, callable-or-skippable
// step (see the --clean/--no-clean flag) instead of being inlined and
// unconditional.
describe("cleanSnapshotDir", () => {
  it("deletes existing image files in the directory", () => {
    const dir = mkdtempSync(join(tmpdir(), "snapshot-clean-"));
    writeFileSync(join(dir, "frame-1.png"), "stub");
    writeFileSync(join(dir, "frame-2.jpg"), "stub");
    try {
      cleanSnapshotDir(dir);
      expect(readdirSync(dir)).toEqual([]);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("only removes image files, leaving other files untouched", () => {
    const dir = mkdtempSync(join(tmpdir(), "snapshot-clean-scope-"));
    writeFileSync(join(dir, "frame.png"), "stub");
    writeFileSync(join(dir, "descriptions.md"), "keep me");
    try {
      cleanSnapshotDir(dir);
      expect(readdirSync(dir)).toEqual(["descriptions.md"]);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("does not throw when the directory does not exist", () => {
    expect(() =>
      cleanSnapshotDir(join(tmpdir(), "snapshot-clean-missing-nonexistent")),
    ).not.toThrow();
  });
});
