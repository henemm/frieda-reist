# Plan: Frieda Reist mehrsprachig (Deutsch und Englisch als Vorgabe)

Stand 30.10.2026. Entscheidungen: [ADR-0006](adr/0006-mehrsprachigkeit.md) (gilt, Product Owner 30.10.2026). Dieser Plan beschreibt die Arbeitspakete so, dass Agenten sie einzeln umsetzen können, jedes als eigener Pull Request mit grünen Tests. Die fertigen Aufträge je Paket liegen in `docs/auftraege/mehrsprachigkeit/` (README mit den Grundregeln, `M0.md` bis `M12.md`); dort steht auch der Stand.

## Ziel

- Die Reiseseite erscheint in der Sprache der Reise (`reise.yaml sprache`, Vorgabe `de`); ein Umschalter wechselt die Hülle (Beschriftungen, Datum, Zahl, Sortierung) im Browser, der Inhalt bleibt in der Sprache der Reise.
- Der Konnektor spricht die Sprache des Kontos: Anleitung, Werkzeugbeschreibungen, Ergebnisse, Fehler. Werkzeuge und Parameter heißen englisch, die deutschen Namen gelten als Aliase weiter.
- Kontoseiten und Mails folgen dem Konto; Kalender, Wächter-Meldungen und alles, was in Dateien der Reise geschrieben wird, folgen der Reise.
- Deutsch bleibt wörtlich wie heute; die bestehenden Tests bleiben grün. Englisch ist vollständig. Eine dritte Sprache ist eine Datei und sonst nichts: Konnektor und Seite kennen keine Sprache beim Namen (ADR-0006, Punkt 9); eine Pseudo-Sprache im Test beweist das bei jedem Lauf.
- Reiseinhalte, Datenschlüssel, Enum-Werte, ID-Präfixe, Dateinamen und die Pfade des Schreibwegs ändern sich nicht.

## Bestandsaufnahme (30.10.2026)

| Ort | Was | Umfang | Befund |
|---|---|---|---|
| `engine/vorlage.html` | Beschriftungen, Knöpfe, Meldungen, Plural, Datum, Zahl im Inline-Skript (Z. 826–4447); 10 Stellen im HTML (`lang`, `title`, Suche, Offline) | ca. 700 Literale, ca. 90 Template-Strings | Kein Templating: `bauen.py` ersetzt `/*__DATEN__*/` durch den JSON-Blob, die Seite zeichnet alles im Browser. Kleine Vorläufer eines Katalogs: `STATUS_TEXT`, `BUCHUNG_STATUS`, `RM_STATUS`, `WU_STATUS`, `AG_STATUS`, `AG_FELD`, `G` (überschreibbar per `darstellung.gruppen`). Molekül `umschalter` (Stile Z. 241) vorhanden |
| `engine/vorlage.html` | Erkennung deutschen Inhalts per Regex: `frageStand` (geklärt, erledigt, entfällt …, Z. 2689), `Auftrag|Rückmeldung|Anfrage` (1764), `^Übersicht:` (2777), `^Tag \d+` (2418, 3182), `gehzeit|dauer|länge` (1120) | 5 Stellen | Müssen sprachfest werden, sonst bricht eine englische Reise |
| `engine/vorlage.html` | Datum und Zahl von Hand: `datumText`, `datumKurz`, `dauer` (1095–1106), `WT` (2772), `toLocaleString("de-DE")` (2514), `replace(".", ",")` (1110, 1360, 1912, 2423, 2431), `localeCompare(…, "de")` (5 Stellen), Karte `lang: "de"` (4 Stellen) | ca. 20 Stellen | Auf `Intl` mit einer Locale-Variablen umstellen |
| `engine/bauen.py`, `engine/routen.py` | `manifest.json lang`, „Küste schematisch“ (911), `WOCHENTAGE` als Feld `tage[].wochentag` (routen 32, 1173), Mahnungssätze (routen 238–252), `ETAPPEN_MUSTER` „Etappe“ (46), Ebenen-Titel „Zusammenfassung“, „Eckdaten“, „Quellen“, „Prüfung“, „Karten“ (57–59) | ca. 15 Stellen | Python erzeugt kaum Seitentext; die Muster erkennen deutschen Inhalt |
| `engine/konnektor.py` | 55 Werkzeuge als Dicts (`WERKZEUGE` ab 2113, Einzelkonstanten 2220–2656, Konto 1852–2039), 258 `description`, Anleitungen `anleitung()` 2705–2793, `anleitung_frieda` 1916, `anleitung_konto` 2044, `SPRACHE` 1912, `STATUS_SATZ` 2695; Aufruf über if-Kette `werkzeug()` 2796, `ontologie_werkzeug()` 1100, `frieda_werkzeug()` 1965; Ergebnisse der Klasse `Handbuch` 381–1020 (`datum_de`, `zeit_de`); ca. 113 Rückgabetexte, davon 87 Fehler | ca. 920 Zeilen mit Prosa | Kein Framework, selbstgebautes JSON-RPC; `_mit_mail` (2685) ändert eine Beschreibung per `str.replace`. Werkzeugnamen stehen zusätzlich in `SCHREIB_WERKZEUGE` (73), `ONTOLOGIE_WERKZEUGE` (77), `ONTOLOGIE_AKTION`/`SCHREIB_AKTION`, in `schreiben.WERKZEUGE` und als Pfad `/<reise>/<werkzeug>` des Schreibwegs |
| `engine/schreiben.py` | `Ablehnung` (78) mit 253 verstreuten `raise Ablehnung(f"…")`; zentrale Feldprüfung `text_wert`/`bool_wert`/`liste_wert` (128–170); jedes Werkzeug gibt `(Titel, Text)`, beides geht an Claude **und** in den Commit; der Titel muss mit der ID beginnen (Regex im Schreiber, ca. 2812) | ca. 500 Zeilen mit Prosa | Gespeicherte Prosa: Fragestatus (1615), Verlaufsgründe (1458), `ARTEN_KOPF` (71), `KATEGORIEN_KOPF` (343) |
| `engine/rueckmeldungen.py` | ca. 53 `{"fehler": "…"}`, Prüftexte „zu lang“, `aufgaben_text()` (1185) für den Konnektor; `ARTEN` der Rückmeldungen sind deutsche Wörter als Daten und Enum (79) | ca. 140 Zeilen | Fehler erscheinen auf der Seite („Nicht angenommen: …“, vorlage 3708, 3930, 4145) und im Konnektor |
| `engine/anmeldung.py`, `engine/konten.py`, `engine/oauth.py` | Kontoseiten in Python gerendert (`lang="de"`, ca. 40 Texte), Code-Mail (250–257), Einladungsmail (663), OAuth-Fehler | ca. 60 Texte | Hängen am Konto, nicht an der Reise |
| `engine/kalender.py`, `engine/waechter.py` | iCal-Titel und -Beschreibungen (113–181, 228, 254), Meldungen (64–67, 182–245) | ca. 40 Texte | Folgen der Reise |
| `engine/reisevorlage/`, `engine/neu.py` | deutsche Startinhalte („Eckdaten“, „Zeitraum“, Spalten der offenen Fragen), `MONATE` (39) | 4 Dateien | Inhalt der Reise, den `bauen.py` und die Vorlage per Muster wiedererkennen |
| `engine/konten.py` | Tabelle `konten(id, email, name, rechte, gesperrt, angelegt)`, kein Migrationsmechanismus (`CREATE IF NOT EXISTS`) | | Neue Spalte braucht `ALTER TABLE` mit Fehlerfang |
| `engine/tests/` | Teilstring-Vergleiche auf deutsche Wörter, keine Snapshots: test_konnektor ~162, test_schreiben ~126, test_gespraech ~64, test_regeln ~38, test_oauth ~35, test_rueckmeldungen ~13; Mengenvergleiche auf Werkzeugnamen (test_konnektor 178–184, 288, 540, 615); `test_design.py` prüft die vier Stellen eines Bausteins; `test_betrieb.py` prüft die Modullisten in `deploy.sh` | ca. 440 Prüfungen | Bleiben grün, solange Deutsch wörtlich gleich bleibt und die deutschen Namen als Aliase gelten |
| Sonstiges | `FR_SPRACHEN=de,en` nur für OSM-Namen (`werkzeuge/wissen_punkte_holen.py`); kein Feld `sprache` an Reise, Konto oder Instanz; ca. 590 Nennungen von Werkzeugnamen in `docs/` und Tests | | |

