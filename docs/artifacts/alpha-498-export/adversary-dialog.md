# Adversary Dialog — alpha-498-export
Spec: docs/specs/betrieb/export-498.md
Datum: 2026-11-12 07:21

## Checkliste
- [x] **AC-1:** Given ein angemeldetes Konto / When es Mein Konto öffnet (de und en) / Then steht der Abschnitt „Meine Daten“ (`id="daten"`) in der rechten Spalte nach „Einstellungen“ und vor dem Linkblock, mit Hinweis, Knopf „Meine Daten herunterladen“ (Formular `POST /konto`, `aktion=export`), `<details>` „Was ist drin?“ mit den vier Punkten und dem Schlusssatz, im freigegebenen Wortlaut; die #381-Teile der Seite sind unverändert.
- [x] **AC-2:** Given ein Konto mit Mitgliedschaft in `beispielreise` (Ida, Karl) oder `stadtwochenende` (Tom, Lea) / When `POST /konto aktion=export` / Then antwortet Mein Konto mit `200`, `Content-Type: application/zip`, `Content-Disposition: attachment; filename="frieda-daten-<JJJJ-MM-TT>.zip"` (UTC), `Cache-Control: no-store`, und einer gültigen ZIP.
- [x] **AC-3:** Given die ZIP / When sie geöffnet wird / Then enthält sie `person.json` und je Mitgliedschaft (auch archivierte) die Ordner `<reise>/reise/`, `<reise>/beitraege/` und `<reise>/belege/` mit dem beschriebenen Inhalt; `reise/` ist die ganze Reise im Dateiformat samt Fotos und GPX, soweit die Reise sie hat.
- [x] **AC-4:** Given `person.json` / When sie gelesen wird / Then stehen darin `name`, `email`, `sprache`, `erstellt`, `mitgliedschaften` (`reise`, `titel`, `rolle`, `seit`), `geraete`, `kalender` und `push`, aber keine Schlüssel, Token, Push-Endpunkte und keine Daten anderer Konten.
- [x] **AC-5:** Given eine Organisator:in und eine mitwirkende Person oder ein Gast derselben Reise / When beide exportieren / Then enthalten die Beiträge bei allen Rollen dasselbe, was die Reiseseite jedem Mitglied zeigt (Aufgaben, Brett, Packstand, Rückmeldungen vollständig); die Belege folgen der Rolle: Organisator:in alle, sonst nur die nach `belege.liste` (Sichtregeln, Zurückgezogene nur für Organisator:innen und die hochladende Person).
- [x] **AC-6:** Given Reisen, in denen das Konto nicht Mitglied ist, vorgemerkte oder entfernte Reisen (`reise_vorgemerkt` wahr) / When es exportiert / Then kommt keine davon in der ZIP vor; ein manipuliertes Formular (zusätzliche Reisefelder) ändert nichts.
- [x] **AC-7:** Given Konten anderer Personen mit E-Mail-Adressen, auch Eingeladene / When exportiert wird / Then steht keine fremde Adresse, kein Inhalt von `einladungen.json`, kein Dienstgeheimnis und kein Serverpfad irgendwo in der ZIP; andere Personen stehen nur mit Namen darin.
- [x] **AC-8:** Given der Schreibdienst / When `GET /<reise>/export` mit Geheimnis und bekannter Speicherreise oder Git-Reise / Then `200`, `application/zip` mit korrekter `Content-Length` und dem Reiseinhalt wie `reisespeicher.exportieren` beziehungsweise `origin/main:reisen/<reise>`. Der Ordner `<reise>/reise/` der Gesamt-ZIP lässt sich mit `reisespeicher.importieren` wieder einlesen (Rundlauf).
- [x] **AC-9:** Given der Schreibdienst / When das Geheimnis fehlt oder falsch ist / Then `403`, gleich für bekannte und unbekannte Reisen; bei unbekannter, ungültig benannter, vorgemerkter oder entfernter Reise `404` (nicht 410), ohne Zugriff auf den Speicher bei vorgemerkten; bei `EinstellungenNichtLesbar` `503` (`einstellungen_nicht_lesbar`), bei Speicher- oder Git-Fehlern `503` (`speicher_nicht_erreichbar`, `repo_nicht_erreichbar`).
- [x] **AC-10:** Given große Dateien (Fotos, Belege) / When der Schreibdienst, der Konnektor oder Mein Konto sie verarbeiten / Then wird keine Datei und keine ZIP ganz in den Speicher gelesen (Streaming in Stücken, temporäre Dateien statt Bytes); `_anmeldung` streamt Dateiobjekte mit `Content-Length` per `os.fstat`, schließt sie immer und lässt alle Bytes-Antworten unverändert.
- [x] **AC-11:** Given ein Fehler beim Abruf einer Reise (nicht 404), eine ungültige oder abgeschnittene ZIP, ein unlesbarer Beleg, eine Zeitüberschreitung (Budget 55 s) oder ein zweiter gleichzeitiger Export / When exportiert wird / Then kommt keine ZIP, sondern die ganze Seite Mein Konto mit „Export gerade nicht möglich“ (de und en); alle temporären Dateien sind weg; ein `404` einer einzelnen Reise überspringt nur diese Reise.
- [x] **AC-12:** Given ein Export / When er erfolgreich oder gescheitert ist / Then wurde nichts geschrieben oder verändert (keine Datei in Ablage, Seiten, Speicher oder Repo, kein Verlauf, keine Mail, keine Meldung) und nichts bleibt auf dem Server liegen.
- [x] **AC-13:** Given `GET /konto?aktion=export` oder ein POST ohne gültige Sitzung/Herkunft / When aufgerufen / Then keine ZIP; Herkunfts- und Formularprüfung wie bei `alle_abmelden` und `loeschen`.
- [x] **AC-14:** Given die Datenschutzseite (de und en) / When sie geöffnet wird / Then steht `recht.datenschutz.export` wörtlich im Rechte-Block vor `folgt`, `folgt` nennt nur noch Löschen und Export eines Eintrags auf der Warteliste, und die Absätze von #381 sind unverändert.
- [x] **AC-15:** Given alle neuen Texte / When `test_texte.py` und `test_rechtliches.py` laufen / Then sind `konto.export.*`, `recht.datenschutz.export` und der geänderte `folgt` in `texte_de.py` und `texte_en.py` vorhanden, Ausnahmelisten nicht länger.
- [x] **AC-16:** Given beide Beispielreisen / When die Tests laufen / Then bestehen sie für Wanderung und Städtewochenende gleichermaßen (auch ohne Routen); `deploy.sh` braucht keine neue Zeile; alle bestehenden Tests bleiben grün (`engine/.venv/bin/python -m pytest -q engine/tests -n 3`).

