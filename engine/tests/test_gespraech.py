"""Tests für Paket C: Gespräch für alle (entscheiden, frage_beantworten, person_einladen) gegen die Beispielreise.
Personen: Ida und Max Organisator:innen, Karl Mitwirkender, Kim gast (siehe test_regeln.reise_bauen)."""
import datetime
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import konnektor as kn  # noqa: E402
import reise as rg  # noqa: E402
import rueckmeldungen as rm  # noqa: E402
from test_regeln import IDA, KARL, KIM, MAX, anfrage, umgebung  # noqa: E402,F401  (umgebung: Fixture)
from schnittstelle_hilfe import N  # noqa: E402

BASIS = "https://beispiel.invalid/mcp"


@pytest.fixture(autouse=True)
def link_adresse(monkeypatch):
    monkeypatch.setenv("KN_BASIS", BASIS)


def token_aus(text):
    """Den Link aus der Antwort von person_einladen lesen -> Token."""
    link = next(z for z in text.splitlines() if z.startswith(BASIS + "/"))
    return link.rsplit("/", 1)[1]


def ruf(u, token, werkzeug, **args):
    """Wie u.werkzeug, aber mit dem Argument „name“ (u.werkzeug belegt den Parameter name selbst)."""
    r = u.rpc(token, "tools/call", {"name": werkzeug, "arguments": args})
    return r["content"][0]["text"], r["isError"]


# ---------- entscheiden ----------

def test_entscheiden_prueft_und_schreibt_direkt(umgebung):
    u = umgebung("planung")
    t, f = u.werkzeug(IDA, "entscheiden", option="V-01.b", status="gewaehlt",
                      grund="Karl möchte einmal mit der Kirnitzschtalbahn fahren")
    assert not f and "geschrieben: /beispielreise/entscheiden" in t and "es gilt ab jetzt" in t
    pfad, body = u.schreibweg[-1]
    assert pfad == "/beispielreise/entscheiden" and body["person"] == "ida" and body["name"] == "Ida" and body["rolle"] == "organisator"
    assert body["args"] == {"option": "V-01.b", "status": "gewaehlt", "grund": "Karl möchte einmal mit der Kirnitzschtalbahn fahren"}
    assert not (u.o / "auftraege.jsonl").exists()      # kein Auftrag mehr, direkt geschrieben
    # die formale Prüfung kommt vor dem Schreiben
    t, f = u.werkzeug(IDA, "entscheiden", option="V-99.a", status="gewaehlt", grund="x")
    assert f and "gibt es nicht" in t and len(u.schreibweg) == 1


def test_entscheiden_lehnt_unstimmiges_mit_begruendung_ab(umgebung):
    u = umgebung("planung")
    fall = [({"option": "V-99.a", "status": "gewaehlt", "grund": "x"}, "gibt es nicht"),
            ({"option": "V-01", "status": "gewaehlt", "grund": "x"}, "eine Wahlstelle"),
            ({"option": "V-01.b", "status": "gewaehlt", "grund": ""}, "Der Grund fehlt"),
            ({"option": "V-01.b", "status": "favorisiert", "grund": "x"}, "status muss einer von"),
            ({"option": "V-03.a", "status": "gewaehlt", "grund": "x"}, "schon gewählt"),
            ({"option": "V-03.b", "status": "verworfen", "grund": "x"}, "schon verworfen"),
            ({"option": "V-01.a", "status": "ersetzt", "grund": "x"}, "wodurch die Option ersetzt wird"),
            ({"option": "V-01.a", "status": "ersetzt", "ersetzt_durch": "V-03.a", "grund": "x"}, "derselben Wahlstelle"),
            ({"option": "V-03.a", "status": "ersetzt", "ersetzt_durch": "V-03.b", "grund": "x"}, "selbst verworfen"),
            ({"option": "V-01.a", "status": "verworfen", "ersetzt_durch": "V-01.b", "grund": "x"}, "nur beim Status ersetzt"),
            ({"option": "V-01.a", "status": "verworfen", "grund": "Zeile eins\nZeile zwei"}, "eine Zeile")]
    for args, soll in fall:
        t, f = u.werkzeug(IDA, "entscheiden", **args)
        assert f and soll in t, (args, t)
    assert u.schreibweg == []   # nichts davon wurde geschrieben
    t, f = u.werkzeug(IDA, "entscheiden", option="V-01.a", status="ersetzt", ersetzt_durch="V-01.b", grund="Bahnfahrt gewünscht")
    assert not f and u.schreibweg[-1][1]["args"]["ersetzt_durch"] == "V-01.b"


