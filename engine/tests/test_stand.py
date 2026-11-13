"""Tests für den Reise-Stand (Epic #223, engine/stand.py): Nummer, Änderungsliste, Zustand auf dem Server, Schreibantwort,
publish_status, api/stand und Zeiten mit Zeitzone. Nur mit der Beispielreise und erfundenen Daten."""
import datetime
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import stand  # noqa: E402
from test_schreiben import repo  # noqa: E402,F401  (Fixture: Reisen-Repo mit origin und Arbeitskopie des Schreibwegs)

WURZEL = Path(__file__).resolve().parent.parent.parent
BEISPIEL = WURZEL / "beispiel" / "reisen" / "beispielreise"


def git(ordner, *args):
    return subprocess.run(["git", "-C", str(ordner), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def reisen_repo(tmp_path):
    """Reisen-Repo mit der Beispielreise und einem Ordner frieda/ (steht für die Software) -> (wurzel, commit(text, datei))."""
    w = tmp_path / "repo"
    (w / "reisen").mkdir(parents=True)
    import shutil
    shutil.copytree(BEISPIEL, w / "reisen" / "beispielreise")
    (w / "frieda").mkdir()
    (w / "frieda" / "version").write_text("1\n")
    git(w, "init", "-q", "-b", "main")
    git(w, "config", "user.email", "test@example.invalid")
    git(w, "config", "user.name", "Ida Beispiel")
    git(w, "add", "-A")
    git(w, "commit", "-qm", "Beispielreise angelegt")

    def commit(text, datei="reisen/beispielreise/notiz.md", person=None):
        p = w / datei
        p.write_text((p.read_text() if p.exists() else "") + text + "\n")
        git(w, "add", "-A")
        git(w, "commit", "-qm", text + (f"\n\n{stand.PERSON_TRAILER}: {person}\n" if person else ""))
    return w, commit


# ---------- S1: Nummer ----------

def test_nummer_zaehlt_nur_aenderungen_der_reise(reisen_repo):
    w, commit = reisen_repo
    ordner = w / "reisen" / "beispielreise"
    assert stand.nummer(ordner) == 1
    commit("Beispielreise: Wert eingetragen")
    commit("Beispielreise: Frage angelegt")
    assert stand.nummer(ordner) == 3                         # zwei Schreibvorgänge, zwei aufeinanderfolgende Nummern
    commit("Software nachgezogen", "frieda/version")         # Software-Update ohne Inhaltsänderung
    assert stand.nummer(ordner) == 3
    assert stand.nummer(ordner, "HEAD~3") == 1


def test_nummer_fehlt_ohne_git_und_im_flachen_klon(reisen_repo, tmp_path):
    w, commit = reisen_repo
    commit("Beispielreise: zweiter Stand")
    assert stand.nummer(tmp_path / "gibt-es-nicht") is None
    ohne = tmp_path / "ohne-git"
    ohne.mkdir()
    assert stand.nummer(ohne) is None
    flach = tmp_path / "flach"
    subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{w}", str(flach)], check=True, capture_output=True)
    assert stand.nummer(flach / "reisen" / "beispielreise") is None   # die Zahl wäre falsch (1 statt 2)


# ---------- S9: Änderungsliste ----------

def test_aenderungen_mit_person_zeit_und_namen_statt_kennungen(reisen_repo):
    w, commit = reisen_repo
    commit("Beispielreise: U-01 „Hotel am Elbufer“ geändert: Preis", person="Karl")
    commit("Beispielreise: Wert an U-01 eingetragen")
    liste = stand.aenderungen(w / "reisen" / "beispielreise", {"U-01": "Hotel am Elbufer"})
    assert [a["nummer"] for a in liste] == [3, 2, 1]
    assert liste[0] == {"nummer": 3, "zeit": liste[0]["zeit"], "was": "Wert an „Hotel am Elbufer“ eingetragen", "wer": "Ida Beispiel"}
    assert liste[1]["was"] == "„Hotel am Elbufer“ geändert: Preis" and liste[1]["wer"] == "Karl"
    assert liste[2]["was"] == "Beispielreise angelegt"
    assert all(a["zeit"].endswith("Z") for a in liste)
    assert stand.ohne_kennungen("X-99 bleibt", {}) == "X-99 bleibt"


def test_namen_der_ids_ohne_grundformen_zu_kennen(tmp_path):
    d = bauen.bauen(BEISPIEL, tmp_path / "s")
    namen = stand.namen_der_ids(d)
    assert namen["U-01"] and namen["T-01"] and namen["E-01"]
    assert all(stand.ID_MUSTER.fullmatch(i) for i in namen)


def test_bau_legt_den_reise_stand_in_die_seite_ohne_bauzeit(reisen_repo, tmp_path):
    """Die Nummer steht in der Seite (daten.reise_stand); gleicher Inhalt ergibt dieselbe Seite (kein Zeitstempel des Baus)."""
    w, commit = reisen_repo
    commit("Beispielreise: zweiter Stand", person="Karl")
    ziel = tmp_path / "s"
    bauen.bauen(w / "reisen" / "beispielreise", ziel)
    d = json.loads((ziel / "daten.json").read_text())
    assert d["reise_stand"]["nummer"] == 2 and d["reise_stand"]["aenderungen"][0]["wer"] == "Karl"
    assert d["reise_stand"]["zeit"] == d["reise_stand"]["aenderungen"][0]["zeit"]
    sw = (ziel / "sw.js").read_text()
    bauen.bauen(w / "reisen" / "beispielreise", ziel)
    assert (ziel / "sw.js").read_text() == sw
    commit("Beispielreise: dritter Stand")
    bauen.bauen(w / "reisen" / "beispielreise", ziel)
    assert json.loads((ziel / "daten.json").read_text())["reise_stand"]["nummer"] == 3 and (ziel / "sw.js").read_text() != sw


def test_bau_ohne_git_hat_keinen_reise_stand(tmp_path):
    import shutil
    shutil.copytree(BEISPIEL, tmp_path / "beispielreise")
    bauen.bauen(tmp_path / "beispielreise", tmp_path / "s")
    assert json.loads((tmp_path / "s" / "daten.json").read_text())["reise_stand"] is None


# ---------- Stufe 2 (#347): Stand je Weg ----------

def test_fuer_seite_je_weg(reisen_repo, tmp_path, monkeypatch):
    """AC-17: Eine Reise mit Speichereintrag (#454: im Speicher ist, was im Speicher steht) bekommt Nummer, Zeit und Änderungsliste aus dem Speicher
    (der Bau kennt nur den Ordner; die Reise ist sein Name). Eine Git-Reise liefert dasselbe wie vor der Verschiebung
    (stand_git). Ohne Eintrag und ohne Git bleibt es bei None."""
    import shutil
    import reisespeicher
    import stand_git
    w, commit = reisen_repo
    commit("Beispielreise: zweiter Stand", person="Karl")
    git_ordner = w / "reisen" / "beispielreise"
    s = stand.fuer_seite(git_ordner, {})
    assert s["nummer"] == 2 == stand_git.nummer(git_ordner)
    assert s["aenderungen"] == stand_git.aenderungen(git_ordner, {}) and s["aenderungen"][0]["wer"] == "Karl"
    # Speicher-Reise
    stadt = BEISPIEL.parent / "stadtwochenende"
    monkeypatch.setenv("FR_SPEICHERREISEN", "stadtwochenende")
    reisespeicher.importieren(stadt, "stadtwochenende", wer="Tom")
    reisespeicher.vorgang_schreiben("stadtwochenende", {"inhalt/notiz.md": b"Beispielwert\n"}, wer="Lea",
                                    werkzeug="item_update", titel="U-01 geändert: Preis", wann="2026-11-06T09:00:00Z")
    ordner = tmp_path / "bau" / "stadtwochenende"
    reisespeicher.exportieren("stadtwochenende", ordner)
    daten = {"dinge": {"U-01": {"name": "Pension Beispiel"}}}
    s = stand.fuer_seite(ordner, daten)
    assert s["nummer"] == 2 and s["zeit"] == "2026-11-06T09:00:00Z"
    assert s["aenderungen"][0] == {"nummer": 2, "zeit": "2026-11-06T09:00:00Z", "was": "„Pension Beispiel“ geändert: Preis",
                                   "wer": "Lea"}
    assert [a["nummer"] for a in s["aenderungen"]] == [2, 1] and s["aenderungen"][1]["wer"] == "Tom"
    bauen.bauen(ordner, tmp_path / "seite")
    assert json.loads((tmp_path / "seite" / "daten.json").read_text())["reise_stand"]["nummer"] == 2
    # Reise der Liste ohne Eintrag und ohne Git: kein Stand. Seit #454 ist im Speicher, was im Speicher steht: eine leere
    # FR_SPEICHERREISEN ändert am Stand der Speicherreise nichts
    monkeypatch.setenv("FR_SPEICHERREISEN", "stadtwochenende,beispielreise")
    shutil.copytree(BEISPIEL, tmp_path / "ohne" / "beispielreise")
    assert stand.fuer_seite(tmp_path / "ohne" / "beispielreise", {}) is None
    monkeypatch.setenv("FR_SPEICHERREISEN", "")
    assert stand.fuer_seite(ordner, daten)["nummer"] == 2


def test_fuer_seite_unlesbare_einstellungen_bricht_ab(reisen_repo, tmp_path, monkeypatch):
    """#361 (AC-8): Ist die Einstellungsdatei vorhanden, aber nicht lesbar, weiß der Bau nicht, welche Reisen im Speicher
    liegen: er bricht laut ab und nimmt nie einen Stand aus Git."""
    import instanz
    w, _ = reisen_repo
    unlesbar = tmp_path / "einstellungen-unlesbar.env"
    unlesbar.mkdir()
    monkeypatch.delenv("FR_SPEICHERREISEN", raising=False)
    monkeypatch.setenv("FR_EINSTELLUNGEN", str(unlesbar))
    with pytest.raises(instanz.EinstellungenNichtLesbar):
        stand.fuer_seite(w / "reisen" / "beispielreise", {})


def test_probebau_ohne_stand(monkeypatch, tmp_path):
    """AC-17: Probebau und Rollenprüfung des Schreibwegs brauchen keinen Stand; die Arbeitskopie hat keinen Bezug zum
    Speicher. Wächtertest: Bauer.daten() ruft fuer_seite nicht (nur Bauer.schreiben)."""
    import shutil
    import schreiben
    monkeypatch.setattr(stand, "fuer_seite", lambda *a, **k: pytest.fail("Probebau fragt den Stand"))
    shutil.copytree(BEISPIEL, tmp_path / "beispielreise")
    assert schreiben.warnungen_des_baus(tmp_path / "beispielreise") == []
    assert bauen.Bauer(tmp_path / "beispielreise", tmp_path / "ziel").eck


# ---------- S3–S5: Zustand auf dem Server ----------

@pytest.fixture
def server(tmp_path, monkeypatch):
    """Seiten- und Dienstordner einer Instanz -> (seite(nummer), gesichert(nummer, zeit), lauf(**felder), rot(**felder))."""
    seiten, dienst = tmp_path / "seiten", tmp_path / "_dienst"
    monkeypatch.setenv("FR_SEITEN", str(seiten))
    monkeypatch.setenv("FR_DIENST", str(dienst))
    (seiten / "beispielreise").mkdir(parents=True)
    (dienst / "reise-stand").mkdir(parents=True)

    def seite(n, zeit="2026-11-02T08:30:00Z"):
        (seiten / "beispielreise" / "daten.json").write_text(json.dumps({"reise_stand": {"nummer": n, "zeit": zeit, "aenderungen": []}}))

    def gesichert(n, zeit):
        stand.gesichert_schreiben("beispielreise", n, "abc", zeit)

    def lauf(**f):
        (dienst / "reise-stand" / "beispielreise.lauf.json").write_text(json.dumps(f))

    def rot(**f):
        (dienst / "veroeffentlichen-rot").write_text("".join(f"{k}={v}\n" for k, v in f.items()))
    return seite, gesichert, lauf, rot


JETZT = datetime.datetime(2026, 11, 2, 8, 34, 0, tzinfo=datetime.timezone.utc)


def test_zustaende_vom_sichern_bis_zur_veroeffentlichung(server):
    seite, gesichert, lauf, rot = server
    assert stand.lesen("beispielreise", JETZT)["zustand"] == "unbekannt"
    seite(42)
    z = stand.lesen("beispielreise", JETZT)
    assert z["zustand"] == "veroeffentlicht" and z["veroeffentlicht"]["nummer"] == 42 and stand.enthalten(z, 42) is True
    gesichert(43, "2026-11-02T08:32:00Z")                                   # gesichert, noch nicht gebaut
    z = stand.lesen("beispielreise", JETZT)
    assert z["zustand"] == "wartet" and z["gesichert"] == {"nummer": 43, "zeit": "2026-11-02T08:32:00Z"}
    assert z["dauer"] == 120 and not z["ueber_ziel"] and stand.enthalten(z, 43) is False and stand.enthalten(z, 42) is True
    lauf(zustand="baut", nummer=43, gesichert="2026-11-02T08:32:00Z", seit="2026-11-02T08:32:10Z")
    z = stand.lesen("beispielreise", JETZT + datetime.timedelta(seconds=30))
    assert z["zustand"] == "baut" and z["seit"] == "2026-11-02T08:32:10Z" and z["ueber_ziel"]   # 150 s: über dem Ziel
    lauf(zustand="veroeffentlicht", nummer=43, gesichert="2026-11-02T08:32:00Z", seit="2026-11-02T08:33:10Z", dauer=70)
    seite(43)
    z = stand.lesen("beispielreise", JETZT)
    assert z["zustand"] == "veroeffentlicht" and z["veroeffentlicht"] == {"nummer": 43, "zeit": "2026-11-02T08:33:10Z"}
    assert z["dauer"] == 70 and stand.enthalten(z, 43) is True


def test_fehlgeschlagen_nennt_grund_und_sichtbaren_stand(server):
    seite, gesichert, lauf, rot = server
    seite(42)
    gesichert(43, "2026-11-02T08:32:00Z")
    lauf(zustand="fehlgeschlagen", nummer=43, gesichert="2026-11-02T08:32:00Z", seit="2026-11-02T08:33:00Z",
         grund="plan/routen.yaml: U-09 gibt es nicht")
    z = stand.lesen("beispielreise", JETZT)
    assert z["zustand"] == "fehlgeschlagen" and z["grund"] == "plan/routen.yaml: U-09 gibt es nicht" and z["grund_art"] == "bau"
    assert z["veroeffentlicht"]["nummer"] == 42
    # Ein neuer Stand nach dem Fehlschlag wartet wieder; rote Software hält ihn auf und nennt die roten Tests
    gesichert(44, "2026-11-02T08:33:30Z")
    assert stand.lesen("beispielreise", JETZT)["zustand"] == "wartet"
    rot(commit="abc", art="software", reisen="", seit="2026-11-02T08:20:00Z", tests="test_bauen.py::test_x")
    z = stand.lesen("beispielreise", JETZT)
    assert z["zustand"] == "fehlgeschlagen" and z["grund_art"] == "software" and z["grund"] == "test_bauen.py::test_x"


# ---------- S2: Schreibantwort nennt beide Stände ----------

def test_schreibweg_zaehlt_und_antwortet_mit_beiden_staenden(repo, tmp_path, monkeypatch):
    import test_schreiben as ts
    import schreiben as sb
    wurzel, _, arbeit, _ = repo
    monkeypatch.setattr(sb.Schreiber, "veroeffentlichen_anstossen", lambda self: None)
    seiten = tmp_path / "seiten"
    (seiten / "beispielreise").mkdir(parents=True)
    (seiten / "beispielreise" / "daten.json").write_text(json.dumps({"reise_stand": {"nummer": 1}}))
    monkeypatch.setenv("FR_SEITEN", str(seiten))
    s = ts.schreiber(repo)
    a = s.schreiben("beispielreise", "art_definieren", {**ts.IDA, "args": {"bezeichnung": "Refugi", "grundform": "aufenthalt"}})
    assert a["stand"] == {"gesichert": 2, "veroeffentlicht": 1}
    assert f"{stand.PERSON_TRAILER}: Ida" in git(wurzel, "log", "-1", "--format=%B", "origin/main")
    s.vorbereiten()
    a = s.schreiben("beispielreise", "art_definieren", {**ts.IDA, "args": {"bezeichnung": "Ryokan", "grundform": "aufenthalt"}})
    assert a["stand"]["gesichert"] == 3
    g = json.loads((tmp_path / "_dienst" / "reise-stand" / "beispielreise.gesichert.json").read_text())
    assert g["nummer"] == 3 and g["commit"] == a["commit"] and g["zeit"].endswith("Z")


def test_jedes_schreibwerkzeug_nennt_beide_staende(monkeypatch, tmp_path):
    """Über die Werkzeugliste: Jedes Werkzeug des Konnektors, das über den Schreibweg sichert, hängt den Satz zum Reise-Stand an;
    der Satz entsteht an einer Stelle (tools/call), nicht je Werkzeug."""
    import konnektor as kn
    import schnittstelle
    gerufen = []

    def schreibweg(reise, werkzeug, anfrage):
        gerufen.append(werkzeug)
        return {"ok": True, "text": "eingetragen", "stand": {"gesichert": 43, "veroeffentlicht": 42}}, None

    def ueber_schreibweg(zugang, name, args):
        kn.stand_merken(schreibweg("beispielreise", name, {})[0]["stand"])
        return "Eingetragen.", False

    monkeypatch.setattr(kn, "werkzeug", ueber_schreibweg)
    schreibende = set(kn.ONTOLOGIE_WERKZEUGE) | {"entscheiden", "person_einladen", "person_entfernen"}
    for name in sorted(schreibende):
        a = kn.antwort_auf({"reise": "beispielreise", "person": "ida"},
                           {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": {}}})
        text = a["result"]["content"][0]["text"]
        assert "Gesichert als Reise-Stand 43. Veröffentlicht ist Stand 42" in text, name
        assert schnittstelle.INTERN_ZU_ENGLISCH["veroeffentlichung_pruefen"] in text   # der englische Name, wie tools/list
    # Ohne Schreibvorgang kein Satz (Lesen, Ablehnung)
    monkeypatch.setattr(kn, "werkzeug", lambda zugang, name, args: ("Gelesen.", False))
    a = kn.antwort_auf({"reise": "beispielreise", "person": "ida"},
                       {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "ueberblick", "arguments": {}}})
    assert a["result"]["content"][0]["text"] == "Gelesen."


def test_schreib_anfrage_merkt_den_stand_nur_bei_erfolg(monkeypatch):
    import io
    import konnektor as kn

    class Antwort(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setenv("KN_SCHREIBDIENST", "http://127.0.0.1:9")
    monkeypatch.setattr(kn.urllib.request, "urlopen", lambda req, timeout=None: Antwort(
        json.dumps({"ok": True, "text": "x", "stand": {"gesichert": 7, "veroeffentlicht": None}}).encode()))
    kn._gesichert.wert = None
    kn.schreib_anfrage("beispielreise", "wert_eintragen", {})
    assert kn.stand_satz().startswith("Gesichert als Reise-Stand 7. Veröffentlicht ist noch kein Stand")
    assert kn.stand_satz() is None                                             # einmal je Aufruf
    monkeypatch.setattr(kn.urllib.request, "urlopen", lambda req, timeout=None: Antwort(json.dumps({"ok": True, "text": "x"}).encode()))
    kn.schreib_anfrage("beispielreise", "wert_eintragen", {})
    assert kn.stand_satz().startswith("Gesichert. Ob die Änderung auf der Seite ist")   # Schreibweg ohne Nummer


# ---------- S3: publish_status ----------

def test_publish_status_meldet_enthalten_und_zustand(server, monkeypatch):
    import konnektor as kn
    seite, gesichert, lauf, rot = server
    monkeypatch.setenv("FR_ZEITZONE", "Europe/Berlin")
    kn._zone.wert = None
    seite(42, "2026-11-02T08:00:00Z")
    gesichert(43, "2026-11-02T08:32:00Z")
    t = kn.veroeffentlichung_text("beispielreise")
    assert "- Gesichert: Stand 43, 02.11.2026 09:32 (MEZ)" in t and "- Veröffentlicht: Stand 42" in t
    assert "- Zustand: wartet auf das Veröffentlichen" in t and "- Stand 43 enthalten: nein" in t
    assert "Ziel: höchstens 2 Min." in t
    assert "- Stand 42 enthalten: ja" in kn.veroeffentlichung_text("beispielreise", 42)
    lauf(zustand="fehlgeschlagen", nummer=43, gesichert="2026-11-02T08:32:00Z", seit="2026-11-02T08:33:00Z", grund="Baufehler X")
    t = kn.veroeffentlichung_text("beispielreise")
    assert "- Zustand: fehlgeschlagen, 02.11.2026 09:33 (MEZ). Sichtbar bleibt Stand 42." in t and "- Grund: Baufehler X" in t
    lauf(zustand="veroeffentlicht", nummer=43, gesichert="2026-11-02T08:32:00Z", seit="2026-11-02T08:35:30Z", dauer=210)
    seite(43)
    t = kn.veroeffentlichung_text("beispielreise", 43)
    assert "- Stand 43 enthalten: ja" in t and "3 Min. 30 s (Ziel: höchstens 2 Min.) – länger als das Ziel" in t


def test_publish_status_ist_ein_werkzeug_fuer_alle_mit_englischem_namen():
    import konnektor as kn
    import schnittstelle
    w = next(w for w in kn.WERKZEUGE if w["name"] == "veroeffentlichung_pruefen")
    assert w["annotations"]["readOnlyHint"] and schnittstelle.INTERN_ZU_ENGLISCH["veroeffentlichung_pruefen"] == "publish_status"
    assert "veroeffentlichung_pruefen" not in kn.SCHREIB_AKTION


def test_api_stand_vom_server(server):
    """api/stand liefert den Stand vom Server; der Service Worker lässt api/ nie über seinen Speicher (sonst sähe die Seite
    den alten Stand, bis jemand „Aktualisieren“ tippt)."""
    import threading
    import urllib.request
    from http.server import ThreadingHTTPServer
    import rueckmeldungen as rm
    seite, gesichert, lauf, rot = server
    seite(42)
    gesichert(43, "2026-11-02T08:32:00Z")
    import instanz
    (instanz.ablage() / "beispielreise").mkdir(parents=True)
    s = ThreadingHTTPServer(("127.0.0.1", 0), rm.Dienst)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{s.server_address[1]}/beispielreise/stand") as r:
            assert r.headers["Cache-Control"] == "no-store"
            z = json.loads(r.read())
    finally:
        s.shutdown()
    assert z["gesichert"]["nummer"] == 43 and z["veroeffentlicht"]["nummer"] == 42 and z["zustand"] == "wartet"
    sw = (WURZEL / "engine" / "sw.vorlage.js").read_text(encoding="utf-8")
    assert 'if (url.pathname.startsWith(scope + "api/") || url.pathname === scope + "sw.js") return;' in sw


# ---------- S6: Zeiten mit Zeitzone ----------

def test_zeiten_des_konnektors_tragen_die_zone(monkeypatch):
    import konnektor as kn
    kurz_vor = datetime.datetime(2026, 11, 2, 23, 30, tzinfo=datetime.timezone.utc)   # Datumswechsel in Mitteleuropa
    assert kn.zeit_de(kurz_vor, "de", "Europe/Berlin") == "03.11.2026 00:30 (MEZ)"
    assert kn.zeit_de(kurz_vor, "en", "Europe/Berlin") == "03/11/2026 00:30 (CET)"
    assert kn.zeit_de(datetime.datetime(2026, 7, 1, 22, 0, tzinfo=datetime.timezone.utc), "de", "Europe/Berlin") == "02.07.2026 00:00 (MESZ)"
    assert kn.zeit_de(kurz_vor, "de", "UTC") == "02.11.2026 23:30 (UTC)"
    assert kn.zeit_de(kurz_vor, "de", "Nirgendwo/Gibtsnicht") == "02.11.2026 23:30 (UTC)"
    monkeypatch.delenv("FR_ZEITZONE", raising=False)
    kn._zone.wert = None
    assert kn.aufruf_zone() == "UTC"                                   # ohne Angabe nennt die Zeit die Zone UTC
    assert kn.zeit_iso_de("2026-11-02T00:00:00Z", "de").endswith("(UTC)")


def test_zone_der_person_aus_ihrem_geraet(monkeypatch, tmp_path):
    import konnektor as kn
    import konten
    monkeypatch.setenv("FR_ZEITZONE", "Europe/Lisbon")
    monkeypatch.setenv("FR_MAIL_DATEI", str(tmp_path / "mails.jsonl"))
    monkeypatch.setenv("FR_BASIS", "https://frieda.example.invalid")
    konten.code_anfordern("ida@example.invalid")
    code = json.loads((tmp_path / "mails.jsonl").read_text().splitlines()[-1])["text"].split(": ", 1)[1][:7]
    kid = konten.anmelden("ida@example.invalid", code, name="Ida")[1]["id"]
    assert kn.zone_des_zugangs({"konto_id": kid}) == "Europe/Lisbon"
    konten.push_abo_speichern(kid, {"endpoint": "https://push.example.invalid/abc12345", "keys": {"p256dh": "a" * 20, "auth": "b" * 20}},
                              "beispielreise", "", "geraet123", "Europe/Berlin")
    assert kn.zone_des_zugangs({"konto_id": kid}) == "Europe/Berlin"
    assert kn.zone_des_zugangs({"reise": "beispielreise"}) == "Europe/Lisbon"


def test_seite_zeigt_zeiten_in_ortszeit_des_geraets():
    """Die Seite rechnet Zeiten aus api/stand und der Änderungsliste (UTC mit Z) mit Intl in die Ortszeit des Geräts um."""
    v = (WURZEL / "engine" / "vorlage.html").read_text(encoding="utf-8")
    assert 'const standZeit = iso => { try { return new Intl.DateTimeFormat(LOCALE, {day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit"}).format(new Date(iso))' in v
    assert 'fetch("api/stand", {cache: "no-store"})' in v
