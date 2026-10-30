"""Tests für den Kalender (frieda-reist #77): engine/kalender.py, Abo-Link (konten.py), Rückmeldedienst, Konto-Seite,
Konnektor, Uhrzeiten beginn/ende im Modell und im Schreibweg. Alle Beispiele sind erfunden (Beispielreise, Ida und Karl)."""
import datetime
import json
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bauen  # noqa: E402
import kalender  # noqa: E402
import konten  # noqa: E402

BEISPIEL = Path(__file__).resolve().parents[2] / "beispiel" / "reisen" / "beispielreise"
JETZT = datetime.datetime(2026, 10, 29, 12, 0, tzinfo=datetime.timezone.utc)
SEITE = "https://frieda.beispiel.invalid/beispielreise-0123456789abcdef01234567/"


@pytest.fixture(scope="module")
def daten(tmp_path_factory):
    ziel = tmp_path_factory.mktemp("seiten") / "beispielreise"
    bauen.bauen(BEISPIEL, ziel)
    return json.loads((ziel / "daten.json").read_text(encoding="utf-8"))


def nach_uid(d, aufgaben=None):
    return {e["uid"]: e for e in kalender.eintraege(d, aufgaben)}


def test_nur_entschiedenes(daten):
    e = nach_uid(daten)
    # T-05 hängt an der offenen Planungs-Wahlstelle V-01 (Abstieg): erst nach der Entscheidung im Kalender
    assert [t["vorlaeufig"] for t in daten["route"]["tage"] if t["id"] == "T-05"] == [["V-01"]]
    assert {"T-01", "T-02", "T-03"} <= set(e) and "T-05" not in e
    assert not any(x.startswith(("E-04", "E-22", "E-21")) for x in e)
    # Nacht aus der entschiedenen Wahlstelle V-03 (Pension Burgblick) steht drin, ebenso die festen Nächte
    assert e["U-02"]["tag"] == datetime.date(2027, 5, 14) and e["U-02"]["bis"] == datetime.date(2027, 5, 15)
    assert e["U-01"]["titel"] == "Übernachtung: Hotel am Elbufer" and e["U-01"]["ort"] == "Terrassenufer 1, 01067 Dresden"
    assert "Nummer HE-2027-0415" in e["U-01"]["text"]
    assert "Nacht: Pension Burgblick" in e["T-02"]["text"]


def test_uhrzeiten_und_fristen(daten):
    e = nach_uid(daten)
    s = e["E-20-2027-05-14"]
    assert (s["beginn"], s["ende"]) == (datetime.datetime(2027, 5, 14, 8, 12), datetime.datetime(2027, 5, 14, 8, 40))
    a = e["A-01-2027-05-14"]
    assert (a["beginn"].hour, a["ende"].hour) == (16, 18) and "tag" not in a
    assert e["B-01-storno"]["tag"] == datetime.date(2027, 5, 11)
    assert e["B-02-frist"]["titel"].startswith("Frist: Ticket in die App laden")
    aufgaben = [{"id": "AG-01", "titel": "Rucksack packen", "frist": "2027-05-10", "status": "offen", "zustaendig": "Karl"},
                {"id": "AG-02", "titel": "Erledigtes", "frist": "2027-05-10", "status": "erledigt"},
                {"id": "AG-03", "titel": "Ohne Frist", "frist": "", "status": "offen"}]
    e = nach_uid(daten, aufgaben)
    assert e["AG-01-frist"]["titel"] == "Aufgabe fällig: Rucksack packen" and "Zuständig: Karl" in e["AG-01-frist"]["text"]
    assert "AG-02-frist" not in e and "AG-03-frist" not in e


def test_ende_vor_beginn_ist_am_tag_danach():
    d = {"route": {"tage": [{"id": "T-01", "nr": 1, "datum": "2027-05-13", "titel": "Nachtfähre", "strecken": [{"id": "E-01", "wahl": None}],
                             "aufenthalte": [], "nacht": None}],
                   "strecken": {"E-01": {"titel": "Nachtfähre", "von": "O-01", "nach": "O-02", "ab": "22:30", "an": "07:15"}},
                   "orte": {"O-01": {"name": "Hafen A"}, "O-02": {"name": "Hafen B"}}}}
    s = nach_uid(d)["E-01-2027-05-13"]
    assert s["ende"] == datetime.datetime(2027, 5, 14, 7, 15)
    # Zeitpunkt mit Zeitzone (#135): steht als UTC in der Datei
    d["route"]["strecken"]["E-01"].update(ab="2027-05-13T22:30+02:00", an="2027-05-14T07:15+02:00")
    t = kalender.ics(d, "beispielreise", jetzt=JETZT)
    assert "DTSTART:20270513T203000Z" in t and "DTEND:20270514T051500Z" in t
    d["route"]["strecken"]["E-01"]["an"] = "07:15"          # verschiedene Form: kein Ende
    assert nach_uid(d)["E-01-2027-05-13"]["ende"] is None


