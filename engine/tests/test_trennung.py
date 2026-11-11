"""Trennung der Tester in einer gemeinsamen Instanz (#380, Meilenstein M5a): Ein Konto sieht, durchsucht, liest und
beschreibt nur Reisen, in denen es Mitglied ist. Zwei Konten, zwei Reisen: A (Ida) ist Organisatorin der Beispielreise,
B (Tom) Organisator nur des Stadtwochenendes. Alle Daten sind erfunden.

Bewusste Grenze (Product Owner, #421): Wer den geheimen Seitenlink kennt, liest ohne Anmeldung; ein angemeldetes
Nicht-Mitglied sieht dabei nicht mehr als ein Gast."""
import datetime
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import anmeldung  # noqa: E402
import bauen  # noqa: E402
import kalender  # noqa: E402
import konnektor as kn  # noqa: E402
import konten  # noqa: E402
import rueckmeldungen as rm  # noqa: E402
import waechter as wa  # noqa: E402
from test_anmeldung import BASIS, SEITE, abruf, anmelden, welt  # noqa: E402,F401  (welt: Fixture)
from conftest import meldet  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
STADT = WURZEL / "beispiel" / "reisen" / "stadtwochenende"
STADT_SEITE = f"{BASIS}/stadtwochenende-89abcdef0123456789abcdef/"
IDA, KARL, TOM = "ida@beispiel.invalid", "karl@beispiel.invalid", "tom@beispiel.invalid"
D = datetime.date


def stadt_bauen(u, status=None, bausteine=None):
    """Das Stadtwochenende neben die Beispielreise der Umgebung bauen und veröffentlichen (eigene Ablage)."""
    quelle = u.seiten.parent / "stadt-quelle"
    shutil.copytree(STADT, quelle)
    if status or bausteine:
        y = yaml.safe_load((quelle / "reise.yaml").read_text(encoding="utf-8"))
        if status:
            y["status"] = {"wert": status, "verlauf": y["status"]["verlauf"] + [
                {"datum": D(2026, 11, 4), "wert": status, "wer": "Tom", "grund": "Test"}]}
        if bausteine:
            y["bausteine"] = bausteine
        (quelle / "reise.yaml").write_text(yaml.safe_dump(y, allow_unicode=True), encoding="utf-8")
    bauen.bauen(quelle, u.seiten / "stadtwochenende")
    (u.ablage / "stadtwochenende").mkdir(parents=True, exist_ok=True)


@pytest.fixture
def zwei(welt, monkeypatch, tmp_path):
    """Umgebung mit beiden Reisen, Konto A (Ida, Beispielreise) und Konto B (Tom, Stadtwochenende)."""
    def neu(status=None, bausteine=None, stadt_status=None, stadt_bausteine=None):
        u = welt(**({"status": status} if status else {}), **({"bausteine": bausteine} if bausteine else {}))
        stadt_bauen(u, stadt_status, stadt_bausteine)
        links = tmp_path / "seiten-beide.json"
        links.write_text(json.dumps({"beispielreise": SEITE, "stadtwochenende": STADT_SEITE}))
        monkeypatch.setenv("KN_SEITENLINKS", str(links))
        monkeypatch.setenv("RM_SEITEN", str(u.seiten))
        monkeypatch.setenv("KN_BASIS", BASIS)
        konten.einladen("beispielreise", "ida", IDA, "organisator", "Ida", "Ida")
        konten.einladen("beispielreise", "karl", KARL, "mitwirkend", "Karl", "Ida")
        konten.einladen("stadtwochenende", "tom", TOM, "organisator", "Tom", "Tom")
        u.a_keks, _ = anmelden(u, IDA)
        u.b_keks, _ = anmelden(u, TOM)
        u.a = konten.konto_per_email(IDA)
        u.b = konten.konto_per_email(TOM)
        return u
    return neu


def pruefwerte():
    """Was aus der Beispielreise nie in einer Antwort an B stehen darf: Namen der Personen, ihre Adressen in den
    Testkonten, Titel und Ordnername. Gelesen aus der veröffentlichten Reise, nicht aus einer festen Liste."""
    d = kn.daten("beispielreise")
    r = d.get("reise") or {}
    namen = [p["name"] for p in r.get("personen") or [] if p.get("name")]
    assert namen and r.get("titel")
    return namen + [IDA, KARL, r["titel"], "beispielreise"]


