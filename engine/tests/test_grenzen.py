"""Mengenbegrenzung je Konto für die öffentliche Alpha (#380, Meilenstein M5a): angelegte Reisen (FR_GRENZE_REISEN,
Vorgabe 10) und schreibende Werkzeugaufrufe im Konnektor je Stunde (FR_GRENZE_SCHREIBEN, Vorgabe 300). Werte aus der
Instanz, Betreiber ausgenommen, Ablehnung freundlich mit Wartezeit, ohne Alarm. Alle Daten sind erfunden."""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import anmeldung  # noqa: E402
import instanz  # noqa: E402
import konnektor as kn  # noqa: E402
import konten  # noqa: E402
import texte  # noqa: E402
from test_anmeldung import anmelden, welt  # noqa: E402,F401  (welt: Fixture)
from conftest import meldet  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
IDA, BEN, MO = "ida@beispiel.invalid", "ben@beispiel.invalid", "mo@beispiel.invalid"
SCHREIBEND = set(kn.SCHREIB_WERKZEUGE) | set(kn.SCHREIB_AKTION) | set(kn.ONTOLOGIE_WERKZEUGE)


def konto(u, email, name, reise=True):
    if reise:
        konten.einladen("beispielreise", "ida", email, "organisator", name, name)
    anmelden(u, email, name)
    return konten.konto_per_email(email)


def schreiben(k, n=1):
    return [kn.frieda_werkzeug(k, "aufgabe_anlegen", {"titel": f"Karten kaufen {i}"}) for i in range(n)]


def anlegen(k, titel, von="2027-02-06", bis="2027-02-13"):
    return kn.frieda_werkzeug(konten.konto(k["id"]), "reise_anlegen", {"titel": titel, "von": von, "bis": bis})


# ---------- AC-8: Grenzwerte aus der Instanz ----------

def test_grenzwerte_vorgabe_und_instanz(monkeypatch, tmp_path):
    assert instanz.grenze_reisen() == 10 and instanz.grenze_schreiben() == 300
    monkeypatch.setenv("FR_GRENZE_REISEN", "4")
    monkeypatch.setenv("FR_GRENZE_SCHREIBEN", "50")
    assert instanz.grenze_reisen() == 4 and instanz.grenze_schreiben() == 50
    for falsch in ("abc", "0", "-3", "2.5", " "):
        monkeypatch.setenv("FR_GRENZE_REISEN", falsch)
        monkeypatch.setenv("FR_GRENZE_SCHREIBEN", falsch)
        assert instanz.grenze_reisen() == 10 and instanz.grenze_schreiben() == 300, falsch
    monkeypatch.delenv("FR_GRENZE_REISEN")
    monkeypatch.delenv("FR_GRENZE_SCHREIBEN")
    datei = tmp_path / "einstellungen.env"
    datei.write_text("FR_GRENZE_REISEN=3\nFR_GRENZE_SCHREIBEN=\"20\"\n", encoding="utf-8")
    monkeypatch.setenv("FR_EINSTELLUNGEN", str(datei))
    assert instanz.grenze_reisen() == 3 and instanz.grenze_schreiben() == 20


# ---------- AC-9: Schreibgrenze je Konto und Stunde ----------

def test_schreibgrenze_je_konto_und_stunde(welt, monkeypatch):
    u = welt()
    k = konto(u, IDA, "Ida")
    monkeypatch.setenv("FR_GRENZE_SCHREIBEN", "3")
    # fremde Reise: Fehler der Mitgliedschaft, verbraucht keinen Zähler
    text, fehler = kn.frieda_werkzeug(k, "aufgabe_anlegen", {"reise": "fremdreise", "titel": "x"})
    assert fehler and meldet(text, "konnektor.frieda_werkzeug.1")
    for text, fehler in schreiben(k, 3):
        assert not fehler, text
    vorher = len(u.schreibweg), sorted(p.name for p in u.o.rglob("*"))
    aufgaben_vorher = (u.o / "aufgaben.json").read_text(encoding="utf-8") if (u.o / "aufgaben.json").exists() else ""
    text, fehler = schreiben(k)[0]
    assert fehler and meldet(text, "konnektor.grenze.schreiben"), text
    assert re.search(r"\d+", text), text                                   # nennt die Wartezeit in Minuten
    assert (len(u.schreibweg), sorted(p.name for p in u.o.rglob("*"))) == vorher
    assert ((u.o / "aufgaben.json").read_text(encoding="utf-8") if (u.o / "aufgaben.json").exists() else "") == aufgaben_vorher
    # lesende und Konto-Werkzeuge bleiben frei
    for name, args in (("ueberblick", {}), ("suche", {"begriff": "Bastei"}), ("meine_reisen", {}),
                       ("sprache_setzen", {"sprache": "de"})):
        text, fehler = kn.frieda_werkzeug(k, name, args)
        assert not fehler, (name, text)
    # nach Ablauf des Fensters geht es wieder
    jetzt = konten._jetzt()
    monkeypatch.setattr(konten, "_jetzt", lambda: jetzt + 3601)
    text, fehler = schreiben(k)[0]
    assert not fehler, text
    # ein anderes Konto ist nicht betroffen
    monkeypatch.setattr(konten, "_jetzt", lambda: jetzt)
    konten.einladen("beispielreise", "karl", "karl@beispiel.invalid", "mitwirkend", "Karl", "Ida")
    anmelden(u, "karl@beispiel.invalid")
    karl = konten.konto_per_email("karl@beispiel.invalid")
    text, fehler = schreiben(karl)[0]
    assert not fehler, text


# ---------- AC-10: Reisegrenze je Konto ----------

