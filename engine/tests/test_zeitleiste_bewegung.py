"""Zeitleiste einer Bewegung (#665, Spec docs/specs/oberflaeche/zeitleiste-bewegung-665.md): Zeitpunkt-Merkmale ohne Rolle am
Ding, die Eigenschaften „erinnern“ und „bei“ der Merkmal-Definition, Wächter und Kalender, die Seitendaten der Zeitleiste und die
Seite im Browser. Gegen beide Beispielreisen (Stadtwochenende mit Bahn und Buchung, Wanderung als Gegenprobe) und erfundene
Abwandlungen davon."""
import datetime
import functools
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import kalender  # noqa: E402
import konnektor as kn  # noqa: E402
import neu  # noqa: E402
import schnittstelle  # noqa: E402
import schreiben as sb  # noqa: E402
import texte  # noqa: E402
import waechter as wa  # noqa: E402
from conftest import meldet  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402
from test_schreiben import IDA, arten_auf_main, repo, schreiber  # noqa: E402,F401  (repo: Fixture)
from test_konnektor import ALT_ORGANISATOR, dienst, werkzeug  # noqa: E402,F401  (dienst: Fixture)

WURZEL = Path(__file__).resolve().parent.parent.parent
BEISPIELE = WURZEL / "beispiel" / "reisen"
D = datetime.date
Q = "erfunden (Beispiel)"
OHNE_BROWSER = pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")

# Merkmale, die die Beispielreise Stadtwochenende für #665 an der Art bahn trägt (Spec, Abschnitt Beispielreisen)
ERINNERND = "freischalten"   # Typ zeitpunkt, erinnern: true; an E-01 mit Datum (Vortag), an E-02 nur Uhrzeit
GLEIS = "gleis"              # Typ text, bei: abfahrt, nach_buchung: true; an E-01 mit Wert, an E-02 ohne


# ---------- Hilfen ----------

def kopie(tmp_path, reise="stadtwochenende"):
    q = tmp_path / "quelle" / reise
    shutil.copytree(BEISPIELE / reise, q)
    return q


def yaml_lesen(datei):
    return yaml.safe_load(datei.read_text(encoding="utf-8"))


def yaml_schreiben(datei, roh):
    datei.write_text(yaml.safe_dump(roh, allow_unicode=True, sort_keys=False), encoding="utf-8")


def abwandeln(q, art="bahn", definitionen=None, werte=None, entfernen=(), buchung=None):
    """Erfundene Abwandlung einer Reise: definitionen {Merkmal: Definition} kommen an die Art (vorhandene werden ersetzt),
    werte {ID: {Merkmal: Wert oder None zum Entfernen}} an die Strecken; entfernen: Merkmale der Art, die wegfallen;
    buchung: {ID: None} entfernt eine Buchung."""
    arten = q / "plan" / "arten.yaml"
    a = yaml_lesen(arten)
    mk = a["arten"][art].setdefault("merkmale", {})
    for k in entfernen:
        mk.pop(k, None)
    mk.update(definitionen or {})
    yaml_schreiben(arten, a)
    routen = q / "plan" / "routen.yaml"
    r = yaml_lesen(routen)
    for did, felder in (werte or {}).items():
        m = r["strecken"][did].setdefault("merkmale", {})
        for k, w in felder.items():
            if w is None:
                m.pop(k, None)
            else:
                m[k] = w if isinstance(w, dict) else {"wert": w, "quelle": Q}
    for bid, b in (buchung or {}).items():
        if b is None:
            r["buchungen"].pop(bid, None)
            for s in r["strecken"].values():
                s.pop("buchung", None)
    yaml_schreiben(routen, r)
    return q


def bau(q, tmp_path, name="web"):
    return bauen.bauen(q, tmp_path / name / q.name)


def bau_fehler(q, tmp_path, schluessel):
    with pytest.raises(bauen.BauFehler) as e:
        bau(q, tmp_path)
    assert meldet(e.value.args[0], schluessel), e.value.args[0]
    return e.value.args[0]


def def_von(d, art, merkmal):
    return next((x for x in (d["route"]["merkmale"].get(art) or []) if x["id"] == merkmal), None)


def leiste(d, did):
    """Die Zeitleiste einer Strecke in den Seitendaten -> [(art, merkmal)]"""
    return [(p["art"], p.get("merkmal")) for p in d["route"]["strecken"][did].get("zeitleiste") or []]


# Zeitpunkt-Merkmal ohne Rolle mit „erinnern“ und ein Merkmal „bei“ der Abfahrt, für Abwandlungen der Reise vor dem Beispiel
DEF_ERINNERND = {"name": "Fahrkarte freischalten ab", "typ": "zeitpunkt", "erinnern": True}
DEF_GLEIS = {"name": "Gleis", "typ": "text", "bei": "abfahrt", "nach_buchung": True}


# ---------- a) Zeitpunkt ohne Rolle am Ding ----------

def test_zeitpunkt_ohne_rolle_bleibt_merkmal_und_wird_geprueft(tmp_path):
    """Test 1, AC-1: ein Zeitpunkt-Merkmal ohne Rolle (mit Datum und nur Uhrzeit) ist gültig und bleibt Merkmal; die Rollen
    abfahrt und ankunft falten weiter; ein ungültiger Wert bleibt ein Fehler."""
    # mit Typ am Wert (wie abfahrt und ankunft), ohne Definition an der Art: heute pruefung.routen.lage_rolle
    zp = lambda w: {"typ": "zeitpunkt", "wert": w, "quelle": Q}   # noqa: E731
    q = abwandeln(kopie(tmp_path), werte={"E-01": {"boarding": zp("2027-03-12T08:55")}, "E-02": {"boarding": zp("17:25")}})
    d = bau(q, tmp_path)
    e1, e2 = d["route"]["strecken"]["E-01"], d["route"]["strecken"]["E-02"]
    assert e1["merkmale"]["boarding"]["wert"] == "2027-03-12T08:55" and e2["merkmale"]["boarding"]["wert"] == "17:25"
    assert (e1["ab"], e1["an"]) == ("09:10", "11:25")   # abfahrt/ankunft gefaltet wie bisher
    abwandeln(q, werte={"E-02": {"boarding": zp("morgen früh")}})
    bau_fehler(q, tmp_path / "x", "pruefung.routen.lage_wert")


