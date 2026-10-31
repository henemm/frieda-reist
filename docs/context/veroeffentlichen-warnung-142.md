# Context: Veröffentlichen hält bei einer Warnung im Plan einer Reise alles an (#142)

## Request Summary
Eine Inhaltsfrage einer einzelnen Reise (Warnung im Plan) darf das Veröffentlichen nicht anhalten. Der Product Owner hat am 31.10.2026 entschieden, alle sechs Punkte des Issues in einem Zug umzusetzen: Inhalt sperrt nie, eine Reise hält die anderen nicht auf, Schreibweg und Tor prüfen dasselbe (neue Warnungen in der Antwort), kein Wiederholen ohne Änderung, Alarm nach 30 Minuten Rot, Start und Ende des Plans über den Konnektor.

## Ursache (belegt)
- `betrieb/veroeffentlichen.sh:70` lässt vor allen Reisen `pytest engine/tests tests` laufen. `tests/` ist der Testordner des privaten Reisen-Repos. Ist irgendetwas rot, bricht der Lauf ab (Zeile 71), nichts geht online, und der Stand wird nicht gemerkt.
- Die Tests im Reisen-Repo enthalten **Schnappschüsse des Inhalts** der echten Reisen: exakte Warnungslisten (`r["warnungen"] == []`, eine feste Liste zweier Warnungstexte), Tageszahlen, Summen in km und Stunden, Bildanzahlen. Jede Änderung über den Schreibweg kann sie rot machen, auch ohne Warnung. Das Tor prüft also den Inhaltsstand, nicht die Software.
- Der Probebau des Schreibwegs (`engine/schreiben.py:2759 probebau`) lehnt nur bei `bauen.BauFehler` ab, Warnungen lässt er durch. Schreibweg und Tor prüfen also Verschiedenes.
- `veroeffentlichen.sh:61` vergleicht nur mit dem zuletzt **gelungenen** Stand (`<FR_DIENST>/veroeffentlicht`). Ein roter Stand wird deshalb bei jedem Timer-Lauf (alle 5 Minuten, dazu nach jedem Schreibvorgang) neu geprüft: etwa 6 Minuten pytest je Lauf.
- Ein Fehlschlag meldet niemandem etwas, nur der Erfolgsstempel bleibt aus. Der Monitor der Instanz merkt das erst nach etwa 2 h (`docs/betrieb.md`, Überwachung).
- Start und Ende des Plans (`start.ort`, `start.datum`, `ende.ort` in `plan/routen.yaml`) setzt kein Werkzeug. `reise_aendern` (`engine/schreiben.py:2419`) verweist nur darauf.

## Related Files
| File | Relevance |
|------|-----------|
| `betrieb/veroeffentlichen.sh` | Tor: Prüfungen, Schleife über die Reisen, Merken des Stands, Erfolgsstempel und Heartbeat |
| `betrieb/deploy.sh` | Baut eine Reise (`bauen.py`), prüft sonst selbst (ohne `FR_GEPRUEFT`), kopiert erst nach gelungenem Bau nach `<FR_SEITEN>/<reise>` (letzter guter Stand bleibt also bei Baufehler) |
| `betrieb/gemeinsam.sh` | `fr_melden` (Nachricht an den Betreiber über `FR_MELDEN`), gemeinsame Einstellungen |
| `engine/schreiben.py` | `Schreiber.probebau`, `schreiben` (Antwort `{"ok", "text", "commit"}`), `reise_aendern`, `WERKZEUGE`, `AKTIONEN` |
| `engine/konnektor.py` | Werkzeugliste und Beschreibungen (`REISE_AENDERN` um Zeile 2534), Überblick zeigt `r["warnungen"]` unter „Hinweise der Prüfung“ (Zeile 733), Meldungen an Personen |
| `engine/routen.py` | `bauen()` ab Zeile 1148: `start.datum` Pflicht (Fehler), `start.ort` als Ausgangspunkt; Lücken werden mit `warne` gemeldet (Zeile 1125, 923) |
| `engine/bauen.py` | `BauFehler` (Fehler) und `daten()` mit `route.warnungen` |
| `engine/rueckmeldungen.py` | `meldung_anlegen` / `meldungen` (Meldungen an Personen in der Ablage, `meldungen.jsonl`) |
| `engine/waechter.py`, `betrieb/waechter.sh` | Vorbild: Meldungen an Organisator:innen mit `schluessel` gegen Doppelte; Betreiber-Meldung über `fr_melden` |
| `engine/tests/test_betrieb.py` | Fixture `vf` (Attrappen für Deploy, Prüfen, Freischalten, curl), Tests des Veröffentlichens ab Zeile 167 |
| `engine/tests/test_schreiben.py` | Tests des Schreibwegs, auch für `reise_aendern` und Probebau |
| `docs/betrieb.md` | Abschnitte Veröffentlichen und Überwachung |
| `docs/konnektor.md` | Werkzeugtabelle (ein Test gleicht sie mit `WERKZEUGE` ab) |
| Privates Reisen-Repo `tests/test_reisen.py` | Inhalts-Schnappschüsse der echten Reisen (nicht in diesem Repo, nur Konvention vorgeben) |