## Dialog

### Runde 1
**Adversary:** Spec zuerst gelesen, Erwartung gebildet, danach Code und Diff geprüft. Gesamte Testsuite gelaufen (adversary-test-output.txt). Eigene Probe-Skripte (Scratchpad, nicht im Repo): Datenleck (Adressen von Karl, Tom, Eingeladenem, Fremdkonto, Wort "einladungen", Dienstgeheimnis, Wurzelpfad: nichts in der ZIP), Herkunft (ohne/fremde/"null" Herkunft, ohne und mit falschem Cookie: jeweils 403, nie eine ZIP), GET und HEAD /konto?aktion=export (HTML, keine ZIP), Pfad-Tricks bei GET /<reise>/export (.., %2e%2e, Großschreibung, Zeilenumbruch, "-x", doppelter Schrägstrich: alle 404), böse Belegdateinamen in belege.json (../belege.json, sub/x.pdf, .., leer: jeweils Fehlerseite statt ZIP), Sperre und Temp-Dateien bei Fehler (RuntimeError im Abruf: alle Temp-Dateien geschlossen, Sperre frei) und bei BaseException (Sperre frei, nächster Export gelingt).
**Implementierer:** Keine Rückmeldung in diesem Lauf (isolierte Prüfung ohne Implementiererkontext).