def test_reisegrenze_je_konto(welt, monkeypatch):
    u = welt()
    monkeypatch.setenv("FR_GRENZE_REISEN", "2")
    ben = konto(u, BEN, "Ben", reise=False)
    konten.freischalten(ben["id"])
    text, fehler = anlegen(ben, "Winterwoche eins")
    assert not fehler, text
    text, fehler = anlegen(ben, "Fehlerhafte Reise", von="2027-02-13", bis="2027-02-06")   # Fehler zählt nicht
    assert fehler and not meldet(text, "konnektor.grenze.reisen"), text
    text, fehler = anlegen(ben, "Winterwoche zwei")
    assert not fehler, text
    text, fehler = anlegen(ben, "Winterwoche drei")
    assert fehler and meldet(text, "konnektor.grenze.reisen") and "2" in text, text
    assert "winterwoche-drei" not in (konten.pfad().parent / "neu" / "auftraege.jsonl").read_text(encoding="utf-8")
    mo = konto(u, MO, "Mo", reise=False)
    konten.freischalten(mo["id"])
    text, fehler = anlegen(mo, "Sommerwoche")
    assert not fehler, text


# ---------- AC-11: Betreiber ausgenommen ----------

def test_betreiber_ausgenommen(welt, monkeypatch):
    u = welt()
    monkeypatch.setenv("FR_GRENZE_REISEN", "1")
    monkeypatch.setenv("FR_GRENZE_SCHREIBEN", "1")
    k = konto(u, IDA, "Ida")
    konten.recht_setzen(k["id"], "betreiber")
    konten.freischalten(k["id"])
    k = konten.konto(k["id"])
    for text, fehler in schreiben(k, 3):
        assert not fehler, text
    for titel in ("Herbstwoche eins", "Herbstwoche zwei"):
        text, fehler = anlegen(k, titel)
        assert not fehler, text


# ---------- AC-12: Protokollzeile, Texte in allen Sprachen, kein Alarm ----------

def test_ablehnung_protokoll_texte_ohne_alarm(welt, monkeypatch, capsys):
    u = welt()
    gemeldet = []
    monkeypatch.setattr(anmeldung, "betreiber_melden", lambda *a, **kw: gemeldet.append(a))
    monkeypatch.setenv("FR_GRENZE_SCHREIBEN", "1")
    monkeypatch.setenv("FR_GRENZE_REISEN", "1")
    k = konto(u, IDA, "Ida")
    monkeypatch.setattr(konten, "mail_senden", lambda *a, **kw: gemeldet.append(a))   # erst nach dem Anmelden
    konten.freischalten(k["id"])
    schreiben(k)
    capsys.readouterr()
    text, fehler = schreiben(k)[0]
    assert fehler and meldet(text, "konnektor.grenze.schreiben")
    anlegen(k, "Herbstwoche eins")
    text, fehler = anlegen(k, "Herbstwoche zwei")
    assert fehler and meldet(text, "konnektor.grenze.reisen")
    fehlerausgabe = capsys.readouterr().err
    zeilen = [z for z in fehlerausgabe.splitlines() if z.startswith("grenze ")]
    assert any("schreiben" in z for z in zeilen) and any("reisen" in z for z in zeilen), fehlerausgabe
    assert all(k["id"] in z and IDA not in z and "Ida" not in z for z in zeilen), zeilen
    assert not gemeldet
    for sprache in texte.SPRACHEN:
        for schluessel in ("konnektor.grenze.schreiben", "konnektor.grenze.reisen"):
            assert texte.t(sprache, schluessel, minuten=5, grenze=2) != schluessel, (sprache, schluessel)


# ---------- AC-13: „schreibend“ aus der vorhandenen Einteilung ----------

def test_schreibend_aus_vorhandener_einteilung(welt, monkeypatch):
    u = welt()
    k = konto(u, IDA, "Ida")
    gezaehlt = []
    monkeypatch.setattr(kn, "werkzeug", lambda zugang, name, args: ("ok", False))
    monkeypatch.setattr(konten, "schreibgrenze", lambda k_: None)
    monkeypatch.setattr(konten, "schreiben_vormerken", lambda k_: gezaehlt.append(k_))
    namen = {w["name"] for w in kn.frieda_werkzeuge(k) if "reise" in w["inputSchema"].get("properties", {})} | SCHREIBEND
    for name in sorted(namen):
        gezaehlt.clear()
        kn.frieda_werkzeug(k, name, {"reise": "beispielreise"})
        assert len(gezaehlt) == (1 if name in SCHREIBEND else 0), name


# ---------- AC-14: Doku der Instanz ----------

def test_einstellungen_beispiel_nennt_grenzen():
    for datei in ("betrieb/einstellungen.beispiel", "docs/betrieb.md"):
        text = (WURZEL / datei).read_text(encoding="utf-8")
        assert re.search(r"FR_GRENZE_REISEN\D{0,80}10", text), datei
        assert re.search(r"FR_GRENZE_SCHREIBEN\D{0,80}300", text), datei


def test_konten_doku_nennt_grenzen_und_seitenlink():
    text = (WURZEL / "docs" / "konten.md").read_text(encoding="utf-8")
    assert "FR_GRENZE_REISEN" in text and "FR_GRENZE_SCHREIBEN" in text and "#421" in text


# ---------- #534: Tagesgrenze der Warteliste (AC-23) ----------

def test_doku_nennt_tagesgrenze_der_warteliste():
    for datei in ("betrieb/einstellungen.beispiel", "docs/betrieb.md", "docs/konten.md"):
        text = (WURZEL / datei).read_text(encoding="utf-8")
        assert re.search(r"FR_GRENZE_WARTELISTE_TAG\D{0,80}20", text), datei
