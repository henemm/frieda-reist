#!/usr/bin/env python3
"""Belege zu Buchungen (Product Owner 29.10.2026, frieda-reist #76): Buchungsbestätigung, Ticket, Rechnung als Datei.

Eine Buchung (B-…) steht als eigenes Ding in plan/routen.yaml der Reise (engine/routen.py). Ihr Beleg ist eine Datei und
liegt nie im Repo: Er gehört in die Ablage der Instanz, <ablage>/<reise>/belege/, neben Rückmeldungen und Aufgaben, und
dieser Dienst (engine/rueckmeldungen.py) ist sein einziger Schreiber. Das Verzeichnis belege.json hält je Datei: welche
Buchung, Name, Typ, Größe, wer sie hochgeladen hat, wann, und wer sie sehen darf.

Regeln (Product Owner 28.10.2026 in #76):
- Hochladen ab Rolle Mitwirkende:r (Aktion „buchung“, reise.AKTIONEN), über die Reiseseite bei der Buchung. Der Konnektor
  bekommt von Claude nur Text, keine Dateien; dort trägt die Person Nummer, Frist und Stornoregel ein (buchung_anlegen).
- Sehen: sichere Vorgabe nur die hochladende Person und Organisator:innen („beteiligte“); eine Organisator:in gibt einen
  Beleg für alle Personen der Reise frei („alle“). Ohne Anmeldung sieht die Seite nur freigegebene Belege.
- Nichts wird gelöscht: Ein Beleg lässt sich zurückziehen (zurueckgezogen mit Person und Zeit), die Datei bleibt.
- Grenzen: 10 MB je Datei, 100 MB und 200 Dateien je Reise; erlaubt sind PDF, JPEG, PNG, WebP und HEIC, geprüft am Inhalt
  (Magic Bytes), nicht an der Endung.
"""
import datetime
import json
import re
import unicodedata
from pathlib import Path

import texte

MAX_DATEI = 10 * 1024 * 1024
MAX_REISE = 100 * 1024 * 1024
MAX_ANZAHL = 200
TYPEN = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/heic": "heic",
         "text/plain; charset=utf-8": "txt"}   # txt: Abschrift einer Bestätigung aus dem Gespräch (beleg_anlegen, Issue #135)
SICHTBAR = ("beteiligte", "alle")
DID_MUSTER = re.compile(r"^D-\d{2,}$")
BID_MUSTER = re.compile(r"^B-\d+$")


def typ_erkennen(daten, dateiname=None):
    """MIME-Typ aus den ersten Bytes oder None, wenn kein erlaubter Typ. Text (UTF-8, ohne Steuerzeichen) nur, wenn der
    Dateiname .txt oder .md heißt: die Abschrift einer Bestätigung, die der AI-Client über den Konnektor anhängt."""
    k = daten[:16]
    if str(dateiname or "").lower().endswith((".txt", ".md")):
        try:
            t = daten.decode("utf-8")
        except UnicodeDecodeError:
            return None
        return "text/plain; charset=utf-8" if t.strip() and not any(ord(c) < 32 and c not in "\n\r\t" for c in t) else None
    if k.startswith(b"%PDF-"):
        return "application/pdf"
    if k.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if k.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if k[:4] == b"RIFF" and k[8:12] == b"WEBP":
        return "image/webp"
    if k[4:8] == b"ftyp" and k[8:12] in (b"heic", b"heix", b"mif1", b"msf1", b"heif"):
        return "image/heic"
    return None


def name_saeubern(name):
    """Dateiname aus der Anfrage -> kurzer, ungefährlicher Anzeigename (nur zum Zeigen; gespeichert wird unter der D-ID)."""
    n = unicodedata.normalize("NFC", str(name or "")).strip().replace("\\", "/").split("/")[-1]
    n = re.sub(r"[\x00-\x1f\x7f]", "", n)[:120].strip()
    return n or "Beleg"


def lesen(o):
    try:
        d = json.loads((Path(o) / "belege.json").read_text(encoding="utf-8"))
        if isinstance(d, dict) and isinstance(d.get("belege"), list):
            return d
    except (OSError, ValueError):
        pass
    return {"naechste": 1, "belege": []}


def speichern(o, d):
    pfad = Path(o) / "belege.json"
    tmp = pfad.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(pfad)


