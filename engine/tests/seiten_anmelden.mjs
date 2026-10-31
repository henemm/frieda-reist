// Anmeldeseiten im echten Browser (Paket J2), aufgerufen von test_seite.py mit laufendem Konnektor-Dienst.
// Aufruf: node seiten_anmelden.mjs <playwright-modul> <frieda-url> <email>
// Schickt das Formular ab wie ein Mensch (der Browser setzt Origin selbst) und meldet, was danach zu sehen ist.
// Den Code liest das Testskript aus der Maildatei und reicht ihn über stdin herein.
import {createInterface} from "node:readline";
const [, , modul, frieda, email] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const aus = {antworten: []};
const p = await (await b.newContext({ locale: "de-DE" })).newPage();
p.on("response", r => { if (r.request().method() === "POST") aus.antworten.push(r.status()); });
await p.goto(frieda + "/anmelden");
await p.fill("#email", email);
await p.click("button");
await p.waitForLoadState();
aus.nachAdresse = await p.locator("h1").textContent();
console.log(JSON.stringify({bereit: true}));
const code = await new Promise(r => createInterface({input: process.stdin}).once("line", r));
await p.fill("#code", code);
await p.click("button");
await p.waitForLoadState();
aus.nachCode = await p.locator("h1").textContent();
await b.close();
console.log(JSON.stringify(aus));
