"""Bilder einer Reise, Stufe 1 (#455, #581; Spec docs/specs/oberflaeche/bilder-455-stufe1.md).

Ein Bild ist keine Grundform, keine Art und kein Merkmal, sondern eine Eigenschaft der Grundformen mit eigener Liste (wie die
Packliste). Die Liste steht in plan/bilder.yaml der Reise:

  bilder:
    - id: BI-01
      zu: E-01                     # genau eine Kennung einer Grundform oder „reise“
      quelle: {commons: Datei.jpg} # oder {wikidata: Q…, commons: Datei.jpg} oder „reise“ (aus der Reise übernommener Altbestand)
      urheber: Max Muster          # gesäuberter Text; bei quelle: reise entfallen urheber, lizenz, lizenz_url und seite
      lizenz: CC BY-SA 4.0
      lizenz_url: https://creativecommons.org/licenses/by-sa/4.0
      seite: https://commons.wikimedia.org/wiki/File:Datei.jpg
      bildunterschrift: …          # freiwillig
      alt: …                       # freiwillig
      titelbild: true              # höchstens eines je Reise
      status: aktiv                # oder zurueckgezogen (bleibt in Liste und Ablage, lässt sich wiederherstellen)
      dateien: {klein: medien/bilder/BI-01-480.webp, gross: medien/bilder/BI-01-1600.webp}
      breite: 1600
      hoehe: 1000
      hinzugefuegt: {datum: 2026-11-15, wer: Ida}

Claude nennt über den Konnektor nur eine Commons-Datei oder eine Wikidata-Kennung; Frieda holt das Bild selbst (nie das
Original, höchstens 1600 px), liest Urheber und Lizenz, prüft den Inhalt mit Pillow und legt zwei WebP-Fassungen ab. Die
Lizenz wird nicht geprüft, sondern nur eingeordnet (#613, Spec docs/specs/oberflaeche/bilder-lizenzhinweis-613.md): Die
Nutzungsrechte verantwortet die Person, die das Bild hinzufügt; einschraenkungen() liefert die Codes für den Hinweis.
Ablehnungen tragen einen Schlüssel bild.abgelehnt.* des Katalogs (Abgelehnt); der Schreibweg macht daraus seine Ablehnung.
Hier stehen keine sichtbaren Texte.
"""
import html
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

import instanz

COMMONS_API = "https://commons.wikimedia.org/w/api.php"     # FR_COMMONS_API überschreibt (zur Laufzeit gelesen)
WIKIDATA_API = "https://www.wikidata.org/w/api.php"         # FR_WIKIDATA_API überschreibt
BILDHOSTS = ("https://upload.wikimedia.org/", "https://thumb.wikimedia.org/")   # nur von hier wird eine Bilddatei geladen
COMMONS_SEITE = "https://commons.wikimedia.org/"
ZEITLIMIT = 20                 # Sekunden je Anfrage
FRIST = 60                     # Sekunden für den ganzen Abruf (vor der Sperre, unter der Wartezeit des Konnektors von 120 s)
PAUSE = 2                      # Sekunden vor der einen Wiederholung nach 429 oder 5xx
MAX_META = 1024 * 1024         # Antwort der API (Metadaten)
MAX_BILD = 15 * 1024 * 1024    # Bilddatei vor der Verkleinerung (Grenze wie bei Belegen)
MAX_URHEBER = 300
MAX_DATEINAME = 240
FASSUNGEN = {"klein": 480, "gross": 1600}
RASTER = {"JPEG", "PNG", "GIF", "WEBP", "TIFF"}
ORDNER = "medien/bilder"
LISTE = "plan/bilder.yaml"
KENNUNG = re.compile(r"BI-\d+")
WIKIDATA_KENNUNG = re.compile(r"Q\d{1,12}")
GEMEINFREI = re.compile(r"CC0(?: 1\.0)?|Public domain|PD(?:-[\w.-]+)?", re.I)
OHNE_EINSCHRAENKUNG = re.compile(r"CC BY(?:-SA)?(?: \d\.\d)?(?: [a-z]{2})?", re.I)
EINSCHRAENKUNGEN = (("nc", re.compile(r"\bNC\b", re.I)), ("nd", re.compile(r"\bND\b", re.I)),
                    ("gfdl", re.compile(r"\bGFDL\b", re.I)))
VORAB_UMGEBUNG = "FR_BILD_VORAB"


