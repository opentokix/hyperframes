import { defineCommand } from "citty";
import type { Example } from "./_examples.js";
import { existsSync, readFileSync } from "node:fs";

export const examples: Example[] = [
  ["Present the current deck", "hyperframes present"],
  ["Present a specific project directory", "hyperframes present ./my-deck"],
  ["Use a custom port", "hyperframes present --port 8080"],
  ["Start without opening the browser", "hyperframes present --no-open"],
  ["Open with a specific browser", "hyperframes present --browser-path /usr/bin/chromium"],
];
import { resolve } from "node:path";
import * as clack from "@clack/prompts";
import { c } from "../ui/colors.js";
import { resolveProject } from "../utils/project.js";
import {
  openBrowser,
  parseRemoteDebuggingPort,
  validateRemoteDebuggingPortDeps,
} from "../utils/openBrowser.js";
import {
  resolveRuntimePath,
  resolvePlayerPath,
  resolveSlideshowPath,
  listenOnFreePort,
  injectRuntime,
  assetContentType,
} from "../utils/compositionServer.js";

export default defineCommand({
  meta: {
    name: "present",
    description: "Serve a slideshow deck and open it in presenter mode (with audience sync)",
  },
  args: {
    dir: { type: "positional", description: "Project directory", required: false },
    port: { type: "string", description: "Port to run the present server on", default: "3004" },
    open: { type: "boolean", default: true, description: "Open browser automatically" },
    "browser-path": { type: "string", description: "Path to the browser executable to open" },
    "user-data-dir": {
      type: "string",
      description: "Chromium-compatible user data directory (requires --browser-path)",
    },
    "remote-debugging-port": {
      type: "string",
      description: "Chromium remote debugging port (requires --browser-path and --user-data-dir)",
    },
  },
  async run({ args }) {
    const project = resolveProject(args.dir);
    const startPort = parseInt(args.port ?? "3004", 10);

    if (args["user-data-dir"] && !args["browser-path"]) {
      clack.log.error("--user-data-dir requires --browser-path");
      process.exitCode = 1;
      return;
    }
    const depsError = validateRemoteDebuggingPortDeps({
      browserPath: args["browser-path"] as string | undefined,
      userDataDir: args["user-data-dir"] as string | undefined,
      remoteDebuggingPort: args["remote-debugging-port"] as string | undefined,
    });
    if (depsError) {
      clack.log.error(depsError);
      process.exitCode = 1;
      return;
    }
    let remoteDebuggingPort: number | undefined;
    try {
      remoteDebuggingPort = parseRemoteDebuggingPort(
        args["remote-debugging-port"] as string | undefined,
      );
    } catch (err) {
      clack.log.error((err as Error).message);
      process.exitCode = 1;
      return;
    }

    const runtimePath = resolveRuntimePath();
    if (!runtimePath) {
      clack.log.error("HyperFrames runtime not found. Run `bun run build` first.");
      process.exitCode = 1;
      return;
    }
    const playerPath = resolvePlayerPath();
    const slideshowPath = resolveSlideshowPath();
    if (!playerPath || !slideshowPath) {
      clack.log.error(
        "@hyperframes/player not found. Run `bun run --cwd packages/player build` first.",
      );
      process.exitCode = 1;
      return;
    }

    // The deck must carry a slideshow island; the presenter view is meaningless
    // without one. Extract it here so we can inline it into the wrapper page.
    const indexHtml = readFileSync(project.indexPath, "utf-8");
    const { slideshowIslandRegex } = await import("@hyperframes/core/slideshow");
    const islandMatch = slideshowIslandRegex("i").exec(indexHtml);
    if (!islandMatch?.[1]) {
      clack.log.error(
        `No slideshow island found in ${project.indexPath}. ` +
          `Add a <script type="application/hyperframes-slideshow+json"> block — see /hyperframes (slideshow).`,
      );
      process.exitCode = 1;
      return;
    }
    const islandJson = islandMatch[1].trim();

    const { Hono } = await import("hono");
    const { createAdaptorServer } = await import("@hono/node-server");
    const { isSafePath } = await import("@hyperframes/core/studio-api");

    const app = new Hono();

    app.get("/player.js", (ctx) =>
      ctx.body(readFileSync(playerPath, "utf-8"), 200, {
        "Content-Type": "application/javascript",
        "Cache-Control": "no-cache",
      }),
    );
    app.get("/slideshow.js", (ctx) =>
      ctx.body(readFileSync(slideshowPath, "utf-8"), 200, {
        "Content-Type": "application/javascript",
        "Cache-Control": "no-cache",
      }),
    );
    app.get("/runtime.js", (ctx) =>
      ctx.body(readFileSync(runtimePath, "utf-8"), 200, {
        "Content-Type": "application/javascript",
        "Cache-Control": "no-cache",
      }),
    );

    // Serve composition files (HTML gets the runtime injected; other assets pass through).
    app.get("/composition/*", (ctx) => {
      const reqPath = ctx.req.path.replace("/composition/", "");
      const filePath = resolve(project.dir, reqPath);
      // Security: canonicalizes symlinks + guards the trailing separator so neither
      // an in-project symlink nor a sibling dir sharing the prefix can escape.
      if (!isSafePath(project.dir, filePath)) return ctx.text("Forbidden", 403);
      if (!existsSync(filePath)) return ctx.text("Not found", 404);
      if (filePath.endsWith(".html")) {
        return ctx.html(injectRuntime(readFileSync(filePath, "utf-8")));
      }
      return ctx.body(readFileSync(filePath), 200, { "Content-Type": assetContentType(filePath) });
    });

    // Both the presenter window and the audience window (opened by present() with
    // ?mode=audience) load this same page; the component reads the mode from the URL.
    app.get("/", (ctx) => ctx.html(buildPresentPage(project.name, islandJson)));

    clack.intro(c.bold("hyperframes present"));
    const s = clack.spinner();
    s.start("Starting presenter server...");

    const server = createAdaptorServer({ fetch: app.fetch });
    const actualPort = await listenOnFreePort(server, startPort);

    const url = `http://localhost:${actualPort}`;
    s.stop(c.success("Presenter server running"));
    console.log();
    if (actualPort !== startPort) {
      console.log(`  ${c.warn(`Port ${startPort} is in use, using ${actualPort} instead`)}`);
    }
    console.log(`  ${c.dim("Deck")}      ${c.accent(project.name)}`);
    console.log(`  ${c.dim("Present")}   ${c.accent(url)}`);
    console.log();
    console.log(`  ${c.dim("Click ▶ Present (or press P) to open the audience display.")}`);
    console.log(`  ${c.dim("Press Ctrl+C to stop")}`);
    console.log();

    if (args.open) {
      void openBrowser(url, {
        browserPath: args["browser-path"] as string | undefined,
        userDataDir: args["user-data-dir"] as string | undefined,
        remoteDebuggingPort,
      });
    }

    return new Promise<void>(() => {});
  },
});

