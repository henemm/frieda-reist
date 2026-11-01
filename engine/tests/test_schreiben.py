"""Tests für engine/schreiben.py: der Konnektor schreibt direkt in die Ontologie der Reise (ADR-0001, Paket O-3).

Aufbau: ein erfundenes Reisen-Repo mit der Beispielreise und einem „origin“ daneben; die Software liegt als Verweis engine/
im Repo (wie der Verweis engine -> frieda/engine einer Instanz). Veröffentlichen ist ein Stummel, der nur festhält, dass er
gerufen wurde."""
import datetime
import json
import os
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import schreiben as sb  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
BEISPIEL = WURZEL / "beispiel" / "reisen" / "beispielreise"
IDA = {"person": "ida", "name": "Ida", "rolle": "organisator"}
KARL = {"person": "karl", "name": "Karl", "rolle": "mitwirkend"}


def git(ordner, *args):
    return subprocess.run(["git", "-C", str(ordner), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """-> (wurzel, origin, arbeit, veroeffentlicht-Datei). FR_*-Werte zeigen auf den Testordner."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    wurzel = tmp_path / "reisen"
    subprocess.run(["git", "clone", "-q", str(origin), str(wurzel)], check=True, capture_output=True)
    git(wurzel, "config", "user.email", "test@example.invalid")
    git(wurzel, "config", "user.name", "Test")
    git(wurzel, "checkout", "-q", "-b", "main")
    shutil.copytree(BEISPIEL, wurzel / "reisen" / "beispielreise")
    (wurzel / "engine").symlink_to(WURZEL / "engine")
    (wurzel / ".gitignore").write_text("dist/\n__pycache__/\n")
    git(wurzel, "add", "-A")
    git(wurzel, "commit", "-q", "-m", "Beispielreise")
    git(wurzel, "push", "-q", "-u", "origin", "main")
    arbeit = tmp_path / "reisen-schreiben"
    stempel = tmp_path / "veroeffentlicht"
    stub = tmp_path / "veroeffentlichen.sh"
    stub.write_text(f"#!/bin/sh\necho \"$FR_WURZEL\" >> {stempel}\n")
    stub.chmod(0o755)
    for k in list(os.environ):
        if k.startswith(("FR_", "SB_", "KN_", "RM_")):
            monkeypatch.delenv(k)
    monkeypatch.setenv("FR_WURZEL", str(wurzel))
    monkeypatch.setenv("FR_SCHREIBKOPIE", str(arbeit))
    monkeypatch.setenv("SB_VEROEFFENTLICHEN", str(stub))
    monkeypatch.setenv("FR_KONTEN", str(tmp_path / "konten"))
    monkeypatch.setenv("FR_SPERREN", str(tmp_path))
    return wurzel, origin, arbeit, stempel


def arten_auf_main(origin):
    text = subprocess.run(["git", "-C", str(origin), "show", "main:reisen/beispielreise/plan/arten.yaml"],
                          check=True, capture_output=True, text=True).stdout
    return yaml.safe_load(text)["arten"], text


@pytest.fixture(autouse=True)
def _bestaetigungen_in_jeder_sprache(monkeypatch):
    """Jede Bestätigung des Schreibwegs, die aus dem Katalog kommt, reist als Schlüssel mit (text_teile, ADR-0006): auf Deutsch ist sie
    der Text selbst, auf Englisch ein vollständiger Satz ohne offene Platzhalter und ohne deutsche Sprachbausteine."""
    import texte
    original = sb.Schreiber.schreiben

    def pruefen(self, *args, **kw):
        antwort = original(self, *args, **kw)
        if isinstance(antwort, dict) and antwort.get("text_teile"):
            satz = texte.Satz.aus_json(antwort["text_teile"])
            assert satz == antwort["text"] and satz.text("de") == antwort["text"]
            en = satz.text("en")
            assert en and "{" not in en and "}" not in en, en
            for wort in (" angelegt", "Grund:", "Herkunft", " für ", "Merkmal ", "Frage "):
                assert wort not in en, (wort, en)
        return antwort
    monkeypatch.setattr(sb.Schreiber, "schreiben", pruefen)


def schreiber(repo):
    wurzel, _, arbeit, _ = repo
    s = sb.Schreiber(wurzel, arbeit)
    s.vorbereiten()
    return s


def warten_auf(datei, versuche=50):
    import time
    for _ in range(versuche):
        if datei.exists():
            return True
        time.sleep(0.05)
    return False


# ---------- Kategorien der Kartenpunkte (O-7) ----------

def kategorien_auf_main(origin):
    text = git(origin, "show", "main:reisen/beispielreise/plan/kategorien.yaml")
    return yaml.safe_load(text)["kategorien"], text


def test_kategorie_anlegen_aendern_und_ablehnen(repo):
    wurzel, origin, arbeit, stempel = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "kategorie_definieren", {**IDA, "args": {
        "kategorie": "aussicht", "bezeichnung": "Aussichtspunkte", "gruppe": "punkt", "farbe": "#336699", "symbol": "karte"}})
    assert a["ok"] and "aussicht" in a["text"]
    k, text = kategorien_auf_main(origin)
    assert k["aussicht"] == {"gruppe": "punkt", "name": "Aussichtspunkte", "farbe": "#336699", "symbol": "karte"}
    assert k["wasser"]["arten"]["quelle"]["umriss"] is True            # Bestand der Beispielreise unverändert
    assert text.startswith("# Kategorien der Kartenpunkte dieser Reise") and "Ida" in text
    # ändern: Art-Zusatz und Name; die Gruppe lässt sich nicht ändern
    a = s.schreiben("beispielreise", "kategorie_definieren", {**IDA, "args": {
        "kategorie": "aussicht", "bezeichnung": "Aussicht", "art": "viewpoint", "art_bezeichnung": "Aussichtspunkt"}})
    assert a["ok"]
    k, _ = kategorien_auf_main(origin)
    assert k["aussicht"]["name"] == "Aussicht" and k["aussicht"]["arten"]["viewpoint"] == {"name": "Aussichtspunkt"}
    for args, grund in (({"kategorie": "aussicht", "gruppe": "wissen"}, "Gruppe"),
                        ({"kategorie": "neu", "bezeichnung": "Neu"}, "braucht"),
                        ({"kategorie": "neu", "bezeichnung": "N", "gruppe": "punkt", "farbe": "rot"}, "farbe"),
                        ({"kategorie": "aussicht", "symbol": "nix"}, "symbol"),
                        ({"kategorie": "aussicht", "art_hinweis": "x", "bezeichnung": "Aussicht"}, "art")):
        with pytest.raises(sb.Ablehnung, match=grund):
            s.schreiben("beispielreise", "kategorie_definieren", {**IDA, "args": args})
    with pytest.raises(sb.Ablehnung, match="nothing about it is to change"):
        s.schreiben("beispielreise", "kategorie_definieren", {**IDA, "args": {"kategorie": "aussicht", "bezeichnung": "Aussicht"}})


# ---------- Arten ----------

def test_art_anlegen_geht_nach_main_und_wird_veroeffentlicht(repo):
    wurzel, origin, arbeit, stempel = repo
    s = schreiber(repo)
    vorher = git(origin, "rev-parse", "main")
    a = s.schreiben("beispielreise", "art_definieren", {**IDA, "args": {"bezeichnung": "Refugi", "grundform": "aufenthalt",
                                                                         "beschreibung": "bewirtschaftete Berghütte", "grund": "GR-Etappen"}})
    assert a["ok"] and "Refugi" in a["text"] and "refugi" in a["text"] and "Aufenthalt" in a["text"]
    assert git(origin, "rev-parse", "main") == a["commit"] != vorher
    import texte
    en = texte.Satz.aus_json(a["text_teile"]).text("en")   # dieselbe Bestätigung für eine englische Person (M9)
    assert en.startswith("Kind “Refugi” created: key refugi, basic form ") and "angelegt" not in en, en
    arten, text = arten_auf_main(origin)
    r = arten["refugi"]
    assert r["grundform"] == "aufenthalt" and r["name"] == "Refugi" and r["beschreibung"] == "bewirtschaftete Berghütte"
    assert r["farbe"] not in {x.get("farbe") for k, x in arten.items() if k != "refugi" and x["grundform"] == "aufenthalt"}
    assert "merkmale" not in r                       # Merkmale kommen im Gespräch dazu (merkmal_definieren)
    assert text.startswith("# Arten und Merkmale dieser Reise") and "Gepflegt im Gespräch" in text and "Ida" in text
    assert "hotel" in arten and arten["hotel"]["merkmale"]["preis"]["name"] == "Preis pro Nacht"   # Bestand unverändert
    nachricht = git(origin, "log", "-1", "--format=%B", "main")
    assert nachricht.startswith("Beispielreise – Malerweg in vier Tagen: Art „Refugi“ (refugi) angelegt")
    assert "Ida (organisator)" in nachricht and "art_definieren" in nachricht and "Grund: GR-Etappen" in nachricht
    assert warten_auf(stempel) and stempel.read_text().strip() == str(wurzel)
    assert not git(arbeit, "status", "--porcelain")   # Arbeitskopie sauber, steht auf dem neuen Stand
    assert git(arbeit, "rev-parse", "HEAD") == a["commit"]


def test_art_bewegung_summiert_bekommt_berechnete_merkmale_und_folge_auch(repo):
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "art_definieren", {**IDA, "args": {"bezeichnung": "Radfahren", "grundform": "bewegung",
                                                                         "summiert": True, "farbe": "oliv"}})
    assert "gehzeit, laenge, hoehenmeter" in a["text"]
    arten, _ = arten_auf_main(origin)
    assert arten["radfahren"]["summiert"] is True and arten["radfahren"]["farbe"] == "oliv"
    assert set(arten["radfahren"]["merkmale"]) == {"gehzeit", "laenge", "hoehenmeter"}
    assert arten["radfahren"]["merkmale"]["laenge"] == {"name": "Länge", "auto": "laenge"}
    s.vorbereiten()
    a = s.schreiben("beispielreise", "art_definieren", {**IDA, "args": {"bezeichnung": "Etappe", "grundform": "folge"}})
    arten, _ = arten_auf_main(origin)
    assert set(arten["etappe"]["merkmale"]) == {"tage", "gehzeit", "unterkuenfte", "anschluss"}
    # Bus ohne summiert: keine berechneten Merkmale
    s.vorbereiten()
    s.schreiben("beispielreise", "art_definieren", {**IDA, "args": {"art": "zug", "bezeichnung": "Zugfahrt", "grundform": "bewegung"}})
    arten, _ = arten_auf_main(origin)
    assert "merkmale" not in arten["zug"] and "farbe" not in arten["zug"]


def test_art_aendern_und_ablehnungen(repo):
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "art_definieren", {**IDA, "args": {"art": "hotel", "bezeichnung": "Hotel oder Pension", "farbe": "rosa"}})
    assert "Name „Hotel“ → „Hotel oder Pension“" in a["text"] and "Farbe rosa" in a["text"]
    arten, _ = arten_auf_main(origin)
    assert arten["hotel"]["name"] == "Hotel oder Pension" and arten["hotel"]["farbe"] == "rosa"
    assert arten["hotel"]["merkmale"]["preis"]["typ"] == "geld"      # Merkmale bleiben
    s.vorbereiten()
    s.schreiben("beispielreise", "art_definieren", {**IDA, "args": {"art": "wandern", "farbe": "gruen"}})
    arten, _ = arten_auf_main(origin)
    assert arten["wandern"]["lesetext"]["charakter"]["name"] == "Charakter"   # Gliederung des Lesetexts bleibt
    stand = git(origin, "rev-parse", "main")
    s.vorbereiten()
    for args, text in (
        ({"art": "hotel"}, "nothing about it is to change"),
        ({"art": "hotel", "grundform": "bewegung"}, "lässt sich nicht ändern"),
        ({"bezeichnung": "Neu"}, "„grundform“ fehlt"),
        ({"grundform": "aufenthalt"}, "„bezeichnung“ fehlt"),
        ({"bezeichnung": "X", "grundform": "aufenthalt", "farbe": "neon"}, "„farbe“ muss"),
        ({"bezeichnung": "X", "grundform": "aufenthalt", "summiert": True}, "nur bei Bewegung"),
        ({"bezeichnung": "X", "grundform": "sonstwas"}, "„grundform“ muss"),
        ({"art": "unterwegs", "bezeichnung": "X", "grundform": "aufenthalt"}, "taugt nicht"),
        ({"art": "Groß", "bezeichnung": "X", "grundform": "aufenthalt"}, "taugt nicht"),
    ):
        with pytest.raises(sb.Ablehnung, match=text):
            s.schreiben("beispielreise", "art_definieren", {**IDA, "args": args})
        assert not git(arbeit, "status", "--porcelain"), args
    assert git(origin, "rev-parse", "main") == stand


# ---------- Merkmale ----------

def test_merkmal_anlegen_aendern_abschalten(repo):
    _, origin, _, _ = repo
    s = schreiber(repo)
    with pytest.raises(sb.Ablehnung, match="braucht „werte“"):
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "bezeichnung": "Stornierung", "typ": "auswahl"}})
    a = s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {
        "art": "pension", "bezeichnung": "Stornierung", "typ": "auswahl", "werte": ["kostenlos", "gegen Gebühr", "nicht möglich", "unklar"],
        "veraenderlich": True, "hilfe": "Buchungsbedingungen auf der Website", "frage": "Bis wann kann man absagen?", "auch": ["Storno"]}})
    assert "Stornierung" in a["text"] and "auswahl (kostenlos | gegen Gebühr | nicht möglich | unklar)" in a["text"] \
        and "veränderlich" in a["text"] and "Stufe gut zu wissen (empfohlen)" in a["text"]
    arten, _ = arten_auf_main(origin)
    m = arten["pension"]["merkmale"]["stornierung"]
    assert m == {"name": "Stornierung", "typ": "auswahl", "werte": ["kostenlos", "gegen Gebühr", "nicht möglich", "unklar"],
                 "veraenderlich": True, "hilfe": "Buchungsbedingungen auf der Website", "frage": "Bis wann kann man absagen?", "auch": ["storno"]}
    assert "stufe" not in m                           # empfohlen ist die Vorgabe und steht nicht in der Datei
    assert arten["pension"]["merkmale"]["preis"]["typ"] == "geld" and arten["hotel"]["merkmale"]["lage"]["stufe"] == "angeboten"
    # Umbenennen und Stufe; die Stufe darf als Wort für Menschen kommen („nötig“), gespeichert wird der Schlüssel (29.10.2026)
    s.vorbereiten()
    a = s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "merkmal": "stornierung",
                                                                             "bezeichnung": "Absagen", "stufe": "Nötig"}})
    assert "Name „Stornierung“ → „Absagen“" in a["text"] and "Stufe nötig (pflicht)" in a["text"]
    arten, _ = arten_auf_main(origin)
    assert arten["pension"]["merkmale"]["stornierung"]["name"] == "Absagen" and arten["pension"]["merkmale"]["stornierung"]["stufe"] == "pflicht"
    # auch die anderen Wörter kommen als Eingabe an; ein unbekanntes Wort wird mit den Wörtern abgelehnt
    for wort, schluessel, text in (("zusätzlich", "angeboten", "Stufe zusätzlich (angeboten)"),
                                   ("Gut zu wissen", "empfohlen", "Stufe gut zu wissen (empfohlen)")):
        s.vorbereiten()
        a = s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "merkmal": "stornierung", "stufe": wort}})
        assert text in a["text"], a["text"]
        arten, _ = arten_auf_main(origin)
        assert arten["pension"]["merkmale"]["stornierung"].get("stufe", "empfohlen") == schluessel
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="nötig"):
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "merkmal": "stornierung", "stufe": "wichtig"}})
    # Abschalten
    s.vorbereiten()
    a = s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "merkmal": "lage", "stufe": "aus",
                                                                             "grund": "interessiert uns nicht"}})
    assert "abgeschaltet" in a["text"] and "Grund: interessiert uns nicht" in a["text"]
    arten, _ = arten_auf_main(origin)
    assert arten["pension"]["merkmale"]["lage"]["stufe"] == "aus"
    # Zweiter Name darf kein neues Merkmal werden
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="schon ein anderer Name"):
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "bezeichnung": "Storno"}})
    with pytest.raises(sb.Ablehnung, match="gibt es bei dieser Reise nicht"):
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "ryokan", "bezeichnung": "Onsen"}})
    with pytest.raises(sb.Ablehnung, match="nothing about it is to change"):
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "merkmal": "preis"}})
    with pytest.raises(sb.Ablehnung, match="„stufe“ muss"):
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "merkmal": "preis", "stufe": "wichtig"}})



def test_merkmal_nach_buchung_sichtbar(repo):
    """Product Owner 31.10.2026: Die Reise legt fest, welches Merkmal nach der Buchung sichtbar bleibt (nach_buchung, z. B. der
    Charakter eines Hotels); alle übrigen stehen dann „Aus der Planung“. Bei Merkmalen der Buchung gibt es das nicht."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "bezeichnung": "Charakter", "nach_buchung": True}})
    assert "bleibt nach der Buchung sichtbar" in a["text"], a["text"]
    arten, _ = arten_auf_main(origin)
    assert arten["pension"]["merkmale"]["charakter"] == {"name": "Charakter", "typ": "text", "nach_buchung": True}
    s.vorbereiten()
    a = s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "merkmal": "charakter", "nach_buchung": False}})
    assert "„Aus der Planung“" in a["text"], a["text"]
    arten, _ = arten_auf_main(origin)
    assert "nach_buchung" not in arten["pension"]["merkmale"]["charakter"]
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="„nach_buchung“ gibt es bei Merkmalen der Buchung nicht"):
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "fuer": "buchung", "bezeichnung": "Zimmer",
                                                                            "nach_buchung": True}})


def test_probebau_lehnt_ab_und_laesst_nichts_zurueck(repo):
    """Neue Auswahlwerte, zu denen die eingetragenen Werte der Reise nicht passen: der Generator lehnt ab, die Arbeitskopie
    bleibt sauber, main unverändert."""
    _, origin, arbeit, stempel = repo
    s = schreiber(repo)
    stand = git(origin, "rev-parse", "main")
    with pytest.raises(sb.Ablehnung, match="nicht bauen"):
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "merkmal": "fruehstueck",
                                                                             "werte": ["ja", "nein"]}})
    assert not git(arbeit, "status", "--porcelain")
    assert git(origin, "rev-parse", "main") == stand and not stempel.exists()
    # Issue #142: der Probebau liefert die Warnungen des Baus (bezug, text); die Beispielreise hat keine
    assert s.probebau(arbeit / "reisen" / "beispielreise") == []


