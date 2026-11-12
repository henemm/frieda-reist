"""Tests für #530 (Meilenstein M5a): Rückmeldung an den Betreiber aus der Claude-App. Spec:
docs/specs/betrieb/betreiber-meldung-530.md (AC-1 bis AC-19; AC-20 ist die Abnahme auf der Instanz).

Nur erfundene Daten: beispielreise (Ida, Karl), stadtwochenende (Tom, Lea), Betreiber-Konten mit Adressen unter
beispiel.invalid, alles unter tmp_path. Texte werden über ihren Schlüssel geprüft (meldet/text aus conftest.py).

Schnittstelle, die diese Tests festlegen (aus der Spec):
  konten.BETREIBER_MELDUNG_ARTEN = ("Fehler", "Wunsch", "Frage")
  konten.BETREIBER_MELDUNG_MAX = 2000
  konten.JE_KONTO_MELDUNGEN = (10, 24 * 3600)            gezählt in versand unter betreiber_meldung:<konto>
  konten.an_betreiber_melden(k, art, text, reise=None, zusammenhang=None) -> Nummer | KontoFehler
  konten.betreiber_meldungen(alle=False)                 älteste zuerst, mit name und email des Kontos
  konten.betreiber_meldung_erledigt(nr, issue) -> bool
  konten.eigene_betreiber_meldungen(kid)                 für den Export, ohne issue
  konten.mail_senden(an, betreff, text, antwort_an=None)  Reply-To
  konten.main(["meldungen"[, "--alle"]]), konten.main(["meldung-erledigt", nr, issue])
  Konnektor: Konto-Werkzeug an_frieda_melden (report_to_frieda), Parameter text, art, reise, zusammenhang (context)
  anmeldung: DATENSCHUTZ_ABSCHNITTE mit "betreiber_meldungen", alpha_inhalt nennt den Meldeweg, export_person
             mit betreiber_meldungen
"""
import io
import json
import re
import sqlite3
import sys
import zipfile
from contextlib import closing
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
WURZEL = ENGINE.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import anmeldung  # noqa: E402
import konnektor as kn  # noqa: E402
import konten  # noqa: E402
import schnittstelle  # noqa: E402
import texte  # noqa: E402
from conftest import meldet, text  # noqa: E402
from test_anmeldung import welt  # noqa: E402,F401  (Fixture, von zwei gebraucht)
from test_trennung import zwei, IDA, KARL, TOM  # noqa: E402,F401  (zwei: Fixture)

LEA = "lea@beispiel.invalid"
OHNE = "ohne-reise@beispiel.invalid"
BETR_DE, BETR_EN, BETR_GESPERRT = "betrieb-de@beispiel.invalid", "betrieb-en@beispiel.invalid", "betrieb-alt@beispiel.invalid"
WERKZEUG = "an_frieda_melden"
FEHLER_TEXT = "Beispielwert: Die Karte lädt nicht."
ZUSAMMENHANG = "Beispielwert: nach zeige T-02 kam ein Fehler."
NEUE_SCHLUESSEL = (
    "wert.Fehler", "konto.betreiber_meldung.leer", "konto.betreiber_meldung.zu_lang", "konto.betreiber_meldung.art",
    "konto.betreiber_meldung.grenze", "konto.betreiber_meldung.issue_fehlt", "konto.betreiber_meldung.mail_betreff",
    "konto.betreiber_meldung.mail_text", "konnektor.an_frieda_melden.angekommen", "konnektor.meine_reisen.betreiber_meldungen",
    "konnektor.meine_reisen.betreiber_meldung", "konnektor.werkzeug.an_frieda_melden", "konnektor.werkzeug.an_frieda_melden.text",
    "konnektor.werkzeug.an_frieda_melden.art", "konnektor.werkzeug.an_frieda_melden.zusammenhang",
    "konnektor.werkzeug.an_frieda_melden.reise", "konnektor.anleitung.frieda.melden",
    "recht.datenschutz.betreiber_meldungen.titel", "recht.datenschutz.betreiber_meldungen.text", "recht.alpha.melden",
    "recht.alpha.melden_impressum")
