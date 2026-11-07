"""Tests für die Warteliste mit Freigabe (#382, Meilenstein M5a, Spec docs/specs/betrieb/warteliste-382.md).
Alle Adressen sind erfunden. Mails gehen über FR_MAIL_DATEI, jeder Test hat eine eigene Kontendatenbank."""
import json
import re
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import konten  # noqa: E402
import texte  # noqa: E402
from conftest import meldet  # noqa: E402
from test_anmeldung import BASIS, abruf, anmelden as seite_anmelden, welt  # noqa: E402,F401  (welt: Fixture)

IDA, KARL, MO, LEA = "ida@beispiel.invalid", "karl@beispiel.invalid", "mo@beispiel.invalid", "lea@beispiel.invalid"
TAG = 24 * 3600


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    monkeypatch.setenv("FR_KONTEN", str(tmp_path / "konten"))
    monkeypatch.setenv("FR_MAIL_DATEI", str(tmp_path / "mails.jsonl"))
    monkeypatch.setenv("FR_BASIS", BASIS)
    uhr = {"t": 1_800_000_000.0}
    monkeypatch.setattr(konten, "_jetzt", lambda: uhr["t"])
    return {"tmp": tmp_path, "uhr": uhr}


def mails(pfad, an=None):
    p = Path(pfad)
    alle = [json.loads(z) for z in p.read_text().splitlines()] if p.exists() else []
    return [m for m in alle if an is None or m["an"] == an]


def bestaetigungswort(m):
    return re.search(r"/warteliste/bestaetigen/([A-Za-z0-9_-]+)", m["text"]).group(1)


def zeilen():
    with closing(sqlite3.connect(konten.pfad())) as v:
        return v.execute("SELECT * FROM warteliste").fetchall()


def eintragen_und_bestaetigen(umgebung, adresse, **kw):
    konten.warteliste_eintragen(adresse, **kw)
    wort = bestaetigungswort(mails(umgebung["tmp"] / "mails.jsonl", adresse)[-1])
    return konten.warteliste_bestaetigen(wort)


# ---------------------------------------------------------------- Modell: Eintrag (AC-1, AC-2)

def test_eintrag_legt_zeile_an_und_schickt_mail_mit_link(umgebung):
    konten.warteliste_eintragen("  Ida@Beispiel.INVALID ", sprache="de")
    m = mails(umgebung["tmp"] / "mails.jsonl", IDA)
    assert len(m) == 1 and meldet(m[0]["betreff"], "mail.warteliste.betreff")
    assert f"{BASIS}/warteliste/bestaetigen/" in m[0]["text"] and meldet(m[0]["text"], "mail.warteliste.zeile_link")
    assert len(zeilen()) == 1


def test_bestaetigungswort_liegt_nur_als_hash_in_der_datenbank(umgebung):
    konten.warteliste_eintragen(IDA)
    wort = bestaetigungswort(mails(umgebung["tmp"] / "mails.jsonl", IDA)[0])
    with closing(sqlite3.connect(konten.pfad())) as v:
        inhalt = "".join(str(x) for z in v.execute("SELECT * FROM warteliste") for x in z)
    assert wort not in inhalt and len(wort) >= 20


def test_ungueltige_adresse_wird_abgewiesen_und_nichts_gespeichert(umgebung):
    for roh in ("keine-adresse", "", None, "a@b"):
        with pytest.raises(konten.KontoFehler) as f:
            konten.warteliste_eintragen(roh)
        assert meldet(f.value.text("de"), "konto.fehler.keine_adresse")
    assert zeilen() == [] and mails(umgebung["tmp"] / "mails.jsonl") == []


def test_doppelter_eintrag_kein_zweiter_datensatz_mail_nur_solange_unbestaetigt(umgebung):
    mf = umgebung["tmp"] / "mails.jsonl"
    konten.warteliste_eintragen(IDA)
    konten.warteliste_eintragen(IDA.upper())                    # erneut: gleiche Zeile, Mail geht noch einmal
    assert len(zeilen()) == 1 and len(mails(mf, IDA)) == 2
    wort = bestaetigungswort(mails(mf, IDA)[-1])
    konten.warteliste_bestaetigen(wort)
    konten.warteliste_eintragen(IDA)                            # bestätigt: keine Mail mehr, keine Fehlermeldung
    assert len(zeilen()) == 1 and len(mails(mf, IDA)) == 2


