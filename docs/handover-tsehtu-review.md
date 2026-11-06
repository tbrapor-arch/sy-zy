# Handover: fixes from the Tsheh-tû code review (6 Nov 2026)

Tsheh-tû (Taigi) had a full review on 6 Nov 2026: commit `0f32402` in `tbrapor-arch/tsehtu`
(`app/index.template.html`, `app/pwa/sw.js`, `tools/build_app.py`). Sy-zy shares most of that code, and the same
problems were found in Sy-zy's `main` (commit of 6 Nov, "Lesson audio: synthetic Shanghainese") when this note was
written. **Apply each fix below during Sy-zy's next code review**, checking first that the code still looks as quoted.
Tick the box and note the commit when done.

Copy the Tsheh-tû code when in doubt: it is tested (17 behaviour checks with a faked GitHub API, the full
`tools/smoke.py` run, and the private module loaded on the new page).

---

## 1. Sync: Undo of a finished lesson does not stick (bug, user-visible) ☐

**Where:** `app/src/sync.js` `mergeProgress`, `app/src/app.js` around lines 447–448 (finish block: `#mark`, `#undo`).

**Problem:** `mergeProgress` takes the union of `doneAt`. Undo deletes the lesson locally, then the next sync (4 s later)
pulls the gist, which still has it, and puts it back. Undo is impossible while sync is on. Reproduced on Tsheh-tû.

**Fix (as in Tsheh-tû):** a timestamped mark per lesson, like the word lists already use (`+time` done, `-time` undone);
on merge the later change wins.
- New synced store key `marks` (add it to `SYNC_KEYS`, `progressData()`, `saveDone()`).
- Mark done / undo only through one function:
  ```js
  const marks = store.get('marks', {});
  function setDone(id, on) {
    if (on) { doneAt[id] = today(); done.add(id); } else { delete doneAt[id]; done.delete(id); }
    marks['d' + id] = on ? Date.now() : -Date.now(); saveDone();
  }
  ```
- In `mergeProgress`, before the `doneAt` union merge the marks, and after it apply the undone ones:
  ```js
  Object.entries(d.marks || {}).forEach(([k, t]) => { if (Math.abs(t) > Math.abs(marks[k] || 0)) marks[k] = t; });
  // … existing doneAt union …
  Object.entries(marks).forEach(([k, t]) => { if (t < 0 && k[0] === 'd') { delete doneAt[k.slice(1)]; done.delete(+k.slice(1)); } });
  ```
  A copy without marks (old app version, old progress file) counts as older than any Undo.
- Sy-zy only: decide whether `bookRead` (same union-earliest-date rule) needs the same treatment if it can be undone.

## 2. Sync: a change made while a sync is running is lost (bug) ☐

**Where:** `app/src/sync.js`, `Sync.soon()` and `Sync.run()`.

**Problem:** `soon()` returns when `busy`. Marking a lesson done during the 1–2 s of a sync is never pushed (until the
next change). Careful with the obvious fix: `mergeProgress` saves through `_set` today, but if any merge path ever goes
through `store.set`, a "re-run if busy" flag turns into an endless sync every 4 s.

**Fix:** `soon()` sets `this.again = true` when busy; `run()` calls `soon()` again after `finally` if `again` is set;
`pull()` sets `this.merging = true` around `mergeProgress` and `soon()` ignores calls while merging. `run()` also clears
a pending timer when it starts.

## 3. Sync: the page is redrawn after every startup sync (bug) ☐

**Where:** last lines of `app/src/sync.js` (`if (Sync.on) setTimeout(() => Sync.run(true).then(() => { … route() … }))`).

**Problem:** the current page is rebuilt even when nothing came from the gist: revealed English hidden again, and on a
video page the YouTube player is destroyed and reloaded.

**Fix:** `pull()` compares a snapshot of `progressData()` (without `at`) before and after the merge and returns whether
it changed; `run()` returns that. Redraw only if true, never during a card session, and on video pages redraw only the
tab bar:
```js
function refreshAfterSync() {
  if (sess) return;
  if (/^vid-/.test(location.hash.slice(1))) return renderTabs(currentTab());   // adapt to Sy-zy's video routes
  const y = scrollY; route.keepSheet = true; route(); route.keepSheet = false; scrollTo(0, y);
}
if (Sync.on) Sync.run(true).then(ch => { if (ch) refreshAfterSync(); });
```

