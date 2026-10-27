const CACHE = "pycode-v1";
const BASICOS = ["/", "/manifest.webmanifest", "/icone-192.png", "/icone-512.png"];

function guardar(pedido, resposta) {
  if (resposta && resposta.ok) {
    const copia = resposta.clone();
    caches.open(CACHE).then((c) => c.put(pedido, copia));
  }
  return resposta;
}

self.addEventListener("install", (evento) => {
  self.skipWaiting();
  evento.waitUntil(caches.open(CACHE).then((c) => c.addAll(BASICOS)).catch(() => {}));
});

self.addEventListener("activate", (evento) => evento.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (evento) => {
  const url = new URL(evento.request.url);
  if (evento.request.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) return;
  if (url.pathname.startsWith("/libs/")) {
    evento.respondWith(caches.match(evento.request).then((r) => r || fetch(evento.request).then((resp) => guardar(evento.request, resp))));
    return;
  }
  evento.respondWith(
    fetch(evento.request)
      .then((resp) => guardar(evento.request, resp))
      .catch(() => caches.match(evento.request).then((r) => r || caches.match("/")))
  );
});
