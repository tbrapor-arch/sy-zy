// ---------- optional private module (same contract as Tsheh-tû's). Nothing of it is in this public page: the Books tab
// and the Book course appear only on a device whose GitHub token can read the owner's private repo; the module's code
// and content come from there. Contract: module/index.json lists the files with content hashes; app.css and app.js are
// fetched through GitHub's API, cached in the browser by hash (works offline), then window.ExamModule.init(loader) and
// window.ExamModule.route(hash) are called; the optional window.ExamModule.cardExtra(entry) adds a section to word cards. Routes handed to it: #books, #books-…, #bookcourse, #bookcourse-…,
// and those of any extra tab the index declares (index.tabs: [{ id, label }] → #id and #id-…).
const Module = {
  REPO: 'tbrapor-arch/syzy-private', DIR: 'module', CACHE: 'syzy-module', index: null, loaded: null,
  get token() { return Sync.token; },
  get on() { return !!this.token && store.get('moduleOn', false); },
  get bookcourse() { return this.on && !!store.get('moduleBC', false); },
  get tabs() { return this.on ? store.get('moduleTabs', []) : []; },
  tabOf(h) { const t = this.tabs.find(t => h === t.id || h.startsWith(t.id + '-')); return t ? t.id : null; },
  // is the token allowed to read the private repo? (offline: keep the last answer)
  async check() {
    if (!this.token) { store.set('moduleOn', false); return false; }
    try {
      const r = await fetch(`https://api.github.com/repos/${this.REPO}`, { headers: { Accept: 'application/vnd.github+json', Authorization: 'Bearer ' + this.token }, cache: 'no-store' });
      if (r.ok || [401, 403, 404].includes(r.status)) store.set('moduleOn', r.ok);
    } catch {}
    return this.on;
  },
  async raw(path) {
    const r = await fetch(`https://api.github.com/repos/${this.REPO}/contents/${path.split('/').map(encodeURIComponent).join('/')}?ref=main`, { headers: { Accept: 'application/vnd.github.raw', Authorization: 'Bearer ' + this.token }, cache: 'no-store' });
    if (!r.ok) throw new Error(r.status === 404 ? 'not found: ' + path : 'GitHub error ' + r.status);
    return r;
  },
  // a file of the module, kept in the browser cache under its content hash so it works offline
  async file(path) {
    const sha = this.index && this.index.files && this.index.files[path];
    const key = `https://module.invalid/${path}?${sha || 'x'}`;
    let c = null; try { c = await caches.open(this.CACHE); } catch {}
    const hit = c && sha && await c.match(key);
    if (hit) return hit;
    const r = await this.raw(this.DIR + '/' + path);
    if (c && sha) { try { await c.put(key, r.clone()); } catch {} }
    return r;
  },
  urls: {},
  async media(path) { if (!this.urls[path]) this.urls[path] = this.file(path).then(r => r.blob()).then(b => URL.createObjectURL(b)); return this.urls[path]; },
  async load() {
    if (this.loaded) return this.loaded;
    return this.loaded = (async () => {
      let c = null; try { c = await caches.open(this.CACHE); } catch {}
      try { const r = await this.raw(this.DIR + '/index.json'); this.index = await r.clone().json(); if (c) await c.put('https://module.invalid/index.json', r); }
      catch (e) { const hit = c && await c.match('https://module.invalid/index.json'); if (!hit) throw e; this.index = await hit.json(); }
      store.set('moduleBC', !!this.index.bookcourse);
      const tabs = (this.index.tabs || []).filter(t => /^[a-z][a-z0-9]*$/.test(t.id || '') && t.label).map(t => ({ id: t.id, label: String(t.label) }));
      if (JSON.stringify(tabs) !== JSON.stringify(store.get('moduleTabs', []))) {
        store.set('moduleTabs', tabs); renderTabs(currentTab());
        const h = location.hash.slice(1);   // opened on a tab this device did not know yet: show it once the module is in
        if (this.tabOf(h)) setTimeout(() => { if (location.hash.slice(1) === h) route(); }, 0);
      }
      if (!this.index.files || !this.index.files['app.js']) return;     // nothing built yet
      if (this.index.files['app.css']) { const css = document.createElement('style'); css.textContent = await (await this.file('app.css')).text(); document.head.append(css); }
      const js = await (await this.file('app.js')).text();
      await new Promise((res, rej) => { const sc = document.createElement('script'); sc.src = URL.createObjectURL(new Blob([js], { type: 'text/javascript' })); sc.onload = res; sc.onerror = rej; document.head.append(sc); });
      if (window.ExamModule) await window.ExamModule.init(this);
    })().catch(e => { this.loaded = null; throw e; });
  },
  // a section the module may add to any word card (e.g. what the owner's books say about the word); '' when off
  cardExtra(e) { try { return (this.on && window.ExamModule && window.ExamModule.cardExtra && window.ExamModule.cardExtra(e)) || ''; } catch { return ''; } },
  async show(h) {
    renderTabs(currentTab());
    const here = location.hash;
    const tab = this.tabs.find(t => t.id === this.tabOf(h));
    const [ey, ti] = /^bookcourse/.test(h) ? ['Lessons', '课本'] : tab ? [tab.label, ''] : ['Books', '书'];
    const page = body => { $('#main').innerHTML = `<div class="col"><div class="head"><span class="eyebrow">${ey}</span>${ti ? `<h1>${esc(hzt(ti))}</h1>` : ''}</div>${body}</div>`; wireGo($('#main')); };
    if (!this.on) return page('<p class="sub">Not available on this device.</p>');
    if (!window.ExamModule) page('<p class="sub">Loading…</p>');
    try {
      await this.load();
      if (location.hash !== here) return;
      if (window.ExamModule) window.ExamModule.route(h);
      else page('<div class="card"><b>Nothing here yet</b><span class="sub">The private module is connected but has no content built yet.</span></div>');
    } catch (e) { page(`<div class="card raised"><b>Could not load the private module</b><span class="sub">${esc(e.message || e)}. It needs the internet the first time; after that it works offline.</span><button class="btn small" style="align-self:start" data-go="${esc(h)}">Try again</button></div>`); }
  },
};
// at start: check (quietly) whether this device's token opens the private repo, then load the module in the background
if (Module.token) {
  const was = Module.on;
  Module.check().then(on => {
    const mine = h => /^(books|bookcourse)/.test(h) || Module.tabOf(h);
    if (on !== was) { if (mine(location.hash.slice(1))) route(); else renderTabs(currentTab()); }
    if (on && !mine(location.hash.slice(1))) Module.load().then(() => { if ((location.hash.slice(1) || 'lessons') === 'lessons') route(); else renderTabs(currentTab()); }).catch(() => {});
  });
}