@pytest.mark.parametrize("merkmal, schluessel", [
    ({"typ": "uhrzeit", "wert": "08:55", "quelle": Q}, "pruefung.routen.lage_rolle"),
    ({"typ": "zeitpunkt", "rolle": "abfahrt", "wert": "09:00", "quelle": Q}, "pruefung.routen.lage_doppelt"),
])
def test_uhrzeit_ohne_rolle_und_zweite_abfahrt_bleiben_fehler(tmp_path, merkmal, schluessel):
    """Test 2, AC-1 (Gegenprobe, ADR-0007): uhrzeit braucht weiter eine Rolle, abfahrt und ankunft gelten je Ding einmal."""
    q = abwandeln(kopie(tmp_path), werte={"E-01": {"zweite": merkmal}})
    bau_fehler(q, tmp_path, schluessel)


def test_text_lage_rolle_nennt_zeitpunkt_nicht_mehr_als_rollenpflichtig():
    """Der Fehlertext lage_rolle gilt nur noch für uhrzeit; ein Zeitpunkt braucht keine Rolle mehr."""
    for sprache in ("de", "en"):
        t = texte.t(sprache, "pruefung.routen.lage_rolle", wo="E-01", k="x", typ="uhrzeit")
        assert "zeitpunkt" not in t.replace("{typ}", ""), (sprache, t)


# ---------- b) Eigenschaft erinnern ----------

def test_erinnern_an_zeitpunkt_wird_uebernommen(tmp_path):
    """Test 3/AC-2: erinnern: true an einem Zeitpunkt-Merkmal steht mit der Definition in den Seitendaten."""
    q = abwandeln(kopie(tmp_path), definitionen={ERINNERND: DEF_ERINNERND}, werte={"E-01": {ERINNERND: "2027-03-11T08:00"}})
    d = bau(q, tmp_path)
    assert def_von(d, "bahn", ERINNERND)["erinnern"] is True


@pytest.mark.parametrize("definition, schluessel", [
    ({"name": "Hinweis", "typ": "text", "erinnern": True}, "pruefung.routen.erinnern_typ"),
    ({"name": "Uhr", "typ": "uhrzeit", "erinnern": True}, "pruefung.routen.erinnern_typ"),
    ({"name": "Ab", "typ": "zeitpunkt", "erinnern": "ja"}, "pruefung.routen.erinnern"),
])
def test_erinnern_nur_an_zeitpunkt_und_nur_wahr_oder_falsch(tmp_path, definition, schluessel):
    """Test 3: erinnern an einem anderen Typ oder mit einem anderen Wert als true/false lehnt die Prüfung der Art ab."""
    q = abwandeln(kopie(tmp_path), definitionen={"x": definition})
    bau_fehler(q, tmp_path, schluessel)


