/* Service Worker der Frieda-App (Issue #21, Entscheidung A vom 2.11.2026): Scope „/“ auf Friedas Adresse, installiert von
 * „Mein Konto“ (engine/app/konto.js). Er zeigt nur Push-Nachrichten und öffnet beim Tippen die Stelle.
 *  - Kein fetch-Handler: Er liegt über /anmelden, /authorize, /konto und /mcp und darf keine Anfrage abfangen oder
 *    speichern. „Mein Konto“ bleibt ohne Offline-Speicher (Entscheidung #41); Kontodaten liegen nicht auf dem Gerät.
 *  - Die Reiseseiten haben ihren eigenen Worker mit engerem Scope (/<reise>-<token>/); der Browser nimmt für sie den.
 *  - Nachricht: {titel, text, url, tag} wie beim Worker der Reiseseite (engine/sw.vorlage.js, engine/push.py).
 */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", event => event.waitUntil(self.clients.claim()));

self.addEventListener("push", event => {
  let d = {};
  try { d = event.data ? event.data.json() : {}; } catch (e) { d = {text: event.data ? event.data.text() : ""}; }
  // iOS verlangt zu jedem Push eine sichtbare Nachricht; ohne Inhalt steht der Name der App da
  event.waitUntil(self.registration.showNotification(d.titel || "Frieda", {
    body: d.text || "", tag: d.tag || "frieda", renotify: true, icon: "/icon-192.png", badge: "/icon-192.png",
    data: {url: d.url || "/konto"}}));
});

self.addEventListener("notificationclick", event => {
  event.notification.close();
  const ziel = new URL((event.notification.data && event.notification.data.url) || "/konto", self.location.origin);
  event.waitUntil((async () => {
    // Ein offenes Fenster der App übernimmt (kein zweites). navigate geht nur bei Fenstern, die dieser Worker steuert;
    // eine Reiseseite gehört ihrem eigenen Worker, dann öffnet sich die Stelle neu. Fremde Adressen: neues Fenster.
    if (ziel.origin === self.location.origin) {
      const fenster = await self.clients.matchAll({type: "window", includeUncontrolled: true});
      const gleich = fenster.find(c => c.url === ziel.href);
      if (gleich) {
        try { return await gleich.focus(); } catch (e) {}
      }
      for (const c of fenster) {
        try { const neu = await c.navigate(ziel.href); if (neu) return neu.focus(); } catch (e) {}
      }
    }
    return self.clients.openWindow(ziel.href);
  })());
});
