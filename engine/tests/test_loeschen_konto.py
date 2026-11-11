"""Tests für #381 (Meilenstein M5a), Teil Konto: Konto löschen vollständig, Sperre für die letzte Organisator:in,
Mitgehen eigener Reisen, Pseudonymisieren („gelöschte Person“). Spec: docs/specs/betrieb/loeschen-381.md
(Teilschritte B1, B2, C2; AC-12 bis AC-16, AC-18, AC-19).

Nur erfundene Daten: beispielreise (Ida Organisatorin, Karl mitwirkend), stadtwochenende (Tom Organisator, Lea
mitwirkend), alles unter tmp_path. Schnittstelle zusätzlich zu test_loeschen_reise.py:
  konten.loeschen(kid)                          lehnt mit KontoFehler ab, wenn kid letzte Organisator:in einer Reise mit
                                                weiteren Mitgliedern ist (Reise im Fehler genannt); merkt Reisen nur mit
                                                der Person zur Löschung vor; pseudonymisiert Ablage-Dateien sofort
  reisespeicher.namen_ersetzen(reise, name, ersatz) -> int   Herkunftsmuster und vorgaenge.wer, Prüfsummen neu
  Katalog: konto.geloeschte_person
"""
import json
import re
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
WURZEL = ENGINE.parent
BEISPIEL = WURZEL / "beispiel" / "reisen"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import konten  # noqa: E402
import texte  # noqa: E402
from test_anmeldung import abruf, anmelden, welt  # noqa: E402,F401
from test_trennung import zwei, IDA, KARL, TOM  # noqa: E402,F401
from test_loeschen_reise import speicher, _abdruck, REISEN  # noqa: E402,F401

GELOESCHT = texte.t("de", "konto.geloeschte_person") if "konto.geloeschte_person" in getattr(
    texte.sprache("de"), "TEXTE", {}) else "gelöschte Person"


def _spuren(kid, email, name=None):
    """Jede Zeile einer Tabelle der Kontendatenbank, in der Konto, Adresse oder Name noch vorkommen."""
    funde = []
    # die Kennung auch als Teil eines Werts („sammel:<kid>“ in push_stand), aber nicht als Präfix einer anderen Kennung
    kennung = re.compile(rf"(?<![\w-]){re.escape(kid)}(?![\w-])")
    with closing(konten.db()) as v:
        for (t,) in v.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"):
            for z in v.execute(f"SELECT * FROM {t}"):
                werte = [str(x) for x in tuple(z)]
                if any(kennung.search(w) or email in w or (name and w == name) for w in werte):
                    funde.append((t, werte))
    return funde


# ---------- B1: Konto vollständig weg ----------

def test_loeschen_hinterlaesst_in_keiner_tabelle_spuren(zwei):
    u = zwei()
    anmelden(u, KARL)
    karl = konten.konto_per_email(KARL)
    kid = karl["id"]
    with closing(konten.db()) as v, v:
        v.execute("INSERT INTO angelegte_reisen VALUES (?, 'testreise', 1)", (kid,))
        v.execute("INSERT INTO schreibvorgaenge VALUES (?, 1)", (kid,))
        v.execute("INSERT INTO oauth_codes VALUES ('h1','c','r','x','s',?,9e9,NULL,'f')", (kid,))
        v.execute("INSERT INTO oauth_tokens VALUES ('h2','zugang',?,'c','s','f',9e9,NULL)", (kid,))
        v.execute("INSERT INTO warteliste (email, erstellt) VALUES (?, 1)", (KARL,))
        v.execute("INSERT INTO versand VALUES (?, 1)", (f"adresse:{KARL}",))
        v.execute("INSERT INTO versand VALUES (?, 1)", (f"warteliste:{KARL}",))
        v.execute("INSERT INTO push_einstellungen VALUES (?, '{}')", (kid,))
        v.execute("INSERT INTO meldung_gelesen VALUES (?, 'M-1', 1)", (kid,))
        # push_stand (engine/push.py): Sammelliste und Mail-Merker des Kontos; daneben eine andere Kennung, die mit der
        # von Karl beginnt, und ein Schlüssel des Servers: beide bleiben
        v.executemany("INSERT INTO push_stand VALUES (?, '[]')",
                      [(f"sammel:{kid}",), (f"mail:M-20261101-000000-ab12:{kid}",), (f"sammel:{kid}9",),
                       (f"mail:M-20261101-000000-ab12:{kid}9",), ("vapid_stand",)])
    konten.einladen("stadtwochenende", "lea", "lea@beispiel.invalid", "mitwirkend", "Lea", "Karl")
    assert _spuren(kid, KARL)
    konten.loeschen(kid)
    assert _spuren(kid, KARL) == []
    assert konten.konto_per_email(KARL) is None
    with closing(konten.db()) as v:
        rest = sorted(z[0] for z in v.execute("SELECT schluessel FROM push_stand"))
    assert rest == sorted([f"sammel:{kid}9", f"mail:M-20261101-000000-ab12:{kid}9", "vapid_stand"])