def test_erinnern_im_schreibweg(repo):
    """Test 3, 4, AC-2: attribute_define legt erinnern an einem Zeitpunkt an, schaltet es ab; dasselbe noch einmal ändert
    nichts (Ablehnung .12); an einem Text-Merkmal und beim Ändern des Typs eines erinnernden Merkmals Ablehnung."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "bahn", "bezeichnung": "Online-Check-in",
                                                                             "typ": "zeitpunkt", "erinnern": True}})
    assert meldet(a["text"], "schreiben.antwort.merkmal.erinnern_an"), a["text"]
    arten, _ = arten_auf_main(origin)
    assert arten["bahn"]["merkmale"]["online_check_in"] == {"name": "Online-Check-in", "typ": "zeitpunkt", "erinnern": True}
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung) as e:
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "bahn", "merkmal": "online_check_in", "erinnern": True}})
    assert e.value.schluessel == "schreiben.merkmal_definieren.12"
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung) as e:
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "bahn", "merkmal": "online_check_in", "typ": "text"}})
    assert e.value.schluessel == "schreiben.merkmal_definieren.erinnern_typ"
    s.vorbereiten()
    a = s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "bahn", "merkmal": "online_check_in", "erinnern": False}})
    assert meldet(a["text"], "schreiben.antwort.merkmal.erinnern_aus"), a["text"]
    arten, _ = arten_auf_main(origin)
    assert "erinnern" not in arten["bahn"]["merkmale"]["online_check_in"]
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung) as e:
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "bahn", "bezeichnung": "Bahnsteig", "erinnern": True}})
    assert e.value.schluessel == "schreiben.merkmal_definieren.erinnern_typ"


# ---------- d) Eigenschaft bei ----------

def test_bei_auf_rolle_und_auf_zeitpunkt_weiter_unten(tmp_path):
    """Test 15, AC-10: bei: abfahrt und bei: <Schlüssel eines Zeitpunkt-Merkmals> (das weiter unten steht) werden übernommen."""
    q = abwandeln(kopie(tmp_path), definitionen={
        GLEIS: DEF_GLEIS, "hinweis_karte": {"name": "Wo freischalten", "typ": "text", "bei": ERINNERND}, ERINNERND: DEF_ERINNERND})
    d = bau(q, tmp_path)
    assert def_von(d, "bahn", GLEIS)["bei"] == "abfahrt" and def_von(d, "bahn", "hinweis_karte")["bei"] == ERINNERND


@pytest.mark.parametrize("art, definitionen, schluessel", [
    ("bahn", {"x": {"name": "Ab", "typ": "zeitpunkt", "bei": "abfahrt"}}, "pruefung.routen.bei_typ"),
    ("bahn", {"x": {"name": "Uhr", "typ": "uhrzeit", "bei": "ankunft"}}, "pruefung.routen.bei_typ"),
    ("bahn", {"x": {"name": "Gleis", "bei": "gibt_es_nicht"}}, "pruefung.routen.bei_ziel"),
    ("bahn", {"x": {"name": "Gleis", "bei": "dauer"}}, "pruefung.routen.bei_ziel"),           # Ziel vom Typ text
    ("gastzimmer", {"x": {"name": "Tür", "bei": "abfahrt"}}, "pruefung.routen.bei_ziel"),      # keine Bewegung
    ("bahn", {"x": {"name": "Gleis", "bei": ""}}, "pruefung.routen.bei"),
    ("bahn", {"x": {"name": "Gleis", "bei": 5}}, "pruefung.routen.bei"),
])
def test_bei_wird_geprueft(tmp_path, art, definitionen, schluessel):
    """Test 16, AC-10: bei nicht an Zeitpunkt/Uhrzeit, nur auf ein vorhandenes Zeitpunkt-Merkmal derselben Art oder auf
    abfahrt/ankunft einer Bewegung, nur als nichtleerer Text. Die Ablehnung des Ziels nennt die gültigen Ziele."""
    q = abwandeln(kopie(tmp_path), art=art, definitionen=definitionen)
    text = bau_fehler(q, tmp_path, schluessel)
    if schluessel == "pruefung.routen.bei_ziel" and art == "bahn":
        assert "abfahrt" in text and "ankunft" in text, text


def test_bei_im_schreibweg(repo):
    """Test 16, 17, AC-10: attribute_define setzt bei, ein leerer Text entfernt es; unbekanntes Ziel, bei an einem Zeitpunkt
    und das Ändern des Typs eines Ziels, auf das ein anderes Merkmal zeigt, werden abgelehnt."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "bahn", "bezeichnung": "Sitzplatz frei ab", "typ": "zeitpunkt"}})
    s.vorbereiten()
    a = s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "bahn", "bezeichnung": "Gleis", "bei": "abfahrt"}})
    assert meldet(a["text"], "schreiben.antwort.merkmal.bei"), a["text"]
    s.vorbereiten()
    a = s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "bahn", "bezeichnung": "Wagen", "bei": "sitzplatz_frei_ab"}})
    arten, _ = arten_auf_main(origin)
    assert arten["bahn"]["merkmale"]["gleis"]["bei"] == "abfahrt" and arten["bahn"]["merkmale"]["wagen"]["bei"] == "sitzplatz_frei_ab"
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung) as e:
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "bahn", "merkmal": "sitzplatz_frei_ab", "typ": "text"}})
    assert e.value.schluessel == "schreiben.merkmal_definieren.bei_abhaengig" and "wagen" in str(e.value).lower() + str(e.value.werte).lower()
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung) as e:
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "bahn", "merkmal": "gleis", "bei": "gibt_es_nicht"}})
    assert e.value.schluessel == "schreiben.merkmal_definieren.bei_ziel"
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung) as e:
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "bahn", "merkmal": "sitzplatz_frei_ab", "bei": "abfahrt"}})
    assert e.value.schluessel == "schreiben.merkmal_definieren.bei_typ"
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung) as e:
        s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "bahn", "merkmal": "gleis", "typ": "zeitpunkt"}})
    assert e.value.schluessel == "schreiben.merkmal_definieren.bei_typ"
    s.vorbereiten()
    a = s.schreiben("beispielreise", "merkmal_definieren", {**IDA, "args": {"art": "bahn", "merkmal": "gleis", "bei": ""}})
    assert meldet(a["text"], "schreiben.antwort.merkmal.bei_aus"), a["text"]
    arten, _ = arten_auf_main(origin)
    assert "bei" not in arten["bahn"]["merkmale"]["gleis"]


# ---------- Konnektor: Schema, englische Namen, Anzeige ----------

def test_schema_und_englische_namen():
    """Test 4, 17: attribute_define nimmt erinnern (englisch remind) und bei (englisch at); bei heißt an den Buchungswerkzeugen
    weiter booked_with, und die deutsche Eingabe bei gilt an beiden."""
    props = kn.MERKMAL_DEFINIEREN["inputSchema"]["properties"]
    assert props["erinnern"]["type"] == "boolean" and props["bei"]["type"] == "string"
    assert schnittstelle.parameter_zu_englisch("merkmal_definieren")["erinnern"] == "remind"
    assert schnittstelle.parameter_zu_englisch("merkmal_definieren")["bei"] == "at"
    assert schnittstelle.parameter_zu_intern("merkmal_definieren")["at"] == "bei"
    assert schnittstelle.parameter_zu_intern("merkmal_definieren")["remind"] == "erinnern"
    for w in ("buchung_anlegen", "buchung_aendern"):
        assert schnittstelle.parameter_zu_englisch(w)["bei"] == "booked_with" and schnittstelle.parameter_zu_intern(w)["booked_with"] == "bei"
    for k in ("konnektor.werkzeug.merkmal_definieren.erinnern", "konnektor.werkzeug.merkmal_definieren.bei"):
        assert texte.t("de", k) != k and texte.t("en", k) != k


@pytest.fixture(scope="module")
def seiten(tmp_path_factory):
    """Seiten der Beispielreise; an der Art bahn ein erinnernder Zeitpunkt und ein Merkmal bei der Abfahrt (erfundene Definitionen
    in den Seitendaten, damit die Anzeige des Konnektors unabhängig vom Lesen der Art geprüft wird). Ersetzt die Fixture seiten
    von test_konnektor für dienst."""
    quelle = tmp_path_factory.mktemp("quelle") / "beispielreise"
    shutil.copytree(BEISPIELE / "beispielreise", quelle)
    s = tmp_path_factory.mktemp("seiten")
    bauen.bauen(quelle, s / "beispielreise")
    datei = s / "beispielreise" / "daten.json"
    d = json.loads(datei.read_text(encoding="utf-8"))
    d["route"]["merkmale"]["bahn"] += [{"id": "online_check_in", "name": "Online-Check-in", "typ": "zeitpunkt", "erinnern": True},
                                       {"id": "gleis", "name": "Gleis", "typ": "text", "bei": "online_check_in"}]
    datei.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return s


