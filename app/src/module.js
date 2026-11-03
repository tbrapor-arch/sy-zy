// ---------- optional private module (same contract as Tsheh-tû's). Nothing of it is in this public page: the Books tab
// and the Book course appear only on a device whose GitHub token can read the owner's private repo; the module's code
// and content come from there. Contract: module/index.json lists the files with content hashes; app.css and app.js are
// fetched through GitHub's API, cached in the browser by hash (works offline), then window.ExamModule.init(loader) and
// window.ExamModule.route(hash) are called. Routes handed to it: #books, #books-…, #bookcourse, #bookcourse-….
const Module = {
  REPO: 'tbrapor-arch/syzy-private', DIR: 'module', CACHE: 'syzy-module', index: null, loaded: null,
  get token() { return store.get('ghToken', ''); },
  get on() { return !!this.token && store.get('moduleOn', false); },
  get bookcourse() { return this.on && !!store.get('moduleBC', false); },
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
      if (!this.index.files || !this.index.files['app.js']) return;     // nothing built yet
      if (this.index.files['app.css']) { const css = document.createElement('style'); css.textContent = await (await this.file('app.css')).text(); document.head.append(css); }
      const js = await (await this.file('app.js')).text();
      await new Promise((res, rej) => { const sc = document.createElement('script'); sc.src = URL.createObjectURL(new Blob([js], { type: 'text/javascript' })); sc.onload = res; sc.onerror = rej; document.head.append(sc); });
      if (window.ExamModule) await window.ExamModule.init(this);
    })().catch(e => { this.loaded = null; throw e; });
  },
  async show(h) {
    renderTabs(currentTab());
    const here = location.hash;
    const [ey, ti] = /^bookcourse/.test(h) ? ['Lessons', '课本'] : ['Books', '书'];
    const page = body => { $('#main').innerHTML = `<div class="col"><div class="head"><span class="eyebrow">${ey}</span><h1>${esc(hzt(ti))}</h1></div>${body}</div>`; wireGo($('#main')); };
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
// Settings › Private module: the GitHub token (fine-grained, Contents: Read on the private repo), kept in this browser
function moduleBlock() {
  const t = Module.token;
  return `<h2><span class="han">${esc(hzt('私人'))}</span> Private module</h2>
    <div class="card"><span class="sub" style="font-size:.9rem">Your own books and the book course are read from your private GitHub repository. Paste a fine-grained token with <b>Contents: Read</b> on <code>${Module.REPO}</code>. It stays in this browser and goes only to GitHub.</span>
      ${t ? `<span>${Module.on ? '✓ Connected: the Books tab is on.' : 'Token saved, but it cannot read the repository.'}</span>
        <div class="row"><button class="btn small" id="gh-check">Check again</button><button class="btn small quiet" id="gh-off">Remove token</button></div>`
      : `<form class="row" id="gh-form"><input id="gh-token" type="password" placeholder="github_pat_…" autocomplete="off" spellcheck="false" style="flex:1;min-width:14em" aria-label="GitHub token"><button class="btn small" type="submit">Connect</button></form>`}</div>`;
}
function wireModule(m, rerender) {
  const f = $('#gh-form', m), ck = $('#gh-check', m), off = $('#gh-off', m);
  const after = async () => { const on = await Module.check(); toast(on ? 'Private module connected' : 'This token cannot read the private repository'); if (on) Module.load().catch(() => {}); rerender(); };
  if (f) f.onsubmit = e => { e.preventDefault(); const v = $('#gh-token', m).value.trim(); if (!v) return; store.set('ghToken', v); after(); };
  if (ck) ck.onclick = after;
  if (off) off.onclick = () => { store.set('ghToken', ''); store.set('moduleOn', false); store.set('moduleBC', false); rerender(); };
}
// at start: check (quietly) whether this device's token opens the private repo, then load the module in the background
if (Module.token) {
  const was = Module.on;
  Module.check().then(on => {
    if (on !== was) { if (/^(books|bookcourse)/.test(location.hash.slice(1))) route(); else renderTabs(currentTab()); }
    if (on && !/^(books|bookcourse)/.test(location.hash.slice(1))) Module.load().then(() => { if ((location.hash.slice(1) || 'lessons') === 'lessons') route(); else renderTabs(currentTab()); }).catch(() => {});
  });
}