def test_ablehnung_des_probebaus_reist_als_satz_und_kommt_auf_englisch_an(repo):
    """Prüfmeldungen der Reise (pruefung.*, ADR-0006) reisen mit Schlüsseln zum Konnektor: Deutsch bleibt der Wortlaut des
    Protokolls, die Person liest denselben Fehler in ihrer Sprache."""
    import json
    import texte
    s = schreiber(repo)
    with pytest.raises(sb.Ablehnung) as fehler:
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "merkmal": "fruehstueck",
                                                                             "werte": ["ja", "nein"]}})
    e = fehler.value
    unterwegs = json.loads(json.dumps({"fehler": str(e), "fehler_code": e.schluessel, "werte": e.werte_json()}))   # wie über HTTP
    werte = {n: texte.Satz.aus_json(v["satz"]) if isinstance(v, dict) and "satz" in v else v for n, v in unterwegs["werte"].items()}
    satz = texte.Satz(unterwegs["fehler"], unterwegs["fehler_code"], werte)
    assert satz.text("de") == str(e) and "nicht bauen" in satz.text("de")
    en = satz.text("en")
    assert "{" not in en and "cannot be built" in en and "allowed:" in en, en
    for wort in (" gibt es nicht", " muss ", "Merkmal ", "erlaubt", "nicht bauen"):
        assert wort not in en, (wort, en)


def test_hinweise_reisen_mit_schluesseln(repo):
    """Neue Warnungen des Baus kommen als Sätze zum Konnektor (hinweise_teile) und lassen sich dort in jeder Sprache setzen."""
    import texte
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "termin_setzen", {**IDA, "args": {"datum": "2027-05-20", "titel": "Konzert am Abend (Test)",
                                                                       "ort": "O-01", "quelle": "erfunden (Test)"}})
    assert a["hinweise"] == [AUSSERHALB] and len(a["hinweise_teile"]) == 1
    satz = texte.Satz.aus_json(a["hinweise_teile"][0])
    assert str(satz) == AUSSERHALB and satz.text("de") == AUSSERHALB


# ---------- Rolle, Status, Person ----------

def test_rolle_aus_reise_yaml_gilt_vor_dem_konnektor(repo):
    s = schreiber(repo)
    with pytest.raises(sb.Ablehnung, match="nur Organisator:innen"):
        s.schreiben("beispielreise", "art_definieren", {**KARL, "args": {"bezeichnung": "X", "grundform": "aufenthalt"}})
    # Karl behauptet, Organisator zu sein: reise.yaml sagt mitwirkend
    with pytest.raises(sb.Ablehnung, match="nur Organisator:innen"):
        s.schreiben("beispielreise", "art_definieren", {**KARL, "rolle": "organisator", "args": {"bezeichnung": "X", "grundform": "aufenthalt"}})
    # Ida wird als mitwirkend gemeldet: reise.yaml sagt organisator, also geht es
    a = s.schreiben("beispielreise", "art_definieren", {**IDA, "rolle": "mitwirkend", "args": {"bezeichnung": "X", "grundform": "aufenthalt"}})
    assert a["ok"]
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="Name fehlt"):
        s.schreiben("beispielreise", "art_definieren", {"person": None, "name": "", "rolle": "organisator",
                                                        "args": {"bezeichnung": "Y", "grundform": "aufenthalt"}})
    with pytest.raises(sb.Ablehnung, match="gibt es im Repo nicht"):
        s.schreiben("andere", "art_definieren", {**IDA, "args": {}})
    with pytest.raises(sb.Ablehnung, match="Unbekanntes Werkzeug"):
        s.schreiben("beispielreise", "alles_loeschen", {**IDA, "args": {}})


def test_archivierte_reise_ist_schreibgeschuetzt(repo):
    wurzel, _, _, _ = repo
    p = wurzel / "reisen/beispielreise/reise.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace("wert: planung", "wert: archiv"), encoding="utf-8")
    git(wurzel, "commit", "-qam", "archiviert")
    git(wurzel, "push", "-q", "origin", "main")
    s = schreiber(repo)
    with pytest.raises(sb.Ablehnung, match="archiviert"):
        s.schreiben("beispielreise", "art_definieren", {**IDA, "args": {"bezeichnung": "X", "grundform": "aufenthalt"}})


# ---------- Gleichzeitigkeit und Dienst ----------

def test_setzt_auf_zwischenzeitliche_aenderung_auf(repo, tmp_path):
    wurzel, origin, arbeit, _ = repo
    s = schreiber(repo)
    # Jemand anderes schreibt inzwischen nach main (eine Sitzung in Claude Code …)
    andere = tmp_path / "andere"
    subprocess.run(["git", "clone", "-q", str(origin), str(andere)], check=True, capture_output=True)
    git(andere, "config", "user.email", "x@example.invalid")
    git(andere, "config", "user.name", "X")
    (andere / "reisen/beispielreise/CLAUDE.md").write_text("Notiz\n", encoding="utf-8")
    git(andere, "commit", "-qam", "Notiz")
    git(andere, "push", "-q", "origin", "main")
    a = s.schreiben("beispielreise", "art_definieren", {**IDA, "args": {"bezeichnung": "Refugi", "grundform": "aufenthalt"}})
    assert git(origin, "rev-parse", "main") == a["commit"]
    assert git(origin, "log", "--format=%s", "main").splitlines()[1] == "Notiz"
    assert "refugi" in arten_auf_main(origin)[0]


def test_dienst_nur_fuer_den_konnektor_und_mit_dem_code_der_arbeitskopie(repo):
    import konten
    wurzel, origin, arbeit, stempel = repo
    sb.Dienst.schreiber = sb.Schreiber(wurzel, arbeit)
    server = ThreadingHTTPServer(("127.0.0.1", 0), sb.Dienst)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    basis = f"http://127.0.0.1:{server.server_address[1]}"

    def post(pfad, daten, geheim):
        kopf = {"Content-Type": "application/json"}
        if geheim is not None:
            kopf["X-Frieda-Dienst"] = geheim
        req = urllib.request.Request(f"{basis}/{pfad}", data=json.dumps(daten).encode(), method="POST", headers=kopf)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())
    try:
        with urllib.request.urlopen(f"{basis}/gesund") as r:
            assert json.loads(r.read()) == {"gesund": True}
        anfrage = {**IDA, "args": {"bezeichnung": "Refugi", "grundform": "aufenthalt"}}
        assert post("beispielreise/art_definieren", anfrage, None)[0] == 403
        assert post("beispielreise/art_definieren", anfrage, "falsch")[0] == 403
        assert not arbeit.exists()
        geheim = konten.dienst_geheimnis()
        assert post("beispielreise/loeschen", anfrage, geheim)[0] == 404
        assert post("Reise_X/art_definieren", anfrage, geheim)[0] == 404
        code, a = post("beispielreise/art_definieren", anfrage, geheim)
        assert code == 200 and a["ok"] and "Refugi" in a["text"], a
        assert git(origin, "rev-parse", "main") == a["commit"] and "refugi" in arten_auf_main(origin)[0]
        assert warten_auf(stempel)
        code, a = post("beispielreise/art_definieren", {**KARL, "args": {"bezeichnung": "X", "grundform": "aufenthalt"}}, geheim)
        assert code == 422 and not a["ok"] and "organisers" in a["fehler"]
        code, a = post("beispielreise/art_definieren", anfrage, geheim)
        assert code == 422 and "nothing about it is to change" in a["fehler"]
        # GET /<reise>/buchung/<B-id>: gibt es die Buchung auf main? (Beleg vor dem Veröffentlichen, Issue #135)

        def get(pfad, geheim):
            req = urllib.request.Request(f"{basis}/{pfad}", headers={"X-Frieda-Dienst": geheim} if geheim else {})
            try:
                with urllib.request.urlopen(req) as r:
                    return r.status, json.loads(r.read())
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read())
        assert get("beispielreise/buchung/B-01", None)[0] == 403
        assert get("beispielreise/buchung/B-01", geheim) == (200, {"gibt_es": True, "fuer": ["U-01"], "wer": "Ida"})
        assert get("beispielreise/buchung/B-77", geheim) == (200, {"gibt_es": False})
        assert get("andere-reise/buchung/B-01", geheim) == (200, {"gibt_es": False})
        assert get("beispielreise/buchung/U-01", geheim) == (200, {"gibt_es": False})
    finally:
        server.shutdown()
        sb.Dienst.schreiber = None


def test_sperre_je_reise_und_begrenzte_wartezeit(repo, monkeypatch):
    import fcntl
    wurzel, _, arbeit, _ = repo
    s = sb.Schreiber(wurzel, arbeit)
    monkeypatch.setattr(sb, "ZEIT_SPERRE", 0.2)
    anfrage = {**IDA, "args": {"bezeichnung": "Refugi", "grundform": "aufenthalt"}}
    with open(sb.sperrdatei("beispielreise"), "w") as f:      # ein Vorgang dieser Reise hängt
        fcntl.flock(f, fcntl.LOCK_EX)
        code, a = sb.anwenden_extern(s, "beispielreise", "art_definieren", anfrage)
        assert code == 429 and not a["ok"] and "gleich noch einmal" in a["fehler"]
        # eine andere Reise wartet nicht darauf (hier: gibt es im Repo nicht, aber die Sperre hält sie nicht auf)
        code, a = sb.anwenden_extern(s, "andere-reise", "art_definieren", anfrage)
        assert code == 422 and "does not exist in the repo" in a["fehler"]
    code, a = sb.anwenden_extern(s, "beispielreise", "art_definieren", anfrage)
    assert code == 200 and a["ok"]


def test_ablehnungsgrund_steht_im_protokoll(repo, capsys):
    wurzel, _, arbeit, _ = repo
    s = sb.Schreiber(wurzel, arbeit)
    code, a = sb.anwenden_extern(s, "beispielreise", "art_definieren", {**KARL, "args": {"bezeichnung": "X", "grundform": "aufenthalt"}})
    assert code == 422
    err = capsys.readouterr().err
    zeile = next(z for z in err.splitlines() if z.startswith("Abgelehnt"))
    assert zeile.startswith("Abgelehnt art_definieren 422: ") and "organisers" in zeile and len(zeile) < 260


def _abbruch_im_anwenden(repo, monkeypatch, capsys, origin_kaputt=True):
    """Ein Vorgang, dessen Anwenden die Frist überschreitet (Arbeitskopie steht, Vorbereiten tut nichts). -> (Code, Antwort, Protokoll)"""
    wurzel, _, arbeit, _ = repo
    s = sb.Schreiber(wurzel, arbeit)
    anfrage = {**IDA, "args": {"bezeichnung": "X", "grundform": "aufenthalt"}}
    sb.anwenden_extern(s, "beispielreise", "art_definieren", {**anfrage, "args": {"bezeichnung": "Vorlauf", "grundform": "aufenthalt"}})
    capsys.readouterr()
    if origin_kaputt:
        git(wurzel, "remote", "set-url", "origin", str(wurzel / "gibt-es-nicht.git"))   # die Ergebnisprüfung kommt nicht ans Ziel
    monkeypatch.setattr(sb.Schreiber, "vorbereiten", lambda self: None)
    monkeypatch.setattr(sb, "ZEIT_GESAMT", 0.05)
    code, a = sb.anwenden_extern(s, "beispielreise", "art_definieren", anfrage)
    return code, a, capsys.readouterr().err


def test_zu_langsamer_vorgang_gibt_meldung_in_der_zeit(repo, monkeypatch, capsys):
    code, a, err = _abbruch_im_anwenden(repo, monkeypatch, capsys)
    assert code == 504 and not a["ok"] and "prüfen, ob es angekommen ist" in a["fehler"]
    assert "Zeit art_definieren 504: abgebrochen, ungeprüft" in err


def test_arten_text_ist_die_form_der_datei():
    text = sb.arten_text({"hotel": {"grundform": "aufenthalt", "name": "Hotel", "merkmale": {"preis": {"name": "Preis", "typ": "geld"}}}},
                         "Probe.")
    assert text.startswith("# Arten und Merkmale dieser Reise (docs/ontologie.md, ADR-0001). Probe.\n")
    assert yaml.safe_load(text) == {"arten": {"hotel": {"grundform": "aufenthalt", "name": "Hotel",
                                                        "merkmale": {"preis": {"name": "Preis", "typ": "geld"}}}}}
    assert "&id" not in sb.arten_text({"a": {"merkmale": {"x": {"werte": ["j", "n"]}, "y": {"werte": ["j", "n"]}}}}, "")


def test_aufruf_anwenden(repo, capsys):
    wurzel, origin, arbeit, _ = repo
    s = sb.Schreiber(wurzel, arbeit)
    s.vorbereiten()
    anfrage = json.dumps({**IDA, "args": {"bezeichnung": "Refugi", "grundform": "aufenthalt"}})
    r = subprocess.run([sys.executable, str(WURZEL / "engine/schreiben.py"), "anwenden", "beispielreise", "art_definieren"],
                       input=anfrage, capture_output=True, text=True, env=dict(os.environ))
    code, a = json.loads(r.stdout)
    assert code == 200 and a["ok"], r.stderr
    assert "refugi" in arten_auf_main(origin)[0]
    assert sb.main(["vorbereiten"]) == 0 and "steht auf" in capsys.readouterr().out
    assert sb.main([]) == 1


# ---------- Werte an Dingen (plan/routen.yaml) ----------

def routen_auf_main(origin):
    text = subprocess.run(["git", "-C", str(origin), "show", "main:reisen/beispielreise/plan/routen.yaml"],
                          check=True, capture_output=True, text=True).stdout
    return yaml.safe_load(text), text


def test_wert_eintragen_an_unterkunft_strecke_und_option(repo):
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    vorher = routen_auf_main(origin)[1]
    a = s.schreiben("beispielreise", "wert_eintragen", {**KARL, "args": {"ziel": "U-02", "merkmal": "preis", "wert": "95 €",
                                                                         "quelle": "Website der Pension", "geprueft": "2026-10-29"}})
    assert a["ok"] and a["text"].startswith("Preis pro Nacht an U-02 Pension Burgblick: 95 € (vorher: 85 €). Herkunft: Website der Pension, geprüft 2026-10-29.")
    r, text = routen_auf_main(origin)
    assert r["unterkuenfte"]["U-02"]["merkmale"]["preis"] == {"wert": "95 €", "geprueft": datetime.date(2026, 10, 29), "quelle": "Website der Pension"}
    assert r["unterkuenfte"]["U-02"]["merkmale"]["fruehstueck"] == {"wert": "inklusive", "quelle": "erfunden (Beispiel)", "notiz": "Beispielwert, erfunden"}   # Nachbarn unberührt
    assert "# Alle Unterkünfte sind erfunden" in text and "# Buchungsstand: aus der Buchung B-01" in text        # Kommentare bleiben
    assert git(origin, "log", "-1", "--format=%s", "main") == "Beispielreise – Malerweg in vier Tagen: U-02 Pension Burgblick: Preis pro Nacht „85 €“ → „95 €“"
    assert "Karl (mitwirkend)" in git(origin, "log", "-1", "--format=%b", "main")
    # Nur die geänderte Stelle: der Rest der Datei ist zeichengleich
    import difflib
    diff = [z for z in difflib.unified_diff(vorher.splitlines(), text.splitlines(), lineterm="", n=0) if z[:1] in "+-" and z[:3] not in ("+++", "---")]
    assert diff == ['-      preis: {wert: "85 €", quelle: "erfunden (Beispiel)", notiz: "Beispielwert, erfunden"}',
                    '+      preis: {wert: "95 €", geprueft: 2026-10-29, quelle: "Website der Pension"}']
    # Werte je Datum: der Eintrag für den 15.5. wird ersetzt, der Eintrag ohne gilt bleibt
    s.vorbereiten()
    a = s.schreiben("beispielreise", "wert_eintragen", {**IDA, "args": {"ziel": "U-01", "merkmal": "preis", "quelle": "Booking", "geprueft": "2026-10-29",
                                                                        "werte": [{"wert": "150 €", "gilt": ["2027-05-15", "2027-05-16"]}]}})
    assert "150 € (am 15.05., 16.05.) (vorher: 140 € (am 15.05.))" in a["text"]
    r, text = routen_auf_main(origin)
    assert r["unterkuenfte"]["U-01"]["merkmale"]["preis"] == [
        {"wert": "120 €", "quelle": "erfunden (Beispiel)", "notiz": "Beispielwert, erfunden"},
        {"wert": "150 €", "gilt": [datetime.date(2027, 5, 15), datetime.date(2027, 5, 16)], "geprueft": datetime.date(2026, 10, 29), "quelle": "Booking"}]
    assert '- {wert: "150 €", gilt: [2027-05-15, 2027-05-16], geprueft: 2026-10-29, quelle: "Booking"}' in text
    # Strecke ohne bisherige Merkmale, Option einer Wahlstelle
    s.vorbereiten()
    a = s.schreiben("beispielreise", "wert_eintragen", {**IDA, "args": {"ziel": "E-22", "merkmal": "dauer", "wert": "ca. 25 min", "quelle": "Fahrplan 2027",
                                                                        "geprueft": "2026-10-29", "notiz": "Sommerfahrplan"}})
    r, _ = routen_auf_main(origin)
    assert r["strecken"]["E-22"]["merkmale"] == {"dauer": {"wert": "ca. 25 min", "geprueft": datetime.date(2026, 10, 29), "quelle": "Fahrplan 2027", "notiz": "Sommerfahrplan"}}
    s.vorbereiten()
    a = s.schreiben("beispielreise", "wert_eintragen", {**IDA, "args": {"ziel": "V-03.a", "merkmal": "lage", "wert": "oben am Markt", "quelle": "Ida im Gespräch"}})
    r, _ = routen_auf_main(origin)
    o = next(o for o in r["wahlstellen"]["V-03"]["optionen"] if o["id"] == "V-03.a")
    assert o["merkmale"]["lage"] == {"wert": "oben am Markt", "quelle": "Ida im Gespräch"}
    assert not git(arbeit, "status", "--porcelain")


