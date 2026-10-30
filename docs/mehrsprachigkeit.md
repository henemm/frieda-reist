# Plan: Frieda Reist mehrsprachig (Deutsch und Englisch als Vorgabe)

Stand 30.10.2026. Entscheidungen und offene Fragen: [ADR-0006](adr/0006-mehrsprachigkeit.md) (Entwurf). Dieser Plan beschreibt die Arbeitspakete so, dass Agenten sie einzeln umsetzen können, jedes als eigener Pull Request mit grünen Tests. Vor Paket 1 braucht es die Antworten des Product Owners auf die fünf Fragen im ADR; der Plan geht von den dort vorgeschlagenen Antworten aus.

## Ziel

- Die Reiseseite erscheint in der Sprache der Reise (`reise.yaml sprache`, Vorgabe `de`), mit Datum, Zahl und Sortierung der Locale.
- Der Konnektor spricht die Sprache des Kontos: Anleitung, Werkzeugbeschreibungen, Ergebnisse, Fehler.
- Kontoseiten, Mails, Kalender und Meldungen des Wächters folgen derselben Regel (Konto bzw. Reise).
- Deutsch bleibt wörtlich wie heute; die bestehenden Tests bleiben grün. Englisch ist vollständig. Eine dritte Sprache ist eine Datei.
- Reiseinhalte, Kennungen, Schlüssel, Werkzeugnamen und Dateinamen ändern sich nicht.

## Bestandsaufnahme (30.10.2026)