def verraet(text, werte):
    """Welche Prüfwerte stehen im Text (als ganzes Wort)?"""
    text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
    return [w for w in werte if re.search(r"(?<![\w-])" + re.escape(w) + r"(?![\w])", text)]


def abdruck(*ordner):
    """Inhalt der Ordner als Prüfsumme je Datei: vorher und nachher gleich heißt, nichts wurde geschrieben."""
    aus = {}
    for o in ordner:
        for f in sorted(Path(o).rglob("*")):
            if f.is_file():
                aus[str(f)] = hashlib.sha256(f.read_bytes()).hexdigest()
    return aus


def reise_werkzeuge(k):
    return [w["name"] for w in kn.frieda_werkzeuge(k) if "reise" in w["inputSchema"].get("properties", {})]


# ---------- AC-1: jedes Reise-Werkzeug lehnt eine fremde Reise ab ----------

def test_fremde_reise_ueber_werkzeuge_abgelehnt(zwei):
    u = zwei()
    werte = pruefwerte()
    namen = reise_werkzeuge(u.b)
    assert len(namen) > 20 and "suche" in namen, namen   # lesend wie schreibend, auch suche, zeige, ueberblick
    vorher = abdruck(u.ablage / "beispielreise", u.seiten / "beispielreise")
    fehler = []
    for name in namen:
        text, ist_fehler = kn.frieda_werkzeug(u.b, name, {"reise": "beispielreise", "begriff": "Ida", "id": "T-01"})
        if not (ist_fehler and meldet(text, "konnektor.frieda_werkzeug.1")) or verraet(text, werte):
            fehler.append((name, text[:200]))
    assert not fehler, fehler
    assert not u.schreibweg
    assert abdruck(u.ablage / "beispielreise", u.seiten / "beispielreise") == vorher


# ---------- AC-2: Übersichten nur über eigene Reisen ----------

def test_uebersichten_nur_eigene_reisen(zwei):
    u = zwei()
    werte = pruefwerte()
    konten.verknuepfen(u.b["id"], "unveroeffentlicht", "tom")   # Mitgliedschaft auf einer Reise ohne Seite
    text, fehler = kn.frieda_werkzeug(u.b, "meine_reisen", {})
    assert not fehler and "stadtwochenende" in text and not verraet(text, werte), text
    text, fehler = kn.frieda_werkzeug(u.b, "kalender", {})
    assert not fehler and not verraet(text, werte), text
    abo = kalender.ics_person(anmeldung.kalender_reisen(u.b), konten.kalender_einstellungen(u.b["id"]))
    assert [r for r, *_ in anmeldung.kalender_reisen(u.b)] == ["stadtwochenende"]
    assert not verraet(abo or "", werte)
    # ohne Angabe reise: B hat genau eine veröffentlichte Reise, die gilt
    for name in reise_werkzeuge(u.b):
        if name in kn.SCHREIB_WERKZEUGE or name in kn.ONTOLOGIE_WERKZEUGE:
            continue
        text, _ = kn.frieda_werkzeug(u.b, name, {"begriff": "Ida"})
        assert not verraet(text, werte), (name, text[:300])
    assert not verraet(kn.anleitung_frieda(u.b), werte)
    assert {w["name"] for w in kn.frieda_werkzeuge(u.b)} and all(
        set(w["inputSchema"]["properties"]["reise"].get("enum", [])) <= {"stadtwochenende"}
        for w in kn.frieda_werkzeuge(u.b) if "reise" in w["inputSchema"].get("properties", {}))


# ---------- AC-3: B schreibt nichts in die Beispielreise ----------

SCHREIBVERSUCHE = [
    ("rueckmeldung_geben", {"art": "Kommentar", "ziel": "T-01", "text": "fremd"}),
    ("aufgabe_anlegen", {"titel": "fremde Aufgabe"}),
    ("buchung_anlegen", {"titel": "fremde Buchung", "ziel": "U-01"}),
    ("person_einladen", {"vorname": "Zoe", "email": "zoe@beispiel.invalid", "rolle": "organisator"}),
    ("person_entfernen", {"person": "karl"}),
    ("wert_eintragen", {"id": "U-01", "merkmal": "preis", "wert": "1 €", "quelle": "erfunden"}),
]


