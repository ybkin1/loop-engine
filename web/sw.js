/* NordRelay Mobile — Service Worker（PWA 离线壳 + 缓存） */
const CACHE = 'nrmobile-v1';
const ASSETS = ['./', './index.html', './app.js', './api.js', './style.css', './manifest.json', './icon.svg'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  // API/SSE 请求永不缓存；静态资源走 cache-first
  if (e.request.url.includes('/api/') || e.request.url.includes('/events')) {
    return;
  }
  e.respondWith(
    caches.match(e.request).then((hit) => hit || fetch(e.request))
  );
});
