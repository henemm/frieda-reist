"""Tests für #648: Testzugang `frieda-test` für Abnahmen über den Konnektor (betrieb/testzugang.py).
Spec: docs/specs/betrieb/testkonto-648.md (Tests 1 bis 7, AC-1 bis AC-5).

Alles läuft gegen die Wegwerf-Instanz der Testwelt (Fixture `welt`), nur mit erfundenen Adressen unter beispiel.invalid.

Schnittstelle, die diese Tests festlegen:
  Umgebung: FR_KN_ADRESSE (Adresse des Konnektors, hier der lokale Testdienst), FR_BASIS (Herkunft der Seiten),
            FR_KONTEN (Kontendatenbank), FR_TESTKONTO (Adresse des Testkontos), FR_TESTZUGANG (Ablage-Datei)
  python3 betrieb/testzugang.py einrichten   Testkonto anlegen oder finden (nur Recht reise_anlegen), echter OAuth-Weg,
                                             Ablage (JSON mit mindestens client_id und refresh_token, Rechte 600);
                                             Exit-Code ungleich 0 ohne FR_TESTKONTO oder bei einem Betreiberkonto
  python3 betrieb/testzugang.py dienst       stdio-MCP-Brücke: je Zeile eine JSON-RPC-Nachricht, Antwort als eine Zeile;
                                             Benachrichtigungen ohne Antwort; erneuert Tokens selbst; prüft beim Start das
                                             Konto (falsches Konto oder Betreiber: Exit-Code ungleich 0, nichts auf stdout)
"""
import ast
import json
import os
import re
import socket
import stat
import subprocess
import sys
import threading
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit

import pytest

ENGINE = Path(__file__).resolve().parents[1]
WURZEL = ENGINE.parent
SKRIPT = WURZEL / "betrieb" / "testzugang.py"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import konten  # noqa: E402
from test_anmeldung import BASIS, welt  # noqa: E402,F401  (welt: Fixture)
from test_oauth import mcp, verbinden  # noqa: E402

TEST = "frieda-test@beispiel.invalid"
ANDERS = "anders-test@beispiel.invalid"
CHEF = "betrieb@beispiel.invalid"

INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "pytest", "version": "1"}}}
INITIALISIERT = {"jsonrpc": "2.0", "method": "notifications/initialized"}
LISTE = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}


@pytest.fixture
def zugang(welt, tmp_path, monkeypatch):
    """Testinstanz mit Instanzwerten für den Testzugang; die Ablage liegt außerhalb des Repos (tmp_path)."""
    u = welt()
    monkeypatch.setenv("FR_KN_ADRESSE", u.kurl)
    monkeypatch.setenv("FR_BASIS", BASIS)
    monkeypatch.setenv("FR_TESTKONTO", TEST)
    ablage = tmp_path / "zugang" / "testzugang.json"
    ablage.parent.mkdir()
    monkeypatch.setenv("FR_TESTZUGANG", str(ablage))
    u.ablage_zugang = ablage
    return u


def einrichten(env=None):
    return subprocess.run([sys.executable, str(SKRIPT), "einrichten"], capture_output=True, text=True, timeout=60,
                          env={**os.environ, **(env or {})})


def bruecke(*nachrichten, env=None):
    """Brücke starten, Nachrichten zeilenweise schicken, stdin schließen. -> (returncode, [Antworten], stderr)"""
    eingabe = "".join(json.dumps(n) + "\n" for n in nachrichten)
    p = subprocess.run([sys.executable, str(SKRIPT), "dienst"], input=eingabe, capture_output=True, text=True,
                       timeout=60, env={**os.environ, **(env or {})})
    return p.returncode, [json.loads(z) for z in p.stdout.splitlines() if z.strip()], p.stderr