def test_fremde_reise_nicht_beschreibbar(zwei):
    u = zwei()
    werte = pruefwerte()
    vorher = abdruck(u.ablage / "beispielreise", u.seiten / "beispielreise")
    mitglieder = konten.zugangsstand("beispielreise")
    for name, args in SCHREIBVERSUCHE:
        text, fehler = kn.frieda_werkzeug(u.b, name, {"reise": "beispielreise", **args})
        assert fehler and meldet(text, "konnektor.frieda_werkzeug.1") and not verraet(text, werte), (name, text)
    assert not u.schreibweg
    assert abdruck(u.ablage / "beispielreise", u.seiten / "beispielreise") == vorher
    assert konten.zugangsstand("beispielreise") == mitglieder


# ---------- AC-4: Rückmeldedienst schreibt nur für Mitglieder ----------

def test_rueckmeldedienst_schreiben_ohne_mitgliedschaft(zwei):
    u = zwei()
    vorher = abdruck(u.ablage / "beispielreise")
    versuche = [
        (f"{u.rurl}/beispielreise/rueckmeldungen", {"art": "Kommentar", "ziel": "T-01", "text": "fremd", "name": "Ida"}),
        (f"{u.rurl}/beispielreise/aufgaben", {"titel": "fremde Aufgabe", "name": "Ida"}),
        (f"{u.rurl}/beispielreise/status", {"status": "fest"}),
    ]
    for url, body in versuche:
        s, _, t = abruf(url, "POST", cookie=u.b_keks, json_body=body)
        assert s == 403, (url, s, t)
        s, _, t = abruf(url, "POST", json_body=body)
        assert s == 401, (url, s, t)
    # Beleg zur Buchung der Beispielreise (Datei als Body)
    for keks, erwartet in ((u.b_keks, 403), (None, 401)):
        s, _, t = _beleg(u, keks)
        assert s == erwartet, (s, t)
    assert abdruck(u.ablage / "beispielreise") == vorher


def _beleg(u, keks):
    import http.client
    import urllib.parse
    t = urllib.parse.urlsplit(u.rurl)
    c = http.client.HTTPConnection(t.hostname, t.port, timeout=10)
    h = {"Content-Type": "application/pdf", "Origin": BASIS, "Accept-Language": "de"}
    if keks:
        h["Cookie"] = f"__Host-frieda={keks}"
    c.request("POST", "/beispielreise/belege/B-01?name=Ida&dateiname=x.pdf", body=b"%PDF-", headers=h)
    r = c.getresponse()
    return r.status, r.getheaders(), r.read().decode()


# ---------- AC-5: Meldungen und Belege ----------

def test_meldungen_und_belege_nur_eigene_reisen(zwei):
    u = zwei()
    werte = pruefwerte()
    rm.meldung_anlegen(u.ablage / "beispielreise", ["Karl", "Ida"], "konflikt", "T-01", "Fähre buchen für Karl und Ida")
    rm.meldung_anlegen(u.ablage / "stadtwochenende", ["Tom"], "konflikt", "T-01", "Kuchen mitbringen")
    ms = rm.meldungen_des_kontos(u.b)
    assert ms and {m["reise"] for m in ms} <= {"stadtwochenende", None}
    assert not verraet([m["text"] for m in ms], werte)
    text, _ = kn.frieda_werkzeug(u.b, "meine_reisen", {})
    assert "Kuchen" in text and not verraet(text, werte)
    s, _, t = abruf(f"{u.rurl}/beispielreise/ich", cookie=u.b_keks)
    ich = json.loads(t)
    assert s == 200 and ich["person"] is None and ich["meldungen"] == []
    gast = abruf(f"{u.rurl}/beispielreise/belege")
    fremd = abruf(f"{u.rurl}/beispielreise/belege", cookie=u.b_keks)
    assert fremd[0] == gast[0] and json.loads(fremd[2]) == json.loads(gast[2])
    assert not verraet(fremd[2], [IDA, KARL])


# ---------- AC-6: Wächter und Erinnerer melden nur an die eigene Reise ----------

