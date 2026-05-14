import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  _resetAutoBrowserGpuModeCacheForTests,
  buildChromeArgs,
  forceReleaseBrowser,
  resolveBrowserGpuMode,
} from "./browserManager.js";

describe("buildChromeArgs browser GPU mode", () => {
  const base = { width: 1920, height: 1080 };

  it("uses SwiftShader software GL by default for reproducible local renders", () => {
    const args = buildChromeArgs(base);
    expect(args).toContain("--enable-features=CanvasDrawElement");
    expect(args).toContain("--use-gl=angle");
    expect(args).toContain("--use-angle=swiftshader");
    expect(args).toContain("--enable-unsafe-swiftshader");
    expect(args).not.toContain("--enable-gpu-rasterization");
  });

  it("uses Metal-backed ANGLE for hardware browser GPU mode on macOS", () => {
    const args = buildChromeArgs({ ...base, platform: "darwin" }, { browserGpuMode: "hardware" });
    expect(args).toContain("--use-gl=angle");
    expect(args).toContain("--use-angle=metal");
    expect(args).toContain("--enable-gpu-rasterization");
    expect(args).not.toContain("--use-angle=swiftshader");
  });

  it("uses D3D11-backed ANGLE for hardware browser GPU mode on Windows", () => {
    const args = buildChromeArgs({ ...base, platform: "win32" }, { browserGpuMode: "hardware" });
    expect(args).toContain("--use-gl=angle");
    expect(args).toContain("--use-angle=d3d11");
    expect(args).toContain("--enable-gpu-rasterization");
    expect(args).not.toContain("--use-angle=swiftshader");
  });

  it("uses EGL for hardware browser GPU mode on Linux", () => {
    const args = buildChromeArgs({ ...base, platform: "linux" }, { browserGpuMode: "hardware" });
    expect(args).toContain("--use-gl=egl");
    expect(args).toContain("--enable-gpu-rasterization");
    expect(args).not.toContain("--use-gl=angle");
    expect(args).not.toContain("--use-angle=swiftshader");
  });

  it("keeps --disable-gpu authoritative when requested", () => {
    const args = buildChromeArgs(
      { ...base, platform: "darwin" },
      { browserGpuMode: "hardware", disableGpu: true },
    );
    expect(args).toContain("--disable-gpu");
    expect(args).toContain("--use-angle=swiftshader");
    expect(args).not.toContain("--use-angle=metal");
  });
});

describe("resolveBrowserGpuMode", () => {
  beforeEach(() => {
    _resetAutoBrowserGpuModeCacheForTests();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    _resetAutoBrowserGpuModeCacheForTests();
  });

  it("passes 'software' through unchanged without probing", async () => {
    const mode = await resolveBrowserGpuMode("software");
    expect(mode).toBe("software");
  });

  it("passes 'hardware' through unchanged without probing", async () => {
    const mode = await resolveBrowserGpuMode("hardware");
    expect(mode).toBe("hardware");
  });

  it("falls back to 'software' when the probe browser cannot launch", async () => {
    // No chromePath, env unset, and (in the test env) no system Chrome to find
    // → puppeteer.launch will throw → caller catches → software fallback.
    // Force a definitely-missing chrome binary so the launch path errors fast.
    const mode = await resolveBrowserGpuMode("auto", {
      chromePath: "/definitely/not/a/real/chrome/binary",
      browserTimeout: 2000,
    });
    expect(mode).toBe("software");
  });

  it("caches the probe result across calls", async () => {
    const first = await resolveBrowserGpuMode("auto", {
      chromePath: "/definitely/not/a/real/chrome/binary",
      browserTimeout: 2000,
    });
    // Second call uses cache — no new launch. Assert the same answer comes back
    // even with a different chromePath that would have a different probe outcome.
    const second = await resolveBrowserGpuMode("auto", {
      chromePath: "/another/definitely/missing/path",
      browserTimeout: 2000,
    });
    expect(first).toBe("software");
    expect(second).toBe("software");
    // Reset and re-probe to confirm the test-only reset works.
    _resetAutoBrowserGpuModeCacheForTests();
    const third = await resolveBrowserGpuMode("hardware");
    expect(third).toBe("hardware");
  });

  it("deduplicates concurrent auto-mode probes by caching the in-flight Promise", async () => {
    // Parallel coordinator fires N workers via Promise.all — without Promise-
    // level caching, a `--workers 4` render against a no-GPU host would launch
    // 4 simultaneous probe Chromes. Verify all concurrent callers get the
    // exact same Promise reference (proving the probe runs once, not N times).
    const p1 = resolveBrowserGpuMode("auto", {
      chromePath: "/definitely/not/a/real/chrome/binary",
      browserTimeout: 2000,
    });
    const p2 = resolveBrowserGpuMode("auto", {
      chromePath: "/definitely/not/a/real/chrome/binary",
      browserTimeout: 2000,
    });
    const p3 = resolveBrowserGpuMode("auto", {
      chromePath: "/definitely/not/a/real/chrome/binary",
      browserTimeout: 2000,
    });
    expect(p1).toBe(p2);
    expect(p2).toBe(p3);
    const results = await Promise.all([p1, p2, p3]);
    expect(results).toEqual(["software", "software", "software"]);
  });
});

