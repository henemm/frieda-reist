"""Infoseite „Was ist Frieda?“ (#436): die Startseite der Adresse für alle ohne Anmeldung, mit Grundprinzipien, erfundenen
Beispiel-Gesprächen, Bildern der Reiseseite aus den Beispielreisen und den ersten Schritten; Deutsch und Englisch (jede Sprache
der Software). Bilder unter /info/, erzeugt von engine/info/erzeugen.py."""
import html
import http.client
import shutil
import sys
import urllib.parse
from pathlib import Path

import pytest
from PIL import Image

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import anmeldung  # noqa: E402
import texte  # noqa: E402
from conftest import meldet, text  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402
from test_anmeldung import BASIS, IDA, abruf, anmelden, kopf, welt  # noqa: E402,F401

INFO = ENGINE / "info"


def test_startseite_ohne_anmeldung_ist_die_infoseite(welt):
    """Ohne Anmeldung zeigt / die Infoseite mit allem, was sie erklären soll; angemeldet führt / weiter zu Mein Konto (#41)."""
    u = welt()
    s, h, t = abruf(f"{u.kurl}/")
    assert s == 200 and kopf(h, "Cache-Control") == ["no-store"] and '<html lang="de"' in t
    assert meldet(t, "info.ueberschrift") and meldet(t, "info.lead")
    for p in anmeldung.INFO_PRINZIPIEN:
        assert meldet(t, f"info.prinzip.{p}.titel") and meldet(t, f"info.prinzip.{p}.text"), p
    for name, folge in anmeldung.INFO_GESPRAECHE:      # jedes Gespräch vollständig, mit den Sprechern
        assert meldet(t, f"info.gespraech.{name}.titel"), name
        for n, r in enumerate(folge, 1):
            assert meldet(t, f"info.gespraech.{name}.{n}") and f'<p class="blase {r}">' in t, (name, n)
    assert t.count('<p class="blase claude">') == sum(f.count("claude") for _, f in anmeldung.INFO_GESPRAECHE)
    for name in anmeldung.INFO_BILDER:                 # jedes Bild mit Beschreibung, in der Sprache der Seite
        assert f'src="/info/{name}-de.webp"' in t and meldet(t, f"info.bild.{name}"), name
    # erste Schritte mit der Adresse des Konnektors dieser Instanz zum Kopieren; Anmelden und Warteliste als Wege
    assert meldet(t, "info.schritte.titel") and f'value="{BASIS}/mcp"' in t and meldet(t, "konto.verbinden.bezahlt")
    assert 'href="/anmelden"' in t and 'href="/warteliste"' in t and 'href="/datenschutz"' in t
    s, h, _ = abruf(f"{u.kurl}/", cookie=anmelden(u, IDA, name="Ida")[0])
    assert s == 303 and kopf(h, "Location") == ["/konto"]


def test_infoseite_in_jeder_sprache(welt):
    """Sprache nach dem Browser, umschaltbar mit ?sprache= (der Umschalter nennt jede Sprache der Software); ein
    unbekanntes Kürzel ändert nichts. Die Bilder kommen in der Sprache der Seite."""
    u = welt()
    for sp in texte.SPRACHEN:
        t = abruf(f"{u.kurl}/?sprache={sp}")[2]
        assert f'<html lang="{sp}"' in t and html.escape(text("info.ueberschrift", sp), quote=True) in t, sp
        assert f'<a href="/?sprache={sp}" lang="{sp}" hreflang="{sp}" aria-current="page">' in t
        bild = f"reise-{sp}.webp" if (INFO / f"reise-{sp}.webp").exists() else f"reise-{texte.VORGABE_REISE}.webp"
        assert f'src="/info/{bild}"' in t, sp
        assert t.count('<a href="/?sprache=') == len(texte.SPRACHEN)
    andere = next(sp for sp in texte.SPRACHEN if sp != "de")
    assert f'<html lang="{andere}"' in abruf(f"{u.kurl}/", kopf={"Accept-Language": andere})[2]
    assert '<html lang="de"' in abruf(f"{u.kurl}/?sprache=zz")[2]


def test_anmeldeseite_fuehrt_zur_infoseite(welt):
    u = welt()
    t = abruf(f"{u.kurl}/anmelden")[2]
    assert f'<a href="/">{html.escape(text("info.link", "de"))}</a>' in t


def test_bilder_der_infoseite_ausgeliefert(welt):
    """/info/<name>.webp aus engine/info/, mit Zwischenspeicher; nichts sonst aus dem Ordner und kein Weg hinaus."""
    u = welt()
    t = urllib.parse.urlsplit(u.kurl)

    def hol(pfad, methode="GET"):
        c = http.client.HTTPConnection(t.hostname, t.port, timeout=10)
        c.request(methode, pfad)
        r = c.getresponse()
        return r.status, r.getheader("Content-Type"), r.getheader("Cache-Control"), r.read()

    s, art, cache, body = hol("/info/tag-de.webp")
    assert (s, art, cache) == (200, "image/webp", "public, max-age=86400") and body[8:12] == b"WEBP"
    for pfad in ("/info/erzeugen.py", "/info/aufnehmen.mjs", "/info/fehlt-de.webp", "/info/../konten.py", "/info/%2e%2e/konten.py",
                 "/info/Reise-de.webp", "/info/", "/info"):
        assert hol(pfad)[0] == 404, pfad
    assert hol("/info/tag-de.webp", "POST")[0] == 404


def test_bilder_vollstaendig_und_gleich_gross():
    """Je Bild der Infoseite und Sprache der Software eine Datei, alle so groß, wie die Seite sie einplant; das Skript zum
    Erzeugen kennt dieselben Bilder."""
    from info import erzeugen
    assert list(erzeugen.BILDER) == list(anmeldung.INFO_BILDER)
    for sp in texte.SPRACHEN:
        if sp not in texte.ERSTE:      # die Pseudo-Sprache der Tests hat keine Bilder; die Seite nimmt dann die der Vorgabe
            continue
        for name in anmeldung.INFO_BILDER:
            with Image.open(INFO / f"{name}-{sp}.webp") as b:
                assert (b.format, b.size) == ("WEBP", (erzeugen.BREITE, erzeugen.HOEHE)), (name, sp)
    assert f"aspect-ratio:{erzeugen.BREITE}/{erzeugen.HOEHE}" in anmeldung.CSS


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
def test_bilder_lassen_sich_erzeugen(tmp_path):
    """Das Skript baut die Beispielreisen, nimmt jede Ansicht ohne Skriptfehler auf und schreibt die Bilder. Keine Ansicht
    zeigt „null“ (die Packliste ohne Summen tat das, gefunden beim Aufnehmen)."""
    from info import erzeugen
    sp = texte.VORGABE_REISE
    bericht = erzeugen.erzeugen(tmp_path, sprachen=(sp,))[sp]
    assert bericht["fehler"] == []
    for name in anmeldung.INFO_BILDER:
        assert "null" not in bericht["texte"][name].split(), name
        with Image.open(tmp_path / f"{name}-{sp}.webp") as b:
            assert b.size == (erzeugen.BREITE, erzeugen.HOEHE)
    assert text("seite.packliste.titel", sp) in bericht["texte"]["packliste"]
