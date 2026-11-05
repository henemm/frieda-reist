"""#215, Teil 3 (Rest): Route `offen` heißt `zu-tun`, das Bestandsfeld `buchung:` entfällt
(Spec docs/specs/oberflaeche/altformen-rest-215.md). Nur erfundene Daten: die beiden Beispielreisen."""
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
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bauen  # noqa: E402
import neu  # noqa: E402
import texte  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
BEISPIELE = ["beispielreise", "stadtwochenende"]
SCHLUESSEL_PRUEFUNG = "pruefung.routen.buchung_feld"
SCHLUESSEL_QUELLE = "inhalt.nachziehen.buchung_quelle"   # Bereiche der Schlüssel: docs/sprachen.md, test_texte.test_schluessel_form
SCHLUESSEL_PRUEFEN = "pruefung.neu.nachziehen.buchung_pruefen"
OHNE_BROWSER = pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")


def kopie(name, tmp_path):
    r = tmp_path / name
    shutil.copytree(WURZEL / "beispiel" / "reisen" / name, r)
    return r


def feld_setzen(reise, ding, wert):
    """Trägt `buchung: <wert>` an einer Unterkunft ein (Zeile hinter `art:`), wie es ein früherer Stand tat."""
    p = reise / "plan" / "routen.yaml"
    text = p.read_text(encoding="utf-8")
    muster = re.compile(rf"(^  {re.escape(ding)}:\n(?:    .*\n)*?    art: .*\n)", re.M)
    assert muster.search(text), ding
    p.write_text(muster.sub(lambda m: m.group(1) + f"    buchung: {json.dumps(wert, ensure_ascii=False)}\n", text, count=1), encoding="utf-8")
    return p


def roh(reise):
    return yaml.safe_load((reise / "plan" / "routen.yaml").read_text(encoding="utf-8"))


def stand(reise, tmp_path, ding):
    return bauen.Bauer(reise, tmp_path / "dist").daten()["route"]["unterkuenfte"][ding]["buchung"]


def buchungen_fuer(reise, ding):
    return {k: b for k, b in (roh(reise).get("buchungen") or {}).items() if ding in (b.get("fuer") or [])}


# ---------- Umstellung buchung: -> Buchung B-… (Test 5 bis 9) ----------

def test_angefragt_wird_zur_buchung_angefragt(tmp_path):
    """Test 5: `buchung: angefragt` ohne Buchung -> Buchung fuer [U-02], status angefragt, quelle, Feld weg, Stand unverändert."""
    r = kopie("beispielreise", tmp_path)
    p = feld_setzen(r, "U-02", "angefragt")
    assert not buchungen_fuer(r, "U-02")
    m = neu.nachziehen(r)
    assert any("U-02" in z and "buchung" in z for z in m), m
    d = roh(r)
    assert "buchung" not in d["unterkuenfte"]["U-02"] and "buchung:" not in p.read_text(encoding="utf-8").split("buchungen:")[0]
    b = buchungen_fuer(r, "U-02")
    assert len(b) == 1
    neu_b = next(iter(b.values()))
    assert neu_b["status"] == "angefragt" and neu_b["quelle"] == texte.t("de", SCHLUESSEL_QUELLE)
    assert stand(r, tmp_path, "U-02") == "angefragt"


def test_offen_loescht_nur_den_schluessel(tmp_path):
    """Test 6: `buchung: offen` -> nur der Schlüssel verschwindet, keine Buchung, Stand bleibt offen."""
    r = kopie("beispielreise", tmp_path)
    vorher = set((roh(r).get("buchungen") or {}))
    feld_setzen(r, "U-02", "offen")
    neu.nachziehen(r)
    assert "buchung" not in roh(r)["unterkuenfte"]["U-02"]
    assert set(roh(r)["buchungen"]) == vorher and not buchungen_fuer(r, "U-02")
    assert stand(r, tmp_path, "U-02") == "offen"


