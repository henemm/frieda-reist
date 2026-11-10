"""Tests für das Hilfsprogramm mit Root-Rechten, das die Orte-Datei des Konnektors installiert (#445, Teil 3;
betrieb/vorlagen/nginx-orte-installieren.py, Spec docs/specs/betrieb/nginx-orte-automatisch-445.md).

Muster: test_units_helfer.py. Die Funktionen laufen direkt mit Parametern in einem Testordner, ohne root; erfundene Instanz
„probe“, Zonen probe_mcp/probe_anmelden/probe_konto, Snippets-Pfad im include fest /etc/nginx/snippets (Vorgabe von
einrichten.sh). Unter /etc wird nichts gelesen oder geschrieben.

Schnittstelle des Hilfsprogramms, die diese Tests festlegen:
- Konstanten INSTANZ, SNIPPETS (Pfad im include und Vorgabe-Zielordner), NGINX="/usr/sbin/nginx", SYSTEMCTL="/usr/bin/systemctl",
  SICHERUNG="/var/lib/<instanz>-nginx-sicherung", MAX_BYTES=64 KiB.
- Ausnahme Abgelehnt (Ausgang 3).
- installieren(neu: bytes, snippets=…, sicherung=…, sperre=…, nginx=…, testen=…, neu_laden=…) -> 0, 2, 4, 5 oder 6;
  Abgelehnt bei Ausgang 3. testen() und neu_laden() geben True/False zurück.
- main(argv, daten=None, **kw) -> Ausgang; kw wie bei installieren. Kein Pfad endet mit einem Traceback.
- nginx_testen() und nginx_neu_laden(): Vorgaben für testen/neu_laden, feste Programme und Umgebung.
"""
import fcntl
import importlib.machinery
import importlib.util
import os
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

BETRIEB = Path(__file__).resolve().parents[2] / "betrieb"
VORLAGE = BETRIEB / "vorlagen" / "nginx-orte-installieren.py"
ORTE_VORLAGE = BETRIEB / "vorlagen" / "nginx-konnektor-orte.inc"
SAUBER = {k: v for k, v in os.environ.items() if not k.startswith(("FR_", "RM_", "KN_", "EA_", "VF_", "FS_", "WA_", "EI_"))}
NAME = "probe-konnektor-orte.inc"
INC = "include /etc/nginx/snippets/probe-konnektor.inc;"

BASIS = f"""# Orte des Konnektors (erfundene Instanz probe)
location = /mcp {{
    limit_req zone=probe_mcp burst=40 nodelay;
    limit_req_status 429;
    {INC}
    # Streamable HTTP, ein Kommentar im Block mit Umlauten: ungepuffert
    proxy_buffering off;
    proxy_read_timeout 300s;
}}
location = /token                  {{ {INC} }}
location ^~ /.well-known/oauth-    {{ {INC} }}
location ~ ^/(?:konto|abmelden)?$ {{
    limit_req zone=probe_konto burst=20 nodelay;
    limit_req_status 429;
    {INC}
}}
"""
NEU = BASIS + f"location ^~ /info/                 {{ {INC} }}\n"


def ersetze(text, snippets="/etc/nginx/snippets"):
    return (text.replace("__INSTANZ__", "probe").replace("__SNIPPETS__", snippets).replace("__ZONE_MCP__", "probe_mcp")
            .replace("__ZONE_ANMELDEN__", "probe_anmelden").replace("__ZONE_KONTO__", "probe_konto"))


def lade(datei, name="nginx_helfer"):
    # Das erzeugte Hilfsprogramm hat keine Endung .py: Lader ausdrücklich angeben
    spec = importlib.util.spec_from_file_location(name, datei, loader=importlib.machinery.SourceFileLoader(name, str(datei)))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


