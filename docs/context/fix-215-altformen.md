# Context: fix-215-altformen (#215, Abschlussprüfung)

## Request Summary
#215 sammelt technische Schulden. Der Issue-Text (Stand 2.11.2026) ist älter als der Code. Geprüft wurde, was davon noch offen ist.

## Stand der fünf Teile
| Teil | Stand | Beleg |
|------|-------|-------|
| 1 Etappe als Typ der Software | erledigt | #269 (geschlossen); `bauen.py` kennt `etappen_dossier`/`etappen_ebenen` nur noch als Einstellungen der Reise |
| 2 Kennzahl-Regeln doppelt | erledigt | #268 (geschlossen, `c602dad`), Kommentar im Issue |
| 3 Altformen | fast erledigt | #267 (geschlossen): `self.alt`, Bestandssprache `de`, Lesepfad `typ`; Umstellung in `neu.py nachziehen` |
| 4 Kleinigkeiten | erledigt | die Zeile `a.typ === "etappe" ? a.titel : a.titel` ist weg |
| 5 zweite Testreise | erledigt | `beispiel/reisen/stadtwochenende` vorhanden |

## Verbleibende Reste (Teil 3)
- Reiter/Route heißt im Code noch `offen` (`vorlage.html` 1147, 1154; `seiten_browser.mjs`; Push-URL `#offen` in `pwa_browser.mjs`), die Seite nennt ihn seit 28.10. „Zu tun“. Umbenennung berührt gespeicherte Links und Push-Adressen.
- Bestandsfeld `buchung` an Dingen (`vorlage.html` 1313–1322, Kommentar in `routen.yaml` der Beispielreise: „ein eigener Eintrag buchung: ginge auch“). Noch dokumentierte, gelesene Form.
- Bewusst bleibt: `varianten_titel` (Entscheidung in #267, wird von einer Reise genutzt), Einzelform der Merkmalswerte (Lesetoleranz, laut Gesamtspec von #267).

## Risiken
- Bestandsfeld `buchung`: Entfernen ändert das Datenformat; braucht Umstellung in `neu.py nachziehen` mit Test (CLAUDE.md).
- Route `offen`: Alte Links und Benachrichtigungen mit `#offen` müssten weiter greifen.

## Offene Entscheidung
Beide Reste umsetzen, oder #215 mit dem Hinweis auf #267/#268/#269 schließen und die Reste als eigene Issues anlegen?

## Analysis

### Type
Feature (Aufräumen technischer Schulden, Teil 3 von #215)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/vorlage.html | MODIFY | Route/Reiter `offen` → `zu-tun`, alter Hash `#offen` leitet weiter; `buchungChip` liest nur noch Buchungen `B-…` statt Feld `buchung` |
| engine/neu.py | MODIFY | `nachziehen`: Feld `buchung` an Dingen in echte Buchung umstellen |
| engine/sw.vorlage.js / Push-Adressen | MODIFY (prüfen) | alte Push-URLs `#offen` müssen weiter greifen |
| engine/bauen.py | MODIFY | Symbolzuordnung `offen` (Z. 1419) |
| engine/tests/seiten_*.mjs, pwa_browser.mjs, stil_abzug.mjs, sprachen_rundgang.mjs | MODIFY | Route umbenennen, Test für alten Link |
| engine/tests/test_nachziehen*.py | CREATE/MODIFY | Test der Umstellung `buchung` |
| beispiel/reisen/beispielreise/plan/routen.yaml | MODIFY | Kommentar zu `buchung:` entfernen |

### Scope Assessment
- Files: ca. 10–12
- Estimated LoC: +120/−60
- Risk Level: MEDIUM (Datenformat und gespeicherte Links/Push-Adressen)

### Technical Approach
1. `offen` → `zu-tun`: neue Route, `#offen` bleibt als dauerhafter Alias (Weiterleitung beim Start), damit gespeicherte Links und bereits versandte Push-Adressen funktionieren. Alias ist Lesetoleranz, keine Altform im Datenformat.
2. Feld `buchung`: Umstellung in `neu.py nachziehen` (Wert `offen`/`angefragt`/Text → Buchung `B-…` bzw. Status), danach Lesepfad in der Vorlage entfernen. Mit Test, gegen beide Beispielreisen (CLAUDE.md, #250).
3. Bleibt bewusst: `varianten_titel`, Einzelform der Merkmalswerte (Entscheidung #267).
4. Teile 1, 2, 4, 5 sind erledigt (#269, #268, Kleinigkeit, Stadtwochenende); #215 danach schließen.

### Dependencies
`buchungChip` (Vorlage 1313–1322, genutzt 1463, 1490); Push-Erzeugung in Wächter/Rückmeldedienst (URL `#offen`); ADR-0001 Prüfstelle, Instanzen-Tests vor dem Vorspulen.

### Open Questions
- [x] Beide Reste umsetzen: PO-Entscheidung 5.11.2026 (beide hier umsetzen, danach #215 schließen)
- [ ] Nutzt eine echte Reise das Feld `buchung` (nur über Instanz-Tests prüfbar)?
