"""Funktionsseiten unter /info/ (#711): Karte „Was Frieda alles kann“ auf der Infoseite, Übersicht „Alle Funktionen“ unter
/info/funktionen/ und ihre Wege, in jeder Sprache der Software, an Handy und Rechner. Die Spec:
docs/specs/oberflaeche/funktionsseiten-711.md."""
import html
import http.client
import json
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import anmeldung  # noqa: E402
import texte  # noqa: E402
from conftest import meldet, text  # noqa: E402
from PIL import Image  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402
from test_anmeldung import IDA, abruf, anmelden, kopf, welt  # noqa: E402,F401

INFO = ENGINE / "info"
UEBERSICHT = "/info/funktionen/"


def e(schluessel, sp="de", **w):
    return html.escape(text(schluessel, sp, **w), quote=True)


def hol(u, pfad, methode="GET"):
    t = urllib.parse.urlsplit(u.kurl)
    c = http.client.HTTPConnection(t.hostname, t.port, timeout=10)
    c.request(methode, pfad)
    r = c.getresponse()
    return r.status, r.getheader("Content-Type") or "", r.getheader("Cache-Control") or "", r.read()




def test_infoseite_fuehrt_zu_allen_funktionen(welt):
    """AC-6: Die Karte „Was Frieda alles kann“ mit Knopf zur Übersicht ersetzt den Link auf GitHub; der Quellcode bleibt."""
    import instanz
    u = welt()
    for sp in texte.SPRACHEN:
        t = abruf(f"{u.kurl}/info/?sprache={sp}")[2]
        assert '<section class="karte einstieg">' in t and meldet(t, "info.einstieg.titel", sp) and meldet(t, "info.einstieg.text", sp)
        assert f'<a class="knopf" href="{UEBERSICHT}">{e("info.einstieg.knopf", sp)}</a>' in t, sp
        assert "docs/funktionen" not in t and "README.en.md" not in t, sp
        assert f'<a href="{instanz.QUELLCODE}" target="_blank" rel="noopener">{e("info.quellcode", sp)}</a>' in t, sp


def test_uebersicht_alle_funktionen(welt):
    """AC-7: drei Orte, drei Gruppen mit je einer Zeile je Bereich; nur Bereiche mit Unterseite sind Links, die anderen tragen
    „Seite folgt“; „Wer darf was“ mit den Rollen; Sprachumschalter auf derselben Adresse."""
    u = welt()
    assert len(anmeldung.INFO_ORTE) == 3 and len(anmeldung.INFO_GRUPPEN) == 3
    for sp in texte.SPRACHEN:
        s, h, t = abruf(f"{u.kurl}{UEBERSICHT}?sprache={sp}")
        assert s == 200 and kopf(h, "Cache-Control") == ["no-store"] and f'<html lang="{sp}"' in t
        assert f"<title>{e('info.funktionen.titel', sp)} – Frieda</title>" in t
        assert f'<a class="zurueck" href="/info/">‹ {e("info.titel", sp)}</a>' in t
        assert meldet(t, "info.funktionen.lead", sp) and meldet(t, "info.orte.titel", sp)
        for o in anmeldung.INFO_ORTE:
            assert meldet(t, f"info.ort.{o}.titel", sp) and meldet(t, f"info.ort.{o}.text", sp), (sp, o)
        bereiche = [b for _, liste in anmeldung.INFO_GRUPPEN for b in liste]
        for g, _ in anmeldung.INFO_GRUPPEN:
            assert f'<p class="gruppe">{e(f"info.gruppe.{g}", sp)}</p>' in t, (sp, g)
        for b in bereiche:
            assert f'id="{b}"' in t and meldet(t, f"info.bereich.{b}.titel", sp) and meldet(t, f"info.bereich.{b}.satz", sp), (sp, b)
            assert (f'href="{UEBERSICHT}{b}/"' in t) == (b in anmeldung.INFO_UNTERSEITEN), (sp, b)
        ohne = len([b for b in bereiche if b not in anmeldung.INFO_UNTERSEITEN])
        assert t.count(f'<span class="marke leise">{e("info.funktionen.folgt", sp)}</span>') == ohne, sp
        assert meldet(t, "info.rollen.titel", sp)
        for r in anmeldung.INFO_ROLLEN:
            assert meldet(t, f"info.rolle.{r}.titel", sp) and meldet(t, f"info.rolle.{r}.text", sp), (sp, r)
        assert f'<a href="{UEBERSICHT}?sprache={sp}" lang="{sp}" hreflang="{sp}" aria-current="page">' in t



def nummern(praefix, sp="de"):
    katalog, n = texte.sprache(sp).TEXTE, 0
    while f"{praefix}.{n + 1}" in katalog or f"{praefix}.{n + 1}.titel" in katalog:
        n += 1
    return n