@pytest.fixture
def h(tmp_path):
    """Hilfsprogramm aus der Vorlage, Platzhalter ersetzt; Testordner als Snippets-Ordner mit installierter Orte-Datei;
    Attrappen für nginx -t und Reload (zählen Aufrufe, Ergebnis einstellbar)."""
    text = ersetze(VORLAGE.read_text(encoding="utf-8"))
    datei = tmp_path / "helfer.py"
    datei.write_text(text, encoding="utf-8")
    modul = lade(datei)
    snippets = tmp_path / "snippets"
    snippets.mkdir()
    (snippets / NAME).write_text(BASIS, encoding="utf-8")
    (snippets / NAME).chmod(0o640)
    nginx = tmp_path / "nginx"
    nginx.write_text("#!/bin/sh\n")
    nginx.chmod(0o755)
    zustand = {"tests": [], "laden": [], "test_ergebnisse": [], "laden_ok": True}

    def testen():
        ergebnis = zustand["test_ergebnisse"].pop(0) if zustand["test_ergebnisse"] else True
        zustand["tests"].append((snippets / NAME).read_text(encoding="utf-8"))
        return ergebnis

    def neu_laden():
        zustand["laden"].append(1)
        return zustand["laden_ok"]

    kw = {"snippets": str(snippets), "sicherung": str(tmp_path / "sicherung"), "sperre": str(tmp_path / "sperre"),
          "nginx": str(nginx), "testen": testen, "neu_laden": neu_laden}

    def lauf(neu):
        if isinstance(neu, str):
            neu = neu.encode("utf-8")
        return modul.installieren(neu, **kw)

    def main(neu, argv=("helfer",)):
        if isinstance(neu, str):
            neu = neu.encode("utf-8")
        return modul.main(list(argv), neu, **kw)

    return {"m": modul, "lauf": lauf, "main": main, "kw": kw, "snippets": snippets, "ziel": snippets / NAME,
            "sicherung": tmp_path / "sicherung", "z": zustand, "tmp": tmp_path, "text": text}


def abgelehnt(h, neu):
    """Ausgang 3 über main, installierte Datei unverändert, kein nginx-Aufruf, keine Reste im Snippets-Ordner."""
    vorher = h["ziel"].read_bytes() if h["ziel"].is_file() else None
    namen_vorher = sorted(p.name for p in h["snippets"].iterdir())
    assert h["main"](neu) == 3
    assert not h["z"]["tests"] and not h["z"]["laden"]
    nachher = h["ziel"].read_bytes() if h["ziel"].is_file() else None
    assert nachher == vorher
    assert sorted(p.name for p in h["snippets"].iterdir()) == namen_vorher


def im_block(zeile):
    """Zeile zusätzlich in den Block /mcp."""
    return NEU.replace("    proxy_buffering off;\n", f"    proxy_buffering off;\n    {zeile}\n", 1)


def oben(text):
    return NEU + text + "\n"


# ---------- AC-1: die echte Vorlage besteht die Grammatik und wird installiert ----------

