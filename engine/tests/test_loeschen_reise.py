"""Tests für #381 (Meilenstein M5a), Teil Reise: Löschen einer ganzen Reise mit Schonfrist.
Spec: docs/specs/betrieb/loeschen-381.md (Teilschritte C1, A, A2a, A2b, A3; AC-1 bis AC-11, AC-17, AC-19).

Nur erfundene Daten: die beiden Beispielreisen (beispielreise: Ida Organisatorin, Karl mitwirkend; stadtwochenende:
Tom Organisator, Lea mitwirkend) und erfundene Inhalte, alles unter tmp_path.

Schnittstelle, die diese Tests festlegen (Abweichung von der Spec nur im Namen: `konten.reise_vormerken` gibt es schon
für die Reisegrenze (#380), die Funktionen zum Löschen heißen daher `loeschung_*`):
  instanz.loeschfrist_tage() -> int                    Vorgabe 14, aus FR_LOESCHFRIST_TAGE
  konten.loeschung_vormerken(reise, kid) -> dict       {reise, konto, wann, frist} (Zeitstempel in Sekunden, UTC);
                                                       schon vorgemerkt: KontoFehler, die erste Frist bleibt
  konten.loeschung_zurueckholen(reise, kid)            nach Fristende: KontoFehler
  konten.loeschungen() -> list[dict]                   alle vorgemerkten Reisen (für Mein Konto)
  konten.reise_vorgemerkt(reise) -> bool               vorgemerkt oder schon entfernt (Löschprotokoll)
  konten.faellige_loeschungen() -> list[str]           Reisen mit erreichtem Fristende
  konten.loeschung_abschliessen(reise)                 Zeile weg, Eintrag ins Löschprotokoll (nur Kennung und Datum)
  konten.loeschprotokoll() -> list[str]
  `python3 engine/konten.py vorgemerkt`                je vorgemerkte oder entfernte Reise eine Zeile (für Skripte)
  reisespeicher.reise_entfernen(reise)                 Ausnahme vom Nur-Anhängen, eine Transaktion
  reisespeicher.verdichten()                           wal_checkpoint(TRUNCATE) und VACUUM
  waechter.loeschungen_ausfuehren() -> list[str]       der tägliche Lauf für fällige und protokollierte Reisen
  Mein Konto: GET /konto?reise_loeschen=<reise> (Bestätigung 1), POST aktion=reise_loeschen_1 (verstanden=ja,
  zu Bestätigung 2), POST aktion=reise_loeschen (verstanden=ja, titel=<Reisename>), POST aktion=reise_zurueckholen.
"""
import datetime
import inspect
import json
import os
import re
import shutil
import sqlite3
import subprocess
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
from test_anmeldung import abruf, welt  # noqa: E402,F401  (welt: Fixture)
from test_trennung import zwei, IDA, KARL, TOM  # noqa: E402,F401  (zwei: Fixture)

TAG = 24 * 3600
REISEN = ["beispielreise", "stadtwochenende"]
PNG = b"\x89PNG\r\n\x1a\n" + b"erfundenes Gipfelfoto " * 40
GEHEIM = "Zauberwort-Quittenmus-4711"   # eindeutiger Testinhalt für die Byte-Suche


# ---------- Aufbau ----------

@pytest.fixture
def kdb(tmp_path, monkeypatch):
    """Nur die Kontendatenbank: zwei erfundene Konten."""
    monkeypatch.setenv("FR_KONTEN", str(tmp_path / "konten"))
    monkeypatch.setenv("FR_MAIL_DATEI", str(tmp_path / "mails.jsonl"))
    with closing(konten.db()) as v, v:
        for kid, mail, name in (("k-ida", IDA, "Ida"), ("k-karl", KARL, "Karl")):
            v.execute("INSERT INTO konten (id, email, name, angelegt, sprache) VALUES (?,?,?,?,?)",
                      (kid, mail, name, "2026-11-01T00:00:00+00:00", "de"))
    return konten


def _spaeter(monkeypatch, tage):
    jetzt = konten._jetzt()
    monkeypatch.setattr(konten, "_jetzt", lambda: jetzt + tage * TAG)


