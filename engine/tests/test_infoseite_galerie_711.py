"""Galerie der Erklärseiten unter /info/ (#711): wischbare Bildreihe der Infoseite, Großansicht PhotoSwipe mit Unterschrift
im eigenen Streifen, in jeder Sprache der Software. Die Spec: docs/specs/oberflaeche/funktionsseiten-711.md."""
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
from conftest import text  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402
from test_anmeldung import abruf, welt  # noqa: E402,F401

HIER = Path(__file__).resolve().parent


def e(schluessel, sp="de", **w):
    return html.escape(text(schluessel, sp, **w), quote=True)


def hol(u, pfad, methode="GET"):
    t = urllib.parse.urlsplit(u.kurl)
    c = http.client.HTTPConnection(t.hostname, t.port, timeout=10)
    c.request(methode, pfad)
    r = c.getresponse()
    return r.status, r.getheader("Content-Type") or "", r.getheader("Cache-Control") or "", r.read()


def test_infoseite_hat_die_bildreihe_und_das_skript(welt):
    """AC-1: Bildreihe mit Name der Galerie und Texten für das Skript, je Bild die Maße der großen Fassung, Hinweis zum Wischen;
    das Skript liegt unter /info/, kein Inline-Skript."""
    u = welt()
    for sp in texte.SPRACHEN:
        t = abruf(f"{u.kurl}/?sprache={sp}")[2]
        assert '<div class="bilder reihe" data-galerie="' in t, sp
        assert '<script src="/info/galerie.js" defer></script>' in t and "<script>" not in t, sp
        assert t.count('data-breite="585" data-hoehe="1050"') == len(anmeldung.INFO_BILDER), sp
        assert f'<p class="wisch">{e("info.galerie.wischen", sp)}</p>' in t, sp
        daten = json.loads(html.unescape(t.split('data-texte="', 1)[1].split('"', 1)[0]))
        assert daten["zaehler"] == text("info.galerie.zaehler", sp) and daten["schliessen"] == text("seite.bild.schliessen", sp)
        assert ".pswp" in t and ".unterschrift-streifen" in t, sp       # Stile von PhotoSwipe und Streifen stehen in der Seite


def test_skripte_unter_info_ausgeliefert(welt):
    """AC-2: Skript der Galerie und PhotoSwipe-Modul als JavaScript; alles andere unter /info/ bleibt 404."""
    u = welt()
    for pfad, quelle in (("/info/galerie.js", ENGINE / "app" / "galerie.js"),
                         ("/info/photoswipe-5.4.4.esm.min.js", ENGINE / "vendor" / "photoswipe-5.4.4.esm.min.js")):
        s, art, cache, body = hol(u, pfad)
        assert (s, art) == (200, "text/javascript; charset=utf-8") and body == quelle.read_bytes(), pfad
        assert cache == "no-cache", pfad
    for pfad in ("/info/photoswipe-5.4.4.css", "/info/konto.js", "/info/galerie.mjs", "/info/../app/galerie.js",
                 "/info/vendor/leaflet-1.9.4.js", "/info/funktionen/galerie.js"):
        assert hol(u, pfad)[0] == 404, pfad


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("sp", list(texte.ERSTE))
@pytest.mark.parametrize("pfad", ["/info/", "/info/funktionen/reiseseite/"])
def test_galerie_im_browser(welt, sp, pfad):
    """AC-3, AC-4, AC-5: Reihe am Handy wischbar mit Hinweis, am Rechner in einer Zeile; die Großansicht zeigt das angetippte
    Bild, die Unterschrift im undurchsichtigen Streifen unter dem Bild und den Zähler, blättert und schließt; Blättern sofort
    beim Öffnen (#706) wirft keinen Fehler, der Streifen passt danach zum gezeigten Bild."""
    u = welt()
    r = subprocess.run(["node", str(HIER / "info_galerie_711.mjs"), str(PLAYWRIGHT), f"{u.kurl}{pfad}?sprache={sp}",
                        text("info.galerie.zaehler", sp)], capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-2000:]
    m = json.loads(r.stdout.strip().splitlines()[-1])
    assert m["fehler"] == [], m["fehler"]
    handy, rechner = m["390"], m["1280"]
    assert handy["scroll"] and 0.55 <= handy["bild"] / handy["reihe"] <= 0.7 and handy["hinweis"], handy
    assert handy["symbol"], handy
    assert not rechner["hinweis"] and len(set(rechner["oben"][:4])) == 1 and not rechner["scroll"], rechner
    assert not handy["ueber"] and not rechner["ueber"]
    offen, weiter = handy["offen"], handy["weiter"]
    assert offen["zahl"] == handy["erwartet"]["offen"] and offen["bildAlt"] in offen["text"], offen
    assert offen["grund"] in ("rgb(21, 24, 22)",) and offen["bildUnten"] <= offen["oben"] + 1, offen
    assert weiter["zahl"] == handy["erwartet"]["weiter"] and weiter["bildAlt"] in weiter["text"], weiter
    assert handy["zu"]
    schnell = handy["schnell"]
    assert schnell and schnell["bildAlt"] and schnell["bildAlt"] in schnell["text"], json.dumps(schnell)
    taste = handy["taste"]
    assert taste and taste["bildAlt"] and taste["bildAlt"] in taste["text"], json.dumps(taste)
    for n, b in enumerate(handy["schmal"], 1):     # 320 px: der Streifen wächst mit, das Bild endet immer darüber
        assert b["zahl"] == text("info.galerie.zaehler", sp, galerie=handy["galerie"], i=n, n=handy["anzahl"]), b
        assert b["bildUnten"] is not None and b["bildUnten"] <= b["oben"] + 1, b
    v = handy["verkleinert"]                       # bei offener Großansicht schmaler geworden
    assert v and v["bildUnten"] is not None and v["bildUnten"] <= v["oben"] + 1, v
