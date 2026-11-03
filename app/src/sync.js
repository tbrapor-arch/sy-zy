
// ---------- Google Drive: the book and your progress, on every device
// Two routes, chosen by where the app is open:
//  - hosted (tbrapor-arch.github.io/syzy): Google sign-in and the hidden app folder of Drive, as in 书架 Shūjià.
//    Same site and same Google client as Shūjià, so the two apps share that folder: a book imported in Shūjià is found here.
//  - inside claude.ai: the page cannot sign in to Google itself; it goes through the viewer's Google Drive connector,
//    and keeps the book as an ordinary file in Drive.
const HOSTED = !!document.querySelector('link[rel=manifest]');
const SYNC_KEYS = ['doneAt', 'deck', 'days', 'bookNotes', 'readAt', 'lists'];

// ---- hosted: Google Identity Services + Drive appDataFolder (code shape taken from Shūjià)
const GCLIENT = '509495064448-dip09vjpfiq0690mq5l03hssm4g0rmsa.apps.googleusercontent.com';
const DRIVE = 'https://www.googleapis.com/drive/v3/files', UPLOAD = 'https://www.googleapis.com/upload/drive/v3/files';
const Sync = {
  busy: false, timer: 0, status: '',
  enabled() { return store.get('syncOn', false); },
  token() { const t = store.get('gToken', null); return t && t.exp > Date.now() + 60000 ? t.t : null; },
  loadGIS() {
    return new Promise((res, rej) => {
      if (window.google && google.accounts && google.accounts.oauth2) return res();
      const sc = document.createElement('script'); sc.src = 'https://accounts.google.com/gsi/client';
      sc.onload = res; sc.onerror = () => rej(new Error('Google cannot be reached from this page.'));
      document.head.append(sc);
    });
  },
  async login() {
    await this.loadGIS();
    const tok = await new Promise((res, rej) => {
      const tc = google.accounts.oauth2.initTokenClient({ client_id: GCLIENT, scope: 'https://www.googleapis.com/auth/drive.appdata',
        callback: r => r.error ? rej(new Error(r.error_description || r.error)) : res(r),
        error_callback: e => rej(new Error(e.type === 'popup_closed' ? 'The Google window was closed.' : (e.message || e.type))) });
      tc.requestAccessToken({ prompt: this.enabled() ? '' : 'consent' });
    });
    store.set('gToken', { t: tok.access_token, exp: Date.now() + (tok.expires_in || 3600) * 1000 }); store.set('syncOn', true);
  },
  logout() { const t = this.token(); try { if (t && window.google) google.accounts.oauth2.revoke(t, () => {}); } catch {} store.set('gToken', null); store.set('syncOn', false); },
  async g(url, opts = {}) {
    const t = this.token(); if (!t) throw new Error('Sign in to Google again.');
    const r = await fetch(url, Object.assign({}, opts, { headers: Object.assign({ Authorization: 'Bearer ' + t }, opts.headers || {}) }));
    if (r.status === 401) { store.set('gToken', null); throw new Error('Sign in to Google again.'); }
    if (!r.ok) throw new Error('Google Drive answered ' + r.status + '.');
    return r;
  },
  async list() {
    const out = []; let pt = '';
    do { const r = await (await this.g(`${DRIVE}?spaces=appDataFolder&pageSize=1000&fields=nextPageToken,files(id,name,size,modifiedTime)${pt ? '&pageToken=' + pt : ''}`)).json(); out.push(...(r.files || [])); pt = r.nextPageToken || ''; } while (pt);
    return out;
  },
  async put(name, blob, mime, id) {
    if (id) return this.g(`${UPLOAD}/${id}?uploadType=media`, { method: 'PATCH', headers: { 'Content-Type': mime }, body: blob });
    const b = 'syzy' + Date.now(), meta = { name, parents: ['appDataFolder'] };
    const body = new Blob([`--${b}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n${JSON.stringify(meta)}\r\n--${b}\r\nContent-Type: ${mime}\r\n\r\n`, blob, `\r\n--${b}--`]);
    return this.g(`${UPLOAD}?uploadType=multipart`, { method: 'POST', headers: { 'Content-Type': `multipart/related; boundary=${b}` }, body });
  },
  get(id) { return this.g(`${DRIVE}/${id}?alt=media`); },
  // the book: our own copy first, else the one Shūjià keeps (its library list names each book file)
  async findBook(files) {
    const own = files.find(f => f.name === 'syzy-longtang.epub');
    if (own) return { blob: await (await this.get(own.id)).blob(), from: 'Sy-zy' };
    const st = files.find(f => f.name === 'shujia-state.json');
    if (!st) return null;
    const state = await (await this.get(st.id)).json();
    const b = Object.values(state.books || {}).find(x => x && /弄堂/.test(x.title || '') && x.format === 'epub');
    const f = b && files.find(x => x.name === `book-${b.id}.epub`);
    return f ? { blob: await (await this.get(f.id)).blob(), from: '书架 Shūjià' } : null;
  },
  // progress: merged both ways (earliest finish dates, most advanced review boxes, every study day, every book note)
  local() { const o = {}; SYNC_KEYS.forEach(k => o[k] = store.get(k, k === 'days' ? [] : {})); return o; },
  merge(a, b) {
    const o = { doneAt: { ...b.doneAt }, readAt: { ...b.readAt }, deck: { ...b.deck }, bookNotes: { ...b.bookNotes }, days: [...new Set([...(a.days || []), ...(b.days || [])])].sort() };
    for (const k of ['doneAt', 'readAt']) Object.entries(a[k] || {}).forEach(([n, d]) => { if (!(n in o[k]) || (d && (!o[k][n] || d < o[k][n]))) o[k][n] = d; });
    Object.entries(a.deck || {}).forEach(([id, v]) => { const r = o.deck[id]; if (!r || v.box > r.box || (v.box === r.box && v.due > r.due)) o.deck[id] = v; });
    Object.entries(a.bookNotes || {}).forEach(([id, v]) => { const r = o.bookNotes[id]; if (!r || (v.at || '') >= (r.at || '')) o.bookNotes[id] = v; });
    o.lists = JSON.parse(JSON.stringify(b.lists || {}));
    const keep = lists; lists = o.lists; mergeLists(a.lists); lists = keep;   // mergeLists works on the global: borrow it
    return o;
  },
  dirty() { if (!HOSTED || !this.enabled() || this.busy) return; clearTimeout(this.timer); this.timer = setTimeout(() => this.run(false).catch(() => {}), 15000); },
  async run(interactive) {
    if (this.busy) return; this.busy = true; clearTimeout(this.timer);
    try {
      if (!this.token()) { if (!interactive) { this.status = 'Sign in again to sync'; return; } await this.login(); }
      this.status = 'Syncing…'; paintSync();
      const files = await this.list(), sf = files.find(f => f.name === 'syzy-state.json');
      const remote = sf ? await (await this.get(sf.id)).json() : {};
      const merged = this.merge(this.local(), remote);
      applyProgress(merged);
      await this.put('syzy-state.json', new Blob([JSON.stringify(merged)], { type: 'application/json' }), 'application/json', sf && sf.id);
      const pf = files.find(f => f.name === 'syzy-longtang-pack.json');
      if (pf && !hasTranslations()) { const pk = await (await this.get(pf.id)).json(); applyPack(pk); store.set('pack:longtang', pk); }
      else if (!pf && hasTranslations() && store.get('pack:longtang', null)) await this.savePack(store.get('pack:longtang', null), files);
      if (!BOOK) { const got = await this.findBook(files); if (got) { await loadBookBlob(got.blob); toast(`Book found in your Drive (${got.from})`); } }
      this.status = 'Synced ' + new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
    } catch (err) { this.status = err.message || 'Sync failed'; if (interactive) throw err; }
    finally { this.busy = false; paintSync(); }
  },
  async savePack(pk, files) {
    if (!HOSTED || !this.token() || !pk) return false;
    files = files || await this.list(); const f = files.find(x => x.name === 'syzy-longtang-pack.json');
    await this.put('syzy-longtang-pack.json', new Blob([JSON.stringify(pk)], { type: 'application/json' }), 'application/json', f && f.id);
    return true;
  },
  async saveBook(blob) {
    if (!HOSTED || !this.token()) return false;
    const files = await this.list(); const f = files.find(x => x.name === 'syzy-longtang.epub');
    if (!f) await this.put('syzy-longtang.epub', blob, 'application/epub+zip');
    return true;
  },
};
function applyProgress(m) {
  Object.assign(doneAt, m.doneAt); Object.keys(m.doneAt).forEach(k => done.add(+k));
  Object.assign(deck, m.deck); Object.assign(bookNotes, m.bookNotes); m.days.forEach(d => studyDays.add(d));
  if (m.lists) { mergeLists(m.lists); store.set('lists', lists); }
  store.set('doneAt', doneAt); store.set('deck', deck); store.set('bookNotes', bookNotes); store.set('days', [...studyDays]); store.set('readAt', m.readAt);
}
function paintSync() { const el = $('#sync-status'); if (el) el.textContent = Sync.status; }

