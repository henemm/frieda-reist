"""Tests für engine/schreiben.py: der Konnektor schreibt direkt in die Ontologie der Reise (ADR-0001, Paket O-3).

Aufbau: ein erfundenes Reisen-Repo mit der Beispielreise und einem „origin“ daneben; die Software liegt als Verweis engine/
im Repo (wie der Verweis engine -> frieda/engine einer Instanz). Veröffentlichen ist ein Stummel, der nur festhält, dass er
gerufen wurde."""
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
    # Jemand anderes schreibt inzwischen nach main (eine Sitzung, das Einarbeiten …)
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
