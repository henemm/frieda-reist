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

CSS = """
:root{--bg:#f8f8f5;--fg:#1d2420;--mut:#5b645e;--card:#ffffff;--line:#e4e5df;--acc:#1f7a57;--acc2:#e3f1ea;
--warn:#9a5b00;--warnbg:#fbeed6}
@media (prefers-color-scheme:dark){:root{--bg:#151816;--fg:#eceee9;--mut:#a5aca6;--card:#1d211e;--line:#2c312d;
--acc:#6fd0a5;--acc2:#1f3329;--warn:#f0c46a;--warnbg:#3a3017}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:1.0625rem/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",
Roboto,sans-serif}
header{background:var(--card);color:var(--fg);border-bottom:1px solid var(--line);padding:.75rem 1rem;font:700 1.25rem -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:30rem;margin:1.5rem auto;padding:0 1rem}
.karte{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:1.25rem;margin-bottom:1rem}
h1{font-size:1.4rem;margin:0 0 .75rem}h2{font-size:1.1rem;margin:0 0 .5rem}
label{display:block;margin:.75rem 0 .25rem;font-weight:600}
input[type=email],input[type=text]{width:100%;min-height:2.75rem;padding:.5rem .75rem;font:inherit;color:var(--fg);
background:var(--bg);border:1px solid var(--line);border-radius:.375rem}
input.code{font-size:1.5rem;letter-spacing:.3em;text-align:center}
button{min-height:2.75rem;margin-top:1rem;padding:.5rem 1.25rem;font:600 1rem inherit;border:0;border-radius:.375rem;
background:var(--acc);color:var(--card);cursor:pointer}
button.leise{background:var(--acc2);color:var(--fg)}button.gefahr{background:var(--warnbg);color:var(--warn)}
.fehler{background:var(--warnbg);color:var(--warn);padding:.6rem .8rem;border-radius:.375rem;margin:.5rem 0}
.hinweis,.klein{color:var(--mut)}.klein{font-size:.875rem}
fieldset{border:0;padding:0;margin:.75rem 0 0}legend{font-weight:600;padding:0}label.haken{font-weight:400;margin:.35rem 0}
select{min-height:2.75rem;font:inherit;width:100%}ul{padding-left:1.2rem}a{color:var(--acc)}form.zeile{display:inline}
"""


def esc(t):
    return html.escape(str(t or ""), quote=True)


def seite(titel, *teile):
    rumpf = "".join(teile)
    sp = sprache_der_seite()
    return (f'<!DOCTYPE html><html lang="{esc(sp)}" dir="{esc(texte.sprache(sp).RICHTUNG)}"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">'
            f'<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="icon" href="/favicon.ico" sizes="48x48">'
            f'<link rel="apple-touch-icon" href="/apple-touch-icon.png">'
            f'<title>{esc(titel)} – Frieda</title><style>{CSS}</style></head><body><header>Frieda</header>'
            f'<main>{rumpf}</main></body></html>')


def karte(*teile):
    return '<section class="karte">' + "".join(teile) + "</section>"


def fehler(t):
    return f'<p class="fehler" role="alert">{esc(t)}</p>' if t else ""


def verdeckt(**felder):
    return "".join(f'<input type="hidden" name="{esc(k)}" value="{esc(v)}">' for k, v in felder.items() if v)


def formular(ziel, inhalt, knopf, klasse=""):
    k = f' class="{klasse}"' if klasse else ""
    return f'<form method="post" action="{esc(ziel)}">{inhalt}<button{k}>{esc(knopf)}</button></form>'


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
        f"<h1>{esc(tx('konto.anmelden.ueberschrift'))}</h1>",
        f"<p>{esc(tx('konto.anmelden.hinweis'))}</p>",
        fehler(meldung),
        formular("/anmelden", verdeckt(schritt="adresse", zurueck=zurueck, einladung=einladung)
                 + f'<label for="email">{esc(tx("konto.email_adresse"))}</label>'
                 f'<input id="email" type="email" name="email" value="{esc(email)}" autocomplete="email" required '
                 'autofocus>', tx("konto.code_schicken")),
        f'<p class="klein">{esc(tx("konto.datenschutz"))}</p>'))


