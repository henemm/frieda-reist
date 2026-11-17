// Bild einer Stelle der Reiseseite für den Konnektor (page_view / seite_ansehen, #618): Frieda sieht die Seite so, wie sie
// am Handy oder am Rechner erscheint, und erfährt, wo eine Kennung auf der Seite steht.
// Aufruf: node seitenbild.mjs <playwright-modul> <ordner der veröffentlichten Seite> <kennung oder -> <handy|rechner>
// Liefert eine JSON-Zeile auf stdout: {ort: {reiter, ansicht, teil, klappen, gekuerzt, markiert}, bild (JPEG, base64), fehler}.
// Die Seite kommt nur aus dem Ordner (eigener kleiner Server auf 127.0.0.1, wie betrieb/startprobe.mjs); jede andere Adresse,
// auch /api/ des Rückmeldedienstes, ist gesperrt: keine geheimen Links, keine Live-Daten, nichts nach außen.
// Den Ort bestimmt die Seite selbst (route, zumZiel in vorlage.html): Das Skript steuert #<kennung> an wie ein Link und merkt
// sich, welche Klappen die Seite dafür öffnen musste. Keine zweite Logik der Heimat (ADR-0003) außerhalb der Seite.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";

const [, , modul, ordner, kennung, geraet] = process.argv;
const GERAETE = {handy: {viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true},
                 rechner: {viewport: {width: 1280, height: 860}}};
const typen = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".css": "text/css",
               ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
               ".woff2": "font/woff2", ".gpx": "application/gpx+xml"};
const wurzel = path.resolve(ordner);

function ausliefern(q, a) {
  let rel;
  try { rel = decodeURIComponent(new URL(q.url, "http://x").pathname).replace(/^\/+/, "") || "index.html"; } catch (e) { a.writeHead(400).end(); return; }
  const datei = path.join(wurzel, rel);
  if (!datei.startsWith(wurzel + path.sep) || !fs.existsSync(datei) || fs.statSync(datei).isDirectory()) { a.writeHead(404).end(); return; }
  const typ = typen[path.extname(datei).toLowerCase()] || "application/octet-stream", groesse = fs.statSync(datei).size;
  const bereich = /^bytes=(\d*)-(\d*)$/.exec(q.headers.range || "");
  if (bereich) {   // Kartenkacheln (.pmtiles) werden bereichsweise gelesen
    const von = bereich[1] === "" ? Math.max(0, groesse - Number(bereich[2])) : Number(bereich[1]);
    const bis = bereich[1] === "" || bereich[2] === "" ? groesse - 1 : Math.min(Number(bereich[2]), groesse - 1);
    a.writeHead(206, {"content-type": typ, "accept-ranges": "bytes", "content-range": `bytes ${von}-${bis}/${groesse}`, "content-length": bis - von + 1});
    fs.createReadStream(datei, {start: von, end: bis}).pipe(a);
    return;
  }
  a.writeHead(200, {"content-type": typ, "accept-ranges": "bytes", ...(path.extname(datei) === ".html" ? {} : {"content-length": groesse})});
  if (path.extname(datei) === ".html") {
    // Die Umzugsweiterleitung (FR_UMZUG_NACH, bauen.py) schickt die Seite auf die Live-Adresse: hier entfernen
    a.end(fs.readFileSync(datei, "utf8").replace(/<script>if \(location\.origin !== [^\n]*?location\.hash\)<\/script>/, ""));
    return;
  }
  fs.createReadStream(datei).pipe(a);
}

const zeile = s => (s || "").replace(/\s+/g, " ").trim();