| Ort | Was | Umfang | Befund |
|---|---|---|---|
| `engine/vorlage.html` | Beschriftungen, Knöpfe, Meldungen, Plural, Datum, Zahl im Inline-Skript (Z. 826–4447); 10 Stellen im HTML (`lang`, `title`, Suche, Offline) | ca. 700 Literale, ca. 90 Template-Strings | Kein Templating: `bauen.py` ersetzt `/*__DATEN__*/` durch den JSON-Blob, die Seite zeichnet alles im Browser. Kleine Vorläufer eines Katalogs: `STATUS_TEXT`, `BUCHUNG_STATUS`, `RM_STATUS`, `WU_STATUS`, `AG_STATUS`, `AG_FELD`, `G` (überschreibbar per `darstellung.gruppen`) |
| `engine/vorlage.html` | Erkennung deutschen Inhalts per Regex: `frageStand` (geklärt, erledigt, entfällt …, Z. 2689), `Auftrag|Rückmeldung|Anfrage` (1764), `^Übersicht:` (2777), `^Tag \d+` (2418, 3182), `gehzeit|dauer|länge` (1120) | 5 Stellen | Müssen sprachfest werden, sonst bricht eine englische Reise |
| `engine/vorlage.html` | Datum und Zahl von Hand: `datumText`, `datumKurz`, `dauer` (1095–1106), `WT` (2772), `toLocaleString("de-DE")` (2514), `replace(".", ",")` (1110, 1360, 1912, 2423, 2431), `localeCompare(…, "de")` (5 Stellen), Karte `lang: "de"` (4 Stellen) | ca. 20 Stellen | Auf `Intl` mit einer Locale-Konstanten umstellen |
| `engine/bauen.py`, `engine/routen.py` | `manifest.json lang`, „Küste schematisch“ (911), `WOCHENTAGE` als Feld `tage[].wochentag` (routen 32, 1173), Mahnungssätze (routen 238–252), `ETAPPEN_MUSTER` „Etappe“ (46), Ebenen-Titel „Zusammenfassung“, „Eckdaten“, „Quellen“, „Prüfung“, „Karten“ (57–59) | ca. 15 Stellen | Python erzeugt kaum Seitentext; die Muster erkennen deutschen Inhalt |
| `engine/konnektor.py` | 54 Werkzeuge als Dicts (`WERKZEUGE` ab 2113, Einzelkonstanten 2220–2656, Konto 1852–2039), 258 `description`, Anleitungen `anleitung()` 2705–2793, `anleitung_frieda` 1916, `anleitung_konto` 2044, `SPRACHE` 1912, `STATUS_SATZ` 2695; Ergebnisse der Klasse `Handbuch` 381–1020 (`datum_de`, `zeit_de`); ca. 113 Rückgabetexte, davon 87 Fehler | ca. 920 Zeilen mit Prosa | Kein Framework, selbstgebautes JSON-RPC; `_mit_mail` (2685) ändert eine Beschreibung per `str.replace` |
| `engine/schreiben.py` | `Ablehnung` (78) mit 253 verstreuten `raise Ablehnung(f"…")`; zentrale Feldprüfung `text_wert`/`bool_wert`/`liste_wert` (128–170); jedes Werkzeug gibt `(Titel, Text)`, beides geht an Claude **und** in den Commit; der Titel muss mit der ID beginnen (Regex im Schreiber, ca. 2812) | ca. 500 Zeilen mit Prosa | Gespeicherte Prosa: Fragestatus (1615), Verlaufsgründe (1458), `ARTEN_KOPF` (71), `KATEGORIEN_KOPF` (343) |
| `engine/rueckmeldungen.py` | ca. 53 `{"fehler": "…"}`, Prüftexte „zu lang“, `aufgaben_text()` (1185) für den Konnektor; `ARTEN` der Rückmeldungen sind deutsche Wörter als Daten und Enum (79) | ca. 140 Zeilen | Fehler erscheinen auf der Seite („Nicht angenommen: …“, vorlage 3708, 3930, 4145) und im Konnektor |
| `engine/anmeldung.py`, `engine/konten.py`, `engine/oauth.py` | Kontoseiten in Python gerendert (`lang="de"`, ca. 40 Texte), Code-Mail (250–257), Einladungsmail (663), OAuth-Fehler | ca. 60 Texte | Hängen am Konto, nicht an der Reise |
| `engine/kalender.py`, `engine/waechter.py` | iCal-Titel und -Beschreibungen (113–181, 228, 254), Meldungen (64–67, 182–245) | ca. 40 Texte | Folgen der Reise |
| `engine/reisevorlage/`, `engine/neu.py` | deutsche Startinhalte („Eckdaten“, „Zeitraum“, Spalten der offenen Fragen), `MONATE` (39) | 4 Dateien | Inhalt der Reise, den `bauen.py` und die Vorlage per Muster wiedererkennen |
| `engine/konten.py` | Tabelle `konten(id, email, name, rechte, gesperrt, angelegt)`, kein Migrationsmechanismus (`CREATE IF NOT EXISTS`) | | Neue Spalte braucht `ALTER TABLE` mit Fehlerfang |
| `engine/tests/` | Teilstring-Vergleiche auf deutsche Wörter, keine Snapshots: test_konnektor ~162, test_schreiben ~126, test_gespraech ~64, test_regeln ~38, test_oauth ~35, test_rueckmeldungen ~13; `test_design.py` prüft die vier Stellen eines Bausteins; `test_betrieb.py` prüft die Modullisten in `deploy.sh` | ca. 440 Prüfungen | Bleiben grün, solange Deutsch wörtlich gleich bleibt |
| Sonstiges | `FR_SPRACHEN=de,en` nur für OSM-Namen (`werkzeuge/wissen_punkte_holen.py`); kein Feld `sprache` an Reise, Konto oder Instanz | | |

## Architektur

### Katalog

```
engine/texte.py       t(sprache, schluessel, **werte) -> str; plural über Schlüssel {schluessel}.one/.other und Wert n;
                      Rückfall auf "de", fehlender Schlüssel -> der Schlüssel selbst (nie Absturz);
                      SPRACHEN = ("de", "en"); vorgabe() aus FR_SPRACHE (instanz.wert), sonst "de";
                      datum(d, sprache), datum_kurz(d, sprache), zeit(t, sprache) ersetzen datum_de/zeit_de;
                      seite(sprache) -> dict nur der Schlüssel "seite.*" für den JSON-Blob der Vorlage;
                      inhaltswoerter(schluessel) -> set der Wörter aller Sprachen (für die Inhaltserkennung)
engine/texte_de.py    TEXTE = {"seite.reiter.plan": "Plan", "seite.anzahl.tage.one": "1 Tag", "seite.anzahl.tage.other": "{n} Tage", …}
engine/texte_en.py    TEXTE = {…dieselben Schlüssel…}
```

