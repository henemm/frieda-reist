"""Tests für #498 (Meilenstein M5a): Export der Reisen und der Angaben zur Person. Spec: docs/specs/betrieb/export-498.md
(AC-1 bis AC-16).

Nur erfundene Daten: beispielreise (Ida Organisatorin, Karl mitwirkend), stadtwochenende (Tom Organisator, Lea
mitwirkend), ein fremdes Konto ohne Mitgliedschaft; alles unter tmp_path.

Schnittstelle, die diese Tests festlegen (aus der Spec):
  schreiben.ZEIT_EXPORT = 50                      Gesamtfrist des Git-Wegs (fetch höchstens 20 s)
  schreiben.Dienst: GET /<reise>/export           ZIP der Reise (Speicher oder origin/main:reisen/<reise>)
  schreiben.Dienst._datei_senden(code, datei, typ)
  schreiben_git.reise_archiv(s, reise, datei)     -> None, wenn die Reise auf origin/main fehlt
  konnektor.reise_export(reise, datei)            -> (True, None) | ("fehlt", None) | (False, fehler)
  anmeldung.reise_exportieren                     Modulvariable, vom Konnektor gesetzt; Vorgabe None
  anmeldung.EXPORT_BUDGET = 55                    Gesamtbudget des Exports in Sekunden
  anmeldung.export_karte(k)                       Abschnitt „Meine Daten“ (id="daten")
  POST /konto aktion=export                       ZIP als Download, sonst Mein Konto mit konto.export.fehler
  Katalog: konto.export.*, recht.datenschutz.export, recht.datenschutz.folgt (geändert)
"""
import datetime
import hashlib
import http.client
import inspect
import io
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import tracemalloc
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
WURZEL = ENGINE.parent
BEISPIEL = WURZEL / "beispiel" / "reisen"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import anmeldung  # noqa: E402
import belege  # noqa: E402
import konnektor as kn  # noqa: E402
import konten  # noqa: E402
import rueckmeldungen as rm  # noqa: E402
import schreiben as sb  # noqa: E402
import texte  # noqa: E402
from conftest import meldet  # noqa: E402
from test_anmeldung import BASIS, abruf, anmelden, welt  # noqa: E402,F401  (welt: Fixture)
from test_trennung import zwei, IDA, KARL, TOM, abdruck  # noqa: E402,F401  (zwei: Fixture)
from test_schreiben_speicher import speicher, Dienst, repo, git  # noqa: E402,F401  (Fixtures)

REISEN = ["beispielreise", "stadtwochenende"]
FREMD = "fremd@beispiel.invalid"
MO = "mo@beispiel.invalid"
EINGELADEN = "eingeladen@beispiel.invalid"
HEUTE = lambda: datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")   # noqa: E731


# ---------- Hilfen ----------

