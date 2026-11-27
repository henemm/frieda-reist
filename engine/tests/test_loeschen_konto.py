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
    # push_stand hält auch Zeilen je Konto (sammel:, mail:); bild_loeschungen (#582) hält wie loeschprotokoll nur Reise,
    # Bildkennung und Datum, keine Spalte mit Konto oder Adresse
    nur_server = {"push_schluessel", "loeschprotokoll", "bild_loeschungen"}
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
    # Stempel ohne Software-Kennung: veroeffentlichen.sh baut neu ([ -z "$gk" ]); der Stempel bleibt mit der Nummer stehen
    # (die Sperre der ersten Umschaltung, #350, ist mit #557 entfallen)
    assert stempel.read_text().split() == ["3"]
    text = (WURZEL / "betrieb" / "veroeffentlichen.sh").read_text(encoding="utf-8")
    assert '[ -z "$gk" ]' in text


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


# ---------- #694: Ablage ohne Reise (neu/), Aufträge und ausstehende neue Reisen ----------
# Spec: docs/specs/betrieb/konto-loeschen-ablage-neu-694.md. Schnittstelle zusätzlich:
#   rueckmeldungen.ablage_sperre(ordner)   Kontextmanager, Dateisperre für Anhängen und Umschreiben in einem Ordner
#   konten._ablage_neu_bereinigen(kid, email, name)   räumt neu/meldungen.jsonl und neu/auftraege.jsonl ab, Aufruf in
#                                                      loeschen; die Ausstehend-Datei (KN_AUSSTEHEND) räumt zustellen.py ab

import contextlib  # noqa: E402
import os  # noqa: E402
import rueckmeldungen as rm  # noqa: E402

sys.path.insert(0, str(WURZEL / "betrieb"))
import zustellen  # noqa: E402

LEA = "lea@beispiel.invalid"   # Beispielwert: weitere eingeladene Person, bleibt unberührt


def _zeilen(p):
    return [json.loads(z) for z in p.read_text(encoding="utf-8").splitlines() if z.strip()] if p.exists() else []


def _schreiben(p, zeilen):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(z, ensure_ascii=False) + "\n" for z in zeilen), encoding="utf-8")


@pytest.fixture
def neu_lage(zwei, tmp_path, monkeypatch):
    """Beide Reisen, Karl angemeldet (die Person, deren Konto gelöscht wird), Ausstehend-Datei unter tmp_path."""
    def bauen():
        u = zwei()
        anmelden(u, KARL)
        u.karl = konten.konto_per_email(KARL)
        u.neu = rm.ordner_neu(anlegen=True)
        u.ausstehend = tmp_path / "konnektor" / "neue-reisen-ausstehend.jsonl"
        monkeypatch.setenv("KN_AUSSTEHEND", str(u.ausstehend))
        return u
    return bauen


def _bitte(u, k, mit_konto=True):
    """Meldung „Reisen anlegen“ wie anmeldung.betreiber_melden, an Ida."""
    return rm.meldung_anlegen(u.neu, [u.a["id"]], "anfrage_reisen", "reise", f"{k['name']} <{k['email']}> bittet",
                              teile=[("konto.meldungen.text.anfrage_reisen", {"name": k["name"], "email": k["email"]})],
                              extra={"konto": k["id"]} if mit_konto else None)


def _warteliste(u, email):
    return rm.meldung_anlegen(u.neu, [u.a["id"]], "anfrage_warteliste", "reise", f"{email} wartet",
                              teile=[("konto.meldungen.text.anfrage_warteliste", {"email": email})])


def _auftrag(aid, k, pfad, personen, einladen=()):
    namen = ", ".join(f"{p['name']} ({p['rolle']})" for p in personen.values())
    return {"id": aid, "erstellt": "2026-11-20T10:00:00+00:00", "name": k["name"], "konto": k["name"].lower(),
            "konto_id": k["id"], "art": "Neue Reise", "ziel": "allgemein", "quelle": "Claude-App",
            "text": f"Neue Reise „Skiwoche“. Personen: {namen}. Ordner {pfad}.",
            "daten": {"neue_reise": {"pfad": pfad, "sprache": "de", "personen": personen}}, "einladen": list(einladen)}


def _zustellen(u, tmp_path):
    """Lauf von betrieb/zustellen.py auf der Ausstehend-Datei; die Seiten sind leer, also wird nichts freigeschaltet."""
    (tmp_path / "seiten").mkdir(exist_ok=True)
    return zustellen.ausstehend(WURZEL, u.ausstehend, seiten=tmp_path / "seiten", freischalten="/bin/false")