Regeln für Schlüssel: flach, Kleinbuchstaben, Punkte als Trenner, Bereich vorn (`seite`, `konnektor`, `schreiben`, `dienst`, `konto`, `mail`, `kalender`, `waechter`, `inhalt`). Platzhalter in geschweiften Klammern mit Namen (`{name}`, `{n}`, `{id}`), nie positional. Werkzeugbeschreibungen: `konnektor.werkzeug.<name>` und `konnektor.werkzeug.<name>.<parameter>`. Anleitungsbausteine: `konnektor.anleitung.<baustein>`. Fehler: `schreiben.<werkzeug>.<grund>` bzw. `dienst.<grund>`.

In der Vorlage: `bauen.py` ersetzt `/*__TEXTE__*/null` durch `texte.seite(sprache)`; eine JS-Funktion `t(schluessel, werte)` (Atom, ADR-0002) liest daraus, mit `Intl.PluralRules(LOCALE)` für `.one/.other`. `LOCALE` kommt aus `D.sprache` (`de-DE`, `en-GB`). Alle `Intl`-Aufrufe und `localeCompare` nutzen `LOCALE`.

### Wo die Sprache liegt

| Wer | Quelle | Vorgabe | Setzen |
|---|---|---|---|
| Seite, Service Worker, Manifest, Kalender, Wächter-Meldungen, alles, was in Dateien der Reise geschrieben wird, Commit-Nachrichten | `reise.yaml sprache` | `de` | `reise_anlegen` (Parameter `sprache`), `einstellung_setzen` (nur Organisator:innen, mit Grund) |
| Konnektor (Anleitung, Beschreibungen, Ergebnisse, Fehler), Kontoseiten, Mails an die Person | `konten.sprache` | `FR_SPRACHE` der Instanz, sonst `de`; beim Anlegen des Kontos aus `Accept-Language` | Kontoseite, Werkzeug `sprache_setzen` |
| Übergangs-Links ohne Konto (`zugaenge.json`) | Sprache der Reise | | |
| Rückmeldedienst | Header `Accept-Language` bzw. Feld `sprache` der Anfrage; die Seite schickt `D.sprache`, der Konnektor die Sprache der Person | `de` | |

### Was nie übersetzt wird

Werkzeugnamen, Parameternamen, Enum-Werte, ID-Präfixe, Dateinamen, Schlüssel in YAML, Namen von Arten, Merkmalen, Kategorien, Auswahlwerte, Wissen, Lesetexte, Titel, Gründe. Die `ARTEN` der Rückmeldungen („Kommentar“, „Frage“ …) bleiben als Datenwerte und Enum deutsch; die englische Beschreibung erklärt sie.

### Tests, die den Umbau tragen

- `test_texte.py`: Parität (gleiche Schlüssel, gleiche Platzhalter in allen Sprachen), Rückfall, Plural, `vorgabe()`.
- `test_texte.py::test_keine_literale_in_der_vorlage`: findet im Skript der Vorlage String-Literale mit Umlauten oder ß außerhalb von `t(…)`, Kommentaren und einer Ausnahmeliste; die Ausnahmeliste wird mit jedem Paket kürzer und ist am Ende leer. Dasselbe für `konnektor.py` (Bereich Werkzeuge und Anleitung), `schreiben.py` (`raise Ablehnung(f"`), `rueckmeldungen.py` (`"fehler":`), `anmeldung.py`, `konten.py`, `kalender.py`, `waechter.py`.
- Englischer Rundgang: `test_seite_en.py` baut eine Kopie der Beispielreise mit `sprache: en` und prüft im Browser (`seiten_browser.mjs` mit Parameter Sprache) Reiter, Datum (`Thu 13/5`), Zahl, Plural, Knöpfe, Offline-Hinweis, `lang="en"`.
- Konnektor: `tools/list` und `initialize` mit Konto `sprache: en` liefern englische Beschreibungen und Anleitung; ein Schreibfehler kommt englisch zurück; die Datei der Reise bleibt deutsch.

## Arbeitspakete

Jedes Paket ist ein Pull Request mit PR-Template (Prüfstelle ADR-0001) und grünen Tests (`engine/.venv/bin/python -m pytest -q engine/tests`). Modell: **Haiku** für mechanische Arbeit mit klarem Muster und Test als Leitplanke, **Sonnet** wo entschieden, umformuliert oder quer über Module gedacht werden muss. Kein Paket ändert deutsche Texte im Wortlaut (sonst fallen Tests, siehe Bestandsaufnahme); Umformulierungen sind ein eigener Schritt am Ende.

