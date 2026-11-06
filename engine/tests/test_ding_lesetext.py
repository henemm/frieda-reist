"""Lesetext an Unterkunft und Aufenthalt (#334, Product Owner 6.11.2026: die allgemeinste Form, ohne Dossier je Grundform):
Feld lesetext am Ding in routen.yaml ({text, quelle, geschrieben, wer}), die Karte des Dings zeigt es mit Herkunftszeile,
gegliedert nach der Art. Erfundene Testdaten beider Beispielreisen."""
import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import konnektor as kn  # noqa: E402
import schreiben as sb  # noqa: E402
from conftest import meldet  # noqa: E402

BEISPIELE = Path(__file__).resolve().parent.parent.parent / "beispiel" / "reisen"
IDA = {"name": "Ida"}


def kopie(tmp_path, reise="beispielreise"):
    q = tmp_path / reise
    shutil.copytree(BEISPIELE / reise, q)
    return q


def routen(q):
    return yaml.safe_load((q / "plan" / "routen.yaml").read_text(encoding="utf-8"))


def schreib(q, ziel, text, quelle="erfunden (Test)"):
    return sb.lesetext_schreiben(q, IDA, {"ziel": ziel, "text": text, "quelle": quelle})


def test_beispielreise_unterkunft_mit_lesetext_im_bau(tmp_path):
    d = bauen.bauen(kopie(tmp_path), tmp_path / "web")
    lt = d["route"]["unterkuenfte"]["U-02"]["lesetext"]
    assert "<strong>Das Haus.</strong>" in lt and "Herkunft: erfunden (Beispiel)" in lt and "Ida" in lt
    assert "lesetext" not in d["route"]["unterkuenfte"]["U-01"]


def test_unterkunft_schreiben_ersetzt_und_prueft_rubriken(tmp_path):
    q = kopie(tmp_path)
    with pytest.raises(sb.Ablehnung) as e:
        schreib(q, "U-02", "**Essen.** Gut (Test).")
    assert meldet(str(e.value), "schreiben.lesetext_schreiben.4") and "Das Haus, Ankommen" in str(e.value)
    titel, antwort = schreib(q, "u-02", "**Ankommen.** Klingeln am Tor (Test).\n\n**Das Haus.** Klein (Test).")
    assert meldet(titel, "schreiben.titel.lesetext_ersetzt") and meldet(antwort, "schreiben.antwort.lesetext.ding_ersetzt")
    lt = routen(q)["unterkuenfte"]["U-02"]["lesetext"]
    assert lt["text"].startswith("**Ankommen.** Klingeln am Tor (Test).") and lt["quelle"] == "erfunden (Test)" and lt["wer"] == "Ida"
    assert "geschrieben" in lt and routen(q)["unterkuenfte"]["U-02"]["merkmale"]["preis"]["wert"] == "85 €"   # sonst nichts verändert
    d = bauen.bauen(q, tmp_path / "web")
    assert "Klingeln am Tor" in d["route"]["unterkuenfte"]["U-02"]["lesetext"]


def test_ohne_gliederung_frei_und_neu_angelegt(tmp_path):
    q = kopie(tmp_path)
    titel, antwort = schreib(q, "U-01", "**Lage.** Am Fluss (Test).")   # hotel ohne Gliederung: jedes Stichwort
    assert meldet(titel, "schreiben.titel.lesetext_angelegt") and meldet(antwort, "schreiben.antwort.lesetext.ding_angelegt")
    schreib(q, "A-01", "Die Burg über dem Tal (Test).")
    assert routen(q)["aufenthalte"]["A-01"]["lesetext"]["text"] == "Die Burg über dem Tal (Test)."
    d = bauen.bauen(q, tmp_path / "web")
    assert "Am Fluss" in d["route"]["unterkuenfte"]["U-01"]["lesetext"] and "Burg über dem Tal" in d["route"]["aufenthalte"]["A-01"]["lesetext"]


