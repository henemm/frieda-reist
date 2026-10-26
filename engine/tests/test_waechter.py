"""Tests für Paket E: Wächter und Erinnerer gegen die Beispielreise, mit simuliertem Datum.
Personen: Ida Bestimmerin, Karl Einbringer. Reisetage der Beispielreise: 13.–16.5.2027."""
import datetime
import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import konnektor as kn  # noqa: E402
import reise as rg  # noqa: E402
import rueckmeldungen as rm  # noqa: E402
import waechter as wa  # noqa: E402
from test_regeln import IDA, KARL, umgebung  # noqa: E402,F401  (umgebung: Fixture)

WURZEL = Path(__file__).resolve().parent.parent.parent
BEISPIEL = WURZEL / "beispiel" / "reisen" / "beispielreise"
D = datetime.date
BAUSTEINE = ["varianten", "karte", "tagesseiten", "rueckmeldungen", "fragen", "aufgaben", "wuensche", "waechter"]


class Reise:
    """Beispielreise gebaut und veröffentlicht, mit Ablage; Wächter und Konnektor lesen von dort."""

    def __init__(self, tmp, monkeypatch, status="fest", bausteine=None, regeln=None, geprueft=None):
        quelle = tmp / "quelle"
        shutil.copytree(BEISPIEL, quelle)
        y = yaml.safe_load((quelle / "reise.yaml").read_text(encoding="utf-8"))
        if status != "planung":
            y["status"] = {"wert": status, "verlauf": y["status"]["verlauf"] + [
                {"datum": D(2026, 10, 25), "wert": status, "wer": "Ida", "grund": "Test"}]}
        y["bausteine"] = BAUSTEINE if bausteine is None else bausteine
        if regeln:
            y.setdefault("regeln", {}).update(regeln)
        (quelle / "reise.yaml").write_text(yaml.safe_dump(y, allow_unicode=True), encoding="utf-8")
        if geprueft:   # Prüfdatum für den Preis von U-01 (veränderliche Angabe)
            r = quelle / "plan" / "routen.yaml"
            r.write_text(r.read_text(encoding="utf-8").replace(
                'preis: {wert: "120 €", notiz: "Beispielwert, erfunden"}',
                f'preis: {{wert: "120 €", notiz: "Beispielwert, erfunden", geprueft: {geprueft}, quelle: "https://beispiel.invalid/u1"}}'),
                encoding="utf-8")
        self.seiten = tmp / "seiten"
        bauen.bauen(quelle, self.seiten / "beispielreise")
        self.ablage = tmp / "ablage"
        (self.ablage / "beispielreise").mkdir(parents=True)
        self.o = self.ablage / "beispielreise"
        monkeypatch.setenv("RM_ABLAGE", str(self.ablage))
        monkeypatch.setenv("RM_SEITEN", str(self.seiten))
        monkeypatch.setenv("KN_SEITEN", str(self.seiten))

    def aufgabe(self, titel, name="Ida", **felder):
        a, fehler = rm.aufgabe_anlegen(self.o, {"name": name, "titel": titel, **felder})
        assert not fehler, fehler
        return a

    def lauf(self, heute, **kw):
        return wa.lauf_reise("beispielreise", heute, **kw)


@pytest.fixture
def reise(tmp_path, monkeypatch):
    def neu(**kw):
        return Reise(tmp_path / f"r{len(list(tmp_path.iterdir()))}", monkeypatch, **kw)
    return neu


# ---------- wann der Wächter arbeitet ----------

def test_waechter_arbeitet_nur_mit_baustein_und_ab_fest(reise):
    assert reise(status="fest").lauf(D(2026, 11, 1))["aktiv"]
    assert reise(status="unterwegs").lauf(D(2027, 5, 14))["aktiv"]
    for status in ("idee", "planung", "danach", "archiv"):
        r = reise(status=status).lauf(D(2026, 11, 1))
        assert not r["aktiv"] and "wacht der Wächter nicht" in r["grund"], status
    aus = reise(bausteine=[b for b in BAUSTEINE if b != "waechter"]).lauf(D(2026, 11, 1))
    assert not aus["aktiv"] and "ausgeschaltet" in aus["grund"]
    trocken = reise()
    assert trocken.lauf(D(2026, 11, 1), trocken=True)["auftrag"]    # würde angelegt, wird aber nicht geschrieben
    assert rm.auftraege(trocken.o) == [] and not trocken.o.joinpath("meldungen.jsonl").exists()


