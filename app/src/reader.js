
// ---------- Read: 《弄堂》 (胡宝谈, 2011), the first novel written in Shanghainese.
// The app holds no text of the novel. The reader loads their own copy (.epub) once; it is kept in this browser.
// Each prepared chapter ships a "pack": word boundaries, the author's inline readings and an English translation,
// matched to the reader's text paragraph by paragraph through a fingerprint.
const RB = DATA.reader;
const BOOK_KEY = 'book:longtang';
let BOOK = null;                     // [{head, paras: [text]}] from the reader's epub
try { BOOK = store.get(BOOK_KEY, null); } catch { BOOK = null; }
const RPREF = Object.assign({ ruby: 'sh', en: false }, store.get('rprefs', {}));
// the public build has no translations: they come in the private study pack (loaded once, kept here and in Drive)
const hasTranslations = () => RB.chapters.some(c => c.pack && c.pack.some(p => p.en));
function applyPack(pk) {
  if (!pk || pk.app !== 'syzy-pack') throw new Error('This is not a Sy-zy study pack.');
  pk.chapters.forEach(pc => { const c = RB.chapters.find(x => x.n === pc.n); if (!c || !c.pack) return;
    if (pc.en_head) c.en_head = pc.en_head;
    pc.paras.forEach((pp, i) => { if (c.pack[i]) { if (pp.en) c.pack[i].en = pp.en; if (pp.a && Object.keys(pp.a).length) c.pack[i].a = pp.a; } }); });
}
try { const sp = store.get('pack:longtang', null); if (sp) applyPack(sp); } catch {}

function fnv(s) { let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; } return h >>> 0; }
const squash = s => s.replace(/\s+/g, '');
// the author's [readings]: removed from the text, kept against the character they follow
function cleanPara(t) {
  const ann = {}; let out = '', i = 0;
  for (const m of t.matchAll(/\[([^\]]+)\]/g)) { out += t.slice(i, m.index); const pos = out.length - 1; ann[pos] = ann[pos] ? ann[pos] + '/' + m[1] : m[1]; i = m.index + m[0].length; }
  return { text: out + t.slice(i), ann };
}
async function readEpub(file) {
  if (!window.JSZip) throw new Error('The unzip library did not load: check the connection and try again.');
  const zip = await JSZip.loadAsync(file);
  const opfName = Object.keys(zip.files).find(n => n.endsWith('.opf'));
  if (!opfName) throw new Error('This file is not an epub.');
  const opf = new DOMParser().parseFromString(await zip.file(opfName).async('string'), 'application/xml');
  const base = opfName.includes('/') ? opfName.slice(0, opfName.lastIndexOf('/') + 1) : '';
  const href = {}; opf.querySelectorAll('manifest > item').forEach(it => href[it.getAttribute('id')] = it.getAttribute('href'));
  const out = [];
  for (const ref of opf.querySelectorAll('spine > itemref')) {
    const f = zip.file(base + decodeURIComponent(href[ref.getAttribute('idref')] || ''));
    if (!f) continue;
    const doc = new DOMParser().parseFromString(await f.async('string'), 'application/xhtml+xml');
    doc.querySelectorAll('h2, p').forEach(el => {
      const t = el.textContent.trim();
      if (el.tagName.toLowerCase() === 'h2') out.push({ head: t, paras: [] });
      else if (out.length && t) out[out.length - 1].paras.push(t);
    });
  }
  return out;
}
const chapterText = n => {
  const c = RB.chapters[n - 1]; if (!BOOK || !c) return null;
  return BOOK.find(b => b.head.startsWith(c.head)) || null;
};