def code_seite(email, zurueck="", einladung="", code="", meldung="", name_noetig=False, name=""):
    name_feld = (f'<label for="name">{esc(tx("konto.name_frage"))}</label>'
                 f'<input id="name" type="text" name="name" value="{esc(name)}" maxlength="{konten.MAX_NAME}" '
                 'autocomplete="name" required>'
                 f'<p class="klein">{esc(tx("konto.name_hinweis"))}</p>'
                 if name_noetig else "")
    return seite(tx("konto.code.titel"), karte(
        f"<h1>{esc(tx('konto.code.titel'))}</h1>",
        f"<p>{th('konto.code.gesendet', email=fett(email), minuten=str(konten.CODE_MINUTEN))}</p>"
        if not code else f"<p>{th('konto.code.anmelden_als', email=fett(email))}</p>",
        fehler(meldung),
        formular("/anmelden", verdeckt(schritt="code", email=email, zurueck=zurueck, einladung=einladung)
                 + f'<label for="code">{esc(tx("konto.code.label"))}</label>'
                 f'<input id="code" class="code" type="text" name="code" value="{esc(code)}" inputmode="numeric" '
                 'autocomplete="one-time-code" pattern="[0-9 ]{6,7}" maxlength="7" required'
                 f'{"" if code or name_noetig else " autofocus"}>' + name_feld, tx("konto.anmelden.titel")),
        f'<p class="klein"><a href="/anmelden?{urllib.parse.urlencode({"zurueck": zurueck, "einladung": einladung})}">'
        f'{esc(tx("konto.code.andere_adresse"))}</a></p>'))


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


def kalender_antwort(k, datei=False):
    """Persönlicher Kalender des Kontos mit seinen Einstellungen: als Abo (Kalender-App) oder als Datei (Download)."""
    text = kalender.ics_person(kalender_reisen(k), konten.kalender_einstellungen(k["id"]), sprache=sprache_der_seite())
    kopf = [("Content-Type", "text/calendar; charset=utf-8"), ("Cache-Control", "private, no-store")]
    if datei:
        kopf.append(("Content-Disposition", 'attachment; filename="frieda-reisen.ics"'))
    return 200, kopf, text.encode("utf-8")


def kalender_karte(k, reise_info):
    """Karte „Kalender“ auf Mein Konto: Abo-Link, Download und Einstellungen für alle Reisen (Product Owner 30.10.2026)."""
    e = konten.kalender_einstellungen(k["id"])
    basis = os.environ.get("KN_BASIS")
    if basis:
        url = kalender.abo_url(basis, konten.kalender_token(k["id"]))
        link = f'<a href="{esc(kalender.webcal(url))}">{esc(tx("konto.kalender.abonnieren_link"))}</a>'
        abo = (f'<p>{th("konto.kalender.abonnieren", link=link)}</p>'
               f'<label for="kal-url">{esc(tx("konto.kalender.url_label"))}</label>'
               f'<input id="kal-url" type="text" readonly value="{esc(url)}">')
    else:
        abo = f'<p class="hinweis">{esc(tx("konto.kalender.abo_fehlt"))}</p>'
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
    datei = '<a href="/konto?kalender=datei">' + esc(tx("konto.kalender.datei_link")) + "</a>"
    return karte(f"<h2>{esc(tx('konto.kalender.titel'))}</h2>",
                 f'<p class="klein">{esc(tx("konto.kalender.hinweis"))}</p>',
                 abo, f"<p>{th('konto.kalender.datei', link=datei)}</p>",
                 formular("/konto", felder, tx("konto.kalender.einstellungen")),
                 formular("/konto", verdeckt(aktion="kalender_neu"), tx("konto.kalender.neuer_link"), "leise"))