def test_ac1_echte_vorlage_aus_einrichten_wird_installiert(tmp_path):
    ziel = tmp_path / "soll"
    env = {**SAUBER, "FR_WURZEL": str(tmp_path), "FR_INSTANZ": "probe", "FR_TITEL": "Probe", "FR_BENUTZER": "hans", "EI_ZIEL": str(ziel)}
    r = subprocess.run(["bash", str(BETRIEB / "einrichten.sh"), "--erzeugen"], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    modul = lade(ziel / "sbin" / "probe-nginx-orte-installieren", "nginx_helfer_echt")
    soll = (ziel / "nginx" / NAME).read_bytes()
    snippets = tmp_path / "snippets"
    snippets.mkdir()
    (snippets / NAME).write_text(BASIS, encoding="utf-8")
    nginx = tmp_path / "nginx-bin"
    nginx.write_text("")
    aufrufe = []
    rc = modul.installieren(soll, snippets=str(snippets), sicherung=str(tmp_path / "sicherung"), sperre=str(tmp_path / "sperre"),
                            nginx=str(nginx), testen=lambda: aufrufe.append("test") or True,
                            neu_laden=lambda: aufrufe.append("laden") or True)
    assert rc == 0
    assert (snippets / NAME).read_bytes() == soll
    assert oct((snippets / NAME).stat().st_mode & 0o777) == "0o640"
    assert aufrufe == ["test", "laden"]


def test_ac1_installieren_mit_basis(h):
    assert h["lauf"](NEU) == 0
    assert h["ziel"].read_text(encoding="utf-8") == NEU
    assert oct(h["ziel"].stat().st_mode & 0o777) == "0o640"
    assert h["z"]["tests"] == [NEU] and h["z"]["laden"] == [1]


# ---------- AC-2: nicht fangende Gruppe, gleiche Wirkung ----------

def test_ac2_vorlage_nutzt_nicht_fangende_gruppe_mit_gleicher_wirkung():
    text = ORTE_VORLAGE.read_text(encoding="utf-8")
    assert "location ~ ^/(?:konto|abmelden|authorize|gesund)?$ {" in text
    assert "~ ^/(konto" not in text
    alt, neu = re.compile(r"^/(konto|abmelden|authorize|gesund)?$"), re.compile(r"^/(?:konto|abmelden|authorize|gesund)?$")
    pfade = ["/", "/konto", "/abmelden", "/authorize", "/gesund", "/konto/", "/kontox", "/xkonto", "/beispielreise/", "/konto/a",
             "//", "/gesund?x", "/info/", "/mcp", "/Konto"]
    assert [bool(alt.match(p)) for p in pfade] == [bool(neu.match(p)) for p in pfade]
    assert neu.match("/") and neu.match("/konto") and not neu.match("/beispielreise/")


# ---------- AC-3: grammatikgerechte Änderungen laufen ohne Änderung des Hilfsprogramms durch ----------

@pytest.mark.parametrize("neu", [
    NEU,                                                                                         # neuer ^~-Ort an Segmentgrenze
    BASIS + f"location = /neu {{\n    limit_req zone=probe_anmelden burst=5 nodelay;\n    limit_req_status 429;\n    {INC}\n}}\n",
    BASIS.replace("burst=40", "burst=60").replace("burst=20", "burst=7"),                         # Burst geändert
    "# Neuer Kommentar: Größe, Öffnungszeiten\n\n" + BASIS,                                      # Kommentar mit Umlauten
    BASIS + f"location ^~ /.well-known/neu-  {{ {INC} }}\n",                                     # Präfix unter /.well-known/
    BASIS + f"location ~ ^/$ {{ {INC} }}\n",                                                     # Regex leer
    BASIS + f"location ~ ^/start$ {{ {INC} }}\n",                                                # Regex ein Wort
    BASIS + f"location ~ ^/(?:a-b|c_d|e1)$ {{ {INC} }}\n",                                       # Gruppe ohne ?
    BASIS + f"location = /x.y_z-1/a {{\n\t{INC}\n\tproxy_read_timeout 30s;\n}}\n",               # Tabs, Punkt im Pfad
    BASIS.replace("    limit_req zone=probe_mcp burst=40 nodelay;\n    limit_req_status 429;\n",
                  "    limit_req_status 429;\n    limit_req zone=probe_mcp burst=40 nodelay;\n"),       # andere Reihenfolge
    BASIS.replace(f"location = /token                  {{ {INC} }}\n", ""),                    # Ort entfernt
])
def test_ac3_grammatikgerechte_aenderung_wird_installiert(h, neu):
    assert h["lauf"](neu) == 0
    assert h["ziel"].read_text(encoding="utf-8") == neu


# ---------- AC-4 bis AC-6: Sicherheits-Negativfälle (Tabelle N-1 bis N-24, N-29 der Spec) ----------

ZWEI_INC = f"{INC} {INC}"
NEGATIV = {
    "N-1 proxy_pass": im_block("proxy_pass http://127.0.0.1:1;"),
    "N-2 alias": im_block("alias /etc/;"),
    "N-2 root": im_block("root /;"),
    "N-3 return mit Anführungszeichen": im_block('return 200 "x";'),
    "N-3 return": im_block("return 200 x;"),
    "N-3 rewrite": im_block("rewrite ^ /x;"),
    "N-4 add_header": im_block("add_header X y;"),
    "N-5 if": im_block("if ($x) { return 403; }"),
    "N-5 if ohne Variable": im_block("if (-f /x) { }"),
    "N-5 set": im_block("set $a b;"),
    "N-5 try_files": im_block("try_files /x =404;"),
    "N-5 error_page": im_block("error_page 404 /x;"),
    "N-5 access_by_lua": im_block("access_by_lua_block x;"),
    "N-5 fastcgi_pass": im_block("fastcgi_pass 127.0.0.1:9000;"),
    "N-6 fremdes include": NEU.replace(INC, "include /etc/nginx/other.conf;", 1),
    "N-6 include .bak": NEU.replace(INC, "include /etc/nginx/snippets/probe-konnektor.inc.bak;", 1),
    "N-6 include fremde Instanz": NEU.replace(INC, "include /etc/nginx/snippets/andere-konnektor.inc;", 1),
    "N-6 include anderer Ordner": NEU.replace(INC, "include /tmp/probe-konnektor.inc;", 1),
    "N-6 include mit Stern": NEU.replace(INC, "include /etc/nginx/snippets/probe-*.inc;", 1),
    "N-7 fremde Zone": NEU.replace("zone=probe_mcp", "zone=fremde"),
    "N-7 Zone der Reise-Bausteine": NEU.replace("zone=probe_mcp", "zone=probe_api"),
    "N-8 limit_req_zone im Block": im_block("limit_req_zone x zone=x:1m rate=1r/s;"),
    "N-8 limit_req_zone oben": oben("limit_req_zone x zone=x:1m rate=1r/s;"),
    "N-9 Variable im Wert": NEU.replace("proxy_read_timeout 300s;", "proxy_read_timeout $x;"),
    "N-9 $ im genauen Pfad": oben(f"location = /a$b {{ {INC} }}"),
    "N-9 $ mitten in Regex": oben(f"location ~ ^/a$b$ {{ {INC} }}"),
    "N-10 doppelte Anführungszeichen": NEU.replace("proxy_buffering off;", 'proxy_buffering "off";'),
    "N-10 einfache Anführungszeichen": NEU.replace("proxy_buffering off;", "proxy_buffering 'off';"),
    "N-10 Backtick": NEU.replace("proxy_buffering off;", "proxy_buffering `off`;"),
    "N-11 Zeilenfortsetzung": NEU.replace("proxy_buffering off;", "proxy_buffering \\\noff;"),
    "N-11 Fortsetzung im Kommentar": "# Kommentar \\\n" + NEU,
    "N-11 Backslash": NEU.replace("proxy_buffering off;", "proxy_buffering o\\ff;"),
    "N-12 CR": NEU.replace("\n", "\r\n"),
    "N-12 NUL": NEU + "\x00",
    "N-12 Steuerzeichen im Kommentar": "# Glocke \x07\n" + NEU,
    "N-12 DEL": NEU + "#\x7f\n",
    "N-12 ESC": NEU.replace("proxy_buffering off;", "proxy_buffering off;\x1b"),
    "N-13 NBSP": NEU.replace("proxy_buffering off;", "proxy_buffering off;"),
    "N-13 Nicht-ASCII im Kopf": oben(f"location = /ö {{ {INC} }}"),
    "N-13 NBSP vor location": oben(f" location = /x {{ {INC} }}"),
    "N-14 unverankerte Regex": oben(f"location ~ /konto {{ {INC} }}"),
    "N-14 Regex ohne $": oben(f"location ~ ^/konto {{ {INC} }}"),
    "N-14 Regex ohne ^": oben(f"location ~ /konto$ {{ {INC} }}"),
    "N-15 fangende Gruppe": NEU.replace("(?:konto|abmelden)", "(konto|abmelden)"),
    "N-16 .* in Regex": oben(f"location ~ ^/.*$ {{ {INC} }}"),
    "N-16 location /": oben(f"location / {{ {INC} }}"),
    "N-16 ^~ /": oben(f"location ^~ / {{ {INC} }}"),
    "N-16 = /": oben(f"location = / {{ {INC} }}"),
    "N-16 Modifikator ~*": oben(f"location ~* ^/x$ {{ {INC} }}"),
    "N-16 benannter Ort": oben(f"location @x {{ {INC} }}"),
    "N-6 Regex mit Punkt": oben(f"location ~ ^/a.b$ {{ {INC} }}"),
    "N-6 Regex mit Plus": oben(f"location ~ ^/a+$ {{ {INC} }}"),
    "N-6 Regex mit Klasse": oben(f"location ~ ^/[a-z]$ {{ {INC} }}"),
    "N-6 Regex Wort und Gruppe": oben(f"location ~ ^/x(?:a|b)$ {{ {INC} }}"),
    "N-6 Regex zwei Gruppen": oben(f"location ~ ^/(?:a)(?:b)$ {{ {INC} }}"),
    "N-6 Regex leere Alternative": oben(f"location ~ ^/(?:a|)$ {{ {INC} }}"),
    "N-6 Regex mit Schrägstrich": oben(f"location ~ ^/a/b$ {{ {INC} }}"),
    "N-29 Präfix ohne Segmentgrenze": oben(f"location ^~ /r {{ {INC} }}"),
    "N-29 /info ohne Schrägstrich": oben(f"location ^~ /info {{ {INC} }}"),
    "N-30 acme-challenge mit ^~": oben(f"location ^~ /.well-known/acme-challenge/ {{ {INC} }}"),
    "N-30 /.well-known/ allein": oben(f"location ^~ /.well-known/ {{ {INC} }}"),
    "N-30 Präfix überdeckt acme": oben(f"location ^~ /.well-known/a {{ {INC} }}"),
    "N-30 acme-challenge mit =": oben(f"location = /.well-known/acme-challenge/x {{ {INC} }}"),
    "N-17 ..": oben(f"location = /a/../b {{ {INC} }}"),
    "N-17 .. bei ^~": oben(f"location ^~ /a/../ {{ {INC} }}"),
    "N-17 //": oben(f"location = //x {{ {INC} }}"),
    "N-17 // innen": oben(f"location ^~ /a//b/ {{ {INC} }}"),
    "N-17 Prozent im Pfad": oben(f"location = /a%20 {{ {INC} }}"),
    "N-18 ohne include": oben("location = /x { proxy_buffering off; }"),
    "N-19 include zweimal": oben(f"location = /x {{ {ZWEI_INC} }}"),
    "N-20 Lesefrist zu lang": NEU.replace("300s", "99999s"),
    "N-20 Lesefrist ohne s": NEU.replace("300s", "300"),
    "N-20 Burst zu groß": NEU.replace("burst=40", "burst=12345"),
    "N-20 limit_req ohne nodelay": NEU.replace("burst=40 nodelay", "burst=40"),
    "N-20 limit_req_status anders": NEU.replace("limit_req_status 429;", "limit_req_status 444;", 1),
    "N-20 proxy_buffering on": NEU.replace("proxy_buffering off;", "proxy_buffering on;"),
    "N-21 server": oben("server { listen 80; }"),
    "N-21 upstream": oben("upstream x { server 127.0.0.1:1; }"),
    "N-21 Anweisung oben": oben("proxy_buffering off;"),
    "N-22 verschachtelt": oben(f"location = /x {{\n    {INC}\n    location = /y {{ {INC} }}\n}}"),
    "N-23 Anweisung doppelt": NEU.replace("limit_req_status 429;", "limit_req_status 429;\n    limit_req_status 429;", 1),
    "N-24 Ortskopf doppelt": oben(f"location = /token {{ {INC} }}"),
    "Kommentar hinter Anweisung": NEU.replace("proxy_buffering off;", "proxy_buffering off; # x"),
    "Semikolon fehlt": NEU.replace("proxy_buffering off;", "proxy_buffering off"),
    "Block nicht geschlossen": oben(f"location = /x {{ {INC}"),
    "Klammer zu viel": oben("}"),
    "Spitze Klammer": oben(f"location = /x {{ {INC} }} <"),
    "Kaufmanns-Und": oben(f"location = /x& {{ {INC} }}"),
    "Pipe außerhalb Regex": oben(f"location = /a|b {{ {INC} }}"),
    "Fragezeichen außerhalb Regex": oben(f"location = /a? {{ {INC} }}"),
}


@pytest.mark.parametrize("neu", list(NEGATIV.values()), ids=list(NEGATIV.keys()))
def test_ac4_bis_ac6_negativfaelle_lehnen_die_ganze_eingabe_ab(h, neu):
    abgelehnt(h, neu)


def test_ac4_ablehnung_nennt_einen_grund_auf_stderr_und_nichts_auf_stdout(h, capsys):
    assert h["main"](NEGATIV["N-1 proxy_pass"]) == 3
    aus = capsys.readouterr()
    assert aus.out == "" and aus.err.strip() and "Traceback" not in aus.err


def test_ac4_abgelehnt_ist_eine_ausnahme_von_installieren(h):
    with pytest.raises(h["m"].Abgelehnt):
        h["lauf"](NEGATIV["N-1 proxy_pass"])


# ---------- AC-7: das Installierte selbst lesen ----------

def test_ac7_installierte_datei_fehlt(h):
    h["ziel"].unlink()
    abgelehnt(h, NEU)


def test_ac7_symlink_wird_nicht_gefolgt(h):
    anderswo = h["tmp"] / "anderswo.inc"
    anderswo.write_text(BASIS)
    h["ziel"].unlink()
    h["ziel"].symlink_to(anderswo)
    abgelehnt(h, NEU)
    assert anderswo.read_text() == BASIS and h["ziel"].is_symlink()


def test_ac7_nicht_datei(h):
    h["ziel"].unlink()
    h["ziel"].mkdir()
    abgelehnt(h, NEU)


def test_ac7_als_root_fremdes_eigentum_lehnt_ab(h, monkeypatch):
    if os.geteuid() == 0:
        pytest.skip("braucht einen Nicht-root-Besitzer der Testdatei")
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    gesetzt = []
    monkeypatch.setattr(os, "fchown", lambda *a: gesetzt.append(a))
    monkeypatch.setattr(os, "chown", lambda *a, **k: gesetzt.append(a))
    abgelehnt(h, NEU)


def test_ac7_als_root_mit_root_eigentum_setzt_root_root(h, monkeypatch):
    echt = os.fstat

    def fstat(fd):
        s = echt(fd)
        return os.stat_result((s.st_mode, s.st_ino, s.st_dev, s.st_nlink, 0, 0, s.st_size, int(s.st_atime), int(s.st_mtime), int(s.st_ctime)))
    gesetzt = []
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    monkeypatch.setattr(os, "fstat", fstat)
    monkeypatch.setattr(os, "fchown", lambda fd, uid, gid: gesetzt.append((uid, gid)))
    monkeypatch.setattr(os, "chown", lambda p, uid, gid, **k: gesetzt.append((uid, gid)))
    assert h["lauf"](NEU) == 0
    assert gesetzt and set(gesetzt) == {(0, 0)}


def test_f002_installierte_datei_groesser_als_64_kib_wird_nicht_gekuerzt_gesichert(h, capsys):
    """Gegenprüfung F002: Eine installierte Datei über 64 KiB lehnt das Hilfsprogramm ab, statt sie gekürzt zu sichern."""
    h["ziel"].write_text(BASIS + "#" * (64 * 1024) + "\n", encoding="utf-8")
    abgelehnt(h, NEU)
    assert not h["sicherung"].exists()
    assert "larger" in capsys.readouterr().err


# ---------- AC-8: Eingabe und Aufruf ----------

@pytest.mark.parametrize("neu", [NEU + "#" * 70000, b"\xff\xfe location", "", "\n\n", "# nur Kommentar\n"],
                         ids=["zu groß", "kein UTF-8", "leer", "nur Leerzeilen", "kein Block"])
def test_ac8_eingabe_wird_abgelehnt(h, neu):
    abgelehnt(h, neu)


def test_ac8_genau_64_kib_plus_ein_byte_wird_abgelehnt(h):
    rest = 64 * 1024 + 1 - len(NEU.encode())
    abgelehnt(h, NEU + "#" * (rest - 1) + "\n")


@pytest.mark.parametrize("argv", [("helfer", "x"), ("helfer", NAME), ("helfer", "", "")])
def test_ac8_jedes_argument_ergibt_ausgang_3(h, argv):
    vorher = h["ziel"].read_bytes()
    assert h["main"](NEU, argv=argv) == 3
    assert h["ziel"].read_bytes() == vorher and not h["z"]["tests"]


def test_ac8_gleich_ist_nichts_zu_tun(h):
    assert h["lauf"](BASIS) == 2
    assert not h["z"]["tests"] and not h["z"]["laden"]
    assert not h["sicherung"].exists() or not list(h["sicherung"].iterdir())


def test_ac8_main_liest_stdin_wenn_keine_daten(h, monkeypatch):
    import io
    import sys
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(NEU.encode())))
    assert h["m"].main(["helfer"], **h["kw"]) == 0
    assert h["ziel"].read_text(encoding="utf-8") == NEU