def test_antwort_ist_fuer_jeden_stand_gleich(umgebung):
    mf = umgebung["tmp"] / "mails.jsonl"
    konten.code_anfordern(KARL)
    code = re.search(r"(\d{3}) (\d{3})", mails(mf, KARL)[-1]["text"]).expand(r"\1\2")
    konten.anmelden(KARL, code, name="Karl")                    # Karl hat schon ein Konto
    eintragen_und_bestaetigen(umgebung, IDA)
    konten.freigeben(IDA)                                       # Ida ist freigegeben
    # keine Ausnahme, kein Rückgabewert, der den Stand verrät
    ergebnisse = [konten.warteliste_eintragen(a) for a in (MO, MO, IDA, KARL)]
    assert ergebnisse == [None] * 4
    assert len(mails(mf, KARL)) == 2      # Anmeldecode und Bestätigung: Konten werden wie alle eingetragen (PO, 7.11.2026)
    assert len(mails(mf, IDA)) == 2      # Eintrag, Freigabe, nichts Neues beim erneuten Eintragen


# ---------------------------------------------------------------- Modell: Bestätigung (AC-3)

def test_bestaetigung_einmal_und_nur_sieben_tage(umgebung):
    mf = umgebung["tmp"] / "mails.jsonl"
    konten.warteliste_eintragen(IDA)
    wort = bestaetigungswort(mails(mf, IDA)[0])
    assert konten.warteliste() == []                            # noch nicht bestätigt: für den Betreiber unsichtbar
    e = konten.warteliste_bestaetigen(wort)
    assert e["email"] == IDA
    assert [z["email"] for z in konten.warteliste()] == [IDA]
    with pytest.raises(konten.KontoFehler) as f:
        konten.warteliste_bestaetigen(wort)                     # zweites Mal
    assert meldet(f.value.text("de"), "konto.fehler.warteliste_link")
    konten.warteliste_eintragen(MO)
    wort2 = bestaetigungswort(mails(mf, MO)[0])
    umgebung["uhr"]["t"] += 8 * TAG
    with pytest.raises(konten.KontoFehler):
        konten.warteliste_bestaetigen(wort2)                    # abgelaufen
    with pytest.raises(konten.KontoFehler):
        konten.warteliste_bestaetigen("gibt-es-nicht")


def test_liste_zeigt_aelteste_zuerst_und_zaehlt_unbestaetigte(umgebung):
    eintragen_und_bestaetigen(umgebung, MO)
    umgebung["uhr"]["t"] += 60
    eintragen_und_bestaetigen(umgebung, IDA)
    konten.warteliste_eintragen(KARL)                           # unbestätigt
    assert [z["email"] for z in konten.warteliste()] == [MO, IDA]
    assert konten.warteliste_unbestaetigt() == 1


# ---------------------------------------------------------------- Modell: Schutz (AC-4)

def test_grenze_je_adresse_drei_mails_in_fuenfzehn_minuten(umgebung):
    for _ in range(3):
        konten.warteliste_eintragen(IDA)
    with pytest.raises(konten.KontoFehler) as f:
        konten.warteliste_eintragen(IDA)
    assert meldet(f.value.text("de"), "konto.fehler.zu_viele_codes")
    assert len(mails(umgebung["tmp"] / "mails.jsonl", IDA)) == 3
    umgebung["uhr"]["t"] += 16 * 60
    konten.warteliste_eintragen(IDA)                            # nach 15 Minuten wieder möglich


def test_grenze_je_ip_zehn_eintraege_in_der_stunde(umgebung):
    for i in range(10):
        konten.warteliste_eintragen(f"x{i}@beispiel.invalid", ip="203.0.113.7")
    with pytest.raises(konten.KontoFehler) as f:
        konten.warteliste_eintragen("x10@beispiel.invalid", ip="203.0.113.7")
    assert meldet(f.value.text("de"), "konto.fehler.zu_viele_codes")
    konten.warteliste_eintragen("x10@beispiel.invalid", ip="203.0.113.8")   # andere IP geht


def test_obergrenze_unbestaetigter_eintraege(umgebung, monkeypatch):
    monkeypatch.setattr(konten, "WARTELISTE_MAX_UNBESTAETIGT", 2)
    konten.warteliste_eintragen(IDA)
    konten.warteliste_eintragen(KARL)
    with pytest.raises(konten.KontoFehler) as f:
        konten.warteliste_eintragen(MO)
    assert meldet(f.value.text("de"), "konto.fehler.warteliste_voll")
    assert len(zeilen()) == 2
    konten.warteliste_eintragen(IDA)                            # ein vorhandener Eintrag bekommt weiter seine Mail


