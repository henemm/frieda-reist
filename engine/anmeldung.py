"""Anmeldeseiten für Konten (Paket J2, Issues #43 und #46). Der Konnektor-Dienst liefert sie unter Friedas eigener
Adresse aus (FR_BASIS): /anmelden, /einladung/<token>, /konto, /abmelden.

Ablauf: E-Mail-Adresse eingeben -> Code per Mail -> Code eingeben (beim ersten Mal auch den Namen) -> angemeldet.
Der Code ist der Hauptweg; der Link aus der Mail enthält keinen Code und öffnet nur die Code-Seite (Mailprogramme rufen
Links vorab auf, und Codes gehören nicht in Protokolle). Die Sitzung steht im Cookie __Host-frieda (HttpOnly, Secure,
SameSite=Lax, ein Jahr, rollierend). Jede Änderung (POST) muss von Friedas eigener Adresse kommen (Origin), sonst
403 (CSRF; SameSite trennt nicht von Nachbar-Subdomains). Rückkehradressen sind nur Pfade auf Friedas Adresse.

Reiseseiten bleiben zum Lesen über ihren geheimen Link offen; mitmachen geht nach dem Anmelden (Rückmeldedienst).
"""
import html
import json
import os
import re
import threading
import urllib.parse

import kalender
import konten
from reise import rolle_neu
import rueckmeldungen as rm
import texte

COOKIE = rm.COOKIE
JAHR = 365 * 86400

# Sprache der Seite (ADR-0006): vor dem Anmelden aus Accept-Language, danach die des Kontos. Jede Anfrage läuft in einem eigenen
# Thread des Dienstes; bearbeiten() setzt die Sprache, die Seitenfunktionen lesen sie mit tx()/th().
_anfrage = threading.local()


def sprache_der_seite():
    return getattr(_anfrage, "sprache", texte.VORGABE)


def tx(schluessel, **werte):
    """Text aus dem Katalog in der Sprache der Seite (Klartext, nicht für HTML)."""
    return texte.t(sprache_der_seite(), schluessel, **werte)


def th(schluessel, **html_werte):
    """Text aus dem Katalog als HTML: der Text wird maskiert, die Werte sind schon HTML (zum Beispiel <strong>…</strong>)."""
    marken = {k: f"\u0000{k}\u0000" for k in html_werte}
    text = html.escape(texte.t(sprache_der_seite(), schluessel, **marken), quote=True)
    for k, v in html_werte.items():
        text = text.replace(f"\u0000{k}\u0000", v)
    return text


def fett(wert):
    return f"<strong>{esc(wert)}</strong>"

