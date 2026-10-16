const element = id => document.getElementById(id);
const groups = {
  exposure: {mode: 'exposureAuto', manual: 'manualExposure', auto: 'autoExposure', fields: ['iso', 'shutterMs']},
  focus: {mode: 'focusAuto', manual: 'manualFocus', auto: 'autoFocus', fields: ['focus']},
  wb: {mode: 'whiteBalanceAuto', manual: 'manualWhiteBalance', auto: 'autoWhiteBalance', fields: ['temperature', 'tint']},
  zoom: {manual: 'canZoom', fields: ['zoom']}
};
let timer, query = '', latest, session, pending = false, connectionGeneration = 0;
const status = element('status');
const video = element('video');
const disconnect = element('disconnect');

function enableControls() {
  for (const [name, group] of Object.entries(groups)) {
    const caps = latest?.camera?.capabilities;
    const online = Boolean(query && latest?.cameraConnected && caps);
    element(name + '-group').disabled = !online || pending || (!caps[group.manual] && !caps[group.auto]);
    if (!online) continue;
    if (group.mode) {
      element(group.mode).disabled = !caps[group.manual] || !caps[group.auto];
      for (const field of group.fields) {
        element(field).disabled = element(group.mode).checked || !caps[group.manual];
      }
    }
  }
}

function updateOutputs() {
  element('focus-value').textContent = Number(element('focus').value).toFixed(2);
  element('zoom-value').textContent = Number(element('zoom').value).toFixed(2) + '×';
}

function seedFields(group) {
  const camera = latest?.camera;
  if (!camera) return;
  for (const field of group.fields) {
    const limits = camera.capabilities[field];
    const input = element(field);
    input.min = limits.min;
    input.max = limits.max;
    input.value = Math.min(limits.max, Math.max(limits.min, camera.current[field]));
  }
  updateOutputs();
}

function renderCamera() {
  const camera = latest?.camera;
  if (latest?.cameraConnected && camera) {
    if (session !== camera.session) {
      session = camera.session;
      for (const group of Object.values(groups)) {
        if (group.mode) element(group.mode).checked = camera.current[group.mode];
        seedFields(group);
      }
    }
    const current = camera.current;
    element('exposure-reading').textContent = `Live: ISO ${current.iso.toFixed(0)} · ${current.shutterMs.toFixed(2)} ms (${current.exposureAuto ? 'auto' : 'manual'})`;
    element('focus-reading').textContent = `Live: ${current.focus.toFixed(2)} (${current.focusAuto ? 'auto' : 'manual'}) · 0 nearest, 1 furthest`;
    element('wb-reading').textContent = `Live: ${current.temperature.toFixed(0)} K · tint ${current.tint.toFixed(1)} (${current.whiteBalanceAuto ? 'auto' : 'manual'})`;
    element('zoom-reading').textContent = `Live: ${current.zoom.toFixed(2)}×`;
    element('control-status').textContent = latest.revision > camera.appliedRevision
      ? 'Waiting for iPhone to acknowledge settings…'
      : camera.error ? `Camera rejected settings: ${camera.error}`
      : 'Camera ready. Live readings show the actual sensor settings. Unsupported controls are disabled.';
  } else {
    element('control-status').textContent = 'Camera controls offline. Start streaming on your iPhone.';
  }
  enableControls();
}

async function poll(generation) {
  try {
    const response = await fetch('/status' + query);
    if (!response.ok) throw Error(response.status === 401 ? 'Invalid pairing key.' : 'Receiver unavailable.');
    const state = await response.json();
    if (generation !== connectionGeneration) return;
    latest = state;
    status.textContent = state.connected ? 'Live · ' + state.frames + ' frames received' : 'Waiting for your iPhone. Open NoSub Cam and start streaming.';
    renderCamera();
  } catch (error) {
    if (generation !== connectionGeneration) return;
    latest = null;
    status.textContent = error.message;
    renderCamera();
  }
}

element('pair').onsubmit = async event => {
  event.preventDefault();
  clearInterval(timer);
  const generation = ++connectionGeneration;
  query = '?key=' + encodeURIComponent(element('key').value.trim());
  session = null;
  latest = null;
  enableControls();
  await poll(generation);
  if (generation !== connectionGeneration || !latest) return;
  video.src = '/stream.mjpg' + query;
  video.hidden = false;
  disconnect.hidden = false;
  element('obs').textContent = location.origin + '/stream.mjpg' + query;
  timer = setInterval(() => poll(generation), 700);
};

disconnect.onclick = () => {
  ++connectionGeneration;
  clearInterval(timer);
  query = ''; latest = null; session = null;
  video.removeAttribute('src'); video.hidden = true;
  disconnect.hidden = true; status.textContent = 'Preview disconnected.';
  element('obs').textContent = 'Connect to show the stream address.';
  renderCamera();
};

for (const group of Object.values(groups)) {
  if (group.mode) element(group.mode).onchange = () => {
    if (!element(group.mode).checked) seedFields(group);
    enableControls();
  };
  for (const field of group.fields) element(field).oninput = updateOutputs;
}

for (const button of document.querySelectorAll('[data-group]')) {
  button.onclick = async () => {
    if (pending || !latest?.cameraConnected) return;
    const group = groups[button.dataset.group];
    const settings = {};
    if (group.mode) settings[group.mode] = element(group.mode).checked;
    if (!group.mode || !settings[group.mode]) {
      for (const field of group.fields) {
        const input = element(field);
        if (!input.value || !input.reportValidity()) return;
        settings[field] = Number(input.value);
      }
    }
    const generation = connectionGeneration;
    const request = {session, revision: latest.revision, settings};
    pending = true;
    enableControls();
    element('control-status').textContent = 'Sending camera settings…';
    try {
      const response = await fetch('/controls' + query, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(request)
      });
      if (!response.ok) throw Error(await response.text());
      await poll(generation);
    } catch (error) {
      if (generation === connectionGeneration) element('control-status').textContent = error.message;
    } finally {
      pending = false;
      enableControls();
    }
  };
}