function showLibrary() {
  renderTabs('read');
  const prepared = RB.chapters.filter(c => c.pack), read = store.get('readAt', {});
  const letter = c => { const r = (c.rom || '').trim(); return r ? r[0].toUpperCase() : '·'; };
  const groups = {};
  RB.chapters.forEach(c => (groups[letter(c)] = groups[letter(c)] || []).push(c));
  $('#main').innerHTML = `<div class="col">
    <div class="head"><span class="eyebrow">Read</span><h1>弄堂</h1><span class="rom">${esc(RB.author)} · ${RB.year} · the first novel written in Shanghainese</span></div>
    <div class="card raised book-card">
      <p style="margin:0;max-width:62ch">Built like a dictionary: each of its ${RB.chapters.length} chapters opens on a Shanghainese expression, then tells a scene from one lane, with the same neighbours from chapter to chapter: A San, Old Uncle, Little Subei. The author marks hard readings in brackets; here they show above the characters.</p>
      ${BOOK ? `<span class="sub" style="font-size:.88rem">✓ Your copy is loaded in this browser (${BOOK.length} chapters found).</span>
        <div class="row"><button class="btn small line" id="bk-load">Load another copy</button><button class="btn small quiet" id="bk-forget">Remove it from this browser</button></div>`
      : `<span class="sub" style="font-size:.9rem">The app does not include the novel's text. Load your copy of the book (the .epub file) once: it stays in this browser and is never uploaded.</span>
        <div class="row"><button class="btn" id="bk-load">Load my copy (.epub)</button></div>`}
      <input type="file" id="bk-file" accept=".epub,application/epub+zip" hidden>
      <span class="fb" id="bk-msg" aria-live="polite"></span>
      ${hasTranslations() ? '' : `<div class="drive"><b>Study pack</b><span class="sub" style="font-size:.88rem">The English translations are not in the public app (the book is under copyright). Load your study pack file once (syzy-longtang-pack.json): it stays in this browser${HOSTED ? ' and in your Drive app folder' : ''}.</span>
        <div class="row"><button class="btn small line" id="pk-load">Load the study pack</button><input type="file" id="pk-file" accept=".json,application/json" hidden></div></div>`}
      ${driveBlock()}</div>
    <h2><span class="han">目录</span> Chapters <span class="sub" style="font-weight:600;font-size:.85rem">${prepared.length} prepared of ${RB.chapters.length}</span></h2>
    ${Object.entries(groups).map(([L, list]) => `<div class="chl"><span class="chl-l">${esc(L)}</span><div class="chl-g">${list.map(c => `<button class="chb ${c.pack ? 'ready' : ''} ${read[c.n] ? 'done' : ''}" ${c.pack ? `data-go="read-${c.n}"` : 'disabled'} aria-label="${esc(c.head)}${c.pack ? '' : ', not prepared yet'}">
        <span class="han">${esc(c.head)}</span><span class="r">${esc(c.rom)}</span>${c.en_head ? `<span class="g">${esc(c.en_head)}</span>` : ''}</button>`).join('')}</div></div>`).join('')}
    <p class="sub" style="font-size:.85rem;margin:0">Grey chapters are not prepared yet: each one needs its words checked and a translation. Spellings in grey under each title are the author's own system.</p>
  </div>`;
  const m = $('#main');
  wireGo(m); wireDrive(m, showLibrary);
  $('#bk-load', m).onclick = () => $('#bk-file', m).click();
  const pl = $('#pk-load', m); if (pl) { pl.onclick = () => $('#pk-file', m).click();
    $('#pk-file', m).onchange = async e => { const f = e.target.files[0]; if (!f) return;
      try { const pk = JSON.parse(await f.text()); applyPack(pk); store.set('pack:longtang', pk); toast('Study pack loaded'); if (HOSTED) Sync.savePack(pk).catch(() => {}); showLibrary(); }
      catch (err) { const msg = $('#bk-msg', m); msg.className = 'fb no'; msg.textContent = err.message || 'Could not read this file.'; } }; }
  const fg = $('#bk-forget', m); if (fg) fg.onclick = () => { BOOK = null; try { localStorage.removeItem('syzy:' + BOOK_KEY); } catch {} showLibrary(); };
  $('#bk-file', m).onchange = async e => {
    const f = e.target.files[0], msg = $('#bk-msg', m); if (!f) return;
    msg.className = 'fb'; msg.textContent = 'Reading the book…';
    try {
      const hits = await loadBookBlob(f);
      toast(`Book loaded · ${hits} chapters recognised`); showLibrary();
      afterManualLoad(f, $('#main'));
    } catch (err) { msg.className = 'fb no'; msg.textContent = err.message || 'Could not read this file.'; }
  };
}