## Architektur

### Katalog

```
engine/texte.py       SPRACHEN: Reihenfolge der Sprachen = Reihenfolge der Sprachdateien (de, en, …); VORGABE = "en" für Personen,
                      Reisen ohne Feld bauen mit "de" (Bestand);
                      t(sprache, schluessel, **werte) -> str; Plural: Wert n -> Kategorie über plural() der Sprachdatei ->
                      Schlüssel {schluessel}.<kategorie>, Rückfall auf .other; fehlender Schlüssel -> Rückfall auf "en",
                      dann der Schlüssel selbst (nie Absturz);
                      aus_header(accept_language) -> beste Sprache aus SPRACHEN nach q-Wert, Region abgeschnitten (de-AT -> de), sonst VORGABE;
                      datum(d, sprache), datum_kurz(d, sprache), zeit(t, sprache): Formate aus der Sprachdatei;
                      seite() -> {sprache: {name, locale, richtung, plural (als Name der CLDR-Regel), texte "seite.*"}} für alle Sprachen;
                      inhaltswoerter(schluessel) -> set der Wörter aller Sprachen (für die Inhaltserkennung)
engine/texte_de.py    NAME = "Deutsch"; LOCALE = "de-DE"; RICHTUNG = "ltr"; PLURAL = "one_other" (oder eine Funktion n -> Kategorie);
                      DATUM = "%-d.%-m.%Y"; DATUM_KURZ = "%-d.%-m."; ZEIT = "%-H:%M";
                      TEXTE = {"seite.reiter.plan": "Plan", "seite.anzahl.tage.one": "1 Tag", "seite.anzahl.tage.other": "{n} Tage", …}
engine/texte_en.py    dieselben Felder, dieselben Schlüssel
engine/tests/texte_xx.py   Pseudo-Sprache nur für Tests: NAME "Pseudo", LOCALE "ar-EG" (andere Ziffern, Richtung rtl), PLURAL mit
                      sechs Kategorien, jeder Text "[xx {original}]", abgeleitet aus texte_en.py; wird vom Test über eine
                      Umgebungsvariable FR_TEXTE_ZUSATZ als weitere Sprache geladen
```

Regeln für Schlüssel: flach, Kleinbuchstaben, Punkte als Trenner, Bereich vorn (`seite`, `konnektor`, `schreiben`, `dienst`, `konto`, `mail`, `kalender`, `waechter`, `inhalt`). Platzhalter in geschweiften Klammern mit Namen (`{name}`, `{n}`, `{id}`), nie positional. Jeder Text ist ein ganzer Satz oder eine ganze Beschriftung; nichts wird aus Teilen zusammengesetzt (`"Nacht in " + ort` wird `t("seite.tag.nacht_in", ort=…)`), damit andere Wortstellungen möglich sind. Plural immer über Kategorien (`.zero`, `.one`, `.two`, `.few`, `.many`, `.other`; Deutsch und Englisch füllen nur `.one` und `.other`), nie über `n === 1 ? … : …`. Werkzeugbeschreibungen: `konnektor.werkzeug.<interner Name>` und `konnektor.werkzeug.<interner Name>.<interner Parameter>` (interne, also deutsche Namen als Schlüssel; die Namenstabelle übersetzt beim Ausgeben). Anleitungsbausteine: `konnektor.anleitung.<baustein>`. Fehler: `schreiben.<werkzeug>.<grund>` bzw. `dienst.<grund>`.