@pytest.fixture
def speicher(tmp_path, monkeypatch):
    """Reisespeicher mit beiden Beispielreisen, je ein gemeinsames Foto (dieselbe Ablagedatei) und ein eindeutiger
    Inhalt nur in der Beispielreise; Ablage der Instanz, Webordner, Bauordner und Stempel je Reise."""
    for k in list(os.environ):
        if k.startswith(("FR_", "RM_", "KN_")):
            monkeypatch.delenv(k)
    werte = {"FR_SPEICHER": tmp_path / "_speicher", "FR_KONTEN": tmp_path / "konten", "RM_ABLAGE": tmp_path / "ablage",
             "RM_SEITEN": tmp_path / "seiten", "KN_SEITEN": tmp_path / "seiten", "FR_DIENST": tmp_path / "_dienst",
             "FR_MAIL_DATEI": tmp_path / "mails.jsonl", "FR_SPEICHERREISEN": ",".join(REISEN)}
    for k, w in werte.items():
        monkeypatch.setenv(k, str(w))
    import reisespeicher as rs
    for r in REISEN:
        rs.importieren(BEISPIEL / r, r, "Ida" if r == "beispielreise" else "Tom")
        rs.vorgang_schreiben(r, {"medien/gemeinsam.png": PNG}, wer="Ida", werkzeug="item_update", titel="Foto")
        (tmp_path / "ablage" / r).mkdir(parents=True)
        (tmp_path / "ablage" / r / "eingang.jsonl").write_text('{"name": "Ida", "text": "Beispiel"}\n')
        (tmp_path / "ablage" / r / "belege").mkdir()
        (tmp_path / "ablage" / r / "belege" / "B-01.pdf").write_bytes(b"%PDF erfundener Beleg")
        (tmp_path / "seiten" / r).mkdir(parents=True)
        (tmp_path / "seiten" / r / "index.html").write_text("<html>Beispiel</html>")
        (tmp_path / "_dienst" / "bau" / "reisen" / r).mkdir(parents=True)
        (tmp_path / "_dienst" / "bau" / "reisen" / r / "reise.yaml").write_text("titel: Beispiel\n")
        (tmp_path / "_dienst" / "reise-stand").mkdir(parents=True, exist_ok=True)
        (tmp_path / "_dienst" / "reise-stand" / f"{r}.gebaut").write_text("3\n")
    rs.vorgang_schreiben("beispielreise", {"wissen/geheim.md": f"# Notiz\n{GEHEIM}\n".encode()}, wer="Ida",
                         werkzeug="knowledge_write", titel=GEHEIM)
    with closing(konten.db()) as v, v:
        v.execute("INSERT INTO konten (id, email, name, angelegt, sprache) VALUES ('k-ida', ?, 'Ida', '2026-11-01', 'de')",
                  (IDA,))
    rs.t = tmp_path
    return rs


def _abdruck(rs, reise):
    """Alle Zeilen einer Reise im Speicher (Vorgänge und Versionen) als vergleichbarer Wert."""
    with closing(sqlite3.connect(rs.pfad())) as v:
        return ([tuple(z) for z in v.execute("SELECT * FROM vorgaenge WHERE reise = ? ORDER BY nummer", (reise,))],
                [tuple(z) for z in v.execute("SELECT * FROM versionen WHERE reise = ? ORDER BY vorgang, pfad", (reise,))])


def _faellig_machen(monkeypatch, reise, kid="k-ida"):
    konten.loeschung_vormerken(reise, kid)
    _spaeter(monkeypatch, 15)


# ---------- C1: Ausnahme vom Nur-Anhängen in ADR-0001 und ADR-0009 ----------

@pytest.mark.parametrize("adr", ["0001-kern.md", "0009-reisespeicher.md"])
def test_adr_nennt_ausnahme_vom_nur_anhaengen(adr):
    text = (WURZEL / "docs" / "adr" / adr).read_text(encoding="utf-8")
    assert "reise_entfernen" in text and "namen_ersetzen" in text, adr
    assert re.search(r"Ausnahme", text) and "#381" in text, adr


# ---------- A: Vormerken, Frist, Zurückholen (Kontendatenbank) ----------

def test_frist_vorgabe_und_einstellung(monkeypatch):
    import instanz
    monkeypatch.delenv("FR_LOESCHFRIST_TAGE", raising=False)
    assert instanz.loeschfrist_tage() == 14
    monkeypatch.setenv("FR_LOESCHFRIST_TAGE", "3")
    assert instanz.loeschfrist_tage() == 3