def test_ics_datei(daten):
    text = kalender.ics(daten, "beispielreise", jetzt=JETZT)
    zeilen = text.split("\r\n")
    assert zeilen[0] == "BEGIN:VCALENDAR" and zeilen[-2] == "END:VCALENDAR" and zeilen[-1] == ""
    assert all(len(z.encode("utf-8")) <= 75 for z in zeilen)
    entfaltet = text.replace("\r\n ", "")
    assert "DTSTART:20270514T081200\r\nDTEND:20270514T084000" in entfaltet          # Ortszeit, ohne Zeitzone
    assert "UID:T-01.beispielreise@frieda" in entfaltet and "DTSTAMP:20261029T120000Z" in entfaltet
    assert "DTSTART;VALUE=DATE:20270513\r\nDTEND;VALUE=DATE:20270514" in entfaltet
    assert "Ankunft mittags mit dem Zug\\, Nachmittag" in entfaltet                   # Komma maskiert
    uids = [z for z in entfaltet.split("\r\n") if z.startswith("UID:")]
    assert len(uids) == len(set(uids)) == entfaltet.count("BEGIN:VEVENT")
    assert kalender.ics(daten, "beispielreise", jetzt=JETZT) == text                  # gleiche Daten, gleiche Datei


def test_einzelnes_ding(daten):
    t = kalender.ics(daten, "beispielreise", nur="U-01", jetzt=JETZT)
    assert t.count("BEGIN:VEVENT") == 1 and "Hotel am Elbufer" in t
    assert kalender.ics(daten, "beispielreise", nur="T-05") is None                  # vorläufig
    assert kalender.ics(daten, "beispielreise", nur="U-99") is None


def test_falten_zerteilt_kein_zeichen():
    z = kalender._falten("SUMMARY:" + "ä" * 100)
    teile = z.split("\r\n ")
    assert "".join(teile) == "SUMMARY:" + "ä" * 100 and all(len(x.encode()) <= 75 for x in teile)


def test_uhrzeit_im_modell_wird_geprueft(tmp_path):
    q = tmp_path / "reise"
    shutil.copytree(BEISPIEL, q)
    p = q / "plan" / "routen.yaml"
    text = p.read_text(encoding="utf-8")
    p.write_text(text.replace('beginn: "16:00"', 'beginn: "16 Uhr"'), encoding="utf-8")
    with pytest.raises(bauen.BauFehler, match="beginn muss eine Uhrzeit HH:MM"):
        bauen.bauen(q, tmp_path / "ziel")
    p.write_text(text.replace('beginn: "16:00"', ""), encoding="utf-8")
    with pytest.raises(bauen.BauFehler, match="ende ohne beginn"):
        bauen.bauen(q, tmp_path / "ziel")


# ---------- Abo-Link (konten.py) ----------

@pytest.fixture
def konten_welt(tmp_path, monkeypatch):
    monkeypatch.setenv("RM_ABLAGE", str(tmp_path / "ablage"))
    monkeypatch.setenv("FR_KONTEN", str(tmp_path / "konten"))
    v = konten.db()
    for kid, mail, name in (("k-ida", "ida@beispiel.invalid", "Ida"), ("k-karl", "karl@beispiel.invalid", "Karl")):
        v.execute("INSERT INTO konten (id, email, name, angelegt) VALUES (?,?,?,?)", (kid, mail, name, "2026-10-29"))
    v.commit()
    v.close()
    konten.verknuepfen("k-ida", "beispielreise", "ida")
    konten.verknuepfen("k-karl", "beispielreise", "karl")


def test_abo_link_erneuern_und_entziehen(konten_welt):
    t = konten.kalender_token("k-ida", "beispielreise")
    assert t == konten.kalender_token("k-ida", "beispielreise") and len(t) == 40
    assert t != konten.kalender_token("k-karl", "beispielreise")
    assert konten.kalender_konto("beispielreise", t)["schluessel"] == "ida"
    assert konten.kalender_konto("andere-reise", t) is None and konten.kalender_konto("beispielreise", "x" * 40) is None
    neu = konten.kalender_token("k-ida", "beispielreise", erneuern=True)
    assert neu != t and konten.kalender_konto("beispielreise", t) is None
    assert konten.kalender_konto("beispielreise", neu)["id"] == "k-ida"
    with pytest.raises(konten.KontoFehler, match="nicht dabei"):
        konten.kalender_token("k-ida", "andere-reise")
    k = konten.kalender_token("k-karl", "beispielreise")
    konten.sperren("k-karl")
    assert konten.kalender_konto("beispielreise", k) is None
    konten.entfernen("beispielreise", "ida")
    assert konten.kalender_konto("beispielreise", neu) is None
    assert kalender.abo_url(SEITE, "abc") == SEITE + "api/kalender/abc.ics"
    assert kalender.webcal(SEITE + "api/kalender/abc.ics").startswith("webcal://frieda.beispiel.invalid/")


