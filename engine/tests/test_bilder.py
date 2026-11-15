"""Tests für Bilder Stufe 1, Paket P1 (#455, #581; Spec docs/specs/oberflaeche/bilder-455-stufe1.md): Liste plan/bilder.yaml mit
Kennung BI-NN, Abruf aus Wikimedia Commons und Wikidata, Lizenz-Positivliste, zwei WebP-Fassungen, Rechte, Werkzeuge,
Hotlink-Sperre, bilder_nachziehen und BI- im Text. Kein Test geht ins Netz: urllib.request.urlopen wird ersetzt, Commons- und
Wikidata-Antworten sind Fixtures in dieser Datei, das Testbild entsteht mit Pillow.

Was diese Tests als Schnittstelle festlegen (über die Spec hinaus):
  bilder.Abgelehnt(schluessel, **werte)         Ablehnung des Moduls; .schluessel ist bild.abgelehnt.*
  bilder.lizenz_pruefen(extmetadata) -> dict     {"lizenz", "lizenz_url", "gemeinfrei"}; wirft Abgelehnt("bild.abgelehnt.lizenz")
  bilder.urheber_saeubern(html) -> str           reiner Text
  bilder.abrufen(commons=None, wikidata=None) -> dict   Netzabruf (Metadaten und Bytes der 1600er-Fassung):
                                                 {"datei", "urheber", "lizenz", "lizenz_url", "seite", "gemeinfrei", "inhalt"}
  bilder.ZEITLIMIT = 20, bilder.MAX_META = 1 MB, bilder.MAX_BILD = 15 MB, bilder.PAUSE (Wartezeit vor der Wiederholung)
  bilder.FASSUNGEN = {"klein": 480, "gross": 1600}
  sb.bild_hinzufuegen(reise_dir, wer, args) / sb.bild_aendern(reise_dir, wer, args) -> (Titel, Text); Titel beginnt mit BI-NN
  sb.bild_vorab(s, reise, anfrage, vorab)       Abruf vor der Sperre; der Unterprozess liest das Ergebnis über FR_BILD_VORAB
  Antwort des Schreibwegs an den Konnektor: Feld "vorschau" (Base64 der kleinen Fassung) -> MitBild an Claude
  neu.bilder_nachziehen(reise_dir, schreiben=True) -> Meldungen; läuft in neu.nachziehen
  Baufehler: pruefung.bauen.bild_fremd (fremde Bildadresse), pruefung.bauen.bild_unbekannt (BI- ohne Eintrag)
"""
import base64
import io
import json
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bauen  # noqa: E402
import neu  # noqa: E402
import reise as rg  # noqa: E402
import routen  # noqa: E402
import schreiben as sb  # noqa: E402
from conftest import meldet  # noqa: E402
from test_konnektor import dienst, schreibweg, seiten  # noqa: E402,F401  (Fixtures)
from test_schreiben import repo  # noqa: E402,F401  (Fixture)

WURZEL = Path(__file__).resolve().parent.parent.parent
WANDERUNG = WURZEL / "beispiel" / "reisen" / "beispielreise"
STADT = WURZEL / "beispiel" / "reisen" / "stadtwochenende"
IDA = {"name": "Ida", "rolle": "organisator"}
KARL = {"name": "Karl", "rolle": "mitwirkend"}


def bilder_modul():
    import bilder
    return bilder


# ---------- Fixtures: Commons, Wikidata, Testbild ----------

def bild_bytes(breite=2000, hoehe=1250, art="JPEG"):
    from PIL import Image
    puffer = io.BytesIO()
    Image.new("RGB", (breite, hoehe), (120, 140, 90)).save(puffer, art)
    return puffer.getvalue()


def meta(lizenz="CC BY-SA 4.0", url="https://creativecommons.org/licenses/by-sa/4.0", artist='<a href="//commons.wikimedia.org/wiki/User:Max">Max Muster</a>'):
    m = {"Artist": {"value": artist}}
    if lizenz is not None:
        m["LicenseShortName"] = {"value": lizenz}
    if url is not None:
        m["LicenseUrl"] = {"value": url}
    return m


def commons_antwort(datei="Basteibruecke.jpg", extmetadata=None, mime="image/jpeg", fehlt=False):
    if fehlt:
        return {"query": {"pages": {"-1": {"title": f"File:{datei}", "missing": ""}}}}
    return {"query": {"pages": {"42": {"title": f"File:{datei}", "imageinfo": [{
        "thumburl": f"https://upload.wikimedia.org/thumb/{datei}/1600px-{datei}", "thumbwidth": 1600, "thumbheight": 1000,
        "url": f"https://upload.wikimedia.org/{datei}", "descriptionurl": f"https://commons.wikimedia.org/wiki/File:{datei}",
        "mime": mime, "extmetadata": extmetadata if extmetadata is not None else meta()}]}}}}


class Antwort:
    def __init__(self, inhalt, status=200):
        self.inhalt, self.status, self.headers = inhalt, status, {"Content-Length": str(len(inhalt))}

    def read(self, n=-1):
        return self.inhalt if n is None or n < 0 else self.inhalt[:n]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Netz:
    """Ersetzt urllib.request.urlopen: Commons-API (prop=imageinfo), Wikidata (wbgetclaims) und die Bilddatei.
    fehler: Liste von Ausnahmen oder HTTP-Codes, die nacheinander vor der echten Antwort geworfen werden."""

    def __init__(self, monkeypatch, commons=None, wikidata=None, bild=None, fehler=()):
        self.commons = commons if commons is not None else commons_antwort()
        self.wikidata = wikidata if wikidata is not None else {"claims": {"P18": [{"mainsnak": {"datavalue": {"value": "Basteibruecke.jpg"}}}]}}
        self.bild = bild if bild is not None else bild_bytes()
        self.fehler = list(fehler)
        self.aufrufe = []      # (url, user_agent, timeout)
        monkeypatch.setattr(urllib.request, "urlopen", self.urlopen)
        monkeypatch.setattr(bilder_modul().time, "sleep", lambda s: None)

    def urlopen(self, req, timeout=None, **kw):
        url = req.full_url if isinstance(req, urllib.request.Request) else req
        ua = req.get_header("User-agent") if isinstance(req, urllib.request.Request) else None
        self.aufrufe.append((url, ua, timeout))
        if self.fehler:
            f = self.fehler.pop(0)
            if isinstance(f, int):
                raise urllib.error.HTTPError(url, f, "Fehler", {}, None)
            raise f
        if "wbgetclaims" in url:
            return Antwort(json.dumps(self.wikidata).encode())
        if "imageinfo" in url:
            return Antwort(json.dumps(self.commons).encode() if isinstance(self.commons, dict) else self.commons)
        return Antwort(self.bild)