Reihenfolge: M0 → M1 → M2 → (M3, M4, M5 parallel) → M6 → M7 → (M8, M9, M10 parallel) → M11 → M12. Die Pakete M3 bis M5 betreffen nur die Vorlage, M6 bis M10 nur Python; sie können nebeneinander laufen, solange jeder PR die Ausnahmelisten seines Bereichs pflegt.

### M0 · Katalog und Leitplanken (Haiku)

- Neu: `engine/texte.py`, `engine/texte_de.py`, `engine/texte_en.py` (zunächst mit den schon vorhandenen Zuordnungen `STATUS_TEXT`, `BUCHUNG_STATUS`, `RM_STATUS`, `WU_STATUS`, `AG_STATUS`, `AG_FELD`, `WORT` aus konnektor und schreiben, `GRUNDFORM_WORT`, `BUCHUNG_WORTE`, `stufe_wort`).
- `betrieb/deploy.sh`: die drei Module in `KN_MODULE`, `RM_MODULE`, `SB_MODULE`; `CODE_DATEIEN` in konnektor.py.
- `engine/tests/test_texte.py`: Parität, Rückfall, Plural, Vorgabe; Literal-Test mit vollständiger Ausnahmeliste (also zunächst grün).
- `docs/betrieb.md`: `FR_SPRACHE`. `CLAUDE.md`: Regel „Sichtbare Texte stehen im Katalog in allen Sprachen, nie im Code“.
- DoD: Tests grün, `test_betrieb.py` akzeptiert die Modullisten, kein Verhalten geändert.

### M1 · Sprache der Reise und der Seite (Haiku)

- `engine/reise.py`: Feld `sprache` (Eckdaten, erlaubt `texte.SPRACHEN`, Vorgabe `de`, Fehlermeldung bei anderem Wert); in `daten()` ausgeben; `einstellung_setzen` im Schreibweg darf es setzen (Verlauf mit Grund).
- `engine/bauen.py`: `/*__TEXTE__*/`, `<html lang>`, `<title>`, `manifest.json lang`, „Küste schematisch“ aus dem Katalog; `WOCHENTAGE` aus routen entfernen, Wochentag in JS aus dem Datum.
- `engine/vorlage.html`: `LOCALE`, `t()` als Atom (Kopfkommentar, Stile keine, Bausteinseite ein Beispiel, `docs/design.md`); die vorhandenen Map-Objekte lesen aus `t()`.
- `engine/neu.py`, `reise_anlegen`: Parameter `sprache` (Vorgabe: Sprache des Kontos).
- Beispielreise: `sprache: de` ausdrücklich eintragen; `docs/neue-reise.md`, `docs/konnektor.md` ergänzen.
- DoD: Bau der Beispielreise unverändert (Diff der erzeugten `index.html` nur die neuen Konstanten); `test_design.py` grün.

### M2 · Datum, Zahl, Sortierung, Karte (Sonnet)

- `datumText`, `datumKurz`, `dauer`, `WT`, `zahl`, alle `replace(".", ",")`, alle `localeCompare`, Karte `lang` auf `Intl` und `LOCALE`. Die zwei Datumsformen aus ADR-0002 bleiben genau zwei; Deutsch ergibt dieselben Zeichenketten wie heute („Do 13.5.“, „13.5.“, „5:30 h“).
- Auch `texte.datum()` für Python (konnektor `datum_de`, `zeit_de`; schreiben, waechter, kalender nutzen es ab M8/M10).
- Test: `test_seite.py` vergleicht die deutschen Ausgaben vor und nach dem Umbau; englische Stichproben im Rundgang.

### M3 · Vorlage, Teil A: Rahmen, Reiter, Suche, Plan, Tag, Etappe (Haiku)

- Zeilenbereich ca. 804–1500 und 1900–2000 der Vorlage: alle Literale nach `t()`, Schlüssel `seite.rahmen.*`, `seite.reiter.*`, `seite.suche.*`, `seite.plan.*`, `seite.tag.*`, `seite.etappe.*`, Plural über `.one/.other`.
- Ausnahmeliste im Literal-Test um diesen Bereich kürzen.
- DoD: Deutsch wörtlich gleich (Browser-Rundgang grün), Literal-Test grün, englische Schlüssel vollständig.

