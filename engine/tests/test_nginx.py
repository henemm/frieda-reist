"""Tests für die nginx-Vorlage des Konnektors und ihren Abgleich (#206, #260; betrieb/nginx.py, vorlagen/nginx-*.conf).
Alles mit erfundener Instanz „probe“ und Beispieladressen aus dem Testbereich (192.0.2.0/24); unter /etc wird nichts gelesen oder geschrieben."""
import http.server
import importlib.util
import os
import re
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

BETRIEB = Path(__file__).resolve().parents[2] / "betrieb"
SAUBER = {k: v for k, v in os.environ.items() if not k.startswith(("FR_", "RM_", "KN_", "EA_", "VF_", "FS_", "WA_", "EI_"))}


def erzeugen(tmp_path, **extra):
    """Die Bausteine einer Instanz „probe“ nach tmp_path/soll erzeugen; liefert den Ordner nginx/."""
    env = {**SAUBER, "FR_WURZEL": str(tmp_path), "FR_INSTANZ": "probe", "FR_TITEL": "Probe", "EI_ZIEL": str(tmp_path / "soll"), **extra}
    r = subprocess.run(["bash", str(BETRIEB / "einrichten.sh"), "--erzeugen"], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return tmp_path / "soll" / "nginx"


def nginx_modul():
    spec = importlib.util.spec_from_file_location("nginx_abgleich", BETRIEB / "nginx.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------- Vorlage ----------

def test_zonendatei_hat_eigene_zonen_und_die_ausnahme(tmp_path):
    zone = (erzeugen(tmp_path) / "probe-zone.conf").read_text()
    assert re.search(r"limit_req_zone \$probe_schluessel zone=probe_mcp:\d+m rate=10r/s;", zone)
    assert re.search(r"limit_req_zone \$probe_schluessel zone=probe_anmelden:\d+m rate=5r/m;", zone)
    assert re.search(r"limit_req_zone \$probe_schluessel zone=probe_konto:\d+m rate=30r/m;", zone)
    assert zone.count("limit_req_zone") == 3
    # keine Namen aus der gemeinsamen Datei, keine Zone der Reise-Bausteine (die bleibt dort bis zur Bereinigung)
    assert not re.search(r"zone=(login|probe_api|frieda\w*)\b", zone)
    assert re.search(r"geo \$probe_eigen \{[^}]*127\.0\.0\.1 1;[^}]*::1 1;", zone, re.S)
    assert re.search(r'map \$probe_eigen \$probe_schluessel \{[^}]*0 \$binary_remote_addr;[^}]*1 "";', zone, re.S)


def test_eigene_adressen_sind_einstellbar(tmp_path):
    zone = (erzeugen(tmp_path, FR_EIGENE_ADRESSEN="192.0.2.7 2001:db8::7") / "probe-zone.conf").read_text()
    assert "192.0.2.7 1;" in zone and "2001:db8::7 1;" in zone and "127.0.0.1 1;" in zone and "::1 1;" in zone


def test_orte_nutzen_die_drei_zonen(tmp_path):
    conf = (erzeugen(tmp_path) / "probe-konnektor-orte.inc").read_text()
    assert not re.search(r"zone=probe_api\b", conf)

    def ort(kopf):
        i = conf.index(kopf)
        return conf[i:conf.index("}", i)]   # die Orte enthalten keine verschachtelten Blöcke
    mcp = ort("location = /mcp")
    assert "zone=probe_mcp burst=40 nodelay" in mcp and "proxy_buffering off" in mcp and "proxy_read_timeout 300s" in mcp
    assert "zone=probe_anmelden burst=10 nodelay" in ort("location = /anmelden")
    for frei in ("location = /token", "location = /register", "location ^~ /.well-known/oauth-", "location ^~ /schrift/"):
        assert "limit_req" not in ort(frei), frei
    for konto in ("location ^~ /einladung/", "location ^~ /kalender/"):
        assert "zone=probe_konto burst=20 nodelay" in ort(konto), konto
    # keine Direktive doppelt in einem Ort: Lesefrist und Puffer stehen nur dort, wo sie gelten
    inc = (erzeugen(tmp_path) / "probe-konnektor.inc").read_text()
    assert "proxy_read_timeout" not in inc and "proxy_buffering" not in inc


def test_vorlagen_ohne_echte_adressen():
    for n in ("nginx-zone.conf", "nginx-konnektor-orte.inc", "nginx-konnektor.inc"):
        text = (BETRIEB / "vorlagen" / n).read_text()
        assert not re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", text.replace("127.0.0.1", "")), n


def _frei():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.skipif(not shutil.which("nginx"), reason="nginx fehlt")
def test_nginx_laedt_die_zonen_und_nimmt_eigene_adressen_aus(tmp_path):
    kn_port, port = _frei(), _frei()
    snippets = tmp_path / "snippets"
    snippets.mkdir()

    class Dienst(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", kn_port), Dienst)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    temp = " ".join(f"{n}_temp_path {tmp_path}/{n};" for n in ("client_body", "proxy", "fastcgi", "uwsgi", "scgi"))
    benutzer = "user root;" if os.geteuid() == 0 else ""

    def starten(eigene):
        aus = erzeugen(tmp_path, FR_KN_PORT=str(kn_port), FR_NGINX_SNIPPETS=str(snippets), FR_EIGENE_ADRESSEN=eigene)
        for n in ("probe-konnektor-orte.inc", "probe-konnektor.inc"):
            shutil.copy(aus / n, snippets / n)
        (tmp_path / "nginx.conf").write_text(f"""{benutzer} pid {tmp_path}/nginx.pid; error_log {tmp_path}/fehler.log; daemon off;
events {{}}
http {{ access_log off; {temp}
  include {aus}/probe-zone.conf;
  server {{ listen 127.0.0.1:{port};
    include {snippets}/probe-konnektor-orte.inc;
  }}
}}
""")
        args = ["nginx", "-e", str(tmp_path / "fehler.log"), "-c", str(tmp_path / "nginx.conf"), "-p", str(tmp_path)]
        pruefung = subprocess.run([*args[:1], "-t", *args[1:]], capture_output=True, text=True)
        assert pruefung.returncode == 0, pruefung.stderr
        p = subprocess.Popen(args, stderr=subprocess.PIPE)
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                return p
            except OSError:
                time.sleep(0.1)
        raise AssertionError("nginx antwortet nicht")

    def codes(pfad, n, von):
        import http.client
        erg = []
        for _ in range(n):
            c = http.client.HTTPConnection("127.0.0.1", port, source_address=(von, 0))
            c.request("GET", pfad)
            erg.append(c.getresponse().status)
            c.close()
        return erg

    ng = starten("192.0.2.7")
    try:
        # Eigene Adresse (hier die Schleife 127.0.0.1) wird nie begrenzt, weit über Wiederholungsrate und Burst hinaus
        assert set(codes("/konto", 80, "127.0.0.1")) == {200} and set(codes("/mcp", 80, "127.0.0.1")) == {200}
        # Eine fremde Adresse (127.0.0.2 steht nicht in der Liste): die Drossel greift (Konto 30/min, burst 20; Anmelden 5/min, burst 10)
        c = codes("/konto", 60, "127.0.0.2")
        assert c[0] == 200 and 429 in c
        assert 429 in codes("/anmelden", 30, "127.0.0.2")
    finally:
        ng.terminate()
        ng.wait(timeout=10)
        s.shutdown()


# ---------- Abgleich ----------

@pytest.fixture
def abgleich(tmp_path):
    """Soll aus einrichten.sh, installiert wird in Ordnern unter tmp_path; lauf() ruft nginx.py pruefen."""
    confd, snippets, dienst = tmp_path / "confd", tmp_path / "snippets", tmp_path / "dienst"
    for d in (confd, snippets, dienst):
        d.mkdir()
    env = {**SAUBER, "FR_WURZEL": str(tmp_path), "FR_INSTANZ": "probe", "FR_TITEL": "Probe", "FR_DIENST": str(dienst),
           "FR_NGINX_SNIPPETS": str(snippets), "EI_NGINX_CONFD": str(confd), "FR_SUDO": ""}

    def lauf(**extra):
        return subprocess.run([str(BETRIEB / "nginx.py"), "pruefen"], env={**env, **extra}, capture_output=True, text=True)

    def installieren():
        aus = erzeugen(tmp_path, FR_NGINX_SNIPPETS=str(snippets), FR_DIENST=str(dienst))
        shutil.copy(aus / "probe-zone.conf", confd)
        for n in ("probe-konnektor-orte.inc", "probe-konnektor.inc"):
            shutil.copy(aus / n, snippets)
    return {"lauf": lauf, "installieren": installieren, "confd": confd, "snippets": snippets, "dienst": dienst}


def test_abgleich_nicht_eingerichtet_ist_still(abgleich):
    r = abgleich["lauf"]()
    assert r.returncode == 0 and "not set up" in r.stdout, r.stdout + r.stderr


def test_abgleich_gleich_endet_mit_0(abgleich):
    abgleich["installieren"]()
    r = abgleich["lauf"]()
    assert r.returncode == 0 and r.stdout.strip() == "", r.stdout + r.stderr


def test_abgleich_abweichung_nennt_datei_und_einen_befehl(abgleich):
    abgleich["installieren"]()
    zone = abgleich["confd"] / "probe-zone.conf"
    zone.write_text(zone.read_text().replace("rate=10r/s", "rate=20r/s"))
    vorher = {p: p.read_text() for p in (*abgleich["confd"].iterdir(), *abgleich["snippets"].iterdir())}
    r = abgleich["lauf"]()
    assert r.returncode == 3, r.stdout + r.stderr
    assert "probe-zone.conf" in r.stdout and "rate=20r/s" in r.stdout
    befehle = [z for z in r.stdout.splitlines() if z.startswith("sudo env ")]
    assert len(befehle) == 1 and befehle[0].endswith("nginx.py anwenden") and "FR_DIENST=" + str(abgleich["dienst"]) in befehle[0], r.stdout
    # nichts installiert, nichts verändert
    assert {p: p.read_text() for p in (*abgleich["confd"].iterdir(), *abgleich["snippets"].iterdir())} == vorher


def test_abgleich_fehlende_einzeldatei_ist_abweichung(abgleich):
    abgleich["installieren"]()
    (abgleich["snippets"] / "probe-konnektor.inc").unlink()
    r = abgleich["lauf"]()
    assert r.returncode == 3 and "probe-konnektor.inc" in r.stdout and "missing" in r.stdout


def test_abgleich_fehler_endet_mit_1(abgleich):
    r = abgleich["lauf"](FR_DIENST="")
    assert r.returncode == 1 and "ERROR" in r.stderr
    r = abgleich["lauf"](FR_INSTANZ="")
    assert r.returncode == 1



# ---------- Anwenden (von Hand, mit Sicherung und Rückweg) ----------

def _anwenden(abgleich, tmp_path, test_ok=True):
    log = tmp_path / "ng.log"
    test = tmp_path / "ng-test.sh"
    test.write_text("#!/bin/sh\necho test >> " + str(log) + "\n[ " + ("1" if test_ok else "0") + " = 1 ]\n")
    laden = tmp_path / "ng-laden.sh"
    laden.write_text("#!/bin/sh\necho laden >> " + str(log) + "\n")
    for f in (test, laden):
        f.chmod(0o755)
    env = {**SAUBER, "FR_WURZEL": str(tmp_path), "FR_INSTANZ": "probe", "FR_TITEL": "Probe", "FR_DIENST": str(abgleich["dienst"]),
           "FR_NGINX_SNIPPETS": str(abgleich["snippets"]), "EI_NGINX_CONFD": str(abgleich["confd"]), "FR_SUDO": "",
           "EI_NGINX_TEST": str(test), "EI_NGINX_LADEN": str(laden)}
    r = subprocess.run([str(BETRIEB / "nginx.py"), "anwenden"], env=env, capture_output=True, text=True)
    return r, (log.read_text().split() if log.exists() else [])


def test_anwenden_installiert_prueft_und_laedt_neu(abgleich, tmp_path):
    abgleich["installieren"]()
    zone = abgleich["confd"] / "probe-zone.conf"
    soll = zone.read_text()
    zone.write_text(soll.replace("rate=10r/s", "rate=99r/s"))
    r, log = _anwenden(abgleich, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert zone.read_text() == soll and log == ["test", "laden"]
    sicherung = list((abgleich["dienst"] / "nginx-sicherung").iterdir())
    assert len(sicherung) == 1 and "rate=99r/s" in (sicherung[0] / "probe-zone.conf").read_text()
    assert abgleich["lauf"]().returncode == 0
    # gleich: nichts zu tun, kein Neuladen
    r, log = _anwenden(abgleich, tmp_path)
    assert r.returncode == 0 and "nothing to do" in r.stdout and log == ["test", "laden"]


def test_anwenden_rollt_bei_fehlgeschlagenem_nginx_test_zurueck(abgleich, tmp_path):
    abgleich["installieren"]()
    zone = abgleich["confd"] / "probe-zone.conf"
    kaputt = zone.read_text().replace("rate=10r/s", "rate=99r/s")
    zone.write_text(kaputt)
    (abgleich["snippets"] / "probe-konnektor.inc").unlink()      # fehlte vorher: muss nach dem Rückweg wieder fehlen
    r, log = _anwenden(abgleich, tmp_path, test_ok=False)
    assert r.returncode == 1 and "restoring the backup" in r.stderr, r.stdout + r.stderr
    assert log == ["test"]                                          # nie neu geladen
    assert zone.read_text() == kaputt and not (abgleich["snippets"] / "probe-konnektor.inc").exists()
    assert (abgleich["snippets"] / "probe-konnektor-orte.inc").exists()


def test_einrichten_lehnt_ungueltige_eigene_adressen_ab(tmp_path):
    basis = {**SAUBER, "FR_WURZEL": str(tmp_path), "FR_INSTANZ": "probe", "FR_TITEL": "Probe", "EI_ZIEL": str(tmp_path / "soll")}
    for schlecht in ("1.2.3.4;", "0.0.0.0/0", "1.2.3.4/33", "....", "*", "a b}", "::/0", "\u0661.\u0662.\u0663.\u0664"):
        r = subprocess.run(["bash", str(BETRIEB / "einrichten.sh"), "--erzeugen"], env={**basis, "FR_EIGENE_ADRESSEN": schlecht},
                           capture_output=True, text=True)
        assert r.returncode == 1 and "not an address" in r.stdout, (schlecht, r.stdout)
    for gut in ("192.0.2.0/24", "2001:db8::/32", "203.0.113.5 2001:db8::5"):
        r = subprocess.run(["bash", str(BETRIEB / "einrichten.sh"), "--erzeugen"], env={**basis, "FR_EIGENE_ADRESSEN": gut},
                           capture_output=True, text=True)
        assert r.returncode == 0, (gut, r.stdout)
