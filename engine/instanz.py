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
  Speicherreisen Im Speicher ist, was im Speicher steht (#454): die Reisen mit Eintrag im Reisespeicher, deren Umschaltung
           nicht offen ist (speicherreisen()). FR_SPEICHERREISEN ist nur noch Übergang: gelesen, wirkungslos
  Neu      <Konten>/neu (Anfragen nach neuen Reisen und Meldungen an Personen, gehört zu keiner Reise, #72); ein älterer
           Ordner <Ablage>/_neu/ gilt weiter, solange am neuen Ort nichts liegt
  Konnektor FR_KONNEKTOR; sonst der Ordner von KN_ZUGAENGE (alter Name aus den Units, bis sie neu erzeugt sind);
           sonst <Seiten>/_konnektor (seiten.json, neue-reisen-ausstehend.jsonl; die alten Links sind abgeschafft, #421)

Einstellungen der Instanz (#454): FR_EINSTELLUNGEN, sonst <Dienst>/instanz/einstellungen.env, sonst (Übergang, alter Ort)
<FR_WURZEL bzw. aktueller Ordner>/betrieb/einstellungen.env; Zeilen NAME=wert wie in betrieb/einstellungen.beispiel. Die
Umgebung gilt vor der Datei. Der Dienstordner für diese Suche kommt nur aus der Umgebung (FR_DIENST, sonst aus FR_SEITEN bzw.
FR_INSTANZ), nie aus der Datei selbst.
"""
import os
from pathlib import Path

VORGABE_INSTANZ = "frieda"
KENNUNG = "Frieda-Reist/1 (+https://github.com/henemm/frieda-reist)"


def wurzel():
    """Wurzel des Reisen-Repos: FR_WURZEL, sonst der aktuelle Ordner (Aufrufe von Hand dort)."""
    return Path(os.environ.get("FR_WURZEL") or Path.cwd())


def _dienst_aus_umgebung():
    """Dienstordner nur aus der Umgebung (wie gemeinsam.sh vor dem Einlesen): FR_DIENST, sonst <FR_SEITEN>/_dienst, sonst
    /srv/<FR_INSTANZ>/_dienst. Die Einstellungsdatei liegt darin, kann ihn also nicht selbst nennen."""
    if os.environ.get("FR_DIENST"):
        return Path(os.environ["FR_DIENST"])
    seiten_ = os.environ.get("FR_SEITEN") or f"/srv/{os.environ.get('FR_INSTANZ') or VORGABE_INSTANZ}"
    return Path(seiten_) / "_dienst"


def _datei():
    """Einstellungsdatei der Instanz (#454): FR_EINSTELLUNGEN, sonst <Dienst>/instanz/einstellungen.env, sonst (Übergang)
    der alte Ort <Wurzel>/betrieb/einstellungen.env."""
    if os.environ.get("FR_EINSTELLUNGEN"):
        return Path(os.environ["FR_EINSTELLUNGEN"])
    neu = _dienst_aus_umgebung() / "instanz" / "einstellungen.env"
    if neu.exists() or neu.is_symlink():
        return neu
    return wurzel() / "betrieb" / "einstellungen.env"


def einstellungen():
    """Werte aus der Einstellungsdatei der Instanz -> {NAME: wert}; nur Namen FR_…, ohne Shell-Auswertung.
    Nachsichtig: eine fehlende oder unlesbare Datei gibt {} (Pfade, Ablage, Zeitzone brauchen weiter ihre Vorgaben)."""
    try:
        return _lesen()
    except OSError:
        return {}


def _lesen():
    """Wie einstellungen(), aber Lesefehler (FileNotFoundError, PermissionError, …) gehen an den Aufrufer."""
    zeilen = _datei().read_text(encoding="utf-8").splitlines()
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


class EinstellungenNichtLesbar(OSError):
    """Die Einstellungsdatei der Instanz existiert, kann aber nicht gelesen werden (#361), oder der Reisespeicher ist nicht
    lesbar (SpeicherNichtLesbar, #454): Welche Reisen im Speicher liegen, ist dann unbekannt. Wer darüber den Weg einer Reise
    wählt, muss laut abbrechen, nicht auf den Git-Weg ausweichen."""


class SpeicherNichtLesbar(EinstellungenNichtLesbar):
    """Der Reisespeicher ist vorhanden, aber nicht lesbar (#454): speicherreisen() kennt die Reisen nicht (fail closed)."""


def einstellungen_pruefen():
    """Fail closed (#361): Ist die Einstellungsdatei vorhanden, aber nicht lesbar, EinstellungenNichtLesbar; eine fehlende
    Datei ist in Ordnung. Für Entscheidungen, die von Orten aus den Einstellungen abhängen (Speicher, Dienstordner)."""
    try:
        _lesen()
    except FileNotFoundError:
        pass
    except OSError as e:
        raise EinstellungenNichtLesbar(f"{_datei().name}: {e.strerror or type(e).__name__}") from e


def speicherreisen():
    """Reisen, die über den Reisespeicher geschrieben und gebaut werden (#454): Im Speicher ist, was im Speicher steht, also
    jede Reise mit mindestens einem Vorgang, deren Umschaltung nicht offen ist (reisespeicher.speicherreisen). Sortiert.
    FR_SPEICHERREISEN aus Umgebung oder Datei ist nur noch Übergang und wirkungslos. Ohne Datenbank: keine. Ist der Speicher
    vorhanden, aber nicht lesbar, wird SpeicherNichtLesbar ausgelöst (fail closed, #361), nie eine leere Liste. Ebenso
    EinstellungenNichtLesbar, wenn die Einstellungsdatei vorhanden, aber nicht lesbar ist: Speicher und Dienstordner können
    dort stehen, die Antwort wäre ungewiss (#361)."""
    einstellungen_pruefen()
    import reisespeicher
    try:
        return reisespeicher.speicherreisen()
    except EinstellungenNichtLesbar:
        raise
    except reisespeicher.sqlite3.Error as e:
        raise SpeicherNichtLesbar(f"{reisespeicher.pfad().name}: {e}") from e
    except OSError as e:
        raise SpeicherNichtLesbar(f"{reisespeicher.pfad().name}: {e.strerror or type(e).__name__}") from e


def _belegt(p):
    return p.is_dir() and any(p.iterdir())


def neu():
    """Ordner für Anfragen nach neuen Reisen und Meldungen an Personen: Personenbezogenes ohne Reise liegt bei den Konten
    (#72). Der alte Ort <Ablage>/_neu gilt weiter, solange am neuen nichts liegt (Übergang wie beim Umzug der Konten)."""
    neu, alt = konten() / "neu", ablage() / "_neu"
    return alt if not _belegt(neu) and _belegt(alt) else neu


def konnektor():
    """Ordner des Konnektors (seiten.json, neue-reisen-ausstehend.jsonl). KN_ZUGAENGE nannte bis #421 die Datei der alten
    Links darin; ältere Units setzen nur sie, darum gilt ihr Ordner, solange FR_KONNEKTOR fehlt."""
    if os.environ.get("FR_KONNEKTOR"):
        return Path(os.environ["FR_KONNEKTOR"])
    if os.environ.get("KN_ZUGAENGE"):
        return Path(os.environ["KN_ZUGAENGE"]).parent
    return Path(wert("FR_KONNEKTOR") or seiten() / "_konnektor")


def kennung():
    """Kennung bei Abrufen fremder Dienste (OpenStreetMap verlangt eine Kontaktangabe): FR_KENNUNG der Instanz."""
    return wert("FR_KENNUNG", KENNUNG)


VORGABE_GRENZE_REISEN = 10
VORGABE_GRENZE_SCHREIBEN = 300
VORGABE_GRENZE_WARTELISTE_TAG = 20


def _grenze(name, vorgabe):
    """Ganze Zahl ab 1 aus Umgebung oder Einstellungsdatei; leer, keine ganze Zahl oder kleiner als 1 gilt als nicht gesetzt."""
    try:
        n = int(str(wert(name, "")).strip())
    except ValueError:
        return vorgabe
    return n if n >= 1 else vorgabe


def grenze_reisen():
    """Höchstzahl angelegter Reisen je Konto (FR_GRENZE_REISEN, #380); Betreiber sind ausgenommen (konten.py)."""
    return _grenze("FR_GRENZE_REISEN", VORGABE_GRENZE_REISEN)


def grenze_schreiben():
    """Höchstzahl schreibender Werkzeugaufrufe je Konto und Stunde im Konnektor (FR_GRENZE_SCHREIBEN, #380)."""
    return _grenze("FR_GRENZE_SCHREIBEN", VORGABE_GRENZE_SCHREIBEN)


def grenze_warteliste_tag():
    """Höchstzahl der Bestätigungsmails der Warteliste je Kalendertag (UTC) (FR_GRENZE_WARTELISTE_TAG, #534), damit das
    Mail-Kontingent der Instanz reicht. Abschalten mit 0 geht nicht: ungültige Werte gelten als nicht gesetzt."""
    return _grenze("FR_GRENZE_WARTELISTE_TAG", VORGABE_GRENZE_WARTELISTE_TAG)


VORGABE_GRENZE_CODES_TAG = 30


def grenze_codes_tag():
    """Höchstzahl der Anmeldecodes je Kalendertag (UTC) an Adressen ohne Konto und ohne offene Einladung
    (FR_GRENZE_CODES_TAG), damit niemand über das Anmeldeformular das Mail-Kontingent der Instanz leert. Wer ein Konto
    oder eine Einladung hat, bekommt seinen Code immer."""
    return _grenze("FR_GRENZE_CODES_TAG", VORGABE_GRENZE_CODES_TAG)


VORGABE_LOESCHFRIST_TAGE = 14


def loeschfrist_tage():
    """Schonfrist in Tagen zwischen „Reise löschen“ und dem endgültigen Entfernen (FR_LOESCHFRIST_TAGE, #381); in dieser
    Zeit kann eine Organisator:in die Reise zurückholen."""
    return _grenze("FR_LOESCHFRIST_TAGE", VORGABE_LOESCHFRIST_TAGE)