@pytest.fixture
def wanderung(tmp_path):
    ziel = tmp_path / "beispielreise"
    shutil.copytree(WANDERUNG, ziel)
    return ziel


@pytest.fixture
def stadt(tmp_path):
    ziel = tmp_path / "stadtwochenende"
    shutil.copytree(STADT, ziel)
    return ziel


def liste(ordner):
    p = ordner / "plan" / "bilder.yaml"
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("bilder") or [] if p.exists() else []


def eintrag(ordner, bid):
    return next(b for b in liste(ordner) if b["id"] == bid)


def neu_hinzu(ordner, wer=IDA, **args):
    titel, text = sb.bild_hinzufuegen(ordner, wer, {"commons": "Basteibruecke.jpg", "zu": "E-01", **args})
    return titel.split()[0], text


# ---------- Lizenz und Urheber (V8, V9) ----------

@pytest.mark.parametrize("lizenz, url", [("CC0", "https://creativecommons.org/publicdomain/zero/1.0"), ("Public domain", None),
                                         ("PD", None), ("CC BY 3.0", "https://creativecommons.org/licenses/by/3.0"),
                                         ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0"),
                                         ("CC BY-SA 2.5", "https://creativecommons.org/licenses/by-sa/2.5")])
def test_lizenz_positivliste_nimmt_an(lizenz, url):
    r = bilder_modul().lizenz_pruefen(meta(lizenz, url))
    assert r["lizenz"] == lizenz
    assert r["gemeinfrei"] == (lizenz in ("CC0", "Public domain", "PD"))


@pytest.mark.parametrize("lizenz", ["Free Art License", "FAL", "CC BY-NC 4.0", "CC BY-NC-SA 3.0", "CC BY-ND 4.0", "GFDL",
                                    "Copyrighted", "", None])
def test_lizenz_ausserhalb_der_positivliste_wird_abgelehnt(lizenz):
    b = bilder_modul()
    with pytest.raises(b.Abgelehnt) as e:
        b.lizenz_pruefen(meta(lizenz, None))
    assert e.value.schluessel == "bild.abgelehnt.lizenz"


def test_urheber_wird_zu_text_gesaeubert():
    t = bilder_modul().urheber_saeubern('<a href="//x">Max <b>Muster</b></a><script>alert(1)</script><img src=x onerror=y>')
    assert t == "Max Muster" and "<" not in t and "alert" not in t


# ---------- Abruf (V7, AC-5) ----------

def test_abruf_mit_user_agent_zeitlimit_und_ohne_original(monkeypatch):
    import instanz
    b = bilder_modul()
    netz = Netz(monkeypatch)
    r = b.abrufen(commons="Basteibruecke.jpg")
    assert r["datei"] == "Basteibruecke.jpg" and r["urheber"] == "Max Muster" and r["lizenz"] == "CC BY-SA 4.0"
    assert r["seite"] == "https://commons.wikimedia.org/wiki/File:Basteibruecke.jpg" and r["inhalt"] == netz.bild
    assert b.ZEITLIMIT == 20
    assert all(ua == instanz.kennung() and t == 20 for _, ua, t in netz.aufrufe), netz.aufrufe
    api = urllib.parse.parse_qs(urllib.parse.urlsplit(netz.aufrufe[0][0]).query)
    assert api["iiurlwidth"] == ["1600"] and "extmetadata" in api["iiprop"][0]
    assert netz.aufrufe[-1][0].startswith("https://upload.wikimedia.org/thumb/")      # die 1600er-Fassung, nie das Original


def test_abruf_wiederholt_einmal_nach_429(monkeypatch):
    netz = Netz(monkeypatch, fehler=[429])
    assert bilder_modul().abrufen(commons="Basteibruecke.jpg")["lizenz"] == "CC BY-SA 4.0"
    assert len(netz.aufrufe) == 3


@pytest.mark.parametrize("fehler", [[503, 503], [502, 500], [TimeoutError(), TimeoutError()],
                                    [urllib.error.URLError("weg"), urllib.error.URLError("weg")]])
def test_abruf_dauerhaft_gestoert_lehnt_ab(monkeypatch, fehler):
    b = bilder_modul()
    Netz(monkeypatch, fehler=fehler)
    with pytest.raises(b.Abgelehnt) as e:
        b.abrufen(commons="Basteibruecke.jpg")
    assert e.value.schluessel == "bild.abgelehnt.netz"


def test_abruf_wikidata_liest_p18(monkeypatch):
    netz = Netz(monkeypatch)
    r = bilder_modul().abrufen(wikidata="Q12345")
    assert r["datei"] == "Basteibruecke.jpg"
    assert "wbgetclaims" in netz.aufrufe[0][0] and "Q12345" in netz.aufrufe[0][0] and "P18" in netz.aufrufe[0][0]