Verboten im Code (der Literal-Test und ein Grep-Test prüfen das): `if sprache == "de"` oder ein anderes Kürzel, feste Locale-Strings (`"de-DE"`), feste Wochentags- oder Monatslisten, `one/other` als einzige Pluralfrage, eine feste Zahl von Sprachknöpfen.

In der Vorlage: `bauen.py` ersetzt `/*__TEXTE__*/null` durch `texte.seite()` (alle Sprachen, damit der Umschalter offline geht; etwa 15 KB je Sprache). Eine JS-Funktion `t(schluessel, werte)` (Atom, ADR-0002) liest aus dem Katalog der Variablen `SPRACHE`, mit `Intl.PluralRules(LOCALE).select(n)` für die Kategorie. `SPRACHE` startet mit `localStorage` (Schlüssel `SP + "sprache"`), sonst `D.sprache`; `LOCALE` und `RICHTUNG` kommen aus dem Katalogeintrag der Sprache. Der Umschalter zeigt je Sprache des Katalogs einen Knopf mit ihrem `name`, setzt `SPRACHE`, `document.documentElement.lang` und `dir`, speichert und zeichnet die Ansicht neu. Alle `Intl`-Aufrufe (`DateTimeFormat`, `NumberFormat`, `Collator`, `PluralRules`) und die Karte nutzen `LOCALE`; Abstände in neuen Stilen mit logischen Eigenschaften (`margin-inline`, `padding-inline-start`), damit `rtl` nicht kippt. Schriften: die mitgelieferten Schriften bekommen einen System-Rückfall (`system-ui`) für Zeichen, die sie nicht haben.

### Namen der Schnittstelle (ADR-0006, Punkt 4)

Eine Tabelle `NAMEN` im Konnektor bildet englische Werkzeugnamen auf die internen (deutschen) ab; `tools/list` zeigt englische Namen, `tools/call` nimmt beide. Je Werkzeug eine Tabelle der Parameternamen (englisch → intern), angewandt auf das `inputSchema` beim Ausgeben und auf die Argumente beim Aufruf (beide Namen gelten, englisch gewinnt bei Doppelung). Enum-Aliase (`chosen` → `gewaehlt`, `rejected` → `verworfen`, `replaced` → `ersetzt`, `organizer` → `organisator`, `contributor` → `mitwirkend`, `guest` → `gast`, `required`/`recommended`/`optional`/`off` → `pflicht`/`empfohlen`/`angeboten`/`aus`, `comment`/`question`/`correction`/`addition`/`answer`/`wish` → `Kommentar`/`Frage`/`Korrektur`/`Ergänzung`/`Antwort`/`Wunsch`) werden beim Aufruf auf den Datenwert abgebildet; das Schema nennt den Datenwert, die englische Beschreibung beide. Alles darunter (`werkzeug()`, `ontologie_werkzeug()`, Schreibweg, Rückmeldedienst, Dateien) sieht nur interne Namen.

| Englisch (neu, `tools/list`) | Intern und Alias |
|---|---|
| `overview` | `ueberblick` |
| `show` | `zeige` |
| `search` | `suche` |
| `open_questions` | `offene_fragen` |
| `variants` | `varianten` |
| `feedback_list` | `rueckmeldungen` |
| `feedback_give` | `rueckmeldung_geben` |
| `feedback_resolve` | `rueckmeldung_erledigen` |
| `tasks` | `aufgaben` |
| `task_create` | `aufgabe_anlegen` |
| `task_update` | `aufgabe_aendern` |
| `wishes` | `wuensche` |
| `wish_update` | `wunsch_aendern` |
| `wish_propose` | `wunsch_vorschlagen` |
| `categories` | `kategorien` |
| `category_define` | `kategorie_definieren` |
| `attributes` | `merkmale` |
| `attribute_define` | `merkmal_definieren` |
| `attribute_merge` | `merkmal_zusammenfuehren` |
| `kind_define` | `art_definieren` |
| `kinds_adopt` | `arten_uebernehmen` |
| `value_set` | `wert_eintragen` |
| `location_set` | `lage_eintragen` |
| `item_create` | `ding_anlegen` |
| `item_update` | `ding_aendern` |
| `option_create` | `option_anlegen` |
| `option_update` | `option_aendern` |
| `choice_create` | `wahlstelle_anlegen` |
| `choice_update` | `wahlstelle_aendern` |
| `decide` | `entscheiden` |
| `plan_create` | `plan_anlegen` |
| `plan_update` | `plan_aendern` |
| `day_create` | `tag_anlegen` |
| `day_update` | `tag_aendern` |
| `fixed_date_set` | `termin_setzen` |
| `question_create` | `frage_anlegen` |
| `question_answer` | `frage_beantworten` |
| `question_close` | `frage_schliessen` |
| `knowledge_write` | `wissen_schreiben` |
| `knowledge_update` | `wissen_aendern` |
| `narrative_write` | `lesetext_schreiben` |
| `booking_create` | `buchung_anlegen` |
| `booking_update` | `buchung_aendern` |
| `receipt_add` | `beleg_anlegen` |
| `person_invite` | `person_einladen` |
| `person_remove` | `person_entfernen` |
| `trip_update` | `reise_aendern` |
| `trip_status_set` | `reise_status_setzen` |
| `setting_set` | `einstellung_setzen` |
| `my_trips` | `meine_reisen` |
| `trip_create` | `reise_anlegen` |
| `trip_create_request` | `reisen_anlegen_anfragen` |
| `request_decide` | `anfrage_entscheiden` |
| `calendar` | `kalender` |
| `language_set` | `sprache_setzen` (neu, M7) |
| `frieda` | `frieda` (unverändert) |