def test_wert_eintragen_ablehnungen(repo):
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    stand = git(origin, "rev-parse", "main")
    for args, text in (
        ({"ziel": "U-02", "merkmal": "preis", "wert": "95 €", "geprueft": "2026-10-29"}, "„quelle“ fehlt"),
        ({"ziel": "U-02", "merkmal": "preis", "wert": "95 €", "quelle": "x"}, "veränderlich"),
        ({"ziel": "U-02", "merkmal": "preis", "wert": "95 €", "quelle": "x", "geprueft": "gestern"}, "JJJJ-MM-TT"),
        ({"ziel": "U-02", "merkmal": "preis", "wert": "95 €", "quelle": "x", "geprueft": "2099-01-01"}, "Zukunft"),
        ({"ziel": "U-02", "merkmal": "fruehstueck", "wert": "vielleicht", "quelle": "x"}, "erlaubt: inklusive"),
        ({"ziel": "U-02", "merkmal": "pool", "wert": "ja", "quelle": "x"}, "gibt es an U-02 nicht"),
        ({"ziel": "E-01", "merkmal": "gehzeit", "wert": "3 h", "quelle": "x"}, "berechnet"),
        ({"ziel": "U-99", "merkmal": "preis", "wert": "1 €", "quelle": "x", "geprueft": "2026-10-29"}, "gibt es nicht"),
        ({"ziel": "T-01", "merkmal": "preis", "wert": "1 €", "quelle": "x"}, "muss eine Unterkunft"),
        ({"ziel": "U-02", "merkmal": "preis", "quelle": "x", "geprueft": "2026-10-29"}, "„wert“ fehlt"),
        ({"ziel": "U-02", "merkmal": "preis", "quelle": "x", "geprueft": "2026-10-29",
          "werte": [{"wert": "1 €"}, {"wert": "2 €"}]}, "mehrere Werte ohne „gilt“"),
        ({"ziel": "U-02", "merkmal": "preis", "quelle": "x", "geprueft": "2026-10-29",
          "werte": [{"wert": "1 €", "gilt": "2027-05-14"}, {"wert": "2 €", "gilt": ["2027-05-14"]}]}, "zwei Werten"),
    ):
        with pytest.raises(sb.Ablehnung, match=text):
            s.schreiben("beispielreise", "wert_eintragen", {**IDA, "args": args})
        assert not git(arbeit, "status", "--porcelain"), args
    # Gäste schreiben nicht
    with pytest.raises(sb.Ablehnung, match="nur lesen"):
        s.schreiben("beispielreise", "wert_eintragen", {"person": "mo", "name": "Mo", "rolle": "gast",
                                                        "args": {"ziel": "U-02", "merkmal": "lage", "wert": "x", "quelle": "x"}})
    assert git(origin, "rev-parse", "main") == stand


def test_wert_eintragen_typ_link(repo):
    """Typ link (#165): nur Adressen; der Konnektor kennt den Typ."""
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "bezeichnung": "Buchungsseite", "typ": "link"}})
    assert a["ok"], a
    s.vorbereiten()
    for falsch in ("pension-burgblick.example", "bitte anrufen", "ftp://pension.example/"):
        with pytest.raises(sb.Ablehnung, match="keine Adresse"):
            s.schreiben("beispielreise", "wert_eintragen", {**IDA, "args": {"ziel": "U-02", "merkmal": "buchungsseite", "wert": falsch, "quelle": "x"}})
        assert not git(arbeit, "status", "--porcelain"), falsch
    a = s.schreiben("beispielreise", "wert_eintragen", {**IDA, "args": {"ziel": "U-02", "merkmal": "buchungsseite",
                                                                        "wert": "https://pension-burgblick.example/buchen", "quelle": "Website der Pension"}})
    assert a["ok"], a
    r, _ = routen_auf_main(origin)
    assert r["unterkuenfte"]["U-02"]["merkmale"]["buchungsseite"]["wert"] == "https://pension-burgblick.example/buchen"


def test_beispielreise_ist_in_normalform():
    """Die Routendatei der Beispielreise geht zeichengleich durch den Schreibweg; so ändert ein Schreibvorgang nur seine Stelle."""
    import io
    p = BEISPIEL / "plan" / "routen.yaml"
    out = io.StringIO()
    sb.yaml_rund().dump(sb.yaml_rund().load(p.read_text(encoding="utf-8")), out)
    assert out.getvalue() == p.read_text(encoding="utf-8")


# ---------- Dinge, Optionen, Wahlstellen, Fragen ----------

def test_ding_option_wahlstelle_und_frage_anlegen(repo):
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "ding_anlegen", {**KARL, "args": {"was": "ort", "titel": "Rathen", "quelle": "Karte", "hinweis": "Kurort"}})
    assert "O-07" in a["text"]
    s.vorbereiten()
    a = s.schreiben("beispielreise", "ding_anlegen", {**KARL, "args": {
        "was": "unterkunft", "titel": "Pension Elbblick", "ort": "O-07", "art": "pension", "quelle": "Website pension-elbblick.example",
        "geprueft": "2026-10-29", "buchungslink": "https://pension-elbblick.example/buchen", "merkmale": {"preis": "90 €", "fruehstueck": "inklusive"}}})
    assert a["text"].startswith("Unterkunft U-05 „Pension Elbblick“ angelegt in Rathen, Art pension, Merkmale: preis, fruehstueck.")
    r, text = routen_auf_main(origin)
    u = r["unterkuenfte"]["U-05"]
    assert u["ort"] == "O-07" and u["art"] == "pension" and "typ" not in u and u["buchungslink"].startswith("https://")
    assert u["merkmale"]["preis"] == {"wert": "90 €", "quelle": "Website pension-elbblick.example", "geprueft": datetime.date(2026, 10, 29)}
    assert r["orte"]["O-07"] == {"name": "Rathen", "hinweis": "Kurort", "quelle": "Karte"}
    ids = yaml.safe_load(subprocess.run(["git", "-C", str(origin), "show", "main:reisen/beispielreise/ids.yaml"], check=True,
                                        capture_output=True, text=True).stdout)
    assert ids["O"] == 7 and ids["U"] == 5                      # Marken steigen, IDs werden nie neu vergeben
    s.vorbereiten()
    a = s.schreiben("beispielreise", "ding_anlegen", {**KARL, "args": {"was": "strecke", "titel": "Fähre Rathen → Stadt Wehlen", "von": "O-07",
                                                                       "nach": "O-02", "art": "bus", "quelle": "Fahrplan"}})
    r, _ = routen_auf_main(origin)
    assert r["strecken"]["E-24"] == {"titel": "Fähre Rathen → Stadt Wehlen", "von": "O-07", "nach": "O-02", "art": "bus", "quelle": "Fahrplan"}
    # Option an bestehender Wahlstelle: Status vorgeschlagen, Verlauf mit Person und Datum
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="quelle fehlt"):   # Herkunft ist Pflicht, keine Ersatzquelle (ADR-0001, Frage 5)
        s.schreiben("beispielreise", "option_anlegen", {**KARL, "args": {"wahlstelle": "V-03", "titel": "Pension Elbblick", "unterkuenfte": ["U-05"]}})
    a = s.schreiben("beispielreise", "option_anlegen", {**KARL, "args": {"wahlstelle": "V-03", "titel": "Pension Elbblick", "unterkuenfte": ["U-05"],
                                                                         "plus": ["Elbblick"], "grund": "Karl kennt sie", "quelle": "Karl im Gespräch"}})
    assert "V-03.c" in a["text"] and "vorgeschlagen" in a["text"]
    r, text = routen_auf_main(origin)
    o = next(o for o in r["wahlstellen"]["V-03"]["optionen"] if o["id"] == "V-03.c")
    assert o["unterkuenfte"] == ["U-05"] and o["plus"] == ["Elbblick"] and o["quelle"] == "Karl im Gespräch"
    assert o["verlauf"] == [{"datum": datetime.date.today(), "status": "vorgeschlagen", "wer": "Karl", "grund": "Karl kennt sie"}]
    assert "wer: Karl, grund:" in text and "&id" not in text
    # Wahlstelle planung ohne Frage: die Frage entsteht mit (offene-fragen.md), Schlüssel bleiben gültig
    s.vorbereiten()
    a = s.schreiben("beispielreise", "wahlstelle_anlegen", {**KARL, "args": {"titel": "Anreise nach Stadt Wehlen", "an": ["T-01"], "art": "bahn",
        "optionen": [{"titel": "S-Bahn wie bisher", "strecken": ["E-20"], "quelle": "Fahrplan"},
                     {"titel": "Mit dem Auto", "text": "Parken in Wehlen", "minus": ["Auto steht vier Tage"], "quelle": "Karl im Gespräch"}]}})
    assert "V-04" in a["text"] and "F-04" in a["text"]
    r, _ = routen_auf_main(origin)
    w = r["wahlstellen"]["V-04"]
    assert w["wann"] == "planung" and w["an"] == ["T-01"] and w["art"] == "bahn" and w["frage"] == "F-04" and "bereich" not in w
    assert [o["id"] for o in w["optionen"]] == ["V-04.a", "V-04.b"] and w["optionen"][1]["minus"] == ["Auto steht vier Tage"]
    fragen = subprocess.run(["git", "-C", str(origin), "show", "main:reisen/beispielreise/offene-fragen.md"], check=True, capture_output=True, text=True).stdout
    assert "| F-04 | Anreise nach Stadt Wehlen: welche Option? (V-04) | vor Abreise | offen |" in fragen
    s.vorbereiten()
    a = s.schreiben("beispielreise", "frage_anlegen", {**KARL, "args": {"text": "Hat die Pension im Mai offen?", "bis": "März 2027", "bezug": ["U-05"]}})
    assert a["text"].startswith("Offene Frage F-05 angelegt: Hat die Pension im Mai offen? (U-05), bis März 2027")
    assert not git(arbeit, "status", "--porcelain")


def test_lage_eintragen(repo):
    """ADR-0004: Adresse und Koordinaten mit Herkunft und Prüfdatum; ohne quelle, ohne Angabe oder falsch: abgelehnt."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "lage_eintragen", {**KARL, "args": {"ziel": "U-02", "adresse": "Burgstraße 1, 01848 Hohnstein",
                    "koordinaten": "50.9792, 14.1128", "quelle": "erfunden (Beispiel)", "geprueft": "2026-10-29"}})
    assert "Adresse „Burgstraße 1, 01848 Hohnstein“" in a["text"] and "Koordinaten „50.9792, 14.1128“" in a["text"]
    r, _ = routen_auf_main(origin)
    u = r["unterkuenfte"]["U-02"]
    assert u["adresse"]["wert"] == "Burgstraße 1, 01848 Hohnstein" and u["adresse"]["quelle"] == "erfunden (Beispiel)"
    assert u["punkt"]["wert"] == [50.9792, 14.1128] and str(u["punkt"]["geprueft"]) == "2026-10-29"
    s.vorbereiten()
    for args, text in (({"ziel": "U-02", "adresse": "x"}, "„quelle“ fehlt"), ({"ziel": "U-02", "quelle": "x"}, "adresse"),
                       ({"ziel": "U-02", "koordinaten": "91, 0", "quelle": "x"}, "Breite, Länge"), ({"ziel": "O-01", "adresse": "x", "quelle": "x"}, "Unterkunft U-")):
        with pytest.raises(sb.Ablehnung, match=text):
            s.schreiben("beispielreise", "lage_eintragen", {**KARL, "args": args})


def test_uhrzeit_beginn_ende(repo):
    """beginn und ende eines Aufenthalts (#77, Kalender): Uhrzeit HH:MM, leer entfernt, ende nur mit beginn."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "ding_aendern", {**KARL, "args": {"ziel": "A-01", "beginn": "9:05", "ende": "09:52"}})
    assert "beginn „16:00“ → „09:05“" in a["text"] and "ende „18:00“ → „09:52“" in a["text"]
    r, text = routen_auf_main(origin)
    assert (r["aufenthalte"]["A-01"]["beginn"], r["aufenthalte"]["A-01"]["ende"]) == ("09:05", "09:52") and 'beginn: "09:05"' in text
    s.vorbereiten()
    a = s.schreiben("beispielreise", "ding_aendern", {**KARL, "args": {"ziel": "A-01", "beginn": "", "ende": ""}})
    assert "beginn entfernt" in a["text"]
    r, _ = routen_auf_main(origin)
    assert "beginn" not in r["aufenthalte"]["A-01"] and "ende" not in r["aufenthalte"]["A-01"]
    s.vorbereiten()
    s.schreiben("beispielreise", "ding_anlegen", {**KARL, "args": {"was": "aufenthalt", "titel": "Abendessen", "ort": "O-04",
                                                                    "art": "besichtigung", "beginn": "19:00", "quelle": "Beispiel"}})
    r, _ = routen_auf_main(origin)
    assert any(x.get("beginn") == "19:00" for x in r["aufenthalte"].values())
    s.vorbereiten()
    for args, text in (({"ziel": "A-01", "beginn": "25:00"}, "Uhrzeit HH:MM"), ({"ziel": "A-01", "ende": "10:00"}, "nur zusammen mit")):
        with pytest.raises(sb.Ablehnung, match=text):
            s.schreiben("beispielreise", "ding_aendern", {**KARL, "args": args})


def test_ding_aendern_und_ablehnungen(repo):
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "ding_aendern", {**KARL, "args": {"ziel": "U-02", "hinweis": "Zimmer zur Burg fragen", "buchungslink": "https://burgblick.example"}})
    assert "hinweis „erfunden; Doppelzimmer mit Blick auf die Burg“ → „Zimmer zur Burg fragen“" in a["text"] and "buchungslink „https://burgblick.example“" in a["text"]
    r, text = routen_auf_main(origin)
    assert r["unterkuenfte"]["U-02"]["hinweis"] == "Zimmer zur Burg fragen" and r["unterkuenfte"]["U-02"]["merkmale"]["preis"]["wert"] == "85 €"
    assert "# Alle Unterkünfte sind erfunden" in text
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="nur Organisator:innen"):
        s.schreiben("beispielreise", "ding_aendern", {**KARL, "args": {"ziel": "U-02", "art": "hotel"}})
    # Die neue Art muss zu den eingetragenen Werten passen (Hotel kennt kein Abendessen): der Probebau lehnt ab
    with pytest.raises(sb.Ablehnung, match="abendessen"):
        s.schreiben("beispielreise", "ding_aendern", {**IDA, "args": {"ziel": "U-02", "art": "hotel", "grund": "ist ein Hotel"}})
    a = s.schreiben("beispielreise", "ding_aendern", {**IDA, "args": {"ziel": "U-03", "art": "pension", "grund": "eher eine Pension"}})
    assert "art „gasthof“ → „pension“" in a["text"] and "Grund: eher eine Pension" in a["text"]
    r, _ = routen_auf_main(origin)
    assert r["unterkuenfte"]["U-03"]["art"] == "pension" and "typ" not in r["unterkuenfte"]["U-03"]
    s.vorbereiten()
    a = s.schreiben("beispielreise", "ding_aendern", {**KARL, "args": {"ziel": "O-03", "neuer_name": "Hohnstein (Sächs. Schweiz)", "hinweis": ""}})
    r, _ = routen_auf_main(origin)
    assert r["orte"]["O-03"] == {"name": "Hohnstein (Sächs. Schweiz)", "quelle": "OpenStreetMap; Hinweis Wikipedia (W-05)"}
    s.vorbereiten()
    stand = git(origin, "rev-parse", "main")
    for werkzeug, args, text in (
        ("ding_aendern", {"ziel": "U-02"}, "Nichts zu ändern"),
        ("ding_aendern", {"ziel": "T-01", "hinweis": "x"}, "muss eine Unterkunft"),
        ("ding_aendern", {"ziel": "U-02", "ort": "O-99"}, "gibt es nicht"),
        ("ding_anlegen", {"was": "unterkunft", "titel": "X", "ort": "O-01", "art": "bahn", "quelle": "x"}, "Aufenthalts-Art"),
        ("ding_anlegen", {"was": "unterkunft", "titel": "X", "ort": "O-01", "art": "pension"}, "„quelle“ fehlt"),
        ("ding_anlegen", {"was": "unterkunft", "titel": "X", "ort": "O-01", "art": "pension", "quelle": "x", "merkmale": {"preis": "1 €"}}, "veränderlich"),
        ("ding_anlegen", {"was": "unterkunft", "titel": "X", "ort": "O-01", "art": "pension", "quelle": "x", "merkmale": {"pool": "ja"}}, "merkmal_definieren"),
        ("ding_anlegen", {"was": "strecke", "titel": "X", "von": "O-01", "nach": "O-02", "art": "pension", "quelle": "x"}, "Bewegungs-Art"),
        ("ding_anlegen", {"was": "zelt", "titel": "X", "quelle": "x"}, "unterkunft, aufenthalt"),
        ("option_anlegen", {"wahlstelle": "V-03", "titel": "X", "unterkuenfte": ["U-02"], "strecken": ["E-01"]}, "nur eines von"),
        ("option_anlegen", {"wahlstelle": "V-03", "titel": "X", "erfordert": ["V-09.z"]}, "gibt es nicht"),
        ("option_anlegen", {"wahlstelle": "V-99", "titel": "X"}, "gibt es nicht"),
        ("wahlstelle_anlegen", {"titel": "X", "optionen": []}, "mindestens eine Option"),
        ("wahlstelle_anlegen", {"titel": "X", "an": ["T-77"], "optionen": [{"titel": "a"}]}, "gibt es nicht"),
        ("wahlstelle_anlegen", {"titel": "X", "wann": "vielleicht", "optionen": [{"titel": "a", "quelle": "x"}]}, "planung"),
        ("wahlstelle_anlegen", {"titel": "X", "art": "schloss", "optionen": [{"titel": "a", "quelle": "x"}]}, "Art dieser Reise"),
        ("wahlstelle_anlegen", {"titel": "X", "optionen": [{"titel": "a"}]}, "quelle fehlt"),
        ("frage_anlegen", {"bis": "morgen"}, "„text“ fehlt"),
    ):
        with pytest.raises(sb.Ablehnung, match=text):
            s.schreiben("beispielreise", werkzeug, {**IDA, "args": args})
        assert not git(arbeit, "status", "--porcelain"), (werkzeug, args)
    assert git(origin, "rev-parse", "main") == stand


# ---------- Entscheiden und Plan ----------

def fragen_auf_main(origin):
    return subprocess.run(["git", "-C", str(origin), "show", "main:reisen/beispielreise/offene-fragen.md"], check=True,
                          capture_output=True, text=True).stdout


