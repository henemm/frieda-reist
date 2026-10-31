"""Namen der Schnittstelle des Konnektors (ADR-0006, Punkt 4): Werkzeug- und Parameternamen heißen für den AI-Client englisch
(tools/list), die deutschen Namen gelten als Aliase weiter. Die Übersetzung geschieht nur am Rand des Konnektors: Schreibweg,
Rückmeldedienst, Dateien und Tests darunter kennen nur die internen (deutschen) Namen.

  NAMEN                    englischer Werkzeugname -> interner Name
  PARAMETER                interner Parametername -> englischer Name (für alle Werkzeuge)
  PARAMETER_JE_WERKZEUG    Ausnahmen, wo dasselbe Wort etwas anderes meint
  ENUM_ALIAS               englischer Wert -> Datenwert (nur Eingabe; Datenwerte bleiben deutsch)
"""
import copy
import re

NAMEN = {
    "overview": "ueberblick",
    "show": "zeige",
    "search": "suche",
    "open_questions": "offene_fragen",
    "variants": "varianten",
    "feedback_list": "rueckmeldungen",
    "feedback_give": "rueckmeldung_geben",
    "feedback_resolve": "rueckmeldung_erledigen",
    "tasks": "aufgaben",
    "task_create": "aufgabe_anlegen",
    "task_update": "aufgabe_aendern",
    "wishes": "wuensche",
    "wish_update": "wunsch_aendern",
    "wish_propose": "wunsch_vorschlagen",
    "categories": "kategorien",
    "category_define": "kategorie_definieren",
    "attributes": "merkmale",
    "attribute_define": "merkmal_definieren",
    "attribute_merge": "merkmal_zusammenfuehren",
    "kind_define": "art_definieren",
    "kinds_adopt": "arten_uebernehmen",
    "value_set": "wert_eintragen",
    "location_set": "lage_eintragen",
    "item_create": "ding_anlegen",
    "item_update": "ding_aendern",
    "option_create": "option_anlegen",
    "option_update": "option_aendern",
    "choice_create": "wahlstelle_anlegen",
    "choice_update": "wahlstelle_aendern",
    "decide": "entscheiden",
    "plan_create": "plan_anlegen",
    "plan_update": "plan_aendern",
    "day_create": "tag_anlegen",
    "day_update": "tag_aendern",
    "fixed_date_set": "termin_setzen",
    "question_create": "frage_anlegen",
    "question_answer": "frage_beantworten",
    "question_close": "frage_schliessen",
    "knowledge_write": "wissen_schreiben",
    "knowledge_update": "wissen_aendern",
    "narrative_write": "lesetext_schreiben",
    "booking_create": "buchung_anlegen",
    "booking_update": "buchung_aendern",
    "receipt_add": "beleg_anlegen",
    "person_invite": "person_einladen",
    "person_remove": "person_entfernen",
    "trip_update": "reise_aendern",
    "trip_status_set": "reise_status_setzen",
    "setting_set": "einstellung_setzen",
    "my_trips": "meine_reisen",
    "trip_create": "reise_anlegen",
    "trip_create_request": "reisen_anlegen_anfragen",
    "request_decide": "anfrage_entscheiden",
    "calendar": "kalender",
    "language_set": "sprache_setzen",
    "language_set": "sprache_setzen",
}
INTERN_ZU_ENGLISCH = {i: e for e, i in NAMEN.items()}