def test_waechter_ohne_veroeffentlichte_seite(tmp_path, monkeypatch):
    monkeypatch.setenv("RM_ABLAGE", str(tmp_path / "ablage"))
    monkeypatch.setenv("RM_SEITEN", str(tmp_path / "seiten"))
    r = wa.lauf_reise("beispielreise", D(2026, 11, 1))
    assert not r["aktiv"] and "nicht veröffentlicht" in r["grund"]
    assert wa.alle_reisen() == []


# ---------- Wächter: veränderliche Angaben ----------

def test_zu_pruefen_findet_nie_und_lange_nicht_gepruefte(reise):
    r = reise(geprueft="2026-10-20")
    d = wa.veroeffentlicht("beispielreise")
    # 12 Tage später ist die Angabe frisch, alles andere Veränderliche wurde nie geprüft
    items = wa.zu_pruefen(d, D(2026, 11, 1), 60)
    gefunden = {(t["bezug"], t["merkmal"]) for t in items}
    assert ("U-01", "preis") not in gefunden and ("U-01", "fruehstueck") in gefunden
    assert all(t["geprueft"] is None and t["grund"] == "noch nie geprüft" for t in items)
    # nicht veränderlich (Abendessen, Lage) und nicht im Plan (verworfene Option V-03.b) stehen nicht dabei
    assert not any(t["merkmal"] in ("abendessen", "lage", "zimmer") for t in items)
    assert not any(t["bezug"] == "V-03.b" for t in items)
    # 87 Tage später ist sie zu alt; die nie geprüften stehen trotzdem vorn
    spaeter = wa.zu_pruefen(d, D(2027, 1, 15), 60)
    alt = next(t for t in spaeter if (t["bezug"], t["merkmal"]) == ("U-01", "preis"))
    assert alt["alter_tage"] == 87 and "vor 87 Tagen" in alt["grund"] and alt["quelle"] == "https://beispiel.invalid/u1"
    assert spaeter[-1] is alt
    # eine längere Frist lässt sie wieder zu
    assert ("U-01", "preis") not in {(t["bezug"], t["merkmal"]) for t in wa.zu_pruefen(d, D(2027, 1, 15), 90)}


def test_pruefauftrag_einmal_und_mit_abstand(reise):
    r = reise(geprueft="2026-10-20")
    heute = D(2027, 1, 15)
    erg = r.lauf(heute)
    a = erg["auftrag"]
    assert a and a["name"] == "Wächter" and a["art"] == "Prüfung" and a["daten"]["frist_tage"] == 60
    assert 0 < len(a["daten"]["pruefung"]) <= wa.MAX_PRUEFUNGEN
    assert "NICHT ändern" in a["text"] and "offene Frage" in a["text"] and "U-01 " in a["text"]
    (gespeichert,) = rm.auftraege(r.o)
    assert gespeichert["id"] == a["id"] and gespeichert["status"] == "neu"
    # solange der Auftrag offen ist und danach eine Woche lang kommt kein zweiter
    assert r.lauf(heute)["auftrag"] is None
    rm.setze("beispielreise", a["id"], "uebernommen", "geprüft")
    assert r.lauf(heute + datetime.timedelta(days=3))["auftrag"] is None
    zweiter = r.lauf(heute + datetime.timedelta(days=8))["auftrag"]
    assert zweiter and zweiter["id"] != a["id"]
    assert len(rm.auftraege(r.o)) == 2


def test_pruefauftrag_ist_kein_entscheidungsauftrag(reise, capsys):
    r = reise()
    r.lauf(D(2026, 11, 1))
    rm.liste("beispielreise", False)
    aus = capsys.readouterr().out
    assert "PRÜFAUFTRAG des Wächters" in aus and "keine Entscheidung eines Bestimmers" in aus
    # kein Material für Widersprüche: nur die Entscheidungen im Plan stehen, kein Auftrag
    assert not [e for e in kn.stehende_entscheidungen("beispielreise", kn.daten("beispielreise")) if e.get("auftrag")]


def test_pruefauftrag_begrenzt_die_menge(reise, monkeypatch):
    r = reise()
    monkeypatch.setattr(wa, "MAX_PRUEFUNGEN", 2)
    a = r.lauf(D(2026, 11, 1))["auftrag"]
    assert len(a["daten"]["pruefung"]) == 2 and a["text"].count("\n- U-") + a["text"].count("\n- V-") >= 2


