const CACHE_NAME = "lifesource-static-v1";
const STATIC_ASSETS = [
  "/static/icons/lifesource.svg"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  const url = new URL(event.request.url);

  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(event.request).then((cached) =>
        cached || fetch(event.request).then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return response;
        })
      )
    );
    return;
  }

  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(() =>
        new Response(
          "<!doctype html><title>LifeSource Offline</title><meta name='viewport' content='width=device-width,initial-scale=1'><body style='font-family:-apple-system,BlinkMacSystemFont,sans-serif;padding:2rem;background:#faf9f7;color:#1c1917'><h1>LifeSource is offline</h1><p>Reconnect to your local server on the same Wi-Fi network.</p></body>",
          { headers: { "content-type": "text/html; charset=utf-8" } }
        )
      )
    );
  }
});