def test_entscheiden_hinweise_ersetzen_und_offene_wahlstelle(umgebung):
    u = umgebung("planung")
    # Ida hat V-03.a gewählt; V-03.b zu wählen ersetzt sie (gleiche Person: kein Widerspruch)
    t, f = u.werkzeug(IDA, "entscheiden", option="V-03.b", status="gewaehlt", grund="doch lieber abends im Haus essen")
    assert not f and "V-03.a ist bisher gewählt und wird dadurch ersetzt" in t and u.schreibweg[-1][0] == "/beispielreise/entscheiden"
    # Die gewählte Option verwerfen: Wahlstelle danach offen
    u2 = umgebung("planung")
    t, f = u2.werkzeug(IDA, "entscheiden", option="V-03.a", status="verworfen", grund="Pension ist ausgebucht")
    assert not f and "danach offen" in t
    # Unterwegs-Wahlstelle vor der Reise
    t, f = u2.werkzeug(IDA, "entscheiden", option="V-02.b", status="gewaehlt", grund="Wolfsschlucht klingt gut")
    assert not f and "für unterwegs" in t and "Auslöser" in t


def test_entscheiden_widerspruch_wird_offene_frage(umgebung):
    u = umgebung("planung")
    # Ida hat V-03.a im Plan gewählt; Max will V-03.b: Widerspruch -> nichts geschrieben, offene Frage und Meldung an beide
    t, f = u.werkzeug(MAX, "entscheiden", option="V-03.b", status="gewaehlt", grund="Abendessen im Haus")
    assert not f and "Nicht entschieden" in t and "offene Frage" in t and "Sag nie" in t
    assert [p for p, _ in u.schreibweg] == ["/beispielreise/frage_anlegen"]
    frage = u.schreibweg[-1][1]["args"]
    assert "Widerspruch" in frage["text"] and "Max will gewählt" in frage["text"] and frage["bezug"] == ["V-03"]
    meldung = rm.meldungen(u.o, "Ida")
    assert meldung and meldung[0]["art"] == "konflikt" and rm.meldungen(u.o, "Max")
    t, _ = u.werkzeug(IDA, "rueckmeldungen")
    assert "Meldungen an dich" in t
    # dieselbe Organisator:in ändert ihre Meinung selbst: kein Widerspruch
    t, f = u.werkzeug(IDA, "entscheiden", option="V-03.b", status="gewaehlt", grund="doch im Haus essen")
    assert not f and "Nicht entschieden" not in t and u.schreibweg[-1][0] == "/beispielreise/entscheiden"


def test_entscheiden_nur_organisator_mit_persoenlichem_link(umgebung):
    u = umgebung("planung")
    args = dict(option="V-01.b", status="gewaehlt", grund="Bahn")
    for token, soll in ((KARL, "nur Organisator:innen"), (KIM, "nur Organisator:innen")):
        t, f = u.werkzeug(token, "entscheiden", **args)
        assert f and soll in t, token
    assert u.schreibweg == []
    # Link nur mit Rolle (kein Name): keine Entscheidung, sie gehört genau einer Person
    kn.zugaenge_pfad().write_text(json.dumps({**kn.zugaenge(), "b" * 32: {"reise": "beispielreise", "rolle": "organisator"}}))
    t, f = u.werkzeug("b" * 32, "entscheiden", **args)
    assert f and "persönlichen Link" in t and u.schreibweg == []
    assert "entscheiden" in u.werkzeuge(IDA) and "entscheiden" not in u.werkzeuge(KARL) | u.werkzeuge(KIM)


