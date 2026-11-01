"""OAuth 2.1 für den Konnektor „Frieda“ (Paket J3, Issues #43 und #47): ein Konnektor für alle Reisen einer Person,
angemeldet mit ihrem Konto (E-Mail-Adresse und Code, engine/anmeldung.py).

Endpunkte unter Friedas Adresse (FR_BASIS), ausgeliefert vom Konnektor-Dienst:
  POST /mcp                                        MCP mit Bearer-Token; ohne gültiges Token 401 mit resource_metadata
  GET  /.well-known/oauth-protected-resource[/mcp] RFC 9728: resource = <FR_BASIS>/mcp, authorization_servers
  GET  /.well-known/oauth-authorization-server     RFC 8414: Endpunkte, S256, CIMD, offline_access
  POST /register                                   RFC 7591 (DCR), nur erlaubte Redirect-URIs
  GET  /authorize                                  Anmelden (falls nötig), dann Zustimmung: wer fragt, wohin es geht
  POST /authorize                                  Zustimmung -> Code an die Redirect-URI (mit state und iss)
  POST /token                                      authorization_code (PKCE S256 Pflicht), refresh_token (Rotation)

Wer darf fragen (Schutz vor Code-Diebstahl über fremde Clients, Claude-Doku „Authentication for connectors“, geprüft
27.10.2026): Redirect-URIs nur https://claude.ai/api/mcp/auth_callback (dazu FR_OAUTH_REDIRECTS, durch Komma getrennt)
und Loopback (http://localhost, http://127.0.0.1, jeder Port; Claude Code, MCP Inspector). Clients per DCR oder per
Client ID Metadata Document, dessen Adresse auf einem freigegebenen Host liegt (FR_CIMD_HOSTS, Vorgabe claude.ai).
Die Zustimmungsseite zeigt, welcher Client fragt und wohin der Code geht; bei Loopback mit Warnung.
"""
import base64
import hashlib
import html
import json
import os
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import sys

import anmeldung
import konten
import texte

CLAUDE_CALLBACK = "https://claude.ai/api/mcp/auth_callback"
SCOPES = ("frieda", "offline_access")
CHALLENGE_MUSTER = re.compile(r"^[A-Za-z0-9._~-]{43,128}$")
CIMD_CACHE_SEKUNDEN = 86400
LOOPBACK = ("localhost", "127.0.0.1")


def basis():
    return konten.basis()


def ressource():
    return basis() + "/mcp"


def metadaten_ressource():
    return {"resource": ressource(), "authorization_servers": [basis()], "scopes_supported": list(SCOPES),
            "bearer_methods_supported": ["header"], "resource_name": "Frieda"}


def metadaten_server():
    b = basis()
    return {"issuer": b, "authorization_endpoint": b + "/authorize", "token_endpoint": b + "/token",
            "registration_endpoint": b + "/register", "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"], "token_endpoint_auth_methods_supported": ["none"],
            "scopes_supported": list(SCOPES), "client_id_metadata_document_supported": True,
            "authorization_response_iss_parameter_supported": True}


def www_authenticate(fehler=False):
    zeiger = f'Bearer resource_metadata="{basis()}/.well-known/oauth-protected-resource/mcp"'
    return zeiger + (', error="invalid_token"' if fehler else "")


# ---------------------------------------------------------------- Redirects und Clients

def _feste_redirects():
    extra = [x.strip() for x in os.environ.get("FR_OAUTH_REDIRECTS", "").split(",") if x.strip()]
    return {CLAUDE_CALLBACK, *extra}


def loopback(uri):
    u = urllib.parse.urlsplit(uri or "")
    return u.scheme == "http" and u.hostname in LOOPBACK and not u.username and not u.password


def redirect_erlaubt(uri):
    """Darf überhaupt ein Code an diese Adresse gehen?"""
    if not isinstance(uri, str) or len(uri) > 500 or "#" in uri:
        return False
    return uri in _feste_redirects() or loopback(uri)


def redirect_passt(registriert, uri):
    """uri ist registriert; Loopback ohne Rücksicht auf den Port (RFC 8252 7.3, Claude Code wählt ihn je Sitzung)."""
    if not redirect_erlaubt(uri):
        return False
    if uri in registriert:
        return True
    if loopback(uri):
        u = urllib.parse.urlsplit(uri)
        return any(loopback(r) and (lambda v: (v.hostname, v.path, v.query) == (u.hostname, u.path, u.query))(
            urllib.parse.urlsplit(r)) for r in registriert)
    return False


