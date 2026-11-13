// Browser-Prüfung des Reise-Stands (Epic #223), aufgerufen von test_pwa.py.
// Aufruf: node stand_browser.mjs <playwright-modul> <basis-url> <web-ordner der Reise> <ordner mit Stand 2>
// Prüft: Fuß mit Reise-Stand, Zeit in Ortszeit (Europe/Berlin) und Release; Änderungsliste mit Person; api/stand liefert den neuen
// Stand, während der Service Worker noch den alten hält; der Hinweis „Neu: Reise-Stand 2“ erscheint, „Aktualisieren“ lädt ihn.
import fs from "node:fs";
import path from "node:path";

const [, , modul, basis, ordner, stand2] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({locale: "de-DE", timezoneId: "Europe/Berlin"});
const p = await ctx.newPage();
const fehler = [];
p.on("pageerror", e => fehler.push(String(e)));
const ergebnis = {};
const serverStand = n => fetch(new URL(`/__stand/${n}`, basis));

await serverStand(1);
await p.goto(basis);
await p.evaluate(() => navigator.serviceWorker.ready);
await p.waitForFunction(() => navigator.serviceWorker.controller !== null, null, {timeout: 15000});
await p.waitForFunction(() => /veröffentlicht/.test(document.querySelector("#release").textContent), null, {timeout: 15000});
ergebnis.fuss = (await p.textContent("#release")).replace(/\s+/g, " ").trim();
// Datum eines Zeitpunkts in UTC kurz vor Mitternacht: in Berlin schon der nächste Tag (#227)
ergebnis.mitternacht = await p.evaluate(() => [datumKurz("2026-11-02T23:30:00+00:00"), datumKurz("2026-11-02T23:30:00Z"), datumKurz("2026-11-02")]);

// Änderungsliste: ein Tipp auf die Nummer
await p.click("[data-stand-liste]");
ergebnis.listeSichtbar = await p.isVisible("#aenderungen");
ergebnis.liste = (await p.$$eval("#aenderungen li", li => li.map(x => x.textContent.replace(/\s+/g, " ").trim())));
ergebnis.ausgeklappt = await p.getAttribute("[data-stand-liste]", "aria-expanded");

// Stand 2 liegt auf dem Server, der Worker hält noch Stand 1: api/stand geht am Speicher vorbei
for (const f of fs.readdirSync(stand2)) fs.cpSync(path.join(stand2, f), path.join(ordner, f), {recursive: true});
await serverStand(2);
await p.reload();
await p.waitForSelector("#neu:not([hidden])", {timeout: 15000});
// Erst zeigt der Service Worker den allgemeinen Hinweis, danach setzt api/stand (1 s verzögert) „Neu: Reise-Stand 2.“ (#550):
// auf den Zielzustand warten; läuft die Zeit ab, trotzdem lesen, damit der Test mit seiner Meldung scheitert
await p.waitForFunction(() => (document.querySelector("#neu")?.textContent || "").includes("Neu: Reise-Stand"), null, {timeout: 15000}).catch(() => {});
ergebnis.hinweis = (await p.textContent("#neu")).replace(/\s+/g, " ").trim();
ergebnis.apiStand = await p.evaluate(async () => (await (await fetch("api/stand", {cache: "no-store"})).json()).veroeffentlicht.nummer);
ergebnis.seiteNochAlt = await p.evaluate(() => D.reise_stand.nummer);
await Promise.all([p.waitForEvent("load", {timeout: 30000}), p.click("#neuLaden")]);
await p.waitForFunction(() => D.reise_stand.nummer === 2, null, {timeout: 30000});
// Die Fußzeile zeigt erst „geändert <Zeit des Baus>“ und wechselt auf „veröffentlicht“, sobald api/stand geantwortet hat (#321):
// auf „Reise-Stand 2“ allein zu warten liest je nach Tempo den Zwischenzustand mit der echten Uhrzeit des Laufs.
await p.waitForFunction(() => /Reise-Stand 2 · veröffentlicht/.test(document.querySelector("#release").textContent), null, {timeout: 15000});
ergebnis.fussNeu = (await p.textContent("#release")).replace(/\s+/g, " ").trim();
ergebnis.fehler = fehler;
console.log(JSON.stringify(ergebnis));
await b.close();
