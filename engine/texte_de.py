"""Texte der Software auf Deutsch (ADR-0006). Alles, was eine Sprache ausmacht, steht in dieser Datei; der Code kennt
keine Sprache beim Namen. Deutsche Texte stehen wörtlich so, wie die Software sie von jeher zeigt."""

NAME = "Deutsch"
LOCALE = "de-DE"
RICHTUNG = "ltr"
DATUM = "%-d.%-m.%Y"
DATUM_KURZ = "%-d.%-m."
ZEIT = "%-H:%M"
WOCHENTAGE_KURZ = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")   # Montag bis Sonntag


def PLURAL(n):
    """Pluralkategorie nach CLDR: Deutsch kennt one und other."""
    return "one" if n == 1 else "other"


TEXTE = {
    # Status einer Option (Wahlstelle) auf der Seite
    "seite.status.vorgeschlagen": "vorgeschlagen",
    "seite.status.favorisiert": "favorisiert",
    "seite.status.gewaehlt": "gewählt",
    "seite.status.verworfen": "verworfen",
    "seite.status.ersetzt": "ersetzt",
    # Status einer Buchung
    "seite.buchung.status.gebucht": "gebucht",
    "seite.buchung.status.angefragt": "angefragt",
    "seite.buchung.status.storniert": "storniert",
    # Status einer Rückmeldung
    "seite.rueckmeldung.status.neu": "neu",
    "seite.rueckmeldung.status.uebernommen": "übernommen",
    "seite.rueckmeldung.status.verworfen": "verworfen",
    "seite.rueckmeldung.status.rueckfrage": "Rückfrage",
    "seite.rueckmeldung.status.ausstehend": "noch nicht gesendet",
    # Status eines Wunsches (Art Wunsch einer Rückmeldung)
    "seite.wunsch.status.neu": "neu",
    "seite.wunsch.status.uebernommen": "aufgenommen",
    "seite.wunsch.status.verworfen": "passt nicht",
    "seite.wunsch.status.rueckfrage": "Rückfrage",
    "seite.wunsch.status.ausstehend": "noch nicht gesendet",
    # Aufgaben
    "seite.aufgabe.status.offen": "offen",
    "seite.aufgabe.status.in_arbeit": "in Arbeit",
    "seite.aufgabe.status.erledigt": "erledigt",
    "seite.aufgabe.status.entfaellt": "entfällt",
    "seite.aufgabe.feld.titel": "Titel",
    "seite.aufgabe.feld.bezug": "Bezug",
    "seite.aufgabe.feld.zustaendig": "Zuständig",
    "seite.aufgabe.feld.prioritaet": "Priorität",
    "seite.aufgabe.feld.ab": "Ab",
    "seite.aufgabe.feld.frist": "Frist",
    "seite.aufgabe.feld.notiz": "Notiz",
    "seite.aufgabe.feld.status": "Status",
    # Sprache der Seite
    "seite.sprache.titel": "Sprache",
    "seite.bausteine.text.beschreibung": "Jeder Text der Seite kommt aus dem Katalog der gewählten Sprache (T mit Schlüssel); Plural wählt die Regel der Sprache.",
    "seite.bausteine.text.huelle": "Sprache der Hülle",
    # Karte
    "seite.karte.kueste": "Küste schematisch",
    # Konnektor
    "konnektor.wort.gewaehlt": "gewählt",
    "konnektor.wort.verworfen": "verworfen",
    "konnektor.wort.ersetzt": "ersetzt",
    # Schreibweg: Entscheidungen, Grundformen, Felder einer Buchung, Stufen eines Merkmals
    "schreiben.wort.gewaehlt": "gewählt",
    "schreiben.wort.verworfen": "verworfen",
    "schreiben.wort.ersetzt": "ersetzt",
    "schreiben.grundform.aufenthalt": "Aufenthalt",
    "schreiben.grundform.bewegung": "Bewegung",
    "schreiben.grundform.folge": "Folge",
    "schreiben.buchung.fuer": "Gehört zu",
    "schreiben.buchung.status": "Status",
    "schreiben.buchung.nummer": "Nummer",
    "schreiben.buchung.bei": "Gebucht bei",
    "schreiben.buchung.preis": "Preis",
    "schreiben.buchung.bezahlt": "Bezahlt",
    "schreiben.buchung.frist": "Frist",
    "schreiben.buchung.frist_was": "Was bis zur Frist",
    "schreiben.buchung.storno": "Stornoregel",
    "schreiben.buchung.storno_bis": "Stornofrist",
    "schreiben.buchung.gebucht_am": "Gebucht am",
    "schreiben.buchung.quelle": "Herkunft",
    "schreiben.buchung.notiz": "Notiz",
    "schreiben.buchung.ab": "Ab",
    "schreiben.buchung.ab_was": "Was ab dann geht",
    "schreiben.buchung.personen": "Reisende",
    "schreiben.buchung.preise": "Preise je Ding",
    "schreiben.stufe.pflicht": "nötig",
    "schreiben.stufe.empfohlen": "gut zu wissen",
    "schreiben.stufe.angeboten": "zusätzlich",
    "schreiben.stufe.aus": "aus",
}