@pytest.mark.parametrize("status,geht", [("idee", True), ("planung", True), ("fest", True), ("unterwegs", True),
                                          ("danach", False), ("archiv", False)])
def test_entscheiden_je_status(umgebung, status, geht):
    u = umgebung(status)
    t, f = u.werkzeug(IDA, "entscheiden", option="V-01.b", status="gewaehlt", grund="Bahn")
    assert (not f) == geht, t
    assert ("entscheiden" in u.werkzeuge(IDA)) == geht
    if not geht:
        assert "schreibgeschützt" in t or "archiviert" in t


def test_entscheiden_braucht_baustein_varianten(umgebung):
    u = umgebung(bausteine=["rueckmeldungen", "fragen"])
    t, f = u.werkzeug(IDA, "entscheiden", option="V-01.b", status="gewaehlt", grund="Bahn")
    assert f and "ausgeschaltet" in t and "entscheiden" not in u.werkzeuge(IDA)


# ---------- frage_beantworten ----------

def test_frage_beantworten_landet_an_der_frage(umgebung):
    u = umgebung("planung")
    t, f = u.werkzeug(KARL, "frage_beantworten", frage="F-01", antwort="Die Bahn fährt sonntags alle 30 Minuten",
                      quelle="https://beispiel.invalid/fahrplan")
    assert not f and "hängt an F-01" in t and "entscheidet Ida und Max" in t and "V-01" in t
    (e,) = rm.eintraege(u.o)
    assert (e["name"], e["art"], e["ziel"], e["status"]) == ("Karl", "Antwort", "F-01", "neu")
    assert e["quelle"] == "https://beispiel.invalid/fahrplan"
    # die Frage selbst bleibt offen, die Antwort steht dabei (Eingabe, keine Entscheidung)
    t, _ = u.werkzeug(IDA, "zeige", id="F-01")
    assert "Antworten (Eingaben, keine Entscheidung)" in t and "Karl: Die Bahn fährt" in t
    assert "F-01" in u.werkzeug(IDA, "offene_fragen")[0]
    # Organisator:innen dürfen auch antworten und werden auf die Entscheidung hingewiesen
    t, f = u.werkzeug(IDA, "frage_beantworten", frage="F-01", antwort="Ich habe angerufen")
    assert not f and "mit entscheiden entscheiden" in t


def test_frage_beantworten_prueft(umgebung):
    u = umgebung("planung")
    t, f = u.werkzeug(KARL, "frage_beantworten", frage="F-99", antwort="x")
    assert f and "gibt es nicht" in t
    t, f = u.werkzeug(KARL, "frage_beantworten", frage="F-02", antwort="x")   # geklärt
    assert f and "nicht mehr offen" in t
    t, f = u.werkzeug(KARL, "frage_beantworten", frage="F-01", antwort="  ")
    assert f and "Antwort fehlt" in t
    t, f = u.werkzeug(KARL, "frage_beantworten", frage="V-01", antwort="x")
    assert f and "gibt es nicht" in t
    t, f = u.werkzeug(KIM, "frage_beantworten", frage="F-01", antwort="x")
    assert f and "nur lesen" in t
    assert "frage_beantworten" not in u.werkzeuge(KIM) and "frage_beantworten" in u.werkzeuge(KARL)
    assert rm.eintraege(u.o) == []


def test_frage_beantworten_ohne_namen_fragt_nach(umgebung):
    u = umgebung("planung")
    kn.zugaenge_pfad().write_text(json.dumps({**kn.zugaenge(), "e" * 32: {"reise": "beispielreise", "rolle": "mitwirkend"}}))
    t, f = u.werkzeug("e" * 32, "frage_beantworten", frage="F-01", antwort="Bahn")
    assert f and "Name fehlt" in t
    t, f = ruf(u, "e" * 32, "frage_beantworten", frage="F-01", antwort="Bahn", name="Lena")
    assert not f and rm.eintraege(u.o)[0]["name"] == "Lena"


