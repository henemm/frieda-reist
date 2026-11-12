"""Erzeugt docs/artifacts/meldungen-konto-407/mockup.html mit dem echten CSS der Kontoseiten."""
import re, sys
from pathlib import Path
repo = Path(sys.argv[1])
css = re.search(r'^CSS = """(.*?)"""', (repo / "engine/anmeldung.py").read_text(encoding="utf-8"), re.S | re.M).group(1)
# Schriften liegen nur auf dem Server; Tokens auf die Rahmen statt :root, damit hell und dunkel nebeneinander gehen
css = re.sub(r"@font-face\{.*?\}\s*", "", css, flags=re.S)
hell = re.search(r":root\{(.*?)\}", css, re.S).group(1)
dunkel = re.search(r"prefers-color-scheme:dark\)\{:root\{(.*?)\}\}", css, re.S).group(1)
css = re.sub(r"@media \(prefers-color-scheme:dark\)\{:root\{.*?\}\}", "", css, flags=re.S)
css = css.replace(":root{" + hell + "}", "")
css = css.replace("body{margin:0;background:var(--bg);color:var(--fg);", ".rahmen{background:var(--bg);color:var(--fg);")
neu = """
/* --- neu nach Spec meldungen-konto-407 --- */
.marke.warm{color:var(--warn);background:var(--warnbg)}
.zahl{font-size:.8125rem;font-weight:700;color:var(--card);background:var(--acc);border-radius:999px;padding:.05rem .55rem;margin-left:.4rem;vertical-align:.15em}
.abschnitt-kopf{display:flex;align-items:baseline;justify-content:space-between;margin:0 .25rem}
.abschnitt-kopf h2{margin:0}.abschnitt-kopf button.link{min-height:auto;padding:.2rem 0;font-size:.9375rem}
.meldung{align-items:flex-start}.meldung::after{align-self:center}
.neu-punkt{flex:none;width:.5rem;height:.5rem;border-radius:50%;background:var(--acc);margin-top:.55rem}
.ohne-punkt{flex:none;width:.5rem}
.meldung-kopf{display:flex;align-items:center;gap:.4rem;min-width:0;font-size:.8125rem;color:var(--mut)}
.meldung-kopf .marke{font-size:.75rem;padding:.05rem .5rem;flex:none}
.meldung-kopf .reise{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.meldung-kopf .zeit{flex:none}
.meldung .meldungstext{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.meldung.ungelesen .meldungstext{font-weight:600}
.leer{padding:.9rem 1rem;color:var(--mut);font-size:.9375rem}
details.gelesen>summary{color:var(--mut);font-weight:600}
details.gelesen>.liste-innen>*{border-top:1px solid var(--line)}
"""
seite = """
.buehne{display:flex;flex-wrap:wrap;gap:2rem;padding:2rem;background:#d9dbd4;font:1rem/1.4 "Source Sans 3",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.buehne>figure{margin:0;display:flex;flex-direction:column;gap:.6rem}
.buehne figcaption{font-weight:700;color:#1d2420;max-width:390px}.buehne figcaption span{display:block;font-weight:400;font-size:.875rem;color:#454c47}
.rahmen{width:390px;border-radius:28px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.18);font:1.0625rem/1.45 "Source Sans 3",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.rahmen main{max-width:none}
.rahmen.hell{""" + hell + """}
.rahmen.dunkel{""" + dunkel + """}
"""

def kopf(name, mail):
    return (f'<header class="kopf breit"><span><img src="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 28 28%22%3E%3Crect width=%2228%22 height=%2228%22 rx=%227%22 fill=%22%232f7a57%22/%3E%3C/svg%3E" alt="">Frieda</span>'
            f'<form><button class="link" type="button">Abmelden</button></form></header>'
            f'<div><h1 style="font-size:1.875rem">Hallo {name}</h1><p class="hinweis" style="margin:.1rem 0 0">{mail}</p></div>')

def ist_zeile(unter, text, link=False):
    inhalt = f'<span class="was"><span class="klein">{unter}</span><span class="meldungstext">{text}</span></span>'
    return f'<a class="zeile" href="#">{inhalt}</a>' if link else f'<div class="zeile ohne-link">{inhalt}</div>'

