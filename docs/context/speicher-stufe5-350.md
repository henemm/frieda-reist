# Context: speicher-stufe5-350

## Request Summary

Stufe 5 des Reisespeichers (#350, Teil von #345, ADR-0009): Alle Reisen einer Instanz laufen je Reise über den Reisespeicher statt über Git (Schalter `FR_SPEICHERREISEN`, Reihenfolge Testreise → kleinste echte Reise → übrige; vor jeder Umschaltung Vergleichslauf „gleich“, danach Prüfung im Konnektor). Schreibweg und Veröffentlichen kommen ohne GitHub-Zugang aus, das alte Repo der Instanz bleibt Archiv. Instanzspezifisches liegt im privaten Reisen-Repo (dort Issue #252), nicht hier.

## Stand (aus den Kommentaren im Issue, 9.11.2026)

- Testreise „Ablage 349 (erfunden)“ ist umgeschaltet: Wanderung mit GPX aus der Ablage, Foto (2,2 MB) nach `ablage-umstellung` in der Ablage, Tageskarte zeigt die Spur, auch offline (Chromium).
- Rundgang „Reise ohne Pläne“: Beispielreise Stadtwochenende lokal ohne Befund (Chromium, WebKit); auf der Instanz braucht die Seite Anmeldung → nächster Schritt Prüfsitzung (`betrieb/pruefsitzung.py`, storageState) + `engine/tests/seiten_browser.mjs` gegen die echte Adresse.
- Offen: AC-27 aus #349 (Schreiben bis Veröffentlichen mit ~110 MB Fotos, Ziel < 120 s), Rückholung der Sicherung außer Haus (#347), kleinste echte Reise, übrige Reisen, #252 im Reisen-Repo.
- Offene Produktfrage: Foto-Link im Wissenstext wird auf der Seite nicht als Bild gezeigt, nur als Datei ausgeliefert.
- Lehre: Handbefehle (`pruefen`, Schreiben) immer mit dem Code der Instanz (`<FR_DIENST>/reisespeicher.py`), nie mit dem Untermodul des Reisen-Repos.

## Related Files

| Datei | Relevanz |
|------|-----------|
| `engine/instanz.py:116-130` | `speicherreisen()`: liest den Schalter (Umgebung vor `einstellungen.env`, unlesbar → Fehler, #361) |
| `engine/schreiben.py` ~5096-5207 | `anwenden_extern`: Verzweigung Speicherweg/Git-Weg, 503 wenn Reise in Liste aber nicht im Speicher |
| `engine/schreiben_git.py:171,179` | Git-Weg lehnt Speicherreisen ab |
| `engine/stand.py:151-160`, `engine/stand_git.py` | Stand für die Seite aus Speicher bzw. Git |
| `engine/reisespeicher.py` (CLI ab 880) | `importieren`, `exportieren`, `verlauf`, `vergleichen`, `pruefen`, `sichern`, `materialisieren`, `zustand`, `staende`, `zuruecksetzen` (714: neuer Vorgang mit altem Inhalt, Verlauf bleibt) |
| `engine/neu.py` ~1003-1047, 1357 | `nachziehen-speicher` inkl. `ablage_umstellen` (Vorgang `ablage-umstellung`) |
| `betrieb/gemeinsam.sh:103-114` | `speicherreisen()` in Shell |
| `betrieb/veroeffentlichen.sh:158-182, 362-397, 481-494` | Speicherreisen vor `git fetch`; Git-Teil (fetch/merge, `gh workflow run`, `git ls-remote`) läuft weiter für Git-Reisen und Software |
| `betrieb/software-nachziehen.sh`, `.yml` | überspringt Speicherreisen; sonst Git/GitHub |
| `betrieb/vergleichslauf.sh` | Vergleich Git (`git archive HEAD`) gegen Speicher; „bis Stufe 5 Auskunft, keine Sperre“ (Z. 4-5) |
| `betrieb/einrichten.sh:61,67` | prüft `git ls-remote origin`, `gh auth status` |
| `betrieb/deploy.sh:24,32`, `betrieb/einstellungen.beispiel:38-40` | Schalter dokumentiert |
| `betrieb/pruefsitzung.py`, `engine/tests/seiten_browser.mjs`, `betrieb/startprobe.mjs` | Browser-Rundgang auf angemeldeten Seiten |
| `betrieb/messlauf-schreibweg.py` | Messung Schreibweg (für AC-27) |
| `docs/betrieb.md:35-39, 89-97, 157-160, 229, 243, 276, 294, 397-399` | Sicherung, Speicherweg, Anfangsvorgang/Vergleichslauf, Schalter-Tabelle, Seite zurücknehmen per `git revert` |
| `docs/adr/0009-reisespeicher.md:20,28` | Sicherung und Grenzen |

## Existing Patterns

- Je Reise ein Schalter, eine Quelle; Git-Weg und Speicherweg schließen sich gegenseitig aus (503 statt Doppelschreiben).
- Anfangsvorgang: `importieren … --ab <n−1>`, Stand-Nummer läuft ohne Sprung weiter; danach Vergleichslauf mit Stempel `<FR_DIENST>/vergleich/<reise>.json`.
- Formatwechsel ziehen Speicherreisen beim Veröffentlichen selbst nach (`nachziehen-speicher`), Git-Reisen über den Workflow „Software nachziehen“ (#250).
- Zurücksetzen auf früheren Stand = neuer Vorgang (`zuruecksetzen`), nur anhängen.

## Dependencies

- Upstream: SQLite-Reisespeicher (`<FR_SPEICHER>`), Ablage (`<FR_ABLAGE>`), Server-Backup der Instanz (außer Haus, restic liegt in der Instanz, nicht im Repo), Einstellungen der Instanz.
- Downstream: Konnektor (über Schreibdienst), Veröffentlichen, `publish_status`, Wächter (Schnappschuss), Monitor (`zustand`), Reisen-Repo der Instanz (#252, dessen Tests).

## Existing Specs

- `docs/specs/…/speicher-346-stufe1.md`, `speicher-347-stufe2.md`, `speicher-347-tempo.md`, `speicher-348-stufe3.md`, `speicher-349-stufe4.md`; Kontexte `docs/context/reisespeicher-346.md`, `schreibweg-speicher-347.md`, `speicher-348-stufe3.md`, `speicher-349-stufe4.md`.

## Mögliche Software-Lücken für Stufe 5 (zu klären in /20-analyse)

- `vergleichslauf.sh` ist nur Auskunft; soll ein fehlender/alter Stempel „gleich“ die Umschaltung sperren (z. B. Schreibweg/Veröffentlichen verweigert eine Speicherreise ohne Stempel)?
- Wenn alle Reisen im Speicher sind: `veroeffentlichen.sh` macht weiter `git fetch/merge` der Reisen, `einrichten.sh` prüft `gh auth`; ohne GitHub-Zugang muss das entfallen (Akzeptanz: „ohne GitHub-Zugang“). Wie erkennt die Software „keine Git-Reisen mehr“ — leere Git-Liste oder Einstellung?
- „Workflows der Instanz bei GitHub entfallen“: `software-nachziehen.yml` und `gh workflow run` aus `veroeffentlichen.sh` ohne Git-Reisen überflüssig.
- Rückweg Speicher → Git nicht beschrieben (Rückfallplan während der Umschaltung).
- Doku: eigener Abschnitt „Umschaltung einer Reise“ in `docs/betrieb.md` fehlt.
- Kein Test für Stufe 5.

## Risks & Considerations

- Echte Reisen: nie Inhalte in dieses Repo; Abnahme nur an Testreise/erfundenen Daten, an beiden Reisetypen.
- Vorbedingung vor echter Reise: Rückspielversuch der Sicherung außer Haus (#347) nachgewiesen.
- Parallele Sitzungen: Umschaltung vorher im Issue ansagen.
- Änderungen an Umgebungswerten/Skripten, die die Instanz nutzt → Tests des Reisen-Repos mit dem Branch laufen lassen.
- Keine Handschritte nach Software-Wechsel (#250).

## Analysis

### Type
Feature (Betriebsumstellung, Software-Anteil von Stufe 5). Die eigentliche Umschaltung der echten Reisen ist Arbeit an der Instanz (privates Reisen-Repo), nicht in diesem Repo.

### Befunde (Code gelesen, 9.11.2026)

1. **Vergleichslauf ist nur Auskunft.** `betrieb/vergleichslauf.sh` (Kopf Z. 4-5, 12-13) schreibt den Stempel `<FR_DIENST>/vergleich/<reise>.json`, aber weder `speicher_reisen_lauf` (`betrieb/veroeffentlichen.sh:158`) noch der Schreibweg (`engine/schreiben.py`, `anwenden_extern`) lesen ihn. Eine Reise lässt sich also ohne „gleich“ umschalten. Laut Kommentar und ADR-0009 (Z. 44) soll das in Stufe 5 erzwungen werden.
2. **Veröffentlichen wird ohne GitHub rot.** `main()` in `betrieb/veroeffentlichen.sh:484` ruft `git fetch -q origin main` unter `set -euo pipefail`. Der Speicher-Teil ist dann zwar schon gebaut (Z. 480-482), aber der Lauf endet mit Exit ≠ 0 (systemd „failed“, kein `erfolg_melden`, Heartbeat bleibt aus). Akzeptanz „Veröffentlichen kommt ohne GitHub-Zugang aus“ ist damit verletzt.
3. **Software kommt weiter über das Reisen-Repo.** Der Bauordner ist ein Klon des Reisen-Repos, die Software steckt darin als Submodul `frieda/`; neue Software erreicht die Instanz nur, wenn der Workflow „Software nachziehen“ (`betrieb/software-nachziehen.yml`) den Submodul-Zeiger hebt, angestoßen per `gh workflow run` (`software_anstossen`, `anstoss_weitergeben`). „Workflows der Instanz entfallen“ hieße, dass die Instanz die Software direkt holt — ein Umbau des Software-Wegs (Rot-Datei, `software_kennung`, Prüfung vor Deploy hängen am Commit des Bauordners).
4. **Rückweg Speicher → Git** ist nirgends beschrieben (Rückfallplan während der Umschaltung). Werkzeuge existieren: `reisespeicher.py exportieren`, Reise aus `FR_SPEICHERREISEN` nehmen.
5. **Zurücksetzen** (Akzeptanz 3) ist gebaut: `reisespeicher.py zuruecksetzen` (neuer Vorgang mit altem Inhalt, Verlauf bleibt), getestet in `engine/tests/test_reisespeicher.py`. Fehlt nur in der Betriebsanleitung als Schritt.
6. **Sicherung außer Haus** (Akzeptanz 2): Schnappschuss täglich im Wächter (`betrieb/waechter.sh:31`), restic und Rückspielversuch sind Instanzsache (#347, #384). Kein Software-Anteil offen.
7. Doku: Kein Abschnitt „Umschaltung einer Reise“ in `docs/betrieb.md`; ADR-0009 hat keine Zeile für Stufe 5.

### Entscheidung zum Software-Weg (Tech Lead)

| Variante | Was | Aufwand/Risiko | Akzeptanz |
|---|---|---|---|
| A | Reisen-Repo bleibt Träger der Software (Submodul, Workflow hebt nur noch den Zeiger); Reiseinhalte ganz ohne Git; ein ausgefallenes GitHub macht das Veröffentlichen nicht mehr rot, sondern nur die Software-Aktualisierung wartet (Warnung) | klein, gezielt; berührt nur `main()` und Tests | Schreibweg und Veröffentlichen der Reisen ohne GitHub: erfüllt. Workflow „Software nachziehen“ bleibt (schrumpft auf den Zeiger) |
| B | Instanz holt die Software direkt aus dem öffentlichen Repo, Reisen-Repo wird reines Archiv, keine Workflows | groß: Software-Weg, Rot-Datei, Kennung, Prüfung vor Deploy neu; Risiko am Live-System hoch | erfüllt auch „Workflows entfallen“ |

**Empfehlung: A in #350**, B als eigenes Folge-Issue (Software-Weg ohne Reisen-Repo). Begründung: Die Akzeptanz verlangt Unabhängigkeit der **Reisedaten** von GitHub; die Software stammt ohnehin von GitHub. B ist ein eigener, riskanter Umbau ohne Nutzen für den Reisebetrieb und gehört nicht in denselben Schritt wie die Umschaltung echter Reisen (eine Änderung zur Zeit). Gegen A spricht nur der Wortlaut „Workflows entfallen“ im Umfang (nicht in der Akzeptanz); das Issue wird entsprechend präzisiert.

### Affected Files (with changes)

| File | Change Type | Description |
|------|-------------|-------------|
| `betrieb/veroeffentlichen.sh` | MODIFY | (a) Sperre: Speicherreise ohne Stempel `.gebaut` (erste Veröffentlichung aus dem Speicher), die in Git unter `reisen/<r>` liegt und keinen Vergleichsstempel „gleich“ hat → nicht bauen, Hinweis, Reise bleibt auf dem alten Stand. (b) `git fetch` gescheitert → Warnung „Software-Aktualisierung wartet“, Ergebnis des Laufs = Ergebnis des Speicher-Teils (gemerkt, ab einer Frist Warnung im Zustand statt Alarm je Lauf) |
| `engine/instanz.py` | MODIFY | Hilfsfunktion „Umschaltung freigegeben?“ (Stempel lesen), gemeinsam für Schreibweg und Tests |
| `engine/schreiben.py` | MODIFY | `anwenden_extern`: Speicherreise, die in Git liegt, noch nie aus dem Speicher veröffentlicht wurde und keinen Stempel „gleich“ hat → 503 mit eigenem Text, nichts geschrieben |
| `engine/texte_*.py` | MODIFY | neuer Fehlertext (alle Sprachen) |
| `betrieb/vergleichslauf.sh` | MODIFY | Kopfkommentar: Stempel ist ab Stufe 5 Voraussetzung |
| `engine/tests/test_speicher_stufe5.py` | CREATE | Sperre ohne Stempel (Veröffentlichen, Schreibweg), mit „gleich“ frei, Reise nur im Speicher frei, bereits umgeschaltete Reise (Stempel `.gebaut`) unberührt; Veröffentlichen mit unerreichbarem `origin` grün für Speicherreisen |
| `docs/betrieb.md` | MODIFY | Abschnitt „Umschaltung einer Reise“: Reihenfolge, Anfangsvorgang, Vergleichslauf, Schalter, Prüfung im Konnektor, Rückweg Speicher → Git, Zurücksetzen, Archiv |
| `docs/adr/0009-reisespeicher.md` | MODIFY | Zeile Stufe 5 |

### Scope Assessment
- Files: ~8
- Estimated LoC: +250/-20 (davon ~150 Tests, ~60 Doku)
- Risk Level: MEDIUM — `veroeffentlichen.sh` ist der Lieferweg aller Reisen; die Sperre darf die schon umgeschaltete Testreise nicht treffen (daher nur ohne `.gebaut`-Stempel). Instanz-Tests mit dem Branch laufen lassen (Umgebungswerte/Meldungen ändern sich).

### Technical Approach
Variante A: Sperre aus Vergleichsstempel nur für die **erste** Umschaltung (kein `.gebaut`, Reise liegt in Git), in Veröffentlichen und Schreibweg gleich geregelt; `git fetch` ohne Netz kein Fehler des Laufs mehr; Rückweg und Zurücksetzen als Betriebsschritte dokumentiert. Danach (Instanz, nicht hier): kleinste echte Reise, übrige, AC-27-Messung, Rückspielversuch #347.

### Dependencies
- Hängt an: Stufen 1-4 (gebaut), Stempel von `vergleichslauf.sh`, `reise-stand/<r>.gebaut` aus `speicher_reisen_lauf`.
- Wirkt auf: Reisen-Repo der Instanz (Tests mit dem Branch), Monitor der Instanz (Warnung statt rot bei GitHub-Ausfall).

### Open Questions
- Keine Produktfrage. Folge-Issue für Variante B anlegen (Software-Weg ohne Reisen-Repo). Die Produktfrage Foto-Link im Wissenstext gehört nicht zu #350, eigenes Issue.