def test_unbestaetigte_eintraege_verfallen_nach_sieben_tagen(umgebung):
    konten.warteliste_eintragen(IDA)
    eintragen_und_bestaetigen(umgebung, KARL)
    umgebung["uhr"]["t"] += 8 * TAG
    konten.warteliste_eintragen(MO)                             # Aufräumen beim nächsten Eintrag
    adressen = {z[0] for z in sqlite3.connect(konten.pfad()).execute("SELECT email FROM warteliste")}
    assert adressen == {KARL, MO}                               # Ida (unbestätigt, alt) weg, Karl (bestätigt) bleibt


def test_ohne_mail_einrichtung_wird_nichts_gespeichert(umgebung, monkeypatch):
    monkeypatch.delenv("FR_MAIL_DATEI")
    monkeypatch.delenv("FR_SMTP_HOST", raising=False)
    monkeypatch.delenv("FR_ABSENDER", raising=False)
    with pytest.raises(konten.KontoFehler) as f:
        konten.warteliste_eintragen(IDA)
    assert meldet(f.value.text("de"), "konto.fehler.mail_nicht_eingerichtet")
    assert zeilen() == []


# ---------------------------------------------------------------- Modell: Freigabe (AC-5, AC-6)

def test_nur_bestaetigte_eintraege_lassen_sich_freigeben(umgebung):
    with pytest.raises(konten.KontoFehler) as f:
        konten.freigeben(IDA)                                   # unbekannt
    assert meldet(f.value.text("de"), "konto.fehler.warteliste_nicht_bestaetigt")
    konten.warteliste_eintragen(IDA)
    with pytest.raises(konten.KontoFehler):
        konten.freigeben(IDA)                                   # eingetragen, aber nicht bestätigt


def test_freigabe_mit_konto_setzt_das_recht_sofort_und_schickt_mail_in_der_sprache_des_eintrags(umgebung):
    mf = umgebung["tmp"] / "mails.jsonl"
    konten.code_anfordern(IDA)
    code = re.search(r"(\d{3}) (\d{3})", mails(mf, IDA)[-1]["text"]).expand(r"\1\2")
    _, k = konten.anmelden(IDA, code, name="Ida")
    assert not konten.recht(konten.konto(k["id"]), "reise_anlegen")
    eintragen_und_bestaetigen(umgebung, IDA, sprache="en")
    assert konten.freigeben(IDA) is True
    assert konten.recht(konten.konto(k["id"]), "reise_anlegen")
    m = mails(mf, IDA)[-1]
    assert meldet(m["betreff"], "mail.freigabe.betreff", "en") and meldet(m["text"], "mail.freigabe.zeile_anmelden", "en")
    assert f"{BASIS}/anmelden" in m["text"] and meldet(m["text"], "mail.freigabe.zeile_claude", "en")
    assert konten.warteliste() == []                            # nicht mehr in der Liste der Wartenden


def test_freigabe_ohne_konto_gilt_beim_ersten_anmelden(umgebung):
    mf = umgebung["tmp"] / "mails.jsonl"
    eintragen_und_bestaetigen(umgebung, LEA, sprache="de")
    konten.freigeben(LEA)
    assert konten.konto_per_email(LEA) is None
    konten.code_anfordern(LEA)
    code = re.search(r"(\d{3}) (\d{3})", mails(mf, LEA)[-1]["text"]).expand(r"\1\2")
    _, k = konten.anmelden(LEA, code, name="Lea")
    assert konten.recht(konten.konto(k["id"]), "reise_anlegen")
    # wer nie auf der Liste stand, bekommt das Recht nicht
    konten.code_anfordern(MO)
    code = re.search(r"(\d{3}) (\d{3})", mails(mf, MO)[-1]["text"]).expand(r"\1\2")
    _, k2 = konten.anmelden(MO, code, name="Mo")
    assert not konten.recht(konten.konto(k2["id"]), "reise_anlegen")


def test_zweite_freigabe_aendert_nichts_und_schickt_keine_mail(umgebung):
    mf = umgebung["tmp"] / "mails.jsonl"
    eintragen_und_bestaetigen(umgebung, IDA)
    assert konten.freigeben(IDA) is True
    n = len(mails(mf, IDA))
    assert konten.freigeben(IDA) is False
    assert len(mails(mf, IDA)) == n


