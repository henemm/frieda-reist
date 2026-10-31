---
entity_id: veroeffentlichen-warnung-142
type: module
created: 2026-10-31
updated: 2026-10-31
status: draft
version: "1.0"
tags: [veroeffentlichen, betrieb, tor, warnung, alarm, schreibweg, start-ende]
---

# Veröffentlichen hält bei einer Warnung im Plan einer Reise alles an (#142)

Workflow: `fix-142-veroeffentlichen-warnung` · Grundlage: `docs/context/veroeffentlichen-warnung-142.md` · Product Owner hat am 31.10.2026 entschieden: alle sechs Punkte des Issues in einem Zug.

## Approval

- [ ] Approved

## Purpose

Eine Inhaltsfrage einer einzelnen Reise (eine Warnung im Plan) darf das Veröffentlichen nie anhalten, und ein wirklicher Fehler muss jemanden erreichen, statt still liegen zu bleiben. Sechs Punkte:

1. Inhalt sperrt nie: nur die Software-Tests und ein Baufehler einer Reise halten etwas an.
2. Eine Reise hält die anderen nicht auf.
3. Schreibweg und Tor prüfen dasselbe; der Schreibweg nennt neue Warnungen in seiner Antwort.
4. Kein Wiederholen ohne Änderung: ein roter Stand wird nicht alle 5 Minuten neu geprüft (rund 6 Minuten pytest je Lauf).
5. Alarm nach 30 Minuten Rot, genau einmal: an den Betrieb und an die Organisator:innen der betroffenen Reise(n).
6. Start und Ende des Plans setzt ein Werkzeug des Konnektors.

## Problem und Ursache (belegt)

- `betrieb/veroeffentlichen.sh:70` lässt vor allen Reisen `pytest engine/tests tests` laufen. `tests/` ist der Testordner des privaten Reisen-Repos. Ist irgendetwas rot, bricht der Lauf ab (Zeile 71: „Prüfungen rot, nichts veröffentlicht“), keine Reise geht online, der Stand wird nicht gemerkt.
- Die Tests im Reisen-Repo enthalten Schnappschüsse des Inhalts der echten Reisen (feste Warnungslisten, Tageszahlen, Summen in km und Stunden, Bildanzahlen). Jede Änderung über den Schreibweg kann sie rot machen, auch ohne Fehler. Das Tor prüft damit den Inhaltsstand, nicht die Software.
- Der Probebau des Schreibwegs (`engine/schreiben.py:2759 probebau`) lehnt nur bei `bauen.BauFehler` ab, Warnungen lässt er durch. `bauen.py` als Kommandozeile endet bei Warnungen mit Exit 0 (`engine/bauen.py:1286-1297`), `deploy.sh:28` sperrt bei Warnungen also nicht. Schreibweg und Tor prüfen den Inhalt damit gleich (beide sperren nur bei Baufehler); die Sperre kam allein aus pytest über `tests/`.
- `veroeffentlichen.sh:61` vergleicht nur mit dem zuletzt gelungenen Stand (`<FR_DIENST>/veroeffentlicht`). Ein roter Stand wird daher bei jedem Timer-Lauf (alle 5 Minuten, dazu nach jedem Schreibvorgang) neu geprüft.
- Ein Fehlschlag meldet niemandem etwas; nur der Erfolgsstempel bleibt aus. Der Monitor der Instanz merkt das erst nach etwa 2 Stunden (`docs/betrieb.md`, Überwachung).
- Start und Ende des Plans (`start.ort`, `start.datum`, `ende.ort`, `ende.datum` in `plan/routen.yaml`) setzt kein Werkzeug. `reise_aendern` (`engine/schreiben.py:2419`, Text Zeile 2459) verweist nur darauf („stehen in plan/routen.yaml“), `REISE_AENDERN` in `engine/konnektor.py` (um Zeile 2534) sagt „stehen in den Tagen“.

## Source