# Gesicht „B2 Freundlich“ wie die Reiseseiten (docs/design.md): heller Grund, Flächen ohne Rahmen mit weichem Schatten,
# Radius 18 px, Knöpfe als Pillen, Source Sans 3 (liefert der Konnektor unter /schrift/ aus). Entwurf und Entscheidung: #60.
CSS = """
@font-face{font-family:"Source Sans 3";font-style:normal;font-weight:200 900;font-display:swap;
src:url(/schrift/source-sans-3-latin-ext-wght-normal.woff2) format("woff2-variations");
unicode-range:U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C4,U+2113,U+2C60-2C7F,U+A720-A7FF}
@font-face{font-family:"Source Sans 3";font-style:normal;font-weight:200 900;font-display:swap;
src:url(/schrift/source-sans-3-latin-wght-normal.woff2) format("woff2-variations");
unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
:root{--bg:#f8f8f5;--fg:#1d2420;--mut:#5b645e;--card:#ffffff;--line:#e4e5df;--feld:#d3d6cf;--acc:#1f7a57;--acc2:#e3f1ea;
--neutral:#efefea;--warn:#9a5b00;--warnbg:#fbeed6;--gefahr:#a33b2b;--schatten:0 1px 2px rgba(29,36,32,.06),0 8px 24px rgba(29,36,32,.07)}
@media (prefers-color-scheme:dark){:root{--bg:#151816;--fg:#eceee9;--mut:#a5aca6;--card:#1d211e;--line:#2c312d;--feld:#3a403b;
--acc:#6fd0a5;--acc2:#1f3329;--neutral:#272b28;--warn:#f0c46a;--warnbg:#3a3017;--gefahr:#f08a7a;--schatten:none}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:1.0625rem/1.45 "Source Sans 3",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:28rem;margin:0 auto;padding:1.25rem 1rem 2.5rem;display:flex;flex-direction:column;gap:1.5rem}
.kopf{display:flex;align-items:center;justify-content:center;gap:.6rem;padding-top:1.5rem;font-weight:700;font-size:1.375rem}
.kopf img{width:28px;height:28px;border-radius:7px}
.kopf.breit{justify-content:space-between;padding-top:0}.kopf.breit span{display:flex;align-items:center;gap:.5rem;font-size:1.25rem}
.karte{background:var(--card);border-radius:18px;box-shadow:var(--schatten);padding:1.6rem 1.35rem 1.4rem;display:flex;flex-direction:column;gap:1rem}
.karte>*,.karte form>*{margin:0}
h1{font-size:1.625rem;line-height:1.2;margin:0}h2{font-size:1.1875rem;margin:0 .25rem}
.lead,.hinweis,.klein{color:var(--mut)}.klein{font-size:.875rem}.lead strong{color:var(--fg);font-weight:600}
form{display:flex;flex-direction:column;gap:.5rem;margin:0}
label{font-size:.9375rem;font-weight:600}
input[type=email],input[type=text],select{width:100%;height:3.125rem;padding:0 .875rem;font:inherit;color:var(--fg);
background:var(--bg);border:1.5px solid var(--feld);border-radius:12px}
input.code{height:3.6rem;font-size:1.75rem;font-weight:600;letter-spacing:.28em;text-align:center}
button,a.knopf{display:flex;align-items:center;justify-content:center;min-height:3.125rem;margin-top:.5rem;padding:.5rem 1.25rem;
font-family:inherit;font-size:1.0625rem;font-weight:600;border:0;border-radius:999px;background:var(--acc);color:var(--card);cursor:pointer;text-decoration:none}
button.leise{background:var(--acc2);color:var(--acc)}button.neutral{background:var(--neutral);color:var(--fg)}
button.gefahr{background:var(--gefahr);color:var(--card)}
button.link{background:none;color:var(--acc);min-height:2.75rem;margin:0;padding:.5rem .25rem;font-size:1rem}
a{color:var(--acc)}.links{display:flex;justify-content:center;flex-wrap:wrap;gap:0 1.4rem}.links a{font-weight:600;font-size:1rem;text-decoration:none;padding:.6rem .25rem}
.fuss{display:flex;flex-direction:column;gap:.6rem;padding:0 .4rem;font-size:.875rem;color:var(--mut)}.fuss p{margin:0}
.fehler{background:var(--warnbg);color:var(--warn);padding:.6rem .8rem;border-radius:12px}
.neu{border-top:1px solid var(--line);margin-top:.75rem;padding-top:1rem;display:flex;flex-direction:column;gap:.5rem}
.marke{align-self:flex-start;font-size:.8125rem;font-weight:600;color:var(--acc);background:var(--acc2);border-radius:999px;padding:.1rem .6rem}
.marke.leise{color:var(--mut);background:var(--neutral)}
.darf{list-style:none;padding:0;display:flex;flex-direction:column;gap:.6rem}
.darf li{display:flex;gap:.6rem}.darf li::before{content:"✓";flex:none;width:1.4rem;height:1.4rem;border-radius:50%;
background:var(--acc2);color:var(--acc);font-weight:700;font-size:.85rem;display:flex;align-items:center;justify-content:center}
.kasten{background:var(--bg);border-radius:12px;padding:.65rem .8rem;font-size:.875rem;color:var(--mut)}.kasten strong{color:var(--fg)}
.abschnitt{display:flex;flex-direction:column;gap:.6rem}.abschnitt>p{margin:0 .25rem;font-size:.9375rem}
.liste{background:var(--card);border-radius:18px;box-shadow:var(--schatten);display:flex;flex-direction:column;overflow:hidden}
.liste>*+*{border-top:1px solid var(--line)}
.zeile{display:flex;align-items:center;gap:.75rem;padding:.9rem 1rem;color:var(--fg);text-decoration:none;cursor:pointer;list-style:none}
.zeile::-webkit-details-marker{display:none}
.zeile::after{content:"›";color:var(--mut);font-size:1.4rem;line-height:1}details[open]>.zeile::after{transform:rotate(90deg)}
.zeile .was{flex:1;min-width:0;display:flex;flex-direction:column;gap:.2rem}.zeile .titel{font-weight:600}
.zeile .wert{color:var(--mut);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:55%}
details>.inhalt{padding:0 1rem 1rem;display:flex;flex-direction:column;gap:.5rem}
.kalender-links{display:flex;flex-wrap:wrap;justify-content:space-between;gap:0 1rem}
.kalender-links>a,.kalender-links summary{font-weight:600;color:var(--acc);text-decoration:none;padding:.4rem 0;cursor:pointer;list-style:none}
.kalender-links summary::-webkit-details-marker{display:none}.kalender-links details[open]{flex-basis:100%}
.kalender-links details[open]>summary{margin-bottom:.5rem}
fieldset{border:0;padding:0;margin:.5rem 0 0;display:flex;flex-direction:column;gap:.35rem}legend{font-weight:600;padding:0;margin-bottom:.25rem}
label.haken{font-weight:400;font-size:1rem;display:flex;gap:.5rem;align-items:flex-start}
label.haken input{width:1.15rem;height:1.15rem;margin-top:.2rem;accent-color:var(--acc)}
.bestaetigen{background:var(--bg);border-radius:12px;padding:.75rem}.bestaetigen input{accent-color:var(--gefahr)}
ul.geraete{margin:0;padding-left:1.1rem}
.zurueck{font-weight:600;text-decoration:none;padding:.5rem .25rem;align-self:flex-start}
"""


def esc(t):
    return html.escape(str(t or ""), quote=True)


def seite(titel, *teile, kopf=None):
    """Ganze Seite. kopf: eigener Kopf (Mein Konto); sonst Friedas Zeichen mittig über der Karte."""
    rumpf = "".join(teile)
    sp = sprache_der_seite()
    kopf = kopf if kopf is not None else '<header class="kopf"><img src="/favicon.svg" alt="">Frieda</header>'
    return (f'<!DOCTYPE html><html lang="{esc(sp)}" dir="{esc(texte.sprache(sp).RICHTUNG)}"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">'
            f'<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="icon" href="/favicon.ico" sizes="48x48">'
            f'<link rel="apple-touch-icon" href="/apple-touch-icon.png">'
            f'<title>{esc(titel)} – Frieda</title><style>{CSS}</style></head><body>'
            f'<main>{kopf}{rumpf}</main></body></html>')


def karte(*teile):
    return '<section class="karte">' + "".join(teile) + "</section>"


def fehler(t):
    return f'<p class="fehler" role="alert">{esc(t)}</p>' if t else ""


def verdeckt(**felder):
    return "".join(f'<input type="hidden" name="{esc(k)}" value="{esc(v)}">' for k, v in felder.items() if v)


def formular(ziel, inhalt, knopf, klasse=""):
    k = f' class="{klasse}"' if klasse else ""
    return f'<form method="post" action="{esc(ziel)}">{inhalt}<button{k}>{esc(knopf)}</button></form>'


def fuss(*saetze):
    """Leise Zeilen unter der Karte."""
    return '<div class="fuss">' + "".join(f"<p>{esc(t)}</p>" for t in saetze if t) + "</div>"