function buildPresentPage(projectName: string, islandJson: string): string {
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${projectName} — Presenter</title>
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { height: 100%; background: #0a0a0a; overflow: hidden; }
      hyperframes-slideshow { display: block; position: relative; width: 100vw; height: 100vh; }
      #present-btn {
        position: fixed; top: 18px; right: 18px; z-index: 99999;
        font: 600 14px/1 system-ui, sans-serif; color: #0d1321;
        background: #f4b740; border: none; border-radius: 999px;
        padding: 11px 18px; cursor: pointer; box-shadow: 0 6px 20px rgba(0,0,0,.45);
      }
      #present-btn:hover { background: #ffcb5c; }
    </style>
    <script src="/player.js"></script>
    <script src="/slideshow.js"></script>
  </head>
  <body>
    <hyperframes-slideshow tabindex="0" sound>
      <hyperframes-player src="/composition/index.html"></hyperframes-player>
      <script type="application/hyperframes-slideshow+json">
${islandJson}
      </script>
    </hyperframes-slideshow>
    <button id="present-btn" type="button">▶&nbsp; Present</button>
    <script>
      (function () {
        // The audience window loads this same page with ?mode=audience; it must not
        // show the Present button or it would recurse opening windows.
        var isAudience = new URLSearchParams(location.search).get("mode") === "audience";
        var btn = document.getElementById("present-btn");
        if (isAudience) { if (btn) btn.remove(); return; }
        function present() {
          var ss = document.querySelector("hyperframes-slideshow");
          if (ss && typeof ss.present === "function") {
            ss.present();
            if (btn) btn.style.display = "none";
          }
        }
        if (btn) btn.addEventListener("click", present);
        // 'P' opens presenter mode (window.open needs a user gesture, so a key/click).
        window.addEventListener("keydown", function (e) {
          if ((e.key === "p" || e.key === "P") && !e.metaKey && !e.ctrlKey) present();
        });
      })();
    </script>
  </body>
</html>`;
}