@pytest.mark.parametrize("status,geht", [("planung", True), ("fest", True), ("danach", True), ("archiv", False)])
def test_frage_beantworten_je_status(umgebung, status, geht):
    u = umgebung(status)
    t, f = u.werkzeug(KARL, "frage_beantworten", frage="F-01", antwort="Bahn")
    assert (not f) == geht, t
    assert ("frage_beantworten" in u.werkzeuge(KARL)) == geht


def test_frage_beantworten_braucht_bausteine(umgebung):
    for bausteine in (["rueckmeldungen"], ["fragen"]):   # ohne fragen bzw. ohne rueckmeldungen
        u = umgebung(bausteine=bausteine)
        t, f = u.werkzeug(KARL, "frage_beantworten", frage="F-01", antwort="Bahn")
        assert f and "ausgeschaltet" in t
        assert "frage_beantworten" not in u.werkzeuge(KARL)


# ---------- person_einladen ----------

def test_einladen_legt_person_an_und_stellt_zugang_aus(umgebung, capsys):
    u = umgebung("planung")
    t, f = u.werkzeug(IDA, "person_einladen", vorname="Jörg", rolle="mitwirkend", notiz="Karls Bruder")
    assert not f and "Jörg ist eingeladen" in t and "Rolle mitwirkend" in t
    token = token_aus(t)
    assert kn.zugang_zu(token)["person"] == "joerg"
    assert (kn.zugaenge_pfad().stat().st_mode & 0o777) == 0o600
    e = rm.einladungen_lesen(u.o)["joerg"]
    assert (e["name"], e["rolle"], e["reist"], e["eingeladen_von"], e["notiz"]) == ("Jörg", "mitwirkend", True, "Ida", "Karls Bruder")
    pfad, body = u.schreibweg[-1]      # die Person steht sofort in reise.yaml (person_schreiben über den Schreibweg)
    assert pfad == "/beispielreise/person_schreiben" and body["name"] == "Ida"
    assert body["args"] == {"schluessel": "joerg", "vorname": "Jörg", "rolle": "mitwirkend", "reist": True, "notiz": "Karls Bruder"}
    # Der Link funktioniert sofort: Name und Rolle stehen fest, ohne dass reise.yaml schon geändert ist
    t, f = ruf(u, token, "rueckmeldung_geben", ziel="T-03", art="Kommentar", text="Schön!", name="Jemand")
    assert not f and rm.eintraege(u.o)[0]["name"] == "Jörg"
    assert "Du sprichst mit Jörg (Mitwirkende:r)" in u.rpc(token, "initialize")["instructions"]
    assert "frage_beantworten" in u.werkzeuge(token) and "entscheiden" not in u.werkzeuge(token)
    assert "person_einladen" not in u.werkzeuge(token)   # Vorgabe: nur Organisator:innen laden ein
    # Auch der Rückmeldedienst kennt ihn jetzt als Mitwirkende:r
    assert rm.rolle_von(rm.zustand("beispielreise"), "Jörg") == "mitwirkend"
    # Die Kommandozeile findet die Person ebenfalls
    kn.zugang_anlegen("beispielreise", "joerg")
    assert "Jörg, mitwirkend" in capsys.readouterr().out


def test_einladen_gast_darf_nur_lesen(umgebung):
    u = umgebung("planung")
    t, f = u.werkzeug(IDA, "person_einladen", vorname="Mia", rolle="gast", reist=False)
    assert not f and "nur lesen" in t
    token = token_aus(t)
    assert rm.einladungen_lesen(u.o)["mia"]["reist"] is False
    assert not u.werkzeuge(token) & kn.SCHREIB_WERKZEUGE
    t, f = ruf(u, token, "rueckmeldung_geben", ziel="T-03", art="Kommentar", text="x", name="Mia")
    assert f and "nur lesen" in t
    # der Dienst lehnt die Person auch über die Webseite ab (Name bekannt, Rolle gast)
    code, a = anfrage(f"{u.rurl}/beispielreise/rueckmeldungen", {"name": "Mia", "art": "Kommentar", "ziel": "T-03", "text": "x"})
    assert code == 403 and "nur lesen" in a["fehler"]


