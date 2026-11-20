# Context: test-529-vorgemerkte-durchlauf

## Request Summary
Issue #529 (Nachzug zu #381, AC-6): Das Auslassen zum Löschen vorgemerkter Reisen in `betrieb/veroeffentlichen.sh` ist
bisher nur per Quelltextprüfung (`test_veroeffentlichen_kennt_vorgemerkte`) belegt. Gewünscht ist ein Test, der
`vorgemerkte_entfernen`/`ist_vorgemerkt` in einem echten Skriptlauf gegen eine Testinstanz mit Beispielreisen ausführt.

## Related Files
| File | Relevance |
|------|-----------|
| betrieb/veroeffentlichen.sh:256 | `vorgemerkte_entfernen`: liest `konten.py vorgemerkt`, entfernt `<FR_SEITEN>/<reise>`, Exit 1 bei unlesbarer Liste (fail closed) |
| betrieb/veroeffentlichen.sh:312 | `ist_vorgemerkt`: Filter in `reisen_des_laufs` (Git-Teil), `git_reisen_umschalten`, `speicher_reisen_lauf` |
| betrieb/veroeffentlichen.sh:911, 1191 | Aufruf in `main_klon` (neue Anordnung) und im Lauf der alten Anordnung, jeweils vor allem Bauen |
| engine/konten.py:1214, 1721 | `vorgemerkte_reisen()` und Befehl `vorgemerkt` (Vormerkung + Löschprotokoll) |
| engine/konten.py:1175, 1193 | `loeschung_vormerken`, `loeschung_zurueckholen` |
| engine/anmeldung.py:770 | Löschen ist nur für Reisen im Reisespeicher erlaubt → der fachlich echte Fall ist der Speicher-Teil |
| engine/tests/test_loeschen_reise.py:471 | bisherige reine Quelltextprüfung |
| engine/tests/test_betrieb.py:179, 2842 | Fixtures `vf` (Bauordner, Deploy-Attrappe) und `sp` (Reisespeicher mit beispielreise, stadtwochenende; Deploy-Attrappe schreibt Seite mit `daten.json`) |
| engine/tests/test_nginx_baustein_loeschen_527.py | Vorbild: Fixture `kdb` (Kontendatenbank mit Konto k-ida), Skriptläufe gegen `vf` mit `FR_KONTEN` |

## Existing Patterns
- Skriptläufe: `vf["lauf"](*args, **env)`, Deploy-Protokoll über `vf["deploys"]()`; `sp` erweitert `vf["env"]` um Speicher und Seiten.
- Kontendatenbank im Test: `kdb`-Fixture setzt `FR_KONTEN`; für den Skriptlauf muss `FR_KONTEN` zusätzlich in die Laufumgebung.

## Probelauf (Analyse, Wegwerf-Test, 20.11.2026)
Mit `sp` + `kdb`, `stadtwochenende` vorgemerkt:
1. Erster Lauf baut alle Reisen.
2. Nach Vormerken: Seite `seiten/stadtwochenende` weg, kein Deploy, Exit 0, Meldung „is marked for deletion: page removed.“
3. Auch mit `--immer` wird die vorgemerkte Reise nicht gebaut, die anderen schon.
4. Nach `loeschung_zurueckholen`: der nächste Lauf baut `stadtwochenende` wieder (die Seite hat keinen Stand mehr, Speicher-Stand ≠ Seiten-Stand), Seite wieder da.
5. Kontendatenbank unlesbar (Müll statt SQLite): Exit 1, „ERROR: the list of deleted trips cannot be read“, kein Deploy.

→ Verhalten entspricht AC-6 vollständig; es geht nur um den Test, keine Änderung am Skript nötig.

Nebenbefund Git-Teil: Eine Git-Reise würde nach dem Zurückholen ohne Änderung nicht neu gebaut. Kein Fehler, weil
Löschen nur für Reisen im Reisespeicher erlaubt ist (`anmeldung._loeschen_erlaubt`).

