"""Elternbezug an: (ADR-0007, Schritt a, frieda-reist#282): lesen und prüfen, Heimat als Regel, item_update mit an,
nachziehen ohne Arbeit. Erfundene Testdaten der beiden Beispielreisen."""
import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import neu  # noqa: E402
import schreiben as sb  # noqa: E402
from conftest import meldet  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402
from test_schreiben import IDA, KARL, repo, routen_auf_main, schreiber  # noqa: E402,F401

WURZEL = Path(__file__).resolve().parent.parent.parent
BEISPIELE = WURZEL / "beispiel" / "reisen"


def kopie(tmp_path, reise="beispielreise"):
    q = tmp_path / "quelle"
    shutil.copytree(BEISPIELE / reise, q)
    return q


def routen_aendern(quelle, fn):
    r = quelle / "plan" / "routen.yaml"
    t = r.read_text(encoding="utf-8")
    r.write_text(fn(t), encoding="utf-8")


def a01_an_ort(t):
    """A-01 (Burg Hohnstein) hängt an seinem Ort O-03 und steht an keinem Tag mehr."""
    assert "aufenthalte: [A-01], " in t
    t = t.replace("aufenthalte: [A-01], ", "")
    assert "    name: Burg Hohnstein\n    ort: O-03\n" in t
    return t.replace("    name: Burg Hohnstein\n    ort: O-03\n", "    name: Burg Hohnstein\n    ort: O-03\n    an: O-03\n")


def test_ohne_an_gilt_die_vorgabe(tmp_path):
    d = bauen.bauen(kopie(tmp_path), tmp_path / "web" / "b")
    # nur die früheren Kartenpunkte hängen mit an: an Strecken und Blöcken (ADR-0007, Schritt d); A-01 hat die Vorgabe
    assert "A-01" not in d["route"]["eltern"] and all(v[:2] in ("E-", "W-") for v in d["route"]["eltern"].values())
    assert d["route"]["aufenthalte"]["A-01"]["tage"] == ["T-02"]


def test_an_wird_gelesen(tmp_path):
    q = kopie(tmp_path)
    routen_aendern(q, a01_an_ort)
    d = bauen.bauen(q, tmp_path / "web" / "b")
    assert d["route"]["eltern"]["A-01"] == "O-03"
    assert d["route"]["aufenthalte"]["A-01"]["tage"] == [] and d["route"]["aufenthalte"]["A-01"]["ohne_tag"]


@pytest.mark.parametrize("an, schluessel", [
    ("O-99", "pruefung.routen.eltern_unbekannt"),
    ("A-01", "pruefung.routen.eltern_selbst"),
    ("F-01", "pruefung.routen.eltern_art"),
    ("irgendwo", "pruefung.routen.eltern_art"),
    ("T-99", "pruefung.routen.eltern_unbekannt"),
])
def test_an_pruefung(tmp_path, an, schluessel):
    q = kopie(tmp_path)
    routen_aendern(q, lambda t: a01_an_ort(t).replace("    an: O-03\n", f"    an: {an}\n"))
    with pytest.raises(bauen.BauFehler) as e:
        bauen.bauen(q, tmp_path / "web" / "b")
    assert meldet(e.value.args[0], schluessel)


def test_an_im_kreis(tmp_path):
    q = kopie(tmp_path, "stadtwochenende")
    routen_aendern(q, lambda t: t.replace("    name: Mittagessen bei Onkel Paul\n", "    name: Mittagessen bei Onkel Paul\n    an: A-02\n")
                                 .replace("    name: Stadtmuseum\n", "    name: Stadtmuseum\n    an: A-01\n"))
    with pytest.raises(bauen.BauFehler) as e:
        bauen.bauen(q, tmp_path / "web" / "b")
    assert meldet(e.value.args[0], "pruefung.routen.eltern_kreis")