# Wortlaut von recht.datenschutz.folgt vor #530: bleibt byteweise gleich
FOLGT = {s: texte.t(s, "recht.datenschutz.folgt") for s in ("de", "en")}


# ---------- Hilfen ----------

def konto_neu(kid, email, name, sprache="de", rechte="", gesperrt=0):
    with closing(konten.db()) as v, v:
        v.execute("INSERT INTO konten (id, email, name, rechte, gesperrt, angelegt, sprache) VALUES (?,?,?,?,?,?,?)",
                  (kid, email, name, rechte, gesperrt, "2026-11-12", sprache))
    return konten.konto(kid)


def betreiber_anlegen():
    """Zwei Betreiber (de, en) und ein gesperrter Betreiber, der keine Mail bekommen darf."""
    konto_neu("k-betr-de", BETR_DE, "Betrieb Deutsch", "de", "betreiber")
    konto_neu("k-betr-en", BETR_EN, "Betrieb English", "en", "betreiber")
    konto_neu("k-betr-alt", BETR_GESPERRT, "Betrieb Alt", "de", "betreiber", gesperrt=1)
    return konten.konto("k-betr-de"), konten.konto("k-betr-en")


@pytest.fixture
def db_welt(tmp_path, monkeypatch):
    """Nur die Kontendatenbank und die Mail-Datei, ohne veröffentlichte Reise."""
    mails = tmp_path / "mails.jsonl"
    monkeypatch.setenv("FR_MAIL_DATEI", str(mails))
    ida = konto_neu("k-ida", IDA, "Ida")
    karl = konto_neu("k-karl", KARL, "Karl")
    return {"ida": ida, "karl": karl, "mails": mails}


def mails(datei, betreff_schluessel="konto.betreiber_meldung.mail_betreff"):
    """Mails an Betreiber aus FR_MAIL_DATEI (andere Mails der Umgebung, etwa Anmeldecodes, bleiben außen vor)."""
    if not Path(datei).exists():
        return []
    alle = [json.loads(z) for z in Path(datei).read_text(encoding="utf-8").splitlines() if z.strip()]
    return [m for m in alle if any(meldet(m["betreff"], betreff_schluessel, s) for s in ("de", "en"))]


def zeilen(konto=None):
    with closing(konten.db()) as v:
        sql = "SELECT * FROM betreiber_meldungen" + (" WHERE konto = ?" if konto else "") + " ORDER BY id"
        return [dict(z) for z in v.execute(sql, (konto,) if konto else ())]


def versand(schluessel):
    with closing(konten.db()) as v:
        return v.execute("SELECT COUNT(*) FROM versand WHERE schluessel = ?", (schluessel,)).fetchone()[0]


def werkzeug_von(k):
    ws = [w for w in kn.frieda_werkzeuge(k) if w["name"] == WERKZEUG]
    assert len(ws) == 1, [w["name"] for w in kn.frieda_werkzeuge(k)]
    return ws[0]


def melden(k, **args):
    return kn.frieda_werkzeug(k, WERKZEUG, args)


def nummer(antwort):
    m = re.findall(r"\d+", antwort)
    assert m, antwort
    return int(m[-1])


def seite_in(sprache, monkeypatch):
    monkeypatch.setattr(anmeldung._anfrage, "sprache", sprache, raising=False)


# ---------- AC-1: Werkzeug für jedes Konto ----------

@pytest.mark.parametrize("fall", ["beispielreise", "stadtwochenende", "beide", "ohne"])
def test_werkzeug_in_liste_fuer_jedes_konto(zwei, fall):
    u = zwei()
    if fall == "beispielreise":
        k, erwartet = u.a, {"beispielreise"}
    elif fall == "stadtwochenende":
        k, erwartet = u.b, {"stadtwochenende"}
    elif fall == "beide":
        konten.verknuepfen(u.a["id"], "stadtwochenende", "lea")
        k, erwartet = konten.konto(u.a["id"]), {"beispielreise", "stadtwochenende"}
    else:
        k, erwartet = konto_neu("k-ohne", OHNE, "Ohne"), set()
    w = werkzeug_von(k)
    props = w["inputSchema"]["properties"]
    assert set(w["inputSchema"].get("required", [])) == {"text", "art"}
    assert set(props["art"]["enum"]) == {"Fehler", "Wunsch", "Frage"} == set(konten.BETREIBER_MELDUNG_ARTEN)
    assert "zusammenhang" in props and "text" in props
    if erwartet:
        assert set(props["reise"]["enum"]) == erwartet
    else:
        assert "reise" not in props


