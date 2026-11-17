"""Bilder Stufe 1, Paket P3 (#455, #581): „Meine Reisen“ als Kacheln mit Titelbild und die angemeldete Bildroute
/bild/<reise>/<datei>. Spec: docs/specs/oberflaeche/bilder-455-p3.md (AC-1 bis AC-4; präzisiert V21, V22, AC-16, AC-17 der
Stufe-1-Spec docs/specs/oberflaeche/bilder-455-stufe1.md).

Nur erfundene Daten: die Beispielreise (mit Bildern, Titelbild BI-02) und das Stadtwochenende (ohne Bilder), Konten Ida
(Mitglied beider Reisen) und Tom (nur Stadtwochenende), alles unter tmp_path.

Schnittstelle, die diese Tests festlegen:
  GET/HEAD /bild/<reise>/BI-NN.webp   kleine Fassung des aktiven Bildes laut daten.json (Feld klein)
  GET/HEAD /bild/<reise>/symbol.png   App-Symbol der gebauten Seite (icon-192.png)
  alles andere unter /bild/           dieselbe 404-Antwort
  Kachel der Kontoseite: <div class="kachel"> mit Bild oder Fläche oben, darunter Titel und Rolle; Rahmen class="liste".
"""
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
WURZEL = ENGINE.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import konten  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402
from test_anmeldung import BASIS, SEITE, abruf, anmelden, welt  # noqa: E402,F401  (welt: Fixture)
from test_trennung import IDA, STADT_SEITE, TOM, stadt_bauen  # noqa: E402

TITELBILD = "BI-02"      # titelbild: true in beispiel/reisen/beispielreise/plan/bilder.yaml
ANDERES = "BI-03"        # aktiv, kein Titelbild
SCHUTZ = ("Cache-Control", "X-Content-Type-Options")


# ---------- Aufbau ----------

@pytest.fixture
def bw(welt, monkeypatch, tmp_path):
    """Beispielreise und Stadtwochenende gebaut; Ida Mitglied beider, Tom nur des Stadtwochenendes."""
    def neu(stadt_status=None, dritte=False):
        u = welt()
        stadt_bauen(u, stadt_status)
        links = tmp_path / "seiten-bilder.json"
        links.write_text(json.dumps({"beispielreise": SEITE, "stadtwochenende": STADT_SEITE}))
        monkeypatch.setenv("KN_SEITENLINKS", str(links))
        monkeypatch.setenv("RM_SEITEN", str(u.seiten))
        monkeypatch.setenv("KN_BASIS", BASIS)
        konten.einladen("beispielreise", "ida", IDA, "organisator", "Ida", "Ida")
        konten.einladen("stadtwochenende", "tom", TOM, "organisator", "Tom", "Tom")
        konten.einladen("stadtwochenende", "lea", IDA, "mitwirkend", "Ida", "Tom")
        if dritte:   # eine Reise ohne gebaute Seite (erfunden)
            konten.einladen("dritte-reise", "ida", IDA, "organisator", "Ida", "Ida")
        u.ida, _ = anmelden(u, IDA, name="Ida")
        u.tom, _ = anmelden(u, TOM, name="Tom")
        return u
    return neu


def holen(url, methode="GET", cookie=None):
    """Eine Anfrage, Pfad unverändert (auch %2e%2e und ..). -> (status, {kopf: wert}, bytes)"""
    t = urllib.parse.urlsplit(url)
    c = http.client.HTTPConnection(t.hostname, t.port, timeout=10)
    pfad = url.split(f"{t.hostname}:{t.port}", 1)[1]
    h = {"Cookie": f"__Host-frieda={cookie}"} if cookie else {}
    c.putrequest(methode, pfad, skip_accept_encoding=True)
    for k, v in h.items():
        c.putheader(k, v)
    c.endheaders()
    r = c.getresponse()
    kopf = {k: v for k, v in r.getheaders() if k.lower() != "date"}
    return r.status, kopf, r.read()


def daten(u, reise="beispielreise"):
    return json.loads((u.seiten / reise / "daten.json").read_text(encoding="utf-8"))


def klein(u, bild, reise="beispielreise"):
    return next(b["klein"] for b in daten(u, reise)["bilder"] if b["id"] == bild)


def kachel_von(t, titel):
    return next((k for k in t.split('<div class="kachel')[1:] if titel in k.split("</a>", 1)[0] or titel in k[:2000]), None)


def img_tags(t):
    return re.findall(r"<img\b[^>]*>", t)


def titel(u, reise):
    return daten(u, reise)["reise"]["titel"]


# ---------- AC-1: Bildroute ----------