USER_AGENT = "Frieda-Reist/1 (OAuth client metadata; +https://github.com/henemm/frieda-reist)"


def cimd_erlaubt(client_id):
    hosts = [h.strip() for h in os.environ.get("FR_CIMD_HOSTS", "claude.ai").split(",") if h.strip()]
    u = urllib.parse.urlsplit(client_id or "")
    return u.scheme == "https" and u.hostname in hosts and not u.port and not u.username and u.path not in ("", "/")


class _KeineWeiterleitung(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def cimd_laden(client_id):
    """Client ID Metadata Document holen (nur von freigegebenen Hosts, ohne Weiterleitungen, höchstens 64 KB)."""
    if not cimd_erlaubt(client_id):
        # Nur den Host protokollieren: zeigt bei der ersten echten Verbindung, ob FR_CIMD_HOSTS passt
        print(f"OAuth: Client-Dokument von nicht freigegebenem Host abgelehnt: "
              f"{urllib.parse.urlsplit(client_id or '').hostname}", file=sys.stderr, flush=True)
        return None
    alt = konten.oauth_client(client_id)
    if alt and alt["art"] == "cimd" and time.time() - alt["erstellt"] < CIMD_CACHE_SEKUNDEN:
        return alt
    try:
        oeffner = urllib.request.build_opener(_KeineWeiterleitung)
        # Eigene Kennung: claude.ai (Cloudflare) weist die Standardkennung „Python-urllib“ mit 403 ab (28.10.2026)
        anfrage = urllib.request.Request(client_id, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
        with oeffner.open(anfrage, timeout=5) as r:
            doc = json.loads(r.read(65536 + 1)[:65536])
    except (urllib.error.URLError, OSError, ValueError) as f:
        print(f"OAuth: Client-Dokument von {urllib.parse.urlsplit(client_id).hostname} nicht lesbar: "
              f"{getattr(f, 'code', '') or type(f).__name__}", file=sys.stderr, flush=True)
        return alt
    uris = doc.get("redirect_uris") if isinstance(doc, dict) else None
    if not isinstance(doc, dict) or doc.get("client_id") != client_id or not isinstance(uris, list) \
            or not all(isinstance(x, str) for x in uris):
        return None
    konten.oauth_client_speichern(client_id, str(doc.get("client_name") or ""), uris, "cimd")
    return konten.oauth_client(client_id)


def client_finden(client_id):
    if isinstance(client_id, str) and client_id.startswith("https://"):
        return cimd_laden(client_id)
    return konten.oauth_client(client_id) if isinstance(client_id, str) and len(client_id) < 100 else None


def registrieren(body, ip):
    """DCR (RFC 7591). -> (code, json)"""
    if not konten.oauth_registrierung_erlaubt(ip):
        return 429, {"error": "too_many_requests"}
    try:
        roh = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return 400, {"error": "invalid_client_metadata", "error_description": "kein JSON"}
    uris = roh.get("redirect_uris") if isinstance(roh, dict) else None
    if not isinstance(uris, list) or not uris or len(uris) > 10 or not all(redirect_erlaubt(u) for u in uris):
        return 400, {"error": "invalid_redirect_uri",
                     "error_description": "Erlaubt sind die Claude-Callback-Adresse und Loopback-Adressen."}
    if roh.get("token_endpoint_auth_method", "none") != "none":
        return 400, {"error": "invalid_client_metadata", "error_description": "nur öffentliche Clients (none)"}
    cid = "c_" + secrets.token_urlsafe(16)
    name = str(roh.get("client_name") or "")[:200]
    konten.oauth_client_speichern(cid, name, uris, "dcr")
    return 201, {"client_id": cid, "client_id_issued_at": int(time.time()), "client_name": name, "redirect_uris": uris,
                 "token_endpoint_auth_method": "none", "grant_types": ["authorization_code", "refresh_token"],
                 "response_types": ["code"]}


# ---------------------------------------------------------------- Autorisieren

FELDER = ("response_type", "client_id", "redirect_uri", "code_challenge", "code_challenge_method", "state", "scope",
          "resource")


def anfrage_pruefen(q):
    """-> (client, None) oder (None, Fehlertext). Fehler hier gehen nie an die Redirect-URI (sie ist nicht geprüft)."""
    c = client_finden(q.get("client_id"))
    if not c:
        return None, anmeldung.tx("konto.oauth.unbekannter_client")
    if not redirect_passt(c["redirect_uris"], q.get("redirect_uri")):
        return None, anmeldung.tx("konto.oauth.ruecksprung")
    if q.get("response_type") != "code":
        return None, anmeldung.tx("konto.oauth.nur_code")
    if q.get("code_challenge_method") != "S256" or not CHALLENGE_MUSTER.match(q.get("code_challenge") or ""):
        return None, anmeldung.tx("konto.oauth.pkce")
    if q.get("resource") and q["resource"].rstrip("/") != ressource():
        return None, anmeldung.tx("konto.oauth.ressource")
    if len(q.get("state") or "") > 500:
        return None, anmeldung.tx("konto.oauth.state_lang")
    return c, None


def scope_von(q):
    gewuenscht = (q.get("scope") or "frieda").split()
    return " ".join(s for s in SCOPES if s in gewuenscht or s == "frieda")


def ziel_mit(uri, **werte):
    u = urllib.parse.urlsplit(uri)
    q = urllib.parse.parse_qsl(u.query) + [(k, v) for k, v in werte.items() if v]
    return urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, urllib.parse.urlencode(q), ""))


