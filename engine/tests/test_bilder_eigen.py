"""Tests für Bilder Stufe 2: eigene Fotos hochladen, löschen, Link aus dem Chat (#582; Spec
docs/specs/oberflaeche/bilder-582-eigene-fotos.md, Pakete P1, P3, P2). Nur erfundene Daten: die Beispielreise (Ida
Organisatorin, Karl mitwirkend, dazu in einzelnen Tests Mo mitwirkend und Kim Gast) und das Stadtwochenende (Tom, Lea),
Testfotos entstehen mit Pillow, alles unter tmp_path. Kein Test geht ins Netz.

Was diese Tests als Schnittstelle festlegen (Entscheidung des Tech Leads in der RED-Phase):
  bilder.MAX_EIGEN = 12 MB                       Grenze je Foto vor der Verkleinerung
  bilder.MAX_PIXEL = 60_000_000                  setzt PIL.Image.MAX_IMAGE_PIXELS; schon das Überschreiten (Warnung von
                                                 Pillow, nicht erst die doppelte Grenze) ist eine Ablehnung
  bilder.eigen_umwandeln(inhalt) -> {"klein": bytes, "gross": bytes, "breite", "hoehe"}
                                                 Magic Bytes über belege.typ_erkennen (JPEG, PNG, WebP, HEIC/HEIF über
                                                 pillow_heif), Drehung angewendet, WebP ohne EXIF, XMP, GPS; Ablehnungen
                                                 bilder.Abgelehnt mit bild.abgelehnt.foto_zu_gross ({mb}) und
                                                 bild.abgelehnt.format; Bombe, kaputt, falsches ftyp: format, nie ein Absturz
                                                 (bild.abgelehnt.zu_gross bleibt der Text für Commons mit 15 MB)
  bilder.waisen_aufraeumen(reise_dir, liste) -> [entfernte Pfade, relativ zur Reise]
                                                 Dateien unter medien/bilder/ ohne Eintrag in der Liste
  reise.VORGABEN_BILDER = {"max_anzahl": 60, "offline_mb": 25, "max_mb": 150}; bild.abgelehnt.grenze nennt {anzahl} und {mb}
  Eintrag in plan/bilder.yaml für ein eigenes Foto: quelle: eigen, urheber: Anzeigename, besitzer: Personenschlüssel der
                                                 Reise (reise.yaml), keine Lizenz; nach dem Entfernen status: entfernt,
                                                 entfernt: {datum, wer}, ohne dateien, bildunterschrift, alt, titelbild
  Schreibweg: POST /<reise>/bild_hochladen        roher Body (bis 12 MB, nicht durch MAX_BODY begrenzt), Kopf X-Frieda-Bild
                                                 (JSON {"zu", "person", "name"}), nur mit X-Frieda-Dienst; Werkzeug
                                                 bild_hochladen (sb.WERKZEUGE, sb.AKTIONEN) liest die umgewandelten Fassungen
                                                 vor der Sperre aus FR_BILD_VORAB (bilder.eigen_vorab_schreiben(ordner,
                                                 ergebnis) -> Pfad) und räumt Waisen im selben Zug auf
  Schreibweg: Werkzeug bild_entfernen             args {"ziel": "BI-NN"}; Recht: besitzer oder organisator; ruft danach
                                                 reisespeicher.bild_entfernen(reise, bid) und vermerkt das Bild im
                                                 Löschprotokoll (konten.bild_loeschung_protokollieren)
  reisespeicher.bild_entfernen(reise, bid) -> int dritte Ausnahme vom Nur-Anhängen: leert nur medien/bilder/<bid>-480.webp und
                                                 -1600.webp in allen Versionen (inhalt und pruefsumme NULL), dann
                                                 _ablage_aufraeumen und verdichten; pruefen, materialisieren, Export vertragen es
  konten.bild_loeschprotokoll() -> [(reise, bid)]; waechter.bildloeschungen_nachholen() -> [(reise, bid)] (täglicher Lauf,
                                                 nach dem Rückspielen einer alten Sicherung)
  reisespeicher.namen_ersetzen ersetzt auch urheber eigener Fotos; besitzer bleibt
  Rückmeldedienst: POST /<reise>/bilder?zu=<ID>  roher Body, nur angemeldet (Cookie, Origin), Rolle über rolle_aktuell,
                                                 Drosselung, 413 über 12 MB und 415 bei falschem Format, ohne den Schreibweg
                                                 zu erreichen; leitet an POST /<reise>/bild_hochladen weiter
  Rückmeldedienst: DELETE /<reise>/bilder/<BI-NN> nur angemeldet; leitet an das Werkzeug bild_entfernen weiter
  Rückmeldedienst (P2): GET /hochladen/<token>     Link-Seite mit eigener CSP, Referrer-Policy: no-referrer, ohne Seitenlink;
                                                 POST /hochladen/<token> roher Body, Rolle bei jedem Foto neu geprüft;
                                                 abgelaufen, aufgebraucht, unbekannt, Person nicht mehr in der Reise: dieselbe
                                                 Antwort (Seite mit hochladen.abgelaufen)
  konten.hochladelink_anlegen(reise, person, konto_id, zu=None) -> token   nur sha256 in konten.db, 30 Minuten, 10 Fotos
  konten.hochladelink_pruefen(token, reise) -> dict {"reise", "person", "konto", "zu", "rest", "ablauf"} oder None
  Konnektor: Werkzeug bild_hochladelink (englisch image_upload_link), ab mitwirkend; die Antwort enthält
                                                 <FR_BASIS>/hochladen/<token>
  nginx: Block location ^~ /__REISE__-__TOKEN__/api/bilder/ (client_max_body_size 12m bis 14m) in nginx-reise.conf,
                                                 location ^~ /hochladen/ in einer Vorlage unter betrieb/vorlagen/
  veroeffentlichen.sh: prüft vor dem Bau einer neuen Python-Umgebung die Glibc (mindestens 2.28); VF_GLIBC ersetzt im Test
                                                 die erkannte Version
  daten.json: Bild aus eigener Quelle mit "eigen": true, "besitzer" und nennung {"urheber"}; entfernte Bilder nur in
                                                 "bilder_entfernt": [{"id", "zu", "datum", "wer"}], ohne Dateinamen
  Texte (alle Sprachen): seite.bild.hochladen, .hochladen_blatt, .hochladen_abbrechen, .hochladen_knopf, .hochladen_anmelden,
                                                 .hinweis_personen, .hinweis_metadaten, .foto_von, .entfernen, .entfernen_titel,
                                                 .entfernen_zusage, .entfernen_behalten, .entfernen_ja, .entfernt;
                                                 hochladen.titel, .zu, .auswaehlen, .fertig, .laeuft, .rest, .erklaerung,
                                                 .abgelaufen_titel, .abgelaufen; bild.abgelehnt.foto_zu_gross, .format,
                                                 .entfernen_recht (weder Besitzer noch Organisator:in), .nicht_eigen
                                                 (Commons und Altbestand: nur zurückziehen);
                                                 konnektor.werkzeug.bild_hochladelink
  Browser (seiten_bilder_eigen.mjs): Knopf mit dem Text seite.bild.hochladen, input[type=file], Knöpfe nach ihrem Text,
                                                 Großansicht #gross; Seite schickt POST api/bilder?zu=<ID> und
                                                 DELETE api/bilder/<BI-NN>
"""
import hashlib
import http.client
import io
import json
import os
import re
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
import zlib
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

ENGINE = Path(__file__).resolve().parents[1]
WURZEL = ENGINE.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bauen  # noqa: E402
import konten  # noqa: E402
import neu  # noqa: E402
import reise as rg  # noqa: E402
import schreiben as sb  # noqa: E402
import texte  # noqa: E402
from conftest import meldet  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402
import test_schreiben_speicher as tss  # noqa: E402
from test_schreiben_speicher import speicher  # noqa: E402,F401  (Fixture: beide Beispielreisen im Reisespeicher)
from test_anmeldung import BASIS, SEITE, abruf, anmelden, kopf, welt  # noqa: E402,F401  (welt: Fixture)
from test_trennung import zwei, IDA as IDA_MAIL, KARL as KARL_MAIL, TOM as TOM_MAIL  # noqa: E402,F401  (zwei: Fixture)
from test_software_weg_454 import sw, _python_vorbereiten  # noqa: E402,F401  (sw: Fixture)

WANDERUNG = WURZEL / "beispiel" / "reisen" / "beispielreise"
STADT = WURZEL / "beispiel" / "reisen" / "stadtwochenende"
KIM_MAIL, LEA_MAIL, MO_MAIL = "kim@beispiel.invalid", "lea@beispiel.invalid", "mo@beispiel.invalid"
KAMERA = b"Beispielkamera-4711"          # Suchmarke im EXIF des Testfotos
XMP = b"Beispiel-XMP-4711"               # Suchmarke im XMP des Testfotos
MB = 1024 * 1024
MO = {"person": "mo", "name": "Mo", "rolle": "mitwirkend"}


def bilder_modul():
    import bilder
    return bilder


# ---------- Testfotos ----------

def foto(breite=2000, hoehe=1250, drehung=None, gps=True, art="JPEG"):
    """Foto aus Rauschen (größer als 64 KB), mit Kamera, GPS und XMP in den Metadaten; drehung: EXIF-Orientierung."""
    from PIL import Image
    im = Image.frombytes("RGB", (breite, hoehe), os.urandom(breite * hoehe * 3))
    ex = Image.Exif()
    ex[0x010F] = KAMERA.decode()
    if drehung:
        ex[0x0112] = drehung
    if gps:
        ex[0x8825] = {1: "N", 2: (50.0, 57.0, 30.0), 3: "E", 4: (14.0, 2.0, 0.0)}
    puffer = io.BytesIO()
    extra = {"xmp": b'<x:xmpmeta xmlns:x="adobe:ns:meta/">' + XMP + b"</x:xmpmeta>"} if art == "JPEG" else {}
    im.save(puffer, art, exif=ex, **extra)
    return puffer.getvalue()


def klein_foto():
    from PIL import Image
    puffer = io.BytesIO()
    Image.new("RGB", (640, 400), (90, 120, 160)).save(puffer, "JPEG")
    return puffer.getvalue()


def _png_chunk(art, daten):
    return struct.pack(">I", len(daten)) + art + daten + struct.pack(">I", zlib.crc32(art + daten) & 0xFFFFFFFF)


