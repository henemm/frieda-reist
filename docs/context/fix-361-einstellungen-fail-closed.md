# Context: fix-361-einstellungen-fail-closed

## Request Summary
Issue #361 (Teil von #345, Stufe 5): Kann die Einstellungsdatei der Instanz nicht gelesen werden, darf eine Reise aus
`FR_SPEICHERREISEN` nicht auf den Git-Weg fallen. Der Schreibweg muss stattdessen mit 503 ablehnen (fail closed), mit Test.
Voraussetzung dafür, dass in Stufe 5 echte Reisen umgeschaltet werden (#350).

## Ursache (belegt)
- `engine/instanz.py:39-44` `einstellungen()` fängt jeden `OSError` und gibt `{}` zurück.
- `engine/instanz.py:103-107` `speicherreisen()` liest `FR_SPEICHERREISEN` aus der Umgebung, sonst aus `einstellungen()`; bei `{}` ist die Liste leer.
- Folge: `engine/schreiben.py:5015` (`anwenden_extern`) wählt den Git-Weg, und der Schutz in `engine/schreiben_git.py:172` fragt dieselbe Funktion und greift nicht.
- Ebenfalls betroffen, weil sie dieselbe Liste fragen: `engine/stand.py:156` (Stand der Seite käme aus Git), `engine/schreiben.py:5146` (`/gesund`), `engine/schreiben.py:5157` (Buchungsabfrage).

## Related Files
| Datei | Relevanz |
|---|---|
| `engine/instanz.py` | `einstellungen()`, `speicherreisen()`, `wert()`: hier entsteht das leere Ergebnis |
| `engine/schreiben.py` (~5015, 5146, 5157) | Weichen Speicher/Git; Fehlerweg 503 mit Katalogtext existiert (`speicher_nicht_erreichbar`, `fehler_antwort`) |
| `engine/schreiben_git.py:172` | Schutz `reise_im_speicher`, fragt dieselbe Funktion |
| `engine/stand.py:156` | `fuer_seite` wählt Quelle über `speicherreisen()` |
| `engine/texte_de.py:870`, `texte_en.py` | Katalog; neuer Text für „Einstellungen nicht lesbar“ in allen Sprachen |
| `betrieb/gemeinsam.sh:61-74` (`fr_einlesen`) | Shell-Gegenstück: `[ -r "$1" ] || return 0` überspringt eine unlesbare Datei stillschweigend; Entscheidung nötig |
| `betrieb/gemeinsam.sh:107-123`, `veroeffentlichen.sh:166`, `software-nachziehen.sh:78-105` | Shell-Seite der Speicherreisen-Liste |
| Tests: `test_schreiben_speicher.py`, `test_speicher_stufe3.py`, `test_stand.py`, `test_betrieb.py`, `test_software_nachziehen.py`, `test_reisespeicher_ablage.py` | nutzen `FR_SPEICHERREISEN`; dort anknüpfen |

## Existing Patterns
- Fail closed im Speicher-Zweig: `sqlite3.Error`/`OSError` wird zu 503 mit `schreiben.dienst.speicher_nicht_erreichbar` (schreiben.py ~5160).
- Sichtbare Texte nur im Katalog, alle Sprachen (`test_texte.py`, ADR-0006).
- `fehler_antwort(schluessel, mit_ok)` baut die Antwort.

## Wichtige Unterscheidung (Risiko)
Eine **fehlende** Datei (`FileNotFoundError`) ist normal: Beispielreisen, Tests und Instanzen ohne `einstellungen.env`
haben keine; dort bleibt `{}` und alles läuft über Git. Nur eine **vorhandene, aber nicht lesbare** Datei
(`PermissionError` u. a.) darf nicht stillschweigend zu „keine Speicherreisen“ werden. Ein Test muss beides trennen.
Zu klären in der Analyse: Umgebungswert `FR_SPEICHERREISEN` gilt weiter vor der Datei (kein Lesen nötig).

## Dependencies
- Upstream: `os.environ`, Einstellungsdatei (`FR_EINSTELLUNGEN` oder `<wurzel>/betrieb/einstellungen.env`).
- Downstream: Schreibweg, `/gesund` des Schreibdienstes, Stand der Seite, Buchungsabfrage; Shell-Skripte lesen die Datei separat.

## Existing Specs
- Keine eigene Spec zu #361. Rahmen: ADR-0009 (Reisespeicher), Specs zu Stufe 2 bis 4 (`docs/specs/`), Befund F003 aus der Adversary-Prüfung von #347.

## Risks & Considerations
- Der Dienst darf wegen eines Lesefehlers nicht ganz ausfallen: Git-Reisen ohne Speicherreise brauchen die Datei nicht; nur wenn sie existiert und unlesbar ist, gilt „unbekannt“.
- Der Fehler muss laut sein (Protokollzeile auf stderr, `/gesund` 503), damit er in der Überwachung auftaucht.
- Shell-Seite (`fr_einlesen`) hat dieselbe Lücke: Entscheidung in der Analyse, ob sie im selben PR geschlossen wird (Veröffentlichen würde sonst eine Speicherreise aus Git bauen).
- Änderung betrifft eine Schnittstelle, die Instanzen nutzen: vor dem Vorspulen laufen die Tests der einbindenden Instanzen mit dem Branch.
- Format der Reisedaten ändert sich nicht, kein `nachziehen` nötig.

## Analysis

### Type
Bug (Befund F003 aus #347; Voraussetzung für Stufe 5, #350).

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/instanz.py | MODIFY | Neue Ausnahme `EinstellungenNichtLesbar` (Unterklasse von OSError). `speicherreisen()` liest die Datei streng: Umgebungswert gilt zuerst; fehlt die Datei (FileNotFoundError), bleibt die Liste leer; existiert sie, ist aber nicht lesbar, wird die Ausnahme ausgelöst. `einstellungen()` und `wert()` bleiben nachsichtig (sonst fiele der ganze Dienst aus: Pfade, Ablage, Zeitzone) |
| engine/schreiben.py | MODIFY | `anwenden_extern`: Ausnahme vor der Weiche fangen, 503 mit neuem Katalogtext, Protokollzeile auf stderr. `/gesund`: 503. Buchungsabfrage: 503 |
| engine/schreiben_git.py | MODIFY | Schutz in `vorgang`: Ausnahme ebenfalls zu 503 (zweite Sicherung, falls jemand `vorgang` direkt ruft) |
| engine/stand.py | MODIFY | `fuer_seite` lässt die Ausnahme durch: der Bau bricht laut ab, statt den Stand aus Git zu nehmen |
| engine/texte_de.py, texte_en.py (+ weitere Sprachen) | MODIFY | Ein Schlüssel `schreiben.dienst.einstellungen_nicht_lesbar` in allen Sprachen |
| betrieb/gemeinsam.sh | MODIFY | `fr_einlesen`: Datei vorhanden, aber nicht lesbar -> Fehlermeldung und Abbruch (statt stillschweigend überspringen); fehlende Datei bleibt erlaubt. Sonst baut Veröffentlichen eine Speicherreise aus Git |
| engine/tests/test_schreiben_speicher.py, test_stand.py, test_betrieb.py | MODIFY | Neue Tests |

### Scope Assessment
- Files: 7 bis 8 plus Tests
- Estimated LoC: +70/-5 Code, +90 Tests
- Risk Level: MEDIUM (Schreibweg und Veröffentlichen sind zentral; mitigiert, weil fehlende Datei unverändert läuft)

### Technical Approach
Fail closed nur dort, wo eine Fehlentscheidung Daten auf den falschen Weg bringt (die vier Aufrufer von `speicherreisen()` und das Shell-Einlesen). Unterscheiden: fehlende Datei = „keine Speicherreisen“ (Beispielreisen, Tests); vorhandene, nicht lesbare Datei = „unbekannt“ -> 503. Test als Root-sicher umsetzen (Rechte entziehen greift bei root nicht): Datei durch Verzeichnis ersetzen (IsADirectoryError) oder `read_text` patchen, plus echter Test mit chmod 000, übersprungen unter root. Umgebungswert `FR_SPEICHERREISEN` gilt weiter vor der Datei, auch bei unlesbarer Datei.

### Dependencies
Schreibweg, `/gesund`, Stand der Seite, Buchungsabfrage; Shell-Skripte (`veroeffentlichen.sh`, `software-nachziehen.sh`) über `fr_einlesen`. Vor dem Vorspulen laufen die Tests der einbindenden Instanzen mit dem Branch (Schnittstelle: Meldungstext, Verhalten von `gemeinsam.sh`).

### Open Questions
- [ ] Keine, die den PO betreffen. Entscheidung der Analyse: Shell-Seite im selben PR schließen (gleiche Lücke, kleiner Eingriff).
