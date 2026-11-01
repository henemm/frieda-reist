#!/usr/bin/env python3
"""Erzeugt aus den Markdown-Dateien einer Reise eine eigenständige Webseite.

Aufruf:  python engine/bauen.py [--reisen ORDNER] [--ziel ORDNER] <reise>
         (Vorgabe: reisen/ und dist/ im aktuellen Ordner, also im Repo der Reisen)
Ergebnis: <ziel>/<reise>/index.html, daten.json, verkleinerte Bilder und die PWA-Hülle
(manifest.json, Icons, sw.js mit Inhalts-Hash als Version; Issue #6).

Eckdaten, Status, Personen und Einstellungen stehen in reisen/<reise>/reise.yaml (siehe reise.py),
die Zuordnung der Inhalte (Abschnitt -> ID, Kennzahlen) in reisen/<reise>/reise.json,
der Plan mit allen Alternativen in reisen/<reise>/plan/routen.yaml (siehe routen.py).
"""
import datetime
import hashlib
import html as htmlmod
from html.parser import HTMLParser
import json
import os
import shutil
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import markdown
    import yaml
    from PIL import Image, ImageOps
except ImportError:
    # Außerhalb der Projektumgebung gestartet: automatisch in engine/.venv neu starten.
    venv_python = WURZEL / "engine" / ".venv" / "bin" / "python"
    if venv_python.exists() and Path(sys.prefix).resolve() != (WURZEL / "engine" / ".venv").resolve():
        os.execv(str(venv_python), [str(venv_python), *sys.argv])
    sys.exit("Es fehlen Programmteile. Einmalig einrichten:\n"
             "  python3 -m venv engine/.venv && engine/.venv/bin/pip install -r engine/requirements.txt\n"
             "Danach läuft:  python3 engine/bauen.py <reise>")
from reise import Reise  # noqa: E402
from routen import FARBEN, Routen, verhalten_anwenden  # noqa: E402
import gpx  # noqa: E402
import texte  # noqa: E402

ZIEL_ID = re.compile(r"^[A-Za-z0-9][\w.\-]{0,79}$", re.ASCII)
BILD_ENDUNGEN = (".jpg", ".jpeg", ".png", ".webp", ".gif")
def etappen_muster():
    """Titel einer Etappe („Etappe 3: Name“, englisch „Stage 3: Name“): das Wort aller Sprachen des Katalogs (ADR-0006, Punkt 7)."""
    return r"^(?:" + texte.inhaltsmuster("inhalt.etappe") + r")\s+(\d+[A-Za-z]?)\s*:\s*(.+)$"
UMLAUTE = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
# Ebenen der Tagesseite (B2, docs/design.md „Tagesseite“): Jeder Abschnitt einer Etappe gehört zu einer Ebene, erkannt am
# Anfang seines Titels (Groß- und Kleinschreibung egal). Die Software kennt nur die Form (ADR-0001, kein Katalog): die
# Zusammenfassung ist „Der Weg“, Eckdaten (die Kennzahlentabelle) und die Unterkünfte-Liste des Dossiers sind „Unterwegs
# nachschlagen“, Quellen, Prüfung und Karten sind „Quellen und Prüfung“. Welche Rubriken eine Reise sonst unterwegs
# nachschlagen will (Höhenprofil, Wegpunkte, Wasser, Fahrplan, Tempel …), sagt sie in reise.json „etappen_ebenen“
# ({"unterwegs": ["Höhenprofil", "Fahrplan"], …}); die Titelanfänge der Reise gelten vor der Vorgabe. Was nirgends passt,
# ist Hintergrund. Bis 29.10.2026 enthielt die Vorgabe Wandervokabular (Wegpunkte, Wasser, Einkehr, Verpflegung).
EBENEN = ("weg", "unterwegs", "hintergrund", "quellen")
def ebenen_vorgabe():
    """Titelanfänge je Ebene aus dem Katalog, in allen Sprachen (inhalt.ebene.*)."""
    def woerter(*schluessel):
        return tuple(sorted(set().union(*(texte.inhaltswoerter(s) for s in schluessel))))
    return {"weg": woerter("inhalt.ebene.zusammenfassung"),
            "unterwegs": woerter("inhalt.ebene.eckdaten", "inhalt.ebene.unterkuenfte"),
            "quellen": woerter("inhalt.ebene.quellen", "inhalt.ebene.pruefung", "inhalt.ebene.karten")}
# Stichwort am Anfang eines Absatzes im Lesetext („**Charakter.** …“), Rubrik der Gliederung einer Art (docs/ontologie.md)
STICHWORT = re.compile(r"<p>\s*<strong>([^<]{1,60})</strong>")
BILD_LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)\)")


class BauFehler(Exception):
    """Sammelt verständliche Fehlermeldungen."""

    def __init__(self, meldungen):
        self.meldungen = list(meldungen)
        super().__init__("\n".join(self.meldungen))


def slug(text):
    t = text.lower()
    for k, v in UMLAUTE.items():
        t = t.replace(k, v)
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:60] or "abschnitt"


def zerlege(text, ebene):
    """Teilt Text an Überschriften der Ebene (2 = '##'). -> (vorspann, [(titel, zeile, body)])"""
    marke = "#" * ebene + " "
    vor, teile, aktuell = [], [], None
    for nr, zeile in enumerate(text.splitlines(), 1):
        if zeile.startswith(marke):
            aktuell = [zeile[len(marke):].strip(), nr, []]
            teile.append(aktuell)
        elif aktuell is None:
            vor.append(zeile)
        else:
            aktuell[2].append(zeile)
    return "\n".join(vor), [(t, n, "\n".join(b)) for t, n, b in teile]


FUSSNOTE_DEF = re.compile(r"^\[\^(\d+)\]:\s*(.*)$")
FUSSNOTE_REF = re.compile(r"\[\^(\d+)\]")


def fussnote_html(definition):
    """„Titel | URL | Datum“ -> Titel, Link, Datum. Pfade ohne http (Arbeitsdateien der Recherche) sind nicht
    erreichbar und erscheinen als „projektintern“."""
    teile = [t.strip() for t in definition.split(" | ")]
    titel, url, datum = (teile + ["", ""])[:3] if len(teile) <= 3 else (" | ".join(teile[:-2]), teile[-2], teile[-1])
    aus = [htmlmod.escape(titel)]
    if url.startswith(("http://", "https://")):
        aus.append(f'<a target="_blank" rel="noopener" href="{htmlmod.escape(url)}">{htmlmod.escape(url.split("//", 1)[1].split("/", 1)[0])}</a>')
    elif url:
        aus.append("projektintern")
    if datum:
        aus.append(htmlmod.escape(datum))
    return " · ".join(aus)


class TextPruefung(HTMLParser):
    """Reisetexte sind Fließtext (docs/design.md, Reisetexte): nur, was Markdown selbst erzeugt. Eigenes HTML mit
    Stilen, Klassen oder Bausteinen umgeht das Designsystem. Sammelt, was nicht vorgesehen ist."""
    TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "a", "img", "em", "strong", "code", "pre",
            "blockquote", "hr", "br", "table", "thead", "tbody", "tr", "th", "td"}
    ATTRIBUTE = {"a": {"href", "title"}, "img": {"src", "alt", "title"}, "th": {"style"}, "td": {"style"}}

    def __init__(self):
        super().__init__()
        self.fremd = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.TAGS:
            self.fremd.append(f"<{tag}>")
        for k, v in attrs:
            # Spaltenausrichtung der Tabellen-Erweiterung ist das einzige erlaubte style
            if k == "style" and re.fullmatch(r"text-align: (left|right|center);", v or ""):
                continue
            if k not in self.ATTRIBUTE.get(tag, ()):
                self.fremd.append(f"<{tag} {k}>")


TABELLE = re.compile(r"<table>(.*?)</table>", re.S)
ZEILE = re.compile(r"<tr>(.*?)</tr>", re.S)
ZELLE = re.compile(r"<t([hd])([^>]*)>(.*?)</t\1>", re.S)
LEER = re.compile(r"\s*[–—-]?\s*")


def ohne_tags(h):
    return re.sub(r"<[^>]+>", "", h).strip()


def tabellen_ordnen(h):
    """Tabellen aus Reisetexten lesbar machen (B2, docs/design.md, Reisetexte). Der Text bleibt reines Markdown,
    die Seite ordnet: zweispaltig (Merkmal | Wert) wird eine Merkmalliste <dl class="textmerkmale"> ohne Kopfzeile,
    ein „/“ im Merkmal darf umbrechen. Breitere Tabellen bleiben Tabellen (.tabelle.stapel); jede Zelle trägt ihren
    Spaltenkopf (data-spalte), leere Zellen („–“) heißen „leer“, damit die Seite sie bei wenig Platz je Zeile stapeln kann."""
    def ordne(m):
        zeilen = [ZELLE.findall(z) for z in ZEILE.findall(m.group(1))]
        kopf = [ohne_tags(c[2]) for c in zeilen[0]] if zeilen and all(c[0] == "h" for c in zeilen[0]) else []
        rumpf = zeilen[1:] if kopf else zeilen
        if len(kopf) == 2 and all(len(z) == 2 for z in rumpf):
            def merkmal(c):   # „/“ nur im Text, nicht in Links oder Attributen
                return "".join(t if t.startswith("<") else t.replace("/", "/<wbr>") for t in re.split(r"(<[^>]+>)", c.strip()))
            return '<div class="tabelle merkmale"><dl class="textmerkmale">' + "".join(
                f"<div><dt>{merkmal(z[0][2])}</dt><dd>{z[1][2].strip()}</dd></div>" for z in rumpf) + "</dl></div>"
        def zelle(c, i):
            spalte = f' data-spalte="{htmlmod.escape(htmlmod.unescape(kopf[i]))}"' if c[0] == "d" and i < len(kopf) and kopf[i] else ""
            leer = ' class="leer"' if LEER.fullmatch(ohne_tags(c[2])) else ""
            return f"<t{c[0]}{c[1]}{spalte}{leer}>{c[2]}</t{c[0]}>"
        def tr(z):
            return "<tr>" + "".join(zelle(c, i) for i, c in enumerate(z)) + "</tr>"
        thead = "<thead>" + tr(zeilen[0]) + "</thead>" if kopf else ""
        return f'<div class="tabelle stapel"><table>{thead}<tbody>{"".join(tr(z) for z in rumpf)}</tbody></table></div>'
    return TABELLE.sub(ordne, h)