def jetzt_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def darf_sehen(b, name, rolle):
    """Darf diese Person (Name, Rolle der Reise; None = nicht angemeldet) den Beleg sehen?"""
    if b.get("sichtbar") == "alle":
        return rolle is not None
    if rolle == "organisator":
        return True
    return bool(name) and str(b.get("wer", "")).casefold() == str(name).casefold()


def liste(o, name, rolle, buchung=None):
    """Belege, die die Person sehen darf (zurückgezogene nur für Organisator:innen und die hochladende Person)."""
    aus = []
    for b in lesen(o)["belege"]:
        if buchung and b.get("buchung") != buchung:
            continue
        if not darf_sehen(b, name, rolle):
            continue
        if b.get("zurueckgezogen") and not (rolle == "organisator" or str(b.get("wer", "")).casefold() == str(name or "").casefold()):
            continue
        aus.append(b)
    return aus


def datei_pfad(o, b):
    return Path(o) / "belege" / b["datei"]


def ablegen(o, bid, name, dateiname, daten):
    """Eine Datei zu einer Buchung ablegen -> (eintrag, None) oder (None, (code, fehler))."""
    if not BID_MUSTER.match(bid or ""):
        return None, (404, texte.satz("dienst.belege.buchung_unbekannt"))
    if not daten:
        return None, (400, texte.satz("dienst.belege.leer"))
    if len(daten) > MAX_DATEI:
        return None, (413, texte.satz("dienst.belege.zu_gross", mb=MAX_DATEI // 1024 // 1024))
    typ = typ_erkennen(daten, dateiname)
    if typ is None:
        return None, (415, texte.satz("dienst.belege.format"))
    d = lesen(o)
    if len(d["belege"]) >= MAX_ANZAHL:
        return None, (409, texte.satz("dienst.belege.anzahl", n=MAX_ANZAHL))
    if sum(int(b.get("groesse") or 0) for b in d["belege"]) + len(daten) > MAX_REISE:
        return None, (409, texte.satz("dienst.belege.platz", mb=MAX_REISE // 1024 // 1024))
    did = f"D-{d['naechste']:02d}"
    b = {"id": did, "buchung": bid, "name": name_saeubern(dateiname), "datei": f"{did}.{TYPEN[typ]}", "typ": typ, "groesse": len(daten),
         "wer": name, "hochgeladen": jetzt_iso(), "sichtbar": "beteiligte", "zurueckgezogen": None}
    ordner = Path(o) / "belege"
    ordner.mkdir(mode=0o750, exist_ok=True)
    ziel = ordner / b["datei"]
    tmp = ziel.with_suffix(ziel.suffix + ".tmp")
    tmp.write_bytes(daten)
    tmp.chmod(0o640)
    tmp.replace(ziel)
    d["naechste"] += 1
    d["belege"].append(b)
    speichern(o, d)
    return b, None


def aendern(o, did, roh, name, rolle):
    """Sichtbarkeit setzen (nur Organisator:innen) oder zurückziehen (hochladende Person oder Organisator:in)
    -> (eintrag, None) oder (None, (code, fehler))."""
    d = lesen(o)
    b = next((x for x in d["belege"] if x["id"] == did), None)
    if b is None:
        return None, (404, texte.satz("dienst.belege.nicht_gefunden"))
    eigener = str(b.get("wer", "")).casefold() == str(name or "").casefold()
    geaendert = False
    if "sichtbar" in roh:
        if rolle != "organisator":
            return None, (403, texte.satz("dienst.belege.sichtbar_organisator"))
        if roh["sichtbar"] not in SICHTBAR:
            return None, (400, texte.satz("dienst.belege.sichtbar_wert"))
        if b.get("sichtbar") != roh["sichtbar"]:
            b["sichtbar"] = roh["sichtbar"]
            geaendert = True
    if roh.get("zurueckziehen"):
        if not (eigener or rolle == "organisator"):
            return None, (403, texte.satz("dienst.belege.zurueckziehen"))
        if not b.get("zurueckgezogen"):
            b["zurueckgezogen"] = {"wer": name, "zeit": jetzt_iso()}
            geaendert = True
    if not geaendert:
        return None, (400, texte.satz("dienst.belege.nichts"))
    speichern(o, d)
    return b, None


def finden(o, did):
    if not DID_MUSTER.match(did or ""):
        return None
    return next((x for x in lesen(o)["belege"] if x["id"] == did), None)