## Existing Patterns
- Überschreibbare Pfade für Tests in den Betriebsskripten (`VF_PRUEFEN`, `VF_STAND`, `VF_DEPLOY`, `VF_STEMPEL` …).
- Heartbeat und Erfolgsstempel nur bei fachlichem Erfolg (Readiness statt Liveness).
- Meldungen an Organisator:innen über die Ablage mit `schluessel`, damit nichts doppelt kommt (Wächter).
- Verlauf mit Datum, Person und Grund bei Änderungen durch Organisator:innen (`reise_aendern`, `plan_aendern`).
- Ablehnungen des Schreibwegs als `Ablehnung` mit verständlichem Text; der Grund steht im Protokoll.

## Dependencies
- Upstream: `bauen.Bauer(...).daten()` liefert `route.warnungen`. pytest für die Software-Tests. `git` für den Stand.
- Downstream: systemd-Timer und Schreibweg rufen `veroeffentlichen.sh` auf. Der Monitor der Instanz liest den Erfolgsstempel. Der Konnektor gibt die Antwort des Schreibwegs an die Claude-App weiter.

## Existing Specs
- `docs/specs/betrieb/schreibweg-zeitgrenzen.md` (#118–#121, Zeitgrenzen und Sperre je Reise; bereits auf main)

## Risks & Considerations
- **Kein Inhaltsschnappschuss im Tor**, aber die Prüfung der Software muss vollständig bleiben. Ohne die Inhaltsprüfungen fallen Tests des Reisen-Repos weg, die echte Fehler fänden (Betrieb der Instanz, Privates). Eine Trennung per Markierung oder Ordner muss das Reisen-Repo selbst vornehmen; diese Software kann nur die Konvention festlegen.
- Der Bau einer Reise prüft schon den Inhalt (Fehler = Abbruch). Er ist das richtige Tor je Reise.
- „Rot gemerkt“ darf einen Fehlschlag aus vorübergehenden Gründen (Dienst kurz nicht bereit) nicht dauerhaft festhalten: Erneut prüfen, wenn sich `main` bewegt, mit `--immer` oder nach einer Wartezeit?
- Alarm nach 30 Minuten: Wo steht der Zeitpunkt des ersten Rots, und wie wird nicht bei jedem Lauf erneut gemeldet?
- Neue Warnungen im Schreibweg: Ein zweiter Bau des alten Stands kostet Zeit (Zeitgrenzen aus #118). Den Vergleich besser aus einem Bau des Stands vor der Änderung ziehen oder die Warnungen vorher merken.
- Start und Ende: Ableiten aus dem ersten und letzten Tag ändert das Verhalten bestehender Reisen; ein Werkzeug ist expliziter. Beides ist an ADR-0001 zu messen (Grundform Folge).
- Repo ist öffentlich: keine Namen echter Reisen in Code, Tests oder Doku.

## Nebenbefund
#118 bis #121 sind laut Code und Commit 6185d56 bereits umgesetzt (Ablehnungsgrund im Protokoll, Sperre je Reise, Zeitgrenzen, nice/ionice), die Issues sind aber noch offen.

## Analysis

### Type
Bugfix mit Erweiterungen (sechs Punkte des Issues, PO-Entscheidung 31.10.2026: alle in einem Zug). Untersuchung inline durchgeführt (Code gelesen, Probebau gemessen), Ansatz vom Advisor geprüft.

### Zusätzliche Befunde der Analyse
- `bauen.py` als Kommandozeile endet bei Warnungen mit 0, nur `BauFehler` gibt 1 (`engine/bauen.py:1286-1297`). `deploy.sh:28` sperrt also bei Warnungen nicht; die Sperre kam allein aus pytest über `tests/` des Reisen-Repos.
- Der volle Bau (`bauen()` = `daten()` + `schreiben()`) kann nach `daten()` nur noch an der Vorlage scheitern (`bauen.py:1070`, Platzhalter fehlt): das ist Software und von `engine/tests` abgedeckt. Probebau (`daten()`) und Tor (voller Bau) prüfen damit für den Inhalt dasselbe. Restlücke (Dateisystem, Bilder kopieren) ist kein Inhaltsfehler und gilt als Infrastruktur.
- Probebau der Beispielreise: 0,1 s. Ein zweiter Bau vor der Änderung (für „neue Warnungen“) passt in `ZEIT_GESAMT = 25` s (`engine/schreiben.py:58`); große echte Reisen liegen geschätzt bei etwa 1 s.
- Der Konnektor reicht `antwort["text"]` des Schreibwegs durch (`engine/konnektor.py:1170`, `1453`). Ein neues Feld `hinweise` in der Antwort muss dort an beiden Stellen angehängt werden.
- `deploy.sh:30-35` lässt pytest erneut laufen, wenn `FR_GEPRUEFT` nicht passt; muss gleich wie das Tor geändert werden (ein Test prüft die Zeile wörtlich).

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `betrieb/veroeffentlichen.sh` | MODIFY | Nur `engine/tests` sperrt; `tests/` des Reisen-Repos läuft weiter, Rot dort nur Warnung + `fr_melden`. Schleife: gescheiterte Reise hält die anderen nicht auf; Freischalten nur für gelungene Reisen. Roter Stand mit Commit, Art und Zeitpunkt des ersten Rots in `<FR_DIENST>/veroeffentlichen-rot`; bekannter roter Commit wird übersprungen **ohne Stempel und ohne Heartbeat**. Alarm nach 30 Minuten Rot, einmal. |
| `betrieb/deploy.sh` | MODIFY | Eigene Prüfung (pytest) genauso eingeschränkt wie das Tor; Rückgabe unterscheidet Baufehler der Reise (deterministisch) von globalen Fehlern (Dienste nicht bereit), z. B. eigener Exit-Code. |
| `betrieb/gemeinsam.sh` | MODIFY (evtl.) | Gemeinsame Hilfe für den Rot-Zustand, falls nötig |
| `betrieb/melden_rot.py` (Name offen) oder Unterbefehl in `engine/waechter.py` | CREATE/MODIFY | Meldung an die Organisator:innen der betroffenen Reise über `rueckmeldungen.meldung_anlegen` mit `schluessel` (Muster Wächter, `organisator_von`) |
| `engine/schreiben.py` | MODIFY | `probebau` liefert Warnungen; Bau vor der Änderung, Vergleich nach `(bezug, text)`, neue Warnungen als `hinweise` in der Antwort. Neues Werkzeug für Start und Ende des Plans (`start.ort`, `start.datum`, `ende.ort`, `ende.datum`; nur Organisator:innen, mit `grund`, Verlauf). `reise_aendern`-Text verweist auf das neue Werkzeug. |
| `engine/konnektor.py` | MODIFY | Werkzeugdefinition des neuen Werkzeugs; `hinweise` der Schreibweg-Antwort an den Text hängen („eingetragen; Hinweis: …“) |
| `engine/tests/test_betrieb.py` | MODIFY | Fixture `vf`: Fehlschlag je Reise (`kaputt-<reise>`), Deploy-Attrappe mit Exit-Code je Fehlerart, Attrappe für Software- und Instanzprüfung getrennt. Bestehende Tests anpassen: `fehlschlag_wird_wiederholt` (widerspricht Punkt 4), `prueft_einmal_fuer_alle_reisen`, `heartbeat_nur_bei_erfolg`, `stempel_nur_bei_erfolg` (erwarten Erfolg auf demselben Commit). Neue Tests: Warnung sperrt nicht, eine Reise hält andere nicht auf, roter Commit nicht erneut geprüft, Überspringen ohne Stempel/Heartbeat, Alarm einmal nach 30 Minuten, Infrastrukturfehler wird wiederholt. |
| `engine/tests/test_schreiben.py` | MODIFY | Neue Warnung in der Antwort; keine Hinweise ohne neue Warnung; Start/Ende-Werkzeug (Rolle, Grund, Verlauf, Ablehnungen) |
| `docs/betrieb.md` | MODIFY | Abschnitte Veröffentlichen und Überwachung; Konvention für `tests/` des Reisen-Repos (Inhaltsschnappschüsse sperren nicht) |
| `docs/konnektor.md` | MODIFY | Werkzeugtabelle (Test gleicht sie mit `WERKZEUGE` ab) |
| `beispiel/reisen/beispielreise/…` | MODIFY (evtl.) | Nur falls Tests ein Verlauf-Feld für Start/Ende in der Beispielreise brauchen |

### Scope Assessment
- Files: etwa 9–10
- Estimated LoC: +350 / -40 (davon gut die Hälfte Tests)
- Risk Level: MEDIUM — betrifft das Tor jeder Instanz; Fehler dort halten wieder alles an oder lassen Kaputtes durch. Abgesichert durch die Testattrappen des Veröffentlichens.

### Technical Approach
1. **Inhalt sperrt nie (Punkt 1).** Sperrend sind nur `engine/tests` (Software) und ein `BauFehler` einer Reise. `tests/` des Reisen-Repos läuft weiter, bei Rot nur Warnung im Protokoll und `fr_melden normal` an den Betrieb. Das behebt den Vorfall **ohne Änderung am privaten Reisen-Repo**. Empfehlung an das Reisen-Repo (nur Doku): Inhaltsschnappschüsse entfernen oder kennzeichnen.
2. **Eine Reise hält die anderen nicht auf (Punkt 2).** `deploy.sh` unterscheidet: Exit 2 = Bau der Reise gescheitert (deterministisch, nur diese Reise), sonst globaler Fehler (Dienste nicht bereit, Ordner fehlt). Bei Exit 2 laufen die anderen Reisen weiter und werden freigeschaltet; die gescheiterte bleibt auf ihrem letzten guten Stand (`deploy.sh` kopiert erst nach gelungenem Bau). Der Stand `veroeffentlicht` wird gemerkt, wenn alles außer Baufehlern gelang; die roten Reisen stehen in der Rot-Datei.
3. **Schreibweg und Tor prüfen dasselbe (Punkt 3).** Tor für Inhalt = Bau (`BauFehler`), Probebau = `daten()` desselben Baus. Neue Warnungen: Bau vor dem Werkzeug, Bau danach, Differenz nach `(bezug, text)` als `hinweise`; der Konnektor hängt sie an seine Antwort.
4. **Kein Wiederholen ohne Änderung (Punkt 4).** Nur deterministische Fehler (Software-Tests rot, Bau gescheitert) werden mit Commit gemerkt. Gleicher Commit ohne `--immer` → übersprungen, **kein Stempel, kein Heartbeat** (Readiness). Infrastrukturfehler (Dienst nicht bereit, Submodul, Vorspulen) werden wie bisher vom Timer wiederholt.
5. **Alarm (Punkt 5).** Rot-Datei mit Commit, Zeitpunkt des ersten Rots (bleibt über neue rote Commits erhalten) und Merker „gemeldet“. Nach 30 Minuten einmal `fr_melden high` an den Betrieb und eine Meldung an die Organisator:innen der betroffenen Reise(n) (`meldung_anlegen` mit `schluessel`); bei Software-Rot nur an den Betrieb. Wird es grün, wird die Rot-Datei entfernt. Der Stempel bleibt aus, solange Software rot ist; bei nur einer roten Reise bleibt er ebenfalls aus (Teil-Erfolg ist kein fachlicher Erfolg), die anderen Reisen gehen aber online.
6. **Start und Ende im Konnektor (Punkt 6).** Neues Werkzeug (Arbeitsname `start_ende_setzen`) für `start.ort`, `start.datum`, `ende.ort`, `ende.datum` in `plan/routen.yaml`; nur Organisator:innen, Pflicht-`grund`, Verlauf wie `reise_aendern`; Probebau prüft das Ergebnis. Kein Ableiten im Generator (PO: über den Konnektor).

**Prüfstelle ADR-0001 (Kurzfassung, vollständig in der Spec):** Punkt 3 und 6 bleiben in den Grundformen (Folge: Start/Ende des Plans; Warnungen sind Prüfergebnis der Software, keine reisespezifische Logik). Keine KI in Frieda; der Schreibweg prüft nur nach Regeln. Nichts Reise- oder Instanzspezifisches in Engine und `betrieb/` (Schwelle 30 Minuten als Vorgabe, überschreibbar über Umgebung).

### Dependencies
- Upstream: `bauen.Bauer(...).daten()` mit `route.warnungen`; `rueckmeldungen.meldung_anlegen`; `waechter.organisator_von`; `fr_melden`.
- Downstream: Timer und Schreibweg rufen `veroeffentlichen.sh`; Monitor der Instanz liest Stempel und Heartbeat; Konnektor gibt die Antwort des Schreibwegs an die Claude-App.

### Open Questions
- Keine für den PO. Technische Festlegungen (Exit-Code 2, Name der Rot-Datei, Werkzeugname) trifft die Spec.

## Hinweise für die RED-Phase (aus dem Spec-Schreiben, 2026-10-31)

Punkte, die die Spec offen lässt und die vor dem Schreiben der Tests am Code zu prüfen sind:

- Genauer Pfad der Warnungen in `bauen.Bauer(...).daten()`: belegt ist nur `route.warnungen` als Liste von `{bezug, text}` (`engine/routen.py:304 warne`).
- Werte `art` und `ziel` der Meldung an Personen im neuen Unterbefehl `rot-melden` (`engine/waechter.py`) an die bestehenden Meldungen des Wächters angleichen; die Spec nennt sie nur sinngemäß.
- Testnamen `test_werkzeugtabelle_stimmt_mit_dem_konnektor` und `test_werkzeuge_je_rolle` (AC-28, AC-30) gegen die echten Namen in `engine/tests/test_konnektor.py` abgleichen.
- AC-5 braucht eine Reise mit Warnung: Testdaten in `tmp_path` anlegen, die Beispielreise nur im Notfall ergänzen.
- `docs/specs/_template.md` gibt es nicht; Aufbau der Spec folgt `docs/specs/betrieb/schreibweg-zeitgrenzen.md`.
- Nicht Teil von #142: die Issues #118 bis #121 sind laut Kontext umgesetzt, aber noch offen.
