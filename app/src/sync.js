// ---------- sync between devices (as in Tsheh-tû): progress kept in a secret GitHub gist that only you can list.
// One fine-grained token does both jobs: Gists read/write (sync) and Contents read on the private repo (Books tab).
// It stays in this browser. Pull + merge when the app opens, push a few seconds after any change.
const HOSTED = !!document.querySelector('link[rel=manifest]');
const SYNC_KEYS = new Set(['doneAt', 'waveAt', 'deck', 'days', 'bookNotes', 'lists', 'bookRead', 'modSync']);   // modSync: the private module's own progress, { key: { at, … } }
const _set = store.set.bind(store);
store.set = (k, v) => { _set(k, v); if (SYNC_KEYS.has(k) && typeof Sync !== 'undefined') Sync.soon(); };

function progressData() { return { app: 'syzy', v: 2, at: new Date().toISOString(), doneAt, waveAt, deck, lists, bookNotes, days: [...studyDays], bookRead: store.get('bookRead', {}), modSync: store.get('modSync', {}), last: store.get('last', null) }; }
// merge another copy into this one: earliest finish dates, the most recently reviewed card, the latest book note
function mergeProgress(d) {
  if (!d || d.app !== 'syzy') throw new Error('not a progress file');
  Object.entries(d.doneAt || {}).forEach(([k, v]) => { if (!(k in doneAt) || (v && (!doneAt[k] || v < doneAt[k]))) doneAt[k] = v; done.add(+k); });
  Object.entries(d.waveAt || {}).forEach(([k, v]) => { if (!(k in waveAt) || (v && v < waveAt[k])) waveAt[k] = v; });
  Object.entries(d.deck || {}).forEach(([k, v]) => { const m = deck[k]; if (!m || (v.at || 0) > (m.at || 0) || (!v.at && !m.at && v.box > m.box)) deck[k] = v; });
  Object.entries(d.bookNotes || {}).forEach(([k, v]) => { const r = bookNotes[k]; if (!r || (v.at || '') >= (r.at || '')) bookNotes[k] = v; });
  const br = store.get('bookRead', {}); Object.entries(d.bookRead || {}).forEach(([k, v]) => { if (!br[k] || (v && v < br[k])) br[k] = v; });
  const ms = store.get('modSync', {}); Object.entries(d.modSync || {}).forEach(([k, v]) => { if (!ms[k] || (v && (v.at || 0) > (ms[k].at || 0))) ms[k] = v; });
  (d.days || []).forEach(x => studyDays.add(x));
  if (d.lists) mergeLists(d.lists);
  saveDone(); _set('deck', deck); _set('bookNotes', bookNotes); _set('lists', lists); _set('days', [...studyDays]); _set('bookRead', br); _set('modSync', ms);
}
const Sync = {
  FILE: 'syzy-progress.json', timer: null, busy: false,
  get token() { return store.get('ghToken', ''); }, get id() { return store.get('gistId', ''); },
  get on() { return HOSTED && !!this.token && store.get('syncOn', true); },
  async api(path, opts = {}) {
    const r = await fetch('https://api.github.com' + path, { ...opts, headers: { Accept: 'application/vnd.github+json', Authorization: 'Bearer ' + this.token, ...(opts.body ? { 'Content-Type': 'application/json' } : {}) } });
    if (!r.ok) throw new Error(r.status === 401 ? 'token refused' : r.status === 403 ? 'the token has no Gists permission' : r.status === 404 ? 'not found' : 'GitHub error ' + r.status);
    return r.status === 204 ? null : r.json();
  },
  async findOrCreate() {
    if (this.id) return this.id;
    for (let page = 1; page <= 5; page++) {
      const list = await this.api(`/gists?per_page=100&page=${page}`);
      const g = list.find(x => x.files && x.files[this.FILE]);
      if (g) { _set('gistId', g.id); return g.id; }
      if (list.length < 100) break;
    }
    const g = await this.api('/gists', { method: 'POST', body: JSON.stringify({ public: false, description: '书橱 Sy-zy progress', files: { [this.FILE]: { content: JSON.stringify(progressData()) } } }) });
    _set('gistId', g.id); return g.id;
  },
  async pull() {
    const g = await this.api('/gists/' + await this.findOrCreate());
    const f = g.files[this.FILE];
    let text = f && f.content;
    if (f && f.truncated) text = await (await fetch(f.raw_url)).text();
    if (text) mergeProgress(JSON.parse(text));
  },
  async push() { await this.api('/gists/' + await this.findOrCreate(), { method: 'PATCH', body: JSON.stringify({ files: { [this.FILE]: { content: JSON.stringify(progressData()) } } }) }); },
  async run(quiet) {
    if (!this.on || this.busy) return;
    this.busy = true;
    try { await this.pull(); await this.push(); _set('syncAt', Date.now()); _set('syncErr', ''); if (!quiet) toast('Progress synced'); }
    catch (e) { _set('syncErr', String(e.message || e)); if (!quiet) toast('Sync failed: ' + (e.message || e)); }
    finally { this.busy = false; }
  },
  soon() { if (!this.on || this.busy) return; clearTimeout(this.timer); this.timer = setTimeout(() => this.run(true), 4000); },
};
// Settings › Sync and private books: one card, one token
function syncBlock() {
  if (!HOSTED) return '';
  const t = Sync.token, at = store.get('syncAt', 0), err = store.get('syncErr', '');
  return `<h2><span class="han">${esc(hzt('同步'))}</span> Sync and your books</h2>
    <div class="card">${t ? `<span>${Sync.on ? `Progress synced with your GitHub account${at ? ` · last ${new Date(at).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}` : ''}.` : 'Sync is off on this device.'}</span>
        ${err ? `<span class="fb no">Last attempt failed: ${esc(err)}</span>` : ''}
        <span>${Module.on ? '✓ Your books are on (Books tab).' : 'Books: this token cannot read the private repository.'}</span>
        <div class="row"><button class="btn small" id="sync-now">Sync now</button><button class="btn small quiet" id="sync-off">Remove the token from this device</button></div>`
      : `<span>One GitHub token keeps your progress the same on every device and opens your own books (Books tab).</span>
        <ol class="sub" style="font-size:.9rem;margin:0;padding-left:1.2rem">
          <li>GitHub › Settings › Developer settings › Personal access tokens › <b>Fine-grained tokens</b> › Generate new token.</li>
          <li>Name it <i>syzy</i>; set an expiry and note the date.</li>
          <li>Repository access: <b>Only select repositories</b> › <code>${Module.REPO}</code>; Repository permissions › <b>Contents: Read-only</b>.</li>
          <li>Account permissions › <b>Gists: Read and write</b>. Nothing else.</li>
          <li>Generate, copy, paste here on each device.</li></ol>
        <form class="row" id="sync-form"><input id="sync-token" type="password" autocomplete="off" spellcheck="false" placeholder="github_pat_…" aria-label="GitHub token" style="flex:1 1 14rem;min-width:0;font:inherit;padding:.5rem .8rem;border:1.5px solid var(--line);border-radius:var(--r);background:var(--bg);color:var(--text)">
          <button class="btn small" type="submit">Connect</button></form>
        <span class="sub" style="font-size:.8rem">The token is kept in this browser only and sent only to GitHub.</span>`}</div>`;
}
function wireSync(m, rerender) {
  const sf = $('#sync-form', m);
  if (sf) sf.onsubmit = async e => {
    e.preventDefault(); const t = $('#sync-token', m).value.trim(); if (!t) return;
    _set('ghToken', t); _set('gistId', ''); _set('syncOn', true);
    await Sync.run(true); const on = await Module.check();
    const err = store.get('syncErr', '');
    if (err && !on) { _set('ghToken', ''); toast('Token refused: ' + err); }
    else { toast(err ? 'Books connected; sync failed: ' + err : on ? 'Synced · your books are on' : 'Synced · this token cannot read your books'); if (on) Module.load().catch(() => {}); }
    rerender();
  };
  const sn = $('#sync-now', m); if (sn) sn.onclick = async () => { sn.disabled = true; await Sync.run(); await Module.check(); rerender(); };
  const so = $('#sync-off', m); if (so) so.onclick = () => { _set('ghToken', ''); _set('gistId', ''); _set('moduleOn', false); _set('moduleBC', false); toast('Token removed from this device'); rerender(); };
}
if (HOSTED && 'serviceWorker' in navigator && location.protocol === 'https:') navigator.serviceWorker.register('sw.js').catch(() => {});
// pull the other devices' progress at start, then refresh the current page (not during a card session)
if (Sync.on) setTimeout(() => Sync.run(true).then(() => { if (!sess) { const y = scrollY; route.keepSheet = true; route(); route.keepSheet = false; scrollTo(0, y); } }), 0);