def test_einladen_rolle_nie_hoeher_als_die_eigene(umgebung):
    u = umgebung("planung", regeln={"einladen": "mitwirkend"})
    assert "person_einladen" in u.werkzeuge(KARL) and "person_einladen" not in u.werkzeuge(KIM)
    t, f = u.werkzeug(KARL, "person_einladen", vorname="Nora", rolle="organisator")
    assert f and "höchstens eine Rolle" in t and rm.einladungen_lesen(u.o) == {}
    t, f = u.werkzeug(KARL, "person_einladen", vorname="Nora")   # Standard mitwirkend
    assert not f and rm.einladungen_lesen(u.o)["nora"]["rolle"] == "mitwirkend"
    assert "Karl" in rm.einladungen_lesen(u.o)["nora"]["eingeladen_von"]
    t, f = u.werkzeug(KIM, "person_einladen", vorname="Olga")
    assert f and "nur lesen" in t
    # Organisator:innen vergeben jede Rolle, auch organisator
    t, f = u.werkzeug(IDA, "person_einladen", vorname="Paul", rolle="organisator")
    assert not f
    t, _ = u.werkzeug(token_aus(t), "entscheiden", option="V-01.b", status="gewaehlt", grund="Bahn")
    assert "nur Organisator:innen" not in t and rm.rolle_von(rm.zustand("beispielreise"), "Paul") == "organisator"


def test_einladen_nur_organisator_ist_die_vorgabe(umgebung):
    u = umgebung("planung")
    t, f = u.werkzeug(KARL, "person_einladen", vorname="Nora")
    assert f and "nur Organisator:innen" in t and rm.einladungen_lesen(u.o) == {}


def test_einladen_pruefungen(umgebung, monkeypatch, tmp_path):
    u = umgebung("planung")
    for args, soll in (({"vorname": ""}, "vorname fehlt"), ({"vorname": "A\nB"}, "vorname fehlt"),
                       ({"vorname": "Nora", "rolle": "chef"}, "Rolle muss"),
                       ({"vorname": "Nora", "notiz": "x" * 301}, "Notiz"),
                       ({"vorname": "???"}, "Schlüssel")):
        t, f = u.werkzeug(IDA, "person_einladen", **args)
        assert f and soll in t, (args, t)
    assert rm.einladungen_lesen(u.o) == {} and u.schreibweg == []
    # Link ohne Namen kann nicht einladen
    kn.zugaenge_pfad().write_text(json.dumps({**kn.zugaenge(), "b" * 32: {"reise": "beispielreise", "rolle": "organisator"}}))
    t, f = u.werkzeug("b" * 32, "person_einladen", vorname="Nora")
    assert f and "persönlichen Link" in t
    # ohne eingerichtete Link-Adresse
    monkeypatch.delenv("KN_BASIS")
    t, f = u.werkzeug(IDA, "person_einladen", vorname="Nora")
    assert f and "KN_BASIS" in t and rm.einladungen_lesen(u.o) == {}


def test_einladen_vorhandene_person_bekommt_nur_einen_neuen_link(umgebung):
    u = umgebung("planung")
    vorher = set(kn.zugaenge())
    t, f = u.werkzeug(IDA, "person_einladen", vorname="karl")   # Schreibweise egal
    assert not f and "Neuer Link für Karl" in t and "Rolle mitwirkend" in t
    neu = set(kn.zugaenge()) - vorher
    assert len(neu) == 1 and kn.zugaenge()[neu.pop()]["person"] == "karl"
    assert rm.einladungen_lesen(u.o) == {} and u.schreibweg == []   # keine zweite Person, nichts geschrieben
    # Rolle ändern: Organisator:in, direkt nach reise.yaml
    t, f = u.werkzeug(IDA, "person_einladen", vorname="Karl", rolle="organisator")
    assert not f and "hat jetzt die Rolle organisator" in t and u.schreibweg[-1][1]["args"] == {"schluessel": "karl", "rolle": "organisator"}
    # ein:e Mitwirkende:r (bei einladen: mitwirkend) kann keinen Link für ein:e Organisator:in ausstellen
    u2 = umgebung("planung", regeln={"einladen": "mitwirkend"})
    t, f = u2.werkzeug(KARL, "person_einladen", vorname="Ida")
    assert f and "mindestens dieser Rolle" in t