def test_entscheiden_schreibt_verlauf_und_klaert_die_frage(repo):
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    heute = datetime.date.today()
    a = s.schreiben("beispielreise", "entscheiden", {**IDA, "args": {"option": "V-01.b", "status": "gewaehlt",
                                                                     "grund": "Karl möchte mit der Bahn fahren", "quelle": "Gespräch"}})
    assert a["text"].startswith("Entschieden: V-01.b „Zum Lichtenhainer Wasserfall") and "ist gewählt (Ida," in a["text"] and "Frage F-01 ist damit geklärt" in a["text"]
    r, text = routen_auf_main(origin)
    o = next(o for o in r["wahlstellen"]["V-01"]["optionen"] if o["id"] == "V-01.b")
    assert o["verlauf"][-1] == {"datum": heute, "status": "gewaehlt", "wer": "Ida", "grund": "Karl möchte mit der Bahn fahren (Quelle: Gespräch)"}
    assert len(o["verlauf"]) == 3                                   # die alten Einträge bleiben
    # Die übrigen Optionen der Wahlstelle sind damit nicht gewählt: ersetzt durch die gewählte, mit Verlauf
    assert "Nicht gewählt und damit ausgeschieden: V-01.a" in a["text"]
    a_opt = next(x for x in r["wahlstellen"]["V-01"]["optionen"] if x["id"] == "V-01.a")
    assert a_opt["verlauf"][-1] == {"datum": heute, "status": "ersetzt", "wer": "Ida", "durch": "V-01.b",
                                    "grund": "nicht gewählt, V-01.b „Zum Lichtenhainer Wasserfall und mit der Kirnitzschtalbahn zurück (Plan B)“ ist gewählt"}
    assert f"| vor Abreise | geklärt {heute.strftime('%-d.%-m.%Y')}: Ida, Zum Lichtenhainer Wasserfall" in fragen_auf_main(origin)
    assert git(origin, "log", "-1", "--format=%s", "main").endswith("V-01.b „Zum Lichtenhainer Wasserfall und mit der Kirnitzschtalbahn zurück (Plan B)“ gewählt")
    # gewählt an einer Wahlstelle mit gewählter Option: die alte wird ersetzt (eigener Verlaufseintrag), die Frage bleibt geklärt
    s.vorbereiten()
    a = s.schreiben("beispielreise", "entscheiden", {**IDA, "args": {"option": "V-03.b", "status": "gewaehlt", "grund": "Abendessen im Haus"}})
    assert "Bisher gewählt und dadurch ersetzt: V-03.a" in a["text"]
    r, _ = routen_auf_main(origin)
    opts = {o["id"]: o for o in r["wahlstellen"]["V-03"]["optionen"]}
    assert opts["V-03.a"]["verlauf"][-1]["status"] == "ersetzt" and opts["V-03.a"]["verlauf"][-1]["durch"] == "V-03.b"
    assert opts["V-03.b"]["verlauf"][-1]["status"] == "gewaehlt"
    assert "| F-02 | Unterkunft in Hohnstein wählen (Pension Burgblick oder Gasthof Polenztal) | – | geklärt" in fragen_auf_main(origin)
    assert "Gasthof Polenztal (V-03.b)" in fragen_auf_main(origin)
    # Alle Optionen ungültig (V-03.a ersetzt, V-03.b verworfen): der Probebau lehnt ab, nichts geändert
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="alle Optionen sind verworfen"):
        s.schreiben("beispielreise", "entscheiden", {**IDA, "args": {"option": "V-03.b", "status": "verworfen", "grund": "doch zu laut"}})
    assert not git(arbeit, "status", "--porcelain")
    # verworfen ohne verbleibende Wahl (V-01.a bleibt vorgeschlagen): Wahlstelle offen, Frage wieder offen
    a = s.schreiben("beispielreise", "entscheiden", {**IDA, "args": {"option": "V-01.b", "status": "verworfen", "grund": "Fahrplan passt nicht"}})
    assert "V-01 ist danach offen, Frage F-01 wieder offen" in a["text"]
    assert "Wieder offen: V-01.a" in a["text"]                      # was nur wegen dieser Wahl ausschied, ist wieder im Spiel
    r, _ = routen_auf_main(origin)
    assert next(x for x in r["wahlstellen"]["V-01"]["optionen"] if x["id"] == "V-01.a")["verlauf"][-1]["status"] == "vorgeschlagen"
    assert "| vor Abreise | offen |" in fragen_auf_main(origin)
    s.vorbereiten()
    stand = git(origin, "rev-parse", "main")
    for args, text in (
        ({"option": "V-01.b", "status": "verworfen", "grund": "x"}, "schon verworfen"),
        ({"option": "V-01.a", "status": "ersetzt", "grund": "x"}, "ersetzt_durch"),
        ({"option": "V-01.a", "status": "ersetzt", "ersetzt_durch": "V-03.b", "grund": "x"}, "derselben Wahlstelle"),
        ({"option": "V-01.a", "status": "verworfen", "ersetzt_durch": "V-01.b", "grund": "x"}, "nur beim Status ersetzt"),
        ({"option": "V-01.a", "status": "favorisiert", "grund": "x"}, "„status“ muss"),
        ({"option": "V-01.a", "status": "verworfen"}, "„grund“ fehlt"),
        ({"option": "V-99.a", "status": "gewaehlt", "grund": "x"}, "gibt es nicht"),
        ({"option": "V-01", "status": "gewaehlt", "grund": "x"}, "muss eine Option"),
    ):
        with pytest.raises(sb.Ablehnung, match=text):
            s.schreiben("beispielreise", "entscheiden", {**IDA, "args": args})
        assert not git(arbeit, "status", "--porcelain"), args
    with pytest.raises(sb.Ablehnung, match="nur Organisator:innen"):
        s.schreiben("beispielreise", "entscheiden", {**KARL, "args": {"option": "V-01.a", "status": "verworfen", "grund": "x"}})
    assert git(origin, "rev-parse", "main") == stand


def test_tag_aendern_nur_organisator(repo):
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    with pytest.raises(sb.Ablehnung, match="nur Organisator:innen"):
        s.schreiben("beispielreise", "tag_aendern", {**KARL, "args": {"ziel": "T-03", "nacht": "V-03"}})
    a = s.schreiben("beispielreise", "tag_aendern", {**IDA, "args": {"ziel": "T-03", "nacht": "V-03", "text": "Nacht jetzt zur Wahl", "grund": "Probe"}})
    assert "nacht „U-04“ → „V-03“" in a["text"] and "Grund: Probe" in a["text"]
    r, text = routen_auf_main(origin)
    assert r["tage"]["T-03"]["nacht"] == "V-03" and r["tage"]["T-03"]["text"] == "Nacht jetzt zur Wahl" and r["tage"]["T-03"]["strecken"] == ["E-02"]
    assert 'T-03: {titel: "Hohnstein → Brand → Altendorf", strecken: [E-02], nacht: V-03, text: "Nacht jetzt zur Wahl"}' in text
    s.vorbereiten()
    a = s.schreiben("beispielreise", "tag_aendern", {**IDA, "args": {"ziel": "T-04", "strecken": ["E-03", "E-23"]}})
    r, _ = routen_auf_main(origin)
    assert r["tage"]["T-04"]["strecken"] == ["E-03", "E-23"]
    s.vorbereiten()
    for args, text in (({"ziel": "T-03", "nacht": "U-99"}, "gibt es nicht"), ({"ziel": "T-03"}, "Nichts zu ändern"),
                       ({"ziel": "T-99", "nacht": "U-01"}, "gibt es nicht"), ({"ziel": "T-03", "nacht": "E-01"}, "„nacht“ ist")):
        with pytest.raises(sb.Ablehnung, match=text):
            s.schreiben("beispielreise", "tag_aendern", {**IDA, "args": args})
    # ein Plan, der nicht aufgeht (Strecke beginnt woanders): der Probebau meldet nur Warnungen, kein Fehler -> geht durch; aber
    # eine Nacht an einem Ort ohne Unterkunft bleibt erlaubt. Hier reicht: die Arbeitskopie ist sauber.
    assert not git(arbeit, "status", "--porcelain")


# ---------- Wissen, Fragen schließen, Personen ----------

def datei_auf_main(origin, rel):
    return subprocess.run(["git", "-C", str(origin), "show", f"main:reisen/beispielreise/{rel}"], check=True, capture_output=True, text=True).stdout


def test_wissen_schreiben_neu_und_ergaenzen(repo):
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    heute = datetime.date.today().strftime("%-d.%-m.%Y")
    a = s.schreiben("beispielreise", "wissen_schreiben", {**KARL, "args": {"titel": "Kirnitzschtalbahn", "text": "Die Bahn fährt seit 1898 durch das Tal.",
                                                                           "quelle": "Wikipedia, Artikel Kirnitzschtalbahn, gelesen heute", "gruppe": "wissen"}})
    assert a["text"].startswith("Neuer Abschnitt W-") and "inhalt/wissen.md" in a["text"]
    wissen = datei_auf_main(origin, "inhalt/wissen.md")
    assert "\n## Kirnitzschtalbahn\n\nDie Bahn fährt seit 1898 durch das Tal.\n\n*Herkunft: Wikipedia, Artikel Kirnitzschtalbahn, gelesen heute; eingetragen am " + heute + " von Karl über den Konnektor.*" in wissen
    cfg = json.loads(datei_auf_main(origin, "reise.json"))
    wid = cfg["abschnitte"]["inhalt/wissen.md"]["Kirnitzschtalbahn"][0]
    assert wid.startswith("W-") and cfg["abschnitte"]["inhalt/wissen.md"]["Kirnitzschtalbahn"][1] == "wissen"
    # Ergänzen eines vorhandenen Abschnitts: der Absatz kommt ans Ende des Abschnitts, vor die nächste Überschrift
    s.vorbereiten()
    a = s.schreiben("beispielreise", "wissen_schreiben", {**IDA, "args": {"abschnitt": "W-05", "text": "Ergänzung zur Geologie.", "quelle": "Ida im Gespräch"}})
    assert a["text"].startswith("Abschnitt W-05 „Elbsandstein in Kürze“ (inhalt/wissen.md) ergänzt.")
    wissen = datei_auf_main(origin, "inhalt/wissen.md")
    i = wissen.index("Ergänzung zur Geologie.")
    start = wissen.index("\n## Elbsandstein in Kürze")
    assert start < i < wissen.index("\n## ", start + 3)          # vor der nächsten Hauptüberschrift, nach den ###-Unterabschnitten
    # Ein vorhandener Titel wird ergänzt statt doppelt angelegt
    a = s.schreiben("beispielreise", "wissen_schreiben", {**IDA, "args": {"titel": "Elbsandstein in Kürze", "text": "Noch ein Absatz.", "quelle": "Ida"}})
    assert a["text"].startswith("Abschnitt W-05 „Elbsandstein in Kürze“")
    s.vorbereiten()
    for args, text in (({"text": "x", "quelle": "y"}, "„titel“"),
                       ({"abschnitt": "W-99", "text": "x", "quelle": "y"}, "gibt es nicht"), ({"titel": "Neu", "text": "x"}, "„quelle“ fehlt"),
                       ({"titel": "Neu", "text": "x", "quelle": "y", "gruppe": "egal"}, "„gruppe“"), ({"titel": "Neu", "text": "x", "quelle": "y", "datei": "../x.md"}, "„datei“")):
        with pytest.raises(sb.Ablehnung, match=text):
            s.schreiben("beispielreise", "wissen_schreiben", {**IDA, "args": args})
    assert not git(arbeit, "status", "--porcelain")


def test_frage_schliessen_und_person_schreiben(repo):
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    heute = datetime.date.today().strftime("%-d.%-m.%Y")
    with pytest.raises(sb.Ablehnung, match="nur Organisator:innen"):
        s.schreiben("beispielreise", "frage_schliessen", {**KARL, "args": {"frage": "F-03", "ergebnis": "x"}})
    a = s.schreiben("beispielreise", "frage_schliessen", {**IDA, "args": {"frage": "F-03", "ergebnis": "Fahrplan steht, Bahn fährt 9:10"}})
    assert f"| F-03 | Fahrplan der S-Bahn" in datei_auf_main(origin, "offene-fragen.md")
    assert f"| April 2027 | geklärt {heute}: Ida, Fahrplan steht, Bahn fährt 9:10 |" in datei_auf_main(origin, "offene-fragen.md")
    s.vorbereiten()
    a = s.schreiben("beispielreise", "frage_schliessen", {**IDA, "args": {"frage": "F-01", "ergebnis": "wird unterwegs entschieden", "status": "entfaellt"}})
    assert "entfällt" in a["text"]
    with pytest.raises(sb.Ablehnung, match="gibt es nicht"):
        s.schreiben("beispielreise", "frage_schliessen", {**IDA, "args": {"frage": "F-77", "ergebnis": "x"}})
    # Personen: anlegen (Rolle höchstens die eigene), ändern, ausscheiden als gast
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="nur Organisator:innen"):      # regeln.einladen (Vorgabe): nur Organisator:innen
        s.schreiben("beispielreise", "person_schreiben", {**KARL, "args": {"schluessel": "anna", "vorname": "Anna", "rolle": "mitwirkend"}})
    a = s.schreiben("beispielreise", "person_schreiben", {**IDA, "args": {"schluessel": "anna", "vorname": "Anna", "rolle": "mitwirkend", "notiz": "eingeladen"}})
    r = yaml.safe_load(datei_auf_main(origin, "reise.yaml"))
    assert r["personen"]["anna"] == {"name": "Anna", "rolle": "mitwirkend", "reist": True, "notiz": "eingeladen"}
    assert "# Rollen" in datei_auf_main(origin, "reise.yaml") or "# Eckdaten" in datei_auf_main(origin, "reise.yaml")   # Kommentare bleiben
    s.vorbereiten()
    a = s.schreiben("beispielreise", "person_schreiben", {**IDA, "args": {"schluessel": "anna", "rolle": "gast", "reist": False, "notiz": "ausgeschieden"}})
    assert "rolle „mitwirkend“ → „gast“" in a["text"]
    r = yaml.safe_load(datei_auf_main(origin, "reise.yaml"))
    assert r["personen"]["anna"]["rolle"] == "gast" and r["personen"]["anna"]["reist"] is False and "karl" in r["personen"]
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="Nichts zu ändern"):
        s.schreiben("beispielreise", "person_schreiben", {**IDA, "args": {"schluessel": "anna", "rolle": "gast"}})
    with pytest.raises(sb.Ablehnung, match="Name „Ida“ kommt zweimal"):
        s.schreiben("beispielreise", "person_schreiben", {**IDA, "args": {"schluessel": "ida2", "vorname": "Ida"}})
    assert not git(arbeit, "status", "--porcelain")


# ---------- Status, Einstellungen, neue Reise ----------

def test_status_und_einstellungen_der_reise(repo):
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    heute = datetime.date.today()
    with pytest.raises(sb.Ablehnung, match="nur Organisator:innen"):
        s.schreiben("beispielreise", "reise_status_setzen", {**KARL, "args": {"status": "fest", "grund": "x"}})
    a = s.schreiben("beispielreise", "reise_status_setzen", {**IDA, "args": {"status": "fest", "grund": "Unterkünfte stehen"}})
    assert a["text"].startswith("Die Reise hat jetzt den Status fest (vorher planung; Ida,")
    r = yaml.safe_load(datei_auf_main(origin, "reise.yaml"))
    assert r["status"]["wert"] == "fest" and r["status"]["verlauf"][-1] == {"datum": heute, "wert": "fest", "wer": "Ida", "grund": "Unterkünfte stehen"}
    assert len(r["status"]["verlauf"]) == 3 and "# Eckdaten" in datei_auf_main(origin, "reise.yaml")
    # Aus dem Archiv zurück geht nur für den Status (alles andere ist dort gesperrt)
    s.vorbereiten()
    s.schreiben("beispielreise", "reise_status_setzen", {**IDA, "args": {"status": "archiv", "grund": "vorbei"}})
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="archiviert"):
        s.schreiben("beispielreise", "frage_anlegen", {**IDA, "args": {"text": "x"}})
    a = s.schreiben("beispielreise", "reise_status_setzen", {**IDA, "args": {"status": "planung", "grund": "doch nochmal"}})
    assert "vorher archiv" in a["text"]
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="schon den Status"):
        s.schreiben("beispielreise", "reise_status_setzen", {**IDA, "args": {"status": "planung", "grund": "x"}})
    with pytest.raises(sb.Ablehnung, match="„status“ muss"):
        s.schreiben("beispielreise", "reise_status_setzen", {**IDA, "args": {"status": "fertig", "grund": "x"}})
    # Einstellungen: Bausteine und Regeln; Unbekanntes lehnt der Schreibweg ab, Falsches der Probebau
    a = s.schreiben("beispielreise", "einstellung_setzen", {**IDA, "args": {"bausteine": ["varianten", "karte", "fragen", "waechter"],
                                                                            "regeln": {"einladen": "mitwirkend", "waechter_frist_tage": "45"}}})
    assert "bausteine" in a["text"] and "regeln.einladen „organisator“ → „mitwirkend“" in a["text"] and "waechter_frist_tage „60“ → „45“" in a["text"]
    r = yaml.safe_load(datei_auf_main(origin, "reise.yaml"))
    assert r["bausteine"] == ["varianten", "karte", "fragen", "waechter"] and r["regeln"]["einladen"] == "mitwirkend" and r["regeln"]["waechter_frist_tage"] == 45
    assert r["regeln"]["kontingent"] == {"art": "punkte", "je_person": 10}     # Bestehendes bleibt
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="Unbekannte Bausteine"):
        s.schreiben("beispielreise", "einstellung_setzen", {**IDA, "args": {"bausteine": ["karte", "zauber"]}})
    with pytest.raises(sb.Ablehnung, match="Unbekannte Regel"):
        s.schreiben("beispielreise", "einstellung_setzen", {**IDA, "args": {"regeln": {"farbe": "rot"}}})
    with pytest.raises(sb.Ablehnung, match="nicht bauen"):
        s.schreiben("beispielreise", "einstellung_setzen", {**IDA, "args": {"regeln": {"einladen": "chef"}}})
    with pytest.raises(sb.Ablehnung, match="Nichts zu ändern"):
        s.schreiben("beispielreise", "einstellung_setzen", {**IDA, "args": {}})
    # Sprache der Reise (ADR-0006): nur bekannte Sprachen, der alte Wert steht im Verlauf der Antwort
    with pytest.raises(sb.Ablehnung, match="Unbekannte Sprache"):
        s.schreiben("beispielreise", "einstellung_setzen", {**IDA, "args": {"sprache": "klingonisch"}})
    a = s.schreiben("beispielreise", "einstellung_setzen", {**IDA, "args": {"sprache": "en", "grund": "Gruppe liest Englisch"}})
    assert "sprache „de“ → „en“" in a["text"]
    assert yaml.safe_load(datei_auf_main(origin, "reise.yaml"))["sprache"] == "en"
    s.vorbereiten()
    # Mitwirkende dürfen jetzt einladen (regeln.einladen = mitwirkend), aber keine höhere Rolle vergeben
    with pytest.raises(sb.Ablehnung, match="höchstens eine Rolle"):
        s.schreiben("beispielreise", "person_schreiben", {**KARL, "args": {"schluessel": "anna", "vorname": "Anna", "rolle": "organisator"}})
    a = s.schreiben("beispielreise", "person_schreiben", {**KARL, "args": {"schluessel": "anna", "vorname": "Anna", "rolle": "mitwirkend"}})
    assert "Anna steht jetzt in der Reise" in a["text"]
    assert not git(arbeit, "status", "--porcelain")