def test_f003_stdin_nicht_lesbar_ist_ausgang_3_ohne_traceback(h, monkeypatch, capsys):
    """Gegenprüfung F003: Ein Fehler vor jeder Änderung (stdin nicht lesbar) ergibt 3, nicht 6."""
    import sys

    class Kaputt:
        class buffer:
            @staticmethod
            def read(*a):
                raise OSError("stdin geschlossen")
    monkeypatch.setattr(sys, "stdin", Kaputt)
    assert h["m"].main(["helfer"], **h["kw"]) == 3
    assert h["ziel"].read_text(encoding="utf-8") == BASIS and not h["z"]["tests"]
    assert "Traceback" not in capsys.readouterr().err


def test_f003_unerwarteter_fehler_nach_beginn_des_ersetzens_ist_6(h, monkeypatch):
    def testen():
        raise ValueError("unerwartet")
    kw = dict(h["kw"], testen=testen)
    assert h["m"].main(["helfer"], NEU.encode(), **kw) == 6


# ---------- AC-9: Sicherung und atomares Ersetzen ----------

def test_ac9_sicherung_im_root_ordner_vor_dem_ersetzen(h):
    assert h["lauf"](NEU) == 0
    sicherungen = list(h["sicherung"].iterdir())
    assert len(sicherungen) == 1 and sicherungen[0].read_text(encoding="utf-8") == BASIS
    assert oct(h["sicherung"].stat().st_mode & 0o777) == "0o700"
    assert h["snippets"] not in sicherungen[0].parents