@pytest.mark.parametrize("fall, schluessel", [
    ("ohne_p18", "bild.abgelehnt.nicht_gefunden"),
    ("fehlt", "bild.abgelehnt.nicht_gefunden"),
    ("svg", "bild.abgelehnt.kein_rasterbild"),
    ("pdf", "bild.abgelehnt.kein_rasterbild"),
    ("kaputt", "bild.abgelehnt.kein_rasterbild"),
    ("meta_gross", "bild.abgelehnt.zu_gross"),
])
def test_abruf_lehnt_ab(monkeypatch, fall, schluessel):
    b = bilder_modul()
    kw = {"ohne_p18": {"wikidata": {"claims": {}}}, "fehlt": {"commons": commons_antwort(fehlt=True)},
          "svg": {"commons": commons_antwort("X.svg", mime="image/svg+xml"), "bild": b'<svg xmlns="http://www.w3.org/2000/svg"/>'},
          "pdf": {"commons": commons_antwort("X.pdf", mime="application/pdf"), "bild": b"%PDF-1.4\n"},
          "kaputt": {"bild": b"\xff\xd8\xff\xe0kaputt"},
          "meta_gross": {"commons": b"{" + b" " * (b.MAX_META + 10) + b"}"}}[fall]
    Netz(monkeypatch, **kw)
    with pytest.raises(b.Abgelehnt) as e:
        b.abrufen(**({"wikidata": "Q1"} if fall == "ohne_p18" else {"commons": "X.jpg"}))
    assert e.value.schluessel == schluessel


def test_bilddatei_ueber_15_mb_wird_vor_der_verkleinerung_abgelehnt(monkeypatch):
    b = bilder_modul()
    assert b.MAX_BILD == 15 * 1024 * 1024
    Netz(monkeypatch, bild=b"\xff\xd8" + b"0" * (b.MAX_BILD + 1))
    with pytest.raises(b.Abgelehnt) as e:
        b.abrufen(commons="Basteibruecke.jpg")
    assert e.value.schluessel == "bild.abgelehnt.zu_gross"


# ---------- Hinzufügen (V1, V4, AC-1, AC-2) ----------

def test_bild_hinzufuegen_legt_eintrag_mit_herkunft_und_zwei_webp_fassungen_an(wanderung, monkeypatch):
    from PIL import Image
    Netz(monkeypatch)
    vorher = {b["id"] for b in liste(wanderung)}
    bid, text = neu_hinzu(wanderung, bildunterschrift="Die Basteibrücke", alt="Steinbrücke über einer Schlucht")
    assert bid.startswith("BI-") and bid not in vorher
    b = eintrag(wanderung, bid)
    assert b["zu"] == "E-01" and b["quelle"] == {"commons": "Basteibruecke.jpg"}
    assert b["urheber"] == "Max Muster" and b["lizenz"] == "CC BY-SA 4.0"
    assert b["lizenz_url"].startswith("https://creativecommons.org/") and b["seite"].startswith("https://commons.wikimedia.org/")
    assert b["bildunterschrift"] == "Die Basteibrücke" and b["alt"] == "Steinbrücke über einer Schlucht"
    assert b["status"] == "aktiv" and not b.get("titelbild")
    assert b["hinzugefuegt"]["wer"] == "Ida" and b["hinzugefuegt"]["datum"]
    for fassung, breite in (("klein", 480), ("gross", 1600)):
        pfad = wanderung / b["dateien"][fassung]
        assert b["dateien"][fassung].startswith("medien/bilder/") and pfad.suffix == ".webp"
        with Image.open(pfad) as im:
            assert im.format == "WEBP" and im.width == breite
    assert b["breite"] == 1600 and b["hoehe"] == 1000
    assert "Max Muster" in text and "CC BY-SA 4.0" in text


def test_bild_aus_wikidata(wanderung, monkeypatch):
    Netz(monkeypatch)
    bid = sb.bild_hinzufuegen(wanderung, IDA, {"wikidata": "Q12345", "zu": "O-01"})[0].split()[0]
    assert eintrag(wanderung, bid)["quelle"] == {"wikidata": "Q12345", "commons": "Basteibruecke.jpg"}


@pytest.mark.parametrize("args, schluessel", [
    ({"commons": "X.jpg", "wikidata": "Q1", "zu": "E-01"}, "bild.abgelehnt.quelle"),
    ({"zu": "E-01"}, "bild.abgelehnt.quelle"),
    ({"commons": "X.jpg", "zu": "E-99"}, "bild.abgelehnt.ziel"),
    ({"commons": "X.jpg", "zu": "Quatsch"}, "bild.abgelehnt.ziel"),
])
def test_bild_hinzufuegen_lehnt_ab_ohne_eintrag(wanderung, monkeypatch, args, schluessel):
    netz = Netz(monkeypatch)
    vorher = liste(wanderung)
    with pytest.raises(sb.Ablehnung) as e:
        sb.bild_hinzufuegen(wanderung, IDA, args)
    assert e.value.schluessel == schluessel
    assert liste(wanderung) == vorher and netz.aufrufe == []       # Prüfung der Anfrage vor dem Netz


@pytest.mark.parametrize("lizenz", ["Free Art License", "CC BY-NC 4.0", "CC BY-ND 4.0", "GFDL", None])
def test_bild_mit_unfreier_lizenz_kommt_nicht_in_die_reise(wanderung, monkeypatch, lizenz):
    Netz(monkeypatch, commons=commons_antwort(extmetadata=meta(lizenz, None)))
    vorher, webp_vorher = liste(wanderung), sorted((wanderung / "medien").rglob("*.webp"))
    with pytest.raises(sb.Ablehnung) as e:
        neu_hinzu(wanderung)
    assert e.value.schluessel == "bild.abgelehnt.lizenz" and meldet(str(e.value), "bild.abgelehnt.lizenz")
    assert liste(wanderung) == vorher
    assert sorted((wanderung / "medien").rglob("*.webp")) == webp_vorher       # keine Datei in der Ablage


def test_zu_reise_ist_erlaubt(wanderung, monkeypatch):
    Netz(monkeypatch)
    bid, _ = neu_hinzu(wanderung, zu="reise")
    assert eintrag(wanderung, bid)["zu"] == "reise"