# ---------- AC-2: Alias englisch/deutsch ----------

def test_alias_deutsch_englisch(zwei):
    u = zwei()
    assert schnittstelle.NAMEN.get("report_to_frieda") == WERKZEUG
    assert schnittstelle.PARAMETER.get("zusammenhang") == "context"
    ok = lambda r: {"result": r}   # noqa: E731
    aussen = kn.frieda_antwort({"konto_id": u.a["id"]}, 1, "tools/list", {}, ok)["result"]["tools"]
    assert "report_to_frieda" in [w["name"] for w in aussen]
    en = kn.frieda_antwort({"konto_id": u.a["id"]}, 2, "tools/call", {"name": "report_to_frieda", "arguments": {
        "text": FEHLER_TEXT, "art": "Fehler", "context": ZUSAMMENHANG}}, ok)["result"]
    de = kn.frieda_antwort({"konto_id": u.a["id"]}, 3, "tools/call", {"name": WERKZEUG, "arguments": {
        "text": FEHLER_TEXT, "art": "Fehler", "zusammenhang": ZUSAMMENHANG}}, ok)["result"]
    assert en["isError"] is False and de["isError"] is False
    z = zeilen(u.a["id"])
    assert len(z) == 2 and z[0]["zusammenhang"] == z[1]["zusammenhang"] == ZUSAMMENHANG


# ---------- AC-3: Meldung anlegen ----------

@pytest.mark.parametrize("reise", ["beispielreise", "stadtwochenende"])
def test_meldung_wird_gespeichert_und_nummer_geantwortet(zwei, reise):
    u = zwei()
    k = u.a if reise == "beispielreise" else u.b
    t, fehler = melden(k, art="Fehler", text="  " + FEHLER_TEXT + "  ", reise=reise, zusammenhang=ZUSAMMENHANG)
    assert fehler is False and meldet(t, "konnektor.an_frieda_melden.angekommen", k["sprache"]), t
    z = zeilen(k["id"])
    assert len(z) == 1
    assert (z[0]["konto"], z[0]["reise"], z[0]["art"], z[0]["text"], z[0]["zusammenhang"]) == (
        k["id"], reise, "Fehler", FEHLER_TEXT, ZUSAMMENHANG)
    assert z[0]["zeit"] and z[0]["issue"] is None and nummer(t) == z[0]["id"]
    t, fehler = melden(k, art="Wunsch", text="Beispielwert: ein Wunsch")
    assert fehler is False
    z = zeilen(k["id"])[-1]
    assert z["reise"] == "" and z["zusammenhang"] == "" and z["art"] == "Wunsch"


# ---------- AC-5: fremde Reise ----------

def test_fremde_reise_abgelehnt(zwei):
    u = zwei()
    betreiber_anlegen()
    t, fehler = melden(u.a, art="Fehler", text=FEHLER_TEXT, reise="stadtwochenende")
    assert fehler is True and meldet(t, "konnektor.frieda_werkzeug.1", u.a["sprache"]), t
    assert zeilen() == [] and mails(u.mails) == [] and versand(f"betreiber_meldung:{u.a['id']}") == 0
    t, fehler = melden(u.a, art="Fehler", text=FEHLER_TEXT, reise="gibt-es-nicht")
    assert fehler is True and zeilen() == []


# ---------- AC-6: Pflicht und Grenzen der Felder ----------