def antwort(code, body, extra=()):
    return code, [("Content-Type", "text/html; charset=utf-8"), *extra], body.encode("utf-8")


def weiter(ziel, extra=()):
    return 303, [("Location", ziel), *extra], b""


def cookie_setzen(token):
    return ("Set-Cookie", f"{COOKIE}={token}; Path=/; Max-Age={JAHR}; Secure; HttpOnly; SameSite=Lax")


def cookie_loeschen():
    return ("Set-Cookie", f"{COOKIE}=; Path=/; Max-Age=0; Secure; HttpOnly; SameSite=Lax")


def rueckweg(roh):
    """Nur Pfade auf Friedas eigener Adresse (kein offener Umleiter). Lang genug für /authorize mit allen Angaben."""
    r = roh or ""
    if not r.startswith("/") or r.startswith("//") or "\\" in r or len(r) > 2000 or re.search(r"[\x00-\x1f]", r):
        return "/konto"
    return r


# ---------------------------------------------------------------- Seiten

def adress_seite(zurueck="", einladung="", email="", meldung=""):
    return seite(tx("konto.anmelden.titel"), karte(
        f"<div><h1>{esc(tx('konto.anmelden.ueberschrift'))}</h1>",
        f'<p class="lead">{esc(tx("konto.anmelden.hinweis"))}</p></div>',
        fehler(meldung),
        formular("/anmelden", verdeckt(schritt="adresse", zurueck=zurueck, einladung=einladung)
                 + f'<label for="email">{esc(tx("konto.email_adresse"))}</label>'
                 f'<input id="email" type="email" name="email" value="{esc(email)}" autocomplete="email" required '
                 f'placeholder="{esc(tx("konto.email_beispiel"))}" autofocus>', tx("konto.code_schicken"))),
        fuss(tx("konto.anmelden.nur_lesen"), tx("konto.datenschutz")))


def code_seite(email, zurueck="", einladung="", code="", meldung="", name_noetig=False, name=""):
    name_feld = (f'<div class="neu"><span class="marke">{esc(tx("konto.code.neu_hier"))}</span>'
                 f'<label for="name">{esc(tx("konto.name_frage"))}</label>'
                 f'<input id="name" type="text" name="name" value="{esc(name)}" maxlength="{konten.MAX_NAME}" '
                 f'autocomplete="given-name" placeholder="{esc(tx("konto.name_beispiel"))}" required>'
                 f'<p class="klein">{esc(tx("konto.name_hinweis"))}</p></div>'
                 if name_noetig else "")
    neuer_code = (f'<form method="post" action="/anmelden">{verdeckt(schritt="adresse", email=email, zurueck=zurueck, einladung=einladung)}'
                  f'<button class="link">{esc(tx("konto.code.neuer_code"))}</button></form>')
    andere = f'<a href="/anmelden?{urllib.parse.urlencode({"zurueck": zurueck, "einladung": einladung})}">{esc(tx("konto.code.andere_adresse"))}</a>'
    return seite(tx("konto.code.titel"), karte(
        f"<div><h1>{esc(tx('konto.code.titel'))}</h1>",
        f'<p class="lead">{th("konto.code.gesendet", email=fett(email), minuten=str(konten.CODE_MINUTEN))}</p></div>'
        if not code else f'<p class="lead">{th("konto.code.anmelden_als", email=fett(email))}</p></div>',
        fehler(meldung),
        formular("/anmelden", verdeckt(schritt="code", email=email, zurueck=zurueck, einladung=einladung)
                 + f'<label for="code">{esc(tx("konto.code.label"))}</label>'
                 f'<input id="code" class="code" type="text" name="code" value="{esc(code)}" inputmode="numeric" '
                 'autocomplete="one-time-code" pattern="[0-9 ]{6,7}" maxlength="7" required'
                 f'{"" if code or name_noetig else " autofocus"}>'
                 + ("" if code else f'<p class="klein">{esc(tx("konto.code.spam"))}</p>') + name_feld, tx("konto.anmelden.titel"))),
        f'<div class="links">{neuer_code}{andere}</div>')


