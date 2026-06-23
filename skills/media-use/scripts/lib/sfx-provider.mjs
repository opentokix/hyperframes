import { execSync } from "node:child_process";

function searchHeygenSfx(query, { limit = 5, minScore = 0.4 } = {}) {
  try {
    const q = query.replace(/'/g, "'\\''");
    const cmd = `heygen --x-source media-use audio sounds list --query '${q}' --type sound_effects --limit ${limit} --min-score ${minScore}`;
    const out = execSync(cmd, { encoding: "utf8", timeout: 15000, stdio: ["pipe", "pipe", "pipe"] });
    const payload = JSON.parse(out);
    const data = payload?.data;
    if (!Array.isArray(data) || data.length === 0) return null;
    return data;
  } catch {
    return null;
  }
}

export const sfxProvider = {
  async search(intent) {
    const results = searchHeygenSfx(intent);
    if (!results) return null;
    const best = results[0];
    return {
      url: best.audio_url,
      source: "search",
      ext: ".mp3",
      metadata: {
        description: best.description || best.name || intent,
        duration: best.duration || null,
        provider: "heygen.audio.sounds",
        provenance: { track_id: best.id, score: best.score, query: intent },
      },
    };
  },
};
