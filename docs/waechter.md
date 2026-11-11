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
| Statuswechsel | **jede Reise mit Tagen, auch ohne Baustein `waechter`** (#513): Status `idee` oder `planung` und der erste Tag in höchstens `regeln.status_vorlauf_tage` Tagen (Vorgabe 7) → „fest“; erster Tag erreicht und noch nicht `unterwegs` → „unterwegs“; letzter Tag vorbei und nicht `danach` oder `archiv` → „danach“; alle 7 Tage neu, bis gewechselt ist | alle Organisator:innen |
| Prüfung | veränderliche Angaben sind zu lange ungeprüft (siehe unten) | Organisator:innen sehen die Meldung; der AI-Client schlägt im Gespräch nach und trägt Prüfdatum und Quelle mit `wert_eintragen` ein |

Die KI wechselt den Reisestatus nie selbst: Sie erinnert, ein:e Organisator:in entscheidet, auf der Reiseseite (Tipp auf das Status-Etikett unter dem Untertitel oder auf den Knopf am Hinweis „Für dich“, #513) oder in der Claude-App (`trip_status_set`). Die Seite schickt die Wahl an den Rückmeldedienst (`POST <reise>/status`, nur angemeldete Organisator:innen, ohne `archiv`), der sie wie der Konnektor an den Schreibweg gibt (`reise_status_setzen`, Verlauf mit Name, Datum und Grund „auf der Reiseseite umgestellt“).

Ein Statushinweis geht über alle Wege (Product Owner, 11.11.2026): sofort als Hinweis auf der Reiseseite und als Push-Nachricht; gilt er nach einem Tag noch und hat die Person auf keinem Gerät Benachrichtigungen, kommt er einmal per Mail (Kanal `mail`, `engine/push.py`).

## Wann der Wächter arbeitet

Nur wenn der Baustein `waechter` eingeschaltet ist und der Status es zulässt: `fest` und `unterwegs` (der Statuswechsel oben gilt immer). In `idee`, `planung`, `danach` und `archiv` ruht er (Aufgabenfristen zählen erst ab `fest`, siehe `produkt.md`). Die Mahnungen des Generators (Paket B, `route.mahnungen`, in der Claude-App) bleiben davon unberührt.

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
| `mail` | Rückfall für Statushinweise (#513): Gilt ein Hinweis nach 24 Stunden noch und hat die Person auf keinem Gerät Benachrichtigungen, schickt der Push-Dienst ihn einmal per Mail an die Adresse des Kontos (in der Sprache des Kontos, mit Link zur Reiseseite und zu „Mein Konto“; höchstens drei Versuche, ältere als drei Tage nicht mehr). Andere Meldungen gehen nicht per Mail | gebaut (11.11.2026) |
| `push` | Push-Nachricht aufs Handy (Web Push, `engine/push.py`, Dienst `<instanz>-push`): Meldungen an Personen, dazu neue Rückmeldungen an die Organisator:innen, neu zugewiesene Aufgaben und neue Releases der Software. Jede Person schaltet es je Gerät auf „Mein Konto“ ein (Frieda-App vom Home-Bildschirm auf iPhone und iPad, Entscheidung 2.11.2026) und stellt dort ein, welche Arten kommen und wann Ruhe ist (Vorgabe 21:30 bis 7:00 auf der Uhr des Geräts; was in der Ruhezeit anfällt, kommt an ihrem Ende). Gleichzeitig Wartendes einer Reise kommt als eine Nachricht. Tippen öffnet die Stelle (`#AG-…`, `#T-…`, „Offen“) | gebaut (Issue #21, 1.11.2026) |
| Meldungen auf der Webseite anzeigen | – | Issue #21, Stufe 1 |

Vorgabe: `[app, nachricht, push, mail]`. Ohne `push` schickt die Reise keine Push-Nachrichten, auch keine zu Rückmeldungen, Aufgaben oder Releases.

## Aufruf

```
python3 engine/waechter.py zeige <reise> [--heute JJJJ-MM-TT]      zeigt, was anstünde, ändert nichts
python3 engine/waechter.py lauf [<reise>…] [--heute …] [--bericht DATEI]
```

`lauf` ohne Reise läuft über alle Reisen der Rückmelde-Ablage. Gleiche Meldungen werden nicht doppelt angelegt (`schluessel`). Gedacht ist ein täglicher Lauf; ein zweiter am selben Tag meldet nichts Neues.