def test_leer_zu_lang_falsche_art(db_welt):
    ida = db_welt["ida"]
    faelle = [({"art": "Fehler", "text": ""}, "konto.betreiber_meldung.leer"),
              ({"art": "Fehler", "text": " \n\t "}, "konto.betreiber_meldung.leer"),
              ({"art": "Fehler", "text": "x" * 2001}, "konto.betreiber_meldung.zu_lang"),
              ({"art": "Fehler", "text": "ok", "zusammenhang": "x" * 2001}, "konto.betreiber_meldung.zu_lang"),
              ({"art": "Lob", "text": "ok"}, "konto.betreiber_meldung.art"),
              ({"art": None, "text": "ok"}, "konto.betreiber_meldung.art")]
    for args, schluessel in faelle:
        with pytest.raises(konten.KontoFehler) as f:
            konten.an_betreiber_melden(ida, args["art"], args["text"], zusammenhang=args.get("zusammenhang"))
        assert f.value.schluessel == schluessel, (args, f.value.schluessel)
    assert zeilen() == [] and versand("betreiber_meldung:k-ida") == 0
    nr = konten.an_betreiber_melden(ida, "Frage", "x" * 2000, zusammenhang="y" * 2000)
    assert isinstance(nr, int) and len(zeilen()) == 1
    assert konten.BETREIBER_MELDUNG_MAX == 2000


def test_fehler_im_werkzeug_in_sprache_des_kontos(db_welt):
    k = konto_neu("k-en", "en@beispiel.invalid", "Eve", "en")
    t, fehler = melden(k, art="Fehler", text="   ")
    assert fehler is True and meldet(t, "konto.betreiber_meldung.leer", "en"), t


# ---------- Punkt 2: zählt nicht in die Schreibgrenze ----------

def test_zaehlt_nicht_in_schreibgrenze(db_welt, monkeypatch):
    monkeypatch.setenv("FR_GRENZE_SCHREIBEN", "2")
    ida = db_welt["ida"]
    for i in range(5):
        t, fehler = melden(ida, art="Wunsch", text=f"Beispielwert {i}")
        assert fehler is False, t
    with closing(konten.db()) as v:
        assert v.execute("SELECT COUNT(*) FROM schreibvorgaenge WHERE konto = 'k-ida'").fetchone()[0] == 0
    assert konten.schreibgrenze(ida) is None


# ---------- AC-16: Anleitung ----------

@pytest.mark.parametrize("sprache", ["de", "en"])
def test_anleitung_nennt_melden(zwei, sprache):
    u = zwei()
    konten.sprache_setzen(u.a["id"], sprache)
    mit = kn.anleitung_frieda(konten.konto(u.a["id"]))
    ohne = kn.anleitung_frieda(konto_neu("k-ohne", OHNE, "Ohne", sprache))
    assert meldet(mit, "konnektor.anleitung.frieda.melden", sprache)
    assert meldet(ohne, "konnektor.anleitung.frieda.melden", sprache)


# ---------- AC-4: Mail an Betreiber mit Reply-To ----------

def test_mail_an_betreiber_mit_reply_to(db_welt):
    betreiber_anlegen()
    nr = konten.an_betreiber_melden(db_welt["ida"], "Fehler", FEHLER_TEXT, "beispielreise", ZUSAMMENHANG)
    ms = mails(db_welt["mails"])
    assert sorted(m["an"] for m in ms) == sorted([BETR_DE, BETR_EN]), ms
    for m in ms:
        sprache = "de" if m["an"] == BETR_DE else "en"
        assert m["antwort_an"] == IDA
        assert m["betreff"] == text("konto.betreiber_meldung.mail_betreff", sprache, nr=nr,
                                    art=texte.datenwert(sprache, "Fehler"))
        assert meldet(m["text"], "konto.betreiber_meldung.mail_text", sprache)
        for teil in (str(nr), "Ida", IDA, texte.datenwert(sprache, "Fehler"), "beispielreise", FEHLER_TEXT, ZUSAMMENHANG):
            assert teil in m["text"], (sprache, teil)
        assert FEHLER_TEXT not in m["betreff"] and IDA not in m["betreff"]


