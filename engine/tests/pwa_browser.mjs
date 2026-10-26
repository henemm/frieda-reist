// Browser-Prüfung der Offline-Fähigkeit (Issue #6), aufgerufen von test_pwa.py.
// Aufruf: node pwa_browser.mjs <playwright-modul> <basis-url> <web-ordner der Reise>
// Prüft: Vorab-Speicher vollständig, Lesen ohne Netz (Seite und Bild), Update-Hinweis und
// Übernahme, verworfenes Update bei fehlender Datei.
import fs from "node:fs";
import path from "node:path";

const [, , modul, basis, ordner] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext();
const p = await ctx.newPage();
const fehler = [];
p.on("pageerror", e => fehler.push(String(e)));
const ergebnis = {};

const swVersion = () => p.evaluate(() => new Promise(r => {
  const c = new MessageChannel(); c.port1.onmessage = e => r(e.data);
  navigator.serviceWorker.controller.postMessage({typ: "version"}, [c.port2]);
}));
const swDatei = path.join(ordner, "sw.js");
const swText = fs.readFileSync(swDatei, "utf8");
const liste = JSON.parse(/const DATEIEN = (\[.*\]);/.exec(swText)[1]);
const neueVersion = (v) => fs.writeFileSync(swDatei, swText.replace(/const VERSION = "[^"]*"/, `const VERSION = "${v}"`));

await p.goto(basis);
await p.evaluate(() => navigator.serviceWorker.ready);
await p.waitForFunction(() => navigator.serviceWorker.controller !== null, null, {timeout: 15000});
ergebnis.version1 = await swVersion();
ergebnis.gespeichert = await p.evaluate(async () => {
  const n = (await caches.keys()).filter(k => k.startsWith("rh:"));
  return n.length === 1 ? (await (await caches.open(n[0])).keys()).length : -n.length;
});
ergebnis.erwartet = liste.length;

// Ohne Netz neu laden. Der Testserver antwortet nicht mehr (wie ein Funkloch); Chromium meldet
// zusätzlich „offline“ an die Seite. WebKit kann setOffline nicht mit Service Worker kombinieren.
const chromium = (process.env.RH_BROWSER || "chromium") === "chromium";
await fetch(new URL("/__netz/aus", basis));
if (chromium) await ctx.setOffline(true);
await p.reload();
await p.waitForSelector("#titel:not(:empty)");
ergebnis.offlineTitel = await p.textContent("#titel");
ergebnis.offlineHinweis = chromium ? await p.isVisible("#offline") : null;
const bild = liste.find(f => f.startsWith("medien/"));
ergebnis.offlineBild = bild ? await p.evaluate(src => new Promise(r => {
  const i = new Image(); i.onload = () => r(i.naturalWidth > 0); i.onerror = () => r(false); i.src = src;
}), bild) : null;
if (chromium) await ctx.setOffline(false);
await fetch(new URL("/__netz/an", basis));

// Update mit fehlender Datei: alte Version bleibt, kein Hinweis
if (bild) {
  const pfad = path.join(ordner, bild), weg = pfad + ".weg";
  fs.renameSync(pfad, weg);
  // Hash ändern, damit die Datei geladen werden muss (unveränderte übernimmt der Worker aus dem alten Speicher)
  fs.writeFileSync(swDatei, swText.replace(/const VERSION = "[^"]*"/, 'const VERSION = "kaputt"').replace(`"${bild}": "`, `"${bild}": "x`));
  await p.evaluate(() => navigator.serviceWorker.getRegistration().then(r => r.update()).catch(() => {}));
  await p.waitForTimeout(1500);
  ergebnis.kaputtHinweis = await p.isVisible("#neu");
  ergebnis.kaputtVersion = await swVersion();
  fs.renameSync(weg, pfad);
}

// Ordentliches Update: Hinweis erscheint, Tippen übernimmt und lädt neu. Unveränderte Dateien
// kommen aus dem alten Speicher: außer sw.js geht keine Anfrage an den Server (Issue #64).
await fetch(new URL("/__log/leeren", basis));
neueVersion("neu");
await p.evaluate(() => navigator.serviceWorker.getRegistration().then(r => r.update()));
await p.waitForSelector("#neu:not([hidden])", {timeout: 15000});
ergebnis.updateHinweis = true;
ergebnis.geladenBeimInstallieren = await (await fetch(new URL("/__log/zeigen", basis))).json();
await Promise.all([p.waitForEvent("load"), p.click("#neuLaden")]);
await p.waitForFunction(() => navigator.serviceWorker.controller !== null);
ergebnis.version2 = await swVersion();
ergebnis.speicherNachUpdate = await p.evaluate(async () => (await caches.keys()).filter(k => k.startsWith("rh:")).length);
ergebnis.geladenBeimUpdate = await (await fetch(new URL("/__log/zeigen", basis))).json();
fs.writeFileSync(swDatei, swText);

ergebnis.fehler = fehler;
console.log(JSON.stringify(ergebnis));
await b.close();
