# Mini-Spec: nginx-vorlage-206

Issue #206 und nginx-Teil von #260 (Product Owner, 3.11.2026: Empfehlung A, „so bauen“). Die Vorlage des Konnektors bekommt den Stand des
Servers, mit eigenen Drosselzonen in einer eigenen Datei; ein täglicher Abgleich meldet Abweichungen vom Installierten als ein Issue mit
dem einen Befehl. Es wird nichts automatisch installiert und am Server nichts geändert.

## Was ändert sich

- `betrieb/vorlagen/nginx-zone.conf`: eigene Datei der Instanz mit `geo` und `map` (Adressen aus `FR_EIGENE_ADRESSEN`, Vorgabe `127.0.0.1` und `::1`;
  für sie ist der Schlüssel leer, die Zonen zählen sie nicht) und drei Zonen mit eigenen Namen: `<instanz>_mcp` 10 r/s, `<instanz>_anmelden` 5 r/min,
  `<instanz>_konto` 30 r/min. Die geteilte Datei `conf.d/limit-req.conf` bleibt unberührt; die alten Zonen der Instanz dort entfernt ein späterer, eigener Schritt.
- `betrieb/vorlagen/nginx-konnektor.conf` und `.inc`: Orte wie auf dem Server. `/mcp` mit Zone `_mcp` (burst 40), ohne Puffer, Lesefrist 300 s; `/anmelden` mit
  Zone `_anmelden` (burst 10); `/token`, `/register`, `/.well-known/oauth-`, `/schrift/`, Symbole, Manifest ohne Drossel; Konto, Abmelden, Zustimmung,
  Bereitschaft, Einladung, Kalender-Abo und die Übergangs-Links mit Zone `_konto` (burst 20). Die gemeinsame `.inc` hat keine eigene Lesefrist mehr (nginx-Vorgabe 60 s).
- `betrieb/einrichten.sh`: setzt die neuen Namen und Adressen ein und nennt die Installation der Zonendatei.
- `betrieb/nginx.py` (Standardbibliothek): `pruefen` erzeugt die Bausteine (`einrichten.sh --erzeugen`) und vergleicht sie mit den installierten
  (`conf.d/<instanz>-zone.conf`, `<snippets>/<instanz>-konnektor.conf` und `.inc`). Ausgang 0 gleich oder noch nicht eingerichtet, 3 abweichend (mit dem einen Befehl zum Beheben), 1 Fehler.
- `betrieb/veroeffentlichen.sh`: meldet Ausgang 3 einmal je Fingerabdruck als normales Issue (nie Alarm, nie Abbruch), installiert nichts.
- `docs/betrieb.md`: Abschnitt zu Zonen, Ausnahme (Bedingung: keine Funktion, mit der der Server fremde Adressen aufruft), Abgleich und der späteren einmaligen Umstellung.

## Was darf sich nicht ändern

- Reise-Bausteine (`nginx-reise.conf`, `freischalten.sh`); die Zone `<instanz>_api` zieht um, siehe zone-api-eigene-datei-316.
- Nichts am Server, nichts in `/etc`; nginx wird nie automatisch geändert oder neu geladen.
- Ein Fehler im Abgleich stoppt das Veröffentlichen nie.

## Acceptance Criteria

- AC-1: Die erzeugte Zonendatei lädt in einem echten nginx (Test mit `nginx -t`/Start) und enthält genau die drei Zonen mit Instanz-Namen, keinen Namen aus der geteilten Datei und `geo`/`map` mit leerem Schlüssel für die eigenen Adressen.
- AC-2: Eine Anfrage von einer eigenen Adresse wird nie mit 429 beantwortet (Test mit vielen Anfragen); von einer fremden Adresse greift die Drossel (429).
- AC-3: Die Orte des Konnektors nutzen die drei Zonen wie oben beschrieben (`/mcp` großzügig, `/anmelden` streng, Konto-Orte 30/min, Token/Registrierung/Metadaten/Schrift ohne Drossel); keine Direktive doppelt.
- AC-4: Die Lesefristen bleiben über dem längsten Schreibvorgang (`test_zeitgrenzen…` angepasst).
- AC-5: `nginx.py pruefen` endet mit 0 bei gleichen Dateien und bei nicht eingerichteter Instanz (keine installierte Datei), mit 3 und Ausgabe des Befehls bei Abweichung, mit 1 bei Fehler; es schreibt nie unter `/etc`.
- AC-6: `veroeffentlichen.sh` meldet Ausgang 3 einmal je Fingerabdruck als normale Meldung, löscht den Merker bei Ausgang 0, bleibt bei Ausgang 1 grün und installiert nichts.
- AC-7: Die Tests laufen ohne echte Reisen grün; Ausgabe und Dateien enthalten keine echten Adressen oder Pfade.

## Manuelle Test-Schritte

1. Auf dem Server (nur lesend): `nginx.py pruefen` endet mit 0 und meldet „nicht eingerichtet“, solange die Umstellung fehlt.

## Inline-Test (wird während Implementierung geschrieben)

- [ ] `test_betrieb.py`: AC-1 bis AC-3 gegen echtes nginx mit den erzeugten Dateien; AC-6 mit Attrappen.
- [ ] `test_nginx.py`: AC-5.
- [ ] `test_schreiben.py`: AC-4.
