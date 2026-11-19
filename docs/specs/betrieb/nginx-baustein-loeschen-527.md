---
entity_id: nginx-baustein-loeschen-527
type: bugfix
created: 2026-11-19
updated: 2026-11-19
status: draft
version: "1.0"
tags: [betrieb, nginx, loeschen, veroeffentlichen, root-helfer]
workflow: nginx-baustein-loeschen-527
---

# Verwaisten nginx-Baustein nach endgültigem Entfernen einer Reise automatisch löschen (#527)

Grundlage: `docs/context/nginx-baustein-loeschen-527.md` (Kontext, Analyse). Auslöser: Adversary-Finding F006 aus `docs/artifacts/alpha-381-loeschen/adversary-dialog.md`. Vorgänger: `docs/specs/betrieb/loeschen-381.md` (Löschen von Reise und Konto, Löschprotokoll), `docs/specs/betrieb/dienstrechte-552.md` (Root nur über feste Helfer, Helfer `nginx-reise-installieren` mit `--entfernen`), `docs/specs/betrieb/veroeffentlichen-eigener-dienst-624.md` (Veröffentlichen als eigener Dienst).

## Approval

- [ ] Approved

## Purpose

Wird eine Reise endgültig entfernt (#381), räumt der Wächter ihre Seiten, Stempel und den Eintrag in `seiten.json` ab, aber der nginx-Baustein `<FR_NGINX_SNIPPETS>/<instanz>-<reise>.conf` bleibt stehen und liefert für den alten Link 404. Das ist ein Handschritt nach dem Betrieb und widerspricht #250. Künftig entfernt der nächste Lauf von Veröffentlichen den Baustein über das vorhandene Root-Hilfsprogramm (Sicherung, `nginx -t`, Rückweg, Reload), ohne dass jemand etwas tun muss.

## Entscheidungen (Tech Lead, nicht offen)

1. **Aufruf aus `betrieb/veroeffentlichen.sh`**, nicht aus dem Wächter. Der Wächterdienst bekommt keine Root-Rechte (Rechtetrennung, #552). Veröffentlichen läuft als eigener Dienst ohne `NoNewPrivileges` (`betrieb/vorlagen/veroeffentlichen.service`, Kommentar im Kopf; seit #624 startet eine Path-Einheit den Dienst, nicht mehr der Schreibweg als Kindprozess) und hat `root_geht` sowie das Muster „ohne Root merken, mit Root nachholen“ (#465, #494).
2. **Quelle ist allein das Löschprotokoll** (endgültig entfernte Reisen), nicht `vorgemerkt`. In der Schonfrist kann die Reise zurückgeholt werden und behält dann ihren Link. Dazu kommt der neue Befehl `engine/konten.py entfernt` (eine Reise je Zeile, sortiert, liest nur). `vorgemerkt` bleibt unverändert.
3. **Der Zustand „Baustein-Datei existiert noch“ ist die Vormerkung.** Keine eigene Ausstehend-Datei. Vor jedem Aufruf von `sudo` prüft das Skript ohne Root mit `[ -e <FR_NGINX_SNIPPETS>/<instanz>-<reise>.conf ]` (Bausteine sind 0640 root:<Gruppe>, der Ordner ist lesbar; `betrieb/nginx.py` liest sie ebenfalls ohne sudo). Das Löschprotokoll wächst dauerhaft; so wird `sudo` (jeder Aufruf steht im Journal) nur bei echter Arbeit aufgerufen.
4. **Neue Funktion `entfernte_bausteine`** direkt nach `vorgemerkte_entfernen`, an beiden Aufrufstellen (Speicherteil und Git-Teil des Laufs). Je Reise: Namensmuster wie in `freischalten.sh` und im Helfer (`^[a-z0-9][a-z0-9-]{1,39}$`, also zwei bis 40 Zeichen; das Muster von `vorgemerkte_entfernen` ist weiter, Reisen außerhalb des Helfermusters werden still übersprungen), Existenzprüfung ohne Root, dann `root_geht`, dann `printf '%s\n' "$r" | $FR_SUDO $HELFER --entfernen`. Helfer-Pfad wie in `freischalten.sh`: `${FR_NGINX_REISE_HELFER:-/usr/local/sbin/$FR_INSTANZ-nginx-reise-installieren}`; fehlt er (nicht ausführbar), Warnzeile, kein Abbruch. `FR_SUDO` ist `sudo -n` (Vorgabe) oder leer; leer heißt ohne sudo (Tests).
5. **Ausgänge des Helfers:** 0 = „Block removed: <reise>“; 2 = nichts da (Wettlauf), still; 3 bis 6 oder anderer Wert = Warnzeile mit Grund (nginx lehnt ab, Reload gescheitert, Rückweg gescheitert), der nächste Lauf versucht es erneut. Der Helfer stellt bei 4 und 6 den alten Stand wieder her und lädt nie einen Stand, den `nginx -t` ablehnt.
6. **Kein Ausfall, kein `high`-Alarm.** Die Seite liefert ohnehin 404, nichts ist kaputt, es liegt nur eine tote Regel. Nur Warnzeile im Protokoll; keine neue Stelle in `ALARMSTELLEN`. Der Lauf wird weder abgebrochen noch rot (`entfernte_bausteine` gibt immer 0 zurück).
7. **Ist die Liste nicht lesbar** (`konten.py entfernt` scheitert): Warnzeile, kein Abbruch. Der Bau hängt davon nicht ab; das Fail-closed für das Nichtbauen entfernter Reisen leistet schon `vorgemerkte_entfernen` (mit eigener Liste aus `vorgemerkt`).
8. **Ohne Datenbank der Konten** (weder `$FR_KONTEN/konten.db` noch `$FR_ABLAGE/_konten/konten.db`): nichts zu tun, wie bei `vorgemerkte_entfernen`.
9. **Bestehende Instanzen:** Verwaiste Bausteine bereits früher entfernter Reisen stehen im Löschprotokoll und werden beim ersten Lauf nach dem Software-Wechsel mit erfasst. Kein Handschritt, keine Umstellung in `neu.py nachziehen` nötig (kein Format der Reisedaten ändert sich).

## Prüfung gegen #624 und #552 (Annahmen)

- **Rechte im Lauf:** `veroeffentlichen.service` hat kein `NoNewPrivileges`; die sudoers-Regel der Instanz erlaubt den Helfer ohne Einschränkung der Argumente (`betrieb/einrichten.sh`, #552), also auch `--entfernen`. `root_geht` prüft `sudo -l` und gelingt im Dienst. Der Ansatz trägt, ohne Änderung an sudoers, `einrichten.sh` oder den Einheiten.
- **Lauf ohne Root (Übergang oder Start aus dem Schreibweg mit `NoNewPrivileges`, falls die Path-Einheit der Instanz noch nicht aktiv ist):** `root_geht` ist falsch, das Skript schreibt eine Hinweiszeile und tut nichts; die Datei bleibt liegen und ist damit die Vormerkung. Der nächste Lauf des Timers (alle fünf Minuten) holt es nach. Das ist das bestehende Muster aus #465 und #494, nur ohne eigene Vormerkdatei.
- **Annahme:** Bis zum Eintreffen des Wächters-Laufs steht der Eintrag im Löschprotokoll erst nach `loeschung_abschliessen`; erst dann (nicht in der Schonfrist) greift diese Funktion.
- **Annahme:** Eine endgültig entfernte Reise taucht nie wieder als gleichnamige neue Reise auf, weil `reise_vorgemerkt` auch für das Löschprotokoll wahr ist (#381, Punkt 12). Deshalb kann ein späteres Freischalten desselben Namens den Baustein nicht wieder anlegen und mit dem Entfernen kollidieren.

## Source

- **Files:** `betrieb/veroeffentlichen.sh`, `engine/konten.py`, `engine/waechter.py` (nur Docstring), `docs/betrieb.md`, `docs/waechter.md`
- **Identifier:** `entfernte_bausteine` (neu), `konten.py entfernt` (neu), `vorgemerkte_entfernen`, `root_geht`, `loeschungen_ausfuehren`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `betrieb/vorlagen/nginx-reise-installieren.py` (`--entfernen`, Ausgänge 0 bis 6) | Root-Helfer | entfernt den Baustein mit Sperre, Sicherung, `nginx -t`, Rückweg, Reload; unverändert |
| `betrieb/veroeffentlichen.sh` (`root_geht`, `vorgemerkte_entfernen`) | Skript | Ort des Aufrufs, Muster „ohne Root später nachholen“ |
| `betrieb/vorlagen/veroeffentlichen.service` / `.path` | Vorlage | Dienst ohne `NoNewPrivileges`, Auslösung (#624); unverändert |
| `engine/konten.py` (`loeschprotokoll()`) | Modul | Quelle der entfernten Reisen; neuer Befehl `entfernt` |
| sudoers-Regel der Instanz (`einrichten.sh`, #552) | Betrieb | erlaubt den Helfer; unverändert |
| `betrieb/freischalten.sh` | Skript | Vorlage für Helferpfad, Namensmuster und Ausgangsunterscheidung; unverändert |
| nginx, sudo | Fremd | Reload, Rechte |
| Reisen-Repo der Instanz | Fremd | neue Protokollzeilen in `veroeffentlichen.sh`: dessen Tests laufen vor dem Vorspulen mit dem Branch (CLAUDE.md) |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/konten.py` | MODIFY | Befehl `entfernt` (Löschprotokoll, je Zeile eine Reise); Befehlsliste im Kopf ergänzen |
| `betrieb/veroeffentlichen.sh` | MODIFY | Funktion `entfernte_bausteine`, Aufruf direkt nach `vorgemerkte_entfernen` an beiden Stellen |
| `engine/waechter.py` | MODIFY | Docstring von `loeschungen_ausfuehren`: Baustein entfernt der nächste Lauf von Veröffentlichen |
| `docs/betrieb.md`, `docs/waechter.md` | MODIFY | Ablauf beim endgültigen Entfernen nachziehen |
| `engine/tests/test_nginx_baustein_loeschen_527.py` | CREATE | Tests für den Aufruf aus dem Veröffentlichen mit Attrappe des Helfers |
| `engine/tests/test_konten*.py` | MODIFY | Test für `konten.py entfernt` |

Keine Änderung: Helfer, `einrichten.sh`, sudoers, Einheiten, `deploy.sh`, `ALARMSTELLEN`, Wächter-Dienst.

### Nicht im Scope

- Root-Rechte für den Wächter oder `sudo` aus `loeschungen_ausfuehren`.
- Entfernen von Bausteinen von Reisen, die nur vorgemerkt sind (Schonfrist).
- Aufräumen von Bausteinen, die zu keiner Reise im Löschprotokoll gehören (z. B. von Hand gelöschte Reisen des alten Git-Wegs); das bleibt Sache des Betreibers.
- Änderung am Helfer, an `nginx.py pruefen` oder an den sudoers-Regeln.
- Neue sichtbare Texte (Protokollzeilen im Skript folgen dem bestehenden Stil von `veroeffentlichen.sh`; keine Seite, kein Konnektor, keine Mail).

### Estimated Changes

- Files: 6 bis 8 (2 Code, Rest Doku und Tests)
- LoC: +120/-5 (Code etwa 40, Tests etwa 70, Doku etwa 10)
- Risiko mittel: nginx-Reload betrifft alle Reisen der Instanz; der Helfer sichert, prüft und rollt zurück, das Risiko liegt nur im richtigen Aufruf (richtige Reise, nur Löschprotokoll).

## Implementation Details

`konten.py entfernt` gibt `loeschprotokoll()` Zeile für Zeile aus (ohne Datenbank: keine Ausgabe, Ausgang 0, legt keine Datenbank an).

`entfernte_bausteine` in `veroeffentlichen.sh` (Ablauf, kein Code hier):

1. Ohne Kontendatenbank zurück (Entscheidung 8).
2. Liste mit `"$FR_PYTHON" .../engine/konten.py entfernt` lesen; Fehler: Warnzeile, Rückgabe 0.
3. Je Reise: Muster prüfen (sonst überspringen); Baustein `${FR_NGINX_SNIPPETS:-/etc/nginx/snippets}/$FR_INSTANZ-$r.conf` fehlt: weiter (kein `sudo`).
4. Datei da, aber `root_geht` falsch: eine Hinweiszeile („Note: nginx block of $r not removed in this run (no root rights); the next timer run does it.“), weiter.
5. Helfer prüfen (`-x`), sonst Warnzeile. Dann `printf '%s\n' "$r" | ${FR_SUDO-sudo -n} "$HELFER" --entfernen` mit Fehlerausgabe in eine Temp-Datei, Ausgang 0: „Block removed: $r“; 2: still; sonst „Warning: nginx block of $r not removed (exit N), the next run tries again: <Grund>“.

Testbarkeit über die vorhandenen Umgebungswerte `FR_SUDO` (leer), `FR_NGINX_REISE_HELFER` (Attrappe, die ihre Eingabe aufzeichnet und die Datei löscht oder mit Ausgang N endet), `FR_NGINX_SNIPPETS` und `FR_INSTANZ` (tmp), Kontendatenbank mit Löschprotokoll und Schonfrist-Eintrag über die Funktionen aus `konten.py`.

## Test Plan

### Automated Tests (TDD RED)

- [ ] Test 1 (AC-1): GIVEN eine Kontendatenbank mit einer Reise im Löschprotokoll und einer in der Schonfrist WHEN `konten.py entfernt` läuft THEN steht nur die Reise des Löschprotokolls in der Ausgabe; GIVEN keine Datenbank THEN keine Ausgabe und Ausgang 0
- [ ] Test 2 (AC-2): GIVEN Baustein-Dateien für die entfernte und die Schonfrist-Reise und eine Helfer-Attrappe WHEN `veroeffentlichen.sh` den Schritt ausführt THEN ruft die Attrappe `--entfernen` genau einmal mit dem Namen der entfernten Reise auf stdin auf, die Datei der Schonfrist-Reise bleibt, die Zeile „Block removed“ steht im Protokoll
- [ ] Test 3 (AC-3): GIVEN eine entfernte Reise ohne Baustein-Datei WHEN der Schritt läuft THEN wird die Attrappe nicht aufgerufen (auch kein `sudo`)
- [ ] Test 4 (AC-4): GIVEN `FR_SUDO` verweigert Root (Attrappe, die bei `-l` scheitert) WHEN der Schritt läuft THEN kein Aufruf des Helfers, Hinweiszeile, Datei bleibt, der Lauf endet erfolgreich; im nächsten Lauf mit Root wird sie entfernt
- [ ] Test 5 (AC-5): GIVEN die Attrappe endet mit den Ausgängen 3, 4, 5 und 6 WHEN der Schritt läuft THEN steht je eine Warnzeile mit Ausgang und Grund im Protokoll, der Schritt gibt 0 zurück, der Bau läuft weiter, es wird keine Meldung auf der Stufe `high` abgesetzt; ein zweiter Lauf versucht es erneut
- [ ] Test 6 (AC-5): GIVEN die Attrappe endet mit Ausgang 2 WHEN der Schritt läuft THEN keine Warnzeile
- [ ] Test 7 (AC-6): GIVEN ein Name im Löschprotokoll außerhalb des Musters (Großbuchstaben, Schrägstrich, `..`, ein Zeichen, 41 Zeichen) WHEN der Schritt läuft THEN wird er übersprungen und der Helfer nicht aufgerufen
- [ ] Test 8 (AC-7): GIVEN `konten.py entfernt` scheitert WHEN der Schritt läuft THEN Warnzeile, kein Abbruch, kein Aufruf des Helfers
- [ ] Test 9 (AC-8): GIVEN `veroeffentlichen.sh` WHEN der Skripttext geprüft wird THEN steht `entfernte_bausteine` an beiden Aufrufstellen direkt nach `vorgemerkte_entfernen`
- [ ] Test 10 (AC-9): GIVEN `docs/betrieb.md`, `docs/waechter.md` und der Docstring von `loeschungen_ausfuehren` WHEN sie gelesen werden THEN sagen sie, dass der nächste Lauf von Veröffentlichen den Baustein entfernt, und „Baustein bleibt (Root-Rechte)“ steht nirgends mehr
- [ ] Test 11 (AC-10): GIVEN `ALARMSTELLEN` in `test_betrieb.py` WHEN die Tests laufen THEN ist die Liste unverändert grün (keine neue `high`-Stelle), ebenso `test_nginx_reise_helfer.py` und die Tests zu #381

Beide Beispielreisen: Die Tests nutzen erfundene Reisekennungen (zum Beispiel `beispielreise`, `stadtwochenende`) nur als Namen im Löschprotokoll; keine echten Reisen, keine Pfade, Adressen oder Zugangsdaten.

## Expected Behavior

- **Input:** Eine Reise steht im Löschprotokoll, ihr Baustein `<instanz>-<reise>.conf` liegt noch im Snippet-Ordner.
- **Output:** Der nächste Lauf von Veröffentlichen mit Root-Rechten entfernt den Baustein über den Helfer, nginx ist geladen; Protokollzeile „Block removed: <reise>“.
- **Side effects:** Ein Reload von nginx je entfernte Reise (gesichert und mit Rückweg). Ohne Root-Rechte im Lauf: Hinweiszeile, der Timer holt es nach.

## Known Limitations

- Ohne Root-Rechte im Lauf wartet der Baustein bis zum nächsten Timer-Lauf (bis zu fünf Minuten); die Seite liefert in der Zeit weiter 404 wie bisher.
- Scheitert der Helfer dauerhaft (zum Beispiel nginx-Konfiguration der Instanz kaputt), erscheint bei jedem Lauf dieselbe Warnzeile, aber kein Alarm; das ist gewollt, weil nichts ausgefallen ist. Ein kaputtes nginx fiele ohnehin über den Betrieb auf.
- Bausteine von Reisen, die nie im Löschprotokoll standen, bleiben Sache des Betreibers.

## Acceptance Criteria

- **AC-1:** Given Reisen im Löschprotokoll und in der Schonfrist / When `konten.py entfernt` läuft / Then listet es nur die Reisen des Löschprotokolls, eine je Zeile, ohne Datenbank nichts. Test: 1.
- **AC-2:** Given eine entfernte Reise mit liegendem Baustein und Root-Rechten / When Veröffentlichen läuft / Then wird der Helfer mit `--entfernen` und dem Reisenamen auf stdin aufgerufen und die Zeile „Block removed“ steht im Protokoll; der Baustein einer Reise in der Schonfrist bleibt. Test: 2.
- **AC-3:** Given eine entfernte Reise ohne Baustein-Datei / When Veröffentlichen läuft / Then wird weder der Helfer noch `sudo` aufgerufen. Test: 3.
- **AC-4:** Given ein Lauf ohne Root-Rechte / When der Schritt läuft / Then wird nichts verändert, eine Hinweiszeile steht im Protokoll, der Lauf bleibt grün und der nächste Lauf mit Root holt es nach. Test: 4.
- **AC-5:** Given der Helfer endet mit Ausgang 3 bis 6 / When der Schritt läuft / Then steht eine Warnzeile mit Grund im Protokoll, der Bau läuft weiter, es entsteht kein `high`-Alarm, der nächste Lauf versucht es erneut; bei Ausgang 2 bleibt es still. Test: 5, 6.
- **AC-6:** Given ein ungültiger Reisename im Löschprotokoll / When der Schritt läuft / Then wird er übersprungen und der Helfer nicht aufgerufen. Test: 7.
- **AC-7:** Given die Liste ist nicht lesbar / When der Schritt läuft / Then Warnzeile ohne Abbruch des Laufs. Test: 8.
- **AC-8:** Given der Skripttext / When er geprüft wird / Then steht der Schritt an beiden Aufrufstellen direkt nach `vorgemerkte_entfernen`. Test: 9.
- **AC-9:** Given Doku und Docstring / When sie gelesen werden / Then beschreiben sie den neuen Ablauf, und der alte Satz „Baustein bleibt (Root-Rechte)“ fehlt. Test: 10.
- **AC-10:** Given die bestehenden Tests / When `engine/.venv/bin/python -m pytest -q engine/tests -n 3` läuft / Then ist alles grün, `ALARMSTELLEN` ist unverändert, `test_nginx_reise_helfer.py` und die Tests zu #381 bestehen. Test: 11.
- **AC-11:** (Instanz, Teil von „fertig“) Given die Software ist auf der Instanz / When eine eigene Testreise endgültig entfernt wird / Then ist ihr Baustein nach dem nächsten Lauf von Veröffentlichen weg, `nginx -t` ist grün und der Reload hat stattgefunden. Ausnahme mit Begründung: braucht nginx und Root auf dem echten Server und läuft nicht in CI; der Nachweis steht ohne Serverpfade im Issue #527 (Uhrzeiten mit Zeitzone).

## Definition of Done

- [ ] AC-1 bis AC-10 sind durch Tests belegt; AC-11 durch den Nachweis auf der Instanz (vorhandene eigene Testreise, danach nichts zurückzustellen, weil entfernt; Konto nicht zumüllen).
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests -n 3` ist ohne echte Reisen grün; die Tests der einbindenden Instanzen laufen vor dem Vorspulen mit diesem Stand (CLAUDE.md, Regel zu Meldungstexten).
- [ ] Prüfstelle ADR-0001 im Pull Request beantwortet (siehe unten).
- [ ] #527 mit Nachweis kommentiert und erst nach Auslieferung auf `main` und Entfernen eines echten Testfalls geschlossen.

## Prüfstelle ADR-0001 (kurz)

Betrieb, nicht Kern: Keine neue Grundform, keine Art, kein Merkmal, keine Änderung der Reise-Ontologie (Fragen zu Grundformen, Arten und Merkmalen: nicht berührt). Nichts Reisespezifisches in der Engine und nichts Instanzspezifisches in `betrieb/` (Instanzname, Ordner, Helferpfad und Sudo-Befehl kommen aus den Einstellungen der Instanz). Beide Reisetypen: reiseunabhängig, die Tests nutzen nur Kennungen als Namen im Löschprotokoll, weder Wanderung noch Wochenende werden vorausgesetzt. Keine eigene KI, keine neue Fremdbibliothek, keine Sprache im Code (keine neuen sichtbaren Texte; Protokollzeilen folgen dem bestehenden Stil des Skripts). Root bleibt bei den festen Helfern (ADR der Rechte, #552). Kein Widerspruch zum Kern.

## Risiken

- **Falsche Reise entfernt:** Quelle ist ausschließlich das Löschprotokoll; Schonfrist-Reisen stehen nicht darin (Test 2). Namensmuster vor dem Aufruf, der Helfer prüft ein zweites Mal.
- **Reload für alle Reisen der Instanz:** Der Helfer sichert, prüft mit `nginx -t`, rollt zurück und lädt nie einen abgelehnten Stand; nur eine Reise je Aufruf.
- **Dauerhafter Fehler des Helfers:** wiederkehrende Warnzeile, kein Alarm (Entscheidung 6); die Seite ist ohnehin 404.
- **Wachsendes Löschprotokoll:** Existenzprüfung ohne `sudo` vor jedem Aufruf (Entscheidung 3).
- **Reisen-Repo der Instanz:** neue Protokollzeilen; dessen Tests laufen vor dem Vorspulen mit dem Branch.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine neue
- **Rationale:** Anwendung bestehender Muster (Root nur über feste Helfer, #552; ohne Root vormerken und mit Root nachholen, #465 und #494; Löschprotokoll, #381). Keine Architekturgrenze aus den ADRs 0001 bis 0011 wird berührt.

## Changelog

- 2026-11-19: Initial spec created (Issue #527; Aufruf des vorhandenen Helfers `--entfernen` aus Veröffentlichen, Quelle Löschprotokoll über `konten.py entfernt`)
