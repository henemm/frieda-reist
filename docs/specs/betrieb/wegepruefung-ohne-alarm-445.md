---
entity_id: wegepruefung-ohne-alarm-445
type: bugfix
created: 2026-11-09
updated: 2026-11-09
status: draft
workflow: fix-445-nginx-orte-meldung
---

# Wegeprüfung meldet kein Alarm mehr; Server-Einstellung wird einmal nachgezogen (#445)

Grundlage: `docs/context/fix-445-nginx-orte-meldung.md` (Kontext und Analyse). Vorbild für Aufbau: `docs/specs/betrieb/veroeffentlichen-neustart-242.md`.

## Approval

- [ ] Approved

## Purpose

`wege_pruefen` (`betrieb/gemeinsam.sh`) schickt bei jedem Lauf, in dem ein Pfad des Konnektors nicht über nginx ankommt, eine Meldung der Stufe `high` (Telegram). Seit #436 fehlt der Ort `/info/` in der nginx-Einstellung der Instanz; die Meldung feuert seitdem bei jedem Lauf (sechs offene Nachrichten). Sie ist kein Ausfall (nur Bilder der Infoseite fehlen), der Empfänger kann nichts tun, und dieselbe Abweichung meldet `nginx_abgleichen` (`veroeffentlichen.sh`) bereits einmal als normale Meldung (Issue). Die `high`-Meldung widerspricht der Regel „Claude MQ nur für Ausfälle“.

## Ziel

1. `wege_pruefen` meldet nichts mehr über `fr_melden`; die Warnzeile im Protokoll bleibt.
2. Fehlende Konnektor-Pfade werden stattdessen als Teil-Check (Warnung, nicht kritisch) von `henemm-infra/scripts/monitor.sh` überwacht.
3. Die nginx-Einstellung der Instanz wird einmalig auf den Stand der Vorlage gebracht; danach ist die Prüfung grün.

