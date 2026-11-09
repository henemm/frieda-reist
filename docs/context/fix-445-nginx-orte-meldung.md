# Context: fix-445-nginx-orte-meldung

## Request Summary
Die Meldung „nginx: paths to the connector missing“ (Priorität high, Telegram) feuert bei jedem Prüflauf, weil der neue Ort `/info/` (#436) in der nginx-Einstellung der Instanz fehlt. Sie ist kein Ausfall und der Empfänger kann nichts tun (Regel: MQ nur für Ausfälle). Neue Orte der nginx-Vorlage sollen sich selbst einrichten, die Einstellung auf dem Server einmalig nachgezogen werden.

## Related Files
| File | Relevance |
|------|-----------|
| `betrieb/gemeinsam.sh:144-168` | `wege_pruefen`: curl auf neun Pfade, `fr_melden high` bei fehlendem Kopf `X-Frieda`; hier steht die unerwünschte Meldung (Zeile 167) |
| `betrieb/vorlagen/nginx-konnektor-orte.inc:85-86` | Vorlage mit dem neuen Ort `^~ /info/` |
| `betrieb/nginx.py` | `pruefen` (Soll gegen Ist, Ausgang 0/3/1, installiert nie) und `anwenden` (Root, Sicherung, `nginx -t`, Rollback, läuft nie automatisch) |
| `betrieb/veroeffentlichen.sh:655-676` | `nginx_abgleichen`: nach jedem grünen Lauf, genau eine **normale** Meldung je Abweichung (Merker `nginx-gemeldet`); Vorbild für Teil-Meldung ohne Alarm |
| `betrieb/veroeffentlichen.sh:625-653` | `units_abgleichen`: Vorbild für automatisches Installieren über ein root-eigenes Hilfsprogramm (#260) |
| `betrieb/deploy.sh:123`, `veroeffentlichen.sh:244,555,590` | Aufrufer von `wege_pruefen` |
| `betrieb/einrichten.sh:100-137` | erzeugt Bausteine, nennt die Befehle (Handschritt), sudoers-Hinweise |
| `engine/tests/test_betrieb.py:1010-1030` | Test von `wege_pruefen` mit Attrappe für `FR_MELDEN` |
| `engine/tests/test_nginx.py` | Tests von `nginx.py` |
| `docs/betrieb.md` (Abschnitte „nginx-Bausteine abgleichen (#206)“, „Einheiten abgleichen (#260)“) | Entscheidungen und Begründung |
| `/home/hem/henemm-infra/scripts/monitor.sh:1959` | `check_frieda_seiten`: Vorbild für einen Teil-Check statt Telegram (anderes Repo, selbst erledigen) |

## Existing Patterns
- **Meldeweg-Stufen:** `fr_melden high` = Alarm (Telegram), `fr_melden normal` = Issue ohne Alarm. `nginx_abgleichen` und `units_abgleichen` melden normal, mit Fingerabdruck-Merker, damit nur eine Abweichung genau einmal gemeldet wird.
- **Automatisch installieren geht bei Einheiten (#260):** root-eigenes Hilfsprogramm `/usr/local/sbin/<instanz>-units-installieren` nimmt nur eng erlaubte Änderungen an; einmalig und bewusst installiert.
- **nginx bewusst nicht automatisch (#206, #316):** `docs/betrieb.md`: „Installiert wird nie automatisch: Jede nginx-Zeile wirkt als Root … es gibt keine harmlose Teilmenge wie bei den Einheiten.“
- Der Betriebsbenutzer hat laut `einrichten.sh:134` für `freischalten.sh` bereits `sudo -n nginx -t`, `systemctl reload nginx` und install/test/cat/rm in den Snippets.
- Heartbeat/Meldung nur bei Erfolg bzw. echtem Ausfall (globale Regel „Readiness statt Liveness“, „MQ nur für Ausfälle“).

## Dependencies
- Upstream: `FR_KN_ADRESSE`, `fr_melden`/`FR_MELDEN`, `nginx.py` (Soll aus `einrichten.sh --erzeugen`).
- Downstream: Telegram über Claude MQ (aktuell sechs offene Nachrichten gleichen Inhalts), `monitor.sh` in `henemm-infra`, Tests mit Attrappen, Doku `docs/betrieb.md`.

## Existing Specs
- `docs/specs/fast/nginx-uebergang-206.md`, `docs/specs/betrieb/veroeffentlichen-neustart-242.md` (Kontext zu nginx-Abgleich und Meldeweg).
- Vorherige Kontexte: `docs/context/nginx-uebergang-206.md`.

## Risks & Considerations
- **Zielkonflikt, der den Product Owner betrifft:** Vorhaben 3 („Neue Orte … automatisch einrichten“) widerspricht der dokumentierten Sicherheitsentscheidung „nginx wird nie automatisch installiert“. Alternativen für die Analyse: (a) nur Meldung entschärfen und Handschritt erhalten; (b) automatisches Anwenden über ein root-eigenes Hilfsprogramm, das nur den bekannten Orte-Baustein aus fester Vorlage mit `nginx -t` und Rollback anwendet; (c) Ort-Prüfung bei Software-Wechsel blockieren, bis angewendet. Entscheidung gehört in die Analyse, ggf. per Frage an den PO (Sicherheit, Root-Rechte). Dazu passt die Regel „keine Handarbeit im Betrieb“.
- Vorhaben 1 und 2 (Meldung entfernen, Teil-Check in `monitor.sh`) sind unstrittig; Warnzeile im Protokoll bleibt, aus `fr_melden high` wird nichts oder höchstens `normal` (Issue statt Telegram).
- Bestehende Tests erwarten die Meldung (`test_betrieb.py` ab Zeile 1010): müssen angepasst werden.
- Aktuell laufen die sechs HIGH-Nachrichten weiter auf; nach der Entschärfung als erledigt markieren (`ack.sh`).
- Einstellung auf dem Live-Server einmalig nachziehen: `nginx.py anwenden` braucht Root; Rollback bei `nginx -t`-Fehler ist eingebaut. Nur nach Prüfung durch `nginx.py pruefen` und mit Sicherung.
- Zwei Reisetypen (ADR-0001, Frage 1): Betrieb ist reiseunabhängig; trotzdem nichts Instanzspezifisches in `betrieb/` (Adressen, Pfade kommen aus `einstellungen.env`).

## Analysis

### Type
Bug (Betrieb): Alarm für etwas, das kein Ausfall ist, plus fehlender Selbstablauf beim Software-Wechsel.

### Befund
- Ursache: `wege_pruefen` (`betrieb/gemeinsam.sh:167`) meldet jeden fehlenden Pfad mit `fr_melden high` (Telegram). Seit #436 prüft sie `/info/pruefung.webp`; der installierte Baustein `frieda-reisen-konnektor-orte.inc` kennt `/info/` noch nicht (Handschritt `nginx.py anwenden` nie gelaufen).
- Doppelt gemeldet: `nginx_abgleichen` (`veroeffentlichen.sh:658`) meldet dieselbe Abweichung bereits einmal als normale Meldung (Issue) mit dem Befehl. Die `high`-Meldung aus `wege_pruefen` ist also redundant und verstößt gegen „MQ nur für Ausfälle“.
- Folge für Nutzer: nur die Bilder der Infoseite fehlen; Konnektor und Reiseseiten laufen.
- Der Betriebsbenutzer `hem` hat auf diesem Server passwortloses sudo: `nginx.py anwenden` kann jetzt ohne Handarbeit des PO laufen (Sicherung, `nginx -t`, Rollback eingebaut).

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `betrieb/gemeinsam.sh` | MODIFY | `fr_melden high` aus `wege_pruefen` entfernen; Warnzeile im Protokoll bleibt; Kommentar anpassen |
| `engine/tests/test_betrieb.py` | MODIFY | Test erwartet bisher die Meldung; neu: keine Meldung bei fehlendem Pfad, Warnzeile bleibt |
| `docs/betrieb.md` | MODIFY | Abschnitt zu `wege_pruefen` (nur Warnung, Meldung kommt vom nginx-Abgleich als Issue) |
| `/home/hem/henemm-infra/scripts/monitor.sh` | MODIFY | Teil-Check der Konnektor-Pfade, als Warnung (nicht kritisch), Vorbild `check_frieda_seiten`; eigenes Issue in `henemm-infra` |
| Live-Server | EINMALIG | `nginx.py pruefen`, dann `anwenden` (Sicherung vorher); danach Prüfung grün; sechs MQ-Nachrichten mit `ack.sh` erledigen |
| (offen, siehe Frage) Hilfsprogramm + `veroeffentlichen.sh` | CREATE/MODIFY | Vorhaben 3: neue Orte beim Software-Wechsel automatisch einrichten |

### Scope Assessment
- Vorhaben 1, 2, 4 (unstrittig): 3 Repo-Dateien + `monitor.sh`, ca. +40/-15 Zeilen. Risiko NIEDRIG.
- Vorhaben 3: neues root-eigenes Hilfsprogramm mit Zeilen-Whitelist, ca. +250 Zeilen mit Tests. Risiko HOCH (Root-Rechte über Konfiguration).

### Technical Approach
1. Meldung aus `wege_pruefen` entfernen, Warnzeile bleibt.
2. Teil-Check in `monitor.sh` (Warnung, entprellt wie `check_frieda_seiten`).
3. Einstellung auf dem Server jetzt einmalig nachziehen und prüfen.
4. Vorhaben 3: Zielkonflikt zwischen der dokumentierten Sicherheitsentscheidung „nginx wird nie automatisch installiert“ (#206, #316) und „keine Handarbeit im Betrieb“ (#250). Optionen: (a) Handschritt bleibt, nur vom normalen Issue des nginx-Abgleichs begleitet; (b) root-eigenes Hilfsprogramm, das nur den Orte-Baustein anwendet und nur eine feste Auswahl harmloser Zeilen (`location`, `proxy_pass` auf den lokalen Konnektor, `limit_req` mit bekannter Zone, Fristen) zulässt, mit `nginx -t` und Rollback (wie #260 bei Einheiten); (c) Software-Wechsel blockieren, bis angewendet.

### Dependencies
`FR_KN_ADRESSE`, `fr_melden`, `nginx.py` (`pruefen` 0/3/1, `anwenden`), `veroeffentlichen.sh` (`nginx_abgleichen`), Claude MQ, `monitor.sh` in `henemm-infra`.

### Open Questions
- [x] Vorhaben 3: PO hat (b) gewählt (9.11.2026): Automatik mit enger Whitelist, als eigener Schritt nach 1, 2, 4.
