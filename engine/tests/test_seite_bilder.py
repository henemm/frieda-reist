"""Seitentests für Bilder Stufe 1, Paket P2 (#455, Spec docs/specs/oberflaeche/bilder-455-p2.md, AC-1 bis AC-4) in Chromium
und WebKit: gebaute Beispielreise (mit einem Bildlink im Satz ergänzt) und Stadtwochenende, Skript seiten_bilder_p2.mjs."""
import functools
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
SATZ = "Vom Hockstein sieht man [die Basteibrücke]({bid}) gut."


def bauen_beide(tmp_path):
    """Beispielreise mit Bildlink im Satz (auf das erste aktive Commons-Bild) und Stadtwochenende, gebaut unter web/."""
    quelle = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", quelle)
    bilder = yaml.safe_load((quelle / "plan/bilder.yaml").read_text(encoding="utf-8"))["bilder"]
    bid = next(b["id"] for b in bilder if isinstance(b.get("quelle"), dict) and b.get("status", "aktiv") == "aktiv")
    w = quelle / "inhalt" / "wissen.md"
    w.write_text(w.read_text(encoding="utf-8").replace("### Der Hockstein\n", "### Der Hockstein\n" + SATZ.format(bid=bid) + "\n\n", 1),
                 encoding="utf-8")
    daten = bauen.bauen(quelle, tmp_path / "web" / "beispiel")
    bauen.bauen(WURZEL / "beispiel/reisen/stadtwochenende", tmp_path / "web" / "stadt")
    return daten


@pytest.fixture(scope="module", params=["chromium", "webkit"])
def ergebnis(request, tmp_path_factory):
    if not PLAYWRIGHT.exists() or not shutil.which("node"):
        pytest.skip("Playwright fehlt")
    tmp_path = tmp_path_factory.mktemp("bilder_p2")
    daten = bauen_beide(tmp_path)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    basis = f"http://127.0.0.1:{s.server_address[1]}"
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_bilder_p2.mjs"), str(PLAYWRIGHT), basis + "/beispiel/",
                              basis + "/stadt/"], capture_output=True, text=True, timeout=600,
                             env={**os.environ, "RH_BROWSER": request.param})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-3000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    return e, daten


def test_ohne_seitenfehler_und_ohne_csp_meldung(ergebnis):
    """AC-4 (AC-13): keine CSP-Meldung, kein Seitenfehler; die Großansicht trägt keine Inline-Handler."""
    e, _ = ergebnis
    assert e["fehler"] == [], e["fehler"]
    assert e["aus"]["anzahl"] > 0, "daten.json ohne bilder"
    g = e["aus"]["gross"]
    assert g and g["auf"] and not g["auf"]["inline"], g


def test_titelbild_vor_dem_reisekopf_mit_nennung(ergebnis):
    """AC-1: Titelbild 16:10, Radius --r-gross, mit Nennung, vor dem Reisekopf."""
    e, _ = ergebnis
    t = e["aus"]["reise"]["titel"]
    assert t, "kein .bild.titel in der Reise"
    assert abs(t["seite"] - 16 / 10) < 0.03, t
    assert t["token"] and t["radius"] == t["token"], t
    assert t["vorKopf"] and t["nennung"].strip() and t["label"], t
    assert t["zoom"] == "zoom-in", t


def test_mini_in_der_tagesliste_nur_bei_tagen_mit_kopfbild(ergebnis):
    """AC-1: Mini (44 px) in der Tagesliste nur bei Tagen mit Kopfbild."""
    e, _ = ergebnis
    gruppen, tage = e["aus"]["gruppen"], e["aus"]["reise"]["tage"]
    assert tage, "keine Tagesliste"
    assert any(z.startswith("T-") for z in gruppen), "kein Tag mit Bild in der Beispielreise"
    for z in tage:
        if z["tag"] in gruppen:
            assert z["mini"] and z["mini"]["b"] == 44 and z["mini"]["h"] == 44, z
        else:
            assert z["mini"] is None, z


def test_kopfbilder_16_9_an_ort_etappe_tag_unterkunft_und_bildreihe(ergebnis):
    """AC-1: Kopfbild 16:9 an Ort, Etappe, Tag und Unterkunft; am Ort mit mehreren Bildern die Bildreihe 72 × 54 mit „n Bilder“."""
    e, _ = ergebnis
    gruppen, kopf = e["aus"]["gruppen"], e["aus"]["kopf"]
    for vorsilbe in ("O-", "E-", "T-", "U-"):
        assert any(z.startswith(vorsilbe) for z in kopf), (vorsilbe, sorted(gruppen))
    for zu, k in kopf.items():
        assert k, f"kein Kopfbild an {zu}"
        assert abs(k["seite"] - 16 / 9) < 0.03, (zu, k)
    mehr = {zu: g for zu, g in gruppen.items() if zu.startswith("O-") and len(g) >= 3}
    assert mehr, "kein Ort mit 3 Bildern"
    for zu, g in mehr.items():
        gal = kopf[zu]["galerie"]
        assert gal and len(gal["bilder"]) >= len(g) - 1, (zu, gal)
        assert all(x == [72, 54] for x in gal["bilder"]), gal
        assert re.search(rf"\b{len(g)}\b", gal["text"]), gal