def test_vormerken_legt_zeile_mit_fristende_an(kdb):
    z = konten.loeschung_vormerken("beispielreise", "k-ida")
    assert z["reise"] == "beispielreise" and z["konto"] == "k-ida"
    assert z["frist"] == pytest.approx(z["wann"] + 14 * TAG, abs=1)
    assert [x["reise"] for x in konten.loeschungen()] == ["beispielreise"]
    assert konten.reise_vorgemerkt("beispielreise") and not konten.reise_vorgemerkt("stadtwochenende")


def test_doppelt_vormerken_behaelt_erste_frist(kdb, monkeypatch):
    erst = konten.loeschung_vormerken("beispielreise", "k-ida")
    _spaeter(monkeypatch, 2)
    with pytest.raises(konten.KontoFehler):
        konten.loeschung_vormerken("beispielreise", "k-ida")
    assert konten.loeschungen()[0]["frist"] == erst["frist"]


def test_zurueckholen_in_der_frist(kdb, monkeypatch):
    konten.loeschung_vormerken("stadtwochenende", "k-ida")
    _spaeter(monkeypatch, 13)
    konten.loeschung_zurueckholen("stadtwochenende", "k-ida")
    assert not konten.reise_vorgemerkt("stadtwochenende") and konten.loeschungen() == []


def test_zurueckholen_nach_fristende_abgelehnt(kdb, monkeypatch):
    konten.loeschung_vormerken("beispielreise", "k-ida")
    _spaeter(monkeypatch, 15)
    with pytest.raises(konten.KontoFehler):
        konten.loeschung_zurueckholen("beispielreise", "k-ida")
    assert konten.reise_vorgemerkt("beispielreise")
    assert konten.faellige_loeschungen() == ["beispielreise"]


def test_faellig_erst_nach_fristende(kdb, monkeypatch):
    konten.loeschung_vormerken("beispielreise", "k-ida")
    _spaeter(monkeypatch, 13)
    assert konten.faellige_loeschungen() == []


def test_loeschprotokoll_nur_kennung_und_datum(kdb):
    konten.loeschung_vormerken("beispielreise", "k-ida")
    konten.loeschung_abschliessen("beispielreise")
    assert konten.loeschungen() == [] and konten.loeschprotokoll() == ["beispielreise"]
    assert konten.reise_vorgemerkt("beispielreise"), "entfernte Reisen gelten als vorgemerkt (AC-17)"
    with closing(konten.db()) as v:
        tabelle = next(z[0] for z in v.execute("SELECT name FROM sqlite_master WHERE type='table'")
                       if "protokoll" in z[0])
        spalten = [z[1] for z in v.execute(f"PRAGMA table_info({tabelle})")]
        zeilen = [tuple(z) for z in v.execute(f"SELECT * FROM {tabelle}")]
    assert len(spalten) == 2 and "reise" in spalten, spalten
    assert not any(IDA in str(z) or "Ida" in str(z) or "k-ida" in str(z) for z in zeilen)


def test_befehl_vorgemerkt_fuer_skripte(kdb):
    konten.loeschung_vormerken("stadtwochenende", "k-ida")
    r = subprocess.run([sys.executable, str(ENGINE / "konten.py"), "vorgemerkt"], capture_output=True, text=True,
                       env=os.environ)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["stadtwochenende"]


# ---------- A: Mein Konto (Link, zwei Bestätigungen, Block, Zurückholen, Benachrichtigung) ----------

def _seite(u, keks):
    s, _, t = abruf(f"{u.kurl}/konto", cookie=keks)
    assert s == 200, t
    return t


def _titel(reise):
    import yaml
    return yaml.safe_load((BEISPIEL / reise / "reise.yaml").read_text(encoding="utf-8"))["titel"]


def _mails_an(u, an):
    if not u.mails.exists():
        return []
    return [json.loads(z) for z in u.mails.read_text().splitlines() if json.loads(z)["an"] == an]


