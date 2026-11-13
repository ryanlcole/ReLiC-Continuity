import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "app.js"), "utf8");
const source = fs.readFileSync(path.join(root, "rion_adapter.js"), "utf8");

new vm.Script(app);
new vm.Script(source);
const runtime = { window: {} };
vm.runInNewContext(source, runtime);
const rion = runtime.window.ReLiCRionAdapter;
assert.equal(rion.version, "RION-DEMO-v1");
assert.equal(rion.encodeLane(1, 0, 1), 5);
assert.equal(rion.encodeLane(0, 0, 0), 0);
assert.equal(rion.pack([{ known: 1, sign: 0, selected: 1 }, { known: 0, sign: 0, selected: 0 }]), "101 000");
const lane = rion.decodeLane(5);
assert.equal(lane.knownness, 1);
assert.equal(lane.sign, 0);
assert.equal(lane.value, 1);
assert.equal(rion.flipKnownValue(rion.flipKnownValue(5, 1), 1), 5);
assert.equal(rion.flipKnownValue(0, 1), 0);
assert.throws(() => rion.encodeLane(0, 0, 1));
assert.throws(() => rion.encodeLane(1, 0, 2));
assert.throws(() => rion.decodeLane(8));

for (const id of [...app.matchAll(/\$\("([\w-]+)"\)/g)].map((m) => m[1])) {
  assert.ok(html.includes('id="' + id + '"'), "Missing DOM element " + id);
}
for (const id of ["bios", "decode", "presence", "fullscreen", "save", "continue", "cancel", "exit", "probe", "talk"]) {
  assert.ok(html.includes('id="' + id + '"'), "Missing required section/control " + id);
}
assert.ok(html.includes('src="./rion_adapter.js" defer'), "Rion adapter must load first");
assert.ok(html.includes('src="./app.js" defer'), "App script missing");
assert.ok(html.includes('Content-Security-Policy'), "Missing CSP");
assert.ok(app.includes("RION LANES [KNOWN SIGN VALUE]"), "Missing binary state view");
assert.ok(app.includes("credentials: \"omit\""), "Probe must omit credentials");
assert.ok(app.includes('method: "HEAD"'), "Probe method must be HEAD");
assert.ok(!/getUserMedia\s*\(/.test(app), "No mic/camera capture in BIOS");
assert.ok(!/document\.cookie\s*=/.test(app), "No cookies created in demo");
assert.ok(!/\beval\s*\(/.test(app), "Do not eval commands");
console.log("Portal static contract: PASS");
