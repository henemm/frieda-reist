// Startprobe der gebauten Reiseseite (#395, Lehre aus #387): lädt <ordner>/index.html im Browser und meldet Seitenfehler
// beim Start, console.error, eine leere Seite und die sichtbare Startfehler-Meldung (#387). Exit 0 gesund, 1 rot (Meldung auf stdout).
// Aufruf: node startprobe.mjs <playwright-modul> <ordner mit index.html>
import http from "node:http";
import fs from "node:fs";
import path from "node:path";

const [, , modul, ordner] = process.argv;
const typen = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png"};
const server = http.createServer((q, a) => {
  const rel = decodeURIComponent(new URL(q.url, "http://x").pathname).replace(/^\/+/, "") || "index.html";
  const datei = path.join(ordner, rel);
  if (!datei.startsWith(path.resolve(ordner)) || !fs.existsSync(datei) || fs.statSync(datei).isDirectory()) {
    a.writeHead(404).end();
    return;
  }
  const typ = typen[path.extname(datei)] || "application/octet-stream", groesse = fs.statSync(datei).size;
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
    // Die Umzugsweiterleitung (FR_UMZUG_NACH, bauen.py) schickt die Seite auf die Live-Adresse: für die Probe entfernen
    a.end(fs.readFileSync(datei, "utf8").replace(/<script>if \(location\.origin !== [^\n]*?location\.hash\)<\/script>/, ""));
    return;
  }
  fs.createReadStream(datei).pipe(a);
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const fehler = [];
const pw = await import(path.resolve(modul));
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
try {
  const ctx = await b.newContext({viewport: {width: 1300, height: 900}, serviceWorkers: "block"});
  await ctx.route("**/api/**", r => r.abort());
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(`Seitenfehler: ${e}`));
  p.on("console", m => { if (m.type() === "error" && !/Failed to load resource|ERR_FAILED/.test(m.text())) fehler.push(`console.error: ${m.text()}`); });
  await p.goto(`http://127.0.0.1:${server.address().port}/`);
  await p.waitForTimeout(1500);
  const text = await p.evaluate(() => (document.querySelector("#main") || {}).textContent || "");
  if (!text.trim()) fehler.push("Seite leer (#main ohne Inhalt)");
  // Startfehler-Meldung des Fängers (#387): sichtbar heißt, der Start ist gescheitert
  if (await p.locator("#startfehler").isVisible()) fehler.push("Startfehler-Meldung sichtbar");
} finally {
  await b.close();
  server.close();
}
if (fehler.length) { console.log(fehler.join("\n")); process.exit(1); }
console.log("Startprobe gut");