Parameternamen: feste Wörter über alle Werkzeuge gleich übersetzen, zum Beispiel `reise` → `trip`, `ziel` → `target`, `quelle` → `source`, `geprueft` → `checked`, `gilt` → `valid_for`, `grund` → `reason`, `titel` → `title`, `art` → `kind`, `wer` → `who`, `frist` → `deadline`, `zustaendig` → `assignee`, `begriff` → `query`, `alle` → `all`, `rolle` → `role`, `von`/`bis` → `from`/`until`, `datum` → `date`, `nacht` → `night`, `strecken` → `legs`, `aufenthalte` → `stays`, `wahlstellen` → `choices`, `stufe` → `level`, `hilfe` → `help`, `frage` → `question`, `fuer` → `for`, `an` → `at`, `wann` → `when`, `sprache` → `language`. Die vollständige Tabelle entsteht in M8b aus dem Code (`inputSchema` aller Werkzeuge) und wird in `docs/konnektor.md` festgehalten.

### Wo die Sprache liegt

| Wer | Quelle | Vorgabe | Setzen |
|---|---|---|---|
| Seite (Startwert), Manifest, Kalender, Wächter-Meldungen, alles, was in Dateien der Reise geschrieben wird, Commit-Nachrichten | `reise.yaml sprache` | `de` | `trip_create` (Parameter `language`, Vorgabe: Sprache des Kontos), `setting_set` (nur Organisator:innen, mit Grund) |
| Seite (Hülle), nach dem Umschalten | `localStorage` der Person | Sprache der Reise | Umschalter auf der Seite |
| Konnektor (Anleitung, Beschreibungen, Ergebnisse, Fehler), Kontoseiten, Mails an die Person | `konten.sprache` | aus `Accept-Language` beim Anlegen des Kontos, sonst `en` | Kontoseite, Werkzeug `language_set` |
| Übergangs-Links ohne Konto (`zugaenge.json`) | Sprache der Reise | | |
| Rückmeldedienst | Feld `sprache` der Anfrage; die Seite schickt `SPRACHE`, der Konnektor die Sprache der Person | Sprache der Reise | |

### Was nie übersetzt wird

Datenschlüssel in YAML und JSON, Enum-Werte, ID-Präfixe, Dateinamen, Pfade des Schreibwegs, Namen von Arten, Merkmalen, Kategorien, Auswahlwerte, Wissen, Lesetexte, Titel, Gründe. Die `ARTEN` der Rückmeldungen („Kommentar“, „Frage“ …) bleiben als Datenwerte und Enum deutsch; englische Aliase gelten beim Aufruf.

### Eine Sprache hinzufügen (Zielbild, wird `docs/sprachen.md` in M11)

1. `engine/texte_<kürzel>.py` anlegen: `NAME`, `LOCALE`, `RICHTUNG`, `PLURAL`, `DATUM`, `DATUM_KURZ`, `ZEIT`, `TEXTE` mit allen Schlüsseln aus `texte_en.py` (der Paritätstest nennt, was fehlt).
2. Das Kürzel in `texte.SPRACHEN` eintragen und die Datei in `betrieb/deploy.sh` (KN_, RM_, SB_MODULE) aufnehmen; der Test `test_betrieb.py` prüft das.
3. Optional `engine/reisevorlage/<kürzel>/` (sonst Englisch) und `README.<kürzel>.md`.
4. Tests laufen lassen: Parität, Rundgang je Sprache (parametrisiert über `SPRACHEN`), Konnektor je Sprache. Mehr ist nicht zu tun; Umschalter, Kontoseite, `Accept-Language`, Inhaltserkennung, Kalender und Mails kennen die Sprache ab jetzt.

### Tests, die den Umbau tragen

- `test_texte.py`: Parität (gleiche Schlüssel, gleiche Platzhalter in allen Sprachen), Rückfall, Plural nach Kategorien, `aus_header` (q-Werte, Region, unbekannt → `en`), Pflichtfelder jeder Sprachdatei.
- `test_texte.py::test_pseudo_sprache`: lädt `texte_xx.py` als dritte Sprache (`FR_TEXTE_ZUSATZ`), baut die Beispielreise mit `sprache: xx`, prüft `lang="xx"`, `dir="rtl"`, markierte Texte `[xx …]`, Plural mit Kategorie `few`, Datum und Zahl der Locale; der Umschalter zeigt drei Knöpfe; `tools/list` mit Konto `sprache: xx` liefert markierte Beschreibungen. Grep-Test: kein `== "de"`, `== "en"`, `"de-DE"`, `"en-GB"` außerhalb der Sprachdateien.
- `test_texte.py::test_keine_literale_in_der_vorlage`: findet im Skript der Vorlage String-Literale mit Umlauten oder ß außerhalb von `t(…)`, Kommentaren und einer Ausnahmeliste; die Ausnahmeliste wird mit jedem Paket kürzer und ist am Ende leer. Dasselbe für `konnektor.py` (Bereich Werkzeuge und Anleitung), `schreiben.py` (`raise Ablehnung(f"`), `rueckmeldungen.py` (`"fehler":`), `anmeldung.py`, `konten.py`, `kalender.py`, `waechter.py`.
- Rundgang je Sprache: `test_seite_sprachen.py`, parametrisiert über `texte.SPRACHEN`, baut eine Kopie der Beispielreise mit `sprache: <kürzel>` und prüft im Browser (`seiten_browser.mjs` mit Parameter Sprache) Reiter, Datum (Englisch `Thu 13/5`), Zahl, Plural, Knöpfe, Offline-Hinweis, `lang`; dazu Umschalten auf der deutschen Beispielreise in jede andere Sprache und zurück, Wahl überlebt Neuladen, Inhalt bleibt deutsch.
- Konnektor: `tools/list` zeigt englische Namen; Aufrufe mit englischem und mit deutschem Namen (und gemischten Parameternamen) liefern dasselbe; mit Konto `sprache: en` sind Beschreibungen und Anleitung englisch; ein Schreibfehler kommt englisch zurück; die Datei der Reise bleibt deutsch. Vergleich der Schemata beider Sprachen ohne `description` ist identisch.

## Arbeitspakete

Jedes Paket ist ein Pull Request mit PR-Template (Prüfstelle ADR-0001) und grünen Tests (`engine/.venv/bin/python -m pytest -q engine/tests`). Modell: **Haiku** für mechanische Arbeit mit klarem Muster und Test als Leitplanke, **Sonnet** wo entschieden, umformuliert oder quer über Module gedacht werden muss. Kein Paket ändert deutsche Texte im Wortlaut (sonst fallen Tests, siehe Bestandsaufnahme); Umformulierungen sind ein eigener Schritt am Ende. Jeder Paketauftrag enthält die Liste „Was nie übersetzt wird“.