def test_neue_reise_aus_der_anfrage(repo):
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    anfrage = {"id": "A-20261029-120000-abcd", "erstellt": "2026-10-29T12:00:00+00:00", "name": "Ida", "art": "Auftrag",
               "daten": {"neue_reise": {"titel": "Skiwoche im Allgäu", "von": "2027-02-06", "bis": "2027-02-13", "ziel": "Oberstdorf", "pfad": "skiwoche-allgaeu-2027",
                                        "personen": {"ida": {"name": "Ida", "rolle": "organisator"}, "karl": {"name": "Karl", "rolle": "mitwirkend"}},
                                        "wer": "Ida", "notiz": "Idee aus dem Gespräch."}}}
    a = s.schreiben("skiwoche-allgaeu-2027", "reise_anlegen", {"person": None, "name": "Ida", "rolle": "organisator", "args": {"auftrag": anfrage}})
    assert a["ok"] and a["text"].startswith("Die Reise „Skiwoche im Allgäu“ ist angelegt (Ordner skiwoche-allgaeu-2027, Status Idee).")
    assert git(origin, "log", "-1", "--format=%s", "main") == "Reisen: Neue Reise skiwoche-allgaeu-2027 angelegt"
    dateien = subprocess.run(["git", "-C", str(origin), "ls-tree", "-r", "--name-only", "main", "reisen/skiwoche-allgaeu-2027"], check=True, capture_output=True, text=True).stdout
    assert "reisen/skiwoche-allgaeu-2027/reise.yaml" in dateien and "reisen/skiwoche-allgaeu-2027/ids.yaml" in dateien
    r = yaml.safe_load(subprocess.run(["git", "-C", str(origin), "show", "main:reisen/skiwoche-allgaeu-2027/reise.yaml"], check=True, capture_output=True, text=True).stdout)
    assert r["status"]["wert"] == "idee" and r["personen"]["karl"]["rolle"] == "mitwirkend"
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="gibt es schon"):
        s.schreiben("skiwoche-allgaeu-2027", "reise_anlegen", {"person": None, "name": "Ida", "rolle": "organisator", "args": {"auftrag": anfrage}})
    with pytest.raises(sb.Ablehnung, match="keine neue Reise"):
        s.schreiben("x-2027", "reise_anlegen", {"person": None, "name": "Ida", "rolle": "organisator", "args": {}})
    assert not git(arbeit, "status", "--porcelain")


def test_neue_reise_bekommt_beim_ersten_eintrag_einen_plan(repo):
    """Eine Reise aus der App hat noch kein plan/routen.yaml. Der erste Eintrag legt den leeren Plan aus dem Zeitraum
    an, statt abzulehnen; danach lassen sich Orte, Strecken und Tage anlegen, und der Generator baut die Reise."""
    wurzel, origin, arbeit, _ = repo
    s = schreiber(repo)
    anfrage = {"id": "A-20261101-120000-abcd", "erstellt": "2026-11-01T12:00:00+00:00", "name": "Ida", "art": "Auftrag",
               "daten": {"neue_reise": {"titel": "Kurztrip (Beispiel)", "von": "2027-04-10", "bis": "2027-04-12", "ziel": "", "pfad": "kurztrip-2027",
                                        "personen": {"ida": {"name": "Ida", "rolle": "organisator"}}, "wer": "Ida", "notiz": ""}}}
    s.schreiben("kurztrip-2027", "reise_anlegen", {"person": None, "name": "Ida", "rolle": "organisator", "args": {"auftrag": anfrage}})
    s.vorbereiten()
    a = s.schreiben("kurztrip-2027", "ding_anlegen", {**IDA, "args": {"was": "ort", "titel": "Dresden", "quelle": "Karte", "ausserhalb": True}})
    assert "O-01" in a["text"], a["text"]
    s.vorbereiten()
    s.schreiben("kurztrip-2027", "ding_anlegen", {**IDA, "args": {"was": "ort", "titel": "Prag", "quelle": "Karte"}})
    s.vorbereiten()
    s.schreiben("kurztrip-2027", "art_definieren", {**IDA, "args": {"art": "bus", "bezeichnung": "Bus", "grundform": "bewegung"}})
    s.vorbereiten()
    a = s.schreiben("kurztrip-2027", "ding_anlegen", {**IDA, "args": {"was": "strecke", "titel": "Bus Dresden → Prag", "von": "O-01",
                                                                       "nach": "O-02", "art": "bus", "ab": "08:00", "an": "10:30", "quelle": "Fahrplan"}})
    assert "E-01" in a["text"], a["text"]
    s.vorbereiten()
    a = s.schreiben("kurztrip-2027", "tag_anlegen", {**IDA, "args": {"titel": "Anreise (Beispiel)", "strecken": ["E-01"]}})
    assert "T-01" in a["text"], a["text"]
    text = git(origin, "show", "main:reisen/kurztrip-2027/plan/routen.yaml")
    r = yaml.safe_load(text)
    assert r["start"] == {"datum": datetime.date(2027, 4, 10)} and r["ende"] == {"datum": datetime.date(2027, 4, 12)}
    assert r["orte"]["O-01"]["ausserhalb"] is True and r["route"] == ["T-01"] and r["tage"]["T-01"]["strecken"] == ["E-01"]
    assert json.loads(git(origin, "show", "main:reisen/kurztrip-2027/reise.json"))["routen"] == {"datei": "plan/routen.yaml"}
    # der Generator baut die Reise mit dem Plan: der Tag steht auf der Seite
    import bauen
    git(wurzel, "pull", "-q")
    d = bauen.Bauer(wurzel / "reisen" / "kurztrip-2027", str(wurzel / "dist")).daten()
    assert [t["id"] for t in d["route"]["tage"]] == ["T-01"]
    assert not git(arbeit, "status", "--porcelain")


def test_aufenthalt_ohne_nacht_anlegen_an_den_tag_haengen_und_buchen(repo):
    """Paket O-5: ding_anlegen was=aufenthalt (A-…, Ort, Aufenthalts-Art, Zeit), tag_aendern aufenthalte; der Buchungsstand
    kommt nur noch aus einer Buchung (buchung_anlegen, 29.10.2026), das freie Feld buchung lehnt der Schreibweg ab."""
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "ding_anlegen", {**KARL, "args": {
        "was": "aufenthalt", "titel": "Festung Königstein", "ort": "O-05", "art": "besichtigung", "zeit": "14–16 Uhr",
        "quelle": "erfunden (Test)", "geprueft": "2026-10-29", "merkmale": {"geoeffnet": "ja"}}})
    assert a["text"].startswith("Aufenthalt A-02 „Festung Königstein“ angelegt in Bad Schandau, Art besichtigung, Merkmale: geoeffnet.")
    assert "tag_aendern" in a["text"]
    r, _ = routen_auf_main(origin)
    x = r["aufenthalte"]["A-02"]
    assert x["ort"] == "O-05" and x["art"] == "besichtigung" and x["zeit"] == "14–16 Uhr" and "typ" not in x
    s.vorbereiten()
    a = s.schreiben("beispielreise", "tag_aendern", {**IDA, "args": {"ziel": "T-04", "aufenthalte": ["A-02"]}})
    assert "aufenthalte [] → ['A-02']" in a["text"]
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="nur als Buchung"):
        s.schreiben("beispielreise", "ding_aendern", {**KARL, "args": {"ziel": "A-02", "buchung": "Zeitfenster 14 Uhr gebucht"}})
    with pytest.raises(sb.Ablehnung, match="nur als Buchung"):
        s.schreiben("beispielreise", "ding_anlegen", {**KARL, "args": {"was": "aufenthalt", "titel": "y", "ort": "O-05", "art": "besichtigung",
                                                                       "quelle": "x", "buchung": "gebucht"}})
    a = s.schreiben("beispielreise", "buchung_anlegen", {**KARL, "args": {"fuer": "A-02", "status": "gebucht", "nummer": "Z-14",
                                                                          "quelle": "Zeitfenster-Ticket per Mail (Test)"}})
    assert a["ok"]
    r, _ = routen_auf_main(origin)
    assert r["tage"]["T-04"]["aufenthalte"] == ["A-02"] and "buchung" not in r["aufenthalte"]["A-02"]
    assert r["buchungen"]["B-04"]["fuer"] == ["A-02"] and r["buchungen"]["B-04"]["status"] == "gebucht"
    with pytest.raises(Exception, match="Aufenthalts-Art"):
        s.vorbereiten()
        s.schreiben("beispielreise", "ding_anlegen", {**KARL, "args": {"was": "aufenthalt", "titel": "x", "ort": "O-05", "art": "bahn", "quelle": "x"}})


def test_merkmale_der_buchung_definieren(repo):
    """#166: merkmal_definieren mit fuer: buchung legt Merkmale der Buchungen einer Art an (buchung_merkmale); ohne Stufe,
    Rolle und Prüfdatum. art_definieren lässt sie stehen."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "fuer": "buchung", "bezeichnung": "Zimmer",
                                                                            "frage": "Welches Zimmer habt ihr bekommen?"}})
    assert "Merkmal der Buchung „Zimmer“ (zimmer) an der Art Pension angelegt: Typ text" in a["text"]
    arten, text = arten_auf_main(origin)
    assert arten["pension"]["buchung_merkmale"] == {"zimmer": {"name": "Zimmer", "typ": "text", "frage": "Welches Zimmer habt ihr bekommen?"}}
    assert "zimmer" not in arten["pension"]["merkmale"] and "buchung_merkmale" in text.split("arten:")[0]   # Kopf nennt die Form
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="„stufe“ gibt es bei Merkmalen der Buchung nicht"):
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "fuer": "buchung", "bezeichnung": "X", "stufe": "pflicht"}})
    with pytest.raises(sb.Ablehnung, match="„fuer“ ist ding"):
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "fuer": "reise", "bezeichnung": "X"}})
    with pytest.raises(sb.Ablehnung, match="braucht „werte“"):
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "fuer": "buchung", "bezeichnung": "Tarif", "typ": "auswahl"}})
    with pytest.raises(sb.Ablehnung, match="schon, und nichts"):
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "fuer": "buchung", "merkmal": "zimmer"}})
    a = s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "fuer": "buchung", "merkmal": "zimmer",
                                                                            "typ": "auswahl", "werte": ["Einzel", "Doppel"]}})
    assert "geändert: Typ auswahl, Werte Einzel | Doppel" in a["text"]
    s.vorbereiten()
    s.schreiben("beispielreise", "art_definieren", {**IDA, "args": {"art": "pension", "beschreibung": "kleines Haus"}})
    arten, _ = arten_auf_main(origin)
    assert arten["pension"]["buchung_merkmale"]["zimmer"]["werte"] == ["Einzel", "Doppel"] and arten["pension"]["beschreibung"] == "kleines Haus"


def test_buchung_mit_zahlstand_und_merkmalen(repo):
    """#166 (Product Owner 31.10.2026): zahlung ist ein festes Feld mit festen Werten (englische Aliase bei der Eingabe, gespeichert
    deutsch); merkmale nur die, die die Arten der Dinge für Buchungen festlegen (Beispielreise: Bahn mit Ticketart und Wagen)."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    for args, grund in (({"zahlung": "teilweise"}, "„zahlung“ muss einer von offen, angezahlt"),
                        ({"zahlung": "refunded"}, "erstattet gibt es nur bei einer stornierten"),
                        ({"merkmale": {"klasse": "1"}}, "„klasse“ ist kein Merkmal der Buchung bei bahn"),
                        ({"merkmale": {"ticketart": "First"}}, "Ticketart: „First“ steht nicht unter den Werten"),
                        ({"merkmale": "Sparpreis"}, "„merkmale“ ist {Merkmal: Wert}")):
        with pytest.raises(sb.Ablehnung, match=grund):
            s.schreiben("beispielreise", "buchung_anlegen", {**KARL, "args": {"fuer": ["E-21"], "quelle": "Mail", **args}})
    with pytest.raises(sb.Ablehnung, match="Für Buchungen der Art hotel sind keine Merkmale festgelegt"):
        s.schreiben("beispielreise", "buchung_anlegen", {**KARL, "args": {"fuer": ["U-01"], "quelle": "Mail", "merkmale": {"zimmer": "12"}}})
    a = s.schreiben("beispielreise", "buchung_anlegen", {**KARL, "args": {
        "fuer": ["E-21"], "preis": "39,80 €", "zahlung": "deposit", "bezahlt": "20 € an", "merkmale": {"Ticketart": "sparpreis", "wagen": ""},
        "quelle": "Bestätigung bahn.de (Test)"}})
    assert "Preis 39,80 €, Zahlung angezahlt (20 € an), Ticketart: Sparpreis." in a["text"]
    r, text = routen_auf_main(origin)
    b = r["buchungen"]["B-04"]
    assert b["zahlung"] == "angezahlt" and b["bezahlt"] == "20 € an" and b["merkmale"] == {"ticketart": "Sparpreis"}
    assert list(b)[:6] == ["fuer", "status", "preis", "zahlung", "bezahlt", "gebucht_am"] and list(b).index("merkmale") == list(b).index("wer") - 1
    assert "merkmale: {ticketart: Sparpreis}" in text
    # Ändern: Zahlstand mit Wort und Alias, Merkmale einzeln (leer entfernt eines), Verlauf nennt die Namen
    s.vorbereiten()
    a = s.schreiben("beispielreise", "buchung_aendern", {**KARL, "args": {"ziel": "B-04", "zahlung": "paid",
                                                                          "merkmale": {"wagen": "Wagen 5, Platz 61", "ticketart": ""}}})
    assert "Zahlung „angezahlt“ → „bezahlt“" in a["text"] and "Merkmale Wagen und Platz: Wagen 5, Platz 61; Ticketart entfernt" in a["text"]
    r, _ = routen_auf_main(origin)
    b = r["buchungen"]["B-04"]
    assert b["zahlung"] == "bezahlt" and b["merkmale"] == {"wagen": "Wagen 5, Platz 61"}
    assert b["verlauf"][-1]["was"] == "Zahlung; Wagen und Platz, Ticketart"
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="erstattet gibt es nur bei einer stornierten"):
        s.schreiben("beispielreise", "buchung_aendern", {**KARL, "args": {"ziel": "B-04", "zahlung": "erstattet"}})
    a = s.schreiben("beispielreise", "buchung_aendern", {**KARL, "args": {"ziel": "B-04", "status": "storniert", "zahlung": "erstattet",
                                                                          "grund": "Zug fällt aus"}})
    assert "Zahlung „bezahlt“ → „erstattet“" in a["text"]
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="erstattet gibt es nur bei einer stornierten"):
        s.schreiben("beispielreise", "buchung_aendern", {**KARL, "args": {"ziel": "B-04", "status": "gebucht"}})
    a = s.schreiben("beispielreise", "buchung_aendern", {**KARL, "args": {"ziel": "B-04", "status": "gebucht", "zahlung": "Vor Ort",
                                                                          "merkmale": {"wagen": ""}}})
    r, text = routen_auf_main(origin)
    assert r["buchungen"]["B-04"]["zahlung"] == "vor_ort" and "merkmale" not in r["buchungen"]["B-04"]
    s.vorbereiten()
    s.schreiben("beispielreise", "buchung_aendern", {**KARL, "args": {"ziel": "B-04", "zahlung": ""}})
    r, _ = routen_auf_main(origin)
    assert "zahlung" not in r["buchungen"]["B-04"]
    # Die Meldung offener Zahlungen schaltet eine Organisator:in je Reise ein (Vorgabe aus)
    s.vorbereiten()
    a = s.schreiben("beispielreise", "einstellung_setzen", {**IDA, "args": {"regeln": {"waechter_zahlung": "ja"}}})
    assert "regeln.waechter_zahlung „False“ → „True“" in a["text"]
    assert yaml.safe_load(datei_auf_main(origin, "reise.yaml"))["regeln"]["waechter_zahlung"] is True
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="regeln.waechter_zahlung ist true oder false"):
        s.schreiben("beispielreise", "einstellung_setzen", {**IDA, "args": {"regeln": {"waechter_zahlung": "vielleicht"}}})