def test_merkmale_zeigt_erinnern_und_bei(dienst):
    """Test 4, 17, AC-2, AC-10: attributes (merkmale) nennt am Merkmal „erinnert“ und „steht bei <Name des Ziels>“."""
    basis, _ = dienst
    t, f = werkzeug(basis, ALT_ORGANISATOR, "merkmale", art="bahn")
    assert not f, t
    zeile = lambda k: next(z for z in t.splitlines() if z.startswith(f"- {k} "))   # noqa: E731
    assert meldet(zeile("online_check_in"), "konnektor.merkmale.erinnern"), t
    assert meldet(zeile("gleis"), "konnektor.merkmale.bei") and "Online-Check-in" in zeile("gleis"), t


# ---------- Wächter und Kalender ----------

def stadt_fest(tmp_path, monkeypatch, werte, buchung_ab=None):
    """Stadtwochenende im Status fest mit Wächter, gebaut; danach an der Art bahn der erinnernde Zeitpunkt (Definition und Werte
    in den Seitendaten, damit Wächter und Kalender unabhängig vom Lesen der Art geprüft werden). -> Seitendaten"""
    q = kopie(tmp_path)
    y = yaml_lesen(q / "reise.yaml")
    y["status"] = {"wert": "fest", "verlauf": y["status"]["verlauf"] + [{"datum": D(2026, 11, 20), "wert": "fest", "wer": "Tom", "grund": "Test"}]}
    y["bausteine"] = sorted(set(y.get("bausteine") or []) | {"waechter"})
    yaml_schreiben(q / "reise.yaml", y)
    seiten = tmp_path / "seiten"
    bauen.bauen(q, seiten / "stadtwochenende")
    datei = seiten / "stadtwochenende" / "daten.json"
    d = json.loads(datei.read_text(encoding="utf-8"))
    d["route"]["merkmale"]["bahn"].append({"id": ERINNERND, "name": "Fahrkarte freischalten ab", "typ": "zeitpunkt", "erinnern": True})
    for did, w in werte.items():
        d["route"]["strecken"][did]["merkmale"][ERINNERND] = {"wert": w, "quelle": Q, "notiz": None, "geprueft": None, "ungeprueft": True}
    if buchung_ab:
        d["route"]["buchungen"]["B-01"]["je_ding"]["E-01"]["ab"] = buchung_ab
    datei.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    ablage = tmp_path / "ablage"
    (ablage / "stadtwochenende").mkdir(parents=True)
    for k, v in (("RM_ABLAGE", ablage), ("RM_SEITEN", seiten), ("KN_SEITEN", seiten)):
        monkeypatch.setenv(k, str(v))
    return d


def zeit_meldungen(heute):
    return [m for m in wa.lauf_reise("stadtwochenende", heute)["meldungen"] if m["schluessel"].startswith("zeit:")]


def test_waechter_erinnert_einmal_am_tag_des_zeitpunkts(tmp_path, monkeypatch):
    """Test 5, AC-3: ein erinnernder Zeitpunkt mit Datum meldet sich einmal, sobald sein Tag da ist, an die Organisator:innen,
    mit eigenem Schlüssel; nicht vorher und nicht noch einmal."""
    stadt_fest(tmp_path, monkeypatch, {"E-01": "2027-03-11T08:00"})
    assert zeit_meldungen(D(2027, 3, 10)) == []
    ms = zeit_meldungen(D(2027, 3, 11))
    assert [m["schluessel"] for m in ms] == [f"zeit:E-01:{ERINNERND}:2027-03-11T08:00"], ms
    assert ms[0]["bezug"] == "E-01" and ms[0]["ziel"] == "E-01" and ms[0]["art"] == "erinnerung"
    assert "Fahrkarte freischalten ab" in ms[0]["text"] and "08:00" in ms[0]["text"], ms[0]["text"]
    assert zeit_meldungen(D(2027, 3, 12)) == []


def test_ohne_datum_keine_erinnerung_und_kein_termin(tmp_path, monkeypatch):
    """Test 6, AC-3: nur eine Uhrzeit (E-02) erinnert nicht und steht nicht im Kalender; der Zeitpunkt mit Datum an E-01 (Beispielwert)
    erinnert weiter genau einmal."""
    d = stadt_fest(tmp_path, monkeypatch, {"E-02": "17:00"})
    meldungen = zeit_meldungen(D(2027, 3, 13)) + zeit_meldungen(D(2027, 3, 14))
    assert not [m for m in meldungen if m["schluessel"].startswith("zeit:E-02:")], meldungen
    assert not [e for e in kalender.eintraege(d) if e["uid"] == f"E-02-zeit-{ERINNERND}"]
    assert len([e for e in kalender.eintraege(d) if e["uid"] == f"E-01-zeit-{ERINNERND}"]) == 1


def test_keine_doppelte_erinnerung_bei_gleichem_zeitpunkt_wie_die_buchung(tmp_path, monkeypatch):
    """Test 7, AC-4: Buchungs-ab und erinnerndes Merkmal mit gleichem Datum und gleicher Uhrzeit am selben Ding: nur die
    Erinnerung der Buchung und nur ihr Kalendertermin."""
    d = stadt_fest(tmp_path, monkeypatch, {"E-01": "2027-03-11T09:10"})   # B-01 je Ding E-01: ab 2027-03-11T09:10
    alle = wa.lauf_reise("stadtwochenende", D(2027, 3, 11))["meldungen"]
    assert not [m for m in alle if m["schluessel"].startswith("zeit:")], alle
    assert [m for m in alle if m["schluessel"] == "ab:B-01:E-01:2027-03-11T09:10"], alle
    uids = [e["uid"] for e in kalender.eintraege(d)]
    assert "B-01-E-01-ab" in uids and f"E-01-zeit-{ERINNERND}" not in uids


def test_verschiedene_zeiten_erinnern_beide(tmp_path, monkeypatch):
    """Test 7: bei verschiedener Uhrzeit melden sich Merkmal und Buchung je einmal."""
    stadt_fest(tmp_path, monkeypatch, {"E-01": "2027-03-11T08:00"})
    alle = [m["schluessel"] for m in wa.lauf_reise("stadtwochenende", D(2027, 3, 11))["meldungen"]]
    assert f"zeit:E-01:{ERINNERND}:2027-03-11T08:00" in alle and "ab:B-01:E-01:2027-03-11T09:10" in alle, alle


