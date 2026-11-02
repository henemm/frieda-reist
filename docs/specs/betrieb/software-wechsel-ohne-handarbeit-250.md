# Software-Wechsel ohne Handarbeit (#250)

## Anlass

Prüfung am 2.11.2026: Nach #217 hätten vier Reisen der Instanz von Hand mit `neu.py nachziehen` umgestellt werden
müssen, und zwar erst, nachdem die neue Software online ist. Mit der alten Software baut eine umgestellte Reise nicht
(„unknown key ziel“). Der Zeitplan von GitHub startete „Software nachziehen“ nicht alle 30 Minuten, sondern nur alle
paar Stunden (am 1. und 2.11.2026 Abstände von 3 bis 8 Stunden). Und jede Änderung an der Vorlage des Workflows musste
von Hand in jedes Reisen-Repo kopiert werden.

Product Owner (2.11.2026): „Denke Frieda als Produkt. Ich möchte keine Software, die Handarbeit braucht.“

## Lösung

| Handschritt bisher | Künftig |
|---|---|
| `neu.py nachziehen` je Reise, in der richtigen Reihenfolge | Der Lauf „Software nachziehen“ stellt jede Reise um, im selben Commit wie der neue Software-Stand |
| Vorlage des Workflows neu kopieren | Der Workflow ruft nur `frieda/betrieb/software-nachziehen.sh` aus dem neuen Stand auf; der Ablauf kommt mit der Software |
| Auf den Zeitplan von GitHub warten oder von Hand starten | `veroeffentlichen.sh` startet den Workflow, sobald `main` der Software ein anderer Stand ist als das Submodul, einmal je Stand (Wiederholung frühestens nach 6 Stunden) |
| Reste der früheren Vorlage von Hand entfernen | Die Umstellung entfernt sie, wenn sie nur ausgefüllte Kopien der Vorlage sind |

### Ablauf von `betrieb/software-nachziehen.sh` (im Reisen-Repo, auf dem Runner)

1. **Umstellen:** `neu.py nachziehen` für jede Reise mit `reise.json`. Das läuft bei jedem Lauf, auch ohne neuen
   Software-Stand (idempotent). So werden auch Reisen umgestellt, deren Software schon früher nachgezogen wurde. Ein
   offener Punkt („OFFEN …“) sperrt nicht selbst, er erscheint als Warnung; sperren kann nur der Bau.
