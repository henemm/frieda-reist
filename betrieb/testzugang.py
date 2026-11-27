#!/usr/bin/env python3
"""Testzugang `frieda-test` für Abnahmen über den Konnektor (#648, docs/specs/betrieb/testkonto-648.md).

Claude Code arbeitet bei Abnahmen nicht über das Konto des Product Owners, sondern über ein eigenes Testkonto derselben
Instanz. Dieses Skript hat zwei Befehle:

  python3 betrieb/testzugang.py einrichten
      Als Dienstbenutzer mit den Werten der Instanz. Legt das Testkonto (FR_TESTKONTO) an oder findet es, gibt ihm nur das
      Recht reise_anlegen und verweigert ein Betreiberkonto. Dann der Weg der Claude-App: dynamische Registrierung mit
      Loopback-Adresse, kurze Sitzung (wie die Prüfsitzung), Zustimmung, Code gegen Token (PKCE S256). Client-Kennung und
      Tokens liegen in der Ablage FR_TESTZUGANG (Vorgabe <FR_DIENST>/instanz/testzugang.json; außerhalb des Repos,
      Rechte 600, atomar geschrieben). Ein vorhandener Zugang wird ersetzt und widerrufen. Nichts davon wird ausgegeben.

  python3 betrieb/testzugang.py dienst
      Stdio-MCP-Server für Claude Code (.mcp.json, Server frieda-test): je Zeile eine JSON-RPC-Nachricht auf stdin, je
      Anfrage eine Zeile Antwort auf stdout, Benachrichtigungen ohne Antwort. Leitet an <FR_KN_ADRESSE>/mcp weiter,
      erneuert Tokens selbst (Rotation; eine Dateisperre verhindert, dass parallele Sitzungen dieselbe Familie zweimal
      einlösen) und prüft beim Start, dass der Zugang zum Testkonto gehört und kein Betreiber ist; sonst Abbruch ohne
      Weiterleitung. Ist der Konnektor nicht erreichbar oder scheitert die Erneuerung, bekommt die Anfrage eine
      JSON-RPC-Fehlerantwort -32603 und die Brücke läuft weiter; eine am Netz gescheiterte Kontoprüfung wird vor der
      nächsten Weiterleitung nachgeholt (#669). Nur Standardbibliothek: läuft mit dem python3 des Systems.

Instanzwerte (Umgebung vor der Einstellungsdatei der Instanz, wie engine/instanz.py): FR_KN_ADRESSE, FR_TESTKONTO,
FR_TESTZUGANG, für `einrichten` außerdem FR_KONTEN und FR_BASIS.
"""
import base64
from contextlib import closing
import fcntl
import hashlib
import http.client
import json
import os
import re
import secrets
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

LOOPBACK = "http://127.0.0.1/frieda-test"     # Rücksprung der Registrierung; der Code wird aus der Weiterleitung gelesen
GERAET = "Testzugang"
SITZUNG_SEKUNDEN = 300
VORLAUF = 60                                    # Sekunden: so kurz vor Ablauf gilt ein Access-Token schon als abgelaufen
PROTOKOLL = "2025-06-18"


class Abbruch(Exception):
    """Fehler mit einer Meldung für stderr; der Befehl endet mit Exit-Code 1."""


class ErneuernFehler(Abbruch):
    """Token-Erneuerung gescheitert. Die Brücke beantwortet die Anfrage mit einem Fehler und läuft weiter (#669)."""


class Serverfehler(Exception):
    """5xx bei der Kontoprüfung, etwa 502 hinter nginx während eines Neustarts: wie ein Netzfehler (#669, AC-6)."""


NETZFEHLER = (OSError, http.client.HTTPException, Serverfehler)    # Konnektor nicht erreichbar: abgelehnt, Zeitüberschreitung, …


# ---------------------------------------------------------------- Instanzwerte (wie engine/instanz.py, ohne Engine)

def _einstellungsdatei():
    if os.environ.get("FR_EINSTELLUNGEN"):
        return Path(os.environ["FR_EINSTELLUNGEN"])
    if os.environ.get("FR_DIENST"):
        dienst = Path(os.environ["FR_DIENST"])
    else:
        dienst = Path(os.environ.get("FR_SEITEN") or f"/srv/{os.environ.get('FR_INSTANZ') or 'frieda'}") / "_dienst"
    neu = dienst / "instanz" / "einstellungen.env"
    if neu.exists() or neu.is_symlink():
        return neu
    return Path(os.environ.get("FR_WURZEL") or Path.cwd()) / "betrieb" / "einstellungen.env"


