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


# ---------- Persönlicher Kalender: Einstellungen (kalender.py) ----------

def test_einstellungen_filtern_und_erinnern(daten):
    aufgaben = [{"id": "AG-01", "titel": "Rucksack packen", "frist": "2027-05-10", "status": "offen", "zustaendig": "Karl"},
                {"id": "AG-02", "titel": "Karten kaufen", "frist": "2027-05-11", "status": "offen", "zustaendig": "ida"}]
    reisen = [("beispielreise", daten, aufgaben, "Ida")]
    alles = kalender.ics_person(reisen, {}, jetzt=JETZT)
    assert "Rucksack packen" in alles and "Karten kaufen" in alles and "BEGIN:VALARM" not in alles
    t = kalender.ics_person(reisen, {"sorten": ["aufgaben", "fahrten", "unbekannt"], "nur_meine_aufgaben": True,
                                     "erinnerung_fristen": "-PT15H", "erinnerung_termine": "-PT30M"}, jetzt=JETZT)
    entfaltet = t.replace("\r\n ", "")
    assert "Karten kaufen" in entfaltet and "Rucksack packen" not in entfaltet          # nur eigene, Name ohne Groß/klein
    assert "UID:T-01" not in entfaltet and "UID:E-20-2027-05-14.beispielreise@frieda" in entfaltet
    assert entfaltet.count("TRIGGER:-PT15H") == 1 and entfaltet.count("TRIGGER:-PT30M") == 1
    assert "X-WR-CALNAME:Frieda – meine Reisen" in entfaltet
    assert kalender.ics_person(reisen, {"reisen_aus": ["beispielreise"]}, jetzt=JETZT).count("BEGIN:VEVENT") == 0
    # zwei Reisen: der Titel nennt die Reise, UIDs bleiben verschieden
    zwei = kalender.ics_person(reisen + [("zweite-reise", daten, [], "Ida")], {"sorten": ["tage"]}, jetzt=JETZT).replace("\r\n ", "")
    assert "UID:T-01.zweite-reise@frieda" in zwei and "(Beispielreise – Malerweg in vier Tagen)" in zwei
    assert kalender.einstellungen({"erinnerung_fristen": "-P99D", "reisen_aus": "x"}) == kalender.VORGABE


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
    t = konten.kalender_token("k-ida")
    assert t == konten.kalender_token("k-ida") and len(t) == 40 and t != konten.kalender_token("k-karl")
    assert konten.kalender_konto(t)["id"] == "k-ida" and konten.kalender_konto("x" * 40) is None
    neu = konten.kalender_token("k-ida", erneuern=True)
    assert neu != t and konten.kalender_konto(t) is None and konten.kalender_konto(neu)["id"] == "k-ida"
    assert konten.kalender_einstellungen("k-ida") == kalender.VORGABE
    e = konten.kalender_einstellungen("k-ida", {"sorten": ["tage"], "reisen_aus": ["beispielreise"]})
    assert konten.kalender_einstellungen("k-ida") == e and e["sorten"] == ["tage"]
    assert konten.kalender_token("k-ida") == neu                         # Einstellungen ändern den Link nicht
    k = konten.kalender_token("k-karl")
    konten.sperren("k-karl")
    assert konten.kalender_konto(k) is None
    with pytest.raises(konten.KontoFehler):
        konten.kalender_token("k-niemand")
    assert kalender.abo_url("https://frieda.beispiel.invalid/fr-mcp/", "abc") == "https://frieda.beispiel.invalid/fr-mcp/kalender/abc.ics"
    assert kalender.webcal("https://frieda.beispiel.invalid/fr-mcp/kalender/abc.ics").startswith("webcal://frieda.beispiel.invalid/")


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
    monkeypatch.setenv("FR_MAIL_DATEI", str(tmp_path / "mails.jsonl"))
    monkeypatch.delenv("KN_BASIS", raising=False)
    u.mails = tmp_path / "mails.jsonl"
    v = konten.db()
    v.execute("INSERT INTO konten (id, email, name, angelegt) VALUES ('k-ida', 'ida@beispiel.invalid', 'Ida', '2026-10-29')")
    v.commit()
    v.close()
    konten.verknuepfen("k-ida", "beispielreise", "ida")
    yield u
    u.schliessen()


def test_dienst_liefert_datei(umgebung):
    u = umgebung
    s, h, t = holen(f"{u.rurl}/beispielreise/kalender.ics")
    assert s == 200 and h["Content-Type"] == "text/calendar; charset=utf-8" and "attachment" in h["Content-Disposition"]
    assert "UID:T-01.beispielreise@frieda" in t
    s, h, t = holen(f"{u.rurl}/beispielreise/kalender.ics?id=T-02")
    assert s == 200 and t.count("BEGIN:VEVENT") == 1 and 'beispielreise-T-02.ics' in h["Content-Disposition"]
    assert holen(f"{u.rurl}/beispielreise/kalender.ics?id=T-05")[0] == 404
    assert holen(f"{u.rurl}/beispielreise/kalender.ics?id=%22%3B")[0] == 400


