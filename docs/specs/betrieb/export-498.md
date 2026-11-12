---
entity_id: export-498
type: feature
created: 2026-11-12
updated: 2026-11-12
status: draft
workflow: alpha-498-export
version: "1.0"
tags: [datenschutz, export, konten, schreibdienst, reisespeicher, alpha, m5a]
---

# Alpha: Export der Reisen und der Angaben zur Person (#498, Meilenstein M5a)

## Approval

- [ ] Approved

## Purpose

Jede Person soll auf „Mein Konto“ mit einem Knopf alles herunterladen können, was Frieda zu ihr und ihren Reisen gespeichert hat: eine ZIP-Datei mit jeder Reise, in der sie Mitglied ist (im Dateiformat der Reise, samt Fotos und Routen), den Beiträgen und den Belegen, die sie sehen darf, und ihren Kontoangaben. Das ist das Gegenstück zum Löschen (#381): Wer geht oder nachsehen will, was gespeichert ist, bekommt seine Daten vollständig und lesbar heraus (Datenschutz der öffentlichen Alpha, #383). Der Datenschutztext darf den Export erst nennen, wenn es ihn gibt; mit dieser Spec wird er genannt.

Der Product Owner hat den Entwurf der sichtbaren Teile am 11.11.2026 freigegeben (Artefakt „Meine Daten herunterladen“). Der Wortlaut der Texte in dieser Spec ist verbindlich. Kontext und Analyse: `docs/context/export-498.md`; Bauplan und Absprachen mit #381 in den Kommentaren von #498.

## Ziel und Abgrenzung

- **Im Scope:**
  - Abschnitt „Meine Daten“ (`id="daten"`) auf Mein Konto, rechte Spalte, nach „Einstellungen“ und vor dem Linkblock; Knopf, `<details>` „Was ist drin?“, Fehlertext.
  - Neuer Zweig `aktion=export` in `POST /konto` (`engine/anmeldung.py`), der die ZIP baut und als Download antwortet.
  - Neue Schnittstelle am Schreibdienst `GET /<reise>/export` (`engine/schreiben.py`, `engine/schreiben_git.py`): liefert die Reise als ZIP, aus dem Reisespeicher oder, solange #350 noch nicht für alle Reisen durch ist, aus dem Reisen-Repo.
  - `_anmeldung` im Konnektor (`engine/konnektor.py`) kann Dateiobjekte streamen; neue Funktion `reise_export` (Aufruf des Schreibdienstes).
  - `person.json`, je Reise `reise/`, `beitraege/`, `belege/` nach den Sichtregeln der Rolle.
  - Datenschutztext: Schlüssel `recht.datenschutz.export` neu, `recht.datenschutz.folgt` ohne den Export der Reisedaten, Einfügen in `datenschutz_inhalt()`.
  - Texte in `engine/texte_de.py` und `engine/texte_en.py` (jede künftige `texte_<kürzel>.py` folgt der Regel aus `docs/sprachen.md`).
  - Tests in `engine/tests/test_export.py` (neu).
- **Nicht im Scope:**
  - **Alle Teile von #381 bleiben unangetastet:** der Linkblock (Auf allen Geräten abmelden, Konto löschen), `loeschen_seite()`, `reise_loeschen_seite()`, der Block der vorgemerkten Reisen, `konten.loeschung_*`, `recht.datenschutz.konto_loeschen`, `reise_loeschen`, `namen_freitext` und die Sicherungsfrist. Der Export liest `konten.reise_vorgemerkt(reise)` (schon vorhanden, Z. 975) und ändert nichts daran.
  - Kein halber Export: Es gibt keinen „teilweisen“ Download, keine Auswahl einzelner Reisen und keine Wiederholung nur der gescheiterten Reise. Entweder die ganze ZIP stimmt, oder die Person bekommt den Fehler.
  - Kein Wieder-Einlesen (Import) auf Frieda-Seite; die ZIP ist ein Archiv im Dateiformat der Reise, das Frieda in der Claude-App wieder einlesen kann (Satz im freigegebenen Wortlaut), aber kein neuer Importweg der Software. Getragen wird das Versprechen vom vorhandenen `reisespeicher.importieren(ordner, reise, wer)`: der Ordner `<reise>/reise/` der ZIP muss sich damit unverändert wieder einlesen lassen (Rundlauf-Test im Test Plan).
  - Kein Export für Betreiber:innen („alle Konten“), kein Export des Wartelisteneintrags (Warteliste: eigener Weg nach #382/#383), keine Aufbewahrung der Datei auf dem Server.
  - Keine Änderung am Speicherformat, am Reisespeicher (`reisespeicher.exportieren` wird nur aufgerufen), am Schreibweg für Änderungen und an den Rollen.
  - Keine Messung oder Anhebung der Proxy-Zeitgrenze (siehe Annahme, Abschnitt Fehlerverhalten).
- **Kern (ADR-0001):** Der Export betrifft Konten und Betrieb, nicht die Ontologie. Er kennt keine Art und kein Merkmal, enthält keine KI, schreibt nichts in eine Reise und überschreibt keinen Verlauf. Er liest nur.
- **Instanzen:** Nichts Instanzspezifisches: Wurzel, Ablage, Seiten, Adresse des Schreibdienstes (`KN_SCHREIBDIENST`) kommen aus den Einstellungen der Instanz. Keine echten Reisen, Namen, Pfade oder Adressen in Spec, Tests und Beispielen.

## Source

- `engine/schreiben.py`: `Dienst.do_GET` (Z. 5653; Muster `GET /<reise>/buchung/<B-id>` mit `X-Frieda-Dienst`-Prüfung per `hmac.compare_digest`, `instanz.speicherreisen()`, `EinstellungenNichtLesbar` → 503, `fehler_antwort(…, mit_ok=False)`), `Dienst._senden` (Z. 5644, nur JSON), `REISE_MUSTER` (Z. 61), `ZEIT_PRUEFUNG` (Z. 71). Der Dienst ist ein `ThreadingHTTPServer` (Z. 5722); ein langer Export blockiert andere Anfragen nicht.
- `engine/schreiben_git.py`: `git(ordner, *args, fehler, frist)` (Z. 24), `buchung_im_repo` (Z. 83; `fetch` plus Lesen von `origin/main`).
- `engine/reisespeicher.py`: `exportieren(reise, ziel, bis=None)` (Z. 519; unbekannte Reise: `KeyError` aus `_stand`, Ziel fehlt oder ist leer, sonst `FileExistsError`; Dateien aus der Ablage als Hardlink mit Modus 400, sonst Kopie; `AblageFehlt` Z. 97, `AblageFehler` Z. 105).
- `engine/konnektor.py`: `schreibdienst()` (Z. 1283), `buchung_im_repo` (Z. 1656, Aufrufmuster mit `urllib.request`), `Dienst._anmeldung` (Z. 3307, schickt `inhalt` mit `len()` und `wfile.write`), `reise_kurz` (Z. 2091).
- `engine/anmeldung.py`: `konto_seite` (Z. 858), `bearbeiten` (Z. 1174; `/konto`-POST-Zweige ab Z. 1321), `datenschutz_inhalt` (Z. 1012), `_speicherreisen` (Z. 677), `_person` (Z. 697), `ist_organisatorin` (Z. 705), `reise_titel`, Hilfen `tx`, `esc`, `karte`, `verdeckt`, `formular` (Z. 212), `antwort` (Z. 240), `weiter` (Z. 244).
- `engine/konten.py`: `konto` (Z. 352), `geraete` (Z. 447; nur Gerätename, Datum „seit“ und „zuletzt“), `mitgliedschaften` (Z. 856; `reise`, `schluessel`, `seit`), `reise_vorgemerkt` (Z. 975), `push_einstellungen` (Z. 1115), `kalender_einstellungen` (Z. 1160), `dienst_geheimnis()`.
- `engine/rueckmeldungen.py` (`rm`): `ordner(reise)` (Z. 140, liefert `None` bei vorgemerkter oder fehlender Ablage), `zustand(reise)` (Z. 174; Personen mit Schlüssel, Name, Rolle, Status), `eintraege(o)` (Z. 423), `aufgaben_lesen(o)` (Z. 500), `packstand_lesen(o)` (Z. 645), `brett_lesen(o)` (Z. 725); `einladungen_lesen` wird bewusst nicht benutzt.
- `engine/belege.py`: `liste(o, name, rolle)` (Z. 96, Sichtregeln), `datei_pfad(o, b)` (Z. 110), `lesen(o)` (Z. 66).
- `engine/texte_de.py`, `engine/texte_en.py`: `konto.export.*` (neu), `recht.datenschutz.export` (neu), `recht.datenschutz.folgt` (Z. 3538, ändern).
- `engine/tests/test_schreiben_speicher.py` (Fixture `speicher` mit beiden Beispielreisen, Hilfsklasse `Dienst`), `engine/tests/test_schreiben.py` (Git-Fixture `repo`), `engine/tests/test_anmeldung.py`, `engine/tests/test_loeschen_konto.py` (Muster für Konto-Seite und `/konto`-POST).
- `betrieb/vorlagen/nginx-konnektor.inc` (keine eigene Lesefrist, nginx-Vorgabe 60 s) und `betrieb/vorlagen/nginx-konnektor-orte.inc` (nur gelesen, siehe Annahme).

## Verhalten

### Architektur: zwei Dienste, eine Quelle je Reise

1. Mein Konto läuft im Konnektor-Dienst (systemd `ProtectHome=yes`: kein Zugriff auf das Reisen-Repo und nicht sicher auf den Reisespeicher). Reise-Ordner holt er darum vom **Schreibdienst** (`GET <KN_SCHREIBDIENST>/<reise>/export`, Geheimnis-Header). Ablage (Rückmeldungen, Aufgaben, Belege) und Kontendatenbank liegen dem Konnektor ohnehin vor (`rm.ordner`, `belege`, `konten`) und werden dort gelesen.
2. Der Konnektor baut die Gesamt-ZIP in einer `tempfile.TemporaryFile` (kein benannter Pfad, verschwindet beim Schließen) und streamt sie als Antwort. Weder die Gesamt-ZIP noch eine Reise-ZIP noch eine einzelne Datei werden je ganz in den Speicher gelesen (Kopieren in Stücken mit `shutil.copyfileobj`).

### Abschnitt „Meine Daten“ auf Mein Konto

3. `export_karte(k)` in `engine/anmeldung.py` erscheint in `konto_seite()` in der rechten Spalte **nach „Einstellungen“ und vor dem Linkblock** (kein Eingriff in Linkblock, Reise-Zeilen oder Block der vorgemerkten Reisen aus #381). Der Abschnitt hat `id="daten"` und besteht aus: Überschrift „Meine Daten“, Satz (`konto.export.hinweis`), Formular `POST /konto` mit `aktion=export` und dem leisen Knopf „Meine Daten herunterladen“, danach `<details>` „Was ist drin?“ mit vier Punkten und dem kleinen Schlusssatz. Der Abschnitt erscheint für jedes angemeldete Konto, auch ohne Reise (dann enthält die ZIP nur `person.json`).
4. Das Formular benutzt die vorhandenen Hilfen (`formular`, `verdeckt`) und damit das Herkunfts- und CSRF-Muster der übrigen `/konto`-Zweige unverändert (siehe Sicherheit). Ein GET auf `/konto` (auch mit `?aktion=export`) liefert nie eine ZIP und ändert nichts.

### Zweig `aktion=export` in `bearbeiten()`

5. Ablauf (alles in dieser Reihenfolge, nur bei Erfolg wird geantwortet; jeder Fehler vor dem ersten Antwort-Byte führt zu Punkt 22):
   1. Konto `k` ist angemeldet (sonst wie bei den anderen Zweigen Weiterleitung zur Anmeldung).
   2. `mitgliedschaften = konten.mitgliedschaften(k["id"])`, ohne die, für die `konten.reise_vorgemerkt(reise)` wahr ist (Schonfrist und entfernt: wie nicht vorhanden). Archivierte Reisen (Status „archiv“) bleiben dabei. Reisen ohne Mitgliedschaft des Kontos kommen nie vor: Es gibt keine Eingabe, die eine Reise nennt (Sicherheit).
   3. `person.json` schreiben (Punkt 8).
   4. Je Mitgliedschaft: `<reise>/reise/` (Punkt 9), `<reise>/beitraege/` (Punkt 10), `<reise>/belege/` (Punkt 11).
   5. ZIP schließen, zum Anfang zurückspulen, antworten (Punkt 6).
6. Antwort `200` mit `Content-Type: application/zip`, `Content-Disposition: attachment; filename="frieda-daten-<JJJJ-MM-TT>.zip"` (Datum UTC, rein aus Ziffern, kein Name und keine Reisekennung darin), `Cache-Control: no-store`, `Content-Length` (Länge der Datei) und den üblichen Kopfzeilen der Anmeldeseiten. Die Datei entsteht erst beim Herunterladen und wird auf dem Server nicht aufbewahrt (Punkt 26).
7. Die Reihenfolge der Reisen in der ZIP folgt `seit` der Mitgliedschaft; der Ordnername ist die Reisekennung (`REISE_MUSTER`, ASCII, kein Sonderzeichen).

### Datenformat der ZIP

```
frieda-daten-2026-11-12.zip
├── person.json
└── <reise>/                       je Mitgliedschaft, z. B. beispielreise/ und stadtwochenende/
    ├── reise/                     die ganze Reise im Dateiformat der Reise
    │   ├── reise.yaml, plan/…, wissen/…, aufgaben/… (soweit die Reise sie hat)
    │   └── fotos/…, gpx/… (wie im Speicher oder im Repo abgelegt)
    ├── beitraege/                 nur, wenn die Ablage der Reise da ist
    │   ├── aufgaben.json
    │   ├── brett.json             Wünsche
    │   ├── packstand.json         Packliste: wer hat was eingepackt
    │   └── rueckmeldungen.json
    └── belege/                    nur, wenn die Ablage da ist
        ├── belege.json            Verzeichnis der sichtbaren Belege
        └── <Dateien der Belege>   unter dem Namen aus belege.json ("datei")
```

8. **`person.json`** (UTF-8, `ensure_ascii=False`, eingerückt, `sort_keys` für Tests stabil):
   - `erstellt`: Zeitpunkt der Erstellung, ISO-8601 mit Zone `+00:00` (UTC).
   - `name`, `email`, `sprache` aus `konten.konto(kid)`; andere Felder des Kontos (Kennungen, Zähler) nicht.
   - `mitgliedschaften`: Liste je Reise ohne die vorgemerkten, mit `reise`, `titel` (aus `reise_kurz`/`reise_titel`, sonst die Kennung), `rolle` (aus `_person(...)`, bei fehlender Seite aus `reise.yaml`, sonst `"gast"`) und `seit`. Der interne Personenschlüssel steht nicht darin.
   - `geraete`: Ergebnis von `konten.geraete(kid)` (Gerätename, `seit`, `zuletzt`); nie Anmeldeschlüssel, Sitzungs-Token oder Push-Schlüssel.
   - `kalender`: `konten.kalender_einstellungen(kid)`; `push`: `konten.push_einstellungen(kid)` (ohne Endpunkte und Schlüssel der Geräte, nur die Einstellungen).
   - Keine Adressen anderer Personen und keine Einladungen.
9. **`<reise>/reise/`**: die Einträge der ZIP des Schreibdienstes, mit dem Präfix `<reise>/reise/` versehen und einzeln durchgereicht (`ZipFile.open` des Quelleintrags, `copyfileobj` in den Zieleintrag). Eintragsnamen werden geprüft: absolute Pfade, `..`-Teile, Laufwerks- oder Backslash-Pfade und Verzeichniseinträge außerhalb brechen den ganzen Export ab (Punkt 22), weil das auf eine beschädigte Quelle hindeutet. Eine Reise-ZIP ohne Eintrag ist ebenfalls ein Fehler. Die Dateien stammen unverändert aus dem Speicher beziehungsweise dem Repo; die Personenangaben in `reise.yaml` enthalten keine E-Mail-Adressen (`einladungen.json` liegt in der Ablage, nicht in der Reise) und werden nicht verändert.
10. **`<reise>/beitraege/`** (Ablage `o = rm.ordner(reise)`; ist `o` `None` oder fehlt, entfällt der Ordner `beitraege/` ganz und es gibt keinen Fehler). Name und Rolle der Person kommen aus `rm.zustand(reise)` über den Personenschlüssel der Mitgliedschaft (`_person`); fehlt der Zustand, gilt die Rolle `gast` und der Name aus dem Konto. Dateien sind JSON (UTF-8):
    - **Für jede Rolle gleich** (Organisator:in, mitwirkend, Gast): `aufgaben.json` = `rm.aufgaben_lesen(o)`, `brett.json` = `rm.brett_lesen(o)`, `packstand.json` = `rm.packstand_lesen(o)`, `rueckmeldungen.json` = `rm.eintraege(o)`, jeweils vollständig. Begründung (Abgleich mit dem Code, 12.11.2026): Die Reiseseite liefert diese vier Bestände über `api/rueckmeldungen/<reise>/{aufgaben,brett,packstand,rueckmeldungen}` jedem lesenden Mitglied ungefiltert, ohne Rollenprüfung; die Vorlage blendet sie nur nach eingeschalteten Bausteinen (`B(...)`), nicht nach Rolle. Der freigegebene Satz „Als Organisator:in alle, sonst deine eigenen und was du auf der Reiseseite siehst“ ergibt damit heute für alle Rollen denselben Inhalt. Eine eigene, strengere Filterung im Export wäre eine zweite Sichtregel neben der Seite (ADR-0003, eine Heimat) und würde der Person Daten vorenthalten, die sie ohnehin sieht. Wird die Seite später nach Rolle gefiltert, folgt der Export derselben Regel (eine gemeinsame Funktion, kein Eigenbau im Export).
    - Die Rolle wirkt im Export nur bei den Belegen (Punkt 11).
    - Der freigegebene Wortlaut `konto.export.punkt_2` bleibt unverändert und stimmt: „deine eigenen und was du auf der Reiseseite siehst“ ist heute für mitwirkende Personen und Gäste dieselbe Menge wie „alle“, weil die Seite alle Beiträge zeigt. Er beschreibt die Regel, nicht einen Filter; filtert die Seite später nach Rolle, stimmt er weiter.
    - Fehlt eine Quelldatei oder ist sie leer, entsteht die Datei mit dem leeren Grundwert der Lesefunktion (Aufgaben `{"naechste": 1, "aufgaben": []}`, sonst `{}` beziehungsweise `[]`), damit die Form der ZIP je Reise gleich ist.
    - Es gibt nie `einladungen.json`, `eingang.jsonl` im Rohformat, Sperrdateien oder Verzeichnisse der Ablage jenseits der genannten Dateien.
11. **`<reise>/belege/`**: `rm.ordner(reise)` wie oben; `bl = belege.liste(o, name, rolle)` (Sichtregeln von `belege.darf_sehen`: „alle“-Belege für jedes Mitglied; sonst Organisator:in alle, sonst nur die eigenen; Zurückgezogene nur für Organisator:innen und die hochladende Person). `belege.json` enthält diese Einträge (`{"belege": [...]}`) mit allen Feldern der Belegliste und ohne Pfade des Servers. Jede Datei wird aus `belege.datei_pfad(o, b)` gestreamt nach `<reise>/belege/<b["datei"]>`. Der Dateiname wird wie bei den Reiseeinträgen geprüft (nur Name, kein Pfad); fehlt eine Datei oder ist sie nicht lesbar, ist das ein Fehler (Punkt 22), kein stilles Auslassen. Gibt es keine sichtbaren Belege, entsteht `belege.json` mit leerer Liste.
12. **Andere Personen** erscheinen in der ZIP nur mit ihrem Namen (in `reise.yaml`, Rückmeldungen mit Namen, Wünschen, Belegen mit `wer`), nie mit einer E-Mail-Adresse. Die Software liest dafür keine Adresse anderer Konten; ein Test sucht die ganze ZIP nach den Adressen aller Testkonten ab (Sicherheit).

### Schnittstelle des Schreibdienstes: `GET /<reise>/export`

13. Neuer Zweig in `Dienst.do_GET`, **nur lesend**, ohne die Sperre des Schreibwegs. Prüfungen in dieser Reihenfolge:
    1. Pfad `/<reise>/export` (zwei Teile, zweiter Teil `export`).
    2. Header `X-Frieda-Dienst` gleich `konten.dienst_geheimnis()` (`hmac.compare_digest`, auch bei fehlendem Header), sonst `403` mit `fehler_antwort("schreiben.dienst.nur_konnektor", mit_ok=False)` (Muster Buchungs-GET). Die Prüfung steht **vor** jeder Aussage über die Reise: Ohne Geheimnis ist die Antwort für bekannte und unbekannte Reisen gleich.
    3. `REISE_MUSTER` passt nicht → `404` (`schreiben.dienst.unbekannt`).
    4. `konten.reise_vorgemerkt(reise)` wahr (vorgemerkt oder entfernt) → `404` (nicht 410): Eine gelöschte Reise verrät nichts. Die Prüfung läuft vor dem Zugriff auf Speicher und Repo.
    5. `instanz.speicherreisen()`; `EinstellungenNichtLesbar` → `503` mit `schreiben.dienst.einstellungen_nicht_lesbar` (#361), Meldung auf stderr wie bei der Buchung.
    6. **Speicherweg** (Reise in `speicherreisen()`): `tempfile.TemporaryDirectory()`, darin `reisespeicher.exportieren(reise, <tmp>/reise)`; danach wird der Ordner in eine `tempfile.TemporaryFile` gezippt (`zipfile.ZIP_DEFLATED`, Pfade relativ zum Reiseordner, Dateien einzeln mit `ZipFile.write` im Streaming-Modus, nie als Bytes im Speicher; Dateien aus der Ablage sind Hardlinks mit Modus 400 und werden nur gelesen). Das Aufräumen des Temp-Ordners muss auch bei Modus 400 gelingen (der Ordner gehört dem Dienst; ein Test deckt das ab). `KeyError` (Reise im Speicher unbekannt) → `404`. `AblageFehlt`, `AblageFehler`, `sqlite3.Error`, `OSError` → `503` mit `schreiben.dienst.speicher_nicht_erreichbar` (Meldung auf stderr gekürzt, nichts Inhaltliches an die Person). `ValueError`/`FileExistsError` aus `exportieren` sind Programmfehler und ebenfalls `503`.
    7. **Repo-Weg** (Reise nicht in `speicherreisen()`): `schreiben_git.reise_archiv(s, reise, datei)`: `git fetch -q origin main` (Frist 20 s), `git ls-tree origin/main reisen/<reise>`: leer → `None` → `404`; sonst `git archive --format=zip -o <datei> origin/main:reisen/<reise>` (Frist `ZEIT_EXPORT`). Das Archiv enthält die Dateien relativ zum Reiseordner; Fotos und GPX kommen echt mit (kein LFS im Einsatz, geprüft). Fehlt `s.wurzel/.git` oder scheitert Git (`RuntimeError`, `subprocess.TimeoutExpired`) → `503` mit `schreiben.dienst.repo_nicht_erreichbar`.
    8. Erfolg: `200`, `Content-Type: application/zip`, `Content-Length` per `os.fstat(...).st_size`, `Cache-Control: no-store`, Inhalt in Stücken (1 MiB) über den neuen Helfer `Dienst._datei_senden(code, datei, typ)` (`shutil.copyfileobj`, Datei im `finally` schließen, auch bei abgebrochener Verbindung). Der Helfer sendet kein JSON; `_senden` bleibt unverändert.
14. Die Antwort enthält nie Kontodaten, nie Pfade des Servers und nie Namen anderer Reisen. Die Fehlerantworten sind JSON wie bei der Buchung.
15. **Frist:** `ZEIT_EXPORT = 50` Sekunden gilt nur für den Git-Weg, als Gesamtfrist für `fetch` (höchstens 20 s) und `archive` zusammen (die Restzeit nach `fetch` ist die Frist für `archive`). Der Speicherweg ist lokal und hat keine eigene Abbruchlogik; seine Dauer wird allein durch das Budget des Konnektors (Punkt 24, 55 s, als Timeout des Abrufs) begrenzt. Beide Fristen liegen bewusst unter der Proxy-Zeitgrenze (Punkt 25); sie dürfen nicht `ZEIT_PRUEFUNG` (3 s) sein. Ein Test hält `ZEIT_EXPORT < Budget < 60` fest.

### Konnektor: Aufruf und Streaming

16. Neue Funktion `reise_export(reise, datei)` in `engine/konnektor.py` (Muster `buchung_im_repo`): ohne `schreibdienst()` (leer = nicht eingerichtet) → `(False, fehler)`; `urllib.request` mit Header `X-Frieda-Dienst`, Kopie der Antwort in `datei` in Stücken (`shutil.copyfileobj`), Zeitgrenze je Aufruf = Rest des **Gesamtbudgets von 55 Sekunden** des Exports (Punkt 24), nie länger. Rückgabe `(True, None)`; bei `HTTPError 404` → `("fehlt", None)` (die Reise wird übersprungen, wie nicht vorhanden); jeder andere Fehler (andere Codes, `URLError`, `OSError`, Zeitüberschreitung, Antwort ist keine ZIP oder bricht ab) → `(False, fehler)`. Eine unvollständig empfangene Datei wird nie weiterverarbeitet.
17. **Einsetzbarer Abruf (ohne Zirkelimport):** `engine/anmeldung.py` importiert den Konnektor nicht (er importiert `anmeldung`). Darum hat `anmeldung.py` eine **Modulvariable `reise_exportieren`** (Vorgabe: `None`, dann „nicht eingerichtet“ = Fehler nach Punkt 22), die `konnektor.py` beim Start setzt (wie `reise_info`/`reise_kurz` übergeben werden: `anmeldung.reise_exportieren = reise_export`). Tests setzen eine eigene Funktion mit gleicher Signatur `(reise, datei) -> (True|"fehlt"|False, fehler)` ein. Die Funktion wird in `bearbeiten()` über die Modulvariable aufgerufen, nie über einen Import.
18. **`_anmeldung` für Dateiobjekte:** `anmeldung.bearbeiten` darf als `inhalt` entweder `bytes` (wie bisher, Verhalten unverändert) oder ein **Dateiobjekt** liefern (erkennbar daran, dass es kein `bytes` ist und `read` hat). `Dienst._anmeldung` setzt dann `Content-Length` per `os.fstat(inhalt.fileno()).st_size`, schreibt nach `end_headers()` mit `shutil.copyfileobj(inhalt, self.wfile, 1024 * 1024)` (nie `inhalt.read()` ganz) und schließt das Objekt im `finally`, auch bei `BrokenPipeError`/`ConnectionResetError` und bei `HEAD` (dann ohne Inhalt, aber geschlossen). Die Kopfzeilen (`Cache-Control`, `X-Content-Type-Options`, `Referrer-Policy`, `Content-Security-Policy`) bleiben dieselben; `oauth.bearbeiten` bleibt unverändert (Bytes). Alle bestehenden Anmeldeseiten verhalten sich byteweise wie bisher (Test).

### Texte

19. Alle sichtbaren Texte stehen im Katalog (`engine/texte_de.py` **und** `engine/texte_en.py`, nie im Code, ADR-0006). Schlüssel und **verbindlicher deutscher Wortlaut** (freigegebener Entwurf vom 11.11.2026):

| Schlüssel | Deutsch (wörtlich) |
|---|---|
| `konto.export.titel` | Meine Daten |
| `konto.export.hinweis` | Lade alles herunter, was Frieda zu dir und deinen Reisen gespeichert hat: eine Datei mit jeder Reise, in der du dabei bist, und deinen Kontoangaben. |
| `konto.export.knopf` | Meine Daten herunterladen |
| `konto.export.was_drin` | Was ist drin? |
| `konto.export.punkt_1` | Je Reise ein Ordner mit der ganzen Reise: Tage, Pläne, Unterkünfte, Buchungen, Wissen, Fotos und Routen (GPX). Frieda kann sie daraus wieder einlesen. |
| `konto.export.punkt_2` | Die Beiträge der Reise: Aufgaben, Wünsche, Packliste und Rückmeldungen. Als Organisator:in alle, sonst deine eigenen und was du auf der Reiseseite siehst. |
| `konto.export.punkt_3` | Die Belege, die du sehen darfst. |
| `konto.export.punkt_4` | Deine Kontoangaben: Name, E-Mail-Adresse, Sprache, deine Reisen mit Rolle, deine Geräte und deine Einstellungen für Kalender und Benachrichtigungen. |
| `konto.export.andere` | Andere Personen stehen darin nur mit ihrem Namen, ohne E-Mail-Adresse. Auch archivierte Reisen sind dabei. |
| `konto.export.fehler` | Export gerade nicht möglich. Bitte versuche es in ein paar Minuten noch einmal. |
| `recht.datenschutz.export` | Unter „Mein Konto“ kannst du jederzeit alles herunterladen, was Frieda zu dir speichert: deine Kontoangaben und jede Reise, in der du Mitglied bist, mit Fotos, Routen und den Belegen, die du sehen darfst. Die Datei entsteht beim Herunterladen und wird auf dem Server nicht aufbewahrt. |
| `recht.datenschutz.folgt` (geändert) | Noch nicht eingebaut, das folgt (ohne festen Termin): Löschen und Export eines Eintrags auf der Warteliste. |

    `konto.export.fehler` ist im Entwurf mit freiem Wortlaut („Export gerade nicht möglich“, Muster vorhandener Fehler); der zweite Satz ist vom Tech Lead festgelegt und damit ebenfalls verbindlich (Hilfe zum Weitermachen, kein technisches Wort).
20. **Englisch** (`texte_en.py`, sinngleich, ohne Fachjargon; der Wortlaut ist keine Produktentscheidung, `test_texte.py` prüft nur, dass die Schlüssel da sind):
    - `konto.export.titel`: My data
    - `konto.export.hinweis`: Download everything Frieda has stored about you and your trips: one file with every trip you are part of, and your account details.
    - `konto.export.knopf`: Download my data
    - `konto.export.was_drin`: What is included?
    - `konto.export.punkt_1`: One folder per trip with the whole trip: days, plans, stays, bookings, knowledge, photos and routes (GPX). Frieda can read it in again from there.
    - `konto.export.punkt_2`: The contributions to the trip: tasks, wishes, packing list and feedback. As an organiser, all of them; otherwise your own and whatever you see on the trip page.
    - `konto.export.punkt_3`: The receipts you are allowed to see.
    - `konto.export.punkt_4`: Your account details: name, email address, language, your trips with your role, your devices and your settings for calendar and notifications.
    - `konto.export.andere`: Other people appear in it only by name, without an email address. Archived trips are included, too.
    - `konto.export.fehler`: Export is not possible right now. Please try again in a few minutes.
    - `recht.datenschutz.export`: Under “My account” you can download everything Frieda stores about you at any time: your account details and every trip you are a member of, with photos, routes and the receipts you are allowed to see. The file is created when you download it and is not kept on the server.
    - `recht.datenschutz.folgt`: Not built yet, this will follow (no fixed date): deleting and exporting an entry on the waiting list.
    Die Schreibweise („organiser“, „receipts“) folgt den vorhandenen englischen Texten des Katalogs (zuerst nachsehen: „Beleg“, „Mein Konto“, „Organisator:in“ sind dort schon übersetzt und werden übernommen, nicht neu erfunden).
21. **Datenschutztext:** In `datenschutz_inhalt()` steht `recht.datenschutz.export` im Rechte-Block **nach** `recht.datenschutz.reise_loeschen`/`namen_freitext` und **vor** `recht.datenschutz.folgt` (also hinter den von #381 stammenden Absätzen, vor dem Rest; Zeilen von #381 bleiben unverändert). Der Satz „und der Export deiner Reisedaten“ entfällt aus `folgt` (de und en); es bleibt „Löschen und Export eines Eintrags auf der Warteliste“. Die Tests zum Datenschutztext (`test_rechtliches.py`) und `test_texte.py` (Ausnahmelisten nur kürzer) bleiben grün; der Text sagt nur zu, was es gibt (kein Wort über Aufbewahrung der Datei).

### Fehlerverhalten

22. **Kein halber Export.** Scheitert irgendetwas vor dem ersten Antwort-Byte, wird die temporäre ZIP geschlossen (damit gelöscht) und die ganze Antwort ist die Seite Mein Konto (`konto_seite(k, reise_info, meldung=tx("konto.export.fehler"), offen="daten")`, Status 200 wie bei den anderen Fehlern dieser Seite) mit dem Fehlertext. Das gilt für: Schreibdienst nicht eingerichtet oder nicht erreichbar, jeder Code außer 200 und 404, Zeitüberschreitung, abgebrochene oder ungültige ZIP, Eintragsnamen, die aus dem Ordner führen, fehlende oder unlesbare Belegdatei, `OSError` beim Lesen der Ablage oder beim Schreiben der temporären Datei (Platte voll), `sqlite3.Error` der Kontendatenbank.
23. **404 des Schreibdienstes** (Reise inzwischen vorgemerkt, entfernt oder unbekannt) heißt: diese Reise wird ausgelassen (wie nicht vorhanden), der Export der anderen Reisen läuft weiter. Das ist kein Teilexport im Sinne von Punkt 22, weil die Reise für die Person nicht mehr existiert. Eine Mitgliedschaft in einer Reise, die der Dienst nie kannte, ist darum kein Fehler; nur `404` zählt so, nie ein anderer Code.
24. **Zeitbudget:** Der ganze Export hat ein Budget von **55 Sekunden** (`time.monotonic()` ab Beginn von Punkt 5). Jeder Abruf beim Schreibdienst und die Kopierschleifen prüfen den Rest; ist es aufgebraucht, gilt Punkt 22. So kommt die Person zu einer verständlichen Fehlerseite, bevor der Webserver (nginx) die Verbindung abbricht.
25. **Annahme Proxy-Zeitgrenze:** `nginx-konnektor.inc` setzt für `/konto` keine eigene Lesefrist; es gilt die nginx-Vorgabe `proxy_read_timeout 60s` (Wartezeit zwischen zwei Lesevorgängen von der Antwort des Dienstes, die erste Antwortbytes kommen erst, wenn die ZIP fertig ist) und gepufferte Antworten. Annahme: Eine Reise mit Fotos von rund 100 MB ist unter 55 Sekunden gebaut und kopiert (lokale Hardlinks und lokale Kopien, kein Netz außer Loopback). Nach dem Ausliefern wird das an der eigenen Testreise der Instanz gemessen und im Issue #498 festgehalten. Reicht die Zeit nicht, ist die Maßnahme eine eigene Änderung (eigener nginx-Ort mit längerer Lesefrist oder Erstellen im Hintergrund mit Abholen), nicht Teil dieser Spec; der Nutzer sieht dann den Fehlertext, nie eine kaputte Datei.
26. **Aufräumen:** Alle temporären Dateien und Ordner (Reise-ZIPs, Gesamt-ZIP, Temp-Ordner des Speicherwegs) sind `TemporaryFile`/`TemporaryDirectory` und verschwinden mit dem Schließen, auch im Fehlerfall (`try/finally`). Der Export schreibt nirgends sonst auf die Platte (nicht in Ablage, Seiten, Speicher oder Repo) und ändert keine Daten (kein Verlaufseintrag, keine Meldung, keine Mail). Fehler werden gekürzt auf stderr protokolliert (`Error export …`), ohne Inhalt der Daten und ohne Adressen.

### Sicherheit

27. **Keine fremden Reisen:** Die einzige Quelle der Reisen ist `konten.mitgliedschaften(k["id"])` des angemeldeten Kontos. Das Formular nimmt keine Reisekennung, keinen Pfad und keine Kennung entgegen; zusätzliche Felder im POST werden ignoriert. Im Schreibdienst gilt: ohne Geheimnis nichts (403), nur `REISE_MUSTER`-Namen, vorgemerkte und entfernte Reisen 404.
28. **Keine fremden E-Mail-Adressen:** `person.json` enthält nur die Adresse der angemeldeten Person. Die ZIP enthält nie `einladungen.json` und liest keine Tabellen mit Adressen anderer Konten. Wo Reisedaten Namen anderer Personen tragen (Personen, Rückmeldungen, Wünsche, Belege), steht nur der Name.
29. **Herkunft/CSRF wie die anderen `/konto`-Zweige:** Der Export ist ein `POST /konto` mit demselben Herkunfts-/Formularschlüssel-Schutz wie `alle_abmelden` und `loeschen` (SameSite-Cookie `__Host-frieda`, Prüfung von `Origin`/`Referer` und Formularfeld in `bearbeiten()`; der Zweig steht hinter diesen Prüfungen und nicht davor). Ein GET löst nichts aus. Die Antwort trägt `Cache-Control: no-store`.
30. **Begrenzung:** Wie jeder `/konto`-Aufruf fällt der Export unter die Begrenzung des Webservers (30 Anfragen/Minute je Adresse). Zusätzlich lässt `bearbeiten()` je Konto nur einen Export zugleich zu (einfacher Zähler im Prozess, Sperre mit Frist null): ein zweiter gleichzeitiger Export desselben Kontos bekommt `konto.export.fehler`. So können wiederholte Klicks den Dienst nicht beliebig belasten.
31. **Inhalt der ZIP ist Nutzdaten:** keine Server-Pfade, keine Geheimnisse (Dienstgeheimnis, Anmeldeschlüssel, Push-Schlüssel) und keine internen Namen von Konten. Ein Test sucht die ZIP nach dem Dienstgeheimnis, dem Wurzelpfad der Instanz und den Adressen fremder Konten ab.

## Was darf sich nicht ändern

- Der Linkblock, die Löschseiten und der Block der vorgemerkten Reisen auf Mein Konto (#381) sind byteweise gleich wie vorher (Test: Teil der Seite zwischen den Markern vor und nach dem neuen Abschnitt, oder Vergleich der Seite ohne den Abschnitt).
- Alle bestehenden Anmeldeseiten und OAuth-Antworten: gleiche Kopfzeilen, gleiche Längen, gleicher Inhalt (`_anmeldung` mit `bytes` unverändert).
- Der Reisespeicher bleibt nur anhängend; `reisespeicher.exportieren` wird nicht verändert. Der Export legt weder Dateien in Speicher noch Ablage an.
- Der Schreibweg (POST) und `GET /gesund`, `GET /<reise>/buchung/<B-id>` verhalten sich unverändert.
- `deploy.sh`: kein neues Modul, die Liste der Dienst-Module bleibt (ein vorhandener Test prüft sie).
- Beide Beispielreisen (`beispiel/reisen/beispielreise`, `beispiel/reisen/stadtwochenende`) funktionieren; nichts nimmt eine Wanderung als Regelfall an (Stadtwochenende hat keine Routen oder GPX, der Export muss auch damit vollständig sein).

## Test Plan

Datei `engine/tests/test_export.py`. Nur erfundene Konten und Adressen (Ida und Karl in `beispielreise`; Tom und Lea in `stadtwochenende`; ein drittes, fremdes Konto ohne Mitgliedschaft), Mails über `FR_MAIL_DATEI`, eigene Datenbanken je Test, beide Beispielreisen parametrisiert. Speicherweg über das Fixture `speicher` (aus `test_schreiben_speicher.py`), Repo-Weg über das Git-Fixture `repo` (aus `test_schreiben.py`), der Schreibdienst im Thread, die ZIP-Abfrage mit `urllib` und `zipfile` (die Hilfsklasse `Dienst` liefert JSON; für ZIP eine eigene Abfrage).

Schreibdienst:
- [ ] GIVEN eine Speicherreise (beide Beispielreisen) WHEN `GET /<reise>/export` mit Geheimnis THEN `200`, `application/zip`, `Content-Length` stimmt, ZIP gültig (`testzip()`), enthält die Dateien des Stands wie `reisespeicher.exportieren` (Namensliste und Inhalt gleich, inklusive ausgelagerter Fotos oder GPX, soweit die Reise sie hat).
- [ ] GIVEN eine Reise nur im Reisen-Repo (Git-Fixture) WHEN `GET /<reise>/export` THEN `200` und die ZIP enthält den Inhalt von `reisen/<reise>/` von `origin/main` (Namensliste, Inhalt), ohne Präfix.
- [ ] GIVEN fehlendes oder falsches Geheimnis WHEN `GET /<reise>/export` (bekannte und unbekannte Reise) THEN `403` mit derselben Antwort.
- [ ] GIVEN eine unbekannte Reise (Speicher und Repo), eine nach `REISE_MUSTER` ungültige Kennung, eine vorgemerkte und eine entfernte Reise (`konten.reise_vorgemerkt` wahr) WHEN `GET /<reise>/export` THEN `404`, bei der vorgemerkten ohne Zugriff auf den Speicher (mit `reisespeicher.exportieren` als Spion, nicht aufgerufen).
- [ ] GIVEN unlesbare Instanz-Einstellungen (`EinstellungenNichtLesbar`) THEN `503` mit Schlüssel `schreiben.dienst.einstellungen_nicht_lesbar`; GIVEN `AblageFehlt` oder `sqlite3.Error` im Speicherweg THEN `503` `speicher_nicht_erreichbar`; GIVEN `git`-Fehler oder Zeitüberschreitung THEN `503` `repo_nicht_erreichbar`.
- [ ] GIVEN eine ZIP mit Hardlinks (Modus 400) im Speicherweg WHEN der Aufruf zu Ende ist THEN existiert kein Temp-Ordner mehr und keine Fehlermeldung wegen Modus 400.
- [ ] GIVEN eine große Datei (z. B. 50 MB, erzeugt im Test) WHEN exportiert wird THEN bleibt der Speicherverbrauch des Dienstes unter einer Schranke (kein `read()` der ganzen Datei; Quelltext-/`tracemalloc`-Test) und die Antwort stimmt in Länge und Prüfsumme.
- [ ] GIVEN `GET /<reise>/buchung/<B-id>` und `GET /gesund` THEN unverändert (Regression).

Konnektor und `_anmeldung`:
- [ ] GIVEN `anmeldung.bearbeiten` liefert ein Dateiobjekt WHEN `_anmeldung` antwortet THEN `Content-Length` stimmt, der Inhalt kommt vollständig an, das Objekt ist danach geschlossen, auch bei abgebrochener Verbindung und bei `HEAD`.
- [ ] GIVEN Bytes als Inhalt THEN alle bisherigen Seiten (`/anmelden`, `/konto`, `/datenschutz`, OAuth) antworten wie zuvor (Kopfzeilen und Länge).
- [ ] GIVEN `reise_export` und ein Schreibdienst im Thread THEN `(True, None)` bei 200, `("fehlt", None)` bei 404, `(False, …)` bei 403/503/`URLError`/Zeitüberschreitung/abgebrochener Antwort; ohne `schreibdienst()` `(False, …)`.
- [ ] GIVEN der Konnektor-Start THEN `anmeldung.reise_exportieren` ist gesetzt (`reise_export`); `anmeldung.py` importiert `konnektor` nicht (Quelltext-Test).

Mein Konto und ZIP (Abruf durch eingesetzte Funktion oder echten Schreibdienst im Thread):
- [ ] GIVEN ein angemeldetes Konto mit Mitgliedschaft in `beispielreise` WHEN `POST /konto aktion=export` THEN `200`, `application/zip`, `Content-Disposition: attachment; filename="frieda-daten-<heute UTC>.zip"`, `Cache-Control: no-store`; die ZIP enthält `person.json` und `beispielreise/reise/…`, `beispielreise/beitraege/…`, `beispielreise/belege/belege.json`; dasselbe für `stadtwochenende` (Tom/Lea), auch ohne Routen.
- [ ] GIVEN `person.json` THEN enthält es Name, E-Mail, Sprache, Mitgliedschaften (`reise`, `titel`, `rolle`, `seit`), Geräte, Kalender und Push-Einstellungen; keine Schlüssel, keine Token, keine Adresse einer anderen Person.
- [ ] GIVEN ein Konto mit Mitgliedschaft in beiden Reisen (eine davon archiviert) THEN sind beide Ordner in der ZIP; GIVEN eine vorgemerkte oder entfernte Reise THEN fehlt sie; GIVEN eine Reise ohne Mitgliedschaft (fremde Reise im Speicher) THEN fehlt sie in jedem Fall, auch bei manipuliertem Formular (zusätzliche Felder wie `reise=` werden ignoriert).
- [ ] GIVEN ein Konto ohne Reise THEN enthält die ZIP nur `person.json`.
- [ ] GIVEN Organisator:in und mitwirkende Person derselben Reise (Rückmeldungen, Aufgaben, Packstand von beiden, Wünsche, Belege mit `sichtbar` „alle“ und „beteiligte“, ein zurückgezogener Beleg) THEN enthalten `beitraege/` bei allen Rollen dieselben vier vollständigen Dateien (wie die Reiseseite sie jedem Mitglied liefert); `belege/` enthält bei der Organisator:in alle Belege, bei mitwirkender Person und Gast nur die, die `belege.liste` für sie liefert (ein zurückgezogener fremder Beleg fehlt).
- [ ] GIVEN eine Reise ohne Ablage (`rm.ordner` ist `None`) THEN nur `reise/` ohne `beitraege/` und `belege/`, kein Fehler.
- [ ] GIVEN Konten fremder Personen mit Adressen (Mitglieder derselben Reise, Eingeladene in `einladungen.json`) THEN kommt keine dieser Adressen und kein Wert der Datei `einladungen.json` irgendwo in der ZIP vor (Suche über alle Einträge, auch in `reise.yaml`), ebenso nicht das Dienstgeheimnis und der Wurzelpfad.
- [ ] GIVEN eine Datei ≥ 50 MB in Reise und Beleg THEN Streaming: kein Schritt liest sie ganz in den Speicher (Quelltext-Test: kein `.read()` ohne Größe auf Datei-Einträgen im Exportpfad), ZIP ist vollständig und gültig.
- [ ] GIVEN ein Export einer Speicherreise (beide Beispielreisen) THEN lässt sich der Ordner `<reise>/reise/` der ZIP mit `reisespeicher.importieren` als neue Reise in einen leeren Speicher einlesen, und deren erneuter Export ist inhaltlich gleich (Rundlauf, Versprechen aus `konto.export.punkt_1`).
- [ ] GIVEN die Fristkonstanten THEN gilt `ZEIT_EXPORT` < Budget des Konnektors (55 s) < 60 s (nginx-Lesefrist), und `fetch` bekommt höchstens 20 s.
- [ ] GIVEN Eintragsnamen mit `..`, absolutem Pfad oder Backslash in der Reise-ZIP (Test-Dienst liefert eine solche ZIP) THEN Fehler nach Punkt 22, keine Datei außerhalb.

Fehlerfälle (ganzer Abbruch, kein halber Export):
- [ ] GIVEN zwei Reisen, der Abruf der zweiten liefert `503`, `403`, Zeitüberschreitung, eine abgeschnittene oder keine ZIP THEN ist die Antwort Mein Konto mit dem Text `konto.export.fehler` (de und en), kein `application/zip`, keine Download-Kopfzeile, und alle temporären Dateien sind weg (Spion auf `tempfile`).
- [ ] GIVEN `404` für genau eine der Reisen THEN läuft der Export weiter und die ZIP enthält die übrigen Reisen.
- [ ] GIVEN eine nicht lesbare Belegdatei oder `OSError` beim Schreiben der temporären Datei THEN ebenso Fehlerseite.
- [ ] GIVEN ein zweiter gleichzeitiger Export desselben Kontos THEN `konto.export.fehler` (Punkt 30).
- [ ] GIVEN `anmeldung.reise_exportieren` ist `None` (Dienst nicht eingerichtet) THEN Fehlerseite.
- [ ] GIVEN ein Export WHEN er fertig ist (Erfolg und Fehler) THEN gibt es keine neue Datei in Ablage, Seiten, Speicher oder Repo, keine Mail und keine Meldung (Verzeichnisvergleich vorher/nachher).

Seite und Texte:
- [ ] GIVEN Mein Konto WHEN geöffnet (de und en) THEN steht der Abschnitt `id="daten"` mit Titel, Hinweis, Knopf, `<details>` mit vier Punkten und dem Schlusssatz, **nach** „Einstellungen“ und **vor** dem Linkblock; Formular `POST /konto` mit `aktion=export`; Wortlaut wörtlich gleich Punkt 19; der Rest der Seite (Linkblock, Block der vorgemerkten Reisen) unverändert.
- [ ] GIVEN `GET /konto?aktion=export` THEN keine ZIP, die normale Seite; GIVEN ein POST ohne gültige Herkunft/ohne Sitzung THEN abgewiesen wie bei `alle_abmelden`.
- [ ] GIVEN die Datenschutzseite (de und en) THEN steht `recht.datenschutz.export` im Rechte-Block vor `folgt`; `folgt` enthält nicht mehr „Export deiner Reisedaten“, aber „Löschen und Export eines Eintrags auf der Warteliste“; die Absätze von #381 sind unverändert.
- [ ] GIVEN alle Schlüssel `konto.export.*` und `recht.datenschutz.export` THEN in `texte_de.py` und `texte_en.py` vorhanden; `test_texte.py` und `test_rechtliches.py` grün, Ausnahmelisten nicht länger.
- [ ] GIVEN `betrieb/deploy.sh` THEN ohne neue Modulzeile; der Test zur Modulliste bleibt grün.

Gesamt:
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests -n 3` grün; alle bestehenden Tests (Anmeldung, Konten, Loeschen, Schreibdienst, Speicher, Texte, Datenschutz) unverändert grün.

**Instanz-Tests:** Die Schnittstelle zwischen Konnektor und Schreibdienst ist neu (`GET /<reise>/export`, Dateiantworten in `_anmeldung`). Vor dem Vorspulen auf `main` laufen darum die Tests der einbindenden Instanzen mit dem Branch (Anleitung im Reisen-Repo der Instanz; CLAUDE.md). Die öffentliche CI führt private Tests nicht aus. Nach dem Ausliefern: Export an der eigenen Testreise der Instanz (Zeit, Größe, Entpacken, Wiedereinlesen durch Frieda) und Messung der Zeitgrenze, Ergebnis im Issue #498.

## Architektur-Entscheidung (ADR)

**ADR-Nr.:** ADR-0001, ADR-0005, ADR-0006 und ADR-0009 (bestehend, keine neue ADR)

Rationale: Keine neue ADR. Der Export ändert weder Grundformen noch das Speicherformat; er folgt ADR-0009 (Speicher und `exportieren` als vorhandener Weg), ADR-0005 (Konten) und ADR-0006 (Texte). Die Schnittstelle zwischen Konnektor und Schreibdienst steht in `docs/betrieb.md` und wird dort nachgetragen (`docs/konnektor.md` bleibt unverändert; die ADRs sind nur Referenz, sie werden nicht geändert): ein Absatz „Export der Daten“ mit dem Inhalt der ZIP und dem Hinweis, dass Mein Konto den Schreibdienst braucht.

## Dependencies

| Abhängigkeit | Art | Wirkung |
|---|---|---|
| `reisespeicher.exportieren` | Code, nur gelesen | Reise im Dateiformat aus dem Speicher |
| `schreiben_git.git` | Code | `git fetch`, `ls-tree`, `archive` für Reisen auf dem Git-Weg (bis #350 durch ist) |
| `konten` (`mitgliedschaften`, `reise_vorgemerkt`, `geraete`, `push_einstellungen`, `kalender_einstellungen`, `konto`, `dienst_geheimnis`) | Code | Quelle der Reisen und der Kontoangaben; `reise_vorgemerkt` kommt aus #381 |
| `rueckmeldungen` (`ordner`, `eintraege`, `aufgaben_lesen`, `brett_lesen`, `packstand_lesen`, `zustand`) | Code | Beiträge und Rollen |
| `belege` (`liste`, `datei_pfad`) | Code | Sichtbare Belege |
| #381 (Löschen, Sitzung `frieda-reist-f5`) | Gleichzeitig | gleiche Seite; deren Teile bleiben unangetastet; `reise_vorgemerkt` ist die einzige Abfrage |
| #350/#506 (Umschaltung auf den Speicher) | Nachbar | Git-Weg bleibt bis Stufe 5 nötig |
| #383 (Datenschutz) | Gleichzeitig | Datenschutztext nennt den Export erst jetzt |
| Instanz (Konnektor ↔ Schreibdienst) | Betrieb | neue GET-Route; Instanz-Tests vor dem Ausliefern |
| nginx (60 s Lesefrist) | Fremd | Annahme Proxy-Zeitgrenze, Punkt 25 |

## Scope

**Affected Files:**

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/schreiben.py` | MODIFY | `Dienst.do_GET`: Zweig `GET /<reise>/export`; Helfer `_datei_senden`; `ZEIT_EXPORT`; Speicherweg (`exportieren` in Temp-Ordner, zippen) |
| `engine/schreiben_git.py` | MODIFY | `reise_archiv(s, reise, datei)` (`fetch`, `ls-tree`, `archive`) |
| `engine/konnektor.py` | MODIFY | `_anmeldung` streamt Dateiobjekte; `reise_export(reise, datei)`; setzt `anmeldung.reise_exportieren` |
| `engine/anmeldung.py` | MODIFY | `export_karte(k)` in `konto_seite()`; Zweig `aktion=export`; ZIP-Bau (`person.json`, `reise/`, `beitraege/`, `belege/`); Modulvariable `reise_exportieren`; `datenschutz_inhalt()` |
| `engine/texte_de.py`, `engine/texte_en.py` | MODIFY | `konto.export.*`, `recht.datenschutz.export`, `recht.datenschutz.folgt` |
| `engine/tests/test_export.py` | CREATE | Tests nach Test Plan |
| `docs/betrieb.md` (Absatz) | MODIFY | Hinweis zum Export; kein neues Modul, `deploy.sh` unverändert |

**Estimated Changes:** 8 Dateien (6 Engine-Dateien inklusive der zwei Katalogdateien, 1 Test, 1 Doku), etwa +450/−5 Zeilen (rund 250 Tests). Risiko mittel: neue Schnittstelle zwischen zwei Diensten und ein erweiterter Antwortweg für alle Anmeldeseiten.

## Acceptance Criteria

- **AC-1:** Given ein angemeldetes Konto / When es Mein Konto öffnet (de und en) / Then steht der Abschnitt „Meine Daten“ (`id="daten"`) in der rechten Spalte nach „Einstellungen“ und vor dem Linkblock, mit Hinweis, Knopf „Meine Daten herunterladen“ (Formular `POST /konto`, `aktion=export`), `<details>` „Was ist drin?“ mit den vier Punkten und dem Schlusssatz, im freigegebenen Wortlaut; die #381-Teile der Seite sind unverändert.
- **AC-2:** Given ein Konto mit Mitgliedschaft in `beispielreise` (Ida, Karl) oder `stadtwochenende` (Tom, Lea) / When `POST /konto aktion=export` / Then antwortet Mein Konto mit `200`, `Content-Type: application/zip`, `Content-Disposition: attachment; filename="frieda-daten-<JJJJ-MM-TT>.zip"` (UTC), `Cache-Control: no-store`, und einer gültigen ZIP.
- **AC-3:** Given die ZIP / When sie geöffnet wird / Then enthält sie `person.json` und je Mitgliedschaft (auch archivierte) die Ordner `<reise>/reise/`, `<reise>/beitraege/` und `<reise>/belege/` mit dem beschriebenen Inhalt; `reise/` ist die ganze Reise im Dateiformat samt Fotos und GPX, soweit die Reise sie hat.
- **AC-4:** Given `person.json` / When sie gelesen wird / Then stehen darin `name`, `email`, `sprache`, `erstellt`, `mitgliedschaften` (`reise`, `titel`, `rolle`, `seit`), `geraete`, `kalender` und `push`, aber keine Schlüssel, Token, Push-Endpunkte und keine Daten anderer Konten.
- **AC-5:** Given eine Organisator:in und eine mitwirkende Person oder ein Gast derselben Reise / When beide exportieren / Then enthalten die Beiträge bei allen Rollen dasselbe, was die Reiseseite jedem Mitglied zeigt (Aufgaben, Brett, Packstand, Rückmeldungen vollständig); die Belege folgen der Rolle: Organisator:in alle, sonst nur die nach `belege.liste` (Sichtregeln, Zurückgezogene nur für Organisator:innen und die hochladende Person).
- **AC-6:** Given Reisen, in denen das Konto nicht Mitglied ist, vorgemerkte oder entfernte Reisen (`reise_vorgemerkt` wahr) / When es exportiert / Then kommt keine davon in der ZIP vor; ein manipuliertes Formular (zusätzliche Reisefelder) ändert nichts.
- **AC-7:** Given Konten anderer Personen mit E-Mail-Adressen, auch Eingeladene / When exportiert wird / Then steht keine fremde Adresse, kein Inhalt von `einladungen.json`, kein Dienstgeheimnis und kein Serverpfad irgendwo in der ZIP; andere Personen stehen nur mit Namen darin.
- **AC-8:** Given der Schreibdienst / When `GET /<reise>/export` mit Geheimnis und bekannter Speicherreise oder Git-Reise / Then `200`, `application/zip` mit korrekter `Content-Length` und dem Reiseinhalt wie `reisespeicher.exportieren` beziehungsweise `origin/main:reisen/<reise>`. Der Ordner `<reise>/reise/` der Gesamt-ZIP lässt sich mit `reisespeicher.importieren` wieder einlesen (Rundlauf).
- **AC-9:** Given der Schreibdienst / When das Geheimnis fehlt oder falsch ist / Then `403`, gleich für bekannte und unbekannte Reisen; bei unbekannter, ungültig benannter, vorgemerkter oder entfernter Reise `404` (nicht 410), ohne Zugriff auf den Speicher bei vorgemerkten; bei `EinstellungenNichtLesbar` `503` (`einstellungen_nicht_lesbar`), bei Speicher- oder Git-Fehlern `503` (`speicher_nicht_erreichbar`, `repo_nicht_erreichbar`).
- **AC-10:** Given große Dateien (Fotos, Belege) / When der Schreibdienst, der Konnektor oder Mein Konto sie verarbeiten / Then wird keine Datei und keine ZIP ganz in den Speicher gelesen (Streaming in Stücken, temporäre Dateien statt Bytes); `_anmeldung` streamt Dateiobjekte mit `Content-Length` per `os.fstat`, schließt sie immer und lässt alle Bytes-Antworten unverändert.
- **AC-11:** Given ein Fehler beim Abruf einer Reise (nicht 404), eine ungültige oder abgeschnittene ZIP, ein unlesbarer Beleg, eine Zeitüberschreitung (Budget 55 s) oder ein zweiter gleichzeitiger Export / When exportiert wird / Then kommt keine ZIP, sondern die ganze Seite Mein Konto mit „Export gerade nicht möglich“ (de und en); alle temporären Dateien sind weg; ein `404` einer einzelnen Reise überspringt nur diese Reise.
- **AC-12:** Given ein Export / When er erfolgreich oder gescheitert ist / Then wurde nichts geschrieben oder verändert (keine Datei in Ablage, Seiten, Speicher oder Repo, kein Verlauf, keine Mail, keine Meldung) und nichts bleibt auf dem Server liegen.
- **AC-13:** Given `GET /konto?aktion=export` oder ein POST ohne gültige Sitzung/Herkunft / When aufgerufen / Then keine ZIP; Herkunfts- und Formularprüfung wie bei `alle_abmelden` und `loeschen`.
- **AC-14:** Given die Datenschutzseite (de und en) / When sie geöffnet wird / Then steht `recht.datenschutz.export` wörtlich im Rechte-Block vor `folgt`, `folgt` nennt nur noch Löschen und Export eines Eintrags auf der Warteliste, und die Absätze von #381 sind unverändert.
- **AC-15:** Given alle neuen Texte / When `test_texte.py` und `test_rechtliches.py` laufen / Then sind `konto.export.*`, `recht.datenschutz.export` und der geänderte `folgt` in `texte_de.py` und `texte_en.py` vorhanden, Ausnahmelisten nicht länger.
- **AC-16:** Given beide Beispielreisen / When die Tests laufen / Then bestehen sie für Wanderung und Städtewochenende gleichermaßen (auch ohne Routen); `deploy.sh` braucht keine neue Zeile; alle bestehenden Tests bleiben grün (`engine/.venv/bin/python -m pytest -q engine/tests -n 3`).

## Prüfstelle (ADR-0001, zehn Fragen)

| Nr. | Antwort |
|---|---|
| 1 Ontologie statt Sonderfall | Der Export kennt nur Dateien, Rollen und die Grundstruktur der Ablage, keine Art, kein Merkmal und keine Reise im Besonderen; mit beiden Beispielreisen (Wanderung, Städtewochenende ohne Routen) durchgespielt. |
| 2 Kein Katalog | Nein. Keine Art, kein Merkmal, keine Vorlage; die ZIP trägt, was in der Reise steht. |
| 3 Keine KI in Frieda | Nein. Rein mechanisches Sammeln und Zippen nach festen Sichtregeln. |
| 4 Die Tür | Der Export ist für die Person über Mein Konto (Browser) da, nicht über den Konnektor; die Reise darin lässt sich in der Claude-App wieder einlesen. Ein Werkzeug des Konnektors ist nicht nötig (Datenschutzfunktion der Konto-Seite, wie Löschen) und wird in `docs/konnektor.md` nicht aufgenommen. |
| 5 Herkunft | Es entsteht keine neue Aussage; Herkunfts- und Prüfangaben der Reise gehen unverändert mit. |
| 6 Rollen entscheiden | Der Export entscheidet nichts. Die Rolle bestimmt nur den Umfang der Belege (Organisator:in alle, sonst nach `belege.liste`); Beiträge wie auf der Reiseseite für jedes Mitglied. |
| 7 IDs und Verlauf | Keine ID wird vergeben oder gelöscht, nichts überschrieben, nichts geschrieben; der Verlauf der Reise bleibt in `reise/` vollständig. |
| 8 PWA | Die Reiseseite und ihr Offline-Verhalten sind nicht berührt; der Abschnitt auf Mein Konto folgt dem Atomic Design (vorhandene Bausteine `karte`, `formular`, `details`), keine neuen Bausteine. Browser-Rundgang der Konto-Seite. |
| 9 Claude Code | Nein. Reiseinhalte entstehen weiter im AI-Client. |
| 10 Dokumentation | Diese Spec, `docs/betrieb.md` (Absatz Export und Hinweis zu Mein Konto ↔ Schreibdienst), ADR-0001 (Prüfstelle), ADR-0009 (`exportieren` als Quelle), ADR-0005 (Konten). |

## Definition of Done

- [ ] Alle Punkte des Test Plans sind als Tests in `engine/tests/test_export.py` umgesetzt und grün; `engine/tests` insgesamt grün (CI-Pflichtprüfungen `tests (leer)`, `tests (instanz)`, `gitleaks`).
- [ ] Alle 16 Acceptance Criteria sind durch Tests belegt.
- [ ] Texte in allen Sprachen (de, en) vollständig; Datenschutztext stimmt mit dem Verhalten überein.
- [ ] Die Tests der einbindenden Instanzen laufen mit dem Branch (neue Schnittstelle des Schreibdienstes, CLAUDE.md), vor dem Vorspulen auf `main`.
- [ ] Der Abschnitt auf Mein Konto entspricht dem vom Product Owner am 11.11.2026 freigegebenen Entwurf (Wortlaut wörtlich, Stelle der Seite).
- [ ] `docs/betrieb.md` ergänzt; `deploy.sh` unverändert (kein neues Modul).
- [ ] Nach dem Ausliefern auf `main`: Export an der eigenen Testreise der Instanz, Zeit und Größe gemessen (Proxy-Zeitgrenze, Punkt 25), ZIP entpackt und geprüft, Ergebnis im Issue #498 festgehalten; Issue #498 erst danach schließen (end-to-end).
- [ ] Die Prüfstelle (zehn Fragen) ist im PR beantwortet.

## Offene Punkte

- Keine offenen Produktfragen.
- Technisch festgelegt: Reise-ZIP kommt vom Schreibdienst (eine Quelle für Speicher und Repo); Gesamtbudget 55 s unter der nginx-Lesefrist von 60 s; Abruf über die Modulvariable `anmeldung.reise_exportieren`; ein Export je Konto zugleich; fehlender Rest einer Reise wird nie still ausgelassen (nur 404).
- Nach dem Ausliefern zu messen: reicht das Zeitbudget für Reisen mit rund 100 MB? Wenn nicht, eigenes Issue (nginx-Ort mit längerer Lesefrist oder Erstellen im Hintergrund mit Abholen).

## Changelog

- 2026-11-12: Erstfassung (Entwurf) für #498 mit dem vom Product Owner am 11.11.2026 freigegebenen Entwurf; technische Festlegungen aus `docs/context/export-498.md` und den Kommentaren von #498; Abweichungen vom Kontext: Gesamtbudget 55 s statt Aufruffrist ~120 s (nginx-Lesefrist 60 s), Beiträge für alle Rollen vollständig wie auf der Reiseseite (Abgleich mit dem Code), Begrenzung auf einen gleichzeitigen Export je Konto.