### M4 · Vorlage, Teil B: Varianten, Wahlstellen, Optionen, Buchungen, Karte, Unterkunft (Haiku)

- Zeilenbereich ca. 1300–1450, 1500–1900, 2000–2600: Schlüssel `seite.wahl.*`, `seite.buchung.*`, `seite.karte.*`, `seite.unterkunft.*`, `seite.kosten.*`.
- Enthält die `confirm`/`alert`-Texte und „Nicht angenommen: “ (Fehler des Dienstes kommen ab M9 als `fehler_code` und werden hier über `t("dienst." + code)` gezeigt; bis dahin bleibt der Text des Dienstes).

### M5 · Vorlage, Teil C: Wissen, Fragen, Aufgaben, Wünsche, Rückmeldungen, Konto, Bausteinseite (Haiku)

- Zeilenbereich ca. 2600–4447: Schlüssel `seite.wissen.*`, `seite.frage.*`, `seite.aufgabe.*`, `seite.wunsch.*`, `seite.rueckmeldung.*`, `seite.konto.*`, `seite.bausteine.*` (die Erklärtexte der Bausteinseite sind lang; sie kommen als eigene Schlüssel, Deutsch wörtlich).
- Am Ende: Ausnahmeliste für die Vorlage leer; englischer Rundgang (`test_seite_en.py`) als neuer Test.

### M6 · Inhaltserkennung sprachfest, Reisevorlage je Sprache (Sonnet)

- `frageStand`, `Auftrag|Rückmeldung|Anfrage`, `^Übersicht:`, `^Tag \d+`, `gehzeit|dauer|länge` in der Vorlage; `ETAPPEN_MUSTER` und Ebenen-Titel in `bauen.py`; `MONATE` in `neu.py`: Wörter aus `texte.inhaltswoerter("inhalt.<…>")` aller Sprachen, als Alternation ins Muster. Der Fragestatus, den `schreiben.py` schreibt („geklärt {datum}: …“), nimmt das Wort der Reise-Sprache.
- `engine/reisevorlage/de/` (heutiger Stand) und `engine/reisevorlage/en/`; `neu.py` wählt nach `sprache`. `reise.json` der Vorlage nennt die Überschriften passend.
- Test: `test_neu.py` legt eine englische Reise an, baut sie, die Seite erkennt Eckdaten, Überblick, Quellen und eine offene Frage mit Status „open“ / „resolved“.

### M7 · Sprache am Konto (Haiku)

- `engine/konten.py`: Spalte `sprache TEXT NOT NULL DEFAULT ''` (`ALTER TABLE` im `try`, leer heißt Vorgabe), `_konto_dict` liefert `sprache` (aufgelöst über `texte.vorgabe()`), Funktion `sprache_setzen(konto_id, sprache)`; beim Anlegen des Kontos `Accept-Language` auswerten (nur Sprachen aus `texte.SPRACHEN`).
- `engine/anmeldung.py`: Kontoseite mit Auswahl der Sprache; alle Seitentexte und `lang` über `t(sprache, …)`; Mails in `konten.py` (Code, Einladung) in der Sprache des Empfängers, bei Einladung unbekannter Personen in der Sprache der Reise.
- `engine/konnektor.py`: Werkzeug `sprache_setzen` (Konto-Werkzeug, alle Rollen); `zugang` trägt `sprache`.
- Tests: `test_konten.py` (Migration auf alter Datenbank, Setzen, Vorgabe), `test_anmeldung.py` (englische Kontoseite), `test_oauth.py` unverändert.

### M8 · Konnektor: Anleitung und Beschreibungen (Sonnet für die Übersetzung der Anleitung, Haiku für die Extraktion)

