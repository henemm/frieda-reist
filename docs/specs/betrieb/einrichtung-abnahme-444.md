---
entity_id: einrichtung-abnahme-444
type: feature
created: 2026-11-10
updated: 2026-11-10
status: draft
workflow: fix-444-einrichtung-abnahme
version: "1.0"
tags: [betrieb, kartendienst, overpass, abnahme, monitor, k14]
---

# Einrichtung und Abnahme des eigenen Kartendienstes (#444, Abschluss; Ursprung #240)

Die Software steht auf `main` (PR #468, Spec `docs/specs/betrieb/eigener-kartendienst-444.md`, AC-1 bis AC-19 durch Tests belegt). Diese Spec deckt nur den Betriebsabschluss ab: Einrichtung auf der Instanz, AC-20 am laufenden Dienst, Überwachung, Aufräumen. Es entsteht kein neuer Software-Umfang.

## Approval

- [ ] Approved

## Purpose

Der eigene Kartendienst soll auf der Instanz laufen und an Testreisen nachweislich arbeiten, damit die Abnahme von `map_points_fetch` (#240) gelingt und #444 end to end geschlossen werden kann.

## Source

- **Files:** keine Änderung an `engine/`, `betrieb/`, `werkzeuge/`. Änderung nur außerhalb: Einstellungen im Reisen-Repo der Instanz, `scripts/monitor.sh` in `henemm-infra`. Hier neu: ein Abnahmenachweis in `docs/artifacts/`.
- **Identifier:** `FR_KARTENDIENST`, `FR_KARTENDIENST_ORDNER`, `FR_KARTENDIENST_REGIONEN`, `abdeckung.json`
- Zeigt die Einrichtung einen Fehler der Skripte, wird er in diesem Workflow mit Test behoben (eigener Commit) und hier ergänzt.

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `docs/specs/betrieb/eigener-kartendienst-444.md` | Spec | Verhalten, AC-20 und Abnahmeschritte 1 bis 7 |
| `betrieb/einrichten.sh`, `betrieb/kartendienst.sh` | Skript | Einrichtung, Einspielen |
| Docker, `systemd-socket-proxyd`, Image `wiktorn/overpass-api`, Geofabrik-Auszug | Extern | Betrieb |
| `henemm-infra/scripts/monitor.sh` (`check_frieda_seiten` als Vorbild) | Extern | Teil-Check |

## Implementation Details

1. Testaufbau stoppen: Container `overpass-test` anhalten und entfernen (Port 12345 frei).
2. Speicher prüfen (Einspielen einmalig ca. 1,6 GiB, 2 GB Platte). Region Balearen in den Einstellungen des Reisen-Repos eintragen (eigenes Issue und Commit dort), `betrieb/einrichten.sh` ausführen, Einspielen über `betrieb/kartendienst.sh`.
3. Bereitschaft nur über eine echte Abfrage prüfen (`/api/status` liefert 502). Datenordner hat Rechte 755.
4. AC-20 nach Abnahme Schritte 2 bis 5 der Haupt-Spec, an der vorhandenen archivierten Testreise und am Städtewochenende (nichts neu anlegen; Reisen im Nachweis als Platzhalter).
5. Issue in `henemm-infra`; Teil-Check in `monitor.sh`: Alter von `abdeckung.json`, Warnung (kein Alarm) ab 40 Tagen, kein eigener Heartbeat; einmal laufen lassen.
6. Nachweis in `docs/artifacts/` (Pfade relativ, ohne echte Reisen), Kommentar in #444 und #240.
7. Aufräumen: `~/overpass-test` (Container, Datenbank, pbf).

## Expected Behavior

- **Input:** Instanz mit gesetzter Region, Testreisen.
- **Output:** Eigener Dienst läuft bei Bedarf, antwortet innerhalb von 10 Sekunden, ruht ohne Container, Rückfall auf den öffentlichen Dienst bleibt.
- **Side effects:** Docker-Image und Datenbank (2 GB) auf dem Server; ein Teil-Check in `monitor.sh`.

## Acceptance Criteria

- **AC-1:** Given Region gesetzt / When `einrichten.sh` und Einspielen laufen / Then existiert `abdeckung.json` mit der Fläche der Balearen und eine echte Abfrage antwortet.
- **AC-2:** Given Wanderung innerhalb der Fläche / When `map_points_fetch` mit Wasserstellen läuft / Then Treffer mit Quelle, Datenstand und Hinweis auf den eigenen Dienst innerhalb von 10 Sekunden auch beim Kaltstart (gemessen 2 s); zweiter Aufruf ersetzt statt zu verdoppeln; zweite Kategorie ebenso.
- **AC-3:** Given Städtewochenende / When die Abfrage läuft / Then Ablehnung wie bisher oder Antwort des öffentlichen Dienstes (beides gilt als bestanden, solange die Abfrage nicht am eigenen Dienst hängt) am eigenen Dienst.
- **AC-4:** Given 15 min ohne Aufruf / When `docker ps` geprüft wird / Then kein Container und kein Proxy-Prozess; der nächste Aufruf startet beides wieder.
- **AC-5:** Given gestoppter eigener Dienst / When eine Abfrage läuft / Then Rückfall auf den öffentlichen Dienst mit dessen Ergebnis oder Fehlermeldung.
- **AC-6:** Given der Teil-Check / When er läuft / Then meldet er Warnung ab 40 Tagen Alter von `abdeckung.json`, sonst grün; ein Lauf ist belegt.
- **AC-7:** Given Abschluss / When aufgeräumt ist / Then `~/overpass-test` und der Testcontainer sind weg; Nachweis steht in #444, #240 und `docs/artifacts/`; `engine/tests/test_protokolle_ohne_pfade.py` ist grün.

## Test Plan

Kein neuer automatischer Test (keine Software-Änderung). Abnahme manuell am laufenden Dienst; Nachweis als Protokoll. Vor dem Vorspulen des Nachweises: `engine/.venv/bin/python -m pytest -q engine/tests/test_protokolle_ohne_pfade.py`. Bei einem Skriptfehler: Test zuerst, dann Fix.

## Known Limitations

- Erste Docker-Nutzung auf dem knappen Server; Rückfall auf den öffentlichen Dienst bleibt.
- Veraltete Daten: Aktualisierung der Region bleibt ein manueller Schritt, der Teil-Check warnt nur.

## Scope

- Files: 0 im Repo (Software), 1 Nachweis hier, 2 außerhalb (Reisen-Repo der Instanz, `henemm-infra`)
- Geschätzte LoC: +30 (Teil-Check), Software 0
- Risiko: MEDIUM (erste Docker-Nutzung, 1,6 GiB beim Einspielen); Rückfall auf den öffentlichen Dienst bleibt.

## Definition of Done

- [ ] AC-1 bis AC-7 erfüllt, Nachweis in `docs/artifacts/`, #444 und #240
- [ ] Teil-Check in `monitor.sh` läuft einmal grün; Issue in `henemm-infra` erledigt
- [ ] `~/overpass-test` und Testcontainer entfernt
- [ ] #240 und #444 erst geschlossen, wenn alles end to end erledigt ist

## Rückweg

Region in den Einstellungen entfernen: die Software fragt wieder nur den öffentlichen Dienst. Container, Einheiten und Datenordner lassen sich mit `betrieb/kartendienst.sh` bzw. durch Löschen des Ordners entfernen.

## Changelog

- 2026-11-10: Erstfassung (Betriebsabschluss von #444)