// ---- claude.ai: the viewer's Google Drive connector
const GD = 'Google Drive';
let MCP = null;
const mcpReady = (window.claude && window.claude.use ? window.claude.use('mcp').catch(() => null) : Promise.resolve(null)).then(m => (MCP = m));
// connector answers come in several shapes: dig out what we need without assuming one
function findFiles(x, out = []) {
  if (!x || typeof x !== 'object') return out;
  if (Array.isArray(x)) { x.forEach(v => findFiles(v, out)); return out; }
  if (typeof x.id === 'string' && (x.title || x.name)) out.push({ id: x.id, title: x.title || x.name, mime: x.mimeType || '' });
  Object.values(x).forEach(v => findFiles(v, out));
  return out;
}
function findBase64(x) {
  let best = '';
  const walk = v => { if (typeof v === 'string') { if (v.length > best.length && /^[A-Za-z0-9+/=\s_-]+$/.test(v.slice(0, 2000))) best = v; } else if (v && typeof v === 'object') Object.values(v).forEach(walk); };
  walk(x); return best;
}
const b64ToBlob = s => { const bin = atob(s.replace(/\s+/g, '').replace(/-/g, '+').replace(/_/g, '/')); const a = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i); return new Blob([a], { type: 'application/epub+zip' }); };
function mcpMessage(err) {
  const c = err && err.code;
  if (c === 'server_not_connected' || c === 'selection_required') return 'Add the Google Drive connector in claude.ai Settings → Connectors, then try again.';
  if (c === 'needs_reauth') return 'Reconnect Google Drive in claude.ai Settings → Connectors.';
  if (c === 'not_in_manifest' || c === 'approval_required' || c === 'consent_required') return 'Google Drive is not allowed for this page. Allow it when asked, then try again.';
  if (c === 'blocked_by_policy') return 'Your organisation does not allow Google Drive here.';
  if (c === 'server_unavailable') return 'Google Drive did not answer. Try again in a moment.';
  if (c === 'tool_error') return 'Google Drive refused: ' + (err.message || 'unknown reason');
  return (err && err.message) || 'Google Drive could not be reached.';
}
async function driveFindBook() {
  const r = await MCP.callTool(GD, 'search_files', { query: "title contains '弄堂' and mimeType = 'application/epub+zip'", excludeContentSnippets: true, pageSize: 10 });
  const f = findFiles(r.payload ?? r)[0];
  if (!f) return null;
  const d = await MCP.callTool(GD, 'download_file_content', { fileId: f.id });
  const b64 = findBase64(d.payload ?? d);
  if (!b64) throw new Error('Google Drive sent the file in a form this page cannot read.');
  return b64ToBlob(b64);
}
async function driveSaveBook(blob) {
  const lt = await MCP.listTools().catch(() => ({}));
  if (!lt.fileArgs) throw new Error('This view cannot send a file to Google Drive. Upload the .epub to your Drive yourself, then use "Find it in my Drive".');
  await MCP.callTool(GD, 'create_file', { title: '弄堂 (Sy-zy).epub', contentMimeType: 'application/epub+zip', disableConversionToGoogleType: true,
    base64Content: { $file: { data: blob, name: 'longtang.epub', type: 'application/epub+zip' } } });
}