@pytest.mark.parametrize("name", list(anmeldung.INFO_UNTERSEITEN))
def test_unterseite(welt, name):
    """Jede Unterseite (Muster: Reiseseite) mit allen Abschnitten aus dem Katalog, Bildern in der Sprache der Seite und „Siehe
    auch“ ohne kaputte Links; eine neue Unterseite braucht keinen eigenen Test."""
    u = welt()
    seite = anmeldung.INFO_UNTERSEITEN[name]
    p = f"info.bereich.{name}"
    assert seite["bilder"] and nummern(f"{p}.tun") and nummern(f"{p}.wie") and nummern(f"{p}.rolle") and nummern(f"{p}.gut")
    for sp in texte.SPRACHEN:
        s, _, t = abruf(f"{u.kurl}{UEBERSICHT}{name}/?sprache={sp}")
        assert s == 200 and f"<title>{e(f'{p}.titel', sp)} – Frieda</title>" in t, sp
        assert f'<a class="zurueck" href="{UEBERSICHT}">‹ {e("info.funktionen.titel", sp)}</a>' in t
        assert meldet(t, f"{p}.lead", sp) and meldet(t, f"{p}.wo", sp) and meldet(t, f"{p}.wer", sp)
        assert '<dl class="kurz">' in t and meldet(t, "info.unterseite.wo", sp) and meldet(t, "info.unterseite.wer", sp)
        bild_sp = sp if sp in texte.ERSTE else texte.VORGABE_REISE
        assert '<div class="bilder reihe" data-galerie="' in t
        for b in seite["bilder"]:
            assert f'href="/info/{b}-{bild_sp}.webp"' in t and meldet(t, f"{p}.bild.{b}", sp), (sp, b)
        for n in range(1, nummern(f"{p}.tun") + 1):
            assert meldet(t, f"{p}.tun.{n}", sp), (sp, n)
        assert t.count('<details><summary class="zeile">') == nummern(f"{p}.wie")
        for n in range(1, nummern(f"{p}.wie") + 1):
            assert meldet(t, f"{p}.wie.{n}.titel", sp), (sp, n)
            for absatz in text(f"{p}.wie.{n}.text", sp).split("\n\n"):
                assert f"<p>{html.escape(absatz, quote=True)}</p>" in t, (sp, n)
        for n, r in enumerate(seite["gespraech"], 1):
            assert f'<p class="blase {r}">' in t and meldet(t, f"{p}.gespraech.{n}", sp), (sp, n)
        for n in range(1, nummern(f"{p}.rolle") + 1):
            assert meldet(t, f"{p}.rolle.{n}.titel", sp) and meldet(t, f"{p}.rolle.{n}.text", sp)
        for n in range(1, nummern(f"{p}.gut") + 1):
            assert meldet(t, f"{p}.gut.{n}", sp)
        for ziel in seite["siehe"]:
            href = f"{UEBERSICHT}{ziel}/" if ziel in anmeldung.INFO_UNTERSEITEN else f"{UEBERSICHT}#{ziel}"
            assert f'<a href="{href}">{e(f"info.bereich.{ziel}.titel", sp)}</a>' in t, (sp, ziel)
        for titel in ("bilder", "tun", "wie", "gespraech", "rollen", "gut", "siehe"):
            assert meldet(t, f"info.unterseite.{titel}", sp), (sp, titel)


def test_texte_und_bilder_jeder_unterseite():
    """AC-10: jede Unterseite hat ihre Texte in jeder Sprache; jedes Bild gibt es für Deutsch und Englisch in den Maßen von
    erzeugen, und das Skript zum Erzeugen kennt alle Bilder."""
    from info import erzeugen
    alle = set(anmeldung.INFO_BILDER) | {b for s in anmeldung.INFO_UNTERSEITEN.values() for b in s["bilder"]}
    assert set(erzeugen.BILDER) == alle == erzeugen.alle_bilder()
    for name, seite in anmeldung.INFO_UNTERSEITEN.items():
        assert {"bilder", "gespraech", "siehe"} <= set(seite), name
        for ziel in seite["siehe"]:
            assert any(ziel in liste for _, liste in anmeldung.INFO_GRUPPEN), (name, ziel)
        for sp in texte.SPRACHEN:
            katalog = texte.sprache(sp).TEXTE
            for k in ("titel", "lead", "wo", "wer", "gespraech.einleitung", "gespraech.person"):
                assert f"info.bereich.{name}.{k}" in katalog, (sp, name, k)
            for b in seite["bilder"]:
                assert f"info.bereich.{name}.bild.{b}" in katalog, (sp, name, b)
            assert all(f"info.bereich.{name}.gespraech.{n}" in katalog for n in range(1, len(seite["gespraech"]) + 1))
    for sp in texte.ERSTE:
        for b in alle:
            with Image.open(INFO / f"{b}-{sp}.webp") as bild:
                assert (bild.format, bild.size) == ("WEBP", (erzeugen.BREITE, erzeugen.HOEHE)), (b, sp)