PARAMETER = {
    "ab": "available_from", "ab_was": "available_from_what", "abschnitt": "section", "adresse": "address", "alle": "all", "an": "at",
    "antwort": "answer", "art": "kind", "art_bezeichnung": "kind_label", "art_hinweis": "kind_hint", "art_symbol": "kind_symbol",
    "art_umriss": "kind_outline", "arten": "kinds", "auch": "aliases", "aufenthalte": "stays", "ausloeser": "trigger",
    "ausserhalb": "outside", "auswahl": "selection", "bausteine": "blocks", "beginn": "start_time", "begriff": "query",
    "bei": "booked_with", "beleg_base64": "receipt_base64", "beleg_dateiname": "receipt_filename", "beleg_text": "receipt_text",
    "beschreibung": "description", "bezahlt": "paid", "bezeichnung": "label", "bezug": "refs", "bis": "until", "buchbar": "bookable",
    "buchung": "booking", "buchungslink": "booking_link", "datei": "file", "dateiname": "filename", "daten_base64": "data_base64",
    "datum": "date", "eingeplant": "scheduled", "einheit": "unit", "einzahl": "singular", "ende": "end_time", "entfernen": "remove",
    "erfordert": "requires", "ergebnis": "result", "erlauben": "allow", "erlebt": "experienced", "ersetzt_durch": "replaced_by",
    "farbe": "colour", "favorisiert": "favoured", "folge": "sequence", "frage": "question", "frist": "deadline",
    "frist_was": "deadline_what", "fuer": "for", "gebucht_am": "booked_on", "geprueft": "checked", "gilt": "valid_for",
    "grund": "reason", "grundform": "basic_form", "gruppe": "group", "hilfe": "help", "hinweis": "hint", "kategorie": "category",
    "kommentar": "comment", "koordinaten": "coordinates", "kurz": "short", "lesetext": "reading_text", "merkmal": "attribute",
    "merkmale": "attributes", "minus": "cons", "nach": "after", "nacht": "night", "neu": "new", "neuer_name": "new_name",
    "neuer_titel": "new_title", "notiz": "note", "nummer": "number", "nummeriert": "numbered", "ohne_route": "without_route",
    "optionen": "options", "ort": "place", "personen": "people", "pfad": "path", "plus": "pros", "preis": "price", "preise": "prices", "zahlung": "payment",
    "prioritaet": "priority", "punkte": "points", "quelle": "source", "regeln": "rules", "reist": "travels", "rolle": "role",
    "rubrik": "heading", "schliesst_aus": "excludes", "schluessel": "key", "siehe": "see", "sprache": "language",
    "storno": "cancellation", "storno_bis": "cancellation_until", "strecken": "legs", "stufe": "level", "stufen": "levels",
    "summiert": "summed", "titel": "title", "trotzdem": "anyway", "typ": "type", "unterkuenfte": "accommodations",
    "untertitel": "subtitle", "veraenderlich": "changeable", "von": "from", "von_reise": "from_trip", "vor": "before",
    "vorname": "first_name", "wahl": "choices", "wahlstelle": "choice", "wann": "when", "was": "what", "wert": "value",
    "werte": "values", "wunsch": "wish", "zeit": "time_text", "ziel": "target", "zustaendig": "assignee", "reise": "trip",
}
# Gleiches Wort, andere Bedeutung: bei Strecken (ding_anlegen, ding_aendern) sind von/nach Start und Ziel, ab/an Abfahrt und Ankunft
STRECKE = {"von": "from_place", "nach": "to_place", "ab": "departure", "an": "arrival"}
PARAMETER_JE_WERKZEUG = {
    "ding_anlegen": STRECKE, "ding_aendern": STRECKE,
    "aufgabe_anlegen": {"ab": "earliest"}, "aufgabe_aendern": {"ab": "earliest"},
    "tag_aendern": {"nacht": "night", "wahl": "choices"},
    "buchung_anlegen": {"ab": "available_from"}, "buchung_aendern": {"ab": "available_from"},
}
ENUM_ALIAS = {
    "chosen": "gewaehlt", "rejected": "verworfen", "replaced": "ersetzt", "proposed": "vorgeschlagen", "favoured": "favorisiert",
    "organizer": "organisator", "organiser": "organisator", "contributor": "mitwirkend", "guest": "gast",
    "required": "pflicht", "recommended": "empfohlen", "optional": "angeboten", "off": "aus",
    "open": "offen", "in_progress": "in_arbeit", "done": "erledigt", "dropped": "entfaellt",
    "booked": "gebucht", "requested": "angefragt", "cancelled": "storniert", "resolved": "geklaert",
    "idea": "idee", "planning": "planung", "fixed": "fest", "travelling": "unterwegs", "after": "danach", "archive": "archiv",
    "comment": "Kommentar", "question": "Frage", "correction": "Korrektur", "addition": "Ergänzung", "answer": "Antwort", "wish": "Wunsch",
}