def test_neu_anfrage_reisen_der_person_entfaellt(neu_lage):
    u = neu_lage()
    _bitte(u, u.karl)
    _bitte(u, u.karl, mit_konto=False)          # alte Zeile von vor #687: nur über die Adresse zuzuordnen
    fremd = _bitte(u, u.b)
    konten.loeschen(u.karl["id"])
    assert _zeilen(u.neu / "meldungen.jsonl") == [fremd]


def test_neu_anfrage_warteliste_derselben_adresse_entfaellt(neu_lage):
    u = neu_lage()
    _warteliste(u, KARL)
    fremd = _warteliste(u, LEA)
    konten.loeschen(u.karl["id"])
    assert _zeilen(u.neu / "meldungen.jsonl") == [fremd]


def test_neu_betreiberin_nur_kennung_aus_an(neu_lage):
    u = neu_lage()
    konten.recht_setzen(u.karl["id"], "betreiber")
    beide = rm.meldung_anlegen(u.neu, [u.a["id"], u.karl["id"]], "anfrage_reisen", "reise", "Tom bittet",
                               extra={"konto": u.b["id"]})
    rm.meldung_anlegen(u.neu, [u.karl["id"]], "technik", "reise", "Sicherung gelungen")
    konten.loeschen(u.karl["id"])
    assert _zeilen(u.neu / "meldungen.jsonl") == [beide | {"an": [u.a["id"]]}]


def test_neu_neue_reise_an_person_entfaellt(neu_lage):
    u = neu_lage()
    rm.meldung_anlegen(u.neu, [u.karl["id"]], "neue_reise", "skiwoche-2027", "Deine Reise ist online")
    rm.meldung_anlegen(u.neu, [u.karl["name"]], "neue_reise", "skiwoche-2027", "Deine Reise ist online")  # alter Rückfall
    rm.meldung_anlegen(u.neu, [u.karl["id"]], "loeschung", "reise", "Ida hat eine Reise vorgemerkt")
    konten.loeschen(u.karl["id"])
    assert _zeilen(u.neu / "meldungen.jsonl") == []


def test_neu_name_in_an_bleibt_wenn_anderes_konto_ihn_traegt(neu_lage):
    u = neu_lage()
    konten.name_setzen(u.b["id"], u.karl["name"])
    gleich = rm.meldung_anlegen(u.neu, [u.karl["name"]], "neue_reise", "skiwoche-2027", "Deine Reise ist online")
    rm.meldung_anlegen(u.neu, [u.karl["id"]], "neue_reise", "skiwoche-2027", "Deine Reise ist online")
    konten.loeschen(u.karl["id"])
    assert _zeilen(u.neu / "meldungen.jsonl") == [gleich]


def test_neu_auftrag_der_person_pseudonymisiert(neu_lage):
    u = neu_lage()
    name = u.karl["name"]
    personen = {"karl": {"name": name, "rolle": "organisator"}, "karla": {"name": name + "a", "rolle": "mitwirkend"}}
    _schreiben(u.neu / "auftraege.jsonl", [_auftrag("A-20261120-100000-ab12", u.karl, "skiwoche-2027", personen)])
    konten.loeschen(u.karl["id"])
    [a] = _zeilen(u.neu / "auftraege.jsonl")
    assert a["name"] == GELOESCHT and a["konto"] == GELOESCHT and "konto_id" not in a
    assert a["daten"]["neue_reise"]["personen"]["karl"]["name"] == GELOESCHT
    assert a["daten"]["neue_reise"]["personen"]["karla"]["name"] == name + "a"     # längerer Name bleibt
    assert f"{GELOESCHT} (organisator)" in a["text"] and f"{name}a (mitwirkend)" in a["text"]
    assert not re.search(rf"\b{re.escape(name)}\b", a["text"])
    assert a["daten"]["neue_reise"]["pfad"] == "skiwoche-2027" and a["id"] == "A-20261120-100000-ab12"