def test_scheitert_die_mail_der_freigabe_bleibt_der_eintrag_wartend(umgebung, monkeypatch):
    mf = umgebung["tmp"] / "mails.jsonl"
    konten.code_anfordern(IDA)
    code = re.search(r"(\d{3}) (\d{3})", mails(mf, IDA)[-1]["text"]).expand(r"\1\2")
    _, k = konten.anmelden(IDA, code, name="Ida")
    eintragen_und_bestaetigen(umgebung, IDA)
    echt = konten.mail_senden

    def kaputt(*a):
        raise konten.KontoFehler("konto.fehler.mail_fehlgeschlagen")
    monkeypatch.setattr(konten, "mail_senden", kaputt)
    with pytest.raises(konten.KontoFehler) as f:
        konten.freigeben(IDA)
    assert meldet(f.value.text("de"), "konto.fehler.mail_fehlgeschlagen")
    assert [z["email"] for z in konten.warteliste()] == [IDA]       # nicht stumm freigegeben
    assert not konten.recht(konten.konto(k["id"]), "reise_anlegen")
    n = len(mails(mf, IDA))
    monkeypatch.setattr(konten, "mail_senden", echt)
    assert konten.freigeben(IDA) is True                            # zweiter Versuch: Mail und Recht
    assert len(mails(mf, IDA)) == n + 1 and meldet(mails(mf, IDA)[-1]["betreff"], "mail.freigabe.betreff")
    assert konten.recht(konten.konto(k["id"]), "reise_anlegen") and konten.warteliste() == []


# ---------------------------------------------------------------- Befehle

def test_befehle_warteliste_und_freigeben(umgebung, capsys):
    eintragen_und_bestaetigen(umgebung, IDA)
    konten.warteliste_eintragen(KARL)
    assert konten.main(["warteliste"]) == 0
    aus = capsys.readouterr().out
    assert IDA in aus and KARL not in aus and "1" in aus        # bestätigt gelistet, unbestätigte nur als Zahl
    assert konten.main(["freigeben", IDA]) == 0
    assert konten.main(["warteliste"]) == 0 and IDA not in capsys.readouterr().out
    assert konten.main(["freigeben", KARL]) == 2                # nicht bestätigt
    assert "ERROR" in capsys.readouterr().out
    assert konten.main(["freigeben"]) == 1                      # falscher Aufruf: Hilfe


# ---------------------------------------------------------------- Seiten (AC-1 bis AC-6)

def betreiber_und_nutzer(u):
    ida, _ = seite_anmelden(u, IDA, "Ida")
    konten.recht_setzen(konten.konto_per_email(IDA)["id"], "betreiber")
    mo, _ = seite_anmelden(u, MO, "Mo")
    return ida, mo


def test_seite_zeigt_formular_und_voraussetzung(welt):
    u = welt()
    s, _, t = abruf(f"{u.kurl}/warteliste")
    assert s == 200 and meldet(t, "warteliste.titel") and meldet(t, "warteliste.voraussetzung") and 'name="email"' in t


def test_eintrag_ueber_die_seite_antwort_ist_immer_gleich(welt):
    u = welt()
    seite_anmelden(u, KARL, "Karl")                              # Karl hat ein Konto
    antworten = []
    for adresse in (LEA, LEA, KARL):
        s, _, t = abruf(f"{u.kurl}/warteliste", "POST", {"email": adresse})
        assert s == 200 and meldet(t, "warteliste.gesendet")
        antworten.append(re.sub(r"\s+", " ", re.sub(r"(?i)" + re.escape(adresse), "X", t)))
    assert antworten[0] == antworten[1] == antworten[2]
    # ungültig: verständliche Ablehnung, nichts gespeichert
    s, _, t = abruf(f"{u.kurl}/warteliste", "POST", {"email": "unsinn"})
    assert meldet(t, "konto.fehler.keine_adresse") and not meldet(t, "warteliste.gesendet")
    assert {z[0] for z in sqlite3.connect(konten.pfad()).execute("SELECT email FROM warteliste")} == {LEA, KARL}


def test_falsche_herkunft_ist_403(welt):
    u = welt()
    konten.db().close()                                          # Datenbank anlegen, damit die Prüfung unten lesen kann
    assert abruf(f"{u.kurl}/warteliste", "POST", {"email": LEA}, origin="https://boese.invalid")[0] == 403
    assert abruf(f"{u.kurl}/warteliste/bestaetigen/abc", "POST", {}, origin="https://boese.invalid")[0] == 403
    assert not sqlite3.connect(konten.pfad()).execute("SELECT 1 FROM warteliste").fetchall()