# ---------- Rechte, Titelbild, Zurückziehen (V2, V5, V6, AC-3, AC-4) ----------

def test_rechte_in_reise_und_schreibweg():
    alle = rg.BAUSTEINE
    for w in ("bild_hinzufuegen", "bild_aendern"):
        assert w in sb.WERKZEUGE and w in sb.AKTIONEN and sb.AKTIONEN[w] in rg.AKTIONEN
    aktion = sb.AKTIONEN["bild_hinzufuegen"]
    assert rg.erlaubt(aktion, "mitwirkend", "planung", alle)[0]
    assert not rg.erlaubt(aktion, "gast", "planung", alle)[0]
    assert "titelbild" in rg.AKTIONEN and rg.AKTIONEN["titelbild"]["rolle"] == "organisator"
    assert not rg.erlaubt("titelbild", "mitwirkend", "planung", alle)[0] and rg.erlaubt("titelbild", "organisator", "planung", alle)[0]


def test_titelbild_nur_organisator_und_hoechstens_eines(wanderung, monkeypatch):
    Netz(monkeypatch)
    with pytest.raises(sb.Ablehnung) as e:
        neu_hinzu(wanderung, KARL, titelbild=True)
    assert e.value.schluessel == "bild.abgelehnt.rolle"
    a, _ = neu_hinzu(wanderung, KARL)                                  # ohne Titelbild darf Karl hinzufügen
    with pytest.raises(sb.Ablehnung) as e:
        sb.bild_aendern(wanderung, KARL, {"ziel": a, "titelbild": True})
    assert e.value.schluessel == "bild.abgelehnt.rolle"
    sb.bild_aendern(wanderung, IDA, {"ziel": a, "titelbild": True})
    b, _ = neu_hinzu(wanderung, IDA, titelbild=True)                  # ein neues Titelbild löst das bisherige ab
    titel = [x["id"] for x in liste(wanderung) if x.get("titelbild")]
    assert titel == [b]


def test_mitwirkend_aendert_zieht_zurueck_und_stellt_wieder_her(wanderung, monkeypatch):
    Netz(monkeypatch)
    bid, _ = neu_hinzu(wanderung, KARL)
    sb.bild_aendern(wanderung, KARL, {"ziel": bid, "bildunterschrift": "Neu", "alt": "Brücke", "zu": "O-01"})
    b = eintrag(wanderung, bid)
    assert (b["bildunterschrift"], b["alt"], b["zu"]) == ("Neu", "Brücke", "O-01")
    with pytest.raises(sb.Ablehnung) as e:
        sb.bild_aendern(wanderung, KARL, {"ziel": bid, "zu": "U-99"})
    assert e.value.schluessel == "bild.abgelehnt.ziel"
    sb.bild_aendern(wanderung, KARL, {"ziel": bid, "zurueckziehen": True})
    b = eintrag(wanderung, bid)
    assert b["status"] == "zurueckgezogen" and all((wanderung / f).exists() for f in b["dateien"].values())
    sb.bild_aendern(wanderung, KARL, {"ziel": bid, "wiederherstellen": True})
    assert eintrag(wanderung, bid)["status"] == "aktiv"


def test_grenze_je_reise(wanderung, monkeypatch):
    Netz(monkeypatch)
    vorhanden = len([b for b in liste(wanderung) if b["status"] == "aktiv"])
    p = wanderung / "reise.yaml"
    roh = yaml.safe_load(p.read_text(encoding="utf-8"))
    roh["bilder"] = {"max_anzahl": vorhanden + 1, "offline_mb": 25}
    p.write_text(yaml.safe_dump(roh, allow_unicode=True, sort_keys=False), encoding="utf-8")
    neu_hinzu(wanderung)
    with pytest.raises(sb.Ablehnung) as e:
        neu_hinzu(wanderung)
    assert e.value.schluessel == "bild.abgelehnt.grenze"
    roh["bilder"]["max_anzahl"] = vorhanden + 2
    p.write_text(yaml.safe_dump(roh, allow_unicode=True, sort_keys=False), encoding="utf-8")
    neu_hinzu(wanderung)


def test_vorgabe_der_grenze_ist_60():
    assert rg.VORGABEN_BILDER == {"max_anzahl": 60, "offline_mb": 25}


# ---------- Kennung BI- neben B- (V1, AC-9) ----------

def test_bi_und_b_werden_nicht_verwechselt(wanderung):
    assert "BI" in neu.ARTEN and "B" in neu.ARTEN
    (wanderung / "plan" / "notiz.md").write_text("BI-07 und B-03\n", encoding="utf-8")
    assert neu._nummern(wanderung, "BI") >= 7
    assert neu._nummern(wanderung, "B") < 7
    import re
    assert re.fullmatch(routen.MUSTER["bild"], "BI-03") and not re.fullmatch(routen.MUSTER["bild"], "B-03")
    assert not re.fullmatch(routen.MUSTER["buchung"], "BI-03")
    assert sb.ID_MUSTER.match("BI-03") and sb.ID_MUSTER.match("B-03")


def test_modul_steht_in_der_deploy_liste():
    import re
    text = (WURZEL / "betrieb" / "deploy.sh").read_text(encoding="utf-8")
    for liste_ in ("KN_MODULE", "SB_MODULE"):
        m = re.search(rf"{liste_}=\"?\(?([^\n)]*)", text)
        assert m and "bilder.py" in m.group(1), liste_


# ---------- Vorab-Abruf vor der Sperre (V7, AC-5) ----------