def test_abo_ueber_den_konnektor(umgebung):
    u = umgebung
    tok = konten.kalender_token("k-ida")
    (u.o / "aufgaben.json").write_text(json.dumps({"naechste": 2, "aufgaben": [
        {"id": "AG-01", "titel": "Rucksack packen", "frist": "2027-05-10", "status": "offen", "zustaendig": "Karl"}]}))
    s, h, t = holen(f"{u.kurl}/kalender/{tok}.ics")
    assert s == 200 and h["Content-Type"] == "text/calendar; charset=utf-8" and "Content-Disposition" not in h
    assert "UID:T-01.beispielreise@frieda" in t and "Aufgabe fällig: Rucksack packen" in t
    konten.kalender_einstellungen("k-ida", {"sorten": ["aufgaben"], "nur_meine_aufgaben": True})
    assert "BEGIN:VEVENT" not in holen(f"{u.kurl}/kalender/{tok}.ics")[2]     # Karl ist zuständig, nicht Ida
    assert holen(f"{u.kurl}/kalender/{'0' * 40}.ics")[0] == 404


def anmelden_ida(u):
    konten.code_anfordern("ida@beispiel.invalid")
    m = json.loads((u.mails).read_text().splitlines()[-1])
    import re
    code = re.search(r"(\d{3}) (\d{3})", m["text"]).expand(r"\1\2")
    token, _ = konten.anmelden("ida@beispiel.invalid", code)
    return {"Cookie": f"__Host-frieda={token}", "Origin": "https://frieda.beispiel.invalid"}


def test_konto_seite_kalender(umgebung, monkeypatch):
    import anmeldung
    monkeypatch.setenv("KN_BASIS", "https://frieda.beispiel.invalid/fr-mcp")
    kopf = anmelden_ida(umgebung)
    info = lambda r: {"titel": "Beispielreise", "seite": SEITE}   # noqa: E731
    code, _, body = anmeldung.bearbeiten("GET", "/konto", kopf, b"", "127.0.0.1", info)
    html = body.decode()
    alt = konten.kalender_token("k-ida")
    assert code == 200 and f"webcal://frieda.beispiel.invalid/fr-mcp/kalender/{alt}.ics" in html
    assert "https://calendar.google.com/calendar/render?cid=webcal%3A%2F%2Ffrieda.beispiel.invalid" in html
    assert "https://outlook.live.com/calendar/0/addfromweb?url=https%3A%2F%2Ffrieda.beispiel.invalid" in html
    assert 'href="/konto?kalender=datei"' in html and 'name="sorte_tage" value="ja" checked' in html
    assert 'name="reise_beispielreise" value="ja" checked' in html and "1 week before at 9:00" in html
    # Download mit den Einstellungen des Kontos
    code, k_, body = anmeldung.bearbeiten("GET", "/konto?kalender=datei", kopf, b"", "127.0.0.1", info)
    assert code == 200 and ("Content-Disposition", 'attachment; filename="frieda-reisen.ics"') in k_ and b"BEGIN:VCALENDAR" in body
    # Einstellungen speichern: fehlende Häkchen sind aus
    form = "aktion=kalender_einstellungen&sorte_tage=ja&sorte_fahrten=ja&erinnerung_termine=-PT1H&reise_beispielreise=ja"
    code, _, body = anmeldung.bearbeiten("POST", "/konto", kopf, form.encode(), "127.0.0.1", info)
    assert code == 200 and "Calendar settings saved" in body.decode()
    e = konten.kalender_einstellungen("k-ida")
    assert e["sorten"] == ["tage", "fahrten"] and e["erinnerung_termine"] == "-PT1H" and e["reisen_aus"] == []
    code, _, body = anmeldung.bearbeiten("GET", "/konto?kalender=datei", kopf, b"", "127.0.0.1", info)
    assert b"Unterkunft" not in body.replace(b"\r\n ", b"") and b"TRIGGER:-PT1H" in body
    anmeldung.bearbeiten("POST", "/konto", kopf, b"aktion=kalender_einstellungen", "127.0.0.1", info)
    assert konten.kalender_einstellungen("k-ida")["reisen_aus"] == ["beispielreise"]
    # Neuer Link
    anmeldung.bearbeiten("POST", "/konto", kopf, b"aktion=kalender_neu", "127.0.0.1", info)
    assert konten.kalender_token("k-ida") != alt and konten.kalender_konto(alt) is None