def test_mitglied_bekommt_kleine_fassung(bw):
    u = bw()
    s, h, inhalt = holen(f"{u.kurl}/bild/beispielreise/{TITELBILD}.webp", cookie=u.ida)
    assert s == 200, (s, inhalt[:200])
    assert h.get("Content-Type") == "image/webp"
    assert h.get("Cache-Control") == "private, max-age=86400"
    assert h.get("X-Content-Type-Options") == "nosniff"
    assert inhalt == (u.seiten / "beispielreise" / klein(u, TITELBILD)).read_bytes()
    s, hh, leer = holen(f"{u.kurl}/bild/beispielreise/{TITELBILD}.webp", "HEAD", cookie=u.ida)
    assert s == 200 and leer == b"" and hh.get("Content-Type") == "image/webp"
    assert hh.get("Cache-Control") == "private, max-age=86400" and hh.get("Content-Length") == str(len(inhalt))


def test_mitglied_bekommt_symbol(bw):
    u = bw()
    for reise in ("beispielreise", "stadtwochenende"):
        s, h, inhalt = holen(f"{u.kurl}/bild/{reise}/symbol.png", cookie=u.ida)
        assert s == 200 and h.get("Content-Type") == "image/png", (reise, s)
        assert h.get("Cache-Control") == "private, max-age=86400" and h.get("X-Content-Type-Options") == "nosniff"
        assert inhalt == (u.seiten / reise / "icon-192.png").read_bytes()


def _404(u, pfad, cookie):
    return holen(f"{u.kurl}{pfad}", cookie=cookie)


def test_ohne_anmeldung_404(bw):
    u = bw()
    s, _, inhalt = holen(f"{u.kurl}/bild/beispielreise/{TITELBILD}.webp")
    assert s == 404 and b"RIFF" not in inhalt
    assert holen(f"{u.kurl}/bild/beispielreise/symbol.png")[0] == 404


def test_nicht_mitglied_gleiche_antwort_wie_unbekannte_reise(bw):
    u = bw()
    fremd = _404(u, f"/bild/beispielreise/{TITELBILD}.webp", u.tom)
    unbekannt = _404(u, f"/bild/gibt-es-nicht/{TITELBILD}.webp", u.tom)
    assert fremd[0] == 404 and fremd == unbekannt
    assert _404(u, "/bild/beispielreise/symbol.png", u.tom) == _404(u, "/bild/gibt-es-nicht/symbol.png", u.tom)


@pytest.mark.parametrize("pfad", [
    "/bild/Beispielreise/BI-02.webp",           # gegen das Muster der Ordnernamen
    "/bild/../beispielreise/BI-02.webp",
    "/bild/beispielreise/../beispielreise/BI-02.webp",
    "/bild/%2e%2e/beispielreise/BI-02.webp",
    "/bild/beispielreise/%2e%2e%2fdaten.json",
    "/bild/beispielreise/daten.json",
    "/bild/beispielreise/index.html",
    "/bild/beispielreise/icon-192.png",          # nur über den festen Namen symbol.png
    "/bild/beispielreise/medien/bilder/BI-02-480.webp",
    "/bild/beispielreise/BI-02-480.webp",        # Dateiname statt ID
    "/bild/beispielreise/BI-02-1600.webp",       # große Fassung
    "/bild/beispielreise/BI-02.WEBP",
    "/bild/beispielreise/BI-02.webp/",
    "/bild/beispielreise/bi-02.webp",
    "/bild/beispielreise/BI-99.webp",            # gibt es nicht
    "/bild/beispielreise",
    "/bild/beispielreise/",
    "/bild/",
])
def test_unzulaessig_einheitlich_404(bw, pfad):
    u = bw()
    vorlage = _404(u, f"/bild/gibt-es-nicht/{TITELBILD}.webp", u.ida)
    s, h, inhalt = _404(u, pfad, u.ida)
    assert s == 404, (pfad, s)
    assert (s, h, inhalt) == vorlage, pfad


def test_grosse_fassung_auch_mit_id_nie(bw):
    """Die Route liefert für BI-NN nur die kleine Fassung, nie die große (andere Bytes)."""
    u = bw()
    gross = next(b["gross"] for b in daten(u)["bilder"] if b["id"] == TITELBILD)
    inhalt = holen(f"{u.kurl}/bild/beispielreise/{TITELBILD}.webp", cookie=u.ida)[2]
    assert inhalt != (u.seiten / "beispielreise" / gross).read_bytes()


