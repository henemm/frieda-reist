# Context: fix-641-meldeweg-ohne-reisen-repo

## Request Summary
Rest von #557 (AC-36): Das private Reisen-Repo der ersten Instanz soll archiviert werden. Vorher braucht der Meldeweg
der Stufe `normal` ein anderes privates Ziel (ohne Handschritt), und die offenen Issues des alten Repos müssen
übertragen oder geschlossen sein.

## Befund (Stand 23.11.2026)
- Die Instanz läuft seit #454/#557 ohne das Reisen-Repo: Units starten aus `<FR_SEITEN>/_software` (Klon dieses Repos),
  Reisen liegen im Reisespeicher, Einstellungen und Meldeweg unter `<FR_DIENST>/instanz/` (vom Server-Backup erfasst,
  nicht versioniert). Der alte Workflow „Software nachziehen“ im Reisen-Repo ist abgeschaltet (#557, L0).
- Einzige laufende Abhängigkeit vom Reisen-Repo: `<FR_DIENST>/instanz/melden.sh` der Instanz legt Meldungen der Stufe
  `normal` als Issue (Label `betrieb-meldung`) in `${FR_MELDEN_REPO:-<Reisen-Repo>}` an; `FR_MELDEN_REPO` ist dort
  nicht gesetzt, also gilt die Vorgabe im Skript.
- `fr_einlesen` (`betrieb/gemeinsam.sh:56`) exportiert jede Zeile `FR_…=wert` aus `<FR_DIENST>/instanz/einstellungen.env`;
  `FR_MELDEN_REPO` dort einzutragen erreicht also `melden.sh` ohne Software-Änderung. Nur Shell ruft `FR_MELDEN`
  (`fr_melden`, `betrieb/gemeinsam.sh:169`), keine Python-Dienste.
- Weitere Nutzungen des Reisen-Repos (nicht Teil des Betriebs, aber Arbeitsort):
  - Arbeitsordner der Instanz-Sitzungen (`henemm-infra/scripts/sitzung-starten.sh`, Eintrag „reisen“), CLAUDE.md der
    Instanz mit Entscheidungen und der Anleitung „Instanz-Tests mit einem Branch der Software“ (veraltet: beschreibt
    das Submodul `frieda/`, die Tests liegen seit #454 unter `<FR_DIENST>/instanz/tests/`).
  - Kopie von `betrieb/melden.sh`, `betrieb/einstellungen.env` und `tests/` (teils abweichend von `<FR_DIENST>/instanz/`).
  - Claude-MQ-Skripte (`ack.sh`, `check-messages*.sh` in henemm-infra/claude-mq) ordnen Ordner `~/<Reisen-Repo>*`
    der Instanz „frieda“ zu.
- Offene Issues im Reisen-Repo: 6 (Instanz-Test rot, Bild-Kennungen im ID-Abgleich, Sicherheitsprüfung 12.11.,
  Kartendienst Balearen, Grunddesign B2, J5 Umstellung auf Konten).

## Related Files
| File | Relevance |
|------|-----------|
| `<FR_DIENST>/instanz/melden.sh` (Instanz, privat) | Ziel der Stufe normal, Vorgabe Reisen-Repo |
| `<FR_DIENST>/instanz/einstellungen.env` (Instanz, privat) | Ort für `FR_MELDEN_REPO` |
| `betrieb/gemeinsam.sh` | `fr_einlesen`, `fr_melden`, Auflösung von `FR_MELDEN` |
| `docs/betrieb.md` (Meldeweg, Abschnitt ~Z. 337) | Vertrag `<befehl> <normal|high> <betreff> <text> [erledigt]` |
| `engine/konten.py:37,903`, `docs/konten.md:187` | Verweis „Issue im privaten Reisen-Repo“ bei `meldung-erledigt` |
| `CLAUDE.md:44,59`, `README.md:47` | nennen Reisen-Repo als Ort der Einstellungen und der Instanz-Test-Anleitung |
| `henemm-infra/scripts/sitzung-starten.sh` | Arbeitsordner der Instanz-Sitzung |
| `henemm-infra/claude-mq/{ack,check-messages,check-messages-hook}.sh` | Ordner → Instanz „frieda“ |

## Existing Patterns
- Instanzwerte nur über `einstellungen.env` der Instanz, nie in der Software (CLAUDE.md, Regeln).
- Meldeweg: Stufe `normal` = Issue, `high` = Telegram nur bei Ausfall (#445/#446).
- Archivieren statt Löschen (bewahrt Verlauf, #557).

## Dependencies
- Upstream: `gh` mit Zugriff des Betriebsbenutzers auf das Zielrepo.
- Downstream: alle `fr_melden normal`-Stellen (Veröffentlichen, Wächter, Instanz-Tests), Instanz-Sitzungen.

## Existing Specs
- `docs/specs/betrieb/` (Betrieb, Meldeweg), #454 Spec (AC-2.10 Meldeweg), #557 Rückbau (AC-36).

## Risks & Considerations
- Archiv ist schreibgeschützt: vor dem Archivieren muss der Meldeweg nachweislich ins neue Ziel schreiben (Probemeldung).
- Neues Ziel muss privat sein (Meldungen können private Reisedaten enthalten).
- Keine Namen, Pfade oder Repo-Namen der Instanz in dieses öffentliche Repo.
- Instanz-Sitzungen brauchen danach einen beschreibbaren Arbeitsort (sonst landet Instanzarbeit im Archiv).

## Analysis

### Type
Feature (Betriebsumstellung, Rest von #557 AC-36); kein Fehlverhalten der Software.

### Entscheidung zum Ziel (Tech Lead, 23.11.2026)
Neues, schlankes privates Repo der Instanz (`<Instanz-Repo>`, auf GitHub privat, Name mit dem Präfix der Instanz,
damit Sitzungs- und MQ-Zuordnung greifen). Es ist **Arbeitsort und Issue-Ziel**, nicht Quelle des Betriebs:
- enthält nur die `CLAUDE.md` der Instanz (aktualisiert: keine Submodul-Anordnung, Verweis auf `<FR_DIENST>/instanz/`,
  Anleitung „Instanz-Tests mit einem Branch der Software“ nach Stand #454/#557) und eine kurze README;
- **keine Kopien** von `melden.sh`, `einstellungen.env`, `tests/`: Die laufende Fassung bleibt allein in
  `<FR_DIENST>/instanz/`, wie in #557 entschieden; doppelte Quellen sind heute schon auseinandergelaufen.

Verworfen: (a) Issues in `henemm-infra` (mischt Projekt- und Infrastruktur-Issues, gegen die globale Regel
„Projekt-Issues im jeweiligen Repo“); (b) altes Repo umbenennen statt archivieren (widerspricht AC-36, trägt
Altlasten wie Reisedateien und Submodul weiter); (c) öffentliches Ziel (private Reisedaten in Meldungen).

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| GitHub: neues privates Instanz-Repo | CREATE | Label `betrieb-meldung`, CLAUDE.md, README |
| `<FR_DIENST>/instanz/einstellungen.env` (Instanz) | MODIFY | `FR_MELDEN_REPO=<Instanz-Repo>` |
| `<FR_DIENST>/instanz/melden.sh` (Instanz) | MODIFY | Vorgabe von `FR_MELDEN_REPO` auf das neue Repo |
| `<FR_DIENST>/instanz/tests/` (Instanz) | MODIFY | Test: Meldeziel ist nicht das alte Reisen-Repo |
| altes Reisen-Repo | TRANSFER + ARCHIVE | 6 offene Issues übertragen oder begründet schließen, danach archivieren |
| `henemm-infra/scripts/sitzung-starten.sh` | MODIFY | Eintrag „reisen“ → Instanz-Repo (Issue in henemm-infra) |
| `henemm-infra/claude-mq/{ack,check-messages,check-messages-hook}.sh` | MODIFY | Ordner des Instanz-Repos → Instanz „frieda“ |
| `CLAUDE.md:44,59`, `README.md:47` | MODIFY | Einstellungen unter `<FR_DIENST>/instanz/`, Anleitung im privaten Repo der Instanz |
| `engine/konten.py:37,903`, `docs/konten.md:187`, `docs/betrieb.md:58` und Abschnitt „Meldeweg“ | MODIFY | „Issue im privaten Repo der Instanz“ |
| `engine/texte_*.py` (`konnektor.ontologie_werkzeug.4`) | MODIFY (prüfen) | sichtbarer Text nennt „Sitzung im Reisen-Repo“; anpassen, falls der Zweig noch erreichbar ist |
| `engine/tests/` | MODIFY | Test: Ist-Doku und Usage nennen das Reisen-Repo nicht mehr als aktuellen Ort (Historie, Specs ausgenommen) |

### Scope Assessment
- Software-Repo: etwa 6–8 Dateien, rund +40/−25 Zeilen (Doku, Usage, Text, ein Test)
- Instanz: 2 Dateien und ein Test; GitHub: ein neues Repo, bis zu 6 Übertragungen, eine Archivierung; henemm-infra: 4 Skripte
- Risk Level: MEDIUM — der Meldeweg ist ein Betriebspfad, Archivieren ist nur von Hand umkehrbar; die Reihenfolge sichert ab.

### Technical Approach (Reihenfolge)
1. Instanz-Repo anlegen (privat), Label `betrieb-meldung`, CLAUDE.md und README.
2. `FR_MELDEN_REPO` in `einstellungen.env` setzen und Vorgabe in `melden.sh` ändern; **Probemeldung** der Stufe
   `normal` über `fr_melden` (wie aus dem Betrieb) → Issue erscheint im neuen Repo → schließen. Instanz-Test dazu.
3. Offene Issues mit `gh issue transfer` übertragen (Kommentare bleiben, alte Verweise leitet GitHub weiter);
   durch #454/#557 überholte (etwa #277 Instanz-Test mit Submodul, #134 J5) vorher prüfen und mit Begründung schließen.
4. henemm-infra: Sitzungsordner und MQ-Zuordnung (eigenes Issue dort).
5. Software-Repo: Doku, Usage und Texte auf den Ist-Zustand, Test gegen Rückfall.
6. Erst wenn 2–5 nachgewiesen sind: altes Repo archivieren, Stand in #641 und #557 vermerken. Lokale Arbeitskopien
   bleiben (nur lesen); ihr Löschen ist nicht Teil dieses Issues.

### Dependencies
- `gh` des Betriebsbenutzers mit Schreibrecht auf das neue Repo (gleicher Besitzer, vorhanden).
- `fr_einlesen` (`betrieb/gemeinsam.sh:56`) exportiert `FR_MELDEN_REPO` aus `einstellungen.env`; am Meldeweg der
  Software ist nichts zu ändern.
- Nur Shell ruft den Meldeweg (`fr_melden`, `fr_alarm`), kein Python-Dienst.

### Open Questions
- Keine Produktfrage. Name des Instanz-Repos und Umgang mit überholten Issues entscheidet Claude (Kriterium: in der
  Sache noch offen → übertragen, sonst mit Begründung schließen).

## Stand nach TDD RED (2026-11-23)

Rückfall-Test `engine/tests/test_meldeweg_ziel_641.py`: 8 rot, 3 grün mit Absicht. Grün sind Test 4 (Ausnahmeliste: jede Fundstelle gibt es noch), Test 5 (`fr_einlesen` reicht `FR_MELDEN_REPO` an `melden.sh` durch, belegt: kein Eingriff in die Software nötig) und Test 6 (`ALARMSTELLEN` unverändert); sie sichern ab, statt Neues zu fordern.

Für GREEN umzuschreiben (Liste aus dem RED-Lauf, `docs/artifacts/fix-641-meldeweg-ohne-reisen-repo/test-red-output.txt`): `CLAUDE.md` (Einstellungen `<FR_DIENST>/instanz/einstellungen.env`, Anleitung der Instanz-Tests im privaten Repo der Instanz), `README.md` Abschnitt „Auf dem eigenen Server“ (Instanz ohne Reisen-Repo, Werte unter `<FR_DIENST>/instanz/`), `docs/betrieb.md` (Zeilen zweite Instanz, Löschen auf dem alten Weg, Meldungen-Tabelle, Export „weder das Reisen-Repo noch“, Meldeweg: `FR_MELDEN_REPO` und „privaten Repo der Instanz“), `docs/design.md`, `docs/konnektor.md`, `docs/konten.md`, `docs/produkt.md`, `docs/werkzeuge.md`, `betrieb/einstellungen.beispiel` (Zeile Impressum umformulieren; `#FR_MELDEN_REPO=<Instanz-Repo>` mit Erklärung beim Meldeweg ergänzen; prüfen, ob `test_betrieb.py` Variablen in der Vorlage verlangt, die kein Skript liest), `betrieb/zustellen.py` (Usage: Wurzel ist der Software-Klon), `engine/konten.py` (Usage und Kommentar), `konnektor.ontologie_werkzeug.4` in allen Sprachen (de und en; der Zweig „Schreibweg nicht eingerichtet“ ist erreichbar, der Satz über die Sitzung entfällt oder nennt den Betreiber). Echte Ausnahmen nur die acht im Test begründeten Fundstellen.
