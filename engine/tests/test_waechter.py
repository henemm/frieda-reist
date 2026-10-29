"""Tests für Paket E: Wächter und Erinnerer gegen die Beispielreise, mit simuliertem Datum.
Personen: Ida Organisatorin, Karl Mitwirkender. Reisetage der Beispielreise: 13.–16.5.2027."""
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
            text = r.read_text(encoding="utf-8")
            alt = '- {wert: "120 €", quelle: "erfunden (Beispiel)", notiz: "Beispielwert, erfunden"}'    # Hauptwert; der Eintrag für den 15.5. bleibt ungeprüft
            assert alt in text
            r.write_text(text.replace(
                alt, f'- {{wert: "120 €", quelle: "https://beispiel.invalid/u1", geprueft: {geprueft}, notiz: "Beispielwert, erfunden"}}'),
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
    probe = trocken.lauf(D(2026, 11, 1), trocken=True)
    assert [m for m in probe["meldungen"] if m["art"] == "pruefung"]    # würde angelegt, wird aber nicht geschrieben
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
    assert ("U-01", "fruehstueck") in gefunden
    assert {t["wert"] for t in items if (t["bezug"], t["merkmal"]) == ("U-01", "preis")} == {"140 €"}   # der Hauptwert ist frisch
    assert all(t["geprueft"] is None and t["grund"] == "noch nie geprüft" for t in items)
    # nicht veränderlich (Abendessen, Lage) und nicht im Plan (verworfene Option V-03.b) stehen nicht dabei
    assert not any(t["merkmal"] in ("abendessen", "lage", "zimmer") for t in items)
    assert not any(t["bezug"] == "V-03.b" for t in items)
    # Werte je Datum haben ein eigenes Prüfdatum: der Preis für den 15.5. ist nie geprüft und steht dabei
    je_datum = next(t for t in items if (t["bezug"], t["merkmal"]) == ("U-01", "preis"))
    assert je_datum["wert"] == "140 €" and "am 15.5.2027" in je_datum["name"] and je_datum["geprueft"] is None
    # 87 Tage später ist sie zu alt; die nie geprüften stehen trotzdem vorn
    spaeter = wa.zu_pruefen(d, D(2027, 1, 15), 60)
    alt = next(t for t in spaeter if (t["bezug"], t["merkmal"], t["wert"]) == ("U-01", "preis", "120 €"))
    assert alt["alter_tage"] == 87 and "vor 87 Tagen" in alt["grund"] and alt["quelle"] == "https://beispiel.invalid/u1"
    assert alt in spaeter and all(t["alter_tage"] is None or t["alter_tage"] <= 87 for t in spaeter[spaeter.index(alt):])   # die ältesten zuerst
    # eine längere Frist lässt sie wieder zu
    assert "120 €" not in {t["wert"] for t in wa.zu_pruefen(d, D(2027, 1, 15), 90) if t["merkmal"] == "preis"}


def test_pruefmeldungen_je_angabe_an_organisatorinnen_und_wiederholung_nach_frist(reise):
    """ADR-0001, Paket O-4: Der Wächter legt keinen Prüfauftrag für eine KI an, sondern je Angabe eine Meldung an die
    Organisator:innen; der AI-Client schlägt im Gespräch nach. Dieselbe Angabe frühestens nach der Frist noch einmal."""
    r = reise(geprueft="2026-10-20")
    heute = D(2027, 1, 15)
    erg = r.lauf(heute)
    pr = [m for m in erg["meldungen"] if m["art"] == "pruefung"]
    assert 0 < len(pr) <= wa.MAX_PRUEFUNGEN and all(m["an"] == ["Ida"] for m in pr)
    u01 = next(m for m in pr if m["bezug"] == "U-01")
    assert "nachschlagen" in u01["text"] and "nichts wird still übernommen" in u01["text"] and u01["ziel"] == "U-01"
    assert rm.auftraege(r.o) == []                      # kein Auftrag, keine KI
    assert len({m["schluessel"] for m in pr}) == len(pr)
    gespeichert = [m for m in rm.meldungen(r.o) if m["art"] == "pruefung"]
    assert len(gespeichert) == len(pr) and "U-01" in {m["bezug"] for m in gespeichert}
    # am selben Tag und innerhalb der Frist nichts Neues, nach der Frist wieder
    assert not [m for m in r.lauf(heute)["meldungen"] if m["art"] == "pruefung"]
    assert not [m for m in r.lauf(heute + datetime.timedelta(days=30))["meldungen"] if m["art"] == "pruefung"]
    assert [m for m in r.lauf(heute + datetime.timedelta(days=61))["meldungen"] if m["art"] == "pruefung"]
    # kein Material für Widersprüche: nur die Entscheidungen im Plan stehen, kein Auftrag
    assert not [e for e in kn.stehende_entscheidungen("beispielreise", kn.daten("beispielreise")) if e.get("auftrag")]


def test_pruefmeldungen_begrenzt_die_menge_und_im_bericht(reise, monkeypatch):
    r = reise()
    monkeypatch.setattr(wa, "MAX_PRUEFUNGEN", 2)
    erg = r.lauf(D(2026, 11, 1))
    assert len([m for m in erg["meldungen"] if m["art"] == "pruefung"]) == 2
    assert len(erg["zu_pruefen"]) > 2 and "weitere veränderliche Angaben" in erg["bericht"]


def test_frist_ist_einstellbar(reise):
    r = reise(geprueft="2026-10-20", regeln={"waechter_frist_tage": 10})
    erg = r.lauf(D(2026, 11, 1), trocken=True)
    assert "120 €" in {t["wert"] for t in erg["zu_pruefen"] if (t["bezug"], t["merkmal"]) == ("U-01", "preis")}


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
    assert len(rm.meldungen(r.o, "Karl")) == 3 and [m for m in rm.meldungen(r.o, "Ida") if m["art"] != "pruefung"] == []


def test_erinnerer_ab_termin_und_wer_zustaendig_ist(reise):
    r = reise()
    r.aufgabe("Hütte buchen", ab="2026-11-05", zustaendig="Karl")
    r.aufgabe("Zug buchen", ab="2026-11-05")                 # niemand zuständig -> Organisator:innen
    r.aufgabe("Fahrrad leihen", ab="2026-11-05", zustaendig="Unbekannt")   # keine Person der Reise -> Organisator:innen
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

def test_statuswechsel_wird_den_organisatoren_gemeldet(reise):
    r = reise(status="fest")
    assert not [m for m in r.lauf(D(2027, 5, 12))["meldungen"] if m["art"] == "status"]
    (m,) = [x for x in r.lauf(D(2027, 5, 13))["meldungen"] if x["art"] == "status"]
    assert m["an"] == ["Ida"] and "begonnen" in m["text"] and "unterwegs" in m["text"] and "Organisator:in" in m["text"]
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
    assert "beispielreise: 12 neue Meldung(en), 11 Angabe(n) zu prüfen" in aus and "Prüfauftrag" not in aus   # seit 29.10.2026 auch die Adresse von U-01
    text = datei.read_text(encoding="utf-8")
    assert "Karl: Frist in 1 Tag(en)" in text and "Ida: U-01 " in text and "nachschlagen" in text
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
    assert "Frist morgen" not in u.werkzeug(IDA, "ueberblick")[0]      # Ida bekommt Karls Meldung nicht
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


def test_zu_pruefen_laesst_ausgeschaltete_merkmale_aus():
    """ADR-0001, Paket O-0: Merkmale mit Stufe aus (je Reise, auch je Art) prüft der Wächter nicht."""
    preis = {"id": "preis", "name": "Preis", "veraenderlich": True, "stufe": {"*": "aus", "refugi": "empfohlen"}}
    d = {"route": {"wahlstellen": [], "merkmale": {"hotel": [preis], "refugi": [preis]},   # Merkmale je Art
                   "unterkuenfte": {"U-1": {"art": "hotel", "naechte": ["T-01"], "merkmale": {"preis": {"wert": "1 €"}}},
                                    "U-2": {"art": "refugi", "naechte": ["T-02"], "merkmale": {"preis": {"wert": "2 €"}}}}}}
    assert [t["bezug"] for t in wa.zu_pruefen(d, D(2026, 11, 1), 60)] == ["U-2"]
    preis["stufe"] = "aus"
    assert wa.zu_pruefen(d, D(2026, 11, 1), 60) == []


def test_erinnerer_meldet_fristen_von_buchungen(reise):
    """#76: Frist und Stornofrist einer Buchung (B-…) wie Aufgabenfristen, an die Person, die gebucht hat. Beispielreise:
    B-01 (Ida) kostenlos stornierbar bis 11.5.2027, B-02 (Karl) Frist 13.5.2027 „Ticket in die App laden“."""
    r = reise()
    ms = [m for m in r.lauf(D(2027, 5, 10))["meldungen"] if m["art"] == "erinnerung"]
    assert sorted((m["an"][0], m["bezug"]) for m in ms) == [("Ida", "B-01"), ("Karl", "B-02")]
    assert any("Kostenlos stornieren geht nur noch bis 11.5.2027: Buchung B-01 Hotel am Elbufer (kostenlos bis 3 Tage vorher" in m["text"] for m in ms)
    assert any("Frist in 3 Tag(en): Ticket in die App laden zur Buchung B-02" in m["text"] for m in ms)
    assert not [m for m in r.lauf(D(2027, 5, 11))["meldungen"] if m["art"] == "erinnerung"]   # nicht doppelt
    ueber = [m for m in r.lauf(D(2027, 5, 15))["meldungen"] if m["art"] == "erinnerung"]
    assert len(ueber) == 1 and "Überfällig seit 2 Tag(en): Ticket in die App laden zur Buchung B-02" in ueber[0]["text"] and ueber[0]["an"] == ["Karl"]


def test_zu_pruefen_auch_strecken_aufenthalte_und_lage():
    """Abgleich 29.10.2026: Der Wächter prüft alle Aussagen mit Prüfdatum, auch an Strecken im Plan, an Aufenthalten ohne Nacht
    und die Lage (Adresse, Punkt; ADR-0004), nicht nur Unterkünfte und Optionen."""
    verkehrt = {"id": "verkehrt", "name": "Fährt", "veraenderlich": True}
    eintritt = {"id": "eintritt", "name": "Eintritt", "typ": "geld", "veraenderlich": True}
    d = {"route": {"wahlstellen": [], "merkmale": {"bahn": [verkehrt], "besichtigung": [eintritt], "hotel": []},
                   "unterkuenfte": {"U-1": {"art": "hotel", "naechte": ["T-01"], "merkmale": {},
                                            "adresse": {"wert": "Straße 1", "quelle": "x"}, "punkt": {"wert": [1, 2], "quelle": "x", "geprueft": "2026-10-20"}}},
                   "aufenthalte": {"A-1": {"art": "besichtigung", "tage": ["T-02"], "merkmale": {"eintritt": {"wert": "6 €"}}},
                                   "A-2": {"art": "besichtigung", "tage": [], "merkmale": {"eintritt": {"wert": "9 €"}}}},
                   "strecken": {"E-1": {"titel": "Bahn", "art": "bahn", "art_schluessel": "bahn", "merkmale": {"verkehrt": {"wert": "stündlich"}}},
                                "E-2": {"titel": "Bahn alt", "art": "bahn", "art_schluessel": "bahn", "merkmale": {"verkehrt": {"wert": "x"}}}},
                   "aktiv_strecken": ["E-1"]}}
    t = wa.zu_pruefen(d, D(2026, 11, 1), 60)
    assert sorted((x["bezug"], x["merkmal"]) for x in t) == [("A-1", "eintritt"), ("E-1", "verkehrt"), ("U-1", "adresse")]
    assert next(x for x in t if x["bezug"] == "U-1")["name"] == "Adresse" and next(x for x in t if x["bezug"] == "E-1")["grund"] == "noch nie geprüft"
    # Punkt mit frischem Prüfdatum und Dinge außerhalb des Plans (A-2, E-2) bleiben still
    assert wa.zu_pruefen(d, D(2026, 12, 25), 60)[-1]["merkmal"] == "punkt"