def test_link_nur_fuer_organisatorin_einer_speicherreise(zwei, monkeypatch):
    u = zwei()
    monkeypatch.setenv("FR_SPEICHERREISEN", "beispielreise")
    assert "reise_loeschen=beispielreise" in _seite(u, u.a_keks)
    from test_anmeldung import anmelden
    karl_keks, _ = anmelden(u, KARL)
    assert "reise_loeschen=" not in _seite(u, karl_keks), "Mitwirkende sehen den Link nicht"
    monkeypatch.setenv("FR_SPEICHERREISEN", "")
    t = _seite(u, u.a_keks)
    assert "reise_loeschen=" not in t, "Reisen auf dem alten Weg: kein Link"


def test_zwei_bestaetigungen(zwei, monkeypatch):
    u = zwei()
    monkeypatch.setenv("FR_SPEICHERREISEN", "beispielreise")
    s, _, t = abruf(f"{u.kurl}/konto?reise_loeschen=beispielreise", cookie=u.a_keks)
    assert s == 200 and 'name="verstanden"' in t and not konten.reise_vorgemerkt("beispielreise")
    # ohne Haken: nichts
    abruf(f"{u.kurl}/konto", "POST", {"aktion": "reise_loeschen", "reise": "beispielreise",
                                      "titel": _titel("beispielreise")}, cookie=u.a_keks)
    assert not konten.reise_vorgemerkt("beispielreise")
    # Bestätigung 1 führt zur Eingabe des Namens
    s, _, t = abruf(f"{u.kurl}/konto", "POST", {"aktion": "reise_loeschen_1", "reise": "beispielreise",
                                                "verstanden": "ja"}, cookie=u.a_keks)
    assert s == 200 and 'name="titel"' in t and not konten.reise_vorgemerkt("beispielreise")
    # falscher Name: nichts
    abruf(f"{u.kurl}/konto", "POST", {"aktion": "reise_loeschen", "reise": "beispielreise", "verstanden": "ja",
                                      "titel": "Eine andere Reise"}, cookie=u.a_keks)
    assert not konten.reise_vorgemerkt("beispielreise")
    # richtiger Name, Leerraum und Groß-/Kleinschreibung egal
    name = "  " + _titel("beispielreise").upper().replace(" ", "   ") + " "
    abruf(f"{u.kurl}/konto", "POST", {"aktion": "reise_loeschen", "reise": "beispielreise", "verstanden": "ja",
                                      "titel": name}, cookie=u.a_keks)
    assert konten.reise_vorgemerkt("beispielreise")


def test_get_aendert_nie_etwas(zwei, monkeypatch):
    u = zwei()
    monkeypatch.setenv("FR_SPEICHERREISEN", "beispielreise")
    import urllib.parse
    abruf(f"{u.kurl}/konto?aktion=reise_loeschen&reise=beispielreise&verstanden=ja&titel="
          + urllib.parse.quote(_titel("beispielreise")), cookie=u.a_keks)
    assert not konten.reise_vorgemerkt("beispielreise")


def test_mitwirkender_kann_nicht_vormerken(zwei, monkeypatch):
    u = zwei()
    monkeypatch.setenv("FR_SPEICHERREISEN", "beispielreise")
    from test_anmeldung import anmelden
    karl_keks, _ = anmelden(u, KARL)
    abruf(f"{u.kurl}/konto", "POST", {"aktion": "reise_loeschen", "reise": "beispielreise", "verstanden": "ja",
                                      "titel": _titel("beispielreise")}, cookie=karl_keks)
    assert not konten.reise_vorgemerkt("beispielreise")


def test_block_oben_knopf_nur_fuer_organisatorin_und_zurueckholen(zwei, monkeypatch):
    u = zwei()
    monkeypatch.setenv("FR_SPEICHERREISEN", "beispielreise")
    konten.loeschung_vormerken("beispielreise", u.a["id"])
    t = _seite(u, u.a_keks)
    block = t.index('class="vorgemerkt')
    assert block < t.index('class="liste"'), "Block steht oben in Meine Reisen"
    assert re.search(r"\d{1,2}\.\s?\d{1,2}\.\s?\d{4}.{0,40}(UTC|MEZ|MESZ|CET|CEST|\+\d\d)", t[block:block + 2000]), \
        "Datum mit Zeitzone"
    assert 'value="reise_zurueckholen"' in t
    from test_anmeldung import anmelden
    karl_keks, _ = anmelden(u, KARL)
    tk = _seite(u, karl_keks)
    assert 'class="vorgemerkt' in tk and 'value="reise_zurueckholen"' not in tk
    abruf(f"{u.kurl}/konto", "POST", {"aktion": "reise_zurueckholen", "reise": "beispielreise"}, cookie=karl_keks)
    assert konten.reise_vorgemerkt("beispielreise"), "Mitwirkende holen nicht zurück"
    abruf(f"{u.kurl}/konto", "POST", {"aktion": "reise_zurueckholen", "reise": "beispielreise"}, cookie=u.a_keks)
    assert not konten.reise_vorgemerkt("beispielreise")


