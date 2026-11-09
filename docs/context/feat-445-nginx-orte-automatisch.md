# Context: feat-445-nginx-orte-automatisch

## Request Summary
Teil 3 von #445: Neue Orte der nginx-Vorlage des Konnektors (`betrieb/vorlagen/nginx-konnektor-orte.inc`) sollen beim
Software-Wechsel automatisch auf der Instanz eingerichtet werden, ohne Handschritt. Entscheidung des Product Owners
(9.11.2026, Kommentar in #445 und `docs/context/fix-445-nginx-orte-meldung.md`): Variante (b), root-eigenes Hilfsprogramm
mit enger Whitelist, wie bei den systemd-Einheiten (#260); eigene Spec, braucht Sicherheitsprüfung.

Teile 1, 2 und 4 sind erledigt (PR #447 auf `main`, henemm-infra#415): Wegeprüfung warnt nur, Monitor prüft die Pfade.

## Related Files
| File | Relevance |
|------|-----------|
| `betrieb/nginx.py` | Abgleich `pruefen` (Ausgang 0/3/1) und `anwenden` (von Hand, root; Sicherung, `nginx -t`, Rückweg, Reload). Wird um einen automatischen Weg über das Hilfsprogramm ergänzt (analog `units.py installieren`). |
| `betrieb/veroeffentlichen.sh:625-675` | `units_abgleichen` (ruft bei Ausgang 3 `units.py installieren`, dann neu `pruefen`) und `nginx_abgleichen` (meldet nur, Merker `<FR_DIENST>/nginx-gemeldet`). `nginx_abgleichen` bekommt den Installationsversuch. |
| `betrieb/vorlagen/units-installieren.py` | Vorbild für das neue Hilfsprogramm: `#!/usr/bin/python3 -I`, nur Standardbibliothek, Platzhalter `__INSTANZ__`/`__BENUTZER__`, liest Installiertes selbst (O_NOFOLLOW, root-Eigentum), Eingabe per stdin (max 64 KiB, UTF-8, keine Steuerzeichen), Whitelist `ERLAUBT`, atomar ersetzen, Ausgang 0/2/3. |
| `betrieb/units.py` | Vorbild für die Aufrufseite: `FR_UNITS_HELFER`, `FR_SUDO`, Ausgang 5 wenn Hilfsprogramm fehlt/scheitert; Erlaubnisliste gleich in beiden (Test). |
| `betrieb/einrichten.sh` | `--erzeugen` erzeugt Soll (`$ZIEL/nginx/<instanz>-konnektor-orte.inc` u. a., Zeile ~100), `--installieren` installiert; erzeugt `sbin/<instanz>-units-installieren` und nennt am Ende Installationsbefehl und sudoers-Zeile (Zeilen 133-137). Neues Hilfsprogramm kommt dazu. |
| `betrieb/vorlagen/nginx-konnektor-orte.inc` | Der Baustein mit den Orten (99 Zeilen). Direktiven darin: `location` (`=`, `^~`, eine Regex `~ ^/(konto|abmelden|authorize|gesund)?$`), `limit_req zone=__ZONE_*__ burst=N nodelay;`, `limit_req_status 429;`, `include __SNIPPETS__/__INSTANZ__-konnektor.inc;`, `proxy_buffering off;`, `proxy_read_timeout 300s;`, Kommentare. Kein `proxy_pass`, kein `add_header`. |
| `betrieb/vorlagen/nginx-konnektor.inc` | Gemeinsamer Baustein (proxy_pass auf 127.0.0.1:Port, Kopfzeilen, client_max_body_size). Ändert sich selten; enthält sicherheitsrelevante Zeilen. |
| `betrieb/vorlagen/nginx-zone.conf` | Drossel-Zonen in conf.d (http-Kontext). |
| `betrieb/gemeinsam.sh:144` | `wege_pruefen` (seit #445 nur Warnung). |
| `engine/tests/test_nginx.py`, `test_units.py`, `test_units_helfer.py` | Bestehende Tests; `test_units_helfer.py` ist das Muster für Tests eines root-Hilfsprogramms (ohne Root, mit umgelenkten Ordnern). |
| `engine/tests/test_betrieb.py:2224-2300` | Tests für `units_abgleichen`/`nginx_abgleichen` in `veroeffentlichen.sh` mit Attrappen (`VF_UNITS`, `VF_NGINX`). |
| `docs/betrieb.md:321-352` (Einheiten abgleichen), `:354ff` (nginx-Bausteine abgleichen), `:59`, `:185-193` | Doku, mehrfach steht „übernommen mit `nginx.py anwenden` (von Hand)“; muss angepasst werden. |

## Existing Patterns
- **Abgleich + root-Hilfsprogramm (#260):** Prüfen ohne Wirkung; bei nur erlaubten Abweichungen ruft der Betrieb `sudo -n /usr/local/sbin/<instanz>-…` mit dem Soll auf stdin; das Hilfsprogramm traut dem Aufrufer nichts, prüft selbst und installiert atomar. Einmalig und bewusst installiert (Hilfsprogramm + sudoers-Zeile, von `einrichten.sh` genannt). Ohne Hilfsprogramm bleibt es bei der Meldung.
- **Einmal melden je Abweichung:** Fingerabdruck in `<FR_DIENST>/<x>-gemeldet`, normale Meldung (Issue), kein Alarm.
- **Sicher anwenden (nginx.py anwenden):** Sicherung nach `<FR_DIENST>/nginx-sicherung/<Zeit>`, installieren, `nginx -t`, bei Fehler Rückweg, erst dann `systemctl reload nginx`.
- Erlaubnisliste doppelt (Aufrufer und Hilfsprogramm), ein Test prüft Gleichheit.

## Dependencies
- Upstream: `einrichten.sh --erzeugen` (Soll), sudo (`FR_SUDO`), `/usr/sbin/nginx -t`, `systemctl reload nginx`.
- Downstream: `veroeffentlichen.sh` (nach grünem Lauf), Monitor der Instanz (henemm-infra `monitor.sh`, Konnektor-Pfade), `wege_pruefen`.
- Server-Stand (9.11.2026): `/usr/local/sbin/frieda-reisen-units-installieren` installiert (root), sudoers NOPASSWD dafür vorhanden; für hem zusätzlich `nginx`, `systemctl reload nginx`, `cat /etc/nginx/*`.

## Existing Specs
- `docs/specs/betrieb/wegepruefung-ohne-alarm-445.md` – Teile 1/2/4, grenzt diese Automatik ausdrücklich aus.
- Specs zu #206/#260/#316 (nginx-Vorlage, Einheiten, Zone) in `docs/specs/betrieb/` – Herkunft der Regel „nginx nie automatisch“.

## Risks & Considerations
- **Sicherheit (hoch):** Jede nginx-Zeile wirkt als root-konfigurierter Webserver. Die Whitelist muss Rechte-Ausweitung ausschließen: kein `proxy_pass`/`alias`/`root`/`return`/`rewrite`/`add_header`/`include` außer genau dem eigenen Konnektor-Baustein, keine Blöcke außer `location`, keine fremden Zonen, keine `if`/`set`/Variablen. Ort-Pfade mit engem Muster (Regex-Orte nur verankert `^/…$`, sonst könnte ein Ort Reiseseiten überdecken – kein Rechtegewinn, aber Ausfall).
- **Umfang:** Nur `<instanz>-konnektor-orte.inc` automatisch; `konnektor.inc` (proxy_pass, Kopfzeilen) und `zone.conf` (http-Kontext) bleiben bewusster Schritt (`nginx.py anwenden`). Zu klären in der Analyse.
- **Eingaben dem Aufrufer nicht trauen:** Hilfsprogramm liest Installiertes selbst, Ziele fest (Snippets-Ordner, Dateiname aus Instanz), Inhalt nur per stdin, Größen-/Zeichenprüfung, Symlinks ablehnen, root-Eigentum prüfen; Platzhalter `__SNIPPETS__`, Zonennamen, Port fest eingesetzt.
- **Rückweg:** `nginx -t` mit Sicherung und Wiederherstellung im Hilfsprogramm selbst (der Aufrufer hat keine Schreibrechte unter /etc).
- **Einmaliger bewusster Schritt bleibt:** Installation des Hilfsprogramms und der sudoers-Zeile (wie #260). Das ist kein wiederkehrender Handschritt, entspricht der Regel „keine Handarbeit im Betrieb“ nach Einrichtung. Auf dem Server dieser Instanz muss das Hilfsprogramm einmalig installiert werden (Claude selbst, mit sudo).
- **Doku-Widerspruch:** `docs/betrieb.md` und `nginx.py`-Docstring sagen „nginx nie automatisch“; mit Verweis auf die Entscheidung des PO (9.11.2026) anpassen.
- **Instanz-Tests:** Ändert sich Verhalten von `veroeffentlichen.sh`/Umgebungswerte, laufen die Tests des Reisen-Repos mit dem Branch.
- Geschätzt ca. +300 Zeilen inkl. Tests, Risiko hoch → Gegenprüfung (Adversary) und `/security-review` vor dem Vorspulen.

## Analysis

### Type
Feature (Teil 3 von #445; Entscheidung des PO 9.11.2026: Variante b, root-eigenes Hilfsprogramm mit enger Whitelist).

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `betrieb/vorlagen/nginx-orte-installieren.py` | CREATE | root-Hilfsprogramm (`#!/usr/bin/python3 -I`, nur Standardbibliothek). Platzhalter `__INSTANZ__`, `__SNIPPETS__`, `__ZONE_MCP__`, `__ZONE_ANMELDEN__`, `__ZONE_KONTO__` setzt `einrichten.sh` fest ein. Soll per stdin (max. 64 KiB), Grammatikprüfung des ganzen Solls, installierte Datei per O_NOFOLLOW lesen (reguläre Datei, root-Eigentum), Sicherung unter root, atomar ersetzen (mkstemp im Snippets-Ordner, Name ohne `.conf`/`.inc`-Endung, fsync, 640 root:root, os.replace), `/usr/sbin/nginx -t`, bei Fehler Rückweg, dann `systemctl reload nginx`. `flock` gegen gleichzeitige Läufe. |
| `betrieb/nginx.py` | MODIFY | Neuer Befehl `installieren` (wie `units.py installieren`): nur wenn genau und nur `<instanz>-konnektor-orte.inc` abweicht (konnektor.inc, zone.conf, fremde Zone gleich bzw. ohne Befund), ruft `$FR_SUDO $FR_NGINX_HELFER` (Vorgabe `/usr/local/sbin/<instanz>-nginx-orte-installieren`) mit dem Soll auf stdin auf, danach erneut `pruefen`. `pruefen` liefert dafür die Liste der abweichenden Dateien. Ausgang 5, wenn das Hilfsprogramm fehlt oder scheitert. Docstring „installiert nie etwas / läuft nie automatisch“ anpassen. |
| `betrieb/veroeffentlichen.sh` (`nginx_abgleichen`, ~Z. 655–675) | MODIFY | Wie `units_abgleichen`: bei Ausgang 3 Installationsversuch, danach `pruefen`. Ist danach alles gleich: nur Protokollzeile, Merker löschen. Bleibt eine Abweichung oder fehlt der Helfer: einmalige normale Meldung je Fingerabdruck, mit dem Ergebnis des Versuchs. Veröffentlichen stoppt nie. |
| `betrieb/einrichten.sh` | MODIFY | `--erzeugen` erzeugt `sbin/<instanz>-nginx-orte-installieren` mit eingesetzten Platzhaltern. Die Ausgabe nennt einmalig den Installationsbefehl und die sudoers-Zeile (wie Z. 135–137). |
| `betrieb/einstellungen.beispiel` | MODIFY | `FR_NGINX_HELFER` dokumentieren (Test prüft Vollständigkeit). |
| `betrieb/vorlagen/units-installieren.py` | MODIFY (klein) | Nebenbefund: `daemon-reload` nach `os.replace` mit `check=True` ungefangen → Traceback statt klarem Ausgang. Gleich mitbeheben (eigener Commit). |
| `engine/tests/test_nginx_helfer.py` | CREATE | Muster `test_units_helfer.py`: ohne root, umgelenkte Ordner. Positiv: echte Vorlage, erzeugt mit `einrichten.sh --erzeugen`, geht durch (bricht jede künftige Vorlagenänderung, die die Grammatik verletzt, schon im Test). Negativ als Tabelle: je verbotene Direktive, fremde Zone, fremder include, `$`, Anführungszeichen, Steuerzeichen, Zeilenfortsetzung, unverankerte Regex, `..`, Ort ohne include, Symlink, fremdes Eigentum, zu groß; `nginx -t` scheitert → Rückweg; reload scheitert → Ausgang 5. |
| `engine/tests/test_nginx.py` | MODIFY | Tests für `nginx.py installieren` (nur Orte abweichend → Helfer; weitere Abweichung → kein Aufruf; Helfer fehlt → 5). |
| `engine/tests/test_betrieb.py` (~Z. 2268–2292) | MODIFY | `protokoll == ["pruefen"]` ändert sich; neue Fälle mit Attrappe (Erfolg ohne Meldung, Scheitern mit Meldung). |
| `docs/betrieb.md` (Z. 23, 59, 190–193, 306, 369–382) | MODIFY | „von Hand / nie automatisch“ für die Orte-Datei ersetzen; Einmalschritt (Helfer + sudoers) beschreiben; `konnektor.inc` und `zone.conf` bleiben `nginx.py anwenden`. Test verbietet „von Hand übernommen“. |
| `docs/specs/betrieb/nginx-orte-automatisch-445.md` | CREATE | Eigene Spec (Phase 3), Vorlage `docs/specs/fast/units-installieren-260.md`. |
| `docs/specs/fast/nginx-vorlage-206.md` | MODIFY (ein Satz) | Hinweis, dass „nginx nie automatisch“ für die Orte-Datei seit #445 nicht mehr gilt. |
| `betrieb/vorlagen/nginx-konnektor-orte.inc` | MODIFY (optional) | Regex-Gruppe `(konto|…)?` → `(?:konto|…)?`, damit die Grammatik keine Captures zulassen muss. |

### Scope Assessment
- Files: ~12 (2 neu)
- Estimated LoC: ca. +300 Code und Tests (Helfer ~170, nginx.py ~50, Shell ~20, Tests ~175), ca. 60 Zeilen Doku; −10
- Risk Level: HIGH (root-Hilfsprogramm, Webserver-Konfiguration der laufenden Instanz)

### Technical Approach
Variantenvergleich der Whitelist:

| Kriterium | (A) Strukturprüfung des ganzen Solls | (B) Differenzprüfung (nur neue Orte) |
|---|---|---|
| Sicherheit | prüft alles gegen feste Grammatik, kein Vertrauen in den Altbestand | vertraut dem Altbestand, braucht für neue Blöcke trotzdem dieselbe Grammatik |
| Geänderte/entfernte Orte, Kommentare, burst | laufen automatisch durch | abgelehnt → wieder Handschritt |
| Aufwand | mittel (~120 Zeilen Prüfung) | höher (Blockvergleich + Grammatik) |
| Testbarkeit | sehr gut (echte Vorlage positiv, Tabelle negativ) | mittel |

**Empfehlung: (A).** (B) enthält (A) und bringt nichts dazu.

Grammatik (A), außerhalb von Kommentaren nur ASCII; abgelehnt: `"`, `'`, `\`, `$`, Steuerzeichen außer `\n`/`\t`, Zeilenfortsetzung.
- Oberste Ebene nur `location`-Blöcke; Modifikator `=`, `^~` oder `~`.
- Pfad `=`/`^~`: `/[A-Za-z0-9._/-]*`, kein `..`, kein `//`.
- Regex `~`: verankert `^/…$`, nur feste Wörter, höchstens eine nicht fangende Alternativ-Gruppe `(?:a|b)?`; Vorlage wird dafür umgestellt.
- Im Block, je höchstens einmal: `limit_req zone=<ZB>_(mcp|anmelden|konto) burst=<1–3 Ziffern> nodelay;`, `limit_req_status 429;`, `include <SNIPPETS>/<instanz>-konnektor.inc;` (Pflicht, genau einmal), `proxy_buffering off;`, `proxy_read_timeout <1–4 Ziffern>s;`.
- Nichts sonst (kein `proxy_pass`, `alias`, `root`, `return`, `rewrite`, `add_header`, `if`, `set`, fremdes `include`, verschachtelte Blöcke).

Ablauf im Helfer: prüfen → gleich? Ausgang 2 → Sicherung in root-Ordner (`/var/lib/<instanz>-nginx-sicherung/`, nicht im beschreibbaren `FR_DIENST`) → atomar ersetzen → `nginx -t` → bei Fehler Sicherung zurück (und erneut `nginx -t`), Ausgang 4 → `systemctl reload nginx`; scheitert der reload: kein Rückweg (Datei ist getestet), Ausgang 5. Ausgänge: 0 installiert und geladen, 2 nichts zu tun, 3 abgelehnt, 4 `nginx -t` gescheitert und zurückgerollt, 5 reload gescheitert. Unterprozesse ohne `check=True`, feste Pfade, feste Umgebung.

Aufrufer installiert nur, wenn ausschließlich die Orte-Datei abweicht; eine neue Zone in den Orten ohne passende `zone.conf` fängt `nginx -t` ab (Rückweg, Meldung).

### Dependencies
- Upstream: `einrichten.sh --erzeugen` (Soll und Helfer mit eingesetzten Werten), `FR_SUDO`, `/usr/sbin/nginx`, `systemctl reload nginx`.
- Downstream: `veroeffentlichen.sh` (nach grünem Lauf), `wege_pruefen` (sieht neue Orte danach erreichbar), Monitor der Instanz (henemm-infra `monitor.sh`, Konnektor-Pfade).
- Instanz: Umgebungswert `FR_NGINX_HELFER` neu, Verhalten von `nginx_abgleichen` ändert sich → Tests des Reisen-Repos mit dem Branch laufen lassen. Einmalig auf dem Server: Helfer nach `/usr/local/sbin/` (root:root 0755) und sudoers-Zeile; erledigt Claude selbst nach dem Vorspulen.

### Befunde, die gegen den Plan sprechen
- Keiner, der ihn kippt.
- **Rechtegrenze auf diesem Server:** `sudo -l` für hem zeigt `(ALL) NOPASSWD: ALL` (dazu die engen Zeilen). Auf dieser Instanz ist der Helfer daher Schutz vor Fehlern (falsche Vorlage legt den Webserver nicht lahm, keine Pfadüberdeckung), keine Sicherheitsgrenze gegen einen kompromittierten Dienstbenutzer. Außerdem braucht `freischalten.sh` laut `einrichten.sh` ohnehin `install/rm` im Snippets-Ordner per sudo. Die Software baut die Grenze trotzdem richtig (für Instanzen mit engen sudoers); die breite sudo-Regel des Servers ist Sache von henemm-infra und nicht Teil dieses Issues.
- Nebenbefund im Vorbild `units-installieren.py` (ungefangener `daemon-reload`-Fehler) wird mitbehoben.

### Open Questions
- [x] Umfang: nur die Orte-Datei automatisch; `konnektor.inc` (proxy_pass, Kopfzeilen) und `zone.conf` (http-Kontext) bleiben `nginx.py anwenden` (bewusst, höhere Wirkung, ändern sich selten). Technische Entscheidung, keine Produktfrage.
- [x] Whitelist-Variante: (A). Technische Entscheidung.
- Keine offenen Produktfragen.
