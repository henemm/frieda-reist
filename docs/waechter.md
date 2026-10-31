# Wächter und Erinnerer (Paket E)

Beschlossen vom Product Owner am 26.10.2026 (Issue #11). Der Baustein `waechter` in `reise.yaml` schaltet beides ein. Code: `engine/waechter.py`.

## Was gemeldet wird

| Art | Wann | An wen |
|---|---|---|
| Frist | Aufgabe offen, Frist in höchstens `regeln.erinnerung_vorlauf_tage` Tagen (Vorgabe 3), einmal | Zuständige Person, sonst alle Organisator:innen |
| Überfällig | Frist vorbei, alle 7 Tage neu, bis die Aufgabe erledigt ist | wie oben |
| Ab-Termin | `ab` einer offenen Aufgabe ist erreicht („jetzt möglich“), einmal | wie oben |
| Buchungsfrist | Frist einer nicht stornierten Buchung (`B-…`, #76; `frist`, etwa „Anzahlung“ oder „Ticket laden“) in höchstens `regeln.erinnerung_vorlauf_tage` Tagen, einmal; überfällig alle 7 Tage neu | Person, die gebucht hat (`wer`), sonst alle Organisator:innen |
| Zahlung offen | nur mit `regeln.waechter_zahlung: true` (Vorgabe aus, #166): gebuchte Buchung mit `zahlung` `offen` oder `angezahlt`, deren Frist oder erster Tag ihrer Dinge im Plan in höchstens `regeln.erinnerung_vorlauf_tage` Tagen liegt; danach alle 7 Tage neu, bis sich der Zahlstand ändert. `vor_ort`, `inklusive`, `bezahlt` melden nie | Person, die gebucht hat (`wer`), sonst alle Organisator:innen |
| Stornofrist | `storno_bis` einer nicht stornierten Buchung in höchstens `regeln.erinnerung_vorlauf_tage` Tagen („kostenlos stornieren geht nur noch bis …“), einmal | wie oben |
| Statuswechsel | Status `fest`, aber der erste Reisetag ist erreicht; Status `fest` oder `unterwegs`, aber der letzte Reisetag ist vorbei; alle 7 Tage neu, bis gewechselt ist | alle Organisator:innen |
| Prüfung | veränderliche Angaben sind zu lange ungeprüft (siehe unten) | Organisator:innen sehen die Meldung; der AI-Client schlägt im Gespräch nach und trägt Prüfdatum und Quelle mit `wert_eintragen` ein |

Die KI wechselt den Reisestatus nie selbst: Sie erinnert, ein:e Organisator:in entscheidet (`reise_status_setzen`).

## Wann der Wächter arbeitet

Nur wenn der Baustein `waechter` eingeschaltet ist und der Status es zulässt: `fest` und `unterwegs`. In `idee`, `planung`, `danach` und `archiv` ruht er (Aufgabenfristen zählen erst ab `fest`, siehe `produkt.md`). Die Mahnungen des Generators (Paket B, `route.mahnungen`, in der Claude-App) bleiben davon unberührt.

## Veränderliches prüfen

Geprüft werden Merkmale mit `veraenderlich: true` (Preis, Öffnungszeiten, Fahrzeiten …) der Optionen im Plan (nicht verworfene), der Unterkünfte mit Nächten, der Aufenthalte ohne Nacht und der Strecken im Plan sowie die Lage. Zu prüfen sind Angaben ohne Prüfdatum und solche, deren Prüfdatum älter ist als `waechter_frist_tage` (Vorgabe 60); abgeschaltete Merkmale (Stufe `aus`, auch je Art) nicht.

Daraus entsteht je Angabe eine **Meldung** (Art `pruefung`) an die Organisator:innen, seit dem 29.10.2026 (ADR-0001, Paket O-4: Frieda enthält keine eigene KI; bis dahin ein Prüfauftrag für das Einarbeiten mit Claude Code). Seit dem Abgleich vom 29.10.2026 prüft der Wächter alle Aussagen mit Prüfdatum: Merkmale der Optionen im Plan, der Unterkünfte mit Nächten, der Aufenthalte ohne Nacht an einem Tag und der Strecken im Plan sowie die Lage (Adresse, Punkt; ADR-0004).

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
