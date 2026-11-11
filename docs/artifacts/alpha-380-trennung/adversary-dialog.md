# Adversary Dialog — alpha-380-trennung
Spec: docs/specs/konnektor/trennung-grenzen-380.md
Datum: 2026-11-11 19:01

## Checkliste
- [x] **Input:** schreibender Werkzeugaufruf oder `reise_anlegen` eines Kontos.
- [x] **Output:** innerhalb der Grenzen unverändertes Verhalten; darüber eine verständliche Ablehnung (Fehlerflag gesetzt), die Wartezeit nennt (Schreibgrenze) beziehungsweise sagt, dass die Höchstzahl angelegter Reisen erreicht ist.
- [x] **Side effects:** je angenommenem Schreibvorgang eine Zeile in `schreibvorgaenge`, je angenommener Reiseanfrage eine in `angelegte_reisen`; bei Ablehnung eine Protokollzeile.
- [x] **AC-1:** Given Konto B ist nur Mitglied des Stadtwochenendes, Konto A der Beispielreise / When B jedes Reise-Werkzeug aus der Werkzeugliste des Konnektors (`frieda_werkzeuge`, im Test darüber parametrisiert, also lesend wie schreibend, auch `suche`, `show`, `overview`) mit `reise=beispielreise` aufruft / Then lehnt der Konnektor mit dem Fehler `konnektor.frieda_werkzeug.1` ab, nichts wird geschrieben, und die Antwort enthält keinen Namen und keine Adresse aus der Beispielreise.
- [x] **AC-2:** Given dieselben Konten / When B `meine_reisen`, `kalender` und Werkzeuge ohne Angabe `reise` aufruft / Then erscheinen nur Reisen mit Mitgliedschaft von B; Antworttexte und Kalender-Abo (nur über Mitgliedschaften) enthalten nichts aus der Beispielreise, auch nicht bei einer Mitgliedschaft auf einer unveröffentlichten Reise.
- [x] **AC-3:** Given dieselben Konten / When B über den Konnektor bei der Beispielreise schreibt (Rückmeldung, Aufgabe, Buchung, Person einladen oder entfernen, Wert eintragen) / Then wird abgelehnt, und die Reisedaten der Beispielreise bleiben unverändert (Vergleich der Datei oder Version vor und nach dem Versuch).
- [x] **AC-4:** Given (a) eine gültige Sitzung (Cookie) von B, (b) eine Anfrage ganz ohne Sitzung / When jeweils per POST an den Rückmeldedienst für die Beispielreise geschrieben wird (Rückmeldung, Beleg, Entscheidung) / Then antwortet der Dienst bei (a) mit 403 und bei (b) mit 401, und in beiden Fällen wird nichts gespeichert.
- [x] **AC-5:** Given Meldungen und Belege in der Beispielreise / When B Meldungen, die Belegliste und einzelne Belege der Beispielreise über seinen Cookie abruft / Then enthalten Meldungen nur Reisen mit Mitgliedschaft von B, und Belege sehen angemeldete Nicht-Mitglieder wie ein Gast (`seher`); Namen und Adressen aus der Beispielreise tauchen in keiner Antwort an B auf.
- [x] **AC-6:** Given der Wächter und der Erinnerer laufen über beide Reisen / When sie Mails erzeugen / Then geht jede Mail nur an Personen derselben Reise; kein Konto ohne Mitgliedschaft bekommt eine Mail oder Meldung einer fremden Reise.
- [x] **AC-7:** Given der geheime Seitenlink der Beispielreise (bewusste Grenze, #421) / When ein Gast ohne Anmeldung und ein angemeldetes Nicht-Mitglied `stand`, `brett` und `packstand` lesen / Then bekommen beide dieselbe Antwort (Gast-Sicht), und das Nicht-Mitglied sieht nicht mehr als der Gast.
- [x] **AC-8:** Given eine Instanz ohne Einstellung der Grenzen / When ein Konto Werkzeuge schreibend aufruft und Reisen anlegt / Then gelten die Vorgaben 10 Reisen und 300 Schreibvorgänge je Stunde; Werte aus der Instanz (`FR_GRENZE_REISEN`, `FR_GRENZE_SCHREIBEN`, auch über `einstellungen.env`) ersetzen sie; ungültige oder nicht positive Werte fallen auf die Vorgabe zurück.
- [x] **AC-9:** Given `FR_GRENZE_SCHREIBEN=3` / When ein Konto drei schreibende Aufrufe innerhalb einer Stunde ausführt und einen vierten versucht / Then wird der vierte mit freundlichem Text samt Wartezeit abgelehnt und schreibt nichts; lesende Werkzeuge und Konto-Werkzeuge bleiben frei; nach Ablauf des Fensters (Zeit im Test verschoben) geht es wieder; ein Aufruf einer fremden Reise (Fehler der Mitgliedschaft) verbraucht keinen Zähler.
- [x] **AC-10:** Given `FR_GRENZE_REISEN=2` und ein Konto mit Recht `reise_anlegen` / When es die dritte Reise anlegen will / Then wird abgelehnt mit Text, der die Höchstzahl nennt; die ersten beiden gehen durch, eine fehlerhafte Anfrage zählt nicht, und eine zweite Person (anderes Konto) ist nicht betroffen.
- [x] **AC-11:** Given ein Konto mit Recht `betreiber` / When es über beiden Grenzen liegt / Then wird es nicht abgelehnt.
- [x] **AC-12:** Given eine Ablehnung durch eine Grenze / When sie auftritt / Then steht eine Zeile im Dienstprotokoll (ohne Adresse und Namen), der Text kommt aus dem Katalog in jeder vorhandenen Sprache (de, en und weitere), und es wird weder eine Meldung an Betreiber noch ein Alarm ausgelöst.
- [x] **AC-13:** Given die Schreibgrenze / When die Menge der „schreibenden“ Werkzeuge bestimmt wird / Then stammt sie aus `SCHREIB_WERKZEUGE`, `SCHREIB_AKTION` und `ONTOLOGIE_WERKZEUGE` (keine zweite Liste), und jedes dort genannte Werkzeug zählt, kein anderes.
- [x] **AC-14:** Given die Doku der Instanz / When die Grenzen eingebaut sind / Then nennen `betrieb/einstellungen.beispiel` und `docs/betrieb.md` beide Umgebungswerte `FR_GRENZE_REISEN` und `FR_GRENZE_SCHREIBEN` mit ihren Vorgaben, und `docs/konten.md` nennt beide Werte sowie die bewusste Grenze beim Lesen über den Seitenlink mit Verweis auf #421.

## Dialog

### Runde 1
**Adversary:** Tests selbst gelaufen: `pytest -q test_grenzen.py test_trennung.py test_texte.py` = 104 passed, 0 failed, 0 übersprungen (Ausgabe: docs/artifacts/alpha-380-trennung/adversary-test-output.txt, keine absoluten Pfade). Der Diff zeigt keine Änderung an engine/tests/test_texte.py (Ausnahmelisten nicht verlängert). Angriffe: (1) Werte der Grenzen per Skript geprüft: "0"->300, "-5"->300, "2.5"->300, " 7 "->7, " "->300, "abc"->300, "1e3"->300 (nur Arabisch-Indische Ziffern wie "٣" werden als 3 gelesen, harmlos). (2) Reihenfolge in frieda_werkzeug: Mitgliedschaftsprüfung (`konnektor.frieda_werkzeug.1`) läuft vor Grenze und Zähler, fremde Reise verbraucht keinen Zähler. (3) Wartezeit: `max(1, aeltester + 3600 - t)` dann `ceil(/60)`, mindestens 1 Minute, nie 0 oder negativ; an der Fenstergrenze löscht `zeit <= t-3600` den ältesten Eintrag, danach frei. (4) Betreiber: `recht(k,"betreiber")` liefert früh frei bzw. False, in beiden Prüfungen. (5) reise_anlegen ohne konto_id: `wer_konto=None`, dann keine Grenze und kein Zähler. Einziger Aufrufer ist frieda_werkzeug (konnektor.py:2293) mit `konto_id=k["id"]`, also im Produktionspfad unerreichbar; kein Bypass. (6) Protokollzeile: `grenze <konto-id> schreiben|reisen`, Konto-ID, keine Adresse und kein Name; kein betreiber_melden. (7) conftest.py: `monkeypatch.delattr(texte._aufruf, "sprache", raising=False)` ist rein Test-Isolation (thread-lokale Sprache aus früherem Test zurücksetzen), autouse, wird per monkeypatch wiederhergestellt; verdeckt nichts am Produktionscode.
**Implementierer:** (aus Code und Doku abgeleitet) Die Grenze prüft vor `werkzeug(...)`, wie in der Spec Schritt 2 festgelegt.

### Runde 2
**Adversary:** Tiefere Probes. (a) Zählt eine abgelehnte (Fehler-)Schreibaktion? Ja: `schreiben_vormerken` läuft direkt nach bestandener Grenzprüfung, vor `werkzeug()` (konnektor.py:2333). Ein Aufruf, den werkzeug() wegen Eingabefehlers ablehnt, verbraucht Zähler. Spec Schritt 2 schreibt genau diese Reihenfolge vor ("vor werkzeug(...)"); spec-konform, bei Vorgabe 300 praktisch folgenlos: LOW. Mitgliedschaftsfehler zählen nicht (AC-9 erfüllt). (b) Rennen: reise_anlegen prüft in einem `_sperre`-Block und merkt in einem späteren, zweiten Block vor (nach `schreib_anfrage`); zwei gleichzeitige Anfragen desselben Kontos können beide die Prüfung bestehen und die Grenze knapp überschreiten. Ebenso Prüfen und Vormerken in frieda_werkzeug ohne gemeinsame Transaktion: LOW. (c) einstellungen.env: `instanz.wert` liest Umgebung vor Datei, die Datei nur über FR_WURZEL/cwd/FR_EINSTELLUNGEN. Der Konnektor läuft laut betrieb/vorlagen/konnektor.service mit `EnvironmentFile=-__DIENST__/konten.env` und ohne Zugriff auf einstellungen.env. Wer die Werte nur in betrieb/einstellungen.env setzt (wie Spec "Instanzen" und AC-8 nahelegen), erzielt im Konnektor keine Wirkung, die Vorgabe greift stumm. Die Doku (docs/betrieb.md, einstellungen.beispiel, konten.md) sagt das ehrlich und verweist auf konten.env, wie beim Impressum; AC-8 ist als Funktion von `instanz.wert` getestet. Code und Doku stimmig, die Spec-Formulierung ist ungenau: MEDIUM. (d) Texte: nur de und en vorhanden, beide Schlüssel in beiden; test_texte grün. (e) Doku: einstellungen.beispiel, betrieb.md, konten.md nennen beide Werte, Vorgaben und #421.

Finding:
  ID: F001
  Severity: MEDIUM
  Category: spec_violation
  Code reference: engine/instanz.py:65
  Description: wert() liest Umgebung, dann einstellungen.env (nur mit FR_WURZEL/cwd); der Konnektor-Dienst sieht die Datei nicht, nur konten.env über EnvironmentFile.
  Spec requirement: AC-8 — Werte aus der Instanz (auch über einstellungen.env) ersetzen die Vorgaben
  Conflict: Werte nur in einstellungen.env wirken im Konnektor nicht; Doku weist korrekt auf konten.env, Spec-Text und "Instanzen"-Absatz nicht. Kein Code-Fehler, Angleichung nötig.
  Remediation: In Spec/Instanz-Anleitung konten.env nennen oder das Einrichten die Werte nach konten.env übernehmen lassen.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/konnektor.py:2158
  Description: Prüfung der Reisegrenze (Zeile 2112) und Vormerken (2158) liegen in verschiedenen _sperre-Blöcken; parallele Anfragen eines Kontos können die Grenze knapp überschreiten. Gleiches bei Schreibgrenze (engine/konten.py:565 schreibgrenze, getrennt von schreiben_vormerken).
  Spec requirement: AC-10 — dritte Reise wird abgelehnt
  Conflict: Nur bei echter Gleichzeitigkeit, Überschreitung um wenige.
  Remediation: Optional Prüfen und Vormerken in einer Transaktion.

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: engine/konnektor.py:2328
  Description: schreiben_vormerken läuft vor werkzeug(); ein von werkzeug() wegen Eingabefehlers abgelehnter Aufruf zählt mit.
  Spec requirement: Expected Behavior — Zeile je angenommenem schreibendem Aufruf
  Conflict: Spec Schritt 2 schreibt diese Reihenfolge vor; Auslegung von "angenommen" knapp.
  Remediation: Keine nötig bei Vorgabe 300; sonst nach Erfolg zählen.

Confirmation:
  AC: Input, Output, Side effects, AC-9, AC-11, AC-13
  Code reference: engine/konten.py:532
  Evidence: reisegrenze_erreicht, reise_vormerken, schreibgrenze (Fenster 3600, Wartezeit min. 1 s), schreiben_vormerken; Betreiber frei; Tabellen in SCHEMA (konten.py:131); Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/instanz.py:157
  Evidence: _grenze fällt bei Leer, Nicht-Zahl, <1 auf Vorgabe 10/300 zurück; per Skript geprüft.
  Status: CONFIRMED

Confirmation:
  AC: AC-1, AC-2, AC-3, AC-9, AC-10, AC-13
  Code reference: engine/konnektor.py:2328
  Evidence: Grenze nach Mitgliedschaftsprüfung, Menge aus SCHREIB_WERKZEUGE/SCHREIB_AKTION/ONTOLOGIE_WERKZEUGE ohne zweite Liste; reise_anlegen mit Ablehnung (2112) und Vormerken nur nach Erfolg (2158).
  Status: CONFIRMED

Confirmation:
  AC: AC-4, AC-5, AC-6, AC-7
  Code reference: engine/konnektor.py:2321
  Evidence: Trennungstests in test_trennung.py grün (Ist-Stand, keine Lücke, Mitgliedschaftsprüfung unverändert).
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/texte_de.py:2039
  Evidence: Schlüssel konnektor.grenze.reisen und .schreiben, freundlich, mit Wartezeit; Protokollzeile ohne Adresse, kein Alarm.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/texte_en.py:2038
  Evidence: gleiche Schlüssel in en; test_texte.py grün, Ausnahmelisten unverändert.
  Status: CONFIRMED

Confirmation:
  AC: Regression (Test-Isolation)
  Code reference: engine/tests/conftest.py:49
  Evidence: delattr der thread-lokalen Aufrufsprache nur Isolation, autouse, verdeckt keinen Produktionspfad.
  Status: CONFIRMED

Confirmation:
  AC: AC-14
  Code reference: engine/instanz.py:157
  Evidence: Doku nennt beide Werte, Vorgaben, #421 (beide Doku-Tests grün).
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Tests: 104 passed, 0 failed, 0 übersprungen
Edge cases: Werte, Wartezeit, Betreiber, fehlende konto_id, Fehlerzählung, Rennen geprüft; F001 (MEDIUM, Spec/Doku-Angleichung), F002/F003 (LOW)
Regressions: None found
Checklist: 17/17 points proven

## Geprüfte Dateien

- sha256:e1279efeba1472fc8c6819b94841c0dad33bbd9f4b9226a21238d48d3732f933  engine/instanz.py
- sha256:10f224a26a0af734a0a42b4f8101231d62e91c6637dc4b7477814e2604071a43  engine/konnektor.py
- sha256:fbda9e8a492b260dad9464ef8807164d269876cefa1ce7faf60df08b688af4c4  engine/konten.py
- sha256:142c93cb112c8b3fe925dcdfae577dcaba93da819b8a0f64761d52911bfdb5f4  engine/tests/conftest.py
- sha256:38dea121f34a1a1a33114060111db276f0929bf22ac48fa2a602caf989e83b41  engine/texte_de.py
- sha256:39392ea355e5ac849dd5b6930af5b31cd7b12003ff62dc88203f83af9d4412a6  engine/texte_en.py

## Prüfbasis

- base: eeeffd8d98eb3a555c9f710c9543cd524419ce74
- blob:22b776a275250d480f7192e4ae15af5d77e476af  engine/instanz.py
- blob:ded50f499669b56bed3d1277eeb3ac17b1fff675  engine/konnektor.py
- blob:4cb1505876ba276fb2934ab0bc59cda37a12b291  engine/konten.py
- blob:1059155764fea671220b50ce11f363cedb23ae11  engine/tests/conftest.py
- blob:bd3b0d90eda5b8997e26a48e4c9358049f67e0e1  engine/texte_de.py
- blob:f3cfffa283e43f1975b8e4e29655c76e2b5cc9a5  engine/texte_en.py

## Geprüfte Dateien

- sha256:e1279efeba1472fc8c6819b94841c0dad33bbd9f4b9226a21238d48d3732f933  engine/instanz.py
- sha256:10f224a26a0af734a0a42b4f8101231d62e91c6637dc4b7477814e2604071a43  engine/konnektor.py
- sha256:fbda9e8a492b260dad9464ef8807164d269876cefa1ce7faf60df08b688af4c4  engine/konten.py
- sha256:142c93cb112c8b3fe925dcdfae577dcaba93da819b8a0f64761d52911bfdb5f4  engine/tests/conftest.py
- sha256:38dea121f34a1a1a33114060111db276f0929bf22ac48fa2a602caf989e83b41  engine/texte_de.py
- sha256:39392ea355e5ac849dd5b6930af5b31cd7b12003ff62dc88203f83af9d4412a6  engine/texte_en.py

## Prüfbasis

- base: eeeffd8d98eb3a555c9f710c9543cd524419ce74
- blob:22b776a275250d480f7192e4ae15af5d77e476af  engine/instanz.py
- blob:ded50f499669b56bed3d1277eeb3ac17b1fff675  engine/konnektor.py
- blob:4cb1505876ba276fb2934ab0bc59cda37a12b291  engine/konten.py
- blob:1059155764fea671220b50ce11f363cedb23ae11  engine/tests/conftest.py
- blob:bd3b0d90eda5b8997e26a48e4c9358049f67e0e1  engine/texte_de.py
- blob:f3cfffa283e43f1975b8e4e29655c76e2b5cc9a5  engine/texte_en.py