# ---------- Rückmeldedienst, Konto-Seite und Konnektor ----------

def holen(url):
    try:
        with urllib.request.urlopen(url) as r:
            return r.status, dict(r.headers), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    from test_regeln import Umgebung
    u = Umgebung(tmp_path, monkeypatch)
    links = tmp_path / "seiten.json"
    links.write_text(json.dumps({"beispielreise": SEITE}))
    monkeypatch.setenv("KN_SEITENLINKS", str(links))
    monkeypatch.setenv("FR_BASIS", "https://frieda.beispiel.invalid")
    v = konten.db()
    v.execute("INSERT INTO konten (id, email, name, angelegt) VALUES ('k-ida', 'ida@beispiel.invalid', 'Ida', '2026-10-29')")
    v.commit()
    v.close()
    konten.verknuepfen("k-ida", "beispielreise", "ida")
    yield u
    u.schliessen()


def test_dienst_liefert_datei_und_abo(umgebung):
    u = umgebung
    s, h, t = holen(f"{u.rurl}/beispielreise/kalender.ics")
    assert s == 200 and h["Content-Type"] == "text/calendar; charset=utf-8" and "attachment" in h["Content-Disposition"]
    assert "UID:T-01.beispielreise@frieda" in t
    s, h, t = holen(f"{u.rurl}/beispielreise/kalender.ics?id=T-02")
    assert s == 200 and t.count("BEGIN:VEVENT") == 1 and 'beispielreise-T-02.ics' in h["Content-Disposition"]
    assert holen(f"{u.rurl}/beispielreise/kalender.ics?id=T-05")[0] == 404
    assert holen(f"{u.rurl}/beispielreise/kalender.ics?id=%22%3B")[0] == 400
    tok = konten.kalender_token("k-ida", "beispielreise")
    s, h, t = holen(f"{u.rurl}/beispielreise/kalender/{tok}.ics")
    assert s == 200 and "Content-Disposition" not in h and "X-WR-CALNAME:Beispielreise" in t
    assert holen(f"{u.rurl}/beispielreise/kalender/{'0' * 40}.ics")[0] == 404
    # Aufgaben mit Frist kommen live aus der Ablage dazu
    (u.o / "aufgaben.json").write_text(json.dumps({"naechste": 2, "aufgaben": [
        {"id": "AG-01", "titel": "Rucksack packen", "frist": "2027-05-10", "status": "offen"}]}))
    assert "Aufgabe fällig: Rucksack packen" in holen(f"{u.rurl}/beispielreise/kalender/{tok}.ics")[2]


def test_konto_seite_zeigt_abo_und_erneuert(umgebung):
    import anmeldung
    k = konten.konto("k-ida")
    info = lambda r: {"titel": "Beispielreise", "seite": SEITE}   # noqa: E731
    alt = konten.kalender_token("k-ida", "beispielreise")
    html = anmeldung.konto_seite(k, info)
    assert f"webcal://frieda.beispiel.invalid/beispielreise-0123456789abcdef01234567/api/kalender/{alt}.ics" in html
    assert 'value="kalender_neu"' in html
    konten.kalender_token("k-ida", "beispielreise", erneuern=True)
    assert alt not in anmeldung.konto_seite(k, info)


def test_konnektor_werkzeug_kalender(umgebung):
    import konnektor as kn
    k = konten.konto("k-ida")
    namen = [w["name"] for w in kn.frieda_werkzeuge(k)]
    assert "kalender" in namen
    text, fehler = kn.frieda_werkzeug(k, "kalender", {})
    tok = konten.kalender_token("k-ida", "beispielreise")
    assert not fehler and f"{SEITE}api/kalender/{tok}.ics" in text and "webcal://" in text
    text, fehler = kn.frieda_werkzeug(k, "kalender", {"neu": True})
    assert not fehler and "Neuer Kalender-Link" in text and tok not in text


def test_uhrzeit_im_konnektor_lesbar(umgebung):
    d = yaml.safe_load((BEISPIEL / "plan" / "routen.yaml").read_text(encoding="utf-8"))
    assert d["aufenthalte"]["A-01"]["beginn"] == "16:00"
    import konnektor as kn
    text, _ = kn.frieda_werkzeug(konten.konto("k-ida"), "zeige", {"id": "T-02"})
    assert "16:00–18:00 Uhr" in text