def test_neu_einladen_mit_adresse_entfernt_fremder_auftrag(neu_lage):
    u = neu_lage()
    personen = {"tom": {"name": "Tom", "rolle": "organisator"}, "karl": {"name": "Karli", "rolle": "mitwirkend"},
                "lea": {"name": "Lea", "rolle": "mitwirkend"}}
    lea = {"schluessel": "lea", "email": LEA, "rolle": "mitwirkend", "name": "Lea"}
    _schreiben(u.neu / "auftraege.jsonl", [_auftrag("A-20261121-100000-cd34", u.b, "segeltoern-2027", personen, [
        {"schluessel": "karl", "email": KARL.upper(), "rolle": "mitwirkend", "name": "Karli"}, lea])])
    vorher = _zeilen(u.neu / "auftraege.jsonl")[0]
    konten.loeschen(u.karl["id"])
    [a] = _zeilen(u.neu / "auftraege.jsonl")
    assert a["einladen"] == [lea]
    assert a["daten"]["neue_reise"]["personen"]["karl"]["name"] == GELOESCHT
    assert "Karli" not in a["text"] and f"{GELOESCHT} (mitwirkend)" in a["text"] and "Lea (mitwirkend)" in a["text"]
    erwartet = vorher | {"einladen": [lea], "text": a["text"],
                         "daten": {"neue_reise": vorher["daten"]["neue_reise"] | {"personen": a["daten"]["neue_reise"]["personen"]}}}
    assert a == erwartet and a["name"] == "Tom" and a["konto_id"] == u.b["id"]
    assert a["daten"]["neue_reise"]["personen"]["lea"]["name"] == "Lea"


def test_neu_ausstehende_reise_vorgemerkt(neu_lage, tmp_path, capsys):
    u = neu_lage()
    fremd = {"ordner": "segeltoern-2027", "aid": "A-20261121-100000-cd34", "name": "Tom", "person": "tom", "konto_id": u.b["id"]}
    _schreiben(u.ausstehend, [{"ordner": "skiwoche-2027", "aid": "A-20261120-100000-ab12", "name": u.karl["name"],
                               "person": "karl", "konto_id": u.karl["id"]}, fremd])
    vorher = u.ausstehend.read_bytes()
    konten.loeschen(u.karl["id"])
    assert u.ausstehend.read_bytes() == vorher   # der Rückmeldedienst darf den Ordner des Konnektors nicht beschreiben
    assert _zustellen(u, tmp_path) == 0
    assert _zeilen(u.ausstehend) == [fremd]
    assert "Dropped: skiwoche-2027 (account deleted)" in capsys.readouterr().out
    assert konten.reise_vorgemerkt("skiwoche-2027") and not konten.reise_vorgemerkt("segeltoern-2027")
    assert [z["konto"] for z in konten.loeschungen() if z["reise"] == "skiwoche-2027"] == [None]


def test_neu_fremde_zeilen_byteidentisch(neu_lage):
    u = neu_lage()
    _bitte(u, u.b)
    _warteliste(u, LEA)
    _schreiben(u.neu / "auftraege.jsonl", [_auftrag("A-20261121-100000-cd34", u.b, "segeltoern-2027",
                                                    {"tom": {"name": "Tom", "rolle": "organisator"}})])
    _schreiben(u.ausstehend, [{"ordner": "segeltoern-2027", "aid": "A-1", "name": "Tom", "person": "tom", "konto_id": u.b["id"]}])
    dateien = [u.neu / "meldungen.jsonl", u.neu / "auftraege.jsonl", u.ausstehend]
    vorher = [p.read_bytes() for p in dateien]
    konten.loeschen(u.karl["id"])
    assert [p.read_bytes() for p in dateien] == vorher


def test_neu_volltextsuche_ohne_spur(neu_lage, tmp_path):
    u = neu_lage()
    name = u.karl["name"]
    _bitte(u, u.karl)
    _warteliste(u, KARL)
    rm.meldung_anlegen(u.neu, [u.karl["id"]], "neue_reise", "skiwoche-2027", "Deine Reise ist online")
    _schreiben(u.neu / "auftraege.jsonl", [
        _auftrag("A-1", u.karl, "skiwoche-2027", {"karl": {"name": name, "rolle": "organisator"}}),
        _auftrag("A-2", u.b, "segeltoern-2027", {"tom": {"name": "Tom", "rolle": "organisator"},
                                                 "karl": {"name": name, "rolle": "mitwirkend"}},
                 [{"schluessel": "karl", "email": KARL, "rolle": "mitwirkend", "name": name}])])
    _schreiben(u.ausstehend, [{"ordner": "skiwoche-2027", "aid": "A-1", "name": name, "person": "karl", "konto_id": u.karl["id"]}])
    konten.loeschen(u.karl["id"])
    _zustellen(u, tmp_path)
    for p in [*sorted(x for x in u.neu.rglob("*") if x.is_file()), u.ausstehend]:
        t = p.read_text(encoding="utf-8")
        assert KARL not in t and u.karl["id"] not in t and not re.search(rf"\b{re.escape(name)}\b", t), p.name