def parameter_zu_englisch(werkzeug):
    """interner Parametername -> englischer Name für dieses Werkzeug"""
    return {**PARAMETER, **PARAMETER_JE_WERKZEUG.get(werkzeug, {})}


def parameter_zu_intern(werkzeug):
    return {e: i for i, e in parameter_zu_englisch(werkzeug).items()}


# ---------- Werkzeugliste nach außen ----------

def _schema_aussen(x, tab):
    if isinstance(x, dict):
        neu = {}
        for k, v in x.items():
            if k == "properties" and isinstance(v, dict):
                neu[k] = {tab.get(p, p): _schema_aussen(s, tab) for p, s in v.items()}
            elif k == "required" and isinstance(v, list):
                neu[k] = [tab.get(p, p) for p in v]
            else:
                neu[k] = _schema_aussen(v, tab)
        return neu
    if isinstance(x, list):
        return [_schema_aussen(e, tab) for e in x]
    return x


# Namen, die im Fließtext als Werkzeugnamen stehen: mit Unterstrich unverwechselbar, die übrigen nur als eigenständiges Wort
_TEXT_NAMEN = [i for i in INTERN_ZU_ENGLISCH if "_" in i or i in ("ueberblick", "zeige", "suche", "varianten", "merkmale", "kategorien",
                                                                  "aufgaben", "wuensche", "rueckmeldungen")]
_TEXT_MUSTER = re.compile(r"(?<![\wäöüÄÖÜß.-])(" + "|".join(sorted(map(re.escape, _TEXT_NAMEN), key=len, reverse=True)) + r")(?![\wäöüÄÖÜß-])")


# „entscheiden“ ist auch ein deutsches Verb: als Werkzeugname nur in den Wendungen „mit/nur/with/Only entscheiden“ und „(entscheiden)“
_ENTSCHEIDEN = re.compile(r"(?:(?<=mit )|(?<=nur )|(?<=with )|(?<=Only )|(?<=\())entscheiden(?![\wäöüÄÖÜß-])")


_STRENG_NAMEN = [i for i in INTERN_ZU_ENGLISCH if "_" in i or i == "ueberblick"]
_STRENG_MUSTER = re.compile(r"(?<![\wäöüÄÖÜß.-])(" + "|".join(sorted(map(re.escape, _STRENG_NAMEN), key=len, reverse=True)) + r")(?![\wäöüÄÖÜß-])")


def namen_im_text(text, streng=False):
    """Werkzeugnamen im Text durch die Namen ersetzen, die tools/list zeigt. Eigene Texte (Anleitung, Beschreibungen) ersetzen auch
    die Namen, die zugleich deutsche Wörter sind (suche, zeige …); streng=True (Antworten, die Inhalt der Reise enthalten) nur die
    unverwechselbaren Namen mit Unterstrich und ueberblick."""
    if not isinstance(text, str):
        return text
    if streng:
        return _STRENG_MUSTER.sub(lambda m: INTERN_ZU_ENGLISCH[m.group(1)], text)
    return _ENTSCHEIDEN.sub(INTERN_ZU_ENGLISCH["entscheiden"], _TEXT_MUSTER.sub(lambda m: INTERN_ZU_ENGLISCH[m.group(1)], text))