### Runde 2
**Adversary:** Gezielt gegen die Randfälle gebohrt, die die Tests nicht abdecken. Treffer: (a) Ablagedatei mit Änderungszeit vor 1980: GET /<reise>/export liefert dauerhaft 503 (ZipFile.write ohne strict_timestamps=False), Probe ALTE_MTIME 503. (b) 404 einer Reise: person.json nennt die Reise weiter bei den Mitgliedschaften, obwohl ihr Ordner fehlt. (c) Dateien aus der Ablage kommen mit Modus 0400 in die ZIP (entpackt schreibgeschützt). (d) offen="daten" bleibt wirkungslos, die Meldung steht trotzdem oben. (e) kalender_einstellungen schreibt beim Lesen eine leere Zeile in kalender_abo (INSERT OR IGNORE), das ist die in der Spec vorgeschriebene Funktion. (f) Abweichung 404 statt 503 ohne .git bei nicht leerer Speicherliste folgt demselben Muster wie /gesund (Zeile 5755) und ist für eine Instanz im Speicherbetrieb sachlich richtig; bei einer Instanz im Übergang, deren .git fehlt, würde eine Git-Reise still ausgelassen statt Fehlerseite.
**Implementierer:** Keine Rückmeldung in diesem Lauf.

### Runde 3
**Adversary:** Nachbesserung geprüft (engine/schreiben.py reise_zip_aus_speicher und _export_repo, Tech-Lead-Entscheidungen). F001: Probe mit Änderungszeit 0 an allen Ablagedateien: GET /beispielreise/export jetzt 200, alle Dateien Modus 0o644, Zeitstempel 1980-01-01. Streaming bleibt (ZipInfo.from_file plus z.open und copyfileobj in 1-MiB-Stücken, kein read() der ganzen Datei; Test mit 40 MB grün). Speicherreise läuft ohne .git korrekt (Probe: Wurzel ohne .git, Speicherreise 200). F006 Modus: in der Dienst-ZIP 0o644; die Gesamt-ZIP reicht external_attr der Quelle durch (anmeldung.py:973). F002: ohne .git jetzt immer 503 repo_nicht_erreichbar; Folge, die die Spec so vorsieht: auf einer Instanz ohne .git ergibt auch eine dem Dienst unbekannte Reise 503 statt 404, der Export dieses Kontos scheitert dann ganz (Fehlerseite) statt die Reise zu überspringen, was auf einer reinen Speicherinstanz ohne Repo nur bei einer Mitgliedschaft in einer im Speicher fehlenden Reise vorkommt (LOW, Spec-konform). Volle Suite selbst ausgeführt: 2436 passed, 0 failed, 0 skipped.
**Implementierer:** Nachbesserung F001, F002, F006 geliefert; F003, F004, F005, F007 bewusst belassen (LOW).

## Bewertung der Test-Korrekturen
1. AblageFehlt("fehlt", "0"*64): berechtigt (Signatur der Ausnahme verlangt zwei Argumente, reisespeicher.py Z. 97; Testfehler).
2. medien/gross.bin durch gross.jpg: berechtigt für die Aussage des Tests (.bin wird nicht ausgelagert, exportieren liest nicht ausgelagerte Blobs ganz, reisespeicher.py Z. 583). Für reale Reisen ist AC-10 dadurch nicht verletzt: Schreibweg lässt nur kurze Texte (MAX_BODY 64 KB, GPX 60000 Zeichen) in die Datenbank, große Medien tragen immer eine Endung aus AUSLAGERN und liegen in der Ablage. Es bleibt eine Lücke der Spec (reisespeicher.exportieren darf laut Spec nicht geändert werden und liest nicht ausgelagerte Dateien ganz), kein Defekt des Exports (F005, LOW).
3. c2.sock.close() durch r2.close(): berechtigt (bei HTTP/1.0 hängt die Verbindung an der Antwort, der Test bricht weiterhin die Verbindung mitten in der Antwort ab).
4. del gross auskommentiert: berechtigt (Testhilfe braucht den Wert noch, Messung beginnt erst nach tracemalloc.start).
5. seit-Vorgabe 2099: berechtigt (neue Mitgliedschaft soll in der Reihenfolge nach seit hinter der vorhandenen stehen, die Vorgabe lag vor den Einladungen aus der Testumgebung).
6. monotonic 10**12 statt 10**6: berechtigt (time.monotonic des Rechners kann 10**6 Sekunden überschreiten, Test hing von der Betriebszeit der Maschine ab).
Die Abweichungen der Umsetzung: 404 statt 503 (siehe F002, MEDIUM, Spec 13.7 verlangt 503), Restzeit per Thread-Frist (sachlich nötig, weil anmeldung den Konnektor nicht importieren darf, Spec Punkt 17), offen="daten" wirkungslos (F004, LOW).

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Findings