def test_buchung_anlegen_und_aendern(repo):
    """#76: Buchung als eigenes Ding über den Schreibweg; Mitwirkende dürfen (wer bucht, trägt ein); Herkunft Pflicht; Verlauf."""
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    with pytest.raises(sb.Ablehnung, match="„quelle“ fehlt"):
        s.schreiben("beispielreise", "buchung_anlegen", {**KARL, "args": {"fuer": ["U-02"], "nummer": "P-7"}})
    with pytest.raises(sb.Ablehnung, match="U-99 gibt es in dieser Reise nicht"):
        s.schreiben("beispielreise", "buchung_anlegen", {**KARL, "args": {"fuer": "U-99", "quelle": "Mail"}})
    with pytest.raises(sb.Ablehnung, match="„frist“ muss ein Datum"):
        s.schreiben("beispielreise", "buchung_anlegen", {**KARL, "args": {"fuer": "U-02", "quelle": "Mail", "frist": "bald"}})
    a = s.schreiben("beispielreise", "buchung_anlegen", {**KARL, "args": {
        "fuer": "U-02, E-21", "status": "angefragt", "nummer": "P-7", "bei": "telefonisch", "preis": "85 €", "frist": "2027-01-15",
        "frist_was": "Anzahlung überweisen", "storno": "kostenlos bis 14 Tage vorher", "storno_bis": "2027-05-01",
        "quelle": "Telefonat mit der Pension am 29.10.2026", "notiz": "Zimmer zur Burg"}}, )
    assert a["ok"] and a["text"].startswith("Buchung B-04 angelegt (angefragt) für U-02 Pension Burgblick, E-21 S-Bahn Bad Schandau → Dresden, Nr. P-7, bei telefonisch")
    assert a["id"] == "B-04"   # die neue ID, damit der Konnektor den Beleg gleich anhängen kann (Issue #135)
    assert "Frist 15.1.2027 (Anzahlung überweisen)" in a["text"] and "Storno: kostenlos bis 14 Tage vorher (bis 1.5.2027)" in a["text"]
    r, text = routen_auf_main(origin)
    b = r["buchungen"]["B-04"]
    assert b["fuer"] == ["U-02", "E-21"] and b["status"] == "angefragt" and b["nummer"] == "P-7" and b["wer"] == "Karl"
    assert b["frist"] == datetime.date(2027, 1, 15) and b["storno_bis"] == datetime.date(2027, 5, 1) and b["gebucht_am"] == datetime.date.today()
    assert b["quelle"] == "Telefonat mit der Pension am 29.10.2026" and b["verlauf"] == [{"datum": datetime.date.today(), "wer": "Karl", "was": "angelegt"}]
    assert "fuer: [U-02, E-21]" in text and "# Buchungen (B-…, #76)" in text   # Kommentare und Form bleiben
    assert yaml.safe_load(datei_auf_main(origin, "ids.yaml"))["B"] == 4
    # Ändern: Status gebucht, Frist weg, Nummer neu; Verlaufseintrag mit Person, Datum, Grund
    s.vorbereiten()
    a = s.schreiben("beispielreise", "buchung_aendern", {**IDA, "args": {"ziel": "B-04", "status": "gebucht", "frist": "", "nummer": "P-7/2027",
                                                                          "grund": "Bestätigung ist da"}})
    # Felder in Worten, nicht als Schlüssel (Product Owner 29.10.2026)
    assert "Status „angefragt“ → „gebucht“" in a["text"] and "Frist entfernt (war „15.1.2027“)" in a["text"] and "Nummer „P-7“ → „P-7/2027“" in a["text"]
    r, _ = routen_auf_main(origin)
    b = r["buchungen"]["B-04"]
    assert b["status"] == "gebucht" and "frist" not in b and b["nummer"] == "P-7/2027"
    assert b["verlauf"][-1] == {"datum": datetime.date.today(), "wer": "Ida", "was": "Status; Nummer; Frist entfernt", "grund": "Bestätigung ist da"}
    # Mitwirkende ändern nur, was sie selbst eingetragen haben; Stornieren braucht einen Grund (Product Owner 29.10.2026)
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="hat Ida eingetragen"):
        s.schreiben("beispielreise", "buchung_aendern", {**KARL, "args": {"ziel": "B-01", "notiz": "x"}})
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="Stornieren braucht einen Grund"):
        s.schreiben("beispielreise", "buchung_aendern", {**KARL, "args": {"ziel": "B-04", "status": "storniert"}})
    # Der Buchungsstand der Dinge folgt der Buchung (Probebau liest sie)
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="Nichts zu ändern"):
        s.schreiben("beispielreise", "buchung_aendern", {**IDA, "args": {"ziel": "B-04", "status": "gebucht"}})
    with pytest.raises(sb.Ablehnung, match="gibt es nicht"):
        s.schreiben("beispielreise", "buchung_aendern", {**IDA, "args": {"ziel": "B-09", "status": "storniert"}})
    with pytest.raises(sb.Ablehnung, match="„quelle“ darf nicht leer"):
        s.schreiben("beispielreise", "buchung_aendern", {**IDA, "args": {"ziel": "B-04", "quelle": ""}})
    with pytest.raises(sb.Ablehnung, match="nur lesen"):
        s.schreiben("beispielreise", "buchung_aendern", {"person": "gast", "name": "Gast", "rolle": "gast", "args": {"ziel": "B-04", "status": "storniert"}})
    # Stornieren mit Grund durch die Person, die eingetragen hat (Karl); Organisator:innen dürfen jede Buchung
    s.vorbereiten()
    a = s.schreiben("beispielreise", "buchung_aendern", {**KARL, "args": {"ziel": "B-04", "status": "storniert", "grund": "Pension hat abgesagt"}})
    assert "Status „gebucht“ → „storniert“" in a["text"] and "Grund: Pension hat abgesagt" in a["text"]
    s.vorbereiten()
    assert s.schreiben("beispielreise", "buchung_aendern", {**IDA, "args": {"ziel": "B-04", "notiz": "von Ida"}})["ok"]


def test_gemeinsame_frage_bleibt_offen_bis_alles_gewaehlt(repo):
    """Hängen mehrere Wahlstellen an derselben Frage (etwa „Winteröffnung der Hotels prüfen“), klärt eine Wahl die Frage
    erst, wenn an jeder dieser Wahlstellen etwas gewählt ist."""
    wurzel, origin, _, _ = repo
    r = wurzel / "reisen/beispielreise/plan/routen.yaml"
    text = r.read_text(encoding="utf-8")
    alt = "  V-03:\n    titel: Unterkunft in Hohnstein\n    wann: planung   # art: (die Art der Dinge) kommt hier aus den Optionen: die Art der ersten Unterkunft\n    frage: F-02\n"
    assert alt in text
    # erfunden: V-01 und V-03 teilen F-01, an V-03 ist noch nichts gewählt
    text = text.replace(alt, alt.replace("F-02", "F-01"))
    for zeile in ('{datum: 2026-10-20, status: gewaehlt, wer: Ida, grund: "liegt am Weg, kein Anstieg am Morgen"}',
                  '{datum: 2026-10-20, status: verworfen, wer: Ida, grund: "Anstieg am Morgen"}'):
        assert zeile in text
        text = text.replace(zeile, zeile.replace("gewaehlt", "vorgeschlagen").replace("verworfen", "vorgeschlagen"))
    r.write_text(text, encoding="utf-8")
    git(wurzel, "commit", "-qam", "V-03 hängt an F-01")
    git(wurzel, "push", "-q")
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "entscheiden", {**IDA, "args": {"option": "V-01.b", "status": "gewaehlt", "grund": "Bahn"}})
    assert "Frage F-01 bleibt offen, weil dort noch V-03 zu entscheiden ist." in a["text"], a["text"]
    # die KI fragt danach einzeln, mit den Möglichkeiten der offenen Wahlstelle zur Auswahl
    assert "Frag die Person jetzt einzeln nach" in a["text"] and "V-03 Unterkunft in Hohnstein: V-03.a Pension Burgblick, V-03.b Gasthof Polenztal" in a["text"], a["text"]
    assert "| vor Abreise | offen |" in fragen_auf_main(origin)
    s.vorbereiten()
    a = s.schreiben("beispielreise", "entscheiden", {**IDA, "args": {"option": "V-03.b", "status": "gewaehlt", "grund": "Abendessen"}})
    assert "Frage F-01 ist damit geklärt" in a["text"], a["text"]


def test_zeitgrenzen_liegen_unter_der_des_konnektors():
    import re
    conf = (WURZEL / "betrieb" / "vorlagen" / "nginx-konnektor.conf").read_text()
    grenze = int(re.search(r"proxy_read_timeout (\d+)s", conf).group(1))
    assert sb.ZEIT_GESAMT + sb.ZEIT_PRUEFUNG < grenze
    assert sb.ZEIT_SPERRE <= sb.ZEIT_GESAMT


def test_haengendes_vorbereiten_gibt_504_in_der_zeit(repo, monkeypatch):
    import time
    wurzel, _, arbeit, _ = repo
    s = sb.Schreiber(wurzel, arbeit)
    git(wurzel, "config", "protocol.ext.allow", "always")
    git(wurzel, "remote", "set-url", "origin", "ext::sleep 5")      # git fetch hängt
    monkeypatch.setattr(sb, "ZEIT_GESAMT", 1)
    start = time.monotonic()
    code, a = sb.anwenden_extern(s, "beispielreise", "art_definieren", {**IDA, "args": {"bezeichnung": "X", "grundform": "aufenthalt"}})
    assert time.monotonic() - start < 1 + sb.ZEIT_PRUEFUNG + 0.5
    assert code == 504 and not a["ok"] and "nicht eingetragen" in a["fehler"]


def test_veroeffentlichen_startet_mit_niedriger_prioritaet(repo, monkeypatch):
    wurzel, _, arbeit, _ = repo
    s = sb.Schreiber(wurzel, arbeit)
    gerufen = []

    class Stummel:
        def __init__(self, argv, *a, **k):
            gerufen.append(argv)

    monkeypatch.setattr(sb.subprocess, "Popen", Stummel)
    s.veroeffentlichen_anstossen()
    argv = gerufen[0]
    assert argv[0] == "nice" and "ionice" in argv and argv[-1] == s.veroeffentlichen


def test_nach_abbruch_sagt_die_antwort_ob_eingetragen_wurde(repo, monkeypatch, capsys):
    wurzel, _, arbeit, _ = repo
    # Die Prüfung selbst: Kennung auf origin/main gefunden / nicht gefunden
    monkeypatch.setenv("FR_VORGANG", "k4711")
    monkeypatch.setattr(sb.Schreiber, "veroeffentlichen_anstossen", lambda self: None)   # sys.stderr hat unter capsys keinen Dateideskriptor
    s = schreiber(repo)
    s.schreiben("beispielreise", "art_definieren", {**IDA, "args": {"bezeichnung": "Refugi", "grundform": "aufenthalt"}})
    assert "Frieda-Vorgang: k4711" in git(wurzel, "log", "-1", "--format=%B", "origin/main")
    assert sb.vorgang_eingetragen(s, "k4711") is True
    assert sb.vorgang_eingetragen(s, "k0815") is False
    # Die Antworten nach einem Abbruch im Anwenden
    for ergebnis, code_soll, ok_soll, text, zeile in [(True, 200, True, "ist aber eingetragen", "eingetragen"),
                                                      (False, 504, False, "nicht eingetragen", "nicht eingetragen"),
                                                      (None, 504, False, "prüfen, ob es angekommen ist", "ungeprüft")]:
        monkeypatch.setattr(sb, "vorgang_eingetragen", lambda s_, kennung, e=ergebnis: e)
        code, a, err = _abbruch_im_anwenden(repo, monkeypatch, capsys, origin_kaputt=False)
        assert code == code_soll and a["ok"] is ok_soll, (ergebnis, code, a)
        assert text in (a.get("text") or a.get("fehler") or "")
        assert f"Fertig art_definieren {code_soll} in " in err
        assert f"Zeit art_definieren 504: abgebrochen, {zeile}" in err


def test_kommando_mit_frist_beendet_die_ganze_prozessgruppe(tmp_path):
    import time
    pidfile = tmp_path / "enkel.pid"
    with pytest.raises(subprocess.TimeoutExpired):
        sb.befehl_mit_frist(["sh", "-c", f"sleep 30 & echo $! > {pidfile}; wait"], "", 0.5)
    pid = int(pidfile.read_text())
    for _ in range(40):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    os.kill(pid, 9)
    pytest.fail("Der Enkelprozess läuft nach der Frist weiter")


def test_dauer_steht_im_protokoll(repo, monkeypatch, capsys):
    import fcntl
    import re
    wurzel, _, arbeit, _ = repo
    s = sb.Schreiber(wurzel, arbeit)
    anfrage = {**IDA, "args": {"bezeichnung": "Refugi", "grundform": "aufenthalt"}}
    muster = re.compile(r"^Fertig art_definieren (\d{3}) in \d+\.\d s$", re.M)

    def codes():
        return muster.findall(capsys.readouterr().err)

    sb.anwenden_extern(s, "beispielreise", "art_definieren", anfrage)                               # Erfolg
    assert codes() == ["200"]
    sb.anwenden_extern(s, "beispielreise", "art_definieren", {**KARL, "args": anfrage["args"]})      # abgelehnt
    assert codes() == ["422"]
    monkeypatch.setattr(sb, "ZEIT_SPERRE", 0.1)
    with open(sb.sperrdatei("beispielreise"), "w") as f:                                             # Sperre belegt
        fcntl.flock(f, fcntl.LOCK_EX)
        sb.anwenden_extern(s, "beispielreise", "art_definieren", anfrage)
    assert codes() == ["429"]


def test_langes_veroeffentlichen_haelt_die_antwort_nicht_auf(repo, monkeypatch, capsys, tmp_path):
    # Das Veröffentlichen läuft im Hintergrund weiter; es darf die Ausgabe des Anwendens nicht offen halten
    import time
    wurzel, _, arbeit, _ = repo
    marke = tmp_path / "marke"
    stub = tmp_path / "langsam.sh"
    stub.write_text(f"#!/bin/sh\necho $$ > {marke}.pid\ntouch {marke}.start\necho Ausgabe; echo Fehler >&2\n"
                    f"sleep 6\ntouch {marke}.ende\n")
    stub.chmod(0o755)
    monkeypatch.setenv("SB_VEROEFFENTLICHEN", str(stub))
    s = sb.Schreiber(wurzel, arbeit)
    try:
        code, a = sb.anwenden_extern(s, "beispielreise", "art_definieren",
                                     {**IDA, "args": {"bezeichnung": "Refugi", "grundform": "aufenthalt"}})
        err = capsys.readouterr().err
        assert code == 200 and a["ok"], (code, a)
        assert "abgebrochen" not in err
        for _ in range(40):
            if Path(f"{marke}.start").exists():
                break
            time.sleep(0.05)
        assert Path(f"{marke}.start").exists(), "Veröffentlichen wurde nicht gestartet"
        assert not Path(f"{marke}.ende").exists(), "Die Antwort hat auf das Ende des Veröffentlichens gewartet"
    finally:
        try:
            os.killpg(int(Path(f"{marke}.pid").read_text()), 9)
        except (OSError, ValueError):
            pass


def test_unerwarteter_fehler_gibt_500_und_protokoll(repo, monkeypatch, capsys, tmp_path):
    # z. B. fehlt der Ordner der Sperrdateien
    wurzel, _, arbeit, _ = repo
    monkeypatch.setattr(sb, "sperrdatei", lambda reise: tmp_path / "fehlt" / "x.lock")
    code, a = sb.anwenden_extern(sb.Schreiber(wurzel, arbeit), "beispielreise", "art_definieren",
                                 {**IDA, "args": {"bezeichnung": "X", "grundform": "aufenthalt"}})
    err = capsys.readouterr().err
    assert code == 500 and not a["ok"] and "Fehler im Dienst" in a["fehler"]
    assert "Fehler art_definieren 500: FileNotFoundError" in err
    assert "Fertig art_definieren 500 in " in err


def test_veraltete_sperre_von_git_blockiert_die_reise_nicht(repo, capsys):
    # Nach einem Abbruch kann git eine index.lock in der Arbeitskopie hinterlassen
    wurzel, _, arbeit, _ = repo
    s = sb.Schreiber(wurzel, arbeit)
    assert sb.anwenden_extern(s, "beispielreise", "art_definieren",
                              {**IDA, "args": {"bezeichnung": "Refugi", "grundform": "aufenthalt"}})[0] == 200
    gitdir = Path(git(Path(f"{arbeit}-beispielreise"), "rev-parse", "--absolute-git-dir"))
    (gitdir / "index.lock").touch()
    code, a = sb.anwenden_extern(s, "beispielreise", "art_definieren",
                                 {**IDA, "args": {"bezeichnung": "Finca", "grundform": "aufenthalt"}})
    assert code == 200, (code, a, capsys.readouterr().err)
    assert not (gitdir / "index.lock").exists()


def test_veroeffentlichen_ohne_nice_und_ionice(repo, monkeypatch):
    # Fehlen nice oder ionice, startet es ohne Priorität; scheitert auch das, kommt trotzdem die Antwort
    wurzel, _, arbeit, _ = repo
    s = sb.Schreiber(wurzel, arbeit)
    gerufen = []
    monkeypatch.setattr(sb.shutil, "which", lambda name: None if name == "ionice" else f"/usr/bin/{name}")

    class Stummel:
        fehler = 0

        def __init__(self, argv, *a, **k):
            gerufen.append(argv)
            if len(gerufen) <= Stummel.fehler:
                raise FileNotFoundError(argv[0])

    monkeypatch.setattr(sb.subprocess, "Popen", Stummel)
    s.veroeffentlichen_anstossen()
    assert gerufen[0][0] == "nice" and "ionice" not in gerufen[0] and gerufen[0][-1] == s.veroeffentlichen
    for fehler in (1, 2):
        gerufen.clear()
        Stummel.fehler = fehler
        s.veroeffentlichen_anstossen()      # wirft nie
        assert len(gerufen) == 2 and gerufen[1] == [s.veroeffentlichen]


# ---------- Abgleich 29.10.2026 (Paket 3): die Tür für alle Grundformen ----------

def test_rollen_je_werkzeug_des_schreibwegs(repo):
    """Jedes Werkzeug des Schreibwegs prüft die Rolle nach reise.AKTIONEN: Gäste nie, Mitwirkende nur bei Eingaben, Organisator:innen
    alles; die Liste der Werkzeuge und ihrer Aktionen ist vollständig (ADR-0001, Frage 4 und 6)."""
    import reise as rg
    s = schreiber(repo)
    reise_dir = s.arbeit / "reisen" / "beispielreise"
    assert set(sb.WERKZEUGE) == set(sb.AKTIONEN) - {"person_schreiben"} | {"person_schreiben"}
    gast = {"person": None, "name": "Mo", "rolle": "gast"}
    for werkzeug, aktion in sb.AKTIONEN.items():
        with pytest.raises(sb.Ablehnung):
            s.wer_pruefen(reise_dir, gast, werkzeug)
        darf_mitwirkend = rg.AKTIONEN[aktion]["rolle"] == "mitwirkend"
        if darf_mitwirkend:
            assert s.wer_pruefen(reise_dir, KARL, werkzeug)["rolle"] == "mitwirkend", werkzeug
        else:
            with pytest.raises(sb.Ablehnung):
                s.wer_pruefen(reise_dir, KARL, werkzeug)
        assert s.wer_pruefen(reise_dir, IDA, werkzeug)["rolle"] == "organisator", werkzeug
    # Mitwirkende: Eingaben; Organisator:innen: Plan, Ontologie, Einstellungen
    assert {w for w, a in sb.AKTIONEN.items() if rg.AKTIONEN[a]["rolle"] == "organisator"} >= {
        "tag_anlegen", "tag_aendern", "termin_setzen", "wahlstelle_aendern", "plan_anlegen", "plan_aendern", "reise_aendern",
        "merkmal_zusammenfuehren", "arten_uebernehmen", "entscheiden", "art_definieren", "merkmal_definieren",
        "start_ende_setzen"}   # Issue #142: Start und Ende des Plans wie die Eckdaten der Reise (Aktion einstellung)
    assert sb.AKTIONEN["start_ende_setzen"] == sb.AKTIONEN["reise_aendern"] == "einstellung"
    assert {w for w, a in sb.AKTIONEN.items() if rg.AKTIONEN[a]["rolle"] == "mitwirkend"} >= {
        "option_aendern", "wissen_aendern", "lesetext_schreiben", "wunsch_vorschlagen", "wert_eintragen", "ding_anlegen", "option_anlegen"}