def test_ac9_es_bleiben_die_letzten_20_sicherungen(h):
    for i in range(23):
        assert h["lauf"](BASIS.replace("burst=40", f"burst={41 + i}")) == 0
    sicherungen = list(h["sicherung"].iterdir())
    assert len(sicherungen) == 20
    # die neueste Sicherung (Stand vor dem letzten Lauf) ist dabei
    assert BASIS.replace("burst=40", "burst=62") in {p.read_text(encoding="utf-8") for p in sicherungen}


def test_ac9_sicherungsname_aus_einem_zeitpunkt_auch_an_der_sekundengrenze(h, monkeypatch):
    """Sekunde und Nanosekunden des Namens kommen aus demselben Zeitpunkt: Liest der Helfer sie getrennt und springt
    dazwischen die Sekunde, sortiert die neueste Sicherung vor die älteren und wird beim Aufräumen gelöscht (scheiterte
    unter Last auf dem Server, 10.11.2026)."""
    import time as zeit
    sekunde = int(zeit.time()) + 3600                   # weit weg vom echten Takt: nur der falsche Weg trifft ihn
    takte = iter([sekunde * 10**9 + i * 50_000_000 for i in range(30)])   # 20 Takte je Sekunde, über mehrere Sekunden
    monkeypatch.setattr(zeit, "time_ns", lambda: next(takte))
    for i in range(23):
        assert h["lauf"](BASIS.replace("burst=40", f"burst={41 + i}")) == 0
    sicherungen = sorted(h["sicherung"].iterdir())
    assert len(sicherungen) == 20
    assert sicherungen[-1].read_text(encoding="utf-8") == BASIS.replace("burst=40", "burst=62")