def test_test_kennt_jede_tabelle_des_schemas():
    """Eine künftige Tabelle mit Konto- oder Adressspalte darf loeschen() nicht vergessen."""
    import inspect
    quelle = inspect.getsource(konten.loeschen) + inspect.getsource(konten)
    tabellen = {z for z in __import__("re").findall(r"CREATE TABLE IF NOT EXISTS (\w+)", konten.SCHEMA)}
    nur_server = {"push_schluessel", "loeschprotokoll"}   # push_stand hält auch Zeilen je Konto (sammel:, mail:)
    rumpf = inspect.getsource(konten.loeschen)
    fehlen = [t for t in sorted(tabellen - nur_server - {"konten"}) if t not in rumpf]
    assert not fehlen, f"loeschen() nennt diese Tabellen nicht: {fehlen}"
    assert "reise_loeschung" in tabellen and quelle


# ---------- B1: Sperre letzte Organisator:in ----------

def test_letzte_organisatorin_mit_anderen_mitgliedern_gesperrt(zwei):
    u = zwei()
    anmelden(u, KARL)
    with pytest.raises(konten.KontoFehler) as fehler:
        konten.loeschen(u.a["id"])
    assert "beispielreise" in str(fehler.value.werte) or "Wanderung" in str(fehler.value) or fehler.value.werte
    assert konten.konto(u.a["id"]) is not None
    s, _, t = abruf(f"{u.kurl}/konto?loeschen=1", cookie=u.a_keks)
    assert s == 200 and 'name="sicher"' not in t, "die Seite bietet das Löschen nicht an, sie nennt die Reise"


def test_nach_loeschen_der_reise_klappt_es(zwei):
    u = zwei()
    anmelden(u, KARL)
    konten.loeschung_vormerken("beispielreise", u.a["id"])
    konten.loeschen(u.a["id"])
    assert konten.konto(u.a["id"]) is None
    with closing(konten.db()) as v:
        z = v.execute("SELECT konto FROM reise_loeschung WHERE reise = 'beispielreise'").fetchone()
    assert z is not None and not z[0], "auslösendes Konto geleert, Zeile bleibt"


def test_nach_uebergabe_der_rolle_klappt_es(zwei, monkeypatch):
    u = zwei()
    anmelden(u, KARL)
    import rueckmeldungen as rm
    echt = rm.zustand

    def uebergeben(reise):
        z = echt(reise)
        if z and reise == "beispielreise":
            for p in z.get("personen") or []:
                if p.get("schluessel") == "karl":
                    p["rolle"] = "organisator"
        return z
    monkeypatch.setattr(rm, "zustand", uebergeben)
    konten.loeschen(u.a["id"])
    assert konten.konto(u.a["id"]) is None
    assert not konten.reise_vorgemerkt("beispielreise")


def test_reise_nur_mit_der_person_geht_mit_schonfrist(zwei):
    u = zwei()   # Tom ist allein im Stadtwochenende (Lea nicht angemeldet)
    konten.loeschen(u.b["id"])
    assert konten.reise_vorgemerkt("stadtwochenende")
    z = next(x for x in konten.loeschungen() if x["reise"] == "stadtwochenende")
    assert not z["konto"] and z["frist"] > konten._jetzt()


def test_reise_als_mitglied_bleibt(zwei):
    u = zwei()
    anmelden(u, KARL)
    konten.loeschen(konten.konto_per_email(KARL)["id"])
    assert not konten.reise_vorgemerkt("beispielreise")
    assert konten.mitglied(u.a["id"], "beispielreise") == "ida"


