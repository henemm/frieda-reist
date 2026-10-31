"""Texte der Software auf Englisch (ADR-0006), britische Schreibung. Dieselben Schlüssel und Platzhalter wie
texte_de.py; Datenwerte der Reise (gewaehlt, pflicht …) bleiben deutsch und werden im Text erklärt, nicht übersetzt."""

NAME = "English"
LOCALE = "en-GB"
RICHTUNG = "ltr"
DATUM = "%-d/%-m/%Y"
DATUM_KURZ = "%-d/%-m"
ZEIT = "%H:%M"


def PLURAL(n):
    """Pluralkategorie nach CLDR: Englisch kennt one und other."""
    return "one" if n == 1 else "other"


TEXTE = {
    # Status einer Option (Wahlstelle) auf der Seite
    "seite.status.vorgeschlagen": "proposed",
    "seite.status.favorisiert": "favourite",
    "seite.status.gewaehlt": "chosen",
    "seite.status.verworfen": "rejected",
    "seite.status.ersetzt": "replaced",
    # Status einer Buchung
    "seite.buchung.status.gebucht": "booked",
    "seite.buchung.status.angefragt": "requested",
    "seite.buchung.status.storniert": "cancelled",
    # Status einer Rückmeldung
    "seite.rueckmeldung.status.neu": "new",
    "seite.rueckmeldung.status.uebernommen": "taken up",
    "seite.rueckmeldung.status.verworfen": "rejected",
    "seite.rueckmeldung.status.rueckfrage": "follow-up question",
    "seite.rueckmeldung.status.ausstehend": "not sent yet",
    # Status eines Wunsches (Art Wunsch einer Rückmeldung)
    "seite.wunsch.status.neu": "new",
    "seite.wunsch.status.uebernommen": "added",
    "seite.wunsch.status.verworfen": "doesn't fit",
    "seite.wunsch.status.rueckfrage": "follow-up question",
    "seite.wunsch.status.ausstehend": "not sent yet",
    # Aufgaben
    "seite.aufgabe.status.offen": "open",
    "seite.aufgabe.status.in_arbeit": "in progress",
    "seite.aufgabe.status.erledigt": "done",
    "seite.aufgabe.status.entfaellt": "dropped",
    "seite.aufgabe.feld.titel": "Title",
    "seite.aufgabe.feld.bezug": "Related to",
    "seite.aufgabe.feld.zustaendig": "Assigned to",
    "seite.aufgabe.feld.prioritaet": "Priority",
    "seite.aufgabe.feld.ab": "From",
    "seite.aufgabe.feld.frist": "Deadline",
    "seite.aufgabe.feld.notiz": "Note",
    "seite.aufgabe.feld.status": "Status",
    # Konnektor
    "konnektor.wort.gewaehlt": "chosen",
    "konnektor.wort.verworfen": "rejected",
    "konnektor.wort.ersetzt": "replaced",
    # Schreibweg: Entscheidungen, Grundformen, Felder einer Buchung, Stufen eines Merkmals
    "schreiben.wort.gewaehlt": "chosen",
    "schreiben.wort.verworfen": "rejected",
    "schreiben.wort.ersetzt": "replaced",
    "schreiben.grundform.aufenthalt": "Stay",
    "schreiben.grundform.bewegung": "Movement",
    "schreiben.grundform.folge": "Sequence",
    "schreiben.buchung.fuer": "Belongs to",
    "schreiben.buchung.status": "Status",
    "schreiben.buchung.nummer": "Number",
    "schreiben.buchung.bei": "Booked with",
    "schreiben.buchung.preis": "Price",
    "schreiben.buchung.bezahlt": "Paid",
    "schreiben.buchung.frist": "Deadline",
    "schreiben.buchung.frist_was": "What is due by the deadline",
    "schreiben.buchung.storno": "Cancellation rule",
    "schreiben.buchung.storno_bis": "Cancellation deadline",
    "schreiben.buchung.gebucht_am": "Booked on",
    "schreiben.buchung.quelle": "Source",
    "schreiben.buchung.notiz": "Note",
    "schreiben.buchung.ab": "From",
    "schreiben.buchung.ab_was": "What is possible from then on",
    "schreiben.buchung.personen": "Travellers",
    "schreiben.buchung.preise": "Prices per item",
    "schreiben.stufe.pflicht": "required",
    "schreiben.stufe.empfohlen": "good to know",
    "schreiben.stufe.angeboten": "additional",
    "schreiben.stufe.aus": "off",
}