def test_kalender_termin_je_erinnerndem_zeitpunkt(tmp_path, monkeypatch):
    """Test 8, AC-3: ein Termin je erinnerndem Zeitpunkt mit Datum, UID <Ding>-zeit-<Merkmal>; die UIDs der Buchungstermine
    bleiben."""
    d = stadt_fest(tmp_path, monkeypatch, {"E-01": "2027-03-11T08:00"})
    es = [e for e in kalender.eintraege(d) if e["uid"] == f"E-01-zeit-{ERINNERND}"]
    assert len(es) == 1 and es[0]["sorte"] == "buchungen" and es[0]["tag"] == D(2027, 3, 11), es
    assert "Fahrkarte freischalten ab" in es[0]["titel"], es
    uids = [e["uid"] for e in kalender.eintraege(d)]
    assert "B-01-E-01-ab" in uids and "B-01-E-02-ab" in uids and len(uids) == len(set(uids))


# ---------- c) Seitendaten der Zeitleiste ----------

def test_beispielreise_stadtwochenende_traegt_die_neuen_merkmale():
    """Beispielreisen (Spec): die Art bahn hat den erinnernden Zeitpunkt und das Gleis bei der Abfahrt, als Beispielwerte."""
    a = yaml_lesen(BEISPIELE / "stadtwochenende" / "plan" / "arten.yaml")["arten"]["bahn"]["merkmale"]
    assert a[ERINNERND]["typ"] == "zeitpunkt" and a[ERINNERND]["erinnern"] is True
    assert a[GLEIS]["bei"] == "abfahrt" and a[GLEIS]["nach_buchung"] is True
    r = yaml_lesen(BEISPIELE / "stadtwochenende" / "plan" / "routen.yaml")["strecken"]
    assert re.fullmatch(r"2027-03-11T\d\d:\d\d", r["E-01"]["merkmale"][ERINNERND]["wert"])
    assert re.fullmatch(r"\d\d:\d\d", r["E-02"]["merkmale"][ERINNERND]["wert"])
    assert r["E-01"]["merkmale"][GLEIS]["wert"] and GLEIS not in r["E-02"]["merkmale"]
    assert all("Beispiel" in r[e]["merkmale"][ERINNERND]["quelle"] for e in ("E-01", "E-02"))


def test_zeitleiste_in_den_seitendaten(tmp_path):
    """Test 9, AC-5: E-01 des Stadtwochenendes (Fahrt 12.3.): Merkmal und Buchungs-ab am Vortag, Abfahrt, Ankunft; E-02 (Fahrt
    14.3.): Buchungs-ab am Vortag (13.3., 17:40), Merkmal ohne Datum am Tag der Fahrt vor der Abfahrt, Ankunft. Jeder Punkt mit
    Uhrzeit, Datum, erinnert und bei."""
    d = bau(kopie(tmp_path), tmp_path)
    assert leiste(d, "E-01") == [("merkmal", ERINNERND), ("buchung", None), ("abfahrt", None), ("ankunft", None)]
    assert leiste(d, "E-02") == [("buchung", None), ("merkmal", ERINNERND), ("abfahrt", None), ("ankunft", None)]
    e1 = d["route"]["strecken"]["E-01"]["zeitleiste"]
    assert [p["datum"] for p in e1] == ["2027-03-11", "2027-03-11", "2027-03-12", "2027-03-12"], e1
    assert e1[0]["zeit"] < e1[1]["zeit"] and [p["zeit"] for p in e1][1:] == ["09:10", "09:10", "11:25"], e1
    assert [p["erinnert"] for p in e1] == [True, True, False, False], e1
    assert e1[1]["was"] == "Komfort-Check-in" and e1[1]["buchung"] == "B-01", e1
    assert e1[2]["bei"] == [GLEIS] and all(p["bei"] == [] for p in e1 if p["art"] != "abfahrt"), e1
    e2 = d["route"]["strecken"]["E-02"]["zeitleiste"]
    assert [p["datum"] for p in e2] == ["2027-03-13", "2027-03-14", "2027-03-14", "2027-03-14"], e2
    assert e2[0]["zeit"] == "17:40" and e2[1]["zeit"] < e2[2]["zeit"] == "17:40", e2
    assert all(p["bei"] == [] for p in e2), e2   # Gleis ohne Wert an E-02: nichts zu zeigen


def test_zeige_nennt_die_zeitpunkte_der_zeitleiste(tmp_path, monkeypatch):
    """AC-13: show (zeige) an E-01 des Stadtwochenendes nennt jeden Zeitpunkt, den die Seite in der Zeitleiste zeigt: die
    erinnernden Zeitpunkt mit seinem Wert, Abfahrt und Ankunft mit Uhrzeit und die Buchung, deren ab der vierte Punkt ist."""
    from test_konnektor import rpc
    seiten = tmp_path / "web"
    d = bau(kopie(tmp_path), tmp_path)
    zug = tmp_path / "zugaenge.json"
    zug.write_text(json.dumps({"t" * 32: {"reise": "stadtwochenende", "person": "tom"}}))
    monkeypatch.setenv("KN_SEITEN", str(seiten))
    monkeypatch.setenv("KN_ZUGAENGE", str(zug))
    r = rpc(None, "t" * 32, "tools/call", {"name": "zeige", "arguments": {"id": "E-01"}})
    t = r["content"][0]["text"]
    assert not r["isError"], t
    strecke = d["route"]["strecken"]["E-01"]
    punkte = {p["art"]: p for p in strecke["zeitleiste"]}
    assert set(punkte) == {"merkmal", "buchung", "abfahrt", "ankunft"}, strecke["zeitleiste"]
    assert strecke["merkmale"][punkte["merkmal"]["merkmal"]]["wert"] in t, t   # erinnernder Zeitpunkt mit seinem Wert
    assert f"ab {punkte['abfahrt']['zeit']}" in t and f"an {punkte['ankunft']['zeit']}" in t, t
    assert f"zeige {punkte['buchung']['buchung']}" in t, t   # Buchungs-ab: Heimat ist die Buchung, show verweist darauf (ADR-0003)