def test_tag_anlegen_und_termin_setzen(repo):
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    with pytest.raises(sb.Ablehnung, match="nur Organisator:innen|Rolle"):
        s.schreiben("beispielreise", "tag_anlegen", {**KARL, "args": {"titel": "Ruhetag"}})
    a = s.schreiben("beispielreise", "tag_anlegen", {**IDA, "args": {"titel": "Ruhetag in Dresden", "nach": "T-01", "nacht": "U-01", "text": "Ausschlafen."}})
    assert "T-07" in a["text"] and "nach T-01" in a["text"]
    r, _ = routen_auf_main(origin)
    assert r["tage"]["T-07"] == {"titel": "Ruhetag in Dresden", "text": "Ausschlafen.", "nacht": "U-01"} and r["route"][:3] == ["T-01", "T-07", "T-02"]
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="gibt es nicht"):
        s.schreiben("beispielreise", "tag_anlegen", {**IDA, "args": {"titel": "x", "nach": "T-99"}})
    with pytest.raises(sb.Ablehnung, match="quelle"):
        s.schreiben("beispielreise", "termin_setzen", {**IDA, "args": {"datum": "2027-05-14", "titel": "Tisch um 19 Uhr"}})
    a = s.schreiben("beispielreise", "termin_setzen", {**IDA, "args": {"datum": "2027-05-14", "titel": "Tisch um 19 Uhr", "ort": "O-03", "quelle": "Reservierung per Mail (Test)"}})
    assert "angelegt in O-03" in a["text"]
    r, _ = routen_auf_main(origin)
    assert {"datum": datetime.date(2027, 5, 14), "ort": "O-03", "titel": "Tisch um 19 Uhr", "quelle": "Reservierung per Mail (Test)"} in r["fixpunkte"]
    s.vorbereiten()
    a = s.schreiben("beispielreise", "termin_setzen", {**IDA, "args": {"datum": "2027-05-14", "titel": "Tisch um 19 Uhr", "neuer_titel": "Tisch um 20 Uhr"}})
    assert "Titel „Tisch um 19 Uhr“ → „Tisch um 20 Uhr“" in a["text"]
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="Grund"):
        s.schreiben("beispielreise", "termin_setzen", {**IDA, "args": {"datum": "2027-05-14", "titel": "Tisch um 20 Uhr", "entfernen": True}})
    a = s.schreiben("beispielreise", "termin_setzen", {**IDA, "args": {"datum": "2027-05-14", "titel": "Tisch um 20 Uhr", "entfernen": True, "grund": "abgesagt"}})
    assert "entfernt" in a["text"]
    r, _ = routen_auf_main(origin)
    assert not any(f.get("titel") == "Tisch um 20 Uhr" for f in r["fixpunkte"])


def test_wahlstelle_und_option_aendern(repo):
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "wahlstelle_aendern", {**IDA, "args": {"ziel": "V-02", "titel": "Tag 2: Weg zum Hockstein", "an": ["E-01"], "grund": "klarer"}})
    assert "titel „Tag 2: Zugang zum Hockstein“ → „Tag 2: Weg zum Hockstein“" in a["text"]
    r, text = routen_auf_main(origin)
    w = r["wahlstellen"]["V-02"]
    assert w["an"] == ["E-01"] and w["wann"] == "unterwegs"
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="gibt es an dieser Wahlstelle nicht"):
        s.schreiben("beispielreise", "wahlstelle_aendern", {**IDA, "args": {"ziel": "V-03", "stufen": {"onsen": "nötig"}}})
    a = s.schreiben("beispielreise", "wahlstelle_aendern", {**IDA, "args": {"ziel": "V-03", "stufen": {"abendessen": "nötig"}}})
    assert "Stufe abendessen: wie die Art → pflicht" in a["text"]
    r, _ = routen_auf_main(origin)
    assert r["wahlstellen"]["V-03"]["merkmale"] == {"abendessen": {"stufe": "pflicht"}}
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="Art dieser Reise"):
        s.schreiben("beispielreise", "wahlstelle_aendern", {**IDA, "args": {"ziel": "V-03", "art": "schloss"}})
    with pytest.raises(sb.Ablehnung, match="nur Organisator:innen|Rolle"):
        s.schreiben("beispielreise", "wahlstelle_aendern", {**KARL, "args": {"ziel": "V-03", "titel": "x"}})
    a = s.schreiben("beispielreise", "wahlstelle_aendern", {**IDA, "args": {"ziel": "V-03", "wann": "unterwegs", "art": "pension"}})
    assert "wann planung → unterwegs" in a["text"] and "art – → pension" in a["text"]
    r, _ = routen_auf_main(origin)
    assert r["wahlstellen"]["V-03"]["wann"] == "unterwegs" and r["wahlstellen"]["V-03"]["art"] == "pension"
    # Option: Felder, Favorisieren durch Mitwirkende mit Grund; gewählt nur mit entscheiden
    s.vorbereiten()
    a = s.schreiben("beispielreise", "option_aendern", {**KARL, "args": {"ziel": "V-01.a", "plus": ["kurz", "direkt am Bahnhof"], "favorisiert": True,
                                                                         "grund": "Karl mag den kurzen Weg"}})
    assert "favorisiert (Karl)" in a["text"] and "plus ['kürzester letzter Tag'" not in a["text"]
    r, _ = routen_auf_main(origin)
    o = next(x for x in r["wahlstellen"]["V-01"]["optionen"] if x["id"] == "V-01.a")
    assert o["plus"] == ["kurz", "direkt am Bahnhof"] and o["verlauf"][-1] == {"datum": datetime.date.today(), "status": "favorisiert", "wer": "Karl", "grund": "Karl mag den kurzen Weg"}
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="Grund"):
        s.schreiben("beispielreise", "option_aendern", {**KARL, "args": {"ziel": "V-01.b", "favorisiert": True}})
    with pytest.raises(sb.Ablehnung, match="derselben Wahlstelle"):
        s.schreiben("beispielreise", "option_aendern", {**KARL, "args": {"ziel": "V-01.b", "erfordert": ["V-01.a"]}})
    with pytest.raises(sb.Ablehnung, match="nur eines von"):
        s.schreiben("beispielreise", "option_aendern", {**KARL, "args": {"ziel": "V-03.a", "strecken": ["E-01"]}})
    assert not git(arbeit, "status", "--porcelain")


def test_wissen_aendern_und_lesetext_schreiben(repo):
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    with pytest.raises(sb.Ablehnung, match="„grund“ fehlt"):
        s.schreiben("beispielreise", "wissen_aendern", {**KARL, "args": {"ziel": "W-05", "text": "x", "quelle": "y"}})
    with pytest.raises(sb.Ablehnung, match="„quelle“ fehlt"):
        s.schreiben("beispielreise", "wissen_aendern", {**KARL, "args": {"ziel": "W-05", "text": "x", "grund": "falsch"}})
    # Ein Abschnitt, dessen Unterabschnitte andere Dateien brauchen (W-05), lässt sich nicht einfach ersetzen: der Probebau lehnt ab
    with pytest.raises(sb.Ablehnung, match="nicht bauen"):
        s.schreiben("beispielreise", "wissen_aendern", {**KARL, "args": {"ziel": "W-05", "text": "x", "quelle": "y", "grund": "z"}})
    with pytest.raises(sb.Ablehnung, match="nicht bauen"):   # ebenso ein Abschnitt, dessen Fußnoten andere brauchen (W-07 Quellen)
        s.schreiben("beispielreise", "wissen_aendern", {**KARL, "args": {"ziel": "W-07", "text": "x", "quelle": "y", "grund": "z"}})
    a = s.schreiben("beispielreise", "wissen_aendern", {**KARL, "args": {"ziel": "W-01", "text": "Drei Wandertage auf dem Malerweg (Test).",
                                                                         "quelle": "Beispielreise (Test)", "neuer_titel": "Überblick", "grund": "knapper"}})
    assert "Inhalt ersetzt" in a["text"] and "Titel „Übersicht“ → „Überblick“" in a["text"]
    dossier = subprocess.run(["git", "-C", str(origin), "show", "main:reisen/beispielreise/inhalt/etappen.md"], check=True, capture_output=True, text=True).stdout
    assert "## Überblick\n\nDrei Wandertage auf dem Malerweg (Test).\n\n*Herkunft: Beispielreise (Test); berichtigt am" in dossier
    assert "\n## Übersicht\n" not in dossier and "## Etappe 1:" in dossier
    cfg = json.loads(subprocess.run(["git", "-C", str(origin), "show", "main:reisen/beispielreise/reise.json"], check=True, capture_output=True, text=True).stdout)
    assert cfg["abschnitte"]["inhalt/etappen.md"]["Überblick"] == ["W-01", "uebersicht"] and "Übersicht" not in cfg["abschnitte"]["inhalt/etappen.md"]
    # Lesetext: Rubriken der Art (wandern), fremdes Stichwort abgelehnt, Zusammenfassung ersetzt
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="keine Rubrik der Art"):
        s.schreiben("beispielreise", "lesetext_schreiben", {**KARL, "args": {"ziel": "E-01", "text": "**Wetter.** Sonnig.", "quelle": "x"}})
    a = s.schreiben("beispielreise", "lesetext_schreiben", {**KARL, "args": {"ziel": "E-01", "quelle": "eigene Begehung (Test)",
        "text": "**Charakter.** Ein Tag mit Fels und Wald (Test).\n\n**Ankommen.** Früh in Hohnstein."}})
    assert "Lesetext der Etappe E-01 ersetzt" in a["text"]
    dossier = subprocess.run(["git", "-C", str(origin), "show", "main:reisen/beispielreise/inhalt/etappen.md"], check=True, capture_output=True, text=True).stdout
    assert "### Zusammenfassung\n**Charakter.** Ein Tag mit Fels und Wald (Test).\n\n**Ankommen.** Früh in Hohnstein.\n\n*Herkunft: eigene Begehung (Test); geschrieben am" in dossier
    assert "Ein abwechslungsreicher erster Tag" not in dossier and "### Eckdaten" in dossier
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="steht nicht im Etappen-Dossier"):
        s.schreiben("beispielreise", "lesetext_schreiben", {**KARL, "args": {"ziel": "E-20", "text": "x", "quelle": "y"}})


def test_reise_aendern_und_plaene(repo):
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    with pytest.raises(sb.Ablehnung, match="„grund“ fehlt"):
        s.schreiben("beispielreise", "reise_aendern", {**IDA, "args": {"titel": "x"}})
    with pytest.raises(sb.Ablehnung, match="von und bis zusammen"):
        s.schreiben("beispielreise", "reise_aendern", {**IDA, "args": {"bis": "2027-05-17", "grund": "x"}})
    a = s.schreiben("beispielreise", "reise_aendern", {**IDA, "args": {"untertitel": "Dresden und Sächsische Schweiz, 13.–17.5.2027 · erfundenes Beispiel",
                                                                       "von": "2027-05-13", "bis": "2027-05-17", "grund": "ein Tag länger"}})
    assert "bis – → 2027-05-17" in a["text"] and "untertitel" in a["text"]
    # Issue #142: Start und Ende des Plans setzt ein eigenes Werkzeug; der Text verweist darauf statt auf die Datei
    assert "start_ende_setzen" in a["text"] and "plan/routen.yaml" not in a["text"]
    ry = yaml.safe_load(subprocess.run(["git", "-C", str(origin), "show", "main:reisen/beispielreise/reise.yaml"], check=True, capture_output=True, text=True).stdout)
    assert ry["zeitraum"]["bis"] == datetime.date(2027, 5, 17) and ry["verlauf"][-1]["grund"] == "ein Tag länger" and ry["verlauf"][-1]["wer"] == "Ida"
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="„quelle“ fehlt"):
        s.schreiben("beispielreise", "plan_anlegen", {**IDA, "args": {"titel": "Bus zurück", "auswahl": ["V-01.c"]}})
    with pytest.raises(sb.Ablehnung, match="zwei Optionen für V-01"):
        s.schreiben("beispielreise", "plan_anlegen", {**IDA, "args": {"titel": "x", "auswahl": ["V-01.a", "V-01.b"], "quelle": "y"}})
    a = s.schreiben("beispielreise", "plan_anlegen", {**IDA, "args": {"titel": "Mit dem Bus zurück", "auswahl": ["V-01.c", "V-03.a"], "farbe": "c",
                                                                      "plus": ["kein Umsteigen"], "quelle": "Ida im Gespräch (Test)"}})
    assert "P-C" in a["text"]
    r, _ = routen_auf_main(origin)
    p = next(x for x in r["plaene"] if x["id"] == "P-C")
    assert p["kurz"] == "Plan C" and p["auswahl"] == ["V-01.c", "V-03.a"] and p["farbe"] == "c" and p["quelle"] == "Ida im Gespräch (Test)"
    s.vorbereiten()
    a = s.schreiben("beispielreise", "plan_aendern", {**IDA, "args": {"ziel": "P-C", "kurz": "Plan Bus", "minus": ["Fahrplan"], "grund": "klarer"}})
    assert "kurz „Plan C“ → „Plan Bus“" in a["text"]
    r, _ = routen_auf_main(origin)
    assert next(x for x in r["plaene"] if x["id"] == "P-C")["minus"] == ["Fahrplan"]
    assert not git(arbeit, "status", "--porcelain")


def test_merkmal_zusammenfuehren_und_arten_uebernehmen(repo, tmp_path):
    wurzel, origin, arbeit, _ = repo
    s = schreiber(repo)
    with pytest.raises(sb.Ablehnung, match="Typen passen nicht"):
        s.schreiben("beispielreise", "merkmal_zusammenfuehren", {**IDA, "args": {"art": "hotel", "von": "lage", "nach": "preis", "grund": "x"}})
    with pytest.raises(sb.Ablehnung, match="nur Organisator:innen|Rolle"):
        s.schreiben("beispielreise", "merkmal_zusammenfuehren", {**KARL, "args": {"art": "pension", "von": "lage", "nach": "abendessen", "grund": "x"}})
    # pension: Merkmal lage (text) in ein neues Textmerkmal „umgebung“ aufgehen lassen
    s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "bezeichnung": "Umgebung", "typ": "text"}})
    s.vorbereiten()
    a = s.schreiben("beispielreise", "merkmal_zusammenfuehren", {**IDA, "args": {"art": "pension", "von": "lage", "nach": "umgebung", "grund": "ein Wort reicht"}})
    assert "1 Wert(e) umgehängt" in a["text"] and "„lage“ ist jetzt ein weiterer Name von umgebung" in a["text"]
    r, _ = routen_auf_main(origin)
    assert r["unterkuenfte"]["U-02"]["merkmale"]["umgebung"]["wert"] == "am Markt, zwei Minuten vom Malerweg" and "lage" not in r["unterkuenfte"]["U-02"]["merkmale"]
    arten = yaml.safe_load(subprocess.run(["git", "-C", str(origin), "show", "main:reisen/beispielreise/plan/arten.yaml"], check=True, capture_output=True, text=True).stdout)["arten"]
    assert "lage" not in arten["pension"]["merkmale"] and arten["pension"]["merkmale"]["umgebung"]["auch"] == ["lage"]
    # Arten übernehmen: aus einer zweiten Reise im Repo (hier eine Kopie mit einer zusätzlichen Art), nur die fehlenden
    s.vorbereiten()
    andere = arbeit / "reisen" / "zweite-2027"
    shutil.copytree(arbeit / "reisen" / "beispielreise", andere)
    p = andere / "plan" / "arten.yaml"
    p.write_text(p.read_text(encoding="utf-8") + "  ryokan:\n    grundform: aufenthalt\n    name: Ryokan\n    farbe: rosa\n    merkmale:\n      onsen: {name: Onsen, typ: auswahl, werte: [ja, nein]}\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(arbeit), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(arbeit), "commit", "-qm", "zweite Reise (Test)"], check=True)
    subprocess.run(["git", "-C", str(arbeit), "push", "-q", "origin", "HEAD:main"], check=True)
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="gibt es hier schon"):
        s.schreiben("beispielreise", "arten_uebernehmen", {**IDA, "args": {"von_reise": "zweite-2027", "arten": ["hotel"]}})
    a = s.schreiben("beispielreise", "arten_uebernehmen", {**IDA, "args": {"von_reise": "zweite-2027", "grund": "wie beim letzten Mal"}})
    assert "ryokan „Ryokan“ (1 Merkmale)" in a["text"]
    arten = yaml.safe_load(subprocess.run(["git", "-C", str(origin), "show", "main:reisen/beispielreise/plan/arten.yaml"], check=True, capture_output=True, text=True).stdout)["arten"]
    assert arten["ryokan"]["merkmale"]["onsen"]["werte"] == ["ja", "nein"] and arten["hotel"]["merkmale"]["preis"]["rolle"] == "kosten"


def test_wunsch_vorschlagen(repo):
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    with pytest.raises(sb.Ablehnung, match="Kennung des Wunschs"):
        s.schreiben("beispielreise", "wunsch_vorschlagen", {**KARL, "args": {"wunsch": "R-1", "notiz": "x"}})
    a = s.schreiben("beispielreise", "wunsch_vorschlagen", {**KARL, "args": {"wunsch": "R-20261029-100000-abcd", "bezug": ["T-01", "O-01"],
                                                                             "notiz": "Passt zum Stadttag (Test, erfunden).", "option": "V-01.b"}})
    assert "passt zu T-01, O-01, Option V-01.b" in a["text"] and "eingetragen" in a["text"]
    w = yaml.safe_load(subprocess.run(["git", "-C", str(origin), "show", "main:reisen/beispielreise/plan/wuensche.yaml"], check=True, capture_output=True, text=True).stdout)
    assert w["R-20261029-100000-abcd"] == {"bezug": ["T-01", "O-01"], "notiz": "Passt zum Stadttag (Test, erfunden).", "option": "V-01.b"}
    assert "R-20261021-091500-a1b2" in w   # der vorhandene Vorschlag bleibt
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="gibt es nicht"):
        s.schreiben("beispielreise", "wunsch_vorschlagen", {**KARL, "args": {"wunsch": "R-20261029-100000-abcd", "notiz": "x", "option": "V-09.a"}})