class Abgelehnt(Exception):
    """Ablehnung des Moduls: schluessel ist ein Schlüssel bild.abgelehnt.* des Katalogs, werte seine Platzhalter."""

    def __init__(self, schluessel, **werte):
        super().__init__(schluessel)
        self.schluessel, self.werte = schluessel, werte


# ---------- Lizenz und Urheber ----------

def _meta(m, feld):
    v = (m or {}).get(feld) if isinstance(m, dict) else None
    v = v.get("value") if isinstance(v, dict) else v
    return v.strip() if isinstance(v, str) else ""


def urheber_saeubern(roh):
    """HTML (Feld Artist von Commons) -> reiner Text, ohne Skript, Tags und spitze Klammern, höchstens MAX_URHEBER Zeichen."""
    import nh3
    text = nh3.clean(str(roh or ""), tags=set(), attributes={}, clean_content_tags={"script", "style"})
    text = html.unescape(text).replace("<", "").replace(">", "")
    return " ".join(text.split())[:MAX_URHEBER]


def gemeinfrei(lizenz):
    return bool(GEMEINFREI.fullmatch(str(lizenz or "").strip()))


def lizenz_lesen(extmetadata):
    """Lizenz aus extmetadata lesen -> {"lizenz", "lizenz_url", "gemeinfrei"}; wirft nie wegen der Lizenz (#613). Fehlt sie,
    ist lizenz "", lizenz_url None; als Link zählt nur https://."""
    name = urheber_saeubern(_meta(extmetadata, "LicenseShortName"))
    url = _meta(extmetadata, "LicenseUrl")
    url = "https:" + url if url.startswith("//") else "https://" + url[7:] if url.startswith("http://") else url
    return {"lizenz": name, "lizenz_url": url if re.fullmatch(r"https://[^\s\"<>]+", url) else None, "gemeinfrei": gemeinfrei(name)}


def einschraenkungen(lizenz):
    """Lizenzname -> Codes der Einschränkungen (nc, nd, gfdl; fehlt bei leerer, andere bei nicht eingeordneter Lizenz);
    leer bei CC0, gemeinfrei, CC BY und CC BY-SA. Reine Funktion, informiert nur und sperrt nie (#613)."""
    name = str(lizenz or "").strip()
    if not name:
        return ["fehlt"]
    if gemeinfrei(name) or OHNE_EINSCHRAENKUNG.fullmatch(name):
        return []
    return [code for code, muster in EINSCHRAENKUNGEN if muster.search(name)] or ["andere"]


# ---------- Abruf ----------

def _rest(ende):
    rest = ende - time.monotonic()
    if rest <= 0:
        raise Abgelehnt("bild.abgelehnt.netz")
    return min(ZEITLIMIT, rest)


def _lesen(r, grenze):
    try:
        laenge = int((r.headers or {}).get("Content-Length") or 0)
    except (TypeError, ValueError):
        laenge = 0
    if laenge > grenze:
        raise Abgelehnt("bild.abgelehnt.zu_gross")
    inhalt = r.read(grenze + 1)
    if len(inhalt) > grenze:
        raise Abgelehnt("bild.abgelehnt.zu_gross")
    return inhalt


def _holen(url, grenze, ende):
    """GET mit User-Agent der Instanz und Zeitlimit -> Bytes (höchstens grenze). Eine Wiederholung nach 429 oder 5xx
    (nach PAUSE); 404 heißt nicht gefunden; Zeitüberschreitung und andere Fehler wirft Abgelehnt("bild.abgelehnt.netz")."""
    import http.client
    for versuch in (1, 2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": instanz.kennung()})
            with urllib.request.urlopen(req, timeout=_rest(ende)) as r:
                return _lesen(r, grenze)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise Abgelehnt("bild.abgelehnt.nicht_gefunden")
            if versuch == 2 or not (e.code == 429 or e.code >= 500):
                raise Abgelehnt("bild.abgelehnt.netz")
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError, ValueError):
            raise Abgelehnt("bild.abgelehnt.netz")
        time.sleep(PAUSE)
    raise Abgelehnt("bild.abgelehnt.netz")