// one entry point for both routes: turn an epub blob into the book
async function loadBookBlob(blob) {
  const chs = await readEpub(blob);
  const hits = RB.chapters.filter(c => chs.some(b => b.head.startsWith(c.head))).length;
  if (!hits) throw new Error('No chapter of 《弄堂》 found in this file.');
  BOOK = chs; store.set(BOOK_KEY, chs);
  return hits;
}
// the Drive block on the Read page
function driveBlock() {
  if (HOSTED) {
    const on = Sync.enabled();
    return `<div class="drive"><b>Google Drive</b>
      <span class="sub" style="font-size:.88rem">${on ? 'Your progress and the book follow you on every device. The book is also found if you imported it in 书架 Shūjià.' : 'Sign in once: the app finds the book in your Drive (also the copy in 书架 Shūjià) and keeps your progress in step on every device. It uses the hidden app folder, the same one as Shūjià.'}</span>
      <div class="row">${on ? '<button class="btn small" id="sy-run">Sync now</button><button class="btn small quiet" id="sy-off">Disconnect</button>' : '<button class="btn small" id="sy-on">Connect Google Drive</button>'}<span class="sub" id="sync-status" style="font-size:.85rem">${esc(Sync.status)}</span></div></div>`;
  }
  if (!MCP) return '';
  return `<div class="drive"><b>Google Drive</b>
    <span class="sub" style="font-size:.88rem">Keep the book in your Google Drive and open it from there on any device, through your Google Drive connector.</span>
    <div class="row"><button class="btn small" id="gd-find">Find it in my Drive</button>${BOOK && store.get('bookBlobKept', false) === false ? '' : ''}<span class="sub" id="gd-msg" style="font-size:.85rem"></span></div></div>`;
}
function wireDrive(m, rerender) {
  const msg = t => { const el = $('#gd-msg', m) || $('#sync-status', m); if (el) el.textContent = t; };
  const on = $('#sy-on', m), run = $('#sy-run', m), off = $('#sy-off', m), find = $('#gd-find', m);
  if (on) on.onclick = async () => { try { await Sync.run(true); rerender(); } catch (e) { msg(e.message); } };
  if (run) run.onclick = async () => { try { await Sync.run(true); rerender(); } catch (e) { msg(e.message); } };
  if (off) off.onclick = () => { Sync.logout(); rerender(); };
  if (find) find.onclick = async () => {
    msg('Looking in your Drive…'); find.disabled = true;
    try { const blob = await driveFindBook(); if (!blob) { msg('No 弄堂 .epub in your Drive yet. Load your copy below: the app can then save it to your Drive.'); return; } const n = await loadBookBlob(blob); toast(`Book loaded from your Drive · ${n} chapters`); rerender(); }
    catch (e) { msg(e.code ? mcpMessage(e) : e.message); }
    finally { find.disabled = false; }
  };
}
// after a manual load: offer to keep the file in Drive (claude.ai), or keep it automatically (hosted)
async function afterManualLoad(file, m) {
  if (HOSTED) { try { if (await Sync.saveBook(file)) toast('Book saved to your Drive app folder'); } catch {} return; }
  if (!MCP) return;
  const el = $('#bk-msg', m); if (!el) return;
  el.className = 'fb'; el.innerHTML = '<button class="btn small line" id="gd-save">Also keep it in my Google Drive</button>';
  $('#gd-save', m).onclick = async () => { el.textContent = 'Saving to your Drive…'; try { await driveSaveBook(file); el.textContent = '✓ Saved in your Drive as “弄堂 (Sy-zy).epub”.'; } catch (e) { el.className = 'fb no'; el.textContent = e.code ? mcpMessage(e) : e.message; } };
}
// every saved change to progress schedules a sync (hosted, signed in)
const _set = store.set.bind(store);
store.set = (k, v) => { _set(k, v); if (SYNC_KEYS.includes(k) && typeof Sync !== 'undefined') Sync.dirty(); };
if (HOSTED) {
  if ('serviceWorker' in navigator && location.protocol === 'https:') navigator.serviceWorker.register('sw.js').catch(() => {});
  if (Sync.enabled()) setTimeout(() => Sync.run(false).catch(() => {}), 1500);
}
mcpReady.then(m => { if (m && location.hash === '#read') showLibrary(); });