Reihenfolge: M0 → M1 → M2 → (M3, M4, M5 parallel) → M6 → M7 → M8 → M8b → (M9, M10 parallel) → M11 → M12. Die Pakete M3 bis M5 betreffen nur die Vorlage, M7 bis M10 nur Python; sie können nebeneinander laufen, solange jeder PR die Ausnahmelisten seines Bereichs pflegt.

### M0 · Katalog und Leitplanken (Haiku)

- Neu: `engine/texte.py`, `engine/texte_de.py`, `engine/texte_en.py` mit allen Feldern einer Sprache (`NAME`, `LOCALE`, `RICHTUNG`, `PLURAL`, `DATUM`, `DATUM_KURZ`, `ZEIT`, `TEXTE`; zunächst mit den schon vorhandenen Zuordnungen `STATUS_TEXT`, `BUCHUNG_STATUS`, `RM_STATUS`, `WU_STATUS`, `AG_STATUS`, `AG_FELD`, `WORT` aus konnektor und schreiben, `GRUNDFORM_WORT`, `BUCHUNG_WORTE`, `stufe_wort`); Pluralkategorien nach CLDR mit den Regeln für de und en in den Sprachdateien, `texte.plural(sprache, n)` ruft sie; `engine/tests/texte_xx.py` als Pseudo-Sprache (aus `texte_en.py` abgeleitet, Texte `[xx …]`, Locale `ar-EG`, `rtl`, Pluralregel mit sechs Kategorien), geladen über `FR_TEXTE_ZUSATZ`.
- `betrieb/deploy.sh`: die drei Module in `KN_MODULE`, `RM_MODULE`, `SB_MODULE`; `CODE_DATEIEN` in konnektor.py; ein Test prüft, dass jede Sprache aus `texte.SPRACHEN` in den drei Listen steht.
- `engine/tests/test_texte.py`: Parität, Pflichtfelder, Rückfall, Plural nach Kategorien, `aus_header`; Literal-Test mit vollständiger Ausnahmeliste (also zunächst grün); Grep-Test gegen Sprachweichen im Code (`== "de"`, feste Locale-Strings).
- `CLAUDE.md`: Regel „Sichtbare Texte stehen im Katalog in allen Sprachen, nie im Code; Werkzeug- und Parameternamen englisch mit deutschem Alias“.
- DoD: Tests grün, `test_betrieb.py` akzeptiert die Modullisten, kein Verhalten geändert.

### M1 · Sprache der Reise, Startwert der Seite, Umschalter (Haiku)

- `engine/reise.py`: Feld `sprache` (Eckdaten, erlaubt `texte.SPRACHEN`, Vorgabe `de`, Fehlermeldung bei anderem Wert); in `daten()` ausgeben; `einstellung_setzen` im Schreibweg darf es setzen (Verlauf mit Grund).
- `engine/bauen.py`: `/*__TEXTE__*/` mit allen Sprachen, `<title>`, `manifest.json lang`, „Küste schematisch“ aus dem Katalog; `WOCHENTAGE` aus routen entfernen, Wochentag in JS aus dem Datum.
- `engine/vorlage.html`: `SPRACHE`, `LOCALE`, `RICHTUNG`, `t()` als Atom mit `Intl.PluralRules`; Umschalter als Verwendung des Moleküls `umschalter` an der Stelle der Kontoleiste (Kopfkommentar, Bausteinseite, `docs/design.md`; keine neuen Stile), ein Knopf je Sprache aus dem Katalog mit ihrem `name`, verborgen, wenn der Katalog nur eine Sprache hat; Umschalten setzt `lang` und `dir`, speichert und zeichnet neu; die vorhandenen Map-Objekte lesen aus `t()`.
- DoD zusätzlich: die Pseudo-Sprache baut und zeigt drei Knöpfe (`test_pseudo_sprache`, Teil Seite).
- `engine/neu.py`, `reise_anlegen`: Parameter `sprache` (Vorgabe: Sprache des Kontos).
- Beispielreise: `sprache: de` ausdrücklich eintragen; `docs/neue-reise.md`, `docs/konnektor.md` ergänzen.
- DoD: Bau der Beispielreise unverändert bis auf die neuen Konstanten und den Umschalter; `test_design.py` grün; Umschalter wechselt vorerst nur die Map-Objekte (der Rest folgt in M3 bis M5).

### M2 · Datum, Zahl, Sortierung, Karte (Sonnet)

- `datumText`, `datumKurz`, `dauer`, `WT`, `zahl`, alle `replace(".", ",")`, alle `localeCompare` (→ `Intl.Collator(LOCALE)`), Karte `lang` auf `Intl` und `LOCALE`; Wochentags- und Monatsnamen nur noch aus `Intl.DateTimeFormat`, keine Listen. Die zwei Datumsformen aus ADR-0002 bleiben genau zwei; Deutsch ergibt dieselben Zeichenketten wie heute („Do 13.5.“, „13.5.“, „5:30 h“). Nach dem Umschalten rechnet alles mit der neuen `LOCALE`. Die Pseudo-Sprache zeigt arabisch-indische Ziffern und `rtl`; was dabei kippt, wird mit logischen CSS-Eigenschaften gerichtet.
- Auch `texte.datum()` für Python aus den Formaten der Sprachdatei (konnektor `datum_de`, `zeit_de`; schreiben, waechter, kalender nutzen es ab M9/M10).
- Test: `test_seite.py` vergleicht die deutschen Ausgaben vor und nach dem Umbau; englische Stichproben im Rundgang.

### M3 · Vorlage, Teil A: Rahmen, Reiter, Suche, Plan, Tag, Etappe (Haiku)