def test_wege_der_funktionsseiten(welt):
    """Ohne Schrägstrich weiter, ein Bereich ohne Unterseite gibt 404, POST führt ohne Wirkung zurück, HEAD geht; angemeldet
    Mein Konto im Kopf."""
    u = welt()
    for alt, neu in (("/info/funktionen", UEBERSICHT), ("/info/funktionen?sprache=en", f"{UEBERSICHT}?sprache=en")):
        s, h, _ = abruf(f"{u.kurl}{alt}")
        assert s == 303 and kopf(h, "Location") == [neu], alt
    ohne = next((b for _, liste in anmeldung.INFO_GRUPPEN for b in liste if b not in anmeldung.INFO_UNTERSEITEN), "gibtsnicht")
    assert "reiseseite" in anmeldung.INFO_UNTERSEITEN
    for pfad in (f"{UEBERSICHT}gibtsnicht/", f"/info/funktionen/{ohne}", f"{UEBERSICHT}{ohne}/", f"{UEBERSICHT}reiseseite/mehr/", f"{UEBERSICHT}Karte/",
                 "/info/funktionen/galerie.js", "/info/funktionenx/"):
        assert abruf(f"{u.kurl}{pfad}")[0] == 404, pfad
    s, h, _ = abruf(f"{u.kurl}/info/funktionen/reiseseite")
    assert s == 303 and kopf(h, "Location") == [f"{UEBERSICHT}reiseseite/"]
    for pfad in (UEBERSICHT, f"{UEBERSICHT}reiseseite/"):
        s, h, _ = abruf(f"{u.kurl}{pfad}", "POST", {})
        assert s == 303 and kopf(h, "Location") == [pfad], pfad
        assert hol(u, pfad, "HEAD")[0] == 200, pfad
    ida = anmelden(u, IDA, name="Ida")[0]
    for pfad in (UEBERSICHT, f"{UEBERSICHT}reiseseite/"):
        t = abruf(f"{u.kurl}{pfad}", cookie=ida)[2]
        assert f'<a class="kopf-link" href="/konto">{e("info.mein_konto")}</a>' in t and 'href="/anmelden"' not in t, pfad


MASSE = r"""
const pw = await import(process.argv[1]);
const url = process.argv[2];
const b = await pw.chromium.launch();
const aus = {fehler: []};
for (const breite of [390, 1280]) {
  const c = await b.newContext({viewport: {width: breite, height: 900}});
  const p = await c.newPage();
  p.on("pageerror", x => aus.fehler.push(String(x)));
  await p.goto(url);
  aus[breite] = await p.evaluate(() => ({ueber: document.documentElement.scrollWidth > window.innerWidth,
    zeilen: [...document.querySelectorAll(".liste .zeile")].map(z => z.getBoundingClientRect().height),
    orte: new Set([...document.querySelectorAll(".prinzipien .karte")].map(k => Math.round(k.getBoundingClientRect().top))).size}));
  await c.close();
}
await b.close();
console.log(JSON.stringify(aus));
"""


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("sp", list(texte.ERSTE))
def test_uebersicht_an_handy_und_rechner(welt, sp):
    """Am Handy stehen die drei Orte untereinander, am Rechner nebeneinander; jede Zeile ist hoch genug zum Tippen; nirgends
    seitlicher Überlauf, keine Skriptfehler."""
    u = welt()
    r = subprocess.run(["node", "--input-type=module", "-e", MASSE, str(PLAYWRIGHT), f"{u.kurl}{UEBERSICHT}?sprache={sp}"],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    m = json.loads(r.stdout.strip().splitlines()[-1])
    assert m["fehler"] == [] and not m["390"]["ueber"] and not m["1280"]["ueber"], m
    assert m["390"]["orte"] == 3 and m["1280"]["orte"] == 1, m
    assert min(m["390"]["zeilen"]) >= 44 and min(m["1280"]["zeilen"]) >= 44, m


def test_unterseiten_planen():
    """#711, Etappe 2: Die Gruppe „Planen und entscheiden“ bekommt ihre Unterseiten; jede prüft test_unterseite."""
    assert {"wahrheit", "gespraech", "alternativen", "buchungen", "gespraeche", "lebenslauf"} <= set(anmeldung.INFO_UNTERSEITEN)


def test_unterseiten_unterwegs():
    """#711, Etappe 2: Die Gruppe „Unterwegs und gemeinsam“ bekommt ihre Unterseiten; jede prüft test_unterseite."""
    assert {"karte", "packliste", "zusammenarbeit", "bilder"} <= set(anmeldung.INFO_UNTERSEITEN)