def zip_aus_ordner(ordner, datei, extra=()):
    """Reiseordner als ZIP in das Dateiobjekt datei schreiben (wie der Schreibdienst), Pfade relativ zum Ordner."""
    with zipfile.ZipFile(datei, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(Path(ordner).rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(ordner).as_posix())
        for name, inhalt in extra:
            z.writestr(name, inhalt)


def unecht_export(aufrufe=None, ausnahmen=None):
    """Ersatz für anmeldung.reise_exportieren: liefert die Beispielreise aus dem Repo als ZIP.
    ausnahmen: {reise: "fehlt" | False | "abgeschnitten" | "keinzip" | "boese" | callable}"""
    ausnahmen = ausnahmen or {}

    def export(reise, datei):
        if aufrufe is not None:
            aufrufe.append(reise)
        a = ausnahmen.get(reise)
        if callable(a):
            return a(reise, datei)
        if a == "fehlt":
            return "fehlt", None
        if a is False:
            return False, "Schreibdienst antwortet 503"
        if a == "keinzip":
            datei.write(b"keine ZIP-Datei " * 100)
            return True, None
        if a == "boese":
            zip_aus_ordner(BEISPIEL / reise, datei, extra=[("../ausserhalb.txt", b"x"), ("/abs.txt", b"x"),
                                                           ("a\\..\\..\\b.txt", b"x")])
            return True, None
        puffer = io.BytesIO()
        zip_aus_ordner(BEISPIEL / reise, puffer)
        daten = puffer.getvalue()
        datei.write(daten[: len(daten) // 2] if a == "abgeschnitten" else daten)
        return True, None
    return export


def post_roh(u, keks, felder, origin=BASIS, sprache="de"):
    """POST /konto ohne Dekodieren -> (status, kopfzeilen als dict (klein), bytes)."""
    t = urllib.parse.urlsplit(u.kurl)
    c = http.client.HTTPConnection(t.hostname, t.port, timeout=60)
    h = {"Content-Type": "application/x-www-form-urlencoded", "Accept-Language": sprache,
         "Cookie": f"__Host-frieda={keks}"}
    if origin:
        h["Origin"] = origin
    c.request("POST", "/konto", body=urllib.parse.urlencode(felder).encode(), headers=h)
    r = c.getresponse()
    return r.status, {k.lower(): v for k, v in r.getheaders()}, r.read()


def exportieren(u, keks, **extra):
    return post_roh(u, keks, {"aktion": "export", **extra})


def ist_zip(kopf, daten):
    return kopf.get("content-type", "").startswith("application/zip") and daten[:2] == b"PK"


def als_zip(daten):
    z = zipfile.ZipFile(io.BytesIO(daten))
    assert z.testzip() is None
    return z


def fehlerseite(s, kopf, daten, sprache="de"):
    return (s == 200 and not ist_zip(kopf, daten) and "attachment" not in kopf.get("content-disposition", "")
            and meldet(daten.decode(), "konto.export.fehler", sprache))


def mitglied_dazu(kid, reise, schluessel, seit="2099-01-01T00:00:00+00:00"):
    with closing(konten.db()) as v, v:
        v.execute("INSERT INTO mitgliedschaften (konto, reise, schluessel, seit) VALUES (?, ?, ?, ?)",
                  (kid, reise, schluessel, seit))


@pytest.fixture
def export_welt(zwei, monkeypatch):
    """zwei() mit eingesetztem Abruf der Reise-ZIP (Beispielreisen aus dem Repo)."""
    def neu(aufrufe=None, ausnahmen=None, **kw):
        u = zwei(**kw)
        monkeypatch.setattr(anmeldung, "reise_exportieren", unecht_export(aufrufe, ausnahmen), raising=False)
        return u
    return neu


def zip_holen(d, pfad, geheim=True):
    """GET beim Schreibdienst -> (code, kopf, bytes)."""
    req = urllib.request.Request(f"{d.basis}/{pfad}", headers={"X-Frieda-Dienst": d.geheim} if geheim else {})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, {k.lower(): v for k, v in r.getheaders()}, r.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()


def inhalt_ordner(ordner):
    return {f.relative_to(ordner).as_posix(): f.read_bytes() for f in sorted(Path(ordner).rglob("*")) if f.is_file()}


def inhalt_zip(z, praefix=""):
    return {n[len(praefix):]: z.read(n) for n in z.namelist() if n.startswith(praefix) and not n.endswith("/")}


# ---------- Schreibdienst: GET /<reise>/export (AC-8, AC-9, AC-10) ----------

@pytest.mark.parametrize("reise", REISEN)
def test_dienst_export_speicherreise(speicher, reise, tmp_path):
    with Dienst(speicher.schreiber()) as d:
        code, kopf, daten = zip_holen(d, f"{reise}/export")
    assert code == 200 and kopf["content-type"].startswith("application/zip")
    assert int(kopf["content-length"]) == len(daten) and kopf.get("cache-control") == "no-store"
    vergleich = tmp_path / "vergleich"
    speicher.rs.exportieren(reise, vergleich)
    assert inhalt_zip(als_zip(daten)) == inhalt_ordner(vergleich)


def test_dienst_export_reporeise(repo, monkeypatch):
    wurzel = repo[0]
    monkeypatch.setenv("FR_SPEICHERREISEN", "")
    with Dienst(sb.Schreiber(wurzel)) as d:
        code, kopf, daten = zip_holen(d, "beispielreise/export")
        assert code == 200 and kopf["content-type"].startswith("application/zip"), daten[:300]
        namen = git(wurzel, "ls-tree", "-r", "--name-only", "origin/main", "reisen/beispielreise").splitlines()
        erwartet = {n.removeprefix("reisen/beispielreise/"): git(wurzel, "show", f"origin/main:{n}").encode()
                    for n in namen if not n.endswith((".png", ".jpg", ".gpx"))}
        z = als_zip(daten)
        assert set(z.namelist()) >= set(erwartet) and all(not n.startswith("reisen/") for n in z.namelist())
        for n, inhalt in erwartet.items():
            assert z.read(n).rstrip(b"\n") == inhalt.rstrip(b"\n"), n
        assert zip_holen(d, "gibtesnicht/export")[0] == 404


def test_dienst_export_ohne_geheimnis(speicher):
    with Dienst(speicher.schreiber()) as d:
        a = zip_holen(d, "beispielreise/export", geheim=False)
        b = zip_holen(d, "gibtesnicht/export", geheim=False)
        req = urllib.request.Request(f"{d.basis}/beispielreise/export", headers={"X-Frieda-Dienst": "falsch"})
        try:
            urllib.request.urlopen(req, timeout=10)
            c = (200, None)
        except urllib.error.HTTPError as e:
            c = (e.code, e.read())
    assert a[0] == b[0] == c[0] == 403
    assert a[2] == b[2] == c[1] and json.loads(a[2])["fehler_code"] == "schreiben.dienst.nur_konnektor"


def test_dienst_export_404(speicher, monkeypatch):
    aufgerufen = []
    echt = speicher.rs.exportieren
    monkeypatch.setattr(speicher.rs, "exportieren", lambda *a, **k: (aufgerufen.append(a), echt(*a, **k))[1])
    konten.loeschung_vormerken("stadtwochenende", None)
    with Dienst(speicher.schreiber()) as d:
        for pfad in ("Ungueltig_Name/export", "stadtwochenende/export"):   # unbekannt bei vorhandenem Repo: reporeise
            code, _, daten = zip_holen(d, pfad)
            assert code == 404, (pfad, code)
            assert json.loads(daten)["fehler_code"] == "schreiben.dienst.unbekannt"
    assert not any("stadtwochenende" in map(str, a) for a in aufgerufen), "vorgemerkte Reise: kein Zugriff auf den Speicher"


def test_dienst_export_ohne_repo_503(speicher):
    """Speicherliste nicht leer, .git fehlt: eine unbekannte Reise ist 503, nicht 404 (kein stiller Teilexport)."""
    with Dienst(speicher.schreiber()) as d:
        code, _, daten = zip_holen(d, "gibtesnicht/export")
    assert code == 503 and json.loads(daten)["fehler_code"] == "schreiben.dienst.repo_nicht_erreichbar"


def test_dienst_export_alte_zeitstempel_und_modus(speicher):
    """Ablagedateien mit mtime 0 (vor 1980) und Modus 400: Export gelingt, Dateien stehen mit 644 in der ZIP."""
    speicher.rs.vorgang_schreiben("beispielreise", {"medien/foto.jpg": os.urandom(300 * 1024)}, wer="Ida",
                                  werkzeug="item_update", titel="Foto")
    for f in (speicher.tmp.parent / "_speicher").rglob("*"):
        if f.is_file():
            os.utime(f, (0, 0))
    with Dienst(speicher.schreiber()) as d:
        code, _, daten = zip_holen(d, "beispielreise/export")
    assert code == 200
    z = als_zip(daten)
    assert (z.getinfo("medien/foto.jpg").external_attr >> 16) & 0o777 == 0o644


def test_dienst_export_entfernte_reise_404(speicher):
    konten.loeschung_vormerken("stadtwochenende", None)
    konten.loeschung_abschliessen("stadtwochenende")
    with Dienst(speicher.schreiber()) as d:
        assert zip_holen(d, "stadtwochenende/export")[0] == 404


def test_dienst_export_einstellungen_nicht_lesbar(speicher, monkeypatch):
    import instanz

    def kaputt():
        raise instanz.EinstellungenNichtLesbar("nicht lesbar")
    monkeypatch.setattr(instanz, "speicherreisen", kaputt)
    with Dienst(speicher.schreiber()) as d:
        code, _, daten = zip_holen(d, "beispielreise/export")
    assert code == 503 and json.loads(daten)["fehler_code"] == "schreiben.dienst.einstellungen_nicht_lesbar"


@pytest.mark.parametrize("fehler", ["ablage", "sqlite", "oserror"])
def test_dienst_export_speicherfehler(speicher, monkeypatch, fehler):
    rs = speicher.rs

    def kaputt(*a, **k):
        raise {"ablage": rs.AblageFehlt("fehlt", "0" * 64), "sqlite": sqlite3.OperationalError("db"),
               "oserror": OSError("platte")}[fehler]
    monkeypatch.setattr(rs, "exportieren", kaputt)
    with Dienst(speicher.schreiber()) as d:
        code, _, daten = zip_holen(d, "beispielreise/export")
    assert code == 503 and json.loads(daten)["fehler_code"] == "schreiben.dienst.speicher_nicht_erreichbar"


@pytest.mark.parametrize("fehler", [RuntimeError("git kaputt"), None])
def test_dienst_export_gitfehler(repo, monkeypatch, fehler):
    import subprocess
    import schreiben_git
    monkeypatch.setenv("FR_SPEICHERREISEN", "")

    def kaputt(*a, **k):
        raise fehler or subprocess.TimeoutExpired("git", 50)
    monkeypatch.setattr(schreiben_git, "reise_archiv", kaputt)
    with Dienst(sb.Schreiber(repo[0])) as d:
        code, _, daten = zip_holen(d, "beispielreise/export")
    assert code == 503 and json.loads(daten)["fehler_code"] == "schreiben.dienst.repo_nicht_erreichbar"


def test_dienst_export_fristen_im_gitweg(repo, monkeypatch):
    import schreiben_git
    monkeypatch.setenv("FR_SPEICHERREISEN", "")
    fristen = []
    echt = schreiben_git.git

    def spion(ordner, *args, **kw):
        fristen.append((args[0] if args else "", kw.get("frist")))
        return echt(ordner, *args, **kw)
    monkeypatch.setattr(schreiben_git, "git", spion)
    with closing(tempfile.TemporaryFile()) as f:
        assert schreiben_git.reise_archiv(sb.Schreiber(repo[0]), "beispielreise", f) is not None
    fetch = [fr for befehl, fr in fristen if befehl == "fetch"]
    archive = [fr for befehl, fr in fristen if befehl == "archive"]
    assert fetch and all(fr is not None and fr <= 20 for fr in fetch)
    assert archive and all(fr is not None and fr <= sb.ZEIT_EXPORT for fr in archive)
    with closing(tempfile.TemporaryFile()) as f:
        assert schreiben_git.reise_archiv(sb.Schreiber(repo[0]), "gibtesnicht", f) is None


def test_fristen_unter_der_proxy_grenze():
    assert sb.ZEIT_EXPORT == 50 and anmeldung.EXPORT_BUDGET == 55
    assert sb.ZEIT_EXPORT < anmeldung.EXPORT_BUDGET < 60
    assert sb.ZEIT_EXPORT != sb.ZEIT_PRUEFUNG


def test_dienst_export_raeumt_auf(speicher):
    """Hardlinks aus der Ablage mit Modus 400: der Temp-Ordner verschwindet trotzdem."""
    gross = os.urandom(300 * 1024)    # über der Grenze zum Auslagern
    speicher.rs.vorgang_schreiben("beispielreise", {"medien/foto.jpg": gross}, wer="Ida", werkzeug="item_update",
                                  titel="Foto")
    with Dienst(speicher.schreiber()) as d:
        code, _, daten = zip_holen(d, "beispielreise/export")
    assert code == 200 and als_zip(daten).read("medien/foto.jpg") == gross
    assert list(speicher.tmp.iterdir()) == [], "kein Temp-Ordner bleibt liegen"


def test_dienst_export_streamt_grosse_datei(speicher):
    gross = os.urandom(40 * 1024 * 1024)
    speicher.rs.vorgang_schreiben("beispielreise", {"medien/gross.jpg": gross}, wer="Ida", werkzeug="item_update",
                                  titel="Groß")
    pruef = hashlib.sha256(gross).hexdigest()
    del gross
    with Dienst(speicher.schreiber()) as d:
        tracemalloc.start()
        try:
            req = urllib.request.Request(f"{d.basis}/beispielreise/export", headers={"X-Frieda-Dienst": d.geheim})
            with urllib.request.urlopen(req, timeout=120) as r, tempfile.TemporaryFile() as f:
                laenge = int(r.headers["Content-Length"])
                shutil.copyfileobj(r, f, 1024 * 1024)
                spitze = tracemalloc.get_traced_memory()[1]
                assert f.tell() == laenge
                f.seek(0)
                with zipfile.ZipFile(f) as z, z.open("medien/gross.jpg") as e:
                    h = hashlib.sha256()
                    for stueck in iter(lambda: e.read(1024 * 1024), b""):
                        h.update(stueck)
        finally:
            tracemalloc.stop()
    assert h.hexdigest() == pruef
    assert spitze < 16 * 1024 * 1024, f"Spitze {spitze // 1024 // 1024} MB: die Datei wurde ganz gelesen"


def test_dienst_gesund_unveraendert(speicher):
    with Dienst(speicher.schreiber()) as d:
        assert d.get("gesund") == (200, {"gesund": True})


def test_rundlauf_ueber_importieren(speicher, tmp_path, monkeypatch):
    """Versprechen aus konto.export.punkt_1: der Ordner reise/ lässt sich wieder einlesen."""
    for reise in REISEN:
        with Dienst(speicher.schreiber()) as d:
            code, _, daten = zip_holen(d, f"{reise}/export")
        assert code == 200
        ordner = tmp_path / f"ausgepackt-{reise}" / reise
        als_zip(daten).extractall(ordner)
        vorher = inhalt_ordner(ordner)
        monkeypatch.setenv("FR_SPEICHER", str(tmp_path / f"neuer-speicher-{reise}"))
        speicher.rs.importieren(ordner, reise, wer="Ida", grund="Rundlauf")
        nochmal = tmp_path / f"nochmal-{reise}"
        speicher.rs.exportieren(reise, nochmal)
        assert inhalt_ordner(nochmal) == vorher
        monkeypatch.setenv("FR_SPEICHER", str(speicher.tmp.parent / "_speicher"))


# ---------- Konnektor: reise_export und _anmeldung (AC-10) ----------

class _Antworter(BaseHTTPRequestHandler):
    """Schreibdienst zum Test: der Pfad bestimmt die Antwort."""
    zip_daten = b""

    def do_GET(self):
        art = self.path.strip("/").split("/")[0]
        if art == "ok":
            daten, code = self.zip_daten, 200
        elif art == "keinzip":
            daten, code = b"keine ZIP " * 50, 200
        elif art == "abgeschnitten":
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(self.zip_daten)))
            self.end_headers()
            self.wfile.write(self.zip_daten[: len(self.zip_daten) // 2])
            self.wfile.flush()
            self.connection.close()
            return
        else:
            daten, code = b'{"fehler": "x"}', int(art)
        self.send_response(code)
        self.send_header("Content-Type", "application/zip" if code == 200 else "application/json")
        self.send_header("Content-Length", str(len(daten)))
        self.end_headers()
        self.wfile.write(daten)

    def log_message(self, *a):
        pass


def test_reise_export_codes(monkeypatch, tmp_path):
    puffer = io.BytesIO()
    zip_aus_ordner(BEISPIEL / "stadtwochenende", puffer)
    _Antworter.zip_daten = puffer.getvalue()
    s = ThreadingHTTPServer(("127.0.0.1", 0), _Antworter)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        monkeypatch.setenv("KN_SCHREIBDIENST", f"http://127.0.0.1:{s.server_address[1]}")
        with tempfile.TemporaryFile() as f:
            assert kn.reise_export("ok", f) == (True, None)
            f.seek(0)
            assert f.read() == _Antworter.zip_daten
        for fall, erwartet in (("404", "fehlt"), ("403", False), ("503", False), ("keinzip", False),
                               ("abgeschnitten", False)):
            with tempfile.TemporaryFile() as f:
                ergebnis = kn.reise_export(fall, f)
            assert ergebnis[0] == erwartet, (fall, ergebnis)
            assert erwartet == "fehlt" or ergebnis[1], fall
    finally:
        s.shutdown()
    monkeypatch.setenv("KN_SCHREIBDIENST", "http://127.0.0.1:9")   # nichts hört dort
    with tempfile.TemporaryFile() as f:
        assert kn.reise_export("beispielreise", f)[0] is False
    monkeypatch.setenv("KN_SCHREIBDIENST", "")
    with tempfile.TemporaryFile() as f:
        assert kn.reise_export("beispielreise", f)[0] is False


def test_konnektor_setzt_den_abruf_ohne_zirkelimport():
    assert anmeldung.reise_exportieren is kn.reise_export
    quelle = (ENGINE / "anmeldung.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import konnektor|from konnektor)", quelle, re.M)


class _Datei(io.BufferedRandom):
    pass


def test_anmeldung_streamt_dateiobjekte(welt, monkeypatch):
    u = welt()
    inhalt = os.urandom(3 * 1024 * 1024)
    offen = []

    def bearbeiten(methode, pfad, headers, body, ip, reise_info):
        f = tempfile.TemporaryFile()
        f.write(inhalt)
        f.seek(0)
        offen.append(f)
        return 200, [("Content-Type", "application/zip")], f
    monkeypatch.setattr(anmeldung, "bearbeiten", bearbeiten)
    t = urllib.parse.urlsplit(u.kurl)
    c = http.client.HTTPConnection(t.hostname, t.port, timeout=10)
    c.request("GET", "/konto")
    r = c.getresponse()
    daten = r.read()
    assert r.status == 200 and daten == inhalt and int(r.getheader("Content-Length")) == len(inhalt)
    assert r.getheader("Cache-Control") == "no-store" and r.getheader("Content-Security-Policy")
    c.request("HEAD", "/konto")
    r = c.getresponse()
    assert r.read() == b"" and int(r.getheader("Content-Length")) == len(inhalt)
    # abgebrochene Verbindung: nach wenigen Bytes zu
    c2 = http.client.HTTPConnection(t.hostname, t.port, timeout=10)
    c2.request("GET", "/konto")
    r2 = c2.getresponse()
    r2.read(100)
    r2.close()   # HTTP/1.0: die Verbindung hängt an der Antwort, c2.sock ist schon None
    c2.close()
    ende = time.monotonic() + 5
    while time.monotonic() < ende and not all(f.closed for f in offen):
        time.sleep(0.05)
    assert len(offen) == 3 and all(f.closed for f in offen), "jedes Dateiobjekt wird geschlossen"


def test_anmeldung_bytes_unveraendert(welt):
    u = welt()
    for pfad in ("/anmelden", "/datenschutz", "/impressum", "/.well-known/oauth-authorization-server"):
        t = urllib.parse.urlsplit(u.kurl)
        c = http.client.HTTPConnection(t.hostname, t.port, timeout=10)
        c.request("GET", pfad)
        r = c.getresponse()
        daten = r.read()
        assert int(r.getheader("Content-Length")) == len(daten), pfad
        assert r.getheader("Cache-Control") == "no-store", pfad


# ---------- Mein Konto: der Export (AC-2 bis AC-7) ----------

@pytest.mark.parametrize("wer", ["ida", "tom"])
def test_export_liefert_zip(export_welt, wer):
    u = export_welt()
    keks, reise = (u.a_keks, "beispielreise") if wer == "ida" else (u.b_keks, "stadtwochenende")
    s, kopf, daten = exportieren(u, keks)
    assert s == 200 and ist_zip(kopf, daten), daten[:400]
    assert kopf["content-disposition"] == f'attachment; filename="frieda-daten-{HEUTE()}.zip"'
    assert kopf["cache-control"] == "no-store" and int(kopf["content-length"]) == len(daten)
    z = als_zip(daten)
    namen = z.namelist()
    assert "person.json" in namen
    assert inhalt_zip(z, f"{reise}/reise/") == inhalt_ordner(BEISPIEL / reise)
    for datei in ("aufgaben.json", "brett.json", "packstand.json", "rueckmeldungen.json"):
        assert f"{reise}/beitraege/{datei}" in namen
        json.loads(z.read(f"{reise}/beitraege/{datei}"))
    assert json.loads(z.read(f"{reise}/belege/belege.json")) == {"belege": []}
    andere = [r for r in REISEN if r != reise][0]
    assert not any(n.startswith(f"{andere}/") for n in namen)


def test_person_json(export_welt):
    u = export_welt()
    _, _, daten = exportieren(u, u.a_keks)
    p = json.loads(als_zip(daten).read("person.json"))
    assert p["name"] == "Ida" and p["email"] == IDA and p["sprache"] == "de"
    assert re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?\+00:00$", p["erstellt"])
    assert [m["reise"] for m in p["mitgliedschaften"]] == ["beispielreise"]
    m = p["mitgliedschaften"][0]
    assert set(m) == {"reise", "titel", "rolle", "seit"} and m["rolle"] == "organisator" and m["titel"] != "beispielreise"
    assert p["geraete"] and all(set(g) <= {"geraet", "seit", "zuletzt"} for g in p["geraete"])
    assert "kalender" in p and "push" in p
    text = json.dumps(p, ensure_ascii=False)
    assert KARL not in text and TOM not in text
    for verboten in ("token", "schluessel", "endpoint", "p256dh", "auth", "hash", '"id"'):
        assert verboten not in text, verboten


def test_archivierte_dabei_vorgemerkte_und_fremde_nicht(export_welt):
    u = export_welt(stadt_status="archiv")
    mitglied_dazu(u.a["id"], "stadtwochenende", "ida")
    z = als_zip(exportieren(u, u.a_keks)[2])
    assert {n.split("/")[0] for n in z.namelist() if "/" in n} == {"beispielreise", "stadtwochenende"}
    p = json.loads(z.read("person.json"))
    assert [m["reise"] for m in p["mitgliedschaften"]] == ["beispielreise", "stadtwochenende"]
    konten.loeschung_vormerken("stadtwochenende", u.b["id"])
    z = als_zip(exportieren(u, u.a_keks)[2])
    assert not any(n.startswith("stadtwochenende/") for n in z.namelist())
    assert [m["reise"] for m in json.loads(z.read("person.json"))["mitgliedschaften"]] == ["beispielreise"]


def test_manipuliertes_formular_bringt_keine_fremde_reise(export_welt):
    aufrufe = []
    u = export_welt(aufrufe=aufrufe)
    karl_keks, _ = anmelden(u, KARL)
    s, kopf, daten = exportieren(u, karl_keks, reise="stadtwochenende", reisen="stadtwochenende",
                                 pfad="../stadtwochenende")
    assert ist_zip(kopf, daten)
    assert not any(n.startswith("stadtwochenende/") for n in als_zip(daten).namelist())
    assert "stadtwochenende" not in aufrufe


def test_konto_ohne_reise(export_welt):
    u = export_welt()
    keks, _ = anmelden(u, MO, name="Mo")
    s, kopf, daten = exportieren(u, keks)
    assert ist_zip(kopf, daten) and als_zip(daten).namelist() == ["person.json"]


def _ablage_fuellen(o):
    """Beiträge von Ida und Karl, Belege mit allen Sichtbarkeiten (erfunden)."""
    def aufgabe(aid, titel, wer):
        zeit = "2026-11-01T10:00:00+00:00"
        return {"id": aid, "titel": titel, "bezug": [], "zustaendig": wer, "prioritaet": "normal", "ab": "", "frist": "",
                "notiz": "", "status": "offen", "erstellt": zeit, "erstellt_von": wer, "geaendert": zeit, "erledigt": "",
                "verlauf": [{"zeit": zeit, "wer": wer, "was": "angelegt"}]}
    (o / "aufgaben.json").write_text(json.dumps({"naechste": 3, "aufgaben": [
        aufgabe("AG-01", "Fähre prüfen", "Ida"), aufgabe("AG-02", "Karten kaufen", "Karl")]}), encoding="utf-8")
    (o / "brett.json").write_text(json.dumps({"W-01": {"wer": "Karl", "text": "Badestelle"}}), encoding="utf-8")
    (o / "packstand.json").write_text(json.dumps({"G-01": {"Ida": "2026-11-01T10:00:00+00:00",
                                                           "Karl": "2026-11-02T10:00:00+00:00"}}), encoding="utf-8")
    (o / "eingang.jsonl").write_text('{"name": "Ida", "text": "Von Ida"}\n{"name": "Karl", "text": "Von Karl"}\n',
                                     encoding="utf-8")
    (o / "einladungen.json").write_text(json.dumps({"kim": {"name": "Kim", "rolle": "gast", "email": EINGELADEN,
                                                            "geheimnis": "Einladungsgeheimnis-4711"}}), encoding="utf-8")
    (o / "belege").mkdir(exist_ok=True)
    liste = []
    for i, (wer, sichtbar, zurueck) in enumerate([("Ida", "beteiligte", None), ("Karl", "beteiligte", None),
                                                  ("Ida", "alle", None), ("Ida", "beteiligte", "2026-11-03T00:00:00+00:00")],
                                                 start=1):
        did = f"D-{i:02d}"
        (o / "belege" / f"{did}.pdf").write_bytes(b"%PDF erfundener Beleg " + did.encode())
        liste.append({"id": did, "buchung": "B-01", "name": f"{did}.pdf", "datei": f"{did}.pdf", "typ": "pdf",
                      "groesse": 30, "wer": wer, "hochgeladen": "2026-11-01T00:00:00+00:00", "sichtbar": sichtbar,
                      "zurueckgezogen": zurueck})
    belege.speichern(o, {"naechste": 5, "belege": liste})


def test_beitraege_gleich_belege_nach_rolle(export_welt):
    u = export_welt()
    _ablage_fuellen(u.ablage / "beispielreise")
    karl_keks, _ = anmelden(u, KARL)
    zi = als_zip(exportieren(u, u.a_keks)[2])
    zk = als_zip(exportieren(u, karl_keks)[2])
    for datei in ("aufgaben.json", "brett.json", "packstand.json", "rueckmeldungen.json"):
        n = f"beispielreise/beitraege/{datei}"
        assert json.loads(zi.read(n)) == json.loads(zk.read(n)), datei
    o = u.ablage / "beispielreise"
    assert json.loads(zi.read("beispielreise/beitraege/aufgaben.json")) == rm.aufgaben_lesen(o)
    assert json.loads(zi.read("beispielreise/beitraege/rueckmeldungen.json")) == json.loads(
        json.dumps(rm.eintraege(o), ensure_ascii=False))
    ida_ids = [b["id"] for b in json.loads(zi.read("beispielreise/belege/belege.json"))["belege"]]
    karl_ids = [b["id"] for b in json.loads(zk.read("beispielreise/belege/belege.json"))["belege"]]
    assert ida_ids == ["D-01", "D-02", "D-03", "D-04"]
    assert karl_ids == [b["id"] for b in belege.liste(o, "Karl", "mitwirkend")] == ["D-02", "D-03"]
    for z, ids in ((zi, ida_ids), (zk, karl_ids)):
        dateien = sorted(n for n in z.namelist() if n.startswith("beispielreise/belege/") and n.endswith(".pdf"))
        assert dateien == [f"beispielreise/belege/{i}.pdf" for i in ids]
        assert z.read(dateien[0]) == (o / "belege" / f"{ids[0]}.pdf").read_bytes()
    assert not any("einladungen" in n or "eingang.jsonl" in n for n in zi.namelist())


def test_reise_ohne_ablage(export_welt, monkeypatch):
    u = export_welt()
    monkeypatch.setattr(rm, "ordner", lambda reise: None)
    z = als_zip(exportieren(u, u.a_keks)[2])
    assert any(n.startswith("beispielreise/reise/") for n in z.namelist())
    assert not any(n.startswith(("beispielreise/beitraege/", "beispielreise/belege/")) for n in z.namelist())


def test_keine_fremden_adressen_geheimnisse_pfade(export_welt):
    u = export_welt()
    _ablage_fuellen(u.ablage / "beispielreise")
    anmelden(u, KARL)
    keks_fremd, _ = anmelden(u, FREMD, name="Fremd")
    konten.einladen("beispielreise", "kim", EINGELADEN, "gast", "Kim", "Ida")
    daten = exportieren(u, u.a_keks)[2]
    z = als_zip(daten)
    alles = b"".join(z.read(n) for n in z.namelist())
    for verboten in (KARL, TOM, FREMD, EINGELADEN, "Einladungsgeheimnis-4711", konten.dienst_geheimnis(),
                     str(u.ablage), str(u.seiten), str(WURZEL)):
        assert verboten.encode() not in alles, verboten
    assert IDA.encode() in z.read("person.json")


def test_export_streamt_grosse_dateien(export_welt, monkeypatch):
    gross = os.urandom(40 * 1024 * 1024)
    pruef = hashlib.sha256(gross).hexdigest()

    def gross_export(reise, datei):
        with zipfile.ZipFile(datei, "w", zipfile.ZIP_STORED) as z:
            z.writestr("medien/gross.bin", gross)
            z.write(BEISPIEL / reise / "reise.yaml", "reise.yaml")
        return True, None
    u = export_welt(ausnahmen={"beispielreise": gross_export})
    o = u.ablage / "beispielreise"
    (o / "belege").mkdir(exist_ok=True)
    (o / "belege" / "D-01.pdf").write_bytes(b"%PDF" + gross)
    belege.speichern(o, {"naechste": 2, "belege": [{"id": "D-01", "buchung": "B-01", "name": "x.pdf", "datei": "D-01.pdf",
                                                    "typ": "pdf", "groesse": len(gross) + 4, "wer": "Ida",
                                                    "hochgeladen": "2026-11-01T00:00:00+00:00",
                                                    "sichtbar": "beteiligte", "zurueckgezogen": None}]})
    # gross bleibt: gross_export braucht es noch (vor tracemalloc.start belegt, zählt nicht mit)
    t = urllib.parse.urlsplit(u.kurl)
    c = http.client.HTTPConnection(t.hostname, t.port, timeout=120)
    c.request("POST", "/konto", body=b"aktion=export", headers={
        "Content-Type": "application/x-www-form-urlencoded", "Origin": BASIS, "Cookie": f"__Host-frieda={u.a_keks}"})
    tracemalloc.start()
    try:
        r = c.getresponse()
        with tempfile.TemporaryFile() as f:
            shutil.copyfileobj(r, f, 1024 * 1024)
            spitze = tracemalloc.get_traced_memory()[1]
            f.seek(0)
            with zipfile.ZipFile(f) as z:
                assert z.testzip() is None
                with z.open("beispielreise/reise/medien/gross.bin") as e:
                    h = hashlib.sha256()
                    for stueck in iter(lambda: e.read(1024 * 1024), b""):
                        h.update(stueck)
                assert z.getinfo("beispielreise/belege/D-01.pdf").file_size == 40 * 1024 * 1024 + 4
    finally:
        tracemalloc.stop()
    assert h.hexdigest() == pruef
    assert spitze < 24 * 1024 * 1024, f"Spitze {spitze // 1024 // 1024} MB: eine Datei wurde ganz gelesen"


def test_export_ueber_echten_schreibdienst(zwei, speicher, monkeypatch):
    """Mein Konto -> konnektor.reise_export -> Schreibdienst im Thread -> Speicher: der ganze Weg."""
    monkeypatch.setenv("FR_BASIS", BASIS)                     # die Fixture speicher räumt die Umgebung von welt ab
    monkeypatch.setenv("FR_MAIL_DATEI", str(speicher.tmp.parent / "mails.jsonl"))
    u = zwei()
    monkeypatch.setenv("FR_SPEICHERREISEN", "beispielreise,stadtwochenende")
    with Dienst(speicher.schreiber()) as d:
        monkeypatch.setenv("KN_SCHREIBDIENST", d.basis)
        monkeypatch.setattr(anmeldung, "reise_exportieren", kn.reise_export, raising=False)
        s, kopf, daten = exportieren(u, u.a_keks)
    assert ist_zip(kopf, daten), daten[:400]
    vergleich = speicher.tmp.parent / "vergleich"
    speicher.rs.exportieren("beispielreise", vergleich)
    assert inhalt_zip(als_zip(daten), "beispielreise/reise/") == inhalt_ordner(vergleich)


# ---------- Fehlerfälle: kein halber Export (AC-11, AC-12) ----------

@pytest.fixture
def eigener_temp(tmp_path, monkeypatch):
    t = tmp_path / "temp-export"
    t.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(t))
    monkeypatch.setenv("TMPDIR", str(t))
    return t


@pytest.mark.parametrize("fall", [False, "abgeschnitten", "keinzip", "boese"])
def test_fehler_bei_einer_reise_bricht_alles_ab(export_welt, eigener_temp, fall):
    u = export_welt(ausnahmen={"stadtwochenende": fall})
    mitglied_dazu(u.a["id"], "stadtwochenende", "ida")
    s, kopf, daten = exportieren(u, u.a_keks)
    assert fehlerseite(s, kopf, daten), daten[:400]
    assert list(eigener_temp.iterdir()) == [], "temporäre Dateien sind weg"
    assert not (u.seiten.parent / "ausserhalb.txt").exists() and not Path("/abs.txt").exists()


def test_fehlertext_auf_englisch(export_welt):
    u = export_welt(ausnahmen={"beispielreise": False})
    konten.sprache_setzen(u.a["id"], "en")
    s, kopf, daten = exportieren(u, u.a_keks)
    assert fehlerseite(s, kopf, daten, "en")


def test_zeitbudget_aufgebraucht(export_welt, monkeypatch):
    def langsam(reise, datei):
        monkeypatch.setattr(anmeldung.time, "monotonic", lambda: 10 ** 12)   # Budget mit einem Schlag aufgebraucht
        zip_aus_ordner(BEISPIEL / reise, datei)
        return True, None
    u = export_welt(ausnahmen={"beispielreise": langsam})
    mitglied_dazu(u.a["id"], "stadtwochenende", "ida")
    s, kopf, daten = exportieren(u, u.a_keks)
    assert fehlerseite(s, kopf, daten)


def test_404_einer_reise_wird_uebersprungen(export_welt):
    u = export_welt(ausnahmen={"stadtwochenende": "fehlt"})
    mitglied_dazu(u.a["id"], "stadtwochenende", "ida")
    s, kopf, daten = exportieren(u, u.a_keks)
    z = als_zip(daten)
    assert ist_zip(kopf, daten) and any(n.startswith("beispielreise/reise/") for n in z.namelist())
    assert not any(n.startswith("stadtwochenende/") for n in z.namelist())


def test_fehlende_belegdatei(export_welt, eigener_temp):
    u = export_welt()
    _ablage_fuellen(u.ablage / "beispielreise")
    (u.ablage / "beispielreise" / "belege" / "D-03.pdf").unlink()
    s, kopf, daten = exportieren(u, u.a_keks)
    assert fehlerseite(s, kopf, daten)
    assert list(eigener_temp.iterdir()) == []


def test_platte_voll(export_welt, monkeypatch):
    u = export_welt()
    echt = tempfile.TemporaryFile

    def voll(*a, **k):
        f = echt(*a, **k)

        class Voll:
            def __getattr__(self, n):
                return getattr(f, n)

            def write(self, *_):
                raise OSError(28, "No space left on device")

            def __enter__(self):
                return self

            def __exit__(self, *x):
                f.close()
        return Voll()
    monkeypatch.setattr(tempfile, "TemporaryFile", voll)
    s, kopf, daten = exportieren(u, u.a_keks)
    assert fehlerseite(s, kopf, daten)


def test_nur_ein_export_je_konto_zugleich(export_welt):
    los, drin = threading.Event(), threading.Event()

    def warten(reise, datei):
        drin.set()
        los.wait(20)
        zip_aus_ordner(BEISPIEL / reise, datei)
        return True, None
    u = export_welt(ausnahmen={"beispielreise": warten})
    erstes = {}
    t = threading.Thread(target=lambda: erstes.update(r=exportieren(u, u.a_keks)))
    t.start()
    assert drin.wait(10)
    s, kopf, daten = exportieren(u, u.a_keks)
    los.set()
    t.join(30)
    assert fehlerseite(s, kopf, daten)
    assert ist_zip(erstes["r"][1], erstes["r"][2])
    s, kopf, daten = exportieren(u, u.a_keks)   # danach wieder frei
    assert ist_zip(kopf, daten)


def test_ohne_eingerichteten_abruf(export_welt, monkeypatch):
    u = export_welt()
    monkeypatch.setattr(anmeldung, "reise_exportieren", None)
    s, kopf, daten = exportieren(u, u.a_keks)
    assert fehlerseite(s, kopf, daten)


@pytest.mark.parametrize("ausnahmen", [None, {"beispielreise": False}])
def test_export_schreibt_nichts(export_welt, ausnahmen):
    u = export_welt(ausnahmen=ausnahmen)
    _ablage_fuellen(u.ablage / "beispielreise")
    vorher = abdruck(u.ablage, u.seiten)
    mails = u.mails.read_text() if u.mails.exists() else ""
    meldungen = len(rm.meldungen_des_kontos(u.a))
    exportieren(u, u.a_keks)
    assert abdruck(u.ablage, u.seiten) == vorher
    assert (u.mails.read_text() if u.mails.exists() else "") == mails
    assert len(rm.meldungen_des_kontos(u.a)) == meldungen


# ---------- Seite und Texte (AC-1, AC-13 bis AC-15) ----------

PUNKTE = ["konto.export.titel", "konto.export.hinweis", "konto.export.knopf", "konto.export.was_drin",
          "konto.export.punkt_1", "konto.export.punkt_2", "konto.export.punkt_3", "konto.export.punkt_4",
          "konto.export.andere"]


@pytest.mark.parametrize("sprache", ["de", "en"])
def test_abschnitt_meine_daten(export_welt, sprache):
    u = export_welt()
    konten.sprache_setzen(u.a["id"], sprache)
    s, _, t = abruf(f"{u.kurl}/konto", cookie=u.a_keks)
    assert s == 200 and 'id="daten"' in t
    daten = t.index('id="daten"')
    einstellungen = t.index(texte.t(sprache, "konto.seite.einstellungen"))
    linkblock = t.index('value="alle_abmelden"') if 'value="alle_abmelden"' in t else t.index("alle_abmelden")
    assert einstellungen < daten < linkblock
    abschnitt = t[daten:linkblock]
    for schluessel in PUNKTE:
        assert meldet(abschnitt, schluessel, sprache), schluessel
    assert 'action="/konto"' in abschnitt and 'name="aktion" value="export"' in abschnitt
    assert "<details" in abschnitt and abschnitt.count("<li") >= 4
    assert 'href="/konto?loeschen=1"' in t[linkblock:], "Linkblock (#381) bleibt nach dem Abschnitt"


def test_seite_ohne_abschnitt_unveraendert(export_welt, monkeypatch):
    """Ohne den neuen Abschnitt ist Mein Konto byteweise wie vorher (#381-Teile unangetastet)."""
    u = export_welt()
    k = konten.konto(u.a["id"])
    anmeldung._anfrage.sprache = "de"
    mit = anmeldung.konto_seite(k, kn.reise_kurz)
    karte = anmeldung.export_karte(k)
    assert karte and karte in mit
    monkeypatch.setattr(anmeldung, "export_karte", lambda k: "")
    ohne = anmeldung.konto_seite(k, kn.reise_kurz)
    assert mit.replace(karte, "", 1) == ohne


def test_get_liefert_nie_eine_zip(export_welt):
    u = export_welt()
    t = urllib.parse.urlsplit(u.kurl)
    c = http.client.HTTPConnection(t.hostname, t.port, timeout=10)
    c.request("GET", "/konto?aktion=export", headers={"Cookie": f"__Host-frieda={u.a_keks}"})
    r = c.getresponse()
    daten = r.read()
    assert r.status == 200 and not ist_zip({k.lower(): v for k, v in r.getheaders()}, daten)
    assert 'id="daten"' in daten.decode()


def test_post_ohne_herkunft_oder_sitzung(export_welt):
    u = export_welt()
    s, kopf, daten = post_roh(u, u.a_keks, {"aktion": "export"}, origin="https://boese.invalid")
    assert s == 403 and not ist_zip(kopf, daten)
    s, kopf, daten = post_roh(u, "keine-sitzung", {"aktion": "export"})
    assert s in (302, 303) and not ist_zip(kopf, daten) and "/anmelden" in kopf.get("location", "")


@pytest.mark.parametrize("sprache", ["de", "en"])
def test_datenschutz_nennt_den_export(welt, sprache):
    u = welt()
    s, _, t = abruf(f"{u.kurl}/datenschutz", kopf={"Accept-Language": sprache})
    assert s == 200
    export = texte.t(sprache, "recht.datenschutz.export")
    folgt = texte.t(sprache, "recht.datenschutz.folgt")
    namen = texte.t(sprache, "recht.datenschutz.namen_freitext")
    import html
    e, f, n = (t.index(html.escape(x, quote=False)) for x in (export, folgt, namen))
    assert n < e < f


def test_texte_deutsch_woertlich():
    de = {
        "konto.export.titel": "Meine Daten",
        "konto.export.hinweis": "Lade alles herunter, was Frieda zu dir und deinen Reisen gespeichert hat: eine Datei mit "
                                "jeder Reise, in der du dabei bist, und deinen Kontoangaben.",
        "konto.export.knopf": "Meine Daten herunterladen",
        "konto.export.was_drin": "Was ist drin?",
        "konto.export.punkt_1": "Je Reise ein Ordner mit der ganzen Reise: Tage, Pläne, Unterkünfte, Buchungen, Wissen, "
                                "Fotos und Routen (GPX). Frieda kann sie daraus wieder einlesen.",
        "konto.export.punkt_2": "Die Beiträge der Reise: Aufgaben, Wünsche, Packliste und Rückmeldungen. Als "
                                "Organisator:in alle, sonst deine eigenen und was du auf der Reiseseite siehst.",
        "konto.export.punkt_3": "Die Belege, die du sehen darfst.",
        "konto.export.punkt_4": "Deine Kontoangaben: Name, E-Mail-Adresse, Sprache, deine Reisen mit Rolle, deine Geräte, "
                                "deine Einstellungen für Kalender und Benachrichtigungen und deine Meldungen an den "
                                "Betreiber.",   # Meldungen an den Betreiber seit #530
        "konto.export.andere": "Andere Personen stehen darin nur mit ihrem Namen, ohne E-Mail-Adresse. Auch archivierte "
                               "Reisen sind dabei.",
        "konto.export.fehler": "Export gerade nicht möglich. Bitte versuche es in ein paar Minuten noch einmal.",
        "recht.datenschutz.export": "Unter „Mein Konto“ kannst du jederzeit alles herunterladen, was Frieda zu dir "
                                    "speichert: deine Kontoangaben und jede Reise, in der du Mitglied bist, mit Fotos, "
                                    "Routen und den Belegen, die du sehen darfst. Die Datei entsteht beim Herunterladen "
                                    "und wird auf dem Server nicht aufbewahrt.",
        "recht.datenschutz.folgt": "Noch nicht eingebaut, das folgt (ohne festen Termin): Löschen und Export eines "
                                   "Eintrags auf der Warteliste.",
    }
    for k, v in de.items():
        assert texte.t("de", k) == v, k
        en = texte.t("en", k)
        assert en and en != k and en != v, k
    assert "trip data" not in texte.t("en", "recht.datenschutz.folgt")


def test_deploy_ohne_neues_modul():
    text = (WURZEL / "betrieb" / "deploy.sh").read_text(encoding="utf-8")
    assert "export" not in re.findall(r"\b(\w+)\.py\b", text)