def test_ohne_weitere_zeitpunkte_keine_zeitleiste(tmp_path):
    """Test 10, AC-9 (Gegenprobe Wanderung, #619): die Bahnstrecke der Beispielreise mit Abfahrt und Ankunft allein hat keine
    Zeitleiste; ebenso ein Merkmal mit bei allein."""
    d = bau(kopie(tmp_path, "beispielreise"), tmp_path)
    assert not [sid for sid, s in d["route"]["strecken"].items() if s.get("zeitleiste")]
    q = abwandeln(kopie(tmp_path / "b"), definitionen={GLEIS: DEF_GLEIS}, entfernen=(ERINNERND,),
                  werte={"E-01": {ERINNERND: None, GLEIS: "4 (Beispielwert)"}, "E-02": {ERINNERND: None}}, buchung={"B-01": None})
    d = bau(q, tmp_path / "b")
    assert not d["route"]["strecken"]["E-01"].get("zeitleiste")


def test_bei_ohne_punkt_bleibt_in_der_merkmalliste(tmp_path):
    """Test 19, AC-11: ein Merkmal bei einem Zeitpunkt, der an diesem Ding keinen Wert hat, steht an keinem Punkt."""
    q = abwandeln(kopie(tmp_path), definitionen={"wo": {"name": "Wo freischalten", "typ": "text", "bei": ERINNERND}},
                  werte={"E-01": {"wo": "App des Betreibers (Beispielwert)"}, "E-02": {"wo": "Automat (Beispielwert)", ERINNERND: None}})
    d = bau(q, tmp_path)
    assert next(p for p in d["route"]["strecken"]["E-01"]["zeitleiste"] if p["art"] == "merkmal")["bei"] == ["wo"]
    assert not [p for p in d["route"]["strecken"]["E-02"]["zeitleiste"] if "wo" in p["bei"]]


def test_kein_formatwechsel(tmp_path):
    """Test 14, AC-13: nachziehen ändert an beiden Beispielreisen nichts (erinnern, bei und freie Zeitpunkte sind kein neues
    Format)."""
    for reise in ("stadtwochenende", "beispielreise"):
        q = kopie(tmp_path, reise)
        vorher = {p.relative_to(q): p.read_bytes() for p in q.rglob("*.yaml")}
        assert neu.nachziehen(q) == [], reise
        assert {p.relative_to(q): p.read_bytes() for p in q.rglob("*.yaml")} == vorher, reise


# ---------- Texte ----------

NEUE_TEXTE = ["seite.zeitleiste.name", "seite.zeitleiste.abfahrt", "seite.zeitleiste.ankunft", "seite.zeitleiste.erinnert",
              "seite.zeitleiste.aus_buchung", "pruefung.routen.erinnern", "pruefung.routen.erinnern_typ", "pruefung.routen.bei",
              "pruefung.routen.bei_typ", "pruefung.routen.bei_ziel", "schreiben.merkmal_definieren.erinnern_typ",
              "schreiben.merkmal_definieren.bei_typ", "schreiben.merkmal_definieren.bei_ziel", "schreiben.merkmal_definieren.bei_abhaengig",
              "schreiben.antwort.merkmal.erinnern_an", "schreiben.antwort.merkmal.erinnern_aus", "schreiben.antwort.merkmal.bei",
              "schreiben.antwort.merkmal.bei_aus", "konnektor.merkmale.erinnern", "konnektor.merkmale.bei",
              "konnektor.werkzeug.merkmal_definieren.erinnern", "konnektor.werkzeug.merkmal_definieren.bei"]


@pytest.mark.parametrize("sprache", ["de", "en"])
def test_neue_texte_in_jeder_sprache(sprache):
    """Test 13 (ADR-0006): alle neuen Schlüssel stehen in jeder Sprache (die Pseudo-Sprache leitet test_texte ab)."""
    fehlt = [k for k in NEUE_TEXTE if texte.t(sprache, k) == k]
    assert not fehlt, fehlt


# ---------- Atomic Design ----------

def test_atome_der_leiste_und_ihre_nutzung():
    """Test 21, AC-12: die Atome der Leiste und das Molekül zeitLeiste stehen im Kopfkommentar, sind Funktionen der Vorlage,
    stehen in docs/design.md; zeitLeiste und halteLeiste rufen dieselben Atome; Punkt und Linie haben je einen Stil; GRUNDFORMEN
    nennt zeitLeiste bei der Bewegung."""
    from test_design import DESIGN, VORLAGE, _funktion, _grundformen_code, bausteine
    b = bausteine()
    assert {"leistenPunkt", "leistenZeit", "leistenMarke", "leistenZusatz"} <= set(b["Atome"]), b["Atome"]
    assert "zeitLeiste" in b["Moleküle"], b["Moleküle"]
    for name in ("leistenPunkt", "leistenZeit", "leistenMarke", "leistenZusatz", "zeitLeiste"):
        assert f"`{name}`" in DESIGN, name
    for molekuel in ("zeitLeiste", "halteLeiste"):
        rumpf = _funktion(molekuel)
        assert "leistenPunkt(" in rumpf and "leistenZeit(" in rumpf, molekuel
        assert '"hl-p"' not in rumpf and "hl-zeit" not in rumpf, molekuel   # zeichnet Punkt und Zeit nicht selbst
    stile = VORLAGE[VORLAGE.index("<style"):VORLAGE.index("</style>")]
    assert not re.search(r"ol\.(halte|zeit)>li::before", stile), "Linie je Leiste statt eines gemeinsamen Stils"
    assert not re.search(r"\.hl-p\{", stile), "Punkt der Halteleiste mit eigenem Stil statt des Atoms"
    assert "leiste (CSS)" in VORLAGE[VORLAGE.index("/* Bausteine nach Ebenen"):VORLAGE.index("   Regeln: docs/adr/0002-atomic-design.md")]
    bewegung = next(x for x in _grundformen_code() if x[0] == "bewegung")
    assert "zeitLeiste" in bewegung[4]["seite"] | bewegung[4]["zeile"], bewegung


# ---------- Seite im Browser ----------