def _text_parameter(text, tab):
    """Eigene Parameter in der Beschreibung eines Werkzeugs: nur eindeutige Wörter (kein von, nach, an, ab, bei, vor, was, art)."""
    eindeutig = [i for i, e in tab.items() if len(i) > 5 and i != e and "_" in i or i in (
        "bezug", "ziel", "quelle", "grund", "erlebt", "punkte", "eingeplant", "kommentar", "hinweis", "geprueft", "zustaendig",
        "buchungslink", "unterkuenfte", "strecken", "folge", "ausloeser", "erfordert", "siehe", "preise", "entfernen", "ergebnis",
        "kurz", "auswahl", "farbe", "frist", "stufe", "stufen", "notiz", "lesetext", "wahlstelle", "aufenthalte", "nacht", "titel")]
    if not eindeutig:
        return text
    muster = re.compile(r"(?<![\wäöüÄÖÜß.-])(" + "|".join(sorted(map(re.escape, eindeutig), key=len, reverse=True)) + r")(?![\wäöüÄÖÜß-])")
    return muster.sub(lambda m: tab[m.group(1)], text)


def _beschreibungen(x, werkzeug, tab, tiefe=0):
    if isinstance(x, dict):
        return {k: (_text_parameter(namen_im_text(v), tab) if k == "description" and isinstance(v, str) else _beschreibungen(v, werkzeug, tab, tiefe + 1))
                for k, v in x.items()}
    if isinstance(x, list):
        return [_beschreibungen(e, werkzeug, tab, tiefe + 1) for e in x]
    return x


def aussen(werkzeuge):
    """Werkzeugliste für tools/list: englische Namen, englische Property-Namen (mit required), Beschreibungen nennen die
    Namen, die der Client sieht. Die Eingabe bleibt unverändert."""
    aus = []
    for w in werkzeuge:
        intern = w["name"]
        tab = parameter_zu_englisch(intern)
        neu = copy.deepcopy(w)
        neu["inputSchema"] = _schema_aussen(neu["inputSchema"], tab)
        neu["description"] = _text_parameter(namen_im_text(neu.get("description", "")), tab)
        neu["inputSchema"] = _beschreibungen(neu["inputSchema"], intern, tab)
        neu["name"] = INTERN_ZU_ENGLISCH.get(intern, intern)
        aus.append(neu)
    return aus


# ---------- Aufruf von außen ----------

def intern_name(name):
    """Werkzeugname aus dem Aufruf -> interner Name (englisch oder deutsch gleich gültig)."""
    return NAMEN.get(name, name)


def _enum_schema(schema):
    return schema.get("enum") if isinstance(schema, dict) else None


def intern_argumente(werkzeug, args, schema=None):
    """Argumente eines Aufrufs auf interne Namen und Datenwerte bringen: Parameternamen englisch oder deutsch (gemischt erlaubt,
    der englische gewinnt bei Doppelung); Werte von Eigenschaften mit enum über ENUM_ALIAS. Nur Eigenschaften, die das Schema
    kennt, werden angefasst (freie Objekte wie merkmale oder regeln bleiben, wie sie sind)."""
    if not isinstance(args, dict):
        return args
    zu_intern = parameter_zu_intern(werkzeug)
    props = ((schema or {}).get("properties")) or {}
    neu = {}
    for k, v in args.items():
        if k in zu_intern and k not in props and zu_intern[k] in props:   # englischer Name
            neu[zu_intern[k]] = v
    for k, v in args.items():
        if k in zu_intern and k not in props and zu_intern[k] in props:
            continue
        neu.setdefault(k, v)
    for k, v in list(neu.items()):
        s = props.get(k)
        erlaubt = _enum_schema(s)
        if erlaubt and isinstance(v, str) and v not in erlaubt and v.lower() in ENUM_ALIAS and ENUM_ALIAS[v.lower()] in erlaubt:
            neu[k] = ENUM_ALIAS[v.lower()]
        elif erlaubt and isinstance(v, str) and v not in erlaubt and ENUM_ALIAS.get(v) in erlaubt:
            neu[k] = ENUM_ALIAS[v]
        elif isinstance(s, dict) and isinstance(s.get("items"), dict) and isinstance(v, list):
            neu[k] = [intern_argumente(werkzeug, e, s["items"]) if isinstance(e, dict) else e for e in v]
    return neu