def test_mail_senden_antwort_an_smtp(tmp_path, monkeypatch):
    gesendet = []

    class Spion:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self):
            pass

        def login(self, *a):
            pass

        def send_message(self, m):
            gesendet.append(m)

    monkeypatch.delenv("FR_MAIL_DATEI", raising=False)
    monkeypatch.setenv("FR_SMTP_HOST", "smtp.beispiel.invalid")
    monkeypatch.setenv("FR_ABSENDER", "frieda@beispiel.invalid")
    monkeypatch.setattr(konten.smtplib, "SMTP", Spion)
    konten.mail_senden(BETR_DE, "Betreff", "Text", antwort_an=IDA)
    konten.mail_senden(BETR_DE, "Betreff", "Text")
    assert gesendet[0]["Reply-To"] == IDA and gesendet[0]["From"] == "frieda@beispiel.invalid"
    assert gesendet[1]["Reply-To"] is None
    # FR_MAIL_DATEI: ohne antwort_an dieselbe Zeile wie bisher, mit antwort_an ein Feld mehr
    datei = tmp_path / "m.jsonl"
    monkeypatch.setenv("FR_MAIL_DATEI", str(datei))
    konten.mail_senden(BETR_DE, "B", "T")
    konten.mail_senden(BETR_DE, "B", "T", antwort_an=IDA)
    a, b = [json.loads(z) for z in datei.read_text(encoding="utf-8").splitlines()]
    assert a == {"an": BETR_DE, "betreff": "B", "text": "T"}
    assert b == {"an": BETR_DE, "betreff": "B", "text": "T", "antwort_an": IDA}


# ---------- AC-7: Tagesgrenze ----------

def test_grenze_10_je_konto_und_tag(db_welt, monkeypatch):
    ida, karl = db_welt["ida"], db_welt["karl"]
    assert konten.JE_KONTO_MELDUNGEN == (10, 24 * 3600)
    jetzt = [1_800_000_000.0]
    monkeypatch.setattr(konten, "_jetzt", lambda: jetzt[0])
    for args in (("Fehler", ""), ("Fehler", "x" * 2001), ("Lob", "ok")):   # abgelehnte zählen nicht
        with pytest.raises(konten.KontoFehler):
            konten.an_betreiber_melden(ida, *args)
    for i in range(10):
        konten.an_betreiber_melden(ida, "Wunsch", f"Beispielwert {i}")
    with pytest.raises(konten.KontoFehler) as f:
        konten.an_betreiber_melden(ida, "Wunsch", "elfte")
    assert f.value.schluessel == "konto.betreiber_meldung.grenze" and f.value.werte.get("n") == 10
    assert len(zeilen("k-ida")) == 10
    konten.an_betreiber_melden(karl, "Frage", "Beispielwert: anderes Konto")
    jetzt[0] += 24 * 3600 + 1
    konten.an_betreiber_melden(ida, "Wunsch", "am nächsten Tag")
    assert len(zeilen("k-ida")) == 11


# ---------- AC-8: Mailfehler und kein Betreiber ----------

def test_mailfehler_verliert_meldung_nicht(db_welt, monkeypatch, capsys):
    betr_de, _ = betreiber_anlegen()
    echt = konten.mail_senden
    erreicht = []

    def senden(an, betreff, text_, antwort_an=None):
        if an == BETR_DE:
            raise konten.KontoFehler("konto.fehler.mail_fehlgeschlagen")
        erreicht.append(an)
        return echt(an, betreff, text_, antwort_an=antwort_an)

    monkeypatch.setattr(konten, "mail_senden", senden)
    t, fehler = melden(db_welt["ida"], art="Fehler", text=FEHLER_TEXT, zusammenhang=ZUSAMMENHANG)
    assert fehler is False and meldet(t, "konnektor.an_frieda_melden.angekommen"), t
    nr = nummer(t)
    assert [z["id"] for z in zeilen("k-ida")] == [nr] and erreicht == [BETR_EN]
    err = [z for z in capsys.readouterr().err.splitlines() if z.startswith("operator report")]
    assert len(err) == 1 and err[0].startswith(f"operator report {nr}: mail failed:")
    assert FEHLER_TEXT not in err[0] and "@" not in err[0]
    assert str(nr) in kn.meine_reisen_konto(betr_de)
    konten.main(["meldungen"])
    assert FEHLER_TEXT in capsys.readouterr().out


