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


# ---------- Arten ----------

def test_art_anlegen_geht_nach_main_und_wird_veroeffentlicht(repo):
    wurzel, origin, arbeit, stempel = repo
    s = schreiber(repo)
    vorher = git(origin, "rev-parse", "main")
    a = s.schreiben("beispielreise", "art_definieren", {**IDA, "args": {"bezeichnung": "Refugi", "grundform": "aufenthalt",
                                                                         "beschreibung": "bewirtschaftete Berghütte", "grund": "GR-Etappen"}})
    assert a["ok"] and "Refugi" in a["text"] and "refugi" in a["text"] and "Aufenthalt" in a["text"]
    assert git(origin, "rev-parse", "main") == a["commit"] != vorher
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
        ({"art": "hotel"}, "nichts daran soll sich ändern"),
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
        and "veränderlich" in a["text"] and "Stufe empfohlen" in a["text"]
    arten, _ = arten_auf_main(origin)
    m = arten["pension"]["merkmale"]["stornierung"]
    assert m == {"name": "Stornierung", "typ": "auswahl", "werte": ["kostenlos", "gegen Gebühr", "nicht möglich", "unklar"],
                 "veraenderlich": True, "hilfe": "Buchungsbedingungen auf der Website", "frage": "Bis wann kann man absagen?", "auch": ["storno"]}
    assert "stufe" not in m                           # empfohlen ist die Vorgabe und steht nicht in der Datei
    assert arten["pension"]["merkmale"]["preis"]["typ"] == "geld" and arten["hotel"]["merkmale"]["lage"]["stufe"] == "angeboten"
    # Umbenennen und Stufe
    s.vorbereiten()
    a = s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "merkmal": "stornierung",
                                                                             "bezeichnung": "Absagen", "stufe": "pflicht"}})
    assert "Name „Stornierung“ → „Absagen“" in a["text"] and "Stufe pflicht" in a["text"]
    arten, _ = arten_auf_main(origin)
    assert arten["pension"]["merkmale"]["stornierung"]["name"] == "Absagen" and arten["pension"]["merkmale"]["stornierung"]["stufe"] == "pflicht"
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
    with pytest.raises(sb.Ablehnung, match="nichts daran soll sich ändern"):
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "merkmal": "preis"}})
    with pytest.raises(sb.Ablehnung, match="„stufe“ muss"):
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "pension", "merkmal": "preis", "stufe": "wichtig"}})


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
        assert code == 422 and not a["ok"] and "Organisator" in a["fehler"]
        code, a = post("beispielreise/art_definieren", anfrage, geheim)
        assert code == 422 and "nichts daran soll sich ändern" in a["fehler"]
    finally:
        server.shutdown()
        sb.Dienst.schreiber = None


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
    assert r["unterkuenfte"]["U-02"]["merkmale"]["fruehstueck"] == {"wert": "inklusive", "notiz": "Beispielwert, erfunden"}   # Nachbarn unberührt
    assert "# Alle Unterkünfte sind erfunden" in text and "buchung: gebucht   # Beispielwert" in text        # Kommentare bleiben
    assert git(origin, "log", "-1", "--format=%s", "main") == "Beispielreise – Malerweg in vier Tagen: U-02 Pension Burgblick: Preis pro Nacht „85 €“ → „95 €“"
    assert "Karl (mitwirkend)" in git(origin, "log", "-1", "--format=%b", "main")
    # Nur die geänderte Stelle: der Rest der Datei ist zeichengleich
    import difflib
    diff = [z for z in difflib.unified_diff(vorher.splitlines(), text.splitlines(), lineterm="", n=0) if z[:1] in "+-" and z[:3] not in ("+++", "---")]
    assert diff == ['-      preis: {wert: "85 €", notiz: "Beispielwert, erfunden"}',
                    '+      preis: {wert: "95 €", geprueft: 2026-10-29, quelle: "Website der Pension"}']
    # Werte je Datum: der Eintrag für den 15.5. wird ersetzt, der Eintrag ohne gilt bleibt
    s.vorbereiten()
    a = s.schreiben("beispielreise", "wert_eintragen", {**IDA, "args": {"ziel": "U-01", "merkmal": "preis", "quelle": "Booking", "geprueft": "2026-10-29",
                                                                        "werte": [{"wert": "150 €", "gilt": ["2027-05-15", "2027-05-16"]}]}})
    assert "150 € (am 15.05., 16.05.) (vorher: 140 € (am 15.05.))" in a["text"]
    r, text = routen_auf_main(origin)
    assert r["unterkuenfte"]["U-01"]["merkmale"]["preis"] == [
        {"wert": "120 €", "notiz": "Beispielwert, erfunden"},
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
    assert u["ort"] == "O-07" and u["art"] == "pension" and u["typ"] == "Pension" and u["buchungslink"].startswith("https://")
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
    a = s.schreiben("beispielreise", "option_anlegen", {**KARL, "args": {"wahlstelle": "V-03", "titel": "Pension Elbblick", "unterkuenfte": ["U-05"],
                                                                         "plus": ["Elbblick"], "grund": "Karl kennt sie"}})
    assert "V-03.c" in a["text"] and "vorgeschlagen" in a["text"]
    r, text = routen_auf_main(origin)
    o = next(o for o in r["wahlstellen"]["V-03"]["optionen"] if o["id"] == "V-03.c")
    assert o["unterkuenfte"] == ["U-05"] and o["plus"] == ["Elbblick"] and o["quelle"] == "Vorschlag von Karl im Gespräch (Claude-App)"
    assert o["verlauf"] == [{"datum": datetime.date.today(), "status": "vorgeschlagen", "wer": "Karl", "grund": "Karl kennt sie"}]
    assert "wer: Karl, grund:" in text and "&id" not in text
    # Wahlstelle planung ohne Frage: die Frage entsteht mit (offene-fragen.md), Schlüssel bleiben gültig
    s.vorbereiten()
    a = s.schreiben("beispielreise", "wahlstelle_anlegen", {**KARL, "args": {"titel": "Anreise nach Stadt Wehlen", "an": ["T-01"], "bereich": "bahn",
        "optionen": [{"titel": "S-Bahn wie bisher", "strecken": ["E-20"]}, {"titel": "Mit dem Auto", "text": "Parken in Wehlen", "minus": ["Auto steht vier Tage"]}]}})
    assert "V-04" in a["text"] and "F-04" in a["text"]
    r, _ = routen_auf_main(origin)
    w = r["wahlstellen"]["V-04"]
    assert w["art"] == "planung" and w["an"] == ["T-01"] and w["bereich"] == "bahn" and w["frage"] == "F-04"
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
    assert "art „Gasthof“ → „pension“" in a["text"] and "Grund: eher eine Pension" in a["text"]
    r, _ = routen_auf_main(origin)
    assert r["unterkuenfte"]["U-03"]["art"] == "pension" and r["unterkuenfte"]["U-03"]["typ"] == "Pension"
    s.vorbereiten()
    a = s.schreiben("beispielreise", "ding_aendern", {**KARL, "args": {"ziel": "O-03", "name": "Hohnstein (Sächs. Schweiz)", "hinweis": ""}})
    r, _ = routen_auf_main(origin)
    assert r["orte"]["O-03"] == {"name": "Hohnstein (Sächs. Schweiz)"}
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
        ("ding_anlegen", {"was": "zelt", "titel": "X", "quelle": "x"}, "unterkunft, strecke oder ort"),
        ("option_anlegen", {"wahlstelle": "V-03", "titel": "X", "unterkuenfte": ["U-02"], "strecken": ["E-01"]}, "nur eines von"),
        ("option_anlegen", {"wahlstelle": "V-03", "titel": "X", "erfordert": ["V-09.z"]}, "gibt es nicht"),
        ("option_anlegen", {"wahlstelle": "V-99", "titel": "X"}, "gibt es nicht"),
        ("wahlstelle_anlegen", {"titel": "X", "optionen": []}, "mindestens eine Option"),
        ("wahlstelle_anlegen", {"titel": "X", "an": ["T-77"], "optionen": [{"titel": "a"}]}, "gibt es nicht"),
        ("wahlstelle_anlegen", {"titel": "X", "art": "vielleicht", "optionen": [{"titel": "a"}]}, "planung"),
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