def test_konnektor_werkzeug_kalender(umgebung, monkeypatch):
    import konnektor as kn
    k = konten.konto("k-ida")
    assert "kalender" in [w["name"] for w in kn.frieda_werkzeuge(k)]
    text, fehler = kn.frieda_werkzeug(k, "kalender", {})
    assert fehler and "nicht eingerichtet" in text
    monkeypatch.setenv("KN_BASIS", "https://frieda.beispiel.invalid/fr-mcp")
    text, fehler = kn.frieda_werkzeug(k, "kalender", {})
    tok = konten.kalender_token("k-ida")
    assert not fehler and f"https://frieda.beispiel.invalid/fr-mcp/kalender/{tok}.ics" in text and "Mein Konto" in text
    assert f"webcal://frieda.beispiel.invalid/fr-mcp/kalender/{tok}.ics" in text
    assert "calendar.google.com/calendar/render?cid=webcal" in text and "outlook.live.com/calendar/0/addfromweb" in text
    text, fehler = kn.frieda_werkzeug(k, "kalender", {"neu": True})
    assert not fehler and "Neuer Kalender-Link" in text and tok not in text


def test_uhrzeit_im_konnektor_lesbar(umgebung):
    d = yaml.safe_load((BEISPIEL / "plan" / "routen.yaml").read_text(encoding="utf-8"))
    assert d["aufenthalte"]["A-01"]["beginn"] == "16:00"
    import konnektor as kn
    text, _ = kn.frieda_werkzeug(konten.konto("k-ida"), "zeige", {"id": "T-02"})
    assert "16:00–18:00 Uhr" in text


def test_kalender_in_der_sprache_der_reise(daten):
    """Titel, Beschreibungen und Namen folgen der Sprache der Reise (ADR-0006, M10); Deutsch bleibt wörtlich wie bisher."""
    de = {e["uid"]: e for e in kalender.eintraege(daten)}
    assert de["T-01"]["titel"].startswith("Tag 1:")
    en_daten = json.loads(json.dumps(daten))
    en_daten["reise"]["sprache"] = "en"
    en = {e["uid"]: e for e in kalender.eintraege(en_daten)}
    assert en["T-01"]["titel"].startswith("Day 1:") and "Tag" not in en["T-01"]["titel"].split(":")[0]
    assert any(e["titel"].startswith("Overnight stay: ") for e in en.values())
    assert any("Booking booked" in e["text"] for e in en.values()) and any("Buchung gebucht" in e["text"] for e in de.values())
    assert not any(e["titel"].startswith(("Übernachtung", "Frist:")) for e in en.values())
    assert kalender.sorten("en")["unterkuenfte"] == "Accommodations" and kalender.sorten()["unterkuenfte"] == "Unterkünfte"
    assert list(kalender.erinnerungen(kalender.ERINNERUNG_FRISTEN_SCHLUESSEL, "en").values())[1] == "the day before at 9:00"
    assert "X-WR-CALNAME:Frieda – my trips" in kalender.ics_person([("beispielreise", en_daten, [], "Ida")], {}, jetzt=JETZT, sprache="en")
    assert "X-WR-CALNAME:Frieda – meine Reisen" in kalender.ics_person([("beispielreise", daten, [], "Ida")], {}, jetzt=JETZT)


# ---------- Abo wie Kalender-Apps es abrufen (Apple, Google, Outlook) ----------
# Apple-Geräte (dataaccessd, CalendarAgent) und Prüfdienste fragen vor dem Laden mit HEAD, OPTIONS oder PROPFIND, ob es die
# Adresse gibt und ob sie CalDAV spricht. Ein 501 darauf ließ das Abo scheitern (Fehler im Apple Kalender, 1.11.2026).

APPLE = {"User-Agent": "iOS/18.1 (22B83) dataaccessd/1.0", "Accept": "*/*"}