def test_ohne_betreiber_konto(db_welt):
    t, fehler = melden(db_welt["ida"], art="Frage", text="Beispielwert: eine Frage")
    assert fehler is False and meldet(t, "konnektor.an_frieda_melden.angekommen")
    assert len(zeilen("k-ida")) == 1 and mails(db_welt["mails"]) == []


# ---------- AC-9: Löschen ----------

def test_loeschen_entfernt_zeilen_und_versand_schluessel(db_welt):
    konten.an_betreiber_melden(db_welt["ida"], "Fehler", FEHLER_TEXT)
    konten.an_betreiber_melden(db_welt["karl"], "Wunsch", "Beispielwert: Karls Wunsch")
    assert versand("betreiber_meldung:k-ida") == 1
    konten.loeschen("k-ida")
    assert zeilen("k-ida") == [] and versand("betreiber_meldung:k-ida") == 0
    assert len(zeilen("k-karl")) == 1 and versand("betreiber_meldung:k-karl") == 1
    assert "betreiber_meldungen" in __import__("inspect").getsource(konten.loeschen)


# ---------- AC-13: Export ----------

def test_export_enthaelt_eigene_meldungen_ohne_issue(db_welt, monkeypatch):
    ida, karl = db_welt["ida"], db_welt["karl"]
    vorher = anmeldung.export_person(ida, [], {})
    assert vorher["betreiber_meldungen"] == []
    nr = konten.an_betreiber_melden(ida, "Fehler", FEHLER_TEXT, None, ZUSAMMENHANG)
    konten.an_betreiber_melden(karl, "Wunsch", "Beispielwert: Karls geheimer Wunsch")
    assert konten.betreiber_meldung_erledigt(nr, "privat#7") is True
    p = anmeldung.export_person(ida, [], {})
    assert {k for k in p if k not in ("erstellt", "betreiber_meldungen")} == {
        k for k in vorher if k not in ("erstellt", "betreiber_meldungen")}
    (m,) = p["betreiber_meldungen"]
    assert set(m) == {"art", "text", "zusammenhang", "reise", "zeit", "erledigt"}
    assert (m["art"], m["text"], m["zusammenhang"], m["reise"], m["erledigt"]) == ("Fehler", FEHLER_TEXT, ZUSAMMENHANG, "", True)
    assert re.match(r"^\d{4}-\d{2}-\d{2}T", m["zeit"])
    monkeypatch.setattr(anmeldung, "reise_exportieren", lambda reise, datei: ("fehlt", None))
    with anmeldung.export_bauen(ida, {}) as datei:
        z = zipfile.ZipFile(io.BytesIO(datei.read()))
        alles = b"".join(z.read(n) for n in z.namelist()).decode("utf-8")
    assert FEHLER_TEXT in alles and "privat#7" not in alles
    assert "Karls geheimer Wunsch" not in alles and KARL not in alles


# ---------- AC-10, AC-11: Betreiber-Sicht bei my_trips ----------

def test_betreiber_sieht_offene_meldungen_bei_my_trips(db_welt):
    betr_de, _ = betreiber_anlegen()
    assert not meldet(kn.meine_reisen_konto(betr_de), "konnektor.meine_reisen.betreiber_meldungen")
    konten.reisen_anlegen_anfragen("k-karl")
    lang = "Zeile eins\nZeile zwei " + "x" * 400
    a = konten.an_betreiber_melden(db_welt["ida"], "Fehler", lang)
    b = konten.an_betreiber_melden(db_welt["karl"], "Frage", "Beispielwert: Frage von Karl")
    t = kn.meine_reisen_konto(betr_de)
    assert meldet(t, "konnektor.meine_reisen.betreiber_meldungen")
    assert text("konnektor.meine_reisen.betreiber_meldungen", n=2) in t
    assert t.index(text("konnektor.ausgabe.meine_reisen_konto.3")) < t.index(
        text("konnektor.meine_reisen.betreiber_meldungen", n=2))
    zeile_a = next(z for z in t.splitlines() if IDA in z)
    assert "Zeile eins Zeile zwei" in zeile_a and "\n" not in zeile_a and "x" * 400 not in zeile_a
    assert str(a) in zeile_a and "Ida" in zeile_a and texte.datenwert("de", "Fehler") in zeile_a
    konten.betreiber_meldung_erledigt(b, "privat#8")
    t = kn.meine_reisen_konto(betr_de)
    assert "Frage von Karl" not in t and text("konnektor.meine_reisen.betreiber_meldungen", n=1) in t
    konten.betreiber_meldung_erledigt(a, "privat#9")
    assert not meldet(kn.meine_reisen_konto(betr_de), "konnektor.meine_reisen.betreiber_meldungen")


