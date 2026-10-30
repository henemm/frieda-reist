# Adversary Dialog — loeschwunsch-145
Spec: docs/specs/konnektor/loeschwunsch.md
Datum: 2026-10-30 14:09

## Checkliste
- [x] **Input:** Eine Person sagt dem Assistenten „lösch das“ zu einer Buchung, Option, Aufgabe oder Frage.
- [x] **Output:** Der Assistent nennt (nach der Anleitung) den passenden Weg, lässt bestätigen, ruft das Werkzeug auf; die Antwort des Werkzeugs sagt, dass nichts gelöscht ist, und wie man es zurückholt (bzw. dass es bei Fragen kein Zurückholen gibt).
- [x] **Side effects:** Keine. Bestehende Zustandswechsel, Verläufe und Regeln der Werkzeuge bleiben unverändert.
- [x] **AC-1:** Die Anleitung enthält den Absatz zum Löschwunsch (Frieda löscht nie; Weg je Grundform; erst bestätigen lassen; ein Satz danach; ehrlicher Verweis auf die Rückmeldung, wo es keinen Weg gibt). Er steht für jede Rolle (Gast, Mitwirkende, Organisator:in) in der Anleitung.
- [x] **AC-2:** Die Beschreibungen von `buchung_aendern`, `entscheiden`, `aufgabe_aendern` und `frage_schliessen` nennen den Löschwunsch und den eigenen Weg samt Rückholweg.
- [x] **AC-3:** Der Antworttext nach dem Stornieren einer Buchung enthält „Nicht gelöscht“ und den Rückholweg (Status gebucht). Nach einer anderen Änderung der Buchung (z. B. Nummer) steht der Hinweis nicht.
- [x] **AC-4:** Der Antworttext nach `entscheiden` mit `verworfen` oder `ersetzt` enthält „Nicht gelöscht“ und den Rückholweg (entscheiden, Status gewählt). Bei `gewaehlt` steht der Hinweis nicht.
- [x] **AC-5:** Der Antworttext nach `frage_schliessen` mit `entfaellt` sagt ehrlich, dass es kein Wiedereröffnen gibt; bei `geklaert` steht er nicht.
- [x] **AC-6:** Der Antworttext nach Aufgabe `entfaellt` nennt „wieder offen“ als Rückholweg.
- [x] **AC-7:** Die bisherigen Antwortsätze bleiben unverändert und stehen vor dem Zusatz (Teilstring-Tests der bestehenden Tests bleiben grün).
- [x] **AC-8:** Die Texte nennen nichts Reisespezifisches; in der Beispielreise (Ida, Karl) gibt es keine Namen oder Pfade außerhalb davon.
- [x] **AC-9:** `engine/.venv/bin/python -m pytest -q engine/tests` ist insgesamt grün; die neuen Tests sind ohne die Änderungen rot (TDD RED).

## Dialog

### Runde 1
**Adversary:** Ich zweifle an jedem Punkt und fordere Belege. Zusatz nur bei echtem Statuswechsel? Fragen: erneut stornieren, Nummer bei stornierter Buchung, erneut verwerfen, abgelehnte Aktionen (Stornieren ohne Grund, unbekannte Option oder Frage). Danach: Anleitung für drei Rollen, Länge, AC-7 per Diff, Zulässigkeit der Testanpassungen.
**Implementierer (Belege aus Probeläufen gegen die Beispielreise-Kopie):**
- Erstes Stornieren B-01: Text endet mit „Nicht gelöscht, die Buchung steht weiter mit Verlauf da; zurückholen mit Status gebucht.“ (Code reference: engine/schreiben.py:2010; der Status vorher wird in engine/schreiben.py:1941 vor jeder Änderung gemerkt).
- Zweites Stornieren: Ablehnung „Nichts zu ändern“, also kein Text, kein Zusatz. Nummer ändern bei stornierter Buchung: Antwort „Nummer … → ZZ9.“ ohne Zusatz. Zurückholen storniert→gebucht: ohne Zusatz. Stornieren ohne Grund: Ablehnung, kein Zusatz.
- entscheiden: V-01.b verworfen mit Zusatz (engine/schreiben.py:1489-1490); erneut verworfen: Ablehnung „schon verworfen“; ohne Grund und unbekannte Option: Ablehnung. Der Zusatz steht nach dem alten Satz (Anhängen mit +=).
- frage_schliessen F-01 entfaellt: Zusatz am Ende (engine/schreiben.py:1614-1617); unbekannte Frage: Ablehnung vor dem Text.
- Aufgabe: Der Zusatz hängt im Konnektor erst nach erfolgreichem Dienst-Aufruf, der Fehlerpfad kehrt vorher zurück (engine/konnektor.py:2893-2897).
**Adversary (Nachbohren):** Aufgabe schon entfaellt und erneut entfaellt: der Konnektor kennt den Vorzustand nicht und hängt den Zusatz an. Kleine Abweichung von „nur beim echten Wechsel“; AC-6 verlangt es nur für „nach Aufgabe entfaellt“, die Aussage bleibt wahr. Befund F001 (LOW). Außerdem liest sich der Fragetext bei einem Ergebnis ohne Schlusspunkt als „…: e Nicht gelöscht …“ (F002, LOW, kosmetisch).