def _einstellungen():
    try:
        zeilen = _einstellungsdatei().read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    werte = {}
    for z in zeilen:
        z = z.strip()
        if not z or z.startswith("#") or "=" not in z:
            continue
        name, wert = z.split("=", 1)
        if name.startswith("FR_") and name.replace("_", "").isalnum():
            if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "\"'":
                wert = wert[1:-1]
            werte[name] = wert
    return werte


def wert(name):
    """Instanzwert aus Umgebung oder Einstellungsdatei (leer zählt als nicht gesetzt) oder None."""
    return os.environ.get(name) or _einstellungen().get(name) or None


def ablage_pfad():
    p = wert("FR_TESTZUGANG")
    if p:
        return Path(p)
    dienst = wert("FR_DIENST")
    if not dienst:
        seiten = wert("FR_SEITEN") or f"/srv/{wert('FR_INSTANZ') or 'frieda'}"
        dienst = str(Path(seiten) / "_dienst")
    return Path(dienst) / "instanz" / "testzugang.json"


def adresse_konnektor():
    a = (wert("FR_KN_ADRESSE") or wert("FR_ADRESSE") or "").rstrip("/")
    if not a:
        raise Abbruch("FR_KN_ADRESSE missing (address of the connector).")
    return a


def testkonto():
    e = (wert("FR_TESTKONTO") or "").strip().lower()
    if not e:
        raise Abbruch("FR_TESTKONTO missing (address of the test account) in the settings of the instance.")
    return e


# ---------------------------------------------------------------- HTTP und Ablage

def anfrage(methode, url, body=None, kopf=None):
    """Eine Anfrage, ohne Weiterleitungen zu folgen. -> (status, {kopfzeile klein: wert}, bytes)"""
    t = urllib.parse.urlsplit(url)
    art = http.client.HTTPSConnection if t.scheme == "https" else http.client.HTTPConnection
    c = art(t.hostname, t.port, timeout=60)
    try:
        c.request(methode, (t.path or "/") + (f"?{t.query}" if t.query else ""), body=body, headers=kopf or {})
        r = c.getresponse()
        return r.status, {k.lower(): v for k, v in r.getheaders()}, r.read()
    finally:
        c.close()


def ablage_lesen(pfad):
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise Abbruch(f"No test access at {pfad}: run `testzugang.py einrichten` first.") from None
    except (OSError, ValueError) as f:
        raise Abbruch(f"Test access unreadable ({type(f).__name__}): {pfad}") from None