- Zeilenbereich ca. 804–1500 und 1900–2000 der Vorlage: alle Literale nach `t()`, Schlüssel `seite.rahmen.*`, `seite.reiter.*`, `seite.suche.*`, `seite.plan.*`, `seite.tag.*`, `seite.etappe.*`, Plural über `.one/.other`. Die statischen HTML-Texte (Suche, Offline, Aktualisieren) werden beim Start und beim Umschalten aus `t()` gesetzt.
- Ausnahmeliste im Literal-Test um diesen Bereich kürzen.
- DoD: Deutsch wörtlich gleich (Browser-Rundgang grün), Literal-Test grün, englische Schlüssel vollständig, Umschalten wechselt diesen Bereich.

### M4 · Vorlage, Teil B: Varianten, Wahlstellen, Optionen, Buchungen, Karte, Unterkunft (Haiku)

- Zeilenbereich ca. 1300–1450, 1500–1900, 2000–2600: Schlüssel `seite.wahl.*`, `seite.buchung.*`, `seite.karte.*`, `seite.unterkunft.*`, `seite.kosten.*`.
- Enthält die `confirm`/`alert`-Texte und „Nicht angenommen: “ (Fehler des Dienstes kommen ab M9 als `fehler_code` und werden hier über `t("dienst." + code)` gezeigt; bis dahin bleibt der Text des Dienstes).

### M5 · Vorlage, Teil C: Wissen, Fragen, Aufgaben, Wünsche, Rückmeldungen, Konto, Bausteinseite (Haiku)

- Zeilenbereich ca. 2600–4447: Schlüssel `seite.wissen.*`, `seite.frage.*`, `seite.aufgabe.*`, `seite.wunsch.*`, `seite.rueckmeldung.*`, `seite.konto.*`, `seite.bausteine.*` (die Erklärtexte der Bausteinseite sind lang; sie kommen als eigene Schlüssel, Deutsch wörtlich).
- Am Ende: Ausnahmeliste für die Vorlage leer; englischer Rundgang (`test_seite_en.py`) mit Umschalt-Test als neuer Test.

### M6 · Inhaltserkennung sprachfest, Reisevorlage je Sprache (Sonnet)

- `frageStand`, `Auftrag|Rückmeldung|Anfrage`, `^Übersicht:`, `^Tag \d+`, `gehzeit|dauer|länge` in der Vorlage; `ETAPPEN_MUSTER` und Ebenen-Titel in `bauen.py`; `MONATE` in `neu.py`: Wörter aus `texte.inhaltswoerter("inhalt.<…>")` aller Sprachen, als Alternation ins Muster. Der Fragestatus, den `schreiben.py` schreibt („geklärt {datum}: …“), nimmt das Wort der Reise-Sprache.
- `engine/reisevorlage/de/` (heutiger Stand) und `engine/reisevorlage/en/`; `neu.py` wählt nach `sprache`, fehlt der Ordner einer Sprache, nimmt es `en`. `reise.json` der Vorlage nennt die Überschriften passend.
- Test: `test_neu.py` legt eine englische Reise an, baut sie, die Seite erkennt Eckdaten, Überblick, Quellen und eine offene Frage mit Status „open“ / „resolved“.

### M7 · Sprache am Konto (Haiku)

- `engine/konten.py`: Spalte `sprache TEXT NOT NULL DEFAULT ''` (`ALTER TABLE` im `try`, leer heißt `texte.VORGABE`; ein Wert, den der Katalog nicht mehr kennt, zählt ebenso als Vorgabe), `_konto_dict` liefert `sprache`, Funktion `sprache_setzen(konto_id, sprache)` prüft gegen `texte.SPRACHEN`; beim Anlegen des Kontos `texte.aus_header(Accept-Language)`.
- `engine/anmeldung.py`: Kontoseite mit Auswahl der Sprache (eine Option je Eintrag in `texte.SPRACHEN`, beschriftet mit `NAME`); alle Seitentexte, `lang` und `dir` über die Sprachdatei; Anmeldeseiten vor dem Konto nach `Accept-Language`; Mails in `konten.py` (Code, Einladung) in der Sprache des Empfängers, bei Einladung unbekannter Personen in der Sprache der Reise.
- `engine/konnektor.py`: Werkzeug `sprache_setzen` (intern; englisch `language_set` ab M8b; Konto-Werkzeug, alle Rollen); `zugang` trägt `sprache`.
- Tests: `test_konten.py` (Migration auf alter Datenbank, Setzen, Vorgabe `en` ohne Header), `test_anmeldung.py` (englische Kontoseite), `test_oauth.py` unverändert.

### M8 · Konnektor: Anleitung und Beschreibungen (Haiku für die Extraktion, Sonnet für die Übersetzung)

- Schritt 1 (Haiku): alle `description` der 55 Werkzeuge und ihrer Parameter sowie die Bausteine von `anleitung()`, `anleitung_frieda`, `anleitung_konto`, `SPRACHE`, `STATUS_SATZ` in den Katalog (`konnektor.werkzeug.*`, `konnektor.anleitung.*`); `werkzeuge_fuer(zugang)` und `frieda_werkzeuge(k)` liefern eine Kopie mit Texten der Sprache (`copy.deepcopy`, dann Schlüssel einsetzen); `_mit_mail` auf eigenen Schlüssel statt `str.replace`. Deutsch wörtlich gleich; `test_konnektor.py` bleibt grün.
- Schritt 2 (Sonnet): englische Anleitung und Beschreibungen. Pflicht in jeder englischen Beschreibung: die deutschen Datenwerte erklären (Enum-Werte und ihre englischen Aliase, ID-Präfixe, `art` der Rückmeldung, Stufen). Neuer Satz in beiden Anleitungen: „Antworte in der Sprache der Person; Inhalte der Reise können in einer anderen Sprache stehen, übersetze sie beim Vorlesen, ändere sie beim Schreiben nicht.“ Die Anleitungen nennen Werkzeuge mit den Namen, die `tools/list` zeigt (ab M8b englisch; in M8 noch deutsch, über einen Schlüssel je Name, damit M8b nur die Tabelle tauscht).
- Tests: `initialize` und `tools/list` mit Konto `sprache: en` englisch; Werkzeugnamen und Schemata identisch mit Deutsch (Vergleich der Listen ohne `description`).