def ansehen(seiten, reise, ids, browser, breite=390):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(seiten)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_zeitleiste_665.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/{reise}/", ",".join(ids), str(breite)],
                             capture_output=True, text=True, timeout=180, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == [], e["fehler"]
    return e["dinge"]


@OHNE_BROWSER
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
@pytest.mark.parametrize("breite", [360, 1200])
def test_seite_zeigt_die_zeitleiste(tmp_path, browser, breite):
    """Test 11, 18, AC-5 bis AC-8, AC-11: Stadtwochenende E-01 und E-02 an ihrer Heimat (E-01: Merkmal und Buchungs-ab am
    Vortag vor der Abfahrt; E-02: Buchungs-ab am Vortag, dann das Merkmal ohne Datum am Tag der Fahrt)."""
    folge = {"E-01": ["merkmal", "buchung", "abfahrt", "ankunft"], "E-02": ["buchung", "merkmal", "abfahrt", "ankunft"]}
    q = kopie(tmp_path)
    seiten = tmp_path / "seiten"
    bauen.bauen(q, seiten / "stadtwochenende")
    dinge = ansehen(seiten, "stadtwochenende", ["E-01", "E-02"], browser, breite)
    for did, e in dinge.items():
        assert e["anzahl"] == 1, (did, e)
        arten = [p["art"] for p in e["punkte"]]
        assert arten == folge[did], (did, arten)
        punkt = {p["art"]: p for p in e["punkte"]}
        # eine Schriftgröße für alle Uhrzeiten und Daten, auch das Datum der Kopfzeile und ein abweichendes Datum
        groessen = {p["zeitGroesse"] for p in e["punkte"]} | {p["tagGroesse"] for p in e["punkte"] if p["tag"]} | {e["kopf"]["groesse"]}
        assert len(groessen) == 1, (did, groessen)
        assert all(p["zeitFett"] == e["punkte"][0]["zeitFett"] for p in e["punkte"]), (did, e["punkte"])
        for p in e["punkte"]:
            fest = p["art"] in ("abfahrt", "ankunft")
            assert p["punkt"] and p["voll"] is fest and (p["nameFett"] >= 600) is fest, (did, p)
        assert punkt["merkmal"]["marke"] and punkt["buchung"]["marke"], (did, e["punkte"])   # erinnert: Merkmal und Buchungs-ab
        assert not punkt["abfahrt"]["marke"] and not punkt["ankunft"]["marke"], (did, e["punkte"])
        assert punkt["buchung"]["name"].startswith("Komfort-Check-in") and punkt["buchung"]["zusatz"], (did, punkt["buchung"])
        # Kopfzeile: nur das Datum, fett, ohne Art und ohne Uhrzeit; die alte Zeile „Bahn · Datum · ab … → an …“ fehlt
        assert e["kopf"]["fett"] >= 600 and not re.search(r"\d\d:\d\d", e["kopf"]["text"]) and "Bahn" not in e["kopf"]["text"], (did, e["kopf"])
        assert not [z for z in e["kleinZeilen"] if "→" in z and re.search(r"\d\d:\d\d", z)], (did, e["kleinZeilen"])
        # jede Angabe einmal: Zeitpunkt, ab der Buchung und Gleis stehen nur in der Zeitleiste
        assert "Fahrkarte freischalten ab" not in e["rest"] and "Komfort-Check-in" not in e["rest"], (did, e["rest"])
        assert not e["ueberlauf"], did
    e1 = dinge["E-01"]
    vortag = e1["punkte"][0]
    assert vortag["tag"] and vortag["tagFett"] >= 600 and vortag["tagUnterZeit"], vortag   # abweichendes Datum bei der Uhrzeit
    assert e1["punkte"][2]["tag"] is None, e1["punkte"][2]   # Tag der Fahrt: kein Datum am Punkt
    gleis = e1["werte"][GLEIS]
    assert any(gleis in z for z in e1["punkte"][2]["zusatz"]) and gleis not in e1["rest"], e1   # Gleis bei der Abfahrt
    assert e1["punkte"][2]["zusatzGroesse"] == e1["schrift"] and e1["punkte"][2]["zusatzFarbe"] != e1["punkte"][2]["nameFarbe"], e1
    e2 = {p["art"]: p for p in dinge["E-02"]["punkte"]}
    assert e2["merkmal"]["tag"] is None   # nur Uhrzeit: gilt am Tag der Fahrt
    assert e2["buchung"]["tag"] and e2["buchung"]["tagUnterZeit"], e2["buchung"]   # Buchungs-ab am Vortag


@OHNE_BROWSER
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_seite_bei_und_nach_buchung(tmp_path, browser):
    """Test 18, 20, AC-11: ein Merkmal bei einem Zeitpunkt-Merkmal steht unter diesem Punkt; gebucht steht ein bei-Merkmal ohne
    nach_buchung nur in „Aus der Planung“, ungebucht in der Zeitleiste."""
    werte = {"E-01": {"wo": "App des Betreibers (Beispielwert)", "wagen": "Wagen 5 (Beispielwert)"}}
    defs = {"wo": {"name": "Wo freischalten", "typ": "text", "bei": ERINNERND, "nach_buchung": True},
            "wagen": {"name": "Wagen", "typ": "text", "bei": "abfahrt"}}
    gebucht = abwandeln(kopie(tmp_path / "g"), definitionen=defs, werte=werte)
    bauen.bauen(gebucht, tmp_path / "sg" / "stadtwochenende")
    e = ansehen(tmp_path / "sg", "stadtwochenende", ["E-01"], browser)["E-01"]
    punkt = {p["art"]: p for p in e["punkte"]}
    assert any("App des Betreibers" in z for z in punkt["merkmal"]["zusatz"]), e["punkte"]
    assert not any("Wagen 5" in z for z in punkt["abfahrt"]["zusatz"]) and "Wagen 5" in e["rest"], e
    offen = abwandeln(kopie(tmp_path / "o"), definitionen=defs, werte=werte, buchung={"B-01": None})
    bauen.bauen(offen, tmp_path / "so" / "stadtwochenende")
    e = ansehen(tmp_path / "so", "stadtwochenende", ["E-01"], browser)["E-01"]
    punkt = {p["art"]: p for p in e["punkte"]}
    assert any("Wagen 5" in z for z in punkt["abfahrt"]["zusatz"]) and "Wagen 5" not in e["rest"], e