Nicht Teil dieser Spec: die Automatik, die neue Orte beim Software-Wechsel selbst einrichtet (Entscheidung des Product Owners 9.11.2026: Variante „root-eigenes Hilfsprogramm mit enger Whitelist“, als eigener Schritt danach, eigenes Issue und eigene Spec; sie widerspricht sonst der Entscheidung aus #206/#316 „nginx nie automatisch“ und braucht eine eigene Sicherheitsprüfung).

## Source

- **Files:** `betrieb/gemeinsam.sh`, `engine/tests/test_betrieb.py`, `docs/betrieb.md`, `henemm-infra/scripts/monitor.sh` (anderes Repo, eigenes Issue dort)
- **Identifier:** `wege_pruefen`, `check_frieda_seiten` (Vorbild)

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `betrieb/veroeffentlichen.sh` `nginx_abgleichen` | Funktion | Meldet Abweichung der nginx-Bausteine einmal als normale Meldung (Merker `nginx-gemeldet`); bleibt unverändert |
| `betrieb/nginx.py` | Programm | `pruefen` (0/3/1) und `anwenden` (Sicherung, `nginx -t`, Rollback) für den Live-Schritt |
| `henemm-infra/scripts/monitor.sh` | Skript | Teil-Check, Warnungen über `NON_CRITICAL_PREFIXES` |
| `fr_melden` / `FR_MELDEN` | Funktion | bleibt für andere Aufrufer; `wege_pruefen` ruft sie nicht mehr |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `betrieb/gemeinsam.sh` | MODIFY | `fr_melden high` aus `wege_pruefen` entfernen; Kommentar nennt, dass die Meldung der nginx-Abgleich und der Teil-Check in `monitor.sh` übernehmen |
| `engine/tests/test_betrieb.py` | MODIFY | Test `test_wegepruefung_wartet_bei_429_…`: bei fehlendem Pfad Warnzeile ja, Meldedatei nicht angelegt |
| `docs/betrieb.md` | MODIFY | Abschnitt zur Wegeprüfung: nur Warnung; Meldung kommt vom nginx-Abgleich (Issue), Überwachung vom Teil-Check |
| `henemm-infra/scripts/monitor.sh` | MODIFY | Neuer Teil-Check der Konnektor-Pfade (Warnung), eigenes Issue in `henemm-infra` |
| Live-Server | EINMALIG | `nginx.py pruefen`, bei Abweichung Sicherung, `anwenden`, erneut `pruefen`; die sechs offenen MQ-Nachrichten mit `ack.sh` erledigen |

### Estimated Changes

ca. +40/−15 Zeilen in drei Repo-Dateien und `monitor.sh`. Risiko niedrig.

## Acceptance Criteria

- **AC-1:** Fehlt mindestens ein Konnektor-Pfad, gibt `wege_pruefen` die Warnzeile samt Pfadliste im Protokoll aus (Text unverändert) und ruft `FR_MELDEN` nicht auf.
- **AC-2:** Sind alle Pfade da (auch nach 429 mit Wiederholung), bleibt die Ausgabe leer und es gibt keine Meldung (Verhalten unverändert).
- **AC-3:** `wege_pruefen` endet unverändert mit Ausgang 0; kein Aufrufer (`deploy.sh`, `veroeffentlichen.sh`) bricht durch die Änderung.
- **AC-4:** `monitor.sh` prüft die Konnektor-Pfade (Kopf `X-Frieda`) als Warnung; ein fehlender Pfad löst keinen kritischen Alarm aus und entprellt wie `check_frieda_seiten`.
- **AC-5:** Auf dem Live-Server liefert `nginx.py pruefen` nach dem Nachziehen Ausgang 0, `https://frieda.henemm.com/info/pruefung.webp` trägt den Kopf `X-Frieda`, `nginx -t` ist grün; eine Sicherung der alten Einstellung liegt vor.
- **AC-6:** Die sechs offenen MQ-Nachrichten sind erledigt markiert.
- **AC-7:** `docs/betrieb.md` beschreibt den neuen Meldeweg (Warnung im Protokoll, Issue durch nginx-Abgleich, Teil-Check in `monitor.sh`).

## Definition of Done

- [ ] `wege_pruefen` ruft `FR_MELDEN` nicht mehr auf, die Warnzeile bleibt (Test grün)
- [ ] Betriebstests und `test_nginx.py` grün, CI-Pflichtprüfungen grün
- [ ] `docs/betrieb.md` beschreibt den neuen Meldeweg
- [ ] Teil-Check in `monitor.sh` liegt in `henemm-infra` (eigenes Issue)
- [ ] nginx-Einstellung der Instanz nachgezogen, `nginx.py pruefen` Ausgang 0, `/info/pruefung.webp` erreicht den Konnektor
- [ ] Die sechs offenen MQ-Nachrichten sind erledigt

## Architektur-Entscheidung (ADR)

**ADR-Nr.:** keine neue. Die Änderung folgt der Regel „Claude MQ nur für Ausfälle“ und lässt die Entscheidung „nginx nie automatisch“ (#206, #316) unberührt; die Automatik (Vorhaben 3) bekommt eine eigene Spec und gegebenenfalls einen eigenen ADR.

## Test Plan

- Automatisch: Test in `engine/tests/test_betrieb.py` wie oben (RED: schlägt mit der heutigen Meldung fehl); gesamte Betriebstests und `test_nginx.py` laufen grün; `test_beispiel_einstellungen_sind_vollstaendig` bleibt grün.
- Beide Reisetypen (ADR-0001): Betrieb ist reiseunabhängig; keine reisespezifischen Werte, Adressen kommen aus `einstellungen.env`.
- Manuell (Live): `nginx.py pruefen` vorher/nachher, Abruf `/info/pruefung.webp`, nächster Lauf von `wege_pruefen` ohne Warnzeile, `monitor.sh` ohne neue Warnung.

## Risiken

- `nginx.py anwenden` wirkt als Root; Schutz durch Sicherung, `nginx -t` und eingebauten Rollback; vorher `pruefen`.
- Ohne Telegram erfährt niemand sofort von einem fehlenden Ort: abgedeckt durch das Issue des nginx-Abgleichs und den Teil-Check in `monitor.sh`.
- `monitor.sh` liegt in einem anderen Repo und wird mit eigenem Issue in `henemm-infra` geändert.

## Changelog

- 2026-11-09: Erstfassung (Teile 1, 2, 4 aus #445).