### M8b · Englische Namen der Schnittstelle mit deutschen Aliasen (Sonnet für die Parametertabelle, Haiku für die Umsetzung)

- Schritt 1 (Sonnet): vollständige Tabelle der Parameternamen aus allen `inputSchema` (ein Wort → immer dieselbe Übersetzung, Konflikte auflösen), Enum-Aliase; als `NAMEN`, `PARAMETER`, `ENUM_ALIAS` in `konnektor.py` und als Tabelle in `docs/konnektor.md`.
- Schritt 2 (Haiku): `tools/list` gibt Werkzeuge mit englischem Namen und englischen Property-Namen aus (`required` mit); `tools/call` übersetzt Name, Argumentnamen und Enum-Aliase auf die internen Werte, bevor `werkzeug()`/`frieda_werkzeug()` laufen; deutsche Namen und Argumente gelten weiter (gemischt erlaubt). Anleitungen und Beschreibungen nennen die englischen Namen (Schlüssel aus M8). Alle Stellen, die den Werkzeugnamen in Antworten nennen (etwa „nur mit `entscheiden`“), nutzen die Tabelle.
- Nicht anfassen: `SCHREIB_WERKZEUGE`, `ONTOLOGIE_WERKZEUGE`, `ONTOLOGIE_AKTION`, `SCHREIB_AKTION`, `schreiben.WERKZEUGE`, die Pfade des Schreibwegs, `rueckmeldungen.py`, Dateien, Commits.
- Tests: neue Prüfungen auf englische Namen in `tools/list`; je ein Aufruf englisch, deutsch, gemischt mit gleichem Ergebnis; Enum-Alias; alle bestehenden Tests mit deutschen Namen bleiben unverändert grün. `docs/konnektor.md`: Tabelle „Werkzeug“ bekommt die Spalte „Englisch (tools/list)“; die MCP-Anleitungen in `docs/konnektor.md` zeigen englische Namen.

### M9 · Fehler als Schlüssel: Schreibweg, Regeln, Rückmeldedienst (Sonnet für die Form, Haiku für die Stapel)

- Schritt 1 (Sonnet): `Ablehnung(schluessel, **werte)` mit `__str__` in der Sprache der Anfrage (`sprache` im Request des Konnektors an den Schreibweg; Vorgabe Sprache der Reise); `reise.erlaubt()` gibt `(ok, schluessel, werte)` zurück, `recht()` im Konnektor setzt den Satz; der Rückmeldedienst liefert `fehler_code` und `werte` neben dem bisherigen `fehler`; die Vorlage zeigt `t("dienst." + code, werte)`, wenn vorhanden. Antwort `(Titel, Text)` der Schreibwerkzeuge wird zu `(Titel, Text, antwort)`: `Titel` und `Text` bleiben in der Sprache der Reise (Commit, Verlauf, ID-Regex), `antwort` ist der Text für die Person in ihrer Sprache (Vorgabe: `Text`). Muster an `entscheiden` und `wert_eintragen` vorgeführt, mit Tests.
- Schritt 2 bis 5 (Haiku, je ein PR): die 253 `raise Ablehnung(f"…")` in `schreiben.py` nach Werkzeuggruppen (Dinge und Werte; Wahl und Pläne; Tage, Fragen, Wissen; Buchungen, Arten, Merkmale, Kategorien, Reise) und die 53 Fehler in `rueckmeldungen.py` auf Schlüssel umstellen; die zentralen Prüfer `text_wert`/`bool_wert`/`liste_wert` zuerst. Deutsch wörtlich gleich, `test_schreiben.py`, `test_regeln.py`, `test_rueckmeldungen.py` grün; Ausnahmelisten des Literal-Tests kürzen.
- Was in Dateien der Reise geschrieben wird (Fragestatus, Gründe, `ARTEN_KOPF`, `KATEGORIEN_KOPF`, Commit-Nachrichten), nutzt `t(reise_sprache, …)`.

### M10 · Konnektor-Ergebnisse, Kalender, Wächter (Haiku)

- `Handbuch` (konnektor 381–1020): Überschriften, Beschriftungen, Status-Wörter, `datum_de`/`zeit_de` über `t(sprache, …)` und `texte.datum()`; Bestätigungen („Eingetragen und gesichert …“, „Gespeichert als …“) und die ca. 87 Fehler des Konnektors in den Katalog; `aufgaben_text()` in `rueckmeldungen.py` bekommt die Sprache.
- `kalender.py`: Titel und Beschreibungen, `SORTEN`, Abo-Name in der Sprache der Reise (Abo über mehrere Reisen: Sprache des Kontos).
- `waechter.py`: Meldungen in der Sprache der Reise (sie landen in `meldungen.jsonl` der Reise); `routen.py` Mahnungen ebenso.
- Tests: je Modul ein englischer Stichprobentest; Deutsch unverändert.

### M11 · Dokumentation und Abschluss (Haiku)

- `docs/adr/README.md`; `docs/konnektor.md` (Sprache, `language_set`, `trip_create language`, Namenstabelle), `docs/konten.md`, `docs/betrieb.md` (deploy, Migration der Spalte), `docs/neue-reise.md` (Reisevorlage je Sprache), `docs/design.md` (`t()`, `SPRACHE`, `LOCALE`, Umschalter, Datumsformen), `docs/produkt.md` (Sprache der Reise, des Kontos, Umschalter), `docs/ontologie.md` (Feld `sprache` der Eckdaten).
- `README.en.md` (Kurzfassung: was Frieda ist, Konnektor, Seite, Lizenz) und ein Verweis im `README.md`.
- `docs/sprachen.md`: die vier Schritte „Eine Sprache hinzufügen“ (oben), die Felder einer Sprachdatei, die Pseudo-Sprache, die Verbote im Code.
- Literal-Test ohne Ausnahmen; `CLAUDE.md`-Regel endgültig.

