---
entity_id: speicher-348-stufe3
type: feature
created: 2026-11-06
updated: 2026-11-06
status: draft
workflow: speicher-348-stufe3
version: "1.0"
tags: [reisespeicher, veroeffentlichen, nachziehen, vergleichslauf, ueberwachung, betrieb, epic-345]
---

# Speicher Stufe 3: Veröffentlichen und Nachziehen aus dem Reisespeicher (#348, Epic #345)

Grundlage: `docs/context/speicher-348-stufe3.md` (Kontext und Analyse), ADR-0009, `schreibweg-speicher-347.md` (Stufe 2).

## Approval

- [ ] Approved
- [ ] Die drei Annahmen A-1 bis A-3 (unten) vom Product Owner bestätigt

## Purpose

Ab Stufe 2 (#347) schreibt der Schreibweg die Reisen aus `FR_SPEICHERREISEN` in den Reisespeicher (SQLite, ADR-0009). Gebaut und veröffentlicht wird aber noch nur aus Git: Eine Speicher-Reise bleibt auf der Seite bei „wartet“, und „Software nachziehen“ ist ein GitHub-Workflow, der den Speicher gar nicht sieht. Diese Stufe schließt die Lücke, ohne eine Instanz zu verändern, die nichts einstellt:

1. Eine Reise wird aus dem Speicher in einen Ordner für den Generator gebracht (materialisiert), und ein **Vergleichslauf** zeigt, ob der Export aus der Datenbank dem Dateistand aus Git gleicht.
2. `veroeffentlichen.sh` baut Speicher-Reisen aus dem Speicher, im **gemischten Betrieb** neben den Git-Reisen, und braucht dafür kein GitHub.
3. Speicher-Reisen werden bei einem Software-Wechsel **auf dem Server** mit `neu.py nachziehen` umgestellt, vom vorhandenen 5-Minuten-Lauf, ohne neue systemd-Einheit.
4. Der Zustand von Sicherung und Nachziehen ist **prüfbar**, damit der Monitor der Instanz ihn überwachen kann.

Dazu kommt ein **Prüfpunkt** (kein Code): die Rückholung der Sicherung aus dem Off-Site-Archiv, der Rest von #347.

Die Teile sind einzeln lieferbar (jeder auf `main`, wenn grün). Teil 2 braucht Teil 1, Teil 3 braucht Teil 2; Teil 4 und der Prüfpunkt sind unabhängig.

## Source

- **File:** `engine/reisespeicher.py`, `engine/neu.py`, `engine/stand.py`, `betrieb/veroeffentlichen.sh`, `betrieb/deploy.sh`, `betrieb/gemeinsam.sh`, `betrieb/freischalten.sh`, `betrieb/software-nachziehen.sh`; neu `betrieb/vergleichslauf.sh`, `engine/tests/test_speicher_stufe3.py`
- **Identifier:** `reisespeicher.materialisieren`, `reisespeicher.vergleichen`, `reisespeicher.zustand`, `neu.nachziehen_speicher`, `stand.fuer_seite`, `ist_speicherreise`, `reise_stand_schreiben`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `engine/reisespeicher.py` (Stufe 1 und 2, ADR-0009) | Modul | Export, `ordner_als_vorgang`, Prüfsummen, Stand-Nummer |
| `engine/instanz.py` | Modul | `speicher()`, `speicherreisen()` (`FR_SPEICHER`, `FR_SPEICHERREISEN`) |
| `engine/stand.py`, `engine/stand_git.py` | Module | Stand der Seite je Quelle (`fuer_seite`) |
| `engine/neu.py` | Modul | `nachziehen` (Umstellung eines Ordners), Grundlage von `nachziehen-speicher` |
| `engine/bauen.py` | Modul | Probebau und Bau aus einem Ordner; kennt weder Git noch Speicher |
| `engine/waechter.py` | Modul | `rot-melden`, Rot-Datei, Meldeweg `FR_MELDEN` |
| `betrieb/waechter.sh` | Skript | Sicherung `reisen.db` und Stempel `waechter-erfolg` |
| `betrieb/units.py`, 5-Minuten-Lauf `veroeffentlichen` | Betrieb | vorhandener Zeitgeber, keine neue Einheit (A-1) |
| `docs/specs/betrieb/schreibweg-speicher-347.md`, `speicher-347-tempo.md`, `software-nachziehen-161.md`, `-168.md`, `software-wechsel-ohne-handarbeit-250.md` | Specs | Vorgaben für Schreibweg, Tempo, Tor und Software-Wechsel |
| `docs/adr/0009-reisespeicher.md`, `docs/adr/0001-kern.md` | ADR | Rahmen und Prüfstelle |
| Infra-Repo der Instanz, `scripts/monitor.sh`; Off-Site-Archiv | Betrieb | Teil-Check der Überwachung; Rückholung (Prüfpunkt) |

## Scope

### Im Scope

- **Teil 1:** Materialisieren (`reisespeicher.py materialisieren`), Vergleichslauf (`reisespeicher.py vergleichen`, `betrieb/vergleichslauf.sh`) samt Stempel, Messung mit der 110-MB-Testreise.
- **Teil 2:** `veroeffentlichen.sh`, `deploy.sh`, `gemeinsam.sh`, `freischalten.sh`: Speicher-Reisen bauen und veröffentlichen, Stand-Nummer aus dem Speicher, gemischter Betrieb, Lauf ohne GitHub. `stand.py` lädt den Speicher mit einem normalen Import (Hinweis „mit Stufe 3“ eingelöst).
- **Teil 3:** `neu.py nachziehen-speicher`, Aufruf aus `veroeffentlichen.sh`, Rot-Weg ohne `gh`; `software-nachziehen.sh` überspringt Speicher-Reisen.
- **Teil 4:** `reisespeicher.py zustand` (prüfbare Zustände), Dokumentation für den Monitor; ein eigenes Issue im Infra-Repo der Instanz für den Teil-Check.
- Vorgaben und Dokumentation: `betrieb/einstellungen.beispiel`, `docs/betrieb.md`, Modullisten in `betrieb/deploy.sh`, Anpassung des Modulbindungs-Tests in `engine/tests/test_reisespeicher.py`.
- Prüfpunkt Rückholung aus dem Off-Site-Archiv.

### Affected Files

Siehe Abschnitt „Dateien“ weiter unten (18 Dateien, davon 2 neu).

### Estimated Changes

- Dateien: 18 (2 neu)
- Umfang: ca. +700 / −150 Zeilen (Schätzung aus der Analyse)
- Risiko: hoch, weil die Skripte für alle Reisen einer Instanz laufen. Gegenmittel: Schalter je Reise, ohne Einstellung ändert sich nichts; der Git-Weg bleibt bis Stufe 5 unangetastet.

### Nicht im Scope

- **Umschalten einer echten Reise** (Stufe 5, #350). In dieser Stufe steht keine echte Reise in `FR_SPEICHERREISEN`.
- **Erzwingen** des Vergleichslaufs vor dem Umschalten (Stufe 5, siehe A-3).
- Auslagerung der Fotos aus der Datenbank (Stufe 4, #349), Entfernen des Git-Wegs und des Workflows (Stufe 5), Hash-Kette.
- Neue systemd-Einheit oder neuer Timer; Rechte für `gh` (siehe A-1, A-2).
- Der Teil-Check selbst im Monitor der Instanz (eigenes Issue im Infra-Repo; hier nur die prüfbaren Zustände).
- Änderungen am Format der Reisedaten: Es ändert sich keines, also braucht `neu.py nachziehen` keine neue Umstellung (CLAUDE.md, #250).

## Annahmen, vom Product Owner zu bestätigen

Die Analyse nennt drei offene Fragen. Diese Spec baut auf der Empfehlung der Analyse auf; jede Annahme ist so geschnitten, dass sie sich später ändern lässt, ohne die übrigen Teile umzubauen.

| Nr. | Frage | Annahme (Empfehlung der Analyse) | Folge, wenn der Product Owner anders entscheidet |
|---|---|---|---|
| A-1 | Zeitgeber für das Nachziehen auf dem Server | Der **vorhandene** Lauf `veroeffentlichen` (Timer alle 5 Minuten) trägt das Nachziehen mit. Keine neue Einheit, kein neuer Timer (`units.py` sperrt neue Einheiten ohnehin). | Eine eigene Einheit bräuchte eine Freigabe und eine Erweiterung der Erlaubnisliste in `units.py` und im Hilfsprogramm mit Root-Rechten; Teil 3 riefe dieselbe Funktion nur von dort. |
| A-2 | Meldung bei rotem Tor ohne GitHub | Der Dienstbenutzer bekommt **keine** `gh`-Rechte für Issues. Rot heißt: Rot-Datei (`reise`-Art) und die vorhandene Meldung über `FR_MELDEN` (Organisator:innen der Reise sofort, Betrieb nach `FR_ROT_MELDEN_NACH_MINUTEN`). Kein Issue vom Server. | Mit `gh`-Rechten könnte der Server zusätzlich ein Issue (Label `software-nachziehen`) anlegen; das ist eine Sicherheitsentscheidung. |
| A-3 | Vergleichslauf als Voraussetzung zum Umschalten | In Stufe 3 gibt es den **Befehl und einen Stempel** (Zeit, Ergebnis, Stand). Erzwungen wird er erst in Stufe 5 (#350). | Soll `FR_SPEICHERREISEN` schon jetzt einen Reise-Eintrag ohne gleichen Vergleich ablehnen, kommt eine Prüfung im Lesen von `instanz.speicherreisen()` und im Schreibweg dazu (nicht gebaut). |

Weitere offene Annahmen, die ich nicht belegen konnte, stehen im Abschnitt „Risiken und offene Annahmen“.

## Entscheidungen mit Begründung

1. **Ohne Einstellung ändert sich nichts.** Jeder neue Pfad hängt an `FR_SPEICHERREISEN` (Vorgabe leer). Ist die Liste leer, laufen `veroeffentlichen.sh`, `deploy.sh`, `freischalten.sh` und der Workflow wie vor dieser Stufe; ein Test belegt es (AC-12). Grund: Die Skripte bauen und veröffentlichen alle Reisen einer Instanz; ein Fehler hier hält alle Seiten an (Risk Level HIGH).
2. **Materialisiert wird außerhalb des Git-Bauordners:** `<FR_DIENST>/bau/reisen/<reise>`, bei jedem Bau neu. Variante „Export nach `reisen/<reise>` im Bauordner“ verletzt die Prüfung auf ungesicherte Änderungen (`deploy.sh`, `veroeffentlichen.sh`) und lädt zum versehentlichen Committen ein; ein dauerhafter Ordner mit Abgleich wäre eine zweite Wahrheit und wird mit Stufe 4 überflüssig. Der Unterordner `reisen/` ist nötig, weil `bauen.py --reisen <Ordner> <reise>` den Ordner `<Ordner>/<reise>` liest.
3. **Quelle je Reise:** Eine Reise in `FR_SPEICHERREISEN` kommt aus dem Speicher, jede andere aus Git. Es gibt nie beides für dieselbe Reise. Die Git-Kopie einer Speicher-Reise bleibt bis Stufe 5 als Vorgabe liegen und wird weder gebaut noch umgestellt.
4. **Was neu gebaut wird, folgt aus der Stand-Nummer, nicht aus `git diff`.** Eine Speicher-Reise wird gebaut, wenn `reisespeicher.stand_nummer` von der veröffentlichten Nummer (`stand.veroeffentlicht`, aus `daten.json` der Seite) abweicht oder wenn sich der Software-Stand seit dem letzten Bau dieser Reise geändert hat (Stempel `<FR_DIENST>/reise-stand/<reise>.gebaut`, Inhalt `<nummer> <software-kennung>`, nur nach gelungenem Deploy geschrieben).
5. **Software-Kennung** = Stand des Submoduls `frieda/` im Bauordner (`git rev-parse HEAD:frieda`). Ohne Submodul (Tests, Attrappen) der Inhalt von `git rev-parse HEAD`. Die Kennung beschreibt, mit welcher Software eine Reise zuletzt gebaut wurde.
6. **Der Speicher-Teil läuft zuerst und unabhängig vom Netz.** Reihenfolge im Lauf: Sperre, Speicher-Teil, dann der bestehende Git-Teil (`git fetch`, Vorspulen, Prüfungen). Scheitert `git fetch` (kein GitHub), hat der Speicher-Teil schon gebaut. Er braucht weder `git fetch` noch `gh` noch `ls-remote`.
7. **Nur geprüfte Software baut Speicher-Reisen.** Die Tests der Software (`engine/tests`) laufen einmal je Lauf im Git-Teil. Der Speicher-Teil übernimmt eine **neue** Software-Kennung erst, wenn sie die des zuletzt vollständig veröffentlichten Stands ist (Datei `veroeffentlicht`: `git rev-parse <sha>:frieda` gleich der Kennung von HEAD). Bis dahin baut und stellt er **nichts** um und wartet mit einem Hinweis im Protokoll (der Bauordner trägt dann schon die neue, noch ungeprüfte Software in `engine/`; eine Inhaltsänderung mit der alten Software zu bauen ist nicht möglich). Grund: Kein zweiter Testlauf (20 Minuten) und keine Speicher-Reise auf ungeprüfter Software. Folge: Ein Software-Wechsel erreicht die Speicher-Reisen im Lauf nach dem Git-Teil; dafür legt der Git-Teil nach einem geänderten Software-Stand `veroeffentlichen-nochmal` an (vorhandener Nachlauf), der Speicher-Teil läuft dann sofort noch einmal.
8. **Nachziehen für Speicher-Reisen: erst umstellen und bauen, dann ein Vorgang** (wie der Workflow: Tor, dann Commit). Die umgestellte Fassung wird nur in den Speicher geschrieben, wenn der Probebau mit der neuen Software gelingt. Der Probebau kostet rund 0,1 s (Messlauf #347). Schreibt jemand dazwischen (`StandGeaendert`), wird neu materialisiert und umgestellt, höchstens dreimal (wie der Workflow beim Push), nie erzwungen.
9. **Wer die Software in den Bauordner bringt, bleibt der Workflow.** Das Submodul `frieda/` rückt nur durch den Bot-Commit des Workflows vor (inklusive Vorwärts-Prüfung); `submodule update --remote` auf dem Server bleibt verworfen (Spec 161). Neu ist nur, dass der **Server** die Speicher-Reisen auf den Software-Stand des Bauordners umstellt. Das trennt Netz und Betrieb: Ohne GitHub rückt die Software nicht vor, aber Schreiben, Bauen und Veröffentlichen laufen weiter. Wer das Submodul vorrückt, wenn der Workflow mit Stufe 5 entfällt, ist nicht Teil dieser Stufe (offene Annahme O-1).
10. **Stand-Datei `veroeffentlicht` bleibt für Git.** Die instanzweite Datei mit dem Commit-SHA und die Rot-Datei `veroeffentlichen-rot` gelten weiter nur für den Git-Teil. Speicher-Reisen haben je Reise `…lauf.json` und `….gebaut`. Eine rote Speicher-Reise nutzt die vorhandene Rot-Datei mit `art=reise` und `reisen=<liste>` (ein Weg für beide Quellen, `alarm_pruefen` bleibt).
11. **Medien** werden bis Stufe 4 als BLOB mit exportiert (Bau und Vergleich lesen die Fotos aus der Datenbank). Stufe 3 nimmt die Auslagerung nicht vorweg; die Zeit für die große Reise wird gemessen (Abschnitt „Zeitziele“) und ist ein Befund für #349, nicht für diese Stufe.

## Prüfstelle (ADR-0001, zehn Fragen)

| Nr. | Antwort |
|---|---|
| 1 Ontologie statt Sonderfall | Die Skripte und Befehle kennen nur Pfade und Bytes; nichts Reisespezifisches. Alles ist an beiden Beispielreisen durchgespielt: `beispielreise` (Wanderung mit Varianten, Medien, Ida und Karl) und `stadtwochenende` (ohne Wanderung, ohne Medienordner, Tom und Lea). |
| 2 Kein Katalog | Keine Art und kein Merkmal. |
| 3 Keine KI | Feste Programme: Vergleich, Materialisieren und `neu.py nachziehen` sind Regeln. Auch der Server stellt ohne KI um. |
| 4 Die Tür | Der Konnektor ändert sich nicht; `publish_status` zeigt für Speicher-Reisen statt „wartet“ den echten Stand. Keine neue Funktion im Konnektor, daher kein Eintrag in `docs/konnektor.md`. |
| 5 Herkunft | Der Vorgang des Nachziehens trägt Person („Software-Nachziehen“, automatisch), Werkzeug `nachziehen`, Grund (Software-Stand, Meldungen der Umstellung), Zeit und Kennung. |
| 6 Rollen entscheiden | Nachziehen ändert Schlüssel, keine Inhalte und keine Entscheidungen (`neu.py nachziehen`, Docstring); Entscheidungen bleiben unberührt. |
| 7 IDs und Verlauf | Es werden keine IDs vergeben oder gelöscht; der Speicher bleibt nur anhängend. Nachziehen ist ein Vorgang im Verlauf, kein Überschreiben. |
| 8 PWA | Die Seite einer Speicher-Reise wird mit demselben Generator gebaut; der Browser-Rundgang gehört zur Abnahme (AC-9, beide Reisetypen). |
| 9 Claude Code | Keine Reiseinhalte in Claude Code. |
| 10 Dokumentation | Diese Spec, ADR-0009 (Verlauf Stufe 3), `docs/betrieb.md`, `betrieb/einstellungen.beispiel`. |

## Teil 1: Materialisieren und Vergleichslauf

### Verhalten

**`reisespeicher.py materialisieren <reise> <ordner> [--bis N]`**
- Schreibt den Stand der Reise in `<ordner>`. Ein vorhandener Ordner wird **ersetzt** (erst neben an `<ordner>.neu` schreiben, dann umbenennen; nie ein halber Ordner). Dazu ruft es `exportieren` mit einem leeren Zwischenordner auf.
- Liest zuerst `stand_nummer` und exportiert genau diesen Stand (`bis=N`), damit Nummer und Inhalt zusammenpassen, auch wenn dazwischen jemand schreibt. Die Nummer steht in `<ordner>.stand` (eine Zeile, neben dem Ordner, nie darin: `_ordner_lesen` würde sie sonst als Reisedatei einlesen).
- Ausgabe: `stand <N>`. Exit 0; unbekannte Reise 2; Datenbank gesperrt oder nicht lesbar 2.

**`reisespeicher.py vergleichen <reise> <ordner> [--bis N]`**
- Vergleicht den Export der Reise (Stand `N`, ohne Angabe der neueste) mit einem Ordner über Prüfsummen (`_stand(..., "pruefsumme")` gegen `_ordner_lesen`); keine Inhalte werden als Bytes gehalten, nur Summen.
- Ausgabe: eine Zeile je Unterschied, `nur im Speicher: <pfad>`, `nur im Ordner: <pfad>`, `verschieden: <pfad>`, sortiert; am Ende `gleich` oder `<n> Unterschiede`.
- **Exit-Codes:** 0 gleich, 1 mindestens ein Unterschied, 2 Fehler (Reise unbekannt, Ordner fehlt oder ist keiner, Symlink im Ordner, Datenbank gesperrt oder nicht lesbar, falsche Angaben). Anders als bei den übrigen Befehlen des Moduls (dort ist 1 die Hilfe) gibt auch falsche Aufrufangaben hier 2, damit 1 eindeutig „Unterschied“ heißt.
- Byte-gleich heißt wie im ADR: gleiche Pfadmenge und gleiche Bytes. Leere Ordner, Rechte und Zeitstempel zählen nicht, `.git` gehört nicht dazu.

**`betrieb/vergleichslauf.sh [<reise>…]`** (Betrieb, nutzt `vergleichen`)
- Ohne Angabe: jede Reise, die im Speicher steht **und** als `reisen/<reise>` in Git liegt. Für jede: den Dateistand aus Git (`git archive HEAD reisen/<reise>` in einen Wegwerf-Ordner; der Bauordner bleibt unberührt, ungesicherte Änderungen zählen nicht) mit `vergleichen` gegen den Speicher halten, `--bis` auf den Stand, den der Anfangsvorgang übernommen hat, wenn der Aufrufer ihn mit `--bis` nennt (sonst der neueste).
- Schreibt je Reise einen **Stempel** `<FR_DIENST>/vergleich/<reise>.json`: `zeit` (UTC), `ergebnis` (`gleich` | `unterschied` | `fehler`), `stand`, `git` (Commit-SHA), `unterschiede` (Anzahl). Atomar (erst daneben, dann umbenennen). Ein Stempel ist eine Auskunft, keine Sperre (A-3).
- Gesamt-Exit wie `vergleichen`, nach „schlimmstem Ergebnis“: 2 vor 1 vor 0. Ein Fehler bei einer Reise bricht die übrigen nicht ab.
- Läuft von Hand; kein Timer.

**Anfangsvorgang** (Hinweis für Stufe 5, in `docs/betrieb.md` zu beschreiben): `importieren <ordner> <reise> <wer> --grund "vorher in Git" --ab <N>` übernimmt die bisherige Stand-Nummer (ADR-0009, Stufe 3: ein Anfangsvorgang je Reise genügt). Der Befehl besteht seit Stufe 1; hier wird nur geprüft und dokumentiert, welches `--ab` zur Git-Nummer gehört (`importieren` setzt den Stand auf `ab + 1`).

### Acceptance Criteria (Teil 1)

Siehe Abschnitt „Acceptance Criteria“ weiter unten, Teil 1.

## Teil 2: Veröffentlichen aus dem Speicher (gemischter Betrieb)

### Verhalten

**Einstellung im Shell-Teil.** `betrieb/gemeinsam.sh` liest `FR_SPEICHER` (Vorgabe `<FR_SEITEN>/_speicher`, wie `instanz.speicher()`) und `FR_SPEICHERREISEN` (Vorgabe leer), exportiert beide und stellt `ist_speicherreise <reise>` bereit (Leerzeichen um die Namen und leere Teile fallen weg, wie in `instanz.speicherreisen()`). Beide stehen schon in `engine/instanz.py` und `betrieb/einstellungen.beispiel`; neu ist nur das Einlesen im Shell-Teil.

**`veroeffentlichen.sh`, neuer Ablauf** (alles Weitere bleibt, wie es ist):

1. Sperre, Prüfung „Bauordner auf `main` und sauber“ (beides braucht kein Netz), dann **Speicher-Teil**, dann `git fetch` und der Git-Teil. Gilt die Liste als leer, entfällt der Speicher-Teil ganz (kein Aufruf von Python, kein Zugriff auf die Datenbank).
2. **Speicher-Teil** (`speicher_reisen_lauf`): für jede Reise der Liste mit Eintrag im Speicher (`reisespeicher.reisen()`):
   - **Bauen?** ja, wenn `stand_nummer` ≠ `stand.veroeffentlicht(reise)` oder die Software-Kennung ≠ der im Stempel `.gebaut` (und die neue Kennung gilt nach Entscheidung 7 als geprüft) oder `--immer`.
   - Software-Wechsel und rotes Tor: siehe Teil 3. Ohne Software-Wechsel: `materialisieren <reise> <FR_DIENST>/bau/reisen/<reise>`, `reise_stand_schreiben <reise> baut`, `deploy.sh <reise>`.
   - Exit 0: Stempel `.gebaut`, `reise_stand_schreiben veroeffentlicht`, Freischalten der Reise wie bei Git-Reisen. Exit 2 (Bau gescheitert): `fehlgeschlagen` mit Grund, die Reise bleibt auf dem letzten guten Stand und geht in die Rot-Datei (`art=reise`); die anderen laufen weiter. Exit 1 (Infrastruktur): Lauf endet mit 1, der nächste Lauf wiederholt, nichts wird gemerkt.
   - Nichts zu bauen für keine Reise: kein Aufwand außer einer Abfrage je Reise (`stand_nummer`, `daten.json` lesen).
3. **Stempel und Heartbeat.** Der Stempel `veroeffentlichen-erfolg` (und der Heartbeat) wird nur gesetzt, wenn Speicher-Teil **und** Git-Teil fachlich erfolgreich waren (nichts zu tun oder alles veröffentlicht). Kein Ping bei Teil-Erfolg (Readiness statt Liveness, globale Regel). Ein Speicher-Teil mit Erfolg und ein Git-Teil ohne Netz ergibt also keinen Stempel; der Monitor sieht das nach seiner Frist, und das Veröffentlichen der Speicher-Reisen ist trotzdem geschehen.
4. **Ohne Netz:** `git fetch` scheitert (`set -e`), der Lauf endet wie heute mit Fehler. Der Speicher-Teil lief davor und hat Speicher-Reisen veröffentlicht; er hat weder `git`-Netz noch `gh` noch GitHub-API benutzt.
5. **Software-Wechsel im Git-Teil:** Hat das Vorspulen oder Submodul die Software-Kennung geändert, legt der Git-Teil `veroeffentlichen-nochmal` an; der Nachlauf startet den Lauf gleich noch einmal, und der Speicher-Teil stellt jetzt die Speicher-Reisen um und baut sie (Teil 3).

**`deploy.sh <reise>`, Speicher-Reisen:** erkennt sie mit `ist_speicherreise`.
- Entfallen: die Prüfung, dass `reisen/<reise>` existiert, und die Git-Sauberkeitsprüfung für `reisen/<reise>`; die für `engine/` bleibt.
- Bau aus `<FR_DIENST>/bau/reisen/<reise>` (`--reisen <FR_DIENST>/bau/reisen`), Ziel wie bisher `dist/` und `rsync` nach `<FR_SEITEN>/<reise>/`. Rückmeldedienst, Konnektor und Schreibweg werden wie bisher aktualisiert; Exit-Codes unverändert (0, 2 Bau gescheitert, 1 alles andere).
- `SB_MODULE`, `RM_MODULE`, `KN_MODULE` und `PS_MODULE` enthalten `reisespeicher.py` (siehe „Modullisten“).
- Nach dem Bau: der Ordner `<FR_DIENST>/bau/reisen/<reise>` und `.stand` bleiben liegen (Fehlersuche), werden beim nächsten Bau ersetzt.

**`freischalten.sh`:** die Prüfung, dass die Reise existiert, findet `reise.yaml` oder `reise.json` auch im Bau-Ordner (`FR_REISENORDNER`, von `deploy.sh`/`veroeffentlichen.sh` für Speicher-Reisen gesetzt, Vorgabe `<Wurzel>/reisen`).

**Stand für die Seite.** `stand.fuer_seite` liest für eine Speicher-Reise Nummer und Änderungsliste mit dem Stand, den `materialisieren` festhielt (`<ordner>.stand`), nicht mit dem neuesten. Schreibt jemand zwischen Materialisieren und Bau, nennt die Seite die Nummer ihres Inhalts, und der nächste Lauf baut die neuere. Fehlt die Datei (Bau aus einem anderen Ordner, Tests, Probebau), gilt wie bisher der neueste Stand. `stand.py` lädt `reisespeicher` mit einem normalen Import in der Funktion (kein `importlib` mehr); `reisespeicher.verlauf` bekommt dazu den optionalen Parameter `bis`.

**`reise_stand_schreiben`:** Für Speicher-Reisen ist `nummer` die Stand-Nummer aus dem Speicher (nicht `git rev-list`), die Zeit des Sicherns kommt aus `<reise>.gesichert.json` des Schreibwegs, gleiche Zeitziel-Meldung (120 s).

**Modullisten (`betrieb/deploy.sh`).** `stand.py` steht in `RM_MODULE`, `KN_MODULE` und `PS_MODULE` und lädt jetzt `reisespeicher` (der Modullisten-Test folgt auch Importen in Funktionen); deshalb steht `reisespeicher.py` in jeder Liste, die `stand.py` enthält. `SB_MODULE` hat es schon. Der Rückmeldedienst und der Konnektor **lesen** den Speicher nicht selbst (sie lesen weiter `…gesichert.json`, `…lauf.json` und `daten.json`); sie tragen das Modul nur mit, weil `stand.py` es laden kann.

**Modulbindungs-Test.** `engine/tests/test_reisespeicher.py::test_nur_schreibweg_und_stand_binden_den_speicher_ein` (Stufe 2, AC-23) verbietet `reisespeicher.py` in `RM_MODULE`/`KN_MODULE`. Er wird ersetzt durch `test_jede_modulliste_mit_stand_traegt_reisespeicher`: jede Liste in `deploy.sh`, die `stand.py` enthält, enthält `reisespeicher.py`; `konnektor.py` und `rueckmeldungen.py` nennen `reisespeicher` im Quelltext weiterhin nicht (sie gehen über `stand`).

### Acceptance Criteria (Teil 2)

Siehe Abschnitt „Acceptance Criteria“ weiter unten, Teil 2.

## Teil 3: Nachziehen auf dem Server

### Verhalten

**`neu.py nachziehen-speicher <reise> <ordner>`** (Struktur, wie `nachziehen`; keine Reiseinhalte):
1. Materialisiert die Reise nach `<ordner>` (Teil 1) und merkt den Stand `basis`.
2. Ruft `nachziehen(<ordner>)` auf. Meldungen mit „OFFEN“ sperren nicht, sie erscheinen als Warnung in der Ausgabe (wie im Workflow).
3. Hat sich nichts geändert (Ordner gleich Speicher-Stand): Ausgabe `nichts umzustellen`, Exit 0, **kein** Vorgang (idempotent).
4. Sonst Probebau des umgestellten Ordners mit der laufenden Software. Gelingt er nicht: Exit 2, Ausgabe mit Grund, **nichts geschrieben**.
5. Gelingt er: `ordner_als_vorgang(reise, <ordner>, basis, wer="Software-Nachziehen", werkzeug="nachziehen", titel=<Software-Kennung kurz>, grund=<Meldungen der Umstellung>, kennung="nachziehen:<kennung-kurz>:<reise>:<basis>", rolle="")`. Bei `StandGeaendert`: zurück zu Schritt 1, höchstens dreimal, dann Exit 1 (nächster Lauf wiederholt). Bei `VorgangVorhanden` (ein früherer Versuch hat geschrieben): wie Schritt 3.
6. Schreibt `<ordner>.stand` neu (Stand des Vorgangs). Ausgabe: `umgestellt, stand <N>`. Exit 0.

**Einbindung in `veroeffentlichen.sh` (Speicher-Teil).** Hat eine Speicher-Reise eine **andere Software-Kennung** als im Stempel `.gebaut` (oder keinen Stempel: erste Aufnahme in die Liste) und gilt die neue Kennung als geprüft (Entscheidung 7), ruft der Speicher-Teil statt `materialisieren` den Befehl `nachziehen-speicher` auf und baut danach. Exit 2 des Befehls zählt wie ein gescheiterter Bau (Reise rot, bleibt auf dem letzten guten Stand, `…lauf.json` `fehlgeschlagen`, `grund_art` ist der Bau). Gilt die Kennung noch nicht als geprüft, geschieht für Speicher-Reisen nichts (auch keine Inhaltsbauten), bis der Git-Teil die Software vollständig veröffentlicht hat; die Seiten bleiben auf dem letzten guten Stand.

**Zeitgeber (A-1).** Der vorhandene 5-Minuten-Lauf von `veroeffentlichen.sh` ist der Zeitgeber; der Nachlauf nach einem Software-Wechsel sorgt dafür, dass das Nachziehen nicht bis zum nächsten Takt wartet. Keine neue Einheit; `units.py pruefen` bleibt ohne Befund.

**Tor (wie Workflow und Veröffentlichen, #142, #168).** Tests der Software: einmal je Lauf im Git-Teil, rot sperrt (Rot-Datei `art=software`; die Speicher-Teile übernehmen dann die neue Software nicht). Bau der Reise: rot sperrt nur diese Reise. `tests/` des Reisen-Repos: nur Warnung (Git-Teil, unverändert).

**Rot ohne `gh` (A-2).** Rote Speicher-Reisen laufen durch die vorhandene Meldekette: Rot-Datei (`art=reise`), nach `FR_ROT_MELDEN_NACH_MINUTEN` ein Alarm an den Betrieb über `FR_MELDEN`, sofort die Meldung an die Organisator:innen der Reise (`waechter.py rot-melden`). Der Server legt kein Issue an. (Das Issue des Workflows, Label `software-nachziehen`, bleibt für Git-Reisen.)

**Workflow `software-nachziehen.sh` (Git-Seite, bis Stufe 5).** Liest die Liste der Speicher-Reisen aus der Einstellungsdatei des Reisen-Repos (`betrieb/einstellungen.env`) und **überspringt** sie in `umstellen` und `tor`: Sonst stellte der Workflow die veraltete Git-Kopie um (Bot-Commit ohne Wirkung) und verfälschte den Vergleichslauf. Der Bau jeder anderen Reise bleibt. Ist die Liste leer oder fehlt die Datei, ändert sich nichts. `software-nachziehen.yml` bleibt unverändert (die Vorlage wird nur einmal kopiert, #250; der Ablauf kommt mit der Software).

**Netz.** Das Nachziehen der Speicher-Reisen braucht kein Netz (Entscheidung 9). Nur das Vorrücken des Submoduls braucht GitHub und liegt beim Workflow; ein Ausfall von GitHub stoppt das Schreiben und Veröffentlichen nie.

### Acceptance Criteria (Teil 3)

Siehe Abschnitt „Acceptance Criteria“ weiter unten, Teil 3.

## Teil 4: Überwachung

### Verhalten

Dieses Repo liefert **prüfbare Zustände**; der Teil-Check im Monitor der Instanz gehört in deren Infra-Repo (`scripts/monitor.sh`, Teil-Check, kein eigener BetterStack-Monitor).

**`reisespeicher.py zustand [--sicherung-max-stunden H]`** (nur lesen, schnell, ohne `pruefen`):
- Zeilen `name wert`: `reisen <n>`, `sicherung_alter_s <Sekunden|keine>`, `datenbank <vorhanden|fehlt>`.
- Exit 0, wenn die Datenbank fehlt (Instanz ohne Speicher) oder die Sicherung nicht älter als `H` Stunden ist (Vorgabe 36, wie der Stempel `waechter-erfolg`); Exit 1, wenn die Datenbank da ist und keine oder eine zu alte Sicherung; Exit 2 bei Fehler (Datenbank nicht lesbar). Das Alter ist die Änderungszeit von `<Speicher>/sicherung/reisen.db`.

**Prüfbare Zustände für den Monitor** (in `docs/betrieb.md`, Abschnitt Überwachung, beschrieben):
1. Alter der Sicherung: `reisespeicher.py zustand` (Exit 1 = melden). Ergänzt den Stempel `waechter-erfolg`, der auch bei einem Fehler der Konten-Sicherung ausbleibt.
2. Software-Stand der Speicher-Reisen: je Speicher-Reise der Stempel `<FR_DIENST>/reise-stand/<reise>.gebaut` (zweites Feld = Software-Kennung) gegen `git rev-parse HEAD:frieda` im Bauordner. Weicht sie länger als etwa 6 h ab (gleiche Regel wie beim Rückstand gegen `main`, ab dem ersten Sehen), hängt das Nachziehen oder der Bau; dazu meldet die Rot-Datei schon selbst.
3. Rückstand des Submoduls gegen `main` der Software: unverändert wie beschrieben (`.git/modules/frieda/HEAD` gegen `git ls-remote`); er deckt den Workflow ab.
4. Stempel `vergleich/<reise>.json`: nur Auskunft (kein Alarm in Stufe 3).

Der Teil-Check im Monitor der Instanz wird als **eigenes Issue im Infra-Repo der Instanz** angelegt (dort selbst umsetzen, CLAUDE.md „Zusammenarbeit der Instanzen“) und im Issue #348 verlinkt. Der Heartbeat-Pfad ändert sich nicht.

### Acceptance Criteria (Teil 4)

Siehe Abschnitt „Acceptance Criteria“ weiter unten, Teil 4.

## Acceptance Criteria

### Teil 1

Neue Testdatei `engine/tests/test_speicher_stufe3.py` (Python-Ebene, `tmp_path`, Speicher aus den Beispielreisen), wenn nicht anders genannt; alle Tests parametrisiert über `beispielreise` und `stadtwochenende`.

- **AC-1 Materialisieren:** Given eine importierte Beispielreise / When `materialisieren` läuft / Then entspricht der Ordner Byte für Byte `beispiel/reisen/<reise>` (gleiche Pfadmenge, gleiche Bytes, ohne `.git`), `<ordner>.stand` nennt die Stand-Nummer, und ein zweiter Aufruf auf einen vorhandenen Ordner ersetzt ihn, ohne alte Dateien zu behalten (eine zwischendurch gelöschte Datei fehlt).
  - Test: `test_materialisieren_ersetzt_den_ordner_byte_gleich`
- **AC-2 Konsistente Nummer:** Given `materialisieren` hat Stand N exportiert / When danach ein Vorgang N+1 eintrifft / Then bleibt `<ordner>.stand` bei N, und `stand_nummer` meldet N+1.
  - Test: `test_materialisieren_haelt_nummer_und_inhalt_zusammen`
- **AC-3 Vergleich ohne Unterschied:** Given beide Beispielreisen importiert / When `vergleichen <reise> beispiel/reisen/<reise>` läuft / Then Ausgabe `gleich`, Exit 0 (Akzeptanz aus #348).
  - Test: `test_vergleichen_beispielreisen_ohne_unterschied`
- **AC-4 Vergleich mit Unterschieden:** Given eine geänderte, eine gelöschte und eine neue Datei im Ordner / When `vergleichen` läuft / Then je eine Zeile `verschieden`, `nur im Speicher`, `nur im Ordner`, am Ende `3 Unterschiede`, Exit 1.
  - Test: `test_vergleichen_nennt_jeden_unterschied_exit_1`
- **AC-5 Vergleich: Fehler:** Given unbekannte Reise / fehlender Ordner / Symlink im Ordner / gesperrte Datenbank (Schreibsperre einer zweiten Verbindung über die Wartezeit hinaus) / falsche Angaben / When `vergleichen` läuft / Then Exit 2 mit einer Zeile `ERROR: …`, nichts wird geschrieben.
  - Test: `test_vergleichen_fehler_geben_exit_2`
- **AC-6 Vergleich über Prüfsummen:** Given ein Speicher mit einer Reise mit großen Dateien / When `vergleichen` läuft / Then werden keine Inhalte als Bytes gelesen (der Test ersetzt `aktueller_stand` durch eine Falle, die scheitert; der Vergleich nutzt `_stand(..., "pruefsumme")`).
  - Test: `test_vergleichen_liest_keine_inhalte`
- **AC-7 Vergleichslauf mit Stempel:** Given ein Bauordner mit Git-Reise `beispielreise` und dieselbe Reise im Speicher / When `betrieb/vergleichslauf.sh` läuft / Then Exit 0 und `vergleich/beispielreise.json` mit `ergebnis: gleich`, `stand`, `git`, `zeit`; nach einer Änderung im Speicher Exit 1 und `ergebnis: unterschied`; ein Fehler bei der einen Reise (Reise nur im Speicher, ohne Git-Ordner wird übersprungen; kaputter Speicher) bricht die andere nicht ab, Gesamt-Exit 2; der Bauordner bleibt unverändert (`git status` leer).
  - Test: `engine/tests/test_betrieb.py::test_vergleichslauf_schreibt_stempel_und_exit_codes`
- **AC-8 Messung:** Given die erfundene 110-MB-Testreise aus dem Messlauf von #347 (`betrieb/messlauf-schreibweg.py --auffuellen 110`, Ordner bleibt erhalten) / When Materialisieren und Vergleichen auf dem Server der Instanz gemessen werden / Then stehen die Zeiten im Issue #348 und liegen unter den Zielen aus „Zeitziele“. Nachweis, kein automatischer Test; der Kurzlauf des Messskripts bleibt Test (`test_messlauf_skript_gibt_kennzahlen_aus`).
  - Test: Messwerte im Issue; `engine/tests/test_schreiben_speicher.py::test_messlauf_skript_gibt_kennzahlen_aus` bleibt grün

### Teil 2

Shell-Läufe in `engine/tests/test_betrieb.py` mit der Fixture `vf` (echte Git-Repos, Attrappen über `VF_*`), Python-Ebene in `engine/tests/test_speicher_stufe3.py`.

- **AC-9 Eine Testreise vollständig über die Datenbank bis zur Seite (Akzeptanz #348):** Given je ein Bauordner mit `FR_SPEICHERREISEN=<reise>` und die Beispielreise `beispielreise` bzw. `stadtwochenende` nur im Speicher / When ein Schreibvorgang (z. B. eine Frage anlegen, Stufe-2-Weg) den Stand erhöht und `veroeffentlichen.sh` läuft / Then entsteht `<FR_SEITEN>/<reise>/` mit `index.html`, `sw.js`, `manifest.json`, `daten.json` trägt `reise_stand.nummer` = `stand_nummer`, die neue Frage steht in den Daten, `…lauf.json` zeigt `veroeffentlicht`, `publish_status` (`stand.lesen`) meldet „enthalten“. Dasselbe gilt für beide Reisetypen. Der Browser-Rundgang der Prüfstelle (Frage 8) wird auf dem Server der Instanz mit einer Testreise abgenommen (`betrieb/pruefsitzung.py`, nie mit einer echten Reise).
  - Test: `test_veroeffentlichen_baut_speicher_reise_bis_zur_seite` (parametrisiert), Browser-Rundgang als Nachweis im Issue
- **AC-10 Neu gebaut wird nach der Nummer:** Given eine veröffentlichte Speicher-Reise / When kein Vorgang dazukommt / Then baut der Lauf sie nicht (`deploy` wird nicht aufgerufen); When ein Vorgang dazukommt / Then wird genau diese Reise gebaut und keine andere; `git diff` spielt keine Rolle (der Git-Stand bleibt gleich).
  - Test: `test_veroeffentlichen_baut_speicher_reise_nur_bei_neuer_nummer`
- **AC-11 Gemischter Betrieb:** Given eine Git-Reise A und eine Speicher-Reise B in einer Instanz / When ein Inhalt von A (Commit auf `main`) und einer von B (Vorgang) kommen / Then werden beide gebaut, die Stand-Datei `veroeffentlicht` trägt den Commit-SHA wie bisher, B hat ihre Nummer in `…lauf.json`, A bleibt bei der Git-Nummer; scheitert der Bau von A (Exit 2), wird B trotzdem veröffentlicht und umgekehrt (Rot-Datei `art=reise`, `reisen=` nennt die rote); ein Software-Wechsel baut alle Reisen beider Quellen.
  - Test: `test_gemischter_betrieb_baut_beide_quellen_unabhaengig`
- **AC-12 Ohne Einstellung ändert sich nichts:** Given `FR_SPEICHERREISEN` leer oder nicht gesetzt / When `veroeffentlichen.sh`, `deploy.sh` und `freischalten.sh` laufen / Then rufen sie weder `reisespeicher.py` noch `python` für den Speicher auf (Attrappe `FR_PYTHON` protokolliert), die Ausgaben, Stempel und Dateien sind die der bisherigen Tests; alle bestehenden Tests in `test_betrieb.py` bleiben ohne geänderte Erwartung grün.
  - Test: `test_ohne_speicherreisen_bleibt_alles_wie_vorher` und bestehende Tests
- **AC-13 Ohne GitHub (Akzeptanz #348):** Given eine Speicher-Reise, ein Bauordner, dessen `origin` nicht erreichbar ist (Pfad existiert nicht), ein `gh`-Stub im `PATH`, der eine Marke schreibt und scheitert, `VF_LSREMOTE` scheiternd / When ein Schreibvorgang kommt und `veroeffentlichen.sh` läuft / Then ist die Seite der Speicher-Reise gebaut und veröffentlicht, die Marke fehlt (kein `gh` im Speicher-Teil), der Lauf endet wie bisher mit Fehler wegen `git fetch` und setzt weder `veroeffentlichen-erfolg` noch den Heartbeat. Ein Schreibvorgang über den Dienst ohne Netz gelingt (Stufe 2, `engine/tests/test_schreiben_speicher.py`, kein git).
  - Test: `test_speicher_reise_wird_ohne_github_veroeffentlicht`
- **AC-14 Speicher-Teil vor dem Netz:** Given `git fetch` hängt oder scheitert / When der Lauf startet / Then ist der Speicher-Teil vor dem ersten `git fetch` gelaufen (Reihenfolge im Protokoll).
  - Test: `test_speicher_teil_laeuft_vor_git_fetch`
- **AC-15 Ein Fehler hält nicht alle an:** Given eine Speicher-Reise, deren Bau scheitert (Exit 2) / When der Lauf endet / Then steht die Reise in der Rot-Datei, die Seite bleibt auf dem letzten guten Stand, `…lauf.json` zeigt `fehlgeschlagen` mit Grund, kein Stempel und kein Heartbeat; Given eine Infrastruktur-Störung (`deploy` Exit 1) / Then Exit 1 des Laufs, nichts gemerkt, der nächste Lauf wiederholt.
  - Test: `test_speicher_reise_rot_haelt_die_anderen_nicht_auf`
- **AC-16 Stand-Nummer der Seite gehört zum Inhalt:** Given `materialisieren` hat Stand N festgehalten / When vor dem Bau ein Vorgang N+1 eintrifft / Then trägt die gebaute Seite `reise_stand.nummer` = N und die Änderungsliste endet bei N; der nächste Lauf baut N+1.
  - Test: `test_seite_nennt_die_nummer_des_gebauten_inhalts`
- **AC-17 Freischalten findet die Reise:** Given eine Speicher-Reise ohne `reisen/<reise>` in Git / When `freischalten.sh` läuft / Then findet es `reise.yaml` im Bau-Ordner und schaltet frei wie bei Git-Reisen.
  - Test: `engine/tests/test_betrieb.py::test_freischalten_findet_speicher_reise` (Attrappen wie in den bestehenden Freischalten-Tests)
- **AC-18 Die Liste lesen Shell und Python gleich:** Given `FR_SPEICHERREISEN=" a , ,b ,"` / When `ist_speicherreise` und `instanz.speicherreisen()` fragen / Then liefern beide `a` und `b`, sonst nichts.
  - Test: `test_speicherreisen_shell_und_python_stimmen_ueberein`
- **AC-19 Modullisten:** Given `deploy.sh` / When die Listen gegen die Importe geprüft werden / Then enthält jede Liste, die `stand.py` trägt, `reisespeicher.py`; der bestehende Test der Modullisten (`test_betrieb.py`) bleibt grün; `test_reisespeicher.py::test_jede_modulliste_mit_stand_traegt_reisespeicher` ersetzt den Stufe-2-Test.
  - Test: `engine/tests/test_reisespeicher.py::test_jede_modulliste_mit_stand_traegt_reisespeicher` und `engine/tests/test_betrieb.py` (Modullisten)

### Teil 3

- **AC-20 Umstellen in einem Vorgang:** Given eine Speicher-Reise, die noch das alte Format trägt (Beispielreise mit entferntem `sprache:` in `reise.yaml` und `typ:` statt `art:` an einer Unterkunft; Städtewochenende mit entferntem `sprache:`) / When `neu.py nachziehen-speicher <reise> <ordner>` läuft / Then entsteht **genau ein** Vorgang (Person „Software-Nachziehen“, Werkzeug `nachziehen`, Grund mit den Meldungen, Kennung), die Stand-Nummer steigt um 1, und der Export des neuen Stands entspricht dem Ergebnis von `neu.py nachziehen` auf einer Kopie des Ordners.
  - Test: `engine/tests/test_speicher_stufe3.py::test_nachziehen_speicher_schreibt_einen_vorgang`
- **AC-21 Idempotent:** Given eine bereits umgestellte Reise / When der Befehl erneut läuft / Then `nichts umzustellen`, Exit 0, kein Vorgang, Nummer gleich; derselbe Lauf zweimal hintereinander (auch mit gleicher Kennung) trägt nie doppelt ein.
  - Test: `test_nachziehen_speicher_ist_idempotent`
- **AC-22 Probebau vor dem Eintragen:** Given eine Umstellung, nach der der Bau scheitert (eine Reise, die die neue Software nicht baut; im Test durch eine Attrappe des Probebaus erzwungen) / When der Befehl läuft / Then Exit 2, keine Zeile im Speicher, Stand unverändert.
  - Test: `test_nachziehen_speicher_schreibt_nichts_bei_rotem_bau`
- **AC-23 Wettlauf mit dem Schreibweg:** Given zwischen Materialisieren und Eintragen schreibt der Schreibweg einen Vorgang / When der Befehl einträgt / Then `StandGeaendert`, neu materialisiert und umgestellt (kein Verlust der Schreib-Änderung), höchstens dreimal; nach drei Fehlschlägen Exit 1 und kein Vorgang des Nachziehens.
  - Test: `test_nachziehen_speicher_wiederholt_bei_wettlauf_hoechstens_dreimal`
- **AC-24 Ohne Daten kein Vorgang:** Given eine Reise in der Liste ohne Eintrag im Speicher oder mit leerem Stand / When der Speicher-Teil läuft / Then wird sie übersprungen (Hinweis im Protokoll), kein Fehler, kein Aufruf des Befehls.
  - Test: `engine/tests/test_betrieb.py::test_speicher_teil_uebergeht_reise_ohne_eintrag`
- **AC-25 Server stellt beim Software-Wechsel um:** Given ein Bauordner mit Speicher-Reise (alte Software-Kennung im Stempel `.gebaut`) und ein Software-Wechsel (Submodul auf neuen Stand, Tests der Software grün per `VF_PRUEFEN`) / When `veroeffentlichen.sh` (mit Nachlauf) läuft / Then ruft der Speicher-Teil `nachziehen-speicher` auf, baut danach und setzt den neuen Stempel; ohne Software-Wechsel ruft er den Befehl nicht auf (Attrappe protokolliert).
  - Test: `engine/tests/test_betrieb.py::test_software_wechsel_stellt_speicher_reisen_auf_dem_server_um`
- **AC-26 Ungeprüfte Software wird nicht übernommen:** Given ein Software-Wechsel mit rotem Tor (`VF_PRUEFEN` scheitert) / When der Lauf endet / Then bleibt der Stempel `.gebaut` der Speicher-Reisen bei der alten Kennung, der Befehl wird nicht aufgerufen, der Speicher-Teil baut nichts (auch keine Inhaltsänderung; Hinweis im Protokoll), und die Rot-Datei meldet `art=software`.
  - Test: `test_rotes_software_tor_haelt_speicher_reisen_auf_altem_stand`
- **AC-27 Rot ohne `gh`:** Given eine Speicher-Reise, die nach dem Software-Wechsel nicht baut / When der Lauf endet / Then steht die Reise in der Rot-Datei (`art=reise`), `alarm_pruefen` meldet nach der Schwelle über `FR_MELDEN` und ruft `rot-melden` (`VF_ROTMELDEN`), und ein `gh`-Stub im `PATH` wird nie gerufen.
  - Test: `test_speicher_rot_meldet_ohne_gh`
- **AC-28 Workflow überspringt Speicher-Reisen:** Given ein Reisen-Repo mit Git-Reise A und Speicher-Reise B (Liste in `betrieb/einstellungen.env`) und ein alter Stand / When `software-nachziehen.sh` läuft / Then wird nur A umgestellt (kein Bot-Commit in `reisen/B`) und geprüft; mit leerer Liste ändert sich das Verhalten nicht (bestehende Tests grün).
  - Test: `engine/tests/test_software_nachziehen.py::test_speicher_reisen_werden_im_workflow_uebersprungen` und bestehende Tests
- **AC-29 Keine neue Einheit:** Given die Vorlagen unter `betrieb/vorlagen/` / When `units.py pruefen` und der Test der Vorlagen laufen / Then gibt es keine neue `.service` oder `.timer`, und `ERLAUBT` in `units.py` ist unverändert.
  - Test: `engine/tests/test_units.py` (bestehend) und `test_keine_neue_einheit_fuer_stufe3`
- **AC-30 Kein Handschritt (#250):** Given eine Instanz mit Speicher-Reise und ein neuer Software-Stand, der eine Umstellung verlangt / When der Stand im Bauordner ankommt / Then stellen die Läufe die Reise um, ohne dass jemand `neu.py` aufruft; die Dokumentation (`docs/betrieb.md`) nennt keinen Handschritt nach einem Software-Wechsel.
  - Test: `test_software_wechsel_braucht_keinen_handschritt` (Teil von AC-25 mit Ergebnisprüfung der Daten) und `test_doku_nennt_keinen_handschritt_nach_software_wechsel`

### Teil 4

- **AC-31 Zustand der Sicherung:** Given kein Speicher / eine frische Sicherung / eine Sicherung älter als die Frist / eine Datenbank ohne Sicherung / eine nicht lesbare Datenbank / When `zustand` läuft / Then Exit 0 / 0 / 1 / 1 / 2, die Zeilen nennen Alter und Zahl der Reisen, und der Befehl schreibt nichts (Änderungszeit der Datenbank und der Sicherung unverändert).
  - Test: `engine/tests/test_speicher_stufe3.py::test_zustand_meldet_alter_der_sicherung_und_schreibt_nichts`
- **AC-32 Stempel `.gebaut`:** Given ein gelungener Deploy einer Speicher-Reise / When der Lauf endet / Then enthält `…gebaut` `<nummer> <kennung>`; nach einem gescheiterten Bau bleibt er unverändert.
  - Test: `engine/tests/test_betrieb.py::test_stempel_gebaut_nur_nach_gelungenem_deploy`
- **AC-33 Dokumentation und Issue:** Given die Änderung / When `docs/betrieb.md` gelesen wird / Then beschreibt der Abschnitt Überwachung die vier Zustände mit Befehl und Schwelle; im Infra-Repo der Instanz liegt das Issue für den Teil-Check und ist in #348 verlinkt (Nachweis, kein Test).
  - Test: `engine/tests/test_speicher_stufe3.py::test_doku_beschreibt_die_pruefbaren_zustaende`; Verweis auf das Issue als Nachweis

## Prüfpunkt: Rückholung aus dem Off-Site-Archiv (Rest #347, kein Code)

Voraussetzung: der Speicherordner existiert auf dem Server der Instanz, und ein Backup mit ihm ist gelaufen. Prüfen und im Issue #348 festhalten:

1. Aus dem Off-Site-Archiv die Datei `sicherung/reisen.db` (und `konten.db`) in einen **Wegwerf-Ordner** zurückholen, nie über die laufende Datenbank.
2. Als `reisen.db` einsetzen, `reisespeicher.py pruefen` muss `ok` melden.
3. Von jeder Reise der Sicherung mit `exportieren` ausgeben und mit dem erwarteten Stand vergleichen; für Beispielreisen mit `vergleichen` (Exit 0). Zahl der Vorgänge und Verlauf gleich lang wie am Original.
4. Alter der Sicherung im Archiv ≤ 36 h (passt zur Frist von `zustand`).

Erledigt, wenn die Schritte mit Datum und Ergebnis (ohne Pfade der Instanz) im Issue stehen; erst danach schließt der Rest von #347. Kommt vor dem Umschalten der ersten echten Reise (Stufe 5).

## Fehler- und Randfälle

| Fall | Verhalten |
|---|---|
| Netz weg (GitHub, `git fetch`, `ls-remote`, `gh`) | Speicher-Teil läuft vorher und ohne Netz (AC-13, AC-14); der Git-Teil endet mit Fehler wie heute; kein Stempel, kein Heartbeat bei Teil-Erfolg |
| Datenbank gesperrt (länger als die Wartezeit) | `materialisieren`/`vergleichen`/`zustand` Exit 2; im Speicher-Teil Infrastruktur-Störung (Exit 1 des Laufs, nichts gemerkt, der nächste Lauf wiederholt); der Schreibweg antwortet 503 wie in Stufe 2 |
| Datenbank fehlt, Liste leer | Speicher-Teil entfällt; `zustand` Exit 0 |
| Reise in der Liste ohne Eintrag oder leer | übersprungen mit Hinweis, kein Aufruf von `deploy.sh`, kein Fehler (AC-24) |
| Leere Reise (Vorgang ohne Dateien kann es nicht geben; nur Tombstones) | Export leer, Bau scheitert wie eine Reise ohne `reise.json` (Exit 2): rot, bleibt auf dem letzten guten Stand |
| Gemischter Betrieb | Quelle je Reise; Stand-Datei und Rot-Datei gemeinsam, aber getrennte Bauergebnisse; Git-Kopie einer Speicher-Reise wird nicht gebaut (AC-11) |
| Vorgang zwischen Materialisieren und Bau | Seite trägt die Nummer ihres Inhalts, der nächste Lauf baut neu (AC-16) |
| Reise ohne Pläne (Status Idee, `plan/routen.yaml` fehlt; `nachziehen` kennt den Fall) | Vergleich, Materialisieren und `nachziehen-speicher` laufen ohne Fehler; Test mit einer erfundenen Reise im Status Idee neben den Beispielreisen |
| Wanderung (`beispielreise`) und Wochenende (`stadtwochenende`) | beide durch AC-1 bis AC-3, AC-9, AC-11, AC-20 und AC-21 geprüft; `stadtwochenende` hat keinen Medienordner, `beispielreise` Medien (Icon, GPX) |
| Vergleichslauf: Exit-Codes | 0 gleich, 1 Unterschied, 2 Fehler; gesamt „schlimmstes Ergebnis“ (2 vor 1 vor 0) |
| Vergleichslauf: Reise nur im Speicher oder nur in Git | wird übersprungen (nichts zu vergleichen), Hinweis in der Ausgabe, kein Fehler |
| Zwei Läufe gleichzeitig | Sperre `veroeffentlichen.lock` wie bisher, der zweite merkt `veroeffentlichen-nochmal` |
| Ungesicherte Änderung in `engine/` | `deploy.sh` bricht ab (Exit 1) wie bisher, auch für Speicher-Reisen |
| Symlink oder Sonderdatei in einer Reise | `_ordner_lesen`/Import brechen ab (bestehend); `vergleichen` Exit 2 |

## Zeitziele

Bezugsgröße ist die erfundene Testreise `gross-erfunden` mit 110 MB Zufallsfotos (`betrieb/messlauf-schreibweg.py --auffuellen 110`); die größte echte Reise hat rund 105 MB. Bekannte Werte aus #347 nach dem Tempo-Umbau: Schreibvorgang auf dieser Reise im Mittel 2,2 s, Maximum 4,2 s; Probebau rund 0,1 s.

Die folgenden Zielwerte sind **meine Annahme**, nicht gemessen (O-2); die Messung in Phase 5 ersetzt sie durch Werte, und der Product Owner bestätigt die Ziele:

| Vorgang | Ziel |
|---|---|
| `materialisieren` einer 110-MB-Reise | unter 5 s |
| `vergleichen` einer 110-MB-Reise (Prüfsummen, Ordner gegen Datenbank) | unter 10 s |
| Gesamtzeit vom Sichern bis zur Veröffentlichung einer Speicher-Reise (Schreibvorgang bis `veroeffentlicht`) | wie bei Git-Reisen unter 120 s (`ZIEL_SEKUNDEN`, Product Owner, 2.11.2026); darin Materialisieren, Bau und Kopieren |
| Speicher-Teil eines Laufs ohne Neues | wenige Sekunden (Abfrage je Reise) |

Reißt die große Reise das Ziel wegen der Fotos in der Datenbank, ist das ein Befund für Stufe 4 (#349) und kein Fehler dieser Stufe (Entscheidung 11); er wird dort als Kommentar festgehalten.

## Dateien

| Datei | Änderung | Beschreibung |
|---|---|---|
| `engine/reisespeicher.py` | MODIFY | `materialisieren`, `vergleichen`, `zustand`, `verlauf(bis=)`, Unterbefehle in `main`, Docstring |
| `engine/neu.py` | MODIFY | `nachziehen-speicher` (Funktion und Unterbefehl, Struktur) |
| `engine/stand.py` | MODIFY | normaler Import, Stand aus `<ordner>.stand`; Hinweis „mit Stufe 3“ entfernt |
| `betrieb/veroeffentlichen.sh` | MODIFY | Speicher-Teil vor `git fetch`, Quelle je Reise, `reise_stand_schreiben` je Quelle, Nachlauf bei Software-Wechsel, Stempel `.gebaut` |
| `betrieb/deploy.sh` | MODIFY | Speicher-Modus (Bau aus `<FR_DIENST>/bau/reisen`), `reisespeicher.py` in `RM_MODULE`, `KN_MODULE`, `PS_MODULE` |
| `betrieb/gemeinsam.sh` | MODIFY | `FR_SPEICHER`, `FR_SPEICHERREISEN`, `ist_speicherreise` |
| `betrieb/freischalten.sh` | MODIFY | Reise auch im Bau-Ordner finden |
| `betrieb/vergleichslauf.sh` | CREATE | Vergleichslauf mit Stempel |
| `betrieb/software-nachziehen.sh` | MODIFY | Speicher-Reisen überspringen |
| `betrieb/einstellungen.beispiel` | MODIFY | Hinweis „bis Stufe 3 baut das Veröffentlichen nicht aus dem Speicher“ ersetzen; Vergleichslauf, Zustand |
| `docs/betrieb.md` | MODIFY | Speicherweg/Grenzen (Z. 90), Veröffentlichen, Software nachziehen, Überwachung, Sicherung/Rückholung, Anfangsimport |
| `docs/adr/0009-reisespeicher.md` | MODIFY | Verlauf Stufe 3 |
| `docs/specs/betrieb/schreibweg-speicher-347.md` | MODIFY | Verweis, dass „bis Stufe 3 wartet“ mit dieser Stufe entfällt (Changelog) |
| `engine/tests/test_speicher_stufe3.py` | CREATE | Tests der Python-Ebene |
| `engine/tests/test_betrieb.py` | MODIFY | Shell-Läufe mit `vf`, Modullisten |
| `engine/tests/test_reisespeicher.py` | MODIFY | Modulbindungs-Test ersetzt |
| `engine/tests/test_software_nachziehen.py` | MODIFY | Speicher-Reisen im Workflow |
| `engine/tests/test_texte.py` | MODIFY | falls neue sichtbare Texte (siehe unten) |

Die Modulliste in `betrieb/deploy.sh` und der Test dazu gehören zur Änderung, nicht zur Nacharbeit (CLAUDE.md).

**Texte.** Die Ausgaben der Skripte und Befehle für den Betreiber stehen wie in allen Skripten in `betrieb/` und in den Befehlen im Quelltext (englische Meldungen der Betriebsskripte, Fehlerzeilen `ERROR: …`); es gibt keinen neuen sichtbaren Text für Personen. Entsteht doch einer (etwa die Meldung an die Organisator:innen bei roter Speicher-Reise), gehört er nach `texte_<sprache>.py` in alle Sprachen; die Ausnahmelisten in `test_texte.py` dürfen nicht länger werden. Die bestehende Meldung `waechter.py rot-melden` wird wiederverwendet.

## Risiken und offene Annahmen

- **Kritischer Pfad (HIGH).** Veröffentlichen und Software-Wechsel laufen für alle Reisen über diese Skripte. Gegenmittel: Schalter je Reise, leere Liste ändert nichts (AC-12), Speicher-Teil getrennt vom Git-Teil, Tests mit echten Git-Repos und Attrappen. **Vor dem Vorspulen auf `main`** laufen die Tests der einbindenden Instanzen mit dem Branch (CLAUDE.md; Anleitung im Reisen-Repo der Instanz), weil Meldungstexte, Umgebungswerte (`FR_SPEICHER`, `FR_SPEICHERREISEN`, `FR_REISENORDNER`) und Skriptabläufe betroffen sind.
- **O-1 (offen): Wer rückt das Submodul vor, wenn der Workflow entfällt?** Nicht Teil dieser Stufe. Bis Stufe 5 bleibt der Workflow die einzige Quelle neuer Software-Stände. Der Issue-Text sagt „Software nachziehen läuft auf dem Server … nicht mehr als GitHub-Workflow“: Diese Spec setzt das für die **Umstellung der Speicher-Reisen** um, nicht für das Vorrücken des Submoduls (das ist ein Commit im Reisen-Repo und braucht Schreibrechte auf GitHub). Das ist eine Abweichung vom Wortlaut des Issues; der Product Owner sollte sie bestätigen oder Stufe 5 entsprechend zuschneiden.
- **O-2 (offen): Zielwerte der Zeiten** (Abschnitt „Zeitziele“) sind meine Annahme, bis gemessen.
- **O-3 (offen): Weitere Leser von `reisen/<reise>` im Bauordner.** Eine Suche im Code (`grep` nach `"reisen"` in `engine/` und `betrieb/`) fand außer den Skripten dieser Spec nur `schreiben.py` (Stufe 2, über den Speicher) und `bauen.py` (Argument). Nicht geprüft habe ich Dinge im Reisen-Repo der Instanz (`tests/`, eigene Skripte). Vor dem Umschalten einer echten Reise zu inventarisieren (Stufe 5); Tests des Reisen-Repos sind nur eine Warnung.
- **O-4 (offen): Wer prüft den Stand `ab` beim Anfangsvorgang?** `importieren --ab N` setzt den Stand auf `N + 1`; ob die Git-Nummer `n` zum Aufruf `--ab n-1` führt (Stand = n), ist hier nicht entschieden. Ein Test in Teil 1 klärt es, bevor es in der Doku steht.
- **Software-Kennung ohne Submodul** (Tests, Attrappen): Ersatz `git rev-parse HEAD`. Folge: Jeder Commit gilt in Tests als Software-Wechsel für Speicher-Reisen; im Betrieb mit Submodul tritt das nicht auf. Mit dem Umbau der Tests der Fixture `vf` (echtes Submodul) abzusichern.
- **Rot-Datei teilen:** Eine rote Speicher-Reise und ein roter Git-Commit teilen die Rot-Datei (ein Stand). Der Git-Teil überschreibt `reisen=` mit seiner Liste; bei gleichzeitigem Rot beider Quellen muss `reisen=` die Vereinigung nennen (Test in AC-11 deckt den Fall mit ab, sonst Nacharbeit in `rot_schreiben`).
- **Reihenfolge mit Stufe 4 (#349):** Fotos als BLOB machen Materialisieren und Vergleich langsam; die Messung entscheidet, ob Stufe 4 vor dem Umschalten nötig ist.
- **Dateirechte:** Die Datenbank hat Modus 600; Benutzer des Laufs `veroeffentlichen`, des Schreibwegs und des Wächters müssen dieselbe Datei öffnen können (gleicher Dienstbenutzer in den Vorlagen, wie in Stufe 2). Falsche Rechte zeigen sich als Exit 2 von `materialisieren`.
- **Keine KI auf dem Server, keine Instanzspezifika:** Pfade, Benutzer und Adressen kommen aus den Einstellungen; Beispiele und Tests nutzen nur die beiden Beispielreisen und erfundene Testdaten.

## Test Plan

### Automated Tests (TDD RED)

- [ ] Test 1: GIVEN beide Beispielreisen im Speicher WHEN materialisiert und verglichen wird THEN Byte-gleich, Vergleich `gleich` Exit 0; Änderungen, Löschungen und neue Dateien ergeben Exit 1; Fehler Exit 2 (AC-1 bis AC-6).
- [ ] Test 2: GIVEN ein Bauordner mit Attrappen WHEN der Vergleichslauf läuft THEN Stempel und Exit-Codes (AC-7).
- [ ] Test 3: GIVEN `vf`-Fixture mit Speicher-Reise WHEN veröffentlicht wird THEN Seite, Nummer, Rot-Weg, gemischter Betrieb, ohne Netz, vor `git fetch` (AC-9 bis AC-16).
- [ ] Test 4: GIVEN eine Reise im alten Format WHEN `nachziehen-speicher` läuft THEN ein Vorgang, idempotent, nichts bei rotem Bau, Wiederholung bei Wettlauf (AC-20 bis AC-23).
- [ ] Test 5: GIVEN ein Software-Wechsel WHEN der Lauf (mit Nachlauf) endet THEN Speicher-Reisen umgestellt und gebaut, bei rotem Tor nicht, rot ohne `gh` (AC-25 bis AC-27).
- [ ] Test 6: GIVEN `zustand` WHEN Sicherung fehlt, alt oder frisch ist THEN Exit 0/1/2 und kein Schreiben (AC-31).
- [ ] Test 7: GIVEN die Modullisten WHEN gegen die Importe geprüft THEN `reisespeicher.py` in jeder Liste mit `stand.py` (AC-19).

Die Tests sind den Acceptance Criteria oben zugeordnet; RED vor dem Bauen (`40-tdd-red`).

## Definition of Done

- [ ] Jede Acceptance Criterion ist durch einen automatischen Test belegt (Ausnahmen mit Nachweis im Issue: AC-8 Messung, Browser-Rundgang in AC-9, Issue im Infra-Repo in AC-33, Prüfpunkt Rückholung)
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests -n auto` grün, ohne echte Reisen, mit beiden Beispielreisen
- [ ] Tests der einbindenden Instanzen mit dem Branch laufen vor dem Vorspulen
- [ ] Doku (`docs/betrieb.md`, `betrieb/einstellungen.beispiel`, ADR-0009) aktuell; Modulliste in `deploy.sh` ergänzt
- [ ] Keine echte Reise umgeschaltet; kein Handschritt nach dem Software-Wechsel
- [ ] Annahmen A-1 bis A-3 bestätigt (oder geändert und die Spec nachgezogen)
- [ ] Messwerte (110-MB-Testreise) und Rückholung aus dem Off-Site-Archiv stehen im Issue #348; erst dann Rest von #347 schließen

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** ADR-0009 (`docs/adr/0009-reisespeicher.md`, wird um den Verlauf der Stufe 3 ergänzt; das ADR nennt Stufe 3 bereits: „Veröffentlichen und Nachziehen lesen aus dem Speicher“).
- **Rationale:** Die Entscheidung für den Speicher steht in ADR-0009; Stufe 3 setzt sie für Bau und Umstellung um. Das berührt Grundformen und Merkmale nicht (ADR-0001, Punkt 8), ein neues ADR ist nicht nötig. Die Ablösung des GitHub-Workflows als einziger Weg (O-1) ist eine Frage an den Product Owner, keine Architekturänderung dieser Stufe.

## Known Limitations

- Bis Stufe 5 verdoppelt der gemischte Betrieb die Pfade; die Git-Kopie einer Speicher-Reise bleibt unberührt liegen.
- Das Submodul rückt nur über den Workflow vor (O-1).
- Fotos liegen bis Stufe 4 als BLOB in der Datenbank und verlängern Materialisieren, Vergleich und Bau.
- Der Vergleichslauf wird in Stufe 3 nicht erzwungen (A-3).

## Changelog

- 2026-11-06: Initial spec created