def test_einladen_doppelter_name_nach_einladung(umgebung):
    u = umgebung("planung")
    assert not u.werkzeug(IDA, "person_einladen", vorname="Nora")[1]
    t, f = u.werkzeug(IDA, "person_einladen", vorname="NORA", rolle="organisator")   # Schreibweise egal: Rolle ändern, keine zweite Person
    assert not f and "hat jetzt die Rolle organisator" in t and len(rm.einladungen_lesen(u.o)) == 1
    t, f = u.werkzeug(IDA, "person_einladen", vorname="Nora")   # weiterer Link für dieselbe Person
    assert not f and "Neuer Link für Nora" in t and len(rm.einladungen_lesen(u.o)) == 1


def test_einladen_zugaenge_nicht_beschreibbar(umgebung, monkeypatch):
    u = umgebung("planung")
    def nicht_schreibbar(z):
        raise PermissionError("Dateisystem ist schreibgeschützt")
    monkeypatch.setattr(kn, "zugang_ausstellen", nicht_schreibbar)
    t, f = u.werkzeug(IDA, "person_einladen", vorname="Nora")
    assert f and "nicht schreiben" in t and rm.einladungen_lesen(u.o) == {} and u.schreibweg == []


def test_einladung_gilt_nicht_mehr_doppelt_sobald_reise_yaml_die_person_kennt():
    d = [{"schluessel": "karl", "name": "Karl", "rolle": "mitwirkend"}]
    # kaputte oder fehlende Datei ist kein Fehler
    assert rm.personen_mit_einladungen(d, None) == d
    assert rm.einladungen_lesen(Path("/gibt/es/nicht")) == {}


def test_einladung_wird_von_reise_yaml_abgeloest(umgebung):
    u = umgebung("planung")
    assert not u.werkzeug(IDA, "person_einladen", vorname="Karl")[1]
    # Eine Einladung, die reise.yaml schon enthält (hier: von Hand in die Datei geschrieben), überschreibt die Rolle nicht
    u.o.joinpath("einladungen.json").write_text(json.dumps({"karl": {"name": "Karl", "rolle": "organisator"}}))
    assert rm.rolle_von(rm.zustand("beispielreise"), "Karl") == "mitwirkend"


# ---------- Anleitung und Regeln ----------

def test_anleitung_nennt_rolle_status_und_grenzen(umgebung):
    u = umgebung("fest")
    ida = u.rpc(IDA, "initialize")["instructions"]
    assert "Du sprichst mit Ida (Organisator:in)" in ida and "Status fest" in ida
    assert N("mit entscheiden ein (Option") in ida and "in den Plan" in ida and N("person_einladen") in ida
    karl = u.rpc(KARL, "initialize")["instructions"]
    assert "Du sprichst mit Karl (Mitwirkende:r)" in karl and "Entscheiden kann sie nicht" in karl
    assert N("frage_beantworten") in karl and N("person_einladen") not in karl
    assert "nur lesen" in u.rpc(KIM, "initialize")["instructions"]
    offen = umgebung("planung", regeln={"einladen": "mitwirkend"})
    assert "in den Plan" in offen.rpc(IDA, "initialize")["instructions"]
    assert "darf Personen einladen" in offen.rpc(KARL, "initialize")["instructions"]