def test_frist_ist_einstellbar(reise):
    r = reise(geprueft="2026-10-20", regeln={"waechter_frist_tage": 10})
    erg = r.lauf(D(2026, 11, 1), trocken=True)
    assert ("U-01", "preis") in {(t["bezug"], t["merkmal"]) for t in erg["zu_pruefen"]}


# ---------- Erinnerer ----------

def test_erinnerer_meldet_frist_einmal_und_ueberfaellig_woechentlich(reise):
    r = reise()
    a = r.aufgabe("Fähre buchen", frist="2026-11-10", zustaendig="Karl", bezug=["T-01"])
    erg = r.lauf(D(2026, 11, 7))                       # Frist in 3 Tagen = Vorlauf
    (m,) = [x for x in erg["meldungen"] if x["art"] == "erinnerung"]
    assert m["an"] == ["Karl"] and "in 3 Tag(en)" in m["text"] and a["id"] in m["text"]
    assert not [x for x in r.lauf(D(2026, 11, 7))["meldungen"] if x["art"] == "erinnerung"]   # nicht doppelt
    assert not [x for x in r.lauf(D(2026, 11, 8))["meldungen"] if x["art"] == "erinnerung"]
    ueber = [x for x in r.lauf(D(2026, 11, 12))["meldungen"] if x["art"] == "erinnerung"]
    assert len(ueber) == 1 and "Überfällig seit 2 Tag(en)" in ueber[0]["text"]
    assert not [x for x in r.lauf(D(2026, 11, 15))["meldungen"] if x["art"] == "erinnerung"]  # erst nach 7 Tagen wieder
    wieder = [x for x in r.lauf(D(2026, 11, 19))["meldungen"] if x["art"] == "erinnerung"]
    assert len(wieder) == 1 and "Überfällig seit 9 Tag(en)" in wieder[0]["text"]
    # Karl sieht seine Meldungen, Ida nicht
    assert len(rm.meldungen(r.o, "Karl")) == 3 and rm.meldungen(r.o, "Ida") == []


def test_erinnerer_ab_termin_und_wer_zustaendig_ist(reise):
    r = reise()
    r.aufgabe("Hütte buchen", ab="2026-11-05", zustaendig="Karl")
    r.aufgabe("Zug buchen", ab="2026-11-05")                 # niemand zuständig -> Bestimmer
    r.aufgabe("Fahrrad leihen", ab="2026-11-05", zustaendig="Unbekannt")   # keine Person der Reise -> Bestimmer
    r.aufgabe("Später", ab="2026-12-01", zustaendig="Karl")
    assert not [m for m in r.lauf(D(2026, 11, 4))["meldungen"] if m["art"] == "erinnerung"]
    ms = [m for m in r.lauf(D(2026, 11, 5))["meldungen"] if m["art"] == "erinnerung"]
    assert sorted((m["an"][0], "Jetzt möglich (ab 5.11.2026)" in m["text"]) for m in ms) == \
        [("Ida", True), ("Ida", True), ("Karl", True)]
    assert not [m for m in r.lauf(D(2026, 11, 6))["meldungen"] if m["art"] == "erinnerung"]


def test_erinnerer_nur_offene_aufgaben_und_nur_ab_fest(reise):
    r = reise()
    a = r.aufgabe("Erledigt", frist="2026-11-01", zustaendig="Karl")
    rm.aufgabe_aendern(r.o, a["id"], {"name": "Karl", "status": "erledigt"})
    assert not [m for m in r.lauf(D(2026, 11, 2))["meldungen"] if m["art"] == "erinnerung"]
    # in der Planung zählen Fristen noch nicht (und der Wächter ruht ganz)
    p = reise(status="planung")
    p.aufgabe("Offen", frist="2026-11-01", zustaendig="Karl")
    assert not p.lauf(D(2026, 11, 2))["aktiv"] and rm.meldungen(p.o) == []


def test_erinnerung_verschwindet_wenn_die_aufgabe_erledigt_ist(reise):
    r = reise()
    a = r.aufgabe("Fähre buchen", frist="2026-11-10", zustaendig="Karl")
    r.lauf(D(2026, 11, 8))
    heute = D(2026, 11, 8)
    assert len(rm.meldungen_aktuell(r.o, "Karl", rm.aufgaben(r.o), "fest", BAUSTEINE, heute)) == 1
    rm.aufgabe_aendern(r.o, a["id"], {"name": "Karl", "status": "erledigt"})
    assert rm.meldungen_aktuell(r.o, "Karl", rm.aufgaben(r.o), "fest", BAUSTEINE, heute) == []
    assert len(rm.meldungen(r.o, "Karl")) == 1        # gelöscht wird nichts


