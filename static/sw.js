// QuickFood Service Worker — Cache & Offline
const CACHE_NAME = 'quickfood-v1';
const STATIC_ASSETS = [
  '/',
  '/restaurants',
  '/static/css/style.css',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/static/images/logo.png',
];

// Installation — mise en cache des assets statiques
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activation — nettoyage ancien cache
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(k) { return k !== CACHE_NAME; })
            .map(function(k) { return caches.delete(k); })
      );
    })
  );
  self.clients.claim();
});

// Fetch — stratégie Network First, fallback cache
self.addEventListener('fetch', function(event) {
  // Ignorer les requêtes non-GET et les API externes
  if (event.request.method !== 'GET') return;
  if (event.request.url.includes('nominatim') ||
      event.request.url.includes('paydunya') ||
      event.request.url.includes('ngrok')) return;

  event.respondWith(
    fetch(event.request)
      .then(function(response) {
        // Mettre en cache les réponses réussies
        if (response && response.status === 200) {
          var clone = response.clone();
          caches.open(CACHE_NAME).then(function(cache) {
            cache.put(event.request, clone);
          });
        }
        return response;
      })
      .catch(function() {
        // Fallback cache si réseau indisponible
        return caches.match(event.request).then(function(cached) {
          if (cached) return cached;
          // Page offline générique
          return new Response(
            '<html><body style="font-family:sans-serif;text-align:center;padding:50px;">' +
            '<h2 style="color:#dc2626;">📡 Pas de connexion</h2>' +
            '<p>Reconnectez-vous pour accéder à QuickFood.</p>' +
            '</body></html>',
            { headers: { 'Content-Type': 'text/html' } }
          );
        });
      })
  );
});