def anfrage(url, methode="GET", kopf=None):
    r = urllib.request.Request(url, method=methode, headers={**APPLE, **(kopf or {})})
    try:
        with urllib.request.urlopen(r) as a:
            return a.status, dict(a.headers), a.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def test_abo_fuer_kalender_apps(umgebung):
    url = f"{umgebung.kurl}/kalender/{konten.kalender_token('k-ida')}.ics"
    s, h, body = anfrage(url)
    assert s == 200 and h["Content-Type"] == "text/calendar; charset=utf-8" and body.startswith(b"BEGIN:VCALENDAR\r\n")
    assert h["Cache-Control"] == "private, no-cache" and h["ETag"].startswith('"') and int(h["Content-Length"]) == len(body)
    # HEAD: dieselben Kopfzeilen, kein Inhalt
    s, hk, leer = anfrage(url, "HEAD")
    assert s == 200 and leer == b"" and hk["Content-Length"] == h["Content-Length"] and hk["ETag"] == h["ETag"]
    # OPTIONS: welche Methoden gehen; PROPFIND und andere WebDAV-Methoden: 405 statt 501, damit die App beim Abo bleibt
    s, ho, _ = anfrage(url, "OPTIONS")
    assert s == 204 and ho["Allow"] == "GET, HEAD, OPTIONS" and "Access-Control-Allow-Origin" not in ho
    for m in ("PROPFIND", "REPORT", "PUT", "MKCALENDAR"):
        s, hm, _ = anfrage(url, m, {"Depth": "0"})
        assert (s, hm["Allow"]) == (405, "GET, HEAD, OPTIONS"), m
    # Unbekanntes Wort: auch mit HEAD 404, nicht 501
    assert anfrage(f"{umgebung.kurl}/kalender/{'0' * 40}.ics", "HEAD")[0] == 404


def test_abo_bedingter_abruf(umgebung):
    url = f"{umgebung.kurl}/kalender/{konten.kalender_token('k-ida')}.ics"
    tag = anfrage(url)[1]["ETag"]
    s, h, body = anfrage(url, kopf={"If-None-Match": tag})
    assert s == 304 and body == b"" and h["ETag"] == tag
    assert anfrage(url, kopf={"If-None-Match": '"anders", ' + tag})[0] == 304
    assert anfrage(url)[1]["ETag"] == tag                                   # neuer DTSTAMP ändert das ETag nicht
    konten.kalender_einstellungen("k-ida", {"sorten": ["tage"]})
    s, h, _ = anfrage(url, kopf={"If-None-Match": tag})
    assert s == 200 and h["ETag"] != tag                                    # anderer Inhalt: neu laden


def test_abo_in_der_sprache_des_kontos(umgebung):
    url = f"{umgebung.kurl}/kalender/{konten.kalender_token('k-ida')}.ics"
    v = konten.db()
    v.execute("UPDATE konten SET sprache = 'de' WHERE id = 'k-ida'")
    v.commit()
    v.close()
    assert b"X-WR-CALNAME:Frieda \xe2\x80\x93 meine Reisen" in anfrage(url)[2]   # Kalender-Apps schicken keine Sprache mit


def test_datei_der_reise_mit_head(umgebung):
    s, h, body = anfrage(f"{umgebung.rurl}/beispielreise/kalender.ics", "HEAD")
    assert s == 200 and body == b"" and h["Content-Type"] == "text/calendar; charset=utf-8" and int(h["Content-Length"]) > 0


def test_abo_ist_gueltiges_icalendar(umgebung):
    """Unabhängige Prüfung mit der Bibliothek icalendar (fehlt sie, wird übersprungen)."""
    icalendar = pytest.importorskip("icalendar")
    url = f"{umgebung.kurl}/kalender/{konten.kalender_token('k-ida')}.ics"
    c = icalendar.Calendar.from_ical(anfrage(url)[2])
    assert c["VERSION"] == "2.0" and c.get("NAME") == c.get("X-WR-CALNAME")
    ev = c.walk("VEVENT")
    assert ev and all(e.get("UID") and e.get("DTSTAMP") and e.get("DTSTART") for e in ev)
    assert len({str(e["UID"]) for e in ev}) == len(ev)
    # Leerer Kalender (alles abgewählt): bleibt gültig (RFC 5545 verlangt einen Bestandteil)
    konten.kalender_einstellungen("k-ida", {"sorten": []})
    leer = anfrage(url)[2]
    assert b"BEGIN:VEVENT" not in leer and b"BEGIN:VTIMEZONE" in leer
    assert icalendar.Calendar.from_ical(leer).walk("VTIMEZONE")


def test_links_je_kalender_programm():
    url = "https://frieda.beispiel.invalid/fr-mcp/kalender/abc.ics"
    assert kalender.webcal(url) == "webcal://frieda.beispiel.invalid/fr-mcp/kalender/abc.ics"
    assert kalender.google(url) == ("https://calendar.google.com/calendar/render?cid="
                                    "webcal%3A%2F%2Ffrieda.beispiel.invalid%2Ffr-mcp%2Fkalender%2Fabc.ics")
    assert kalender.outlook(url, "Frieda – meine Reisen") == (
        "https://outlook.live.com/calendar/0/addfromweb?url=https%3A%2F%2Ffrieda.beispiel.invalid%2Ffr-mcp%2Fkalender%2Fabc.ics"
        "&name=Frieda+%E2%80%93+meine+Reisen")
