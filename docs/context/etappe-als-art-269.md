# Kontext und Analyse: #269 Etappe als Art der Reise (Teil von #215)

Stand 4.11.2026, Analyse nur durch Lesen des Codes (nichts ausgeführt). Abgestimmt mit der Sitzung zu #268: Die Sitzung arbeitet an `routen.py`, `vorlage.html`, `konnektor.py`; `bauen.py` (Dossier-Etappen) und die Zuordnung `REGEL.*`/`kennzahlPaar` bleiben für #269. Code in `routen.py`/`vorlage.html` erst nach dem Vorspulen von #268 auf `main`.

## Analysis

### Type
Feature (Umbau, Schuld aus #215 Punkt 1).

### Befund
- Zwei Wege, Etappen zu kennen: (a) das Etappen-Dossier als Markdown (`bauen.py` `daten()` 419–442: fest „Etappe N: Name“, Abschnittstyp `etappe`, Einstellungen `etappen_dossier`, `etappen_muster`, `etappen_ebenen`, `etappen_kennzahlen`), (b) Strecken der Art in `plan/routen.yaml` (`routen.py`). Das Routenmodell mischt beide (`{**self.etappen, **self.strecken}`, `routen.py` 659, 820, 1644).
- Kennzahlen kommen als rohe Namen aus der Eckdaten-Tabelle des Dossiers (`bauen.py` `kennzahlen()` 1141). Die Seite ordnet die Namen erst im Browser Kennungen zu: `REGEL.gehzeit/aufstieg/abstieg/laenge` (`vorlage.html` 968–977) und `kennzahlPaar` (1337); `routen.py` `kennwerte()` (415) macht dieselbe Zuordnung noch einmal. Das ist die doppelte Regel.
- 22 Stellen lesen `typ === "etappe"` (Reiter „Etappen“, Tagesseite, Karte, Dossier-Blöcke).
- Beide Beispielreisen: `beispielreise` nutzt das Dossier (`etappen_kennzahlen` in `reise.json`); `stadtwochenende` hat keine Etappen. Jede Änderung muss an beiden geprüft werden (ADR-0001, Frage 1).

### Technischer Ansatz (Empfehlung)
1. `routen.py` liefert für jede Strecke die Kennzahlen fertig und mit Kennung (`gehzeit`, `aufstieg`, `abstieg`, `laenge`); Dossier-Etappen werden beim Lesen in diese Form gebracht (einmal, in `bauen.py`/`routen.py`, nicht im Browser).
2. `REGEL.gehzeit/aufstieg/abstieg/laenge`, `kennzahlPaar`, `tagMin` und `kennwerte()`-Suche entfallen; die Seite zeigt nur noch fertige Paare, Namen aus dem Textkatalog oder der Art.
3. Abschnittstyp `etappe` wird zu „Strecke einer Art“; die Reiter und die Tagesseite fragen die Grundform (bewegung) statt `typ === "etappe"`.
4. `daten()` wird aufgeteilt (Etappen / Orte / Route).
5. Umstellung bestehender Reisen als `neu.py nachziehen` mit Test (CLAUDE.md), kein Handschritt.

### Betroffene Dateien
| Datei | Änderung |
|---|---|
| engine/bauen.py | MODIFY: `daten()` aufteilen, `kennzahlen()` liefert Kennungen |
| engine/routen.py | MODIFY: Kennzahlen fertig je Strecke, `kennwerte()` vereinfachen (erst nach #268) |
| engine/vorlage.html | MODIFY: `REGEL.*`, `kennzahlPaar`, 22 Stellen `typ === "etappe"` (erst nach #268) |
| engine/neu.py | MODIFY: `nachziehen` für das neue Format |
| engine/tests/* | MODIFY/CREATE |
| docs/design.md, Kopfkommentar der Vorlage | MODIFY |

### Scope und Risiko
Etwa 5–7 Dateien, grob +250/−300 Zeilen. Risiko **mittel bis hoch**: zentrale Seitenlogik, beide Reisetypen, Formatwechsel mit Umstellung.

### Abhängigkeiten
#268 muss zuerst auf `main` (gleiche Dateien). Danach auf `main` aufsetzen.

### Entscheidungen des Product Owners (4.11.2026)
- [x] **Dossier:** Etappen leben in `plan/routen.yaml` (Titel, Art, Kennzahlen an der Strecke `E-…`). Das Etappen-Dossier bleibt nur als Markdown für Lesetext und Ebenen, verknüpft über die ID; die feste Regel „Etappe N: Name“ entfällt. `neu.py nachziehen` zieht Titel und Kennzahlen aus dem Dossier einmal in die Strecken um (<Reise A> und Beispielreise).
- [x] **Wort „Etappe“:** bleibt ein festes Wort der Oberfläche (Textkatalog, alle Sprachen). Der Reiter „Etappen“ zeigt alle Strecken, deren Art `summiert: true` hat. Die Reise nennt ihre Art frei (heute `wandern`, Anzeige „Wanderung“).

### Offen, nicht Teil von #269
- Reisen ohne Dossier können `lesetext_schreiben` nicht nutzen (Ablehnung „kein Etappen-Dossier“); eigenes Folge-Issue.
- #268 muss vor Änderungen an `routen.py`/`vorlage.html` auf `main` sein.
