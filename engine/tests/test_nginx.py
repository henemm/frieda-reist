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
    # Zone der Reise-Bausteine (Rückmeldedienst), ebenfalls mit dem Schlüssel ohne die eigenen Adressen (#316)
    assert re.search(r"limit_req_zone \$probe_schluessel zone=probe_api:1m rate=120r/m;", zone)
    assert zone.count("limit_req_zone") == 4
    # keine Namen aus der gemeinsamen Datei
    assert not re.search(r"zone=(login|frieda\w*)\b", zone)
    assert re.search(r"geo \$probe_eigen \{[^}]*127\.0\.0\.1 1;[^}]*::1 1;", zone, re.S)
    assert re.search(r'map \$probe_eigen \$probe_schluessel \{[^}]*0 \$binary_remote_addr;[^}]*1 "";', zone, re.S)


def test_eigene_adressen_sind_einstellbar(tmp_path):
    zone = (erzeugen(tmp_path, FR_EIGENE_ADRESSEN="192.0.2.7 2001:db8::7") / "probe-zone.conf").read_text()
    assert "192.0.2.7 1;" in zone and "2001:db8::7 1;" in zone and "127.0.0.1 1;" in zone and "::1 1;" in zone


def test_einrichten_meldet_die_zone_der_reise_bausteine_nicht_mehr_als_fehlend(tmp_path):
    env = {**SAUBER, "FR_WURZEL": str(tmp_path), "FR_INSTANZ": "probe", "FR_TITEL": "Probe", "EI_ZIEL": str(tmp_path / "soll")}
    r = subprocess.run(["bash", str(BETRIEB / "einrichten.sh")], env=env, capture_output=True, text=True)
    assert "does not define yet" not in r.stdout + r.stderr


def test_orte_nutzen_die_drei_zonen(tmp_path):
    conf = (erzeugen(tmp_path) / "probe-konnektor-orte.inc").read_text()
    assert not re.search(r"zone=probe_api\b", conf)

    def ort(kopf):
        i = conf.index(kopf)
        return conf[i:conf.index("}", i)]   # die Orte enthalten keine verschachtelten Blöcke
    mcp = ort("location = /mcp")
    assert "zone=probe_mcp burst=40 nodelay" in mcp and "proxy_buffering off" in mcp and "proxy_read_timeout 300s" in mcp
    assert "zone=probe_anmelden burst=10 nodelay" in ort("location = /anmelden")
    for frei in ("location ^~ /.well-known/oauth-", "location ^~ /schrift/"):
        assert "limit_req" not in ort(frei), frei
    # /token und /register: großzügige Drossel der Zone _mcp (#552, AC-11; test_nginx_helfer.py::test_echte_vorlage_mit_drossel)
    for mcp_ort in ("location = /token", "location = /register"):
        assert "zone=probe_mcp burst=40 nodelay" in ort(mcp_ort), mcp_ort
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


# ---------- Zone der Reise-Bausteine zieht aus der gemeinsamen Datei um (#316) ----------

GETEILT = """# Rate-Limit-Zonen für Login
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

# Rückmeldedienst der Reise-Seiten: zweite Bremse vor dem Dienst,
# der selbst je Reise drosselt.
limit_req_zone $binary_remote_addr zone=probe_api:1m rate=30r/m;

# Anderer Dienst
limit_req_zone $binary_remote_addr zone=mcp_api:10m rate=20r/s;
"""
GETEILT_NACHHER = """# Rate-Limit-Zonen für Login
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

# Anderer Dienst
limit_req_zone $binary_remote_addr zone=mcp_api:10m rate=20r/s;
"""


def test_abgleich_meldet_zone_in_fremder_datei(abgleich):
    abgleich["installieren"]()
    (abgleich["confd"] / "limit-req.conf").write_text(GETEILT)
    r = abgleich["lauf"]()
    assert r.returncode == 3 and "limit-req.conf" in r.stdout and "probe_api" in r.stdout, r.stdout + r.stderr
    (abgleich["confd"] / "limit-req.conf").write_text(GETEILT_NACHHER)
    assert abgleich["lauf"]().returncode == 0
    # Kommentare, die den Namen nennen, und Zonen anderer Namen zählen nicht
    (abgleich["confd"] / "andere.conf").write_text("# früher zone=probe_api:1m\nlimit_req_zone $binary_remote_addr zone=probe_apix:1m rate=1r/s;\n")
    assert abgleich["lauf"]().returncode == 0