@pytest.mark.parametrize("reise,ausloeser,andere", [("beispielreise", IDA, KARL), ("stadtwochenende", TOM, None)])
def test_benachrichtigung_nur_an_die_anderen(zwei, monkeypatch, reise, ausloeser, andere):
    u = zwei()
    monkeypatch.setenv("FR_SPEICHERREISEN", ",".join(REISEN))
    if andere is None:   # Lea im Stadtwochenende
        andere = "lea@beispiel.invalid"
        konten.einladen("stadtwochenende", "lea", andere, "mitwirkend", "Lea", "Tom")
        from test_anmeldung import anmelden
        anmelden(u, andere, name="Lea")
        konten.verknuepfen(konten.konto_per_email(andere)["id"], "stadtwochenende", "lea")
    else:
        from test_anmeldung import anmelden
        anmelden(u, andere)
    kid = konten.konto_per_email(ausloeser)["id"]
    andere_kid = konten.konto_per_email(andere)["id"]
    vorher_a, vorher_o = len(_mails_an(u, ausloeser)), len(_mails_an(u, andere))
    import rueckmeldungen as rm
    import anmeldung
    keks = u.a_keks if ausloeser == IDA else u.b_keks
    abruf(f"{u.kurl}/konto", "POST", {"aktion": "reise_loeschen", "reise": reise, "verstanden": "ja",
                                      "titel": _titel(reise)}, cookie=keks)
    assert konten.reise_vorgemerkt(reise)
    assert len(_mails_an(u, andere)) == vorher_o + 1 and len(_mails_an(u, ausloeser)) == vorher_a
    assert _titel(reise) in _mails_an(u, andere)[-1]["text"]
    k_andere = konten.konto(andere_kid)
    assert any(_titel(reise) in anmeldung.meldung_text(m) for m in rm.meldungen_des_kontos(k_andere)), \
        "Meldung auf Mein Konto"
    abruf(f"{u.kurl}/konto", "POST", {"aktion": "reise_zurueckholen", "reise": reise}, cookie=keks)
    assert not konten.reise_vorgemerkt(reise)
    assert len(_mails_an(u, andere)) == vorher_o + 2 and len(_mails_an(u, ausloeser)) == vorher_a
    assert _mails_an(u, andere)[-1]["text"] != _mails_an(u, andere)[-2]["text"]
    assert kid != andere_kid


def test_benachrichtigung_in_der_sprache_des_empfaengers(zwei, monkeypatch):
    u = zwei()
    monkeypatch.setenv("FR_SPEICHERREISEN", "beispielreise")
    from test_anmeldung import anmelden
    anmelden(u, KARL)
    karl = konten.konto_per_email(KARL)
    konten.sprache_setzen(karl["id"], "en")
    abruf(f"{u.kurl}/konto", "POST", {"aktion": "reise_loeschen", "reise": "beispielreise", "verstanden": "ja",
                                      "titel": _titel("beispielreise")}, cookie=u.a_keks)
    import texte
    mail = _mails_an(u, KARL)[-1]
    de = texte.t("de", "konto.reise_loeschen.mail_vorgemerkt_betreff", titel=_titel("beispielreise"))
    en = texte.t("en", "konto.reise_loeschen.mail_vorgemerkt_betreff", titel=_titel("beispielreise"))
    assert de != en and mail["betreff"] == en