def test_link_bestaetigt_erst_per_knopf_und_meldet_den_betreibern_genau_einmal(welt):
    u = welt()
    betreiber_und_nutzer(u)
    abruf(f"{u.kurl}/warteliste", "POST", {"email": LEA})
    wort = bestaetigungswort(mails(u.mails, LEA)[-1])
    meldungen = konten.pfad().parent / "neu" / "meldungen.jsonl"
    vorher = len(meldungen.read_text().splitlines()) if meldungen.exists() else 0
    s, _, t = abruf(f"{u.kurl}/warteliste/bestaetigen/{wort}")  # GET (Mailprogramm-Vorabruf): nur Knopf
    assert s == 200 and "<form" in t and meldet(t, "warteliste.bestaetigen_knopf")
    assert konten.warteliste() == []
    s, _, t = abruf(f"{u.kurl}/warteliste/bestaetigen/{wort}", "POST", {})
    assert s == 200 and meldet(t, "warteliste.bestaetigt")
    assert [z["email"] for z in konten.warteliste()] == [LEA]
    neu = [json.loads(z) for z in meldungen.read_text().splitlines()][vorher:]
    assert len(neu) == 1 and neu[0]["an"] == ["Ida"] and neu[0]["art"] == "anfrage_warteliste" and LEA in neu[0]["text"]
    s, _, t = abruf(f"{u.kurl}/warteliste/bestaetigen/{wort}", "POST", {})   # Wiederholung
    assert meldet(t, "warteliste.link_ungueltig")
    assert len(meldungen.read_text().splitlines()) == vorher + 1


def test_unbekanntes_wort_zeigt_seite_link_gilt_nicht_mehr(welt):
    u = welt()
    s, _, t = abruf(f"{u.kurl}/warteliste/bestaetigen/gibtesnicht")
    assert s == 404 and meldet(t, "warteliste.link_ungueltig") and "/warteliste" in t


def test_abschnitt_auf_konto_nur_fuer_betreiber_und_freigeben_ohne_recht_abgelehnt(welt):
    u = welt()
    ida, mo = betreiber_und_nutzer(u)
    abruf(f"{u.kurl}/warteliste", "POST", {"email": LEA})
    abruf(f"{u.kurl}/warteliste/bestaetigen/{bestaetigungswort(mails(u.mails, LEA)[-1])}", "POST", {})
    s, _, t = abruf(f"{u.kurl}/konto", cookie=ida)
    assert meldet(t, "konto.warteliste.titel") and LEA in t
    s, _, t = abruf(f"{u.kurl}/konto", cookie=mo)
    assert not meldet(t, "konto.warteliste.titel") and LEA not in t
    felder = {"aktion": "warteliste_freigeben", "wer": LEA}
    assert abruf(f"{u.kurl}/konto", "POST", felder, cookie=mo)[0] == 400
    assert konten.warteliste() and mails(u.mails, LEA)[-1]["betreff"] == mails(u.mails, LEA)[0]["betreff"]
    assert abruf(f"{u.kurl}/konto", "POST", felder, cookie=ida)[0] in (200, 303)
    assert konten.warteliste() == []
    assert meldet(mails(u.mails, LEA)[-1]["betreff"], "mail.freigabe.betreff")


# ---------------------------------------------------------------- Betrieb und Texte

def test_nginx_vorlage_enthaelt_die_neuen_pfade():
    inc = (Path(__file__).resolve().parents[2] / "betrieb" / "vorlagen" / "nginx-konnektor-orte.inc").read_text()
    assert re.search(r"location\s+(=|\^~)\s+/warteliste", inc)
    assert "/warteliste/bestaetigen" in inc or re.search(r"location\s+\^~\s+/warteliste/", inc)


@pytest.mark.parametrize("schluessel", [
    "mail.warteliste.betreff", "mail.warteliste.zeile_link", "mail.freigabe.betreff", "mail.freigabe.zeile_anmelden",
    "mail.freigabe.zeile_claude", "warteliste.titel", "warteliste.voraussetzung", "warteliste.gesendet",
    "warteliste.bestaetigen_knopf", "warteliste.bestaetigt", "warteliste.link_ungueltig", "konto.warteliste.titel",
    "konto.fehler.warteliste_voll", "konto.fehler.warteliste_link", "konto.fehler.warteliste_nicht_bestaetigt",
    "konto.betreiber.warteliste"])
def test_texte_in_allen_sprachen(schluessel):
    for sprache in texte.SPRACHEN:
        assert texte.t(sprache, schluessel) != schluessel, f"{schluessel} fehlt in {sprache}"