### Runde 2
**Adversary:** AC-1/AC-8: Anleitung für alle Rollen und mit/ohne Schreibweg? Der Absatz wird in anleitung() unbedingt angehängt (engine/konnektor.py:2771), unabhängig von Rolle und Schreibweg. Gäste: rueckmeldung_geben nur „sofern erlaubt“, nicht irreführend. Länge: test_verfassung_ist_kurz_und_nennt_aufgabe_grenzen_rollen läuft für Organisator:in, Mitwirkende und Gast grün mit Grenze 3900. Anhebung von 3650 auf 3900 ist im Spec-Changelog begründet (Absatz sonst 3640), der Test prüft weiter Rollen, Anfang, Grenzen und Status; nur die Obergrenze stieg, nichts abgeschwächt.
AC-2: alle vier Beschreibungen enthalten einen Satz „Bei einem Löschwunsch …“ mit Weg und Rückholweg, ohne „z. B.“ in diesem Satz (das vorhandene „z. B.“ in BUCHUNG_AENDERN steht davor und ist unverändert).
AC-7: Der Diff gegen HEAD zeigt nur angehängte Zusätze; die 6 entfernten Zeilen sind Zeilen, deren Zeichenkette-Ende verlängert wurde, kein bisheriger Satz wurde umformuliert. schreiben.py: status_vorher ist reine Leseoperation (engine/schreiben.py:1941), keine Verhaltensänderung.
Testanpassung V-03.a→V-02.a (ersetzt durch V-02.b): V-03.b war nach dem ersten Schritt schon verworfen, die Konstellation unzulässig; eine Regel wurde nicht angefasst, der Test behauptet weiter „ersetzt hängt den Hinweis an“. Zulässig, im Changelog begründet.
**Implementierer:** keine weiteren Einwände. Gegenprobe: die 9 neuen Tests waren ohne Änderung rot (test-red-output.txt, 9 failed), jetzt grün (9 passed); Gesamtsuite 639 passed in 376,58 s (adversary-test-output.txt).

## Confirmations
- AC-1 CONFIRMED. Code reference: engine/konnektor.py:2771. Evidence: Absatz unbedingt angehängt, 3 Rollen-Tests grün.
- AC-2 CONFIRMED. Code reference: engine/konnektor.py:2192. Evidence: aufgabe_aendern, FRAGE_SCHLIESSEN, BUCHUNG_AENDERN, ENTSCHEIDEN je mit Weg und Rückholweg.
- AC-3 CONFIRMED. Code reference: engine/schreiben.py:2010. Evidence: nur bei Wechsel nach storniert; erneut, Nummer, zurück und Ablehnung ohne Zusatz (Probelauf).
- AC-4 CONFIRMED. Code reference: engine/schreiben.py:1489. Evidence: verworfen und ersetzt mit Zusatz, gewaehlt ohne; Ablehnungen ohne.
- AC-5 CONFIRMED. Code reference: engine/schreiben.py:1614. Evidence: nur entfaellt; geklaert ohne; Wiedereröffnen ehrlich verneint.
- AC-6 CONFIRMED. Code reference: engine/konnektor.py:2896. Evidence: „wieder offen“ im Zusatz nach erfolgreichem Aufruf (Einschränkung F001).
- AC-7 CONFIRMED. Code reference: engine/schreiben.py:1941. Evidence: nur Anhänge, 639 Tests grün.
- AC-8 CONFIRMED. Code reference: engine/konnektor.py:2771. Evidence: nur Werkzeug- und Statusnamen, Test auf Reisespezifisches grün.
- AC-9 CONFIRMED. Code reference: engine/schreiben.py:1490. Evidence: 9 rot ohne Änderung, 639 grün mit Änderung.

## Findings
Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/konnektor.py:2896
  Description: Der Zusatz für Aufgaben hängt an jedem erfolgreichen Aufruf mit status entfaellt, auch wenn die Aufgabe schon entfaellt war.
  Spec requirement: AC-6 — Antworttext nach Aufgabe entfaellt nennt wieder offen.
  Conflict: Kein Konflikt mit AC-6; nur nicht auf den echten Wechsel beschränkt (anders als AC-3/4/5). Die Aussage bleibt wahr.
  Remediation: Optional Vorzustand prüfen; nicht nötig.
Finding:
  ID: F002
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/schreiben.py:1614
  Description: Der Zusatz wird mit Leerzeichen an das freie Ergebnis der Person gehängt; endet es ohne Punkt, liest sich der Satz „…: e Nicht gelöscht …“.
  Spec requirement: AC-5 — ehrlicher Hinweis, nur Anhängen.
  Conflict: Kosmetisch, Spec wörtlich erfüllt.
  Remediation: Optional vorher einen Schlusspunkt sicherstellen.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
**VERIFIED**
Die Umsetzung hält dem Gegenspielertest stand: Zusätze erscheinen nur nach erfolgreicher Schreibaktion und nur beim echten Statuswechsel (Buchung, Option, Frage); Ablehnungen, erneutes Stornieren, Nummeränderung und Zurückholen bleiben ohne Zusatz. Die Anleitung gilt für alle drei Rollen, die Länge liegt unter der Grenze. Bisherige Sätze sind unverändert (nur Anhänge). Testanpassungen sind begründet und schwächen nichts ab. Tests: 639 passed, 0 failed, 0 übersprungen (Beleg docs/artifacts/loeschwunsch-145/adversary-test-output.txt); die 9 neuen Tests waren ohne Änderung rot, jetzt grün. Offen nur zwei LOW-Hinweise (F001, F002), kein Blocker.

## Geprüfte Dateien

- sha256:8602198b98644611abff97dd115e4974ccdc1bcf3ef56e5b14897a8af7e2965f  engine/konnektor.py
- sha256:b1de55305608e7b3f22cab53ba13f0e8f63b06114459821f0633b7decfa36e4f  engine/schreiben.py

## Prüfbasis

- base: 0d6fb926c732140922797f94c0aebd337690e324
- blob:f81bdd558077468673166c53011d9b714d7024ec  engine/konnektor.py
- blob:861e56bff82953ac8c899802d2fd8cdb21a12748  engine/schreiben.py
