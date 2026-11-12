---
entity_id: meldeweg-nur-ausfaelle-446
type: feature
created: 2026-11-12
updated: 2026-11-12
status: approved
workflow: meldeweg-446
---

# Meldeweg nur für Ausfälle: Regel, Test gegen neue Alarmstellen, Entprellen (#446)

Folgt aus #445 (Product Owner, 9.11.2026). Vorbild für Aufbau: `docs/specs/betrieb/wegepruefung-ohne-alarm-445.md`.

## Approval

- [x] Approved (Tech Lead; Betriebsregel ohne Produktentscheidung, Vorgabe des Product Owners aus #445 und der globalen Anleitung)

## Purpose

Die Stufe `high` von `FR_MELDEN` ist der Alarmweg zum Betreiber (bei der ersten Instanz Telegram über Claude MQ). Sie darf nur für
Ausfälle gelten, bei denen jemand jetzt handeln muss und kann. Bisher stand das nur in der globalen Anleitung; nichts im Code
setzte es durch. `wege_pruefen` schickte deshalb sechs gleiche `high`-Meldungen ohne Ausfall (#445). Zudem meldet
`waechter.sh` einen gescheiterten Lauf oder eine gescheiterte Sicherung bei jedem Lauf erneut, solange die Störung anhält
(täglich, bei Handläufen öfter).

## Bestand (12.11.2026)

| Stelle | Stufe | Ausfall? | Entprellt? |
|---|---|---|---|
| `waechter.sh` „Watchdog failed“ | high | ja: keine neuen Meldungen an Personen, keine Löschung abgelaufener Reisen | nein, je Lauf |
| `waechter.sh` „Account backup failed“ | high | ja: Sicherung der Konten veraltet | nein, je Lauf |
| `waechter.sh` „Trip store backup failed“ | high | ja: Sicherung des Reisespeichers veraltet | nein, je Lauf |
| `veroeffentlichen.sh` `alarm_senden` „Publishing red“ | high | ja: Veröffentlichen seit ≥ 30 min rot | ja, einmal je Rot-Phase (`rot_gemeldet`) |
| `veroeffentlichen.sh` „Publish request failed“, „Tests of the trips repo red“, „Units differ…“, „nginx blocks differ…“ | normal | nein (Issue im Reisen-Repo) | je Stand oder Fingerabdruck; der Meldeweg der Instanz kommentiert ein offenes Issue gleichen Betreffs |
| `waechter.sh` „Watchdog and reminders“ | normal erledigt | nein, Bericht | täglich, wird nicht versendet |
| `engine/`, `werkzeuge/` | – | – | rufen `FR_MELDEN` nicht auf |

## Ziel

1. **Regel in `CLAUDE.md`** als eigener Punkt: `high` nur bei Ausfall (jemand muss jetzt handeln und kann es); alles andere
   `normal` (Issue), Warnzeile im Protokoll oder Teil-Check in `monitor.sh` der Infrastruktur; nie Arbeit an andere Instanzen
   weiterreichen; jeder Alarm einmal je Störung.
2. **Test** listet jede Stelle in `betrieb/` auf, die einen Alarm der Stufe `high` auslöst, und vergleicht sie mit einer
   begründeten Liste. Eine neue Stelle macht ihn rot, bis sie dort mit Begründung steht. Direkte Aufrufe von `FR_MELDEN` gibt
   es nur in den zwei Senderfunktionen (`fr_melden`, `alarm_senden`); `engine/` und `werkzeuge/` rufen ihn nicht auf.
3. **Entprellen im Wächter:** neue Funktion `fr_alarm <schluessel> <betreff> <text>` in `gemeinsam.sh` sendet `high` nur, wenn
   für den Schlüssel noch kein Merker `<FR_DIENST>/alarm-<schluessel>` liegt, und legt ihn nur an, wenn der Meldeweg Erfolg
   meldet. `fr_alarm_ende <schluessel>` löscht den Merker, sobald der Teil wieder gelingt; eine spätere Störung meldet wieder.
   `waechter.sh` nutzt das für seine drei Alarme (Schlüssel `waechter`, `sicherung-konten`, `sicherung-reisen`). Wie lange
   die Störung anhält, zeigt weiter die Überwachung (Stempel `waechter-erfolg`, Teil-Check in `monitor.sh`, Heartbeat der
   Sicherung).

Nicht Teil: die Einstufung der `normal`-Stellen ändert sich nicht (sie gehen als Issue, nicht als Alarm, und sind entprellt);
`alarm_senden` bleibt, wie es ist (schon einmal je Rot-Phase).

## Scope

| File | Change Type | Description |
|------|-------------|-------------|
| `betrieb/gemeinsam.sh` | MODIFY | `fr_alarm`, `fr_alarm_ende` |
| `betrieb/waechter.sh` | MODIFY | drei Alarme über `fr_alarm`, Ende je Teil bei Erfolg |
| `engine/tests/test_betrieb.py` | MODIFY | Bestandstest der Alarmstellen, Tests zum Entprellen |
| `CLAUDE.md` | MODIFY | Regel als eigener Punkt |
| `docs/betrieb.md` | MODIFY | Meldeweg: Stufen, Entprellen, Liste der Alarmstellen |

## Acceptance Criteria

- **AC-1:** Der Bestandstest findet genau die vier begründeten `high`-Stellen (drei im Wächter, Rot-Phase im Veröffentlichen); eine zusätzliche Stelle (`fr_melden high …`, `fr_alarm …` oder ein direkter Aufruf von `"$FR_MELDEN"` außerhalb der Senderfunktionen) lässt ihn scheitern.
- **AC-2:** Scheitert dieselbe Sicherung in zwei Läufen hintereinander, kommt genau ein Alarm.
- **AC-3:** Gelingt die Sicherung danach, ist der Merker weg; scheitert sie später erneut, kommt wieder genau ein Alarm.
- **AC-4:** Kommt ein Alarm nicht an (Meldeweg scheitert), bleibt kein Merker; der nächste Lauf versucht es wieder.
- **AC-5:** Ohne Meldeweg (`FR_MELDEN` leer) wird nichts gesendet und kein Merker angelegt.
- **AC-6:** Die Merker der drei Teile sind unabhängig: Scheitert die Konten-Sicherung weiter und der Lauf des Wächters erstmals, kommt nur der Alarm des Wächters.
- **AC-7:** `CLAUDE.md` und `docs/betrieb.md` beschreiben die Regel.

## Test Plan

- RED: Tests zu AC-1 bis AC-6 in `engine/tests/test_betrieb.py` (AC-2, AC-3, AC-6 scheitern mit heutigem Stand).
- Bestehende Wächter-Tests bleiben grün (erste Störung meldet wie bisher).
- Beide Reisetypen (ADR-0001): Betrieb ist reiseunabhängig.
- Live: nach Auslieferung ein Wächter-Lauf ohne Fehler (Stempel neu, kein Merker).

## Risiken

- Eine lange Störung meldet sich nur einmal: abgedeckt durch Stempel und Teil-Check in `monitor.sh` und den Heartbeat der Sicherung.
- Merker in `<FR_DIENST>` überleben Neustarts; das ist gewollt (einmal je Störung, nicht je Prozess).

## Changelog

- 2026-11-12: Erstfassung.