def kalender_formular(k, f):
    """Formular der Kalender-Karte -> Einstellungen (Häkchen fehlen im Formular, wenn sie aus sind)."""
    reisen = [m["reise"] for m in konten.mitgliedschaften(k["id"])]
    return {"sorten": [s_ for s_ in kalender.SORTEN if f.get("sorte_" + s_) == "ja"],
            "nur_meine_aufgaben": f.get("nur_meine_aufgaben") == "ja",
            "erinnerung_fristen": f.get("erinnerung_fristen", ""), "erinnerung_termine": f.get("erinnerung_termine", ""),
            "reisen_aus": [r for r in reisen if f.get("reise_" + r) != "ja"]}


def konto_seite(k, reise_info, meldung="", hinweis="", adresse_neu=""):
    reisen = []
    for m in konten.mitgliedschaften(k["id"]):
        info = reise_info(m["reise"]) or {}
        z = rm.zustand(m["reise"]) or {}
        p = next((x for x in z.get("personen") or [] if x.get("schluessel") == m["schluessel"]), {})
        link = f' – <a href="{esc(info["seite"])}">{esc(tx("konto.reise.oeffnen"))}</a>' if info.get("seite") else ""
        rolle = rolle_neu(p.get("rolle"))
        reisen.append(f'<li>{esc(info.get("titel") or m["reise"])} ({esc(tx("konto.rolle." + rolle) if rolle in ("gast", "mitwirkend", "organisator") else tx("konto.rolle.dabei"))})'
                      f"{link}</li>")
    reisen_html = f"<ul>{''.join(reisen)}</ul>" if reisen else (
        f'<p class="hinweis">{esc(tx("konto.reisen.keine"))}</p>')
    if konten.recht(k, "reise_anlegen"):
        anlegen = f"<p>{esc(tx('konto.reisen.anlegen_darfst'))}</p>"
    else:
        st = next((a["status"] for a in konten.anfragen(nur_offen=False) if a["konto"] == k["id"]), None)
        anlegen = {"offen": f'<p class="hinweis">{esc(tx("konto.reisen.anlegen_offen"))}</p>',
                   "abgelehnt": f'<p class="hinweis">{esc(tx("konto.reisen.anlegen_abgelehnt"))}</p>'}.get(
            st, formular("/konto", verdeckt(aktion="anfragen"), tx("konto.reisen.anlegen_knopf"), "leise"))
    betreiber = ""
    if konten.recht(k, "betreiber"):
        offen = konten.anfragen()
        zeilen = "".join(
            f'<li>{esc(a["name"])} ({esc(a["email"])}) '
            + formular("/konto", verdeckt(aktion="freischalten", wer=a["konto"]), tx("konto.betreiber.freischalten"), "leise")
            + formular("/konto", verdeckt(aktion="ablehnen", wer=a["konto"]), tx("konto.betreiber.ablehnen"), "gefahr") + "</li>"
            for a in offen)
        betreiber = karte(f"<h2>{esc(tx('konto.betreiber.titel'))}</h2>",
                          f"<ul>{zeilen}</ul>" if zeilen else f'<p class="hinweis">{esc(tx("konto.betreiber.keine"))}</p>')
    geraete = "".join(f'<li>{esc(g["geraet"] or tx("konto.geraete.geraet"))} <span class="klein">{esc(tx("konto.geraete.zuletzt", datum=g["zuletzt"][:10]))}</span>'
                      f"</li>" for g in konten.geraete(k["id"]))
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
    return seite(tx("konto.seite.titel"),
                 karte(f"<h1>{esc(tx('konto.seite.hallo', name=k['name']))}</h1>", fehler(meldung),
                       f'<p class="hinweis">{esc(hinweis)}</p>' if hinweis else "",
                       f"<p>{th('konto.seite.angemeldet_als', email=fett(k['email']))}</p>",
                       formular("/abmelden", "", tx("konto.seite.abmelden"), "leise")),
                 karte(f"<h2>{esc(tx('konto.seite.meine_reisen'))}</h2>", reisen_html, anlegen),
                 kalender_karte(k, reise_info),
                 # Sprache neben dem Kalender: sie gilt auch für die Reiseseiten (#188)
                 karte(f"<h2>{esc(tx('konto.sprache.titel'))}</h2>",
                       formular("/konto", verdeckt(aktion="sprache")
                                + f'<label for="sprache">{esc(tx("konto.sprache.label"))}</label>'
                                f'<select id="sprache" name="sprache">{sprachen}</select>', tx("konto.seite.speichern"), "leise")),
                 betreiber,
                 karte(f"<h2>{esc(tx('konto.seite.name'))}</h2>", formular("/konto", verdeckt(aktion="name")
                                                + f'<label for="name">{esc(tx("konto.seite.name_label"))}</label>'
                                                f'<input id="name" type="text" name="name" value="{esc(k["name"])}" '
                                                f'maxlength="{konten.MAX_NAME}" required>', tx("konto.seite.speichern"), "leise")),
                 karte(f"<h2>{esc(tx('konto.email_adresse'))}</h2>", adresse_teil),
                 karte(f"<h2>{esc(tx('konto.seite.geraete'))}</h2>", f"<ul>{geraete}</ul>",
                       formular("/konto", verdeckt(aktion="alle_abmelden"), tx("konto.seite.ueberall_abmelden"), "leise")),
                 karte(f"<h2>{esc(tx('konto.seite.loeschen_titel'))}</h2>",
                       f'<p class="klein">{esc(tx("konto.seite.loeschen_hinweis"))}</p>',
                       formular("/konto", verdeckt(aktion="loeschen")
                                + f'<label><input type="checkbox" name="sicher" value="ja" required> '
                                  f'{esc(tx("konto.seite.loeschen_haken"))}</label>', tx("konto.seite.loeschen_titel"), "gefahr")))