def test_an_einer_strecke_ist_der_elternbezug_nur_bei_einer_kennung(tmp_path):
    """Bei einer Strecke im alten Format bleibt an: mit einer Uhrzeit die Ankunft; eine Kennung ist der Elternbezug. Im neuen
    Format steht die Ankunft als Merkmal, an: ist frei für den Elternbezug."""
    q = kopie(tmp_path, "stadtwochenende")
    routen_aendern(q, lambda t: t.replace('    nach: O-02\n    art: bahn\n', '    nach: O-02\n    art: bahn\n    an: "11:25"\n', 1)
                                 .replace('      ankunft: {typ: zeitpunkt, rolle: ankunft, wert: "11:25", quelle: "erfunden (Beispiel); Fahrplan nicht geprüft"}\n', '', 1))
    d = bauen.bauen(q, tmp_path / "web" / "b")
    assert d["route"]["strecken"]["E-01"]["an"] == "11:25" and d["route"]["eltern"] == {}
    routen_aendern(q, lambda t: t.replace('    an: "11:25"\n', '    an: O-02\n', 1).replace('      abfahrt:', '      ankunft: {typ: zeitpunkt, rolle: ankunft, wert: "11:25", quelle: "x"}\n      abfahrt:', 1))
    d = bauen.bauen(q, tmp_path / "web2" / "b")
    assert d["route"]["eltern"] == {"E-01": "O-02"} and d["route"]["strecken"]["E-01"]["an"] == "11:25"


def test_nachziehen_schreibt_an_nicht_um(tmp_path):
    """Schritt a ändert kein Dateiformat: nachziehen hat bei Beispielreisen mit und ohne an: nichts zu tun."""
    q = kopie(tmp_path)
    neu.nachziehen(q)   # Altlasten der Beispielreise (Rolle kosten in arten.yaml) gehören nicht zu diesem Schritt
    assert neu.nachziehen(q) == []
    routen_aendern(q, a01_an_ort)
    vorher = (q / "plan" / "routen.yaml").read_text(encoding="utf-8")
    assert neu.nachziehen(q) == []
    assert (q / "plan" / "routen.yaml").read_text(encoding="utf-8") == vorher


def test_item_update_setzt_an_um_und_loest_vom_tag(repo):
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "ding_aendern", {**KARL, "args": {"ziel": "A-01", "an": "O-03"}})
    assert "an „O-03“" in a["text"] or "an: O-03" in a["text"] or "O-03" in a["text"]
    assert "T-02" in a["text"]   # vom Tag gelöst
    r, text = routen_auf_main(origin)
    assert r["aufenthalte"]["A-01"]["an"] == "O-03"
    assert "A-01" not in (r["tage"]["T-02"].get("aufenthalte") or [])
    s.vorbereiten()
    # leer stellt die Vorgabe wieder her
    a = s.schreiben("beispielreise", "ding_aendern", {**KARL, "args": {"ziel": "A-01", "an": ""}})
    r, _ = routen_auf_main(origin)
    assert "an" not in r["aufenthalte"]["A-01"]


def test_item_update_an_lehnt_ab(repo):
    s = schreiber(repo)
    for args, schluessel in (({"ziel": "A-01", "an": "O-99"}, "schreiben.ding_aendern.an_unbekannt"),
                             ({"ziel": "A-01", "an": "T-02"}, "schreiben.ding_aendern.an_tag"),
                             ({"ziel": "A-01", "an": "A-01"}, "schreiben.ding_aendern.an_selbst"),
                             ({"ziel": "A-01", "an": "Hohnstein"}, "schreiben.ding_aendern.an_form")):
        with pytest.raises(sb.Ablehnung) as e:
            s.schreiben("beispielreise", "ding_aendern", {**KARL, "args": args})
        assert meldet(str(e.value), schluessel), (args, str(e.value))
        s.vorbereiten()


def test_item_create_mit_an(repo):
    _, origin, _, _ = repo
    s = schreiber(repo)
    s.schreiben("beispielreise", "ding_anlegen", {**KARL, "args": {"was": "aufenthalt", "titel": "Bäckerei", "ort": "O-03", "art": "besichtigung",
                                                                    "an": "O-03", "quelle": "Beispiel"}})
    r, _ = routen_auf_main(origin)
    neu_ = [a for a in r["aufenthalte"].values() if a["name"] == "Bäckerei"]
    assert neu_ and neu_[0]["an"] == "O-03"


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
def test_aufenthalt_ohne_tag_steht_vollstaendig_auf_der_ortsseite(tmp_path):
    q = kopie(tmp_path)
    routen_aendern(q, a01_an_ort)
    bauen.bauen(q, tmp_path / "web" / "beispiel")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_elternbezug.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/", "A-01", "O-03"],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == []
    assert e["ort"]["voll"] == 1, e                        # vollständig auf der Ortsseite
    # sonst nur die Zeile mit Link: unter der Karte (Reiter Karte) oder im Überblick der Reise, wo keine Karte ist
    assert e["start"]["voll"] == 0 and e["karte"]["voll"] == 0 and e["start"]["links"] + e["karte"]["links"] >= 1, e
    assert e["ziel"]["ortsseite"] and e["ziel"]["voll"] == 1, e      # der Link führt zur Ortsseite