- Schritt 1 (Haiku): alle `description` der 54 Werkzeuge und ihrer Parameter sowie die Bausteine von `anleitung()`, `anleitung_frieda`, `anleitung_konto`, `SPRACHE`, `STATUS_SATZ` in den Katalog (`konnektor.werkzeug.*`, `konnektor.anleitung.*`); `werkzeuge_fuer(zugang)` und `frieda_werkzeuge(k)` liefern eine Kopie mit Texten der Sprache (`copy.deepcopy`, dann Schlüssel einsetzen); `_mit_mail` auf eigenen Schlüssel statt `str.replace`. Deutsch wörtlich gleich; `test_konnektor.py` bleibt grün.
- Schritt 2 (Sonnet): englische Anleitung und Beschreibungen. Pflicht in jeder englischen Beschreibung: die deutschen Kennungen erklären (Enum-Werte, ID-Präfixe, `art` der Rückmeldung, Stufen). Neuer Satz in beiden Anleitungen: „Antworte in der Sprache der Person; Inhalte der Reise können in einer anderen Sprache stehen, übersetze sie beim Vorlesen, ändere sie beim Schreiben nicht.“
- Tests: `initialize` und `tools/list` mit Konto `sprache: en` englisch; Werkzeugnamen und Schemata identisch mit Deutsch (Vergleich der Listen ohne `description`).

### M9 · Fehler als Schlüssel: Schreibweg, Regeln, Rückmeldedienst (Sonnet für die Form, Haiku für die Stapel)

- Schritt 1 (Sonnet): `Ablehnung(schluessel, **werte)` mit `__str__` in der Sprache der Anfrage (`sprache` im Request des Konnektors an den Schreibweg; Vorgabe Sprache der Reise); `reise.erlaubt()` gibt `(ok, schluessel, werte)` zurück, `recht()` im Konnektor setzt den Satz; der Rückmeldedienst liefert `fehler_code` und `werte` neben dem bisherigen `fehler`; die Vorlage zeigt `t("dienst." + code, werte)`, wenn vorhanden. Antwort `(Titel, Text)` der Schreibwerkzeuge wird zu `(Titel, Text, antwort)`: `Titel` und `Text` bleiben deutsch bzw. in der Sprache der Reise (Commit, Verlauf, ID-Regex), `antwort` ist der Text für die Person in ihrer Sprache (Vorgabe: `Text`). Muster an `entscheiden` und `wert_eintragen` vorgeführt, mit Tests.
- Schritt 2 bis 5 (Haiku, je ein PR): die 253 `raise Ablehnung(f"…")` in `schreiben.py` nach Werkzeuggruppen (Dinge und Werte; Wahl und Pläne; Tage, Fragen, Wissen; Buchungen, Arten, Merkmale, Kategorien, Reise) und die 53 Fehler in `rueckmeldungen.py` auf Schlüssel umstellen; die zentralen Prüfer `text_wert`/`bool_wert`/`liste_wert` zuerst. Deutsch wörtlich gleich, `test_schreiben.py`, `test_regeln.py`, `test_rueckmeldungen.py` grün; Ausnahmelisten des Literal-Tests kürzen.
- Was in Dateien der Reise geschrieben wird (Fragestatus, Gründe, `ARTEN_KOPF`, `KATEGORIEN_KOPF`, Commit-Nachrichten), nutzt `t(reise_sprache, …)`.

### M10 · Konnektor-Ergebnisse, Kalender, Wächter (Haiku)

- `Handbuch` (konnektor 381–1020): Überschriften, Beschriftungen, Status-Wörter, `datum_de`/`zeit_de` über `t(sprache, …)` und `texte.datum()`; Bestätigungen („Eingetragen und gesichert …“, „Gespeichert als …“) und die ca. 87 Fehler des Konnektors in den Katalog; `aufgaben_text()` in `rueckmeldungen.py` bekommt die Sprache.
- `kalender.py`: Titel und Beschreibungen, `SORTEN`, Abo-Name in der Sprache der Reise (Abo über mehrere Reisen: Sprache des Kontos).
- `waechter.py`: Meldungen in der Sprache der Reise (sie landen in `meldungen.jsonl` der Reise); `routen.py` Mahnungen ebenso.
- Tests: je Modul ein englischer Stichprobentest; Deutsch unverändert.

### M11 · Dokumentation und Abschluss (Haiku)

