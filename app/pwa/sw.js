// 书橱 Sy-zy service worker: the app opens offline once it has been opened online
const V = 'syzy-4';
const CORE = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png'];
const STATIC = 'syzy-static-1';
self.addEventListener('install', e => { e.waitUntil(caches.open(V).then(c => c.addAll(CORE))); self.skipWaiting(); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V && k !== STATIC).map(k => caches.delete(k))))); self.clients.claim(); });
const cacheFirst = async req => { const c = await caches.open(STATIC); const hit = await c.match(req); if (hit) return hit; const r = await fetch(req); if (r.ok || r.type === 'opaque') c.put(req, r.clone()); return r; };
self.addEventListener('fetch', e => {
  const req = e.request; if (req.method !== 'GET') return;
  const u = new URL(req.url);
  // dialogue audio: the file name carries a version (?v=hash), so cache-first is safe and works offline
  if (u.origin === location.origin && u.pathname.includes('/audio/')) { e.respondWith(cacheFirst(req)); return; }
  if (u.origin === location.origin) {
    // the app page: network first, so updates show at once; the cached copy when offline
    e.respondWith(caches.open(V).then(async c => { try { const r = await fetch(req, { cache: 'no-cache' }); if (r.ok) c.put(req, r.clone()); return r; } catch { return (await c.match(req)) || (await c.match('index.html')); } }));
    return;
  }
  if (u.hostname === 'fonts.googleapis.com' || u.hostname === 'fonts.gstatic.com') e.respondWith(cacheFirst(req));
});