def test_loeschseite_zeigt_was_bleibt_und_was_geht(zwei):
    u = zwei()
    s, _, t = abruf(f"{u.kurl}/konto?loeschen=1", cookie=u.b_keks)
    from conftest import meldet
    assert s == 200 and meldet(t, "konto.seite.loeschen_bleibt") and meldet(t, "konto.seite.loeschen_weg")
    assert meldet(t, "konto.loeschen.reisen_gehen_mit") and "Beispielstadt" in t   # Titel des Stadtwochenendes


# ---------- B2: Pseudonymisieren ----------

def test_namen_ersetzen_im_verlauf_und_in_herkunftsmustern(speicher):
    rs = speicher
    yaml_neu = (BEISPIEL / "beispielreise" / "reise.yaml").read_text(encoding="utf-8") + (
        "\n# Herkunft: eingetragen von Karl am 2026-11-02 (Beispielwert)\n")
    rs.vorgang_schreiben("beispielreise", {"reise.yaml": yaml_neu.encode(),
                                           "wissen/karl.md": b"# Kuchen\nKarl mag Quittenkuchen.\n"},
                         wer="Karl", werkzeug="knowledge_write", titel="Karl ergänzt", herkunft="Karl")
    andere = _abdruck(rs, "stadtwochenende")
    n = rs.namen_ersetzen("beispielreise", "Karl", GELOESCHT)
    assert n >= 1
    verlauf = rs.verlauf("beispielreise")
    assert all(e["wer"] != "Karl" for e in verlauf) and any(e["wer"] == GELOESCHT for e in verlauf)
    for stand in range(1, rs.stand_nummer("beispielreise") + 1):
        assert "von Karl am" not in rs.aktueller_stand("beispielreise", stand).get("reise.yaml", b"").decode()
    assert rs.pruefen() == []
    assert _abdruck(rs, "stadtwochenende") == andere, "ein gleichnamiges Mitglied anderer Reisen bleibt"
    # Ist-Stand (AC-16): Freitext außerhalb der Muster bleibt
    assert b"Karl mag Quittenkuchen" in rs.datei("beispielreise", "wissen/karl.md")


def test_namen_ersetzen_erzwingt_neubau(speicher):
    rs = speicher
    stempel = rs.t / "_dienst" / "reise-stand" / "beispielreise.gebaut"
    rs.vorgang_schreiben("beispielreise", {"wissen/x.md": b"# x\n"}, wer="Karl", werkzeug="knowledge_write", titel="x")
    stempel.write_text("3 abc1234\n")   # „<nummer> <software>“ wie nach einem Bau
    rs.namen_ersetzen("beispielreise", "Karl", GELOESCHT)
    # Stempel ohne Software-Kennung: veroeffentlichen.sh baut neu ([ -z "$gk" ]); er bleibt aber stehen, damit die Sperre der
    # ersten Umschaltung (#350) eine Reise im Git-Bauordner nicht anhält
    assert stempel.read_text().split() == ["3"]
    text = (WURZEL / "betrieb" / "veroeffentlichen.sh").read_text(encoding="utf-8")
    assert '[ -z "$gk" ]' in text and 'if [ ! -e "$FR_DIENST/reise-stand/$r.gebaut" ]' in text


def _zwei_karl(speicher, monkeypatch, zweiter):
    """Beispielreise im Speicher mit Konten für Ida und Karl; zweiter: ein weiteres Mitglied namens Karl in derselben Reise."""
    import rueckmeldungen as rm
    with closing(konten.db()) as v, v:
        v.execute("INSERT INTO konten (id, email, name, angelegt, sprache) VALUES ('k-karl', ?, 'Karl', '2026-11-01', 'de')", (KARL,))
        for kid, schl in (("k-ida", "ida"), ("k-karl", "karl")):
            v.execute("INSERT INTO mitgliedschaften VALUES (?, 'beispielreise', ?, '2026-11-01')", (kid, schl))
    personen = [{"schluessel": "ida", "name": "Ida", "rolle": "organisator"},
                {"schluessel": "karl", "name": "Karl", "rolle": "mitwirkend"}]
    if zweiter:
        personen.append({"schluessel": "karl2", "name": "Karl", "rolle": "mitwirkend"})
    monkeypatch.setattr(rm, "zustand", lambda reise: {"personen": personen, "sprache": "de", "status": "planung"}
                        if reise == "beispielreise" else None)
    speicher.vorgang_schreiben("beispielreise", {"wissen/k.md": b"# k\n"}, wer="Karl", werkzeug="knowledge_write", titel="k")