def test_anwenden_zieht_die_zone_in_einem_lauf_um(abgleich, tmp_path):
    abgleich["installieren"]()
    zone = abgleich["confd"] / "probe-zone.conf"
    soll = zone.read_text()
    zone.write_text(re.sub(r"limit_req_zone \$probe_schluessel zone=probe_api[^\n]*\n", "", soll))   # Stand vor dem Umzug
    geteilt = abgleich["confd"] / "limit-req.conf"
    geteilt.write_text(GETEILT)
    geteilt.chmod(0o640)
    r, log = _anwenden(abgleich, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert zone.read_text() == soll and geteilt.read_text() == GETEILT_NACHHER and log == ["test", "laden"]
    assert oct(geteilt.stat().st_mode & 0o777) == "0o640"
    sicherung = next((abgleich["dienst"] / "nginx-sicherung").iterdir())
    assert GETEILT in [p.read_text() for p in sicherung.rglob("limit-req.conf")]
    assert abgleich["lauf"]().returncode == 0
    r, log = _anwenden(abgleich, tmp_path)
    assert r.returncode == 0 and "nothing to do" in r.stdout and log == ["test", "laden"]


def test_anwenden_rollt_auch_die_fremde_datei_zurueck(abgleich, tmp_path):
    abgleich["installieren"]()
    zone = abgleich["confd"] / "probe-zone.conf"
    alt = re.sub(r"limit_req_zone \$probe_schluessel zone=probe_api[^\n]*\n", "", zone.read_text())
    zone.write_text(alt)
    geteilt = abgleich["confd"] / "limit-req.conf"
    geteilt.write_text(GETEILT)
    r, log = _anwenden(abgleich, tmp_path, test_ok=False)
    assert r.returncode == 1 and log == ["test"], r.stdout + r.stderr
    assert zone.read_text() == alt and geteilt.read_text() == GETEILT


def test_erste_einrichtung_zieht_die_zone_ebenfalls_um(abgleich, tmp_path):
    (abgleich["confd"] / "limit-req.conf").write_text(GETEILT)
    r, log = _anwenden(abgleich, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (abgleich["confd"] / "limit-req.conf").read_text() == GETEILT_NACHHER and (abgleich["confd"] / "probe-zone.conf").exists()


@pytest.mark.parametrize("inhalt", [
    GETEILT + "limit_req_zone $binary_remote_addr zone=probe_api:1m rate=30r/m;\n",                 # doppelt
    "limit_req_zone $binary_remote_addr zone=probe_api:1m rate=30r/m; limit_req_zone $x zone=y:1m rate=1r/s;\n",   # mehrere Direktiven in einer Zeile
])
def test_mehrdeutige_fremde_datei_wird_nicht_angefasst(abgleich, tmp_path, inhalt):
    abgleich["installieren"]()
    geteilt = abgleich["confd"] / "limit-req.conf"
    geteilt.write_text(inhalt)
    zone = abgleich["confd"] / "probe-zone.conf"
    vorher = zone.read_text()
    r, log = _anwenden(abgleich, tmp_path)
    assert r.returncode == 1 and "limit-req.conf" in r.stderr and log == [], r.stdout + r.stderr
    assert geteilt.read_text() == inhalt and zone.read_text() == vorher


@pytest.mark.skipif(not shutil.which("nginx"), reason="nginx fehlt")
def test_nginx_nimmt_vorher_und_nachher_und_lehnt_doppelte_zone_ab(abgleich, tmp_path):
    abgleich["installieren"]()
    confd = abgleich["confd"]
    nachher = (confd / "probe-zone.conf").read_text()
    temp = " ".join(f"{n}_temp_path {tmp_path}/{n};" for n in ("client_body", "proxy", "fastcgi", "uwsgi", "scgi"))
    benutzer = "user root;" if os.geteuid() == 0 else ""

    def pruefe():
        (tmp_path / "ng.conf").write_text(f"{benutzer} pid {tmp_path}/ng.pid; error_log {tmp_path}/ng.log; events {{}}\n"
                                          f"http {{ access_log off; {temp} include {confd}/*.conf; }}\n")
        return subprocess.run(["nginx", "-t", "-e", str(tmp_path / "ng.log"), "-c", str(tmp_path / "ng.conf"), "-p", str(tmp_path)],
                              capture_output=True, text=True)
    (confd / "limit-req.conf").write_text(GETEILT_NACHHER)
    assert pruefe().returncode == 0
    (confd / "limit-req.conf").write_text(GETEILT)
    assert pruefe().returncode != 0          # doppelte Zone: genau der Zwischenstand, den der eine Lauf vermeidet
    (confd / "probe-zone.conf").write_text(re.sub(r"limit_req_zone \$probe_schluessel zone=probe_api[^\n]*\n", "", nachher))
    assert pruefe().returncode == 0          # Stand vor dem Umzug


def test_reise_zone_traegt_zwei_seitenaufrufe_kurz_hintereinander(tmp_path):
    """Ein Seitenaufruf macht sieben Abfragen an api/ (ich, belege, rueckmeldungen, brett, aufgaben, stand, Zeitzeichen).
    Wer neu lädt, ruft innerhalb weniger Sekunden ein zweites Mal auf. Bei 30 pro Minute lief das in 429 und über fail2ban in die Sperre (4.11.2026)."""
    abfragen = 7
    zone = (erzeugen(tmp_path) / "probe-zone.conf").read_text()
    rate = int(re.search(r"zone=probe_api:\d+m rate=(\d+)r/m;", zone).group(1)) / 60      # Abfragen je Sekunde
    bursts = {int(b) for b in re.findall(r"limit_req zone=__ZONE__ burst=(\d+) nodelay", (BETRIEB / "vorlagen" / "nginx-reise.conf").read_text())}
    assert len(bursts) == 1
    assert min(bursts) + rate * 3 >= 2 * abfragen, (min(bursts), rate)


# ---------- Installieren über das Hilfsprogramm (#445, Teil 3, Spec docs/specs/betrieb/nginx-orte-automatisch-445.md) ----------

def _helfer_attrappe(tmp_path, snippets, ausgang=0, stderr=""):
    """Attrappe des Hilfsprogramms: protokolliert Aufruf und stdin; bei Ausgang 0 schreibt sie stdin in die Orte-Datei."""
    protokoll, eingabe = tmp_path / "helfer.log", tmp_path / "helfer.stdin"
    schreiben = f"cp {eingabe} {snippets}/probe-konnektor-orte.inc\n" if ausgang == 0 else ""
    fehler = f"echo grund-{ausgang} >&2\n" if stderr else ""
    helfer = tmp_path / "helfer.sh"
    helfer.write_text(f'#!/bin/sh\necho "helfer $#" >> {protokoll}\ncat > {eingabe}\n{schreiben}{fehler}exit {ausgang}\n')
    helfer.chmod(0o755)
    return helfer, protokoll, eingabe


def _orte_aendern(abgleich):
    orte = abgleich["snippets"] / "probe-konnektor-orte.inc"
    orte.write_text(orte.read_text().replace("location ^~ /info/", "location ^~ /alt-info/"))
    return orte


def _installieren_lauf(abgleich, tmp_path, **extra):
    env = {**SAUBER, "FR_WURZEL": str(tmp_path), "FR_INSTANZ": "probe", "FR_TITEL": "Probe", "FR_DIENST": str(abgleich["dienst"]),
           "FR_NGINX_SNIPPETS": str(abgleich["snippets"]), "EI_NGINX_CONFD": str(abgleich["confd"]), "FR_SUDO": "", **extra}
    return subprocess.run([str(BETRIEB / "nginx.py"), "installieren"], env=env, capture_output=True, text=True)


def test_installieren_nur_orte_abweichend_ruft_das_hilfsprogramm_mit_dem_soll(abgleich, tmp_path):
    abgleich["installieren"]()
    orte = _orte_aendern(abgleich)
    helfer, protokoll, eingabe = _helfer_attrappe(tmp_path, abgleich["snippets"])
    r = _installieren_lauf(abgleich, tmp_path, FR_NGINX_HELFER=str(helfer))
    assert r.returncode == 0, r.stdout + r.stderr
    assert protokoll.read_text().splitlines() == ["helfer 0"]            # genau ein Aufruf, ohne Argumente
    soll = erzeugen(tmp_path, FR_NGINX_SNIPPETS=str(abgleich["snippets"])) / "probe-konnektor-orte.inc"
    assert eingabe.read_text() == soll.read_text() == orte.read_text()
    assert abgleich["lauf"]().returncode == 0                           # danach alles gleich


def test_installieren_haengt_fr_sudo_vor_das_hilfsprogramm(abgleich, tmp_path):
    abgleich["installieren"]()
    _orte_aendern(abgleich)
    helfer, _, _ = _helfer_attrappe(tmp_path, abgleich["snippets"])
    sudo_log = tmp_path / "sudo.log"
    sudo = tmp_path / "sudo-attrappe"
    # printf statt echo: echo nähme das erste Argument „-n“ als eigene Option und schriebe es nicht
    sudo.write_text(f'#!/bin/sh\nprintf "%s\\n" "$*" >> {sudo_log}\nshift\nexec "$@"\n')
    sudo.chmod(0o755)
    r = _installieren_lauf(abgleich, tmp_path, FR_NGINX_HELFER=str(helfer), FR_SUDO=f"{sudo} -n")
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"-n {helfer}" in sudo_log.read_text().splitlines()


@pytest.mark.parametrize("was", ["zone", "konnektor", "orte_fehlt", "fremde_zone"])
def test_installieren_ruft_nichts_auf_wenn_mehr_als_die_orte_abweicht(abgleich, tmp_path, was):
    abgleich["installieren"]()
    _orte_aendern(abgleich)
    if was == "zone":
        zone = abgleich["confd"] / "probe-zone.conf"
        zone.write_text(zone.read_text().replace("rate=10r/s", "rate=20r/s"))
    elif was == "konnektor":
        inc = abgleich["snippets"] / "probe-konnektor.inc"
        inc.write_text(inc.read_text() + "# geändert\n")
    elif was == "orte_fehlt":
        (abgleich["snippets"] / "probe-konnektor-orte.inc").unlink()
    else:
        (abgleich["confd"] / "drossel.conf").write_text("limit_req_zone $binary_remote_addr zone=probe_api:1m rate=1r/s;\n")
    helfer, protokoll, _ = _helfer_attrappe(tmp_path, abgleich["snippets"])
    r = _installieren_lauf(abgleich, tmp_path, FR_NGINX_HELFER=str(helfer))
    assert r.returncode == 3, r.stdout + r.stderr
    assert not protokoll.exists()
    assert "differs" in r.stdout or "missing" in r.stdout or "defines the zone" in r.stdout
    assert r.stdout.strip().splitlines()[-1].startswith("install skipped: other files differ")     # Gegenprüfung F006


def test_installieren_ohne_hilfsprogramm_endet_mit_5_ohne_sudo(abgleich, tmp_path):
    abgleich["installieren"]()
    _orte_aendern(abgleich)
    sudo_log = tmp_path / "sudo.log"
    sudo = tmp_path / "sudo-attrappe"
    sudo.write_text(f'#!/bin/sh\necho "$@" >> {sudo_log}\nexit 1\n')
    sudo.chmod(0o755)
    fehlt = tmp_path / "gibt-es-nicht"
    r = _installieren_lauf(abgleich, tmp_path, FR_NGINX_HELFER=str(fehlt), FR_SUDO=str(sudo))
    assert r.returncode == 5, r.stdout + r.stderr
    assert f"helper missing ({fehlt})" in r.stdout
    assert not sudo_log.exists()


def test_installieren_vorgabe_des_hilfsprogramms(abgleich, tmp_path):
    abgleich["installieren"]()
    _orte_aendern(abgleich)
    r = _installieren_lauf(abgleich, tmp_path)
    assert r.returncode == 5 and "helper missing (/usr/local/sbin/probe-nginx-orte-installieren)" in r.stdout, r.stdout + r.stderr


def test_installieren_ausgang_2_des_hilfsprogramms_ist_kein_fehler(abgleich, tmp_path):
    abgleich["installieren"]()
    _orte_aendern(abgleich)
    helfer, protokoll, _ = _helfer_attrappe(tmp_path, abgleich["snippets"], ausgang=2)
    r = _installieren_lauf(abgleich, tmp_path, FR_NGINX_HELFER=str(helfer))
    assert protokoll.exists() and r.returncode == 3, r.stdout + r.stderr     # Ergebnis der erneuten Prüfung, nicht 5


@pytest.mark.parametrize("ausgang", [3, 4, 5, 6, 7])
def test_installieren_scheiterndes_hilfsprogramm_endet_mit_5_und_nennt_den_ausgang(abgleich, tmp_path, ausgang):
    abgleich["installieren"]()
    _orte_aendern(abgleich)
    helfer, _, _ = _helfer_attrappe(tmp_path, abgleich["snippets"], ausgang=ausgang, stderr=True)
    r = _installieren_lauf(abgleich, tmp_path, FR_NGINX_HELFER=str(helfer))
    assert r.returncode == 5, r.stdout + r.stderr
    assert f"exit {ausgang}" in r.stdout and f"grund-{ausgang}" in r.stdout


def test_installieren_ohne_abweichung_tut_nichts(abgleich, tmp_path):
    abgleich["installieren"]()
    helfer, protokoll, _ = _helfer_attrappe(tmp_path, abgleich["snippets"])
    r = _installieren_lauf(abgleich, tmp_path, FR_NGINX_HELFER=str(helfer))
    assert r.returncode == 0 and not protokoll.exists(), r.stdout + r.stderr


def test_doku_nennt_nginx_orte_hilfsprogramm():
    """AC-20: docs/betrieb.md nennt Hilfsprogramm und Einstellung; die Orte-Datei wird nicht mehr „von Hand“ übernommen."""
    doku = (BETRIEB.parent / "docs" / "betrieb.md").read_text(encoding="utf-8")
    assert "nginx-orte-installieren" in doku and "FR_NGINX_HELFER" in doku
    saetze = re.split(r"(?<=[.!?])\s+|\n\s*\n", doku)
    falsch = [s for s in saetze if "konnektor-orte.inc" in s and re.search(r"von Hand|nie automatisch", s)]
    assert not falsch, falsch
    doc = nginx_modul().__doc__
    assert "installieren" in doc and "#445" in doc


# ---------- #552, AC-8: Reise-Bausteine nur über den Helfer ----------

def test_reise_baustein_ueber_helfer(tmp_path):
    """freischalten.sh legt den Baustein nicht mehr selbst an (kein install/test/cat/rm, kein nginx -t, kein Reload), sondern
    ruft den Reise-Helfer (FR_NGINX_REISE_HELFER, davor FR_SUDO) mit dem Reisenamen auf stdin; dessen Ausgabe ist der Pfad.
    Link und seiten.json entstehen wie bisher."""
    ENGINE = BETRIEB.parent / "engine"
    snippets = tmp_path / "snippets"
    snippets.mkdir()
    aufrufe = tmp_path / "helfer.log"
    helfer = tmp_path / "helfer.sh"
    helfer.write_text(f'#!/bin/sh\nread -r reise\necho "$# $* $reise" >> {aufrufe}\necho "$reise-0123456789abcdef01234567"\n'
                      f'[ -e {tmp_path}/schon-da ] && exit 2\ntouch {tmp_path}/schon-da\nexit 0\n')
    helfer.chmod(0o755)
    abruf = tmp_path / "abruf.sh"
    abruf.write_text("#!/bin/sh\necho 200\n")
    abruf.chmod(0o755)
    repo = tmp_path / "repo"
    (repo / "reisen/beispielreise").mkdir(parents=True)
    (repo / "reisen/beispielreise/reise.yaml").write_text("titel: x\n")
    (repo / "engine").symlink_to(ENGINE)
    env = {**SAUBER, "FR_WURZEL": str(repo), "FR_INSTANZ": "probe", "FR_SEITEN": str(tmp_path / "seiten"),
           "FR_ABLAGE": str(tmp_path / "ablage"), "FR_KONNEKTOR": str(tmp_path / "konnektor"), "FR_RM_PORT": "8871",
           "FR_ADRESSE": "https://example.invalid", "FR_NGINX_SNIPPETS": str(snippets), "FR_SUDO": "",
           "FR_NGINX_REISE_HELFER": str(helfer), "FS_ABRUF": str(abruf), "FS_NGINX_TEST": "false", "FS_NGINX_LADEN": "false", "FS_WARTEN": "0", "FS_429_WARTEN": "0"}
    for _ in range(2):
        r = subprocess.run([str(BETRIEB / "freischalten.sh"), "beispielreise"], env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "Seite: https://example.invalid/beispielreise-0123456789abcdef01234567/" in r.stdout
    assert aufrufe.read_text().splitlines() == ["0  beispielreise", "0  beispielreise"]
    assert list(snippets.iterdir()) == []
    links = (tmp_path / "konnektor" / "seiten.json").read_text()
    assert "https://example.invalid/beispielreise-0123456789abcdef01234567/" in links
    # Scheitert der Helfer, bleibt die Reise ohne Link und der Grund steht als ERROR-Zeile da
    helfer.write_text("#!/bin/sh\necho 'nginx -t failed' >&2\nexit 4\n")
    r = subprocess.run([str(BETRIEB / "freischalten.sh"), "beispielreise"], env=env, capture_output=True, text=True)
    assert r.returncode != 0 and "ERROR" in r.stdout and "Seite:" not in r.stdout, r.stdout


# ---------- #552, Entscheidung 9: Lesen ohne sudo, Installieren mit der Gruppe der Instanz ----------

def test_anwenden_installiert_mit_gruppe_der_instanz():
    """nginx.py anwenden (mit Root-Rechten) installiert die Bausteine der Instanz mit 0640 root:<Gruppe>; eine fremde
    conf.d-Datei behält Modus und Besitz. Ohne Root (Tests) bleibt es beim Modus."""
    m = nginx_modul()
    assert m.install_befehl("640", "/q/probe-konnektor.inc", "/etc/nginx/snippets", "reisegruppe", root=True) == \
        ["install", "-m", "640", "-o", "root", "-g", "reisegruppe", "/q/probe-konnektor.inc", "/etc/nginx/snippets/"]
    assert m.install_befehl("640", "/q/x.conf", "/etc/nginx/conf.d", "reisegruppe", root=False) == \
        ["install", "-m", "640", "/q/x.conf", "/etc/nginx/conf.d/"]
    assert m.install_befehl("644", "/q/limit.conf", "/etc/nginx/conf.d", None, root=True) == \
        ["install", "-m", "644", "/q/limit.conf", "/etc/nginx/conf.d/"]
    assert m.MODI == {"zone": "640", "orte": "640"}


def test_befehl_nennt_die_gruppe(monkeypatch):
    """Der Befehl aus der Meldung trägt die Gruppe des Dienstbenutzers (FR_GRUPPE, sonst die Gruppe des Aufrufers)."""
    m = nginx_modul()
    monkeypatch.setenv("FR_GRUPPE", "reisegruppe")
    assert "FR_GRUPPE=reisegruppe" in m.befehl("probe", "/srv/probe/_dienst", "/etc/nginx/snippets")


def test_pruefen_liest_ohne_sudo_und_ueberspringt_unlesbare_fremde_dateien(abgleich):
    """pruefen liest die Bausteine der Instanz ohne sudo (lesbar über die Gruppe); eine fremde conf.d-Datei, die der
    Dienstbenutzer nicht lesen darf, wird übersprungen statt den Abgleich scheitern zu lassen."""
    if os.geteuid() == 0:
        pytest.skip("als root ist jede Datei lesbar")
    abgleich["installieren"]()
    fremd = abgleich["confd"] / "fremd-logging.conf"
    fremd.write_text("access_log off;\n")
    fremd.chmod(0)
    try:
        r = abgleich["lauf"](FR_SUDO="false")
        assert r.returncode == 0 and r.stdout.strip() == "", r.stdout + r.stderr
    finally:
        fremd.chmod(0o600)