async function aufnehmen(b, basis) {
  const fehler = [];
  const ctx = await b.newContext({...(GERAETE[geraet] || GERAETE.handy), deviceScaleFactor: 2, serviceWorkers: "block"});
  try {
    // Nur der eigene kleine Server, ohne /api/ (Live-Daten brauchen eine Anmeldung, die das Bild nie hat)
    await ctx.route(u => { const x = new URL(u); return x.origin !== basis || x.pathname.startsWith("/api/"); }, r => r.abort());
    const p = await ctx.newPage();
    p.on("pageerror", e => fehler.push(String(e).split("\n")[0]));
    await p.goto(basis + "/", {timeout: 30000});
    await p.waitForSelector("#main > *", {timeout: 20000});
    if (kennung && kennung !== "-") {
      // zumZiel umhüllen: vor dem Öffnen festhalten, hinter welchen Klappen das Ziel liegt
      await p.evaluate(() => {
        const orig = window.zumZiel;
        window.__ort = {markiert: false, klappen: [], teil: "", gekuerzt: false};
        window.zumZiel = function (id) {
          const e = document.getElementById(id);
          if (e) {
            const o = window.__ort, text = x => (x ? x.textContent : "").replace(/\s+/g, " ").trim().slice(0, 80);
            o.markiert = true;
            for (let x = e; x; x = x.parentElement) {
              if (x.tagName === "DETAILS" && !x.open) o.klappen.unshift(text(x.querySelector(":scope > summary")));
            }
            const panel = e.closest("[role=tabpanel]");
            if (panel && panel.hidden) {
              const box = panel.closest(".reiter");
              o.teil = text(box && box.querySelector(`[role=tab][data-teil="${CSS.escape(panel.dataset.teil)}"]`));
            }
            o.gekuerzt = !!e.closest(".weg-text.kurz");
          }
          return orig.apply(this, arguments);
        };
      });
      // Wie ein Link, aber ohne den Sprung des Browsers selbst: Der klappt ein Ziel in <details> schon vor der Seite auf,
      // dann wüsste niemand mehr, dass es zugeklappt war. Die Seite (route) liest location.hash beim Ereignis hashchange.
      await p.evaluate(k => { history.pushState(null, "", "#" + encodeURIComponent(k)); window.dispatchEvent(new HashChangeEvent("hashchange")); }, kennung);
    }
    await p.waitForTimeout(600);
    // Den Blitz der Seite um das angesteuerte Ziel (Rahmen beim Springen) im sichtbaren Teil anhalten, damit das Bild die
    // Stelle zeigt, unabhängig davon, wie schnell der Rechner ist
    await p.evaluate(() => { for (const a of document.getAnimations()) { if (a.animationName === "blitz") { a.pause(); a.currentTime = 300; } } });
    const ort = await p.evaluate(() => {
      const t = x => (x ? x.innerText : "").split("\n").map(s => s.trim()).filter(s => s && !/^\d+$/.test(s)).join(" · ");
      const kopf = document.querySelector("#main h1, #main h2");
      return {reiter: t(document.querySelector("#nav a.on")), ansicht: t(kopf).slice(0, 160), ...(window.__ort || {markiert: false, klappen: []})};
    });
    const bild = (await p.screenshot({type: "jpeg", quality: 72})).toString("base64");
    return {ort, bild, fehler};
  } finally {
    await ctx.close();
  }
}

let ergebnis;
const server = http.createServer(ausliefern);
await new Promise(r => server.listen(0, "127.0.0.1", r));
let b = null;
try {
  // Auch ein Fehler beim Start des Browsers (etwa fehlende Browser) kommt als JSON mit Grund zurück
  const pw = await import(path.resolve(modul));
  b = await pw.chromium.launch();
  ergebnis = await aufnehmen(b, `http://127.0.0.1:${server.address().port}`);
} catch (e) {
  ergebnis = {fehler: [zeile(String(e.message || e).split("\n")[0]).slice(0, 300)]};
} finally {
  if (b) await b.close();
  server.close();
}
// Erst beenden, wenn die Zeile ganz geschrieben ist: process.exit schneidet eine große Ausgabe in eine Pipe sonst ab
process.stdout.write(JSON.stringify(ergebnis) + "\n", () => process.exit(ergebnis.bild ? 0 : 1));