def test_betreiber_sieht_hoechstens_20(db_welt, monkeypatch):
    betr_de, _ = betreiber_anlegen()
    monkeypatch.setattr(konten, "JE_KONTO_MELDUNGEN", (100, 24 * 3600))
    for i in range(25):
        konten.an_betreiber_melden(db_welt["ida"], "Wunsch", f"Beispielwert Nummer {i:02d}")
    t = kn.meine_reisen_konto(betr_de)
    assert sum(1 for z in t.splitlines() if IDA in z) == 20
    assert "Nummer 24" in t and "Nummer 04" not in t


def test_nicht_betreiber_sieht_keine_liste(db_welt):
    konten.an_betreiber_melden(db_welt["ida"], "Fehler", FEHLER_TEXT)
    t = kn.meine_reisen_konto(db_welt["ida"])
    assert not meldet(t, "konnektor.meine_reisen.betreiber_meldungen") and FEHLER_TEXT not in t


# ---------- AC-12: CLI ----------

def test_cli_meldungen_und_erledigt(db_welt, capsys):
    a = konten.an_betreiber_melden(db_welt["ida"], "Fehler", FEHLER_TEXT, "beispielreise", ZUSAMMENHANG)
    b = konten.an_betreiber_melden(db_welt["karl"], "Wunsch", "Beispielwert: Wunsch")
    assert konten.main(["meldungen"]) == 0
    out = capsys.readouterr().out
    assert f"#{a}" in out and f"#{b}" in out and IDA in out and "Ida" in out and "trip: beispielreise" in out
    assert "issue: open" in out and FEHLER_TEXT in out and f"context: {ZUSAMMENHANG}" in out and "trip: -" in out
    assert konten.main(["meldung-erledigt", str(a), "privat#7"]) == 0
    assert "done" in capsys.readouterr().out
    konten.main(["meldungen"])
    out = capsys.readouterr().out
    assert f"#{a}" not in out and f"#{b}" in out
    konten.main(["meldungen", "--alle"])
    out = capsys.readouterr().out
    assert f"#{a}" in out and "issue: privat#7" in out
    konten.main(["meldung-erledigt", "9999", "privat#1"])
    assert "no such report" in capsys.readouterr().out
    assert konten.main(["meldung-erledigt", str(b), "  "]) == 2
    assert meldet(capsys.readouterr().out, "konto.betreiber_meldung.issue_fehlt")
    assert [m["id"] for m in konten.betreiber_meldungen()] == [b]
    assert konten.main(["meldung-erledigt", "abc", "privat#1"]) == 1
    assert konten.main(["meldung-erledigt", str(b)]) == 1
    assert konten.betreiber_meldung_erledigt(9999, "x") is False
    with pytest.raises(konten.KontoFehler):
        konten.betreiber_meldung_erledigt(b, "")


# ---------- AC-14, AC-15, AC-17: Seiten und Texte ----------

