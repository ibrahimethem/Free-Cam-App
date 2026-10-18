/* Local release configuration only: no analytics or third-party API requests.
 * Enable a platform in download/releases.json only after its signed release
 * asset AND checksum have been published and verified on GitHub Releases.
 */
(async () => {
  try {
    const response = await fetch('releases.json', { cache: 'no-cache' });
    if (!response.ok) return;
    const release = await response.json();
    if (!/^\d+\.\d+\.\d+$/.test(release.version)) return;
    const base = `https://github.com/ibrahimethem/Free-Cam-App/releases/download/v${release.version}/`;
    const files = {
      macos: `NoSub-Studio-${release.version}-macOS-Apple-Silicon.dmg`,
      windows: `NoSub-Studio-${release.version}-Windows-x64-Setup.exe`,
    };
    for (const [platform, filename] of Object.entries(files)) {
      if (release[platform]?.published !== true) continue;
      const card = document.querySelector(`[data-platform="${platform}"]`);
      if (!card) continue;
      const download = card.querySelector('[data-download]');
      const checksum = card.querySelector('[data-checksum]');
      download.href = base + filename;
      checksum.href = base + filename + '.sha256';
      download.hidden = false;
      checksum.hidden = false;
      card.querySelector('[data-pending]').hidden = true;
      card.querySelector('[data-status]').textContent = `Version ${release.version} · signed release`;
    }
    // A beta is a separate opt-in channel, never a signed-production flag.
    const beta = release.windows?.beta;
    if (release.windows?.published !== true && beta?.published === true &&
        Number.isInteger(beta.number) && beta.number > 0 && beta.number < 1000) {
      const card = document.querySelector('[data-platform="windows"]');
      if (!card) return;
      const tag = `v${release.version}-windows-beta.${beta.number}`;
      const filename = `NoSub-Studio-${release.version}-Windows-x64-Public-Beta-${beta.number}-Setup.exe`;
      const url = `https://github.com/ibrahimethem/Free-Cam-App/releases/download/${tag}/${filename}`;
      const download = card.querySelector('[data-download]');
      download.href = url;
      download.textContent = 'Download Windows public beta';
      download.hidden = false;
      card.querySelector('[data-pending]').hidden = true;
      const checksum = card.querySelector('[data-checksum]');
      checksum.href = url + '.sha256';
      checksum.hidden = false;
      card.querySelector('[data-status]').textContent = `Version ${release.version} · Public beta ${beta.number} · UNSIGNED`;
      card.querySelector('[data-beta-warning]').hidden = false;
      const notes = card.querySelector('[data-beta-notes]');
      notes.href = `https://github.com/ibrahimethem/Free-Cam-App/releases/tag/${tag}`;
      notes.hidden = false;
    }
  } catch {
    // Keep honest pending states and the working Releases link on any failure.
  }
})();