def test_neu_unlesbare_zeilen_bleiben(neu_lage):
    u = neu_lage()
    _bitte(u, u.karl)
    with (u.neu / "meldungen.jsonl").open("a", encoding="utf-8") as f:
        f.write("{kaputt\n")
    konten.loeschen(u.karl["id"])
    assert (u.neu / "meldungen.jsonl").read_text(encoding="utf-8") == "{kaputt\n"


def test_neu_fehler_bricht_vor_datenbank_ab(neu_lage, monkeypatch):
    u = neu_lage()
    _bitte(u, u.karl)

    def boom(*a, **kw):
        raise OSError("Platte voll")
    echt = konten._ablage_neu_bereinigen
    monkeypatch.setattr(konten, "_ablage_neu_bereinigen", boom)
    with pytest.raises(konten.KontoFehler) as fehler:
        konten.loeschen(u.karl["id"])
    assert fehler.value.schluessel == "konto.fehler.loeschen_spaeter"
    assert konten.konto(u.karl["id"]) and konten.mitgliedschaften(u.karl["id"])
    monkeypatch.setattr(konten, "_ablage_neu_bereinigen", echt)
    konten.loeschen(u.karl["id"])
    assert konten.konto(u.karl["id"]) is None and _zeilen(u.neu / "meldungen.jsonl") == []


def _sperren_protokollieren(monkeypatch):
    genommen = []

    @contextlib.contextmanager
    def sperre(ordner):
        genommen.append(Path(ordner))
        yield
    monkeypatch.setattr(rm, "ablage_sperre", sperre)
    return genommen


def test_neu_sperre_in_meldung_anlegen(neu_lage, monkeypatch):
    u = neu_lage()
    genommen = _sperren_protokollieren(monkeypatch)
    _bitte(u, u.b)
    assert genommen == [u.neu]


def test_neu_sperre_beim_bereinigen(neu_lage, monkeypatch):
    u = neu_lage()
    _bitte(u, u.karl)
    _schreiben(u.ausstehend, [{"ordner": "skiwoche-2027", "aid": "A-1", "name": "Karl", "person": "karl", "konto_id": u.karl["id"]}])
    genommen = _sperren_protokollieren(monkeypatch)
    konten.loeschen(u.karl["id"])
    assert u.neu in genommen and u.ausstehend.parent not in genommen


def test_neu_loeschen_ohne_schreibrecht_im_konnektorordner(neu_lage):
    """Der Rückmeldedienst sieht den Ordner des Konnektors nur lesend (ProtectSystem=strict): Löschen gelingt trotzdem."""
    u = neu_lage()
    _bitte(u, u.karl)
    _schreiben(u.ausstehend, [{"ordner": "skiwoche-2027", "aid": "A-1", "name": "Karl", "person": "karl", "konto_id": u.karl["id"]}])
    modus = u.ausstehend.parent.stat().st_mode & 0o777
    os.chmod(u.ausstehend.parent, 0o500)
    try:
        konten.loeschen(u.karl["id"])
    finally:
        os.chmod(u.ausstehend.parent, modus)
    assert konten.konto(u.karl["id"]) is None and _zeilen(u.neu / "meldungen.jsonl") == []


def test_neu_bestehende_ablage_der_reisen_unveraendert(neu_lage):
    u = neu_lage()
    (u.o / "eingang.jsonl").write_text(json.dumps({"id": "R-01", "name": "Karl", "text": "Idee"}) + "\n")
    _bitte(u, u.karl)
    konten.loeschen(u.karl["id"])
    text = (u.o / "eingang.jsonl").read_text(encoding="utf-8")
    assert '"Karl"' not in text and GELOESCHT in text


from test_konnektor import seiten, dienst, schreibweg, Schreibweg, IDA_KONTO  # noqa: E402,F401,F811


def test_neu_sperre_im_konnektor_anhaengen(schreibweg, tmp_path, monkeypatch):
    import konnektor as kn
    ausstehend = tmp_path / "ausstehend" / "neue-reisen-ausstehend.jsonl"
    monkeypatch.setenv("KN_AUSSTEHEND", str(ausstehend))
    Schreibweg.antwort = (200, {"ok": True, "text": "Die Reise „Skiwoche“ ist angelegt (Ordner skiwoche-2027, Status Idee)."})
    genommen = _sperren_protokollieren(monkeypatch)
    t, f = kn.reise_anlegen(IDA_KONTO, {"titel": "Skiwoche", "von": "2027-02-06", "bis": "2027-02-13", "sprache": "de",
                                        "personen": [{"vorname": "Karl", "rolle": "mitwirkend"}]})
    assert not f, t
    assert rm.ordner_neu() in genommen and ausstehend.parent not in genommen