def test_mailfehler_vormerken_bleibt_gueltig(zwei, monkeypatch):
    u = zwei()
    monkeypatch.setenv("FR_SPEICHERREISEN", "beispielreise")

    def kaputt(*a, **kw):
        raise OSError("Mailserver erfunden nicht erreichbar")
    monkeypatch.setattr(konten, "mail_senden", kaputt)
    import anmeldung
    k = konten.konto_per_email(IDA)
    from test_anmeldung import anmelden
    anmelden(u, KARL)
    anmeldung.reise_loeschen(k, "beispielreise") if hasattr(anmeldung, "reise_loeschen") else \
        konten.loeschung_vormerken("beispielreise", k["id"])
    assert konten.reise_vorgemerkt("beispielreise")


# ---------- A2a: vorgemerkt heißt unsichtbar (Engine) ----------

def test_reisespeicher_liefert_keine_vorgemerkte(speicher):
    assert speicher.reisen() == REISEN
    konten.loeschung_vormerken("beispielreise", "k-ida")
    assert speicher.reisen() == ["stadtwochenende"]
    konten.loeschung_zurueckholen("beispielreise", "k-ida")
    assert speicher.reisen() == REISEN


def test_konnektor_behandelt_vorgemerkte_wie_unbekannt(zwei):
    import konnektor as kn
    from conftest import meldet
    from test_trennung import reise_werkzeuge
    u = zwei()
    konten.loeschung_vormerken("beispielreise", u.a["id"])
    namen = reise_werkzeuge(u.a)
    assert len(namen) > 20
    fehler = []
    for name in namen:
        text, ist_fehler = kn.frieda_werkzeug(u.a, name, {"reise": "beispielreise", "begriff": "Ida", "id": "T-01"})
        if not (ist_fehler and meldet(text, "konnektor.frieda_werkzeug.1")):
            fehler.append((name, text[:160]))
    assert not fehler, fehler
    text, _ = kn.frieda_werkzeug(u.a, "my_trips", {})
    assert "beispielreise" not in text
    assert not u.schreibweg


def test_schreibweg_lehnt_vorgemerkte_ab(speicher):
    import schreiben as sb
    konten.loeschung_vormerken("beispielreise", "k-ida")
    vorher = _abdruck(speicher, "beispielreise")
    code, _ = sb.anwenden_extern(None, "beispielreise", "knowledge_write",
                                 {"args": {"reise": "beispielreise", "titel": "Neu", "text": "neu"}})
    assert code in (404, 410), code
    assert _abdruck(speicher, "beispielreise") == vorher


def test_rueckmeldung_und_einladung_zu_vorgemerkter_abgelehnt(zwei):
    import rueckmeldungen as rm
    u = zwei()
    konten.loeschung_vormerken("beispielreise", u.a["id"])
    with pytest.raises(konten.KontoFehler):
        konten.einladen("beispielreise", "kim", "kim@beispiel.invalid", "gast", "Kim", "Ida")
    s, _, _ = abruf(f"{u.rurl}/beispielreise/rueckmeldungen", "POST",
                    json_body={"name": "Karl", "text": "Noch eine Idee"})
    assert s in (403, 404, 410)
    assert not (u.o / "eingang.jsonl").exists() or "Noch eine Idee" not in (u.o / "eingang.jsonl").read_text()
    assert rm.zustand("beispielreise") is None or konten.reise_vorgemerkt("beispielreise")


# ---------- A2b: unsichtbar im Betrieb ----------

def test_waechter_schliesst_vorgemerkte_aus(speicher):
    import waechter as wa
    assert wa.alle_reisen() == REISEN
    konten.loeschung_vormerken("stadtwochenende", "k-ida")
    assert wa.alle_reisen() == ["beispielreise"]


def test_veroeffentlichen_kennt_vorgemerkte():
    text = (WURZEL / "betrieb" / "veroeffentlichen.sh").read_text(encoding="utf-8")
    assert "konten.py\" vorgemerkt" in text or "konten.py vorgemerkt" in text, \
        "veroeffentlichen.sh fragt die vorgemerkten Reisen ab"
    assert re.search(r"rm -rf[^\n]*FR_SEITEN", text), "und entfernt ihren Webordner"


# ---------- A3: endgültiges Entfernen ----------