def einladungs_seite(e, token, k, reise_info, meldung=""):
    info = reise_info(e["reise"]) or {}
    titel = info.get("titel") or e["reise"]
    rolle = rolle_neu(e["rolle"])
    rolle_text = tx("konto.rolle." + rolle) if rolle in ("gast", "mitwirkend", "organisator") else e["rolle"]
    kopf = (f"<h1>{esc(tx('konto.einladung.titel'))}</h1><p>"
            f"{th('konto.einladung.text', von=esc(e['von']), name=esc(e['name']), titel='<strong>' + esc(titel) + '</strong>', rolle=esc(rolle_text))}</p>")
    if e["eingeloest"]:
        return seite(tx("konto.einladung.titel"), karte(kopf, f'<p class="hinweis">{esc(tx("konto.einladung.angenommen"))}</p>',
                                                       f'<p><a href="/konto">{esc(tx("konto.einladung.zum_konto"))}</a></p>'))
    if k:
        return seite(tx("konto.einladung.titel"), karte(
            kopf, fehler(meldung),
            formular(f"/einladung/{token}", "", tx("konto.einladung.annehmen", name=k["name"], email=k["email"])),
            '<p class="klein">' + th("konto.einladung.anderes_konto", link='<a href="/konto">' + esc(tx("konto.einladung.abmelden_link")) + "</a>") + "</p>"))
    q = urllib.parse.urlencode({"einladung": token, "email": e["email"]})
    return seite(tx("konto.einladung.titel"), karte(
        kopf, f"<p>{esc(tx('konto.einladung.anmelden_hinweis'))}</p>",
        f'<p><a href="/anmelden?{q}"><button type="button">{esc(tx("konto.anmelden.titel"))}</button></a></p>',
        f'<p class="klein">{esc(tx("konto.datenschutz"))}</p>'))


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
        return kalender_antwort(wer)

    if weg == "/konto":
        if not k:
            return weiter("/anmelden?zurueck=/konto")
        if methode == "GET" and q.get("kalender") == "datei":
            return kalender_antwort(k, datei=True)
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
                return antwort(200, konto_seite({**k, "sprache": neu_sprache}, reise_info, hinweis=tx("konto.sprache.gespeichert")))
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
                return antwort(200, konto_seite(k, reise_info, hinweis=tx("konto.kalender.neuer_link_hinweis")))
            if a == "kalender_einstellungen":
                konten.kalender_einstellungen(k["id"], kalender_formular(k, f))
                return antwort(200, konto_seite(k, reise_info, hinweis=tx("konto.kalender.gespeichert_hinweis")))
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