def test_stadtwochenende_aufenthalt_mit_gliederung(tmp_path):
    q = kopie(tmp_path, "stadtwochenende")
    with pytest.raises(sb.Ablehnung):
        schreib(q, "A-02", "**Essen.** Café im Haus (Test).")
    schreib(q, "A-02", "**Sammlung.** Stadtgeschichte in drei Stockwerken (Test).\n\n**Zeit.** Zwei Stunden (Test).")
    d = bauen.bauen(q, tmp_path / "web")
    assert "<strong>Sammlung.</strong>" in d["route"]["aufenthalte"]["A-02"]["lesetext"]
    h = kn.Handbuch(d)
    _, t = h.eintraege["A-02"]
    assert meldet(t, "konnektor.lesetext_zeilen.1") and "- Sammlung: Was es zu sehen gibt" in t
    assert meldet(t, "konnektor.ausgabe.lesetext_ding") and "Stadtgeschichte in drei Stockwerken" in t


def test_unbekanntes_ding(tmp_path):
    q = kopie(tmp_path)
    for ziel in ("U-99", "A-99"):
        with pytest.raises(sb.Ablehnung) as e:
            schreib(q, ziel, "x")
        assert meldet(str(e.value), "schreiben.lesetext_schreiben.ding_fehlt")


def test_bau_prueft_form_und_meldet_fremdes_stichwort(tmp_path):
    q = kopie(tmp_path)
    p = q / "plan" / "routen.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace('      quelle: "erfunden (Beispiel)"\n      geschrieben: 2026-11-06', '      geschrieben: 2026-11-06'), encoding="utf-8")
    with pytest.raises(bauen.BauFehler) as e:
        bauen.bauen(q, tmp_path / "web")
    assert meldet(e.value.args[0], "pruefung.routen.lesetext_ding")
    q = kopie(tmp_path / "h")
    p = q / "plan" / "routen.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace("**Ankommen.** Vom Malerweg", "**Wetter.** Vom Malerweg"), encoding="utf-8")
    b = bauen.Bauer(q, tmp_path / "h" / "web")
    b.daten()
    assert any("U-02" in str(h) and "Wetter" in str(h) for h in b.hinweise)


def test_konnektor_zeigt_unterkunft_und_aufenthalt_mit_lesetext(tmp_path):
    h = kn.Handbuch(bauen.bauen(kopie(tmp_path), tmp_path / "web"))
    _, t = h.eintraege["U-02"]
    assert "- Das Haus: Wie das Haus ist" in t and "altes Bürgerhaus am Markt" in t
    aus, fehler = h.zeige("A-01")   # Aufenthalt ist zeigbar
    assert fehler is None and "Burg Hohnstein" in aus
    mt, _ = h.merkmale("A-01", None)   # Merkmale eines Aufenthalts (stürzte bis #334 ab)
    assert "Burg Hohnstein" in mt


def seiten(tmp_path, q, *paare):
    import functools
    import http.server
    import json
    import os
    import subprocess
    import threading
    from playwright_pfad import PLAYWRIGHT
    bauen.bauen(q, tmp_path / "seiten" / "r")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "seiten")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_ding_lesetext.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/r/", *paare],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == []
    return e


def _browser():
    from playwright_pfad import PLAYWRIGHT
    return PLAYWRIGHT.exists() and shutil.which("node")


@pytest.mark.skipif(not _browser(), reason="Playwright fehlt")
def test_seite_zeigt_lesetext_auf_der_karte_des_dings(tmp_path):
    q = kopie(tmp_path)
    schreib(q, "A-01", "**Rundgang.** Über den Burghof zum Turm (Test).")
    e = seiten(tmp_path, q, "U-02=altes Bürgerhaus am Markt", "A-01=Über den Burghof zum Turm")
    for did in ("U-02", "A-01"):
        assert e[did]["karte"] and e[did]["imDing"] and e[did]["fett"] >= 1 and e[did]["herkunft"] and e[did]["mal"] == 1, (did, e)
    s = kopie(tmp_path / "s", "stadtwochenende")
    schreib(s, "A-02", "**Sammlung.** Stadtgeschichte in drei Stockwerken (Test).")
    e = seiten(tmp_path / "s", s, "A-02=Stadtgeschichte in drei Stockwerken")
    assert e["A-02"]["imDing"] and e["A-02"]["mal"] == 1, e
