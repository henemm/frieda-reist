"""Ordner und Werte einer Instanz für die Software (docs/betrieb.md, Einstellungen).

Die Betriebsskripte (betrieb/) setzen die Umgebung selbst. Ruft man die Software von Hand auf (etwa
`python3 engine/rueckmeldungen.py liste <reise>` im Reisen-Repo) oder läuft ein Dienst nur mit einem Teil der Werte,
leitet dieses Modul den Rest nach derselben Ordnung ab, ohne Werte einer bestimmten Instanz zu kennen:

  Seiten   RM_SEITEN, KN_SEITEN, FR_SEITEN; sonst der Ordner über RM_ABLAGE; sonst aus den Einstellungen der Instanz
           (FR_SEITEN bzw. /srv/<FR_INSTANZ>); sonst /srv/frieda
  Ablage   RM_ABLAGE, FR_ABLAGE; sonst <Seiten>/_rueckmeldungen
  Dienst   FR_DIENST; sonst <Seiten>/_dienst (Code der Dienste, Zustand des Veröffentlichens, Reise-Stände)
  Konten   FR_KONTEN; sonst <Seiten>/_konten (Konten-Datenbank des Dienstes, nicht Teil einer Reise); eine ältere Datenbank
           unter <Ablage>/_konten/ gilt weiter, solange am neuen Ort keine liegt
  Speicher FR_SPEICHER; sonst <Seiten>/_speicher (Reisespeicher reisen.db, Versionen aller Reisen, ADR-0009, #346)
  Speicherreisen FR_SPEICHERREISEN: kommagetrennte Namen (Ordner) der Reisen, die der Schreibweg über den Reisespeicher
           schreibt (Stufe 2, #347); Vorgabe leer: jede Reise schreibt über Git wie bisher (bis Stufe 5)
  Neu      <Konten>/neu (Anfragen nach neuen Reisen und Meldungen an Personen, gehört zu keiner Reise, #72); ein älterer
           Ordner <Ablage>/_neu/ gilt weiter, solange am neuen Ort nichts liegt
  Zugänge  KN_ZUGAENGE; sonst <FR_KONNEKTOR bzw. <Seiten>/_konnektor>/zugaenge.json

Einstellungen der Instanz: <FR_WURZEL bzw. aktueller Ordner>/betrieb/einstellungen.env, Zeilen NAME=wert wie in
betrieb/einstellungen.beispiel. Die Umgebung gilt vor der Datei.
"""
import os
from pathlib import Path

VORGABE_INSTANZ = "frieda"
KENNUNG = "Frieda-Reist/1 (+https://github.com/henemm/frieda-reist)"


def wurzel():
    """Wurzel des Reisen-Repos: FR_WURZEL, sonst der aktuelle Ordner (Aufrufe von Hand dort)."""
    return Path(os.environ.get("FR_WURZEL") or Path.cwd())


def _datei():
    return Path(os.environ.get("FR_EINSTELLUNGEN") or wurzel() / "betrieb" / "einstellungen.env")


def einstellungen():
    """Werte aus der Einstellungsdatei der Instanz -> {NAME: wert}; nur Namen FR_…, ohne Shell-Auswertung."""
    try:
        zeilen = _datei().read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    werte = {}
    for z in zeilen:
        z = z.strip()
        if not z or z.startswith("#") or "=" not in z:
            continue
        name, wert = z.split("=", 1)
        if name.startswith("FR_") and name.replace("_", "").isalnum():
            if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "\"'":
                wert = wert[1:-1]
            werte[name] = wert
    return werte


def wert(name, vorgabe=None):
    """Ein Wert aus Umgebung oder Einstellungsdatei (leer zählt als nicht gesetzt)."""
    return os.environ.get(name) or einstellungen().get(name) or vorgabe


def seiten():
    for name in ("RM_SEITEN", "KN_SEITEN", "FR_SEITEN"):
        if os.environ.get(name):
            return Path(os.environ[name])
    if os.environ.get("RM_ABLAGE"):
        return Path(os.environ["RM_ABLAGE"]).parent
    return Path(wert("FR_SEITEN") or f"/srv/{wert('FR_INSTANZ', VORGABE_INSTANZ)}")


def ablage():
    return Path(os.environ.get("RM_ABLAGE") or wert("FR_ABLAGE") or seiten() / "_rueckmeldungen")


def dienst():
    """Dienstordner der Instanz (betrieb/gemeinsam.sh FR_DIENST): Code der Dienste und Zustand des Veröffentlichens."""
    return Path(wert("FR_DIENST") or seiten() / "_dienst")


def zeitzone():
    """Zeitzone, in der Dienste Zeiten nennen, wenn die der Person unbekannt ist: FR_ZEITZONE (IANA-Name), sonst UTC."""
    return wert("FR_ZEITZONE", "UTC")


def konten():
    """Ordner der Konten-Datenbank (Konten und Anmeldungen aller Nutzer dieser Instanz, getrennt von den Reisen)."""
    neu = Path(os.environ.get("FR_KONTEN") or wert("FR_KONTEN") or seiten() / "_konten")
    alt = ablage() / "_konten"
    return alt if not (neu / "konten.db").exists() and (alt / "konten.db").exists() else neu


def speicher():
    """Ordner des Reisespeichers (engine/reisespeicher.py, ADR-0009): Reisedaten als Versionen in SQLite, mit Sicherung."""
    return Path(wert("FR_SPEICHER") or seiten() / "_speicher")


def speicher_ablage():
    """Ablage des Reisespeichers für Medien (Stufe 4, #349): eine Datei je Inhalt, benannt nach der Prüfsumme."""
    return speicher() / "ablage"


def speicherreisen():
    """Reisen, die über den Reisespeicher geschrieben werden (FR_SPEICHERREISEN, kommagetrennt; Leerzeichen und leere Teile
    fallen weg). Ein gesetzter, auch leerer Wert in der Umgebung gilt vor der Datei. Vorgabe: keine (alles über Git)."""
    roh = os.environ["FR_SPEICHERREISEN"] if "FR_SPEICHERREISEN" in os.environ else einstellungen().get("FR_SPEICHERREISEN", "")
    return [r.strip() for r in roh.split(",") if r.strip()]


def _belegt(p):
    return p.is_dir() and any(p.iterdir())


def neu():
    """Ordner für Anfragen nach neuen Reisen und Meldungen an Personen: Personenbezogenes ohne Reise liegt bei den Konten
    (#72). Der alte Ort <Ablage>/_neu gilt weiter, solange am neuen nichts liegt (Übergang wie beim Umzug der Konten)."""
    neu, alt = konten() / "neu", ablage() / "_neu"
    return alt if not _belegt(neu) and _belegt(alt) else neu


def zugaenge():
    if os.environ.get("KN_ZUGAENGE"):
        return Path(os.environ["KN_ZUGAENGE"])
    return Path(wert("FR_KONNEKTOR") or seiten() / "_konnektor") / "zugaenge.json"


def kennung():
    """Kennung bei Abrufen fremder Dienste (OpenStreetMap verlangt eine Kontaktangabe): FR_KENNUNG der Instanz."""
    return wert("FR_KENNUNG", KENNUNG)
