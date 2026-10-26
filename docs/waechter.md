# Wächter und Erinnerer (Paket E)

Beschlossen vom Product Owner am 26.10.2026 (Issue #11). Der Baustein `waechter` in `reise.yaml` schaltet beides ein. Code: `engine/waechter.py`.

## Was gemeldet wird

| Art | Wann | An wen |
|---|---|---|
| Frist | Aufgabe offen, Frist in höchstens `regeln.erinnerung_vorlauf_tage` Tagen (Vorgabe 3), einmal | Zuständige Person, sonst alle Bestimmer |
| Überfällig | Frist vorbei, alle 7 Tage neu, bis die Aufgabe erledigt ist | wie oben |
| Ab-Termin | `ab` einer offenen Aufgabe ist erreicht („jetzt möglich“), einmal | wie oben |
| Statuswechsel | Status `fest`, aber der erste Reisetag ist erreicht; Status `fest` oder `unterwegs`, aber der letzte Reisetag ist vorbei; alle 7 Tage neu, bis gewechselt ist | alle Bestimmer |
| Prüfung | veränderliche Angaben werden neu nachgeschlagen (Prüfauftrag, siehe unten) | Bestimmer sehen den Auftrag, die Ergebnisse kommen als Rückfrage oder offene Frage |

Die KI wechselt den Reisestatus nie selbst: Sie erinnert, ein Bestimmer entscheidet (Auftrag an `reise`).

## Wann der Wächter arbeitet

Nur wenn der Baustein `waechter` eingeschaltet ist und der Status es zulässt: `fest` und `unterwegs`. In `idee`, `planung`, `danach` und `archiv` ruht er (Aufgabenfristen zählen erst ab `fest`, siehe `produkt.md`). Die Mahnungen der Seite (Paket B) bleiben davon unberührt.

## Veränderliches prüfen

Geprüft werden Merkmale mit `veraenderlich: true` (Preis, Öffnungszeiten, Fahrzeiten …) der Optionen im Plan (nicht verworfene) und der Unterkünfte mit Nächten. Zu prüfen sind Angaben ohne Prüfdatum und solche, deren Prüfdatum älter ist als `regeln.waechter_frist_tage` (Vorgabe 60). Gibt es Werte je Datum (z. B. Samstag teurer, `docs/alternativen.md`), zählt jeder Eintrag mit eigenem Prüfdatum für sich und steht im Prüfauftrag mit „am …“.

Daraus entsteht höchstens ein **Prüfauftrag** (Name „Wächter“, Art Prüfung, `daten.pruefung`) in `auftraege.jsonl`:

- Nie mehr als ein offener Prüfauftrag, frühestens 7 Tage nach dem letzten, höchstens 15 Angaben je Auftrag (die ältesten zuerst). So bleibt ein KI-Lauf klein.
- Das Einarbeiten (Claude Code) schlägt die Angaben nach. Stimmt der Wert, trägt es Prüfdatum und Quelle ein. **Weicht er ab, wird er nicht still übernommen**: Es legt eine offene Frage mit altem und neuem Wert, Quelle und Datum an, und die Bestimmer entscheiden.
- Ein Prüfauftrag ist keine Entscheidung eines Bestimmers und nimmt an keinem Konflikt teil.

## Meldekanäle (`regeln.meldekanal`)

| Kanal | Wirkung | Stand |
|---|---|---|
| `app` | Meldungen stehen im `ueberblick` der Claude-App unter „Meldungen an dich“ und unter `rueckmeldungen`; erledigte Aufgaben, vollzogene Statuswechsel und Meldungen älter als 14 Tage verschwinden (Konflikte nie) | gebaut |
| `nachricht` | Sammelnachricht an den Betreiber (`lauf --bericht`), versandt vom Betriebsskript `ops/waechter.sh` | gebaut |
| E-Mail an alle | – | nicht gebaut |
| Handy über die Webseite (PWA), Push | – | Issue #21 |

Vorgabe: `[app, nachricht]`.

## Aufruf

```
python3 engine/waechter.py zeige <reise> [--heute JJJJ-MM-TT]      zeigt, was anstünde, ändert nichts
python3 engine/waechter.py lauf [<reise>…] [--heute …] [--bericht DATEI]
```

`lauf` ohne Reise läuft über alle Reisen der Rückmelde-Ablage. Gleiche Meldungen werden nicht doppelt angelegt (`schluessel`). Gedacht ist ein täglicher Lauf; ein zweiter am selben Tag meldet nichts Neues.