def test_ac9_temporaere_datei_im_snippets_ordner_ohne_endung_conf_inc(h, monkeypatch):
    echt = tempfile.mkstemp
    erzeugt = []

    def mkstemp(*a, **k):
        fd, pfad = echt(*a, **k)
        erzeugt.append(pfad)
        return fd, pfad
    monkeypatch.setattr(tempfile, "mkstemp", mkstemp)
    assert h["lauf"](NEU) == 0
    im_ordner = [p for p in erzeugt if Path(p).parent == h["snippets"]]
    assert im_ordner, erzeugt
    assert all(not p.endswith((".conf", ".inc")) for p in im_ordner)
    assert sorted(p.name for p in h["snippets"].iterdir()) == [NAME]       # keine temporäre Datei bleibt


def test_ac9_atomar_ohne_reste_und_nur_der_name_auf_stdout(h, capsys):
    assert h["main"](NEU) == 0
    assert capsys.readouterr().out == NAME + "\n"
    assert sorted(p.name for p in h["snippets"].iterdir()) == [NAME]


# ---------- AC-10: Rückweg und Ausgänge 4, 5, 6 ----------

def test_ac10_nginx_test_scheitert_rueckweg_ausgang_4(h, capsys):
    h["z"]["test_ergebnisse"] = [False, True]
    assert h["main"](NEU) == 4
    assert h["ziel"].read_text(encoding="utf-8") == BASIS
    assert h["z"]["tests"] == [NEU, BASIS] and not h["z"]["laden"]
    assert sorted(p.name for p in h["snippets"].iterdir()) == [NAME]
    assert "Traceback" not in capsys.readouterr().err