def bruecke_starten(*nachrichten):
    p = subprocess.Popen([sys.executable, str(SKRIPT), "dienst"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True)
    return p, "".join(json.dumps(n) + "\n" for n in nachrichten)


def namen(antwort):
    return {w["name"] for w in antwort["result"]["tools"]}


def ablage(u):
    return json.loads(u.ablage_zugang.read_text())


def token_zeile(refresh):
    with closing(konten.db()) as v:
        return v.execute("SELECT * FROM oauth_tokens WHERE hash = ? AND art = 'refresh'",
                         (konten._hash("refresh", refresh),)).fetchone()


def access_ablaufen_lassen():
    with closing(konten.db()) as v, v:
        v.execute("UPDATE oauth_tokens SET ablauf = 0 WHERE art = 'access'")


# ---------- Test 1: Einrichten ----------

def test_einrichten_legt_testkonto_und_ablage_an(zugang):
    p = einrichten()
    assert p.returncode == 0, p.stderr
    k = konten.konto_per_email(TEST)
    assert k is not None
    assert konten.recht(k, "reise_anlegen") and not konten.recht(k, "betreiber")
    assert stat.S_IMODE(zugang.ablage_zugang.stat().st_mode) == 0o600
    a = ablage(zugang)
    assert a["client_id"] and a["refresh_token"]
    z = token_zeile(a["refresh_token"])
    assert z is not None and z["konto"] == k["id"] and z["benutzt"] is None and z["client_id"] == a["client_id"]
    # Nichts Geheimes in der Ausgabe
    assert a["refresh_token"] not in p.stdout + p.stderr


def test_einrichten_ohne_testkonto_bricht_ab(zugang, monkeypatch):
    monkeypatch.delenv("FR_TESTKONTO")
    p = einrichten()
    assert p.returncode != 0
    assert "FR_TESTKONTO" in p.stdout + p.stderr
    assert not zugang.ablage_zugang.exists()


def test_einrichten_zweimal_ersetzt_und_widerruft_den_alten_zugang(zugang):
    assert einrichten().returncode == 0
    alt = ablage(zugang)["refresh_token"]
    assert einrichten().returncode == 0
    neu = ablage(zugang)["refresh_token"]
    assert neu != alt
    assert token_zeile(alt) is None
    assert token_zeile(neu) is not None
    assert stat.S_IMODE(zugang.ablage_zugang.stat().st_mode) == 0o600
    k = konten.konto_per_email(TEST)
    assert konten.recht(k, "reise_anlegen") and not konten.recht(k, "betreiber")


# ---------- Test 2: nie ein Betreiberkonto ----------

def test_einrichten_verweigert_betreiberkonto(zugang, monkeypatch):
    with closing(konten.db()) as v, v:
        v.execute("INSERT INTO konten (id, email, name, angelegt, rechte) VALUES (?,?,?,?,?)",
                  ("K-chef", CHEF, "Chef", konten._datum(), "betreiber"))
    monkeypatch.setenv("FR_TESTKONTO", CHEF)
    p = einrichten()
    assert p.returncode != 0
    assert not zugang.ablage_zugang.exists()
    with closing(konten.db()) as v:
        assert v.execute("SELECT COUNT(*) FROM oauth_tokens WHERE konto = 'K-chef'").fetchone()[0] == 0
        assert v.execute("SELECT rechte FROM konten WHERE id = 'K-chef'").fetchone()[0] == "betreiber"


# ---------- #670: Kontaktadresse des Betreibers auch aus <FR_DIENST>/konten.env ----------
# Spec: docs/specs/konnektor/lesewerkzeuge-670.md (AC-7, AC-8)

def _konten_env_setzen(monkeypatch, tmp_path, inhalt):
    """Dienstordner der Testinstanz mit konten.env (oder ohne, wenn inhalt None); FR_BETREIBER_KONTAKT nicht in der
    Umgebung, damit nur die Datei den Wert kennt (wie bei einem Handaufruf auf dem Server)."""
    monkeypatch.delenv("FR_BETREIBER_KONTAKT", raising=False)
    import instanz
    d = instanz.dienst() if os.environ.get("FR_DIENST") else tmp_path / "dienst"
    d.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("FR_DIENST", str(d))
    f = d / "konten.env"
    if f.exists():
        f.unlink()
    if inhalt is not None:
        f.write_text(inhalt, encoding="utf-8")
    return f


def test_einrichten_verweigert_kontaktadresse_aus_konten_env(zugang, monkeypatch, tmp_path):
    _konten_env_setzen(monkeypatch, tmp_path, f'FR_MAIL_PASSWORT=geheim-beispiel\nFR_BETREIBER_KONTAKT="{TEST}"\n')
    p = einrichten()
    assert p.returncode != 0, p.stdout + p.stderr
    assert konten.konto_per_email(TEST) is None
    assert not zugang.ablage_zugang.exists()
    assert "geheim-beispiel" not in p.stdout + p.stderr


def test_einrichten_ohne_konten_env_bricht_nicht_ab(zugang, monkeypatch, tmp_path):
    _konten_env_setzen(monkeypatch, tmp_path, None)
    p = einrichten()
    assert p.returncode == 0, p.stderr
    assert konten.konto_per_email(TEST) is not None


# ---------- Test 3: Brücke ----------

def test_bruecke_liefert_die_werkzeugliste_des_konnektors(zugang):
    assert einrichten().returncode == 0
    rc, antworten, err = bruecke(INIT, INITIALISIERT, LISTE)
    assert rc == 0, err
    assert [a["id"] for a in antworten] == [1, 2]          # die Benachrichtigung bleibt ohne Antwort
    assert antworten[0]["result"]["serverInfo"]["name"] == "frieda"
    # Die Zustimmungsprüfung des Helfers erwartet die deutsche Seite; die Kontosprache ist nicht Gegenstand von #648.
    konten.sprache_setzen(konten.konto_per_email(TEST)["id"], "de")
    t, _ = verbinden(zugang, TEST)
    s, _, direkt = mcp(zugang, t["access_token"], "tools/list")
    assert s == 200
    assert namen(antworten[1]) == {w["name_aussen"] for w in direkt["result"]["tools"]}
    assert "trip_create" in namen(antworten[1])             # Recht reise_anlegen: das Testkonto darf Reisen anlegen
    assert "request_decide" not in namen(antworten[1])      # kein Betreiber


def test_bruecke_ruft_werkzeuge_als_testkonto(zugang):
    assert einrichten().returncode == 0
    rc, antworten, err = bruecke(INIT, {"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                                        "params": {"name": "my_trips", "arguments": {}}})
    assert rc == 0, err
    assert antworten[-1]["id"] == 7 and antworten[-1]["result"]["isError"] is False
    assert TEST in antworten[0]["result"]["instructions"]


# ---------- Test 4: Erneuern ----------

def test_bruecke_erneuert_abgelaufenes_token(zugang):
    assert einrichten().returncode == 0
    rc, _, err = bruecke(INIT, LISTE)
    assert rc == 0, err
    alt = ablage(zugang)["refresh_token"]
    access_ablaufen_lassen()
    rc, antworten, err = bruecke(INIT, LISTE)
    assert rc == 0, err
    assert "my_trips" in namen(antworten[-1])
    neu = ablage(zugang)["refresh_token"]
    assert neu != alt
    assert token_zeile(alt)["benutzt"] is not None and token_zeile(neu)["benutzt"] is None
    assert stat.S_IMODE(zugang.ablage_zugang.stat().st_mode) == 0o600
    # atomar geschrieben: keine liegengebliebenen Zwischendateien neben der Ablage
    assert not [p.name for p in zugang.ablage_zugang.parent.iterdir() if "tmp" in p.name.lower()]


def test_bruecke_erneuert_bei_401_mitten_im_lauf(zugang):
    """Läuft das Access-Token ab, während die Brücke läuft, antwortet der Dienst mit 401; die Brücke erneuert und
    wiederholt die Anfrage, statt den Fehler an Claude Code weiterzugeben."""
    assert einrichten().returncode == 0
    p, eingabe = bruecke_starten(INIT)
    p.stdin.write(eingabe)
    p.stdin.flush()
    erste = json.loads(p.stdout.readline())
    assert erste["id"] == 1
    access_ablaufen_lassen()
    p.stdin.write(json.dumps(LISTE) + "\n")
    p.stdin.close()
    rest = [json.loads(z) for z in p.stdout.read().splitlines() if z.strip()]
    assert p.wait(timeout=60) == 0, p.stderr.read()
    assert rest and rest[-1]["id"] == 2 and "my_trips" in namen(rest[-1])


# ---------- Test 5: parallele Sitzungen ----------

def test_zwei_bruecken_erneuern_ohne_die_token_familie_zu_widerrufen(zugang):
    assert einrichten().returncode == 0
    assert bruecke(INIT, LISTE)[0] == 0
    access_ablaufen_lassen()
    laeufe = [bruecke_starten(INIT, LISTE) for _ in range(3)]
    ergebnisse = [(p, *p.communicate(eingabe, timeout=60)) for p, eingabe in laeufe]
    for p, out, err in ergebnisse:
        assert p.returncode == 0, err
        antworten = [json.loads(z) for z in out.splitlines() if z.strip()]
        assert "my_trips" in namen(antworten[-1])
    k = konten.konto_per_email(TEST)
    with closing(konten.db()) as v:
        offen = v.execute("SELECT COUNT(*) FROM oauth_tokens WHERE konto = ? AND art = 'refresh' AND benutzt IS NULL",
                          (k["id"],)).fetchone()[0]
    assert offen == 1                                         # Familie lebt, genau ein gültiger Refresh-Token
    assert token_zeile(ablage(zugang)["refresh_token"])["benutzt"] is None
    rc, antworten, err = bruecke(INIT, LISTE)                 # und die nächste Sitzung läuft weiter
    assert rc == 0 and "my_trips" in namen(antworten[-1]), err


# ---------- Test 6: falsches Konto ----------

def test_bruecke_bricht_ab_bei_token_eines_anderen_kontos(zugang, monkeypatch):
    assert einrichten({"FR_TESTKONTO": ANDERS}).returncode == 0
    rc, antworten, err = bruecke(INIT, LISTE)                 # FR_TESTKONTO ist TEST, das Token gehört ANDERS
    assert rc != 0
    assert antworten == []
    assert err.strip()


def test_bruecke_bricht_ab_wenn_das_testkonto_betreiber_wurde(zugang):
    assert einrichten().returncode == 0
    konten.recht_setzen(konten.konto_per_email(TEST)["id"], "betreiber")
    rc, antworten, err = bruecke(INIT, LISTE)
    assert rc != 0
    assert antworten == []


# ---------- Test 7: Standardbibliothek, Einbindung ohne Geheimnis ----------

def _fremde_importe(baum):
    """-> [(funktion oder None, modul)] aller Importe, die nicht zur Standardbibliothek gehören."""
    fremd = []

    def besuchen(knoten, funktion):
        for kind in ast.iter_child_nodes(knoten):
            f = kind.name if isinstance(kind, (ast.FunctionDef, ast.AsyncFunctionDef)) else funktion
            if isinstance(kind, ast.Import):
                fremd.extend((f, a.name) for a in kind.names if a.name.split(".")[0] not in sys.stdlib_module_names)
            elif isinstance(kind, ast.ImportFrom):
                if kind.level or (kind.module or "").split(".")[0] not in sys.stdlib_module_names:
                    fremd.append((f, kind.module))
            besuchen(kind, f)
    besuchen(baum, None)
    return fremd


def test_bruecke_nutzt_nur_standardbibliothek():
    """Die Brücke läuft mit dem python3 des Systems; nur `einrichten` darf (wie pruefsitzung.py) die Engine laden."""
    fremd = _fremde_importe(ast.parse(SKRIPT.read_text(encoding="utf-8")))
    assert all(f == "einrichten" for f, _ in fremd), fremd
    quelle = SKRIPT.read_text(encoding="utf-8")
    assert "sys.path.insert" not in quelle.split("def einrichten")[0]


def test_mcp_json_ohne_adresse_und_geheimnis():
    m = json.loads((WURZEL / ".mcp.json").read_text(encoding="utf-8"))
    s = m["mcpServers"]["frieda-test"]
    befehl = " ".join([s["command"], *s.get("args", [])])
    assert "testzugang.py" in befehl and befehl.split()[-1] == "dienst"
    text = json.dumps(s)
    for verboten in ("http", "@", "token", "Bearer", "/home/", "/srv/"):
        assert verboten not in text, verboten
    assert not s.get("env")


def test_settings_bindet_bruecke_und_sperre_ein():
    s = json.loads((WURZEL / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "frieda-test" in s["enabledMcpjsonServers"]
    eintraege = [e for e in s["hooks"]["PreToolUse"] if e["matcher"] == "mcp__claude_ai_Frieda__.*"]
    assert len(eintraege) == 1
    assert any("frieda_sperre.py" in h["command"] for h in eintraege[0]["hooks"])


def test_einstellungen_beispiel_nennt_die_instanzwerte():
    text = (WURZEL / "betrieb" / "einstellungen.beispiel").read_text(encoding="utf-8")
    assert "FR_TESTKONTO=" in text and "FR_TESTZUGANG=" in text


# ---------- Test 8: Netzfehler (#669) ----------
# Spec: docs/specs/fast/fix-669-bruecke-netzfehler.md

def _freier_port():
    """Port, auf dem gerade niemand lauscht (gebunden und wieder geschlossen)."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Weiterleiter:
    """TCP-Weiterleiter zwischen Brücke und Konnektor der Testwelt. Ausgeschaltet nimmt er Verbindungen an und schließt
    sie sofort (für die Brücke ein Netzfehler); eingeschaltet reicht er die Bytes in beide Richtungen durch."""

    def __init__(self, ziel):
        t = urlsplit(ziel)
        self.ziel, self.an = (t.hostname, t.port), True
        self.server = socket.create_server(("127.0.0.1", 0))
        self.url = f"http://127.0.0.1:{self.server.getsockname()[1]}"
        threading.Thread(target=self._annehmen, daemon=True).start()

    def _annehmen(self):
        while True:
            try:
                k, _ = self.server.accept()
            except OSError:
                return
            if self.an == 502:
                threading.Thread(target=self._bad_gateway, args=(k,), daemon=True).start()
                continue
            if isinstance(self.an, bytes):
                threading.Thread(target=self._token_koerper, args=(k, self.an), daemon=True).start()
                continue
            if not self.an:
                k.close()
                continue
            z = socket.create_connection(self.ziel)
            for von, nach in ((k, z), (z, k)):
                threading.Thread(target=self._pumpen, args=(von, nach), daemon=True).start()

    @staticmethod
    def _anfrage_lesen(k):
        daten = b""
        while b"\r\n\r\n" not in daten and (stueck := k.recv(65536)):
            daten += stueck
        kopf, _, rumpf = daten.partition(b"\r\n\r\n")
        laenge = int((re.search(rb"(?i)content-length:\s*(\d+)", kopf) or [b"", b"0"])[1])
        while len(rumpf) < laenge and (stueck := k.recv(65536)):
            rumpf += stueck
        return kopf + b"\r\n\r\n" + rumpf

    @staticmethod
    def _bad_gateway(k):
        """Wie nginx während eines Neustarts: Anfrage ganz lesen, dann 502 (#669, AC-6)."""
        with k:
            Weiterleiter._anfrage_lesen(k)
            k.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")

    def _token_koerper(self, k, koerper):
        """POST /token mit HTTP 200 und dem gegebenen Körper beantworten, alles andere durchreichen (#738)."""
        anfrage = self._anfrage_lesen(k)
        if not anfrage.startswith(b"POST /token"):
            z = socket.create_connection(self.ziel)
            z.sendall(anfrage)
            for von, nach in ((k, z), (z, k)):
                threading.Thread(target=self._pumpen, args=(von, nach), daemon=True).start()
            return
        with k:
            k.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
                      + str(len(koerper)).encode() + b"\r\nConnection: close\r\n\r\n" + koerper)

    @staticmethod
    def _pumpen(von, nach):
        try:
            while daten := von.recv(65536):
                nach.sendall(daten)
        except OSError:
            pass
        finally:
            for s in (von, nach):
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass


@pytest.fixture
def weiterleiter(zugang, monkeypatch):
    w = Weiterleiter(zugang.kurl)
    monkeypatch.setenv("FR_KN_ADRESSE", w.url)
    yield w
    w.server.close()


def _netzfehler(antwort, kennung):
    return antwort["id"] == kennung and antwort["error"]["code"] == -32603 and "result" not in antwort


def _zeile(p, nachricht):
    p.stdin.write(json.dumps(nachricht) + "\n")
    p.stdin.flush()
    return json.loads(p.stdout.readline())


def _ende(p):
    p.stdin.close()
    rest = [json.loads(z) for z in p.stdout.read().splitlines() if z.strip()]
    return p.wait(timeout=60), rest, p.stderr.read()


def test_bruecke_beantwortet_unerreichbaren_konnektor_mit_fehler(zugang):
    assert einrichten().returncode == 0
    rc, antworten, err = bruecke(INIT, INITIALISIERT, LISTE,
                                 env={"FR_KN_ADRESSE": f"http://127.0.0.1:{_freier_port()}"})
    assert rc == 0, err
    assert [a["id"] for a in antworten] == [1, 2]            # die Benachrichtigung bleibt ohne Antwort
    assert all(_netzfehler(a, a["id"]) for a in antworten), antworten
    assert "ConnectionRefusedError" in antworten[0]["error"]["message"]
    assert "Traceback" not in err
    assert ablage(zugang)["refresh_token"] not in json.dumps(antworten) + err


def test_bruecke_ueberlebt_netzfehler_mitten_im_lauf(zugang, weiterleiter):
    assert einrichten({"FR_KN_ADRESSE": zugang.kurl}).returncode == 0
    p, _ = bruecke_starten()
    assert _zeile(p, INIT)["result"]["serverInfo"]["name"] == "frieda"
    weiterleiter.an = False
    assert _netzfehler(_zeile(p, LISTE), 2)
    assert _netzfehler(_zeile(p, {**LISTE, "id": 3}), 3)      # die Brücke lebt und versucht es erneut
    weiterleiter.an = True
    assert "my_trips" in namen(_zeile(p, {**LISTE, "id": 4}))
    rc, rest, err = _ende(p)
    assert rc == 0 and rest == [], err
    assert "Traceback" not in err


def test_bruecke_prueft_nach_netzfehler_beim_start_und_leitet_dann_weiter(zugang, weiterleiter):
    assert einrichten({"FR_KN_ADRESSE": zugang.kurl}).returncode == 0
    weiterleiter.an = False
    p, _ = bruecke_starten()
    assert _netzfehler(_zeile(p, INIT), 1)
    weiterleiter.an = True
    assert "my_trips" in namen(_zeile(p, LISTE))
    rc, rest, err = _ende(p)
    assert rc == 0 and rest == [], err


def test_bruecke_ueberlebt_serverfehler_bei_der_kontopruefung(zugang, weiterleiter):
    """AC-6: 502 bei der Kontoprüfung gilt wie ein Netzfehler; die Prüfung wird nachgeholt, nichts ungeprüft weiter."""
    assert einrichten({"FR_KN_ADRESSE": zugang.kurl}).returncode == 0
    weiterleiter.an = 502
    p, _ = bruecke_starten()
    erste = _zeile(p, INIT)
    assert _netzfehler(erste, 1) and "502" in erste["error"]["message"], erste
    weiterleiter.an = True
    assert "my_trips" in namen(_zeile(p, LISTE))
    rc, rest, err = _ende(p)
    assert rc == 0 and rest == [], err
    assert "Traceback" not in err


def test_bruecke_bricht_nach_netzfehler_beim_start_bei_anderem_konto_ab(zugang, weiterleiter):
    assert einrichten({"FR_KN_ADRESSE": zugang.kurl, "FR_TESTKONTO": ANDERS}).returncode == 0
    weiterleiter.an = False
    p, _ = bruecke_starten()
    assert _netzfehler(_zeile(p, INIT), 1)
    weiterleiter.an = True
    p.stdin.write(json.dumps(LISTE) + "\n")
    rc, rest, err = _ende(p)
    assert rc != 0
    assert rest == []                                         # nichts weitergeleitet
    assert err.strip() and "Traceback" not in err


def test_bruecke_beantwortet_gescheiterte_erneuerung_mit_fehler(zugang):
    assert einrichten().returncode == 0
    daten = ablage(zugang)
    zugang.ablage_zugang.write_text(json.dumps({**daten, "refresh_token": "verfaelscht-beispiel", "access_ablauf": 0}))
    access_ablaufen_lassen()
    rc, antworten, err = bruecke(INIT, INITIALISIERT, LISTE)
    assert rc == 0, err
    assert [a["id"] for a in antworten] == [1, 2]
    assert all(_netzfehler(a, a["id"]) for a in antworten), antworten
    assert "verfaelscht-beispiel" not in json.dumps(antworten) + err
    assert "Traceback" not in err


@pytest.mark.parametrize("koerper", [b"", b"[]", b"{}"])
def test_bruecke_beantwortet_unbrauchbare_erneuerung_mit_fehler(zugang, weiterleiter, koerper):
    """#738, AC-1/AC-2: /token antwortet beim Erneuern mit HTTP 200, aber unbrauchbarem Körper. Die Brücke beantwortet
    jede Anfrage mit -32603, läuft bis zum Ende der Eingabe weiter, und die Ablage bleibt unverändert."""
    assert einrichten({"FR_KN_ADRESSE": zugang.kurl}).returncode == 0
    zugang.ablage_zugang.write_text(json.dumps({**ablage(zugang), "access_ablauf": 0}))
    access_ablaufen_lassen()
    vorher = zugang.ablage_zugang.read_bytes()
    weiterleiter.an = koerper
    rc, antworten, err = bruecke(INIT, INITIALISIERT, LISTE)
    assert rc == 0, err
    assert [a["id"] for a in antworten] == [1, 2]
    assert all(_netzfehler(a, a["id"]) for a in antworten), antworten
    assert "Traceback" not in err
    assert zugang.ablage_zugang.read_bytes() == vorher
