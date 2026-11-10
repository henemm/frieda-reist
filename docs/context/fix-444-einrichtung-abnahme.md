# Context: fix-444-einrichtung-abnahme

## Request Summary
Der Software-Teil von #444 (eigener Kartendienst, PR #468, 083bd63) ist auf `main`. Offen sind Einrichtung auf der Instanz, die Abnahme von #240 am laufenden Dienst (AC-20), der Teil-Check in `monitor.sh` und das Aufräumen. Ein früher angelegter Workflow „Wortlaut Kartenpunkte“ hatte keinen Auftrag und wurde abgebrochen.

## Related Files
| File | Relevance |
|------|-----------|
| docs/specs/betrieb/eigener-kartendienst-444.md | Spec mit Abnahme Schritte 1 bis 7 und AC-20 |
| betrieb/einrichten.sh, betrieb/kartendienst.sh, betrieb/vorlagen/kartendienst/ | Einrichtung, Einspielen, Einheiten |
| betrieb/einstellungen.beispiel | Einstellungen `FR_KARTENDIENST`, `FR_KARTENDIENST_ORDNER`, `FR_KARTENDIENST_REGIONEN` |
| docs/context/feat-444-eigener-kartendienst.md | Kontext und Messungen des Software-Teils |
| ~/overpass-test/ (außerhalb des Repos) | Testaufbau mit Balearen-Auszug, nach Abschluss aufräumen |

## Existing Patterns
- Überwachung als Teil-Check in `henemm-infra/scripts/monitor.sh` (Warnung, kein eigener Heartbeat), Vorbild `check_frieda_seiten`.
- Einstellungen der Instanz liegen in der Einstellungsdatei des Reisen-Repos, nie in diesem Repo.
- Abnahme nur an der eigenen archivierten Testreise und einer Städtewochenende-Testreise, nie an echten Reisen.

## Dependencies
- Upstream: Docker auf dem Server, Image `wiktorn/overpass-api`, Geofabrik-Auszug (Region Balearen/Mallorca), osmium.
- Downstream: Abnahme #240 (`map_points_fetch`), Teil-Check in henemm-infra.

## Existing Specs
- `docs/specs/betrieb/eigener-kartendienst-444.md`

## Risks & Considerations
- Einspielen braucht einmalig rund 1,6 GiB Speicher und 2 GB Platte.
- Datenordner braucht Rechte 755, sonst `Permission denied`.
- `/api/status` des Images liefert 502; Bereitschaft nur über eine echte Abfrage prüfen.
- Änderungen im Reisen-Repo und in henemm-infra sind eigene Commits mit Issue.
- Offener Punkt: Ob für diese Betriebsarbeit überhaupt Software geändert wird, klärt `/20-analyse`; sonst entfällt der Spec-Teil.

## Analysis

### Type
Feature (Betriebsabschluss von #444, kein neuer Software-Umfang)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| Einstellungen im Reisen-Repo der Instanz (`~/frieda-reisen`) | MODIFY | `FR_KARTENDIENST*` setzen (Region Balearen), eigener Commit mit Issue dort |
| `henemm-infra/scripts/monitor.sh` | MODIFY | Teil-Check: Alter von `abdeckung.json`, Warnung ab 40 Tagen; Issue in henemm-infra |
| `docs/artifacts/` (Abnahmenachweis, Pfade relativ, Reisen als Platzhalter) | CREATE | Nachweis AC-20 |
| Repo-Software (`engine/`, `betrieb/`) | keine | nur falls die Einrichtung einen Fehler der Skripte zeigt (dann Fix mit Test) |

### Scope Assessment
- Files: 2 außerhalb dieses Repos, 1 Nachweis hier
- Estimated LoC: +30/-0 (Teil-Check), Software 0
- Risk Level: MEDIUM — erstmals Docker als Baustein und 1,6 GiB beim Einspielen auf dem knappen Server; Rückfall auf den öffentlichen Dienst bleibt.

### Technical Approach
1. Befund: Der Testcontainer `overpass-test` läuft noch (Testaufbau in `~/overpass-test`). Vor dem Einrichten stoppen und entfernen, sonst kollidiert der Port.
2. Region in den Einstellungen der Instanz eintragen, `betrieb/einrichten.sh` ausführen, Einspielen über `betrieb/kartendienst.sh` (Speicher vorher prüfen, einmalig ~1,6 GiB).
3. AC-20 an der vorhandenen archivierten Testreise und am Städtewochenende (kein Neuanlegen): `map_points_fetch` mit eigenem Dienst, Ruhezustand ohne Container, Rückfall bei gestopptem Dienst. Nachweis in #444 und #240.
4. Issue in henemm-infra anlegen, Teil-Check nach Vorbild `check_frieda_seiten` bauen, einmal laufen lassen.
5. Aufräumen: `~/overpass-test` (Container, Datenbank, pbf).
6. Wegen der Betriebsarbeit ohne Software-Änderung: Spec als knappe Abnahme-Checkliste (Verweis auf die bestehende Spec), kein neuer Software-Umfang.

### Dependencies
Docker, `systemd-socket-proxyd`, Geofabrik-Auszug, osmium im Image; Abnahme #240 hängt daran.

### Open Questions
- [ ] Keine Produktfrage. Technisch: Port 12345 frei? (beim Einrichten prüfen)