Finding:
  ID: F001
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/schreiben.py:5655
  Description: [Runde 3: behoben und bestätigt] reise_zip_aus_speicher rief ZipFile.write(f, ...) ohne strict_timestamps=False; die Hardlinks aus der Ablage tragen deren Änderungszeit.
  Spec requirement: AC-8/AC-9 — GET /<reise>/export liefert die Reise aus dem Speicher; 503 nur bei echten Speicher- oder Repo-Fehlern.
  Conflict: Hat eine Ablagedatei eine Änderungszeit vor 1980 (zurückgespielte Sicherung, normalisierte Zeitstempel, Kopie mit erhaltener Zeit), wirft ZipFile.write ValueError, der Dienst antwortet dauerhaft 503 speicher_nicht_erreichbar und die Person sieht für diese Reise immer "Export gerade nicht möglich". Probe: Änderungszeit 0 an allen Ablagedateien, Ergebnis 503 (Meldung "ZIP does not support timestamps before 1980").
  Remediation: zipfile.ZipFile(datei, "w", zipfile.ZIP_DEFLATED, strict_timestamps=False) und einen Test mit Ablagedatei der Zeit 0 ergänzen.

Finding:
  ID: F002
  Severity: MEDIUM
  Category: spec_violation
  Code reference: engine/schreiben.py:5732
  Description: [Runde 3: behoben, jetzt immer 503 ohne .git, bestätigt] _export_repo antwortete 404, wenn s.wurzel/.git fehlt und speicherreisen() nicht leer ist (Muster von /gesund, Zeile 5755); die Spec (Punkt 13.7) verlangt bei fehlendem .git 503 repo_nicht_erreichbar.
  Spec requirement: Spec Punkt 13.7 und AC-9 — fehlt .git oder scheitert der Repo-Zugriff, 503; nur "Reise unbekannt" ist 404.
  Conflict: Der Konnektor behandelt 404 als "Reise gibt es nicht mehr" und lässt sie still aus (anmeldung.py _export_reise, ok == "fehlt"). Auf einer Instanz im Übergang (Speicher teilweise, .git versehentlich weg) fehlt eine Repo-Reise lautlos in der ZIP statt Fehlerseite; das ist genau der stille Teilexport, den Punkt 22/23 ausschließt. Im reinen Speicherbetrieb ist 404 richtig, die Abweichung ist begründbar, aber nicht von der Spec gedeckt.
  Remediation: Entweder Spec anpassen (404, wenn die Reise nicht in speicherreisen() steht und keine Repo-Reisen mehr möglich sind) oder 503, solange der Dienst noch Repo-Reisen kennt. Entscheidung durch Tech Lead.

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: engine/anmeldung.py:921
  Description: person.json wird vor der Reiseschleife geschrieben und listet alle nicht vorgemerkten Mitgliedschaften; ein 404 des Schreibdienstes lässt den Ordner aus (_export_reise, "fehlt"), die Reise bleibt aber in mitgliedschaften.
  Spec requirement: Punkt 23 — 404 heißt: die Reise wird ausgelassen "wie nicht vorhanden".
  Conflict: person.json nennt eine Reise, deren Ordner in der ZIP fehlt (Probe p1).
  Remediation: person.json erst nach der Schleife schreiben und nur tatsächlich exportierte Reisen nennen.