@pytest.mark.parametrize("werkzeug, args", [
    ("ding_anlegen", {"was": "strecke", "titel": "Bus", "von": "O-01", "nach": "O-02", "art": "bus"}),
    ("ding_anlegen", {"was": "ort", "titel": "Rathen"}),
    ("ding_anlegen", {"was": "aufenthalt", "titel": "Burg", "ort": "O-03", "art": "besichtigung"}),
    ("ding_anlegen", {"was": "unterkunft", "titel": "Hof", "ort": "O-03", "art": "pension"}),
    ("option_anlegen", {"wahlstelle": "V-03", "titel": "Hof", "unterkuenfte": ["U-04"]}),
    ("wahlstelle_anlegen", {"titel": "x", "optionen": [{"titel": "a"}]}),
    ("buchung_anlegen", {"fuer": "U-02"}),
    ("lage_eintragen", {"ziel": "U-02", "adresse": "Markt 1"}),
    ("wissen_schreiben", {"titel": "Neu", "text": "x"}),
    ("lesetext_schreiben", {"ziel": "E-01", "text": "x"}),
    ("plan_anlegen", {"titel": "x", "auswahl": ["V-01.a"]}),
    ("termin_setzen", {"datum": "2027-05-14", "titel": "x"}),
])
def test_anlegen_ohne_herkunft_wird_abgelehnt(repo, werkzeug, args):
    """ADR-0001, Frage 5: Jede neue Aussage trägt ihre Herkunft; ohne quelle schreibt der Schreibweg nichts."""
    _, _, arbeit, _ = repo
    s = schreiber(repo)
    with pytest.raises(sb.Ablehnung, match="quelle"):
        s.schreiben("beispielreise", werkzeug, {**IDA, "args": args})
    assert not git(arbeit, "status", "--porcelain")


def test_buchung_mit_reisenden_preisen_und_ab_termin(repo):
    """Issue #135: Reisende je Buchung (nur Personen der Reise), Preis je Ding bei mehreren Dingen, Ab-Termin mit ab_was."""
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    with pytest.raises(sb.Ablehnung, match="steht nicht in der Reise"):
        s.schreiben("beispielreise", "buchung_anlegen", {**KARL, "args": {"fuer": "E-20", "quelle": "Mail", "personen": {"Ida": "", "Anna": "Sitz 1A"}}})
    with pytest.raises(sb.Ablehnung, match="„preise“: U-02 gehört nicht zu dieser Buchung"):
        s.schreiben("beispielreise", "buchung_anlegen", {**KARL, "args": {"fuer": "E-20", "quelle": "Mail", "preise": {"U-02": "1 €"}}})
    with pytest.raises(sb.Ablehnung, match="„ab“ muss ein Datum"):
        s.schreiben("beispielreise", "buchung_anlegen", {**KARL, "args": {"fuer": "E-20", "quelle": "Mail", "ab": "bald"}})
    a = s.schreiben("beispielreise", "buchung_anlegen", {**KARL, "args": {
        "fuer": ["E-20", "E-21"], "status": "gebucht", "nummer": "EW-7", "preis": "230 €", "preise": {"E-20": "120 €", "E-21": "110 €"},
        "personen": {"Ida": "Sitz 12A, 23 kg Gepäck", "Karl": ""}, "ab": "2027-05-13", "ab_was": "Online-Check-in", "quelle": "Mail vom 29.10.2026"}})
    assert a["ok"] and "Reisende: Ida (Sitz 12A, 23 kg Gepäck), Karl" in a["text"] and "Preise: E-20 120 €, E-21 110 €" in a["text"] \
        and "Ab 13.5.2027 (Online-Check-in)" in a["text"]
    r, text = routen_auf_main(origin)
    b = r["buchungen"]["B-04"]
    assert b["personen"] == {"Ida": "Sitz 12A, 23 kg Gepäck", "Karl": ""} and b["preise"] == {"E-20": "120 €", "E-21": "110 €"}
    assert b["ab"] == datetime.date(2027, 5, 13) and b["ab_was"] == "Online-Check-in"
    s.vorbereiten()
    a = s.schreiben("beispielreise", "buchung_aendern", {**KARL, "args": {"ziel": "B-04", "personen": ["Karl"], "ab": "", "grund": "Ida fliegt nicht mit"}})
    assert "Reisende" in a["text"] and "Ab entfernt" in a["text"]
    r, _ = routen_auf_main(origin)
    assert r["buchungen"]["B-04"]["personen"] == {"Karl": ""} and "ab" not in r["buchungen"]["B-04"] and "ab_was" not in r["buchungen"]["B-04"]


def test_strecke_mit_zeiten_und_ort_ausserhalb(repo):
    """Issue #135: ding_anlegen und ding_aendern kennen ab/an an Strecken und ausserhalb an Orten."""
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "ding_anlegen", {**KARL, "args": {"was": "ort", "titel": "Flughafen Beispielstadt", "ausserhalb": True, "quelle": "Karte"}})
    assert a["ok"]
    r, _ = routen_auf_main(origin)
    assert r["orte"]["O-07"] == {"name": "Flughafen Beispielstadt", "quelle": "Karte", "ausserhalb": True}
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="„ab“ ist eine Uhrzeit HH:MM"):
        s.schreiben("beispielreise", "ding_anlegen", {**KARL, "args": {"was": "strecke", "titel": "Flug", "von": "O-07", "nach": "O-01", "art": "bus", "ab": "morgens", "quelle": "x"}})
    a = s.schreiben("beispielreise", "ding_anlegen", {**KARL, "args": {"was": "strecke", "titel": "Bus vom Flughafen", "von": "O-07", "nach": "O-01", "art": "bus",
                                                                       "ab": "2027-05-14T07:45+02:00", "an": "09:10", "quelle": "Fahrplan"}})
    assert a["ok"]
    r, text = routen_auf_main(origin)
    e = r["strecken"]["E-24"]
    assert e["ab"] == "2027-05-14T07:45+02:00" and e["an"] == "09:10" and 'an: "09:10"' in text
    s.vorbereiten()
    a = s.schreiben("beispielreise", "ding_aendern", {**KARL, "args": {"ziel": "E-24", "an": "", "ab": "08:00"}})
    assert "ab „2027-05-14T07:45+02:00“ → „08:00“" in a["text"] and "an entfernt" in a["text"]
    r, _ = routen_auf_main(origin)
    assert r["strecken"]["E-24"]["ab"] == "08:00" and "an" not in r["strecken"]["E-24"]
    s.vorbereiten()
    a = s.schreiben("beispielreise", "ding_aendern", {**KARL, "args": {"ziel": "O-07", "ausserhalb": False}})
    r, _ = routen_auf_main(origin)
    assert "ausserhalb" not in r["orte"]["O-07"] or r["orte"]["O-07"]["ausserhalb"] is False


# --- Löschwunsch (#145): Antworttexte sagen, dass nichts gelöscht ist, und wie man es zurückholt ---

def test_loeschwunsch_antworttext_buchung(repo):
    """Kriterium 3: Stornieren hängt den Hinweis an; eine andere Änderung nicht. Der bisherige Satz bleibt vorn."""
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "buchung_aendern", {**IDA, "args": {"ziel": "B-02", "nummer": "EW-9"}})
    assert "Nicht gelöscht" not in a["text"]
    s.vorbereiten()
    a = s.schreiben("beispielreise", "buchung_aendern", {**IDA, "args": {"ziel": "B-01", "status": "storniert", "grund": "Plan geändert"}})
    assert "Status „gebucht“ → „storniert“" in a["text"] and "Grund: Plan geändert" in a["text"]
    assert a["text"].rstrip().endswith("Nicht gelöscht, die Buchung steht weiter mit Verlauf da; zurückholen mit Status gebucht.")


def test_loeschwunsch_antworttext_option(repo):
    """Kriterium 4: verworfen und ersetzt hängen den Hinweis an; gewählt nicht."""
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "entscheiden", {**IDA, "args": {"option": "V-01.b", "status": "gewaehlt", "grund": "Bahn"}})
    assert a["text"].startswith("Entschieden:") and "Nicht gelöscht" not in a["text"]
    hinweis = "Nicht gelöscht, die Option bleibt mit Verlauf stehen; zurückholen mit entscheiden, Status gewählt."
    s.vorbereiten()
    a = s.schreiben("beispielreise", "entscheiden", {**IDA, "args": {"option": "V-01.b", "status": "verworfen", "grund": "Fahrplan passt nicht"}})
    assert a["text"].startswith("Entschieden:") and hinweis in a["text"]
    s.vorbereiten()
    a = s.schreiben("beispielreise", "entscheiden", {**IDA, "args": {"option": "V-02.a", "status": "ersetzt", "ersetzt_durch": "V-02.b",
                                                                      "grund": "Gasthof ist besser"}})
    assert a["text"].startswith("Entschieden:") and hinweis in a["text"]


def test_loeschwunsch_antworttext_frage(repo):
    """Kriterium 5: entfaellt sagt ehrlich, dass es kein Wiedereröffnen gibt; geklärt nicht."""
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "frage_schliessen", {**IDA, "args": {"frage": "F-03", "ergebnis": "Fahrplan steht"}})
    assert "Nicht gelöscht" not in a["text"]
    s.vorbereiten()
    a = s.schreiben("beispielreise", "frage_schliessen", {**IDA, "args": {"frage": "F-01", "ergebnis": "wird unterwegs entschieden", "status": "entfaellt"}})
    assert "entfällt" in a["text"]
    assert a["text"].rstrip().endswith("Nicht gelöscht, die Frage steht weiter mit Verlauf da; ein Wiedereröffnen gibt es nicht, "
                                       "bei Bedarf eine neue Frage anlegen.")


# ---------- Issue #142: Hinweise der Prüfung, Start und Ende des Plans ----------

AUSSERHALB = "plan: Fixpunkt 20.05. (Konzert am Abend (Test)) liegt außerhalb des Plans."


def test_neue_warnung_steht_als_hinweis_in_der_antwort(repo):
    """AC-9: Schreibweg und Tor prüfen dasselbe (nur Baufehler lehnen ab); eine Warnung, die der Eintrag neu erzeugt, steht
    als Hinweis in der Antwort, eingetragen ist trotzdem. Ohne neue Warnung gibt es das Feld nicht."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "reise_aendern", {**IDA, "args": {"kurz": "Malerweg", "grund": "kürzer"}})
    assert a["ok"] is True and "hinweise" not in a                     # die Beispielreise hat keine Warnung
    s.vorbereiten()
    a = s.schreiben("beispielreise", "termin_setzen", {**IDA, "args": {"datum": "2027-05-20", "titel": "Konzert am Abend (Test)",
                                                                       "ort": "O-01", "quelle": "erfunden (Test)"}})
    assert a["ok"] is True and a["hinweise"] == [AUSSERHALB]
    r, _ = routen_auf_main(origin)
    assert any(f.get("titel") == "Konzert am Abend (Test)" for f in r["fixpunkte"])   # der Eintrag ist im Repo


def test_keine_hinweise_ohne_neue_warnung(repo):
    """AC-10: Hat die Reise schon Warnungen und kommt keine neue dazu, fehlt das Feld hinweise (nur Neues zählt)."""
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "termin_setzen", {**IDA, "args": {"datum": "2027-05-20", "titel": "Konzert am Abend (Test)",
                                                                       "ort": "O-01", "quelle": "erfunden (Test)"}})
    assert a["hinweise"] == [AUSSERHALB]
    s.vorbereiten()
    a = s.schreiben("beispielreise", "reise_aendern", {**IDA, "args": {"kurz": "Malerweg", "grund": "kürzer"}})
    assert a["ok"] is True and "hinweise" not in a


def test_hinweise_sind_begrenzt(repo, monkeypatch):
    """AC-12: Höchstens 10 Hinweise, dann eine Zeile „und N weitere“. Die Warnungen sind erfunden: ein Termin mit dem Titel
    „Viele Hinweise (Test)“ lässt den Bau 13 Warnungen mehr melden."""
    import bauen
    original = bauen.Bauer.daten

    def daten(self):
        d = original(self)
        if "Viele Hinweise (Test)" in (self.reise_dir / "plan" / "routen.yaml").read_text(encoding="utf-8"):
            d["route"]["warnungen"] = d["route"].get("warnungen", []) + [
                {"bezug": "plan", "text": f"Erfundene Warnung {i} (Test)."} for i in range(1, 14)]
        return d
    monkeypatch.setattr(bauen.Bauer, "daten", daten)
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "termin_setzen", {**IDA, "args": {"datum": "2027-05-13", "titel": "Viele Hinweise (Test)",
                                                                       "ort": "O-01", "quelle": "erfunden (Test)"}})
    assert a["ok"] is True
    assert a["hinweise"][:10] == [f"plan: Erfundene Warnung {i} (Test)." for i in range(1, 11)]
    assert len(a["hinweise"]) == 11 and a["hinweise"][10] == "und 3 weitere"


def test_start_ende_setzen_aendert_plan_und_schreibt_verlauf(repo):
    """AC-27: Start und Ende des Plans (plan/routen.yaml) setzt die Organisatorin mit Grund; der Verlauf steht in reise.yaml,
    die Daten aller Tage hängen am Startdatum, die Antwort sagt das."""
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "start_ende_setzen", {**IDA, "args": {"start_datum": "2027-05-20", "ende_datum": "2027-05-23",
                                                                           "grund": "Zug eine Woche später (Test)"}})
    assert a["ok"] is True and "verschieb" in a["text"]
    r, _ = routen_auf_main(origin)
    assert r["start"] == {"datum": datetime.date(2027, 5, 20), "ort": "O-01"}
    assert r["ende"] == {"datum": datetime.date(2027, 5, 23), "ort": "O-01"}
    ry = yaml.safe_load(git(origin, "show", "main:reisen/beispielreise/reise.yaml"))
    v = ry["verlauf"][-1]
    assert v["wer"] == "Ida" and v["grund"] == "Zug eine Woche später (Test)" and v["datum"] == datetime.date.today()
    assert "2027-05-13 → 2027-05-20" in v["was"] and "2027-05-16 → 2027-05-23" in v["was"]
    # Die festen Termine bleiben an ihrem Datum und liegen jetzt außerhalb des Plans: das zeigen die Hinweise
    assert any("Fixpunkt 13.05." in h for h in a["hinweise"])
    s.vorbereiten()
    a = s.schreiben("beispielreise", "start_ende_setzen", {**IDA, "args": {"start_ort": "O-02", "grund": "Start woanders (Test)"}})
    r, _ = routen_auf_main(origin)
    assert r["start"]["ort"] == "O-02" and r["start"]["datum"] == datetime.date(2027, 5, 20)
    assert not git(arbeit, "status", "--porcelain")


def test_start_ende_setzen_verschiebt_die_tagesdaten(repo):
    """AC-27 (Tage): Nach dem Verschieben von start_datum hängen die Daten aller Tage am neuen Start; der erste Tag liegt
    am neuen Startdatum, jeder weitere einen Tag später."""
    import bauen
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    s.vorbereiten()
    vorher = [t["datum"] for t in bauen.Bauer(arbeit / "reisen" / "beispielreise", arbeit / "probe").daten()["route"]["tage"]]
    assert vorher and vorher[0] == "2027-05-13"
    a = s.schreiben("beispielreise", "start_ende_setzen", {**IDA, "args": {"start_datum": "2027-05-20", "ende_datum": "2027-05-23",
                                                                           "grund": "Zug eine Woche später (Test)"}})
    assert a["ok"] is True
    nachher = [t["datum"] for t in bauen.Bauer(arbeit / "reisen" / "beispielreise", arbeit / "probe").daten()["route"]["tage"]]
    erwartet = [(datetime.date(2027, 5, 20) + datetime.timedelta(days=i)).isoformat() for i in range(len(vorher))]
    assert len(nachher) == len(vorher) and nachher == erwartet


@pytest.mark.parametrize("args, grund", [
    ({"start_datum": "2027-05-20"}, "grund"),
    ({"grund": "x"}, "Nichts zu ändern"),
    ({"start_datum": "2027-05-13", "grund": "x"}, "Nichts zu ändern"),
    ({"start_ort": "O-99", "grund": "x"}, "O-99"),
    ({"start_datum": "31.02.2027", "grund": "x"}, "JJJJ-MM-TT"),
    ({"ende_datum": "morgen", "grund": "x"}, "JJJJ-MM-TT"),
    ({"start_datum": "", "grund": "x"}, "start_datum"),
    ({"ende_datum": "2027-05-10", "grund": "x"}, "vor"),
])
def test_start_ende_setzen_lehnt_ungueltiges_ab(repo, args, grund):
    """AC-29: Ablehnung mit verständlichem Grund, die Arbeitskopie bleibt unverändert."""
    _, origin, arbeit, _ = repo
    s = schreiber(repo)
    stand = git(origin, "rev-parse", "main")
    with pytest.raises(sb.Ablehnung, match=grund):
        s.schreiben("beispielreise", "start_ende_setzen", {**IDA, "args": args})
    assert not git(arbeit, "status", "--porcelain") and git(origin, "rev-parse", "main") == stand


def test_start_ende_setzen_entfernt_ende(repo):
    """AC-30: Leerer Text entfernt ende.ort bzw. ende.datum; ohne Ende baut die Reise (höchstens Warnungen)."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "start_ende_setzen", {**IDA, "args": {"ende_ort": "", "ende_datum": "", "grund": "Ende offen (Test)"}})
    assert a["ok"] is True and "entfernt" in a["text"]
    r, _ = routen_auf_main(origin)
    assert not (r.get("ende") or {}).get("datum") and not (r.get("ende") or {}).get("ort")
    assert r["start"] == {"datum": datetime.date(2027, 5, 13), "ort": "O-01"}


def test_start_ende_setzen_warnung_kommt_als_hinweis(repo):
    """AC-31: Ein Ende, das nicht zum Plan passt, ist nur eine Warnung: eingetragen, und sie steht als Hinweis in der Antwort."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "start_ende_setzen", {**IDA, "args": {"ende_datum": "2027-05-18", "grund": "zwei Tage länger (Test)"}})
    assert a["ok"] is True
    assert a["hinweise"] == ["plan: Der aktuelle Plan endet am 16.05., die Reise aber am 18.05. (-2 Tag(e))."]
    r, _ = routen_auf_main(origin)
    assert r["ende"]["datum"] == datetime.date(2027, 5, 18)
