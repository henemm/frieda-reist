---
entity_id: meldeweg-instanz-repo-641
type: feature
created: 2026-11-23
updated: 2026-11-23
status: draft
workflow: fix-641-meldeweg-ohne-reisen-repo
version: "1.0"
tags: [rueckbau, meldeweg, betrieb, instanz, archivierung]
---

# Meldeweg ohne Reisen-Repo: Instanz-Repo als Ziel, altes Repo archivieren (#641, Rest von #557 AC-36)

Folge von #557. Grundlage: `docs/context/fix-641-meldeweg-ohne-reisen-repo.md` (Befund, Analysis, Reihenfolge), `docs/specs/betrieb/rueckbau-git-weg-557.md` (AC-36), `docs/specs/betrieb/rueckbau-nacharbeiten-639.md` (Stil), `docs/betrieb.md` (Abschnitt Meldeweg), ADR-0001.

## Approval

- [ ] Approved

(Keine Produktentscheidung offen. Ziel und Umgang mit überholten Issues sind technisch begründet, siehe Implementation Details.)

## Purpose

Seit #454 und #557 läuft die Instanz ohne ihr privates Reisen-Repo. Eine Abhängigkeit ist geblieben: Meldungen der Stufe `normal` legt das Meldeskript der Instanz als Issue in diesem Repo an. Wird das Repo wie in #557 AC-36 vorgesehen archiviert, ist es schreibgeschützt, und diese Meldungen gingen still verloren. Diese Spec gibt dem Meldeweg ein neues privates Ziel ohne Handschritt, überträgt oder schließt die offenen Issues des alten Repos, bringt Doku, Usage und sichtbare Texte auf den Ist-Zustand und archiviert das alte Repo erst, wenn alles nachgewiesen ist.

## Source

- **File:** `docs/betrieb.md`, `CLAUDE.md`, `README.md`, `engine/konten.py`, `engine/texte_*.py`, `docs/konten.md` (Software-Repo); `<FR_DIENST>/instanz/melden.sh`, `<FR_DIENST>/instanz/einstellungen.env`, `<FR_DIENST>/instanz/tests/` (Instanz, privat); Skripte der Infrastruktur für Sitzungsordner und Meldungszuordnung
- **Identifier:** `fr_einlesen`, `fr_melden` (`betrieb/gemeinsam.sh`, unverändert); Variable `FR_MELDEN_REPO`; Label `betrieb-meldung`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `betrieb/gemeinsam.sh` (`fr_einlesen`, `fr_melden`) | Skript | `fr_einlesen` exportiert jede Zeile `FR_…=wert` aus `<FR_DIENST>/instanz/einstellungen.env`; `FR_MELDEN_REPO` erreicht so `melden.sh` ohne Änderung der Software |
| `<FR_DIENST>/instanz/melden.sh` | Instanz-Skript | Vertrag `<befehl> <normal|high> <betreff> <text> [erledigt]`; Stufe `normal` legt ein Issue mit Label `betrieb-meldung` im Repo `${FR_MELDEN_REPO:-…}` an |
| `gh` des Betriebsbenutzers | Werkzeug | Schreibrecht auf das neue Repo (gleicher Besitzer, vorhanden) |
| `ALARMSTELLEN` in `engine/tests/test_betrieb.py` | Test | Bleibt unverändert; keine neue `high`-Stelle |
| Instanz-Tests unter `<FR_DIENST>/instanz/tests/` | Instanz-Tests | Laufen vor dem Vorspulen mit dem Branch; erhalten den Test zum Meldeziel |
| #557 AC-36 | Spec | Archivierung des alten Repos; wird mit diesem Vorhaben erfüllt |

## Scope

### Im Scope