def png_bombe(breite, hoehe, mit_daten=True):
    """Gültiges Graustufen-PNG mit breite×hoehe Pixeln, klein komprimiert (lauter Nullen); ohne Daten nur der Kopf."""
    kopf_ = struct.pack(">IIBBBBB", breite, hoehe, 8, 0, 0, 0, 0)
    roh = b""
    if mit_daten:
        z = zlib.compressobj(9)
        zeile = b"\x00" * (breite + 1)
        roh = b"".join(z.compress(zeile) for _ in range(hoehe)) + z.flush()
    return b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", kopf_) + _png_chunk(b"IDAT", roh) + _png_chunk(b"IEND", b"")


def ohne_metadaten(webp):
    from PIL import Image
    assert webp[:4] == b"RIFF" and webp[8:12] == b"WEBP", webp[:16]
    for marke in (b"EXIF", b"Exif", b"XMP ", KAMERA, XMP):
        assert marke not in webp, marke
    with Image.open(io.BytesIO(webp)) as im:
        assert "exif" not in im.info and "xmp" not in im.info
        assert not dict(im.getexif())


def heic(breite=900, hoehe=600):
    import pillow_heif
    from PIL import Image
    pillow_heif.register_heif_opener()
    puffer = io.BytesIO()
    Image.new("RGB", (breite, hoehe), (30, 140, 70)).save(puffer, "HEIF")
    return puffer.getvalue()


# ---------- P1: Umwandeln (V2, V3, V5; AC-2, AC-3) ----------

def test_grenzen_der_umwandlung():
    from PIL import Image
    b = bilder_modul()
    assert b.MAX_EIGEN == 12 * MB
    assert b.MAX_PIXEL == 60_000_000
    assert Image.MAX_IMAGE_PIXELS == b.MAX_PIXEL


def test_jpeg_mit_gps_ergibt_zwei_webp_ohne_metadaten():
    b = bilder_modul()
    r = b.eigen_umwandeln(foto())
    assert set(r) >= {"klein", "gross", "breite", "hoehe"}
    from PIL import Image
    for fassung, breite in (("klein", 480), ("gross", 1600)):
        ohne_metadaten(r[fassung])
        with Image.open(io.BytesIO(r[fassung])) as im:
            assert im.width == breite, (fassung, im.size)
    assert (r["breite"], r["hoehe"]) == (1600, 1000)


def test_drehung_wird_angewendet_und_verschwindet():
    from PIL import Image
    r = bilder_modul().eigen_umwandeln(foto(800, 400, drehung=6))
    assert r["breite"] < r["hoehe"], r
    for fassung in ("klein", "gross"):
        with Image.open(io.BytesIO(r[fassung])) as im:
            assert im.height > im.width and 0x0112 not in im.getexif(), (fassung, im.size)


def test_png_und_webp_werden_angenommen():
    b = bilder_modul()
    for art in ("PNG", "WEBP"):
        r = b.eigen_umwandeln(foto(1200, 800, gps=False, art=art))
        ohne_metadaten(r["klein"])


def test_heic_ergibt_zwei_fassungen_falsche_magic_bytes_nicht():
    b = bilder_modul()
    inhalt = heic()
    r = b.eigen_umwandeln(inhalt)
    ohne_metadaten(r["klein"])
    ohne_metadaten(r["gross"])
    for kaputt in (inhalt.replace(b"ftyp", b"xxxx", 1), b"\x00\x00\x00\x18ftypheic" + b"kein Bild " * 200):
        with pytest.raises(b.Abgelehnt) as e:
            b.eigen_umwandeln(kaputt)
        assert e.value.schluessel == "bild.abgelehnt.format"


@pytest.mark.parametrize("inhalt", [
    "Das ist kein Foto, nur eine Datei mit der Endung .jpg (Beispiel)".encode(),
    b"GIF89a" + b"\x00" * 200,
    b"%PDF-1.4\n%%EOF\n",
    b'<svg xmlns="http://www.w3.org/2000/svg"/>',
    b"",
])
def test_falsches_format_wird_abgelehnt(inhalt):
    b = bilder_modul()
    with pytest.raises(b.Abgelehnt) as e:
        b.eigen_umwandeln(inhalt)
    assert e.value.schluessel == "bild.abgelehnt.format"


def test_zu_grosses_foto_vor_der_verkleinerung():
    b = bilder_modul()
    with pytest.raises(b.Abgelehnt) as e:
        b.eigen_umwandeln(b"\xff\xd8\xff\xe0" + b"\x00" * (12 * MB))
    assert e.value.schluessel == "bild.abgelehnt.foto_zu_gross"


@pytest.mark.parametrize("inhalt", [
    pytest.param(lambda: png_bombe(8000, 8000), id="64-megapixel"),          # über der Grenze, unter der doppelten
    pytest.param(lambda: png_bombe(20000, 20000, mit_daten=False), id="400-megapixel"),
    pytest.param(lambda: foto(800, 500)[:4000], id="abgeschnitten"),
])
def test_bombe_und_kaputtes_bild_sind_ablehnung_kein_absturz(inhalt):
    b = bilder_modul()
    with pytest.raises(b.Abgelehnt) as e:
        b.eigen_umwandeln(inhalt())
    assert e.value.schluessel == "bild.abgelehnt.format"


# ---------- P1: Grenzen je Reise in reise.yaml (V4, AC-4) ----------

def test_vorgabe_max_mb_150_und_einstellbar(tmp_path):
    assert rg.VORGABEN_BILDER == {"max_anzahl": 60, "offline_mb": 25, "max_mb": 150}
    assert rg.bilder_grenzen({})["max_mb"] == 150 and rg.bilder_grenzen({"bilder": {"max_mb": 200}})["max_mb"] == 200
    ordner = tmp_path / "beispielreise"
    shutil.copytree(WANDERUNG, ordner)
    p = ordner / "reise.yaml"
    roh = yaml.safe_load(p.read_text(encoding="utf-8"))
    roh["bilder"] = {"max_anzahl": 60, "offline_mb": 25, "max_mb": 200}
    p.write_text(yaml.safe_dump(roh, allow_unicode=True, sort_keys=False), encoding="utf-8")
    with tempfile.TemporaryDirectory() as t:
        bauen.Bauer(ordner, t).daten()
    vorlage = texte.t("de", "bild.abgelehnt.grenze")
    assert "{anzahl}" in vorlage and "{mb}" in vorlage, vorlage


# ---------- P1: Schreibweg über den Reisespeicher (V3, V4, V7, V9) ----------

class Schreibweg(tss.Dienst):
    """Der echte Schreibweg (schreiben.Dienst) im Thread; hoch() schickt ein Foto roh an /<reise>/bild_hochladen."""

    def hoch(self, reise, inhalt, zu="O-01", person="karl", name="Karl", geheim=True, timeout=120):
        h = {"Content-Type": "application/octet-stream",
             "X-Frieda-Bild": json.dumps({"zu": zu, "person": person, "name": name})}
        if geheim:
            h["X-Frieda-Dienst"] = self.geheim
        req = urllib.request.Request(f"{self.basis}/{reise}/bild_hochladen", data=inhalt, method="POST", headers=h)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"null")
        except (urllib.error.URLError, ConnectionError) as e:   # Dienst liest den Body nicht und schließt: keine Antwort
            return 0, str(e)


def liste_im_speicher(sp, reise="beispielreise"):
    return (yaml.safe_load(sp.rs.datei(reise, "plan/bilder.yaml").decode("utf-8")) or {}).get("bilder") or []


def alle_inhalte(sp):
    """Jeder gespeicherte Inhalt: Zeilen der Datenbank und Dateien der Ablage."""
    with closing(sqlite3.connect(sp.rs.pfad())) as v:
        zeilen = [bytes(z[0]) for z in v.execute("SELECT inhalt FROM versionen WHERE inhalt IS NOT NULL")]
    ablage = Path(os.environ["FR_SPEICHER"]) / "ablage"
    return zeilen + [f.read_bytes() for f in ablage.rglob("*") if f.is_file()]


def deutsch(a):
    from test_schreiben import deutsch as d
    return d(a)


@pytest.mark.parametrize("reise, wer, zu", [("beispielreise", tss.KARL, "O-01"), ("stadtwochenende", tss.LEA, "O-02")])
def test_upload_route_legt_eigenes_foto_an_ohne_original(speicher, reise, wer, zu):
    """V3, V7, V10: Eintrag mit quelle eigen, Anzeigename, Besitzkennung, ohne Lizenz; zwei WebP-Fassungen ohne Metadaten;
    das Original liegt nirgends (Datenbank, Ablage, Zwischenordner). Der Body ist größer als MAX_BODY (64 KB)."""
    original = foto()
    assert len(original) > sb.MAX_BODY
    vorher = {b["id"] for b in liste_im_speicher(speicher, reise)} if reise == "beispielreise" else set()
    with Schreibweg(speicher.schreiber()) as d:
        code, a = d.hoch(reise, original, zu=zu, person=wer["person"], name=wer["name"])
    assert code == 200 and a["ok"], a
    neu_ = [b for b in liste_im_speicher(speicher, reise) if b["id"] not in vorher]
    assert len(neu_) == 1, neu_
    b = neu_[0]
    assert b["quelle"] == "eigen" and b["urheber"] == wer["name"] and b["besitzer"] == wer["person"], b
    assert b["zu"] == zu and b["status"] == "aktiv" and not b.get("lizenz") and not b.get("titelbild"), b
    for fassung in ("klein", "gross"):
        ohne_metadaten(speicher.rs.datei(reise, b["dateien"][fassung]))
    inhalte = alle_inhalte(speicher)
    assert not any(KAMERA in x or XMP in x or x == original for x in inhalte)
    rest = [f for f in speicher.tmp.rglob("*") if f.is_file() and KAMERA in f.read_bytes()]
    assert rest == [], rest