describe("acquireBrowser — software-renderer guard", () => {
  // Tests for the defense-in-depth rule that a "software"-resolved GPU mode
  // must force `captureMode = "screenshot"` regardless of platform/binary.
  // Without this guard, BeginFrame attempts on a software-rendered compositor
  // hang at the CDP protocolTimeout (the hf#677 spike repro). Tests below
  // mock puppeteer at the module-import level so no real Chrome is launched.

  const origPlatform = process.platform;

  // Captures the most recent puppeteer.launch call so tests can assert on the
  // args/executablePath actually passed to Chrome.
  let lastLaunchArgs: string[] | undefined;
  let lastLaunchExecutablePath: string | undefined;

  function installPuppeteerMock() {
    const browserStub = {
      close: vi.fn().mockResolvedValue(undefined),
      newPage: vi.fn().mockResolvedValue({
        close: vi.fn().mockResolvedValue(undefined),
        createCDPSession: vi.fn().mockResolvedValue({
          send: vi.fn().mockResolvedValue(undefined),
          detach: vi.fn().mockResolvedValue(undefined),
        }),
      }),
    };
    const launch = vi.fn(async (opts: { args: string[]; executablePath?: string }) => {
      lastLaunchArgs = opts.args;
      lastLaunchExecutablePath = opts.executablePath;
      return browserStub;
    });
    // Both `puppeteer` and `puppeteer-core` are tried by getPuppeteer() — mock
    // both so it doesn't matter which one resolves first.
    vi.doMock("puppeteer", () => ({ default: { launch } }));
    vi.doMock("puppeteer-core", () => ({ default: { launch } }));
    return { launch, browserStub };
  }

  beforeEach(() => {
    vi.resetModules();
    lastLaunchArgs = undefined;
    lastLaunchExecutablePath = undefined;
    Object.defineProperty(process, "platform", { value: "linux", configurable: true });
  });

  afterEach(() => {
    Object.defineProperty(process, "platform", { value: origPlatform, configurable: true });
    vi.restoreAllMocks();
    vi.doUnmock("puppeteer");
    vi.doUnmock("puppeteer-core");
  });

  it("forces screenshot capture mode when browserGpuMode resolves to 'software' on Linux", async () => {
    installPuppeteerMock();
    const { acquireBrowser: acquire } = await import("./browserManager.js");

    // chromePath points to a fake chrome-headless-shell so the Linux + binary
    // preconditions for beginframe are satisfied — the software-GPU guard is
    // the only thing that should flip captureMode to screenshot.
    const chromeArgs = [
      "--no-sandbox",
      "--enable-begin-frame-control",
      "--deterministic-mode",
      "--run-all-compositor-stages-before-draw",
    ];
    const result = await acquire(chromeArgs, {
      chromePath: "/fake/chrome-headless-shell",
      browserGpuMode: "software",
    });

    expect(result.captureMode).toBe("screenshot");
    // BeginFrame-only flags MUST be stripped from the launched args — leaving
    // `--enable-begin-frame-control` in produces blank screenshots because the
    // compositor waits for beginFrames we'll never send.
    expect(lastLaunchArgs).not.toContain("--enable-begin-frame-control");
    expect(lastLaunchArgs).not.toContain("--deterministic-mode");
    expect(lastLaunchArgs).not.toContain("--run-all-compositor-stages-before-draw");
    expect(lastLaunchArgs).toContain("--no-sandbox");
  });

  it("keeps beginframe capture mode when browserGpuMode is 'hardware' on Linux with headless-shell", async () => {
    installPuppeteerMock();
    const { acquireBrowser: acquire } = await import("./browserManager.js");

    const chromeArgs = ["--no-sandbox", "--enable-begin-frame-control"];
    const result = await acquire(chromeArgs, {
      chromePath: "/fake/chrome-headless-shell",
      browserGpuMode: "hardware",
    });

    // Hardware GPU + Linux + headless-shell + no forceScreenshot → beginframe.
    // (The post-launch probe normally checks HeadlessExperimental.enable; our
    // mock CDP session resolves it successfully, so the probe passes.)
    expect(result.captureMode).toBe("beginframe");
    // BeginFrame flags preserved in the launched args.
    expect(lastLaunchArgs).toContain("--enable-begin-frame-control");
    expect(lastLaunchExecutablePath).toBe("/fake/chrome-headless-shell");
  });

  it("forces screenshot mode when forceScreenshot=true regardless of GPU mode", async () => {
    // Existing behavior — the new software-GPU branch must not regress this.
    installPuppeteerMock();
    const { acquireBrowser: acquire } = await import("./browserManager.js");

    const chromeArgs = ["--no-sandbox", "--enable-begin-frame-control"];
    const result = await acquire(chromeArgs, {
      chromePath: "/fake/chrome-headless-shell",
      browserGpuMode: "hardware",
      forceScreenshot: true,
    });

    expect(result.captureMode).toBe("screenshot");
    expect(lastLaunchArgs).not.toContain("--enable-begin-frame-control");
  });

  it("emits a one-time software-GPU warning when the guard actually changed the outcome", async () => {
    installPuppeteerMock();
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const { acquireBrowser: acquire, releaseBrowser: release } =
      await import("./browserManager.js");

    const chromeArgs = ["--no-sandbox", "--enable-begin-frame-control"];
    const acquired = await acquire(chromeArgs, {
      chromePath: "/fake/chrome-headless-shell",
      browserGpuMode: "software",
    });
    // release so subsequent acquires don't reuse a pooled browser (we have
    // pooling off by default but be explicit).
    await release(acquired.browser);

    const messages = warnSpy.mock.calls.map((c) => String(c[0]));
    const softwareWarn = messages.find((m) => m.includes("Software GPU detected"));
    expect(softwareWarn).toBeDefined();
    expect(softwareWarn).toContain("screenshot");
  });

  it("does NOT emit the software-GPU warning on macOS (already screenshot anyway)", async () => {
    // macOS uses screenshot mode unconditionally — the software-GPU guard
    // didn't change the outcome, so the warn should stay silent.
    Object.defineProperty(process, "platform", { value: "darwin", configurable: true });
    installPuppeteerMock();
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const { acquireBrowser: acquire, releaseBrowser: release } =
      await import("./browserManager.js");

    const acquired = await acquire(["--no-sandbox"], {
      chromePath: "/fake/chrome-headless-shell",
      browserGpuMode: "software",
    });
    await release(acquired.browser);

    const messages = warnSpy.mock.calls.map((c) => String(c[0]));
    expect(messages.find((m) => m.includes("Software GPU detected"))).toBeUndefined();
  });
});

describe("forceReleaseBrowser", () => {
  it("kills the browser process and disconnects", () => {
    const killFn = vi.fn(() => true);
    const disconnectFn = vi.fn();
    const mockBrowser = {
      process: () => ({ kill: killFn, killed: false }),
      disconnect: disconnectFn,
    } as any;

    forceReleaseBrowser(mockBrowser);

    expect(killFn).toHaveBeenCalledWith("SIGKILL");
    expect(disconnectFn).toHaveBeenCalled();
  });

  it("tolerates an already-killed process", () => {
    const killFn = vi.fn();
    const disconnectFn = vi.fn();
    const mockBrowser = {
      process: () => ({ kill: killFn, killed: true }),
      disconnect: disconnectFn,
    } as any;

    forceReleaseBrowser(mockBrowser);

    expect(killFn).not.toHaveBeenCalled();
    expect(disconnectFn).toHaveBeenCalled();
  });
});