def _json(url, ende):
    try:
        daten = json.loads(_holen(url, MAX_META, ende).decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise Abgelehnt("bild.abgelehnt.netz")
    if not isinstance(daten, dict):
        raise Abgelehnt("bild.abgelehnt.nicht_gefunden")
    return daten


def _api(name, vorgabe):
    return os.environ.get(name) or vorgabe


def commons_name(name):
    """Dateiname auf Commons (ohne „File:“) -> bereinigter Name; sonst Abgelehnt("bild.abgelehnt.quelle")."""
    name = " ".join(str(name or "").split())
    name = re.sub(r"^file:", "", name, flags=re.I).strip()
    if not name or len(name) > MAX_DATEINAME or re.search(r"[#<>\[\]{}|]", name):
        raise Abgelehnt("bild.abgelehnt.quelle")
    return name


def p18_lesen(qid, ende):
    """Wikidata-Kennung -> Dateiname aus der Eigenschaft P18 (Bild); ohne P18 Abgelehnt("bild.abgelehnt.nicht_gefunden")."""
    if not WIKIDATA_KENNUNG.fullmatch(str(qid or "")):
        raise Abgelehnt("bild.abgelehnt.quelle")
    q = urllib.parse.urlencode({"action": "wbgetclaims", "format": "json", "entity": qid, "property": "P18"})
    daten = _json(f"{_api('FR_WIKIDATA_API', WIKIDATA_API)}?{q}", ende)
    for c in ((daten.get("claims") or {}).get("P18") or []) if isinstance(daten.get("claims"), dict) else []:
        wert = (((c or {}).get("mainsnak") or {}).get("datavalue") or {}).get("value") if isinstance(c, dict) else None
        if isinstance(wert, str) and wert.strip():
            return commons_name(wert)
    raise Abgelehnt("bild.abgelehnt.nicht_gefunden")


def bildinfo(datei, ende):
    """Metadaten einer Commons-Datei (imageinfo mit extmetadata, Fassung 1600 px) -> imageinfo mit „title“."""
    q = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size",
                                "iiurlwidth": str(FASSUNGEN["gross"]), "titles": "File:" + datei})
    daten = _json(f"{_api('FR_COMMONS_API', COMMONS_API)}?{q}", ende)
    seiten = ((daten.get("query") or {}).get("pages") or {}) if isinstance(daten.get("query"), dict) else {}
    seite = next(iter(seiten.values()), None) if isinstance(seiten, dict) else None
    info = (seite or {}).get("imageinfo") if isinstance(seite, dict) else None
    if not isinstance(seite, dict) or "missing" in seite or "invalid" in seite or not isinstance(info, list) or not info \
            or not isinstance(info[0], dict):
        raise Abgelehnt("bild.abgelehnt.nicht_gefunden")
    return {**info[0], "title": str(seite.get("title") or "")}


def raster_pruefen(inhalt):
    """Ist der Inhalt ein Rasterbild, das Pillow lesen kann (kein SVG, Video, PDF, nichts Beschädigtes)?"""
    from PIL import Image, UnidentifiedImageError
    try:
        with Image.open(io.BytesIO(inhalt)) as im:
            art = im.format
            im.load()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        raise Abgelehnt("bild.abgelehnt.kein_rasterbild")
    if art not in RASTER:
        raise Abgelehnt("bild.abgelehnt.kein_rasterbild")


def seite_von(info, datei):
    url = str(info.get("descriptionurl") or "")
    if url.startswith(COMMONS_SEITE) and not re.search(r"[\s\"<>]", url):
        return url
    return COMMONS_SEITE + "wiki/File:" + urllib.parse.quote(datei.replace(" ", "_"))


def abrufen(commons=None, wikidata=None):
    """Netzabruf: Metadaten und Bytes der verkleinerten Fassung (thumburl zu iiurlwidth 1600; Commons liefert eine Stufe
    wie 1920 px, nie das Original), nacheinander, in höchstens FRIST Sekunden ->
    {"datei", "urheber", "lizenz", "lizenz_url", "seite", "gemeinfrei", "inhalt"}; sonst Abgelehnt."""
    ende = time.monotonic() + FRIST
    datei = commons_name(commons) if commons else p18_lesen(wikidata, ende)
    info = bildinfo(datei, ende)
    lizenz = lizenz_lesen(info.get("extmetadata"))
    mime = str(info.get("mime") or "")
    if not mime.startswith("image/") or "svg" in mime:
        raise Abgelehnt("bild.abgelehnt.kein_rasterbild")
    thumb = str(info.get("thumburl") or "")
    if not thumb.startswith(BILDHOSTS):
        raise Abgelehnt("bild.abgelehnt.kein_rasterbild")
    inhalt = _holen(thumb, MAX_BILD, ende)
    raster_pruefen(inhalt)
    name = re.sub(r"^File:", "", info["title"]).strip() or datei
    return {"datei": name, "urheber": urheber_saeubern(_meta(info.get("extmetadata"), "Artist")), "seite": seite_von(info, name),
            **lizenz, "inhalt": inhalt}