def test_entfernen_raeumt_alles_ab_andere_reise_unveraendert(speicher, monkeypatch):
    import waechter as wa
    t = speicher.t
    andere = _abdruck(speicher, "stadtwochenende")
    _faellig_machen(monkeypatch, "beispielreise")
    assert wa.loeschungen_ausfuehren() == ["beispielreise"]
    assert _abdruck(speicher, "beispielreise") == ([], [])
    assert _abdruck(speicher, "stadtwochenende") == andere
    for weg in (t / "ablage" / "beispielreise", t / "seiten" / "beispielreise",
                t / "_dienst" / "bau" / "reisen" / "beispielreise", t / "_dienst" / "reise-stand" / "beispielreise.gebaut"):
        assert not weg.exists(), weg
    for bleibt in (t / "ablage" / "stadtwochenende" / "belege" / "B-01.pdf", t / "seiten" / "stadtwochenende" / "index.html",
                   t / "_dienst" / "reise-stand" / "stadtwochenende.gebaut"):
        assert bleibt.exists(), bleibt
    assert speicher.pruefen() == []
    assert konten.loeschungen() == [] and konten.loeschprotokoll() == ["beispielreise"]


def test_gemeinsame_ablagedatei_bleibt_bis_zur_letzten_reise(speicher, monkeypatch):
    import hashlib
    import waechter as wa
    datei = speicher.ablage_pfad(hashlib.sha256(PNG).hexdigest())
    assert datei.exists()
    konten.loeschung_vormerken("beispielreise", "k-ida")
    konten.loeschung_vormerken("stadtwochenende", "k-ida")
    jetzt = konten._jetzt()
    with closing(konten.db()) as v, v:   # nur die Beispielreise ist fällig
        v.execute("UPDATE reise_loeschung SET frist = ? WHERE reise = 'beispielreise'", (jetzt - 1,))
    wa.loeschungen_ausfuehren()
    assert datei.exists(), "die andere Reise verweist noch darauf"
    _spaeter(monkeypatch, 15)
    wa.loeschungen_ausfuehren()
    assert not datei.exists()


def test_vor_fristende_bleibt_alles(speicher, monkeypatch):
    import waechter as wa
    vorher = _abdruck(speicher, "beispielreise")
    konten.loeschung_vormerken("beispielreise", "k-ida")
    _spaeter(monkeypatch, 13)
    assert wa.loeschungen_ausfuehren() == []
    assert _abdruck(speicher, "beispielreise") == vorher
    assert (speicher.t / "ablage" / "beispielreise").exists()


def test_inhalt_nirgends_mehr_zu_finden(speicher, monkeypatch):
    import waechter as wa
    speicher.sichern()
    _faellig_machen(monkeypatch, "beispielreise")
    wa.loeschungen_ausfuehren()
    ordner = speicher.pfad().parent
    dateien = [p for p in ordner.rglob("*") if p.is_file() and p.suffix in ("", ".db", ".db-wal", ".db-shm")
               or p.name.endswith(("-wal", "-shm", ".db"))]
    assert any(p.name == "reisen.db" and p.parent.name == "sicherung" for p in dateien), "frischer Schnappschuss"
    for p in dateien:
        assert GEHEIM.encode() not in p.read_bytes(), p


def test_verdichten_ruft_checkpoint_und_vacuum(speicher):
    quelle = inspect.getsource(speicher.verdichten)
    assert "wal_checkpoint(TRUNCATE)" in quelle and "VACUUM" in quelle


def test_loeschprotokoll_entfernt_nach_rueckspielen_erneut(speicher, monkeypatch):
    import waechter as wa
    sicherung = speicher.t / "alt.db"
    with closing(sqlite3.connect(speicher.pfad())) as q, closing(sqlite3.connect(sicherung)) as z:
        q.backup(z)
    (speicher.t / "alt-ablage").mkdir()
    shutil.copytree(speicher.t / "ablage" / "beispielreise", speicher.t / "alt-ablage" / "beispielreise")
    _faellig_machen(monkeypatch, "beispielreise")
    wa.loeschungen_ausfuehren()
    # alte Sicherung zurückspielen
    for endung in ("-wal", "-shm"):
        Path(str(speicher.pfad()) + endung).unlink(missing_ok=True)
    shutil.copy(sicherung, speicher.pfad())
    shutil.copytree(speicher.t / "alt-ablage" / "beispielreise", speicher.t / "ablage" / "beispielreise")
    (speicher.t / "seiten" / "beispielreise").mkdir()
    assert "beispielreise" in [z[0] for z in sqlite3.connect(speicher.pfad()).execute("SELECT DISTINCT reise FROM vorgaenge")]
    wa.loeschungen_ausfuehren()
    assert _abdruck(speicher, "beispielreise") == ([], [])
    assert not (speicher.t / "ablage" / "beispielreise").exists()
    assert not (speicher.t / "seiten" / "beispielreise").exists()


