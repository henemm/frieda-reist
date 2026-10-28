/* Service Worker einer Reise-Seite (Issue #6). Erzeugt von engine/bauen.py aus engine/sw.vorlage.js.
 *
 * Bewährtes Muster für Service Worker, mit diesen Lehren:
 *  - Liegt unter /<reise>-<token>/sw.js, Scope ist genau dieser Pfad.
 *  - Seite, Daten und alle Bilder werden bei der Installation vorab gespeichert, damit das
 *    Handbuch unterwegs ohne Netz vollständig ist (Karten, Höhenprofile).
 *  - /api/ (Rückmeldungen) geht nie über den Speicher; ohne Netz sammelt die Seite selbst.
 *  - Eine neue Version wartet, bis man auf der Seite „Aktualisieren“ tippt. Sofortiges Übernehmen
 *    tauscht die Daten unter einer laufenden Seite aus.
 *  - Ein Update, das nicht vollständig geladen wurde (Funkloch), wird verworfen; die alte,
 *    vollständige Version bleibt.
 *  - Mehrere Reisen teilen sich eine Domain; jede räumt nur ihre eigenen Speicher auf.
 *  - Die Offline-Grundkarte (grundkarte.pmtiles, einige 10 MB) wird ganz gespeichert; Bereichsanfragen
 *    der Karte beantwortet der Worker aus dieser Kopie (bereich()).
 */
const VERSION = "__VERSION__";
const DATEIEN = __DATEIEN__;
const STAND = __STAND__;  // Datei -> Inhalts-Hash; gespeichert wird unter „Datei?v=Hash“
const UMZUG = __UMZUG__;  // null oder neue Adresse (Ursprung): Die Seiten sind umgezogen, dieser Worker räumt nur noch auf

const scope = new URL("./", self.location).pathname;
const PREFIX = "rh:" + scope + ":";
const SPEICHER = PREFIX + VERSION;

self.addEventListener("install", event => {
  if (UMZUG) { self.skipWaiting(); return; }  // nichts vorab speichern, sofort übernehmen
  event.waitUntil((async () => {
    const cache = await caches.open(SPEICHER);
    let fehlt = 0;
    // Einzeln statt cache.addAll: addAll bricht bei einer fehlenden Datei alles ab.
    // Höchstens 6 gleichzeitig, damit ein schwaches Netz nicht an 40 Bildern auf einmal hängt.
    // Unveränderte Dateien (gleicher Hash) aus den bisherigen Speichern dieser Reise übernehmen, nicht neu laden:
    // sonst lädt jede Aktualisierung des Texts auch alle Grundkarten (rund 100 MB) erneut (Issue #64).
    const alt = [];
    for (const name of await caches.keys()) if (name.startsWith(PREFIX) && name !== SPEICHER) alt.push(await caches.open(name));
    const offen = DATEIEN.map(f => [scope + f, `${scope}${f}?v=${STAND[f]}`]);
    async function arbeiter() {
      while (offen.length) {
        const [url, schluessel] = offen.shift();
        try {
          let r = null;
          for (const c of alt) if ((r = await c.match(schluessel))) break;
          if (!r) r = await fetch(url, {cache: "reload"});
          if (r.ok) await cache.put(schluessel, r); else fehlt++;
        } catch (e) { fehlt++; }
      }
    }
    await Promise.all(Array.from({length: 6}, arbeiter));
    // Erstinstallation: lieber teilweise als gar nicht (der Rest füllt sich beim Lesen).
    // Update: unvollständig heißt verwerfen, die laufende Version bleibt.
    if (fehlt && self.registration.active) {
      await caches.delete(SPEICHER);
      throw new Error(`${SPEICHER}: ${fehlt} Datei(en) nicht geladen, alte Version bleibt`);
    }
  })());
});

self.addEventListener("message", event => {
  if (event.data && event.data.typ === "version") event.ports[0] && event.ports[0].postMessage(VERSION);
  if (event.data && event.data.typ === "uebernehmen") self.skipWaiting();
});

/* Umzug: gespeicherte Seiten verwerfen und den Worker abmelden. Ein Worker darf Fenster nicht auf eine andere Domain
   schicken (Client.navigate nur im selben Ursprung); das übernimmt die frisch geladene Seite (bauen.py, Kopf von index.html).
   Dass die Fenster neu laden, löst der Wechsel des Workers aus (controllerchange in vorlage.html). */
async function umziehen() {
  for (const name of await caches.keys()) if (name.startsWith(PREFIX)) await caches.delete(name);
  await self.registration.unregister();
}

self.addEventListener("activate", event => {
  if (UMZUG) { event.waitUntil(umziehen()); return; }
  event.waitUntil((async () => {
    for (const name of await caches.keys()) {
      if (name.startsWith(PREFIX) && name !== SPEICHER) await caches.delete(name);
    }
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", event => {
  if (UMZUG) return;
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin || !url.pathname.startsWith(scope)) return;
  if (url.pathname.startsWith(scope + "api/") || url.pathname === scope + "sw.js") return;
  event.respondWith(req.headers.has("range") ? bereich(req) : ausSpeicher(req));
});

/* Bereichsanfragen (Offline-Grundkarte, PMTiles): die Karte liest nur die Stücke, die sie braucht.
   Gespeichert ist die ganze Datei; das gewünschte Stück wird daraus geschnitten (206). */
let GANZ = null;  // [url, Blob, Kopfzeilen] der zuletzt gelesenen Datei
async function bereich(req) {
  const url = new URL(req.url).pathname;
  if (!GANZ || GANZ[0] !== url) {
    const cache = await caches.open(SPEICHER);
    const r = await cache.match(url, {ignoreSearch: true});
    if (!r) return fetch(req);  // noch nicht gespeichert: direkt vom Server (der kann Bereiche selbst)
    GANZ = [url, await r.blob(), r.headers];
  }
  const [, blob, kopf] = GANZ;
  const m = /^bytes=(\d*)-(\d*)$/.exec((req.headers.get("range") || "").trim());
  if (!m || (!m[1] && !m[2])) return new Response(blob, {status: 200, headers: {"Content-Type": kopf.get("Content-Type") || "application/octet-stream"}});
  let start = m[1] ? +m[1] : Math.max(0, blob.size - +m[2]);
  let ende = m[1] && m[2] ? Math.min(+m[2], blob.size - 1) : blob.size - 1;
  if (start >= blob.size || start > ende) return new Response(null, {status: 416, headers: {"Content-Range": `bytes */${blob.size}`}});
  const h = {"Content-Range": `bytes ${start}-${ende}/${blob.size}`, "Content-Length": String(ende - start + 1),
             "Content-Type": kopf.get("Content-Type") || "application/octet-stream", "Accept-Ranges": "bytes"};
  if (kopf.get("ETag")) h.ETag = kopf.get("ETag");
  return new Response(blob.slice(start, ende + 1), {status: 206, statusText: "Partial Content", headers: h});
}

/* Zuerst aus dem Speicher; was fehlt, aus dem Netz (und merken). Ohne Netz: Seite statt Fehler. */
async function ausSpeicher(req) {
  const cache = await caches.open(SPEICHER);
  const treffer = await cache.match(req, {ignoreSearch: true});
  if (treffer) return treffer;
  try {
    const r = await fetch(req);
    if (r.ok && r.status !== 206 && r.type === "basic") cache.put(req, r.clone());
    return r;
  } catch (e) {
    if (req.mode === "navigate") {
      const seite = await cache.match(scope + "index.html", {ignoreSearch: true}) || await cache.match(scope, {ignoreSearch: true});
      if (seite) return seite;
    }
    throw e;
  }
}
