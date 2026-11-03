# Mini-Spec: units-installieren-260

Issue #260, Option B (Product Owner, 3.11.2026). PR 2 von 3. Ein kleines Hilfsprogramm mit Root-Rechten installiert ungefährliche
Änderungen der systemd-Einheiten; alles andere bleibt gesperrt und wird wie bisher gemeldet. Der einmalige Schritt auf dem Server
(Hilfsprogramm installieren, eine sudoers-Zeile) folgt in PR 3 und braucht die Freigabe des Product Owners.

## Was ändert sich

- `betrieb/vorlagen/units-installieren.py` (Vorlage, nur Standardbibliothek, Start mit `python3 -I`): das Hilfsprogramm. `einrichten.sh`
  erzeugt daraus `<EI_ZIEL>/sbin/<instanz>-units-installieren` mit eingesetzter Instanz und eingesetztem Benutzer und nennt die Befehle
  zum Installieren (root:root, 0755, `/usr/local/sbin/`) und die sudoers-Zeile. Das Hilfsprogramm gehört auf dem Server root; die
  Software kann es nicht ändern.
- Aufruf `sudo -n <instanz>-units-installieren <einheit>`; die neue Einheitendatei kommt auf stdin. Es liest die installierte Datei
  selbst, rechnet selbst, ersetzt sie atomar (temporäre Datei im selben Ordner, `fsync`, 0644 root:root, `rename`), führt
  `systemctl daemon-reload` aus und gibt nur den Namen der Einheit aus. Ausgang 0 geändert, 2 nichts zu tun, 3 abgelehnt.
- `betrieb/units.py`: `ERLAUBT` wird eine feste Namensliste (`FR_DIENST`, `FR_ZEITZONE`, `TimeoutStartSec`) mit je eigenem
  Wertmuster, gleich der Liste im Hilfsprogramm (ein Test prüft die Gleichheit). Neuer Aufruf `units.py installieren`: übergibt
  jede Einheit, die nur erlaubte Abweichungen hat, an das Hilfsprogramm, startet danach die betroffenen Dauerdienste neu
  (`rueckmeldungen`, `konnektor`, `schreiben`, `push`; nie `veroeffentlichen` oder `waechter`) und prüft erneut.
  Drop-in-Ordner `<einheit>.d` zählen als gesperrte Abweichung (M2).
- `betrieb/veroeffentlichen.sh`: Hat der Abgleich nur erlaubte Abweichungen und ist das Hilfsprogramm da, wird installiert;
  was danach noch abweicht (gesperrt oder Hilfsprogramm fehlt), meldet der Lauf wie bisher einmal je Fingerabdruck.
- `docs/betrieb.md`: Abschnitt „Einheiten abgleichen“ um Hilfsprogramm, Grenzen und die sudoers-Zeile ergänzt.

## Was darf sich nicht ändern

- Ohne installiertes Hilfsprogramm verhält sich der Lauf wie nach PR 1 (nur melden).
- Ein Fehler beim Installieren stoppt das Veröffentlichen nie.
- `User=`, `ExecStart=`, Rechte, Timer und neue Einheiten werden nie automatisch installiert.

## Acceptance Criteria

- AC-1: Das Hilfsprogramm akzeptiert nur Einheiten aus der festen Menge `<instanz>-{konnektor,push,rueckmeldungen,schreiben,veroeffentlichen,waechter}.service`; jeder andere Name, auch mit `/` oder `..`, und jeder Timer wird mit Ausgang 3 abgelehnt.
- AC-2: Es installiert nur, wenn alle Zeilen außer den erlaubten (`Environment=FR_DIENST=…`, `Environment=FR_ZEITZONE=…`, `TimeoutStartSec=…`, je mit engem Wertmuster, jeder Name höchstens einmal) in neuer und installierter Datei als geordnete Folge je Abschnitt gleich sind; sonst Ausgang 3 und die Datei bleibt unverändert.
- AC-3: Es lehnt die ganze Eingabe ab bei Zeilen, die auf `\` enden, bei CR, NUL und anderen Steuerzeichen, bei ungültigem UTF-8, bei Zeilen ohne `=` (außer leer, Kommentar, Abschnitt) und bei Eingaben über 64 KiB.
- AC-4: Es lehnt ab, wenn `User=` in neuer oder installierter Datei nicht der eingetragene Benutzer ist (insbesondere `root` oder fehlend), wenn die installierte Datei fehlt oder ein Symlink ist, oder wenn ein Drop-in-Ordner `<einheit>.d` besteht.
- AC-5: Erlaubnisliste und Wertmuster in Hilfsprogramm und `units.py` sind gleich; Umgebung und Argumente lenken das Hilfsprogramm nicht um (Pfade und Programmaufrufe sind fest, Tests rufen Funktionen mit Parametern auf).
- AC-6: Das Ersetzen ist atomar; danach läuft `daemon-reload`; ausgegeben wird nur der Name der Einheit.
- AC-7: `units.py installieren` ruft das Hilfsprogramm nur für Einheiten mit ausschließlich erlaubten Abweichungen auf, startet danach nur die vier Dauerdienste neu und liefert nach Erfolg beim erneuten Prüfen Ausgang 0.
- AC-8: `veroeffentlichen.sh` installiert bei Ausgang 3 des Abgleichs, meldet Reste einmal je Fingerabdruck, bleibt grün und läuft ohne installiertes Hilfsprogramm wie nach PR 1.

## Manuelle Test-Schritte

1. Nach PR 3 auf dem Server: `units.py pruefen` zeigt Ausgang 3; nach dem nächsten Veröffentlichen zeigt `systemctl show -p Environment <instanz>-konnektor` die Werte `FR_DIENST` und `FR_ZEITZONE`, `units.py pruefen` endet mit 0.

## Inline-Test (wird während Implementierung geschrieben)

- [ ] `test_units_helfer.py`: AC-1 bis AC-6 mit erfundenen Einheiten in einem Testordner (Funktionen direkt, ohne root).
- [ ] `test_units.py`: AC-5 (gleiche Listen), AC-7 mit Attrappe für Hilfsprogramm und `systemctl`.
- [ ] `test_betrieb.py`: AC-8 mit Attrappen.