def test_abruf_laeuft_vor_der_sperre_und_der_unterprozess_geht_nicht_ins_netz(monkeypatch, request):
    from test_schreiben import IDA as IDA_S, env_mitschneiden, sperre_frei
    wurzel, _, arbeit, _ = request.getfixturevalue("repo")
    b = bilder_modul()
    aufrufe = []
    original = b.abrufen

    def abrufen(**kw):
        aufrufe.append(sperre_frei("beispielreise"))
        Netz(monkeypatch)
        return original(**kw)
    monkeypatch.setattr(b, "abrufen", abrufen)
    monkeypatch.setenv("FR_COMMONS_API", "http://127.0.0.1:9/")      # der Unterprozess fände dort nichts
    monkeypatch.setenv("FR_WIKIDATA_API", "http://127.0.0.1:9/")
    umgebungen = env_mitschneiden(monkeypatch)
    code, a = sb.anwenden_extern(sb.Schreiber(wurzel, arbeit), "beispielreise", "bild_hinzufuegen",
                                 {**IDA_S, "args": {"commons": "Basteibruecke.jpg", "zu": "E-01"}})
    assert code == 200 and a["ok"], a
    assert aufrufe == [True]
    assert len(umgebungen) == 1 and umgebungen[0].get("FR_BILD_VORAB"), umgebungen
    assert a.get("vorschau") and base64.b64decode(a["vorschau"])[:4] == b"RIFF"


# ---------- Konnektor (V4, V6) ----------

def test_werkzeuge_englisch_mit_deutschem_alias():
    import konnektor as kn
    import schnittstelle
    assert schnittstelle.NAMEN["image_add"] == "bild_hinzufuegen" and schnittstelle.NAMEN["image_update"] == "bild_aendern"
    tab = schnittstelle.parameter_zu_englisch("bild_hinzufuegen")
    assert tab["zu"] == "belongs_to" and tab["bildunterschrift"] == "caption" and tab["alt"] == "alt_text"
    assert tab["titelbild"] == "title_image" and tab.get("commons", "commons") == "commons"
    aendern = schnittstelle.parameter_zu_englisch("bild_aendern")
    assert aendern["zurueckziehen"] == "withdraw" and aendern["wiederherstellen"] == "restore"
    for w in ("bild_hinzufuegen", "bild_aendern"):
        assert w in kn.ONTOLOGIE_WERKZEUGE and kn.ONTOLOGIE_AKTION[w] == sb.AKTIONEN[w]


def test_konnektor_gibt_vorschau_als_bild_an_claude(request, monkeypatch):
    from test_konnektor import ALT_ORGANISATOR, GAST, KARL as KARL_TOKEN, Schreibweg, rpc
    basis, _ = request.getfixturevalue("schreibweg")
    namen = lambda token: {t["name"] for t in rpc(basis, token, "tools/list")["tools"]}
    assert {"bild_hinzufuegen", "bild_aendern"} <= namen(KARL_TOKEN) and not {"bild_hinzufuegen", "bild_aendern"} & namen(GAST)
    from PIL import Image
    puffer = io.BytesIO()
    Image.new("RGB", (480, 300), "green").save(puffer, "WEBP")
    monkeypatch.setattr(Schreibweg, "antwort", (200, {"ok": True, "text": "Bild BI-01 angelegt.",
                                                      "vorschau": base64.b64encode(puffer.getvalue()).decode()}))
    r = rpc(basis, ALT_ORGANISATOR, "tools/call", {"name": "image_add", "arguments": {
        "commons": "Basteibruecke.jpg", "belongs_to": "E-01", "caption": "Brücke", "title_image": True}})
    assert not r["isError"] and any(c["type"] == "image" for c in r["content"]), r
    pfad, _, body = Schreibweg.anfragen[-1]
    assert pfad == "/beispielreise/bild_hinzufuegen"
    assert body["args"] == {"commons": "Basteibruecke.jpg", "zu": "E-01", "bildunterschrift": "Brücke", "titelbild": True}


def test_werkzeugliste_der_doku_nennt_die_bildwerkzeuge():
    text = (WURZEL / "docs" / "konnektor.md").read_text(encoding="utf-8")
    assert "image_add" in text and "image_update" in text


# ---------- Hotlink-Sperre (V10, AC-6, #581) ----------

def bau_meldungen(ordner):
    with tempfile.TemporaryDirectory() as t:
        with pytest.raises(bauen.BauFehler) as e:
            bauen.Bauer(ordner, t).daten()
    return e.value.meldungen


def text_anhaengen(ordner, zeile):
    p = ordner / "inhalt" / "wissen.md"
    p.write_text(p.read_text(encoding="utf-8").replace("### Der Hockstein\n", f"### Der Hockstein\n{zeile}\n\n", 1), encoding="utf-8")


@pytest.mark.parametrize("ziel", ["https://example.org/bild.jpg", "http://example.org/bild.png", "//example.org/bild.jpg"])
def test_fremdes_bild_im_text_ist_ein_baufehler(wanderung, ziel):
    text_anhaengen(wanderung, f"![Fremd]({ziel})")
    assert meldet(bau_meldungen(wanderung), "pruefung.bauen.bild_fremd")


def test_link_bleibt_erlaubt_und_csp_begrenzt_bilder(wanderung, tmp_path):
    text_anhaengen(wanderung, "[Fahrplan](https://example.org/fahrplan) und [anderswo](//example.org/x)")
    bauen.bauen(wanderung, tmp_path / "dist")
    seite = (tmp_path / "dist" / "index.html").read_text(encoding="utf-8")
    import re
    regel = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', seite).group(1)
    assert "img-src 'self' data:" in regel


@pytest.mark.parametrize("ziel", ["https://example.org/x.jpg", "//example.org/x.jpg"])
def test_schreibweg_lehnt_fremdes_bild_im_text_ab(request, ziel):
    from test_schreiben import IDA as IDA_S, deutsch
    wurzel, _, arbeit, _ = request.getfixturevalue("repo")
    code, a = sb.anwenden_extern(sb.Schreiber(wurzel, arbeit), "beispielreise", "wissen_schreiben",
                                 {**IDA_S, "args": {"titel": "Testbild", "text": f"Ein Bild: ![x]({ziel})", "gruppe": "wissen",
                                                    "quelle": "eigene Beobachtung"}})
    assert code == 422 and not a["ok"], a
    assert meldet(deutsch(a), "pruefung.bauen.bild_fremd"), a
    assert "example.org" not in (wurzel / "reisen" / "beispielreise" / "inhalt" / "wissen.md").read_text(encoding="utf-8")