def zeile(marke, warm, reise, zeit, text, neu=True):
    m = f'<span class="marke{" warm" if warm else " leise"}">{marke}</span>'
    r = f'<span class="reise">{reise}</span><span>·</span>' if reise else ""
    p = '<span class="neu-punkt" role="img" aria-label="neu"></span>' if neu else '<span class="ohne-punkt"></span>'
    return (f'<a class="zeile meldung{" ungelesen" if neu else ""}" href="#">{p}<span class="was">'
            f'<span class="meldung-kopf">{m}{r}<span class="zeit">{zeit}</span></span>'
            f'<span class="meldungstext">{text}</span></span></a>')

MALERWEG = "Beispielreise – Malerweg in vier Tagen"
HERBST = "Beispiel – Herbstwanderung (erfunden)"

def meine_reisen():
    return ('<div class="abschnitt"><h2>Meine Reisen</h2><div class="liste">'
            f'<a class="zeile" href="#"><span class="was"><span class="titel">{MALERWEG}</span><span class="marke">Du organisierst</span></span></a>'
            f'<a class="zeile" href="#"><span class="was"><span class="titel">{HERBST}</span><span class="marke">Du organisierst</span></span></a>'
            '</div></div>')

ist = (kopf("Ida", "ida@example.org")
       + '<div class="abschnitt" id="meldungen"><h2>Meldungen an dich</h2><div class="liste">'
       + ist_zeile("3.11.", f"Deine neue Reise „{HERBST}“ ist angelegt (Status Idee) und steht in meine_reisen. Seite: https://frieda.example.org/beispiel-herbstwanderung-erfunden-2027-000000000000000000000000/ · Einladung per Mail an 2 Personen verschickt.")
       + ist_zeile("3.11.", f"Deine neue Reise „Testreise Karten (erfunden)“ ist angelegt (Status Idee) und steht in meine_reisen. Seite: https://frieda.example.org/testreise-karten-erfunden-2027-000000000000000000000000/")
       + ist_zeile("2.11.", "Deine neue Reise „Testreise Abnahme (erfunden)“ ist angelegt (Status Idee) und steht in meine_reisen. Seite: https://alt.example.org/testreise-abnahme-erfunden-2027-000000000000000000000000/")
       + ist_zeile(f"1.11. · {MALERWEG}", "Frist morgen: Anzahlung zur Buchung Hotel Elbblick (Frist 2.11.).", True)
       + ist_zeile(f"1.11. · {MALERWEG}", "Waldschänke Hohnstein, Öffnungszeiten: zuletzt geprüft 2.9. (vor 60 Tagen). Bitte im Gespräch nachschlagen und mit Prüfdatum und Quelle eintragen.", True)
       + ist_zeile(f"1.11. · {MALERWEG}", "Pension Rathen, Preis je Nacht: noch nie geprüft. Bitte im Gespräch nachschlagen und mit Prüfdatum und Quelle eintragen.", True)
       + "</div></div>" + meine_reisen())

def soll_neu():
    return (kopf("Ida", "ida@example.org")
            + '<div class="abschnitt" id="meldungen"><div class="abschnitt-kopf"><h2>Meldungen an dich<span class="zahl">4 neu</span></h2>'
              '<button class="link" type="button">Alle gelesen</button></div><div class="liste">'
            + zeile("Konflikt", True, MALERWEG, "heute 9:14", "Karl hat „Pension Rathen“ gewählt, du hattest sie verworfen. Zu klären in einer offenen Frage.")
            + zeile("Frist", True, MALERWEG, "gestern", "Frist morgen: Anzahlung zur Buchung Hotel Elbblick.")
            + zeile("Prüfen", True, MALERWEG, "gestern", "7 Angaben zu prüfen, darunter Öffnungszeiten der Waldschänke Hohnstein und der Preis der Pension Rathen.")
            + zeile("Neue Reise", False, HERBST, "3.11.", "Deine neue Reise ist angelegt (Status Idee). 2 Einladungen per Mail verschickt.")
            + '<details class="gelesen"><summary class="zeile">Gelesen (2)</summary></details>'
            + "</div></div>" + meine_reisen())