def trenner_entfernen(text):
    zeilen = text.rstrip().splitlines()
    while zeilen and zeilen[-1].strip() in ("---", ""):
        zeilen.pop()
    return "\n".join(zeilen).strip("\n")


def ist_tabellenzeile(z):
    return z.lstrip().startswith("|")


def ist_listenzeile(z):
    return bool(re.match(r"\s*([-*+]|\d+[.)])\s", z))


def normalisieren(text):
    """Python-Markdown braucht eine Leerzeile vor Listen und Tabellen. Nur Leerzeilen, kein Text."""
    aus, vorher = [], ""
    for z in text.splitlines():
        beginnt = ist_tabellenzeile(z) or ist_listenzeile(z)
        vorher_block = ist_tabellenzeile(vorher) or ist_listenzeile(vorher) or vorher.startswith((" ", "\t"))
        if beginnt and vorher.strip() and not vorher_block:
            aus.append("")
        aus.append(z)
        vorher = z
    return "\n".join(aus)


def zellen(zeile):
    z = zeile.strip()
    if z.startswith("|"):
        z = z[1:]
    if z.endswith("|") and not z.endswith("\\|"):
        z = z[:-1]
    teile = re.split(r"(?<!\\)\|", z)
    return [t.replace("\\|", "|").strip() for t in teile]


def tabelle_lesen(text, quelle, fehler):
    """Erste Markdown-Tabelle im Text. -> (davor, kopf, zeilen, danach) oder None."""
    zeilen = text.splitlines()
    start = next((i for i, z in enumerate(zeilen) if ist_tabellenzeile(z)), None)
    if start is None:
        return None
    ende = start
    while ende < len(zeilen) and ist_tabellenzeile(zeilen[ende]):
        ende += 1
    kopf = zellen(zeilen[start])
    zeilen_aus = []
    for i in range(start + 2, ende):
        werte = zellen(zeilen[i])
        if len(werte) != len(kopf):
            fehler.append(f"{quelle}: Tabellenzeile hat {len(werte)} statt {len(kopf)} Spalten: {zeilen[i][:60]}")
            continue
        zeilen_aus.append(werte)
    return "\n".join(zeilen[:start]), kopf, zeilen_aus, "\n".join(zeilen[ende:])


def als_datum(x):
    """Datum aus YAML (Datum oder Text JJJJ-MM-TT) -> datetime.date oder None, wenn es keins ist."""
    if isinstance(x, datetime.date):
        return x
    try:
        return datetime.date.fromisoformat(x) if isinstance(x, str) else None
    except ValueError:
        return None


def punkt_geprueft(p, stand, wo, fehler):
    """Prüfdatum eines Kartenpunkts: eigenes „geprueft“ oder der „stand“ der Datei (JJJJ-MM-TT) -> ISO-Text oder None."""
    g = p.get("geprueft", stand)
    if g is None:
        return None
    if als_datum(g) is None:
        fehler.append(f"{wo}: geprueft muss ein Datum sein (JJJJ-MM-TT).")
        return None
    return als_datum(g).isoformat()



def warnungen_in_reisesprache(daten):
    """Warnungen des Baus (Sätze des Katalogs) für die Datei: der Text in der Sprache der Reise (die Seite zeigt ihn so), dazu die Teile
    des Satzes, aus denen der Konnektor ihn in der Sprache der Person setzt (ADR-0006). Die Daten im Speicher bleiben unberührt."""
    route = daten.get("route") or {}
    if not route.get("warnungen"):
        return daten
    sprache = daten["reise"]["sprache"]
    neu = [{**w, "text": w["text"].text(sprache), "teile": w["text"].teile_json()} if isinstance(w.get("text"), texte.Satz) and w["text"].mit_schluesseln()
           else w for w in route["warnungen"]]
    return {**daten, "route": {**route, "warnungen": neu}}