def csp_fuer(uri):
    if loopback(uri):
        ziel = "http://localhost:* http://127.0.0.1:*"
    else:
        u = urllib.parse.urlsplit(uri)
        ziel = f"{u.scheme}://{u.netloc}"
    return ("Content-Security-Policy", f"default-src 'none'; img-src 'self'; font-src 'self'; style-src 'unsafe-inline'; form-action 'self' {ziel}; "
                                       "frame-ancestors 'none'; base-uri 'none'")


def zustimmung(q, c, k, meldung=""):
    e = html.escape
    tx = anmeldung.tx
    host = urllib.parse.urlsplit(q["redirect_uri"]).hostname or "?"
    # Wer fragt: bei einem Client-Dokument dessen Host, sonst der Name, den das Programm selbst angibt (darum in
    # Anführungszeichen); ohne Namen „ein Programm“
    wer = urllib.parse.urlsplit(c["client_id"]).hostname if c["art"] == "cimd" else c["name"]
    frage = tx("konto.oauth.frage", wer=wer) if wer else tx("konto.oauth.frage_ohne_name")
    warnung = anmeldung.fehler(tx("konto.oauth.warnung_localhost")) if loopback(q["redirect_uri"]) else ""
    verdeckt = anmeldung.verdeckt(**{f: q.get(f, "") for f in FELDER})
    return anmeldung.seite(tx("konto.oauth.titel"), anmeldung.karte(
        f"<div><h1>{e(frage)}</h1>",
        f'<p class="hinweis" style="margin:.3rem 0 0">' + anmeldung.th("konto.oauth.angemeldet_als", name=f"<strong>{e(k['name'])}</strong>", email=e(k["email"])) + "</p></div>",
        f'<div><strong>{e(tx("konto.oauth.darf"))}</strong><ul class="darf" style="margin:.6rem 0 0">'
        f'<li>{e(tx("konto.oauth.darf_lesen"))}</li><li>{e(tx("konto.oauth.darf_schreiben"))}</li></ul></div>',
        '<p class="kasten">' + anmeldung.th("konto.oauth.weiter_zu", host=f"<strong>{e(host)}</strong>") + "</p>",
        warnung, anmeldung.fehler(meldung),
        anmeldung.formular("/authorize", verdeckt + anmeldung.verdeckt(aktion="erlauben"), tx("konto.oauth.erlauben")),
        anmeldung.formular("/authorize", verdeckt + anmeldung.verdeckt(aktion="abbrechen"), tx("konto.oauth.abbrechen"), "link")),
        anmeldung.fuss(tx("konto.oauth.beenden")))