def soll_gelesen():
    return (kopf("Ida", "ida@example.org")
            + '<div class="abschnitt" id="meldungen"><div class="abschnitt-kopf"><h2>Meldungen an dich</h2></div><div class="liste">'
            + '<div class="leer">Keine neuen Meldungen.</div>'
            + '<details class="gelesen" open><summary class="zeile">Gelesen (6)</summary><div class="liste-innen">'
            + zeile("Konflikt", True, MALERWEG, "heute 9:14", "Karl hat „Pension Rathen“ gewählt, du hattest sie verworfen. Zu klären in einer offenen Frage.", False)
            + zeile("Frist", True, MALERWEG, "gestern", "Frist morgen: Anzahlung zur Buchung Hotel Elbblick.", False)
            + zeile("Prüfen", True, MALERWEG, "gestern", "7 Angaben zu prüfen, darunter Öffnungszeiten der Waldschänke Hohnstein und der Preis der Pension Rathen.", False)
            + zeile("Neue Reise", False, HERBST, "3.11.", "Deine neue Reise ist angelegt (Status Idee). 2 Einladungen per Mail verschickt.", False)
            + zeile("Neue Reise", False, "Testreise Karten (erfunden)", "3.11.", "Deine neue Reise ist angelegt (Status Idee).", False)
            + zeile("Neue Reise", False, "Testreise Abnahme (erfunden)", "2.11.", "Deine neue Reise ist angelegt (Status Idee).", False)
            + "</div></details></div></div>" + meine_reisen())

def soll_viele():
    zeilen = [zeile("Freischalten", True, "", "heute 8:02", "Tom (tom@example.org) bittet darum, Reisen anlegen zu dürfen."),
              zeile("Hinweis", True, MALERWEG, "heute 7:30", "Die Seite kann seit gestern 23:10 Uhr nicht veröffentlicht werden. Der Betrieb ist informiert."),
              zeile("Status", True, MALERWEG, "gestern", "Die Reise hat am 13.5. begonnen, der Status steht noch auf fest. Soll er auf unterwegs wechseln?"),
              zeile("Frist", True, MALERWEG, "gestern", "Kostenlos stornieren geht nur noch bis 15.5.: Buchung Hotel Elbblick."),
              zeile("Frist", True, MALERWEG, "11.5.", "Überfällig seit 2 Tagen: Fahrkarten kaufen (Frist 9.5.).")]
    return (kopf("Ida", "ida@example.org")
            + '<div class="abschnitt" id="meldungen"><div class="abschnitt-kopf"><h2>Meldungen an dich<span class="zahl">9 neu</span></h2>'
              '<button class="link" type="button">Alle gelesen</button></div><div class="liste">'
            + "".join(zeilen)
            + '<details class="gelesen"><summary class="zeile">Alle 9 neuen zeigen</summary></details>'
            + '<details class="gelesen"><summary class="zeile">Gelesen (3)</summary></details>'
            + "</div></div>" + meine_reisen())

rahmen = [
    ("ist", "hell", "Heute (nachgestellt)", "Neue Reisen ohne Link, Adressen als Rohtext, „meine_reisen“ auf der Webseite, alles gleich laut, Prüfmeldungen einzeln.", ist),
    ("soll-neu", "hell", "Soll: neue Meldungen", "Punkt und Zahlmarke für Neues, Marke je Art, Zeit relativ, jede Zeile führt an die Stelle, Prüfungen gebündelt, Gelesenes zugeklappt.", soll_neu()),
    ("soll-gelesen", "hell", "Soll: alles gelesen", "„Keine neuen Meldungen“, Gelesenes aufgeklappt, ohne Punkt und in normalem Gewicht.", soll_gelesen()),
    ("soll-viele", "hell", "Soll: viele Meldungen", "Höchstens fünf neue, dann „Alle 9 neuen zeigen“; Freischalten (nur Betreiber) ohne Reise.", soll_viele()),
    ("soll-dunkel", "dunkel", "Soll: dunkel", "Dieselbe Liste mit den dunklen Tokens; die warme Marke behält ihren Kontrast.", soll_neu()),
]
figs = "".join(f'<figure id="{i}"><figcaption>{t}<span>{u}</span></figcaption><div class="rahmen {farbe}"><main>{inhalt}</main></div></figure>'
               for i, farbe, t, u, inhalt in rahmen)
html = ('<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Mockup: Meldungen an dich (#407)</title>'
        '<!-- Erzeugt aus dem CSS von engine/anmeldung.py (Stand 8.11.2026) plus den neuen Regeln der Spec '
        'docs/specs/oberflaeche/meldungen-konto-407.md. Alle Daten erfunden. -->'
        f'<style>{css}{neu}{seite}</style></head><body style="margin:0"><div class="buehne">{figs}</div></body></html>')
ziel = repo / "docs/artifacts/meldungen-konto-407"
ziel.mkdir(parents=True, exist_ok=True)
(ziel / "mockup.html").write_text(html, encoding="utf-8")
print("ok", len(html))