- ADR-0006 von „Entwurf“ auf „gilt“ mit den Antworten des Product Owners; `docs/adr/README.md`; `docs/konnektor.md` (Sprache, `sprache_setzen`, `reise_anlegen sprache`), `docs/konten.md`, `docs/betrieb.md` (`FR_SPRACHE`, deploy), `docs/neue-reise.md` (Reisevorlage je Sprache), `docs/design.md` (`t()`, `LOCALE`, Datumsformen), `docs/produkt.md` (Sprache der Reise und des Kontos), `docs/ontologie.md` (Feld `sprache` der Eckdaten).
- `README.en.md` (Kurzfassung: was Frieda ist, Konnektor, Seite, Lizenz) und ein Verweis im `README.md`.
- Literal-Test ohne Ausnahmen; `CLAUDE.md`-Regel endgültig.

### M12 · Abnahme (Sonnet)

- Vollständiger Testlauf, Browser-Rundgänge deutsch und englisch, Konnektor-Gespräch deutsch und englisch gegen die Beispielreise (`test_gespraech.py` um eine englische Variante ergänzt), Stichprobe der englischen Texte auf Verständlichkeit und auf erklärte Kennungen.
- Erst danach, als eigener Schritt und eigene Entscheidung: deutsche Texte umformulieren, wo das Englische eine bessere Fassung nahelegt (betrifft bis zu 440 Teilstring-Prüfungen in den Tests).

## Aufwand (grob)

| Paket | Umfang | Modell |
|---|---|---|
| M0 | 3 neue Module, 1 Test, deploy.sh | Haiku |
| M1 | reise.py, bauen.py, Vorlage (Atom `t`, `LOCALE`), neu.py, Doku | Haiku |
| M2 | ca. 20 Stellen Vorlage, texte.datum() | Sonnet |
| M3–M5 | ca. 700 Literale Vorlage, ca. 350 Schlüssel je Sprache | Haiku, drei PRs |
| M6 | 8 Muster, Reisevorlage en, neu.py | Sonnet |
| M7 | konten.py (Migration), anmeldung.py (ca. 40 Texte), Mails, Werkzeug | Haiku |
| M8 | ca. 300 Beschreibungen und Anleitung; Übersetzung | Haiku + Sonnet |
| M9 | Ablehnung als Schlüssel, 253 + 53 Fehler, Antwort getrennt | Sonnet + Haiku, fünf PRs |
| M10 | Handbuch-Ausgaben, ca. 90 Fehler, Kalender, Wächter | Haiku |
| M11 | Doku, README.en.md | Haiku |
| M12 | Abnahme | Sonnet |

## Risiken und Gegenmittel

- **Deutsch verändert sich unbemerkt** beim Extrahieren (Leerzeichen, Anführungszeichen, Satzzeichen). Gegenmittel: Deutsch wörtlich übernehmen; die bestehenden Teilstring-Tests schlagen sonst an; M1 vergleicht die gebaute `index.html` der Beispielreise vor und nach.
- **Englische Texte werden länger** und sprengen die Leiste unten (Reiter 40 px) oder die Schriftleiter. Gegenmittel: kurze Reiterwörter (`Plan`, `Map`, `Stays`), Prüfung im englischen Rundgang auf Umbruch; ADR-0002 bleibt.
- **Inhalt und Hülle in verschiedenen Sprachen** (deutsche Reise, englisches Konto). Gegenmittel: ADR-0006 Punkt 5; die Anleitung sagt Claude, Inhalte beim Vorlesen zu übersetzen und beim Schreiben nicht zu ändern.
- **Doppelte Wahrheit in Ablehnungstexten**: Deutsch im Code und im Katalog. Gegenmittel: der Literal-Test lässt am Ende keinen Satz mehr im Code zu.
- **Haiku übersetzt Kennungen mit** (`gewaehlt` → `chosen` als Wert). Gegenmittel: in jedem Paketauftrag die Liste „nie übersetzen“ aus dem ADR; Tests vergleichen Schemata und Enum-Werte zwischen den Sprachen.
- **Migration der Konten-Datenbank** auf laufenden Instanzen. Gegenmittel: `ALTER TABLE` im `try`, leer heißt Vorgabe, Test auf einer Datenbank ohne die Spalte.

## Nicht im Plan

Übersetzung von Reiseinhalten; englische Werkzeugnamen; Umschalter im Browser; weitere Sprachen über Englisch hinaus (sie sind nach M0 nur eine Datei); Übersetzung von `docs/`.