def test_zurueckgezogenes_bild_404(bw):
    """Fehlt ein Bild in daten.json (zurückgezogen), liefert die Route es nicht, auch wenn die Datei noch liegt."""
    u = bw()
    d = daten(u)
    datei = u.seiten / "beispielreise" / klein(u, ANDERES)
    d["bilder"] = [b for b in d["bilder"] if b["id"] != ANDERES]
    (u.seiten / "beispielreise" / "daten.json").write_text(json.dumps(d), encoding="utf-8")
    assert datei.is_file()
    assert _404(u, f"/bild/beispielreise/{ANDERES}.webp", u.ida) == _404(u, f"/bild/gibt-es-nicht/{TITELBILD}.webp", u.ida)


def test_fehlende_datei_404(bw):
    u = bw()
    (u.seiten / "beispielreise" / klein(u, ANDERES)).unlink()
    assert _404(u, f"/bild/beispielreise/{ANDERES}.webp", u.ida) == _404(u, f"/bild/gibt-es-nicht/{TITELBILD}.webp", u.ida)
    (u.seiten / "stadtwochenende" / "icon-192.png").unlink()
    assert _404(u, "/bild/stadtwochenende/symbol.png", u.ida)[0] == 404


def test_klein_ausserhalb_des_ordners_404(bw):
    """Zeigt klein in daten.json aus dem Ordner der Reise hinaus, liefert die Route nichts (resolve unter seiten()/<reise>)."""
    u = bw()
    d = daten(u)
    for b in d["bilder"]:
        if b["id"] == ANDERES:
            b["klein"] = "../stadtwochenende/icon-192.png"
    (u.seiten / "beispielreise" / "daten.json").write_text(json.dumps(d), encoding="utf-8")
    assert _404(u, f"/bild/beispielreise/{ANDERES}.webp", u.ida)[0] == 404


def test_post_liefert_nichts_und_allow(bw):
    u = bw()
    s, _, inhalt = holen(f"{u.kurl}/bild/beispielreise/{TITELBILD}.webp", "POST", cookie=u.ida)
    assert s in (404, 405) and b"RIFF" not in inhalt
    s, h, _ = holen(f"{u.kurl}/bild/beispielreise/{TITELBILD}.webp", "OPTIONS")
    assert s == 204 and h.get("Allow") == "GET, HEAD, OPTIONS"


# ---------- AC-2: Kachel in „Meine Reisen“ ----------

def test_kachel_mit_titelbild(bw):
    u = bw()
    t = abruf(f"{u.kurl}/konto", cookie=u.ida)[2]
    assert 'class="liste"' in t and 'class="kachel' in t
    k = kachel_von(t, titel(u, "beispielreise"))
    assert k, "Kachel der Beispielreise"
    bilder = img_tags(k)
    assert bilder and f'src="/bild/beispielreise/{TITELBILD}.webp"' in bilder[0], bilder
    assert 'alt=""' in bilder[0] and 'loading="lazy"' in bilder[0]
    assert k.index("<img") < k.index(titel(u, "beispielreise")), "Bild oben, Titel darunter"
    assert f'href="{SEITE}"' in k and 'class="titel"' in k and 'class="marke' in k   # Link und Rolle wie bisher


def test_kachel_ohne_titelbild_mit_symbol(bw):
    """Stadtwochenende (ohne Bilder): Akzentfläche mit App-Symbol, keine Bildadresse auf ein Foto."""
    u = bw()
    t = abruf(f"{u.kurl}/konto", cookie=u.ida)[2]
    k = kachel_von(t, titel(u, "stadtwochenende"))
    assert k, "Kachel des Stadtwochenendes"
    bilder = img_tags(k)
    assert len(bilder) == 1 and 'src="/bild/stadtwochenende/symbol.png"' in bilder[0], bilder
    assert 'class="flaeche' in k or "flaeche" in k.split("<img", 1)[0]
    assert not re.search(r"/bild/stadtwochenende/BI-", t)
    assert f'href="{STADT_SEITE}"' in k


def test_kachel_ohne_symbol_nur_flaeche(bw):
    u = bw()
    (u.seiten / "stadtwochenende" / "icon-192.png").unlink()
    t = abruf(f"{u.kurl}/konto", cookie=u.ida)[2]
    k = kachel_von(t, titel(u, "stadtwochenende"))
    assert k and not img_tags(k) and "flaeche" in k


def test_kachel_ohne_gebaute_seite(bw):
    u = bw(dritte=True)
    s, _, t = abruf(f"{u.kurl}/konto", cookie=u.ida)
    assert s == 200
    k = kachel_von(t, "dritte-reise")
    assert k, "Kachel der Reise ohne Seite"
    assert "href=" not in k.split('class="personen', 1)[0], "ohne gebaute Seite kein Link"
    assert not img_tags(k) and "flaeche" in k
    assert "/bild/dritte-reise/" not in t