def test_regeln_einladen_und_schluessel():
    assert rg.mindestrolle("einladen") == "organisator"
    assert rg.mindestrolle("einladen", {"einladen": "mitwirkend"}) == "mitwirkend"
    assert rg.mindestrolle("entscheiden") == "organisator" and rg.mindestrolle("antwort") == "mitwirkend"
    assert rg.erlaubt("einladen", "mitwirkend", "planung", None)[0] is False
    assert rg.erlaubt("einladen", "mitwirkend", "planung", None, regeln={"einladen": "mitwirkend"})[0] is True
    assert rg.erlaubt("einladen", "gast", "planung", None, regeln={"einladen": "mitwirkend"})[0] is False
    assert rg.erlaubt("einladen", "organisator", "danach", None)[0] is True and rg.erlaubt("einladen", "organisator", "archiv", None)[0] is False
    assert rg.erlaubt("entscheiden", "organisator", "planung", ["rueckmeldungen"])[0] is False   # Baustein varianten fehlt
    assert [rg.schluessel_aus_name(n) for n in ("Jörg", "Zoë", "Anna Lena", "  Max ", "???")] == \
        ["joerg", "zoe", "anna-lena", "max", ""]


def test_entscheiden_hinweise_zu_regeln(tmp_path):
    """Paket 4 (#18): Regeln zwischen Optionen verhindern nichts, aber die Entscheidung sagt, was nicht mehr passt."""
    from test_regeln import reise_bauen
    d = json.loads((reise_bauen(tmp_path) / "beispielreise" / "daten.json").read_text(encoding="utf-8"))
    h = kn.Handbuch(d)
    _, c = h.option("V-01.c")
    # Die Beispielreise: V-01.c setzt V-03.a voraus (im Plan) und schließt V-02.b aus (nicht im Plan)
    assert [(x["id"], x["im_plan"]) for x in c["erfordert"]] == [("V-03.a", True)]
    text = h.option_text(c)
    assert "Setzt voraus: V-03.a „Pension Burgblick“ (im Plan)" in text
    assert "Schließt aus: V-02.b „Durch die Wolfsschlucht“ (nicht im Plan)" in text
    _, hinweise, fehler = h.entscheidung_pruefen({"option": "V-01.c", "status": "gewaehlt", "grund": "Test"}, "Ida")
    assert not fehler and not [x for x in hinweise if "voraus" in x or "schließen" in x]
    # Stünde V-03.a nicht im Plan und V-02.b schon, sagt die Entscheidung beides
    c["erfordert"][0]["im_plan"] = False
    c["schliesst_aus"][0]["im_plan"] = True
    _, hinweise, _ = h.entscheidung_pruefen({"option": "V-01.c", "status": "gewaehlt", "grund": "Test"}, "Ida")
    assert "V-01.c setzt V-03.a „Pension Burgblick“ voraus; das steht derzeit nicht im Plan." in hinweise
    assert "V-01.c und V-02.b „Durch die Wolfsschlucht“ schließen sich aus; V-02.b steht derzeit im Plan." in hinweise
    # Verwerfen, was eine Option im Plan voraussetzt
    c["im_plan"] = True
    _, hinweise, _ = h.entscheidung_pruefen({"option": "V-03.a", "status": "verworfen", "grund": "ausgebucht"}, "Ida")
    assert "V-01.c „Mit dem Bus zurück (erfundenes Beispiel)“ steht im Plan und setzt V-03.a voraus." in hinweise