def test_freitext_wird_gebucht_mit_notiz_und_pruefmeldung(tmp_path):
    """Test 7: anderer Text -> Buchung gebucht, notiz wörtlich, Meldung „bitte prüfen“; Chip zeigt gebucht (bewusste Abweichung)."""
    r = kopie("beispielreise", tmp_path)
    feld_setzen(r, "U-02", "Zusage per Telefon")
    m = neu.nachziehen(r)
    assert any(texte.t("de", SCHLUESSEL_PRUEFEN, wo="U-02", text="Zusage per Telefon") == z for z in m), m
    b = next(iter(buchungen_fuer(r, "U-02").values()))
    assert b["status"] == "gebucht" and b["notiz"] == "Zusage per Telefon"
    assert stand(r, tmp_path, "U-02") == "gebucht"


def test_vorhandene_buchung_gewinnt_keine_zweite(tmp_path):
    """Test 8: Ding hat `buchung: gebucht` und schon B-01 -> keine zweite Buchung, nur der Schlüssel entfällt."""
    r = kopie("beispielreise", tmp_path)
    vorher = set(roh(r)["buchungen"])
    feld_setzen(r, "U-01", "gebucht")
    neu.nachziehen(r)
    assert "buchung" not in roh(r)["unterkuenfte"]["U-01"]
    assert set(roh(r)["buchungen"]) == vorher
    assert stand(r, tmp_path, "U-01") == "gebucht"


def test_nummer_nach_den_vorhandenen_ids_und_aufenthalt_strecke(tmp_path):
    """Die laufende Nummer folgt den vorhandenen B-IDs; das Feld wird auch an Aufenthalt und Strecke umgestellt."""
    r = kopie("beispielreise", tmp_path)
    feld_setzen(r, "U-02", "gebucht")
    neu.nachziehen(r)
    ids = sorted(roh(r)["buchungen"])
    assert ids == sorted(set(ids)) and f"B-{len(ids):02d}" in ids
    assert ids[-1] == f"B-{len(ids):02d}"   # lückenlos fortgeführt, die neue Nummer ist die höchste


@pytest.mark.parametrize("name", BEISPIELE)
def test_zweiter_lauf_und_reise_ohne_feld_ohne_aenderung(name, tmp_path):
    """Test 9: Reisen ohne `buchung:` bleiben unberührt (Datei, Meldungen); ein zweiter Lauf ändert nichts."""
    r = kopie(name, tmp_path)
    p = r / "plan" / "routen.yaml"
    vorher = p.read_text(encoding="utf-8")
    assert not [z for z in neu.nachziehen(r) if "buchung" in z.lower()]
    assert p.read_text(encoding="utf-8") == vorher
    if name == "beispielreise":
        feld_setzen(r, "U-02", "angefragt")
        neu.nachziehen(r)
        nach = p.read_text(encoding="utf-8")
        assert neu.nachziehen(r) == [] and p.read_text(encoding="utf-8") == nach


# ---------- Prüfung (Test 10, Test 11) ----------

@pytest.mark.parametrize("name", BEISPIELE)
def test_uebriggebliebenes_feld_bricht_den_bau_ab(name, tmp_path):
    """Test 10: kein stilles Ignorieren; die Meldung nennt `neu.py nachziehen`."""
    r = kopie(name, tmp_path)
    feld_setzen(r, "U-01", "gebucht")
    with pytest.raises(bauen.BauFehler) as e:
        bauen.Bauer(r, tmp_path / "dist").daten()
    erwartet = str(texte.satz(SCHLUESSEL_PRUEFUNG, wo="U-01"))
    assert erwartet != SCHLUESSEL_PRUEFUNG and "nachziehen" in erwartet
    assert any(erwartet in m for m in e.value.meldungen), e.value.meldungen


def test_buchung_von_liest_das_eingabefeld_nicht_mehr():
    """Der Lesepfad `d.get("buchung")` in Routen.buchung_von ist entfernt."""
    quelltext = (WURZEL / "engine" / "routen.py").read_text(encoding="utf-8")
    kopf = quelltext.split("def buchung_von", 1)[1].split("def buchung_id", 1)[0]
    assert 'd.get("buchung")' not in kopf and 'd["buchung"]' not in kopf