def test_fehler_beim_entfernen_rollt_zurueck(speicher, monkeypatch):
    vorher = (_abdruck(speicher, "beispielreise"), _abdruck(speicher, "stadtwochenende"))
    echt = speicher._db_ausnahme

    def mit_fehler(*a, **kw):
        v = echt(*a, **kw)

        def wache(aktion, a1, *rest):
            if aktion == sqlite3.SQLITE_DELETE and a1 == "versionen":
                return sqlite3.SQLITE_DENY   # mitten in der Transaktion: Löschen der Versionen scheitert
            return sqlite3.SQLITE_OK
        v.set_authorizer(wache)
        return v
    monkeypatch.setattr(speicher, "_db_ausnahme", mit_fehler)
    with pytest.raises(sqlite3.DatabaseError):
        speicher.reise_entfernen("beispielreise")
    assert (_abdruck(speicher, "beispielreise"), _abdruck(speicher, "stadtwochenende")) == vorher
    with closing(sqlite3.connect(speicher.pfad())) as v:
        trigger = {z[0] for z in v.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
    assert trigger == {"vorgaenge_kein_update", "vorgaenge_kein_delete", "versionen_kein_update",
                       "versionen_kein_delete"}
    assert speicher.pruefen() == []


def test_nach_entfernen_sind_alle_trigger_da_und_nur_anhaengen_gilt(speicher):
    speicher.reise_entfernen("beispielreise")
    with closing(sqlite3.connect(speicher.pfad())) as v:
        trigger = {z[0] for z in v.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
        assert len(trigger) == 4
        with pytest.raises(sqlite3.DatabaseError):
            v.execute("DELETE FROM versionen WHERE reise = 'stadtwochenende'")
    with closing(speicher.db()) as v:
        with pytest.raises(sqlite3.DatabaseError):
            v.execute("DELETE FROM vorgaenge WHERE reise = 'stadtwochenende'")


def test_quelltext_nur_zwei_funktionen_nutzen_die_ausnahme():
    import reisespeicher as rs
    quelle = inspect.getsource(rs)
    nutzer = set()
    for name, f in inspect.getmembers(rs, inspect.isfunction):
        if f.__module__ == rs.__name__ and name != "_db_ausnahme" and "_db_ausnahme" in inspect.getsource(f):
            nutzer.add(name)
    assert nutzer == {"reise_entfernen", "namen_ersetzen"}, nutzer
    for f in (rs.reise_entfernen, rs.namen_ersetzen):
        assert "BEGIN IMMEDIATE" in inspect.getsource(f) or "_ausnahme_transaktion" in inspect.getsource(f)
    assert "SQLITE_DELETE" in quelle and rs.VERBOTEN >= {sqlite3.SQLITE_DROP_TRIGGER, sqlite3.SQLITE_DROP_TABLE}


def test_pruefen_rot_bricht_lauf_ab_und_loescht_keine_weitere(speicher, monkeypatch):
    import waechter as wa
    konten.loeschung_vormerken("beispielreise", "k-ida")
    konten.loeschung_vormerken("stadtwochenende", "k-ida")
    _spaeter(monkeypatch, 15)
    monkeypatch.setattr(speicher, "pruefen", lambda reise=None: ["erfundene Abweichung"])
    assert hasattr(wa, "loeschungen_ausfuehren")
    with pytest.raises(Exception):
        wa.loeschungen_ausfuehren()
    assert len(konten.loeschungen()) + len(konten.loeschprotokoll()) == 2
    assert sum(1 for r in REISEN if _abdruck(speicher, r) != ([], [])) >= 1


def test_waechter_sh_ruft_den_loeschlauf():
    text = (WURZEL / "betrieb" / "waechter.sh").read_text(encoding="utf-8")
    assert re.search(r"waechter\.py\"? loeschen", text)