Finding:
  ID: F004
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/anmeldung.py:899
  Description: export_antwort ruft konto_seite(..., offen="daten") auf; export_karte(k) kennt keinen offen-Parameter, "daten" bleibt wirkungslos (die Meldung oben auf der Seite erscheint trotzdem).
  Spec requirement: Punkt 22 — Fehlerseite mit offen="daten".
  Conflict: Toter Parameter; der Abschnitt "Meine Daten" ist nach einem Fehler nicht hervorgehoben.
  Remediation: Parameter entfernen und Spec angleichen oder den Abschnitt gezielt öffnen.

Finding:
  ID: F005
  Severity: LOW
  Category: edge_case
  Code reference: engine/schreiben.py:5651
  Description: reisespeicher.exportieren (nicht geändert) liest nicht ausgelagerte Dateien (Endung nicht in AUSLAGERN, etwa medien/*.bin oder .pdf) vollständig in den Speicher (reisespeicher.py Z. 583).
  Spec requirement: AC-10 — keine Datei wird ganz in den Speicher gelesen.
  Conflict: Für reale Reisen unkritisch (der Schreibweg lässt nur kurze Texte in die Datenbank, große Medien liegen in der Ablage), aber eine Lücke zwischen AC-10 und der Vorgabe, exportieren nicht zu ändern. Lücke der Spec, kein Defekt des Exports.
  Remediation: In der Spec festhalten oder exportieren später stückweise machen.

Finding:
  ID: F006
  Severity: LOW
  Category: edge_case
  Code reference: engine/konnektor.py:1674
  Description: [Runde 3: Modus behoben, 0o644 bestätigt; Budgetlücke theoretisch, LOW] Dateien aus der Ablage kamen mit Modus 0400 in die Reise-ZIP (z.write übernimmt st_mode, _export_kopieren reicht external_attr durch); entpackt sind Fotos und GPX schreibgeschützt (Probe p4). Außerdem begrenzt urlopen(timeout=Rest) nur die Wartezeit je Lesevorgang, nicht die Gesamtdauer; export_rest() wird erst nach einem vollen Stück geprüft.
  Spec requirement: Punkt 24 — Gesamtbudget 55 s.
  Conflict: Die Budgetlücke betrifft nur einen langsam tröpfelnden Dienst und ist theoretisch (der Dienst ist lokal); Modus 0400 stört beim Löschen oder Bearbeiten der entpackten Dateien.
  Remediation: external_attr beim Zippen auf 0644 setzen; optional in kleineren Stücken lesen.

Finding:
  ID: F007
  Severity: LOW
  Category: edge_case
  Code reference: engine/schreiben_git.py:93
  Description: Repo-Weg: git archive berücksichtigt export-ignore und export-subst aus der .gitattributes des Reisen-Repos; so markierte Dateien fehlen still in der ZIP. Außerdem schreibt kalender_einstellungen (konten.py:1144, in person.json benutzt) bei jedem Lesen ein INSERT OR IGNORE in kalender_abo, obwohl der Export laut Punkt 26 nichts verändert (die Spec schreibt diese Funktion vor).
  Spec requirement: Punkt 26 und AC-12 — Export ändert keine Daten; Punkt 13.7 — Inhalt von reisen/<reise> im Hauptzweig.
  Conflict: Beides ohne praktische Wirkung heute (keine export-ignore-Regel bekannt; leere Zeile in kalender_abo, die Mein Konto ohnehin anlegt).
  Remediation: Beobachten; bei Bedarf eine lesende Variante ohne INSERT verwenden.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:887
  Evidence: export_karte baut id="daten" mit Titel, Hinweis, Formular POST /konto aktion=export, details mit vier Punkten und Schlusssatz; konto_seite fügt sie nach Einstellungen und vor dem Linkblock ein; Texte wörtlich gleich Spec (Diff geprüft); Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/anmeldung.py:899
  Evidence: Antwort 200, application/zip, Content-Disposition mit UTC-Datum aus Ziffern, no-store aus den Anmeldekopfzeilen, Content-Length per fstat; test_export_liefert_zip grün für beide Beispielreisen.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/anmeldung.py:980
  Evidence: _export_reise legt <reise>/reise/, beitraege/ und belege/ an; archivierte Reisen bleiben (Test); fehlt die Ablage, entfallen beitraege/ und belege/.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/anmeldung.py:939
  Evidence: export_person liest nur name, email, sprache aus konten.konto; Mitgliedschaften ohne Personenschlüssel; geraete/kalender/push aus den vorgesehenen Funktionen; test_person_json sucht nach token, schluessel, endpoint, p256dh, auth.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/anmeldung.py:1027
  Evidence: Beiträge für alle Rollen vollständig, Belege über belege.liste(o, name, rolle); Rolle gast und Kontoname, wenn der Zustand fehlt.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/anmeldung.py:921
  Evidence: Einzige Quelle ist konten.mitgliedschaften(k["id"]) ohne reise_vorgemerkt; zusätzliche Formularfelder werden nicht gelesen (Test und eigene Probe).
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/anmeldung.py:961
  Evidence: Probe p9: Adressen von Karl, Tom, Eingeladenem, Fremdkonto, Wort einladungen kommen in keiner Datei der ZIP vor; Eintragsnamen werden geprüft (p8).
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/schreiben.py:5691
  Evidence: GET /<reise>/export liefert Speicher- und Repo-Weg als ZIP mit Content-Length; Rundlauf über reisespeicher.importieren im Test; Pfadtricks (p7) enden in 404.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/schreiben.py:5715
  Evidence: 403 vor jeder Aussage über die Reise (hmac.compare_digest), 404 für ungültig, unbekannt, vorgemerkt, entfernt, 503 für Einstellungen, Speicher, Repo; Abweichung bei fehlendem .git siehe F002.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/konnektor.py:1674
  Evidence: Kopie in Stücken zu 1 MiB, TemporaryFile, _anmeldung mit shutil.copyfileobj und fstat, close im finally (konnektor.py:3369); Bytes-Antworten unverändert; Einschränkung F005.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/anmeldung.py:899
  Evidence: Jede Exception ergibt die Fehlerseite, finally gibt die Sperre frei (auch bei BaseException, Probe p2), alle Temp-Dateien geschlossen (Probe p3); 404 überspringt die Reise (Einschränkung F003).
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/schreiben_git.py:93
  Evidence: Der Export schreibt nur in TemporaryFile und TemporaryDirectory; Verzeichnisvergleich im Test grün; Einschränkung F007 (leere Zeile kalender_abo).
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: engine/anmeldung.py:1502
  Evidence: Zweig steht hinter der GET-Rückgabe und den Sitzungs- und Herkunftsprüfungen; Probe p5 (GET und HEAD liefern HTML) und p6 (403 ohne, fremde und "null" als Herkunft).
  Status: CONFIRMED

Confirmation:
  AC: AC-14
  Code reference: engine/texte_de.py:3675
  Evidence: recht.datenschutz.export wörtlich laut Spec, in datenschutz_inhalt (anmeldung.py:1202) vor folgt; folgt ohne Export der Reisedaten; Absätze von #381 unverändert.
  Status: CONFIRMED

Confirmation:
  AC: AC-15
  Code reference: engine/texte_en.py:3673
  Evidence: Alle Schlüssel konto.export.* und recht.datenschutz.export in de und en vorhanden, englischer Wortlaut gleich Spec Punkt 20; test_texte.py und test_rechtliches.py in der vollen Suite grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-16
  Code reference: engine/texte_de.py:3665
  Evidence: Volle Suite 2434 passed, 0 failed, 0 skipped; beide Beispielreisen parametrisiert; deploy.sh nicht geändert.
  Status: CONFIRMED

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Nachbesserung (F001, F002, F006) ist bestätigt; offen bleiben nur LOW-Findings (F003, F004, F005, F007, Rest von F006).

Tests: 2436 passed, 0 failed, 0 übersprungen
Edge cases: F001 (Zeit 0 an Ablagedateien: 200, Modus 644), F002 (ohne .git 503), Streaming erhalten; geprüft, nichts MEDIUM oder höher offen
Regressions: Keine gefunden
Checklist: 16/16 points proven

## Geprüfte Dateien

- sha256:07fc03feb194ea3433973d876f50f36dc85048e0ff74ed887322d3fa1b70fda7  engine/anmeldung.py
- sha256:36d5af37e2bf69741cd0e62c3f2492f2ff9bfcd44be8502a0144137b8887f42d  engine/konnektor.py
- sha256:d504084249fa97d00ca8fa878e3cfdebe64200431ac83944e35481140d48c6a1  engine/schreiben.py
- sha256:2864b3b5e0eea4e7dd9d433e87987d0883430481cdcdb7d24d108fe2d6e895a5  engine/schreiben_git.py
- sha256:449f443189f05d67bb06023b88a3d2afe68ab71545d60b8513e81d6609613942  engine/texte_de.py
- sha256:fb7be700d9aa5f71cd5a8447bfa3efa33d5ab7f3289b5e624bf06e12c53d8d57  engine/texte_en.py

## Prüfbasis

- base: 48da8b919afe55565137893fe5d1b9ea3dfe7323
- blob:1eba27cf3188911b1bcbd1632b569183c473a4fc  engine/anmeldung.py
- blob:f6e7c334369f11ac91d3af79803d3d564af227c1  engine/konnektor.py
- blob:ff06825c68e23098fea66dfd6ab08d595baa0a06  engine/schreiben.py
- blob:c0a2663b0bcf2b0d6f1148b9d1e35443f4ab348d  engine/schreiben_git.py
- blob:5b08eb3fb3a4878d5517bc5d415aee2d7919139f  engine/texte_de.py
- blob:fdb019f1b0ed39d096801188b1448d01d8e397b6  engine/texte_en.py

## Geprüfte Dateien

- sha256:07fc03feb194ea3433973d876f50f36dc85048e0ff74ed887322d3fa1b70fda7  engine/anmeldung.py
- sha256:36d5af37e2bf69741cd0e62c3f2492f2ff9bfcd44be8502a0144137b8887f42d  engine/konnektor.py
- sha256:d504084249fa97d00ca8fa878e3cfdebe64200431ac83944e35481140d48c6a1  engine/schreiben.py
- sha256:2864b3b5e0eea4e7dd9d433e87987d0883430481cdcdb7d24d108fe2d6e895a5  engine/schreiben_git.py
- sha256:449f443189f05d67bb06023b88a3d2afe68ab71545d60b8513e81d6609613942  engine/texte_de.py
- sha256:fb7be700d9aa5f71cd5a8447bfa3efa33d5ab7f3289b5e624bf06e12c53d8d57  engine/texte_en.py

## Prüfbasis

- base: 48da8b919afe55565137893fe5d1b9ea3dfe7323
- blob:1eba27cf3188911b1bcbd1632b569183c473a4fc  engine/anmeldung.py
- blob:f6e7c334369f11ac91d3af79803d3d564af227c1  engine/konnektor.py
- blob:ff06825c68e23098fea66dfd6ab08d595baa0a06  engine/schreiben.py
- blob:c0a2663b0bcf2b0d6f1148b9d1e35443f4ab348d  engine/schreiben_git.py
- blob:5b08eb3fb3a4878d5517bc5d415aee2d7919139f  engine/texte_de.py
- blob:fdb019f1b0ed39d096801188b1448d01d8e397b6  engine/texte_en.py