@pytest.mark.parametrize("zweiter", [False, True])
def test_gleichnamiges_mitglied_derselben_reise_bleibt(speicher, monkeypatch, zweiter):
    """F003: Der Verlauf kennt nur Namen. Gibt es in derselben Reise ein zweites Mitglied mit demselben Namen, bleibt der
    Name stehen (lieber nicht ersetzen als den Falschen treffen); sonst wird er ersetzt."""
    _zwei_karl(speicher, monkeypatch, zweiter)
    konten.loeschen("k-karl")
    wer = {e["wer"] for e in speicher.verlauf("beispielreise")}
    assert ("Karl" in wer) == zweiter and (GELOESCHT in wer) != zweiter


def test_abbruch_beim_umbenennen_ist_ein_satz_fuer_menschen(speicher, monkeypatch):
    """F005: Scheitert das Ersetzen (Speicher nicht grün), bleibt das Konto, und die Person bekommt einen Satz aus dem Katalog."""
    _zwei_karl(speicher, monkeypatch, False)
    monkeypatch.setattr(speicher, "pruefen", lambda reise=None: ["erfundene Abweichung"])
    with pytest.raises(konten.KontoFehler) as f:
        konten.loeschen("k-karl")
    assert f.value.schluessel == "konto.fehler.loeschen_spaeter" and konten.konto("k-karl") is not None
    for sp in ("de", "en"):
        assert texte.t(sp, "konto.fehler.loeschen_spaeter") != "konto.fehler.loeschen_spaeter"


def test_ablage_dateien_pseudonymisiert(zwei):
    u = zwei()
    anmelden(u, KARL)
    (u.o / "eingang.jsonl").write_text(json.dumps({"id": "R-01", "name": "Karl", "text": "Idee"}) + "\n")
    (u.o / "aufgaben.json").write_text(json.dumps([{"id": "AG-01", "wer": "Karl", "titel": "Karten kaufen"}]))
    konten.loeschen(konten.konto_per_email(KARL)["id"])
    for datei in ("eingang.jsonl", "aufgaben.json"):
        text = (u.o / datei).read_text(encoding="utf-8")
        assert '"Karl"' not in text and GELOESCHT in text, datei


def test_rueckfall_ohne_fehler_bei_pruefen_rot(speicher, monkeypatch):
    rs = speicher
    rs.vorgang_schreiben("beispielreise", {"wissen/y.md": b"# y\n"}, wer="Karl", werkzeug="knowledge_write", titel="y")
    vorher = _abdruck(rs, "beispielreise")
    monkeypatch.setattr(rs, "pruefen", lambda reise=None: ["erfundene Abweichung"])
    assert hasattr(rs, "namen_ersetzen")
    with pytest.raises(Exception):
        rs.namen_ersetzen("beispielreise", "Karl", GELOESCHT)
    assert _abdruck(rs, "beispielreise") == vorher
    with closing(sqlite3.connect(rs.pfad())) as v:
        assert len(list(v.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'"))) == 4


# ---------- C2: Texte und Datenschutz ----------

@pytest.mark.parametrize("sprache", ["de", "en"])
def test_texte_vorhanden(sprache):
    for s in ("konto.geloeschte_person", "konto.reise_loeschen.mail_vorgemerkt_betreff",
              "konto.reise_loeschen.mail_zurueckgeholt_betreff", "konto.loeschen.reisen_gehen_mit",
              "konto.fehler.letzte_organisatorin"):
        assert texte.t(sprache, s) != s, (sprache, s)


def test_datenschutztext_nennt_loeschen_und_grenzen():
    import anmeldung
    t = anmeldung.datenschutz_inhalt()
    assert "14" in t and "30" in t, "Schonfrist und Aufbewahrung der Sicherungen"
    # ohne Anfrage spricht die Seite die Vorgabe der Software (nicht Deutsch): Text in der Sprache der Seite
    assert texte.t(anmeldung.sprache_der_seite(), "recht.datenschutz.namen_freitext") in t


def test_betriebsdoku_belege_nicht_mehr_nie_geloescht():
    text = (WURZEL / "docs" / "betrieb.md").read_text(encoding="utf-8")
    assert "nie gelöscht" not in text.lower() and "#381" in text
    assert "Schonfrist" in text and "30 Tage" in text and "loeschen" in text