- **Files:** `betrieb/veroeffentlichen.sh`, `betrieb/deploy.sh`, `betrieb/gemeinsam.sh` (nur `fr_melden`, unverändert), `engine/waechter.py`, `engine/schreiben.py`, `engine/konnektor.py`
- **Identifier:** `Schreiber.probebau`, `Schreiber.schreiben`, `reise_aendern`, `WERKZEUGE`, `AKTIONEN`, `ONTOLOGIE_AKTION`, `REISE_AENDERN`, `organisator_von`, `rueckmeldungen.meldung_anlegen`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `bauen.Bauer(...).daten()` | Funktion | liefert `route.warnungen` (Liste von `{bezug, text}`, `engine/routen.py:304 warne`) und wirft `BauFehler` |
| `rueckmeldungen.meldung_anlegen` | Funktion | Meldung an Personen mit `schluessel` gegen Doppelte |
| `waechter.organisator_von` | Funktion | Organisator:innen einer Reise |
| `fr_melden` (`betrieb/gemeinsam.sh`) | Shell-Funktion | Nachricht an den Betreiber über `FR_MELDEN` |
| `ZEIT_GESAMT = 25` (`engine/schreiben.py:58`) | Konstante | Zeitgrenze des Schreibwegs aus `docs/specs/betrieb/schreibweg-zeitgrenzen.md` (#118) |
| `docs/adr/0001-kern.md` | ADR | Prüfstelle (siehe unten) |

## Scope

- **Affected Files:** `betrieb/veroeffentlichen.sh`, `betrieb/deploy.sh`, `betrieb/einstellungen.beispiel`, `engine/waechter.py`, `engine/schreiben.py`, `engine/konnektor.py`, `docs/betrieb.md`, `docs/konnektor.md`, `engine/tests/test_betrieb.py`, `engine/tests/test_schreiben.py`, `engine/tests/test_konnektor.py`, `engine/tests/test_waechter.py`
- **Estimated Changes:** ca. +380/-40 LoC, gut die Hälfte Tests
- **Nicht im Scope:** das private Reisen-Repo (seine `tests/` werden nicht angefasst, nur die Konvention steht in `docs/betrieb.md`); Ableiten von Start und Ende aus dem ersten und letzten Tag im Generator (Product Owner: über den Konnektor, ausdrücklich); asynchrones Schreiben; Änderungen an `bauen.py`.

## Implementation Details

### Festlegungen (alle technischen Entscheidungen dieser Spec)

```
F-1  Exit-Codes von deploy.sh:   0 = gelungen
                                 2 = Bau dieser Reise gescheitert (bauen.py endete nicht mit 0; deterministisch, betrifft nur diese Reise)
                                 1 = alles andere (Reise/Ordner fehlt, ungesicherte Änderungen, Dienste nicht bereit, rsync, Seite fehlt)
                                 Der Bau ist der erste Schritt mit Wirkung (deploy.sh:28 -> "... || exit 2"); danach ändert Exit 2 nichts am Zielordner.
F-2  Eigene Prüfung in deploy.sh (nur wenn FR_GEPRUEFT nicht passt, Handaufruf): pytest nur über engine/tests, nie über tests/ des Reisen-Repos.
     Die Zeile `if [ "${FR_GEPRUEFT:-}" != "$(git -C "$WURZEL" rev-parse HEAD)" ]; then` bleibt wörtlich (ein Test prüft sie). Rot dort: Exit 1.
F-3  Sperrend im Tor (veroeffentlichen.sh) sind nur:  (a) pytest engine/tests rot  -> Art "software"
                                                      (b) deploy.sh Exit 2 einer Reise          -> Art "reise"
     tests/ des Reisen-Repos läuft weiter (wenn der Ordner existiert, gleiche --basetemp-Regel), Rot dort sperrt nie: Zeile "Warnung: Tests des
     Reisen-Repos rot (sperren nicht)" im Protokoll und einmal je Commit fr_melden normal (Merker <FR_DIENST>/veroeffentlichen-warnung = Commit der letzten Meldung).
F-4  Rot-Datei <FR_DIENST>/veroeffentlichen-rot (Überschreibbar für Tests: VF_ROT). Einfache Zeilen "schluessel=wert", UTF-8:
         commit=<voller Hash des roten Stands>
         art=software|reise
         reisen=<Ordnernamen der roten Reisen, durch Komma; leer bei art=software>
         seit=<Zeitpunkt des ERSTEN Rots dieser Rot-Phase, UTC, YYYY-MM-DDTHH:MM:SSZ>
         gemeldet=0|1       (1 = Alarm an den Betrieb dieser Rot-Phase ist raus)
     Rot-Phase = Zeitraum vom ersten roten Lauf bis zum nächsten vollständig grünen. Ein neuer roter Commit aktualisiert commit, art, reisen,
     BEHÄLT aber seit und gemeldet. Der Zustand "gemerkter roter Commit" steht NUR in dieser Datei; die Stand-Datei <FR_DIENST>/veroeffentlicht
     wird weiterhin nur bei vollständigem Erfolg geschrieben (siehe F-5, begründet dort).
F-5  Ablauf eines Laufs mit neuem Stand (neu != veroeffentlicht) oder --immer:
         1. merge/Submodul wie bisher (Fehler dort = Infrastrukturfehler, Exit 1, Rot-Datei unberührt).
         2. Gibt es eine Rot-Datei, ist ihr commit == neu und fehlt --immer:  Zeile "Bekannter roter Stand <kurzer Hash>, übersprungen (Art: ...)",
            dann Alarmprüfung (F-6), dann Exit 0 OHNE Stempel, OHNE Heartbeat, ohne pytest, ohne deploy. Die Läufe nach einem roten Lauf kosten so
            Sekunden statt Minuten.
         3. pytest engine/tests. Rot -> Rot-Datei schreiben/aktualisieren (art=software), Alarmprüfung, Exit 1, keine Reise angefasst, kein Stempel.
         4. tests/ des Reisen-Repos (F-3), nur Warnung.
         5. Je Reise deploy.sh. Exit 0: merken als gelungen. Exit 2: Reise in die Liste "rot", weiter mit der nächsten Reise. Anderer Nicht-Null:
            Infrastrukturfehler -> Schleife endet sofort, Exit 1, Rot-Datei UNBERÜHRT (nichts wird gemerkt, der Timer wiederholt den Lauf).
         6. Freischalten (freischalten.sh) nur für die Reisen, deren Deploy gelungen ist; gescheiterte Reisen bleiben auf ihrem letzten guten
            Stand (deploy.sh kopiert erst nach gelungenem Bau).
         7. Ergebnis: alle Reisen gelungen -> Rot-Datei löschen, Stand schreiben, zustellen, Stempel und Heartbeat (wie bisher).
                      mindestens eine Reise rot -> Rot-Datei schreiben/aktualisieren (art=reise), Stand NICHT schreiben, Alarmprüfung, Exit 1,
                      KEIN Stempel, KEIN Heartbeat (Teil-Erfolg ist kein fachlicher Erfolg: Readiness statt Liveness). Die gelungenen Reisen sind online.
     Begründung zum Stand (Widerspruchsprüfung): Würde der Stand bei einer roten Reise gemerkt, ginge der nächste Lauf in den Zweig "nichts Neues"
     (veroeffentlichen.sh:61) und würde Stempel und Heartbeat setzen, obwohl die Reise rot ist. Darum bleibt der Stand ungeschrieben, und das
     Überspringen übernimmt die Rot-Datei (Schritt 2). Dort ist es ausdrücklich ohne Stempel und Heartbeat. Ein neuer Commit (auch einer, der die
     rote Reise nicht anfasst) wird wieder vollständig geprüft und gebaut; das ist gewollt, denn die Reise kann inzwischen grün sein.
     "nichts Neues"-Zweig (neu == veroeffentlicht): unverändert, mit Stempel und Heartbeat. Er kann nur eintreten, wenn der Stand vollständig grün war.
     Existiert beim "nichts Neues"-Zweig zufällig eine Rot-Datei mit anderem Commit (Reste), wird sie nicht beachtet; der Stand ist grün, die Datei wird gelöscht.
F-6  Alarmprüfung (nach jedem Lauf, der Rot kennt, auch beim Überspringen nach F-5 Schritt 2):
         jetzt - seit >= Schwelle  (Schwelle = FR_ROT_MELDEN_NACH_MINUTEN, Vorgabe 30, in betrieb/einstellungen.beispiel erklärt;
         für Tests VF_JETZT = Sekunden seit 1970 überschreibt die Uhr)
         dann:  a) art=reise: python engine/waechter.py rot-melden --reisen <reisen> legt je roter Reise EINE Meldung an deren Organisator:innen an
                   (rueckmeldungen.meldung_anlegen, schluessel "veroeffentlichen-rot:<reise>:<seit>", organisator_von wie im Wächter); derselbe
                   schluessel erzeugt nie eine zweite Meldung, der Aufruf ist also bei jedem Lauf gefahrlos.
                b) gemeldet=0: fr_melden high "Veröffentlichen seit <Minuten> Minuten rot" mit Art, Reisen und kurzem Commit, dann gemeldet=1.
                   gemeldet=1: nichts. Bei art=software nur dieser Schritt b), keine Meldung an Personen.
         Fällt fr_melden aus (Exit != 0), bleibt gemeldet=0; der nächste Lauf versucht es wieder.
     VF_ROTMELDEN (nur Tests) ersetzt den Aufruf von engine/waechter.py rot-melden durch eine Attrappe.
F-7  Ort der Logik für Meldungen an Personen: Unterbefehl rot-melden in engine/waechter.py (dort leben organisator_von und das Muster mit
     schluessel). Kein neues Modul, daher keine Änderung der Modulliste in deploy.sh (der Aufruf läuft aus der Wurzel wie waechter.sh).
     Meldungstext: nennt die Reise, dass sie seit der angegebenen Zeit nicht veröffentlicht werden kann, dass Betrieb informiert ist, den
     Befund in einfachen Worten (Baufehler) und dass die Seite bis dahin auf dem letzten guten Stand bleibt. Keine Pfade, keine Adressen.
F-8  Schreibweg: Schreiber.probebau gibt die Warnungen des Baus zurück (Liste von (bezug, text)); Ablehnung bei BauFehler wie bisher.
     Schreiber.schreiben baut VOR dem Werkzeug (vorher = Warnungen des Stands in der Arbeitskopie; wirft der Vorher-Bau BauFehler, ist vorher leer
     und es gibt keinen Abbruch), wendet das Werkzeug an, baut danach (probebau). hinweise = Warnungen nachher, deren (bezug, text) nicht in vorher
     vorkommen, als Zeilen "<bezug>: <text>", höchstens 10 (bei mehr: letzte Zeile "und N weitere"). Die Antwort {"ok", "text", "commit"} bekommt
     das Feld "hinweise" (Liste von Texten) NUR wenn es neue gibt; sonst fehlt das Feld. Für REPO_WERKZEUGE (reise_anlegen) kein Vergleich, kein Feld.
     Beide Bauten laufen innerhalb ZEIT_GESAMT = 25 s (Beispielreise 0,1 s, große Reisen geschätzt etwa 1 s); es gibt keine neue Zeitgrenze.
F-9  Konnektor: engine/konnektor.py hängt antwort["hinweise"] an beiden Stellen, an denen der Text des Schreibwegs weitergegeben wird
     (ca. Zeile 1170 allgemeines Eintragen, ca. Zeile 1453 entscheiden), an den Text: "Neue Hinweise der Prüfung (durch diesen Eintrag
     entstanden, eingetragen ist trotzdem): - ...". Die Hinweise sind kein Fehler: ok bleibt true, Rückgabe-Fehlerkennzeichen bleibt False.
F-10 Neues Werkzeug start_ende_setzen (Aktion "einstellung" wie reise_aendern, also nur Organisator:innen, in ONTOLOGIE_AKTION und AKTIONEN).
     Felder (nur existierende Felder von plan/routen.yaml; im Code belegt: routen.py:1150-1212 liest start.datum, start.ort, ende.datum, ende.ort):
         start_ort   O-…   vorhandener Ort der Reise (id_liste gegen "orte")
         start_datum JJJJ-MM-TT (datum_wert); Pflichtfeld des Plans, darf nicht leer gesetzt werden
         ende_ort    O-…   vorhandener Ort; "" entfernt den Eintrag
         ende_datum  JJJJ-MM-TT; "" entfernt den Eintrag
         grund       Pflicht
     Mindestens eines der vier Felder; ohne Änderung: Ablehnung "Nichts zu ändern". ende_datum vor start_datum (nach der Änderung): Ablehnung.
     Verlauf wie reise_aendern: Eintrag in reise.yaml unter verlauf mit datum, wer, was ("Start des Plans: Datum 2027-05-13 → 2027-05-20; ..."),
     grund. Der Probebau prüft das Ergebnis (Daten aller Tage hängen von start_datum ab; die Antwort sagt das ausdrücklich).
     ende.datum und ende.ort erzeugen im Bau nur Warnungen (routen.py:1204-1212), start.datum fehlt = Baufehler.
     reise_aendern: Antworttext und REISE_AENDERN verweisen auf start_ende_setzen statt auf "plan/routen.yaml" / "in den Tagen".
     Eintrag in WERKZEUGE (engine/schreiben.py), AKTIONEN/ONTOLOGIE_AKTION, die Organisator-Liste in engine/konnektor.py (neben "reise_aendern"),
     Werkzeugdefinition START_ENDE_SETZEN in der Werkzeugliste, Zeile in der Tabelle von docs/konnektor.md.
```

### Festlegungen aus der RED-Phase (Schnittstellen, die die Tests festschreiben)

```
R-1  Prüf-Attrappe VF_PRUEFEN wird je Prüfung mit einem Argument aufgerufen: "$pruefen" engine/tests (Software, sperrt)
     und, falls der Ordner tests/ existiert, "$pruefen" tests (Reisen-Repo, sperrt nie). Ohne VF_PRUEFEN: zwei pytest-Aufrufe.
R-2  Meldungen an Personen: engine/waechter.py rot-melden --reisen <a,b> --seit <YYYY-MM-DDTHH:MM:SSZ>; dahinter die Funktion
     waechter.rot_melden(reisen: list[str], seit: str) -> Liste der angelegten Meldungen. VF_ROTMELDEN bekommt genau dieselben
     Argumente (--reisen <reisen> --seit <seit>).
R-3  VF_JETZT (Sekunden seit 1970) ersetzt die Uhr beim Schreiben von seit UND bei der Alarmprüfung.
R-4  fr_melden (gemeinsam.sh) gibt heute immer 0 zurück (Fehlschlag wird zu einer Warnzeile). F-6 braucht den Erfolg des
     Alarms: das Tor muss den Rückgabewert von FR_MELDEN erkennen (z. B. eigener Aufruf oder eine Variante von fr_melden mit
     Rückgabewert); die übrigen Aufrufer von fr_melden laufen unter set -e und dürfen davon nicht abbrechen.
R-5  Alarmtext an den Betrieb enthält das Wort „rot“ (Betreff „Veröffentlichen seit <Minuten> Minuten rot“ nach F-6).
R-6  Bereits grün vor der Umsetzung (Regressionsschutz, gewollt): test_bau_mit_warnung_sperrt_nicht (AC-5) und in
     test_deploy_exit_2_bei_baufehler_sonst_1 die Fälle „FR_SEITEN fehlt“ und „Reise fehlt“ (Exit 1); test_werkzeuge_je_rolle
     (ohne Schreibweg kein start_ende_setzen), test_zeitgrenzen_liegen_unter_der_des_konnektors (AC-14).
R-7  Hinweis = genau „<bezug>: <text>“; bei mehr als 10 ist die letzte Zeile wörtlich „und N weitere“. Die Warnungen kommen aus
     d["route"]["warnungen"] von bauen.Bauer(...).daten() (der Test patcht dort). probebau gibt eine Liste zurück (leer ohne Warnung).
R-8  Konnektor: unter „Neue Hinweise der Prüfung …“ je Hinweis eine Zeile „- <hinweis>“. Mitwirkende bekommen für start_ende_setzen
     eine Ablehnung mit „nur Organisator:innen“, ohne dass der Schreibweg gerufen wird.
R-9  start_ende_setzen: Antwort bei geändertem start_datum enthält „verschieb“; Verlauf nennt „alt → neu“ mit ISO-Datum
     (z. B. „2027-05-13 → 2027-05-20“); leere ende_ort/ende_datum: Antwort enthält „entfernt“. Ablehnungen: kein Feld oder
     unveränderter Wert -> „Nichts zu ändern“; unbekannter Ort -> Text nennt die ID (O-99); ungültiges Datum -> „JJJJ-MM-TT“;
     leeres start_datum -> „start_datum“; Ende vor Start -> „vor“.
R-10 Meldung von rot-melden enthält „nicht veröffentlicht“, weder „/“ noch „http“; rot_melden gibt beim zweiten Aufruf mit
     demselben seit eine leere Liste zurück.
R-11 Nicht automatisch belegt: der Baufehler-Teil von AC-31 (mit start_ende_setzen lässt sich kein Baufehler erzeugen, den nicht
     schon die Eingabeprüfung abfängt); die Ablehnung bei Baufehler belegt test_probebau_lehnt_ab_und_laesst_nichts_zurueck.
```

### Ablauf-Skizze `veroeffentlichen.sh` (Pseudocode, maßgeblich sind F-3 bis F-6)

```
main:
  Sperre, Zweig/Sauberkeit prüfen                       (unverändert, Überspringen = kein Stempel)
  fetch; neu=origin/main; alt=<veroeffentlicht>
  neu == alt und kein --immer -> zustellen, rot_loeschen, erfolg_melden, Exit 0      (unverändert, plus Aufräumen)
  merge, Submodul                                       (Fehler: Exit 1, Rot-Datei unberührt)
  rot = lies(Rot-Datei)
  rot.commit == neu und kein --immer -> "Bekannter roter Stand ... übersprungen"; alarm_pruefen; Exit 0   (KEIN erfolg_melden)
  pytest engine/tests   rot -> rot_schreiben(software); alarm_pruefen; Exit 1
  pytest tests (falls Ordner)   rot -> Warnung, einmal je Commit fr_melden normal
  für jede Reise: deploy   0 -> gut += reise | 2 -> rot += reise | sonst -> Exit 1 (Infrastruktur, Rot-Datei unberührt)
  für jede Reise in gut: freischalten
  rot leer  -> rot_loeschen; Stand schreiben; zustellen; erfolg_melden; Exit 0
  rot nicht leer -> rot_schreiben(reise, rot); zustellen; alarm_pruefen; Exit 1   (kein Stand, kein Stempel, kein Heartbeat)
```

## Expected Behavior

- **Input:** ein Lauf von `veroeffentlichen.sh` (Timer, nach einem Schreibvorgang oder von Hand, auch mit `--immer`); ein Schreibvorgang über den Konnektor; ein Aufruf des Werkzeugs `start_ende_setzen`.
- **Output:** Exit-Codes und Protokollzeilen nach F-5; Antwort des Schreibwegs mit optionalem Feld `hinweise`; Antwort von `start_ende_setzen` wie bei `reise_aendern` (`Titel, Text`).
- **Side effects:** Dateien `<FR_DIENST>/veroeffentlichen-rot` und `<FR_DIENST>/veroeffentlichen-warnung`; Meldungen in `meldungen.jsonl` der Ablage der betroffenen Reise; Nachrichten über `FR_MELDEN`; ein Commit im Reisen-Repo je `start_ende_setzen` mit Verlaufseintrag in `reise.yaml`.

## Prüfstelle ADR-0001 (zehn Fragen)

| Nr. | Antwort |
|---|---|
| 1 Ontologie statt Sonderfall | Ja, besteht. Punkte 1 bis 5 sind Betrieb ohne Bezug zu einer Reise. Punkt 6 betrifft die Grundform Folge (Start und Ende des Plans, gelten für jede Reiseart: Hüttentour mit Start im Tal wie Städtereise mit Anreise). Warnungen sind ein Prüfergebnis der Software, keine reisespezifische Logik. Nichts Reise- oder Instanzspezifisches in `engine/` und `betrieb/` (Schwelle als Vorgabe, überschreibbar über die Einstellungen). |
| 2 Kein Katalog | Ja, besteht. Keine Art, kein Merkmal eingeführt oder vorausgesetzt. |
| 3 Keine KI in Frieda | Ja, besteht. Alles sind Regeln im Code (Vergleich von Listen, Zeitschwelle, Dateien); der Alarm rechnet und meldet, deutet nichts. Die Warnungen bewertet der AI-Client im Gespräch. |
| 4 Die Tür | Ja, besteht. Neues Werkzeug `start_ende_setzen` im Konnektor, neue Hinweise in der Antwort jedes Schreibvorgangs, dokumentiert in `docs/konnektor.md`. Die Meldung bei Rot erscheint den Organisator:innen im Konnektor (Überblick, `rueckmeldungen`) wie die Meldungen des Wächters. |
| 5 Herkunft | Ja, besteht. Start und Ende sind Pläne-Eckdaten, keine Aussage über ein Ding mit Merkmal; sie tragen Person, Datum und Grund im Verlauf. Keine neue Aussage ohne Herkunft entsteht. |
| 6 Rollen entscheiden | Ja, besteht. `start_ende_setzen` nur für Organisator:innen, mit Pflicht-Grund und Verlauf; die KI entscheidet nichts. Die Hinweise nach einem Eintrag ändern nichts selbst. |
| 7 IDs und Verlauf | Ja, besteht. Keine ID wird vergeben oder gelöscht (`start_ort` verweist auf vorhandene O-IDs); jede Änderung von Start und Ende steht im Verlauf (`reise.yaml`) und als Commit. |
| 8 PWA | Ja, besteht. Die Seite ändert sich nicht; die Daten der Tage ändern sich durch `start_datum` wie bisher durch den Plan, die Seite zeigt sie nach dem Veröffentlichen. Ein roter Bau lässt die letzte gute Seite online (unverändert, ausdrücklich getestet). Kein neuer Baustein der Oberfläche, kein Browser-Rundgang nötig. |
| 9 Claude Code | Ja, besteht. Reiseinhalte entstehen weiter im AI-Client; Claude Code ändert nur Software und Betrieb. Start und Ende setzt man mit dem neuen Werkzeug im AI-Client, nicht von Hand in `routen.yaml`. |
| 10 Dokumentation | `docs/betrieb.md` (Veröffentlichen, Überwachung, Konvention für `tests/`), `docs/konnektor.md` (Werkzeugtabelle). Die Spec berührt den Kern nur in Frage 4 und verweist auf `docs/adr/0001-kern.md`; ein Hinweis darauf steht in der Konvention in `docs/betrieb.md`. |

## Known Limitations

- Ohne die Inhaltsprüfungen in `tests/` des Reisen-Repos im Tor fängt nur der Bau (Baufehler) Inhaltsfehler. Wer dort Prüfungen braucht, die sperren, schreibt sie als Bau-Regel in die Software (eigenes Issue) und nicht als Schnappschuss. Die Konvention steht in `docs/betrieb.md`.
- Ein roter Stand wird erst bei einem neuen Commit oder mit `--immer` erneut geprüft. Ein Baufehler, der nur durch Umgebungsdaten außerhalb des Repos verschwindet, braucht `--immer`. Der Alarm nach 30 Minuten macht das sichtbar.
- Der Vorher-Bau im Schreibweg verdoppelt dessen Bauzeit; sehr große Reisen könnten dadurch die 25 s von `ZEIT_GESAMT` eher erreichen (Meldung wie in der Spec der Zeitgrenzen). Das Protokoll „Fertig … in … s“ zeigt es.
- Ist die Reise schon vor dem Eintrag mit Baufehler rot, gibt es keinen Vergleichsstand: `vorher` ist leer, alle Warnungen des Ergebnisses gelten als neu.

## Definition of Done

- [ ] Jede Acceptance Criterion ist durch einen automatischen Test belegt
- [ ] Eine Warnung im Plan einer Reise hält das Veröffentlichen nicht an (Test mit Attrappe, Beispielreise mit Warnung)
- [ ] Eine rote Reise hält die anderen nicht auf; kein Stempel, kein Heartbeat bei Rot, auch nicht beim Überspringen
- [ ] Ein roter Commit wird nicht erneut geprüft; Infrastrukturfehler werden weiter wiederholt
- [ ] Alarm kommt genau einmal je Rot-Phase und Ziel und nicht früher als nach der Schwelle
- [ ] `start_ende_setzen` ist im Konnektor, in `docs/konnektor.md` und im Rollen-Test; `reise_aendern` verweist darauf
- [ ] `docs/betrieb.md` beschreibt Tor, Rot-Datei, Alarm, Schwelle, Exit-Codes und die Konvention für `tests/`
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests` ist grün ohne echte Reisen
- [ ] Keine Namen echter Reisen, Personen oder Server in Code, Tests, Doku (nur Beispielreise, Ida, Karl, erfundene Orte)

## Acceptance Criteria

**Punkt 1 – Inhalt sperrt nie**

- **AC-1:** Given ein Stand, bei dem `tests/` des Reisen-Repos rot ist, `engine/tests` und alle Bauten aber grün / When `veroeffentlichen.sh` läuft / Then alle Reisen werden gebaut und freigeschaltet, der Stand wird gemerkt, Stempel und Heartbeat kommen (Exit 0), das Protokoll enthält „Tests des Reisen-Repos rot (sperren nicht)“, und `fr_melden normal` wurde genau einmal aufgerufen
  - Test: `test_veroeffentlichen_rote_reisetests_sperren_nicht`
- **AC-2:** Given derselbe Stand wie in AC-1 / When `--immer` läuft und danach noch einmal `--immer` auf demselben Commit / Then die Nachricht an den Betrieb kommt für diesen Commit nur einmal (Merker `veroeffentlichen-warnung`); ein neuer Commit mit rotem `tests/` meldet wieder einmal
  - Test: `test_veroeffentlichen_warnung_der_reisetests_einmal_je_commit`
- **AC-3:** Given `engine/tests` ist rot / When `veroeffentlichen.sh` läuft / Then Exit 1, keine Reise wird gebaut, kein Stand, kein Stempel, kein Heartbeat, die Rot-Datei hat `art=software` und eine `seit`-Zeit
  - Test: `test_veroeffentlichen_prueft_einmal_fuer_alle_reisen` (angepasst)
- **AC-4:** Given `deploy.sh` und `veroeffentlichen.sh` im Repo / When ihr Text gelesen wird / Then die Prüfung in `deploy.sh` und im Tor läuft über `engine/tests` und nicht über `tests/` (pytest-Zeile von `deploy.sh` enthält kein `$WURZEL/tests`), die Zeile mit `FR_GEPRUEFT` ist unverändert, beide haben `--basetemp "$pruef_tmp"`
  - Test: `test_deploy_prueft_nur_die_tests_der_software` und `test_veroeffentlichen_und_deploy_pruefen_in_eigenem_testordner` (bleibt)
- **AC-5:** Given die Beispielreise mit einer Warnung im Plan (etwa Lücke im Ablauf) / When `bauen.py` und `deploy.sh`-Bau laufen / Then der Bau endet mit Exit 0 und `deploy.sh` kopiert die Seite (Warnung sperrt nie)
  - Test: `test_bau_mit_warnung_sperrt_nicht` (in `test_betrieb.py`, mit erfundenem Testdaten-Zusatz zur Beispielreise in `tmp_path`)

**Punkt 2 – Eine Reise hält die anderen nicht auf**

- **AC-6:** Given `deploy.sh` meldet für `beispielreise` Exit 2 und für `zweitreise` Exit 0 / When das Tor läuft / Then `zweitreise` wird gebaut und freigeschaltet, `beispielreise` nicht (`frei.log` enthält nur `zweitreise`), Exit 1, die Rot-Datei hat `art=reise` und `reisen=beispielreise`, der Stand wird NICHT geschrieben
  - Test: `test_veroeffentlichen_eine_rote_reise_haelt_die_anderen_nicht_auf`
- **AC-7:** Given `deploy.sh` mit einem Bauscheitern (Reise mit Baufehler in `tmp_path`) / When `deploy.sh <reise>` läuft / Then Exit 2; mit fehlendem Zielordner `FR_SEITEN` Exit 1
  - Test: `test_deploy_exit_2_bei_baufehler_sonst_1`
- **AC-8:** Given Exit 1 (Infrastrukturfehler) bei der ersten Reise / When das Tor läuft / Then die Schleife endet, die zweite Reise wird nicht angefasst, Exit 1, die Rot-Datei wird nicht angelegt und eine vorhandene nicht verändert
  - Test: `test_veroeffentlichen_infrastrukturfehler_wird_nicht_gemerkt_und_wiederholt` (siehe auch AC-11)

**Punkt 3 – Schreibweg und Tor prüfen dasselbe**

- **AC-9:** Given eine Reise ohne Warnung / When ein Werkzeug des Schreibwegs einen Eintrag macht, der eine neue Warnung erzeugt (etwa einen Tag mit Lücke) / Then die Antwort hat `ok: true` und das Feld `hinweise` mit der neuen Warnung als „<bezug>: <text>“; der Eintrag ist im Repo
  - Test: `test_neue_warnung_steht_als_hinweis_in_der_antwort` (`test_schreiben.py`)
- **AC-10:** Given eine Reise, die schon Warnungen hat / When ein Eintrag keine neue Warnung erzeugt (gleicher `(bezug, text)`-Satz) / Then die Antwort hat kein Feld `hinweise`
  - Test: `test_keine_hinweise_ohne_neue_warnung`
- **AC-11:** Given ein Eintrag, der einen Baufehler erzeugt / When der Schreibweg läuft / Then Ablehnung wie bisher („nichts geändert“), keine Hinweise, Arbeitskopie zurückgesetzt
  - Test: `test_probebau_lehnt_ab_und_laesst_nichts_zurueck` (bleibt, ergänzt um die Prüfung ohne Feld `hinweise`)
- **AC-12:** Given mehr als 10 neue Warnungen / When die Antwort gebildet wird / Then `hinweise` hat 10 Zeilen plus „und N weitere“
  - Test: `test_hinweise_sind_begrenzt`
- **AC-13:** Given eine Schreibweg-Antwort mit `hinweise` / When der Konnektor sie weitergibt (allgemeines Eintragen und `entscheiden`) / Then der Text an die Claude-App enthält „Neue Hinweise der Prüfung“ und jede Zeile; der Konnektor meldet weiterhin „Eingetragen und gesichert“ (kein Fehler); ohne `hinweise` ändert sich der Text nicht
  - Test: `test_konnektor_haengt_hinweise_an_den_text` (`test_konnektor.py`)
- **AC-14:** Given ein Schreibvorgang mit dem Vorher-Bau / When die Zeitgrenzen aus #118 gelten / Then `ZEIT_GESAMT + ZEIT_PRUEFUNG < proxy_read_timeout` bleibt wahr und die Beispielreise bleibt deutlich unter `ZEIT_GESAMT`
  - Test: `test_zeitgrenzen_liegen_unter_der_des_konnektors` (bleibt unverändert grün)

**Punkt 4 – Kein Wiederholen ohne Änderung**

- **AC-15:** Given ein roter Lauf auf Commit X (Software rot oder Reise rot) / When der nächste Lauf auf demselben Commit X ohne `--immer` kommt / Then pytest und `deploy.sh` laufen nicht (`pruefen.log` und `deploy.log` ohne neue Einträge), das Protokoll enthält „Bekannter roter Stand“, Exit 0
  - Test: `test_veroeffentlichen_roter_stand_wird_nicht_erneut_geprueft`
- **AC-16:** Given das Überspringen aus AC-15 / When der Lauf endet / Then `veroeffentlichen-erfolg` wird nicht berührt (Datei fehlt oder Änderungszeit unverändert) und `curl` (Heartbeat) wird nicht aufgerufen
  - Test: `test_veroeffentlichen_ueberspringen_ohne_stempel_und_heartbeat`
- **AC-17:** Given der rote Commit X / When `--immer` läuft oder ein neuer Commit Y kommt / Then es wird neu geprüft und gebaut; sind Prüfung und Bauten grün, wird die Rot-Datei gelöscht, der Stand geschrieben, Stempel und Heartbeat kommen
  - Test: `test_veroeffentlichen_gruen_raeumt_die_rot_datei_auf`
- **AC-18:** Given ein Infrastrukturfehler (Exit 1 aus `deploy.sh`, oder `merge`/Submodul scheitert) / When der nächste Lauf auf demselben Commit kommt / Then es wird erneut versucht (Deploy läuft wieder); der Fehler wurde nicht in der Rot-Datei gemerkt
  - Test: `test_veroeffentlichen_fehlschlag_wird_wiederholt` (angepasst)
- **AC-19:** Given der Zweig „nichts Neues“ nach vollständig grünem Lauf / When der Timer läuft / Then Stempel und Heartbeat wie bisher
  - Test: `test_veroeffentlichen_heartbeat_nur_bei_erfolg` und `test_veroeffentlichen_stempel_nur_bei_erfolg` (angepasst)

**Punkt 5 – Alarm nach 30 Minuten**

- **AC-20:** Given ein roter Lauf mit `seit` vor 29 Minuten (VF_JETZT) / When die Alarmprüfung läuft / Then weder `fr_melden` noch `rot-melden` werden aufgerufen
  - Test: `test_veroeffentlichen_kein_alarm_vor_der_schwelle`
- **AC-21:** Given `seit` vor 30 Minuten oder mehr / When die Alarmprüfung läuft (auch beim Überspringen) / Then `fr_melden high` wird genau einmal aufgerufen und `gemeldet=1` gesetzt; weitere Läufe (auch mit neuem roten Commit, `seit` bleibt) rufen es nicht erneut auf
  - Test: `test_veroeffentlichen_alarm_genau_einmal`
- **AC-22:** Given `art=reise` mit roter Reise `beispielreise` / When der Alarm fällig ist / Then `waechter.py rot-melden` wird mit `--reisen beispielreise` aufgerufen; bei `art=software` nicht
  - Test: `test_veroeffentlichen_alarm_art_software_nur_an_den_betrieb`
- **AC-23:** Given die Beispielreise und ein roter Zustand / When `waechter.py rot-melden --reisen beispielreise` zweimal mit demselben `seit` läuft / Then in `meldungen.jsonl` steht genau eine Meldung mit `schluessel` „veroeffentlichen-rot:beispielreise:<seit>“, `an` = alle Organisator:innen (Ida), `bezug` „reise“, der Text enthält keine Pfade oder Adressen; mit anderem `seit` entsteht eine neue
  - Test: `test_rot_melden_legt_eine_meldung_je_phase_an_die_organisatoren_an` (`test_waechter.py`)
- **AC-24:** Given `fr_melden` schlägt fehl (Attrappe Exit 1) / When der Alarm fällig ist / Then `gemeldet` bleibt 0 und der nächste Lauf versucht es wieder
  - Test: `test_veroeffentlichen_alarm_wiederholt_bei_ausfall_des_meldewegs`
- **AC-25:** Given `FR_ROT_MELDEN_NACH_MINUTEN=10` / When `seit` vor 11 Minuten liegt / Then der Alarm kommt; die Vorgabe 30 steht in `betrieb/einstellungen.beispiel` und `test_beispiel_einstellungen_sind_vollstaendig` bleibt grün
  - Test: `test_veroeffentlichen_schwelle_ist_einstellbar`
- **AC-26:** Given ein zweiter roter Commit in derselben Rot-Phase / When die Rot-Datei aktualisiert wird / Then `commit` ist der neue, `seit` und `gemeldet` bleiben
  - Test: `test_veroeffentlichen_seit_bleibt_ueber_neue_rote_commits`

**Punkt 6 – Start und Ende im Konnektor**

- **AC-27:** Given eine Organisator:in (Ida) und die Beispielreise / When `start_ende_setzen` mit `start_datum`, `ende_datum` und `grund` läuft / Then `start.datum` und `ende.datum` in `plan/routen.yaml` haben die neuen Werte, `reise.yaml` hat einen Verlaufseintrag mit Datum, Person, „was“ und `grund`, die Daten der Tage verschieben sich, die Antwort nennt das
  - Test: `test_start_ende_setzen_aendert_plan_und_schreibt_verlauf`
- **AC-28:** Given Karl als Mitwirkenden und als Gast / When er `start_ende_setzen` aufruft / Then Ablehnung wegen der Rolle, nichts geändert; die Rollentabelle des Schreibwegs und `test_werkzeuge_je_rolle` führen das Werkzeug nur bei Organisator:innen
  - Test: `test_rollen_je_werkzeug_des_schreibwegs` (angepasst), `test_werkzeuge_je_rolle` (angepasst)
- **AC-29:** Given eine Anfrage ohne `grund`, ohne jedes der vier Felder, mit unverändertem Wert, mit unbekanntem Ort (`O-99`), mit ungültigem Datum („31.02.2027“, „morgen“), mit `start_datum` leer oder mit `ende_datum` vor `start_datum` / When das Werkzeug läuft / Then jeweils eine Ablehnung mit verständlichem Grund und Arbeitskopie unverändert
  - Test: `test_start_ende_setzen_lehnt_ungueltiges_ab` (parametrisiert)
- **AC-30:** Given `ende_ort` oder `ende_datum` als leerer Text / When das Werkzeug läuft / Then der Eintrag `ende.ort` bzw. `ende.datum` wird entfernt, der Probebau besteht (nur Warnung möglich), die Antwort nennt es
  - Test: `test_start_ende_setzen_entfernt_ende`
- **AC-31:** Given ein `ende_datum`, das im Bau eine Warnung erzeugt (Plan endet an einem anderen Tag), oder eine Änderung, die einen Baufehler erzeugt / When der Schreibweg läuft / Then der Baufehler lehnt ab (nichts geändert); die Warnung kommt als `hinweise` in der Antwort (AC-9)
  - Test: `test_start_ende_setzen_warnung_kommt_als_hinweis`
- **AC-32:** Given der Konnektor / When die Werkzeugliste geprüft wird / Then `start_ende_setzen` steht in `WERKZEUGE`, `AKTIONEN`, der Werkzeugliste des Konnektors (nur bei eingerichtetem Schreibweg, nur für Organisator:innen) und in der Tabelle von `docs/konnektor.md`; `reise_aendern` (Antwort und Beschreibung) nennt `start_ende_setzen`
  - Test: `test_werkzeugtabelle_stimmt_mit_dem_konnektor` (vorhanden, deckt `docs/konnektor.md` ab) und `test_reise_aendern_verweist_auf_start_ende_setzen`

**Dokumentation**

- **AC-33:** Given `docs/betrieb.md` / When der Text gelesen wird / Then die Abschnitte Veröffentlichen und Überwachung beschreiben Sperrkriterien, Exit-Codes, Rot-Datei, Überspringen ohne Stempel, Alarm mit Schwelle und Einstellung `FR_ROT_MELDEN_NACH_MINUTEN`, und die Konvention „Inhaltsschnappschüsse im `tests/` des Reisen-Repos sperren nicht und gehören dort gekennzeichnet oder entfernt“
  - Test: `test_betrieb_md_nennt_rot_datei_alarm_und_konvention`

## Test Plan

**`engine/tests/test_betrieb.py`** (Fixture `vf` erweitern: Deploy-Attrappe mit Exit-Code je Reise über Dateien `kaputt-<reise>` (Exit 2) und `infra-<reise>` (Exit 1), getrennte Prüfattrappen `rot` (Software) und `rot-reise` (tests/), `fr_melden`-Attrappe über `FR_MELDEN` mit Protokoll und `melden-aus`, curl-Attrappe wie bisher, `VF_JETZT`, `VF_ROT`, `VF_ROTMELDEN`):

Angepasst, weil sie das alte Verhalten festschreiben:

| Bestehender Test | Anpassung |
|---|---|
| `test_veroeffentlichen_fehlschlag_wird_wiederholt` | „kaputt“ wird zu Infrastrukturfehler (Exit 1): wird wiederholt (AC-18); Baufehler (Exit 2) wird dagegen nicht wiederholt (AC-15) |
| `test_veroeffentlichen_prueft_einmal_fuer_alle_reisen` | rote Software-Tests: Exit 1, Rot-Datei `art=software`; nächster Lauf auf demselben Commit überspringt (kein Eintrag mehr in `pruefen.log`), erst `--immer` oder neuer Commit prüft wieder; Erwartung „pruefen.log == p, p“ entsprechend; Zeile mit `FR_GEPRUEFT` bleibt (AC-3, AC-15) |
| `test_veroeffentlichen_heartbeat_nur_bei_erfolg` | „Deploy fehlgeschlagen“ als Baufehler (Exit 2): kein Ping; Überspringen auf rotem Commit: kein Ping; nach Reparatur (neuer Commit): ein Ping (AC-16, AC-17, AC-19) |
| `test_veroeffentlichen_stempel_nur_bei_erfolg` | wie oben für den Stempel; „erst `kaputt` löschen und denselben Commit erneut laufen lassen“ gilt nicht mehr, dafür neuer Commit oder `--immer` |
| `test_veroeffentlichen_nur_bei_neuem_stand` | unverändert grün (Regression) |
| `test_veroeffentlichen_und_deploy_pruefen_in_eigenem_testordner` | unverändert grün; ggf. um den `tests/`-Lauf des Tors ergänzt |

Neu: `test_veroeffentlichen_rote_reisetests_sperren_nicht`, `test_veroeffentlichen_warnung_der_reisetests_einmal_je_commit`, `test_deploy_prueft_nur_die_tests_der_software`, `test_bau_mit_warnung_sperrt_nicht`, `test_veroeffentlichen_eine_rote_reise_haelt_die_anderen_nicht_auf`, `test_deploy_exit_2_bei_baufehler_sonst_1`, `test_veroeffentlichen_infrastrukturfehler_wird_nicht_gemerkt_und_wiederholt`, `test_veroeffentlichen_roter_stand_wird_nicht_erneut_geprueft`, `test_veroeffentlichen_ueberspringen_ohne_stempel_und_heartbeat`, `test_veroeffentlichen_gruen_raeumt_die_rot_datei_auf`, `test_veroeffentlichen_kein_alarm_vor_der_schwelle`, `test_veroeffentlichen_alarm_genau_einmal`, `test_veroeffentlichen_alarm_art_software_nur_an_den_betrieb`, `test_veroeffentlichen_alarm_wiederholt_bei_ausfall_des_meldewegs`, `test_veroeffentlichen_schwelle_ist_einstellbar`, `test_veroeffentlichen_seit_bleibt_ueber_neue_rote_commits`, `test_betrieb_md_nennt_rot_datei_alarm_und_konvention`.

**`engine/tests/test_waechter.py`:** `test_rot_melden_legt_eine_meldung_je_phase_an_die_organisatoren_an` (AC-23).

**`engine/tests/test_schreiben.py`:** `test_neue_warnung_steht_als_hinweis_in_der_antwort`, `test_keine_hinweise_ohne_neue_warnung`, `test_hinweise_sind_begrenzt`, `test_start_ende_setzen_aendert_plan_und_schreibt_verlauf`, `test_start_ende_setzen_lehnt_ungueltiges_ab`, `test_start_ende_setzen_entfernt_ende`, `test_start_ende_setzen_warnung_kommt_als_hinweis`; angepasst: `test_probebau_lehnt_ab_und_laesst_nichts_zurueck`, `test_rollen_je_werkzeug_des_schreibwegs`, `test_reise_aendern_und_plaene` (neuer Verweistext); unverändert grün: `test_zeitgrenzen_liegen_unter_der_des_konnektors`.

**`engine/tests/test_konnektor.py`:** `test_konnektor_haengt_hinweise_an_den_text`, `test_reise_aendern_verweist_auf_start_ende_setzen`; angepasst: `test_werkzeuge_je_rolle`; die Abgleich-Prüfung zwischen `docs/konnektor.md` und `WERKZEUGE` bleibt grün.

## Betroffene Dateien

| Datei | Art | Änderung |
|---|---|---|
| `betrieb/veroeffentlichen.sh` | MODIFY | Ablauf F-3 bis F-6, Rot-Datei, Überspringen, Alarm, Schleife je Reise, Freischalten nur für Gelungene |
| `betrieb/deploy.sh` | MODIFY | Exit 2 bei Bauscheitern; eigene Prüfung nur über `engine/tests` |
| `betrieb/einstellungen.beispiel` | MODIFY | `FR_ROT_MELDEN_NACH_MINUTEN` mit Vorgabe 30 und Erklärung |
| `engine/waechter.py` | MODIFY | Unterbefehl `rot-melden` (Meldung an Organisator:innen, `schluessel`) |
| `engine/schreiben.py` | MODIFY | `probebau` liefert Warnungen; Vorher-Bau, Feld `hinweise`; Werkzeug `start_ende_setzen`; Text von `reise_aendern` |
| `engine/konnektor.py` | MODIFY | `START_ENDE_SETZEN` (Definition, Rolle, Aktion), Hinweise an zwei Stellen, `REISE_AENDERN`-Text |
| `docs/betrieb.md` | MODIFY | Veröffentlichen, Überwachung, Konvention |
| `docs/konnektor.md` | MODIFY | Zeile in der Werkzeugtabelle |
| `engine/tests/test_betrieb.py`, `test_schreiben.py`, `test_konnektor.py`, `test_waechter.py` | MODIFY | siehe Test Plan |
| `docs/specs/betrieb/veroeffentlichen-warnung-142.md` | CREATE | diese Spec |
| `beispiel/reisen/beispielreise/…` | nur falls nötig | erfundene Ergänzung, falls ein Test eine Warnung braucht; sonst Testdaten in `tmp_path` |

## Risks

- **Tor lässt Kaputtes durch oder hält wieder alles an:** abgesichert durch die Attrappen im Veröffentlichen-Test. Der Bau (`BauFehler`) bleibt das Tor je Reise; der volle Bau kann nach `daten()` nur noch an der Vorlage scheitern (`bauen.py:1070`), das ist Software und von `engine/tests` abgedeckt.
- **Verlust von Prüfungen:** Die Inhaltstests des Reisen-Repos sperren nicht mehr. Ausgleich: Warnung und Nachricht an den Betrieb bei Rot sowie Konvention. Das Reisen-Repo muss selbst entscheiden, was es kennzeichnet oder streicht.
- **Falsch gemerkter Rotstand:** Ein vorübergehender Fehler darf nicht dauerhaft festgehalten werden. Gemerkt werden nur deterministische Fehler (Software-Tests rot, Exit 2 des Baus); alles andere ist Infrastrukturfehler und wird vom Timer wiederholt. Ein Bau, der wegen einer Umgebung scheitert, endet mit Exit 2 und braucht `--immer`; der Alarm nach 30 Minuten macht es sichtbar.
- **Alarmlärm:** begrenzt durch `gemeldet` (Betrieb, einmal je Rot-Phase) und `schluessel` (Organisator:innen, einmal je Reise und Phase). Eine zweite Reise, die in derselben Phase rot wird, bekommt ihre Meldung an Personen, der Betrieb nicht nochmals (bewusst: die Phase läuft schon).
- **Zeit im Schreibweg:** Vorher-Bau kostet zusätzlich eine Bauzeit innerhalb von `ZEIT_GESAMT`; Messwerte liefert das Protokoll „Fertig … in … s“.
- **Start-Datum verschiebt alle Tage:** `start_datum` ändert die Datumsangaben des ganzen Plans, bestehende Buchungen und Fixpunkte bleiben daran gebunden. Die Antwort sagt das, der Probebau und die Hinweise zeigen Folgen (Ende-Warnung), und der Verlauf hält es fest. Wer es nicht will, gibt es nicht ein; das Werkzeug ändert nichts anderes.
- **Öffentliches Repo:** keine echten Reisen, Personen, Server in Code, Tests, Doku; Tests nur mit Beispielreise, Ida, Karl und erfundenen Orten.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine neue
- **Rationale:** Betriebs- und Schreibwegdetail innerhalb der Grundformen (Folge: Start und Ende des Plans); Prüfstelle oben vollständig bestanden. Eine Änderung des Kerns ist nicht nötig.

## Changelog

- 2026-10-31: Initial spec created (Product Owner entschied am 31.10.2026: alle sechs Punkte in einem Zug)
- 2026-10-31: RED-Phase: Schnittstellen R-1 bis R-6 festgelegt (Prüf-Attrappe je Prüfung, rot-melden mit --seit, VF_JETZT, Rückgabewert des Meldewegs)