def test_meldungen_verfallen_ausser_konflikten(reise):
    r = reise()
    alt = datetime.datetime(2026, 10, 1, tzinfo=datetime.timezone.utc)
    rm.meldung_anlegen(r.o, ["Karl"], "erinnerung", "T-01", "Alte Erinnerung", zeit=alt)
    rm.meldung_anlegen(r.o, ["Karl"], "konflikt", "V-01", "Alter Konflikt", zeit=alt)
    arten = [m["art"] for m in rm.meldungen_aktuell(r.o, "Karl", [], "fest", BAUSTEINE, D(2026, 11, 1))]
    assert arten == ["konflikt"]
    # ohne Baustein waechter sind auch frische Meldungen des Wächters weg, Konflikte nicht
    rm.meldung_anlegen(r.o, ["Karl"], "erinnerung", "T-01", "Frisch")
    heute = datetime.date.today()
    assert [m["art"] for m in rm.meldungen_aktuell(r.o, "Karl", [], "fest", ["varianten"], heute)] == ["konflikt"]


# ---------- Statuswechsel ----------

def test_statuswechsel_wird_den_bestimmern_gemeldet(reise):
    r = reise(status="fest")
    assert not [m for m in r.lauf(D(2027, 5, 12))["meldungen"] if m["art"] == "status"]
    (m,) = [x for x in r.lauf(D(2027, 5, 13))["meldungen"] if x["art"] == "status"]
    assert m["an"] == ["Ida"] and "begonnen" in m["text"] and "unterwegs" in m["text"] and "Bestimmer" in m["text"]
    assert not [x for x in r.lauf(D(2027, 5, 14))["meldungen"] if x["art"] == "status"]
    assert len([x for x in r.lauf(D(2027, 5, 20))["meldungen"] if x["art"] == "status"]) == 1   # danach (anderer Schlüssel)
    # nach dem Wechsel ist die Meldung nicht mehr aktuell
    jetzt = D(2027, 5, 14)
    assert rm.meldungen_aktuell(r.o, "Ida", [], "fest", BAUSTEINE, jetzt)
    assert [m for m in rm.meldungen_aktuell(r.o, "Ida", [], "unterwegs", BAUSTEINE, jetzt) if m["art"] == "status"] == []
    # unterwegs: erst nach dem Ende
    u = reise(status="unterwegs")
    assert not [x for x in u.lauf(D(2027, 5, 15))["meldungen"] if x["art"] == "status"]
    (d,) = [x for x in u.lauf(D(2027, 5, 17))["meldungen"] if x["art"] == "status"]
    assert "zu Ende" in d["text"] and "danach" in d["text"]


def test_wechselt_den_status_nie_selbst(reise):
    r = reise(status="fest")
    r.lauf(D(2027, 5, 20))
    assert kn.daten("beispielreise")["reise"]["status"]["wert"] == "fest"


# ---------- Regeln, Lauf und Kanäle ----------

def test_regeln_pruefen(tmp_path):
    def regeln(**kw):
        fehler = []
        rg.Reise({"regeln": kw}, {}, fehler, []).regeln()
        return fehler
    assert regeln() == [] and regeln(waechter_frist_tage=30, erinnerung_vorlauf_tage=0, meldekanal=["app"]) == []
    assert any("waechter_frist_tage" in f for f in regeln(waechter_frist_tage=0))
    assert any("erinnerung_vorlauf_tage" in f for f in regeln(erinnerung_vorlauf_tage=-1))
    assert any("meldekanal" in f for f in regeln(meldekanal="app"))
    assert any("E-Mail an alle ist noch nicht gebaut" in f for f in regeln(meldekanal=["app", "email"]))
    assert rg.VORGABEN["meldekanal"] == ["app", "nachricht"] and "waechter" not in rg.NOCH_NICHT_GEBAUT
    assert rg.verhalten("fest")["waechter"] and not rg.verhalten("planung")["waechter"]