def test_upload_route_nur_mit_dienst_geheimnis_und_bis_12_mb(speicher):
    stand = speicher.rs.stand_nummer("beispielreise")
    with Schreibweg(speicher.schreiber()) as d:
        assert d.hoch("beispielreise", klein_foto(), geheim=False)[0] == 403
        code, _ = d.hoch("beispielreise", b"\xff\xd8\xff\xe0" + b"\x00" * (12 * MB))
        assert code == 413
        code, a = d.hoch("beispielreise", b"kein Foto (Beispiel)")
        assert code == 422 and meldet(deutsch(a), "bild.abgelehnt.format"), a
        code, a = d.hoch("beispielreise", png_bombe(8000, 8000))
        assert code == 422 and meldet(deutsch(a), "bild.abgelehnt.format"), a
        assert d.get("gesund")[0] == 200                     # der Dienst lebt nach der Bombe weiter
    assert speicher.rs.stand_nummer("beispielreise") == stand


def _reise_yaml_setzen(sp, reise, bilder):
    roh = yaml.safe_load(sp.rs.datei(reise, "reise.yaml").decode("utf-8"))
    roh["bilder"] = bilder
    sp.rs.vorgang_schreiben(reise, {"reise.yaml": yaml.safe_dump(roh, allow_unicode=True, sort_keys=False).encode()},
                            wer="Ida", werkzeug="einstellung_setzen", titel="Grenze (Test)")


@pytest.mark.parametrize("grenze", ["anzahl", "mb"])
def test_grenze_je_reise_lehnt_ab_und_speichert_nichts(speicher, grenze):
    aktiv = sum(1 for b in liste_im_speicher(speicher) if (b.get("status") or "aktiv") == "aktiv")
    # die Fassungen der Beispielreise sind zusammen über 3 MB: max_mb 1 ist schon erreicht
    _reise_yaml_setzen(speicher, "beispielreise", {"max_anzahl": aktiv} if grenze == "anzahl" else {"max_mb": 1})
    stand, liste_vorher = speicher.rs.stand_nummer("beispielreise"), liste_im_speicher(speicher)
    with Schreibweg(speicher.schreiber()) as d:
        code, a = d.hoch("beispielreise", klein_foto())
    assert code == 422 and meldet(deutsch(a), "bild.abgelehnt.grenze"), a
    assert speicher.rs.stand_nummer("beispielreise") == stand and liste_im_speicher(speicher) == liste_vorher


def test_waisen_werden_beim_naechsten_hochladen_aufgeraeumt(speicher):
    from PIL import Image
    puffer = io.BytesIO()
    Image.new("RGB", (480, 300), "red").save(puffer, "WEBP")
    waise = {"medien/bilder/BI-77-480.webp": puffer.getvalue(), "medien/bilder/BI-77-1600.webp": puffer.getvalue()}
    speicher.rs.vorgang_schreiben("beispielreise", waise, wer="Ida", werkzeug="bild_hinzufuegen", titel="Waise (Test)")
    with Schreibweg(speicher.schreiber()) as d:
        code, a = d.hoch("beispielreise", klein_foto())
    assert code == 200 and a["ok"], a
    stand = speicher.rs.aktueller_stand("beispielreise")
    assert not any(p.startswith("medien/bilder/BI-77-") for p in stand), sorted(p for p in stand if "BI-77" in p)
    eintraege = {f for b in liste_im_speicher(speicher) for f in (b.get("dateien") or {}).values()}
    assert {p for p in stand if p.startswith("medien/bilder/")} == eintraege


def test_waisen_aufraeumen_und_fehler_mitten_im_speichern(tmp_path, monkeypatch):
    """V9, AC-7: Scheitert das Speichern der Liste nach dem Schreiben der Fassungen, bleiben keine Fassungen zurück;
    waisen_aufraeumen entfernt Dateien ohne Eintrag und lässt alle mit Eintrag stehen."""
    b = bilder_modul()
    ordner = tmp_path / "beispielreise"
    shutil.copytree(WANDERUNG, ordner)
    bilder_ordner = ordner / "medien" / "bilder"
    vorher = {f.name for f in bilder_ordner.iterdir()}
    vorab = tmp_path / "vorab"
    vorab.mkdir()
    monkeypatch.setenv("FR_BILD_VORAB", b.eigen_vorab_schreiben(vorab, b.eigen_umwandeln(klein_foto())))

    def kaputt(*a, **kw):
        raise OSError("Platte voll (Test)")
    monkeypatch.setattr(b, "speichern", kaputt)
    with pytest.raises(Exception):
        sb.bild_hochladen(ordner, {"person": "karl", "name": "Karl", "rolle": "mitwirkend"}, {"zu": "O-01"})
    assert {f.name for f in bilder_ordner.iterdir()} == vorher
    monkeypatch.undo()
    (bilder_ordner / "BI-78-480.webp").write_bytes(b"RIFF....WEBP")
    (bilder_ordner / "BI-78-1600.webp").write_bytes(b"RIFF....WEBP")
    weg = b.waisen_aufraeumen(ordner, b.laden(ordner))
    assert sorted(weg) == ["medien/bilder/BI-78-1600.webp", "medien/bilder/BI-78-480.webp"], weg
    assert {f.name for f in bilder_ordner.iterdir()} == vorher


# ---------- P1: Rückmeldedienst mit Anmeldung (V1, V6; AC-1) ----------

def hoch(u, reise, inhalt, cookie=None, zu="O-01", origin=BASIS, pfad=None):
    """Foto roh an den Rückmeldedienst wie die Seite. -> (status, json oder Text)"""
    t = urllib.parse.urlsplit(u.rurl)
    c = http.client.HTTPConnection(t.hostname, t.port, timeout=60)
    h = {"Content-Type": "application/octet-stream", "Accept-Language": "de"}
    if cookie:
        h["Cookie"] = f"__Host-frieda={cookie}"
    if origin:
        h["Origin"] = origin
    try:
        c.request("POST", pfad or f"/{reise}/bilder?zu={zu}", body=inhalt, headers=h)
        r = c.getresponse()
    except ConnectionError as e:   # Dienst liest den Body nicht und schließt: der Browser bekäme keine Antwort
        return 0, str(e)
    roh = r.read().decode("utf-8", "replace")
    try:
        return r.status, json.loads(roh)
    except ValueError:
        return r.status, roh


def weitergeleitet(u):
    """Was der Rückmeldedienst an den Schreibweg geschickt hat: [(pfad, body, kopf)] für rohe Bodies."""
    return [(p, b["roh"], {k.lower(): v for k, v in b["kopf"].items()}) for p, b in u.schreibweg
            if isinstance(b, dict) and "roh" in b]


@pytest.fixture
def mit_fotos(zwei):
    """Beide Reisen gebaut; Ida (Organisatorin), Karl (mitwirkend), Kim (Gast) der Beispielreise angemeldet, Tom nur im
    Stadtwochenende."""
    def neu_():
        u = zwei()
        u.karl_keks, _ = anmelden(u, KARL_MAIL)
        konten.einladen("beispielreise", "kim", KIM_MAIL, "gast", "Kim", "Ida")
        u.kim_keks, _ = anmelden(u, KIM_MAIL)
        u.karl = konten.konto_per_email(KARL_MAIL)
        return u
    return neu_


def test_rueckmeldedienst_nimmt_fotos_nur_von_mitwirkenden_an(mit_fotos):
    u = mit_fotos()
    inhalt = klein_foto()
    for keks, person in ((u.karl_keks, "karl"), (u.a_keks, "ida")):
        u.schreibweg.clear()
        code, a = hoch(u, "beispielreise", inhalt, keks)
        assert code in (200, 201), (person, code, a)
        w = weitergeleitet(u)
        assert len(w) == 1 and w[0][0] == "/beispielreise/bild_hochladen" and w[0][1] == inhalt, w
        meta = json.loads(w[0][2]["x-frieda-bild"])
        assert meta["zu"] == "O-01" and meta["person"] == person, meta
        assert w[0][2].get("x-frieda-dienst") == konten.dienst_geheimnis()
    u.schreibweg.clear()
    for keks, origin, erwartet in ((u.kim_keks, BASIS, 403), (u.b_keks, BASIS, 403), (None, BASIS, 401),
                                   (u.karl_keks, "https://fremd.invalid", 403), (u.karl_keks, None, 403)):
        code, a = hoch(u, "beispielreise", inhalt, keks, origin=origin)
        assert code == erwartet, (keks, origin, code, a)
    assert weitergeleitet(u) == []


def test_rolle_aus_dem_aktuellen_stand(mit_fotos):
    """Hinkt die veröffentlichte Rolle hinterher (Karl inzwischen Gast), entscheidet rolle_aktuell."""
    u = mit_fotos()
    u.rollen = {"karl": "gast"}
    code, a = hoch(u, "beispielreise", klein_foto(), u.karl_keks)
    assert code == 403, (code, a)
    assert weitergeleitet(u) == []
    assert any(r == "beispielreise" and (p == "karl" or n == "Karl") for r, p, n in u.rollen_abfragen), u.rollen_abfragen


def test_zu_gross_und_falsches_format_erreichen_den_schreibweg_nicht(mit_fotos):
    u = mit_fotos()
    code, a = hoch(u, "beispielreise", b"\xff\xd8\xff\xe0" + b"\x00" * (12 * MB), u.karl_keks)
    assert code == 413, (code, a)
    code, a = hoch(u, "beispielreise", "Nur Text mit Endung .jpg (Beispiel)".encode(), u.karl_keks)
    assert code == 415 and meldet(a["fehler"], "bild.abgelehnt.format"), (code, a)
    assert weitergeleitet(u) == []


def test_drosselung_wie_bei_belegen(mit_fotos):
    u = mit_fotos()
    inhalt = klein_foto()
    codes = [hoch(u, "beispielreise", inhalt, u.karl_keks)[0] for _ in range(31)]
    assert codes[-1] == 429 and all(c in (200, 201) for c in codes[:30]), codes


def test_stadtwochenende_nimmt_fotos_an(mit_fotos):
    """V10: Das Stadtwochenende (ohne Bilder) bekommt die Möglichkeit zum Hochladen."""
    u = mit_fotos()
    konten.einladen("stadtwochenende", "lea", LEA_MAIL, "mitwirkend", "Lea", "Tom")
    lea, _ = anmelden(u, LEA_MAIL)
    u.rollen = {"lea": "mitwirkend"}      # der nachgestellte Schreibweg kennt nur reise.yaml der Beispielreise
    code, a = hoch(u, "stadtwochenende", klein_foto(), lea, zu="O-02")
    assert code in (200, 201), (code, a)
    w = weitergeleitet(u)
    assert w and w[-1][0] == "/stadtwochenende/bild_hochladen" and json.loads(w[-1][2]["x-frieda-bild"])["zu"] == "O-02"


