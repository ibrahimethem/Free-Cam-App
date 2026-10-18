const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'site/assets/downloads.js'), 'utf8');

async function render(release, fails = false) {
  const cards = Object.fromEntries(['macos', 'windows'].map(platform => {
    const fields = Object.fromEntries(['download', 'checksum', 'pending', 'status', 'beta-warning', 'beta-notes'].map(name =>
      [`[data-${name}]`, { hidden: ['download', 'checksum', 'beta-warning', 'beta-notes'].includes(name) }]));
    return [platform, { fields, querySelector: selector => fields[selector] }];
  }));
  await vm.runInNewContext(source, {
    fetch: async url => {
      assert.equal(url, 'releases.json');
      if (fails) throw Error('Offline');
      return { ok: true, json: async () => release };
    },
    document: { querySelector: selector => cards[selector.includes('macos') ? 'macos' : 'windows'] },
  });
  return cards;
}

(async () => {
  const configured = JSON.parse(fs.readFileSync(path.join(root, 'site/download/releases.json'), 'utf8'));
  assert.match(configured.version, /^\d+\.\d+\.\d+$/);
  for (const platform of ['macos', 'windows']) assert.equal(typeof configured[platform].published, 'boolean');
  let cards = await render({ version: '1.0.0', macos: { published: false }, windows: { published: false } });
  for (const card of Object.values(cards)) {
    assert.equal(card.fields['[data-download]'].hidden, true);
    assert.equal(card.fields['[data-pending]'].hidden, false);
  }
  cards = await render({ version: '1.0.0', macos: { published: true }, windows: { published: true } });
  const base = 'https://github.com/ibrahimethem/Free-Cam-App/releases/download/v1.0.0/';
  assert.equal(cards.macos.fields['[data-download]'].href, base + 'NoSub-Studio-1.0.0-macOS-Apple-Silicon.dmg');
  assert.equal(cards.windows.fields['[data-download]'].href, base + 'NoSub-Studio-1.0.0-Windows-x64-Setup.exe');
  for (const card of Object.values(cards)) {
    assert.equal(card.fields['[data-pending]'].hidden, true);
    assert.equal(card.fields['[data-checksum]'].href, card.fields['[data-download]'].href + '.sha256');
  }
  cards = await render({ version: '1.0.0', macos: { published: true }, windows: { published: false } });
  assert.equal(cards.macos.fields['[data-download]'].hidden, false);
  assert.equal(cards.windows.fields['[data-download]'].hidden, true);
  const betaRelease = { version: '1.0.0', macos: { published: true }, windows: { published: false, beta: { published: true, number: 1 } } };
  cards = await render(betaRelease);
  assert.equal(cards.windows.fields['[data-download]'].href,
    'https://github.com/ibrahimethem/Free-Cam-App/releases/download/v1.0.0-windows-beta.1/NoSub-Studio-1.0.0-Windows-x64-Public-Beta-1-Setup.exe');
  assert.match(cards.windows.fields['[data-status]'].textContent, /UNSIGNED/);
  assert.equal(cards.windows.fields['[data-beta-warning]'].hidden, false);
  assert.equal(cards.macos.fields['[data-beta-warning]'].hidden, true);
  assert.equal(cards.windows.fields['[data-checksum]'].href, cards.windows.fields['[data-download]'].href + '.sha256');
  cards = await render({ ...betaRelease, windows: { ...betaRelease.windows, published: true } });
  assert.match(cards.windows.fields['[data-status]'].textContent, /signed release/);
  assert.equal(cards.windows.fields['[data-beta-warning]'].hidden, true);
  for (const number of ['1', '../bad', 0, -1, 1000, 1.5]) {
    cards = await render({ ...betaRelease, windows: { published: false, beta: { published: true, number } } });
    assert.equal(cards.windows.fields['[data-download]'].hidden, true);
  }
  for (const [release, offline] of [[{ version: '../bad', macos: { published: true } }, false], [{ version: '1.0.0', macos: { published: 'true' } }, false], [null, true]]) {
    cards = await render(release, offline);
    assert.equal(cards.macos.fields['[data-download]'].hidden, true);
  }
  console.log('Download links: signed/beta separation, pending, per-platform, checksums, invalid configuration and offline checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