def test_unterkunft_kopfbild_nur_an_der_ersten_nacht(ergebnis):
    """AC-1, ADR-0003: Kopfbild der Unterkunft nur an ihrer Heimat (erste Nacht), an anderen Nächten nur ein Mini."""
    e, daten = ergebnis
    unterkuenfte = [zu for zu in e["aus"]["gruppen"] if zu.startswith("U-")]
    assert unterkuenfte
    for u in unterkuenfte:
        naechte = [t["id"] for t in daten["route"]["tage"] if (t.get("nacht") or {}).get("unterkunft") == u]
        kopf = [t for t, o in e["aus"]["naechte"].items() if o[u]["kopf"]]
        mini = [t for t, o in e["aus"]["naechte"].items() if o[u]["mini"]]
        assert kopf == naechte[:1], (u, kopf, naechte)
        assert set(naechte[1:]) <= set(mini) and not set(kopf) & set(mini), (u, mini, naechte)


def test_bild_im_text_und_bildlink_mit_unterschrift_und_nennung(ergebnis):
    """AC-2: Bild im Wissenstext und Bildlink im Satz erscheinen als Bild mit Unterschrift und Nennung (V16)."""
    e, _ = ergebnis
    text = e["aus"]["text"]
    assert len(text) >= 2, text
    assert all(x["nennung"].strip() for x in text if x["nennung"] is not None), text
    assert any("die Basteibrücke" in x["nachSatz"] for x in text), text
    assert any(x["bildtext"].strip() for x in text), text


def test_grossansicht_zaehler_tasten_fokus_und_wischen(ergebnis):
    """AC-2: Großansicht modal mit „Ding · i / n“, Pfeiltasten wechseln, Escape schließt mit Fokusrückgabe, Wischen waagerecht
    wechselt, nach unten schließt; vor dem ersten Öffnen gibt es kein #gross."""
    e, _ = ergebnis
    assert e["aus"]["grossVorher"] is False
    g = e["aus"]["gross"]
    assert g, "keine Gruppe mit 3 Bildern an einem Ort"
    n = g["n"]
    assert g["auf"] and g["auf"]["offen"] and g["auf"]["modal"], g["auf"]
    assert re.search(rf"· 1 / {n}\b", g["auf"]["text"]) and g["auf"]["src"].endswith(g["gross"][0]), g["auf"]
    assert g["auf"]["hintergrund"].replace(" ", "") in ("rgba(8,10,9,0.94)",), g["auf"]["hintergrund"]
    assert re.search(rf"· 2 / {n}\b", g["rechts"]["text"]) and g["rechts"]["src"].endswith(g["gross"][1]), g["rechts"]
    assert re.search(rf"· 1 / {n}\b", g["links"]["text"]), g["links"]
    assert not g["zu"]["offen"] and g["zu"]["fokusZurueck"], g["zu"]
    assert g["wischWaagerecht"]["offen"] and re.search(rf"· 2 / {n}\b", g["wischWaagerecht"]["text"]), g["wischWaagerecht"]
    assert not g["wischUnten"]["offen"], g["wischUnten"]
    assert g["auf"]["pfeile"] and all(d != "none" for d in g["auf"]["pfeile"]), g["auf"]["pfeile"]


def test_handy_360_ohne_ueberbreite_und_ohne_pfeile(ergebnis):
    """AC-2: bei 360 px keine Überbreite (Tagesliste, Bildreihe, Karten, Tage); bis 560 px sind die Pfeile ausgeblendet."""
    e, _ = ergebnis
    h = e["aus"]["handy"]
    zu_breit = {k: v for k, v in h["ueberbreite"].items() if v > 0}
    assert zu_breit == {}, zu_breit
    assert h.get("pfeile") and all(d == "none" for d in h["pfeile"]), h.get("pfeile")


def test_stadtwochenende_ohne_bild_elemente(ergebnis):
    """AC-3 (AC-12): das Stadtwochenende zeigt keine Bild-Elemente und kein #gross (Schutz gegen Rückschritt)."""
    e, _ = ergebnis
    assert e["aus"]["stadt"] and all(v == 0 for v in e["aus"]["stadt"].values()), e["aus"]["stadt"]