def ablage_schreiben(pfad, daten):
    """Atomar: temporäre Datei daneben (Rechte 600), fsync, Umbenennen."""
    pfad.parent.mkdir(parents=True, exist_ok=True)
    fd, zwischen = tempfile.mkstemp(dir=pfad.parent, prefix=f".{pfad.name}.", suffix=".neu")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            os.fchmod(f.fileno(), 0o600)
            json.dump(daten, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(zwischen, pfad)
    except BaseException:
        Path(zwischen).unlink(missing_ok=True)
        raise
    try:
        d = os.open(pfad.parent, os.O_RDONLY)
        try:
            os.fsync(d)
        finally:
            os.close(d)
    except OSError:
        pass


def _tokens_uebernehmen(daten, t):
    return {**daten, "access_token": t["access_token"], "refresh_token": t["refresh_token"],
            "access_ablauf": int(time.time()) + int(t.get("expires_in") or 3600)}


# ---------------------------------------------------------------- einrichten

def einrichten():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
    import instanz
    import konten
    import pruefsitzung

    try:
        email = konten.adresse(testkonto())
    except konten.KontoFehler:
        raise Abbruch("FR_TESTKONTO is not a valid e-mail address.") from None
    adresse = adresse_konnektor()
    basis = (instanz.wert("FR_BASIS") or adresse).rstrip("/")
    pfad = ablage_pfad()
    k = konten.konto_per_email(email)
    # Kontaktadresse aus Umgebung, Einstellungsdatei oder <FR_DIENST>/konten.env (#670)
    kontakt = (instanz.wert("FR_BETREIBER_KONTAKT") or instanz.konten_wert("FR_BETREIBER_KONTAKT")
               or "").strip().lower()
    if (k and "betreiber" in k.get("rechte", [])) or email == kontakt:
        raise Abbruch(f"{email} is an operator account; the test account must never be one. Nothing set up.")

    kid, sitzung = pruefsitzung.sitzung_ausstellen(email, "Frieda-Test", GERAET, SITZUNG_SEKUNDEN)
    try:
        konten.recht_setzen(kid, "reise_anlegen")
        s, _, t = anfrage("POST", f"{adresse}/register", json.dumps(
            {"client_name": "frieda-test", "redirect_uris": [LOOPBACK]}).encode(), {"Content-Type": "application/json"})
        if s != 201:
            raise Abbruch(f"Registration failed (HTTP {s}).")
        client_id = json.loads(t)["client_id"]
        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        q = {"response_type": "code", "client_id": client_id, "redirect_uri": LOOPBACK, "code_challenge": challenge,
             "code_challenge_method": "S256", "state": secrets.token_urlsafe(12), "scope": "frieda offline_access"}
        keks = {"Cookie": f"{pruefsitzung.rm.COOKIE}={sitzung}"}
        s, _, _ = anfrage("GET", f"{adresse}/authorize?{urllib.parse.urlencode(q)}", kopf=keks)
        if s != 200:
            raise Abbruch(f"Authorization page failed (HTTP {s}).")
        s, h, _ = anfrage("POST", f"{adresse}/authorize", urllib.parse.urlencode({**q, "aktion": "erlauben"}).encode(),
                       {**keks, "Origin": basis, "Content-Type": "application/x-www-form-urlencoded"})
        ziel = urllib.parse.parse_qs(urllib.parse.urlsplit(h.get("location", "")).query)
        if s != 303 or "code" not in ziel or ziel.get("state") != [q["state"]]:
            raise Abbruch(f"Consent failed (HTTP {s}).")
        s, _, t = anfrage("POST", f"{adresse}/token", urllib.parse.urlencode(
            {"grant_type": "authorization_code", "code": ziel["code"][0], "redirect_uri": LOOPBACK,
             "client_id": client_id, "code_verifier": verifier}).encode(),
            {"Content-Type": "application/x-www-form-urlencoded"})
        if s != 200:
            raise Abbruch(f"Token exchange failed (HTTP {s}).")
        tokens = json.loads(t)
    finally:
        with closing(konten.db()) as v, v:
            v.execute("DELETE FROM sitzungen WHERE konto = ? AND geraet = ?", (kid, GERAET))

    alt = None
    if pfad.exists():
        try:
            alt = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            alt = None
    ablage_schreiben(pfad, _tokens_uebernehmen({"client_id": client_id, "konto": email}, tokens))
    if isinstance(alt, dict):           # alten Zugang widerrufen: seine Token-Familie und alles seines Clients
        with closing(konten.db()) as v, v:
            z = v.execute("SELECT familie FROM oauth_tokens WHERE hash = ? AND art = 'refresh'",
                          (konten._hash("refresh", str(alt.get("refresh_token") or "")),)).fetchone()
            if z:
                v.execute("DELETE FROM oauth_tokens WHERE familie = ?", (z["familie"],))
            if alt.get("client_id") and alt.get("client_id") != client_id:
                v.execute("DELETE FROM oauth_tokens WHERE client_id = ?", (alt["client_id"],))
    print(f"Test access for {email} set up: {pfad}")
    return 0


# ---------------------------------------------------------------- dienst

class Bruecke:
    def __init__(self, adresse, pfad):
        self.adresse, self.pfad = adresse, pfad
        self.daten = ablage_lesen(pfad)
        self.geprueft = False

    def erneuern(self, fehlgeschlagen):
        """Refresh-Token einlösen, unter einer Dateisperre: Hat ein anderer Prozess inzwischen erneuert (anderes,
        noch gültiges Access-Token in der Ablage), wird dessen Paar übernommen statt die Familie erneut einzulösen."""
        sperre = os.open(self.pfad.with_name(self.pfad.name + ".sperre"), os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(sperre, fcntl.LOCK_EX)
            daten = ablage_lesen(self.pfad)
            if daten.get("access_token") != fehlgeschlagen and daten.get("access_ablauf", 0) > time.time() + VORLAUF:
                self.daten = daten
                return
            s, _, t = anfrage("POST", f"{self.adresse}/token", urllib.parse.urlencode(
                {"grant_type": "refresh_token", "refresh_token": daten.get("refresh_token") or "",
                 "client_id": daten.get("client_id") or ""}).encode(),
                {"Content-Type": "application/x-www-form-urlencoded"})
            if s != 200:
                raise ErneuernFehler(f"Token refresh failed (HTTP {s}); run `testzugang.py einrichten` again.")
            try:                        # HTTP 200, aber unbrauchbare Antwort: Ablage bleibt unverändert (#738)
                neu = _tokens_uebernehmen(daten, json.loads(t))
            except (ValueError, TypeError, KeyError, AttributeError):
                raise ErneuernFehler("Token refresh failed (unusable answer); run `testzugang.py einrichten` again.") \
                    from None
            self.daten = neu
            ablage_schreiben(self.pfad, self.daten)
        finally:
            os.close(sperre)            # gibt die Sperre frei

    def senden(self, body):
        """POST <adresse>/mcp mit dem Access-Token; bei Ablauf oder 401 einmal erneuern. -> (status, bytes)"""
        if self.daten.get("access_ablauf", 0) <= time.time() + VORLAUF:
            self.erneuern(self.daten.get("access_token"))
        for versuch in range(2):
            access = self.daten.get("access_token") or ""
            s, _, t = anfrage("POST", f"{self.adresse}/mcp", body,
                           {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                            "Authorization": f"Bearer {access}"})
            if s == 401 and versuch == 0:
                self.erneuern(access)
                continue
            return s, t
        return s, t

    def frage(self, methode, params):
        s, t = self.senden(json.dumps({"jsonrpc": "2.0", "id": "frieda-test-pruefung", "method": methode,
                                       "params": params}).encode())
        try:
            a = json.loads(t)
        except ValueError:
            a = None
        if s >= 500:
            raise Serverfehler(f"Connector answered HTTP {s}")
        if s != 200 or not isinstance(a, dict) or "result" not in a:
            raise Abbruch(f"Connector check failed ({methode}, HTTP {s}).")
        return a["result"]

    def konto_pruefen(self, email):
        """Gehört der Zugang zum Testkonto (die Anleitung von initialize nennt das angemeldete Konto) und ist es kein
        Betreiber (Betreiber sehen request_decide in tools/list)?"""
        init = self.frage("initialize", {"protocolVersion": PROTOKOLL, "capabilities": {},
                                         "clientInfo": {"name": "frieda-test", "version": "1"}})
        anleitung = str(init.get("instructions") or "").lower()
        if not re.search(r"(?<![\w.+-])" + re.escape(email) + r"(?![\w.-])", anleitung):
            raise Abbruch(f"The stored access does not belong to the test account {email}; nothing forwarded.")
        namen = {w.get("name") for w in self.frage("tools/list", {}).get("tools", [])}
        if "request_decide" in namen:
            raise Abbruch(f"The test account {email} has operator rights; nothing forwarded.")
        self.geprueft = True

    def weiterleiten(self, email, body):
        """Eine beim Start am Netz gescheiterte Kontoprüfung wird zuerst nachgeholt (#669); erst danach senden."""
        if not self.geprueft:
            self.konto_pruefen(email)
        return self.senden(body)


def _voruebergehend(aufgabe):
    """-> (Ergebnis, None) oder (None, Fehlertext) bei Netzfehler oder gescheiterter Erneuerung (#669).
    Der Text nennt nur die Art des Fehlers, nie Tokens oder Pfade."""
    try:
        return aufgabe(), None
    except Serverfehler as f:
        return None, str(f)
    except NETZFEHLER as f:
        return None, f"Connector unreachable ({type(f).__name__})"
    except ErneuernFehler as f:
        return None, str(f)


def _fehler(nachricht, code, text):
    kennung = nachricht.get("id") if isinstance(nachricht, dict) else None
    return {"jsonrpc": "2.0", "id": kennung, "error": {"code": code, "message": text}}


def dienst():
    email = testkonto()
    b = Bruecke(adresse_konnektor(), ablage_pfad())
    _voruebergehend(lambda: b.konto_pruefen(email))   # Netzfehler: Prüfung bleibt ausstehend, die Brücke läuft
    for zeile in sys.stdin:
        zeile = zeile.strip()
        if not zeile:
            continue
        try:
            nachricht = json.loads(zeile)
        except ValueError:
            antwort = _fehler(None, -32700, "Parse error")
        else:
            ergebnis, text = _voruebergehend(lambda: b.weiterleiten(email, zeile.encode("utf-8")))
            if text is not None:
                if isinstance(nachricht, dict) and "id" not in nachricht:
                    continue                      # Benachrichtigung: auch im Fehlerfall keine Antwort
                antwort = _fehler(nachricht, -32603, text)
                sys.stdout.write(json.dumps(antwort, ensure_ascii=False) + "\n")
                sys.stdout.flush()
                continue
            s, t = ergebnis
            if s == 202 or (s == 200 and not t.strip()):
                continue                          # Benachrichtigung: keine Antwort
            try:
                antwort = json.loads(t)
            except ValueError:
                antwort = None
            if not isinstance(antwort, (dict, list)):
                if isinstance(nachricht, dict) and "id" not in nachricht:
                    continue
                antwort = _fehler(nachricht, -32603, f"Connector answered HTTP {s}")
        sys.stdout.write(json.dumps(antwort, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


def main(argv):
    befehle = {"einrichten": einrichten, "dienst": dienst}
    if len(argv) != 1 or argv[0] not in befehle:
        print(__doc__)
        return 2
    try:
        return befehle[argv[0]]()
    except Abbruch as f:
        print(f"ERROR: {f}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