// one paragraph: the reader's text cut where the pack says, each word linked to the dictionary
function paraHTML(text, pk, key) {
  const { text: t, ann } = cleanPara(text);
  if (!pk || fnv(squash(t)) !== pk.f) return { html: `<span class="unmatched" title="This paragraph differs from the prepared edition">${esc(t)}</span>`, ok: false };
  let i = 0, html = '';
  pk.s.forEach((len, k) => {
    const w = t.slice(i, i + len);
    // the author's readings inside this word
    const annIn = Object.keys(pk.a || ann).map(Number).filter(p => p >= i && p < i + len);
    if (!HAN_RE.test(w)) { html += `<span class="punct">${esc(w)}</span>`; i += len; return; }
    const id = RB.ids[w], e = id && DATA.dict[id];
    const show = RPREF.ruby === 'all' || (RPREF.ruby === 'sh' && e && (e.type === 'sh' || e.type === 'ff'));
    const tk = `${key}:${k}`; TOKS[tk] = { h: w, id };
    const cls = 'tok ' + (id ? cog(id)[2] : '');
    let inner = '';
    if (annIn.length) {
      inner = [...w].map((ch, j) => { const r = (pk.a || ann)[i + j]; return r ? `<ruby class="auth" data-ann="${esc(r)}">${esc(ch)}<rt>${esc(r)}</rt></ruby>` : esc(ch); }).join('');
      html += `<span class="${cls}" tabindex="0" role="button" data-tok="${tk}">${inner}</span>`;
    } else if (show && e && e.ipa) html += `<ruby class="${cls}" tabindex="0" role="button" data-tok="${tk}">${esc(w)}<rt>${esc(spell(e))}</rt></ruby>`;
    else html += `<span class="${cls}" tabindex="0" role="button" data-tok="${tk}">${esc(w)}</span>`;
    i += len;
  });
  return { html, ok: true };
}
const isNote = t => /^[^，。“”]{1,14}——/.test(t);
function showChapter(n) {
  renderTabs('read');
  const c = RB.chapters[n - 1];
  if (!c || !c.pack) return showLibrary();
  const src = chapterText(n), m = $('#main');
  const hid = RB.ids[c.head], he = hid && DATA.dict[hid];
  const top = `<div class="lbar"><button class="icon" data-go="read" aria-label="Back to the chapters">←</button><span class="where">弄堂 · ${esc(c.head)}</span>
      <button class="icon" data-go="read-${prevReady(n)}" aria-label="Previous chapter" ${prevReady(n) ? '' : 'disabled'}>‹</button>
      <button class="icon" data-go="read-${nextReady(n)}" aria-label="Next chapter" ${nextReady(n) ? '' : 'disabled'}>›</button></div>
    <div class="head"><span class="eyebrow">Chapter ${n} · ${esc((c.rom || '')[0] || '').toUpperCase()}</span><h1>${esc(c.head)}</h1>
      <span class="rom">${he && he.ipa ? esc(spell(he)) + ' · ' : ''}${esc(c.en_head || '')}</span>
      <span class="sub" style="font-size:.85rem">The author writes it <b>${esc(c.rom)}</b></span></div>`;
  if (!src) {
    m.innerHTML = `<div class="col">${top}<div class="card raised"><b>Load your copy of the book first</b><span class="sub">This chapter is prepared, but the app holds no text of the novel. Load your .epub once on the Read page.</span>
      <div class="row"><button class="btn" data-go="read">Go to the Read page</button></div></div></div>`;
    wireGo(m); return;
  }
  // which words to meet before reading: Shanghainese words of the chapter, in order of appearance
  const pre = [], seen = new Set();
  src.paras.forEach((p, pi) => {
    const pk = c.pack[pi]; if (!pk || isNote(p) || pi === 0) return;
    const t = cleanPara(p).text; let i = 0;
    pk.s.forEach(len => { const w = t.slice(i, i + len); i += len; const id = RB.ids[w], e = id && DATA.dict[id];
      if (e && e.type === 'sh' && !seen.has(id) && [...w].length > 1) { seen.add(id); pre.push(id); } });
  });
  const rows = src.paras.map((p, pi) => ({ p, pi, pk: c.pack[pi], kind: pi === 0 ? 'def' : isNote(p) ? 'note' : 'story' }));
  const PR = {};
  const para = r => { const { html, ok } = paraHTML(r.p, r.pk, `R${r.pi}`); PR[r.pi] = r.pk ? r.pk.en : '';
    return `<div class="rp ${r.kind}" id="rp-${r.pi}"><p class="txt rtext">${html}</p>${ok ? '' : '<span class="sub" style="font-size:.8rem">This paragraph is not the same as in the prepared edition: words are not linked.</span>'}
      ${r.pk && r.pk.en ? (RPREF.en ? `<p class="ren">${esc(r.pk.en)}</p>` : `<button class="reveal" data-ren="${r.pi}">English</button>`) : ''}</div>`; };
  m.innerHTML = `<div class="col reader">${top}
    ${rows.filter(r => r.kind === 'def').map(para).join('')}
    <details class="card prep" ${store.get('readAt', {})[n] ? '' : 'open'}><summary><span class="han">预习</span> Before you read · ${pre.length} Shanghainese words</summary>
      <p class="sub" style="margin:.4rem 0 0;font-size:.88rem">In order of appearance. Tap one for its card; words in the text open the same card.</p>
      <div class="wgrid prepgrid">${pre.map((id, k) => { const e = DATA.dict[id]; return `<button class="wchip ${cog(id)[2]} ${deck[id] ? 'indeck' : ''}" data-word="${esc(id)}" ${k >= 24 ? 'hidden' : ''}><b>${esc(H(e))}</b><span class="r">${esc(e.ipa ? spell(e) : '')}</span><span class="g">${esc(e.gloss || '')}</span></button>`; }).join('')}</div>
      <div class="row">${pre.length > 24 ? `<button class="btn small line" id="pre-more">Show all ${pre.length}</button>` : ''}<button class="btn small quiet" id="pre-add">Add these words to review</button></div></details>
    <div class="toolbar" role="toolbar" aria-label="Display">
      <div class="seg" role="group" aria-label="Spelling above">${[['sh', 'Over Shanghainese words'], ['all', 'Over every word'], ['none', 'None']].map(([k, t]) => `<button data-rr="${k}" aria-pressed="${RPREF.ruby === k}">${t}</button>`).join('')}</div>
      <div class="seg" role="group" aria-label="Spelling system">${ROMS.map(([k, t]) => `<button data-rom="${k}" aria-pressed="${prefs.rom === k}">${t}</button>`).join('')}</div>
      <label class="toggle"><input type="checkbox" id="opt-ren" ${RPREF.en ? 'checked' : ''}> English</label>
      <div class="legend"><span class="k-to">Shanghainese word</span><span class="k-auth">Author's reading</span></div></div>
    <div class="storybox">${rows.filter(r => r.kind === 'story').map(para).join('')}</div>
    <details class="allnotes" open><summary><span class="han">作者注</span> The author's notes (${rows.filter(r => r.kind === 'note').length})</summary>
      <div class="anotes">${rows.filter(r => r.kind === 'note').map(para).join('')}</div></details>
    <div class="card raised finish"><div><b>${store.get('readAt', {})[n] ? '✓ Read ' + fmtDate(store.get('readAt', {})[n]) : 'Finished the chapter?'}</b><div class="sub" style="font-size:.9rem">Translation by Claude, close to the text. Readings are from the database; the bracketed ones are the author's.</div></div>
      <div class="row">${store.get('readAt', {})[n] ? '' : '<button class="btn" id="ch-done">Mark as read</button>'}${nextReady(n) ? `<button class="btn line" data-go="read-${nextReady(n)}">Next chapter →</button>` : '<button class="btn line" data-go="read">Chapters</button>'}</div></div>
  </div>`;
  wireGo(m); wireTokens(m);
  $$('[data-word]', m).forEach(b => b.onclick = () => openCard(b.dataset.word));
  $$('[data-ren]', m).forEach(b => b.onclick = () => { const p = document.createElement('p'); p.className = 'ren'; p.textContent = PR[b.dataset.ren]; b.replaceWith(p); });
  $$('[data-rr]', m).forEach(b => b.onclick = () => { RPREF.ruby = b.dataset.rr; store.set('rprefs', RPREF); const y = scrollY; showChapter(n); scrollTo(0, y); });
  $$('[data-rom]', m).forEach(b => b.onclick = () => { prefs.rom = b.dataset.rom; store.set('prefs', prefs); const y = scrollY; showChapter(n); scrollTo(0, y); });
  $('#opt-ren', m).onchange = e => { RPREF.en = e.target.checked; store.set('rprefs', RPREF); const y = scrollY; showChapter(n); scrollTo(0, y); };
  const pm = $('#pre-more', m); if (pm) pm.onclick = () => { $$('.prepgrid [hidden]', m).forEach(b => b.hidden = false); pm.remove(); };
  $('#pre-add', m).onclick = () => { const k = addToDeck(pre); renderTabs('read'); toast(k ? `${k} words added to review` : 'Already in your deck'); };
  const dn = $('#ch-done', m); if (dn) dn.onclick = () => { const r = store.get('readAt', {}); r[n] = today(); store.set('readAt', r); studied(); showChapter(n); };
}
const readyNs = () => RB.chapters.filter(c => c.pack).map(c => c.n);
function prevReady(n) { return readyNs().filter(x => x < n).pop() || 0; }
function nextReady(n) { return readyNs().find(x => x > n) || 0; }
