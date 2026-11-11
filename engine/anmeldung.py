"""Anmeldeseiten für Konten (Paket J2, Issues #43 und #46). Der Konnektor-Dienst liefert sie unter Friedas eigener
Adresse aus (FR_BASIS): /anmelden, /einladung/<token>, /konto, /abmelden, dazu die Warteliste (/warteliste,
/warteliste/bestaetigen/<wort>, #382), die drei Seiten /datenschutz, /impressum, /alpha (#383, nur GET, ohne Anmeldung)
und die Infoseite „Was ist Frieda?“ als Startseite / für alle ohne Anmeldung (#436; Bilder unter /info/, engine/info/).

Ablauf: E-Mail-Adresse eingeben -> Code per Mail -> Code eingeben (beim ersten Mal auch den Namen) -> angemeldet.
Der Code ist der Hauptweg; der Link aus der Mail enthält keinen Code und öffnet nur die Code-Seite (Mailprogramme rufen
Links vorab auf, und Codes gehören nicht in Protokolle). Die Sitzung steht im Cookie __Host-frieda (HttpOnly, Secure,
SameSite=Lax, ein Jahr, rollierend). Jede Änderung (POST) muss von Friedas eigener Adresse kommen (Origin), sonst
403 (CSRF; SameSite trennt nicht von Nachbar-Subdomains). Rückkehradressen sind nur Pfade auf Friedas Adresse.

Reiseseiten bleiben zum Lesen über ihren geheimen Link offen; mitmachen geht nach dem Anmelden (Rückmeldedienst).
"""
import datetime
import html
import json
import os
import re
import sys
import threading
import urllib.parse
from pathlib import Path
from zoneinfo import ZoneInfo

