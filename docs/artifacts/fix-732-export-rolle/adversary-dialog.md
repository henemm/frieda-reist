# Adversary Dialog — fix-732-export-rolle
Spec: docs/specs/fast/fix-732-export-rolle.md
Datum: 2026-11-27 16:52

## Checkliste
- [x] AC-1: Liegt die Reise im Reisespeicher und fehlt ihre Seite, enthält der Export einer Organisatorin dieselben Belege wie bei veröffentlichter Seite (Rolle aus `reise.yaml`).
- [x] AC-2: Eine Mitwirkende bekommt in derselben Lage nur die Belege, die `belege.liste` ihr als Mitwirkende zeigt.
- [x] AC-3: Fehlt die Seite und steht die Reise nicht im Speicher, bleibt es bei Gast mit dem Namen des Kontos.
- [x] AC-4: Bestehende Tests zum Export und zum Löschen bleiben grün.

## Dialog

### Runde 1
**Adversary:** Prüfe `_export_rolle` neu: Der Zweig `zs is None -> gast` ist weg, Name und Rolle kommen aus `_person`. Angriff 1: Kann eine Person über den Rückweg mehr Rechte bekommen? Der Schlüssel `m["schluessel"]` stammt aus `konten.mitglieder` (Zuordnung des Kontos), nicht aus Nutzereingabe; `_person` vergleicht exakt mit dem Schlüssel, ein fremder Schlüssel liefert `{}` und damit Gast (Sonde: Schlüssel k2 gegen reise.yaml mit nur k1: Gast). Angriff 2: veröffentlichte Seite vorhanden: `_person` nimmt `rm.zustand` zuerst, der Speicher wird nur bei `personen is None` gelesen; Verhalten gleich wie vorher (der Seitenpfad lieferte schon vorher dasselbe). Angriff 3: Reise nicht im Speicher: `_reise_aus_speicher` gibt `{}`, Gast mit Kontoname (AC-3, Test vorhanden).
**Implementierer:** (Diff-Begründung laut Spec; kein eigener Verlauf gesehen.)

### Runde 2
**Adversary:** Sonden mit präparierten reise.yaml-Inhalten (Seite fehlt): Personen als Liste mit Schlüssel: Organisator erkannt. Personen als Zuordnung: erkannt. Name leer: Kontoname bleibt (`p.get("name") or k["name"]`). Eintrag kein Dict (`k1: x`): Gast. `personen: "x"` (Text): Gast. Leeres/fehlendes reise.yaml, YAML-Syntaxfehler (Exception in `_reise_aus_speicher` gefangen): Gast. Schwachstelle: `personen: 5` (Zahl) wirft TypeError beim Iterieren in `_person`; im Export war das bisher bei fehlender Seite unerreichbar (vorzeitiges Gast), jetzt ist es erreichbar. Gleiche Lücke bestand schon über `export_person` (person.json) und `ist_organisatorin`, also kein neuer Fehlerklasse, nur ein theoretischer Fall (reise.yaml wird vom Dienst geprüft geschrieben). Wertung LOW, kein Blocker.
**Implementierer:** keine Änderung nötig.

## Herkunft der Vorbedingungen

Kein Sprachprofil konfiguriert (`precondition_origins.default_lang`); keine Tabelle angehängt. Geprüft von Hand: Das Feld Rolle wird in `_person` nur gelesen (Seite oder reise.yaml), nicht von dieser Änderung geschrieben; Test für den Weg: `test_belege_ohne_seite_nach_rolle_aus_speicher` und `test_belege_ohne_seite_und_ohne_speicher_gast`.

## Findings und Bestätigungen

Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:1047
  Evidence: `_export_rolle` ruft `_person` ohne vorzeitiges Gast; `_person` (engine/anmeldung.py:729) fällt bei fehlender Seite auf reise.yaml zurück. Test `test_belege_ohne_seite_nach_rolle_aus_speicher`: Organisatorin bekommt D-01 bis D-04.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/anmeldung.py:729
  Evidence: Mitwirkende (Karl) bekommt D-02, D-03, gleich `belege.liste(..., "Karl", "mitwirkend")`.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/anmeldung.py:716
  Evidence: Reise nicht im Speicher: `_reise_aus_speicher` liefert `{}`, `_person` liefert `{}`, Ergebnis (Kontoname, gast). Test `test_belege_ohne_seite_und_ohne_speicher_gast`.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/tests/test_export.py:571
  Evidence: test_export.py und test_loeschen_konto.py: 91 passed; Lauf des Skripts (test-run-output.txt): 125 passed.
  Status: CONFIRMED

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/anmeldung.py:733
  Description: `_person` iteriert `personen` aus reise.yaml; ist es eine Zahl, entsteht ein TypeError. Der Export erreicht diesen Pfad jetzt auch ohne Seite.
  Spec requirement: AC-3 — unbekannte Person oder unlesbarer Stand bleibt Gast
  Conflict: Nur bei hand-kaputter reise.yaml (`personen: 5`); gleiche Lücke bestand schon in `export_person` und `ist_organisatorin`.
  Remediation: Optional in `_person` auf Liste/Zuordnung prüfen, sonst `[]`.

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Änderung hielt dem Prüfversuch stand.
Tests: 125 passed (Lauf des Skripts), 91 passed (Export und Löschen), 0 failed, 0 übersprungen
Edge cases: geprüft, ein LOW-Hinweis (F001), kein Blocker
Regressions: keine gefunden
Checklist: 4/4 Punkte bewiesen

## Geprüfte Dateien

- sha256:5a144bdad3e2e3b4754ffb3ed971739fb18e6b85ad8b9fdfbb38630c5b98b628  engine/anmeldung.py
- sha256:f4ef0201650cc7e966800db63ec8f676b669fe41da2ac7353fd5fe49bdef6472  engine/tests/test_export.py

## Prüfbasis

- base: 1243ad0da7749d33fe125faec887330753183de8
- blob:4710478ab5c0f98053c58160da9369f207d28769  engine/anmeldung.py
- blob:db115320350b83848b74b1b6f913eb0b151f2154  engine/tests/test_export.py