@pytest.mark.parametrize("schluessel", [SCHLUESSEL_PRUEFUNG, SCHLUESSEL_QUELLE, SCHLUESSEL_PRUEFEN])
def test_neue_schluessel_in_jeder_sprache(schluessel):
    for sprache in texte.sprachen():
        assert texte.t(sprache, schluessel, wo="U-01", text="x") != schluessel, (sprache, schluessel)


# ---------- Route zu-tun (Test 1 bis 4, 12) ----------

def test_vorlage_kennt_offen_nur_als_alias():
    """Test 12: `"offen"` kommt in der Vorlage nicht mehr als Reiter- oder Routenschlüssel vor, außer dem einen Alias."""
    v = (WURZEL / "engine" / "vorlage.html").read_text(encoding="utf-8")
    assert '["offen", () => T("seite.reiter.offen")' not in v
    assert 'const REIHE = ["varianten", "karte", "etappen", "zu-tun"' in v
    assert "START === \"offen\"" not in v and 'zeigeReiter("offen")' not in v and 'href="#offen"' not in v
    alias = re.findall(r'===\s*"offen"\s*\?\s*"zu-tun"|"offen":\s*"zu-tun"', v)
    assert len(alias) == 1, alias


def test_symbol_und_pushziel_heissen_zu_tun():
    assert '"zu-tun"' in (WURZEL / "engine" / "bauen.py").read_text(encoding="utf-8")
    assert 'ziel = "zu-tun" if' in (WURZEL / "engine" / "push.py").read_text(encoding="utf-8")


def _bedienen(tmp_path, name, start=None):
    quelle = kopie(name, tmp_path)
    if start:   # start gehört nach reise.yaml (darstellung)
        cfg = quelle / "reise.yaml"
        cfg.write_text(cfg.read_text(encoding="utf-8").replace("darstellung:\n", f"darstellung:\n  start: {start}\n", 1), encoding="utf-8")
    bauen.bauen(quelle, tmp_path / "web" / "reise")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_altformen_215.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/reise/"],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == [], e["fehler"]
    return e


@OHNE_BROWSER
@pytest.mark.parametrize("name", BEISPIELE)
def test_reiter_heisst_zu_tun_und_alter_link_wird_umgeleitet(name, tmp_path):
    """Test 1 und 2: Reiter öffnet `#zu-tun`; alter Link `#offen` zeigt „Zu tun“, Adresse `#zu-tun`, kein neuer Verlaufseintrag."""
    e = _bedienen(tmp_path, name)
    assert e["reiter_hash"] == "#zu-tun" and e["reiter_aktiv"] and e["reiter_sichtbar"], e
    assert e["alt_hash"] == "#zu-tun" and e["alt_aktiv"] and e["alt_sichtbar"], e
    assert e["alt_verlauf"] == e["alt_verlauf_vorher"], e   # replaceState: kein zusätzlicher Eintrag
    assert e["alt_hashchange"] == "#zu-tun", e


@OHNE_BROWSER
def test_start_offen_beginnt_auf_zu_tun(tmp_path):
    """Test 3: reise.yaml (darstellung) `start: offen` wird als `zu-tun` gelesen."""
    e = _bedienen(tmp_path, "beispielreise", start="offen")
    assert e["start_aktiv"] == "zu-tun", e


@OHNE_BROWSER
def test_pwa_oeffnet_alte_push_adresse():
    """Test 4: die Service-Worker-Prüfung öffnet die neue Push-Adresse und die alte `#offen` auf demselben Reiter."""
    quelltext = (Path(__file__).parent / "pwa_browser.mjs").read_text(encoding="utf-8")
    assert 'basis + "#zu-tun"' in quelltext and 'basis + "#offen"' in quelltext