def kalender_reisen(k):
    """[(reise, daten, aufgaben, name der person)] aller veröffentlichten Reisen des Kontos (für den Kalender, #77)."""
    aus = []
    for m in konten.mitgliedschaften(k["id"]):
        try:
            d = json.loads((rm.seiten() / m["reise"] / "daten.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        p = next((x for x in (d.get("reise") or {}).get("personen") or [] if x.get("schluessel") == m["schluessel"]), {})
        o = rm.ordner(m["reise"])
        aus.append((m["reise"], d, rm.aufgaben(o) if o else [], p.get("name") or k["name"]))
    return aus


def kalender_antwort(k, datei=False, headers=None):
    """Persönlicher Kalender des Kontos mit seinen Einstellungen: als Abo (Kalender-App) oder als Datei (Download).
    Das Abo trägt ein ETag; fragt die App mit If-None-Match nach und hat sich nichts geändert, kommt 304 ohne Inhalt.
    Gespeichert werden darf es nur bei der App selbst (private), und nur nach Rückfrage (no-cache)."""
    text = kalender.ics_person(kalender_reisen(k), konten.kalender_einstellungen(k["id"]), sprache=sprache_der_seite())
    if datei:
        return 200, [("Content-Type", "text/calendar; charset=utf-8"), ("Cache-Control", "private, no-store"),
                     ("Content-Disposition", 'attachment; filename="frieda-reisen.ics"')], text.encode("utf-8")
    tag = kalender.etag(text)
    kopf = [("Content-Type", "text/calendar; charset=utf-8"), ("Cache-Control", "private, no-cache"), ("ETag", tag)]
    gefragt = (headers or {}).get("If-None-Match") or ""
    if tag in (x.strip() for x in gefragt.split(",")) or gefragt.strip() == "*":
        return 304, kopf[1:3], b""
    return 200, kopf, text.encode("utf-8")


def kalender_karte(k, reise_info, offen=False):
    """Kalender auf Mein Konto: Abo, Download und, hinter „Konfigurieren“, die Einstellungen für alle Reisen
    (Product Owner 30.10.2026; Gestalt #60)."""
    e = konten.kalender_einstellungen(k["id"])
    basis = os.environ.get("KN_BASIS")
    if basis:
        url = kalender.abo_url(basis, konten.kalender_token(k["id"]))
        # Je Programm der Weg, den es selbst vorsieht: webcal:// für Apple (und Outlook für Windows), „Kalender
        # hinzufügen“ bei Google, „Aus dem Internet abonnieren“ bei Outlook im Web; die https-Adresse für alle anderen
        abo = f'<a class="knopf" href="{esc(kalender.webcal(url))}">{esc(tx("konto.kalender.abonnieren_link"))}</a>'
        andere = (f'<a href="{esc(kalender.google(url))}" target="_blank" rel="noopener noreferrer">{esc(tx("konto.kalender.google_link"))}</a>'
                  f'<a href="{esc(kalender.outlook(url, tx("kalender.abo_name")))}" target="_blank" rel="noopener noreferrer">'
                  f'{esc(tx("konto.kalender.outlook_link"))}</a>')
        link = (f'<label for="kal-url">{esc(tx("konto.kalender.url_label"))}</label>'
                f'<input id="kal-url" type="text" readonly value="{esc(url)}">'
                f'<p class="klein">{esc(tx("konto.kalender.persoenlich"))}</p>')
    else:
        abo, andere, link = "", "", f'<p class="klein">{esc(tx("konto.kalender.abo_fehlt"))}</p>'
    haken = lambda name, an, text: (f'<label class="haken"><input type="checkbox" name="{esc(name)}" value="ja"'   # noqa: E731
                                    f'{" checked" if an else ""}> {esc(text)}</label>')
    wahl = lambda name, werte, jetzt: (f'<select id="{name}" name="{name}">' + "".join(   # noqa: E731
        f'<option value="{esc(w)}"{" selected" if w == jetzt else ""}>{esc(t)}</option>' for w, t in werte.items()) + "</select>")
    reisen = [(m["reise"], (reise_info(m["reise"]) or {}).get("titel") or m["reise"]) for m in konten.mitgliedschaften(k["id"])]
    felder = (verdeckt(aktion="kalender_einstellungen")
              + f"<fieldset><legend>{esc(tx('konto.kalender.was'))}</legend>"
              + "".join(haken("sorte_" + s_, s_ in e["sorten"], t) for s_, t in kalender.sorten(sprache_der_seite()).items())
              + haken("nur_meine_aufgaben", e["nur_meine_aufgaben"], tx("konto.kalender.nur_meine"))
              + "</fieldset>"
              + (f"<fieldset><legend>{esc(tx('konto.kalender.reisen'))}</legend>" + "".join(haken("reise_" + r, r not in e["reisen_aus"], t) for r, t in reisen)
                 + "</fieldset>" if reisen else "")
              + f'<label for="erinnerung_fristen">{esc(tx("konto.kalender.erinnerung_fristen"))}</label>'
              + wahl("erinnerung_fristen", kalender.erinnerungen(kalender.ERINNERUNG_FRISTEN_SCHLUESSEL, sprache_der_seite()), e["erinnerung_fristen"])
              + f'<label for="erinnerung_termine">{esc(tx("konto.kalender.erinnerung_termine"))}</label>'
              + wahl("erinnerung_termine", kalender.erinnerungen(kalender.ERINNERUNG_TERMINE_SCHLUESSEL, sprache_der_seite()), e["erinnerung_termine"])
              + f'<p class="klein">{esc(tx("konto.kalender.erinnerung_hinweis"))}</p>')
    einstellungen = (f'<details{" open" if offen else ""}><summary>{esc(tx("konto.kalender.konfigurieren"))}</summary>'
                     f'<div class="inhalt" style="padding:0">'
                     + formular("/konto", felder, tx("konto.kalender.speichern")) + link
                     + (formular("/konto", verdeckt(aktion="kalender_neu"), tx("konto.kalender.neuer_link"), "neutral") if basis else "")
                     + "</div></details>")
    return (f'<div class="abschnitt"><h2>{esc(tx("konto.kalender.titel"))}</h2>'
            + karte(f'<p>{esc(tx("konto.kalender.hinweis"))}</p>', abo,
                    f'<div class="kalender-links">{andere}<a href="/konto?kalender=datei">{esc(tx("konto.kalender.datei_link"))}</a>'
                    f"{einstellungen}</div>")
            + "</div>")


def push_karte(k, offen=False):
    """Benachrichtigungen auf Mein Konto (Issue #21): was aufs Handy kommt und die Ruhezeit, für alle Reisen gleich.
    Eingeschaltet wird je Gerät im Fuß der Reiseseite (dort liegt der Service Worker, der die Nachricht zeigt)."""
    import push
    e = push.einstellungen_von(k["id"])
    geraete = len({a["geraet"] or a["endpoint"] for a in konten.push_abos(k["id"])})
    haken = lambda name, an, text: (f'<label class="haken"><input type="checkbox" name="{esc(name)}" value="ja"'   # noqa: E731
                                    f'{" checked" if an else ""}> {esc(text)}</label>')
    felder = (verdeckt(aktion="push_einstellungen")
              + f"<fieldset><legend>{esc(tx('konto.push.was'))}</legend>"
              + "".join(haken("art_" + a, a in e["arten"], tx("konto.push.art." + a)) for a in push.ARTEN)
              + "</fieldset>"
              + f"<fieldset><legend>{esc(tx('konto.push.ruhe'))}</legend>"
              + '<div style="display:flex;gap:.6rem">'
              + f'<div style="flex:1"><label for="ruhe_von">{esc(tx("konto.push.ruhe_von"))}</label>'
              + f'<input id="ruhe_von" type="time" name="ruhe_von" value="{esc(e["ruhe_von"])}"></div>'
              + f'<div style="flex:1"><label for="ruhe_bis">{esc(tx("konto.push.ruhe_bis"))}</label>'
              + f'<input id="ruhe_bis" type="time" name="ruhe_bis" value="{esc(e["ruhe_bis"])}"></div></div>'
              + f'<p class="klein">{esc(tx("konto.push.ruhe_hinweis"))}</p></fieldset>')
    geraete_text = tx("konto.push.geraete", n=geraete) if geraete else tx("konto.push.keine_geraete")
    aus = formular("/konto", verdeckt(aktion="push_aus"), tx("konto.push.alle_aus"), "neutral") if geraete else ""
    einstellungen = (f'<details{" open" if offen else ""}><summary>{esc(tx("konto.kalender.konfigurieren"))}</summary>'
                     f'<div class="inhalt" style="padding:0">' + formular("/konto", felder, tx("konto.kalender.speichern"))
                     + aus + "</div></details>")
    return (f'<div class="abschnitt" id="push"><h2>{esc(tx("konto.push.titel"))}</h2>'
            + karte(f'<p>{esc(tx("konto.push.hinweis"))}</p>', f'<p class="klein">{esc(geraete_text)}</p>',
                    f'<div class="kalender-links">{einstellungen}</div>')
            + "</div>")


def push_formular(f):
    """Formular der Karte Benachrichtigungen -> Einstellungen (push.einstellungen bereinigt)."""
    import push
    return {"arten": [a for a in push.ARTEN if f.get("art_" + a) == "ja"],
            "ruhe_von": f.get("ruhe_von", ""), "ruhe_bis": f.get("ruhe_bis", "")}


def kalender_formular(k, f):
    """Formular der Kalender-Karte -> Einstellungen (Häkchen fehlen im Formular, wenn sie aus sind)."""
    reisen = [m["reise"] for m in konten.mitgliedschaften(k["id"])]
    return {"sorten": [s_ for s_ in kalender.SORTEN if f.get("sorte_" + s_) == "ja"],
            "nur_meine_aufgaben": f.get("nur_meine_aufgaben") == "ja",
            "erinnerung_fristen": f.get("erinnerung_fristen", ""), "erinnerung_termine": f.get("erinnerung_termine", ""),
            "reisen_aus": [r for r in reisen if f.get("reise_" + r) != "ja"]}


def rolle_marke(rolle):
    """Rolle als Marke („Du organisierst“); unbekannte Rollen ohne Marke."""
    r = rolle_neu(rolle)
    if r not in ("gast", "mitwirkend", "organisator"):
        return ""
    return f'<span class="marke{"" if r == "organisator" else " leise"}">{esc(tx("konto.rolle." + r))}</span>'


def einstellung(name, titel, wert, inhalt, offen=False):
    """Zeile der Liste „Einstellungen“; Antippen klappt das Formular darunter auf."""
    return (f'<details id="{name}"{" open" if offen else ""}><summary class="zeile"><span class="was">{esc(titel)}</span>'
            f'<span class="wert">{esc(wert)}</span></summary><div class="inhalt">{inhalt}</div></details>')


def konto_seite(k, reise_info, meldung="", hinweis="", adresse_neu="", offen=""):
    """Mein Konto (Gestalt #60): Reisen zuerst, dann Kalender, Freischaltungen (Betreiber), Einstellungen als Liste,
    unten Abmelden auf allen Geräten und Konto löschen. offen: Einstellung, die aufgeklappt erscheint."""
    zeilen = []
    for m in konten.mitgliedschaften(k["id"]):
        info = reise_info(m["reise"]) or {}
        z = rm.zustand(m["reise"]) or {}
        p = next((x for x in z.get("personen") or [] if x.get("schluessel") == m["schluessel"]), {})
        inhalt = (f'<span class="was"><span class="titel">{esc(info.get("titel") or m["reise"])}</span>'
                  f"{rolle_marke(p.get('rolle'))}</span>")
        zeilen.append(f'<a class="zeile" href="{esc(info["seite"])}">{inhalt}</a>' if info.get("seite")
                      else f'<div class="zeile">{inhalt}</div>')
    reisen = f'<div class="liste">{"".join(zeilen)}</div>' if zeilen else karte(f'<p class="hinweis">{esc(tx("konto.reisen.keine"))}</p>')
    if konten.recht(k, "reise_anlegen"):
        anlegen = f'<p class="hinweis">{esc(tx("konto.reisen.anlegen_darfst"))}</p>'
    else:
        st = next((a["status"] for a in konten.anfragen(nur_offen=False) if a["konto"] == k["id"]), None)
        anlegen = {"offen": f'<p class="hinweis">{esc(tx("konto.reisen.anlegen_offen"))}</p>',
                   "abgelehnt": f'<p class="hinweis">{esc(tx("konto.reisen.anlegen_abgelehnt"))}</p>'}.get(
            st, formular("/konto", verdeckt(aktion="anfragen"), tx("konto.reisen.anlegen_knopf"), "leise"))
    betreiber = ""
    if konten.recht(k, "betreiber"):
        offen_anfragen = konten.anfragen()
        bitten = "".join(
            karte(f'<div><strong>{esc(a["name"])}</strong><p class="klein" style="margin:0">{esc(tx("konto.betreiber.anfrage", email=a["email"]))}</p></div>',
                  '<div style="display:flex;gap:.6rem">'
                  + formular("/konto", verdeckt(aktion="freischalten", wer=a["konto"]), tx("konto.betreiber.freischalten"), "leise").replace("<form ", '<form style="flex:1" ', 1)
                  + formular("/konto", verdeckt(aktion="ablehnen", wer=a["konto"]), tx("konto.betreiber.ablehnen"), "neutral").replace("<form ", '<form style="flex:1" ', 1)
                  + "</div>")
            for a in offen_anfragen)
        betreiber = (f'<div class="abschnitt"><h2>{esc(tx("konto.betreiber.titel"))}</h2>'
                     + (bitten or f'<p class="hinweis">{esc(tx("konto.betreiber.keine"))}</p>') + "</div>")
    geraete = konten.geraete(k["id"])
    geraete_liste = "".join(f'<li>{esc(g["geraet"] or tx("konto.geraete.geraet"))} <span class="klein">{esc(tx("konto.geraete.zuletzt", datum=g["zuletzt"][:10]))}</span>'
                            "</li>" for g in geraete)
    adresse_teil = (
        formular("/konto", verdeckt(aktion="adresse", email=adresse_neu)
                 + f'<label for="code">{esc(tx("konto.adresse.code_an", email=adresse_neu))}</label>'
                 '<input id="code" class="code" type="text" name="code" inputmode="numeric" '
                 'autocomplete="one-time-code" maxlength="7" required>', tx("konto.adresse.aendern"))
        if adresse_neu else
        formular("/konto", verdeckt(aktion="adresse_code")
                 + f'<label for="neu">{esc(tx("konto.adresse.neue"))}</label>'
                 '<input id="neu" type="email" name="email" autocomplete="email" required>', tx("konto.code_schicken"), "leise"))
    sprachen = "".join(f'<option value="{esc(c)}"{" selected" if c == k["sprache"] else ""}>{esc(texte.sprache(c).NAME)}</option>'
                       for c in texte.SPRACHEN)
    einstellungen = "".join((
        einstellung("name", tx("konto.seite.name"), k["name"], formular("/konto", verdeckt(aktion="name")
                    + f'<label for="name">{esc(tx("konto.seite.name_label"))}</label>'
                    f'<input id="name" type="text" name="name" value="{esc(k["name"])}" maxlength="{konten.MAX_NAME}" required>',
                    tx("konto.seite.speichern"), "leise"), offen == "name"),
        einstellung("adresse", tx("konto.email_adresse"), k["email"], adresse_teil, offen == "adresse" or bool(adresse_neu)),
        # Sprache gilt auch für die Reiseseiten und den Konnektor (#188)
        einstellung("sprache", tx("konto.sprache.titel"), texte.sprache(k["sprache"]).NAME if k["sprache"] in texte.SPRACHEN else "",
                    formular("/konto", verdeckt(aktion="sprache") + f'<label for="sprache">{esc(tx("konto.sprache.label"))}</label>'
                             f'<select id="sprache" name="sprache">{sprachen}</select>', tx("konto.seite.speichern"), "leise"),
                    offen == "sprache"),
        einstellung("geraete", tx("konto.seite.geraete"), str(len(geraete)), f'<ul class="geraete">{geraete_liste}</ul>', offen == "geraete")))
    kopf = (f'<header class="kopf breit"><span><img src="/favicon.svg" alt="">Frieda</span>'
            f'<form method="post" action="/abmelden"><button class="link">{esc(tx("konto.seite.abmelden"))}</button></form></header>')
    return seite(tx("konto.seite.titel"),
                 f'<div><h1 style="font-size:1.875rem">{esc(tx("konto.seite.hallo", name=k["name"]))}</h1>'
                 f'<p class="hinweis" style="margin:.1rem 0 0">{esc(k["email"])}</p></div>',
                 fehler(meldung), f'<p class="kasten">{esc(hinweis)}</p>' if hinweis else "",
                 f'<div class="abschnitt"><h2>{esc(tx("konto.seite.meine_reisen"))}</h2>{reisen}{anlegen}</div>',
                 kalender_karte(k, reise_info, offen == "kalender"),
                 push_karte(k, offen == "push"),
                 betreiber,
                 f'<div class="abschnitt"><h2>{esc(tx("konto.seite.einstellungen"))}</h2><div class="liste">{einstellungen}</div></div>',
                 '<div class="links" style="flex-direction:column;align-items:center">'
                 f'<form method="post" action="/konto">{verdeckt(aktion="alle_abmelden")}<button class="link">{esc(tx("konto.seite.ueberall_abmelden"))}</button></form>'
                 f'<a href="/konto?loeschen=1" style="color:var(--gefahr)">{esc(tx("konto.seite.loeschen_titel"))}</a></div>',
                 kopf=kopf)


def loeschen_seite(k):
    """Rückfrage vor dem Löschen: was gelöscht wird, was bleibt (#60)."""
    return seite(tx("konto.seite.loeschen_frage"),
                 f'<a class="zurueck" href="/konto">‹ {esc(tx("konto.seite.titel"))}</a>',
                 karte(f"<h1>{esc(tx('konto.seite.loeschen_frage'))}</h1>",
                       f'<div><strong>{esc(tx("konto.seite.loeschen_weg"))}</strong><p style="margin:.2rem 0 0">{esc(tx("konto.seite.loeschen_weg_text"))}</p></div>',
                       f'<div><strong>{esc(tx("konto.seite.loeschen_bleibt"))}</strong><p style="margin:.2rem 0 0">{esc(tx("konto.seite.loeschen_bleibt_text"))}</p></div>',
                       formular("/konto", verdeckt(aktion="loeschen")
                                + f'<label class="haken bestaetigen"><input type="checkbox" name="sicher" value="ja" required> '
                                  f'{esc(tx("konto.seite.loeschen_haken"))}</label>', tx("konto.seite.loeschen_knopf"), "gefahr"),
                       f'<div class="links"><a href="/konto">{esc(tx("konto.seite.abbrechen"))}</a></div>'),
                 kopf="")


def einladungs_seite(e, token, k, reise_info, meldung=""):
    info = reise_info(e["reise"]) or {}
    titel = info.get("titel") or e["reise"]
    kopf = (f"<div><h1>{esc(tx('konto.einladung.titel'))}</h1><p class=\"lead\">"
            f"{th('konto.einladung.text', von=esc(e['von']), name=esc(e['name']), titel='<strong>' + esc(titel) + '</strong>')}</p></div>"
            + rolle_marke(e["rolle"]))
    if e["eingeloest"]:
        return seite(tx("konto.einladung.titel"), karte(kopf, f'<p class="hinweis">{esc(tx("konto.einladung.angenommen"))}</p>',
                                                       f'<a class="knopf" href="/konto">{esc(tx("konto.einladung.zum_konto"))}</a>'))
    if k:
        return seite(tx("konto.einladung.titel"), karte(
            kopf, fehler(meldung),
            formular(f"/einladung/{token}", "", tx("konto.einladung.annehmen", name=k["name"], email=k["email"]))),
            '<div class="fuss"><p>' + th("konto.einladung.anderes_konto", link='<a href="/konto">' + esc(tx("konto.einladung.abmelden_link")) + "</a>") + "</p></div>")
    q = urllib.parse.urlencode({"einladung": token, "email": e["email"]})
    return seite(tx("konto.einladung.titel"), karte(
        kopf, f"<p>{esc(tx('konto.einladung.anmelden_hinweis'))}</p>",
        f'<a class="knopf" href="/anmelden?{q}">{esc(tx("konto.anmelden.titel"))}</a>'),
        fuss(tx("konto.datenschutz")))


# ---------------------------------------------------------------- Ablauf

def sitzung_aus(headers):
    t = rm.sitzungs_token(headers.get("Cookie"))
    return t, (konten.sitzung(t) if t else None)


def herkunft_ok(headers):
    return bool(konten.basis()) and headers.get("Origin") == konten.basis()


def geraet(headers):
    ua = headers.get("User-Agent", "")
    for muster, name in (("iPad", "iPad"), ("iPhone", "iPhone"), ("Android", "Android"), ("Macintosh", "Mac"),
                         ("Windows", "Windows"), ("Linux", "Linux")):
        if muster in ua:
            return name
    return ""   # die Seite zeigt dafür das Wort der Sprache (konto.geraete.geraet)


def ist_unsere(pfad):
    p = pfad.split("?", 1)[0]
    return p in ("/anmelden", "/konto", "/abmelden") or p.startswith(("/einladung/", "/kalender/"))


def bearbeiten(methode, pfad, headers, body, ip, reise_info):
    """-> (code, kopfzeilen, body) für Friedas Anmeldeseiten. reise_info(reise) -> {titel, seite} oder None."""
    teile = urllib.parse.urlsplit(pfad)
    weg, q = teile.path, {k: v[0] for k, v in urllib.parse.parse_qs(teile.query).items()}
    f = {}
    if methode == "POST":
        if not herkunft_ok(headers):
            _anfrage.sprache = texte.aus_header(headers.get("Accept-Language"))
            return antwort(403, seite(tx("konto.nicht_erlaubt"), karte(
                f"<h1>{esc(tx('konto.nicht_erlaubt'))}</h1><p>{esc(tx('konto.fehler.nicht_erlaubt'))}</p>")))
        f = {k: v[0] for k, v in urllib.parse.parse_qs(body.decode("utf-8", "replace")).items()}
    token, k = sitzung_aus(headers)
    # Sprache dieser Anfrage: die des Kontos, vor dem Anmelden die des Browsers (Accept-Language), sonst die Vorgabe der Personen
    _anfrage.sprache = k["sprache"] if k else texte.aus_header(headers.get("Accept-Language"))

    if weg == "/anmelden":
        zurueck, einl = rueckweg(f.get("zurueck") or q.get("zurueck")), f.get("einladung") or q.get("einladung", "")
        if methode == "GET":
            if q.get("schritt") == "code" and q.get("email"):    # Link aus der Mail: nur die Code-Seite
                return antwort(200, code_seite(q["email"], zurueck, einl))
            if k and not einl:
                return weiter(zurueck)
            return antwort(200, adress_seite(zurueck, einl, q.get("email", "")))
        if f.get("schritt") == "adresse":
            try:
                konten.code_anfordern(f.get("email"), ip=ip, sprache=sprache_der_seite())
            except konten.KontoFehler as x:
                return antwort(200, adress_seite(zurueck, einl, f.get("email", ""), x.text(sprache_der_seite())))
            return antwort(200, code_seite(konten.adresse(f["email"]), zurueck, einl))
        try:
            neu, konto = konten.anmelden(f.get("email"), f.get("code"), name=f.get("name"), geraet=geraet(headers),
                                         einladung=einl or None, sprache=sprache_der_seite())
        except konten.NameNoetig as x:
            return antwort(200, code_seite(f.get("email", ""), zurueck, einl, code=f.get("code", ""), meldung=x.text(sprache_der_seite()),
                                           name_noetig=True))
        except konten.KontoFehler as x:
            if k and not k["gesperrt"] and k["email"] == (f.get("email") or "").strip().lower():
                return weiter(zurueck)     # doppelt abgesendet: schon angemeldet, nicht „Code stimmt nicht“ zeigen
            return antwort(200, code_seite(f.get("email", ""), zurueck, einl, meldung=x.text(sprache_der_seite()),
                                           name_noetig=bool(f.get("name"))))
        if token:
            konten.abmelden(token)
        ziel = zurueck
        if einl and zurueck == "/konto":
            e = konten.einladung(einl)
            ziel = ((reise_info(e["reise"]) or {}).get("seite") if e else None) or "/konto"
        return weiter(ziel, [cookie_setzen(neu)])

    if weg == "/abmelden":
        if methode == "POST" and token:
            konten.abmelden(token)
        return weiter("/anmelden", [cookie_loeschen()])

    if weg.startswith("/einladung/"):
        et = weg.rsplit("/", 1)[1]
        e = konten.einladung(et)
        if not e:
            return antwort(404, seite(tx("konto.einladung.titel"), karte(
                f"<h1>{esc(tx('konto.einladung.abgelaufen'))}</h1><p>{esc(tx('konto.einladung.abgelaufen_text'))}</p>")))
        if methode == "GET":
            return antwort(200, einladungs_seite(e, et, k, reise_info))
        if not k:
            return weiter("/anmelden?" + urllib.parse.urlencode({"einladung": et, "email": e["email"]}))
        try:
            reise = konten.einladung_einloesen(et, k["id"])
        except konten.KontoFehler as x:
            return antwort(200, einladungs_seite(e, et, k, reise_info, x.text(sprache_der_seite())))
        return weiter((reise_info(reise) or {}).get("seite") or "/konto")

    if weg.startswith("/kalender/") and methode == "GET":
        # Kalender-Abo (#77): Kalender-Apps melden sich nicht an, das geheime Wort im Pfad steht für das Konto
        wer = konten.kalender_konto(weg.rsplit("/", 1)[1].removesuffix(".ics"))
        if not wer:
            return antwort(404, seite(tx("konto.kalender.titel"), karte(
                f"<h1>{esc(tx('konto.kalender.nicht_gefunden'))}</h1><p>{esc(tx('konto.kalender.nicht_gefunden_text'))}</p>")))
        _anfrage.sprache = wer["sprache"] or _anfrage.sprache      # die App schickt keine Sprache mit, das Konto hat eine
        return kalender_antwort(wer, headers=headers)

    if weg == "/konto":
        if not k:
            return weiter("/anmelden?zurueck=/konto")
        if methode == "GET" and q.get("kalender") == "datei":
            return kalender_antwort(k, datei=True)
        if methode == "GET" and q.get("loeschen"):
            return antwort(200, loeschen_seite(k))
        if methode == "GET":
            return antwort(200, konto_seite(k, reise_info))
        a = f.get("aktion")
        try:
            if a == "name":
                konten.name_setzen(k["id"], f.get("name"))
                return weiter("/konto")
            if a == "sprache":
                neu_sprache = konten.sprache_setzen(k["id"], f.get("sprache"))
                _anfrage.sprache = neu_sprache   # die Seite erscheint gleich in der neuen Sprache
                return antwort(200, konto_seite({**k, "sprache": neu_sprache}, reise_info, hinweis=tx("konto.sprache.gespeichert"), offen="sprache"))
            if a == "adresse_code":
                konten.code_anfordern(f.get("email"), ip=ip, zweck="adresse", konto=k["id"], sprache=k["sprache"])
                return antwort(200, konto_seite(k, reise_info, adresse_neu=konten.adresse(f["email"]),
                                                hinweis=tx("konto.adresse.code_gesendet")))
            if a == "adresse":
                konten.adresse_aendern(k["id"], f.get("email"), f.get("code"))
                return weiter("/konto")
            if a == "anfragen":
                if konten.reisen_anlegen_anfragen(k["id"]) == "offen":
                    betreiber_melden(k)
                return weiter("/konto")
            if a in ("freischalten", "ablehnen") and konten.recht(k, "betreiber"):
                konten.freischalten(f.get("wer"), ja=a == "freischalten")
                return weiter("/konto")
            if a == "kalender_neu":
                konten.kalender_token(k["id"], erneuern=True)
                return antwort(200, konto_seite(k, reise_info, hinweis=tx("konto.kalender.neuer_link_hinweis"), offen="kalender"))
            if a == "kalender_einstellungen":
                konten.kalender_einstellungen(k["id"], kalender_formular(k, f))
                return antwort(200, konto_seite(k, reise_info, hinweis=tx("konto.kalender.gespeichert_hinweis"), offen="kalender"))
            if a == "push_einstellungen":
                import push
                push.einstellungen_von(k["id"], push_formular(f))
                return antwort(200, konto_seite(k, reise_info, hinweis=tx("konto.push.gespeichert"), offen="push"))
            if a == "push_aus":
                for abo in konten.push_abos(k["id"]):
                    konten.push_abo_entfernen(k["id"], abo["endpoint"])
                return antwort(200, konto_seite(k, reise_info, hinweis=tx("konto.push.alle_aus_hinweis"), offen="push"))
            if a == "alle_abmelden":
                konten.alle_abmelden(k["id"])
                return weiter("/anmelden", [cookie_loeschen()])
            if a == "loeschen" and f.get("sicher") == "ja":
                konten.loeschen(k["id"])
                return antwort(200, seite(tx("konto.seite.geloescht"), karte(
                    f"<h1>{esc(tx('konto.seite.geloescht'))}</h1><p>{esc(tx('konto.seite.geloescht_text'))}</p>")), [cookie_loeschen()])
        except konten.KontoFehler as x:
            return antwort(200, konto_seite(k, reise_info, meldung=x.text(sprache_der_seite())))
        return antwort(400, konto_seite(k, reise_info, meldung=tx("konto.fehler.ging_nicht")))

    return antwort(404, seite(tx("konto.nicht_gefunden"), karte(f"<h1>{esc(tx('konto.nicht_gefunden'))}</h1>")))


def betreiber_melden(k):
    """Bitte „Reisen anlegen“: Meldung an alle Betreiber (stehen in der Claude-App bei meine_reisen)."""
    with konten.closing(konten.db()) as v:
        namen = [z["name"] for z in v.execute("SELECT name, rechte FROM konten WHERE gesperrt = 0")
                 if "betreiber" in z["rechte"].split(",")]
    if namen:
        rm.meldung_anlegen(rm.ordner_neu(anlegen=True), namen, "anfrage_reisen", "reise",
                           texte.t(texte.VORGABE_REISE, "konto.betreiber.meldung", name=k["name"], email=k["email"]))