def test_waechter_und_erinnerer_nur_an_eigene_reise(zwei):
    bausteine = ["rueckmeldungen", "aufgaben", "waechter"]
    u = zwei(status="fest", bausteine=["varianten", "karte", "tagesseiten", "rueckmeldungen", "fragen", "aufgaben",
                                       "wuensche", "waechter"],
             stadt_status="fest", stadt_bausteine=bausteine)
    for reise, wer in (("beispielreise", "Karl"), ("stadtwochenende", "Tom")):
        a, fehler = rm.aufgabe_anlegen(u.ablage / reise, {"name": wer, "titel": f"Frist {wer}", "frist": "2026-11-10",
                                                         "zustaendig": wer})
        assert not fehler, fehler
    personen = {r: {p["name"] for p in (kn.daten(r).get("reise") or {}).get("personen") or []}
                for r in ("beispielreise", "stadtwochenende")}
    gesamt = 0
    for reise in ("beispielreise", "stadtwochenende"):
        erg = wa.lauf_reise(reise, D(2026, 11, 7))
        for m in erg["meldungen"]:
            assert set(m["an"]) <= personen[reise], (reise, m)
            gesamt += 1
    assert gesamt >= 2
    ms = rm.meldungen_des_kontos(u.b)
    assert ms and all(m["reise"] in ("stadtwochenende", None) for m in ms)
    assert not verraet([m["text"] for m in ms], pruefwerte())
    assert all(m["reise"] in ("beispielreise", None) for m in rm.meldungen_des_kontos(u.a))


# ---------- AC-7: bewusste Grenze beim Lesen über den Seitenlink (#421) ----------

def test_lesen_per_seitenlink_nicht_mehr_als_gast(zwei):
    u = zwei()
    for was in ("stand", "brett", "packstand"):
        gast = abruf(f"{u.rurl}/beispielreise/{was}")
        fremd = abruf(f"{u.rurl}/beispielreise/{was}", cookie=u.b_keks)
        assert gast[0] == 200, (was, gast)
        assert (fremd[0], json.loads(fremd[2])) == (gast[0], json.loads(gast[2])), was


# ---------- AC-4 und AC-5 ergänzt (Validierung): Entscheidung auf dem Brett, einzelner Beleg ----------

def test_entscheidung_auf_dem_brett_ohne_mitgliedschaft(zwei):
    """Einplanen eines Wunsches ist auf der Seite die Entscheidung der Organisator:in; B darf sie nicht treffen."""
    u = zwei()
    vorher = abdruck(u.ablage / "beispielreise")
    url = f"{u.rurl}/beispielreise/rueckmeldungen/R-20261104-120000-abcd"
    body = {"eingeplant": True, "bezug": "T-01", "name": "Ida"}
    s, _, t = abruf(url, "PATCH", cookie=u.b_keks, json_body=body)
    assert s == 403, (s, t)
    s, _, t = abruf(url, "PATCH", json_body=body)
    assert s in (401, 403), (s, t)
    assert abdruck(u.ablage / "beispielreise") == vorher


def test_einzelner_beleg_wie_ein_gast(zwei):
    """Ein einzelner Beleg der Beispielreise: B sieht ihn genau wie ein Gast (#421: für alle freigegeben ja, nur für
    Beteiligte nein) und ändert ihn nicht."""
    import belege as bl
    u = zwei()
    o = u.ablage / "beispielreise"
    b, nein = bl.ablegen(o, "B-01", "Ida", "fahrkarte.pdf", b"%PDF-1.4\n% Beispielwert\n")
    assert nein is None, nein
    url = f"{u.rurl}/beispielreise/belege/{b['id']}"
    for sichtbar, erwartet in (("beteiligte", 404), ("alle", 200)):
        d = bl.lesen(o)
        d["belege"][0]["sichtbar"] = sichtbar
        bl.speichern(o, d)
        gast = abruf(url)
        fremd = abruf(url, cookie=u.b_keks)
        assert fremd[0] == gast[0] == erwartet, (sichtbar, fremd[0], gast[0])
        assert fremd[2] == gast[2]
        assert not verraet(fremd[2], [IDA, KARL])
    vorher = abdruck(o)
    s, _, t = abruf(url, "PATCH", cookie=u.b_keks, json_body={"sichtbar": "beteiligte", "name": "Ida"})
    assert s in (401, 403), (s, t)
    assert abdruck(o) == vorher
    eigen = abruf(url, cookie=u.a_keks)
    assert eigen[0] == 200