@OHNE_BROWSER
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_seite_gegenprobe_ohne_zeitleiste_und_unterkunft(tmp_path, browser):
    """Test 10, 12, AC-8, AC-9: Bahnstrecke E-20 der Wanderung ohne weitere Zeitpunkte: keine Zeitleiste, die kurze Zeile und die
    Kopfzeile bleiben; an der Unterkunft U-01 bleibt die ab-Zeile der Buchung."""
    from test_regeln import reise_bauen
    seiten = reise_bauen(tmp_path, routen_ersetzen=[('    fuer: [U-01]\n    status: gebucht\n',
                                                     '    fuer: [U-01]\n    status: gebucht\n    ab: "2027-05-12T15:00"\n'
                                                     '    ab_was: "Online-Anmeldung (Testwert)"\n')])
    dinge = ansehen(seiten, "beispielreise", ["E-20", "U-01"], browser)
    e = dinge["E-20"]
    assert e["anzahl"] == 0 and e["kopf"] is None, e
    assert [z for z in e["kleinZeilen"] if "Bahn" in z and "08:12" in z and "08:40" in z], e["kleinZeilen"]
    assert "Online-Anmeldung (Testwert)" in dinge["U-01"]["text"], dinge["U-01"]["text"]


@OHNE_BROWSER
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_halteleiste_sieht_aus_wie_vorher(tmp_path, browser):
    """Test 22, AC-12: die Halteleiste der S-Bahn E-20 (erfundener Halt) misst nach dem Umbau auf gemeinsame Atome dieselben
    Maße, Abstände und Farben wie vorher (halteleiste_vorher.json, vor dem Umbau aufgenommen)."""
    from test_seite import seite_der_variante
    ersetzen = [('    art: bahn\n    quelle: "Beispiel; Fahrplan nicht geprüft"\n    merkmale:\n',
                 '    art: bahn\n    quelle: "Beispiel; Fahrplan nicht geprüft"\n'
                 '    abschnitte:\n'
                 '      - {nach: O-06, kennzahlen: {fahrzeit: "0:12", laenge: 9}, halt: {zweck: "Umsteigen (Beispiel)", dauer: "0:10"}}\n'
                 '      - {nach: O-02, kennzahlen: {fahrzeit: "0:16", laenge: 11}}\n'
                 '    merkmale:\n')]
    e = seite_der_variante(tmp_path, browser, skript="seiten_halteleiste.mjs", routen_ersetzen=ersetzen)
    vorher = json.loads((Path(__file__).parent / "halteleiste_vorher.json").read_text(encoding="utf-8"))[browser]
    assert e["aus"] == vorher


# ---------- Gegenprüfung (adversary-dialog.md): Nachtfahrt, Fahrt ohne Tag, Englisch, Schreibweise von bei ----------

def test_nachtankunft_ohne_datum_liegt_am_tag_danach(tmp_path):
    """F001: eine Ankunft ohne Datum, deren Uhrzeit nicht nach der Abfahrt liegt, ist am Tag danach (wie im Kalender) und steht
    hinter der Abfahrt."""
    q = abwandeln(kopie(tmp_path), werte={"E-01": {"ankunft": {"typ": "zeitpunkt", "rolle": "ankunft", "wert": "06:00", "quelle": Q}}})
    d = bau(q, tmp_path)
    e1 = d["route"]["strecken"]["E-01"]["zeitleiste"]
    assert [(p["art"], p["datum"], p["zeit"]) for p in e1][2:] == [("abfahrt", "2027-03-12", "09:10"), ("ankunft", "2027-03-13", "06:00")], e1
    fahrt = next(e for e in kalender.eintraege(d) if e["sorte"] == "fahrten" and e["id"] == "E-01")
    assert fahrt["ende"].date().isoformat() == "2027-03-13", fahrt   # dieselbe Regel wie der Kalender


def test_fahrt_ohne_tag_stellt_punkte_mit_datum_davor(tmp_path):
    """F002: hängt die Fahrt an keinem Tag des Plans, stehen Merkmal und Check-in mit Datum (Vortag) vor Abfahrt und Ankunft
    ohne Datum; diese folgen untereinander nach Uhrzeit."""
    q = kopie(tmp_path)
    r = yaml_lesen(q / "plan" / "routen.yaml")
    r["tage"]["T-01"]["strecken"] = []
    yaml_schreiben(q / "plan" / "routen.yaml", r)
    e1 = bau(q, tmp_path)["route"]["strecken"]["E-01"]["zeitleiste"]
    assert [p["art"] for p in e1] == ["merkmal", "buchung", "abfahrt", "ankunft"], e1
    assert [p["datum"] for p in e1] == ["2027-03-11", "2027-03-11", None, None], e1


def test_englische_texte_nennen_at_und_remind():
    """F003: englische Sätze nennen die englischen Namen at und remind (Alias-Konvention)."""
    for k in ("pruefung.routen.bei", "pruefung.routen.bei_ziel", "schreiben.merkmal_definieren.bei_ziel", "schreiben.merkmal_definieren.bei_abhaengig"):
        assert "at" in re.findall(r"\w+", texte.t("en", k).replace("“at”", " at ")), k
    for k in ("pruefung.routen.erinnern", "pruefung.routen.erinnern_typ", "schreiben.merkmal_definieren.erinnern_typ"):
        assert "remind" in texte.t("en", k), k


def test_bei_wird_beim_lesen_wie_im_schreibweg_klein_geschrieben(tmp_path):
    """F004: bei: Abfahrt (groß) gilt beim Lesen wie im Schreibweg als abfahrt."""
    q = abwandeln(kopie(tmp_path), definitionen={GLEIS: {**DEF_GLEIS, "bei": "Abfahrt"}})
    d = bau(q, tmp_path)
    assert def_von(d, "bahn", GLEIS)["bei"] == "abfahrt"
    assert next(p for p in d["route"]["strecken"]["E-01"]["zeitleiste"] if p["art"] == "abfahrt")["bei"] == [GLEIS]