# ---------- BI- im Text (V10a, V16, AC-8) ----------

def bild_eintragen(ordner, bid="BI-01", zu="E-01", status="aktiv", quelle=None, lizenz="CC BY-SA 4.0", urheber="Max Muster"):
    from PIL import Image
    (ordner / "medien" / "bilder").mkdir(parents=True, exist_ok=True)
    dateien = {}
    for fassung, breite in (("klein", 480), ("gross", 1600)):
        rel = f"medien/bilder/{bid}-{breite}.webp"
        Image.new("RGB", (breite, breite * 10 // 16), "blue").save(ordner / rel, "WEBP")
        dateien[fassung] = rel
    b = {"id": bid, "zu": zu, "quelle": quelle or {"commons": "Basteibruecke.jpg"}, "status": status,
         "dateien": dateien, "breite": 1600, "hoehe": 1000, "hinzugefuegt": {"datum": "2026-11-15", "wer": "Ida"}}
    if quelle != "reise":
        b.update({"urheber": urheber, "lizenz": lizenz, "lizenz_url": "https://creativecommons.org/licenses/by-sa/4.0",
                  "seite": "https://commons.wikimedia.org/wiki/File:Basteibruecke.jpg"})
    p = ordner / "plan" / "bilder.yaml"
    roh = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
    roh = roh or {}
    roh["bilder"] = [x for x in (roh.get("bilder") or []) if x["id"] != bid] + [b]
    p.write_text(yaml.safe_dump(roh, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return b


def test_bi_im_text_zeigt_grosse_fassung_mit_nennung_und_im_precache(wanderung, tmp_path):
    b = bild_eintragen(wanderung, "BI-50")
    text_anhaengen(wanderung, "![Die Brücke](BI-50)")
    ziel = tmp_path / "dist"
    bauen.bauen(wanderung, ziel)
    seite = (ziel / "index.html").read_text(encoding="utf-8")
    assert b["dateien"]["gross"] in seite and (ziel / b["dateien"]["gross"]).exists()
    assert "Max Muster" in seite and "CC BY-SA 4.0" in seite and "commons.wikimedia.org/wiki/File:Basteibruecke.jpg" in seite
    import re
    dateien = json.loads(re.search(r"const DATEIEN = (\[.*\]);", (ziel / "sw.js").read_text(encoding="utf-8")).group(1))
    assert b["dateien"]["gross"] in dateien


def test_nennung_gemeinfrei_nur_urheber_und_aus_der_reise_ohne(wanderung, tmp_path):
    bild_eintragen(wanderung, "BI-51", lizenz="CC0", urheber="Erika Frei")
    bild_eintragen(wanderung, "BI-52", quelle="reise")
    text_anhaengen(wanderung, "![Frei](BI-51)\n\n![Eigen](BI-52)")
    bauen.bauen(wanderung, tmp_path / "dist")
    seite = (tmp_path / "dist" / "index.html").read_text(encoding="utf-8")
    assert "Erika Frei" in seite and "creativecommons.org/publicdomain" not in seite
    assert "medien/bilder/BI-52-1600.webp" in seite


def test_zurueckgezogenes_bild_entfaellt_ohne_fehler_unbekanntes_ist_baufehler(wanderung, tmp_path):
    b = bild_eintragen(wanderung, "BI-53", status="zurueckgezogen")
    text_anhaengen(wanderung, "![Weg](BI-53)")
    bauen.bauen(wanderung, tmp_path / "dist")
    assert b["dateien"]["gross"] not in (tmp_path / "dist" / "index.html").read_text(encoding="utf-8")
    text_anhaengen(wanderung, "![Gibts nicht](BI-98)")
    assert meldet(bau_meldungen(wanderung), "pruefung.bauen.bild_unbekannt")


# ---------- bilder_nachziehen (V11, AC-7) ----------

def test_nachziehen_stellt_altbestand_um_und_ist_idempotent(wanderung, tmp_path):
    p = wanderung / "inhalt" / "etappen.md"
    # die Beispielreise im Repo ist schon umgestellt (V24): für den Test den Altbestand wiederherstellen
    p.write_text(p.read_text(encoding="utf-8").replace(
        "![Skizze: Felsnadeln, Brücke und Fluss](BI-01)", "![Skizze: Felsnadeln, Brücke und Fluss](../medien/skizze-felsen.png)").replace(
        "![Skizze: Felsnadeln, Brücke und Fluss](../medien/skizze-felsen.png)",
        "![Skizze: Felsnadeln, Brücke und Fluss](../medien/skizze-felsen.png)\n\n![Fremd](https://example.org/f.jpg)"), encoding="utf-8")
    w = wanderung / "inhalt" / "wissen.md"     # ohne Liste auch ohne die Commons-Bilder der Beispielreise im Text
    w.write_text(re.sub(r"\n!\[[^\]]*\]\(BI-\d+\)\n", "\n", w.read_text(encoding="utf-8")), encoding="utf-8")
    shutil.rmtree(wanderung / "medien" / "bilder", ignore_errors=True)
    (wanderung / "plan" / "bilder.yaml").unlink(missing_ok=True)
    neu.nachziehen(wanderung)
    text = p.read_text(encoding="utf-8")
    assert "medien/skizze-felsen.png" not in text and "](https://example.org/f.jpg)" in text and "![Fremd]" not in text
    alt = [b for b in liste(wanderung) if b["quelle"] == "reise"]
    assert len(alt) == 1 and f"]({alt[0]['id']})" in text and alt[0]["zu"].startswith("E-")
    assert "lizenz" not in alt[0] and "urheber" not in alt[0]
    assert all((wanderung / f).suffix == ".webp" and (wanderung / f).exists() for f in alt[0]["dateien"].values())
    assert (wanderung / "medien" / "skizze-felsen.png").exists()                 # das Original bleibt in der Ablage
    stand = {f: f.read_bytes() for f in wanderung.rglob("*") if f.is_file()}
    neu.nachziehen(wanderung)
    assert {f: f.read_bytes() for f in wanderung.rglob("*") if f.is_file()} == stand
    bauen.bauen(wanderung, tmp_path / "dist")
    assert alt[0]["dateien"]["gross"] in (tmp_path / "dist" / "index.html").read_text(encoding="utf-8")


def test_nachziehen_aendert_stadtwochenende_nicht(stadt):
    stand = {f: f.read_bytes() for f in stadt.rglob("*") if f.is_file()}
    neu.nachziehen(stadt)
    assert {f: f.read_bytes() for f in stadt.rglob("*") if f.is_file()} == stand


def test_nachziehen_aendert_die_beispielreise_nicht_mehr(wanderung):
    """Die Beispielreise im Repo ist schon umgestellt (V24): Altbestand steht als BI-, ein Bild mit Commons-Herkunft und ein Titelbild."""
    # nur die Dateien, die bilder_nachziehen berührt; volle Idempotenz der Beispielreise: #584
    def dateien():
        muster = ("plan/bilder.yaml", "ids.yaml", "inhalt/*.md", "medien/bilder/*")
        return {f: f.read_bytes() for m in muster for f in wanderung.glob(m) if f.is_file()}
    stand = dateien()
    neu.nachziehen(wanderung)
    assert dateien() == stand
    bilder = liste(wanderung)
    assert any("commons" in (b["quelle"] if isinstance(b["quelle"], dict) else {}) for b in bilder)
    assert sum(1 for b in bilder if b.get("titelbild")) == 1
    assert not (STADT / "plan" / "bilder.yaml").exists()


def test_beispielbilder_stehen_in_third_party():
    text = (WURZEL / "THIRD_PARTY.md").read_text(encoding="utf-8")
    for b in liste(WANDERUNG):
        if isinstance(b["quelle"], dict) and "commons" in b["quelle"]:
            assert b["quelle"]["commons"] in text and b["lizenz"] in text


# ---------- Export und Löschen nehmen die Bilddateien mit ----------

def test_bilddateien_werden_ausgelagert_und_exportiert(wanderung, tmp_path, monkeypatch):
    import reisespeicher as rs
    monkeypatch.setenv("FR_SPEICHER", str(tmp_path / "_speicher"))
    b = bild_eintragen(wanderung, "BI-54")
    rs.importieren(wanderung, "beispielreise", wer="Ida", grund="Test")
    ziel = tmp_path / "wieder"
    rs.materialisieren("beispielreise", ziel)
    assert (ziel / b["dateien"]["klein"]).read_bytes() == (wanderung / b["dateien"]["klein"]).read_bytes()


# ---------- Seitentest unter der neuen CSP (V10, AC-6) ----------

@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_seite_unter_der_csp_ohne_meldung(tmp_path, browser):
    """Gebaute Beispielreise (Grundkarten als Attrappe wie test_karte_legende): Etappenkarte mit Kacheln und Ebenen-Symbol, Belege,
    App-Symbol und ein Bild ![…](BI-NN) mit Nennung, in Chromium und WebKit ohne CSP-Meldung in der Konsole und ohne Seitenfehler."""
    import functools
    import http.server
    import os
    import subprocess
    import threading
    from test_karte_legende import gebaut
    from test_tagesseite import PLAYWRIGHT
    if not PLAYWRIGHT.exists() or not shutil.which("node"):
        pytest.skip("Playwright fehlt")
    gebaut(tmp_path)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_bilder_csp.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/"],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == [], e["fehler"]
    a = e["aus"]
    assert a["karte"]["marken"] and a["karte"]["kacheln"] and a["karte"]["ebenenSymbol"], a["karte"]
    assert a["symbol"] and all(a["symbol"]), a["symbol"]
    assert a["beleg"] == 1, a
    assert a["bild"] and all(x["breite"] > 0 for x in a["bild"]), a["bild"]
    assert any("CC BY-SA 4.0" in x["nennung"] for x in a["bild"]), a["bild"]


# ---------- Befunde der Gegenprüfung (F001 bis F007) ----------

def reise_yaml_bilder(ordner, wert):
    p = ordner / "reise.yaml"
    roh = yaml.safe_load(p.read_text(encoding="utf-8"))
    roh["bilder"] = wert
    p.write_text(yaml.safe_dump(roh, allow_unicode=True, sort_keys=False), encoding="utf-8")


def probebau(ordner):
    with tempfile.TemporaryDirectory() as t:
        return bauen.Bauer(ordner, t).daten()


def test_f001_bilder_in_reise_yaml_baut_und_hebt_die_grenze(wanderung, monkeypatch):
    Netz(monkeypatch)
    vorhanden = liste(wanderung)
    platzhalter = [{"id": f"BI-{n}", "zu": "reise", "quelle": "reise", "status": "aktiv"} for n in range(100, 160 - len(vorhanden))]
    p = wanderung / "plan" / "bilder.yaml"
    p.write_text(yaml.safe_dump({"bilder": vorhanden + platzhalter}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    assert len([b for b in liste(wanderung) if b["status"] == "aktiv"]) == 60
    with pytest.raises(sb.Ablehnung):
        neu_hinzu(wanderung)
    reise_yaml_bilder(wanderung, {"max_anzahl": 100, "offline_mb": 25})
    probebau(wanderung)                                                  # der Bau kennt den Schlüssel bilder
    bid, _ = neu_hinzu(wanderung)                                        # das 61. Bild wird angenommen
    assert eintrag(wanderung, bid)["status"] == "aktiv"


@pytest.mark.parametrize("wert", [{"max_anzahl": 0}, {"offline_mb": "viel"}, {"unbekannt": 1}, "60"])
def test_f001_falscher_bilder_block_ist_ein_baufehler(wanderung, wert):
    reise_yaml_bilder(wanderung, wert)
    assert meldet(bau_meldungen(wanderung), "pruefung.reise.bilder")


def test_f002_kaputtes_altbild_bleibt_und_der_rest_wird_umgestellt(wanderung):
    w = wanderung / "inhalt" / "wissen.md"
    w.write_text(re.sub(r"\n!\[[^\]]*\]\(BI-\d+\)\n", "\n", w.read_text(encoding="utf-8")), encoding="utf-8")
    (wanderung / "medien" / "kaputt.png").write_bytes(b"\x89PNG kaputt")
    text_anhaengen(wanderung, "![Kaputt](../medien/kaputt.png)")
    p = wanderung / "inhalt" / "etappen.md"
    p.write_text(p.read_text(encoding="utf-8").replace("(BI-01)", "(../medien/skizze-felsen.png)"), encoding="utf-8")
    shutil.rmtree(wanderung / "medien" / "bilder")
    (wanderung / "plan" / "bilder.yaml").unlink()
    meldungen = neu.nachziehen(wanderung, betrieb=False)
    assert any("kaputt.png" in m for m in meldungen), meldungen
    assert "](../medien/kaputt.png)" in w.read_text(encoding="utf-8")
    neu_ids = [b["id"] for b in liste(wanderung)]
    assert len(neu_ids) == 1 and f"]({neu_ids[0]})" in p.read_text(encoding="utf-8")
    assert all((wanderung / f).exists() for f in eintrag(wanderung, neu_ids[0])["dateien"].values())
    probebau(wanderung)
    stand = {f: f.read_bytes() for f in wanderung.rglob("*") if f.is_file()}
    neu.nachziehen(wanderung, betrieb=False)
    assert {f: f.read_bytes() for f in wanderung.rglob("*") if f.is_file()} == stand


def test_f003_titelbild_false_entfernt_nur_die_eigene_marke(wanderung, monkeypatch):
    Netz(monkeypatch)
    a, _ = neu_hinzu(wanderung, titelbild=True)
    b, _ = neu_hinzu(wanderung)
    sb.bild_aendern(wanderung, IDA, {"ziel": b, "titelbild": False})
    assert [x["id"] for x in liste(wanderung) if x.get("titelbild")] == [a]
    sb.bild_aendern(wanderung, IDA, {"ziel": a, "titelbild": False})
    assert [x["id"] for x in liste(wanderung) if x.get("titelbild")] == []


def test_f004_zurueckgezogenes_bild_ist_nie_titelbild(wanderung, monkeypatch):
    Netz(monkeypatch)
    a, _ = neu_hinzu(wanderung, titelbild=True)
    sb.bild_aendern(wanderung, KARL, {"ziel": a, "zurueckziehen": True})
    assert not eintrag(wanderung, a).get("titelbild")
    with pytest.raises(sb.Ablehnung) as e:
        sb.bild_aendern(wanderung, IDA, {"ziel": a, "titelbild": True})
    assert e.value.schluessel == "bild.abgelehnt.zurueckgezogen"


@pytest.mark.parametrize("schreibweise", ['BI-50 "Titel"', "bi-50", "BI-50 'Titel'"])
def test_f005_kennung_mit_titel_oder_klein_wird_aufgeloest(wanderung, tmp_path, schreibweise):
    b = bild_eintragen(wanderung, "BI-50")
    text_anhaengen(wanderung, f"![Die Brücke]({schreibweise})")
    bauen.bauen(wanderung, tmp_path / "dist")
    seite = (tmp_path / "dist" / "index.html").read_text(encoding="utf-8")
    assert b["dateien"]["gross"] in seite and 'src=\\"BI-50' not in seite and 'src=\\"bi-50' not in seite


def test_f005_unbekannte_kennung_klein_ist_baufehler(wanderung):
    text_anhaengen(wanderung, "![x](bi-97)")
    assert meldet(bau_meldungen(wanderung), "pruefung.bauen.bild_unbekannt")


@pytest.mark.parametrize("ziel", ["https://example.org/x.jpg", "//example.org/x.jpg", "/\\example.org/x.jpg", "/a.png",
                                  "data:image/png;base64,AAAA", "javascript:alert(1)", " https://example.org/y.jpg"])
def test_f007_nach_nachziehen_baut_jede_abgelehnte_bildquelle(wanderung, ziel):
    text_anhaengen(wanderung, f"![Alt]({ziel})")
    assert meldet(bau_meldungen(wanderung), "pruefung.bauen.bild_fremd") or bau_meldungen(wanderung)
    neu.nachziehen(wanderung, betrieb=False)
    probebau(wanderung)
    assert "![Alt](" not in (wanderung / "inhalt" / "wissen.md").read_text(encoding="utf-8")


def test_f007_trockenlauf_nennt_eindeutige_kennungen(wanderung):
    p = wanderung / "inhalt" / "etappen.md"
    p.write_text(p.read_text(encoding="utf-8").replace("(BI-01)", "(../medien/skizze-felsen.png)\n\n![Zwei](../medien/icon.svg)"),
                 encoding="utf-8")
    shutil.copy(wanderung / "medien" / "skizze-felsen.png", wanderung / "medien" / "zwei.png")
    p.write_text(p.read_text(encoding="utf-8").replace("../medien/icon.svg", "../medien/zwei.png"), encoding="utf-8")
    meldungen = neu.bilder_nachziehen(wanderung, schreiben=False)
    kennungen = re.findall(r"→ (BI-\d+)", " ".join(meldungen))
    assert len(kennungen) == 2 and len(set(kennungen)) == 2, meldungen