def test_entscheiden_meldet_alte_quellen(tmp_path):
    """Quellen prüfen (#9): Ist eine veränderliche Angabe der gewählten Option älter als die Frist des Wächters,
    sagt die Vorprüfung es mit Datum und Quelle; verhindert wird nichts."""
    from test_regeln import reise_bauen
    d = json.loads((reise_bauen(tmp_path) / "beispielreise" / "daten.json").read_text(encoding="utf-8"))
    h = kn.Handbuch(d)
    w = next(w for w in h.r["wahlstellen"] if any(k["id"] == "preis" and k.get("veraenderlich") for k in w["kriterien"]))
    o = next(x for x in w["optionen"] if x["status"] != "gewaehlt")
    o["merkmale"]["preis"] = {"wert": "99 €", "geprueft": "2026-01-10", "quelle": "Beispielseite"}
    args = {"option": o["id"], "status": "gewaehlt", "grund": "Test"}
    _, hinweise, fehler = h.entscheidung_pruefen(args, "Ida", heute=datetime.date(2026, 10, 27))
    assert not fehler
    assert any(x.startswith("Älter als 60 Tage: ") and "geprüft 10.1.2026" in x and "Beispielseite" in x for x in hinweise), hinweise
    # Innerhalb der Frist kein Hinweis
    o["merkmale"]["preis"]["geprueft"] = "2026-10-01"
    _, hinweise, _ = h.entscheidung_pruefen(args, "Ida", heute=datetime.date(2026, 10, 27))
    assert not any(x.startswith("Älter als") for x in hinweise)


# ---------- dasselbe Gespräch auf Englisch (ADR-0006, M12) ----------

def test_gespraech_auf_englisch_mit_englischen_namen(umgebung, tmp_path):
    """Konto `en`, englische Werkzeug- und Parameternamen: dieselben Antworten und Ablehnungen wie auf Deutsch, aber englisch; was
    zum Schreibweg geht, trägt die internen (deutschen) Namen, und die Datenwerte bleiben deutsch."""
    u = umgebung("planung")
    zug = Path(kn.zugaenge_pfad())
    daten = json.loads(zug.read_text(encoding="utf-8"))
    for token in daten:
        daten[token]["sprache"] = "en"
    zug.write_text(json.dumps(daten), encoding="utf-8")
    # Anleitung und Werkzeugliste
    anleitung = u.rpc(IDA, "initialize")["instructions"]
    assert "You are speaking with Ida" in anleitung and "Reply in the person's language" in anleitung and "Du sprichst" not in anleitung
    namen = {w["name_aussen"] for w in u.rpc(IDA, "tools/list")["tools"]}
    assert {"decide", "question_answer", "person_invite", "overview"} <= namen and "entscheiden" not in namen
    # entscheiden: englische Parameter, interne Werte
    t, f = u.werkzeug(IDA, "decide", option="V-01.b", status="gewaehlt", reason="Karl wants to take the Kirnitzschtal tram")
    assert not f and "geschrieben: /beispielreise/entscheiden" in t
    pfad, body = u.schreibweg[-1]
    assert body["args"] == {"option": "V-01.b", "status": "gewaehlt", "grund": "Karl wants to take the Kirnitzschtal tram"}
    # Ablehnung vor dem Schreiben: englisch
    t, f = u.werkzeug(IDA, "decide", option="V-99.a", status="gewaehlt", reason="x")
    assert f and t.startswith("Not decided:") and "“V-99.a” does not exist" in t and "with variants" in t and len(u.schreibweg) == 1
    t, f = u.werkzeug(IDA, "decide", option="V-01.b", status="gewaehlt", reason="")
    assert f and "The reason is missing" in t
    # Rechte: Karl darf nicht entscheiden, die Ablehnung ist englisch
    t, f = u.werkzeug(KARL, "decide", option="V-01.b", status="gewaehlt", reason="x")
    assert f and t == "Only organisers may do this."
    # Frage beantworten: der Eintrag der Reise bleibt, wie er ist, die Antwort an die Person ist englisch
    t, f = u.werkzeug(KARL, "question_answer", question="F-01", answer="The tram runs every 30 minutes on Sundays")
    assert not f and t.startswith("Answer ") and "attached to F-01" in t and "hängt an" not in t
    (e,) = rm.eintraege(u.o)
    assert (e["name"], e["art"], e["ziel"], e["status"]) == ("Karl", "Antwort", "F-01", "neu")
    # lesen: Überblick und Abschnitt englisch
    t, f = u.werkzeug(IDA, "overview")
    assert not f and "## Day plan" in t and "## Tagesplan" not in t
