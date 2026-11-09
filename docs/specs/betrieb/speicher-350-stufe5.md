---
entity_id: speicher-350-stufe5
type: feature
created: 2026-11-09
updated: 2026-11-09
status: draft
workflow: speicher-stufe5-350
version: "1.0"
tags: [reisespeicher, umschaltung, vergleichslauf, veroeffentlichen, schreibweg, betrieb, epic-345]
---

# Speicher Stufe 5: Instanzen umschalten, altes Repo als Archiv (#350, Epic #345), Software-Anteil

Grundlage: `docs/context/speicher-stufe5-350.md` (Kontext und Analyse mit der Entscheidung des Tech Leads: Variante A), ADR-0009, `speicher-349-stufe4.md` (Stufe 4), `speicher-348-stufe3.md` (Stufe 3).

## Approval

- [ ] Approved

(Keine Annahme für den Product Owner offen: alle Entscheidungen sind technisch und unten begründet.)

## Purpose

Mit Stufe 5 laufen alle Reisen einer Instanz je Reise über den Reisespeicher statt über Git (Schalter `FR_SPEICHERREISEN`, Reihenfolge Testreise, kleinste echte Reise, übrige). Die eigentliche Umschaltung der echten Reisen ist Arbeit an der Instanz (privates Reisen-Repo, dort #252) und gehört nicht in dieses Repo. Die **Software** muss dafür drei Dinge liefern, die heute fehlen (Befunde 1, 2, 4, 5, 7 der Analyse):

1. **Die Umschaltung ist abgesichert.** `betrieb/vergleichslauf.sh` ist bis jetzt nur eine Auskunft; ein Stempel „gleich“ wird von niemandem gelesen. Eine Reise, die in Git liegt und nie aus dem Speicher veröffentlicht wurde, lässt sich also in `FR_SPEICHERREISEN` aufnehmen, ohne dass geprüft ist, dass der Speicher ihren Git-Stand wirklich enthält. Wird sie dann gebaut oder beschrieben, würde Inhalt aus Git still verloren gehen. Ab jetzt werden Veröffentlichen und Schreibweg ohne gültigen Stempel „gleich“ für eine solche Reise verweigert (Sperre bei der ersten Umschaltung).
2. **Veröffentlichen kommt für die Reisen im Speicher ohne GitHub aus.** Heute endet der Lauf mit Fehler (systemd „failed“, Heartbeat bleibt aus), sobald `git fetch` scheitert, obwohl die Reisen aus dem Speicher da schon veröffentlicht sind. Künftig ist ein Ausfall von GitHub für sie kein Fehler des Laufs; nur die Software-Aktualisierung wartet und meldet das einmal je Störung als Warnung.
3. **Die Umschaltung ist beschrieben**: eigener Abschnitt „Umschaltung einer Reise“ in `docs/betrieb.md` mit Reihenfolge, Vergleichslauf, Schalter, Prüfung im Konnektor, Rückweg Speicher nach Git, Zurücksetzen und dem alten Repo als Archiv; dazu die Zeile Stufe 5 in ADR-0009.

Ausdrücklich **nicht** Teil dieses Issues: Der Software-Weg über das Reisen-Repo (Submodul, Workflow „Software nachziehen“) bleibt (Variante A, Entscheidung 1).

## Source

- **File:** `betrieb/veroeffentlichen.sh`, `betrieb/vergleichslauf.sh`, `engine/reisespeicher.py`, `engine/schreiben.py`, `engine/texte_de.py`, `engine/texte_en.py`, `betrieb/einstellungen.beispiel`, `docs/betrieb.md`, `docs/adr/0009-reisespeicher.md`; neu `engine/tests/test_speicher_stufe5.py`
- **Identifier:** `reisespeicher.umschaltung_frei`, Befehl `reisespeicher.py umschaltung`, Stempel `<FR_DIENST>/vergleich/<reise>.json` (neues Feld `baum`), Merker `<FR_DIENST>/software-wartet`, Einstellung `FR_SOFTWARE_WARTET_STUNDEN`, Katalogschlüssel `schreiben.dienst.umschaltung_nicht_freigegeben`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `betrieb/veroeffentlichen.sh` (`speicher_reisen_lauf`, `main`, `erfolg_melden`, `speicher_rot_melden`, `software_anstossen`, `anstoss_weitergeben`) | Skript | Speicher-Teil vor `git fetch`; Stempel `<FR_DIENST>/reise-stand/<reise>.gebaut`; Meldeweg `fr_melden` aus `gemeinsam.sh` |
| `betrieb/vergleichslauf.sh` | Skript | schreibt den Stempel `<FR_DIENST>/vergleich/<reise>.json` (`zeit`, `ergebnis`, `stand`, `git`, `unterschiede`) |
| `betrieb/gemeinsam.sh` (`speicherreisen`, `ist_speicherreise`) | Skript | Liste `FR_SPEICHERREISEN` in der Shell, gleiche Regeln wie `instanz.speicherreisen()` |
| `engine/instanz.py` (`speicherreisen`, `dienst`, `wurzel`) | Modul | Schalter, `<FR_DIENST>`, Bauordner |
| `engine/reisespeicher.py` (`stand_nummer`, `reisen`, `zuruecksetzen`, `exportieren`, CLI `main`) | Modul | Stand-Nummer, Umschaltprüfung (neu), Rückweg und Zurücksetzen (bestehend) |
| `engine/schreiben.py` (`anwenden_extern`, `vorgang_speicher`, `fehler_antwort`) | Modul | Schreibweg der Speicherreisen, bestehender 503-Fall „Reise in der Liste, aber nicht im Speicher“ |
| `engine/texte.py`, `engine/texte_<sprache>.py`, `engine/tests/test_texte.py` | Textkatalog | neuer Fehlertext in allen Sprachen |
| `engine/tests/test_betrieb.py` (Fixtures `vf`, `sp`, Hilfen `git`, `ausfuehrbar`) | Tests | Shell-Läufe mit Attrappen; bestehende Tests der Speicher-Reisen müssen die neue Sperre berücksichtigen (AC-23) |
| `docs/specs/betrieb/speicher-348-stufe3.md`, `speicher-349-stufe4.md`, `docs/adr/0009-reisespeicher.md`, `docs/adr/0001-kern.md` | Specs, ADR | Rahmen und Prüfstelle |

## Scope

### Im Scope

- Sperre bei der ersten Umschaltung in **Veröffentlichen** (`speicher_reisen_lauf`) und im **Schreibweg** (`vorgang_speicher`), mit gemeinsamer Funktion `reisespeicher.umschaltung_frei` und dem Befehl `reisespeicher.py umschaltung <reise>`, den die Shell aufruft (eine Quelle der Wahrheit).
- `vergleichslauf.sh` schreibt im Stempel zusätzlich den Git-Baum der Reise (`baum`), damit „veraltet“ genau bestimmbar ist; Kopfkommentar nennt den Stempel als Voraussetzung.
- Neuer Katalogtext für die Ablehnung im Schreibweg in allen Sprachen.
- `veroeffentlichen.sh`: Scheitert `git fetch`, ist das bei einer Instanz mit Speicherreisen kein Fehler des Laufs. Warnung „Software-Aktualisierung wartet“, einmal je Störung nach einer Frist (`FR_SOFTWARE_WARTET_STUNDEN`), Merker `<FR_DIENST>/software-wartet`.
- Prüfung der übrigen GitHub-Zugriffe des Laufs (`gh workflow run`, `git ls-remote`) auf dasselbe Verhalten (Befund unter „Verhalten“: sie sind schon nur Warnungen; ein Test hält es fest).
- Dokumentation: neuer Abschnitt „Umschaltung einer Reise“ in `docs/betrieb.md`, Anpassung der Sätze „bis Stufe 5 eine Auskunft, keine Sperre“, Einstellung in `docs/betrieb.md` und `betrieb/einstellungen.beispiel`, Kopfkommentar von `vergleichslauf.sh` und `veroeffentlichen.sh`, Zeile Stufe 5 in ADR-0009.
- Tests: neue Datei `engine/tests/test_speicher_stufe5.py`; Anpassung der bestehenden Tests, die von der Sperre oder vom neuen Verhalten bei `git fetch` berührt sind.

### Nicht im Scope

- **Variante B** (die Instanz holt die Software direkt aus dem öffentlichen Repo, Workflows „Software nachziehen“ und `gh workflow run` entfallen, Reisen-Repo wird reines Archiv): eigenes Folge-Issue #454. Das Wort „Workflows entfallen“ im Umfang von #350 wird damit auf dieses Folge-Issue verwiesen; die Akzeptanz von #350 verlangt Unabhängigkeit der **Reisedaten** von GitHub, und die ist mit diesem Scope erfüllt.
- **Umschalten echter Reisen**, Messung AC-27 aus #349 (Schreiben bis Veröffentlichen mit rund 110 MB Fotos, Ziel unter 120 s), Rückspielversuch der Sicherung außer Haus (#347, #384) und das Reisen-Repo-Issue #252: Arbeit an der Instanz, nicht in diesem Repo.
- **Foto-Link im Wissenstext als Bild:** eigenes Issue (Produktfrage, nicht Teil von #350).
- Akzeptanzpunkte 2 (Sicherung außer Haus) und 3 (Zurücksetzen) des Issues: Software-Anteil nur Dokumentation. `zuruecksetzen` ist gebaut und in `engine/tests/test_reisespeicher.py` getestet; Sicherung und Rückspielversuch sind Instanzsache.
- `betrieb/einrichten.sh` (prüft bei der Einrichtung `git ls-remote origin` und `gh auth status`) und `betrieb/software-nachziehen.*`: gehören zum Software-Weg und damit zu Variante B.
- Eine Sperre für Reisen, die schon aus dem Speicher veröffentlicht wurden (Stempel `.gebaut`), und für Reisen, die nur im Speicher liegen.
- Änderungen am Konnektor, an `schreiben_git.py` und an der Seite.

### Affected Files

Siehe Abschnitt „Dateien“ weiter unten.

### Estimated Changes

- Dateien: 9 zu ändern (siehe Tabelle „Dateien“), 1 neue Testdatei, 1 bestehende Testdatei anzupassen
- Umfang: ca. +330 / -30 Zeilen (davon rund 190 Tests, 60 Doku)
- Risiko: mittel. `veroeffentlichen.sh` ist der Lieferweg aller Reisen. Die Sperre darf die schon umgeschaltete Testreise nicht treffen (deshalb nur ohne Stempel `.gebaut`, AC-5, AC-9, AC-16, AC-24).

## Entscheidungen mit Begründung

1. **Variante A statt B.** Das Reisen-Repo bleibt Träger der Software (Submodul `frieda/`); der Workflow „Software nachziehen“ hebt weiter den Zeiger. Die Reisedaten brauchen GitHub nicht mehr. Begründung: B baut den Software-Weg (Rot-Datei, `software_kennung`, Prüfung vor dem Deploy, die alle am Commit des Bauordners hängen) um, ohne Nutzen für den Reisebetrieb, und gehört nicht in denselben Schritt wie die Umschaltung echter Reisen (eine Änderung zur Zeit, Risiko am Live-System).
2. **Sperre nur bei der ersten Umschaltung.** Gesperrt wird eine Reise genau dann, wenn alle vier Bedingungen gelten: sie steht in `FR_SPEICHERREISEN`, sie liegt im Git-Bauordner (`reisen/<reise>` im Commit `HEAD`), es gibt keinen Stempel `<FR_DIENST>/reise-stand/<reise>.gebaut` und es gibt keinen gültigen Vergleichsstempel „gleich“. Der Stempel `.gebaut` entsteht nur nach gelungenem Deploy aus dem Speicher; wo er liegt, war die Reise schon in Betrieb, und die Sperre darf sie nicht treffen: Das ist die Testreise, die schon umgeschaltet ist, und ihre Umstellung nach dem Deploy dieser Software darf keinen Handschritt brauchen (#250). Eine Reise, die nur im Speicher liegt (etwa neu aus der Claude-App angelegt), hat nichts zu vergleichen. Dass `.gebaut` die Prüfung nach der ersten Veröffentlichung beendet, ist gewollt: ab dann ist der Speicher die Quelle, und Schreibvorgänge verändern ihn legitim. Folge für den Rückweg: Er löscht `.gebaut` (Abschnitt „Rückweg“), sonst entfiele die Sperre bei einer zweiten Umschaltung.
3. **Wann gilt ein Stempel als gültig?** Der Stempel `<FR_DIENST>/vergleich/<reise>.json` ist ein JSON-Objekt, das `vergleichslauf.sh` schreibt. Er gilt, wenn alles Folgende stimmt:
   - lesbar, gültiges JSON-Objekt, `ergebnis` ist genau `gleich`;
   - `baum` (neu, siehe Entscheidung 4) ist gleich dem Git-Baum von `reisen/<reise>` im jetzigen `HEAD` des Bauordners (`git rev-parse HEAD:reisen/<reise>`): Der Git-Stand der Reise hat sich seit dem Vergleich nicht geändert;
   - `stand` ist eine Zahl und nicht größer als die jetzige Stand-Nummer der Reise im Speicher (`reisespeicher.stand_nummer`): Der Speicher ist nicht hinter den verglichenen Stand zurückgefallen (etwa ein anderer oder neu angelegter Speicher).

   Begründung: Der Speicher ist nur anhängend; sein Inhalt bei Stand `stand` ist unveränderlich. „Gleich bei Stand s und Baum t“ ist deshalb eine dauerhaft wahre Tatsache, solange der Git-Baum noch t ist. Was die Sperre verhindern soll, ist Verlust von Inhalt aus Git. Er kann nur entstehen, wenn Git sich nach dem Vergleich verändert hat (Baum anders). Schreibt dagegen nach dem Vergleich der Schreibweg in den Speicher (Stand größer), ist das die legitime Fortsetzung, die der Stempel selbst erlaubt hat; verlangte man dort Gleichheit der Stand-Nummer, sperrte der erste Schreibvorgang nach dem Schalter den ersten Bau (Wettlauf, der sich nur durch ein neues, dann „ungleiches“ Vergleichen lösen ließe). Dass `vergleichslauf.sh --bis N` einen älteren Stand vergleichen darf (etwa den Anfangsvorgang), ist in `docs/betrieb.md` schon so vorgesehen und bleibt gültig. Der Commit `git` im Stempel bleibt als Auskunft stehen, zählt aber nicht, weil jeder Commit außerhalb von `reisen/<reise>` (andere Reisen, Software) ihn sonst ungültig machte.
4. **Stempel um den Git-Baum erweitern (`baum`).** `vergleichslauf.sh` schreibt zusätzlich `"baum": "<git rev-parse HEAD:reisen/<reise>>"`. Bestehende Felder bleiben unverändert (der Test `test_vergleichslauf_schreibt_stempel_und_exit_codes` prüft eine Obermenge). Ein Stempel ohne `baum` (von vor dieser Änderung) gilt als veraltet; der Vergleichslauf läuft von Hand und ist in Sekunden wiederholt. Es gibt keine Übergangsregel, die einen Stempel ohne Baum durchließe: eine Sperre mit Lücke wäre keine.
5. **Eine Quelle der Wahrheit: die Funktion in Python, die Shell ruft sie.** `reisespeicher.umschaltung_frei(reise) -> (frei: bool, grund: str)` ist die einzige Stelle der Regel. Die Shell fragt `reisespeicher.py umschaltung <reise>` (Ausgabe `frei` oder `gesperrt <grund>`, Exit 0 frei, 1 gesperrt, 2 Fehler). Begründung: Der Stempel ist JSON und der Git-Baum wird verglichen; das in Shell nachzubauen hieße zwei Implementierungen einer Sicherheitsregel, die auseinanderlaufen können (die Liste `FR_SPEICHERREISEN` gibt es bereits doppelt, mit dem Test `test_ohne_speicherreisen…`, als Beispiel für die Pflege, die das kostet). Die Funktion steht in `reisespeicher.py`, nicht in `engine/instanz.py` (wie im Kontext erwogen), weil sie die Stand-Nummer aus dem Speicher braucht und `reisespeicher.py` `instanz.py` importiert; ein Import in der Gegenrichtung wäre ein Kreis. `reisespeicher.py` steht schon in allen Modullisten von `betrieb/deploy.sh` (`SB_MODULE`, `RM_MODULE`, `KN_MODULE`, `PS_MODULE`); ein neues Modul entsteht nicht.
6. **Fehlerfall der Prüfung ist gesperrt (fail closed, wie #361).** Lässt sich `git` nicht starten, der Stempel nicht lesen oder der Baum nicht bestimmen, obwohl der Bauordner ein Git-Repo ist, gilt die Reise als gesperrt (Grund `git_nicht_lesbar`), nie als frei. Ein Bauordner, der kein Git-Repo ist (`HEAD` nicht auflösbar), zählt dagegen so, als läge nichts in Git: frei. Eine Instanz ohne Git-Bauordner hat nichts zu vergleichen.
7. **Verhalten des Veröffentlichens bei gesperrter Reise.** `speicher_reisen_lauf` überspringt die Reise mit einem Hinweis im Protokoll („is in git and not cleared for the switch (reason), run betrieb/vergleichslauf.sh; it stays at its last state“). Der Lauf bleibt grün, die Reise ist weder rot noch gebaut, und der Git-Teil baut sie auch nicht (er überspringt Reisen der Liste, `reisen_des_laufs`). Die Seite bleibt auf dem Stand des letzten Baus. Es gibt keine Meldung an den Betrieb: Es ist kein Ausfall, sondern ein Schritt, den der Betreiber eben selbst begonnen hat, und der Hinweis steht im Protokoll und in der Ablehnung des Schreibwegs. Lässt sich die Prüfung selbst nicht ausführen (Exit 2 des Befehls, Python-Fehler), ist das eine Störung wie ein unlesbarer Speicher: der Lauf endet mit 1, der nächste versucht es wieder.
8. **Verhalten des Schreibwegs bei gesperrter Reise.** `vorgang_speicher` prüft nach dem bestehenden Fall „Reise nicht im Speicher“ (503, unverändert) und vor dem Exportieren in die Arbeitskopie. Antwort 503 mit `fehler_code` `schreiben.dienst.umschaltung_nicht_freigegeben` und Katalogtext in der Sprache der Person; nichts wird geschrieben, kein Vorgang, die temporären Ordner werden wie in jedem Fall gelöscht. 503 (nicht 422) wie beim bestehenden Nachbarfall: Es ist keine falsche Eingabe der Person, sondern ein Zustand, den der Betreiber beheben muss. `reise_anlegen` (neue Reise) ist nicht betroffen: Es gibt keine Git-Kopie.
9. **Veröffentlichen ohne GitHub (Ergebnis des Laufs = Ergebnis des Speicher-Teils).** Gilt nur, wenn `FR_SPEICHERREISEN` nicht leer ist (`speicher_aktiv`); ohne Liste bleibt jedes Verhalten wie heute (auch ein gescheitertes `git fetch` endet mit 1). Scheitert `git fetch -q origin main`:
   - kein Abbruch des Laufs: Warnung im Protokoll „Warning: git fetch failed (no network or GitHub down), software update and trips still in git wait“;
   - es folgt nichts vom Git-Teil: kein `software_anstossen` (also weder `git ls-remote` noch `gh workflow run`), kein Vorspulen, keine Prüfungen, kein Bau von Git-Reisen. Sie bleiben auf ihrem Stand, genau wie bei jedem Lauf ohne neuen Stand;
   - `zustellen` (Links neuer Reisen) läuft wie im Lauf ohne neuen Stand;
   - Ergebnis: Hat der Speicher-Teil Reisen rot gemeldet (`speicher_rote`), endet der Lauf wie bisher mit `speicher_rot_melden` und Exit 1 (Rot-Datei, Alarm nach der Schwelle). Sonst Exit 0.
   - **Stempel und Heartbeat nur bei vollem Erfolg:** `erfolg_melden` (Stempel `veroeffentlichen-erfolg`, Heartbeat) läuft nur, wenn keine Git-Reise mehr übrig ist (kein Verzeichnis `reisen/<name>` mit `reise.json` im Commit `HEAD`, das nicht in der Liste steht). Gibt es noch Git-Reisen, endet der Lauf mit 0 (systemd „failed“ wäre falsch: es ist kein Fehler der Software), aber ohne Heartbeat; so schlägt die Überwachung nach ihrer Frist an, weil diese Reisen wirklich nicht aktualisiert werden. Das folgt der Regel „Readiness statt Liveness“ (Ping nur bei fachlichem Erfolg, bei Netzwerkfehlern nicht) und lässt die Umschaltung Reise für Reise zu, ohne dass ein GitHub-Ausfall den Dienst auf „failed“ setzt. Sind alle Reisen im Speicher, ist ein GitHub-Ausfall für den Lauf folgenlos.
   - `main()` setzt `neu` vor dem Aufruf von `speicher_rot_melden` auf den jetzigen `HEAD` (die Variable ist an der Stelle sonst nicht gesetzt, `set -u`).
10. **Warnung „Software-Aktualisierung wartet“, entprellt.** Zustand in `<FR_DIENST>/software-wartet` (Zeilen `seit=<Sekunden seit 1970>` und `gemeldet=0|1`). Erster gescheiterter Lauf: Datei anlegen (`seit` = jetzt, `gemeldet=0`). Jeder weitere gescheiterte Lauf: nur die Protokollzeile. Ist `jetzt - seit` mindestens `FR_SOFTWARE_WARTET_STUNDEN` Stunden (Vorgabe 6, wie `FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN`; ungültiger Wert fällt auf 6 zurück) und `gemeldet=0`: genau eine Protokollzeile „Software update waiting since <Dauer>; trips from the trip store are published“ (Stufe Warnung) und `gemeldet=1`. Gelingt `git fetch` wieder, wird die Datei gelöscht; die nächste Störung warnt wieder einmal. **Keine Nachricht über `fr_melden`, weder `normal` noch `high`**: Ein GitHub-Ausfall ist kein Ausfall der Reisen, und der Betreiber kann ihn nicht beheben; der Meldeweg der Instanz ist nur für Ausfälle, bei denen jetzt gehandelt werden muss und kann, dauerhafte Zustände gehören in den Monitor als Warnung. Zeit kommt aus `jetzt` (`VF_JETZT` für Tests). Die Datei ist die „Warnung im Zustand“: Der Monitor der Instanz liest sie (Teil-Check im Monitor-Skript des Infra-Repos, Warnung statt Alarm, sobald `gemeldet=1`); das ist ein eigenes Issue im Infra-Repo der Instanz, das der Tech Lead selbst umsetzt, nicht Teil dieser Spec. Begründung der Frist: Ein kurzer GitHub-Ausfall ist keine Warnung wert, und der Timer läuft alle 5 Minuten; erst ein Ausfall über Stunden ist ein Zustand, den der Monitor zeigen soll.
11. **Andere GitHub-Zugriffe des Laufs.** Befund aus dem Code: `anstoss_weitergeben` (`gh workflow run` für den Anstoß von der Seite) und `software_anstossen` (`git ls-remote`, `gh workflow run`) sind schon heute nur Warnungen; ihr Fehlschlag ändert das Ergebnis des Laufs nicht (`software_anstossen || true`, `anstoss_weitergeben` hat keinen Rückgabewert, der den Lauf beendet). Dazu ruft `speicher_reisen_lauf` weder `git fetch` noch `gh` noch `ls-remote`. Es genügt, das mit Tests festzuhalten (AC-18); nach Entscheidung 9 läuft `software_anstossen` bei gescheitertem `git fetch` gar nicht erst. `anstoss_weitergeben` läuft vor dem Speicher-Teil und braucht bei fehlendem `gh` weiter nur seine bestehende Meldung (eine, weil die Anstoß-Datei danach gelöscht wird).
12. **Keine neue Einheit, kein neuer Timer, kein neues Modul.** Alles läuft im vorhandenen Lauf von `veroeffentlichen.sh` und im Schreibdienst. `betrieb/deploy.sh` bleibt unverändert.
13. **Nichts Instanzspezifisches.** Pfade kommen aus `instanz.dienst()` und `FR_DIENST`, Reisenamen aus der Liste; Beispiele und Tests nutzen nur die zwei Beispielreisen.
14. **Rückweg Speicher nach Git als Betriebsschritt, nicht als Befehl.** Der Rückweg braucht keine neue Funktion: `exportieren` (byte-gleich, getestet) und der Schalter genügen. Ein eigener Befehl wäre Software für einen Notfall, der selten und bewusst von einem Menschen mit Blick auf die Reise ausgeführt wird; die Schritte stehen in der Anleitung (Abschnitt „Dokumentation“, Punkt 5). Wichtig ist nur Schritt (d), das Löschen von `.gebaut`, weil sonst die Sperre bei einer zweiten Umschaltung nicht mehr greift.

## Prüfstelle (ADR-0001, zehn Fragen)

| Nr. | Antwort |
|---|---|
| 1 Ontologie statt Sonderfall | Die Sperre kennt nur Reisenamen, den Stempel des Vergleichs, den Git-Baum und die Stand-Nummer, keine Grundform, keine Art, kein Merkmal. Durchgespielt an beiden Beispielreisen: `beispielreise` (Wanderung mit Varianten, liegt im Test-Bauordner in Git, wird umgeschaltet) und `stadtwochenende` (Reise ohne Pläne, einmal als Reise in Git, einmal nur im Speicher). |
| 2 Kein Katalog | Keine Art und kein Merkmal. |
| 3 Keine KI | Feste Regeln. |
| 4 Die Tür | Der Konnektor ändert sich nicht. Er bekommt im Fall der Sperre einen Fehlertext mit `fehler_code` wie bei den anderen 503-Antworten des Schreibwegs; keine neue Funktion, kein Eintrag in `docs/konnektor.md`. |
| 5 Herkunft | Die Sperre schreibt nichts in die Reise. Der Stempel trägt Zeit, Stand, Baum und Ergebnis des Vergleichs. |
| 6 Rollen entscheiden | Berührt keine Rollen und keine Inhalte; der Schreibweg lehnt vor jeder Rollenprüfung die ganze Reise ab, solange die Umschaltung nicht freigegeben ist. |
| 7 IDs und Verlauf | Keine IDs betroffen. Nur anhängend bleibt unverändert; die Sperre verhindert, dass ein Vorgang auf einem Stand aufbaut, der Git-Inhalt nicht enthält. `zuruecksetzen` bleibt ein neuer Vorgang. |
| 8 PWA | Die Seite wird mit demselben Generator gebaut; die Abnahme der Umschaltung an einer Instanz (Rundgang, Konnektor) ist Arbeit an der Instanz, hier nur beschrieben. Das Verhalten der Seite ändert sich nicht. |
| 9 Claude Code | Keine Reiseinhalte in Claude Code. |
| 10 Dokumentation | Diese Spec, ADR-0009 (Zeile Stufe 5), `docs/betrieb.md` (Abschnitt „Umschaltung einer Reise“, Einstellung, geänderte Sätze). |

## Verhalten

### Funktion `reisespeicher.umschaltung_frei(reise)`

Gibt `(True, "")` oder `(False, grund)` zurück. Reihenfolge der Prüfung (der erste Treffer entscheidet):

1. Die Reise steht nicht in `instanz.speicherreisen()`: frei (nicht zuständig). Löst `instanz.EinstellungenNichtLesbar` aus, wenn die Einstellungen nicht lesbar sind (wie überall, #361).
2. Es gibt `<instanz.dienst()>/reise-stand/<reise>.gebaut` (als Datei vorhanden, Inhalt egal): frei (schon aus dem Speicher veröffentlicht).
3. Der Bauordner `instanz.wurzel()` ist kein Git-Repo (kein auflösbares `HEAD`) oder `reisen/<reise>` ist im Commit `HEAD` nicht vorhanden: frei (nichts in Git, nichts zu vergleichen). Lässt sich `git` nicht ausführen oder der Baum nicht lesen: gesperrt, Grund `git_nicht_lesbar` (Entscheidung 6).
4. Der Stempel `<instanz.dienst()>/vergleich/<reise>.json` fehlt: gesperrt, Grund `kein_stempel`. Ist er nicht lesbar, kein JSON-Objekt, ohne `ergebnis`: gesperrt, Grund `stempel_ungueltig`.
5. `ergebnis` ist nicht `gleich` (`unterschied`, `fehler`, anderer Wert): gesperrt, Grund `stempel_nicht_gleich`.
6. `baum` fehlt oder ist nicht gleich dem Git-Baum von `reisen/<reise>` im jetzigen `HEAD`, oder `stand` ist keine ganze Zahl oder größer als `stand_nummer(reise)`: gesperrt, Grund `stempel_veraltet`. (Hat die Reise keinen Eintrag im Speicher, bleibt es bei den bestehenden Wegen, die das vorher ablehnen oder überspringen; die Funktion wird erst danach aufgerufen. Fällt `stand_nummer` auf `KeyError`, gilt gesperrt mit `stempel_veraltet`.)
7. Sonst: frei.

Die Funktion liest nur (Stempel, Git, Datenbank) und schreibt nichts. Der Name der Reise wird vor jedem Pfadbau gegen das Reisenamen-Muster der Software geprüft (kein `/`, kein `..`); ein ungültiger Name ist gesperrt mit Grund `stempel_ungueltig`.

### Befehl `reisespeicher.py umschaltung <reise>`

Ausgabe `frei` (Exit 0) oder `gesperrt <grund>` (Exit 1), Fehler beim Lesen der Einstellungen oder des Speichers `ERROR: …` (Exit 2). Der Befehl ändert nichts.

### Veröffentlichen: Sperre im Speicher-Teil

In `speicher_reisen_lauf`, in der Schleife je Reise, **nach** dem bestehenden Fall „kein Eintrag im Speicher“ (`n = -`, Hinweis, übersprungen) und **vor** der Entscheidung `modus`: Gibt es `<FR_DIENST>/reise-stand/<reise>.gebaut` nicht, ruft die Schleife `"$FR_PYTHON" "$FR_BETRIEB/../engine/reisespeicher.py" umschaltung "$r"` auf.

- Exit 0: weiter wie bisher (bauen).
- Exit 1: Hinweis im Protokoll mit dem Grund, `continue`. Kein `reise_stand_schreiben`, kein Eintrag in `speicher_rote`, kein Stempel `.gebaut`, kein Deploy, kein Materialisieren.
- anderer Exit: Zeile `ERROR: the switch check of $r failed (…), the next run tries again.` und `return 1` (wie ein unlesbarer Speicher).

Wo `.gebaut` existiert, wird der Befehl gar nicht aufgerufen (kein zusätzlicher Prozess je Lauf für schon umgeschaltete Reisen).

### Schreibweg: Sperre

In `vorgang_speicher` (`engine/schreiben.py`), in `vorbereiten()` im Zweig einer bestehenden Reise (`not neue_reise` und `reise in bekannt`), vor `reisespeicher.exportieren`: `frei, grund = reisespeicher.umschaltung_frei(reise)`. Ist sie nicht frei, merkt `vorbereiten` den Grund (`ergebnis["gesperrt"]`) und exportiert nichts. Nach der Frist-Behandlung antwortet `vorgang_speicher` (nach dem bestehenden `basis is None`-Fall): Protokollzeile `Store {werkzeug} 503: trip {reise} is not cleared for the switch ({grund})`, Antwort `503, fehler_antwort("schreiben.dienst.umschaltung_nicht_freigegeben")`. Ein Fehler der Funktion selbst (`OSError`, `sqlite3.Error`) läuft über die bestehenden Wege (`speicher_fehler`). Die Prüfung liegt in der Sperre der Reise und im Faden mit Frist wie das Exportieren, also unter derselben Zeitgrenze.

### Veröffentlichen ohne GitHub

Im Hauptablauf (`main`) wird `git fetch -q origin main` zu `if ! git fetch -q origin main; then …`. Im Zweig des Scheiterns (nur wenn `speicher_aktiv`, sonst wie heute `return 1`): `software_wartet_merken` (Entscheidung 10), Zustellen, Speicher-Ergebnis wie in Entscheidung 9, Rückkehr. Gelingt `git fetch`, löscht `main` `<FR_DIENST>/software-wartet`. Neue Funktionen in `veroeffentlichen.sh`: `git_reisen_uebrig` (gibt die Namen der Git-Reisen aus dem Commit `HEAD` aus, die nicht in der Liste stehen), `software_wartet_merken`, `software_wartet_loeschen`. Der Zweig setzt weder die Rot-Datei noch den Stand `<FR_DIENST>/veroeffentlicht`, außer über `speicher_rot_melden`.

### Vergleichslauf

`stempel()` in `vergleichslauf.sh` bekommt den Baum als Parameter: `git -C "$FR_WURZEL" rev-parse "HEAD:reisen/$r"`, und schreibt `"baum": "<hash>"` in den Stempel. Der Kopfkommentar nennt den Stempel nicht mehr „eine Auskunft, keine Sperre“, sondern: „Voraussetzung der ersten Umschaltung (erzwungen ab Stufe 5, #350) …; gültig solange der Git-Baum der Reise derselbe ist“. Ausgabe und Exit-Codes bleiben.

### Meldungstext

Ein neuer Katalogschlüssel in **allen Sprachen** (zurzeit `de`, `en`; jede später hinzukommende Sprache bekommt ihn, die Ausnahmelisten in `engine/tests/test_texte.py` dürfen nicht länger werden):

| Schlüssel | de | en |
|---|---|---|
| `schreiben.dienst.umschaltung_nicht_freigegeben` | Diese Reise soll über den Speicher geschrieben werden, ist dafür aber noch nicht freigegeben: Der Vergleich mit ihrem bisherigen Stand fehlt oder ist veraltet. Es wurde nichts geschrieben; der Betreiber muss den Vergleich zuerst durchführen. | This trip is to be written through the store but has not been cleared for it yet: the comparison with its previous state is missing or out of date. Nothing was written; the operator has to run the comparison first. |

Die Betriebsausgaben der Shell-Skripte und der Befehle (`Note: …`, `Warning: …`, `gesperrt <grund>`) bleiben englische Betreiberzeilen wie bisher; sie sind kein Teil des Katalogs.

### Dokumentation

Neuer Abschnitt „Umschaltung einer Reise“ in `docs/betrieb.md` (nach dem Absatz „Anfangsvorgang und Vergleichslauf“ im Speicherweg, als `###`-Überschrift im Abschnitt „Schreibweg“). Er enthält, in dieser Folge:

1. **Vorbedingungen:** Sicherung des Speichers außer Haus und gelungener Rückspielversuch (#347, Instanz), Umschaltung vorher im Issue angesagt, der Bauordner ist aktuell (ein Lauf von `veroeffentlichen.sh` ist grün durchgelaufen und niemand schreibt über den Git-Weg in diese Reise).
2. **Reihenfolge:** erst die Testreise, dann die kleinste echte Reise, dann die übrigen, je eine nach der anderen; jede nach dem Abschluss der Prüfung (Schritt 7), nie zwei gleichzeitig.
3. **Schritte je Reise:** (1) Anfangsvorgang `reisespeicher.py importieren … --ab <n−1>`; (2) `vergleichslauf.sh <reise>` muss `gleich` melden (der Stempel ist die Freigabe; ohne ihn oder mit veraltetem Stempel weigern sich Veröffentlichen und Schreibweg, Abschnitt unten); (3) Schalter: Reise in `FR_SPEICHERREISEN` von `betrieb/einstellungen.env` des Reisen-Repos aufnehmen und committen; (4) nächster Lauf von `veroeffentlichen.sh` baut aus dem Speicher und legt den Stempel `.gebaut` an; (5) Prüfung im Konnektor: `publish_status` meldet „enthalten: ja“ für den Reise-Stand, eine Probe-Änderung an einer Testreise (nie an einer echten Reise zum Probieren) wird veröffentlicht, die Seite lädt, auch offline; (6) Abnahme an beiden Reisetypen, nie nur an der Wanderung; (7) Git-Kopie liegen lassen.
4. **Die Sperre:** Wann sie greift (Entscheidung 2), wie man sie löst (`vergleichslauf.sh <reise>` erneut laufen lassen), was sie nicht trifft (Reisen nur im Speicher, Reisen mit Stempel `.gebaut`), die Ablehnung im Schreibweg (503) und der Hinweis im Protokoll.
5. **Rückweg Speicher nach Git** (Rückfallplan während der Umschaltung, Entscheidung 14): (a) Beteiligte informieren, dass bis zum Abschluss nicht geschrieben wird; (b) `reisespeicher.py exportieren <reise> <leerer Ordner>` (neuester Stand, byte-gleich); (c) den Ordner als `reisen/<reise>` ins Reisen-Repo übernehmen und die Reise aus `FR_SPEICHERREISEN` nehmen, beides im selben Commit, vorspulen auf `main`; (d) `<FR_DIENST>/reise-stand/<reise>.gebaut` und die Datei `<FR_DIENST>/reise-stand/<reise>.lauf.json` der Reise entfernen, damit bei einer späteren zweiten Umschaltung die Sperre wieder gilt; (e) der nächste Lauf baut die Reise aus Git; Kontrolle `vergleichslauf.sh <reise>` meldet `gleich` für den Stand, aus dem exportiert wurde. Die Reise bleibt im Speicher (nur anhängen), er wird nicht gelöscht.
6. **Zurücksetzen auf einen früheren Stand:** `reisespeicher.py verlauf <reise>` zeigt die Vorgänge; `reisespeicher.py zuruecksetzen <reise> <bis> <wer> <grund>` schreibt einen neuen Vorgang mit dem Inhalt des Stands `<bis>`, der Verlauf bleibt; der nächste Lauf veröffentlicht ihn.
7. **Das alte Repo als Archiv:** Nach der Umschaltung aller Reisen schreibt niemand mehr in `reisen/<reise>` des Reisen-Repos; der Stand dort ist das Archiv bis zum Umschalten. Das Reisen-Repo selbst bleibt als Träger der Software (Submodul, Workflow) bestehen, bis das Folge-Issue zu Variante B es ablöst; es wird nicht gelöscht und nicht auf GitHub archiviert (der Workflow „Software nachziehen“ brauchte Schreibrechte).
8. **GitHub-Ausfall:** Was der Lauf dann tut (Entscheidung 9 und 10), wo der Merker liegt, die Einstellung `FR_SOFTWARE_WARTET_STUNDEN`.

Zusätzlich: die Sätze „bis Stufe 5 eine Auskunft, keine Sperre“ im Absatz „Anfangsvorgang und Vergleichslauf“ und der Satz zur Vorbedingung im Absatz „Veröffentlichen und Nachziehen aus dem Speicher“ verweisen auf den neuen Abschnitt; der Satz „erst der Git-Teil endet mit Fehler“ im Abschnitt „Veröffentlichen, Reisen aus dem Reisespeicher“ wird durch das neue Verhalten ersetzt; die Tabelle der Einstellungen bekommt `FR_SOFTWARE_WARTET_STUNDEN`. ADR-0009 bekommt in „Konsequenzen“ und „Verlauf“ die Zeile Stufe 5 (Sperre bei der ersten Umschaltung, Veröffentlichen ohne GitHub, Variante A mit dem Folge-Issue zu B).

## Fehlerfälle

| Fall | Verhalten |
|---|---|
| Reise in Liste, in Git, ohne `.gebaut`, ohne Stempel | Veröffentlichen: Hinweis, übersprungen, Lauf grün. Schreibweg: 503 mit `schreiben.dienst.umschaltung_nicht_freigegeben`, nichts geschrieben. |
| Stempel `unterschied` oder `fehler` | wie oben (Grund `stempel_nicht_gleich`). |
| Stempel `gleich`, aber Git hat sich in `reisen/<reise>` seit dem Vergleich geändert | gesperrt (Grund `stempel_veraltet`); Lösung: Vergleich neu. Ändert sich nur etwas außerhalb von `reisen/<reise>`, bleibt der Stempel gültig. |
| Stempel ohne `baum` (von vor Stufe 5) | gesperrt (`stempel_veraltet`); Lösung: `vergleichslauf.sh <reise>` einmal laufen lassen. |
| Stempel `gleich`, Stand im Speicher inzwischen höher (der Schreibweg hat geschrieben) | frei (legitime Fortsetzung, Entscheidung 3). |
| Stempel `gleich`, `stand` höher als die Nummer im Speicher (anderer oder neuer Speicher) | gesperrt (`stempel_veraltet`). |
| Stempel kaputt (kein JSON, leer) | gesperrt (`stempel_ungueltig`), nie frei. |
| Reise nur im Speicher (nicht in Git) | frei, kein Stempel nötig (neu angelegte Reise, Beispiel `stadtwochenende` im Speicher). |
| Reise hat `.gebaut` (umgeschaltet, etwa die Testreise) | frei, kein Stempel nötig, Befehl wird nicht aufgerufen. |
| Reise steht nicht in `FR_SPEICHERREISEN` | die Funktion sagt frei; sie wird dort nicht gefragt. |
| Reise in Liste, aber nicht im Speicher | unverändert: Veröffentlichen „no entry, skipped“, Schreibweg 503 `reise_nicht_im_speicher` (die neue Prüfung kommt erst danach). |
| `git` nicht startbar oder Baum nicht lesbar (Bauordner ist ein Repo) | gesperrt (`git_nicht_lesbar`); Veröffentlichen: Störung, Exit 1, nächster Lauf wiederholt (nur wenn der Aufruf selbst scheitert, nicht beim normalen „gesperrt“). |
| Einstellungen nicht lesbar | unverändert (#361): Schreibweg 503 „Einstellungen nicht lesbar“; das Skript bricht schon in `gemeinsam.sh` ab. |
| `git fetch` scheitert, Liste leer | unverändert: Exit 1. |
| `git fetch` scheitert, Liste nicht leer, keine Git-Reise übrig | Lauf grün (Exit 0), Stempel `veroeffentlichen-erfolg` und Heartbeat, Warnung im Protokoll, Merker `software-wartet`. |
| `git fetch` scheitert, Liste nicht leer, Git-Reisen übrig | Exit 0, kein Stempel, kein Heartbeat, Git-Reisen bleiben auf ihrem Stand, Warnung im Protokoll, Merker. |
| `git fetch` scheitert und eine Speicher-Reise ist rot | Exit 1, Rot-Datei `art=reise`, Alarm nach der Schwelle, wie bei grünem `git fetch`. |
| `git fetch` scheitert länger als `FR_SOFTWARE_WARTET_STUNDEN` | genau eine Warnzeile im Protokoll und `gemeldet=1` im Merker (für den Monitor), keine Nachricht über `fr_melden`. |
| Software hat gewechselt, GitHub fällt aus, bevor der Git-Teil sie veröffentlicht hat | Speicher-Reisen bleiben auf ihrem letzten guten Stand (wie bisher: „software … is not published yet“); kein Fehler. Sobald GitHub wieder da ist, läuft alles wie in Stufe 3. |
| Vorgang zwischen Prüfung und Schreiben | unverändert: `StandGeaendert` im Unterprozess `anwenden` (503 „bitte noch einmal“). Die Sperre ist kein Ersatz dafür. |

## Acceptance Criteria

Neue Testdatei `engine/tests/test_speicher_stufe5.py`. Die Python-Ebene (AC-1 bis AC-12) nutzt `tmp_path`, einen eigenen `FR_SPEICHER`, `FR_DIENST` und einen kleinen Git-Bauordner (`git init`, ein Commit mit `reisen/<reise>` als Kopie der Beispielreise). Die Shell-Läufe (AC-13 bis AC-22) nutzen die Fixtures `vf` und `sp` aus `engine/tests/test_betrieb.py` (importiert, `# noqa: F401`), mit den Beispielreisen als Git-Reise im Test-Bauordner und im Speicher. Wo „beide Beispielreisen“ steht, sind die Tests über `beispielreise` (Wanderung mit Varianten, Personen Ida und Karl) und `stadtwochenende` (Reise ohne Pläne, Personen Tom und Lea) parametrisiert.

### Sperre: Funktion und Befehl

- **AC-1 Ohne Stempel gesperrt:** Given eine Reise aus der Liste, in Git (`HEAD`), im Speicher, ohne `.gebaut`, ohne Stempel / When `umschaltung_frei` / Then `(False, "kein_stempel")`; derselbe Aufruf über `reisespeicher.py umschaltung <reise>` gibt `gesperrt kein_stempel`, Exit 1; die Funktion schreibt nichts (Dateibaum von `FR_DIENST` und Speicher unverändert).
  - Test: `test_ohne_stempel_ist_die_reise_gesperrt` (beide Beispielreisen)
- **AC-2 Stempel nicht „gleich“ sperrt:** Given ein Stempel mit `ergebnis` `unterschied` oder `fehler` (sonst gültig) / Then gesperrt mit `stempel_nicht_gleich`; Given ein kaputter Stempel (leere Datei, kein JSON, JSON-Liste, ohne `ergebnis`) / Then gesperrt mit `stempel_ungueltig`, nie frei.
  - Test: `test_stempel_ungleich_oder_kaputt_sperrt`
- **AC-3 Stempel „gleich“ gibt frei:** Given ein von `vergleichslauf.sh` selbst geschriebener Stempel `gleich` (der Test lässt das echte Skript laufen: Git-Reise und Speicher mit gleichem Inhalt) / Then `(True, "")`, Exit 0, Ausgabe `frei`. Ein Stempel nach `--bis N` mit `N` kleiner als der jetzige Stand gilt ebenso.
  - Test: `test_stempel_gleich_gibt_die_umschaltung_frei` (beide Beispielreisen)
- **AC-4 Veralteter Stempel sperrt:** Given ein Stempel `gleich` und danach (a) eine Änderung in `reisen/<reise>` per neuem Git-Commit, (b) ein Stempel ohne Feld `baum`, (c) ein Stempel mit `stand` größer als die jetzige Stand-Nummer / Then gesperrt mit `stempel_veraltet`. Given ein Git-Commit nur außerhalb von `reisen/<reise>` (andere Reise, Software) / Then bleibt der Stempel gültig (frei). Given der Speicher hat nach dem Vergleich einen weiteren Vorgang bekommen (Stand höher) / Then frei.
  - Test: `test_veralteter_stempel_sperrt_und_fremde_aenderungen_nicht`
- **AC-5 Ausnahmen:** Given (a) eine Reise nur im Speicher, nicht in Git (`stadtwochenende` ohne Git-Kopie), kein Stempel / Then frei; Given (b) `<FR_DIENST>/reise-stand/<reise>.gebaut` existiert, kein Stempel, die Reise liegt in Git / Then frei, und `reisespeicher.py umschaltung` ist dafür nicht nötig; Given (c) die Reise steht nicht in `FR_SPEICHERREISEN` / Then frei; Given (d) der Bauordner ist kein Git-Repo / Then frei; Given (e) `git` lässt sich nicht starten (leerer `PATH`) bei einem Git-Bauordner / Then gesperrt mit `git_nicht_lesbar`, nie frei.
  - Test: `test_ausnahmen_der_sperre_und_git_nicht_lesbar_sperrt`
- **AC-6 Befehl:** Given `reisespeicher.py umschaltung` mit einem ungültigen Reisenamen (`../x`, leer) oder unlesbarer Einstellungsdatei / Then Exit 1 mit `gesperrt stempel_ungueltig` bzw. Exit 2 mit `ERROR: …`; der Befehl ändert weder Stempel noch Speicher.
  - Test: `test_befehl_umschaltung_exit_codes`

### Sperre: Schreibweg

- **AC-7 Schreibweg lehnt ab:** Given eine gesperrte Reise (AC-1) / When `schreiben.anwenden_extern` ein einfaches Schreibwerkzeug ausführt / Then `(503, antwort)` mit `fehler_code` `schreiben.dienst.umschaltung_nicht_freigegeben`; im Speicher gibt es keinen neuen Vorgang (Stand-Nummer gleich), die temporären Ordner sind gelöscht (kein `frieda-schreiben-*` im `TMPDIR` des Tests), und `anwenden` wurde nicht gestartet (kein Unterprozess, Attrappe).
  - Test: `test_schreibweg_lehnt_gesperrte_reise_ab_und_schreibt_nichts` (beide Beispielreisen)
- **AC-8 Schreibweg nach Freigabe:** Given derselbe Aufbau mit gültigem Stempel `gleich` / Then schreibt dasselbe Werkzeug (Antwort 200, Stand-Nummer um 1 höher). Given der Stempel wird danach durch eine Git-Änderung in `reisen/<reise>` veraltet und kein `.gebaut` existiert / Then lehnt der nächste Schreibvorgang wieder ab.
  - Test: `test_schreibweg_schreibt_nach_freigabe`
- **AC-9 Schreibweg: Ausnahmen (Testreise, nur im Speicher):** Given die Reise hat `.gebaut` und keinen Stempel, liegt aber in Git / Then schreibt der Schreibweg ohne Hinweis auf die Sperre (das ist die schon umgeschaltete Testreise, #250). Given eine Reise nur im Speicher / Then schreibt er ebenso. `reise_anlegen` ist unberührt.
  - Test: `test_schreibweg_sperrt_weder_umgeschaltete_noch_neue_reisen`
- **AC-10 Reihenfolge der Ablehnungen:** Given eine Reise in der Liste und in Git, aber nicht im Speicher / Then bleibt die Antwort `schreiben.dienst.reise_nicht_im_speicher` (unverändert, kein Stempel nötig).
  - Test: `test_reise_nicht_im_speicher_behaelt_ihren_fehler`
- **AC-11 Text in allen Sprachen:** Given der Schlüssel `schreiben.dienst.umschaltung_nicht_freigegeben` / Then steht er in jeder Sprachdatei aus `texte.SPRACHEN` (Parametrisierung über `SPRACHEN`, damit eine neue Sprache ohne Codeänderung mitgeprüft wird), ist nicht leer, hat in jeder Sprache dieselbe Menge Platzhalter (keine), und `texte_de.py` enthält ihn auf Deutsch mit Umlauten; `engine/tests/test_texte.py` bleibt grün, die Ausnahmelisten werden nicht länger.
  - Test: `test_umschaltung_text_steht_in_allen_sprachen` und `engine/tests/test_texte.py` (bestehend)
- **AC-12 Stempel des Vergleichslaufs trägt den Baum:** Given `vergleichslauf.sh <reise>` / Then enthält der Stempel zusätzlich zu `zeit`, `ergebnis`, `stand`, `git`, `unterschiede` das Feld `baum` gleich `git rev-parse HEAD:reisen/<reise>`; Ausgabe und Exit-Codes sind unverändert (0 gleich, 1 Unterschied, 2 Fehler); der Bauordner bleibt unberührt (`git status --porcelain` leer).
  - Test: `test_vergleichslauf_schreibt_den_git_baum` und `test_betrieb.py::test_vergleichslauf_schreibt_stempel_und_exit_codes` (bestehend, bleibt grün)

### Sperre: Veröffentlichen

- **AC-13 Veröffentlichen sperrt ohne Stempel:** Given eine Git-Reise in der Liste mit Eintrag im Speicher, ohne `.gebaut`, ohne Stempel, daneben eine zweite Speicher-Reise ohne Git-Kopie / When `veroeffentlichen.sh` läuft / Then wird die erste nicht gebaut (kein Eintrag in `deploy.log`, kein Ordner unter `<FR_DIENST>/bau/reisen/<reise>`, kein `.gebaut`, kein Eintrag in `reise-stand/<reise>.lauf.json`), das Protokoll nennt sie mit dem Grund, die zweite wird gebaut und freigeschaltet, der Lauf endet mit 0, die Rot-Datei fehlt, der Heartbeat wird wie bei jedem grünen Lauf gepingt (die Sperre allein macht den Lauf nicht rot und verhindert den Erfolg nicht).
  - Test: `test_veroeffentlichen_baut_gesperrte_reise_nicht` (beide Beispielreisen in beiden Rollen)
- **AC-14 Veröffentlichen mit „ungleich“ und „veraltet“:** Given ein Stempel `unterschied`, danach ein Stempel `gleich`, dann ein neuer Git-Commit in `reisen/<reise>` / Then wird die Reise im ersten und im dritten Fall nicht gebaut; im zweiten Fall wird sie gebaut, `.gebaut` trägt Nummer und Software-Kennung, und ein weiterer Lauf ohne neuen Stand baut sie nicht noch einmal (Verhalten der Stufe 3 unverändert).
  - Test: `test_veroeffentlichen_baut_nur_mit_gueltigem_stempel`
- **AC-15 Ende-zu-Ende ohne Handstempel:** Given Anfangsvorgang (`importieren … --ab`) und echter Lauf von `betrieb/vergleichslauf.sh <reise>` (Ergebnis `gleich`) / When der Schalter gesetzt ist und `veroeffentlichen.sh` läuft / Then wird gebaut, ohne dass der Test einen Stempel von Hand schreibt; ein anschließender Schreibvorgang über den Schreibweg gelingt (AC-8). Das ist der dokumentierte Weg der Umschaltung.
  - Test: `test_umschaltung_ende_zu_ende_mit_dem_echten_vergleichslauf` (beide Beispielreisen)
- **AC-16 Schon umgeschaltete Reise unberührt (#250):** Given die Reise hat `.gebaut` (Stand und Kennung einer früheren Software), liegt in Git und hat keinen Stempel (die Testreise nach dem Deploy dieser Software) / When `veroeffentlichen.sh` läuft, auch nach einem Software-Wechsel (Commit außerhalb von `reisen/`, Pfad „nachziehen“) und mit `--immer` / Then wird sie gebaut bzw. umgestellt wie in Stufe 3, ohne dass der Befehl `umschaltung` aufgerufen wird (der Test ersetzt `FR_PYTHON` durch eine protokollierende Attrappe wie `test_ohne_speicherreisen_bleibt_alles_wie_vorher`) und ohne Hinweis auf eine Sperre; es braucht keinen Handschritt.
  - Test: `test_umgeschaltete_reise_wird_nach_dem_deploy_weiter_gebaut_ohne_handschritt`
- **AC-17 Reise nur im Speicher und leere Liste:** Given eine Speicher-Reise ohne Git-Kopie und ohne Stempel / Then wird sie gebaut (neue Reise). Given `FR_SPEICHERREISEN` leer / Then gibt es keinen Aufruf von `reisespeicher.py` (Attrappe) und nichts ändert sich.
  - Test: `test_nur_im_speicher_baut_und_leere_liste_aendert_nichts`

### Veröffentlichen ohne GitHub

- **AC-18 Keine GitHub-Aufrufe im Speicher-Teil und nur Warnungen sonst:** Given `gh` und `git ls-remote` (über `VF_LSREMOTE`) als Attrappen, die ihren Aufruf festhalten und mit Fehler enden, und `_anstoss.json` in der Ablage / When der Lauf mit Speicher-Reisen läuft / Then ruft der Speicher-Teil weder `gh` noch `ls-remote` noch `git fetch` auf (Reihenfolge wie `test_speicher_teil_laeuft_vor_git_fetch`); ein Fehlschlag von `gh workflow run` (Anstoß der Seite) und von `ls-remote` ändert das Ergebnis des Laufs nicht (Warnung im Protokoll, Exit unverändert), und der Anstoß der Seite erzeugt höchstens eine Nachricht.
  - Test: `test_gh_und_ls_remote_aendern_das_ergebnis_des_laufs_nicht`
- **AC-19 `git fetch` scheitert, keine Git-Reise übrig:** Given `origin` zeigt auf einen Ort, den es nicht gibt, und `FR_SPEICHERREISEN` nennt jede Reise, die in `HEAD` unter `reisen/` liegt (und eine weitere, nur im Speicher) / When `veroeffentlichen.sh` läuft / Then endet der Lauf mit 0, die Speicher-Reisen sind gebaut (Seite trägt die Stand-Nummer aus dem Speicher), `veroeffentlichen-erfolg` ist berührt, genau ein Heartbeat, die Rot-Datei fehlt, das Protokoll enthält die Warnung „git fetch failed“, `<FR_DIENST>/software-wartet` existiert (mit `seit`, `gemeldet=0`), kein `gh`-Aufruf, kein `ls-remote`.
  - Test: `test_ohne_github_ist_der_lauf_gruen_wenn_keine_git_reise_uebrig_ist`
- **AC-20 `git fetch` scheitert, Git-Reise übrig:** Given dasselbe mit einer Reise, die in Git bleibt (`zweitreise`) / Then Exit 0, die Speicher-Reisen sind gebaut, die Git-Reise ist nicht gebaut und nicht rot, **kein** Stempel `veroeffentlichen-erfolg`, **kein** Heartbeat, Merker und Warnung wie in AC-19. Given `FR_SPEICHERREISEN` leer / Then endet derselbe Lauf wie heute mit Exit 1 (`test_ohne_speicherreisen_scheitert_git_fetch_wie_bisher` hält das fest).
  - Test: `test_ohne_github_mit_git_reise_gruen_aber_ohne_heartbeat` und `test_ohne_speicherreisen_scheitert_git_fetch_wie_bisher`
- **AC-21 Rote Speicher-Reise bleibt rot:** Given `git fetch` scheitert und eine Speicher-Reise baut nicht (Deploy-Attrappe Exit 2) / Then Exit 1, Rot-Datei `art=reise` mit dieser Reise, die Nachricht an den Betrieb erst nach der Schwelle (`VF_JETZT`), kein Heartbeat, und der Lauf bricht nicht an einer ungesetzten Variablen ab (kein „unbound variable“ in der Ausgabe).
  - Test: `test_ohne_github_rote_speicher_reise_endet_mit_exit_1`
- **AC-22 Warnung entprellt:** Given `git fetch` scheitert in mehreren Läufen mit `VF_JETZT` = Anfang, Anfang + 1 Stunde, Anfang + `FR_SOFTWARE_WARTET_STUNDEN` Stunden, Anfang + Frist + 1 Stunde (Vorgabe 6) / Then geht in keinem Lauf eine Nachricht an `FR_MELDEN` (Attrappe hält jeden Aufruf fest, keiner wegen `git fetch`); vor Ablauf der Frist steht `gemeldet=0` im Merker und keine Zeile „Software update waiting“ im Protokoll, bei Ablauf genau eine solche Zeile und `gemeldet=1`, danach keine weitere. Given `git fetch` gelingt wieder / Then ist `software-wartet` gelöscht, und eine neue Störung warnt nach einer neuen Frist wieder genau einmal. Ein ungültiger Wert von `FR_SOFTWARE_WARTET_STUNDEN` (Text, leer, negative Zahl) fällt auf 6 zurück.
  - Test: `test_software_wartet_warnt_genau_einmal_je_stoerung_ohne_nachricht`

### Bestehende Tests, Katalog, Dokumentation

- **AC-23 Bestehende Tests angepasst:** In `engine/tests/test_betrieb.py` ist (a) die Fixture `sp` so erweitert, dass `beispielreise` (liegt im Test-Bauordner in Git) zur Umschaltung freigegeben ist, damit die Tests der Stufen 3 und 4 weiter prüfen, was sie prüfen: Hilfsfunktion `freigeben(sp, reise)`, die den Stempel `gleich` im dokumentierten Format (`ergebnis`, `stand` = jetzige Stand-Nummer, `baum` = `git rev-parse HEAD:reisen/<reise>`) in `<FR_DIENST>/vergleich/<reise>.json` schreibt und in jedem Test **nach dem letzten Schreiben vor dem ersten Lauf** aufgerufen wird, wo `beispielreise` zum ersten Mal gebaut werden soll; (b) `test_speicher_reise_wird_ohne_github_veroeffentlicht` auf das neue Verhalten umgestellt: Exit 0 statt „ungleich 0“ (es bleibt eine Git-Reise, `zweitreise`, also weiterhin kein Stempel `veroeffentlichen-erfolg` und kein Heartbeat); (c) kein bestehender Test wird gelöscht oder abgeschwächt, um die Sperre zu umgehen; die Sperre selbst wird nicht mit einer Umgebungsvariable oder einem „Test-Schalter“ abschaltbar.
  - Test: `engine/tests/test_betrieb.py` (bestehend, angepasst); `test_speicher_stufe5.py::test_sperre_hat_keinen_schalter_zum_abschalten` (Stichprobe: die Quelltexte von `veroeffentlichen.sh` und `reisespeicher.py` enthalten kein `VF_`/`FR_`-Merkmal, das die Prüfung überspringt)
- **AC-24 Kein Handschritt nach dem Software-Wechsel (#250):** Given ein Speicher, eine Testreise mit `.gebaut` und eine Instanz mit der Software vor dieser Änderung / When der Software-Wechsel (Deploy dieser Spec) geschieht / Then ist die Testreise weder im Veröffentlichen noch im Schreibweg gesperrt und kein Aufruf von `vergleichslauf.sh`, `neu.py` oder `reisespeicher.py` ist nötig; `docs/betrieb.md` nennt für die schon umgeschaltete Reise keinen Handschritt, und der Abschnitt „Umschaltung einer Reise“ sagt, dass die Sperre nur Reisen ohne `.gebaut` trifft.
  - Test: AC-9, AC-16 und `test_doku_nennt_keinen_handschritt_fuer_umgeschaltete_reisen`
- **AC-25 Dokumentation:** `docs/betrieb.md` enthält den Abschnitt „Umschaltung einer Reise“ mit allen acht Punkten aus „Dokumentation“ (der Test prüft die Überschrift und die Stichwörter: Testreise, kleinste echte Reise, `importieren`, `--ab`, `vergleichslauf.sh`, `FR_SPEICHERREISEN`, `publish_status`, `exportieren`, `zuruecksetzen`, `.gebaut`, `Archiv`, `FR_SOFTWARE_WARTET_STUNDEN`); der Satz „Auskunft, keine Sperre“ steht nirgends mehr in `docs/betrieb.md` und im Kopf von `betrieb/vergleichslauf.sh`; `betrieb/einstellungen.beispiel` und die Einstellungstabelle in `docs/betrieb.md` erklären `FR_SOFTWARE_WARTET_STUNDEN` (der bestehende Test `test_beispiel_einstellungen_sind_vollstaendig` bleibt grün); ADR-0009 enthält die Zeile Stufe 5 im Verlauf und in den Konsequenzen; der Kopfkommentar von `betrieb/veroeffentlichen.sh` beschreibt Sperre, Verhalten bei gescheitertem `git fetch` und `FR_SOFTWARE_WARTET_STUNDEN`.
  - Test: `test_doku_beschreibt_die_umschaltung_einer_reise`, `test_vergleichslauf_kopf_nennt_den_stempel_als_voraussetzung`, `test_adr_0009_hat_die_zeile_stufe_5`
- **AC-26 Module, keine Instanz-Besonderheiten:** `betrieb/deploy.sh` bekommt kein neues Modul (der Modullisten-Test bleibt grün, `reisespeicher.py` steht in allen vier Listen); in `engine/` und `betrieb/` steht kein Name einer echten Reise, kein Pfad und keine Adresse einer Instanz; der Test `engine/tests/test_protokolle_ohne_pfade.py` bleibt grün. Die Tests der einbindenden Reisen-Repos laufen vor dem Vorspulen mit dem Branch (Meldungen und Verhalten von `veroeffentlichen.sh` ändern sich: Anleitung im Reisen-Repo der Instanz).
  - Test: `engine/tests/test_betrieb.py` (Modullisten, bestehend), `engine/tests/test_protokolle_ohne_pfade.py` (bestehend); die Tests der Instanz laufen als Schritt vor dem Vorspulen (Definition of Done)

## Test Plan

Alle in `engine/tests/test_speicher_stufe5.py`, bestehende Tests nur wie in AC-23 angepasst.

- [ ] Test 1: GIVEN Stempel fehlt, kaputt, ungleich, veraltet, gleich WHEN `umschaltung_frei` und `reisespeicher.py umschaltung` THEN Matrix der Gründe und Exit-Codes, nichts wird geschrieben (AC-1 bis AC-6).
- [ ] Test 2: GIVEN gesperrte und freigegebene Reise WHEN der Schreibweg schreibt THEN 503 mit Katalogcode und ohne Vorgang bzw. Erfolg; Ausnahmen Testreise und nur im Speicher; Text in allen Sprachen (AC-7 bis AC-11).
- [ ] Test 3: GIVEN der echte Vergleichslauf WHEN er `gleich` meldet THEN `baum` im Stempel, Veröffentlichen baut ab jetzt (AC-12, AC-15).
- [ ] Test 4: GIVEN Veröffentlichen mit gesperrter, freigegebener, umgeschalteter, neuer Reise und leerer Liste THEN die Fälle von AC-13, AC-14, AC-16, AC-17.
- [ ] Test 5: GIVEN `origin` unerreichbar und Attrappen für `gh` und `ls-remote` THEN grün ohne Git-Reise, grün ohne Heartbeat mit Git-Reise, rot bei roter Speicher-Reise, ohne Liste wie bisher, Warnung genau einmal (AC-18 bis AC-22).
- [ ] Test 6: GIVEN die Dokumentation und die geänderten Kopfkommentare THEN die Stichworte und der Wegfall von „Auskunft, keine Sperre“ (AC-24 bis AC-26).

Die Tests sind den Acceptance Criteria zugeordnet; RED vor dem Bauen (`40-tdd-red`). Die gesamte Suite läuft mit `engine/.venv/bin/python -m pytest -q engine/tests -n auto` und muss ohne echte Reisen grün sein.

## Dateien

| Datei | Änderung | Beschreibung |
|---|---|---|
| `engine/reisespeicher.py` | MODIFY | `umschaltung_frei(reise)`, Befehl `umschaltung` in `main`, Hilfe im Kopf der Datei |
| `engine/schreiben.py` | MODIFY | `vorgang_speicher`/`vorbereiten`: Prüfung vor dem Exportieren, Antwort 503 mit neuem Schlüssel |
| `engine/texte_de.py`, `engine/texte_en.py` | MODIFY | `schreiben.dienst.umschaltung_nicht_freigegeben` |
| `betrieb/veroeffentlichen.sh` | MODIFY | Sperre in `speicher_reisen_lauf`; `git fetch` in `main` ohne Abbruch bei Speicherreisen; `git_reisen_uebrig`, `software_wartet_merken`, `software_wartet_loeschen`; `neu` vor `speicher_rot_melden`; Kopfkommentar |
| `betrieb/vergleichslauf.sh` | MODIFY | `baum` im Stempel, Kopfkommentar |
| `betrieb/einstellungen.beispiel` | MODIFY | `FR_SOFTWARE_WARTET_STUNDEN` erklärt |
| `betrieb/deploy.sh` | PRÜFEN | Modulliste unverändert (kein neues Modul) |
| `betrieb/gemeinsam.sh` | PRÜFEN | `speicherreisen`/`ist_speicherreise` unverändert |
| `docs/betrieb.md` | MODIFY | Abschnitt „Umschaltung einer Reise“, Einstellungstabelle, geänderte Sätze (Vergleichslauf, Veröffentlichen aus dem Speicher) |
| `docs/adr/0009-reisespeicher.md` | MODIFY | Zeile Stufe 5 in „Konsequenzen“ und „Verlauf“ |
| `engine/tests/test_speicher_stufe5.py` | CREATE | alle ACs dieser Spec |
| `engine/tests/test_betrieb.py` | MODIFY (klein) | AC-23: `freigeben`-Hilfe in `sp`, ein Test auf das neue Verhalten bei `git fetch` |
| `engine/tests/test_texte.py` | PRÜFEN | Ausnahmelisten nicht länger |

## Risiken und offene Annahmen

- **Die Sperre darf den Lieferweg nicht ausbremsen.** `veroeffentlichen.sh` baut alle Reisen. Gegenmittel: Die Sperre trifft nur Reisen ohne `.gebaut`, die in Git liegen und in der Liste stehen; sie ist schnell (ein Prozess je gesperrter Reise und Lauf); AC-16 hält die Testreise ausdrücklich frei.
- **Bestehende Tests.** Die Fixture `sp` baut `beispielreise` aus Git und Speicher ohne Stempel; ohne Anpassung (AC-23) würden Tests der Stufen 3 und 4 an der neuen Sperre scheitern. Das ist ein Fehler der Testaufbauten, nicht der Sperre, und wird dort behoben, nie durch einen Schalter in der Software.
- **Wettlauf Schalter und erster Bau.** Zwischen dem Setzen des Schalters und dem ersten Bau kann der Schreibweg schon schreiben (Stempel gültig). Der Stand im Speicher ist dann höher als der verglichene; das gilt nach Entscheidung 3 als gültig, sonst würde der erste Bau gesperrt.
- **Bauordner nicht aktuell beim Vergleich.** Der Vergleich nutzt den lokalen `HEAD`. Hat `origin/main` für die Reise Inhalt, den der Bauordner noch nicht hat (jemand schrieb über den Git-Weg und `git fetch` lief noch nicht), fehlt er im Vergleich und damit nach der Umschaltung im Speicher. Gegenmittel: Vorbedingung „Bauordner aktuell, niemand schreibt über Git in diese Reise“ in der Anleitung (Punkt 1 der Dokumentation); die Software erzwingt es nicht, weil der Vergleich bewusst ohne Netz bleibt.
- **Rückweg.** Ohne Löschen von `.gebaut` (Schritt d) greift die Sperre bei einer zweiten Umschaltung nicht. Das steht in der Anleitung und im Test des Dokumentationsstichworts (`.gebaut`); eine Software-Automatik gibt es dafür nicht (Entscheidung 14).
- **Heartbeat bei GitHub-Ausfall mit übrigen Git-Reisen.** Der Lauf endet grün, pingt aber nicht (Entscheidung 9); die Überwachung schlägt nach ihrer Frist an. Das ist gewollt (Readiness statt Liveness) und verschwindet, sobald alle Reisen im Speicher sind.
- **Warnung nur über Merker und Monitor.** Sichtbar wird ein lang anhaltender GitHub-Ausfall erst durch den Teil-Check im Monitor-Skript der Instanz, der `<FR_DIENST>/software-wartet` liest. Er ist Arbeit im Infra-Repo der Instanz, eigenes Issue dort, vom Tech Lead selbst umgesetzt (nicht per Nachricht abgegeben); bis er läuft, steht die Warnung nur im Protokoll. Solange noch Git-Reisen übrig sind, schlägt zusätzlich der ausbleibende Heartbeat an (Entscheidung 9).
- **Stempel von vor dieser Änderung.** Ohne `baum` gelten sie als veraltet; der Betreiber lässt den Vergleichslauf einmal neu laufen. Für die schon umgeschaltete Testreise ist das ohne Wirkung (`.gebaut`).
- **Variante B ist offen.** Die Instanz hängt für die Software weiter am Reisen-Repo und an GitHub; ein GitHub-Ausfall hält nur die Software-Aktualisierung auf. Das Folge-Issue #454 beschreibt den Umbau.
- **Keine echten Reisen und keine Instanzangaben** in Tests, Beispielen und Protokollen (`CLAUDE.md`).

## Definition of Done

- [ ] Jede Acceptance Criterion durch einen automatischen Test belegt
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests -n auto` grün, ohne echte Reisen, mit beiden Beispielreisen (Wanderung und Reise ohne Pläne)
- [ ] Tests der einbindenden Reisen-Repos mit dem Branch gelaufen, bevor auf `main` vorgespult wird (Meldungen, Verhalten und Stempel ändern sich)
- [ ] Katalogtext in allen Sprachen, `test_texte.py` ohne längere Ausnahmelisten
- [ ] `docs/betrieb.md` (Abschnitt „Umschaltung einer Reise“, Einstellung), Kopfkommentare von `vergleichslauf.sh` und `veroeffentlichen.sh`, ADR-0009 aktuell
- [ ] Kein Handschritt nach dem Software-Wechsel (#250): die schon umgeschaltete Testreise ist nicht gesperrt (AC-9, AC-16, AC-24)
- [ ] Folge-Issues in #350 verlinkt: Variante B (#454, Software ohne Reisen-Repo), Foto-Link im Wissenstext als Bild (#455); Teil-Check `software-wartet` im Monitor der Instanz als Issue im Infra-Repo angelegt und umgesetzt
- [ ] #350 bleibt offen, bis die Reisen der Instanz umgeschaltet sind (Arbeit an der Instanz, #252, AC-27-Messung, Rückspielversuch #347): dieses Issue wird erst geschlossen, wenn das end-to-end erledigt ist; der Software-Anteil ist mit dieser Spec abgeschlossen

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** ADR-0009 (`docs/adr/0009-reisespeicher.md`), wird um Stufe 5 ergänzt (Sperre bei der ersten Umschaltung, Veröffentlichen ohne GitHub für Reisen im Speicher, Variante A).
- **Rationale:** ADR-0009 sieht Stufe 5 als Umschaltung und Rückzug von Git vor. Die Entscheidung berührt Grundformen und Merkmale nicht (ADR-0001, Punkt 8); ein neues ADR ist nicht nötig. Variante B wird mit ihrem Folge-Issue entschieden.

## Known Limitations

- Die Software kommt weiter über das Reisen-Repo und GitHub (Variante A); ein GitHub-Ausfall hält nur die Aktualisierung der Software und der noch in Git liegenden Reisen auf.
- Die Sperre vergleicht nur zum Zeitpunkt der Umschaltung; sie schützt nicht vor Inhalt, der nach dem Vergleich noch in Git landet, solange die Reise nicht in der Liste steht (die Anleitung verlangt, dass niemand mehr über Git schreibt).
- Der Stempel `.gebaut` beendet die Sperre dauerhaft; der Rückweg muss ihn von Hand entfernen.
- Eine blockierte Reise erzeugt keine Nachricht, nur einen Hinweis im Protokoll und die Ablehnung im Schreibweg.
- Umgeschaltet werden echte Reisen nicht in diesem Repo, sondern an der Instanz nach der Anleitung.
- `_git_baum` unterscheidet „kein auflösbares `HEAD`“ (frei, Entscheidung 6) nicht von einem Scheitern von `git` genau zwischen der Prüfung `rev-parse --git-dir` (gelungen) und `rev-parse --verify HEAD` (Validierung, 9.11.2026). Ein solcher Ausfall zwischen zwei aufeinanderfolgenden Aufrufen wäre ein vorübergehender Fehler von `git` selbst; das Risiko ist vernachlässigbar, deshalb kein Umbau.
- In der Fixture `speicherweg` von `engine/tests/test_schreiben.py` wird wie in `sp` (AC-23) ein Stempel „gleich“ für beide Beispielreisen geschrieben, damit die bestehenden Schreibweg-Tests prüfen, was sie prüfen; die Datei fehlt in der Tabelle „Dateien“.

## Changelog

- 2026-11-09: Initial spec created
