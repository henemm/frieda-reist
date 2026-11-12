# Context: Export der Reisen und der Angaben zur Person (#498)

## Request Summary
Jede Person lädt auf „Mein Konto“ eine ZIP mit allen Reisen, in denen sie Mitglied ist (Dateiformat der Reise, Fotos, GPX),
ihren Beiträgen und sichtbaren Belegen sowie ihren Kontoangaben herunter. Entwurf vom Product Owner am 11.11.2026 freigegeben
(Artefakt „Meine Daten herunterladen“, https://claude.ai/artifact/H2x2KgsLygLEeF8ZDPxDnP), Bauplan und Absprachen mit #381 in
den Kommentaren von #498.

## Freigegebener Entwurf (sichtbare Teile, Wortlaut verbindlich)
- Abschnitt „Meine Daten“ (`id="daten"`) in der rechten Spalte von `konto_seite()` NACH „Einstellungen“, VOR dem Linkblock
  (Auf allen Geräten abmelden / Konto löschen). Karte: Satz „Lade alles herunter, was Frieda zu dir und deinen Reisen
  gespeichert hat: eine Datei mit jeder Reise, in der du dabei bist, und deinen Kontoangaben.“; Formular POST /konto
  `aktion=export`, Knopf (leise) „Meine Daten herunterladen“; `<details>` „Was ist drin?“ mit vier Punkten:
  1. „Je Reise ein Ordner mit der ganzen Reise: Tage, Pläne, Unterkünfte, Buchungen, Wissen, Fotos und Routen (GPX). Frieda kann sie daraus wieder einlesen.“
  2. „Die Beiträge der Reise: Aufgaben, Wünsche, Packliste und Rückmeldungen. Als Organisator:in alle, sonst deine eigenen und was du auf der Reiseseite siehst.“
  3. „Die Belege, die du sehen darfst.“
  4. „Deine Kontoangaben: Name, E-Mail-Adresse, Sprache, deine Reisen mit Rolle, deine Geräte und deine Einstellungen für Kalender und Benachrichtigungen.“
  Danach klein: „Andere Personen stehen darin nur mit ihrem Namen, ohne E-Mail-Adresse. Auch archivierte Reisen sind dabei.“
  Plus Fehlertext „Export gerade nicht möglich“ (Wortlaut frei, Muster vorhandener Fehler).
- Datei `frieda-daten-<JJJJ-MM-TT>.zip`: `person.json`; je Reise `<reise>/reise/`, `<reise>/beitraege/`, `<reise>/belege/`.
- Datenschutz: aus `recht.datenschutz.folgt` „und der Export deiner Reisedaten“ streichen (bleibt: Löschen und Export eines
  Eintrags auf der Warteliste); neuer Schlüssel `recht.datenschutz.export`: „Unter „Mein Konto“ kannst du jederzeit alles
  herunterladen, was Frieda zu dir speichert: deine Kontoangaben und jede Reise, in der du Mitglied bist, mit Fotos, Routen
  und den Belegen, die du sehen darfst. Die Datei entsteht beim Herunterladen und wird auf dem Server nicht aufbewahrt.“
  In `datenschutz_inhalt()` (engine/anmeldung.py ~1012) im Rechte-Block vor `folgt` einfügen. Alle Texte in texte_de UND texte_en.

## Related Files
| File | Relevance |
|------|-----------|
| engine/schreiben.py | `Dienst.do_GET` (~5653): Muster `GET /<reise>/buchung/<B-id>` mit `X-Frieda-Dienst`-Prüfung (hmac), `instanz.speicherreisen()` + `EinstellungenNichtLesbar`→503, `fehler_antwort(..., mit_ok=False)`, `_senden`. Neu: `GET /<reise>/export` (ZIP). `REISE_MUSTER` Z. 61, `ZEIT_PRUEFUNG`=3 s (für fetch zu kurz, eigene Frist ~60 s). Schreibdienst prüft schon `konten.reise_vorgemerkt` (Z. 5500). |
| engine/schreiben_git.py | `git(ordner, *args, fehler, frist)`, `buchung_im_repo` (fetch + show origin/main:reisen/<reise>/…). Git-Export: `git ls-tree origin/main reisen/<reise>` leer → 404, sonst `git archive --format=zip -o <datei> origin/main:reisen/<reise>`. |
| engine/reisespeicher.py | `exportieren(reise, ziel)` Z. 519 (unbekannte Reise: KeyError aus `_stand`; Ziel muss leer/fehlend sein; Hardlinks aus Ablage, Modus 400 – beim Zippen nur lesen). |
| engine/konnektor.py | `schreibdienst()` Z. 1283 (KN_SCHREIBDIENST, leer = nicht eingerichtet), `buchung_im_repo` Z. 1655 als Aufrufmuster; `_anmeldung` Z. 3307 schickt `inhalt` mit `len()` → für Dateiobjekt erweitern (Content-Length per `os.fstat`, `shutil.copyfileobj`, schließen). |
| engine/anmeldung.py | `konto_seite()` Z. 858 (rechte Spalte: kalender_karte, push_karte, betreiber, Einstellungen, Linkblock), `bearbeiten()` `/konto` POST-Zweige ~1299 (neuer Zweig `a == "export"`), `datenschutz_inhalt()` ~1012, `_speicherreisen`, `_person`, `ist_organisatorin`, `rolle_marke`. Hilfen `tx`, `esc`, `karte`, `formular`, `verdeckt`, `antwort`. |
| engine/konten.py | `mitgliedschaften(kid)` (reise, schluessel, seit), `reise_vorgemerkt(reise)` Z. 975 (von #381, schon da), `geraete(kid)`, `push_einstellungen(kid)`, `kalender_einstellungen(kid)`, `konto(kid)`. |
| engine/rueckmeldungen.py (rm) | `ablage()/reise` = Ablage-Ordner (`ordner()` liefert None bei vorgemerkt); `eintraege(o)`, `aufgaben_lesen(o)`, `brett_lesen(o)`, `packstand_lesen(o)`, `zustand(reise)` (personen mit schluessel, name, rolle; status „archiv“). |
| engine/belege.py | `liste(o, name, rolle)` (Sichtregeln), `datei_pfad(o, b)`, `lesen(o)`. |
| engine/texte_de.py / texte_en.py | Schlüssel `konto.export.*`, `recht.datenschutz.export`, `recht.datenschutz.folgt` ändern. |
| engine/tests/test_schreiben_speicher.py | Fixture `speicher` (beide Beispielreisen im Speicher), Hilfsklasse `Dienst` (HTTP im Thread, get liefert JSON → für ZIP eigene Abfrage). `test_schreiben.repo` = Git-Fixture. |
| engine/tests/test_anmeldung.py, test_loeschen_konto.py | Muster für Konto-Seite und /konto-POST. |

## Technische Festlegungen (Tech Lead, aus Bauplan #498)
- Mein Konto läuft im Konnektor-Dienst (ProtectHome, kein Zugriff aufs Reisen-Repo/Speicher) → Reise-Ordner holt er per
  `GET <schreibdienst>/<reise>/export` (Geheimnis-Header). 404 für unbekannte, vorgemerkte, entfernte Reisen (nicht 410).
- `POST /konto aktion=export` → ZIP in `tempfile.TemporaryFile`: `person.json` (name, email, sprache, mitgliedschaften
  [reise, titel, rolle, seit], geraete, kalender, push); je Mitgliedschaft (auch Archiv, ohne vorgemerkte) `<reise>/reise/`
  (Inhalt der Schreibdienst-ZIP), `<reise>/beitraege/` (aufgaben.json, brett.json, packstand.json, rueckmeldungen.json:
  Organisator:in alle, sonst eigene per Name plus Wünsche, die alle auf dem Brett sehen), `<reise>/belege/` (`belege.liste`
  + Dateien + belege.json als Verzeichnis). Keine einladungen.json (Adressen). Fremde Reisen nie.
- Schreibdienst nicht erreichbar/Fehler → ganze Antwort Mein Konto mit Fehler „Export gerade nicht möglich“ (kein halber Export).
- Antwort: `Content-Type: application/zip`, `Content-Disposition: attachment; filename="frieda-daten-<datum>.zip"`.

## Existing Patterns
- Schreibdienst-GET mit Geheimnis und 503 bei unlesbaren Einstellungen (#361).
- Konto-POST-Zweige geben `antwort(...)`/`weiter(...)` zurück; Fehler über `konto_seite(..., meldung=...)`.

## Dependencies / Dependents
- Upstream: reisespeicher, schreiben_git, konten, rm, belege.
- Downstream: Instanz-Tests (neue Schnittstelle des Schreibdienstes → Instanz-Tests vor dem Ausliefern laufen lassen).
  Neues Modul? Nein (nur bestehende) → deploy.sh-Liste unverändert.

## Risks & Considerations
- Große Reisen (Fotos ~100 MB): nie ganz im Speicher halten (Dateiobjekte streamen).
- Hardlinks im Export-Ordner mit Modus 400: Zippen nur lesend, TemporaryDirectory-Aufräumen muss gehen (Ordner gehört uns).
- #381 (Löschen) teilt sich Mein Konto; deren Teile (Linkblock, loeschen_seite) nicht anfassen.
- Parallelsitzung frieda-reist-f5 arbeitet an #506/#350 (Umschaltung auf Speicher) – Git-Weg bleibt bis Stufe 5 nötig.

## Analysis

### Type
Feature (neue Funktion auf „Mein Konto“, freigegebener Entwurf vom 11.11.2026).

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/schreiben.py | MODIFY | `Dienst.do_GET`: Zweig `GET /<reise>/export` (Geheimnis per `hmac.compare_digest`, `REISE_MUSTER`, `konten.reise_vorgemerkt` → 404, `EinstellungenNichtLesbar` → 503). Neuer Helfer `_datei_senden(code, datei, typ)` (Content-Length per `os.fstat`, `shutil.copyfileobj`). Speicherreise: `reisespeicher.exportieren(reise, tmpdir/reise)` → ZIP in `TemporaryFile`; `KeyError` (unbekannt) → 404; `AblageFehlt/AblageFehler`, `sqlite3.Error`, `OSError` → 503. |
| engine/schreiben_git.py | MODIFY | `reise_archiv(s, reise, datei)`: `fetch` (Frist ~60 s), `ls-tree origin/main reisen/<reise>` leer → None (404), sonst `archive --format=zip origin/main:reisen/<reise>` in die Datei. Kein LFS im Einsatz (geprüft), Fotos kommen echt mit. |
| engine/konnektor.py | MODIFY | `_anmeldung`: `inhalt` darf ein Dateiobjekt sein (Länge per `os.fstat`, Kopie per `shutil.copyfileobj`, im `finally` schließen, HEAD ohne Inhalt); Bytes-Weg unverändert. Neue Funktion `reise_export(reise, datei)` → (ok, fehler) als Aufruf an den Schreibdienst (Muster `buchung_im_repo`, Timeout ~120 s); 404 → Reise überspringen, sonst Fehler. |
| engine/anmeldung.py | MODIFY | `export_karte(k)` in `konto_seite()` rechte Spalte NACH „Einstellungen“, VOR dem Linkblock (freigegebener Entwurf). `bearbeiten()`: Zweig `a == "export"` → ZIP bauen; Fehler → `konto_seite(..., meldung=tx("konto.export.fehler"))`. `datenschutz_inhalt()`: `recht.datenschutz.export` vor `folgt`. Abruf der Reise-ZIP über eine einsetzbare Funktion (Modulvariable, im Konnektor gesetzt wie `reise_info`), damit anmeldung.py den Konnektor nicht importiert und Tests sie ersetzen können. |
| engine/texte_de.py, texte_en.py | MODIFY | `konto.export.titel/hinweis/knopf/was_drin/punkt_1..4/andere/fehler`, `recht.datenschutz.export`, `recht.datenschutz.folgt` gekürzt. |
| engine/tests/test_export.py | CREATE | Schreibdienst-Export (Speicher und Repo-Weg, beide Beispielreisen, 403 ohne Geheimnis, 404 unbekannt/vorgemerkt), ZIP von Mein Konto (person.json, Ordner je Mitgliedschaft, keine fremde Reise, Archiv dabei, vorgemerkte nicht), Sichtregeln Beiträge/Belege (Organisator:in vs. mitwirkend), keine fremden E-Mail-Adressen, Fehlerfall ganzer Abbruch, Texte, Datenschutzsatz, Content-Disposition. |

### Scope Assessment
- Files: 7 (6 MODIFY, 1 CREATE)
- Estimated LoC: +~450 (davon ~250 Tests) / -~5
- Risk Level: MEDIUM — neue Schnittstelle zwischen Konnektor und Schreibdienst (Instanz-Tests vor dem Ausliefern nötig); der Antwortweg `_anmeldung` wird für Dateien erweitert und betrifft alle Anmeldeseiten.

### Technical Approach
1. Der Schreibdienst liefert die Reise als ZIP (eine Quelle für Speicher- und Repo-Reisen; der Konnektor bleibt ohne Zugriff auf Repo/Speicher, wie im Bauplan). Antwort aus `TemporaryFile`, nie ganz im Speicher.
2. Mein Konto baut die Gesamt-ZIP in `tempfile.TemporaryFile`: `person.json`; je `konten.mitgliedschaften(kid)` ohne `reise_vorgemerkt`: `<reise>/reise/` = Einträge der Schreibdienst-ZIP umbenannt (Stream je Eintrag, `ZipFile.open` + `copyfileobj`), `<reise>/beitraege/` (aufgaben.json, brett.json, packstand.json, rueckmeldungen.json – Organisator:in alles, sonst eigene per Name; Brett mit allen Wünschen wie auf der Seite), `<reise>/belege/` (`belege.liste(o, name, rolle)` + Dateien per `belege.datei_pfad` + belege.json). Name und Rolle aus `rm.zustand(reise)` über den Personen-Schlüssel der Mitgliedschaft. Fehlt die Ablage (`rm.ordner` None), nur `reise/`.
3. Ein Fehler beim Abruf einer Reise (außer 404) bricht den ganzen Export ab → Mein Konto mit „Export gerade nicht möglich“; kein halber Export.
4. Antwort 200, `Content-Type: application/zip`, `Content-Disposition: attachment; filename="frieda-daten-<JJJJ-MM-TT>.zip"` (Datum UTC).
5. Der Formular-POST nutzt das vorhandene Herkunfts-/CSRF-Muster der übrigen `/konto`-Zweige unverändert.

### Dependencies
- Upstream: reisespeicher.exportieren, schreiben_git.git, konten (mitgliedschaften, reise_vorgemerkt, geraete, push_/kalender_einstellungen, konto), rueckmeldungen (ordner, eintraege, aufgaben_lesen, brett_lesen, packstand_lesen, zustand), belege (liste, datei_pfad).
- Downstream: Instanz (Konnektor ↔ Schreibdienst, neue GET-Route) → Instanz-Tests mit dem Branch vor dem Ausliefern. Kein neues Modul → deploy.sh-Liste bleibt.
- Zeitgrenze: Proxy-Timeout des Webservers für `/konto` bei großen Reisen in der Spec als Annahme festhalten und nach dem Ausliefern an der eigenen Testreise messen.

### Open Questions
- Keine Produktfrage offen (Entwurf freigegeben). Technische Punkte (Zeitgrenzen, Einbindung des Abrufs ohne Zirkel-Import) legt der Tech Lead in der Spec fest.