def test_ac10_reload_scheitert_ausgang_5_datei_bleibt(h):
    h["z"]["laden_ok"] = False
    assert h["main"](NEU) == 5
    assert h["ziel"].read_text(encoding="utf-8") == NEU
    assert h["z"]["laden"] == [1]


def test_ac10_zweiter_test_scheitert_ausgang_6_alter_stand(h, capsys):
    h["z"]["test_ergebnisse"] = [False, False]
    assert h["main"](NEU) == 6
    assert h["ziel"].read_text(encoding="utf-8") == BASIS
    assert not h["z"]["laden"]
    err = capsys.readouterr().err
    assert "rollback untested" in err and "Traceback" not in err


def test_ac10_zurueckschreiben_scheitert_ausgang_6_sicherung_bleibt(h, monkeypatch, capsys):
    echt = os.replace
    aufs_ziel = []

    def replace(src, dst, *a, **k):
        if os.fspath(dst) == str(h["ziel"]):
            aufs_ziel.append(src)
            if len(aufs_ziel) > 1:
                raise OSError("Platte voll")
        return echt(src, dst, *a, **k)
    monkeypatch.setattr(os, "replace", replace)
    h["z"]["test_ergebnisse"] = [False, True]
    assert h["main"](NEU) == 6
    assert not h["z"]["laden"]
    sicherungen = list(h["sicherung"].iterdir())
    assert len(sicherungen) == 1 and sicherungen[0].read_text(encoding="utf-8") == BASIS
    err = capsys.readouterr().err
    assert "rollback failed" in err and str(sicherungen[0]) in err and "Traceback" not in err


def test_ac10_fehler_beim_schreiben_ausgang_3_datei_unveraendert(h, monkeypatch, capsys):
    monkeypatch.setattr(os, "fsync", lambda fd: (_ for _ in ()).throw(OSError("voll")))
    assert h["main"](NEU) == 3
    assert h["ziel"].read_text(encoding="utf-8") == BASIS
    assert sorted(p.name for p in h["snippets"].iterdir()) == [NAME]
    assert not h["z"]["tests"] and not h["z"]["laden"]
    assert "Traceback" not in capsys.readouterr().err