def test_archiv_mit_denselben_kacheln(bw):
    u = bw(stadt_status="archiv")
    t = abruf(f"{u.kurl}/konto", cookie=u.ida)[2]
    oben, unten = t.split('<details class="archiv">', 1)
    assert 'class="kachel' in oben and "/bild/beispielreise/" in oben
    assert 'class="kachel' in unten and 'src="/bild/stadtwochenende/symbol.png"' in unten
    assert "/bild/stadtwochenende/" not in oben


def test_vorgemerkte_reise_bleibt_im_block_oben(bw):
    u = bw()
    konten.loeschung_vormerken("stadtwochenende", konten.konto_per_email(TOM)["id"])
    t = abruf(f"{u.kurl}/konto", cookie=u.ida)[2]
    assert 'class="vorgemerkt' in t and "/bild/stadtwochenende/" not in t


def test_kachel_ist_ein_baustein_der_kontoseiten():
    """Stil .kachel gehört zu den eigenen Stilen der Kontoseiten (anmeldung.py), eine Spalte, ab 760 px zwei; 16:7."""
    stil = (ENGINE / "anmeldung.py").read_text(encoding="utf-8")
    assert ".kachel" in stil and "16/7" in stil.replace(" ", "")


# ---------- AC-3: Bildadresse ohne Adresse der Reiseseite ----------

def test_bildadresse_ohne_adresse_der_reiseseite(bw):
    u = bw()
    t = abruf(f"{u.kurl}/konto", cookie=u.ida)[2]
    srcs = re.findall(r'<img\b[^>]*\bsrc="(/bild/[^"]*)"', t)
    assert srcs, "Kacheln mit Bildadressen"
    for s in srcs:
        assert re.fullmatch(r"/bild/[a-z0-9][a-z0-9-]*/(BI-\d+\.webp|symbol\.png)", s), s
        for seite in (SEITE, STADT_SEITE):
            pfad = urllib.parse.urlsplit(seite).path.strip("/")
            assert pfad not in s and seite not in s, s


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_kacheln_im_browser(bw, tmp_path, browser):
    """360 px: eine Spalte ohne Überbreite; ab 760 px zwei Kacheln nebeneinander; Bilder 16:7."""
    u = bw()
    seite = tmp_path / "konto.html"
    seite.write_text(abruf(f"{u.kurl}/konto", cookie=u.ida)[2], encoding="utf-8")
    bilder = {f"/bild/beispielreise/{TITELBILD}.webp": str(u.seiten / "beispielreise" / klein(u, TITELBILD)),
              "/bild/stadtwochenende/symbol.png": str(u.seiten / "stadtwochenende" / "icon-192.png")}
    aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_konto_kacheln.mjs"), str(PLAYWRIGHT), str(seite),
                          json.dumps(bilder)], capture_output=True, text=True, timeout=120,
                         env={**os.environ, "RH_BROWSER": browser})
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert not e["fehler"], e
    for breite, w in e["breiten"].items():
        assert w["kacheln"] >= 2 and not w["ueberbreite"], (breite, w)
        assert all(abs(v - 16 / 7) < 0.05 for v in w["verhaeltnis"]), (breite, w)
    assert e["breiten"]["360"]["spalten"] == 1
    assert e["breiten"]["760"]["spalten"] == 2 and e["breiten"]["1300"]["spalten"] == 2


# ---------- Betrieb: nginx-Ort ----------

def test_nginx_ort_bild():
    inc = (WURZEL / "betrieb/vorlagen/nginx-konnektor-orte.inc").read_text(encoding="utf-8")
    zeile = next((z for z in inc.splitlines() if z.startswith("location ^~ /bild/")), None)
    assert zeile and "__SNIPPETS__/__INSTANZ__-konnektor.inc" in zeile, zeile



# ---------- AC-4: Doku ----------

def test_doku_nachgefuehrt():
    k = (WURZEL / "docs/konnektor.md").read_text(encoding="utf-8")
    assert "/bild/<reise>/<datei>" in k and "symbol.png" in k
    d = (WURZEL / "docs/design.md").read_text(encoding="utf-8")
    assert "`reiseKachel`" in d
    o = (WURZEL / "docs/ontologie.md").read_text(encoding="utf-8")
    assert "BI-" in o and "plan/bilder.yaml" in o
    adr = (WURZEL / "docs/adr/0001-kern.md").read_text(encoding="utf-8")
    verlauf = adr.split("## Verlauf", 1)[1]
    assert "#455" in verlauf and "#613" in verlauf
