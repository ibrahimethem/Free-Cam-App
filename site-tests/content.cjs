// Keep marketing screenshots and copy aligned with the shipped UI.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.join(__dirname, '..');
const home = fs.readFileSync(path.join(root, 'site/index.html'), 'utf8');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

for (const [file, width, height] of [['ios-preview.png', 1320, 2868], ['studio-preview.png', 1400, 900]]) {
  const data = fs.readFileSync(path.join(root, 'site/assets', file));
  assert.equal(data.subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
  assert.equal(data.readUInt32BE(16), width);
  assert.equal(data.readUInt32BE(20), height);
  assert.ok(home.includes(`assets/${file}?v=${hash(data).slice(0, 12)}`), 'Update screenshot cache fingerprint');
  assert.ok(home.includes(`width="${width}" height="${height}"`));
}
assert.equal(hash(fs.readFileSync(path.join(root, 'site/assets/ios-preview.png'))),
  hash(fs.readFileSync(path.join(root, 'fastlane/screenshots/en-US/iPhone 17 Pro Max-01WiFiConnection.png'))),
  'Website phone screenshot must match current Fastlane artwork');
for (const obsolete of ['temporary pairing key', '16:9 monitor', 'idle monitor', 'route the stream through OBS']) {
  assert.ok(!home.includes(obsolete), 'Obsolete product copy: ' + obsolete);
}
for (const current of ['Scan the QR once', 'Native webcam output', 'presets', 'simulated', 'disabled in demo mode']) {
  assert.ok(home.includes(current), 'Missing current feature/demo disclosure: ' + current);
}
console.log('Current screenshot sources, PNG dimensions, cache fingerprints, product copy and demo disclosure passed');