# ---------- Abruf vor der Sperre (Muster kartenpunkte_vorab) ----------

def vorab_schreiben(ordner, quelle, ergebnis):
    """Ergebnis des Abrufs vor der Sperre in den Ordner -> Pfad der Datei für FR_BILD_VORAB."""
    ordner = Path(ordner)
    (ordner / "bild.bin").write_bytes(ergebnis["inhalt"])
    datei = ordner / "bild.json"
    datei.write_text(json.dumps({"quelle": quelle, "ergebnis": {k: v for k, v in ergebnis.items() if k != "inhalt"}}), encoding="utf-8")
    return str(datei)


def vorab_lesen(quelle):
    """Ergebnis aus FR_BILD_VORAB, wenn der Dienst genau diese Quelle vorab geholt hat, sonst None."""
    pfad = os.environ.get(VORAB_UMGEBUNG)
    if not pfad:
        return None
    try:
        v = json.loads(Path(pfad).read_text(encoding="utf-8"))
        if v.get("quelle") == quelle and isinstance(v.get("ergebnis"), dict):
            return {**v["ergebnis"], "inhalt": Path(pfad).with_name("bild.bin").read_bytes()}
    except (OSError, ValueError, AttributeError):
        pass
    return None


def holen(commons=None, wikidata=None):
    """Bild einer Quelle: aus dem Abruf vor der Sperre, sonst selbst aus dem Netz (abrufen)."""
    return vorab_lesen({"commons": commons, "wikidata": wikidata}) or abrufen(commons=commons, wikidata=wikidata)


# ---------- Fassungen und Liste ----------

def fassungen_schreiben(inhalt, reise_dir, bid):
    """Zwei WebP-Fassungen (480 und 1600 px breit, nie vergrößert, ohne EXIF) nach medien/bilder/ ->
    {"dateien": {"klein", "gross"}, "breite", "hoehe"} (Maße der großen Fassung)."""
    from PIL import Image, ImageOps
    raster_pruefen(inhalt)
    (Path(reise_dir) / ORDNER).mkdir(parents=True, exist_ok=True)
    dateien, masse = {}, {}
    with Image.open(io.BytesIO(inhalt)) as roh:
        im = ImageOps.exif_transpose(roh)
        im = im.convert("RGBA" if "A" in im.getbands() or "transparency" in im.info else "RGB")
        for fassung, breite in FASSUNGEN.items():
            b = min(breite, im.width)
            h = max(1, round(im.height * b / im.width))
            rel = f"{ORDNER}/{bid}-{breite}.webp"
            (im if b == im.width else im.resize((b, h), Image.LANCZOS)).save(Path(reise_dir) / rel, "WEBP", quality=80)
            dateien[fassung], masse[fassung] = rel, (b, h)
    return {"dateien": dateien, "breite": masse["gross"][0], "hoehe": masse["gross"][1]}


def laden(reise_dir):
    """plan/bilder.yaml -> Liste der Einträge ([] ohne Datei). Eine kaputte Liste wirft ValueError oder yaml.YAMLError."""
    p = Path(reise_dir) / LISTE
    if not p.exists():
        return []
    roh = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    liste = roh.get("bilder") if isinstance(roh, dict) else None
    if liste is None and isinstance(roh, dict):
        return []
    if not isinstance(liste, list) or not all(isinstance(b, dict) and KENNUNG.fullmatch(str(b.get("id") or "")) for b in liste):
        raise ValueError(LISTE)
    return liste


def speichern(reise_dir, liste, kopf=""):
    """Liste nach plan/bilder.yaml, mit Kopfkommentar (Zeilen von kopf)."""
    p = Path(reise_dir) / LISTE
    p.parent.mkdir(parents=True, exist_ok=True)
    kommentar = "".join(f"# {z}\n" if z else "#\n" for z in str(kopf or "").splitlines())
    p.write_text(kommentar + yaml.safe_dump({"bilder": liste}, allow_unicode=True, sort_keys=False, width=10**6), encoding="utf-8")


def aktiv(b):
    return isinstance(b, dict) and (b.get("status") or "aktiv") == "aktiv"