class Bauer:
    def __init__(self, reise_dir, ziel_dir, umzug=None):
        self.reise_dir = Path(reise_dir)
        self.umzug = (umzug or os.environ.get("FR_UMZUG_NACH") or "").rstrip("/") or None  # neue Adresse (Ursprung), siehe sw.vorlage.js
        self.ziel_dir = Path(ziel_dir)
        self.fehler = []
        self._kategorien = None  # plan/kategorien.yaml, beim ersten Gebrauch geladen
        self.ids = {}
        self.bilder = {}  # Quelldatei -> relativer Zielpfad
        self.grundkarte = None  # PMTiles-Datei der Offline-Karte, falls vorhanden
        self.grundkarten = {}  # regionale Grundkarten der Recherche-Karten: Zielname -> Quelldatei
        self.hinweise = []  # Meldungen, die das Bauen nicht verhindern
        self.fussnoten = {}  # Quelldatei -> {Nummer: Definition}
        self.md = markdown.Markdown(extensions=["tables"])
        pfad = self.reise_dir / "reise.json"
        if not pfad.exists():
            raise BauFehler([texte.satz("pruefung.bauen.datei_fehlt", pfad=pfad)])
        self.cfg = json.loads(pfad.read_text(encoding="utf-8"))
        # Eckdaten, Status, Personen, Bausteine, Regeln, Darstellung (docs/produkt.md); fehlt die Datei, alte Form
        self.reise_roh = None
        if (self.reise_dir / "reise.yaml").exists():
            try:
                self.reise_roh = yaml.safe_load((self.reise_dir / "reise.yaml").read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as e:
                raise BauFehler([texte.satz("pruefung.bauen.yaml_reise", e=e)])
        self.eck = Reise(self.reise_roh, self.cfg, self.fehler, self.hinweise).daten()
        self.etappen_muster = re.compile(self.cfg.get("etappen_muster", etappen_muster()))

    # ---------- Hilfen ----------
    def id_anlegen(self, id_, wo):
        if not ZIEL_ID.match(id_):
            self.fehler.append(texte.satz("pruefung.bauen.1", wo=wo, id_=id_))
        if id_ in self.ids:
            self.fehler.append(texte.satz("pruefung.bauen.2", id_=id_, w1=self.ids[id_], wo=wo))
        self.ids[id_] = wo

    def ignoriert(self, rel, titel):
        """Überschriften, die bewusst nicht auf die Seite kommen (reise.json -> ignorieren)."""
        return any(titel.startswith(t) for t in self.cfg.get("ignorieren", {}).get(rel, []))

    def lesen(self, rel):
        if rel is None:  # Datei ist für diese Reise nicht vorgesehen
            return ""
        p = self.reise_dir / rel
        if not p.exists():
            self.fehler.append(texte.satz("pruefung.bauen.3", rel=rel))
            return ""
        return self.fussnoten_lesen(p, p.read_text(encoding="utf-8"))

    def fussnoten_lesen(self, p, text):
        """Fußnoten-Definitionen „[^12]: Titel | URL | Datum“ stehen meist gesammelt am Dateiende, die Datei
        wird aber abschnittsweise umgewandelt. Deshalb hier je Datei einsammeln und aus dem Text nehmen
        (Leerzeile statt Zeile, damit Zeilennummern in Meldungen stimmen); html() setzt sie je Block ein."""
        noten, zeilen = {}, []
        for z in text.splitlines():
            m = FUSSNOTE_DEF.match(z)
            if m:
                noten[m.group(1)] = m.group(2).strip()
                z = ""
            zeilen.append(z)
        if noten:
            self.fussnoten[p] = noten
        return "\n".join(zeilen)

    def finde_abschnitt(self, rel, titel, nr, benutzt):
        """Exakter Treffer, sonst eindeutiger Präfix. -> Eintrag oder None"""
        karte = self.cfg.get("abschnitte", {}).get(rel, {})
        if titel in karte:
            benutzt.add(titel)
            return karte[titel]
        treffer = [k for k in karte if titel.startswith(k)]
        if len(treffer) == 1:
            benutzt.add(treffer[0])
            return karte[treffer[0]]
        if len(treffer) > 1:
            self.fehler.append(texte.satz("pruefung.bauen.4", rel=rel, nr=nr, titel=titel, treffer=treffer))
        return None

    def html(self, md_text, quelldatei):
        md_text = trenner_entfernen(md_text)
        md_text = self.bilder_umschreiben(md_text, quelldatei)
        self.md.reset()
        h = self.md.convert(normalisieren(md_text))
        pruefung = TextPruefung()
        pruefung.feed(h)
        if pruefung.fremd:
            self.fehler.append(texte.satz("pruefung.bauen.5", w1=Path(quelldatei).name, w2=', '.join(dict.fromkeys(pruefung.fremd))))
        h = tabellen_ordnen(h)
        h = re.sub(r'<a href="(https?://)', r'<a target="_blank" rel="noopener" href="\1', h)
        h = re.sub(r'<img ', '<img loading="lazy" ', h)
        h = re.sub(r'<li><a href="(medien/[^"]+\.(?:jpe?g|png|webp|gif))">([^<]*)</a>',
                   r'<li><a class="bild" target="_blank" href="\1"><img loading="lazy" src="\1" alt=""><span>\2</span></a>', h)
        return self.fussnoten_setzen(h, quelldatei)

    def fussnoten_setzen(self, h, quelldatei):
        """„[^12]“ -> hochgestellte Taste (kein Link: ein #-Ziel würde die Seite neu aufbauen) und am Ende
        des Blocks die Liste der hier zitierten Nachweise. Die Seite zeigt den Nachweis beim Antippen direkt
        an der Stelle (25.10.2026)."""
        noten = self.fussnoten.get(Path(quelldatei), {})
        benutzt = []
        def ersetze(m):
            n = m.group(1)
            if n not in noten:
                self.fehler.append(texte.satz("pruefung.bauen.6", w1=Path(quelldatei).name, w2=n))
                return m.group(0)
            if n not in benutzt:
                benutzt.append(n)
            return f'<sup class="fn"><button type="button" data-fn="{n}" aria-label="Nachweis {n}">{n}</button></sup>'
        h = FUSSNOTE_REF.sub(ersetze, h)
        if not benutzt:
            return h
        return h + '<ol class="fussnoten">' + "".join(
            f'<li value="{n}" data-fn="{n}">{fussnote_html(noten[n])}</li>' for n in benutzt) + "</ol>"

    def bilder_umschreiben(self, text, quelldatei):
        def ersetze(m):
            ausruf, alt, ziel = m.groups()
            if not ziel.lower().endswith(BILD_ENDUNGEN) or re.match(r"[a-z]+://", ziel):
                return m.group(0)
            quelle = (Path(quelldatei).parent / ziel).resolve()
            if not quelle.exists():
                self.fehler.append(texte.satz("pruefung.bauen.7", w1=Path(quelldatei).name, ziel=ziel))
                return m.group(0)
            try:
                rel = quelle.relative_to(self.reise_dir.resolve())
            except ValueError:
                self.fehler.append(texte.satz("pruefung.bauen.8", w1=Path(quelldatei).name, ziel=ziel))
                return m.group(0)
            self.bilder[quelle] = rel.as_posix()
            return f"{ausruf}[{alt}]({rel.as_posix()})"
        return BILD_LINK.sub(ersetze, text)

    def bloecke(self, sid, body, quelldatei, wo):
        """### -Abschnitte -> (einleitung_html, [Block])"""
        intro, teile = zerlege(body, 3)
        bl = []
        for titel, nr, b in teile:
            bid = f"{sid}.{slug(titel)}"
            self.id_anlegen(bid, f"{wo}:{nr}")
            bl.append({"id": bid, "titel": titel, "html": self.html(b, quelldatei)})
        return self.html(intro, quelldatei) if intro.strip() else "", bl

    # ---------- Bauen ----------
    def etappen_id(self, nummer):
        return "E-" + (nummer.zfill(3) if nummer[-1].isalpha() else nummer.zfill(2))

    def daten(self):
        c = self.cfg
        self.ebenen_pruefen()
        abschnitte, etappen = [], {}
        benutzt = {}
        d_rel, u_rel, p_rel = c.get("etappen_dossier"), c.get("unterkuenfte_dossier"), c.get("plan")

        # Etappen-Dossier und Wissensabschnitte
        text = self.lesen(d_rel)
        _, teile = zerlege(text, 2)
        benutzt[d_rel] = set()
        for titel, nr, body in teile:
            wo = f"{d_rel}:{nr}"
            m = self.etappen_muster.match(titel)
            if m:
                eid = self.etappen_id(m.group(1))
                self.id_anlegen(eid, wo)
                intro, bl = self.bloecke(eid, body, self.reise_dir / d_rel, wo)
                for b in bl:
                    b["ebene"] = self.ebene(b["titel"])
                etappen[eid] = {"id": eid, "typ": "etappe", "nr": m.group(1), "titel": titel,
                                "name": m.group(2), "intro": intro, "bloecke": bl,
                                "kennzahlen": self.kennzahlen(body, wo)}
                abschnitte.append(etappen[eid])
                continue
            if self.ignoriert(d_rel, titel):
                continue
            eintrag = self.finde_abschnitt(d_rel, titel, nr, benutzt[d_rel])
            if not eintrag:
                self.fehler.append(texte.satz("pruefung.bauen.9", wo=wo, titel=titel))
                continue
            abschnitte.append(self.wissen(eintrag, titel, body, d_rel, wo))

        # Unterkünfte-Dossier
        text = self.lesen(u_rel)
        _, teile = zerlege(text, 2)
        benutzt[u_rel] = set()
        for titel, nr, body in teile:
            wo = f"{u_rel}:{nr}"
            m = self.etappen_muster.match(titel)
            if m:
                eid = self.etappen_id(m.group(1))
                if eid not in etappen:
                    self.fehler.append(texte.satz("pruefung.bauen.10", wo=wo, titel=titel))
                    continue
                bid = f"{eid}.unterkuenfte-liste"
                self.id_anlegen(bid, wo)
                titel_u = "Unterkünfte & Einkehr (Unterkünfte-Dossier)"
                etappen[eid]["bloecke"].append(
                    {"id": bid, "titel": titel_u, "ebene": self.ebene(titel_u),
                     "html": self.html(body, self.reise_dir / u_rel)})
                continue
            if self.ignoriert(u_rel, titel):
                continue
            eintrag = self.finde_abschnitt(u_rel, titel, nr, benutzt[u_rel])
            if not eintrag:
                self.fehler.append(texte.satz("pruefung.bauen.11", wo=wo, titel=titel))
                continue
            abschnitte.append(self.wissen(eintrag, titel, body, u_rel, wo))

        # Plan
        text = self.lesen(p_rel)
        vor, teile = zerlege(text, 2)
        vor = "\n".join(z for z in vor.splitlines() if not z.startswith("# "))
        plan_kopf = self.html(vor, self.reise_dir / p_rel) if vor.strip() else ""
        benutzt[p_rel] = set()
        tab_cfg = c.get("tabellen", {})
        tab_benutzt = set()
        for titel, nr, body in teile:
            wo = f"{p_rel}:{nr}"
            if titel in tab_cfg:
                tab_benutzt.add(titel)
                sid, typ, art = tab_cfg[titel]
                abschnitte.append(self.tabellen_abschnitt(sid, typ, art, titel, body, p_rel, wo))
                continue
            if self.ignoriert(p_rel, titel):
                continue
            eintrag = self.finde_abschnitt(p_rel, titel, nr, benutzt[p_rel])
            if not eintrag:
                self.fehler.append(texte.satz("pruefung.bauen.12", wo=wo, titel=titel))
                continue
            abschnitte.append(self.wissen(eintrag, titel, body, p_rel, wo))
        for titel in tab_cfg:
            if titel not in tab_benutzt:
                self.fehler.append(texte.satz("pruefung.bauen.13", titel=titel, p_rel=p_rel))

        # Weitere Dateien, die nur Abschnitte mit IDs enthalten (z. B. Recherche, Planungsstand)
        for rel in c.get("abschnitte", {}):
            if rel in (d_rel, u_rel, p_rel):
                continue
            vor, teile = zerlege(self.lesen(rel), 2)
            benutzt[rel] = set()
            # Text vor dem ersten ## (z. B. Zusammenfassung unter der Hauptüberschrift) geht nicht
            # stillschweigend verloren: in reise.json unter "#" eine ID geben oder in "ignorieren" "#".
            h1 = next((z[2:].strip() for z in vor.splitlines() if z.startswith("# ")), "")
            vor = trenner_entfernen("\n".join(z for z in vor.splitlines() if not z.startswith("# ")))
            if vor.strip() and not self.ignoriert(rel, "#"):
                eintrag = self.cfg["abschnitte"][rel].get("#")
                if eintrag:
                    benutzt[rel].add("#")
                    abschnitte.append(self.wissen(eintrag, h1 or rel, vor, rel, f"{rel}:1"))
                else:
                    self.fehler.append(texte.satz("pruefung.bauen.14", rel=rel))
            for titel, nr, body in teile:
                wo = f"{rel}:{nr}"
                if self.ignoriert(rel, titel):
                    continue
                eintrag = self.finde_abschnitt(rel, titel, nr, benutzt[rel])
                if not eintrag:
                    self.fehler.append(texte.satz("pruefung.bauen.15", wo=wo, titel=titel))
                    continue
                abschnitte.append(self.wissen(eintrag, titel, body, rel, wo))

        # Orte mit Übersicht und Highlights: je Datei Abschnitte „## O-xx Name“ (reise.json -> orte_dossiers).
        # Die O-ID legt routen.yaml an; hier nur Inhalt und Blöcke, geprüft wird nach dem Routenmodell.
        orte_inhalt = {}
        for rel in c.get("orte_dossiers", []):
            _, teile = zerlege(self.lesen(rel), 2)
            for titel, nr, body in teile:
                wo = f"{rel}:{nr}"
                m = re.match(r"^(O-\d+)\s+(.+)$", titel)
                if not m:
                    self.fehler.append(texte.satz("pruefung.bauen.16", wo=wo, titel=titel))
                    continue
                oid, name = m.groups()
                if oid in orte_inhalt:
                    self.fehler.append(texte.satz("pruefung.bauen.17", wo=wo, oid=oid, w1=orte_inhalt[oid]))
                    continue
                orte_inhalt[oid] = wo
                intro, bl = self.bloecke(oid, body, self.reise_dir / rel, wo)
                abschnitte.append({"id": oid, "typ": "ort", "titel": name, "intro": intro, "bloecke": bl})

        fragen = self.fragen(c["fragen"]) if c.get("fragen") else {"spalten": [], "zeilen": []}

        # Rückwärts-Prüfung: Einträge in reise.json ohne Überschrift
        for rel, karte in c.get("abschnitte", {}).items():
            if rel not in benutzt:
                self.fehler.append(texte.satz("pruefung.bauen.18", rel=rel))
                continue
            for titel in karte:
                if titel not in benutzt[rel]:
                    self.fehler.append(texte.satz("pruefung.bauen.19", titel=titel, rel=rel))

        # Routenmodell (Tage, Strecken, Unterkünfte, Wahlstellen)
        route = None
        r_cfg = c.get("routen")
        if r_cfg:
            r_rel = r_cfg["datei"]
            try:
                roh = yaml.safe_load(self.lesen(r_rel)) or {}
            except yaml.YAMLError as e:
                self.fehler.append(texte.satz("pruefung.bauen.20", r_rel=r_rel, e=e))
                roh = {}
            status = {z["id"]: z["status"] for z in fragen["zeilen"]}
            if "entscheider" in roh and self.reise_roh is not None:
                self.fehler.append(texte.satz("pruefung.bauen.21", r_rel=r_rel))
            organisator = [p["name"] for p in self.eck["personen"] if p["rolle"] == "organisator"]
            # Arten und Merkmale der Reise (docs/ontologie.md): plan/arten.yaml neben routen.yaml
            a_rel = str(Path(r_rel).with_name("arten.yaml"))
            try:
                arten = yaml.safe_load(self.lesen(a_rel)) if (self.reise_dir / a_rel).exists() else None
            except yaml.YAMLError as e:
                self.fehler.append(texte.satz("pruefung.bauen.22", a_rel=a_rel, e=e))
                arten = None
            route = Routen(roh, etappen, status, self.fehler, self.id_anlegen, r_rel, arten=arten,
                           entscheider=organisator if self.reise_roh is not None else None,
                           wissen={i for i in self.ids if i.startswith("W-")}, sprache=self.eck["sprache"]).bauen()
            verhalten_anwenden(route, self.eck["verhalten"], self.eck["sprache"])
            for oid, wo in orte_inhalt.items():
                if route and oid not in route["orte"]:
                    self.fehler.append(texte.satz("pruefung.bauen.23", wo=wo, oid=oid))
            if route and r_cfg.get("karte"):
                route["karte"] = self.karte(r_cfg["karte"], route)
                # Punkte der Etappen-Karten (werkzeuge/punkte_holen.py, docs/werkzeuge.md); Namen im Etappentext werden zu Kartenlinks
                p_rel = str(Path(r_cfg["karte"]).parent / "punkte.yaml")
                if (self.reise_dir / p_rel).exists():
                    route["punkte"] = self.punkte(p_rel, route, etappen)
            if route:
                self.lage_ergaenzen(route)
            if route:
                for art in ("tagesplan", "unterkuenfte"):
                    if art not in r_cfg:
                        continue
                    sid, titel = r_cfg[art]
                    a = next((x for x in abschnitte if x["id"] == sid), None)
                    if a is None:
                        self.id_anlegen(sid, f"reise.json routen.{art}")
                        a = {"id": sid, "typ": "plan", "titel": titel, "intro": "", "bloecke": []}
                        abschnitte.insert(0, a)
                    a["route_ansicht"] = art
                aktiv = set(route["aktiv_strecken"])
                for e in etappen.values():
                    e["im_plan"] = e["id"] in aktiv
                    e["optionen"] = [o["id"] for w in route["wahlstellen"] for o in w["optionen"]
                                     if e["id"] in o["alle_strecken"] and not o["aktiv"]]
                    e["nebenroute"] = not e["im_plan"] and not e["optionen"]
                self.lesetext_pruefen(etappen, route)

        # Claudes Vorschläge zu Wünschen (Wunsch-Brett, Paket G): plan/wuensche.yaml neben routen.yaml
        wunsch_vorschlaege = {}
        if route and (self.reise_dir / Path(r_cfg["datei"]).parent / "wuensche.yaml").exists():
            wunsch_vorschlaege = self.wunsch_vorschlaege(str(Path(r_cfg["datei"]).parent / "wuensche.yaml"), route)

        # Orte und Wissen in beide Richtungen verknüpfen (reise.json orte_wissen -> YAML; 25.10.2026)
        if c.get("orte_wissen"):
            self.orte_wissen(c["orte_wissen"], abschnitte)

        # Karten in der Recherche: Orte je Block auf regionalen Offline-Karten (reise.json wissen_punkte; Issue #64)
        wissen_karte = self.wissen_karte(c["wissen_punkte"], abschnitte) if c.get("wissen_punkte") else None

        kategorien = self.kategorien_laden()   # auch ohne Punkte prüfen, damit ein Fehler in der Datei nicht schlummert
        if self.fehler:
            raise BauFehler(list(dict.fromkeys(self.fehler)))
        return {
            # Eckdaten, Darstellung, Status, Personen, Bausteine, Regeln aus reise.yaml (engine/reise.py)
            "reise": self.eck,
            "inhaltswoerter": texte.seite_inhaltswoerter(),   # Wörter, an denen die Seite Inhalt erkennt (Fragestatus, Tag n, …), alle Sprachen
            "plan_kopf": plan_kopf,
            "abschnitte": abschnitte,
            "fragen": fragen,
            "route": route,
            "wissen_karte": wissen_karte,
            "kategorien": kategorien,
            "wunsch_vorschlaege": wunsch_vorschlaege,
        }

    def wunsch_vorschlaege(self, rel, route):
        """Claudes Vorschläge zu Wünschen (Paket G): je Wunsch (R-…) die Stellen, an die er passt (bezug), eine kurze
        Notiz mit Herkunft und, wenn daraus eine Option wurde, deren ID. Der Wunschtext steht nicht hier, sondern in der
        Rückmelde-Ablage. Eingeplant ist ein Wunsch erst, wenn ein:e Organisator:in diese Option wählt (gewaehlt) oder ihn auf dem
        Brett bestätigt; Claude kann ihn nicht einplanen."""
        try:
            roh = yaml.safe_load(self.lesen(rel)) or {}
        except yaml.YAMLError as e:
            self.fehler.append(texte.satz("pruefung.bauen.24", rel=rel, e=e))
            return {}
        if not isinstance(roh, dict):
            self.fehler.append(texte.satz("pruefung.bauen.25", rel=rel))
            return {}
        optionen = {o["id"]: o for w in route.get("wahlstellen") or [] for o in w["optionen"]}
        bekannt = set(self.ids) | set(route.get("unterkuenfte") or {}) | set(route.get("orte") or {}) | set(optionen)
        aus = {}
        for rid, v in roh.items():
            wo = f"{rel}: {rid}"
            if not re.match(r"^R-\d{8}-\d{6}-[0-9a-f]{4}$", str(rid)):
                self.fehler.append(texte.satz("pruefung.bauen.26", wo=wo))
                continue
            if not isinstance(v, dict) or set(v) - {"bezug", "notiz", "option"}:
                self.fehler.append(texte.satz("pruefung.bauen.27", wo=wo))
                continue
            bezug = v.get("bezug") or []
            if isinstance(bezug, str):
                bezug = [bezug]
            if not isinstance(bezug, list) or not all(isinstance(x, str) for x in bezug):
                self.fehler.append(texte.satz("pruefung.bauen.28", wo=wo))
                continue
            for x in bezug:
                if x not in bekannt:
                    self.fehler.append(texte.satz("pruefung.bauen.29", wo=wo, x=x))
            notiz = v.get("notiz") or ""
            if not isinstance(notiz, str):
                self.fehler.append(texte.satz("pruefung.bauen.30", wo=wo))
                notiz = ""
            option = v.get("option")
            if option is not None and option not in optionen:
                self.fehler.append(texte.satz("pruefung.bauen.31", wo=wo, option=option))
                option = None
            aus[rid] = {"bezug": bezug, "notiz": notiz.strip(), "option": option,
                        "gewaehlt": bool(option) and optionen[option]["status"] == "gewaehlt"}
        return aus

    def kategorien_laden(self):
        """plan/kategorien.yaml der Reise -> {Schlüssel: Definition}; fehlt die Datei, ist es leer. Wer Punkte hat,
        braucht Kategorien (kategorie_pruefen meldet es je Punkt)."""
        if self._kategorien is not None:
            return self._kategorien
        rel = "plan/kategorien.yaml"
        self._kategorien = {}
        if not (self.reise_dir / rel).exists():
            return self._kategorien
        try:
            roh = yaml.safe_load(self.lesen(rel)) or {}
        except yaml.YAMLError as e:
            self.fehler.append(texte.satz("pruefung.bauen.32", rel=rel, e=e))
            return self._kategorien
        roh = roh.get("kategorien") if isinstance(roh, dict) else None
        if not isinstance(roh, dict):
            self.fehler.append(texte.satz("pruefung.bauen.33", rel=rel))
            return self._kategorien
        for k, d in roh.items():
            wo = f"{rel} {k}"
            if not re.fullmatch(KATEGORIE_MUSTER, str(k)):
                self.fehler.append(texte.satz("pruefung.bauen.34", wo=wo))
                continue
            if not isinstance(d, dict) or d.get("gruppe") not in KATEGORIE_GRUPPEN:
                self.fehler.append(texte.satz("pruefung.bauen.35", wo=wo, w1=' oder '.join(KATEGORIE_GRUPPEN)))
                continue
            if set(d) - KATEGORIE_FELDER:
                self.fehler.append(texte.satz("pruefung.bauen.36", wo=wo, w1=', '.join(sorted(set(d) - KATEGORIE_FELDER))))
            if not d.get("name"):
                self.fehler.append(texte.satz("pruefung.bauen.37", wo=wo))
            f = d.get("farbe")
            if f not in KATEGORIE_FARBEN and not (isinstance(f, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", f)):
                self.fehler.append(texte.satz("pruefung.bauen.38", wo=wo, w1=', '.join(KATEGORIE_FARBEN)))
            if d.get("symbol") and d["symbol"] not in SYMBOLE:
                self.fehler.append(texte.satz("pruefung.bauen.39", wo=wo, w1=', '.join(SYMBOLE)))
            arten = d.get("arten") or {}
            if not isinstance(arten, dict):
                self.fehler.append(texte.satz("pruefung.bauen.40", wo=wo))
                arten = {}
            for a, ad in arten.items():
                ad = ad if isinstance(ad, dict) else {"name": ad}
                if set(ad) - KATEGORIE_ART_FELDER:
                    self.fehler.append(texte.satz("pruefung.bauen.41", wo=wo, a=a, w1=', '.join(sorted(set(ad) - KATEGORIE_ART_FELDER))))
                if ad.get("symbol") and ad["symbol"] not in SYMBOLE:
                    self.fehler.append(texte.satz("pruefung.bauen.42", wo=wo, a=a, w1=', '.join(SYMBOLE)))
                arten[a] = ad
            self._kategorien[k] = {"gruppe": d["gruppe"], "name": str(d.get("name") or k), "einzahl": d.get("einzahl"), "farbe": f,
                                   "symbol": d.get("symbol"), "nummeriert": bool(d.get("nummeriert")), "arten": arten}
        return self._kategorien

    def kategorie_pruefen(self, wo, p, gruppe):
        """Die kat eines Kartenpunkts muss in plan/kategorien.yaml stehen, in der Gruppe der Karte."""
        k = self.kategorien_laden()
        gueltig = [n for n, d in k.items() if d["gruppe"] == gruppe]
        if p.get("kat") in gueltig:
            return
        if not gueltig:
            self.fehler.append(texte.satz("pruefung.bauen.43", wo=wo, w1=p.get('kat'), gruppe=gruppe))
        else:
            self.fehler.append(texte.satz("pruefung.bauen.44", wo=wo, w1=', '.join(gueltig)))

    def wissen_karte(self, rel, abschnitte):
        """Punkte je Wissens-Block (W-….<slug>) mit regionalen Grundkarten. Erzeugt vom Betrieb (Punkte aus OpenStreetMap),
        von Hand geprüft. Punkte ohne Lage (nicht gefunden) oder außerhalb jeder Grundkarte kommen nicht auf die
        Karte und werden gemeldet; Namen der gezeigten Punkte werden im Blocktext zu Kartenlinks."""
        try:
            roh = yaml.safe_load(self.lesen(rel)) or {}
        except yaml.YAMLError as e:
            self.fehler.append(texte.satz("pruefung.bauen.45", rel=rel, e=e))
            return None
        stand = roh.get("stand")
        if stand is not None and als_datum(stand) is None:
            self.fehler.append(texte.satz("pruefung.bauen.46", rel=rel))
            stand = None
        karten, fehlen = {}, []
        for name, g in (roh.get("grundkarten") or {}).items():
            r = (g or {}).get("rahmen") or {}
            if not all(isinstance(r.get(x), (int, float)) for x in ("nord", "sued", "west", "ost")):
                self.fehler.append(texte.satz("pruefung.bauen.47", rel=rel, name=name))
                continue
            datei = self.reise_dir / "medien" / "karte" / f"{name}.pmtiles"
            if not datei.exists():
                fehlen.append(name)
                continue
            self.grundkarten[f"karte-{name}.pmtiles"] = datei
            karten[name] = {"url": f"karte-{name}.pmtiles", "titel": g.get("titel", name), "rahmen": r,
                            "maxzoom": pmtiles_maxzoom(datei)}
        if fehlen:
            self.hinweise.append(texte.satz("pruefung.bauen.48", w1=', '.join(fehlen)))
        bloecke = {b["id"]: b for a in abschnitte if a["typ"] != "ort" for b in a["bloecke"]}
        aus, ohne = {}, []
        for bid, liste in (roh.get("bloecke") or {}).items():
            if bid not in bloecke:
                self.fehler.append(texte.satz("pruefung.bauen.49", rel=rel, bid=bid))
                continue
            zeigen = []
            for i, p in enumerate(liste or []):
                wo = f"{rel}: {bid} Punkt {i + 1}"
                self.kategorie_pruefen(wo, p, "wissen")
                if not p.get("name"):
                    self.fehler.append(texte.satz("pruefung.bauen.50", wo=wo))
                lage = p.get("lage")
                if p.get("ohne_karte"):  # bewusst ohne Punkt, Grund steht in der Datei
                    continue
                if lage is None:
                    ohne.append(texte.satz("pruefung.bauen.ort_ohne_karte", name=p.get("name"), bid=bid.split(".")[0]))
                    continue
                if not (isinstance(lage, list) and len(lage) == 2 and all(isinstance(x, (int, float)) for x in lage)):
                    self.fehler.append(texte.satz("pruefung.bauen.51", wo=wo))
                    continue
                if not p.get("quelle"):
                    self.fehler.append(texte.satz("pruefung.bauen.52", wo=wo))
                k = next((n for n, g in karten.items() if g["rahmen"]["sued"] <= lage[0] <= g["rahmen"]["nord"]
                          and g["rahmen"]["west"] <= lage[1] <= g["rahmen"]["ost"]), None)
                if k is None:
                    if karten:
                        ohne.append(texte.satz("pruefung.bauen.ort_ausserhalb", name=p.get("name"), bid=bid.split(".")[0]))
                    continue
                g = punkt_geprueft(p, stand, wo, self.fehler)
                zeigen.append({x: p[x] for x in ("name", "auch", "kat", "lage", "quelle", "hinweis") if p.get(x)} | {"karte": k}
                              | ({"geprueft": g} if g else {}))
            if zeigen:
                aus[bid] = zeigen
                bloecke[bid]["html"] = punkte_verlinken(bloecke[bid]["html"], bid, zeigen)
        if ohne:
            self.hinweise.append(texte.satz("pruefung.bauen.53", rel=rel, w1=len(ohne), w2=texte.Satz.verbinden(ohne)))
        if not aus:
            return None
        return {"grundkarten": karten, "punkte": aus,
                "namensnennung": roh.get("namensnennung", "© OpenStreetMap-Mitwirkende · Protomaps")}

    def lage_ergaenzen(self, route):
        """Lage der Unterkünfte (ADR-0004): fehlt der Punkt, kommt er aus plan/punkte.yaml (Eintrag mit id: U-…, mit dessen
        Quelle). Ab Status fest mahnt der Bau Unterkünfte im Plan ohne Lage (weder Adresse noch Punkt)."""
        for liste in (route.get("punkte") or {}).values():
            for p in liste:
                u = route["unterkuenfte"].get(p.get("id"))
                if u is not None and not u.get("punkt") and isinstance(p.get("lage"), list):
                    u["punkt"] = {"wert": p["lage"], "quelle": p.get("quelle"), "notiz": None, "geprueft": p.get("geprueft")}
        if not self.eck["verhalten"].get("mahnung_planung"):
            return
        im_plan = []
        for t in route.get("tage") or []:
            n = t.get("nacht") or {}
            if n.get("unterkunft"):
                im_plan.append(n["unterkunft"])
            elif n.get("wahl"):
                w = next((x for x in route["wahlstellen"] if x["id"] == n["wahl"]), None)
                akt = w and next((o for o in w["optionen"] if o["aktiv"]), None)
                im_plan += (akt or {}).get("unterkuenfte") or []
        for uid in dict.fromkeys(im_plan):
            u = route["unterkuenfte"].get(uid)
            if u and not u.get("adresse") and not u.get("punkt"):
                route.setdefault("mahnungen", []).append({"bezug": uid, "text": texte.t(self.eck["sprache"], "pruefung.bauen.lage_fehlt", uid=uid, name=u.get("name"))})

    def punkte(self, rel, route, etappen):
        """plan/punkte.yaml prüfen und die Namen im Etappentext mit der Karte verknüpfen."""
        try:
            roh = yaml.safe_load(self.lesen(rel)) or {}
        except yaml.YAMLError as e:
            self.fehler.append(texte.satz("pruefung.bauen.54", rel=rel, e=e))
            return {}
        aus = {}
        stand = roh.get("stand")
        if stand is not None and als_datum(stand) is None:
            self.fehler.append(texte.satz("pruefung.bauen.55", rel=rel))
            stand = None
        for sid, liste in (roh.get("strecken") or {}).items():
            if sid not in route["strecken"] and sid not in etappen:
                self.fehler.append(texte.satz("pruefung.bauen.56", rel=rel, sid=sid))
                continue
            for i, p in enumerate(liste or []):
                wo = f"{rel}: {sid} Punkt {i + 1}"
                lage = p.get("lage")
                self.kategorie_pruefen(wo, p, "punkt")
                if not (isinstance(lage, list) and len(lage) == 2 and all(isinstance(x, (int, float)) for x in lage)):
                    self.fehler.append(texte.satz("pruefung.bauen.57", wo=wo))
                if not p.get("quelle"):
                    self.fehler.append(texte.satz("pruefung.bauen.58", wo=wo))
                if p.get("id") and p["id"] not in self.ids and p["id"] not in route.get("unterkuenfte", {}):
                    self.fehler.append(texte.satz("pruefung.bauen.59", wo=wo, w1=p['id']))
                p["geprueft"] = punkt_geprueft(p, stand, wo, self.fehler)
                if p["geprueft"] is None:
                    del p["geprueft"]
            aus[sid] = liste or []
            if sid in etappen:
                e = etappen[sid]
                e["intro"] = punkte_verlinken(e["intro"], sid, aus[sid])
                for b in e["bloecke"]:
                    b["html"] = punkte_verlinken(b["html"], sid, aus[sid])
        return aus

    def karte(self, rel, route):
        """Schematische Karte (Küste, Orte, Wege) aus plan/karte.yaml; prüft Verweise auf Orte und Strecken."""
        try:
            k = yaml.safe_load(self.lesen(rel)) or {}
        except yaml.YAMLError as e:
            self.fehler.append(texte.satz("pruefung.bauen.60", rel=rel, e=e))
            return None
        def punkt(p, wo):
            ok = isinstance(p, list) and len(p) == 2 and all(isinstance(x, (int, float)) for x in p)
            if not ok:
                self.fehler.append(texte.satz("pruefung.bauen.61", rel=rel, wo=wo))
        for oid, o in (k.get("orte") or {}).items():
            if oid not in route["orte"]:
                self.fehler.append(texte.satz("pruefung.bauen.62", rel=rel, oid=oid))
            punkt(o.get("lage"), oid)
        for art in ("wege", "unmarkiert"):
            for sid, weg in (k.get(art) or {}).items():
                if sid not in route["strecken"] and sid not in self.ids:
                    self.fehler.append(texte.satz("pruefung.bauen.63", rel=rel, art=art, sid=sid))
                for p in weg:
                    punkt(p, sid)
        for sid in k.get("ausgelassen") or []:
            if sid not in self.ids:
                self.fehler.append(texte.satz("pruefung.bauen.64", rel=rel, sid=sid))
        if k.get("linien") not in (None, "alle"):
            self.fehler.append(texte.satz("pruefung.bauen.65", rel=rel))
        r = k.get("rahmen") or {}
        if not all(isinstance(r.get(x), (int, float)) for x in ("nord", "sued", "west", "ost")):
            self.fehler.append(texte.satz("pruefung.bauen.66", rel=rel))
        # GPX-Tracks ersetzen die schematischen Wege (25.10.2026)
        for sid in k.get("gpx") or {}:
            if sid not in route["strecken"] and sid not in self.ids:
                self.fehler.append(texte.satz("pruefung.bauen.67", rel=rel, sid=sid))
        if k.get("gpx"):
            self.fehler += [f"{rel}: {m}" for m in gpx.einbauen(k, route["strecken"], lambda d: gpx.lesen(self.reise_dir / d))]
        # Offline-Grundkarte (OpenStreetMap als PMTiles, werkzeuge/karte-holen.sh); fehlt sie, bleibt die Karte schematisch
        g = k.pop("grundkarte", None)
        if g:
            datei = self.reise_dir / g["datei"]
            if datei.exists():
                self.grundkarte = datei
                k["grundkarte"] = {"url": "grundkarte.pmtiles"}
                k["namensnennung"] = " · ".join(x for x in (k.get("namensnennung"), g.get("namensnennung")) if x)
            else:
                k["namensnennung"] = " · ".join(x for x in (k.get("namensnennung"), texte.t(self.eck["sprache"], "seite.karte.kueste")) if x)
                self.hinweise.append(texte.satz("pruefung.bauen.68", w1=g['datei']))
        return k

    def orte_wissen(self, rel, abschnitte):
        """Je Ort die passenden Abschnitte der Recherche: Ort bekommt „wissen“ (Links mit Notiz),
        der Abschnitt oder Block bekommt „orte“. Ziel ist eine Abschnitts- oder Block-ID."""
        try:
            roh = yaml.safe_load(self.lesen(rel)) or {}
        except yaml.YAMLError as e:
            self.fehler.append(texte.satz("pruefung.bauen.69", rel=rel, e=e))
            return
        orte = {a["id"]: a for a in abschnitte if a["typ"] == "ort"}
        ziele = {}
        for a in abschnitte:
            if a["typ"] != "ort":
                ziele[a["id"]] = (a, a)
                ziele.update({b["id"]: (b, a) for b in a["bloecke"]})
        for oid, liste in roh.items():
            if oid not in orte:
                self.fehler.append(texte.satz("pruefung.bauen.70", rel=rel, oid=oid))
                continue
            for e in liste or []:
                e = {"ziel": e} if isinstance(e, str) else e
                if e.get("ziel") not in ziele:
                    self.fehler.append(texte.satz("pruefung.bauen.71", rel=rel, oid=oid, w1=e.get('ziel')))
                    continue
                x, a = ziele[e["ziel"]]
                orte[oid].setdefault("wissen", []).append(
                    {"id": e["ziel"], "titel": x["titel"], "in": a["titel"] if x is not a else "", "notiz": e.get("notiz", "")})
                if oid not in x.setdefault("orte", []):
                    x["orte"].append(oid)

    def wissen(self, eintrag, titel, body, rel, wo):
        sid, typ = eintrag
        self.id_anlegen(sid, wo)
        intro, bl = self.bloecke(sid, body, self.reise_dir / rel, wo)
        return {"id": sid, "typ": typ, "titel": titel, "intro": intro, "bloecke": bl}

    def lesetext_pruefen(self, etappen, route):
        """Stichworte im Lesetext (Ebene „Der Weg“) gegen die Gliederung der Art der Strecke (arten.yaml lesetext,
        docs/ontologie.md). Ein Absatz, der mit einem fetten Stichwort beginnt, gehört zu einer Rubrik; ein unbekanntes
        Stichwort ist ein Hinweis, kein Fehler. Ohne Gliederung der Art wird nichts geprüft."""
        for eid, e in etappen.items():
            s = (route.get("strecken") or {}).get(eid) or {}
            art = s.get("art_schluessel")
            rubriken = ((route.get("arten") or {}).get(art) or {}).get("lesetext")
            if not rubriken:
                continue
            namen = {r["name"].casefold() for r in rubriken}
            for b in e["bloecke"]:
                if b.get("ebene") != "weg":
                    continue
                for wort in STICHWORT.findall(b["html"]):
                    if wort.strip().rstrip(".:").strip().casefold() not in namen:
                        self.hinweise.append(texte.satz("pruefung.bauen.72", eid=eid, w1=wort.strip().rstrip('.:'), art=art, w2=', '.join(r['name'] for r in rubriken)))

    def ebene(self, titel):
        """Ebene eines Etappen-Abschnitts auf der Tagesseite: zuerst die Titelanfänge der Reise, dann die Vorgabe."""
        t = titel.strip().lower()
        for quelle in (self.cfg.get("etappen_ebenen") or {}, ebenen_vorgabe()):
            for ebene, anfaenge in quelle.items():
                if any(t.startswith(a.lower()) for a in anfaenge):
                    return ebene
        return "hintergrund"

    def ebenen_pruefen(self):
        e = self.cfg.get("etappen_ebenen")
        if e is None:
            return
        if not isinstance(e, dict) or any(not isinstance(v, list) or not all(isinstance(x, str) and x.strip() for x in v)
                                          for v in e.values()):
            self.fehler.append(texte.satz("pruefung.bauen.73"))
            return
        for k in e:
            if k not in EBENEN:
                self.fehler.append(texte.satz("pruefung.bauen.74", k=k, w1=', '.join(EBENEN)))

    def kennzahlen(self, body, wo):
        gewuenscht = self.cfg.get("etappen_kennzahlen", [])
        block = next((b for b in zerlege(body, 3)[1] if slug(b[0]) == "eckdaten"), None)
        if not block or not gewuenscht:
            return {}
        t = tabelle_lesen(block[2], wo, [])
        if not t:
            return {}
        werte = {z[0]: z[1] for z in t[2] if len(z) >= 2}
        return {k: werte[k] for k in gewuenscht if k in werte}

    def tabellen_abschnitt(self, sid, typ, art, titel, body, rel, wo):
        self.id_anlegen(sid, wo)
        t = tabelle_lesen(body, wo, self.fehler)
        if not t:
            self.fehler.append(texte.satz("pruefung.bauen.75", wo=wo, titel=titel))
            return {"id": sid, "typ": typ, "titel": titel, "intro": "", "bloecke": []}
        davor, kopf, rows, danach = t
        quelle = self.reise_dir / rel
        zeilen = []
        for i, werte in enumerate(rows, 1):
            if art == "tage":
                ziffern = re.sub(r"\D", "", werte[0])
                if not ziffern:
                    self.fehler.append(texte.satz("pruefung.bauen.76", wo=wo, w1=werte[0]))
                    continue
                zid = "T-" + ziffern.zfill(2)
            else:
                zid = "U-" + str(i).zfill(2)
            self.id_anlegen(zid, wo)
            zeilen.append({"id": zid, "zellen": werte})
        return {"id": sid, "typ": typ, "titel": titel,
                "intro": self.html(davor, quelle) if davor.strip() else "",
                "nach": self.html(danach, quelle) if danach.strip() else "",
                "tabelle": {"art": art, "spalten": kopf, "zeilen": zeilen}, "bloecke": []}

    def fragen(self, rel):
        t = tabelle_lesen(self.lesen(rel), rel, self.fehler)
        if not t:
            self.fehler.append(texte.satz("pruefung.bauen.77", rel=rel))
            return {"spalten": [], "zeilen": []}
        _, kopf, rows, _ = t
        zeilen = []
        for werte in rows:
            if not re.match(r"^F-\d+$", werte[0]):
                self.fehler.append(texte.satz("pruefung.bauen.78", rel=rel, w1=werte[0]))
                continue
            self.id_anlegen(werte[0], rel)
            sp = next((i for i, k in enumerate(kopf) if k.lower() == "status"), None)
            zeilen.append({"id": werte[0], "zellen": werte, "status": werte[sp] if sp is not None else ""})
        return {"spalten": kopf, "zeilen": zeilen}

    # ---------- Ausgabe ----------
    def bilder_schreiben(self):
        maxbreite = int(self.cfg.get("bilder_max_breite", 1600))
        for quelle, rel in self.bilder.items():
            ziel = self.ziel_dir / rel
            ziel.parent.mkdir(parents=True, exist_ok=True)
            if ziel.exists() and ziel.stat().st_mtime >= quelle.stat().st_mtime:
                continue
            with Image.open(quelle) as im:
                im = ImageOps.exif_transpose(im)
                if im.width > maxbreite:
                    im = im.resize((maxbreite, round(im.height * maxbreite / im.width)), Image.LANCZOS)
                if ziel.suffix.lower() in (".jpg", ".jpeg"):
                    im.convert("RGB").save(ziel, "JPEG", quality=80, optimize=True)
                else:
                    im.save(ziel)

    def schreiben(self, daten):
        daten = warnungen_in_reisesprache(daten)
        vorlage = (Path(__file__).parent / "vorlage.html").read_text(encoding="utf-8")
        vorlage = vorlage.replace("<!--__SYMBOLE__-->", symbole(), 1)
        vorlage = vorlage.replace('data-release="__RELEASE__"', f'data-release="{release_attribut()}"', 1)
        if self.umzug:   # Seite ist umgezogen: gleicher Pfad auf der neuen Adresse (alte Browser-Speicher räumt sw.js auf)
            vorlage = vorlage.replace("<head>", "<head>\n<script>if (location.origin !== " + json.dumps(self.umzug) + ") location.replace(" +
                                      json.dumps(self.umzug) + " + location.pathname + location.search + location.hash)</script>", 1)
        vorlage = vorlage.replace("<!--__GRUNDKARTE__-->", "".join(
            f'<script src="{n}"></script>' for n in VENDOR_GRUNDKARTE.values()) if self.grundkarte or self.grundkarten else "", 1)
        if vorlage.count("/*__DATEN__*/null") != 1 or vorlage.count("/*__TEXTE__*/null") != 1:
            raise BauFehler(["vorlage.html muss die Platzhalter /*__DATEN__*/null und /*__TEXTE__*/null genau einmal enthalten."])
        vorlage = re.sub(r'<html lang="[^"]*">', lambda _: f'<html lang="{daten["reise"]["sprache"]}" dir="{texte.sprache(daten["reise"]["sprache"]).RICHTUNG}">', vorlage, count=1)
        katalog = json.dumps(texte_fuer_seite(), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        vorlage = vorlage.replace("/*__TEXTE__*/null", katalog, 1)
        js = json.dumps(daten, ensure_ascii=False, separators=(",", ":"))
        js = js.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
        self.ziel_dir.mkdir(parents=True, exist_ok=True)
        (self.ziel_dir / "index.html").write_text(vorlage.replace("/*__DATEN__*/null", js), encoding="utf-8")
        (self.ziel_dir / "daten.json").write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
        self.bilder_schreiben()
        self.pwa_schreiben()

    def pwa_schreiben(self):
        """Manifest, Icons und Service Worker. Die Version ist der Hash aller vorab gespeicherten
        Dateien: gleicher Inhalt -> gleiche sw.js -> kein Update-Hinweis auf dem Telefon."""
        c, ziel = self.eck, self.ziel_dir
        kurz = c.get("kurz") or c["titel"].split(" – ")[0]
        motiv = self.reise_dir / "medien" / "icon.svg"  # eigenes App-Symbol der Reise, sonst Kurzname
        (ziel / "manifest.json").write_text(json.dumps({
            "name": c["titel"], "short_name": kurz, "lang": c["sprache"], "dir": texte.sprache(c["sprache"]).RICHTUNG,
            "start_url": "./", "scope": "./", "display": "standalone",
            "background_color": PWA_HINTERGRUND, "theme_color": PWA_FARBE,
            # eigenes Motiv ist für Android-Masken gezeichnet (Motiv im inneren 80 %)
            "icons": [{"src": f"icon-{g}.png", "sizes": f"{g}x{g}", "type": "image/png",
                       "purpose": "any maskable" if motiv.exists() else "any"} for g in (192, 512)],
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        # Fremdbibliotheken aus engine/vendor (lokal statt CDN: offline und keine Anfragen vom geheimen Pfad)
        mit_karte = bool(self.grundkarte or self.grundkarten)
        vendor = {**VENDOR, **(VENDOR_GRUNDKARTE if mit_karte else {})}
        for quelle, name in vendor.items():
            shutil.copyfile(Path(__file__).parent / "vendor" / quelle, ziel / name)
        for name in VENDOR_GRUNDKARTE.values():
            if not mit_karte and (ziel / name).exists():
                (ziel / name).unlink()
        for g in ICON_GROESSEN:
            (icon_aus_svg(motiv, g) if motiv.exists() else icon_zeichnen(kurz, g)).save(ziel / f"icon-{g}.png", optimize=True)
        # Bilder, die keine Quelle mehr haben, nicht ausliefern und nicht vorab laden
        # Offline-Grundkarte: wird wie die Bilder bei der Installation vorab gespeichert
        karte = ziel / "grundkarte.pmtiles"
        if self.grundkarte:
            if not karte.exists() or karte.stat().st_size != self.grundkarte.stat().st_size \
                    or karte.stat().st_mtime < self.grundkarte.stat().st_mtime:
                shutil.copyfile(self.grundkarte, karte)
        elif karte.exists():
            karte.unlink()
        # Regionale Grundkarten der Recherche-Karten (karte-<name>.pmtiles), ebenso vorab gespeichert
        for name, quelle in self.grundkarten.items():
            k = ziel / name
            if not k.exists() or k.stat().st_size != quelle.stat().st_size or k.stat().st_mtime < quelle.stat().st_mtime:
                shutil.copyfile(quelle, k)
        for k in ziel.glob("karte-*.pmtiles"):
            if k.name not in self.grundkarten:
                k.unlink()
        gewollt = {ziel / rel for rel in self.bilder.values()}
        if (ziel / "medien").exists():
            for f in (ziel / "medien").rglob("*"):
                if f.is_file() and f not in gewollt:
                    f.unlink()
        dateien = ["", "index.html", "manifest.json", *vendor.values(), *(f"icon-{g}.png" for g in ICON_GROESSEN),
                   *sorted(set(self.bilder.values())), *(["grundkarte.pmtiles"] if self.grundkarte else []), *sorted(self.grundkarten)]
        # Je Datei ein Inhalts-Hash: Eine neue Version übernimmt unveränderte Dateien (vor allem die großen
        # Grundkarten) aus dem bisherigen Speicher, statt sie neu zu laden (Issue #64).
        stand = {f: datei_hash(ziel / f) for f in dateien[1:]}
        stand[""] = stand["index.html"]
        h = hashlib.sha256()
        for f in dateien[1:]:
            h.update(f.encode() + b"\0" + stand[f].encode())
        sw = (Path(__file__).parent / "sw.vorlage.js").read_text(encoding="utf-8")
        sw = sw.replace("__VERSION__", h.hexdigest()[:12]).replace("__DATEIEN__", json.dumps(dateien, ensure_ascii=False)) \
               .replace("__STAND__", json.dumps(stand, ensure_ascii=False)) \
               .replace("__UMZUG__", json.dumps(self.umzug))
        (ziel / "sw.js").write_text(sw, encoding="utf-8")


VENDOR = {"pico-2.1.1.conditional.jade.min.css": "pico-2.1.1.min.css",   # Pico CSS (MIT), Issue #25
          "leaflet-1.9.4.js": "leaflet-1.9.4.js", "leaflet-1.9.4.css": "leaflet-1.9.4.css",   # Leaflet (BSD-2), Issue #27
          # Schrift Source Sans 3 (OFL, @fontsource-variable 5.3.1) für Titel und Text, Gesicht „Freundlich“ (#52)
          **{f"fonts/source-sans-3-{z}-wght-normal.woff2": f"source-sans-3-{z}-wght-normal.woff2" for z in ("latin", "latin-ext")}}
# Offline-Grundkarte: protomaps-leaflet zeichnet die PMTiles-Vektorkarte in Leaflet (BSD-3), nur wenn eine Grundkarte da ist
VENDOR_GRUNDKARTE = {"protomaps-leaflet-5.1.0.js": "protomaps-leaflet-5.1.0.js"}
# Symbole: Lucide (ISC, lucide.dev), lokal in engine/vendor; beim Bauen als <symbol> in die Seite (Issue #25)
LUCIDE = "lucide-1.55.0"
# Kategorien der Kartenpunkte (docs/ontologie.md „Kartenpunkte“, ADR-0001, Issue O-7): Welche es gibt, sagt allein die Reise in
def software_release(ordner=Path(__file__).resolve().parent):
    """Release der Software, aus der die Seite gebaut wird: {nummer, kennung, commit, github}.
    nummer ist die Zahl der Commits bis zu diesem Stand. main wächst nur (vorspulen, CLAUDE.md), deshalb steigt sie mit
    jedem Stand, ist eindeutig und für main dieselbe Zahl, die GitHub auf der Startseite des Repos bei „Commits“ zeigt.
    kennung ist der kurze Commit-Hash (eindeutig auch außerhalb von main), commit der volle. github ist „besitzer/repo“
    aus der Adresse von origin, wenn die Software auf GitHub liegt (für Link und Vergleich im Fuß der Seite).
    In einem flachen Klon ist die Zahl falsch und fehlt deshalb; ohne Git fehlt alles."""
    def git(*args):
        try:
            r = subprocess.run(["git", "-C", str(ordner), *args], capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return None
        return r.stdout.strip() if r.returncode == 0 else None
    commit = git("rev-parse", "HEAD")
    if not commit:
        return {"nummer": None, "kennung": None, "commit": None, "github": None}
    nummer = git("rev-list", "--count", "HEAD") if git("rev-parse", "--is-shallow-repository") == "false" else None
    m = re.search(r"github\.com[:/]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$", git("config", "--get", "remote.origin.url") or "")
    return {"nummer": int(nummer) if nummer and nummer.isdigit() else None, "kennung": commit[:7], "commit": commit,
            "github": f"{m.group(1)}/{m.group(2)}" if m else None}


def release_attribut():
    """Wert für data-release im Fuß jeder Seite: das Release als JSON (Nummer, Kennung, Commit, GitHub). Die Seite schreibt
    daraus „Frieda Release 412 · 9b4a397“ in ihrer Sprache und vergleicht auf Tippen mit main; leer, wenn unbekannt."""
    r = software_release()
    return htmlmod.escape(json.dumps(r if r["kennung"] else {}, separators=(",", ":")), quote=True)


# plan/kategorien.yaml. Die Software prüft nur die Form: Gruppe, Name, Farbe (Palette der Seite oder #rrggbb), Symbol (aus SYMBOLE).
KATEGORIE_GRUPPEN = ("punkt", "wissen")       # punkt: Etappen-Karte (plan/punkte.yaml), wissen: Karte im Wissensabschnitt
KATEGORIE_FELDER = {"gruppe", "name", "einzahl", "farbe", "symbol", "nummeriert", "arten"}
KATEGORIE_ART_FELDER = {"name", "symbol", "hinweis", "umriss"}
KATEGORIE_FARBEN = FARBEN + ("kontrast",)   # kontrast: Schrift- auf Hintergrundfarbe der Seite (hell wie dunkel lesbar)
KATEGORIE_MUSTER = r"[a-z][a-z0-9_]*"


def datei_hash(pfad):
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        for stueck in iter(lambda: f.read(1 << 20), b""):
            h.update(stueck)
    return h.hexdigest()[:16]


def pmtiles_maxzoom(datei):
    """Höchste Zoomstufe aus dem Kopf einer PMTiles-Datei (Version 3, Byte 101); darüber vergrößert die Karte."""
    with open(datei, "rb") as f:
        kopf = f.read(127)
    return kopf[101] if kopf[:7] == b"PMTiles" and len(kopf) == 127 else 14


def punkte_verlinken(html, sid, punkte):
    """Erste Nennung je Block eines Punktnamens wird zum Kartenlink <a class="kp" data-p="E-04:5">.
    Längere Namen zuerst, nur ganze Wörter, nie innerhalb eines Links oder Tags."""
    namen = sorted({(n, i) for i, p in enumerate(punkte) for n in [p.get("name"), *(p.get("auch") or [])]
                    if n and len(n) >= 4}, key=lambda x: (-len(x[0]), x[0], x[1]))  # fest: gleiche Version bei gleichem Inhalt
    if not namen or not html:
        return html
    muster = [(re.compile(rf"(?<!\w){re.escape(n)}(?!\w)", re.I), i) for n, i in namen]
    teile, in_a, erledigt = re.split(r"(<[^>]+>)", html), 0, set()
    for k, t in enumerate(teile):
        if t.startswith("<"):
            in_a += 1 if re.match(r"<a[\s>]", t) else -1 if t.startswith("</a") else 0
            continue
        if in_a or not t.strip():
            continue
        belegt, treffer = [], []
        for m_re, i in muster:
            if i in erledigt:
                continue
            m = m_re.search(t)
            while m and any(m.start() < e and s < m.end() for s, e in belegt):
                m = m_re.search(t, m.end())
            if m:
                belegt.append((m.start(), m.end()))
                treffer.append((m.start(), m.end(), i))
                erledigt.add(i)
        for s, e, i in sorted(treffer, reverse=True):
            t = f'{t[:s]}<a class="kp" href="#{sid}" data-p="{sid}:{i}">{t[s:e]}</a>{t[e:]}'
        teile[k] = t
    return "".join(teile)


SYMBOLE = {"plan": "calendar-days", "varianten": "split", "etappen": "footprints", "wissen": "book-open",
           "praxis": "backpack", "quellen": "library", "suche": "search", "rueckmeldungen": "message-circle", "zu": "x",
           "aufgaben": "list-checks", "karte": "map", "offen": "list-checks", "wuensche": "sparkles",
           # Kategorien der Etappen-Karten
           "einkehr": "utensils", "wasser": "droplet", "bus": "bus", "unterkunft": "bed-double", "apotheke": "pill",
           "taxi": "car-taxi-front",
           # Symbole, die eine Art der Reise tragen darf (routen.SYMBOLE_ARTEN, docs/ontologie.md „Darstellung“; Paket O-5)
           "zelt": "tent", "ticket": "ticket", "museum": "landmark", "wandern": "footprints", "bahn": "train-front", "schiff": "ship",
           "flug": "plane", "auto": "car", "rad": "bike",
           # Kennzahlen und Orte (Gesicht „Freundlich“, #52)
           "gehzeit": "clock", "aufstieg": "trending-up", "abstieg": "trending-down", "strecke": "route", "ort": "map-pin"}


def symbole():
    """Unsichtbares SVG mit einem <symbol id="i-…"> je Eintrag in SYMBOLE; Lizenzhinweis bleibt erhalten."""
    teile = [f"<!-- Symbole: Lucide 1.55.0, ISC-Lizenz, https://lucide.dev (engine/vendor/{LUCIDE}/LICENSE) -->",
             '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">']
    for name, datei in SYMBOLE.items():
        svg = (Path(__file__).parent / "vendor" / LUCIDE / f"{datei}.svg").read_text(encoding="utf-8")
        inhalt = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)
        teile.append(f'<symbol id="i-{name}" viewBox="0 0 24 24">{" ".join(inhalt.split())}</symbol>')
    return "".join(teile) + "</svg>"


PWA_FARBE = "#1f7a57"       # = --acc der Vorlage
PWA_HINTERGRUND = "#f8f8f5"  # = --bg der Vorlage


ICON_GROESSEN = (32, 180, 192, 512)  # Browser-Tab, iPhone-Homebildschirm, Android/Manifest


def icon_aus_svg(svg, groesse):
    """App-Symbol aus reisen/<reise>/medien/icon.svg; CairoSVG (LGPL) rechnet es in die Größe um."""
    import io
    import cairosvg
    png = cairosvg.svg2png(url=str(svg), output_width=groesse, output_height=groesse)
    return Image.open(io.BytesIO(png)).convert("RGB")  # iOS mag keine Transparenz


def icon_zeichnen(text, groesse):
    """Schlichtes Icon: Kurzname weiß auf Akzentfarbe, Wörter untereinander. iOS rundet selbst ab."""
    from PIL import ImageDraw, ImageFont
    im = Image.new("RGB", (groesse, groesse), PWA_FARBE)
    d = ImageDraw.Draw(im)
    zeilen = text.split()[:2] or ["?"]
    schrift = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    pt = groesse // 2
    while pt > 8:
        try:
            f = ImageFont.truetype(schrift, pt)
        except OSError:
            f = ImageFont.load_default()
            break
        if max(d.textlength(z, font=f) for z in zeilen) <= groesse * 0.8 and pt * 1.15 * len(zeilen) <= groesse * 0.75:
            break
        pt -= 2
    hoehe = pt * 1.15
    y0 = (groesse - hoehe * len(zeilen)) / 2
    for i, z in enumerate(zeilen):
        d.text((groesse / 2, y0 + hoehe * (i + 0.5)), z, font=f, fill="white", anchor="mm")
    return im


def texte_fuer_seite():
    """Katalog aller Sprachen für die Seite (ADR-0006); ab M1 legt der Bau ihn in die Seite, damit der Umschalter offline geht."""
    return texte.seite()


def bauen(reise_dir, ziel_dir, umzug=None):
    b = Bauer(reise_dir, ziel_dir, umzug)
    daten = b.daten()
    b.schreiben(daten)
    for h in b.hinweise:
        print("Hinweis:", h)
    return daten


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="engine/bauen.py", description="Baut die Seite einer Reise.")
    ap.add_argument("reise", help="Ordnername der Reise, z. B. beispielreise")
    ap.add_argument("--reisen", type=Path, default=Path.cwd() / "reisen", help="Ordner mit den Reisen (Vorgabe ./reisen)")
    ap.add_argument("--ziel", type=Path, default=Path.cwd() / "dist", help="Ausgabeordner (Vorgabe ./dist)")
    ap.add_argument("--umzug-nach", default=None, help="Neue Adresse der Seiten (z. B. https://frieda.example): Der Service Worker "
                    "räumt auf und leitet geöffnete Seiten dorthin (Vorgabe: Umgebung FR_UMZUG_NACH)")
    a = ap.parse_args(argv[1:])
    reise = a.reise
    try:
        daten = bauen(a.reisen / reise, a.ziel / reise, a.umzug_nach)
    except BauFehler as e:
        print("Die Seite wurde NICHT gebaut. Das muss zuerst behoben werden:")
        for m in e.meldungen:
            print(" -", m)
        return 1
    n_e = sum(1 for a in daten["abschnitte"] if a["typ"] == "etappe")
    print(f"Fertig: {a.ziel / reise / 'index.html'} ({len(daten['abschnitte'])} Abschnitte, {n_e} Etappen)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
