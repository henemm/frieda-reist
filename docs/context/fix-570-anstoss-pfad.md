# Context: fix-570-anstoss-pfad

## Request Summary
Der Schreibweg soll nach jedem Schreibvorgang das Veröffentlichen auch im Software-Klon (#454) sofort anstoßen. Heute sucht er
das Skript nur in der alten Anordnung (`<FR_WURZEL>/frieda/betrieb/veroeffentlichen.sh`) und schweigt, wenn es fehlt.

## Ursache (belegt)
- `engine/schreiben.py:5106-5107` (`Schreiber.__init__`): Vorgabe `self.wurzel / "frieda" / "betrieb" / "veroeffentlichen.sh"`.
  Im Software-Klon ist `FR_WURZEL` der Klon selbst, `frieda/` gibt es nicht.
- `engine/schreiben.py:5282-5283` (`veroeffentlichen_anstossen`): `if not Path(...).exists(): return` — still, ohne Zeile im Journal.
- Folge: Seite erst mit dem nächsten Timer-Lauf (bis 5 min); `veroeffentlichen-anstoss.log` ohne Eintrag seit 13.11. 07:19 UTC.

## Related Files
| File | Relevance |
|------|-----------|
| engine/schreiben.py | `Schreiber.__init__` (Pfad), `veroeffentlichen_anstossen` (stilles Zurückkehren) |
| betrieb/gemeinsam.sh:46-48 | `fr_alte_anordnung`: alt, wenn `<FR_WURZEL>/.gitmodules` existiert oder `<FR_WURZEL>/frieda/betrieb` ein Ordner ist |
| engine/schreiben_git.py:139,201 | erzeugt `Schreiber` (übernimmt `s.veroeffentlichen`) |
| engine/tests/test_schreiben.py:1470-1660 | Tests zum Anstoß (Priorität, Protokoll, ohne nice); alle mit expliziter Wurzel |
| engine/tests/test_software_weg_454.py | Fixture `l1` für den Software-Klon (setzt `SB_VEROEFFENTLICHEN`) |
| docs/specs/betrieb/software-weg-454.md | Spec der neuen Anordnung; beide Anordnungen bis zum Rückbau |

## Existing Patterns
- Shell: `fr_alte_anordnung` entscheidet zwischen alter und neuer Anordnung; die Python-Seite hat dafür kein Gegenstück.
- Überschreibbar für Tests: `SB_VEROEFFENTLICHEN` (Vorrang vor der Vorgabe), Argument `veroeffentlichen`.
- Fehler beim Start schreibt der Anstoß nach `sys.stderr` („Publishing not started …“) — das landet im Journal des Dienstes.

## Dependencies
- Upstream: `os.environ`, `pathlib`, `instanz.dienst()`.
- Downstream: alle Schreibvorgänge (`schreiben`, `anwenden_extern`), `schreiben_git`.

## Lücke (warum nicht aufgefallen)
Jeder Test setzt `SB_VEROEFFENTLICHEN` oder ruft mit explizitem Skript; die Vorgabe des Pfads war nie geprüft. Das stille
`return` versteckte den Fehler auch im Betrieb (nur die Laufzeit-Warnung > 120 s zeigte ihn indirekt).

## Analyse / Ansatz
1. Kleine Funktion `veroeffentlichen_skript(wurzel)` in `engine/schreiben.py`: dieselbe Regel wie `fr_alte_anordnung`
   (`.gitmodules` vorhanden oder `frieda/betrieb` ein Ordner → `<wurzel>/frieda/betrieb/veroeffentlichen.sh`,
   sonst `<wurzel>/betrieb/veroeffentlichen.sh`). `Schreiber.__init__` nutzt sie als Vorgabe.
2. `veroeffentlichen_anstossen`: fehlt das Skript, eine Zeile nach `sys.stderr` (Journal) statt still zurück; wirft weiter nie.
3. Tests: Vorgabe in beiden Anordnungen; fehlendes Skript → Zeile auf stderr, kein Start.

Kein neues Modul (deploy.sh-Liste unberührt), nichts Instanz- oder Reisespezifisches. ADR-0001: reine Betriebsfehlerbehebung.

## Risks & Considerations
- Kein Risiko für die alte Anordnung: Regel identisch zur Shell-Seite.
- Ohne `SB_VEROEFFENTLICHEN` rufen Tests mit einem Software-Klon als Wurzel künftig das echte `betrieb/veroeffentlichen.sh` des
  Testordners — dort gibt es keins (tmp), also nur die neue Journal-Zeile. Tests mit dem Repo selbst als Wurzel setzen den Stummel.

## Analysis

### Type
Bug

### Ursache (im Code bestätigt, 14.11.2026)
`Schreiber.__init__` (`engine/schreiben.py:5106-5107`) ist die einzige Python-Stelle, die noch fest `<wurzel>/frieda/betrieb/...`
annimmt (Suche nach `"frieda"` in engine/ und betrieb/). `veroeffentlichen_anstossen` (`:5282-5283`) kehrt bei fehlendem Skript
still zurück. Kein Unit-File setzt `SB_VEROEFFENTLICHEN`; im Betrieb gilt also immer die Vorgabe.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/schreiben.py | MODIFY | Funktion `veroeffentlichen_skript(wurzel)` (Regel wie `fr_alte_anordnung`), Vorgabe in `Schreiber.__init__`, Kopfkommentar Z. 34 (Pfad je Anordnung); fehlendes Skript → eine Zeile nach stderr |
| engine/tests/test_schreiben.py (oder neue Testdatei zu #570) | MODIFY/CREATE | Vorgabe in alter Anordnung (`.gitmodules` bzw. Ordner `frieda/betrieb/`) und neuer Anordnung; fehlendes Skript → Zeile auf stderr, kein Start, wirft nicht |
| betrieb/messlauf-schreibweg.py | unverändert | setzt absichtlich ein fehlendes Skript (Veröffentlichen aus); bekommt künftig nur die stderr-Zeile – erwünscht |

### Scope Assessment
- Files: 2 (Code + Tests)
- Estimated LoC: +15/-3 Code, +50 Tests
- Risk Level: LOW — Regel identisch zur Shell-Seite; alte Anordnung liefert denselben Pfad wie bisher; `SB_VEROEFFENTLICHEN` und das Argument behalten Vorrang.

### Technical Approach
1. `veroeffentlichen_skript(wurzel)`: `.gitmodules` vorhanden oder `frieda/betrieb` ein Ordner → `<wurzel>/frieda/betrieb/veroeffentlichen.sh`, sonst `<wurzel>/betrieb/veroeffentlichen.sh`.
2. `Schreiber.__init__`: Reihenfolge Argument → `SB_VEROEFFENTLICHEN` → `veroeffentlichen_skript(self.wurzel)`.
3. `veroeffentlichen_anstossen`: leerer Pfad weiterhin still; nicht vorhandenes Skript → Zeile `Publishing not started (<pfad>): script missing` nach stderr (englisch wie die bestehende Meldung; Betriebsprotokoll, kein sichtbarer Text nach ADR-0006), dann zurück. Wirft nie.
4. Kein neues Modul, keine Änderung an deploy.sh, Units, Reisedaten-Format (kein `nachziehen`), keine Meldungstexte für Instanzen. Abnahme auf dem Server: nach einem Schreibvorgang neuer Eintrag in `veroeffentlichen-anstoss.log`, Seite nach Sekunden statt Minuten.

### Dependencies
`schreiben_git.py:201` reicht `s.veroeffentlichen` weiter (profitiert automatisch). Tests mit Stummel über `SB_VEROEFFENTLICHEN` unberührt.

### Open Questions
- keine (reine Betriebsfehlerbehebung, Lösung im Issue vom Besitzer beschrieben)