1. **Neues privates Instanz-Repo** (`<Instanz-Repo>`, Name mit dem Präfix der Instanz, damit Sitzungs- und Meldungszuordnung greifen) als Arbeitsort und Issue-Ziel: Label `betrieb-meldung`, aktualisierte `CLAUDE.md` der Instanz (keine Submodul-Anordnung, Verweis auf `<FR_DIENST>/instanz/`, Anleitung „Instanz-Tests mit einem Branch der Software“ nach Stand #454/#557), kurze README.
2. **Meldeziel umstellen:** `FR_MELDEN_REPO=<Instanz-Repo>` in `<FR_DIENST>/instanz/einstellungen.env`; die Vorgabe in `melden.sh` zeigt ebenfalls auf das neue Repo, damit ein fehlender Eintrag nicht ins Archiv schreibt.
3. **Probemeldung vor dem Archivieren:** Eine Meldung der Stufe `normal` über `fr_melden`, so wie der Betrieb sie auslöst, erscheint als Issue im neuen Repo; danach wird sie geschlossen.
4. **Offene Issues des alten Repos** (sechs Stück): in der Sache noch offene werden mit `gh issue transfer` in das neue Repo übertragen (Kommentare bleiben, alte Verweise leitet GitHub weiter); durch #454/#557 überholte werden vorher geprüft und mit Begründung geschlossen (etwa der Instanz-Test mit Submodul).
5. **Infrastruktur:** Sitzungsordner „reisen“ und Zuordnung Ordner → Instanz „frieda“ in den Meldungsskripten zeigen auf das Instanz-Repo (eigenes Issue im Infrastruktur-Repo, Umsetzung dort).
6. **Software-Repo:** Doku, Usage und sichtbarer Text nennen das Reisen-Repo nicht mehr als aktuellen Ort (Einstellungen unter `<FR_DIENST>/instanz/`, Anleitung und Issues im privaten Repo der Instanz); Test gegen Rückfall.
7. **Archivieren zuletzt:** Erst wenn 2 bis 6 nachgewiesen sind, wird das alte Repo archiviert; Stand in #641 und #557 vermerkt.

### Nicht im Scope (Out of Scope)

- Keine Änderung am Meldeweg der Software (`fr_melden`, `fr_alarm`, Vertrag aus `docs/betrieb.md`); kein neues Modul, kein Formatwechsel, keine Umstellung in `neu.py nachziehen`.
- Keine Kopien von `melden.sh`, `einstellungen.env` oder `tests/` ins Instanz-Repo: Die laufende Fassung bleibt allein in `<FR_DIENST>/instanz/`, wie in #557 entschieden.
- Kein Löschen lokaler Arbeitskopien des alten Repos (nur lesen); ihr Entfernen ist nicht Teil dieses Issues.
- Keine neue Alarmstelle, keine Meldung per Telegram für diese Umstellung.
- Keine Änderung der wirksamen Gate-Konfiguration.
- Keine echten Repo-Namen, Benutzer, Serveradressen, Pfade der Instanz, Reisenamen oder Issue-Nummern des privaten Repos in diesem öffentlichen Repo; nur Platzhalter (`<Reisen-Repo>`, `<Instanz-Repo>`, `<FR_DIENST>`, `<Reise A>`). Historische Dokumente (Specs, `docs/artifacts/`, ADR-Verlauf, `docs/abgleich-*`) bleiben unverändert.

### Affected Files

Software-Repo (öffentlich, dieses Repo):

| File | Change Type | Description |
|------|-------------|-------------|
| `docs/betrieb.md` (Abschnitt Meldeweg, Einstellungen, Archiv) | MODIFY | Ziel der Stufe `normal` ist ein Issue im privaten Repo der Instanz (`FR_MELDEN_REPO` in `einstellungen.env`); kein Reisen-Repo als aktueller Ort |
| `CLAUDE.md`, `README.md` | MODIFY | Einstellungen der Instanz unter `<FR_DIENST>/instanz/`; Anleitung der Instanz-Tests im privaten Repo der Instanz |
| `engine/konten.py`, `docs/konten.md` | MODIFY | Verweis bei `meldung-erledigt`: „Issue im privaten Repo der Instanz“ |
| `engine/texte_*.py` (Schlüssel `konnektor.ontologie_werkzeug.4`) | MODIFY (prüfen) | Text nennt „Sitzung im Reisen-Repo“; anpassen in allen Sprachen, falls der Zweig erreichbar ist, sonst Begründung im PR |
| `betrieb/einstellungen.beispiel`, Kopfkommentare in `betrieb/*.sh`, `betrieb/zustellen.py` | MODIFY (nur Kommentar, falls aktueller Ort genannt) | Beispiel nennt `FR_MELDEN_REPO` mit Platzhalter `<Instanz-Repo>` |
| `engine/tests/test_meldeweg_ziel_641.py` | CREATE | Rückfall-Test für Ist-Doku, Usage und sichtbare Texte |

Instanz (privat, nicht in diesem Repo):

| Ort | Change Type | Description |
|-----|-------------|-------------|
| `<FR_DIENST>/instanz/einstellungen.env` | MODIFY | `FR_MELDEN_REPO=<Instanz-Repo>` |
| `<FR_DIENST>/instanz/melden.sh` | MODIFY | Vorgabe von `FR_MELDEN_REPO` auf das neue Repo |
| `<FR_DIENST>/instanz/tests/` | MODIFY | Test: Meldeziel ist nicht das alte Reisen-Repo (Skript und Einstellung) |

GitHub:

| Ort | Change Type | Description |
|-----|-------------|-------------|
| `<Instanz-Repo>` (privat) | CREATE | Label `betrieb-meldung`, `CLAUDE.md`, README |
| `<Reisen-Repo>` | TRANSFER + ARCHIVE | Offene Issues übertragen oder begründet schließen, danach archivieren |

Infrastruktur (eigenes Repo und Issue dort):

| Ort | Change Type | Description |
|-----|-------------|-------------|
| Skript zum Starten von Sitzungen | MODIFY | Eintrag „reisen“ zeigt auf `<Instanz-Repo>` |
| Meldungsskripte (`ack`, `check-messages`, `check-messages-hook`) | MODIFY | Ordner von `<Instanz-Repo>` ordnen der Instanz „frieda“ zu |

### Estimated Changes

- Software-Repo: 6 bis 8 Dateien, rund +40/-25 Zeilen (Doku, Usage, Text, ein Test)
- Instanz: 2 Dateien und ein Test; GitHub: ein neues Repo, bis zu 6 Übertragungen, eine Archivierung; Infrastruktur: 4 Skripte
- Risk Level: MEDIUM. Der Meldeweg ist ein Betriebspfad, Archivieren ist nur von Hand umkehrbar; die feste Reihenfolge sichert ab.

## Implementation Details

Technischer Ansatz wie in der Analyse (`docs/context/fix-641-meldeweg-ohne-reisen-repo.md`), verbindlich.

**Entscheidung zum Ziel:** Ein neues, schlankes privates Repo der Instanz ist Arbeitsort und Issue-Ziel, nicht Quelle des Betriebs. Verworfen: (a) Issues im Infrastruktur-Repo (mischt Projekt- und Infrastruktur-Issues, gegen die Regel „Projekt-Issues im jeweiligen Repo“); (b) altes Repo umbenennen statt archivieren (widerspricht AC-36, trägt Reisedateien und Submodul weiter); (c) öffentliches Ziel (Meldungen können private Reisedaten enthalten). Doppelte Quellen von `melden.sh`, `einstellungen.env` und `tests/` sind schon einmal auseinandergelaufen und entstehen deshalb nicht neu.

**Reihenfolge (verbindlich):**
1. Instanz-Repo anlegen (privat), Label, `CLAUDE.md`, README.
2. `FR_MELDEN_REPO` setzen, Vorgabe in `melden.sh` ändern, Instanz-Test ergänzen, Probemeldung über `fr_melden` auslösen, Issue im neuen Repo bestätigen und schließen.
3. Offene Issues übertragen oder begründet schließen (Kriterium: in der Sache noch offen gleich übertragen, sonst mit Begründung schließen).
4. Infrastruktur anpassen.
5. Software-Repo: Doku, Usage, Text, Rückfall-Test; PR, grüne Pflichtprüfungen, Vorspulen.
6. Archivieren, erst wenn 2 bis 5 nachgewiesen sind.

**Rückfall-Test (Software-Repo):** Er liest die Ist-Dokumente (`docs/*.md` außer Historie, `CLAUDE.md`, `README.md`), die Usage-Texte der Skripte in `betrieb/` und die Textkataloge `engine/texte_*.py` und prüft, dass `Reisen-Repo` dort nicht als aktueller Ort vorkommt. Ausgenommen sind Specs, `docs/artifacts/`, `docs/adr/` (Verlaufszeilen), `docs/abgleich-*` und eine kurze, im Test begründete Liste einzelner Fundstellen, die das Reisen-Repo ausdrücklich als früheren Zustand beschreiben (zum Beispiel „das frühere Reisen-Repo“). Wie die Ausnahmelisten in `engine/tests/test_texte.py` darf diese Liste nur kürzer werden.

**Instanz-Test:** Er liest die wirksamen Werte (`einstellungen.env` und die Vorgabe in `melden.sh`) und prüft, dass das Meldeziel nicht das alte Reisen-Repo ist und bei fehlendem Eintrag ebenfalls nicht. Der Test steht im privaten Teil; in diesem Repo wird nur seine Aussage spezifiziert, der Name des alten Repos steht nur dort.

## Test Plan

### Automated Tests (TDD RED)

Software-Repo (`engine/tests/test_meldeweg_ziel_641.py`):

- [ ] Test 1: GIVEN `docs/betrieb.md`, `CLAUDE.md` und `README.md` WHEN nach dem Reisen-Repo als aktuellem Ort gesucht wird THEN gibt es keinen Treffer außerhalb der begründeten Ausnahmen.
- [ ] Test 2: GIVEN `engine/konten.py`, `docs/konten.md` und alle `engine/texte_*.py` WHEN der Verweis zu `meldung-erledigt` und `konnektor.ontologie_werkzeug.4` gelesen wird THEN nennen sie das private Repo der Instanz statt des Reisen-Repos, in allen Sprachen.
- [ ] Test 3: GIVEN die Usage-Kopfkommentare in `betrieb/` und `betrieb/einstellungen.beispiel` WHEN sie gelesen werden THEN nennen sie keinen Ort im Reisen-Repo für Einstellungen; `FR_MELDEN_REPO` ist dokumentiert.
- [ ] Test 4: GIVEN die Ausnahmeliste des Tests WHEN sie geprüft wird THEN enthält sie nur Fundstellen, die es noch gibt (sie wird nur kürzer).
- [ ] Test 5: GIVEN `betrieb/gemeinsam.sh` und eine Einstellungsdatei mit `FR_MELDEN_REPO=<Instanz-Repo>` WHEN `fr_einlesen` läuft THEN steht die Variable in der Umgebung eines Stubs von `FR_MELDEN` (belegt, dass kein Eingriff in die Software nötig ist).
- [ ] Test 6: GIVEN `ALARMSTELLEN` WHEN die Suite läuft THEN ist die Liste unverändert.

Instanz (privat):

- [ ] Test 7: GIVEN `einstellungen.env` und `melden.sh` der Instanz WHEN das wirksame Meldeziel der Stufe `normal` bestimmt wird (mit und ohne Eintrag) THEN ist es nie das alte Reisen-Repo.

### Betriebsnachweise (manuell, im Issue festgehalten)

- [ ] Nachweis A (Probemeldung): Ausgabe von `fr_melden normal` aus dem Betrieb und die Ansicht des entstandenen Issues im Instanz-Repo (Label `betrieb-meldung`), danach geschlossen.
- [ ] Nachweis B (Übertragung): Je offenem Issue ein Eintrag „übertragen nach <Instanz-Repo>“ oder „geschlossen, weil …“ mit Begründung; Liste der offenen Issues im alten Repo ist danach leer.
- [ ] Nachweis C (Archivierung): Ausgabe, dass das alte Repo archiviert ist; danach schlägt ein Anlegen eines Issues dort fehl, die Probemeldung ins neue Repo gelingt weiterhin.
- [ ] Nachweis D (Infrastruktur): Verweis auf das Issue und den Stand der vier Skripte; eine Sitzung im Instanz-Repo wird der Instanz „frieda“ zugeordnet.

Alle Nachweise ohne echte Namen und Adressen: Protokolle im öffentlichen Repo nutzen Platzhalter (`engine/tests/test_protokolle_ohne_pfade.py` bleibt grün); die Originale bleiben in privaten Issues.

## Acceptance Criteria

Jedes Kriterium nennt Test oder Nachweis (T = automatisierter Test, N = Betriebsnachweis).

- **AC-1:** Given das Instanz-Repo ist angelegt / When seine Sichtbarkeit abgefragt wird / Then ist es privat, trägt das Label `betrieb-meldung`, und `CLAUDE.md` beschreibt keine Submodul-Anordnung mehr, sondern `<FR_DIENST>/instanz/` und die Instanz-Tests mit einem Branch der Software. (N)
- **AC-2:** Given das Instanz-Repo enthält nur `CLAUDE.md` und README / When es geprüft wird / Then liegen dort keine Kopien von `melden.sh`, `einstellungen.env` oder `tests/`. (N)
- **AC-3:** Given `einstellungen.env` der Instanz / When der Betrieb sie einliest / Then gilt `FR_MELDEN_REPO=<Instanz-Repo>`, ohne Änderung an `fr_einlesen` oder `fr_melden`. (Test 5, N)
- **AC-4:** Given `FR_MELDEN_REPO` fehlt / When `melden.sh` ein Ziel bestimmt / Then ist die Vorgabe das Instanz-Repo, nie das alte Reisen-Repo. (Test 7)
- **AC-5:** Given der Meldeweg ist umgestellt / When eine Meldung der Stufe `normal` über `fr_melden` aus dem Betrieb ausgelöst wird / Then entsteht ein Issue mit Label `betrieb-meldung` im Instanz-Repo, ohne Handschritt. (Nachweis A)
- **AC-6:** Given die Probemeldung ist erschienen / When sie bearbeitet ist / Then ist das Probe-Issue geschlossen und im Issue #641 als Nachweis vermerkt. (Nachweis A)
- **AC-7:** Given die sechs offenen Issues des alten Repos / When die Übertragung abgeschlossen ist / Then ist jedes entweder in das Instanz-Repo übertragen (Kommentare erhalten, alter Verweis führt weiter) oder mit schriftlicher Begründung geschlossen, und kein Issue ist mehr offen. (Nachweis B)
- **AC-8:** Given ein Issue ist durch #454/#557 überholt (zum Beispiel der Instanz-Test mit Submodul) / When es nicht übertragen wird / Then steht in seinem Abschlusskommentar, was es ersetzt. (Nachweis B)
- **AC-9:** Given das Skript für Sitzungen und die Meldungsskripte der Infrastruktur / When sie nach der Umstellung gelesen werden / Then verweisen sie auf das Instanz-Repo statt auf das alte Reisen-Repo, und ein Issue in der Infrastruktur hält es fest. (Nachweis D)
- **AC-10:** Given `docs/betrieb.md`, `CLAUDE.md`, `README.md` / When sie gelesen werden / Then nennen sie als Ort der Einstellungen `<FR_DIENST>/instanz/` und als Ort der Anleitung und der Meldungen das private Repo der Instanz, nicht das Reisen-Repo. (Test 1)
- **AC-11:** Given `engine/konten.py`, `docs/konten.md` und die Textkataloge aller Sprachen / When der Hinweis bei `meldung-erledigt` und der Text `konnektor.ontologie_werkzeug.4` gelesen werden / Then nennen sie das private Repo der Instanz; die Schlüssel sind in allen Sprachen vorhanden, `engine/tests/test_texte.py` bleibt grün. (Test 2)
- **AC-12:** Given die Usage-Kommentare und `betrieb/einstellungen.beispiel` / When sie gelesen werden / Then ist `FR_MELDEN_REPO` mit Platzhalter beschrieben und das Reisen-Repo nicht als Ort der Einstellungen genannt. (Test 3)
- **AC-13:** Given der Rückfall-Test / When jemand das Reisen-Repo wieder als aktuellen Ort in Ist-Doku, Usage oder sichtbare Texte schreibt / Then wird die Suite rot; Specs und Historie sind ausgenommen, die Ausnahmeliste wird nur kürzer. (Tests 1, 4)
- **AC-14:** Given die Reihenfolge / When das alte Repo archiviert wird / Then liegen AC-5 bis AC-9 bereits nachgewiesen vor; die Archivierung ist der letzte Schritt. (Nachweis C)
- **AC-15:** Given das alte Repo ist archiviert / When erneut eine Probemeldung der Stufe `normal` ausgelöst wird / Then gelingt sie im Instanz-Repo, und das Archiv bleibt unverändert. (Nachweis C)
- **AC-16:** Given dieses öffentliche Repo / When Spec, Doku, Tests und Nachweise gelesen werden / Then enthalten sie keine echten Repo-Namen, Benutzer, Serveradressen, Instanzpfade, Reisenamen und keine Issue-Nummern des privaten Repos (`test_protokolle_ohne_pfade.py` grün).
- **AC-17:** Given die vollständige Testsuite / When sie läuft / Then ist sie grün (`engine/.venv/bin/python -m pytest -q -n 3 engine/tests`), `ALARMSTELLEN` ist unverändert, und die Instanz-Tests laufen vor dem Vorspulen mit dem Branch ohne neuen Fehler gegenüber `main`. (Test 6)
- **AC-18:** Given alle Schritte erledigt / When #641 und #557 geprüft werden / Then tragen beide den Endstand (Ziel, Übertragungen, Archivierung) und AC-36 aus #557 ist erfüllt; #641 wird erst dann geschlossen.

## Definition of Done

- [ ] Alle Acceptance Criteria AC-1 bis AC-18 erfüllt, Nachweise A bis D im Issue.
- [ ] `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` grün; Pflichtprüfungen der CI grün.
- [ ] Tests der Instanz vor dem Vorspulen mit dem Branch grün.
- [ ] Altes Repo archiviert, zuletzt und erst nach den Nachweisen.
- [ ] #641 mit Endstand geschlossen, #557 vermerkt.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Abschluss der Entscheidungen aus #557 und ADR-0009 (Betrieb ohne Reisen-Repo, laufende Fassung nur unter `<FR_DIENST>/instanz/`); die Wahl des Ziels ist eine Betriebsentscheidung ohne neues Muster, ohne Formatwechsel und ohne neue Schnittstelle der Software.

## Changelog

- 2026-11-23: Initial spec created