@pytest.mark.parametrize("sprache", ["de", "en"])
def test_datenschutz_nennt_meldungen(monkeypatch, sprache):
    seite_in(sprache, monkeypatch)
    abschnitte = anmeldung.DATENSCHUTZ_ABSCHNITTE
    assert abschnitte.index("belege") + 1 == abschnitte.index("betreiber_meldungen") == abschnitte.index("sicherungen") - 1
    t = anmeldung.datenschutz_inhalt()
    titel = text("recht.datenschutz.betreiber_meldungen.titel", sprache)
    assert titel in t and meldet(t, "recht.datenschutz.betreiber_meldungen.text", sprache)
    assert t.index(text("recht.datenschutz.belege.titel", sprache)) < t.index(titel) < t.index(
        text("recht.datenschutz.sicherungen.titel", sprache))
    assert meldet(text("recht.datenschutz.konto_loeschen", sprache), "recht.datenschutz.konto_loeschen", sprache)
    assert ("Meldungen an den Betreiber" if sprache == "de" else "reports to the operator") in text(
        "recht.datenschutz.konto_loeschen", sprache)
    assert text("recht.datenschutz.folgt", sprache) == FOLGT[sprache]
    rechte = [text(f"recht.datenschutz.{s}", sprache) for s in ("reise_loeschen", "namen_freitext", "export", "folgt")]
    stellen = [t.find(r.split("{")[0][:30]) for r in rechte]
    assert all(s >= 0 for s in stellen) and stellen == sorted(stellen)


@pytest.mark.parametrize("sprache", ["de", "en"])
def test_alpha_nennt_kontakt_mit_und_ohne_einstellung(monkeypatch, tmp_path, sprache):
    seite_in(sprache, monkeypatch)
    monkeypatch.setenv("FR_EINSTELLUNGEN", str(tmp_path / "keine.env"))
    monkeypatch.setenv("FR_BETREIBER_KONTAKT", "kontakt<x>&co@example.org")
    t = anmeldung.alpha_inhalt()
    assert meldet(t, "recht.alpha.melden", sprache) and "kontakt&lt;x&gt;&amp;co@example.org" in t and "<x>" not in t
    for leer in (None, "   "):
        if leer is None:
            monkeypatch.delenv("FR_BETREIBER_KONTAKT", raising=False)
        else:
            monkeypatch.setenv("FR_BETREIBER_KONTAKT", leer)
        t = anmeldung.alpha_inhalt()
        assert meldet(t, "recht.alpha.melden_impressum", sprache) and 'href="/impressum"' in t
        assert "{kontakt}" not in t and "{impressum}" not in t


@pytest.mark.parametrize("sprache", ["de", "en"])
def test_export_text_nennt_meldungen(sprache):
    t = text("konto.export.punkt_4", sprache)
    assert ("Meldungen an den Betreiber" if sprache == "de" else "reports to the operator") in t


def test_texte_vollstaendig():
    for sprache in texte.SPRACHEN:
        katalog = getattr(texte.sprache(sprache), "TEXTE", {})
        fehlen = [s for s in NEUE_SCHLUESSEL if s not in katalog]
        assert not fehlen, (sprache, fehlen)
    platz = lambda s, sp: set(re.findall(r"\{(\w+)\}", texte.t(sp, s)))   # noqa: E731
    for s in NEUE_SCHLUESSEL:
        assert platz(s, "de") == platz(s, "en"), s
    assert texte.datenwert("de", "Fehler") == "Fehler" and texte.datenwert("en", "Fehler") == "bug"


# ---------- AC-19: nichts Weiteres ändert sich ----------

def test_unveraendert():
    quelle = (ENGINE / "konnektor.py").read_text(encoding="utf-8")
    assert "feedback_give" in schnittstelle.NAMEN and schnittstelle.NAMEN["feedback_give"] == "rueckmeldung_geben"
    assert WERKZEUG not in getattr(kn, "SCHREIB_WERKZEUGE", ()) and WERKZEUG not in getattr(kn, "SCHREIB_AKTION", ())
    assert "an_frieda_melden" in quelle
    deploy = (WURZEL / "betrieb" / "deploy.sh").read_text(encoding="utf-8")
    assert "betreiber" not in deploy.lower() or "betreiber_meldung" not in deploy
    with closing(sqlite3.connect(":memory:")) as v:
        v.executescript(konten.SCHEMA)
        spalten = [z[1] for z in v.execute("PRAGMA table_info(betreiber_meldungen)")]
    assert spalten == ["id", "konto", "reise", "art", "text", "zusammenhang", "zeit", "issue"]
