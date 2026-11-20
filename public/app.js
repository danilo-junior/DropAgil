'use strict';
const paths = {
  upload:'M12 16V3m-5 5 5-5 5 5M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5',
  folder:'M3 7V5a1 1 0 0 1 1-1h5l2 3h9a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7Z',
  transfer:'M4 7h15m-4-4 4 4-4 4M20 17H5m4-4-4 4 4 4',
  network:'M9 3h6v5H9zM3 16h6v5H3zM15 16h6v5h-6zM12 8v4M6 16v-4h12v4',
  devices:'M13 17H4a1 1 0 0 1-1-1V4h16v5M7 21h6M10 17v4M16 11h5v10h-5z',
  monitor:'M3 4h18v13H3zM8 21h8M12 17v4', phone:'M7 2h10v20H7zM10 5h4M11 19h2',
  wifi:'M3 9a15 15 0 0 1 18 0M6 12a10 10 0 0 1 12 0M9 15a5 5 0 0 1 6 0M12 19h0',
  file:'M14 2H5v20h14V7l-5-5Zm0 0v6h5M8 13h8M8 17h6',
  shield:'m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6l8-4Zm-4 10 3 3 5-6',
  help:'M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2-3 4M12 17h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
  check:'m5 12 4 4L19 6', plus:'M12 5v14M5 12h14',
  lock:'M6 10h12v11H6zM8 10V6a4 4 0 0 1 8 0v4',
  qr:'M3 3h6v6H3zM15 3h6v6h-6zM3 15h6v6H3zM15 15h3v3h3v3h-6zM12 3v1M12 9v3H3M21 12h-6M12 15v6',
  drive:'M5 4h14l3 13v4H2v-4L5 4ZM2 17h20M16 19h1M19 19h1',
  spark:'m12 2 2.7 7.3L22 12l-7.3 2.7L12 22l-2.7-7.3L2 12l7.3-2.7L12 2Z',
  search:'M16 16l5 5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
  refresh:'M20 7a9 9 0 1 0 1 9M20 2v6h-6', copy:'M9 9h12v12H9zM15 5V3H3v12h2',
  close:'m6 6 12 12M6 18 18 6', pause:'M8 5v14M16 5v14', play:'m7 4 14 8-14 8V4Z',
  download:'M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4'
};
const $ = id => document.getElementById(id);
function icon(name) { return `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[name] || paths.file}"/></svg>`; }
document.querySelectorAll('[data-icon]').forEach(el => el.innerHTML = icon(el.dataset.icon));
document.querySelector('.version').textContent = 'DropAgíl · versão 2.0';
const androidLink = document.createElement('a');
androidLink.className = 'button primary'; androidLink.href = '/api/android-apk'; androidLink.textContent = 'Baixar aplicativo Android'; androidLink.setAttribute('download','DropAgil-Android.apk');
document.querySelector('.steps-card').append(androidLink);
const androidHint = document.createElement('p'); androidHint.className = 'local-warning'; androidHint.textContent = 'Android 10 ou superior. Instale uma vez para enviar pelo menu Compartilhar e baixar sem abrir o navegador.'; document.querySelector('.steps-card').append(androidHint);
const escapeHTML = value => String(value).replace(/[&<>"']/g, x => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
function bytes(n) { if (!n) return '0 B'; const units = ['B','KB','MB','GB','TB']; const i = Math.min(4, Math.floor(Math.log(n) / Math.log(1024))); return `${(n / 1024 ** i).toLocaleString('pt-BR', {maximumFractionDigits: i < 2 ? 0 : 1})} ${units[i]}`; }
function toast(message) { $('toast').textContent = message; $('toast').hidden = false; clearTimeout(toast.timer); toast.timer = setTimeout(() => $('toast').hidden = true, 5500); }
let status = null, currentView = 'transfer', currentPath = '', files = [], transfers = [], active = 0, booted = false;
let pending = {};
try { pending = JSON.parse(localStorage.getItem('dropagil.pending') || '{}'); } catch { /* Private browser may block storage. */ }
function remember() { try { localStorage.setItem('dropagil.pending', JSON.stringify(pending)); } catch { toast('O navegador não permitiu salvar a retomada. Mantenha esta página aberta.'); } }
function saveTransfer(t) { pending[t.key] = {id:t.id, path:t.path, size:t.size, offset:t.offset, key:t.key, groupId:t.groupId, groupName:t.groupName, done:t.state === 'done', startedAt:t.startedAt, finishedAt:t.finishedAt}; remember(); }
function forget(t) { delete pending[t.key]; remember(); }
async function api(url, options = {}) {
  const response = await fetch(url, {cache:'no-store', ...options});
  const data = await response.json();
  if (!response.ok) { const error = new Error(data.error || 'Não foi possível completar a ação.'); error.status = response.status; throw error; }
  return data;
}
const post = (url, data = {}) => api(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
function showView(view) {
  currentView = view;
  document.querySelectorAll('.view').forEach(el => el.hidden = el.id !== `view-${view}`);
  document.querySelectorAll('[data-view]').forEach(el => el.classList.toggle('active', el.dataset.view === view));
  $('pageCrumb').textContent = {transfer:'Transferir',files:'Arquivos da rede',connect:'Conectar dispositivo'}[view];
  if (view === 'files') loadFiles();
  if (view === 'connect') renderConnection();
}
document.querySelectorAll('[data-view]').forEach(el => el.onclick = () => showView(el.dataset.view));
$('showConnect').onclick = $('connectionButton').onclick = () => showView('connect');
$('helpButton').onclick = () => $('helpDialog').showModal();
$('closeHelp').onclick = () => $('helpDialog').close();
$('loginDialog').addEventListener('cancel', event => event.preventDefault());
$('deviceName').value = /Android|iPhone|iPad|Mobile/i.test(navigator.userAgent) ? 'Meu celular' : 'Meu computador';
$('loginForm').onsubmit = async event => {
  event.preventDefault(); const button = event.submitter; button.disabled = true; $('loginError').textContent = '';
  try { await post('/api/login', {pin:$('pinInput').value, name:$('deviceName').value}); $('loginDialog').close(); await connected(); }
  catch (error) { $('loginError').textContent = error.message; }
  finally { button.disabled = false; }
};
async function refreshStatus() {
  try {
    status = await api('/api/status');
    $('networkStatus').innerHTML = '<span></span>Rede local conectada'; $('networkStatus').classList.remove('offline');
    $('freeSpace').textContent = `${bytes(status.free)} livres`;
    $('deviceCount').textContent = status.devices.length;
    $('devices').innerHTML = status.devices.map(d => `<div class="device">${icon(/celular|phone/i.test(d.name) ? 'phone':'monitor')}<div>${escapeHTML(d.name)}<small>${d.local ? 'Este dispositivo':'Conectado agora'}</small></div><i class="online-dot"></i></div>`).join('');
    $('openFolder').hidden = !status.local;
    if (currentView === 'connect') renderConnection();
    return true;
  } catch (error) {
    $('networkStatus').innerHTML = '<span></span>Sem conexão'; $('networkStatus').classList.add('offline');
    if (error.status === 401 && !$('loginDialog').open) $('loginDialog').showModal();
    return false;
  }
}
async function connected() {
  await refreshStatus();
  if (!booted) {
    booted = true;
    for (const p of Object.values(pending)) {
      if (p && typeof p.path === 'string') transfers.push({...p, groupId:p.groupId || (p.path.includes('/') ? 'legacy:' + p.path.split('/')[0] : undefined), groupName:p.groupName || (p.path.includes('/') ? p.path.split('/')[0] : undefined), name:p.path.split('/').pop(), state:p.done ? 'done':'reselect', error:p.done ? '' : 'Selecione os mesmos arquivos para retomar.', loaded:0});
    }
    renderQueue();
    setInterval(async () => { if (await refreshStatus() && currentView === 'files') loadFiles(true); }, 10000);
  }
  if (currentView === 'files') loadFiles();
}
async function init() {
  try {
    await api('/api/status');
  } catch {
    if (['localhost','127.0.0.1'].includes(location.hostname)) {
      try { await post('/api/local-login'); } catch { $('loginDialog').showModal(); return; }
    } else { $('loginDialog').showModal(); return; }
  }
  await connected();
  if (['files','connect'].includes(location.hash.slice(1))) showView(location.hash.slice(1));
}
function renderConnection() {
  if (!status) return;
  const address = $('networkAddress'), old = address.value;
  if (JSON.stringify([...address.options].map(o => o.value)) !== JSON.stringify(status.urls)) {
    address.innerHTML = status.urls.map(url => `<option value="${escapeHTML(url)}">${escapeHTML(url)}</option>`).join('');
    if (status.urls.includes(old)) address.value = old;
  }
  $('pinBlock').hidden = !status.local;
  $('accessPin').textContent = status.pin || '••••••';
  updateQR();
}
function updateQR() {
  const address = $('networkAddress').value;
  if (!address) { $('qrImage').hidden = true; $('qrFallback').hidden = false; $('qrFallback').textContent = 'Não encontramos um IP de rede. Conecte o computador ao roteador e reinicie o DropAgíl.'; return; }
  const source = `/api/qr?url=${encodeURIComponent(address)}`;
  if ($('qrImage').getAttribute('src') !== source) { $('qrImage').hidden = false; $('qrFallback').hidden = true; $('qrImage').src = source; }
}
$('qrImage').onerror = () => { $('qrImage').hidden = true; $('qrFallback').hidden = false; };
$('networkAddress').onchange = updateQR;
$('copyAddress').onclick = async () => {
  const value = $('networkAddress').value; if (!value) return;
  try {
    if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(value);
    else { const input = document.createElement('textarea'); input.value = value; document.body.append(input); input.select(); const ok = document.execCommand('copy'); input.remove(); if (!ok) throw new Error(); }
    toast('Endereço copiado. Abra no outro dispositivo.');
  } catch { toast(`Abra no celular: ${value}`); }
};
$('openFolder').onclick = async () => { try { await post('/api/open-folder'); } catch (error) { toast(error.message); } };
async function loadFiles(quiet = false) {
  const requestedPath = currentPath;
  try { const data = await api(`/api/files?path=${encodeURIComponent(requestedPath)}`); if (currentPath !== requestedPath) return; files = data.items; renderFiles(); }
  catch (error) { if (!quiet) { $('filesList').innerHTML = `<div class="files-empty"><h2>Não foi possível abrir esta pasta</h2><p>${escapeHTML(error.message)}</p></div>`; } }
}
function renderFiles() {
  const crumb = $('folderBreadcrumb'); crumb.replaceChildren();
  const addCrumb = (label, path) => { const button = document.createElement('button'); button.textContent = label; button.onclick = () => { currentPath = path; loadFiles(); }; crumb.append(button); };
  addCrumb('Todos os arquivos', '');
  currentPath.split('/').filter(Boolean).forEach((part, i, all) => { const divider = document.createElement('span'); divider.textContent = '/'; crumb.append(divider); addCrumb(part, all.slice(0, i + 1).join('/')); });
  const search = $('fileSearch').value.toLocaleLowerCase();
  const matching = files.filter(file => file.name.toLocaleLowerCase().includes(search));
  $('filesList').innerHTML = matching.length ? '' : `<div class="files-empty">${icon('folder')}<h2>${search ? 'Nenhum arquivo encontrado':'Ainda não há arquivos aqui'}</h2><p>${search ? 'Tente buscar por outro nome.':'Envie pelo computador ou celular. Os arquivos aparecem aqui assim que terminarem.'}</p></div>`;
  matching.forEach(file => {
    const row = document.createElement('div'); row.className = 'file-row';
    row.innerHTML = `<span class="file-symbol ${file.directory ? 'directory':''}">${icon(file.directory ? 'folder':'file')}</span><div class="file-details"><${file.directory ? 'button':'span'} class="file-name" title="${escapeHTML(file.name)}">${escapeHTML(file.name)}</${file.directory ? 'button':'span'}><small>${file.directory ? 'Pasta':bytes(file.size)} · ${new Date(file.modified * 1000).toLocaleDateString('pt-BR')}</small></div><a class="button secondary" href="/api/${file.directory ? 'zip':'download'}?path=${encodeURIComponent(file.path)}" download>${icon('download')}${file.directory ? 'ZIP':'Baixar'}</a>`;
    if (file.directory) row.querySelector('.file-name').onclick = () => { currentPath = file.path; $('fileSearch').value = ''; loadFiles(); };
    if (file.directory) row.querySelector('a').onclick = () => toast('Preparando o ZIP direto no download. Pastas grandes podem levar um tempo.');
    const remove = document.createElement('button');
    remove.className = 'button secondary danger'; remove.textContent = 'Apagar';
    remove.setAttribute('aria-label', `Apagar ${file.name}`);
    remove.onclick = async () => {
      const detail = file.directory ? 'A pasta e todos os arquivos dentro dela serão apagados' : 'Este arquivo será apagado';
      if (!confirm(`Apagar “${file.name}”?\n\n${detail} permanentemente do computador e deixarão de estar disponíveis na rede. A cópia original no dispositivo que enviou será mantida.`)) return;
      remove.disabled = true;
      try {
        await api('/api/files', {method:'DELETE', headers:{'Content-Type':'application/json'}, body:JSON.stringify({path:file.path})});
        toast('Apagado da rede.'); await loadFiles();
      } catch (error) { toast(error.message); remove.disabled = false; }
    };
    row.append(remove);
    $('filesList').append(row);
  });
}
$('refreshFiles').onclick = () => loadFiles(); $('fileSearch').oninput = renderFiles;
$('chooseFiles').onclick = () => $('fileInput').click();
$('chooseFolder').onclick = () => $('folderInput').click();
for (const id of ['fileInput','folderInput']) $(id).onchange = () => { enqueue([...$(id).files].map(file => ({file, path:file.webkitRelativePath || file.name}))); $(id).value = ''; };
let dragDepth = 0;
$('dropzone').addEventListener('dragenter', e => { e.preventDefault(); dragDepth++; $('dropzone').classList.add('dragover'); });
$('dropzone').addEventListener('dragover', e => e.preventDefault());
$('dropzone').addEventListener('dragleave', e => { e.preventDefault(); if (--dragDepth <= 0) $('dropzone').classList.remove('dragover'); });
$('dropzone').addEventListener('drop', async e => {
  e.preventDefault(); dragDepth = 0; $('dropzone').classList.remove('dragover');
  const entries = [...e.dataTransfer.items].filter(item => item.kind === 'file').map(item => item.webkitGetAsEntry?.());
  const fallback = [...e.dataTransfer.files];
  try {
    const list = [];
    async function walk(entry, prefix = '') {
      if (entry.isFile) { const file = await new Promise((resolve,reject) => entry.file(resolve,reject)); list.push({file,path:prefix + file.name}); }
      else if (entry.isDirectory) { const reader = entry.createReader(); while (true) { const batch = await new Promise((resolve,reject) => reader.readEntries(resolve,reject)); if (!batch.length) break; for (const child of batch) await walk(child, prefix + entry.name + '/'); } }
    }
    if (entries.length && entries.every(Boolean)) for (const entry of entries) await walk(entry);
    else list.push(...fallback.map(file => ({file,path:file.name})));
    enqueue(list);
  } catch { toast('Não foi possível ler a pasta. Use o botão Enviar pasta.'); }
});
window.addEventListener('dragover', e => e.preventDefault());
window.addEventListener('drop', e => e.preventDefault());
function enqueue(items) {
  if (!items.length) { toast('Nenhum arquivo selecionado. Pastas vazias não são enviadas pelo navegador.'); return; }
  const selectionGroups = new Map();
  for (const {file,path} of items) {
    const key = JSON.stringify([path,file.size,file.lastModified]);
    const completed = transfers.find(t => t.key === key && t.state === 'done' && t.groupId && transfers.some(other => other.groupId === t.groupId && !['done','cancelled'].includes(other.state)));
    if (completed) continue;
    const existing = transfers.find(t => t.key === key && !['done','cancelled'].includes(t.state));
    if (existing && existing.state !== 'reselect') continue;
    const t = existing || {key,id:pending[key]?.id,offset:pending[key]?.offset || 0};
    Object.assign(t, {file,path,name:file.name,size:file.size,state:'queued',loaded:0,error:'',speed:0});
    if (path.includes('/')) {
      const name = path.split('/')[0];
      if (!selectionGroups.has(name)) selectionGroups.set(name, existing?.groupId || transfers.find(other => other.groupName === name && !['done','cancelled'].includes(other.state))?.groupId || `folder:${Date.now()}:${Math.random()}`);
      t.groupId = selectionGroups.get(name); t.groupName = name;
    }
    if (!existing) transfers.push(t);
    saveTransfer(t);
  }
  showView('transfer'); renderQueue(); pump();
}
function pump() {
  while (active < 2) {
    const t = transfers.find(item => item.state === 'queued' && !item.running);
    if (!t) break;
    active++; t.running = true; t.state = 'sending';
    const started = t.groupId ? transfers.find(other => other.groupId === t.groupId && other.startedAt)?.startedAt : t.startedAt;
    t.startedAt = started || Date.now();
    if (t.groupId) transfers.filter(other => other.groupId === t.groupId).forEach(other => other.startedAt = t.startedAt);
    renderQueue();
    send(t).finally(() => { active--; t.running = false; renderQueue(); pump(); });
  }
}
function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
async function send(t) {
  let failures = 0;
  while (t.state === 'sending') {
    try {
      const upload = await post('/api/uploads', {id:t.id,path:t.path,size:t.size,fingerprint:t.key});
      t.id = upload.id; t.offset = upload.offset; saveTransfer(t);
      if (t.state !== 'sending') return;
      if (upload.state !== 'done') {
        const chunkSize = status?.chunkSize || 8 * 1024 * 1024;
        while (t.offset < t.size && t.state === 'sending') {
          const blob = t.file.slice(t.offset, t.offset + chunkSize);
          t.started = performance.now();
          const result = await sendChunk(t, blob);
          t.offset = result.offset; t.loaded = 0; failures = 0; saveTransfer(t); renderQueue();
        }
        if (t.state !== 'sending') return;
        await post(`/api/uploads/${t.id}/complete`);
      }
      if (t.state === 'cancelled') return;
      t.state = 'done'; t.finishedAt = Date.now(); t.offset = t.size; t.loaded = 0; t.error = '';
      if (t.groupId) {
        saveTransfer(t);
        const members = transfers.filter(other => other.groupId === t.groupId && other.state !== 'cancelled');
        if (members.every(other => other.state === 'done')) { members.forEach(other => delete pending[other.key]); remember(); }
      } else forget(t);
      renderQueue();
      refreshStatus(); if (currentView === 'files') loadFiles();
    } catch (error) {
      t.loaded = 0;
      if (t.state !== 'sending') return;
      if (error.status === 401) { t.state = 'error'; t.error = 'Conecte novamente e toque em retomar.'; if (!$('loginDialog').open) $('loginDialog').showModal(); }
      else if (failures < 5 && (!error.status || error.status >= 500 && error.status !== 507 || error.status === 409)) {
        failures++; t.error = `Conexão interrompida. Tentando novamente (${failures}/5)…`; renderQueue();
        await sleep(Math.min(1000 * 2 ** failures, 15000));
      } else { t.state = 'error'; t.error = error.message || 'Conexão perdida. Toque em retomar.'; }
    }
  }
}
function sendChunk(t, blob) {
  return new Promise((resolve,reject) => {
    const xhr = new XMLHttpRequest(); t.xhr = xhr;
    xhr.open('PUT', `/api/uploads/${t.id}`); xhr.timeout = 120000;
    xhr.setRequestHeader('Content-Type','application/octet-stream'); xhr.setRequestHeader('Upload-Offset', t.offset);
    xhr.upload.onprogress = e => { t.loaded = e.loaded; t.speed = e.loaded / Math.max(.1, (performance.now() - t.started) / 1000); t.error = ''; updateRow(t); };
    xhr.onload = () => { t.xhr = null; let data; try { data = JSON.parse(xhr.responseText); } catch { data = {}; } if (xhr.status >= 200 && xhr.status < 300) resolve(data); else { const err = new Error(data.error || 'Não foi possível enviar o bloco.'); err.status = xhr.status; reject(err); } };
    xhr.onerror = xhr.ontimeout = () => { t.xhr = null; reject(new Error('Conexão interrompida. Toque em retomar.')); };
    xhr.onabort = () => { t.xhr = null; reject(new Error('Envio pausado.')); };
    xhr.send(blob);
  });
}
function seconds(n) { if (!isFinite(n) || n < 1) return 'Finalizando'; if (n < 60) return `${Math.ceil(n)} s restantes`; if (n < 3600) return `${Math.ceil(n/60)} min restantes`; return `${(n/3600).toFixed(1).replace('.',',')} h restantes`; }
function rowText(t) {
  if (t.state === 'done') return 'Enviado · disponível na rede';
  if (t.state === 'paused') return 'Pausado · pronto para retomar';
  if (t.state === 'queued') return 'Na fila';
  if (t.error) return t.error;
  if (t.state === 'sending') return t.speed ? `${bytes(t.speed)}/s · ${seconds((t.size - t.offset - t.loaded) / t.speed)}` : 'Preparando envio…';
  return 'Selecione o arquivo novamente';
}
function updateRow(t) {
  const group = t.displayGroup;
  if (!group?.row?.isConnected) return;
  const s = TransferGroups.summarize(group);
  const label = s.state === 'done' ? 'Enviado · disponível na rede' : s.state === 'sending' ? (s.speed ? `${bytes(s.speed)}/s · ${seconds((s.size-s.sent)/s.speed)}` : 'Preparando envio…') : s.state === 'queued' ? 'Na fila' : s.state === 'reselect' ? 'Selecione a pasta original para retomar' : s.state === 'error' ? s.error : 'Pausado · pronto para retomar';
  group.row.querySelector('.progress-fill').style.width = `${s.percent}%`;
  group.row.querySelector('.progress-track').setAttribute('aria-valuenow', s.percent);
  const starts = group.items.map(item => item.startedAt).filter(Boolean);
  const start = starts.length ? Math.min(...starts) : null;
  const end = s.state === 'done' ? Math.max(...group.items.map(item => item.finishedAt || Date.now())) : Date.now();
  const elapsed = start ? formatDuration(end - start) : '00:00';
  group.row.querySelector('.transfer-label').textContent = `${label} · ${s.state === 'done' ? 'Tempo total' : 'Decorrido'}: ${elapsed}`;
  group.row.querySelector('.transfer-percentage').textContent = `${s.percent}%`;
  group.row.querySelector('.file-details small').textContent = `${bytes(s.size)}${group.folder ? ` · ${s.done} de ${s.count} arquivos` : ''}`;
}
function formatDuration(ms) { const total = Math.max(0,Math.floor(ms/1000)), hours = Math.floor(total/3600); return (hours ? `${hours}:` : '') + `${Math.floor(total/60)%60}`.padStart(2,'0') + ':' + `${total%60}`.padStart(2,'0'); }
setInterval(() => { TransferGroups.groupTransfers(transfers).forEach(g => { if (g.items[0]) updateRow(g.items[0]); }); },1000);
async function cancelTransfers(items) {
  const unfinished = items.filter(t => !['done','cancelled'].includes(t.state));
  // Marcar todos primeiro impede a fila de iniciar o próximo durante o cancelamento.
  unfinished.forEach(t => { t.state = 'cancelled'; t.xhr?.abort(); });
  renderQueue();
  let failures = 0;
  let next = 0;
  async function clean() {
    while (next < unfinished.length) {
      const t = unfinished[next++];
      while (t.running) await sleep(100);
      try { if (t.id) await api(`/api/uploads/${t.id}`, {method:'DELETE'}); delete pending[t.key]; }
      catch (error) { if (error.status === 404) delete pending[t.key]; else failures++; }
    }
  }
  await Promise.all([clean(),clean(),clean(),clean()]); items.filter(t => t.state === 'done').forEach(t => delete pending[t.key]); remember();
  toast(failures ? `Fila parada. ${failures} partes precisam ser limpas quando a conexão voltar.` : 'Fila cancelada. Arquivos já concluídos foram mantidos.');
}
function renderQueue() {
  const visible = TransferGroups.groupTransfers(transfers);
  $('queueCount').textContent = visible.length;
  $('queueEmpty').hidden = !!visible.length;
  $('clearCompleted').hidden = !visible.some(group => TransferGroups.summarize(group).state === 'done');
  $('cancelAll').hidden = !transfers.some(t => !['done','cancelled'].includes(t.state));
  $('queueList').replaceChildren();
  visible.forEach(group => {
    const s = TransferGroups.summarize(group);
    const row = document.createElement('div'); group.row = row;
    group.items.forEach(t => t.displayGroup = group);
    row.className = `transfer-row ${s.state === 'done' ? 'done':''} ${s.state === 'error' ? 'error-row':''}`;
    row.innerHTML = `<div class="transfer-top"><span class="file-symbol">${icon(s.state === 'done' ? 'check':group.folder ? 'folder':'file')}</span><div class="file-details"><span class="file-name" title="${escapeHTML(group.name)}">${escapeHTML(group.name)}</span><small></small></div><div class="transfer-actions"></div></div><div class="progress-track" role="progressbar" aria-label="${escapeHTML(group.name)}" aria-valuemin="0" aria-valuemax="100"><div class="progress-fill"></div></div><div class="transfer-meta"><span class="transfer-label"></span><span class="transfer-percentage"></span></div>`;
    const actions = row.querySelector('.transfer-actions');
    function action(label, symbol, fn) { const button = document.createElement('button'); button.className = 'icon-button'; button.title = label; button.setAttribute('aria-label', `${label}: ${group.name}`); button.innerHTML = icon(symbol); button.onclick = fn; actions.append(button); }
    if (['sending','queued'].includes(s.state)) action('Pausar', 'pause', () => { group.items.filter(t => ['sending','queued'].includes(t.state)).forEach(t => { t.state = 'paused'; t.loaded = 0; t.xhr?.abort(); }); renderQueue(); });
    if (group.items.some(t => ['paused','error'].includes(t.state))) action('Retomar', 'play', () => { group.items.filter(t => ['paused','error'].includes(t.state)).forEach(t => { t.state = 'queued'; t.error = ''; }); renderQueue(); pump(); });
    if (group.items.some(t => t.state === 'reselect')) action('Selecionar novamente', 'folder', () => { toast('Selecione a pasta original ou os mesmos arquivos para continuar.'); $(group.folder ? 'folderInput':'fileInput').click(); });
    if (s.state !== 'done') action('Cancelar envio', 'close', () => { if (confirm(`Cancelar o envio de “${group.name}”? Os arquivos já concluídos serão mantidos.`)) cancelTransfers(group.items); });
    $('queueList').append(row); updateRow(group.items[0]);
  });
}
$('cancelAll').onclick = () => { if (confirm('Cancelar todos os envios desta página? Arquivos já concluídos serão mantidos.')) cancelTransfers(transfers); };
$('clearCompleted').onclick = () => { const done = new Set(TransferGroups.groupTransfers(transfers).filter(g => TransferGroups.summarize(g).state === 'done').flatMap(g => g.items)); transfers = transfers.filter(t => !done.has(t)); renderQueue(); };
window.addEventListener('beforeunload', e => { if (active > 0) { e.preventDefault(); e.returnValue = ''; } });
init();