def test_ac10_ersetzen_scheitert_ausgang_3(h, monkeypatch):
    echt = os.replace

    def replace(src, dst, *a, **k):
        if os.fspath(dst) == str(h["ziel"]):
            raise OSError("geht nicht")
        return echt(src, dst, *a, **k)
    monkeypatch.setattr(os, "replace", replace)
    assert h["main"](NEU) == 3
    assert h["ziel"].read_text(encoding="utf-8") == BASIS
    assert sorted(p.name for p in h["snippets"].iterdir()) == [NAME]
    assert not h["z"]["tests"]


def test_ac10_sicherung_nicht_anlegbar_ausgang_3(h):
    h["sicherung"].write_text("keine Ordner")       # an der Stelle des Ordners liegt eine Datei
    assert h["main"](NEU) == 3
    assert h["ziel"].read_text(encoding="utf-8") == BASIS and not h["z"]["tests"]


def test_ac10_nginx_fehlt_vor_dem_ersetzen_ausgang_3(h):
    kw = dict(h["kw"], nginx=str(h["tmp"] / "gibt-es-nicht"))
    assert h["m"].main(["helfer"], NEU.encode(), **kw) == 3
    assert h["ziel"].read_text(encoding="utf-8") == BASIS and not h["z"]["tests"]


# ---------- AC-11: Sperre ----------

def test_ac11_sperre_belegt_ausgang_3(h, capsys):
    with open(h["kw"]["sperre"], "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert h["main"](NEU) == 3
    assert h["ziel"].read_text(encoding="utf-8") == BASIS and not h["z"]["tests"]
    assert "busy" in capsys.readouterr().err


def test_ac11_nach_dem_lauf_ist_die_sperre_frei(h):
    assert h["main"](NEU) == 0
    with open(h["kw"]["sperre"], "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)


# ---------- AC-12: feste Pfade, Programme und Umgebung ----------

def test_ac12_keine_umlenkung_ueber_umgebung_oder_argumente(h):
    quelltext = h["text"]
    assert quelltext.startswith("#!/usr/bin/python3 -I\n")
    assert "os.environ" not in quelltext and "getenv" not in quelltext and not re.search(r"sys\.argv\[", quelltext)
    assert "check=True" not in quelltext and "shell=True" not in quelltext
    m = h["m"]
    assert m.NGINX == "/usr/sbin/nginx" and m.SYSTEMCTL == "/usr/bin/systemctl"
    assert m.SNIPPETS == "/etc/nginx/snippets" and m.SICHERUNG == "/var/lib/probe-nginx-sicherung"
    assert m.INSTANZ == "probe" and m.MAX_BYTES == 64 * 1024
    assert not re.search(r"__[A-Z_]+__", quelltext)


def _aufzeichnen(monkeypatch, ergebnis):
    aufrufe = []

    def run(args, **kw):
        aufrufe.append((list(args), kw))
        if isinstance(ergebnis, BaseException):
            raise ergebnis
        return subprocess.CompletedProcess(args, ergebnis, b"", b"")
    monkeypatch.setattr(subprocess, "run", run)
    return aufrufe


def test_ac12_nginx_testen_und_neu_laden_mit_fester_umgebung(h, monkeypatch):
    monkeypatch.setenv("PATH", "/tmp/boese")
    monkeypatch.setenv("PYTHONPATH", "/tmp/boese")
    aufrufe = _aufzeichnen(monkeypatch, 0)
    assert h["m"].nginx_testen() is True
    assert h["m"].nginx_neu_laden() is True
    (a1, k1), (a2, k2) = aufrufe
    assert a1 == ["/usr/sbin/nginx", "-t"] and a2 == ["/usr/bin/systemctl", "reload", "nginx"]
    for k in (k1, k2):
        assert k.get("env") == {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"}
        assert k.get("stdin") == subprocess.DEVNULL and k.get("timeout") and not k.get("check") and not k.get("shell")


@pytest.mark.parametrize("ergebnis", [1, subprocess.TimeoutExpired(["x"], 1), FileNotFoundError("weg"), PermissionError("nein")])
def test_ac12_scheitern_der_unterprozesse_ist_false_ohne_traceback(h, monkeypatch, ergebnis):
    _aufzeichnen(monkeypatch, ergebnis)
    assert h["m"].nginx_testen() is False
    assert h["m"].nginx_neu_laden() is False
