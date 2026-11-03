"""Art-Übersicht (ADR-0007, Schritt e, frieda-reist#286, löst #275 ab): alle Dinge einer Art mit ihren Merkmalen, nur dort, wo ein
Abschnitt des Wissens oder eine Kartenansicht sie anfordert; kein eigener Reiter, keine Kopie der Werte im Text."""
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import schreiben as sb  # noqa: E402
from conftest import meldet  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402
from test_schreiben import IDA, KARL, repo, routen_auf_main, schreiber  # noqa: E402,F401

WURZEL = Path(__file__).resolve().parent.parent.parent


def kopie(tmp_path, uebersichten=None, reise="beispielreise"):
    q = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen" / reise, q)
    if uebersichten is not None:
        p = q / "reise.json"
        cfg = json.loads(p.read_text(encoding="utf-8"))
        cfg["uebersichten"] = uebersichten
        p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return q


def test_abschnitt_nennt_die_arten_seiner_uebersicht(tmp_path):
    q = kopie(tmp_path, {"W-05": ["pension", "hotel"]})
    d = bauen.bauen(q, tmp_path / "x")
    ab = next(a for a in d["abschnitte"] if a["id"] == "W-05")
    assert ab["uebersicht"] == ["pension", "hotel"]
    assert not any("uebersicht" in a for a in d["abschnitte"] if a["id"] != "W-05")


@pytest.mark.parametrize("uebersichten, schluessel", [
    ({"W-99": ["hotel"]}, "pruefung.bauen.uebersicht_abschnitt"),
    ({"W-05": ["gibtsnicht"]}, "pruefung.bauen.uebersicht_art"),
    ({"W-05": "hotel"}, "pruefung.bauen.uebersicht_liste"),
    (["W-05"], "pruefung.bauen.uebersichten_form"),
])
def test_uebersicht_wird_geprueft(tmp_path, uebersichten, schluessel):
    q = kopie(tmp_path, uebersichten)
    with pytest.raises(bauen.BauFehler) as e:
        bauen.bauen(q, tmp_path / "x")
    assert meldet(e.value.args[0], schluessel)


def test_kartenansicht_nimmt_uebersicht_entgegen(repo):
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "kartenansicht_setzen", {**IDA, "args": {"titel": "Nur Unterkünfte", "arten": ["hotel", "pension"], "uebersicht": ["pension"]}})
    assert a["ok"]
    r, _ = routen_auf_main(origin)
    assert r["karten_ansichten"][-1]["uebersicht"] == ["pension"]
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="gibtsnicht"):
        s.schreiben("beispielreise", "kartenansicht_setzen", {**IDA, "args": {"titel": "X", "arten": ["hotel"], "uebersicht": ["gibtsnicht"]}})


def test_wissen_aendern_setzt_und_entfernt_die_uebersicht(repo):
    import subprocess as sp
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "wissen_aendern", {**IDA, "args": {"ziel": "W-05", "grund": "Übersicht der Unterkünfte", "uebersicht": ["pension", "hotel"]}})
    assert a["ok"] and "pension, hotel" in a["text"]
    cfg = json.loads(sp.run(["git", "-C", str(origin), "show", "main:reisen/beispielreise/reise.json"], check=True, capture_output=True, text=True).stdout)
    assert cfg["uebersichten"] == {"W-05": ["pension", "hotel"]}
    s.vorbereiten()
    s.schreiben("beispielreise", "wissen_aendern", {**IDA, "args": {"ziel": "W-05", "grund": "weg damit", "uebersicht": []}})
    cfg = json.loads(sp.run(["git", "-C", str(origin), "show", "main:reisen/beispielreise/reise.json"], check=True, capture_output=True, text=True).stdout)
    assert "uebersichten" not in cfg


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
def test_uebersicht_im_browser_tabelle_karten_sortierung_und_links(tmp_path):
    """Am Rechner eine Tabelle mit Sortierung, am Telefon (390 px) gestapelte Karten; jede Zeile führt zur Heimat; kein Ding steht
    vollständig in der Übersicht; ein geänderter Wert erscheint nach dem Bau ohne Textänderung."""
    q = kopie(tmp_path, {"W-05": ["pension"]})
    import yaml
    datei = q / "plan/routen.yaml"
    roh = yaml.safe_load(datei.read_text(encoding="utf-8"))
    zweite = json.loads(json.dumps(roh["unterkuenfte"]["U-02"], default=str))   # eine zweite Pension, erfunden
    zweite["name"] = "Pension Talblick"
    zweite["merkmale"]["preis"]["wert"] = "61 €"
    roh["unterkuenfte"]["U-90"] = zweite
    assert roh["unterkuenfte"]["U-02"]["merkmale"]["preis"]["wert"] == "85 €"
    roh["unterkuenfte"]["U-02"]["merkmale"]["preis"]["wert"] = "93 €"   # der Preis steht nur in den Daten, nicht im Text
    datei.write_text(yaml.safe_dump(roh, allow_unicode=True, sort_keys=False), encoding="utf-8")
    bauen.bauen(q, tmp_path / "web" / "beispiel")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_art_uebersicht.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/", "W-05", "pension"],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == []
    r, t = e["rechner"], e["telefon"]
    assert r["tabellen"] == 1 and r["zeilen"] >= 2 and r["tabelleSichtbar"] and not r["kartenSichtbar"], r
    assert not t["tabelleSichtbar"] and t["kartenSichtbar"] and t["karten"] == r["zeilen"], t
    assert all(l.startswith("#U-") for l in r["links"]) and r["vollstaendig"] == 0
    assert "93 €" in r["text"] and "93 €" in t["text"]
    assert sorted(r["vorher"]) == sorted(r["nach_sortierung"]) and r["aria"]
    assert r["nach_klick"].startswith("#")