def test_loeschen_am_rueckmeldedienst_nur_angemeldet(mit_fotos):
    u = mit_fotos()
    s, _, _ = abruf(f"{u.rurl}/beispielreise/bilder/BI-90", "DELETE")
    assert s == 401
    assert not [p for p, _ in u.schreibweg if p.endswith("/bild_entfernen")]
    s, _, t = abruf(f"{u.rurl}/beispielreise/bilder/BI-90", "DELETE", cookie=u.karl_keks)
    assert s in (200, 204), (s, t)
    weiter = [(p, b) for p, b in u.schreibweg if p.endswith("/bild_entfernen")]
    assert weiter and weiter[-1][0] == "/beispielreise/bild_entfernen" and weiter[-1][1]["args"]["ziel"] == "BI-90", weiter
    assert weiter[-1][1].get("person") == "karl", weiter


# ---------- P1: Bau, Nennung, Verlauf, alte Einträge (V7, V13, V18; AC-5, AC-8, AC-13) ----------

def eigen_eintragen(ordner, bid="BI-90", zu="O-01", urheber="Karl", besitzer="karl", entfernt=None):
    """Eigenes Foto in plan/bilder.yaml (vorn in der Liste); entfernt: {datum, wer} statt Dateien."""
    from PIL import Image
    b = {"id": bid, "zu": zu, "quelle": "eigen", "urheber": urheber, "besitzer": besitzer,
         "hinzugefuegt": {"datum": "2026-11-21", "wer": urheber}}
    if entfernt:
        b.update(status="entfernt", entfernt=entfernt)
    else:
        (ordner / "medien" / "bilder").mkdir(parents=True, exist_ok=True)
        dateien = {}
        for fassung, breite in (("klein", 480), ("gross", 1600)):
            rel = f"medien/bilder/{bid}-{breite}.webp"
            Image.new("RGB", (breite, breite * 10 // 16), (200, 120, 40)).save(ordner / rel, "WEBP")
            dateien[fassung] = rel
        b.update(status="aktiv", dateien=dateien, breite=1600, hoehe=1000)
    p = ordner / "plan" / "bilder.yaml"
    roh = (yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else None) or {}
    roh["bilder"] = [b] + [x for x in (roh.get("bilder") or []) if x["id"] != bid]
    p.write_text(yaml.safe_dump(roh, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return b


def text_anhaengen(ordner, zeile):
    p = ordner / "inhalt" / "wissen.md"
    p.write_text(p.read_text(encoding="utf-8") + "\n\n" + zeile + "\n", encoding="utf-8")


def figuren(daten, bid):
    from test_bilder import figur
    return figur(daten, bid)


def test_bau_nennung_foto_von_und_verlauf_foto_entfernt(tmp_path):
    ordner = tmp_path / "beispielreise"
    shutil.copytree(WANDERUNG, ordner)
    eigen_eintragen(ordner, "BI-90")
    eigen_eintragen(ordner, "BI-91", entfernt={"datum": "2026-11-22", "wer": "Ida"})
    text_anhaengen(ordner, "![Unser Foto vom Bahnhof](BI-90)\n\n![Ein entferntes Foto](BI-91)")
    with tempfile.TemporaryDirectory() as t:
        bau = bauen.Bauer(ordner, t)
        d = bau.daten()
        assert not bau.fehler, bau.fehler
    x = next(b for b in d["bilder"] if b["id"] == "BI-90")
    assert x.get("eigen") is True and x.get("besitzer") == "karl", x
    assert {k: v for k, v in (x["nennung"] or {}).items() if v} == {"urheber": "Karl"}, x["nennung"]
    fig = figuren(d, "BI-90")
    assert fig and meldet(fig, "seite.bild.foto_von") and "Karl" in fig, fig
    assert "BI-91" not in [b["id"] for b in d["bilder"]] and figuren(d, "BI-91") is None
    assert d.get("bilder_entfernt") == [{"id": "BI-91", "zu": "O-01", "datum": "2026-11-22", "wer": "Ida"}], d.get("bilder_entfernt")
    assert "BI-91-" not in json.dumps(d, ensure_ascii=False, default=str)
    # alte Einträge (ohne besitzer) und die neuen Felder: nachziehen ändert nichts (V18)
    stand = {f: f.read_bytes() for f in ordner.rglob("*") if f.is_file()}
    neu.nachziehen(ordner)
    assert {f: f.read_bytes() for f in ordner.rglob("*") if f.is_file()} == stand


# ---------- P3: echtes Löschen im Reisespeicher (V11 bis V13; AC-10 bis AC-13) ----------

def webp(farbe, breite=480):
    from PIL import Image
    puffer = io.BytesIO()
    Image.new("RGB", (breite, breite * 10 // 16), farbe).save(puffer, "WEBP")
    return puffer.getvalue()


def eigen_im_speicher(sp, reise="beispielreise", bid="BI-90", besitzer="karl", urheber="Karl", inhalt=None, zu="O-01"):
    """Eigenes Foto über zwei Vorgänge in den Speicher (Fassungen, dann Liste); inhalt: (klein, gross) für gleiche Blobs."""
    klein, gross = inhalt or (webp((200, 120, 40)), webp((200, 120, 41), 1600))
    sp.rs.vorgang_schreiben(reise, {f"medien/bilder/{bid}-480.webp": klein, f"medien/bilder/{bid}-1600.webp": gross},
                            wer=urheber, werkzeug="bild_hochladen", titel=f"{bid} Fassungen (Test)")
    try:
        liste = liste_im_speicher(sp, reise)
    except KeyError:
        liste = []
    liste.append({"id": bid, "zu": zu, "quelle": "eigen", "urheber": urheber, "besitzer": besitzer, "status": "aktiv",
                  "dateien": {"klein": f"medien/bilder/{bid}-480.webp", "gross": f"medien/bilder/{bid}-1600.webp"},
                  "breite": 1600, "hoehe": 1000, "hinzugefuegt": {"datum": "2026-11-21", "wer": urheber}})
    sp.rs.vorgang_schreiben(reise, {"plan/bilder.yaml": yaml.safe_dump({"bilder": liste}, allow_unicode=True,
                                                                       sort_keys=False).encode()},
                            wer=urheber, werkzeug="bild_hochladen", titel=f"{bid} (Test)")
    return klein, gross


def mo_dazu(sp, reise="beispielreise"):
    roh = yaml.safe_load(sp.rs.datei(reise, "reise.yaml").decode("utf-8"))
    roh["personen"]["mo"] = {"name": "Mo", "rolle": "mitwirkend"}
    sp.rs.vorgang_schreiben(reise, {"reise.yaml": yaml.safe_dump(roh, allow_unicode=True, sort_keys=False).encode()},
                            wer="Ida", werkzeug="person_schreiben", titel="Mo (Test)")


def zeilen(sp, reise=None, ohne=()):
    with closing(sqlite3.connect(sp.rs.pfad())) as v:
        return [tuple(z) for z in v.execute("SELECT vorgang, reise, pfad, inhalt, pruefsumme, ausgelagert FROM versionen "
                                            + ("WHERE reise = ? " if reise else "") + "ORDER BY vorgang, pfad",
                                            (reise,) if reise else ()) if z[2] not in ohne]


def ablage_da(summe):
    import reisespeicher as rs
    return rs.ablage_pfad(summe).exists()


def summe(inhalt):
    return hashlib.sha256(inhalt).hexdigest()


def test_bild_entfernen_leert_nur_die_zwei_pfade(speicher):
    """V12, AC-11: nur medien/bilder/BI-90-480.webp und -1600.webp der Beispielreise werden in allen Versionen geleert;
    BI-901 (gleiches Präfix) und derselbe Pfad im Stadtwochenende bleiben unberührt; pruefen ist grün."""
    rs = speicher.rs
    klein, gross = eigen_im_speicher(speicher)
    eigen_im_speicher(speicher, bid="BI-901", inhalt=(webp("navy"), webp("teal", 1600)))
    eigen_im_speicher(speicher, reise="stadtwochenende", bid="BI-90", besitzer="lea", urheber="Lea", zu="O-02",
                      inhalt=(webp("olive"), webp("maroon", 1600)))
    # zweite Version desselben Pfads; mit anderem Inhalt, denn dieselben Bytes noch einmal sind kein Vorgang
    # (reisespeicher.NichtsGeaendert; Korrektur der GREEN-Phase, die RED-Fassung scheiterte schon im Aufbau)
    zweite = webp((201, 121, 41))
    rs.vorgang_schreiben("beispielreise", {"medien/bilder/BI-90-480.webp": zweite}, wer="Karl", werkzeug="test",
                         titel="neue Fassung desselben Pfads (zweite Version)")
    pfade = ("medien/bilder/BI-90-480.webp", "medien/bilder/BI-90-1600.webp")
    rest_vorher, stadt_vorher = zeilen(speicher, "beispielreise", ohne=pfade), zeilen(speicher, "stadtwochenende")
    assert rs.bild_entfernen("beispielreise", "BI-90") >= 3
    betroffen = [z for z in zeilen(speicher, "beispielreise") if z[2] in pfade]
    assert len(betroffen) == 3 and all(z[3] is None and z[4] is None for z in betroffen), betroffen
    assert zeilen(speicher, "beispielreise", ohne=pfade) == rest_vorher
    assert zeilen(speicher, "stadtwochenende") == stadt_vorher
    assert not ablage_da(summe(klein)) and not ablage_da(summe(gross)) and not ablage_da(summe(zweite))
    assert rs.pruefen() == []
    for p in pfade:
        with pytest.raises(KeyError):
            rs.datei("beispielreise", p)
    ziel = speicher.tmp / "export"
    rs.exportieren("beispielreise", ziel)
    assert not (ziel / pfade[0]).exists() and (ziel / "medien/bilder/BI-901-480.webp").exists()
    rs.materialisieren("beispielreise", speicher.tmp / "bau")
    assert not (speicher.tmp / "bau" / pfade[1]).exists()
    with pytest.raises(ValueError):
        rs.bild_entfernen("beispielreise", "BI-90%")


def test_zwei_uploads_mit_gleichem_inhalt_teilen_den_blob(speicher):
    rs = speicher.rs
    gleich = (webp("purple"), webp("purple", 1600))
    eigen_im_speicher(speicher, bid="BI-90", inhalt=gleich)
    eigen_im_speicher(speicher, bid="BI-91", besitzer="ida", urheber="Ida", inhalt=gleich)
    rs.bild_entfernen("beispielreise", "BI-90")
    assert rs.datei("beispielreise", "medien/bilder/BI-91-480.webp") == gleich[0]
    assert ablage_da(summe(gleich[0])) and rs.pruefen() == []
    rs.bild_entfernen("beispielreise", "BI-91")
    assert not ablage_da(summe(gleich[0])) and not ablage_da(summe(gleich[1])) and rs.pruefen() == []


def entfernen(sp, wer, bid="BI-90"):
    return tss.schreib(sp, "beispielreise", "bild_entfernen", {**wer, "args": {"ziel": bid}})


@pytest.mark.parametrize("wer", [tss.KARL, tss.IDA], ids=["hochladende-person", "organisatorin"])
def test_werkzeug_entfernt_foto_verlauf_bleibt(speicher, wer):
    """V11, V13, AC-10, AC-13: die hochladende Person oder eine Organisator:in entfernt; der Eintrag bleibt mit status
    entfernt und entfernt {datum, wer}, ohne Datei- und Textfelder; die Fassungen sind in allen Versionen weg; die ID wird
    nicht neu vergeben; das Bild steht im Löschprotokoll."""
    klein, _ = eigen_im_speicher(speicher)
    code, a = entfernen(speicher, wer)
    assert code == 200 and a["ok"], a
    b = next(x for x in liste_im_speicher(speicher) if x["id"] == "BI-90")
    assert b["status"] == "entfernt" and b["entfernt"]["wer"] == wer["name"] and b["entfernt"].get("datum"), b
    assert not any(b.get(f) for f in ("dateien", "bildunterschrift", "alt", "titelbild")), b
    assert b["besitzer"] == "karl"
    with pytest.raises(KeyError):
        speicher.rs.datei("beispielreise", "medien/bilder/BI-90-480.webp")
    assert not any(x == klein for x in alle_inhalte(speicher)) and speicher.rs.pruefen() == []
    assert ("beispielreise", "BI-90") in konten.bild_loeschprotokoll()
    ordner = speicher.tmp / "lesen"
    speicher.rs.materialisieren("beispielreise", ordner)
    assert sb.neue_id(ordner, "BI") != "BI-90"


def test_andere_mitwirkende_person_darf_nicht_entfernen(speicher):
    assert "bild_entfernen" in sb.WERKZEUGE and "bild_entfernen" in sb.AKTIONEN
    mo_dazu(speicher)
    eigen_im_speicher(speicher)
    stand = speicher.rs.stand_nummer("beispielreise")
    code, a = entfernen(speicher, MO)
    assert code == 422 and not a["ok"] and meldet(deutsch(a), "bild.abgelehnt.entfernen_recht"), a
    assert speicher.rs.stand_nummer("beispielreise") == stand
    assert speicher.rs.datei("beispielreise", "medien/bilder/BI-90-480.webp")


def test_commons_bild_ist_nicht_echt_loeschbar(speicher):
    """Commons und Altbestand haben keinen Besitzer: bild_entfernen gilt nur für eigene Fotos (Zurückziehen wie bisher)."""
    assert "bild_entfernen" in sb.WERKZEUGE
    commons = next(b for b in liste_im_speicher(speicher) if isinstance(b.get("quelle"), dict))
    code, a = entfernen(speicher, tss.IDA, commons["id"])
    assert code == 422 and meldet(deutsch(a), "bild.abgelehnt.nicht_eigen"), a
    assert speicher.rs.datei("beispielreise", commons["dateien"]["klein"])


def test_alte_sicherung_bringt_das_bild_nicht_zurueck(speicher):
    """Nach dem Rückspielen einer alten Sicherung entfernt der tägliche Lauf das Bild über das Löschprotokoll erneut."""
    import waechter as wa
    eigen_im_speicher(speicher)
    sicherung = speicher.tmp / "sicherung"
    shutil.copytree(os.environ["FR_SPEICHER"], sicherung)
    code, a = entfernen(speicher, tss.KARL)
    assert code == 200, a
    shutil.rmtree(os.environ["FR_SPEICHER"])
    shutil.copytree(sicherung, os.environ["FR_SPEICHER"])
    assert speicher.rs.datei("beispielreise", "medien/bilder/BI-90-480.webp")     # die alte Sicherung hat es noch
    assert wa.bildloeschungen_nachholen() == [("beispielreise", "BI-90")]
    with pytest.raises(KeyError):
        speicher.rs.datei("beispielreise", "medien/bilder/BI-90-480.webp")
    assert speicher.rs.pruefen() == [] and wa.bildloeschungen_nachholen() == []


def test_alte_sicherung_eintrag_wird_wieder_entfernt_und_reise_baut(speicher):
    """Nach dem Rückspielen einer Sicherung von vor dem Löschen stünde der Eintrag wieder aktiv in plan/bilder.yaml (ein Bild
    ohne Dateien). Der tägliche Lauf setzt ihn über einen gewöhnlichen Vorgang auf entfernt (Datum aus dem Protokoll, wer:
    der tägliche Lauf), leert Datei- und Textfelder und die Fassungen; die Reise baut ohne Fehler; ein zweiter Lauf ändert
    nichts mehr."""
    import waechter as wa
    eigen_im_speicher(speicher)
    sicherung = speicher.tmp / "sicherung"
    shutil.copytree(os.environ["FR_SPEICHER"], sicherung)
    code, a = entfernen(speicher, tss.KARL)
    assert code == 200, a
    shutil.rmtree(os.environ["FR_SPEICHER"])
    shutil.copytree(sicherung, os.environ["FR_SPEICHER"])
    assert next(x for x in liste_im_speicher(speicher) if x["id"] == "BI-90")["status"] == "aktiv"   # die alte Sicherung
    stand = speicher.rs.stand_nummer("beispielreise")
    assert wa.bildloeschungen_nachholen() == [("beispielreise", "BI-90")]
    assert speicher.rs.stand_nummer("beispielreise") == stand + 1, "ein gewöhnlicher Vorgang, nur angehängt"
    b = next(x for x in liste_im_speicher(speicher) if x["id"] == "BI-90")
    lauf = texte.t("de", "waechter.bild_entfernt_wer")
    assert b["status"] == "entfernt" and b["entfernt"]["wer"] == lauf and b["entfernt"].get("datum"), b
    assert not any(b.get(f) for f in ("dateien", "bildunterschrift", "alt", "titelbild", "breite", "hoehe")), b
    for p in ("medien/bilder/BI-90-480.webp", "medien/bilder/BI-90-1600.webp"):
        with pytest.raises(KeyError):
            speicher.rs.datei("beispielreise", p)
    assert speicher.rs.pruefen() == []
    ordner = speicher.tmp / "bau-quelle"
    speicher.rs.materialisieren("beispielreise", ordner)
    with tempfile.TemporaryDirectory() as t:
        bau = bauen.Bauer(ordner, t)
        d = bau.daten()
        assert not bau.fehler, bau.fehler
    assert "BI-90" not in [x["id"] for x in d["bilder"]]
    assert [x["id"] for x in d.get("bilder_entfernt") or []] == ["BI-90"] and d["bilder_entfernt"][0]["wer"] == lauf
    assert wa.bildloeschungen_nachholen() == [] and speicher.rs.stand_nummer("beispielreise") == stand + 1


# ---------- Nacharbeit der Prüfung (Adversary F001–F003) ----------

@pytest.mark.parametrize("aenderung", [{"wiederherstellen": True}, {"bildunterschrift": "neuer Text"},
                                       {"alt": "neuer Alt-Text"}, {"zurueckziehen": True}, {"zu": "O-01"}],
                         ids=["wiederherstellen", "bildunterschrift", "alt", "zurueckziehen", "zu"])
def test_entferntes_foto_laesst_sich_nicht_mehr_aendern(speicher, aenderung):
    """F001, AC-13: Ein entferntes eigenes Foto ist ein fester Endzustand. bild_aendern lehnt jede Änderung ab (auch für
    Organisator:innen); der Eintrag mit „Foto entfernt“ bleibt unverändert, es entsteht kein Vorgang."""
    eigen_im_speicher(speicher)
    assert entfernen(speicher, tss.KARL)[0] == 200
    vorher = next(x for x in liste_im_speicher(speicher) if x["id"] == "BI-90")
    stand = speicher.rs.stand_nummer("beispielreise")
    code, a = tss.schreib(speicher, "beispielreise", "bild_aendern", {**tss.IDA, "args": {"ziel": "BI-90", **aenderung}})
    assert code == 422 and not a["ok"] and meldet(deutsch(a), "bild.abgelehnt.entfernt"), a
    assert speicher.rs.stand_nummer("beispielreise") == stand
    nachher = next(x for x in liste_im_speicher(speicher) if x["id"] == "BI-90")
    assert nachher == vorher and nachher["status"] == "entfernt" and nachher["entfernt"]["wer"] == "Karl", nachher


def entfernen_hier(sp, wer, bid="BI-90"):
    """Werkzeug bild_entfernen im Testprozess (sb.anwenden wie der Unterprozess des Dienstes), damit Ersetzungen mit
    monkeypatch greifen."""
    arbeit = Path(tempfile.mkdtemp(dir=sp.tmp))
    basis = sp.rs.stand_nummer("beispielreise")
    sp.rs.exportieren("beispielreise", arbeit / "reisen" / "beispielreise", bis=basis)
    return sb.anwenden(sp.wurzel, arbeit, "beispielreise", "bild_entfernen", {**wer, "args": {"ziel": bid}}, basis=basis)


def _protokoll(bid="BI-90"):
    return next((z for z in konten.bild_loeschungen() if z["bild"] == bid), None)


def test_loeschprotokoll_steht_vor_dem_vorgang_und_ist_an_das_foto_gebunden(speicher, monkeypatch):
    """F002, F003: Die Zeile im Löschprotokoll steht schon, wenn der Vorgang geschrieben wird (vorgemerkt), und ist danach
    bestätigt; sie trägt die Prüfsummen der Fassungen aller Versionen."""
    import reisespeicher as rs
    klein, gross = eigen_im_speicher(speicher)
    echt, gesehen = rs.ordner_als_vorgang, []

    def beobachtet(*a, **kw):
        gesehen.append(_protokoll())
        return echt(*a, **kw)
    with monkeypatch.context() as m:
        m.setattr(rs, "ordner_als_vorgang", beobachtet)
        assert entfernen_hier(speicher, tss.KARL)[0] == 200
    assert gesehen and gesehen[0] and gesehen[0]["bestaetigt"] is False, gesehen
    z = _protokoll()
    assert z["bestaetigt"] is True and z["pruefsummen"] == {summe(klein), summe(gross)}, z
    assert ("beispielreise", "BI-90") in konten.bild_loeschprotokoll()


def test_gescheiterter_vorgang_hinterlaesst_kein_loeschprotokoll(speicher, monkeypatch):
    """F002: Scheitert der Vorgang selbst, fällt die Vormerkung wieder weg; das Foto bleibt, der Wächter lässt es in Ruhe."""
    import reisespeicher as rs
    import waechter as wa
    eigen_im_speicher(speicher)

    def gesperrt(*a, **kw):
        raise sqlite3.OperationalError("database is locked (Test)")
    with monkeypatch.context() as m:
        m.setattr(rs, "ordner_als_vorgang", gesperrt)
        code, a = entfernen_hier(speicher, tss.KARL)
    assert code == 503 and not a.get("ok"), a
    assert _protokoll() is None
    assert wa.bildloeschungen_nachholen() == []
    assert next(x for x in liste_im_speicher(speicher) if x["id"] == "BI-90")["status"] == "aktiv"
    assert speicher.rs.datei("beispielreise", "medien/bilder/BI-90-480.webp")


def test_liegengebliebene_vormerkung_ohne_vorgang_schadet_nicht(speicher):
    """F002: Stirbt der Dienst zwischen Vormerkung und Vorgang, bleibt eine unbestätigte Zeile. Der Wächter bestätigt sie nur,
    wenn der Eintrag im neuesten Stand entfernt ist; sonst verwirft er sie, ohne das Foto anzufassen."""
    import waechter as wa
    klein, gross = eigen_im_speicher(speicher)
    assert konten.bild_loeschung_vormerken("beispielreise", "BI-90", {summe(klein), summe(gross)}) is True
    assert ("beispielreise", "BI-90") not in konten.bild_loeschprotokoll()
    stand = speicher.rs.stand_nummer("beispielreise")
    assert wa.bildloeschungen_nachholen() == []
    assert _protokoll() is None and speicher.rs.stand_nummer("beispielreise") == stand
    assert speicher.rs.datei("beispielreise", "medien/bilder/BI-90-480.webp") == klein


def test_fehler_nach_dem_vorgang_ist_kein_abbruch_der_waechter_holt_nach(speicher, monkeypatch):
    """F002: Scheitern Bestätigen und Leeren nach dem festgeschriebenen Vorgang, gilt der Vorgang (200, kein 500). Die
    Vormerkung von vor dem Vorgang bleibt; der Wächter findet den Eintrag entfernt, bestätigt und leert alle Versionen."""
    import reisespeicher as rs
    import waechter as wa
    klein, _ = eigen_im_speicher(speicher)

    def gesperrt(*a, **kw):
        raise sqlite3.OperationalError("database is locked (Test)")
    with monkeypatch.context() as m:
        m.setattr(konten, "bild_loeschung_bestaetigen", gesperrt)
        m.setattr(rs, "bild_entfernen", gesperrt)
        code, a = entfernen_hier(speicher, tss.KARL)
    assert code == 200 and a["ok"], a
    assert _protokoll()["bestaetigt"] is False
    assert any(x == klein for x in alle_inhalte(speicher)), "ältere Versionen noch nicht geleert"
    assert wa.bildloeschungen_nachholen() == [("beispielreise", "BI-90")]
    assert _protokoll()["bestaetigt"] is True
    assert not any(x == klein for x in alle_inhalte(speicher)) and speicher.rs.pruefen() == []


@pytest.mark.parametrize("neues, alte_zeile", [("commons", False), ("commons", True), ("eigen", False)],
                         ids=["commons-mit-pruefsummen", "commons-zeile-von-vorher", "eigen-mit-pruefsummen"])
def test_sicherung_von_vor_dem_hochladen_neues_bild_gleicher_id_bleibt(speicher, neues, alte_zeile):
    """F003: Wird eine Sicherung von vor dem Hochladen zurückgespielt und bekommt danach ein anderes Bild dieselbe ID (aus
    Commons oder ein anderes eigenes Foto), lässt der Wächter es in Ruhe: Eintrag und Fassungen bleiben. Zeilen von vorher
    (ohne Prüfsummen) binden nur über die Quelle eigen."""
    import waechter as wa
    sicherung = speicher.tmp / "sicherung"
    shutil.copytree(os.environ["FR_SPEICHER"], sicherung)
    eigen_im_speicher(speicher)
    assert entfernen(speicher, tss.KARL)[0] == 200
    if alte_zeile:
        with closing(konten.db()) as v, v:
            v.execute("UPDATE bild_loeschungen SET pruefsummen = ''")
    shutil.rmtree(os.environ["FR_SPEICHER"])
    shutil.copytree(sicherung, os.environ["FR_SPEICHER"])
    inhalt = (webp("navy"), webp("teal", 1600))
    eigen_im_speicher(speicher, besitzer="ida", urheber="Ida", inhalt=inhalt)
    if neues == "commons":
        liste = liste_im_speicher(speicher)
        b = next(x for x in liste if x["id"] == "BI-90")
        b.pop("besitzer")
        b.update(quelle={"commons": "Beispiel.jpg"}, urheber="Beispiel", lizenz="CC0", seite="https://beispiel.invalid/")
        speicher.rs.vorgang_schreiben("beispielreise", {"plan/bilder.yaml": yaml.safe_dump(
            {"bilder": liste}, allow_unicode=True, sort_keys=False).encode()},
            wer="Ida", werkzeug="bild_hinzufuegen", titel="BI-90 aus Commons (Test)")
    vorher = next(x for x in liste_im_speicher(speicher) if x["id"] == "BI-90")
    stand = speicher.rs.stand_nummer("beispielreise")
    assert wa.bildloeschungen_nachholen() == []
    assert speicher.rs.stand_nummer("beispielreise") == stand
    assert next(x for x in liste_im_speicher(speicher) if x["id"] == "BI-90") == vorher
    assert speicher.rs.datei("beispielreise", "medien/bilder/BI-90-480.webp") == inhalt[0]
    assert speicher.rs.datei("beispielreise", "medien/bilder/BI-90-1600.webp") == inhalt[1]


def test_alte_protokollzeilen_ohne_neue_spalten_gelten_weiter(speicher):
    """F003, Formatwechsel ohne Handschritt: Eine Kontendatenbank mit der Tabelle von vorher (ohne pruefsummen und
    bestaetigt) bekommt die Spalten beim Öffnen; ihre Zeilen gelten als bestätigt ohne Prüfsummen."""
    konten.db().close()
    with closing(sqlite3.connect(konten.pfad())) as v, v:
        v.execute("DROP TABLE bild_loeschungen")
        v.execute("CREATE TABLE bild_loeschungen (reise TEXT NOT NULL, bild TEXT NOT NULL, datum TEXT NOT NULL, "
                  "PRIMARY KEY (reise, bild))")
        v.execute("INSERT INTO bild_loeschungen VALUES ('beispielreise', 'BI-90', '2026-11-20')")
    assert konten.bild_loeschungen() == [{"reise": "beispielreise", "bild": "BI-90", "datum": "2026-11-20",
                                         "pruefsummen": set(), "bestaetigt": True}]
    assert konten.bild_loeschprotokoll() == [("beispielreise", "BI-90")]


def test_konto_geloescht_nennung_gelöschte_person_organisatorin_loescht(speicher):
    geloescht = texte.t("de", "konto.geloeschte_person")
    eigen_im_speicher(speicher)
    speicher.rs.namen_ersetzen("beispielreise", "Karl", geloescht)
    b = next(x for x in liste_im_speicher(speicher) if x["id"] == "BI-90")
    assert b["urheber"] == geloescht and b["besitzer"] == "karl", b
    code, a = entfernen(speicher, tss.IDA)
    assert code == 200 and a["ok"], a


def test_quelltext_und_adr_nennen_die_dritte_ausnahme():
    import inspect
    import reisespeicher as rs
    assert "BEGIN IMMEDIATE" in inspect.getsource(rs.bild_entfernen)
    adr = (WURZEL / "docs/adr/0009-reisespeicher.md").read_text(encoding="utf-8")
    assert all(f in adr for f in ("reise_entfernen", "namen_ersetzen", "bild_entfernen")) and "#582" in adr
    verlauf = (WURZEL / "docs/adr/0001-kern.md").read_text(encoding="utf-8").split("## Verlauf", 1)[1]
    assert "#582" in verlauf


def test_datenschutztabelle_nennt_eigene_fotos():
    zeilen_ = [z for z in (WURZEL / "docs/betrieb.md").read_text(encoding="utf-8").splitlines() if z.startswith("| ")]
    assert any("Fotos" in z and "30 Tage" in z for z in zeilen_), "Zeile zu eigenen Fotos mit höchstens 30 Tagen"


# ---------- P2: Link aus dem Chat (V16; AC-16 bis AC-21) ----------

TOKEN = re.compile(r"/hochladen/([A-Za-z0-9_-]{20,})")


def link_holen(u, konto, reise="beispielreise", zu="O-01"):
    import konnektor as kn
    text, fehler = kn.frieda_werkzeug(konten.konto(konto["id"]), "bild_hochladelink", {"reise": reise, "zu": zu})
    assert not fehler, text
    text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
    m = TOKEN.search(text)
    assert m and f"{BASIS}/hochladen/" in text, text
    return m.group(1)


def db_text():
    teile = []
    with closing(konten.db()) as v:
        for (t,) in v.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"):
            teile += [str(x) for z in v.execute(f"SELECT * FROM {t}") for x in tuple(z)]
    return "\n".join(teile)


def test_werkzeug_gibt_link_token_nur_als_hash(mit_fotos):
    import konnektor as kn
    import schnittstelle
    u = mit_fotos()
    assert schnittstelle.NAMEN["image_upload_link"] == "bild_hochladelink"
    namen = lambda k: {w["name"] for w in kn.frieda_werkzeuge(konten.konto(k["id"]))}
    assert "bild_hochladelink" in namen(u.karl) and "bild_hochladelink" not in namen(konten.konto_per_email(KIM_MAIL))
    token = link_holen(u, u.karl)
    alles = db_text()
    assert token not in alles and hashlib.sha256(token.encode()).hexdigest() in alles
    z = konten.hochladelink_pruefen(token, "beispielreise")
    assert z and z["person"] == "karl" and z["rest"] == 10 and z["zu"] == "O-01", z
    assert 1790 <= z["ablauf"] - konten._jetzt() <= 1800, z
    assert konten.hochladelink_pruefen(token, "stadtwochenende") is None


def test_hochladen_ueber_link_ohne_anmeldung(mit_fotos):
    u = mit_fotos()
    token = link_holen(u, u.karl)
    inhalt = klein_foto()
    code, a = hoch(u, None, inhalt, pfad=f"/hochladen/{token}")
    assert code in (200, 201), (code, a)
    w = weitergeleitet(u)
    assert w and w[-1][0] == "/beispielreise/bild_hochladen" and w[-1][1] == inhalt, w
    meta = json.loads(w[-1][2]["x-frieda-bild"])
    assert meta["person"] == "karl" and meta["zu"] == "O-01", meta
    assert any(r == "beispielreise" for r, _, _ in u.rollen_abfragen)   # Rolle bei jedem Foto neu geprüft


def _abgelaufen(u, token):
    return hoch(u, None, klein_foto(), pfad=f"/hochladen/{token}")


def test_abgelaufen_aufgebraucht_fremd_dieselbe_antwort(mit_fotos, monkeypatch):
    u = mit_fotos()
    unbekannt = _abgelaufen(u, "x" * 43)
    text = unbekannt[1] if isinstance(unbekannt[1], str) else json.dumps(unbekannt[1], ensure_ascii=False)
    assert unbekannt[0] in (403, 404, 410) and meldet(text, "hochladen.abgelaufen"), unbekannt
    # aufgebraucht: 10 Fotos gehen, das 11. nicht
    token = link_holen(u, u.karl)
    for _ in range(10):
        assert _abgelaufen(u, token)[0] in (200, 201)
    assert _abgelaufen(u, token) == unbekannt
    # Person nicht mehr in der Reise
    token = link_holen(u, u.karl)
    konten.entfernen("beispielreise", "karl")
    assert _abgelaufen(u, token) == unbekannt
    # nach 31 Minuten
    token = link_holen(u, konten.konto(u.a["id"]))
    jetzt = konten._jetzt()
    monkeypatch.setattr(konten, "_jetzt", lambda: jetzt + 31 * 60)
    assert _abgelaufen(u, token) == unbekannt
    s, _, seite = abruf(f"{u.rurl}/hochladen/{token}")
    assert meldet(seite, "hochladen.abgelaufen_titel") and meldet(seite, "hochladen.abgelaufen"), seite[:500]


def test_herabgestufte_rolle_mit_gueltigem_token(mit_fotos):
    u = mit_fotos()
    token = link_holen(u, u.karl)
    u.schreibweg.clear()
    u.rollen = {"karl": "gast"}
    code, a = _abgelaufen(u, token)
    assert code in (401, 403, 410), (code, a)
    assert weitergeleitet(u) == []


def test_token_erlaubt_nur_hochladen(mit_fotos):
    u = mit_fotos()
    token = link_holen(u, u.karl)
    assert abruf(f"{u.rurl}/hochladen/{token}", "DELETE")[0] in (404, 405)
    assert abruf(f"{u.rurl}/hochladen/{token}/daten.json")[0] == 404
    assert abruf(f"{u.rurl}/hochladen/{token}/../beispielreise/rueckmeldungen")[0] in (400, 404)
    # als Sitzung taugt der Token nicht: Löschen und Hochladen auf der Reiseseite verlangen die Anmeldung
    assert abruf(f"{u.rurl}/beispielreise/bilder/BI-90", "DELETE", cookie=token)[0] == 401
    assert hoch(u, "beispielreise", klein_foto(), token)[0] == 401
    assert not [p for p, _ in u.schreibweg if p.endswith("/bild_entfernen")]


def _link_post(u, token, adresse, inhalt=b"\xff\xd8\xff" + b"0" * 100):
    """POST /hochladen/<token> mit X-Real-IP (wie hinter nginx) -> Status."""
    t = urllib.parse.urlsplit(u.rurl)
    c = http.client.HTTPConnection(t.hostname, t.port, timeout=60)
    try:
        c.request("POST", f"/hochladen/{token}", body=inhalt,
                  headers={"Content-Type": "application/octet-stream", "X-Real-IP": adresse, "Accept-Language": "de"})
        return c.getresponse().status
    except ConnectionError:
        return 0
    finally:
        c.close()


def test_link_prueft_token_vor_dem_lesen_und_drosselt_je_link_und_adresse(mit_fotos, monkeypatch):
    """F005: Ein ungültiger Link wird abgelehnt, ohne dass der Body gelesen wird; gedrosselt wird je Link (über wechselnde
    Adressen hinweg) und je Adresse (über wechselnde Links hinweg)."""
    import rueckmeldungen as rm
    u = mit_fotos()
    rm._zeiten.clear()
    gelesen = []
    echt = rm.Dienst._foto_lesen

    def zaehlt(self):
        gelesen.append(1)
        return echt(self)
    monkeypatch.setattr(rm.Dienst, "_foto_lesen", zaehlt)
    assert _link_post(u, "y" * 43, "192.0.2.1") == 410 and gelesen == []
    codes = [_link_post(u, "z" * 43, f"192.0.2.{10 + i}") for i in range(rm.MAX_JE_MINUTE + 1)]
    assert codes[:-1] == [410] * rm.MAX_JE_MINUTE and codes[-1] == 429, codes
    codes = [_link_post(u, f"{i:02d}" + "w" * 41, "198.51.100.7") for i in range(rm.MAX_JE_MINUTE + 1)]
    assert codes[:-1] == [410] * rm.MAX_JE_MINUTE and codes[-1] == 429, codes
    assert gelesen == []
    token = link_holen(u, u.karl)
    assert _link_post(u, token, "203.0.113.5", klein_foto()) in (200, 201) and gelesen == [1]


def test_drosselspeicher_raeumt_alte_schluessel_auf(monkeypatch):
    """F005: Schlüssel ohne Zugriff in der letzten Minute verschwinden aus dem Drosselspeicher."""
    import rueckmeldungen as rm
    jetzt = [1000.0]
    monkeypatch.setattr(rm.time, "monotonic", lambda: jetzt[0])
    monkeypatch.setattr(rm, "_zeiten", {})
    monkeypatch.setattr(rm, "_aufgeraeumt", [0.0])
    for i in range(50):
        assert rm.gedrosselt_je(f"hochladen/198.51.100.{i}") is False
    assert len(rm._zeiten) == 50
    jetzt[0] += 61
    assert rm.gedrosselt_je("hochladen/203.0.113.9") is False
    assert list(rm._zeiten) == ["hochladen/203.0.113.9"]


def test_link_seite_mit_eigener_csp_ohne_seitenlink(mit_fotos):
    u = mit_fotos()
    token = link_holen(u, u.karl)
    s, h, t = abruf(f"{u.rurl}/hochladen/{token}")
    assert s == 200, t[:500]
    csp = " ".join(kopf(h, "Content-Security-Policy"))
    assert "default-src" in csp and "frame-ancestors 'none'" in csp and "http" not in csp and "*" not in csp, csp
    assert kopf(h, "Referrer-Policy") == ["no-referrer"]
    assert SEITE not in t and urllib.parse.urlsplit(SEITE).path.strip("/") not in t and "daten.json" not in t
    for ziel in re.findall(r'\b(?:src|href|action)="([^"]*)"', t):
        assert not re.match(r"(?:[a-z]+:)?//", ziel, re.I), ziel
    for schluessel in ("hochladen.titel", "hochladen.erklaerung", "seite.bild.hinweis_personen", "hochladen.auswaehlen"):
        assert meldet(t, schluessel), schluessel


def test_konto_loeschen_raeumt_tokens_ab():
    with closing(konten.db()) as v, v:
        v.execute("INSERT INTO konten (id, email, name, angelegt, sprache) VALUES ('k-karl', ?, 'Karl', "
                  "'2026-11-01T00:00:00+00:00', 'de')", (KARL_MAIL,))
    token = konten.hochladelink_anlegen("beispielreise", "karl", "k-karl")
    h = hashlib.sha256(token.encode()).hexdigest()
    assert h in db_text()
    konten.loeschen("k-karl")
    assert h not in db_text() and "k-karl" not in db_text()


def test_doku_des_konnektors_nennt_werkzeug_und_routen():
    k = (WURZEL / "docs/konnektor.md").read_text(encoding="utf-8")
    assert "image_upload_link" in k and "bild_hochladelink" in k and "/hochladen/" in k and "bild_hochladen" in k
    assert "#582" in (WURZEL / "docs/design.md").read_text(encoding="utf-8")


# ---------- Übergreifend: Texte (V17; AC-22) ----------

NEUE_TEXTE = ("seite.bild.hochladen", "seite.bild.hochladen_blatt", "seite.bild.hochladen_abbrechen", "seite.bild.hochladen_knopf",
              "seite.bild.hochladen_anmelden", "seite.bild.hinweis_personen", "seite.bild.hinweis_metadaten",
              "seite.bild.foto_von", "seite.bild.entfernen", "seite.bild.entfernen_titel", "seite.bild.entfernen_zusage",
              "seite.bild.entfernen_behalten", "seite.bild.entfernen_ja", "seite.bild.entfernt",
              "hochladen.titel", "hochladen.zu", "hochladen.auswaehlen", "hochladen.fertig", "hochladen.laeuft", "hochladen.rest",
              "hochladen.erklaerung", "hochladen.abgelaufen_titel", "hochladen.abgelaufen",
              "bild.abgelehnt.foto_zu_gross", "bild.abgelehnt.format", "bild.abgelehnt.entfernen_recht",
              "bild.abgelehnt.nicht_eigen", "konnektor.werkzeug.bild_hochladelink")


def test_neue_texte_in_allen_sprachen():
    for kuerzel in texte.SPRACHEN:
        katalog = texte.sprache(kuerzel).TEXTE
        fehlt = [k for k in NEUE_TEXTE if k not in katalog and f"{k}.other" not in katalog]   # Mehrzahl: Schlüssel.other
        assert fehlt == [], (kuerzel, fehlt)
        assert "30" in katalog["seite.bild.entfernen_zusage"], kuerzel
        assert {"{anzahl}", "{mb}"} <= set(re.findall(r"\{\w+\}", katalog["bild.abgelehnt.grenze"])), kuerzel


def test_wortlaut_folgt_dem_entwurf():
    """AC-22: Die festen Wörter der Tabelle V17 stehen so in texte_de.py."""
    de = texte.sprache("de").TEXTE
    assert de["seite.bild.hochladen"] == "+ Foto hinzufügen"
    assert de["seite.bild.foto_von"] == "Foto: {name}"
    assert de["seite.bild.entfernen"] == "Foto entfernen" and de["seite.bild.entfernen_titel"] == "Foto entfernen?"
    assert de["seite.bild.entfernen_behalten"] == "Behalten" and de["seite.bild.entfernen_ja"] == "Entfernen"
    assert de["seite.bild.entfernt"] == "Foto entfernt am {datum} von {name}"
    assert de["hochladen.abgelaufen_titel"] == "Link abgelaufen"
    assert de["seite.bild.hinweis_personen"].startswith("Denk an die Menschen auf den Fotos.")
    assert "bis zu 30 Tage" in de["seite.bild.entfernen_zusage"]


# ---------- P1: Bibliothek und Betrieb (V19; AC-9) ----------

def test_pillow_heif_installiert_mit_lizenz_und_hashes():
    import importlib
    importlib.import_module("pillow_heif")
    assert re.search(r"(?im)^pillow[-_]heif\b", (ENGINE / "requirements.in").read_text(encoding="utf-8"))
    req = (ENGINE / "requirements.txt").read_text(encoding="utf-8")
    m = re.search(r"(?im)^pillow[-_]heif==[\d.]+[^\n]*\n((?:\s+--hash=sha256:[0-9a-f]{64}[^\n]*\n?)+)", req)
    assert m, "pillow-heif mit Hashes in requirements.txt"
    tp = (WURZEL / "THIRD_PARTY.md").read_text(encoding="utf-8")
    zeile = next((z for z in tp.splitlines() if re.search(r"pillow[-_]heif", z, re.I)), "")
    assert "BSD" in zeile and "libheif" in tp and "LGPL" in tp, zeile


def test_glibc_pruefung_vor_dem_tausch_der_python_umgebung(sw):
    """AC-9: Bei Glibc unter 2.28 bricht das Veröffentlichen vor dem Bau der neuen Python-Umgebung mit klarer Meldung ab,
    die laufende bleibt; mit ausreichender Glibc wird sie gebaut (VF_GLIBC ersetzt im Test die erkannte Version)."""
    text = (WURZEL / "betrieb/veroeffentlichen.sh").read_text(encoding="utf-8")
    assert "2.28" in text and re.search(r"glibc", text, re.I)
    extra, live = _python_vorbereiten(sw)
    sw.neuer_commit()
    vorher = sw.zeilen("venv.log")
    r = sw.lauf(**extra, VF_GLIBC="2.27")
    aus = r.stdout + r.stderr
    assert "2.28" in aus and re.search(r"glibc", aus, re.I), aus[-2000:]
    assert sw.zeilen("venv.log") == vorher, "keine neue Umgebung bei zu alter Glibc"
    assert (live / ".requirements.sha256").read_text() == "alte-liste\n" and (live / "marke").exists()
    r = sw.lauf(**extra, VF_GLIBC="2.39")
    assert str(sw.dienst / "python.neu") in sw.zeilen("venv.log"), r.stdout + r.stderr


def test_nginx_block_fuer_fotos_der_hochlade_link():
    vorlagen = WURZEL / "betrieb" / "vorlagen"
    funde = [m.group(1) for f in vorlagen.iterdir() if f.is_file()
             for m in re.finditer(r"location \^~ /hochladen/ \{(.*?)\n\}", f.read_text(encoding="utf-8"), re.S)]
    assert funde, "location ^~ /hochladen/ in einer Vorlage"
    groesse = re.search(r"client_max_body_size (\d+)m;", funde[0])
    assert groesse and 12 <= int(groesse.group(1)) <= 14, funde[0]


# ---------- Browser: Hochladen, Hinweis, Nennung, Löschen mit Zusage, Service Worker (AC-1, AC-6, AC-14, AC-15) ----------

def _browser_bereit():
    if not PLAYWRIGHT.exists() or not shutil.which("node"):
        pytest.skip("Playwright fehlt")


def _quelle(tmp_path, entfernt=False):
    """Beispielreise mit Mo (mitwirkend) und dem eigenen Foto BI-90 von Karl als Kopfbild von O-01."""
    q = tmp_path / ("quelle-entfernt" if entfernt else "quelle")
    shutil.copytree(WANDERUNG, q)
    p = q / "reise.yaml"
    roh = yaml.safe_load(p.read_text(encoding="utf-8"))
    roh["personen"]["mo"] = {"name": "Mo", "rolle": "mitwirkend"}
    p.write_text(yaml.safe_dump(roh, allow_unicode=True, sort_keys=False), encoding="utf-8")
    eigen_eintragen(q, "BI-90", entfernt={"datum": "2026-11-22", "wer": "Karl"} if entfernt else None)
    return q


class _Server:
    def __init__(self, ordner):
        import functools
        import http.server

        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a):
                pass
        self.s = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(ordner)))
        threading.Thread(target=self.s.serve_forever, daemon=True).start()
        self.basis = f"http://127.0.0.1:{self.s.server_address[1]}"

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.s.shutdown()


def _texte_fuer_browser():
    de = lambda k, **w: texte.t("de", k, **w)
    return {"hochladen": de("seite.bild.hochladen"), "knopf": de("seite.bild.hochladen_knopf", n=1),
            "hinweis": de("seite.bild.hinweis_personen"), "anmelden": de("seite.bild.hochladen_anmelden"),
            "fotoVon": de("seite.bild.foto_von", name="Karl"), "entfernen": de("seite.bild.entfernen"),
            "titel": de("seite.bild.entfernen_titel"), "zusage": de("seite.bild.entfernen_zusage"),   # Vorlage: feste Teile zählen
            "behalten": de("seite.bild.entfernen_behalten"), "ja": de("seite.bild.entfernen_ja")}


def _node(argumente, browser, timeout=600):
    aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_bilder_eigen.mjs"), str(PLAYWRIGHT), *argumente],
                         capture_output=True, text=True, timeout=timeout, env={**os.environ, "RH_BROWSER": browser})
    assert aus.returncode == 0, aus.stderr[-3000:]
    return json.loads(aus.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_browser_hochladen_hinweis_nennung_und_loeschen(tmp_path, browser):
    _browser_bereit()
    web = tmp_path / "web"
    bauen.bauen(_quelle(tmp_path), web / "beispiel")
    bauen.bauen(STADT, web / "stadt")
    datei = tmp_path / "urlaubsfoto.jpg"
    datei.write_bytes(foto(1200, 800))
    with _Server(web) as s:
        e = _node(["seite", s.basis + "/beispiel/", s.basis + "/stadt/", str(datei), json.dumps(_texte_fuer_browser())], browser)
    assert e["fehler"] == [], e["fehler"]
    a = e["aus"]
    # Hochladen (Karl, mitwirkend): erst der Hinweis ohne Haken, dann der Knopf; die Anfrage trägt das Foto roh
    k = a["karl"]
    assert k["knopfHochladen"], k
    assert k["blatt"]["hinweisSichtbar"] and k["blatt"]["hinweisVorKnopf"] and k["blatt"]["haken"] == 0, k["blatt"]
    assert k["gesendet"] and k["gesendet"][0]["methode"] == "POST", k["gesendet"]
    g = k["gesendet"][0]
    assert re.search(r"/api/bilder\?zu=O-01$", g["url"]) and g["laenge"] == datei.stat().st_size, g
    # Nennung am eigenen Foto
    assert any(a["fotoVon"] in n for n in k["nennungen"]), k["nennungen"]
    # Löschen mit Zusage: Behalten sendet nichts, erst Entfernen
    d = k["loeschen"]
    assert d["knopf"] and d["dialog"]["titel"] and d["dialog"]["zusage"] and d["dialog"]["knoepfe"] == [True, True], d
    assert d["nachBehalten"] == [] and d["nachEntfernen"] and re.search(r"/api/bilder/BI-90$", d["nachEntfernen"][0]["url"]), d
    assert d["nachEntfernen"][0]["methode"] == "DELETE"
    # andere mitwirkende Person: kein Knopf zum Entfernen; nicht angemeldet: Hinweis zum Anmelden
    assert a["mo"]["loeschen"]["knopf"] is False, a["mo"]
    assert a["gast"]["anmeldenHinweis"], a["gast"]
    # 360 px ohne Überbreite, auch mit offenem Blatt; Stadtwochenende mit Knopf, ohne Fehler
    assert not a["schmal"]["ueberbreite"] and not a["schmal"]["ueberbreiteBlatt"], a["schmal"]
    assert a["stadt"]["knopfHochladen"], a["stadt"]


@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_browser_service_worker_vergisst_geloeschtes_bild(tmp_path, browser):
    """AC-15: Liegt ein gelöschtes Bild im Speicher des Service Workers, ist es nach dem nächsten Laden der Seite weg."""
    _browser_bereit()
    web, neu_web = tmp_path / "web", tmp_path / "web-neu"
    bauen.bauen(_quelle(tmp_path), web / "beispiel")
    bauen.bauen(_quelle(tmp_path, entfernt=True), neu_web / "beispiel")
    with _Server(web) as s:
        # Service Worker nur auf https oder localhost (vorlage.html)
        basis = s.basis.replace("127.0.0.1", "localhost")
        e = _node(["sw", basis + "/beispiel/", str(web / "beispiel"), str(neu_web / "beispiel"), "BI-90-"], browser)
    assert e["fehler"] == [], e["fehler"]
    assert e["vorher"] > 0, e
    assert e["nachher"] == 0, e
