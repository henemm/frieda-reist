# Adversary Dialog — speicher-stufe5-350
Spec: docs/specs/betrieb/speicher-350-stufe5.md
Datum: 2026-11-09 18:40

## Checkliste
- [x] **AC-1 Ohne Stempel gesperrt:** Given eine Reise aus der Liste, in Git (`HEAD`), im Speicher, ohne `.gebaut`, ohne Stempel / When `umschaltung_frei` / Then `(False, "kein_stempel")`; derselbe Aufruf über `reisespeicher.py umschaltung <reise>` gibt `gesperrt kein_stempel`, Exit 1; die Funktion schreibt nichts (Dateibaum von `FR_DIENST` und Speicher unverändert).
- [x] **AC-2 Stempel nicht „gleich“ sperrt:** Given ein Stempel mit `ergebnis` `unterschied` oder `fehler` (sonst gültig) / Then gesperrt mit `stempel_nicht_gleich`; Given ein kaputter Stempel (leere Datei, kein JSON, JSON-Liste, ohne `ergebnis`) / Then gesperrt mit `stempel_ungueltig`, nie frei.
- [x] **AC-3 Stempel „gleich“ gibt frei:** Given ein von `vergleichslauf.sh` selbst geschriebener Stempel `gleich` (der Test lässt das echte Skript laufen: Git-Reise und Speicher mit gleichem Inhalt) / Then `(True, "")`, Exit 0, Ausgabe `frei`. Ein Stempel nach `--bis N` mit `N` kleiner als der jetzige Stand gilt ebenso.
- [x] **AC-4 Veralteter Stempel sperrt:** Given ein Stempel `gleich` und danach (a) eine Änderung in `reisen/<reise>` per neuem Git-Commit, (b) ein Stempel ohne Feld `baum`, (c) ein Stempel mit `stand` größer als die jetzige Stand-Nummer / Then gesperrt mit `stempel_veraltet`. Given ein Git-Commit nur außerhalb von `reisen/<reise>` (andere Reise, Software) / Then bleibt der Stempel gültig (frei). Given der Speicher hat nach dem Vergleich einen weiteren Vorgang bekommen (Stand höher) / Then frei.
- [x] **AC-5 Ausnahmen:** Given (a) eine Reise nur im Speicher, nicht in Git (`stadtwochenende` ohne Git-Kopie), kein Stempel / Then frei; Given (b) `<FR_DIENST>/reise-stand/<reise>.gebaut` existiert, kein Stempel, die Reise liegt in Git / Then frei, und `reisespeicher.py umschaltung` ist dafür nicht nötig; Given (c) die Reise steht nicht in `FR_SPEICHERREISEN` / Then frei; Given (d) der Bauordner ist kein Git-Repo / Then frei; Given (e) `git` lässt sich nicht starten (leerer `PATH`) bei einem Git-Bauordner / Then gesperrt mit `git_nicht_lesbar`, nie frei.
- [x] **AC-6 Befehl:** Given `reisespeicher.py umschaltung` mit einem ungültigen Reisenamen (`../x`, leer) oder unlesbarer Einstellungsdatei / Then Exit 1 mit `gesperrt stempel_ungueltig` bzw. Exit 2 mit `ERROR: …`; der Befehl ändert weder Stempel noch Speicher.
- [x] **AC-7 Schreibweg lehnt ab:** Given eine gesperrte Reise (AC-1) / When `schreiben.anwenden_extern` ein einfaches Schreibwerkzeug ausführt / Then `(503, antwort)` mit `fehler_code` `schreiben.dienst.umschaltung_nicht_freigegeben`; im Speicher gibt es keinen neuen Vorgang (Stand-Nummer gleich), die temporären Ordner sind gelöscht (kein `frieda-schreiben-*` im `TMPDIR` des Tests), und `anwenden` wurde nicht gestartet (kein Unterprozess, Attrappe).
- [x] **AC-8 Schreibweg nach Freigabe:** Given derselbe Aufbau mit gültigem Stempel `gleich` / Then schreibt dasselbe Werkzeug (Antwort 200, Stand-Nummer um 1 höher). Given der Stempel wird danach durch eine Git-Änderung in `reisen/<reise>` veraltet und kein `.gebaut` existiert / Then lehnt der nächste Schreibvorgang wieder ab.
- [x] **AC-9 Schreibweg: Ausnahmen (Testreise, nur im Speicher):** Given die Reise hat `.gebaut` und keinen Stempel, liegt aber in Git / Then schreibt der Schreibweg ohne Hinweis auf die Sperre (das ist die schon umgeschaltete Testreise, #250). Given eine Reise nur im Speicher / Then schreibt er ebenso. `reise_anlegen` ist unberührt.
- [x] **AC-10 Reihenfolge der Ablehnungen:** Given eine Reise in der Liste und in Git, aber nicht im Speicher / Then bleibt die Antwort `schreiben.dienst.reise_nicht_im_speicher` (unverändert, kein Stempel nötig).
- [x] **AC-11 Text in allen Sprachen:** Given der Schlüssel `schreiben.dienst.umschaltung_nicht_freigegeben` / Then steht er in jeder Sprachdatei aus `texte.SPRACHEN` (Parametrisierung über `SPRACHEN`, damit eine neue Sprache ohne Codeänderung mitgeprüft wird), ist nicht leer, hat in jeder Sprache dieselbe Menge Platzhalter (keine), und `texte_de.py` enthält ihn auf Deutsch mit Umlauten; `engine/tests/test_texte.py` bleibt grün, die Ausnahmelisten werden nicht länger.
- [x] **AC-12 Stempel des Vergleichslaufs trägt den Baum:** Given `vergleichslauf.sh <reise>` / Then enthält der Stempel zusätzlich zu `zeit`, `ergebnis`, `stand`, `git`, `unterschiede` das Feld `baum` gleich `git rev-parse HEAD:reisen/<reise>`; Ausgabe und Exit-Codes sind unverändert (0 gleich, 1 Unterschied, 2 Fehler); der Bauordner bleibt unberührt (`git status --porcelain` leer).
- [x] **AC-13 Veröffentlichen sperrt ohne Stempel:** Given eine Git-Reise in der Liste mit Eintrag im Speicher, ohne `.gebaut`, ohne Stempel, daneben eine zweite Speicher-Reise ohne Git-Kopie / When `veroeffentlichen.sh` läuft / Then wird die erste nicht gebaut (kein Eintrag in `deploy.log`, kein Ordner unter `<FR_DIENST>/bau/reisen/<reise>`, kein `.gebaut`, kein Eintrag in `reise-stand/<reise>.lauf.json`), das Protokoll nennt sie mit dem Grund, die zweite wird gebaut und freigeschaltet, der Lauf endet mit 0, die Rot-Datei fehlt, der Heartbeat wird wie bei jedem grünen Lauf gepingt (die Sperre allein macht den Lauf nicht rot und verhindert den Erfolg nicht).
- [x] **AC-14 Veröffentlichen mit „ungleich“ und „veraltet“:** Given ein Stempel `unterschied`, danach ein Stempel `gleich`, dann ein neuer Git-Commit in `reisen/<reise>` / Then wird die Reise im ersten und im dritten Fall nicht gebaut; im zweiten Fall wird sie gebaut, `.gebaut` trägt Nummer und Software-Kennung, und ein weiterer Lauf ohne neuen Stand baut sie nicht noch einmal (Verhalten der Stufe 3 unverändert).
- [x] **AC-15 Ende-zu-Ende ohne Handstempel:** Given Anfangsvorgang (`importieren … --ab`) und echter Lauf von `betrieb/vergleichslauf.sh <reise>` (Ergebnis `gleich`) / When der Schalter gesetzt ist und `veroeffentlichen.sh` läuft / Then wird gebaut, ohne dass der Test einen Stempel von Hand schreibt; ein anschließender Schreibvorgang über den Schreibweg gelingt (AC-8). Das ist der dokumentierte Weg der Umschaltung.
- [x] **AC-16 Schon umgeschaltete Reise unberührt (#250):** Given die Reise hat `.gebaut` (Stand und Kennung einer früheren Software), liegt in Git und hat keinen Stempel (die Testreise nach dem Deploy dieser Software) / When `veroeffentlichen.sh` läuft, auch nach einem Software-Wechsel (Commit außerhalb von `reisen/`, Pfad „nachziehen“) und mit `--immer` / Then wird sie gebaut bzw. umgestellt wie in Stufe 3, ohne dass der Befehl `umschaltung` aufgerufen wird (der Test ersetzt `FR_PYTHON` durch eine protokollierende Attrappe wie `test_ohne_speicherreisen_bleibt_alles_wie_vorher`) und ohne Hinweis auf eine Sperre; es braucht keinen Handschritt.
- [x] **AC-17 Reise nur im Speicher und leere Liste:** Given eine Speicher-Reise ohne Git-Kopie und ohne Stempel / Then wird sie gebaut (neue Reise). Given `FR_SPEICHERREISEN` leer / Then gibt es keinen Aufruf von `reisespeicher.py` (Attrappe) und nichts ändert sich.
- [x] **AC-18 Keine GitHub-Aufrufe im Speicher-Teil und nur Warnungen sonst:** Given `gh` und `git ls-remote` (über `VF_LSREMOTE`) als Attrappen, die ihren Aufruf festhalten und mit Fehler enden, und `_anstoss.json` in der Ablage / When der Lauf mit Speicher-Reisen läuft / Then ruft der Speicher-Teil weder `gh` noch `ls-remote` noch `git fetch` auf (Reihenfolge wie `test_speicher_teil_laeuft_vor_git_fetch`); ein Fehlschlag von `gh workflow run` (Anstoß der Seite) und von `ls-remote` ändert das Ergebnis des Laufs nicht (Warnung im Protokoll, Exit unverändert), und der Anstoß der Seite erzeugt höchstens eine Nachricht.
- [x] **AC-19 `git fetch` scheitert, keine Git-Reise übrig:** Given `origin` zeigt auf einen Ort, den es nicht gibt, und `FR_SPEICHERREISEN` nennt jede Reise, die in `HEAD` unter `reisen/` liegt (und eine weitere, nur im Speicher) / When `veroeffentlichen.sh` läuft / Then endet der Lauf mit 0, die Speicher-Reisen sind gebaut (Seite trägt die Stand-Nummer aus dem Speicher), `veroeffentlichen-erfolg` ist berührt, genau ein Heartbeat, die Rot-Datei fehlt, das Protokoll enthält die Warnung „git fetch failed“, `<FR_DIENST>/software-wartet` existiert (mit `seit`, `gemeldet=0`), kein `gh`-Aufruf, kein `ls-remote`.
- [x] **AC-20 `git fetch` scheitert, Git-Reise übrig:** Given dasselbe mit einer Reise, die in Git bleibt (`zweitreise`) / Then Exit 0, die Speicher-Reisen sind gebaut, die Git-Reise ist nicht gebaut und nicht rot, **kein** Stempel `veroeffentlichen-erfolg`, **kein** Heartbeat, Merker und Warnung wie in AC-19. Given `FR_SPEICHERREISEN` leer / Then endet derselbe Lauf wie heute mit Exit 1 (`test_ohne_speicherreisen_scheitert_git_fetch_wie_bisher` hält das fest).
- [x] **AC-21 Rote Speicher-Reise bleibt rot:** Given `git fetch` scheitert und eine Speicher-Reise baut nicht (Deploy-Attrappe Exit 2) / Then Exit 1, Rot-Datei `art=reise` mit dieser Reise, die Nachricht an den Betrieb erst nach der Schwelle (`VF_JETZT`), kein Heartbeat, und der Lauf bricht nicht an einer ungesetzten Variablen ab (kein „unbound variable“ in der Ausgabe).
- [x] **AC-22 Warnung entprellt:** Given `git fetch` scheitert in mehreren Läufen mit `VF_JETZT` = Anfang, Anfang + 1 Stunde, Anfang + `FR_SOFTWARE_WARTET_STUNDEN` Stunden, Anfang + Frist + 1 Stunde (Vorgabe 6) / Then geht in keinem Lauf eine Nachricht an `FR_MELDEN` (Attrappe hält jeden Aufruf fest, keiner wegen `git fetch`); vor Ablauf der Frist steht `gemeldet=0` im Merker und keine Zeile „Software update waiting“ im Protokoll, bei Ablauf genau eine solche Zeile und `gemeldet=1`, danach keine weitere. Given `git fetch` gelingt wieder / Then ist `software-wartet` gelöscht, und eine neue Störung warnt nach einer neuen Frist wieder genau einmal. Ein ungültiger Wert von `FR_SOFTWARE_WARTET_STUNDEN` (Text, leer, negative Zahl) fällt auf 6 zurück.
- [x] **AC-23 Bestehende Tests angepasst:** In `engine/tests/test_betrieb.py` ist (a) die Fixture `sp` so erweitert, dass `beispielreise` (liegt im Test-Bauordner in Git) zur Umschaltung freigegeben ist, damit die Tests der Stufen 3 und 4 weiter prüfen, was sie prüfen: Hilfsfunktion `freigeben(sp, reise)`, die den Stempel `gleich` im dokumentierten Format (`ergebnis`, `stand` = jetzige Stand-Nummer, `baum` = `git rev-parse HEAD:reisen/<reise>`) in `<FR_DIENST>/vergleich/<reise>.json` schreibt und in jedem Test **nach dem letzten Schreiben vor dem ersten Lauf** aufgerufen wird, wo `beispielreise` zum ersten Mal gebaut werden soll; (b) `test_speicher_reise_wird_ohne_github_veroeffentlicht` auf das neue Verhalten umgestellt: Exit 0 statt „ungleich 0“ (es bleibt eine Git-Reise, `zweitreise`, also weiterhin kein Stempel `veroeffentlichen-erfolg` und kein Heartbeat); (c) kein bestehender Test wird gelöscht oder abgeschwächt, um die Sperre zu umgehen; die Sperre selbst wird nicht mit einer Umgebungsvariable oder einem „Test-Schalter“ abschaltbar.
- [x] **AC-24 Kein Handschritt nach dem Software-Wechsel (#250):** Given ein Speicher, eine Testreise mit `.gebaut` und eine Instanz mit der Software vor dieser Änderung / When der Software-Wechsel (Deploy dieser Spec) geschieht / Then ist die Testreise weder im Veröffentlichen noch im Schreibweg gesperrt und kein Aufruf von `vergleichslauf.sh`, `neu.py` oder `reisespeicher.py` ist nötig; `docs/betrieb.md` nennt für die schon umgeschaltete Reise keinen Handschritt, und der Abschnitt „Umschaltung einer Reise“ sagt, dass die Sperre nur Reisen ohne `.gebaut` trifft.
- [x] **AC-25 Dokumentation:** `docs/betrieb.md` enthält den Abschnitt „Umschaltung einer Reise“ mit allen acht Punkten aus „Dokumentation“ (der Test prüft die Überschrift und die Stichwörter: Testreise, kleinste echte Reise, `importieren`, `--ab`, `vergleichslauf.sh`, `FR_SPEICHERREISEN`, `publish_status`, `exportieren`, `zuruecksetzen`, `.gebaut`, `Archiv`, `FR_SOFTWARE_WARTET_STUNDEN`); der Satz „Auskunft, keine Sperre“ steht nirgends mehr in `docs/betrieb.md` und im Kopf von `betrieb/vergleichslauf.sh`; `betrieb/einstellungen.beispiel` und die Einstellungstabelle in `docs/betrieb.md` erklären `FR_SOFTWARE_WARTET_STUNDEN` (der bestehende Test `test_beispiel_einstellungen_sind_vollstaendig` bleibt grün); ADR-0009 enthält die Zeile Stufe 5 im Verlauf und in den Konsequenzen; der Kopfkommentar von `betrieb/veroeffentlichen.sh` beschreibt Sperre, Verhalten bei gescheitertem `git fetch` und `FR_SOFTWARE_WARTET_STUNDEN`.
- [x] **AC-26 Module, keine Instanz-Besonderheiten:** `betrieb/deploy.sh` bekommt kein neues Modul (der Modullisten-Test bleibt grün, `reisespeicher.py` steht in allen vier Listen); in `engine/` und `betrieb/` steht kein Name einer echten Reise, kein Pfad und keine Adresse einer Instanz; der Test `engine/tests/test_protokolle_ohne_pfade.py` bleibt grün. Die Tests der einbindenden Reisen-Repos laufen vor dem Vorspulen mit dem Branch (Meldungen und Verhalten von `veroeffentlichen.sh` ändern sich: Anleitung im Reisen-Repo der Instanz).

## Dialog

### Runde 1
**Adversary:** Angriff auf die Sperre: Stempel mit `stand` als String, `baum` leer/fehlend, `ergebnis` fehlt, Stempel `stand` > Speicher, Reise mit `.gebaut` aber ohne Speicher-Eintrag, `.git` als Datei (Worktree), `.git` unlesbar, Programm nicht startbar, Reisename `../x`. Gelesen:
Code reference: engine/reisespeicher.py:676 (_git_baum, fail closed bei Fehler von `rev-parse --git-dir` und `ls-tree`; `.git`.exists() gilt auch für eine Datei).
Code reference: engine/reisespeicher.py:700 (umschaltung_frei: Namensmuster, Liste, .gebaut, Baum, Stempel; `stand` nur `int` und kein `bool`, `baum` abweichend -> stempel_veraltet, fehlendes `ergebnis` -> stempel_ungueltig, nicht gleich -> stempel_nicht_gleich; Reise ohne Speichereintrag -> `_hoechster` None -> veraltet).
Code reference: engine/schreiben.py:5183 (Sperre vor `exportieren` und vor `anwenden`; 503 mit neuem Schlüssel; Prüfung reise_nicht_im_speicher kommt zuerst, AC-10).
Code reference: engine/texte_de.py:873 und Code reference: engine/texte_en.py:872 (Schlüssel in beiden Sprachen, keine Platzhalter, Umlaute).
Code reference: betrieb/vergleichslauf.sh:54 (Stempel trägt `baum`, Exit-Codes unverändert, Bauordner unberührt).
Code reference: betrieb/veroeffentlichen.sh:199 (Prüfaufruf mit stdin /dev/null; nur Exit 1 plus Ausgabe exakt `gesperrt <grund>` ist Sperre, alles andere ERROR + return 1: fail closed; Reise mit `.gebaut` ruft die Prüfung nie auf, #250, AC-16).
Code reference: betrieb/veroeffentlichen.sh:442 (software_wartet_merken: ungültige Stunden -> 6, Basis-10-Präfix gegen die Oktalfalle, fehlende oder kaputte Datei -> seit neu, gemeldet=0; im Fehlerzweig keine `fr_melden`-Aufrufe, nur `echo Warning`; `set -u` sicher dank Vorbelegung der lokalen Variablen).
Abweichungen des Implementierers: (1) stand_git.git statt subprocess: Timeout 10 s, `None` -> git_nicht_lesbar, „nicht im Repo“ über `ls-tree -d` mit leerer Ausgabe sauber unterscheidbar. Akzeptiert. (2) Kein `.git` -> frei (Spec Entscheidung 6); `.git` als Datei zählt als Repo, `.git` vorhanden aber unlesbar -> gesperrt git_nicht_lesbar, nie frei. Akzeptiert. (3) Fail closed in veroeffentlichen.sh bestätigt, richtige Richtung. (4) Code reference: engine/tests/test_schreiben.py:2496 schreibt nur einen zusätzlichen gültigen Stempel im Spec-Format; nichts gelöscht, keine Assertion entfernt, kein Schalter zum Abschalten der Sperre; schwächt nichts ab.
Eigene Testläufe (Speicher-schonend, `-n 2`): test_speicher_stufe5, test_betrieb, test_texte, test_protokolle_ohne_pfade, test_schreiben: 422 passed, 0 failed, 0 übersprungen (docs/artifacts/speicher-stufe5-350/adversary-test-output.txt); Gesamtsuite laut Implementierer 1923 passed.
**Implementierer:** (nicht beteiligt, Kontext-Isolation)

### Runde 2
**Adversary:** Zweite Runde, Randfälle. (a) Inhaltsverlust: Die Sperre trifft genau die Reise ohne `.gebaut` mit Baum im Commit; `.gebaut` entsteht nur nach gelungenem Deploy; spätere Änderungen in `reisen/<reise>` nach der Umschaltung werden nicht mehr geprüft, das ist die Spec-Entscheidung (#250), kein Defekt. (b) `.gebaut` mit gelöschtem Speichereintrag: Code reference: betrieb/veroeffentlichen.sh:193 überspringt die Reise mit Hinweis; der Schreibweg lehnt vorher mit reise_nicht_im_speicher ab (engine/schreiben.py:5183), nichts wird aus leerem Speicher überschrieben. (c) `set -e/-u`: Code reference: betrieb/veroeffentlichen.sh:549 ist Bedingungskontext, Variablen vorbelegt; Text, leer, negativ in FR_SOFTWARE_WARTET_STUNDEN fällt auf 6 (Regex auf Ziffern); kaputte software-wartet-Datei: `seit` nicht numerisch -> neu, kein Abbruch. (d) Meldungen: im Fehlerzweig kein `fr_melden`/`alarm_senden`; `speicher_rot_melden` nur bei roter Speicher-Reise nach Schwelle (AC-21); `fr_melden` Zeile 391 ist der alte Anstoß der Seite, höchstens eine Nachricht (AC-18). (e) Schon umgeschaltete Testreise: `.gebaut` -> keine Prüfung, kein Aufruf von `umschaltung`; `umschaltung_frei` (engine/reisespeicher.py:700) gibt vor jedem Zugriff aufs Repo True, also auch bei kaputtem Repo frei (AC-9/16/24). (f) Docs: „Auskunft, keine Sperre“ nur noch in alten Spec- und Kontextdateien, nicht in docs/betrieb.md oder vergleichslauf.sh; AC-25/26-Tests grün.
Restbefunde nur LOW: F001, F002.
**Implementierer:** (nicht beteiligt, Kontext-Isolation)

### Befunde und Bestätigungen

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:203
  Description: Eine gesperrte Reise erzeugt bei jedem Timer-Lauf nur eine Note-Zeile; ein dauerhaft gesperrter Zustand (auch git_nicht_lesbar) bleibt grün und ohne Warnung im Monitor.
  Spec requirement: AC-13 — Lauf bleibt grün, Protokoll nennt Grund
  Conflict: Kein Konflikt mit der Spec; nur Sichtbarkeit.
  Remediation: Optional später ein Teil-Check im Monitor.

Finding:
  ID: F002
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/reisespeicher.py:676
  Description: Ein Stempel nach `--bis N` mit kleinem N bleibt gültig, auch wenn der Speicher danach andere Inhalte bekam (Spec AC-3/AC-4 verlangt genau das).
  Spec requirement: AC-4 — späterer Vorgang im Speicher macht den Stempel nicht ungültig
  Conflict: Kein Konflikt; dokumentierte Entscheidung.
  Remediation: Keine.

Confirmation:
  AC: AC-1
  Code reference: engine/reisespeicher.py:700
  Evidence: kein Stempel -> (False, kein_stempel); Befehl umschaltung gibt gesperrt, Exit 1, schreibt nichts
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/reisespeicher.py:700
  Evidence: ergebnis ungleich gleich -> stempel_nicht_gleich; kaputt oder ohne ergebnis -> stempel_ungueltig
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: betrieb/vergleichslauf.sh:54
  Evidence: echter Stempel gleich mit baum; Test mit dem echten Skript grün; stand kleiner gleich jetzt frei
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/reisespeicher.py:700
  Evidence: baum-Vergleich, fehlender baum, stand größer jetzt -> stempel_veraltet; Commit außerhalb irrelevant, höherer Stand frei
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/reisespeicher.py:676
  Evidence: Ausnahmen a bis e: nur Speicher, .gebaut, nicht in Liste, kein Repo frei; Programm nicht startbar -> git_nicht_lesbar
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/reisespeicher.py:700
  Evidence: ungültiger Name -> gesperrt stempel_ungueltig; falsche Argumentzahl Exit 2; liest nur
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/schreiben.py:5183
  Evidence: 503 mit neuem Schlüssel vor exportieren und anwenden, temporärer Ordner aufgeräumt (Test grün)
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/schreiben.py:5183
  Evidence: gültiger Stempel -> Schreiben; Stempel veraltet -> wieder 503
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/reisespeicher.py:700
  Evidence: .gebaut und nur-im-Speicher geben vor jedem Zugriff aufs Repo frei
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/schreiben.py:5183
  Evidence: reise_nicht_im_speicher wird in vorbereiten() vor der Sperre geprüft
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/texte_de.py:873
  Evidence: Schlüssel in de und en (engine/texte_en.py:872), keine Platzhalter, test_texte grün
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/texte_en.py:872
  Evidence: englischer Text des Schlüssels schreiben.dienst.umschaltung_nicht_freigegeben, keine Platzhalter, test_texte grün
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: betrieb/vergleichslauf.sh:54
  Evidence: Feld baum, Exit-Codes unverändert
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: betrieb/veroeffentlichen.sh:199
  Evidence: ohne Stempel Note und continue, Lauf grün, Rest wird gebaut
  Status: CONFIRMED

Confirmation:
  AC: AC-14
  Code reference: betrieb/veroeffentlichen.sh:199
  Evidence: unterschied oder veraltet gesperrt, gleich gebaut, .gebaut wie Stufe 3
  Status: CONFIRMED

Confirmation:
  AC: AC-15
  Code reference: betrieb/veroeffentlichen.sh:199
  Evidence: echter Vergleichslauf -> Bau ohne Handstempel (Test grün)
  Status: CONFIRMED

Confirmation:
  AC: AC-16
  Code reference: betrieb/veroeffentlichen.sh:197
  Evidence: Bedingung auf fehlendes .gebaut umgeht die Prüfung bei umgeschalteter Reise, auch mit --immer und Software-Wechsel
  Status: CONFIRMED

Confirmation:
  AC: AC-17
  Code reference: betrieb/veroeffentlichen.sh:193
  Evidence: nur-Speicher-Reise frei, leere Liste kein Aufruf
  Status: CONFIRMED

Confirmation:
  AC: AC-18
  Code reference: betrieb/veroeffentlichen.sh:549
  Evidence: Speicher-Teil vor dem Abruf ohne gh und ls-remote; Fehlschläge nur Warnung
  Status: CONFIRMED

Confirmation:
  AC: AC-19
  Code reference: betrieb/veroeffentlichen.sh:549
  Evidence: Abruf-Fehler: Warnung, Merker, zustellen, erfolg_melden wenn keine Reise im Repo übrig
  Status: CONFIRMED

Confirmation:
  AC: AC-20
  Code reference: betrieb/veroeffentlichen.sh:549
  Evidence: Reise im Repo übrig: return 0 ohne Stempel und Heartbeat; leere Liste -> return 1 wie bisher
  Status: CONFIRMED

Confirmation:
  AC: AC-21
  Code reference: betrieb/veroeffentlichen.sh:549
  Evidence: rote Speicher-Reise -> speicher_rot_melden, return 1, Variablen vorbelegt
  Status: CONFIRMED

Confirmation:
  AC: AC-22
  Code reference: betrieb/veroeffentlichen.sh:442
  Evidence: Warnzeile genau einmal, kein fr_melden, Merker gemeldet 0 oder 1, Löschen bei Erfolg, Ungültiges -> 6
  Status: CONFIRMED

Confirmation:
  AC: AC-23
  Code reference: engine/tests/test_schreiben.py:2496
  Evidence: Fixture schreibt zusätzlich Stempel im Spec-Format; nichts gelöscht oder abgeschwächt, kein Schalter
  Status: CONFIRMED

Confirmation:
  AC: AC-24
  Code reference: betrieb/veroeffentlichen.sh:197
  Evidence: Testreise mit .gebaut nie gesperrt, weder Veröffentlichen noch Schreibweg
  Status: CONFIRMED

Confirmation:
  AC: AC-25
  Code reference: docs/betrieb.md:1
  Evidence: Abschnitt und Stichwörter durch Test belegt (grün); Auskunft-Satz entfernt
  Status: CONFIRMED

Confirmation:
  AC: AC-26
  Code reference: engine/reisespeicher.py:676
  Evidence: keine neuen Module, keine Instanzpfade; test_protokolle_ohne_pfade grün
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)


## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Implementierung hat die Prüfung bestanden: Die Sperre schließt fail closed (Repo nicht lesbar, Stempel kaputt, veraltet, stand als String, baum leer), die umgeschaltete Testreise (.gebaut) wird nie gesperrt, im Fehlerzweig des Abrufs geht keine Nachricht an FR_MELDEN, set -u und set -e halten.
Tests: 422 passed, 0 failed, 0 übersprungen (gezielte Dateien, -n 2); Gesamtsuite laut Implementierer 1923 passed
Edge cases: alle geprüft, kein Defekt (zwei LOW-Hinweise F001, F002)
Regressions: keine gefunden
Checklist: 26/26 points proven

## Geprüfte Dateien

- sha256:0fbd66ed92e652ebe5b550dfc23aa4ca8238727d058740845d60b3e099885d5e  betrieb/vergleichslauf.sh
- sha256:eed5078791c77620649ca7fca4a1d45344c599131fae7c1d3cabac7154ffde67  betrieb/veroeffentlichen.sh
- sha256:397738ae224e0bb386adcdc27d1a4f11c39f30c810fed7c65de783289c140a15  docs/betrieb.md
- sha256:23c188cbb2d4605954d4a854d3999d0964736ebefd7e88a674ed09809f4a7feb  engine/reisespeicher.py
- sha256:a67fef4eda9729787e645cb57e8f7b2e0cd026f5184d4e24318ffc6121801883  engine/schreiben.py
- sha256:32c7cc20ab388106f09f46fcf101000405696bf2071d564fbce9e516c377882f  engine/tests/test_schreiben.py
- sha256:0a6e17421c7780196653e1baa5f2133f20b806bb0a662d306990ff9ced80a429  engine/texte_de.py
- sha256:1a45fb47e64fd83f009d5dd850ebcff775a2d3a88f9def7ba7f7396b14c3d043  engine/texte_en.py

## Prüfbasis

- base: 9787d20e704d87223fab950325cc14aad2833130
- blob:7d2abe4c2de93c0037a7c203310af490ba7b4023  betrieb/vergleichslauf.sh
- blob:e733289ddf1605bd0e84b4fe484a106cd89e7ca1  betrieb/veroeffentlichen.sh
- blob:43e07e526fb0dc1b194aafe2eb6722fda0909ba8  docs/betrieb.md
- blob:7f9a344ecda742635340d221261595fb63194cb4  engine/reisespeicher.py
- blob:d1e4193796583f27621806ffa5a28d4b165d827c  engine/schreiben.py
- blob:21f6089c8e7d37aeb6a8a53b9096dc6b6d41b173  engine/tests/test_schreiben.py
- blob:ee1e38c91a9ed8818994b274b3c01f4f65eda77a  engine/texte_de.py
- blob:ba6a4b8bbdd1636e55f8fe4a6228ec85cd8da780  engine/texte_en.py