import instanz
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
button:disabled{background:var(--neutral);color:var(--mut);cursor:default}
ol.schritte{margin:0;padding-left:1.3rem;display:flex;flex-direction:column;gap:.35rem}
#push-geraet{display:flex;flex-direction:column;gap:.5rem}#push-geraet>*{margin:0}#push-geraet .aktiv{font-weight:600;color:var(--acc)}
[hidden]{display:none!important}
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
.zeile.ohne-link{cursor:default}.zeile.ohne-link::after{content:none}
.zeile .meldungstext{overflow-wrap:anywhere}
.marke.warm{color:var(--warn);background:var(--warnbg)}
.zeile.meldung{align-items:flex-start}.zeile.meldung::after{align-self:center}
.meldung-kopf{display:flex;align-items:center;gap:.4rem;min-width:0;font-size:.8125rem;color:var(--mut)}
.meldung-kopf .marke{font-size:.75rem;padding:.05rem .5rem;flex:none}
.meldung-kopf .reise{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}.meldung-kopf .zeit{flex:none}
.zeile.meldung .meldungstext{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
details.weitere>summary,details.gelesen>summary{color:var(--mut);font-weight:600}
details.weitere>.liste-innen>*,details.gelesen>.liste-innen>*{border-top:1px solid var(--line)}
.abschnitt-kopf{display:flex;align-items:baseline;justify-content:space-between;gap:.5rem;margin:0 .25rem}.abschnitt-kopf h2{margin:0}
.abschnitt-kopf form{flex:none}.abschnitt-kopf button.link{min-height:2.75rem;padding:.2rem 0;font-size:.9375rem}
.zahl{font-size:.8125rem;font-weight:700;color:var(--card);background:var(--acc);border-radius:999px;padding:.05rem .55rem;margin-left:.4rem;vertical-align:.15em}
.neu-punkt{flex:none;width:.5rem;height:.5rem;border-radius:50%;background:var(--acc);margin-top:.55rem}.ohne-punkt{flex:none;width:.5rem}
.zeile.meldung.ungelesen .meldungstext{font-weight:600}.leer{padding:.9rem 1rem;color:var(--mut);font-size:.9375rem}
.zeile .wert{color:var(--mut);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:55%}
details>.inhalt{padding:0 1rem 1rem;display:flex;flex-direction:column;gap:.5rem}
.archiv>summary{padding:.7rem .25rem;color:var(--mut);font-size:.9375rem;cursor:pointer}.archiv{margin-top:.5rem}
.personen summary{padding:.2rem 1rem .7rem;color:var(--mut);font-size:.875rem;cursor:pointer}
.personen ul{margin:0;padding:0 1rem 1rem 2.2rem;display:flex;flex-direction:column;gap:.3rem;font-size:.9375rem}
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
.fuss p.recht{display:flex;flex-wrap:wrap;gap:0 1rem}.fuss p.recht a{padding:.35rem 0}
ul.punkte{margin:0;padding-left:1.2rem;display:flex;flex-direction:column;gap:.4rem}
main.breit{max-width:46rem}main.breit>.karte,main.breit>.abschnitt,main.breit>.fuss{width:100%}
.knoepfe{display:flex;flex-wrap:wrap;gap:.6rem}.knoepfe>a.knopf{flex:1 1 12rem;margin:0}a.knopf.leise{background:var(--acc2);color:var(--acc)}
a.kopf-link{font-size:1rem;font-weight:600;text-decoration:none;padding:.5rem .25rem}
.prinzipien{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:1rem}
.prinzipien .karte{padding:1.2rem 1.2rem 1.1rem;gap:.4rem}.prinzipien h3{font-size:1.0625rem;margin:0}.prinzipien p{margin:0;font-size:.9375rem}
.gespraech{display:flex;flex-direction:column;gap:.55rem}.gespraech h3{font-size:1.0625rem;margin:0 0 .2rem}
.blase{max-width:88%;padding:.55rem .85rem .6rem;border-radius:16px;font-size:.9375rem;margin:0}
.blase .wer{display:block;font-size:.75rem;font-weight:700;color:var(--mut)}
.blase.person{align-self:flex-end;background:var(--acc2);border-end-end-radius:4px}
.blase.claude{align-self:flex-start;background:var(--bg);border-end-start-radius:4px}
.bilder{display:grid;grid-template-columns:repeat(auto-fit,minmax(9.5rem,1fr));gap:1rem}
figure{margin:0;display:flex;flex-direction:column;gap:.5rem}
figure a{display:block}figure img{display:block;width:100%;height:auto;aspect-ratio:585/1050;border-radius:14px;border:1px solid var(--line);box-shadow:var(--schatten);background:var(--card)}
figcaption{font-size:.875rem;color:var(--mut)}
ol.erste{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:1rem;counter-reset:schritt}
ol.erste>li{display:flex;gap:.8rem;counter-increment:schritt}
ol.erste>li::before{content:counter(schritt);flex:none;width:1.8rem;height:1.8rem;border-radius:50%;background:var(--acc);color:var(--card);
font-weight:700;display:flex;align-items:center;justify-content:center}
ol.erste>li>div{flex:1;min-width:0;display:flex;flex-direction:column;gap:.35rem}ol.erste p,ol.erste h3{margin:0}ol.erste p{font-size:.9375rem}ol.erste h3{font-size:1.0625rem}
ol.erste ol{margin:0;padding-inline-start:1.2rem;display:flex;flex-direction:column;gap:.3rem;font-size:.9375rem}
.sprachen{display:flex;flex-wrap:wrap;gap:0 1rem}.sprachen a{padding:.35rem 0}.sprachen a[aria-current]{color:var(--fg);font-weight:600;text-decoration:none}
.kopf-rechts{display:flex;flex-wrap:wrap;align-items:center;justify-content:flex-end;gap:0 1.1rem}
.einstieg{border-inline-start:4px solid var(--acc)}.einstieg h2{margin:0}.einstieg a.knopf{margin:0}
.spalten,.spalte{display:flex;flex-direction:column;gap:1.5rem}
@media (min-width:760px){main.konto{max-width:72rem;padding:1.75rem 2rem 3rem}
.spalten{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(0,1fr);gap:2rem;align-items:start}
.einstieg{flex-direction:row;align-items:center;justify-content:space-between;gap:1.5rem}.einstieg a.knopf{flex:none}}
"""


def esc(t):
    return html.escape(str(t or ""), quote=True)


def seite(titel, *teile, kopf=None, skript=False, breit=False, klasse=""):
    """Ganze Seite. kopf: eigener Kopf (Mein Konto); sonst Friedas Zeichen mittig über der Karte. Jede Seite trägt das
    Manifest der Frieda-App (Issue #21: ein Symbol auf dem Home-Bildschirm, Start „Mein Konto“, Scope „/“); skript lädt
    engine/app/konto.js (nur Mein Konto: Benachrichtigungen je Gerät, Speichern mit Zustand); breit: Lesespalte der Infoseite (#436);
    klasse: Klasse von main (konto: zwei Spalten ab Tablet, #441)."""
    rumpf = "".join(teile)
    sp = sprache_der_seite()
    klasse = f' class="{esc(klasse or "breit")}"' if breit or klasse else ""
    kopf = kopf if kopf is not None else '<header class="kopf"><img src="/favicon.svg" alt="">Frieda</header>'
    return (f'<!DOCTYPE html><html lang="{esc(sp)}" dir="{esc(texte.sprache(sp).RICHTUNG)}"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">'
            f'<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="icon" href="/favicon.ico" sizes="48x48">'
            f'<link rel="apple-touch-icon" href="/apple-touch-icon.png"><link rel="manifest" href="/manifest.webmanifest">'
            f'<meta name="apple-mobile-web-app-title" content="Frieda"><meta name="theme-color" content="#f8f8f5">'
            + ('<script src="/konto.js" defer></script>' if skript else "")
            + f'<title>{esc(titel)} – Frieda</title><style>{CSS}</style></head><body>'
            f'<main{klasse}>{kopf}{rumpf}</main></body></html>')


def karte(*teile):
    return '<section class="karte">' + "".join(teile) + "</section>"


def fehler(t):
    return f'<p class="fehler" role="alert">{esc(t)}</p>' if t else ""


def verdeckt(**felder):
    return "".join(f'<input type="hidden" name="{esc(k)}" value="{esc(v)}">' for k, v in felder.items() if v)


def formular(ziel, inhalt, knopf, klasse="", aenderung=False):
    """aenderung: Einstellungen (Baustein speichernKnopf): Mit Skript ist der Knopf aus, bis sich ein Feld ändert
    (engine/app/konto.js); ohne Skript bleibt er an. autocomplete=off, damit der Browser beim Neuladen keine alten
    Eingaben einsetzt, die der Knopf dann nicht als Änderung erkennt."""
    k = f' class="{klasse}"' if klasse else ""
    a = ' data-aenderung autocomplete="off"' if aenderung else ""
    return f'<form method="post" action="{esc(ziel)}"{a}>{inhalt}<button{k}>{esc(knopf)}</button></form>'


def fuss(*saetze, roh=(), recht=False, ausser=""):
    """Leise Zeilen unter der Karte. roh: Zeilen, die schon HTML sind (Sätze mit Link); recht: zuletzt die Rechtszeile
    (Datenschutz, Impressum, Alpha-Hinweis, #383), ohne den Link auf die Seite ausser."""
    zeilen = [f"<p>{esc(t)}</p>" for t in saetze if t] + [f"<p>{h}</p>" for h in roh if h]
    if recht:
        zeilen.append('<p class="recht">' + "".join(f'<a href="{p}">{esc(tx("recht.link." + p[1:]))}</a>'
                                                    for p in RECHT if p != ausser) + "</p>")
    return '<div class="fuss">' + "".join(zeilen) + "</div>"


def link(pfad, schluessel):
    return f'<a href="{esc(pfad)}">{esc(tx(schluessel))}</a>'


def datenschutz_satz():
    """Kurzsatz der Anmeldeseiten mit Verweis auf die Erklärung (Heimat /datenschutz, ADR-0003)."""
    return th("konto.datenschutz", link=link("/datenschutz", "recht.datenschutz.titel"))


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
        fuss(tx("konto.anmelden.nur_lesen"), roh=(datenschutz_satz(), link("/", "info.link")), recht=True))


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
        f'<div class="links">{neuer_code}{andere}</div>', fuss(recht=True))


def warteliste_seite(email="", meldung=""):
    """Öffentliche Seite der Warteliste (#382): Adresse eintragen, Hinweis auf die Alpha und das bezahlte Claude-Konto."""
    return seite(tx("warteliste.titel"), karte(
        f"<div><h1>{esc(tx('warteliste.titel'))}</h1>",
        f'<p class="lead">{esc(tx("warteliste.alpha"))} {th("warteliste.alpha_mehr", link=link("/alpha", "recht.link.alpha"))}</p></div>',
        f'<p class="kasten">{esc(tx("warteliste.voraussetzung"))}</p>',
        fehler(meldung),
        formular("/warteliste", f'<label for="email">{esc(tx("konto.email_adresse"))}</label>'
                 f'<input id="email" type="email" name="email" value="{esc(email)}" autocomplete="email" required '
                 f'placeholder="{esc(tx("konto.email_beispiel"))}" autofocus>', tx("warteliste.knopf"))), fuss(recht=True))


def warteliste_hinweis(schluessel, code=200):
    """Seite mit einem Satz: gesendet, bestätigt oder „Link gilt nicht mehr“ (mit Weg zum neuen Eintrag)."""
    weg = (f'<a class="knopf" href="/warteliste">{esc(tx("warteliste.neu_eintragen"))}</a>'
           if schluessel == "warteliste.link_ungueltig" else "")
    return antwort(code, seite(tx("warteliste.titel"), karte(f"<h1>{esc(tx('warteliste.titel'))}</h1>",
                                                            f"<p>{esc(tx(schluessel))}</p>", weg), fuss(recht=True)))


def warteliste_karte():
    """Abschnitt „Warteliste“ auf Mein Konto, nur für Betreiber: bestätigte Einträge mit Knopf „Freigeben“."""
    eintraege = "".join(
        karte(f'<div><strong>{esc(e["email"])}</strong><p class="klein" style="margin:0">{esc(e["bestaetigt"][:10])}</p></div>',
              formular("/konto", verdeckt(aktion="warteliste_freigeben", wer=e["email"]), tx("konto.warteliste.freigeben"), "leise"))
        for e in konten.warteliste())
    return (f'<div class="abschnitt"><h2>{esc(tx("konto.warteliste.titel"))}</h2>'
            + (eintraege or f'<p class="hinweis">{esc(tx("konto.warteliste.keine"))}</p>')
            + f'<p class="klein">{esc(tx("konto.warteliste.unbestaetigt", n=konten.warteliste_unbestaetigt()))}</p></div>')


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
                     + formular("/konto", felder, tx("konto.kalender.speichern"), aenderung=True) + link
                     + (formular("/konto", verdeckt(aktion="kalender_neu"), tx("konto.kalender.neuer_link"), "neutral") if basis else "")
                     + "</div></details>")
    return (f'<div class="abschnitt"><h2>{esc(tx("konto.kalender.titel"))}</h2>'
            + karte(f'<p>{esc(tx("konto.kalender.hinweis"))}</p>', abo,
                    f'<div class="kalender-links">{andere}<a href="/konto?kalender=datei">{esc(tx("konto.kalender.datei_link"))}</a>'
                    f"{einstellungen}</div>")
            + "</div>")


PUSH_GERAET_TEXTE = ("einschalten", "ausschalten", "an", "aus_wo", "blockiert", "nicht_erlaubt", "fehler", "kein_browser",
                     "installieren", "schritt1", "schritt2", "schritt3")


def push_geraet():
    """Platz für den Schalter dieses Geräts (Baustein pushSchalter): Den Zustand kennt nur der Browser, darum füllt
    engine/app/konto.js ihn; Texte und den öffentlichen Schlüssel bringt die Seite mit. Ohne Skript bleibt er leer."""
    texte_json = json.dumps({n: tx("konto.push.geraet." + n) for n in PUSH_GERAET_TEXTE}, ensure_ascii=False)
    return (f'<div id="push-geraet" hidden data-schluessel="{esc(konten.push_schluessel("vapid_oeffentlich") or "")}" '
            f'data-texte="{esc(texte_json)}"></div>')


def push_karte(k, offen=False):
    """Benachrichtigungen auf Mein Konto (Issue #21, Entscheidung A vom 2.11.2026): ein- und ausschalten je Gerät
    (pushSchalter, Worker der Frieda-App an der Wurzel), dazu was aufs Handy kommt und die Ruhezeit, für alle Reisen gleich.
    Eine Heimat (ADR-0003): Der Fuß der Reiseseite verweist nur hierher. „Auf diesem Gerät ausschalten“ füllt das Skript
    in den Platz push-geraet-aus hinter „Konfigurieren“, vor „Auf allen Geräten ausschalten“, nie an die Stelle des
    Einschaltknopfs (#249); ohne Skript bleibt der Platz leer."""
    import push
    e = push.einstellungen_von(k["id"])
    geraete = len({a["geraet"] or a["endpoint"] for a in konten.push_abos(k["id"])})
    haken = lambda name, an, text: (f'<label class="haken"><input type="checkbox" name="{esc(name)}" value="ja"'   # noqa: E731
                                    f'{" checked" if an else ""}> {esc(text)}</label>')
    def gruppe(kat):   # je Gruppe (#517): aufs Handy ja/nein, per Mail wie (Leises nie per Mail)
        mail = ""
        if kat in push.MAIL_WERTE:
            wahl = "".join(f'<option value="{w}"{" selected" if e["mail"][kat] == w else ""}>{esc(tx("konto.push.mail." + w))}</option>'
                           for w in push.MAIL_WERTE[kat])
            mail = (f'<label for="mail_{kat}">{esc(tx("konto.push.per_mail"))}</label>'
                    f'<select id="mail_{kat}" name="mail_{kat}">{wahl}</select>')
        return (f'<fieldset><legend>{esc(tx("konto.push.kat." + kat))}</legend>'
                f'<p class="klein">{esc(tx("konto.push.kat." + kat + ".was"))}</p>'
                + haken("push_" + kat, e["push"][kat], tx("konto.push.aufs_handy")) + mail + "</fieldset>")
    felder = (verdeckt(aktion="push_einstellungen")
              + "".join(gruppe(k) for k in push.KATEGORIEN)
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
                     f'<div class="inhalt" style="padding:0">'
                     + formular("/konto", felder, tx("konto.kalender.speichern"), aenderung=True)
                     + '<div id="push-geraet-aus" hidden></div>' + aus + "</div></details>")
    return (f'<div class="abschnitt" id="push"><h2>{esc(tx("konto.push.titel"))}</h2>'
            + karte(f'<p>{esc(tx("konto.push.hinweis"))}</p>', push_geraet(), f'<p class="klein">{esc(geraete_text)}</p>',
                    f'<div class="kalender-links">{einstellungen}</div>')
            + "</div>")


def push_geraet_schalten(k, aktion, f):
    """Abruf des Schalters (engine/app/konto.js, POST /konto mit Origin-Prüfung): Abo dieses Geräts speichern (push_an,
    auch das stille Auffrischen beim Öffnen) oder entfernen (push_ab). Antwort ohne Seite: 204, 401 ohne Sitzung,
    400 mit Grund. Das Abo gehört zu keiner Reise (reise leer): Der Worker der Frieda-App zeigt Nachrichten aller Reisen."""
    if not k:
        return 401, [("Content-Type", "text/plain; charset=utf-8")], tx("konto.push.geraet.anmelden").encode("utf-8")
    try:
        if aktion == "push_ab":
            konten.push_abo_entfernen(k["id"], f.get("endpoint") or "")
        else:
            try:
                abo = json.loads(f.get("abo") or "")
            except ValueError:
                abo = None
            basis = konten.basis()
            konten.push_abo_speichern(k["id"], abo, "", basis + "/konto" if basis else "", f.get("geraet"), f.get("zeitzone"))
    except konten.KontoFehler as x:
        return 400, [("Content-Type", "text/plain; charset=utf-8")], x.text(sprache_der_seite()).encode("utf-8")
    return 204, [], b""


def push_formular(f):
    """Formular der Karte Benachrichtigungen -> Einstellungen (push.einstellungen bereinigt)."""
    import push
    return {"push": {k: f.get("push_" + k) == "ja" for k in push.KATEGORIEN},
            "mail": {k: f.get("mail_" + k, "") for k in push.MAIL_WERTE},
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


# Arten von Meldungen, die Handeln verlangen: ihre Marke ist warm, die der übrigen leise (#407). Die Arten sind Begriffe der
# Software (Wächter, Konflikt, Zustellen, Freischalten), keine Arten der Reise.
MELDUNG_WARM = ("konflikt", "erinnerung", "status", "pruefung", "technik", "betrieb", "anfrage_reisen", "anfrage_warteliste")
MELDUNGEN_ZEIGEN = 5          # so viele stehen offen, der Rest hinter „n weitere zeigen“
_ADRESSE = re.compile(r"\s*(?:·\s*)?[^.·]*?:\s*https?://\S+")


def meldung_zeitpunkt(erstellt, zone):
    """Zeitpunkt einer Meldung in der Zeitzone der Person, None bei kaputtem Wert."""
    try:
        z = datetime.datetime.fromisoformat(erstellt)
        z = z if z.tzinfo else z.replace(tzinfo=datetime.timezone.utc)
        return z.astimezone(ZoneInfo(zone))
    except (TypeError, ValueError, KeyError, OSError):
        return None


def meldung_wann(z, heute):
    """„heute 9:14“, „gestern“, sonst das kurze Datum (#407)."""
    if z is None:
        return ""
    tage = (heute - z.date()).days
    if tage == 0:
        return tx("konto.meldungen.heute", zeit=texte.zeit(z, sprache_der_seite()))
    if tage == 1:
        return tx("konto.meldungen.gestern")
    return texte.datum_kurz(z.date(), sprache_der_seite())


def meldung_text(m):
    """Text einer Meldung für die Webseite: aus ihren Teilen in der Sprache der Seite, sonst der gespeicherte Text.
    Meldungen „neue Reise“ ohne Teile trugen die Adresse der Seite (und ohne Konto den Link für die Claude-App) und den
    Namen des Werkzeugs meine_reisen im Text; beides fällt hier weg: Die Zeile ist der Link, und der Link für die Claude-App
    gehört nicht als Text auf die Seite."""
    neu = rm.meldung_text_in(m, sprache_der_seite())     # seit #407 Stufe C: formuliert in der Sprache des Kontos
    if neu is not None:
        return neu
    text = m.get("text") or ""
    if m.get("art") != "neue_reise":
        return text
    text = _ADRESSE.sub("", text)
    for kuerzel in texte.SPRACHEN:
        text = text.replace(texte.t(kuerzel, "konto.meldungen.alt_werkzeug"), "")
    return re.sub(r"\.\s*·\s*", ". ", re.sub(r"\s{2,}", " ", text)).strip(" ·")


def meldungen_ordnen(ms, zone):
    """Ordnung auf Mein Konto (#407): Prüfmeldungen einer Reise vom selben Tag werden eine Zeile; ungelesene stehen vor
    gelesenen, ungelesene Konflikte ganz oben (Entscheidung des Product Owners 8.11.2026), sonst die neueste zuerst.
    -> [{art, reise, zeit, text, anker, ids, gelesen}]; ids: alle Meldungen der Zeile, gelesen: alle davon gelesen."""
    aus, pruefungen = [], {}
    for m in ms:
        z = meldung_zeitpunkt(m.get("erstellt"), zone)
        e = {"art": m.get("art"), "reise": m.get("reise"), "zeit": z, "text": meldung_text(m), "anker": rm.meldung_anker(m),
             "erstellt": m.get("erstellt") or "", "ids": [m.get("id")], "gelesen": bool(m.get("gelesen"))}
        if e["art"] == "pruefung" and e["reise"]:
            pruefungen.setdefault((e["reise"], z.date() if z else None), []).append(e)
        else:
            aus.append(e)
    for gruppe in pruefungen.values():
        if len(gruppe) == 1:
            aus.append(gruppe[0])
        else:
            neueste = max(gruppe, key=lambda e: e["erstellt"])
            aus.append(neueste | {"text": tx("konto.meldungen.pruefungen", n=len(gruppe)), "anker": "zu-tun",
                                  "ids": [i for e in gruppe for i in e["ids"]], "gelesen": all(e["gelesen"] for e in gruppe)})
    aus.sort(key=lambda e: e["erstellt"], reverse=True)
    aus.sort(key=lambda e: (e["gelesen"], e["gelesen"] or e["art"] != "konflikt"))   # stabil, darin die neueste zuerst
    return aus


def meldung_ziel(e, reise_info):
    """Adresse der Stelle, an die eine Zeile führt (#407): Seite der Reise mit Sprungmarke, Bitten zu den Freischaltungen
    auf Mein Konto; None ohne Ziel."""
    info = (reise_info(e["reise"]) or {}) if e["reise"] else {}
    if info.get("seite"):
        return info["seite"] + (f'#{e["anker"]}' if e["anker"] else "")
    if e["art"] in ("anfrage_reisen", "anfrage_warteliste") and not e["reise"]:
        return "/konto#freischalten"
    return None


def meldung_zeile(e, reise_info, heute):
    """Molekül meldungZeile (#407): Punkt, solange ungelesen; Marke der Art, Reise und Zeit klein, darunter der Text. Die
    ganze Zeile führt über /konto?meldung=<id> (merkt gelesen) an die Stelle; ohne Ziel bleibt sie ohne Link."""
    info = (reise_info(e["reise"]) or {}) if e["reise"] else {}
    marken = texte.gruppe(sprache_der_seite(), "konto.meldungen.art")
    marke = (f'<span class="marke{" warm" if e["art"] in MELDUNG_WARM else " leise"}">{esc(marken[e["art"]])}</span>'
             if e["art"] in marken else "")
    reise = f'<span class="reise">{esc(info.get("titel") or e["reise"])}</span><span>·</span>' if e["reise"] else ""
    punkt = ('<span class="ohne-punkt"></span>' if e["gelesen"] else
             f'<span class="neu-punkt" role="img" aria-label="{esc(tx("konto.meldungen.neu_punkt"))}"></span>')
    inhalt = (f'{punkt}<span class="was"><span class="meldung-kopf">{marke}{reise}<span class="zeit">{esc(meldung_wann(e["zeit"], heute))}</span></span>'
              f'<span class="meldungstext">{esc(e["text"])}</span></span>')
    klasse = "zeile meldung" + ("" if e["gelesen"] else " ungelesen")
    if not meldung_ziel(e, reise_info) or not e["ids"][0]:
        return f'<div class="{klasse} ohne-link">{inhalt}</div>'
    return f'<a class="{klasse}" href="/konto?{esc(urllib.parse.urlencode({"meldung": e["ids"][0]}))}">{inhalt}</a>'


def meldungen_zone(k):
    """Zeitzone, in der Mein Konto Zeiten nennt: die des Geräts aus den Benachrichtigungen, sonst die der Instanz."""
    return konten.zeitzone_des_kontos(k["id"]) or instanz.zeitzone()


def meldungen_abschnitt(k, reise_info):
    """Meldungen an die Person über alle Reisen (#21 Stufe 1, #41, #407), dieselbe Quelle wie meine_reisen. Oben die
    ungelesenen mit Zahl und „Alle gelesen“, die ersten MELDUNGEN_ZEIGEN offen, der Rest zugeklappt; darunter zugeklappt
    „Gelesen (n)“. Jede Zeile führt an ihre Stelle. Ohne Meldungen: nichts."""
    zone = meldungen_zone(k)
    jetzt = meldung_zeitpunkt(datetime.datetime.now(datetime.timezone.utc).isoformat(), zone)
    heute = jetzt.date() if jetzt else datetime.date.today()
    alle = meldungen_ordnen(rm.meldungen_des_kontos(k), zone)
    if not alle:
        return ""
    neu = [meldung_zeile(e, reise_info, heute) for e in alle if not e["gelesen"]]
    alt = [meldung_zeile(e, reise_info, heute) for e in alle if e["gelesen"]]
    rest = neu[MELDUNGEN_ZEIGEN:]
    teile = "".join(neu[:MELDUNGEN_ZEIGEN]) if neu else f'<div class="leer">{esc(tx("konto.meldungen.keine_neuen"))}</div>'
    if rest:
        teile += (f'<details class="weitere"><summary class="zeile">{esc(tx("konto.meldungen.weitere", n=len(rest)))}</summary>'
                  f'<div class="liste-innen">{"".join(rest)}</div></details>')
    if alt:
        teile += (f'<details class="gelesen"><summary class="zeile">{esc(tx("konto.meldungen.gelesen", n=len(alt)))}</summary>'
                  f'<div class="liste-innen">{"".join(alt)}</div></details>')
    zahl = f'<span class="zahl">{esc(tx("konto.meldungen.neu", n=len(neu)))}</span>' if neu else ""
    knopf = (f'<form method="post" action="/konto">{verdeckt(aktion="meldungen_gelesen")}'
             f'<button class="link">{esc(tx("konto.meldungen.alle_gelesen"))}</button></form>') if neu else ""
    return (f'<div class="abschnitt" id="meldungen"><div class="abschnitt-kopf"><h2>{esc(tx("konto.meldungen.titel"))}{zahl}</h2>'
            f'{knopf}</div><div class="liste">{teile}</div></div>')


def meldung_oeffnen(k, mid, reise_info):
    """Zeile auf Mein Konto angetippt (#407): ihre Meldungen (bei gebündelten alle) als gelesen merken und an die Stelle
    weiterleiten. Eine Meldung, die nicht an dieses Konto geht oder nicht mehr gilt: 404, nichts wird gemerkt."""
    for e in meldungen_ordnen(rm.meldungen_des_kontos(k), meldungen_zone(k)):
        if mid in e["ids"]:
            konten.gelesen_merken(k["id"], e["ids"])
            return weiter(meldung_ziel(e, reise_info) or "/konto#meldungen")
    return antwort(404, seite(tx("konto.nicht_gefunden"), karte(f"<h1>{esc(tx('konto.nicht_gefunden'))}</h1>"),
                              f'<div class="links"><a href="/konto">{esc(tx("konto.seite.titel"))}</a></div>'))


def personen_block(reise, z, ich, extra=""):
    """Die Personen einer Reise, aufklappbar unter ihrer Zeile auf Mein Konto (#406). Alle Mitglieder sehen Name, Rolle,
    reist mit und von/bis; den Zugang (angemeldet, eingeladen, noch keiner) nur Organisator:innen. extra: steht unter den
    aufgeklappten Personen (Link „Reise löschen …“, #381)."""
    personen = (z or {}).get("personen") or []
    if not personen:
        return extra
    stand = konten.zugangsstand(reise) if rolle_neu(ich.get("rolle")) == "organisator" else None
    liste = "".join(f"<li>{esc(t)}</li>" for t in rm.personen_zeilen(personen, stand, sprache_der_seite()))
    return (f'<details class="personen"><summary>{esc(tx("konnektor.personen.titel", n=len(personen)))}</summary>'
            f"<ul>{liste}</ul>{extra}</details>")


# ---------------------------------------------------------------- Reise löschen (#381)
# Nur Organisator:innen einer Reise im Reisespeicher: Link unter den Personen, Bestätigung 1 (Haken), Bestätigung 2
# (Reisename eintippen), dann vorgemerkt mit Schonfrist; oben in „Meine Reisen“ der Block mit Datum und „Reise
# zurückholen“. Alle anderen Mitglieder bekommen sofort Mail und Meldung, beim Zurückholen eine zweite.

def _speicherreisen():
    try:
        return instanz.speicherreisen()
    except instanz.EinstellungenNichtLesbar:
        return []   # Liste unbekannt: kein Link, nichts wird vorgemerkt


def _reise_aus_speicher(reise):
    """reise.yaml der Reise aus dem Reisespeicher (nach dem Vormerken ist die Seite bald weg) oder {}."""
    if reise not in _speicherreisen():
        return {}
    try:
        import reisespeicher
        import yaml
        d = yaml.safe_load(reisespeicher.datei(reise, "reise.yaml"))
    except Exception:   # noqa: BLE001  ohne lesbaren Stand gibt es keine Angaben, nur die Kennung
        return {}
    return d if isinstance(d, dict) else {}


def _person(reise, schluessel, z=None):
    """Person der Reise zum Personen-Schlüssel: aus der veröffentlichten Seite, sonst aus reise.yaml im Speicher."""
    personen = ((z if z is not None else rm.zustand(reise)) or {}).get("personen")
    if personen is None:
        personen = _reise_aus_speicher(reise).get("personen") or []
    return next((p for p in personen if isinstance(p, dict) and p.get("schluessel") == schluessel), {})


def ist_organisatorin(k, reise, z=None):
    schl = konten.mitglied(k["id"], reise)
    return bool(schl) and rolle_neu(_person(reise, schl, z).get("rolle")) == "organisator"


def reise_titel(reise, reise_info=None):
    return (((reise_info(reise) or {}) if reise_info else {}).get("titel") or _reise_aus_speicher(reise).get("titel")
            or reise)


def frist_text(t, sprache, zone):
    """Zeitpunkt t (Sekunden, UTC) als Datum und Uhrzeit in der Zone der Person, mit Angabe der Zone."""
    try:
        tz = ZoneInfo(zone)
    except (ValueError, OSError, KeyError):
        tz = datetime.timezone.utc
    lokal = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).astimezone(tz)
    abk = lokal.tzname() or "UTC"
    return texte.t(sprache, "konnektor.zeit.mit_zone", zeit=texte.datum_zeit(lokal, sprache),
                   zone=texte.gruppe(sprache, "konnektor.zeitzone").get(abk.lower(), abk))


def loeschung_melden(ausloeser, reise, zeile, art, reise_info=None):
    """Mail (in der Sprache des Empfängers) und Meldung auf Mein Konto an alle anderen Mitglieder der Reise. art:
    vorgemerkt oder zurueckgeholt. Die Meldung entsteht immer; ein Mailfehler ändert am Vormerken nichts."""
    titel = reise_titel(reise, reise_info)
    z = rm.zustand(reise)
    for m in konten.mitglieder(reise):
        an = konten.konto(m["konto"])
        if m["konto"] == ausloeser["id"] or not an or an["gesperrt"]:
            continue
        sp = an["sprache"]
        werte = {"wer": ausloeser["name"], "titel": titel,
                 "frist": frist_text(zeile["frist"], sp, konten.zeitzone_des_kontos(an["id"]) or instanz.zeitzone())}
        zurueck = art == "vorgemerkt" and rolle_neu(_person(reise, m["schluessel"], z).get("rolle")) == "organisator"
        teile = [(f"konto.meldungen.text.reise_{art}", werte)] + (
            [("konto.meldungen.text.reise_vorgemerkt_zurueck", {})] if zurueck else [])
        try:
            rm.meldung_anlegen(rm.ordner_neu(anlegen=True), [an["id"]], "loeschung", "reise",
                               "".join(texte.t(sp, s, **w) for s, w in teile), teile=teile)
        except OSError as f:
            sys.stderr.write(f"deletion message {reise}: {f}\n")
        zeilen = [texte.t(sp, "konto.reise_loeschen.mail_anrede", name=an["name"]), "",
                  texte.t(sp, f"konto.reise_loeschen.mail_{art}", **werte)]
        if zurueck:
            zeilen += ["", texte.t(sp, "konto.reise_loeschen.mail_zurueck")] + ([f"{konten.basis()}/konto"] if konten.basis() else [])
        try:
            konten.mail_senden(an["email"], texte.t(sp, f"konto.reise_loeschen.mail_{art}_betreff", titel=titel), "\n".join(zeilen))
        except (konten.KontoFehler, OSError) as f:
            sys.stderr.write(f"deletion mail {reise}: {type(f).__name__}\n")


def _loeschen_erlaubt(k, reise):
    """Darf k die Reise löschen? Nur Organisator:innen, nur Reisen im Reisespeicher, nicht schon vorgemerkt."""
    if reise not in _speicherreisen() or not ist_organisatorin(k, reise):
        raise konten.KontoFehler("konto.fehler.nur_organisatorin")
    if konten.reise_vorgemerkt(reise):
        raise konten.KontoFehler("konto.fehler.reise_schon_vorgemerkt")


def reise_loeschen(k, reise, reise_info=None):
    """Reise zur Löschung vormerken und alle anderen Mitglieder benachrichtigen -> Zeile der Vormerkung."""
    _loeschen_erlaubt(k, reise)
    titel = reise_titel(reise, reise_info)   # vor dem Vormerken: danach ist die Seite bald weg
    zeile = konten.loeschung_vormerken(reise, k["id"])
    loeschung_melden(k, reise, zeile, "vorgemerkt", lambda r: {"titel": titel})
    return zeile


def reise_zurueckholen(k, reise, reise_info=None):
    """Vormerkung aufheben (nur Organisator:innen, nur in der Frist) und alle anderen Mitglieder benachrichtigen."""
    if not ist_organisatorin(k, reise):
        raise konten.KontoFehler("konto.fehler.nur_organisatorin")
    zeile = konten.loeschung_zurueckholen(reise, k["id"])
    loeschung_melden(k, reise, zeile, "zurueckgeholt", reise_info)
    return zeile


def _gleicher_name(a, b):
    return " ".join(str(a or "").split()).casefold() == " ".join(str(b or "").split()).casefold()


def reise_loeschen_seite(k, reise, reise_info, schritt=1, meldung=""):
    """Bestätigung 1 (Erklärung und Haken) oder 2 (Reisename eintippen) vor dem Löschen einer Reise."""
    titel = reise_titel(reise, reise_info)
    erklaerung = (f'<div><strong>{esc(tx("konto.reise_loeschen.weg"))}</strong><p style="margin:.2rem 0 0">{esc(tx("konto.reise_loeschen.weg_text", titel=titel))}</p></div>'
                  f'<div><strong>{esc(tx("konto.reise_loeschen.frist"))}</strong><p style="margin:.2rem 0 0">{esc(tx("konto.reise_loeschen.frist_text", tage=instanz.loeschfrist_tage()))}</p>'
                  f'<p style="margin:.2rem 0 0">{esc(tx("konto.reise_loeschen.benachrichtigt"))}</p></div>')
    if schritt == 1:
        form = formular("/konto", verdeckt(aktion="reise_loeschen_1", reise=reise)
                        + f'<label class="haken bestaetigen"><input type="checkbox" name="verstanden" value="ja" required> '
                          f'{esc(tx("konto.reise_loeschen.haken"))}</label>', tx("konto.reise_loeschen.weiter"), "gefahr")
    else:
        form = formular("/konto", verdeckt(aktion="reise_loeschen", reise=reise, verstanden="ja")
                        + f'<label for="titel">{esc(tx("konto.reise_loeschen.name_label", titel=titel))}</label>'
                          '<input id="titel" type="text" name="titel" autocomplete="off" required>',
                        tx("konto.reise_loeschen.knopf"), "gefahr")
    return seite(tx("konto.reise_loeschen.titel"),
                 f'<a class="zurueck" href="/konto">‹ {esc(tx("konto.seite.titel"))}</a>',
                 karte(f"<h1>{esc(tx('konto.reise_loeschen.titel'))}</h1>", fehler(meldung), erklaerung, form,
                       f'<div class="links"><a href="/konto">{esc(tx("konto.seite.abbrechen"))}</a></div>'),
                 fuss(recht=True), kopf="")


def loeschen_block(k, vorgemerkt, reise_info):
    """Block der vorgemerkten Reisen oben in „Meine Reisen“: Name, Datum des Entfernens mit Zone, „Reise zurückholen“ nur
    für Organisator:innen und nur vor dem Fristende."""
    zone, jetzt = meldungen_zone(k), konten._jetzt()
    teile = []
    for z in vorgemerkt:
        titel = reise_titel(z["reise"], reise_info)
        offen = z["frist"] > jetzt
        satz = (tx("konto.reise_loeschen.block", titel=titel, frist=frist_text(z["frist"], sprache_der_seite(), zone)) if offen
                else tx("konto.reise_loeschen.block_vorbei", titel=titel))
        knopf = (f'<form method="post" action="/konto">{verdeckt(reise=z["reise"])}<button class="leise" name="aktion" '
                 f'value="reise_zurueckholen">{esc(tx("konto.reise_loeschen.zurueckholen"))}</button></form>'
                 if offen and ist_organisatorin(k, z["reise"]) else "")
        teile.append(f'<div class="vorgemerkt kasten"><p style="margin:0 0 .4rem">{esc(satz)}</p>{knopf}</div>')
    return "".join(teile)


def loeschen_link(k, reise, z, p):
    """Was unter den aufgeklappten Personen steht: für Organisator:innen einer Speicherreise der Link „Reise löschen …“,
    für Organisator:innen einer Reise auf dem alten Weg ein Satz; für alle anderen nichts."""
    if rolle_neu(p.get("rolle")) != "organisator":
        return ""
    if reise not in _speicherreisen():
        return f'<p class="klein" style="margin:0 1rem 1rem">{esc(tx("konto.reise_loeschen.erst_nach_umstellung"))}</p>'
    return (f'<p style="margin:0 1rem 1rem"><a href="/konto?{esc(urllib.parse.urlencode({"reise_loeschen": reise}))}" '
            f'style="color:var(--gefahr)">{esc(tx("konto.reise_loeschen.link"))}</a></p>')


def verbinden_karte():
    """Anleitung, Frieda in der Claude-App als Konnektor hinzuzufügen, mit der Adresse zum Kopieren (#422)."""
    adresse = (konten.basis() or "") + "/mcp"
    schritte = "".join(f"<li>{esc(tx(f'konto.verbinden.schritt{n}'))}</li>" for n in (1, 2, 3, 4))
    schritte = schritte.replace("</li><li>" + esc(tx("konto.verbinden.schritt4")),
                                f'<input type="text" readonly aria-label="{esc(tx("konto.verbinden.adresse_label"))}" value="{esc(adresse)}">'
                                "</li><li>" + esc(tx("konto.verbinden.schritt4")), 1)
    return (f'<div class="abschnitt" id="verbinden"><h2>{esc(tx("konto.verbinden.titel"))}</h2>'
            + karte(f'<p>{esc(tx("konto.verbinden.einleitung"))}</p><ol>{schritte}</ol>'
                    f'<p class="klein">{esc(tx("konto.verbinden.bezahlt"))}</p>') + "</div>")


def einstieg_karte(k):
    """„Neu bei Frieda?“ mit dem Weg zur Infoseite, solange das Konto nicht mit Claude verbunden ist (#440)."""
    if konten.mit_claude_verbunden(k["id"]):
        return ""
    return (f'<section class="karte einstieg"><div><h2>{esc(tx("konto.einstieg.titel"))}</h2>'
            f'<p class="hinweis" style="margin:.35rem 0 0">{esc(tx("konto.einstieg.text"))}</p></div>'
            f'<a class="knopf leise" href="/info/">{esc(tx("konto.einstieg.knopf"))}</a></section>')


def konto_seite(k, reise_info, meldung="", hinweis="", adresse_neu="", offen=""):
    """Mein Konto (Gestalt #60), zugleich die Startseite (#41): Meldungen, Reisen, dann Kalender, Freischaltungen
    (Betreiber), Einstellungen als Liste, unten Abmelden auf allen Geräten und Konto löschen. offen: Einstellung, die
    aufgeklappt erscheint. Ab Tablet zwei Spalten (#441): links, was sich tut (Meldungen, Reisen, Mit Claude verbinden),
    rechts, was selten gebraucht wird; auf dem Handy untereinander in derselben Reihenfolge."""
    zeilen, archiv = [], []
    vorgemerkt = {z["reise"]: z for z in konten.loeschungen()}
    meine_vorgemerkten = []
    for m in konten.mitgliedschaften(k["id"]):
        if m["reise"] in vorgemerkt:   # #381: steht im Block oben, nicht in der Liste
            meine_vorgemerkten.append(vorgemerkt[m["reise"]])
            continue
        info = reise_info(m["reise"]) or {}
        z = rm.zustand(m["reise"]) or {}
        p = next((x for x in z.get("personen") or [] if x.get("schluessel") == m["schluessel"]), {})
        inhalt = (f'<span class="was"><span class="titel">{esc(info.get("titel") or m["reise"])}</span>'
                  f"{rolle_marke(p.get('rolle'))}</span>")
        kopf = (f'<a class="zeile" href="{esc(info["seite"])}">{inhalt}</a>' if info.get("seite")
                else f'<div class="zeile">{inhalt}</div>')
        (archiv if z.get("status") == "archiv" else zeilen).append(
            f'<div class="reise">{kopf}{personen_block(m["reise"], z, p, loeschen_link(k, m["reise"], z, p))}</div>')
    reisen = f'<div class="liste">{"".join(zeilen)}</div>' if zeilen else (
        "" if archiv or meine_vorgemerkten else karte(f'<p class="hinweis">{esc(tx("konto.reisen.keine"))}</p>'))
    reisen = loeschen_block(k, meine_vorgemerkten, reise_info) + reisen
    if archiv:   # archivierte Reisen (auch Testreisen) bleiben erreichbar, stören aber nicht die Liste (#416)
        reisen += (f'<details class="archiv"><summary>{esc(tx("konto.archiv.titel", n=len(archiv)))}</summary>'
                   f'<div class="liste">{"".join(archiv)}</div></details>')
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
        betreiber = (f'<div class="abschnitt" id="freischalten"><h2>{esc(tx("konto.betreiber.titel"))}</h2>'
                     + (bitten or f'<p class="hinweis">{esc(tx("konto.betreiber.keine"))}</p>') + "</div>"
                     + warteliste_karte())
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
    kopf = (f'<header class="kopf breit"><span><img src="/favicon.svg" alt="">Frieda</span><nav class="kopf-rechts">'
            f'<a class="kopf-link" href="/info/">{esc(tx("info.link"))}</a>'
            f'<form method="post" action="/abmelden"><button class="link">{esc(tx("konto.seite.abmelden"))}</button></form></nav></header>')
    return seite(tx("konto.seite.titel"),
                 f'<div><h1 style="font-size:1.875rem">{esc(tx("konto.seite.hallo", name=k["name"]))}</h1>'
                 f'<p class="hinweis" style="margin:.1rem 0 0">{esc(k["email"])}</p></div>',
                 fehler(meldung), f'<p class="kasten">{esc(hinweis)}</p>' if hinweis else "",
                 einstieg_karte(k),
                 '<div class="spalten"><div class="spalte">',
                 meldungen_abschnitt(k, reise_info),
                 f'<div class="abschnitt"><h2>{esc(tx("konto.seite.meine_reisen"))}</h2>{reisen}{anlegen}</div>',
                 verbinden_karte(),
                 '</div><div class="spalte">',
                 kalender_karte(k, reise_info, offen == "kalender"),
                 push_karte(k, offen == "push"),
                 betreiber,
                 f'<div class="abschnitt"><h2>{esc(tx("konto.seite.einstellungen"))}</h2><div class="liste">{einstellungen}</div></div>',
                 '<div class="links" style="flex-direction:column;align-items:center">'
                 f'<form method="post" action="/konto">{verdeckt(aktion="alle_abmelden")}<button class="link">{esc(tx("konto.seite.ueberall_abmelden"))}</button></form>'
                 f'<a href="/konto?loeschen=1" style="color:var(--gefahr)">{esc(tx("konto.seite.loeschen_titel"))}</a></div>',
                 '</div></div>',
                 fuss(recht=True), kopf=kopf, skript=True, klasse="konto")


def loeschen_seite(k, reise_info=None):
    """Rückfrage vor dem Löschen: was gelöscht wird, was bleibt ohne den Namen (#60, #381), welche Reisen mitgehen. Ist die
    Person die einzige Organisator:in einer Reise mit weiteren Mitgliedern, nennt die Seite diese Reisen statt des Formulars."""
    gesperrt, allein, _ = konten.loeschen_pruefen(k["id"])
    titel = lambda r: reise_titel(r, reise_info)   # noqa: E731
    liste = lambda reisen: "<ul>" + "".join(f"<li>{esc(titel(r))}</li>" for r in reisen) + "</ul>"   # noqa: E731
    if gesperrt:
        unten = (f'<div class="fehler"><strong>{esc(tx("konto.loeschen.erst_klaeren"))}</strong> '
                 f'{esc(tx("konto.fehler.letzte_organisatorin", reisen=", ".join(titel(r) for r in gesperrt)))}</div>')
    else:
        unten = formular("/konto", verdeckt(aktion="loeschen")
                         + f'<label class="haken bestaetigen"><input type="checkbox" name="sicher" value="ja" required> '
                           f'{esc(tx("konto.seite.loeschen_haken"))}</label>', tx("konto.seite.loeschen_knopf"), "gefahr")
    mit = (f'<div><p style="margin:.2rem 0 0">{esc(tx("konto.loeschen.reisen_gehen_mit", tage=instanz.loeschfrist_tage()))}</p>'
           f"{liste(allein)}</div>" if allein else "")
    return seite(tx("konto.seite.loeschen_frage"),
                 f'<a class="zurueck" href="/konto">‹ {esc(tx("konto.seite.titel"))}</a>',
                 karte(f"<h1>{esc(tx('konto.seite.loeschen_frage'))}</h1>",
                       f'<div><strong>{esc(tx("konto.seite.loeschen_bleibt"))}</strong><p style="margin:.2rem 0 0">{esc(tx("konto.seite.loeschen_bleibt_text"))}</p></div>',
                       f'<div><strong>{esc(tx("konto.seite.loeschen_weg"))}</strong><p style="margin:.2rem 0 0">{esc(tx("konto.seite.loeschen_weg_text"))}</p></div>',
                       mit, unten,
                       f'<div class="links"><a href="/konto">{esc(tx("konto.seite.abbrechen"))}</a></div>'),
                 fuss(recht=True), kopf="")


def einladungs_seite(e, token, k, reise_info, meldung=""):
    info = reise_info(e["reise"]) or {}
    titel = info.get("titel") or e["reise"]
    kopf = (f"<div><h1>{esc(tx('konto.einladung.titel'))}</h1><p class=\"lead\">"
            f"{th('konto.einladung.text', von=esc(e['von']), name=esc(e['name']), titel='<strong>' + esc(titel) + '</strong>')}</p></div>"
            + rolle_marke(e["rolle"]))
    if e["eingeloest"]:
        return seite(tx("konto.einladung.titel"), karte(kopf, f'<p class="hinweis">{esc(tx("konto.einladung.angenommen"))}</p>',
                                                       f'<a class="knopf" href="/konto">{esc(tx("konto.einladung.zum_konto"))}</a>'), fuss(recht=True))
    if k:
        return seite(tx("konto.einladung.titel"), karte(
            kopf, fehler(meldung),
            formular(f"/einladung/{token}", "", tx("konto.einladung.annehmen", name=k["name"], email=k["email"]))),
            fuss(roh=(th("konto.einladung.anderes_konto", link=link("/konto", "konto.einladung.abmelden_link")),), recht=True))
    q = urllib.parse.urlencode({"einladung": token, "email": e["email"]})
    return seite(tx("konto.einladung.titel"), karte(
        kopf, f"<p>{esc(tx('konto.einladung.anmelden_hinweis'))}</p>",
        f'<a class="knopf" href="/anmelden?{q}">{esc(tx("konto.anmelden.titel"))}</a>'),
        fuss(roh=(datenschutz_satz(),), recht=True))


# ---------------------------------------------------------------- Datenschutz, Impressum, Alpha-Hinweis (#383)
# Heimat (ADR-0003): die Erklärung nur auf /datenschutz, das Impressum nur auf /impressum, der Alpha-Hinweis nur auf /alpha;
# überall sonst nur die Rechtszeile. Die Texte stehen im Katalog (Entwurf, rechtliche Prüfung beim Product Owner), die
# Angaben zum Betreiber kommen aus den Einstellungen der Instanz (instanz.wert), nie aus dem Repo.

RECHT = ("/datenschutz", "/impressum", "/alpha")
BETREIBER = (("FR_BETREIBER_NAME", "name"), ("FR_BETREIBER_ANSCHRIFT", "anschrift"), ("FR_BETREIBER_KONTAKT", "kontakt"))
DATENSCHUTZ_ABSCHNITTE = ("konto", "warteliste", "reise", "verlauf", "belege", "sicherungen", "weitergabe", "cookie")
ALPHA_PUNKTE = ("fehler", "datenverlust", "aenderungen", "claude_konto")


def datenschutz_inhalt():
    impressum = link("/impressum", "recht.link.impressum")
    abschnitte = "".join(f'<div><h2>{esc(tx(f"recht.datenschutz.{a}.titel"))}</h2><p style="margin:.3rem 0 0">'
                         f'{esc(tx(f"recht.datenschutz.{a}.text"))}</p></div>' for a in DATENSCHUTZ_ABSCHNITTE)
    return (f'<div><h1>{esc(tx("recht.datenschutz.titel"))}</h1>'
            f'<p class="lead">{th("recht.datenschutz.einleitung", impressum=impressum)}</p></div>' + abschnitte
            + f'<div><h2>{esc(tx("recht.datenschutz.rechte.titel"))}</h2>'
            f'<p style="margin:.3rem 0 0">{esc(tx("recht.datenschutz.konto_loeschen"))}</p>'
            f'<p style="margin:.3rem 0 0">{esc(tx("recht.datenschutz.reise_loeschen", tage=instanz.loeschfrist_tage()))}</p>'
            f'<p style="margin:.3rem 0 0">{esc(tx("recht.datenschutz.namen_freitext"))}</p>'
            f'<p style="margin:.3rem 0 0">{esc(tx("recht.datenschutz.folgt"))}</p>'
            f'<p style="margin:.3rem 0 0">{th("recht.datenschutz.kontakt", impressum=impressum)}</p></div>')


def impressum_inhalt():
    """Name, Anschrift und Kontakt aus FR_BETREIBER_*; fehlt einer (leer zählt als fehlend), nur der Hinweis „nicht
    eingerichtet“, nie halb gefüllte Felder. Werte maskiert, Zeilenumbrüche der Anschrift bleiben."""
    werte = [(feld, (instanz.wert(name) or "").strip()) for name, feld in BETREIBER]   # nur Leerraum zählt als nicht gesetzt
    kopf = (f'<div><h1>{esc(tx("recht.impressum.titel"))}</h1>'
            f'<p class="lead">{esc(tx("recht.impressum.einleitung"))}</p></div>')
    if not all(w for _, w in werte):
        return kopf + f'<p class="kasten">{esc(tx("recht.impressum.nicht_eingerichtet"))}</p>'
    return kopf + "".join(f'<div><strong>{esc(tx("recht.impressum." + feld))}</strong>'
                          f'<p style="margin:.2rem 0 0">{esc(w).replace(chr(10), "<br>")}</p></div>' for feld, w in werte)


def alpha_inhalt():
    return (f'<div><h1>{esc(tx("recht.alpha.titel"))}</h1><p class="lead">{esc(tx("recht.alpha.einleitung"))}</p></div>'
            '<ul class="punkte">' + "".join(f"<li>{esc(tx('recht.alpha.' + p))}</li>" for p in ALPHA_PUNKTE) + "</ul>")


RECHT_SEITEN = {"/datenschutz": ("recht.datenschutz.titel", datenschutz_inhalt), "/impressum": ("recht.impressum.titel", impressum_inhalt),
                "/alpha": ("recht.alpha.titel", alpha_inhalt)}


def recht_seite(pfad):
    titel, inhalt = RECHT_SEITEN[pfad]
    return seite(tx(titel), karte(inhalt()),
                 f'<div class="links">{link("/warteliste", "recht.zurueck.warteliste")}{link("/anmelden", "recht.zurueck.anmelden")}</div>',
                 fuss(recht=True, ausser=pfad))


# ---------------------------------------------------------------- Infoseite (#436)

# Was die Seite zeigt, in dieser Reihenfolge; die Texte stehen im Katalog unter info.… Die Gespräche sind erfunden und gehören zu
# den beiden Beispielreisen: je Gespräch die Folge der Sprecher (person, claude), die Texte heißen info.gespraech.<name>.<n>.
INFO_PRINZIPIEN = ("gespraech", "wahrheit", "entscheiden", "seite", "gemeinsam", "eigen")
INFO_GESPRAECHE = (("anlegen", ("person", "claude", "person", "claude")),
                   ("vergleichen", ("person", "claude", "person", "claude", "person", "claude")),
                   ("herkunft", ("person", "claude", "person", "claude")),
                   ("unterwegs", ("person", "claude")))
# Bildschirmbilder der Reiseseite je Sprache als engine/info/<name>-<sprache>.webp, erzeugt von engine/info/erzeugen.py aus den
# Beispielreisen; fehlt eine Sprache, nimmt die Seite die Vorgabe der Software, fehlt das Bild ganz, entfällt es.
INFO_BILDER = ("reise", "tag", "wahl", "packliste")
INFO = Path(__file__).resolve().parent / "info"
INFO_DATEI = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\.webp")


def info_bild(name):
    """Pfad des Bilds name in der Sprache der Seite (ersatzweise in der Vorgabe) oder None."""
    for sp in (sprache_der_seite(), texte.VORGABE_REISE):
        if (INFO / f"{name}-{sp}.webp").is_file():
            return f"/info/{name}-{sp}.webp"
    return None


def info_datei(pfad):
    """/info/<datei>.webp -> Datei in engine/info/ oder None (nur Bilder dieser Form, kein Weg aus dem Ordner)."""
    name = pfad.removeprefix("/info/")
    if not pfad.startswith("/info/") or not INFO_DATEI.fullmatch(name):
        return None
    datei = INFO / name
    return datei if datei.is_file() else None


def info_sprachen(pfad="/"):
    """Zeile zum Umschalten der Sprache: ein Link je Sprache der Software auf die Adresse pfad, die aktuelle ist markiert."""
    sp = sprache_der_seite()
    return (f'<nav class="sprachen" aria-label="{esc(tx("info.sprache"))}">'
            + "".join(f'<a href="{esc(pfad)}?sprache={esc(c)}" lang="{esc(c)}" hreflang="{esc(c)}"'
                      + (' aria-current="page"' if c == sp else "") + f'>{esc(texte.sprache(c).NAME)}</a>' for c in texte.SPRACHEN)
            + "</nav>")


def info_gespraech(name, folge):
    wer = {"person": tx(f"info.gespraech.{name}.person"), "claude": tx("info.gespraech.claude")}
    blasen = "".join(f'<p class="blase {r}"><span class="wer">{esc(wer[r])}</span>{esc(tx(f"info.gespraech.{name}.{n}"))}</p>'
                     for n, r in enumerate(folge, 1))
    return karte(f'<div class="gespraech"><h3>{esc(tx(f"info.gespraech.{name}.titel"))}</h3>{blasen}</div>')


def info_seite(k=None, pfad="/"):
    """Was ist Frieda? Grundprinzipien, Beispiel-Gespräche, Bilder der Reiseseite und die ersten Schritte, mit der Adresse des
    Konnektors dieser Instanz. Die Startseite der Adresse für alle, die nicht angemeldet sind (Product Owner, 9.11.2026), und
    unter /info/ für alle, auch angemeldet als Einstiegshilfe (#440). k: angemeldetes Konto, dann führen Kopf und Knopf zu Mein
    Konto statt zu Anmelden und Warteliste. pfad: Adresse der Seite für den Sprachumschalter."""
    if k:
        kopf_link = f'<a class="kopf-link" href="/konto">{esc(tx("info.mein_konto"))}</a>'
        knoepfe = f'<a class="knopf" href="/konto">{esc(tx("info.zu_reisen"))}</a>'
        satz = tx("info.angemeldet_als", name=k["name"])
    else:
        kopf_link = f'<a class="kopf-link" href="/anmelden">{esc(tx("info.anmelden"))}</a>'
        knoepfe = (f'<a class="knopf" href="/anmelden">{esc(tx("info.anmelden"))}</a>'
                   f'<a class="knopf leise" href="/warteliste">{esc(tx("info.warteliste"))}</a>')
        satz = tx("info.schon_dabei")
    kopf = f'<header class="kopf breit"><span><img src="/favicon.svg" alt="">Frieda</span>{kopf_link}</header>'
    oben = karte(f'<div><h1>{esc(tx("info.ueberschrift"))}</h1>', f'<p class="lead">{esc(tx("info.lead"))}</p></div>',
                 f'<div class="knoepfe">{knoepfe}</div>', f'<p class="klein">{esc(satz)}</p>')
    prinzipien = "".join(karte(f'<h3>{esc(tx(f"info.prinzip.{p}.titel"))}</h3><p>{esc(tx(f"info.prinzip.{p}.text"))}</p>')
                         for p in INFO_PRINZIPIEN)
    gespraeche = "".join(info_gespraech(n, f) for n, f in INFO_GESPRAECHE)
    bilder = "".join(f'<figure><a href="{esc(b)}"><img src="{esc(b)}" alt="{esc(tx("info.bild." + n))}" loading="lazy" width="585" '
                     'height="1050"></a>'
                     f'<figcaption>{esc(tx("info.bild." + n))}</figcaption></figure>'
                     for n in INFO_BILDER if (b := info_bild(n)))
    # Adresse des Konnektors dieser Instanz zum Kopieren; ohne eingerichtete Adresse (FR_BASIS) kein leeres Feld
    adresse = (f'<input type="text" readonly aria-label="{esc(tx("konto.verbinden.adresse_label"))}" value="{esc(konten.basis() + "/mcp")}">'
               if konten.basis() else "")
    verbinden = ("".join(f"<li>{esc(tx(f'konto.verbinden.schritt{n}'))}</li>" for n in (1, 2, 3)).removesuffix("</li>")
                 + f'{adresse}</li><li>{esc(tx("info.schritt.verbinden.anmelden"))}</li>')
    schritt = lambda s, inhalt: f'<li><div><h3>{esc(tx(f"info.schritt.{s}.titel"))}</h3>{inhalt}</div></li>'   # noqa: E731
    schritte = "".join((
        schritt("konto", f'<p>{esc(tx("info.schritt.konto.text"))}</p>'),
        schritt("verbinden", f'<ol>{verbinden}</ol><p class="klein">{esc(tx("konto.verbinden.bezahlt"))}</p>'),
        schritt("loslegen", f'<p>{esc(tx("info.schritt.loslegen.text"))}</p>'),
        schritt("seite", f'<p>{esc(tx("info.schritt.seite.text"))}</p><p class="klein">{esc(tx("konto.anmelden.nur_lesen"))}</p>')))
    abschnitt = lambda titel, *inhalt: f'<section class="abschnitt"><h2>{esc(tx(titel))}</h2>{"".join(inhalt)}</section>'   # noqa: E731
    return seite(tx("info.titel"), oben,
                 abschnitt("info.prinzipien.titel", f'<div class="prinzipien">{prinzipien}</div>'),
                 abschnitt("info.gespraeche.titel", f'<p>{esc(tx("info.gespraeche.einleitung"))}</p>', gespraeche),
                 abschnitt("info.bilder.titel", f'<p>{esc(tx("info.bilder.einleitung"))}</p>', f'<div class="bilder">{bilder}</div>')
                 if bilder else "",
                 abschnitt("info.schritte.titel", karte(f'<ol class="erste">{schritte}</ol>')),
                 fuss(roh=(info_sprachen(pfad),), recht=True), kopf=kopf, breit=True)


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
    return p in ("/anmelden", "/konto", "/abmelden", "/warteliste", "/info", "/info/") + RECHT or p.startswith(("/einladung/", "/kalender/",
                                                                                     "/warteliste/bestaetigen/"))


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

    if weg in RECHT:
        if methode != "GET":     # nur lesen: kein Formular, keine Wirkung
            return antwort(405, seite(tx("konto.nicht_erlaubt"), karte(
                f"<h1>{esc(tx('konto.nicht_erlaubt'))}</h1><p>{esc(tx('recht.methode'))}</p>")), [("Allow", "GET")])
        return antwort(200, recht_seite(weg))

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

    if weg == "/warteliste":
        if methode == "GET":
            return antwort(200, warteliste_seite())
        try:
            konten.warteliste_eintragen(f.get("email"), ip=ip, sprache=sprache_der_seite())
        except konten.KontoFehler as x:
            return antwort(200, warteliste_seite(f.get("email", ""), x.text(sprache_der_seite())))
        return warteliste_hinweis("warteliste.gesendet")     # immer derselbe Satz, er verrät nichts über den Stand

    if weg.startswith("/warteliste/bestaetigen/"):
        wort = weg.rsplit("/", 1)[1]
        if methode == "GET":     # Mailprogramme rufen Links vorab auf: erst der Knopf bestätigt
            if not konten.warteliste_wort_gilt(wort):
                return warteliste_hinweis("warteliste.link_ungueltig", 404)
            return antwort(200, seite(tx("warteliste.titel"), karte(
                f"<div><h1>{esc(tx('warteliste.titel'))}</h1>",
                f'<p class="lead">{esc(tx("warteliste.bestaetigen_text"))}</p></div>',
                formular(weg, "", tx("warteliste.bestaetigen_knopf"))), fuss(recht=True)))
        try:
            e = konten.warteliste_bestaetigen(wort)
        except konten.KontoFehler:
            return warteliste_hinweis("warteliste.link_ungueltig", 404)
        betreiber_melden(None, "anfrage_warteliste",
                         texte.t(texte.VORGABE_REISE, "konto.betreiber.warteliste", email=e["email"]),
                         [("konto.meldungen.text.anfrage_warteliste", {"email": e["email"]})])
        return warteliste_hinweis("warteliste.bestaetigt")

    if weg == "/abmelden":
        if methode == "POST" and token:
            konten.abmelden(token)
        return weiter("/anmelden", [cookie_loeschen()])

    if weg.startswith("/einladung/"):
        et = weg.rsplit("/", 1)[1]
        e = konten.einladung(et)
        if not e:
            return antwort(404, seite(tx("konto.einladung.titel"), karte(
                f"<h1>{esc(tx('konto.einladung.abgelaufen'))}</h1><p>{esc(tx('konto.einladung.abgelaufen_text'))}</p>"), fuss(recht=True)))
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

    if weg == "/info":     # nginx leitet /info wegen des Orts /info/ (Bilder) selbst dorthin; der Dienst ebenso, mit der Sprache
        return weiter("/info/" + (f"?{teile.query}" if teile.query else ""))
    if weg in ("/", "/info/"):
        # Startseite: angemeldet Mein Konto (#41), sonst die Infoseite (#436); /info/ zeigt sie allen, auch angemeldet (#440). Sie liegt
        # unter /info/, weil nginx diesen Ort für die Bilder schon zum Dienst führt (kein neuer Ort, kein Handschritt in der Instanz).
        # Nur zum Lesen: der Konnektor leitet / nur mit GET hierher, ein POST auf /info/ führt ohne Wirkung zurück auf die Seite.
        if weg == "/" and k:
            return weiter("/konto")
        if methode == "POST":
            return weiter("/info/")
        if texte.gueltig(q.get("sprache") or ""):     # Umschalter der Infoseite; ein geteilter Link kann die Sprache mitgeben
            _anfrage.sprache = q["sprache"]
        return antwort(200, info_seite(k, weg))
    if weg == "/konto":
        a = f.get("aktion")
        if a in ("push_an", "push_ab"):
            return push_geraet_schalten(k, a, f)
        if not k:
            return weiter("/anmelden?zurueck=/konto")
        if methode == "GET" and q.get("kalender") == "datei":
            return kalender_antwort(k, datei=True)
        if methode == "GET" and q.get("loeschen"):
            return antwort(200, loeschen_seite(k, reise_info))
        if methode == "GET" and q.get("reise_loeschen"):   # Bestätigung 1 (#381); ein GET ändert nie etwas
            try:
                _loeschen_erlaubt(k, q["reise_loeschen"])
            except konten.KontoFehler as x:
                return antwort(200, konto_seite(k, reise_info, meldung=x.text(sprache_der_seite())))
            return antwort(200, reise_loeschen_seite(k, q["reise_loeschen"], reise_info))
        if methode == "GET" and q.get("meldung"):      # Zeile der Meldungen: gelesen merken, an die Stelle (#407)
            return meldung_oeffnen(k, q["meldung"], reise_info)
        if methode == "GET" and q.get("push") in ("an", "aus"):    # zurück vom Schalter (engine/app/konto.js)
            return antwort(200, konto_seite(k, reise_info, hinweis=tx("konto.push.hier_" + q["push"]), offen="push"))
        if methode == "GET":
            return antwort(200, konto_seite(k, reise_info))
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
            if a == "warteliste_freigeben" and konten.recht(k, "betreiber"):
                konten.freigeben(f.get("wer"))
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
            if a == "meldungen_gelesen":
                konten.gelesen_merken(k["id"], [m["id"] for m in rm.meldungen_des_kontos(k) if not m["gelesen"] and m["id"]])
                return weiter("/konto")
            if a == "alle_abmelden":
                konten.alle_abmelden(k["id"])
                return weiter("/anmelden", [cookie_loeschen()])
            if a in ("reise_loeschen_1", "reise_loeschen"):   # Bestätigung 1 und 2 (#381)
                reise = f.get("reise") or ""
                _loeschen_erlaubt(k, reise)
                if f.get("verstanden") != "ja":
                    return antwort(200, reise_loeschen_seite(k, reise, reise_info, meldung=tx("konto.fehler.haken_fehlt")))
                if a == "reise_loeschen_1":
                    return antwort(200, reise_loeschen_seite(k, reise, reise_info, schritt=2))
                titel = reise_titel(reise, reise_info)
                if not _gleicher_name(f.get("titel"), titel):
                    return antwort(200, reise_loeschen_seite(k, reise, reise_info, schritt=2,
                                                             meldung=tx("konto.fehler.reisename_falsch")))
                zeile = reise_loeschen(k, reise, reise_info)
                return antwort(200, konto_seite(k, reise_info, hinweis=tx(
                    "konto.reise_loeschen.vorgemerkt_hinweis", titel=titel,
                    frist=frist_text(zeile["frist"], sprache_der_seite(), meldungen_zone(k)))))
            if a == "reise_zurueckholen":
                reise = f.get("reise") or ""
                reise_zurueckholen(k, reise, reise_info)
                return antwort(200, konto_seite(k, reise_info, hinweis=tx(
                    "konto.reise_loeschen.zurueckgeholt_hinweis", titel=reise_titel(reise, reise_info))))
            if a == "loeschen" and f.get("sicher") == "ja":
                konten.loeschen(k["id"])
                return antwort(200, seite(tx("konto.seite.geloescht"), karte(
                    f"<h1>{esc(tx('konto.seite.geloescht'))}</h1><p>{esc(tx('konto.seite.geloescht_text'))}</p>"), fuss(recht=True)),
                    [cookie_loeschen()])
        except konten.KontoFehler as x:
            return antwort(200, konto_seite(k, reise_info, meldung=x.text(sprache_der_seite())))
        return antwort(400, konto_seite(k, reise_info, meldung=tx("konto.fehler.ging_nicht")))

    return antwort(404, seite(tx("konto.nicht_gefunden"), karte(f"<h1>{esc(tx('konto.nicht_gefunden'))}</h1>")))


def betreiber_melden(k, art="anfrage_reisen", text=None, teile=None):
    """Meldung an alle Betreiber (stehen in der Claude-App bei meine_reisen): die Bitte „Reisen anlegen“ des Kontos k
    oder, mit art, text und teile, etwas anderes (bestätigter Eintrag der Warteliste, #382). teile: für Mein Konto, in
    der Sprache jedes Betreibers (#407 Stufe C)."""
    with konten.closing(konten.db()) as v:
        namen = [z["name"] for z in v.execute("SELECT name, rechte FROM konten WHERE gesperrt = 0")
                 if "betreiber" in z["rechte"].split(",")]
    if namen:
        rm.meldung_anlegen(rm.ordner_neu(anlegen=True), namen, art, "reise", text or
                           texte.t(texte.VORGABE_REISE, "konto.betreiber.meldung", name=k["name"], email=k["email"]),
                           teile=teile or ([("konto.meldungen.text.anfrage_reisen", {"name": k["name"], "email": k["email"]})]
                                           if k else None))
