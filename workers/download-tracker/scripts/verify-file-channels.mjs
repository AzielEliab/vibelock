/**
 * Hosted /v1/detect channel report. No download counter. No container decode.
 * Author: Aziel Eliab.
 */
import assert from "node:assert/strict";
import { handleRuntime } from "../src/runtime.js";

async function post(body) {
  const req = new Request("https://vibelock.example/v1/detect", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const res = await handleRuntime(req, new URL(req.url), {});
  const json = await res.json();
  return { status: res.status, json };
}

const refused = await post({ container_b64: "AAAA", filename: "clip.mp4" });
assert.equal(refused.status, 400);
assert.equal(refused.json.ok, false);
assert.match(refused.json.error, /does not decode container/);
assert.equal(refused.json.decodes_containers, false);

const scored = await post({
  features: { rms: 0.08, zcr: 0.07 },
  linguistics: {
    speech_like: true,
    duration_s: 1.2,
    syllable_peak_ratio: 12,
    interval_cv: 0.01,
    n_intervals: 6,
    transition_median: 0.08,
  },
  filename: "voice.mp3",
  format: "mp3",
});
assert.equal(scored.status, 200);
assert.equal(scored.json.ok, true);
assert.equal(scored.json.accuracy_claim, false);
assert.equal(scored.json.decodes_containers, false);
assert.equal(scored.json.courtroom_proof, false);
const names = scored.json.channels.map((c) => c.name);
assert.deepEqual(names, ["physics", "linguistics", "vibration", "related"]);
const ling = scored.json.channels.find((c) => c.name === "linguistics");
assert.equal(ling.status, "fired");
assert.equal(ling.evidence, "experimental");
assert.ok(ling.reason_codes.includes("LINGUISTIC_RHYTHM_METRONOME"));
const vib = scored.json.channels.find((c) => c.name === "vibration");
assert.equal(vib.status, "insufficient");
assert.equal(scored.json.format, "mp3");
assert.equal(typeof scored.json.score, "number");
assert.ok(!("accuracy" in scored.json));

const withVib = await post({
  features: { rms: 0.1, zcr: 0.08 },
  vibration: { coherence: 0.1, transfer_residual: 1.3, delay_s: 0.1 },
});
assert.equal(withVib.status, 200);
const vibFired = withVib.json.channels.find((c) => c.name === "vibration");
assert.equal(vibFired.status, "fired");
assert.equal(vibFired.evidence, "measurement");
assert.ok(vibFired.reason_codes.includes("COHERENCE_LOW"));

console.log("verify-file-channels: ok");