## Dependencies
- Upstream: `engine/konten.py` (Befehl `vorgemerkt`), `engine/reisespeicher.py staende` (Seitenstand aus `daten.json`).
- Downstream: keine (nur Tests).

## Existing Specs
- Spec zu #381 (Löschen einer Reise), AC-6.

## Risks & Considerations
- Testlaufzeit: ein Lauf ≈ 1 s, vier Läufe vertretbar.
- Fail-closed-Fall muss eine echte unlesbare Liste erzeugen (kaputte Datenbank), nicht nur eine Attrappe.
- Nur erfundene Reisen (beispielreise, stadtwochenende, zweitreise).

## Analysis

### Type
Feature (Testlücke schließen, keine Verhaltensänderung)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/tests/test_vorgemerkte_durchlauf_529.py | CREATE | Skriptläufe von veroeffentlichen.sh mit vorgemerkter Reise, beide Anordnungen |
| betrieb/veroeffentlichen.sh | — | keine Änderung (Probelauf belegt AC-6) |
| engine/tests/test_loeschen_reise.py | — | Quelltextprüfung bleibt als billige Vorab-Prüfung stehen |

### Scope Assessment
- Files: 1 (neu)
- Estimated LoC: +120/-0
- Risk Level: LOW (nur Tests, keine Produktivänderung)

### Technical Approach
Zwei Aufrufstellen von `vorgemerkte_entfernen` existieren: `main_klon` (neue Anordnung #454, Zeile 911, der heutige
Betriebsweg) und der Lauf der alten Anordnung (Zeile 1191). Der Probelauf lief nur über `sp` (alte Anordnung).
Die Tests decken deshalb beide ab:

1. **Neue Anordnung über Fixture `sw`** (`engine/tests/test_software_weg_454.py:296`, importierbar per
   `from test_software_weg_454 import sw` oder als Kopie der Fixture-Nutzung; `sw` setzt `FR_KONTEN` bereits in Lauf-
   und Testumgebung, Reisen beispielreise und stadtwochenende im Speicher):
   - Lauf 1 baut beide Reisen, Seiten da.
   - `konten.loeschung_vormerken("stadtwochenende", <konto>)` → Lauf 2: Exit 0, `seiten/stadtwochenende` weg,
     kein Deploy für stadtwochenende, Meldung „marked for deletion“, beispielreise unberührt.
   - Lauf mit `--immer`: stadtwochenende wird nicht gebaut, beispielreise schon.
   - `konten.loeschung_zurueckholen(...)` → nächster Lauf baut stadtwochenende wieder, Seite wieder da.
   - Kontendatenbank durch Müll ersetzt → Exit 1, „ERROR: the list of deleted trips cannot be read“, kein Deploy,
     keine Seite entfernt (fail closed).
2. **Alte Anordnung über `sp` + Kontendatenbank** (wie Probelauf): mindestens Vormerken → Seite weg/kein Bau und
   fail closed, damit auch Zeile 1191 im echten Lauf belegt ist.

Konto für `loeschung_vormerken`: wie in `test_nginx_baustein_loeschen_527.py` (Fixture `kdb`, Konto k-ida) bzw. mit
`konten.konto_anlegen` in der von `sw` gesetzten `FR_KONTEN`; Spec-Phase legt die genaue Hilfsfunktion fest.
Deploy-Protokoll: `sw.zeilen("deploy.log")` (Format „<reise> <kopf>“) bzw. `vf["deploys"]()`.

### Dependencies
- `engine/konten.py` (`loeschung_vormerken`, `loeschung_zurueckholen`, Befehl `vorgemerkt`)
- Fixtures `sw` (test_software_weg_454.py) und `vf`/`sp` (test_betrieb.py)
- Laufzeit: etwa 5–6 Skriptläufe à ~1 s; mit `-n auto` unkritisch.

### Open Questions
- keine (reiner Testnachzug, Verhalten durch Spec #381 AC-6 festgelegt)