def test_lauf_schreibt_sammelnachricht_nur_fuer_den_kanal_nachricht(reise, tmp_path, capsys):
    r = reise()
    r.aufgabe("Fähre buchen", frist="2026-11-10", zustaendig="Karl")
    datei = tmp_path / "bericht.txt"
    assert wa.main(["lauf", "beispielreise", "--heute", "2026-11-09", "--bericht", str(datei)]) == 0
    aus = capsys.readouterr().out
    assert "beispielreise: 1 neue Meldung(en)" in aus and "Prüfauftrag A-" in aus
    text = datei.read_text(encoding="utf-8")
    assert "Karl: Frist in 1 Tag(en)" in text and "veränderliche Angaben werden nachgeschlagen" in text
    # zweiter Lauf am selben Tag: nichts Neues, keine Nachricht
    datei.unlink()
    wa.main(["lauf", "--heute", "2026-11-09", "--bericht", str(datei)])
    assert "0 neue Meldung(en)" in capsys.readouterr().out and not datei.exists()
    # nur Kanal app: keine Sammelnachricht
    nur_app = reise(regeln={"meldekanal": ["app"]})
    nur_app.aufgabe("Fähre buchen", frist="2026-11-10", zustaendig="Karl")
    wa.main(["lauf", "--heute", "2026-11-09", "--bericht", str(datei)])
    assert not datei.exists()
    assert nur_app.o.joinpath("meldungen.jsonl").exists()   # in der App steht sie trotzdem


def test_zeige_aendert_nichts(reise, capsys):
    r = reise()
    r.aufgabe("Fähre buchen", frist="2026-11-10", zustaendig="Karl")
    assert wa.main(["zeige", "beispielreise", "--heute", "2026-11-09"]) == 0
    aus = capsys.readouterr().out
    assert "Wächter aktiv" in aus and "Zu prüfen (" in aus and "Meldung an Karl" in aus
    assert not r.o.joinpath("meldungen.jsonl").exists() and rm.auftraege(r.o) == []


def test_aufruf_ohne_argumente_zeigt_hilfe(capsys):
    assert wa.main([]) == 1 and "Wächter und Erinnerer" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        wa.main(["zeige", "beispielreise", "--heute", "morgen"])


# ---------- Konnektor: Meldungen in der Claude-App ----------

def test_konnektor_zeigt_meldungen_im_ueberblick(umgebung):
    u = umgebung("fest", bausteine=BAUSTEINE)
    a, _ = rm.aufgabe_anlegen(u.o, {"name": "Ida", "titel": "Fähre buchen", "frist": "2026-11-10", "zustaendig": "Karl"})
    wa.lauf_reise("beispielreise", datetime.date.today().replace(year=2026, month=11, day=9))
    # Meldungen tragen das Datum des simulierten Tages; für die Anzeige zählt das echte Heute: Meldung frisch anlegen
    rm.meldung_anlegen(u.o, ["Karl"], "erinnerung", a["id"], f"Frist morgen: {a['id']} Fähre buchen.", bezug=a["id"],
                       schluessel="test")
    text, f = u.werkzeug(KARL, "ueberblick")
    assert not f and "## Meldungen an dich" in text and "Frist morgen" in text
    assert "Meldungen an dich" not in u.werkzeug(IDA, "ueberblick")[0]      # Ida bekommt Karls Meldung nicht
    text, _ = u.werkzeug(KARL, "rueckmeldungen")
    assert "Meldungen an dich" in text and "Frist morgen" in text
    # erledigt -> verschwindet
    rm.aufgabe_aendern(u.o, a["id"], {"name": "Karl", "status": "erledigt"})
    assert "Frist morgen" not in u.werkzeug(KARL, "ueberblick")[0]


def test_konnektor_ohne_baustein_keine_waechter_meldungen_und_keine_anleitung(umgebung):
    ohne = umgebung("fest", bausteine=[b for b in BAUSTEINE if b != "waechter"])
    rm.meldung_anlegen(ohne.o, ["Karl"], "erinnerung", "AG-01", "Frist morgen", schluessel="x")
    assert "Meldungen an dich" not in ohne.werkzeug(KARL, "ueberblick")[0]
    assert "Wächter und Erinnerer" not in ohne.rpc(KARL, "initialize")["instructions"]
    mit = umgebung("fest", bausteine=BAUSTEINE)
    anleitung = mit.rpc(KARL, "initialize")["instructions"]
    assert "Wächter und Erinnerer sind an" in anleitung and "nie du" in anleitung


def test_json_der_meldungen_bleibt_lesbar(reise):
    r = reise()
    r.aufgabe("Fähre buchen", frist="2026-11-10", zustaendig="Karl")
    r.lauf(D(2026, 11, 9))
    m = json.loads(r.o.joinpath("meldungen.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert m["schluessel"].startswith("frist:AG-") and m["bezug"].startswith("AG-") and m["an"] == ["Karl"]