### M12 · Abnahme (Sonnet)

- Vollständiger Testlauf, Browser-Rundgänge deutsch, englisch, umgeschaltet und mit der Pseudo-Sprache (`rtl`, fremde Ziffern, sechs Pluralkategorien), Konnektor-Gespräch deutsch und englisch gegen die Beispielreise (`test_gespraech.py` um eine englische Variante mit englischen Werkzeugnamen ergänzt), Stichprobe der englischen Texte auf Verständlichkeit und auf erklärte Datenwerte.
- Probe aufs Exempel: eine dritte echte Sprache (etwa Niederländisch oder Spanisch) nach den vier Schritten aus `docs/sprachen.md` anlegen, ohne eine andere Datei anzufassen. Geht das nicht, ist der Plan nicht fertig. Ob die Sprache dann im Repo bleibt, entscheidet der Product Owner.
- Erst danach, als eigener Schritt und eigene Entscheidung: deutsche Texte umformulieren, wo das Englische eine bessere Fassung nahelegt (betrifft bis zu 440 Teilstring-Prüfungen in den Tests).

## Aufwand (grob)

| Paket | Umfang | Modell |
|---|---|---|
| M0 | 3 neue Module, Pseudo-Sprache für Tests, Paritäts-, Literal- und Grep-Test, deploy.sh | Haiku |
| M1 | reise.py, bauen.py, Vorlage (Atom `t`, `SPRACHE`, `LOCALE`, Umschalter), neu.py, Doku | Haiku |
| M2 | ca. 20 Stellen Vorlage, texte.datum() | Sonnet |
| M3–M5 | ca. 700 Literale Vorlage, ca. 350 Schlüssel je Sprache | Haiku, drei PRs |
| M6 | 8 Muster, Reisevorlage en, neu.py | Sonnet |
| M7 | konten.py (Migration), anmeldung.py (ca. 40 Texte), Mails, Werkzeug | Haiku |
| M8 | ca. 300 Beschreibungen und Anleitung; Übersetzung | Haiku + Sonnet |
| M8b | 55 Werkzeugnamen, ca. 150 Parameternamen, Enum-Aliase, Rand des Konnektors, Doku | Sonnet + Haiku |
| M9 | Ablehnung als Schlüssel, 253 + 53 Fehler, Antwort getrennt | Sonnet + Haiku, fünf PRs |
| M10 | Handbuch-Ausgaben, ca. 90 Fehler, Kalender, Wächter | Haiku |
| M11 | Doku, README.en.md | Haiku |
| M12 | Abnahme | Sonnet |

## Risiken und Gegenmittel

- **Deutsch verändert sich unbemerkt** beim Extrahieren (Leerzeichen, Anführungszeichen, Satzzeichen). Gegenmittel: Deutsch wörtlich übernehmen; die bestehenden Teilstring-Tests schlagen sonst an; M1 vergleicht die gebaute `index.html` der Beispielreise vor und nach.
- **Englische Texte werden länger** und sprengen die Leiste unten (Reiter 40 px) oder die Schriftleiter. Gegenmittel: kurze Reiterwörter (`Plan`, `Map`, `Stays`), Prüfung im englischen Rundgang auf Umbruch; ADR-0002 bleibt.
- **Umschalten lässt Teile stehen** (statische HTML-Texte, zwischengespeicherte Beschriftungen, offene Formulare). Gegenmittel: alle Texte entstehen in Zeichenfunktionen oder in einer Funktion `beschrifte()`, die der Umschalter nach dem Neuzeichnen aufruft; der Umschalt-Test prüft jede Ansicht.
- **Inhalt und Hülle in verschiedenen Sprachen** (deutsche Reise, englische Hülle oder englisches Konto). Gegenmittel: ADR-0006 Punkt 5; die Anleitung sagt Claude, Inhalte beim Vorlesen zu übersetzen und beim Schreiben nicht zu ändern.
- **Doppelte Namen verwirren** (englisch in `tools/list`, deutsch in alten Anleitungen, Dateien und Commits). Gegenmittel: Aliase gelten immer; `docs/konnektor.md` führt beide Spalten; Antworten nennen nur den Namen aus `tools/list`.
- **Doppelte Wahrheit in Ablehnungstexten**: Deutsch im Code und im Katalog. Gegenmittel: der Literal-Test lässt am Ende keinen Satz mehr im Code zu.
- **Haiku übersetzt Datenwerte mit** (`gewaehlt` → `chosen` als gespeicherter Wert). Gegenmittel: in jedem Paketauftrag die Liste „Was nie übersetzt wird“; Tests vergleichen Schemata und Dateien zwischen den Sprachen.
- **Migration der Konten-Datenbank** auf laufenden Instanzen. Gegenmittel: `ALTER TABLE` im `try`, leer heißt Vorgabe, Test auf einer Datenbank ohne die Spalte.
- **Zwei ähnliche Sprachen verbergen Annahmen** (Plural one/other, Wortstellung, Ziffern, Richtung, Zeichensatz der Schriften), die bei der dritten Sprache brechen. Gegenmittel: Pseudo-Sprache mit absichtlich anderen Eigenschaften von M0 an in jedem Testlauf; Grep-Test gegen Sprachweichen; Probe mit einer echten dritten Sprache in M12.
- **Katalog wächst mit jeder Sprache in der Seite** (etwa 15 KB je Sprache, offline im Service Worker). Gegenmittel: akzeptabel bis etwa zehn Sprachen; darüber lädt die Seite nur die Reisesprache und die gewählte Sprache nach (nicht Teil dieses Plans).

## Nicht im Plan (Product Owner, 30.10.2026)

Übersetzung von Reiseinhalten; englische Ontologie-Schlüssel, Enum-Werte, Dateinamen oder ID-Präfixe in den Dateien (Stufe 2); englischer Code und englische Doku (Stufe 3); weitere Sprachen über Englisch hinaus (sie sind nach M0 nur eine Datei); Übersetzung von `docs/`.