## 4. Sync when the installed app comes back (improvement) ☐

The installed app can stay open for days and never pull another device's progress. Tsheh-tû now does:
```js
document.addEventListener('visibilitychange', () => {
  if (!Sync.on) return;
  if (document.visibilityState === 'hidden') { if (Sync.timer) Sync.run(true); return; }   // send a pending change
  if (Date.now() - store.get('syncAt', 0) > 120e3) Sync.run(true).then(ch => { if (ch) refreshAfterSync(); });
});
```
Also in `pull()`: check `r.ok` on the `raw_url` fetch of a truncated gist before reading it.

## 5. Faster start: course data as JSON (performance) ☐

**Where:** `tools/build_app.py`, the `<script>{data}{js}</script>` block (around line 87).

**Problem:** the data is written as a JavaScript object inside the script. For several MB, `JSON.parse` of a JSON block
is much faster than parsing the same object as code. Tsheh-tû (11.6 MB page): startup 760 → 460 ms on desktop (−40 %).
Check Sy-zy's page size first: the gain only matters above ~1 MB.

**Fix:**
```html
<script type="application/json" id="app-data">{payload}</script>
<script>
const DATA = JSON.parse(document.getElementById('app-data').textContent);
{js}
</script>
```
with `payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')` (valid JSON; nothing can close the block).
`tools/site.py` hashes only bare `<script>` tags for the CSP, so the JSON block needs no hash (it is not run). Check that
nothing else reads `const DATA = …` out of the HTML (in Tsheh-tû: nothing; `smoke.py` uses `page.evaluate('DATA…')`,
which still works).

## 6. Service worker (bugs) ☐

**Where:** `app/pwa/sw.js`.
- **Audio + range requests:** `cacheFirst` stores whatever `fetch(req)` returns. Audio elements send `Range` requests,
  the reply is a `206`, and `cache.put` of a 206 throws: nothing is cached, and Safari (iPhone) plays audio from the
  service worker only from 206 range replies. Tsheh-tû now fetches the file whole (no Range), caches it under its URL, and
  answers the range asked by slicing it (`ranged()` in Tsheh-tû's `app/pwa/sw.js`, copy it as is).
- **Navigations:** every same-origin page is cached under its own request, which is fine here (unlike Tsheh-tû, where
  `record.html` replaced the app's offline copy), but `cache.put` runs after the response is returned without
  `e.waitUntil`: wrap it so the browser does not stop the worker before the copy is written.
- Use `r.status === 200` rather than `r.ok` before caching (206 is "ok").

## 7. Smaller fixes ☐

- **Biased shuffles:** `.sort(() => Math.random() - .5)` in `app/src/app.js` (review queue ~706, bridge ~813 and ~815)
  favours some orders. Use a Fisher–Yates `shuffle(a)` helper (Tsheh-tû: global `shuffle`, top of the script).
- **IntersectionObserver leak** (`app/src/app.js` ~208, video player): a new observer per page visit, never disconnected.
  Keep one in a module variable, `disconnect()` it before creating the next and when `!root.isConnected`.
- **Adding a word from a lesson redraws the whole lesson** (`rerenderCurrent()` after the card's add button, ~567): this
  hides the English lines already revealed. Tsheh-tû now updates the new-word chips in place (`markListed()`: toggle the
  chip class, update the "N of M" count with an id on its span). In Sy-zy the chips show deck membership
  (`CARDS && deck[id]`): adapt.
- **`play()` without `.catch`** anywhere outside line 424: an unhandled rejection offline. Add `.catch(() => toast(…))`.

---

## How Tsheh-tû tested it (reuse for Sy-zy)
- `tools/smoke.py` full run on the new build (clicks every token of every lesson).
- A behaviour script with Playwright: site served on `127.0.0.1`, `api.github.com` faked by `context.route` (a gist kept
  in memory, an optional delay to make a sync slow), checking: undo survives sync + reload; a copy without marks does not
  bring an undone lesson back; a newer mark on another device wins; a change made during a slow sync reaches the gist;
  no endless pushes; revealed English stays after adding a word; the video page is not rebuilt by a sync; the shuffle is
  fair (60,000 shuffles of 3 items); the service worker answers `Range: bytes=256-511` with a correct 206 from the cache.
- Timing: `performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd`, median of 5 loads, before and after.
