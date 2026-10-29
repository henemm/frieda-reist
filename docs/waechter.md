# Wächter und Erinnerer (Paket E)

Beschlossen vom Product Owner am 26.10.2026 (Issue #11). Der Baustein `waechter` in `reise.yaml` schaltet beides ein. Code: `engine/waechter.py`.

## Was gemeldet wird

| Art | Wann | An wen |
|---|---|---|
| Frist | Aufgabe offen, Frist in höchstens `regeln.erinnerung_vorlauf_tage` Tagen (Vorgabe 3), einmal | Zuständige Person, sonst alle Organisator:innen |
| Überfällig | Frist vorbei, alle 7 Tage neu, bis die Aufgabe erledigt ist | wie oben |
| Ab-Termin | `ab` einer offenen Aufgabe ist erreicht („jetzt möglich“), einmal | wie oben |
| Statuswechsel | Status `fest`, aber der erste Reisetag ist erreicht; Status `fest` oder `unterwegs`, aber der letzte Reisetag ist vorbei; alle 7 Tage neu, bis gewechselt ist | alle Organisator:innen |
| Prüfung | veränderliche Angaben sind zu lange ungeprüft (siehe unten) | Organisator:innen sehen die Meldung; der AI-Client schlägt im Gespräch nach und trägt Prüfdatum und Quelle mit `wert_eintragen` ein |

Die KI wechselt den Reisestatus nie selbst: Sie erinnert, ein:e Organisator:in entscheidet (`reise_status_setzen`).

## Wann der Wächter arbeitet

Nur wenn der Baustein `waechter` eingeschaltet ist und der Status es zulässt: `fest` und `unterwegs`. In `idee`, `planung`, `danach` und `archiv` ruht er (Aufgabenfristen zählen erst ab `fest`, siehe `produkt.md`). Die Mahnungen der Seite (Paket B) bleiben davon unberührt.

## Veränderliches prüfen

Geprüft werden Merkmale mit `veraenderlich: true` (Preis, Öffnungszeiten, Fahrzeiten …) der Optionen im Plan (nicht verworfene) und der Unterkünfte mit Nächten. Zu prüfen sind Angaben ohne Prüfdatum und solche, deren Prüfdatum älter ist als `regeln.waechter_frist_tage` (Vorgabe 60). Gibt es Werte je Datum (z. B. Samstag teurer, `docs/alternativen.md`), zählt jeder Eintrag mit eigenem Prüfdatum für sich und steht im Prüfauftrag mit „am …“.

Daraus entsteht je Angabe eine **Meldung** (Art `pruefung`) an die Organisator:innen, seit dem 28.10.2026 (ADR-0001, Paket O-4: Frieda enthält keine eigene KI; bis dahin ein Prüfauftrag für das Einarbeiten):

- Höchstens 15 Meldungen je Lauf, die ältesten Angaben zuerst; dieselbe Angabe wird frühestens nach `waechter_frist_tage` wieder gemeldet.
- Der AI-Client schlägt die Angabe im Gespräch nach. Stimmt der Wert, bekommt sie Prüfdatum und Quelle. **Weicht er ab, wird er nicht still übernommen**: Ein:e Organisator:in entscheidet; bis dahin bleibt der alte Wert stehen.
- Die Meldung steht im `ueberblick` der Claude-App unter „Meldungen an dich“ und in der Sammelnachricht an den Betreiber; sie verschwindet nach 14 Tagen oder wird nach der Frist erneuert, solange die Angabe ungeprüft ist.

## Meldekanäle (`regeln.meldekanal`)

| Kanal | Wirkung | Stand |
|---|---|---|
| `app` | Meldungen stehen im `ueberblick` der Claude-App unter „Meldungen an dich“ und unter `rueckmeldungen`; erledigte Aufgaben, vollzogene Statuswechsel und Meldungen älter als 14 Tage verschwinden (Konflikte nie) | gebaut |
| `nachricht` | Sammelnachricht an den Betreiber (`lauf --bericht`), versandt vom Betriebsskript `betrieb/waechter.sh` (`docs/betrieb.md`) | gebaut |
| E-Mail an alle | – | nicht gebaut |
| Handy über die Webseite (PWA), Push | – | Issue #21 |

Vorgabe: `[app, nachricht]`.

## Aufruf

```
python3 engine/waechter.py zeige <reise> [--heute JJJJ-MM-TT]      zeigt, was anstünde, ändert nichts
python3 engine/waechter.py lauf [<reise>…] [--heute …] [--bericht DATEI]
```

`lauf` ohne Reise läuft über alle Reisen der Rückmelde-Ablage. Gleiche Meldungen werden nicht doppelt angelegt (`schluessel`). Gedacht ist ein täglicher Lauf; ein zweiter am selben Tag meldet nichts Neues.
