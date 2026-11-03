# Context: nginx-vorlage-206

## Request Summary
#206 und der nginx-Teil von #260 (Product Owner, 3.11.2026, „so bauen“, Empfehlung A): Die nginx-Vorlage des Konnektors auf den Stand des Servers
bringen, mit eigenen Drosselzonen in einer eigenen Datei und einer Ausnahme der eigenen Prüfungen des Servers. Der Abgleich zwischen Vorlage und
Installiertem meldet eine Abweichung als ein Issue mit dem einen Befehl; installiert wird nie automatisch. Am Server wird in diesem Vorhaben nichts geändert.

## Related Files
| File | Relevance |
|------|-----------|
| betrieb/vorlagen/nginx-konnektor.conf, nginx-konnektor.inc | Orte des Konnektors; bisher eine Zone (30/min) für alles |
| betrieb/vorlagen/nginx-zone.conf | bisher eine Zone je Instanz |
| betrieb/vorlagen/nginx-reise.conf, betrieb/freischalten.sh | Reise-Bausteine nutzen `__ZONE__` (`<instanz>_api`); bleiben unverändert |
| betrieb/einrichten.sh | erzeugt die Bausteine (`--erzeugen` nach `EI_ZIEL`), nennt die Installationsbefehle |
| betrieb/units.py, betrieb/veroeffentlichen.sh | Muster für Abgleich, Fingerabdruck und Meldung (#260) |
| engine/tests/test_betrieb.py, test_schreiben.py | Test mit echtem nginx (Zone, Orte), Test der Zeitgrenzen gegen den Schreibweg |
| docs/betrieb.md | Betriebsanleitung |

## Existing Patterns
- Abgleich wie bei den Einheiten: erzeugen mit `einrichten.sh --erzeugen`, vergleichen, eine normale Meldung je Fingerabdruck (`fr_melden normal`), Ausgang 0 gleich / 3 abweichend.
- Zonen eines Projekts mit Instanz-Präfix; leerer Schlüssel einer `limit_req_zone` wird nicht gezählt (`geo` + `map`).

## Dependencies
- Upstream: Instanz-Einstellungen (`FR_*`), nginx auf dem Server (nur lesend, `sudo -n cat` für Bausteine mit Rechten 640).
- Downstream: die einbindende Instanz installiert die erzeugten Dateien einmal bewusst; der Live-Block wird in einem eigenen, freizugebenden Schritt umgestellt.

## Risks & Considerations
- Gleiche Zonennamen in der geteilten Datei und der eigenen würden nginx beim Laden ablehnen: eigene Zonen bekommen neue Namen (`<instanz>_mcp`, `<instanz>_anmelden`, `<instanz>_konto`), die geteilte Datei bleibt unberührt.
- Reise-Bausteine verweisen auf `<instanz>_api` aus der geteilten Datei und bleiben bis zur späteren Bereinigung unverändert.
- Ausnahme für die eigenen Adressen ist sicher, solange Frieda keine Funktion hat, mit der der Server eine fremde Adresse aufruft und die Antwort nach außen reicht (Annahme, im Betrieb dokumentiert).
- Fehlt die installierte Datei (Umstellung noch nicht erfolgt), meldet der Abgleich nichts (kein Alarm vor dem bewussten Schritt).