def autorisieren(methode, pfad, headers, body):
    teile = urllib.parse.urlsplit(pfad)
    _, konto_sitzung = anmeldung.sitzung_aus(headers)   # Sprache der Seite: die des Kontos, sonst die des Browsers
    anmeldung._anfrage.sprache = konto_sitzung["sprache"] if konto_sitzung else texte.aus_header(headers.get("Accept-Language"))
    if methode == "POST":
        if not anmeldung.herkunft_ok(headers):
            return anmeldung.antwort(403, anmeldung.seite(anmeldung.tx("konto.nicht_erlaubt"), anmeldung.karte(
                f"<h1>{html.escape(anmeldung.tx('konto.nicht_erlaubt'))}</h1><p>{html.escape(anmeldung.tx('konto.fehler.nicht_erlaubt'))}</p>")))
        q = {k: v[0] for k, v in urllib.parse.parse_qs(body.decode("utf-8", "replace")).items()}
    else:
        q = {k: v[0] for k, v in urllib.parse.parse_qs(teile.query).items()}
    c, fehler = anfrage_pruefen(q)
    if fehler:
        return anmeldung.antwort(400, anmeldung.seite(anmeldung.tx("konto.oauth.nicht_moeglich"), anmeldung.karte(
            f"<h1>{html.escape(anmeldung.tx('konto.oauth.nicht_moeglich'))}</h1>", anmeldung.fehler(fehler),
            f"<p>{html.escape(anmeldung.tx('konto.oauth.neu_verbinden'))}</p>")))
    _, k = anmeldung.sitzung_aus(headers)
    if not k:
        weiter = "/authorize?" + urllib.parse.urlencode({f: q[f] for f in FELDER if q.get(f)})
        return anmeldung.weiter("/anmelden?" + urllib.parse.urlencode({"zurueck": weiter}))
    if methode == "GET":
        code, kopf, inhalt = anmeldung.antwort(200, zustimmung(q, c, k))
        return code, [*kopf, csp_fuer(q["redirect_uri"])], inhalt
    if q.get("aktion") != "erlauben":
        return 303, [("Location", ziel_mit(q["redirect_uri"], error="access_denied", state=q.get("state"),
                                           iss=basis())), csp_fuer(q["redirect_uri"])], b""
    code = konten.oauth_code_anlegen(c["client_id"], q["redirect_uri"], q["code_challenge"], scope_von(q), k["id"])
    return 303, [("Location", ziel_mit(q["redirect_uri"], code=code, state=q.get("state"), iss=basis())),
                 csp_fuer(q["redirect_uri"])], b""


# ---------------------------------------------------------------- Token

def s256(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")


def token(body, content_type):
    """POST /token (application/x-www-form-urlencoded). -> (code, json)"""
    if not (content_type or "").startswith("application/x-www-form-urlencoded"):
        return 400, {"error": "invalid_request", "error_description": "Formular erwartet"}
    f = {k: v[0] for k, v in urllib.parse.parse_qs(body.decode("utf-8", "replace")).items()}
    art = f.get("grant_type")
    if not client_finden(f.get("client_id")):
        return 401, {"error": "invalid_client"}
    if art == "authorization_code":
        v = f.get("code_verifier") or ""
        if not CHALLENGE_MUSTER.match(v):
            return 400, {"error": "invalid_grant", "error_description": "code_verifier fehlt oder ist ungültig"}
        t = konten.oauth_code_einloesen(f.get("code"), f["client_id"], f.get("redirect_uri"),
                                         lambda ch: secrets.compare_digest(s256(v), ch))
    elif art == "refresh_token":
        t = konten.oauth_erneuern(f.get("refresh_token"), f["client_id"])
    else:
        return 400, {"error": "unsupported_grant_type"}
    return (200, t) if t else (400, {"error": "invalid_grant"})


def bearer(headers):
    a = headers.get("Authorization") or ""
    return a[7:].strip() if a[:7].lower() == "bearer " else None


# ---------------------------------------------------------------- Verteiler (Konnektor-Dienst)

def ist_unsere(pfad):
    p = pfad.split("?", 1)[0]
    return p in ("/register", "/authorize", "/token") or p.startswith("/.well-known/oauth-")


def bearbeiten(methode, pfad, headers, body, ip):
    """-> (code, kopfzeilen, body) für die OAuth-Endpunkte."""
    p = pfad.split("?", 1)[0]
    j = lambda code, obj, extra=(): (code, [("Content-Type", "application/json"), *extra],
                                     json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    if not basis():
        return j(404, {"error": "not_configured"})
    if p.startswith("/.well-known/oauth-protected-resource") and methode == "GET":
        return j(200, metadaten_ressource(), [("Access-Control-Allow-Origin", "*")])
    if p == "/.well-known/oauth-authorization-server" and methode == "GET":
        return j(200, metadaten_server(), [("Access-Control-Allow-Origin", "*")])
    if p == "/register" and methode == "POST":
        return j(*registrieren(body, ip))
    if p == "/token" and methode == "POST":
        return j(*token(body, headers.get("Content-Type")))
    if p == "/authorize" and methode in ("GET", "POST"):
        return autorisieren(methode, pfad, headers, body)
    return j(404, {"error": "not_found"})