2. **Nichts geändert** (weder Submodul noch Reisen): Ende, grün, kein Commit.
3. **Tor** wie bisher (#168): `engine/tests` nur bei neuem Software-Stand, der Bau jeder Reise in jedem Lauf mit Änderung; `tests/` des
   Reisen-Repos nur Warnung.
4. **Übernehmen:** ein Commit des Bots mit Submodul und umgestellten Reisen. Erste Zeile „Software auf Stand X
   (automatisch)“ oder, ohne neuen Stand, „Reisen auf den Stand der Software umgestellt (automatisch)“; darunter die
   Liste der Commits und die Meldungen der Umstellung je Reise (Verlauf, ADR-0001 Frage 7).
5. **Wettlauf mit dem Schreibweg:** Scheitert der Push, wird nicht der alte Commit nachgespielt, sondern auf
   `origin/main` zurückgesetzt, das Submodul (sofern ein neuer Stand vorliegt) erneut darauf gesetzt, neu umgestellt,
   neu geprüft und neu committet. Tor und Issue-Regel (Schritt 6) gelten in jedem Versuch. Höchstens drei Versuche, nie
   `--force`. Scheitern alle drei Pushes, endet der Lauf rot ohne Issue (vorübergehend; der nächste Lauf versucht es
   wieder).
6. **Tor rot:** Liegt noch kein offenes Issue mit Label `software-nachziehen` vor, entsteht eins (Titel mit dem
   Software-Stand wie bisher), und der Lauf endet rot (Exit 1, GitHub mailt). Liegt schon eins vor, endet der Lauf mit
   einer Warnung (`::warning::`) und Exit 0, ohne Commit; nennt das offene Issue den aktuellen Software-Stand (`NEU`
   bei neuem Stand, sonst `ALT`, als kurzer SHA) noch nicht
   (weder im Titel noch in einem Kommentar), bekommt es einen Kommentar mit diesem Stand und dem Lauf. Eine Reise, die
   nicht baut, erzeugt so nicht bei jedem Lauf des Zeitplans eine Meldung; das offene Issue ist die Meldung, bis es
   geschlossen ist.

Fehlt `frieda/betrieb/software-nachziehen.sh` im gesetzten Stand (Submodul älter als #250), endet der Lauf rot mit einem
Hinweis im Protokoll, dass die eingebundene Software älter ist als der Workflow.

Bewusste Abgrenzung zu ADR-0006: Texte für den Betreiber (Commit-Zeilen, Issue, Protokoll des Laufs) stehen wie bei
#168 und allen Skripten in `betrieb/` im Skript. Die Meldungen der Umstellung je Reise kommen aus `neu.py` über `texte.t` in der Sprache der Reise.

Dienste: Konnektor und Schreibweg laufen nach dem Commit noch mit dem alten Code, bis der nächste Lauf von
`veroeffentlichen.sh` sie mit `deploy.sh` neu startet (wenige Minuten). Ein Schreibvorgang in diesem Fenster kann mit
einer Prüfmeldung abgelehnt werden und gelingt danach.

### Anstoß vom Server

`veroeffentlichen.sh` fragt bei jedem Lauf `git ls-remote` nach `main` der Software (URL aus `.gitmodules`). Ist dieser
Stand nicht der eingebundene und steht er nicht in der Merkdatei, startet es `gh workflow run
FR_NACHZIEHEN_WORKFLOW` und merkt den Stand in `<FR_DIENST>/nachziehen-angestossen` (Stand und Zeit). Für denselben
Stand startet es erst wieder, wenn seit der gemerkten Zeit `FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN` (Vorgabe 6) vergangen
sind, ohne weitere Bedingung; das fängt einen Lauf ab, der nie startete oder vorübergehend scheiterte. Ein rotes Tor
erzeugt so je Software-Stand eine Fehler-Mail, nicht eine alle 5 Minuten. Scheitert `ls-remote` oder `gh`,
ist das eine Warnung im Protokoll, kein Abbruch des Veröffentlichens.

Präzisierung: Die URL kommt aus `git config -f .gitmodules submodule.frieda.url`, der eingebundene Stand aus
`git rev-parse HEAD:frieda`, beides im Bauordner, in dem `veroeffentlichen.sh` läuft (`$wurzel`), direkt nach
`anstoss_weitergeben` und vor dem Abgleich mit `origin`. Die Merkdatei („SHA Epoche“) wird erst nach Erfolg von `gh` geschrieben. Die Wartezeit
`FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN` ist eine neue Vorgabe in `betrieb/gemeinsam.sh` mit dem Wert 6 (Stunden). Testhaken:
`VF_LSREMOTE`, `VF_JETZT`, `VF_NACHZIEHEN`. Der Zeitplan von GitHub bleibt als Rückfallweg.

### Umstellung vervollständigt (`neu.py nachziehen`)

Muster der früheren Vorlage: `engine/altformen/vorlage-vor-217/<sprache>/` (`CLAUDE.md`, `kontext/herkunft.md`, Stand
`55446c7^`). Eine Datei der Reise gilt als ausgefüllte Kopie, wenn nach Normalisieren (CRLF zu LF, Leerzeilen am Ende
entfernt) die Zeilenzahl gleich ist und jede Zeile vollständig zur Zeile des Musters passt; ein Platzhalter `$wort` steht
für beliebigen Text. Jede Datei wird für sich geprüft. Eine leere Datei passt nie, eine zusätzliche Zeile (etwa ein
Eintrag im Verlauf) macht die Datei zu einer eigenen. Wird `kontext/` durch das Entfernen leer, wird der Ordner mit
entfernt.

- `CLAUDE.md` und `kontext/herkunft.md` der früheren Vorlage werden entfernt, wenn jede Zeile der Vorlage entspricht
  (Platzhalter `$…` stehen für beliebigen Text). Eigene Dateien bleiben unberührt und werden nicht als offen gemeldet:
  Die Software liest sie nicht.
- Der Kopfkommentar der `reise.yaml` mit wörtlichem `\n` (Rest von #218) bekommt echte Zeilenumbrüche.
- Eine neu angelegte Reise hat nichts nachzuziehen (Test). So laufen Vorlage und Umstellung nicht auseinander.

### Eckdaten

Der Status steht in Worten: „Status: Planung“ (neue Texte `inhalt.eckdaten.status.<wert>` in jeder Sprache).

### Regel

`CLAUDE.md`: Jede Änderung am Format der Reisedaten bringt ihre Umstellung in `neu.py nachziehen` mit, mit Test. Ein
Handschritt in Reisen oder Instanzen nach einem Software-Wechsel ist ein Fehler der Software.

## Nicht Teil dieses Vorhabens

- Die Zeile „Status: …“ im Wissen W-01 der Reise Skiurlaub: Inhalt, wird nach der Umstellung über den Konnektor
  geändert (PO-Zustimmung 2.11.2026), nicht in Claude Code.
- `CLAUDE.md` mit eigenem Inhalt (drei Reisen der Instanz) bleibt unangetastet; ob dieser Inhalt auf die Seite gehört,
  entscheidet der PO (Abschlussbericht).
- Handschritte an den Diensten in `docs/betrieb.md` (Push-Dienst: Pakete, `einrichten.sh`, sudo-Regel): eigenes Issue.
- `reise.json` in `indent=2`: kanonische Form der Software, keine Änderung.

## Betroffene Dateien

| Datei | Änderung |
|---|---|
| `betrieb/software-nachziehen.sh` | neu: Umstellen, Tor, Commit, Push mit Neu-Umstellen, Issue |
| `betrieb/software-nachziehen.yml` | behält „Neuer Stand?“ und „Submodul setzen“, richtet Python ein, ruft das Skript |
| `betrieb/veroeffentlichen.sh`, `betrieb/gemeinsam.sh` | Anstoß je Software-Stand, Vorgabe der Wartezeit |
| `engine/neu.py` | Reste entfernen, Kopfkommentar berichtigen, OFFEN-Meldung zu Resten entfällt |
| `engine/reise.py` | Status in Worten |
| `engine/texte_de.py`, `engine/texte_en.py` | Status-Wörter, Meldungen der Umstellung |
| `engine/altformen/vorlage-vor-217/{de,en}/` | Muster der früheren Vorlage (liegt schon) |
| `docs/betrieb.md`, `CLAUDE.md` | Ablauf, Anstoß, Regel; „von Hand übernehmen“ entfällt |

Kein neues Python-Modul für Konnektor oder Dienst, daher keine Änderung an `betrieb/deploy.sh`.

## Geplante Tests

- `engine/tests/test_umstellung_250.py` (liegt schon, rot): neue Reise ohne Meldung, Reste entfernt (Probelauf schreibt
  nichts), eigene bleiben ohne Meldung, Kopfkommentar, Status in Worten je Sprache, zweiter Lauf ändert nichts. Ergänzung beim Schreiben der Tests: Beim zweiten Lauf werden alle Dateien
  der Reise vor und nach dem Lauf verglichen, nicht nur die Meldungen.
- `engine/tests/test_neu.py` (~387): erwartet keine OFFEN-Meldung zu `CLAUDE.md` mehr.
- `engine/tests/test_software_nachziehen.py`: yml ruft das Skript; Skript gegen ein Reisen-Repo mit Submodul und
  Bare-Remote, Attrappen für `gh`, `pytest`, Bau: Commit mit und ohne neuen Stand, kein Commit ohne Änderung, Tor rot
  mit und ohne offenes Issue (Kommentar nur, wenn das Issue den aktuellen Stand noch nicht nennt; auch Tor rot ohne neuen
  Stand), Skript fehlt (Lauf rot mit Hinweis), Wettlauf (Commit auf origin zwischen Umstellen und Push), drei gescheiterte Pushes.
- `engine/tests/test_betrieb.py`: Anstoß einmal je Stand, Wiederholung nach der Wartezeit, Merkdatei nur nach Erfolg,
  Fehler hält das Veröffentlichen nicht auf.

## Akzeptanzkriterien

- **AC-1:** Die Vorlage `software-nachziehen.yml` ruft `frieda/betrieb/software-nachziehen.sh` mit `ALT`, `NEU` und
  `NEU_DA` auf und richtet Python und Pakete in jedem Lauf ein. Unverändert gegenüber der Vorlage auf `main` (Stand
  74a2d29) bleiben die Schritte „Neuer Stand?“ und „Submodul setzen“, die Auslöser `schedule`
  (`7,37 * * * *`) und `workflow_dispatch`, die Rechte `contents: write` und `issues: write` sowie `concurrency`
  `software-nachziehen` ohne Abbruch laufender Läufe. Fehlt das Skript, endet der Lauf rot mit Hinweis.
- **AC-2:** Das Skript stellt in jedem Lauf jede Reise mit `reise.json` um und übernimmt Submodul und Reisen in einem
  Commit, auch ohne neuen Software-Stand. Ohne Änderung entsteht kein Commit; ein zweiter Lauf direkt danach ändert
  nichts.
- **AC-3:** Tor: `engine/tests` (nur bei neuem Stand) und der Bau jeder Reise sperren, `tests/` warnt nur. Rot ohne
  offenes Issue `software-nachziehen`: Issue und Exit 1. Rot mit offenem Issue: Warnung, Exit 0, kein Commit, und ein
  Kommentar nur dann, wenn das Issue den aktuellen Software-Stand noch nicht nennt.
- **AC-4:** Scheitert der Push, setzt das Skript auf `origin/main` zurück und stellt neu um, höchstens drei Versuche,
  nie `--force`. Nach drei gescheiterten Versuchen Exit 1 ohne Issue.
- **AC-5:** `veroeffentlichen.sh` startet den Workflow einmal je neuem Software-Stand und für denselben Stand erst nach
  `FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN` (Vorgabe 6 Stunden, gerechnet ab der gemerkten Zeit, ohne weitere Bedingung)
  wieder; die Merkdatei entsteht nur nach Erfolg von `gh`; ein
  Fehler dabei hält das Veröffentlichen nicht auf.
- **AC-6:** `neu.py nachziehen` entfernt `CLAUDE.md` und `kontext/herkunft.md` genau dann, wenn sie nach der Regel oben
  ausgefüllte Kopien des Musters sind (ein leeres `kontext/` mit), lässt jede andere Datei unberührt und ohne
  OFFEN-Meldung und berichtigt den Kopfkommentar mit wörtlichem `\n`; eine neu angelegte Reise meldet nichts, in jeder
  Sprache.
- **AC-7:** Die Eckdaten zeigen den Status in Worten („Status: Planung“, „Status: Planning“), für jeden Wert von
  `reise.STATUS` außer `idee` (eigener Text wie bisher) in jeder Sprache.
- **AC-8:** `docs/betrieb.md` beschreibt Ablauf des Skripts, Anstoß vom Server und Wartezeit; `CLAUDE.md` enthält die
  Regel „Formatänderung bringt ihre Umstellung in `neu.py nachziehen` mit, mit Test“; „Änderungen an der Vorlage werden
  von Hand übernommen“ steht nirgends mehr.

- **AC-9:** Vor dem Vorspulen auf `main` laufen die Tests des Reisen-Repos der Instanz mit diesem Branch; rot darf dort
  nur sein, was schon vorher rot war.

## Einführung

Einmalige Ausnahme beim Einführen: Danach kommt jeder Ablauf mit der Software, die Vorlage selbst ändert sich nicht
mehr. Die Sitzung, die #250 ausliefert, erledigt das selbst (kein Auftrag an den PO). Nach dem Zusammenführen wird
die Vorlage ein letztes Mal in das Reisen-Repo der Instanz kopiert (PR dort). Der nächste
Lauf stellt die vier Reisen der Instanz um, die noch Eckdaten der früheren Vorlage tragen.

## Implementation Details

Abweichungen der Umsetzung (2.11.2026), keine Änderung an den Akzeptanzkriterien:

- **Anstoß liest `origin/main` statt `HEAD`.** Die Präzisierung unter „Anstoß vom Server“ nennt
  `git rev-parse HEAD:frieda` und `.gitmodules` im Arbeitsbaum, direkt nach `anstoss_weitergeben`. Umgesetzt ist
  `git config --blob origin/main:.gitmodules submodule.frieda.url` und `git rev-parse origin/main:frieda`, direkt nach
  `git fetch origin main` und vor der frühen Rückkehr bei „nichts Neues“, also weiterhin in jedem Lauf. Grund: Gelesen
  wird der Stand, den der Lauf gleich baut; `HEAD` kennt ein Submodul, das erst mit diesem Lauf in den Bauordner kommt,
  noch nicht (Test `test_anstoss_*` in `engine/tests/test_betrieb.py`).
- **Status in Worten:** planung „Planung“/„Planning“, fest „Plan steht“/„Plan fixed“, unterwegs „Unterwegs“/„Under way“,
  danach „Nach der Reise“/„After the trip“, archiv „Archiviert“/„Archived“ („Plan steht“ wie in der Beschreibung des
  Status für den Konnektor).
- **Veralteter Test:** `engine/tests/test_neu.py::test_eckdaten_folgen_reise_yaml` erwartete „Status: planung“; nach AC-7
  „Status: Planung“.
- `betrieb/einstellungen.beispiel` erklärt die neue Vorgabe `FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN` (Pflicht durch
  `test_beispiel_einstellungen_sind_vollstaendig`).
- Die Zeilen „von Hand übernommen“ in dieser Spec und in `docs/context/…-250.md` zitieren den früheren Satz; AC-8 meint
  Doku und Regeln der Software.
