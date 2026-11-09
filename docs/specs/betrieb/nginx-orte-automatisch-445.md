---
entity_id: nginx-orte-automatisch-445
type: feature
created: 2026-11-09
updated: 2026-11-09
status: draft
workflow: feat-445-nginx-orte-automatisch
---

# Neue Orte der nginx-Vorlage des Konnektors werden beim Software-Wechsel automatisch eingerichtet (#445, Teil 3)

Grundlage: `docs/context/feat-445-nginx-orte-automatisch.md` (Kontext und Analyse). Vorbild für das Hilfsprogramm: `docs/specs/fast/units-installieren-260.md`. Teile 1, 2 und 4 von #445 (Wegeprüfung ohne Alarm, Monitor-Teil-Check): `docs/specs/betrieb/wegepruefung-ohne-alarm-445.md`.

## Approval

- [ ] Approved

## Purpose

Kommt in `betrieb/vorlagen/nginx-konnektor-orte.inc` ein neuer Ort dazu (zuletzt `/info/`, #436), meldet `nginx_abgleichen` (`betrieb/veroeffentlichen.sh`) das nur; bis jemand `nginx.py anwenden` mit Root-Rechten von Hand ausführt, fehlt der Ort auf der Instanz. Das widerspricht der Regel „nach einem Software-Wechsel keine Handarbeit“ (#250). Der Product Owner hat am 9.11.2026 entschieden (Variante b): Wie bei den systemd-Einheiten (#260) installiert ein kleines Hilfsprogramm mit Root-Rechten und enger Whitelist solche Änderungen selbst. Diese Spec löst die Regel „nginx nie automatisch“ aus #206/#316 für genau eine Datei ab, nämlich die Orte-Datei, und nur für Inhalte, die eine feste Grammatik einhalten.

## Abgrenzung

- **Automatisch** wird nur `<instanz>-konnektor-orte.inc` (Snippets-Ordner) installiert.
- `<instanz>-konnektor.inc` (enthält `proxy_pass` und Kopfzeilen) und `<instanz>-zone.conf` (http-Kontext, Drossel-Zonen) sowie das Entfernen einer fremden Zonendefinition bleiben bewusster Schritt (`nginx.py anwenden`, von Hand mit Root-Rechten): höhere Wirkung, ändern sich selten.
- Weicht außer der Orte-Datei noch etwas anderes ab, installiert der automatische Weg nichts; es bleibt bei der Meldung.
- Das Hilfsprogramm ist eine Schutzmaßnahme gegen Fehler (eine falsche Vorlage legt den Webserver nicht lahm; ein Ort kann Reiseseiten nicht über ein Präfix oder eine unverankerte Regex überdecken, nur ein ganzes, gleichnamiges Segment, siehe Grammatik) und gegen Rechte-Ausweitung bei engen sudoers-Regeln. Auf einem Server mit weiter sudo-Regel für den Dienstbenutzer ist es keine Grenze gegen einen kompromittierten Dienstbenutzer; diese Regel ist nicht Teil dieses Issues.
- Einmal je Instanz werden Hilfsprogramm und sudoers-Zeile mit sudo installiert (wie bei #260; auf dieser Instanz erledigt das Claude selbst, siehe „Einmaliger Server-Schritt“); das ist kein wiederkehrender Handschritt.

## Ziel

1. Ein neues Hilfsprogramm `betrieb/vorlagen/nginx-orte-installieren.py` (Root) prüft die Orte-Datei gegen eine feste Grammatik und installiert sie mit Sicherung, `nginx -t`, Rückweg und Reload.
2. `nginx.py installieren` ruft es auf, aber nur, wenn ausschließlich die Orte-Datei abweicht.
3. `nginx_abgleichen` versucht zuerst die Installation; nur was danach noch abweicht, wird einmal je Fingerabdruck gemeldet (normale Meldung, kein Alarm); Veröffentlichen stoppt nie.

## Source

- **Files:** `betrieb/vorlagen/nginx-orte-installieren.py` (neu), `betrieb/nginx.py`, `betrieb/veroeffentlichen.sh`, `betrieb/einrichten.sh`, `betrieb/einstellungen.beispiel`, `betrieb/vorlagen/nginx-konnektor-orte.inc`, `betrieb/vorlagen/units-installieren.py`, `docs/betrieb.md`, `docs/specs/fast/nginx-vorlage-206.md`
- **Identifier:** `nginx_abgleichen`, `nginx.py installieren`, `FR_NGINX_HELFER`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `betrieb/einrichten.sh --erzeugen` | Skript | erzeugt Soll und Hilfsprogramm mit eingesetzten Werten (Instanz, Snippets-Ordner, Zonennamen) |
| `betrieb/nginx.py pruefen` / `anwenden` | Programm | Abgleich und handgemachter Weg; bleiben, `pruefen` liefert zusätzlich die Liste der abweichenden Dateien |
| `betrieb/units.py installieren`, `vorlagen/units-installieren.py` | Programm | Muster (`FR_UNITS_HELFER`, `FR_SUDO`, Ausgang 5, atomares Ersetzen, Tests ohne Root) |
| `FR_SUDO` | Umgebungswert | Vorgabe `sudo -n`; stellt dem Aufruf das sudo voran |
| `/usr/sbin/nginx -t`, `systemctl reload nginx` | Programme | Prüfung und Neuladen im Hilfsprogramm, feste Pfade |
| `betrieb/gemeinsam.sh` `wege_pruefen`, Monitor der Instanz | Funktion/Skript | sehen den neuen Ort nach dem Reload erreichbar; unverändert |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `betrieb/vorlagen/nginx-orte-installieren.py` | CREATE | Hilfsprogramm, Grammatik, Ablauf und Ausgänge wie unten |
| `betrieb/nginx.py` | MODIFY | Neuer Befehl `installieren`; `pruefen` gibt die Liste der abweichenden Dateien intern heraus; Docstring „installiert nie etwas / läuft nie automatisch“ angepasst (Orte-Datei seit #445) |
| `betrieb/veroeffentlichen.sh` | MODIFY | `nginx_abgleichen`: bei Ausgang 3 Installationsversuch, danach `pruefen`; Kommentar „Installiert nie etwas“ angepasst |
| `betrieb/einrichten.sh` | MODIFY | `--erzeugen` erzeugt `sbin/<instanz>-nginx-orte-installieren`; die Ausgabe nennt Installationsbefehl und sudoers-Zeile; zusätzliche Platzhalter-Ersetzung des Helfers gehört in die vorhandene Prüfung „placeholder not replaced“ |
| `betrieb/einstellungen.beispiel` | MODIFY | `FR_NGINX_HELFER` dokumentiert (Test auf Vollständigkeit bleibt grün) |
| `betrieb/vorlagen/nginx-konnektor-orte.inc` | MODIFY | Regex-Ort `(konto|abmelden|authorize|gesund)?` wird zu `(?:konto|abmelden|authorize|gesund)?` (nicht fangende Gruppe, gleiche Wirkung) |
| `betrieb/vorlagen/units-installieren.py` | MODIFY (klein, eigener Commit) | Nebenbefund: `daemon-reload` nach dem Ersetzen mit `check=True` ungefangen |
| `engine/tests/test_nginx_helfer.py` | CREATE | Tests des Hilfsprogramms ohne Root, mit umgelenkten Ordnern |
| `engine/tests/test_nginx.py` | MODIFY | Tests für `nginx.py installieren` |
| `engine/tests/test_betrieb.py` | MODIFY | Tests für `nginx_abgleichen` mit Attrappe (`VF_NGINX`); der bestehende Fall mit `protokoll == ["pruefen"]` wird angepasst |
| `engine/tests/test_units_helfer.py` | MODIFY | Fall für den Nebenbefund |
| `docs/betrieb.md` | MODIFY | Abschnitte zu Orte-Datei, „von Hand/nie automatisch“, Einmalschritt |
| `docs/specs/fast/nginx-vorlage-206.md` | MODIFY (ein Satz) | Hinweis: „nginx nie automatisch“ gilt für die Orte-Datei seit #445 nicht mehr |

### Estimated Changes

ca. +300 Zeilen Code und Tests (Hilfsprogramm ca. 170, `nginx.py` ca. 50, Shell ca. 20, Tests ca. 175), ca. 60 Zeilen Doku, −10. Risiko hoch (Root-Hilfsprogramm, Konfiguration des laufenden Webservers): Gegenprüfung (Adversary) und Sicherheitsprüfung (`/security-review`) vor dem Vorspulen.

## Whitelist-Grammatik

Das Hilfsprogramm prüft den **ganzen** Soll-Text (Strukturprüfung), nicht nur den Unterschied zum Installierten: Es traut weder dem Aufrufer noch dem Altbestand. Die Platzhalter des Hilfsprogramms (`__INSTANZ__`, `__SNIPPETS__`, `__ZONE_MCP__`, `__ZONE_ANMELDEN__`, `__ZONE_KONTO__`) setzt `einrichten.sh` fest ein; Umgebung und Argumente ändern daran nichts.

**Zeichen und Größe.** Eingabe höchstens 64 KiB, gültiges UTF-8. Steuerzeichen außer `\n` und `\t` (auch CR, NUL, DEL) lehnen die ganze Eingabe ab. Außerhalb von Kommentarzeilen nur ASCII; abgelehnt werden dort `"`, `'`, `` ` ``, `\`, `{` und `}` außer als Blockklammer, `<`, `>`, `&`, sowie `$`, `|`, `(`, `)` und `?` überall außer im Pfad eines Regex-Orts genau in der unten beschriebenen Form (`$` nur als letztes Zeichen dieses Pfads, `|`, `(?:` und `)` nur in dessen einer Gruppe, `?` nur als Teil von `(?:` und direkt hinter deren `)`), sowie jede Zeile, die auf `\` endet (Zeilenfortsetzung). Kommentarzeilen (erste Nicht-Leerzeichen-Zeichen `#`, ganze Zeile) und Leerzeilen sind erlaubt und dürfen Umlaute enthalten; ein `#` hinter einer Anweisung ist nicht erlaubt.

**Oberste Ebene.** Nur `location`-Blöcke, Kommentare und Leerzeilen. Kein anderer Block, keine Anweisung außerhalb eines Blocks, keine verschachtelten Blöcke. Ein Block darf mehrzeilig oder in einer Zeile stehen (`location = /token { include …; }`).

**Block-Kopf** `location <Modifikator> <Pfad> {` mit Modifikator `=`, `^~` oder `~`:
- bei `=` und `^~`: Pfad `/[A-Za-z0-9._-][A-Za-z0-9._/-]*`, also mindestens ein Zeichen nach dem führenden `/` (der Pfad `/` allein ist verboten, `location ^~ / {` würde jede Reiseseite überdecken), ohne `..` als Pfadteil und ohne `//`;
- bei `^~` zusätzlich nur an einer Segmentgrenze: Der Pfad endet auf `/` (z. B. `/info/`), **oder** er beginnt mit `/.well-known/` (dort ist auch ein Präfix ohne `/` am Ende erlaubt, z. B. `/.well-known/oauth-`). Begründung: Reiseordner beginnen nach `engine/reise.py` (`PFAD_MUSTER`) immer mit `[a-z0-9]`, nie mit `.`; ein Präfix wie `^~ /r` würde dagegen jede Reise überdecken, deren Name mit `r` beginnt. Verbleibendes Restrisiko, ausdrücklich benannt: Ein ganzer Segment-Ort wie `^~ /info/` überdeckt eine Reise, die genau `info` heißt. Das ist dieselbe Namensraum-Frage wie bisher bei jedem neuen Ort der Vorlage und nicht Aufgabe des Hilfsprogramms (es kennt die Reisen nicht); `=`-Orte treffen nur den genauen Pfad ohne `/` am Ende und überdecken keine Reiseseite;
- bei `~` (Regex): verankert, genau die Form `^/` + Inhalt + `$`, Inhalt entweder leer, ein festes Wort `[A-Za-z0-9_-]+` oder eine einzige nicht fangende Alternativ-Gruppe `(?:wort|wort|…)` mit optionalem `?` dahinter, Wörter aus `[A-Za-z0-9_-]+`. Keine weiteren Sonderzeichen (`.`, `*`, `+`, `[`, `{`, `\`, Rückreferenzen). Fangende Gruppen sind nicht zugelassen; deshalb wird die Vorlage auf `(?:…)` umgestellt;
- derselbe Kopf (Modifikator und Pfad) höchstens einmal in der Datei.

**Anweisungen im Block**, jede höchstens einmal je Block, in beliebiger Reihenfolge, jede mit `;` beendet:
- `limit_req zone=<Zone> burst=<1–3 Ziffern> nodelay;` mit `<Zone>` genau eine der drei eingesetzten Zonen dieser Instanz (`__ZONE_MCP__`, `__ZONE_ANMELDEN__`, `__ZONE_KONTO__`);
- `limit_req_status 429;`
- `include <Snippets-Ordner>/<instanz>-konnektor.inc;` (eingesetzte Werte); **Pflicht, genau einmal je Block**; jedes andere `include` wird abgelehnt;
- `proxy_buffering off;`
- `proxy_read_timeout <1–4 Ziffern>s;`

Alles andere lehnt die ganze Eingabe ab, insbesondere `proxy_pass`, `alias`, `root`, `return`, `rewrite`, `add_header`, `if`, `set`, `try_files`, `error_page`, `access_by_lua*`, `fastcgi_*`, jedes weitere `limit_req_zone`, jede Variable, jeder fremde Block. Die Datei braucht mindestens einen Block.

Die Grammatik steht nur im Hilfsprogramm (eine Quelle); der Aufrufer `nginx.py` prüft sie nicht, sondern übergibt nur und wertet den Ausgang aus. Ein Test lässt die echte Vorlage (erzeugt mit `einrichten.sh --erzeugen`) die Grammatik durchlaufen; eine künftige Vorlagenänderung, die die Grammatik verletzt, scheitert damit schon in der CI.

## Hilfsprogramm: Ablauf und Ausgänge

Datei: `#!/usr/bin/python3 -I`, nur Standardbibliothek, Start ohne Argumente (jedes Argument: Ausgang 3). Gehört auf dem Server root (`/usr/local/sbin/<instanz>-nginx-orte-installieren`, root:root, 0755); die Software kann es nicht ändern. Ziel ist fest: `<Snippets-Ordner>/<instanz>-konnektor-orte.inc`; Pfade, Programme und Umgebung der Unterprozesse sind fest (`/usr/sbin/nginx`, `/usr/bin/systemctl`, `PATH=/usr/sbin:/usr/bin:/sbin:/bin`, `stdin` leer), nichts lässt sich durch Umgebung oder Argumente umlenken. Unterprozesse laufen ohne `check=True` mit Zeitgrenze, ihr Ausgang wird selbst ausgewertet.

1. **Eingabe lesen:** stdin, höchstens 64 KiB (ein Byte mehr: Ausgang 3).
2. **Sperre:** `flock` (exklusiv, nicht blockierend) auf eine feste Sperrdatei im Root-Ordner; ist sie belegt, Ausgang 3 mit Hinweis „busy“.
3. **Grammatik prüfen** (siehe oben); Verstoß: Ausgang 3, Grund auf stderr, nichts verändert.
4. **Installiertes selbst lesen:** `os.open(…, O_NOFOLLOW)`, muss eine reguläre Datei sein, bei Root-Aufruf muss sie root gehören; fehlt sie oder ist sie ein Symlink oder gehört fremd: Ausgang 3 (eine nicht eingerichtete Instanz wird nicht automatisch eingerichtet).
5. **Gleich?** Entspricht die Eingabe byteweise dem Installierten: Ausgang 2, nichts zu tun (ohne Sicherung, ohne Reload).
6. **Sicherung** des Installierten in `/var/lib/<instanz>-nginx-sicherung/` (root, 0700, nicht im für den Dienstbenutzer beschreibbaren `FR_DIENST`), Name mit Zeitstempel; es bleiben die letzten 20.
7. **Atomar ersetzen:** `tempfile.mkstemp` im Snippets-Ordner mit Namen ohne Endung `.conf`/`.inc` (ein Stern-Include bindet halbfertige Dateien nie ein), schreiben, `fsync`, 0640 root:root, `os.replace`.
8. **`nginx -t`.** Besteht er nicht: Sicherung zurück (atomar, gleiche Weise), erneut `nginx -t`, Ausgang 4; es wird nicht neu geladen. Ausgang 6 („Rückweg nicht gesichert“), jeweils ohne Reload und mit Grund auf stderr, in zwei Fällen: (a) der zweite `nginx -t` scheitert ebenfalls („rollback untested“, der alte Stand war schon vorher kaputt, z. B. wegen einer anderen Datei; der alte Stand liegt); (b) das Zurückschreiben der Sicherung selbst scheitert („rollback failed“; dann liegt die ungetestete neue Datei, die Sicherung bleibt im Root-Ordner erhalten und ihr Pfad steht in der Meldung). In beiden Fällen arbeitet der laufende Webserver unverändert mit der zuletzt geladenen Fassung weiter; erst ein späterer Reload würde scheitern, deshalb meldet der Aufrufer Ausgang 6 wie jede andere Abweichung.
9. **`systemctl reload nginx`.** Scheitert er: kein Rückweg (die Datei ist getestet), Ausgang 5.
10. Erfolg: auf stdout nur der Dateiname, Ausgang 0.

Ausgänge: **0** installiert und geladen, **2** nichts zu tun, **3** abgelehnt oder vor dem Ersetzen gescheitert (Grammatik, Eingabe, Installiertes unlesbar/fremd, Sperre belegt, Aufruf, Sicherung/temporäre Datei/`os.replace` gescheitert, `nginx` fehlt), installierte Datei unverändert, **4** `nginx -t` scheiterte, Rückweg erfolgt, **5** Reload scheiterte (Datei ist installiert und getestet), **6** Rückweg nicht gesichert (zweiter `nginx -t` gescheitert oder Zurückschreiben gescheitert, kein Reload). Nach einem Abbruch liegt: bei 3 und 4 der alte Stand, bei 5 ein getesteter neuer Stand, bei 6 der alte Stand (Fall a) oder die ungetestete neue Datei mit erhaltener Sicherung (Fall b); die Datei ist nie halb geschrieben. Jeder Fehler vor dem `os.replace` in Schritt 7 (auch eine Sicherung, die sich nicht anlegen lässt, oder ein Fehler bei `mkstemp`, Schreiben, `fsync`, Rechte setzen) endet ohne Änderung an der installierten Datei mit Ausgang 3 und Grund auf stderr; die temporäre Datei wird entfernt. Ebenso Ausgang 3, wenn `os.replace` selbst scheitert (die alte Datei bleibt, da atomar) oder `/usr/sbin/nginx` vor dem Ersetzen fehlt (das Hilfsprogramm prüft das vorab). Eine überschrittene Zeitgrenze oder ein nicht startbares Programm gilt bei `nginx -t` wie „`nginx -t` scheitert“ (Rückweg, Ausgang 4 bzw. 6), beim Reload wie „Reload scheitert“ (Ausgang 5). Kein Pfad endet mit einem Traceback.

## Aufrufseite

**`nginx.py installieren`** (neu, analog `units.py installieren`): erzeugt das Soll wie `pruefen`. Der Befehl installiert nur, wenn **ausschließlich** `<instanz>-konnektor-orte.inc` abweicht (Soll und Installiertes verschieden); weichen `konnektor.inc`, `zone.conf` oder eine fremde Zonendefinition ab oder fehlt die Orte-Datei, wird kein Hilfsprogramm aufgerufen, die Abweichungen werden wie bei `pruefen` ausgegeben. Der Aufruf ist `$FR_SUDO $FR_NGINX_HELFER` (Vorgabe `/usr/local/sbin/<instanz>-nginx-orte-installieren`) mit dem Soll auf stdin; danach folgt erneut `pruefen`. Ausgang wie `pruefen` (0 gleich, 3 weicht ab, 1 Fehler); **5**, wenn das Hilfsprogramm fehlt oder mit einem Ausgang außer 0 und 2 endet (3, 4, 5, 6 oder unbekannt) (Meldung mit dessen Ausgang und stderr, gekürzt). Ausgang 2 des Hilfsprogramms ist kein Fehler. `FR_NGINX_HELFER` und `FR_SUDO` werden wie bei `units.py` gelesen.

**`nginx_abgleichen`** (`betrieb/veroeffentlichen.sh`), wie `units_abgleichen`: Gibt `pruefen` Ausgang 3, folgt ein Installationsversuch (`installieren`, Ausgang und Ausgabe nur gemerkt, Fehler ignoriert) und danach erneut `pruefen`. Ist danach alles gleich: eine Protokollzeile, der Merker `<FR_DIENST>/nginx-gemeldet` wird gelöscht, keine Meldung. Bleibt eine Abweichung (oder fehlt das Hilfsprogramm, oder wurde es abgelehnt): wie bisher eine normale Meldung je Fingerabdruck, ergänzt um die Zeile „Install attempt: …“ mit dem Ergebnis des Versuchs. Der Fingerabdruck wird nur aus der Ausgabe des zweiten `pruefen` gebildet, nicht aus dem Ergebnis des Versuchs; derselbe Zustand meldet also auch bei wechselndem Versuchsergebnis nur einmal. Kein Alarm; kein Ausgang außer 0; ein Fehler hier stoppt das Veröffentlichen nie.

## Einrichten

- `einrichten.sh --erzeugen` erzeugt `sbin/<instanz>-nginx-orte-installieren` aus der Vorlage mit eingesetzten Werten und nennt am Ende (wie bei den Einheiten) den Installationsbefehl `sudo install -m 755 -o root -g root … /usr/local/sbin/` und die sudoers-Zeile `NOPASSWD: /usr/local/sbin/<instanz>-nginx-orte-installieren` für den Dienstbenutzer. Eine nicht ersetzte Platzhalterzeile bleibt ein Fehler der bestehenden Prüfung.
- `betrieb/einstellungen.beispiel`: `FR_NGINX_HELFER` auskommentiert mit Vorgabewert und Satz „ohne Hilfsprogramm bleibt es bei der Meldung“.

## Nebenbefund: `units-installieren.py`

Im Vorbild `neu_laden` ruft `systemctl daemon-reload` mit `check=True`; ein Fehler dort ergibt einen Traceback und keinen definierten Ausgang, obwohl die Datei schon ersetzt ist. Künftig: Scheitert `daemon-reload`, endet das Hilfsprogramm mit Ausgang 5 und einer Meldung auf stderr (die Datei bleibt installiert), und `units.py` wertet das wie jeden anderen Fehler des Hilfsprogramms (Ausgang 5, Meldung). Eigener Commit.

## Acceptance Criteria

**Grammatik und Ablauf des Hilfsprogramms**

- **AC-1:** Die aus der echten Vorlage mit `einrichten.sh --erzeugen` erzeugte Orte-Datei (Beispielinstanz) besteht die Grammatik und wird installiert (Ausgang 0, Datei hat danach den Soll-Inhalt, 0640, `nginx -t` und Reload wurden je einmal aufgerufen).
- **AC-2:** Die Vorlage verwendet für den Regex-Ort eine nicht fangende Gruppe `(?:konto|abmelden|authorize|gesund)?`; Wirkung unverändert (derselbe Pfadsatz trifft, geprüft mit `re` gegen eine Liste Pfade).
- **AC-3:** Ein neuer, grammatikgerechter Ort (neuer `=`- oder `^~`-Ort mit erlaubten Anweisungen) wird ohne Änderung des Hilfsprogramms akzeptiert; geänderte Burst-Werte und Kommentare ebenso.
- **AC-4:** Jede Anweisung außerhalb der Whitelist und jede Verletzung der Zeichenregeln lehnt die ganze Eingabe mit Ausgang 3 ab; die installierte Datei bleibt unverändert, `nginx` wird nicht aufgerufen (Tabelle unten, alle Zeilen).
- **AC-5:** Fehlt das `include` des eigenen Konnektor-Bausteins in einem Block oder steht es zweimal, wird abgelehnt; jede Anweisung höchstens einmal je Block; derselbe Ortskopf höchstens einmal.
- **AC-6:** Der Ort einer Regex muss verankert und aus festen Wörtern mit höchstens einer nicht fangenden Gruppe bestehen; Pfade mit `..` oder `//` und unverankerte oder fangende Regex werden abgelehnt.
- **AC-7:** Das Hilfsprogramm liest das Installierte selbst mit `O_NOFOLLOW`: Symlink, Nicht-Datei, fehlende Datei (und bei Root-Aufruf fremdes Eigentum) ergeben Ausgang 3.
- **AC-8:** Eingaben über 64 KiB, ungültiges UTF-8 und jedes übergebene Argument ergeben Ausgang 3; ist die Eingabe gleich dem Installierten, endet es mit Ausgang 2 ohne Sicherung und ohne Reload.
- **AC-9:** Vor jedem Ersetzen liegt die Sicherung des Installierten im Root-Ordner `<instanz>-nginx-sicherung` (nicht im Dienstordner), es bleiben die letzten 20; das Ersetzen ist atomar (temporäre Datei im Snippets-Ordner ohne Endung `.conf`/`.inc`, `fsync`, 0640, `os.replace`); bei einem Fehler im Schreiben bleibt keine temporäre Datei zurück.
- **AC-10:** Scheitert `nginx -t`, steht die alte Datei wieder (Inhalt gleich der Sicherung), es gibt keinen Reload, Ausgang 4. Scheitert der Reload, bleibt die getestete neue Datei, Ausgang 5. Scheitert `nginx -t` auch nach dem Rückweg, steht die alte Datei, kein Reload, Ausgang 6; scheitert das Zurückschreiben (Attrappe für `os.replace` im Rückweg), kein Reload, Ausgang 6, die Sicherung ist noch vorhanden und in stderr genannt. Ein Fehler beim Schreiben der temporären Datei ergibt Ausgang 3, die installierte Datei ist unverändert.
- **AC-11:** Läuft bereits ein Lauf (Sperre belegt), endet der zweite mit Ausgang 3 ohne Änderung.
- **AC-12:** Pfade, Programme und Umgebung der Unterprozesse sind fest; eine gesetzte Umgebungsvariable (`PATH`, `PYTHON*`) ändert nichts (Test mit gesetzten Werten; Funktionen werden mit Parametern aufgerufen).

**Aufrufseite**

- **AC-13:** `nginx.py installieren` ruft das Hilfsprogramm genau dann auf, wenn ausschließlich die Orte-Datei abweicht; es übergibt das Soll auf stdin und hängt `FR_SUDO` und `FR_NGINX_HELFER` (Vorgabe `/usr/local/sbin/<instanz>-nginx-orte-installieren`) richtig an.
- **AC-14:** Weicht zusätzlich `konnektor.inc`, `zone.conf` oder eine fremde Zonendefinition ab, oder fehlt die Orte-Datei, wird das Hilfsprogramm nicht aufgerufen und die Abweichungen werden ausgegeben (Ausgang 3).
- **AC-15:** Fehlt das Hilfsprogramm oder endet es mit 3, 4, 5 oder 6, endet `installieren` mit 5 und einer Meldung; Ausgang 2 des Hilfsprogramms gilt als in Ordnung. Nach Erfolg folgt ein erneutes `pruefen` (Ausgang 0).
- **AC-16:** `nginx_abgleichen`: Nach erfolgreichem Installationsversuch gibt es nur eine Protokollzeile, keine Meldung, der Merker `nginx-gemeldet` wird gelöscht.
- **AC-17:** `nginx_abgleichen`: Bleibt eine Abweichung oder scheitert der Versuch, gibt es genau eine normale Meldung je Fingerabdruck (nicht bei jedem Lauf), die auch das Ergebnis des Versuchs nennt; kein Alarm (`high` wird nie gesendet); Ausgang 0 (Veröffentlichen stoppt nie).
- **AC-18:** Ohne installiertes Hilfsprogramm (Pfad aus `FR_NGINX_HELFER` nicht vorhanden): `nginx.py installieren` endet mit 5, ohne `sudo` aufzurufen; `nginx_abgleichen` sendet genau eine normale Meldung je Fingerabdruck, deren Text die Abweichungen und die Zeile `Install attempt: helper missing (<Pfad>)` enthält; kein `high`; Ausgang 0; beim zweiten Lauf mit gleichem Zustand keine weitere Meldung.

**Einrichten, Doku, Nebenbefund**

- **AC-19:** `einrichten.sh --erzeugen` erzeugt `sbin/<instanz>-nginx-orte-installieren` ohne offene Platzhalter und nennt in der Ausgabe Installationsbefehl und sudoers-Zeile; `FR_NGINX_HELFER` steht in `einstellungen.beispiel`, ebenso das bisher fehlende `FR_UNITS_HELFER` (Lücke aus #260) (`test_beispiel_einstellungen_sind_vollstaendig` bleibt grün).
- **AC-20:** `docs/betrieb.md` beschreibt Hilfsprogramm, Whitelist, Einmalschritt (Installieren, sudoers) und die Grenze (nur Orte-Datei; `konnektor.inc` und `zone.conf` bleiben `nginx.py anwenden`); die Sätze „von Hand übernommen / nie automatisch“ gelten nur noch für diese beiden Dateien. `nginx.py`-Docstring und `docs/specs/fast/nginx-vorlage-206.md` tragen den Hinweis auf die Änderung. Ein Doku-Test prüft, dass `docs/betrieb.md` das Hilfsprogramm `nginx-orte-installieren` nennt und die Orte-Datei nicht mehr als „von Hand“ zu übernehmen beschreibt.
- **AC-21:** Scheitert `systemctl daemon-reload` im Einheiten-Hilfsprogramm, gibt es keinen Traceback, sondern eine Meldung auf stderr und Ausgang 5 (Datei bleibt installiert); `units.py installieren` meldet das als Fehler (Ausgang 5).

### Sicherheits-Negativfälle (alle: Ausgang 3, Installiertes unverändert, kein `nginx`-Aufruf)

| Nr. | Eingabe | Grund |
|-----|---------|-------|
| N-1 | Block mit `proxy_pass http://127.0.0.1:1;` | fremde Weiterleitung |
| N-2 | `alias /etc/;` oder `root /;` im Block | Dateizugriff |
| N-3 | `return 200 "x";` / `rewrite ^ /x;` | fremde Umleitung, Anführungszeichen |
| N-4 | `add_header X y;` | Kopfzeile außerhalb des Bausteins |
| N-5 | `if ($x) { … }` / `set $a b;` | Bedingung, Variable, verschachtelter Block |
| N-6 | `include /etc/nginx/other.conf;` oder `include …/<instanz>-konnektor.inc.bak;` | fremdes `include` |
| N-7 | `limit_req zone=fremde burst=1 nodelay;` | fremde Zone |
| N-8 | `limit_req_zone … ;` im Block oder oben | http-Kontext |
| N-9 | `$` außerhalb von Kommentaren an jeder Stelle außer als Abschluss eines Regex-Pfads (z. B. `proxy_read_timeout $x;`, `location = /a$b {`, `location ~ ^/a$b$ {`) | Variable |
| N-10 | `"`, `'`, `` ` `` außerhalb von Kommentaren | Anführungszeichen |
| N-11 | Zeile endet auf `\` | Zeilenfortsetzung |
| N-12 | CR, NUL, anderes Steuerzeichen (auch in Kommentar) | Steuerzeichen |
| N-13 | Nicht-ASCII außerhalb einer Kommentarzeile (z. B. NBSP) | Doppelsinn für nginx |
| N-14 | `location ~ /konto` (unverankert) | Ort überdeckt Reiseseiten |
| N-15 | `location ~ ^/(konto|x)$` (fangende Gruppe) | Capture |
| N-16 | `location ~ ^/.*$`, `location / {`, `location ^~ / {` oder `location = / {` | überdeckt alles bzw. Pfad `/` allein |
| N-29 | `location ^~ /r {` oder `location ^~ /info {` | Präfix ohne Segmentgrenze überdeckt Reiseseiten |
| N-17 | `location = /a/../b` oder `location = //x` | Pfadtrick |
| N-18 | Block ohne `include` des Konnektor-Bausteins | Ort ohne Weiterleitung |
| N-19 | `include` zweimal im Block | Doppelung |
| N-20 | `proxy_read_timeout 99999s;` / `burst=12345` | Zahl außerhalb des Musters |
| N-21 | `server { … }`, `upstream { … }`, Anweisung außerhalb eines Blocks | fremde Ebene |
| N-22 | Block verschachtelt in `location` | Verschachtelung |
| N-23 | Anweisung doppelt im Block (zweimal `limit_req_status 429;`) | höchstens einmal |
| N-24 | derselbe Ortskopf zweimal | doppelter Ort |
| N-25 | Eingabe über 64 KiB / ungültiges UTF-8 / leere Eingabe | Größe, Kodierung, kein Block |
| N-26 | Installierte Datei ist Symlink, Nicht-Datei oder fehlt | `O_NOFOLLOW`, Eigentum |
| N-27 | Argument übergeben (`helfer x`) | Aufruf |
| N-28 | Sperre belegt | gleichzeitiger Lauf |

## Test Plan

- **`engine/tests/test_nginx_helfer.py`** (neu, Muster `test_units_helfer.py`: Hilfsprogramm aus der Vorlage mit eingesetzten Platzhaltern, Funktionen mit Parametern, Testordner statt `/etc`, Attrappen für `nginx -t` und Reload, erfundene Instanz „probe“): AC-1 (echte Vorlage), AC-2, AC-3, AC-4 bis AC-6 (Tabelle N-1 bis N-24 parametrisiert), AC-7, AC-8, AC-9, AC-10 (einschließlich Ausgang 6), AC-11, AC-12, N-25 bis N-29. Ohne Root: Eigentümerprüfung und `fchown` greifen wie im Vorbild nur bei `geteuid() == 0`; der Test ersetzt `os.geteuid` per `monkeypatch` durch 0 und prüft mit einer fremd besessenen Datei (Attrappe von `os.fstat`/`st_uid`) den Ausgang 3 sowie mit einer Attrappe von `os.fchown` den Aufruf mit `(0, 0)`.
- **`engine/tests/test_nginx.py`:** AC-13 bis AC-15 (Attrappe als Hilfsprogramm, das Aufruf und stdin aufzeichnet; Fälle: nur Orte abweichend, zusätzlich `konnektor.inc`/`zone.conf`/fremde Zone, Hilfsprogramm fehlt, Hilfsprogramm Ausgang 2/3/4/5/6 und ein unbekannter Ausgang; die Meldung bei Ausgang 5 nennt den Ausgang des Hilfsprogramms, sodass „fehlt“, „abgelehnt/zurückgerollt“ und „installiert, aber nicht geladen“ unterscheidbar sind).
- **`engine/tests/test_betrieb.py`:** AC-16 bis AC-18 mit Attrappe (`VF_NGINX`): Erfolg ohne Meldung und Merker gelöscht, Scheitern mit einer Meldung (nicht bei jedem Lauf), kein `high`, Ausgang 0; der Fall `protokoll == ["pruefen"]` wird auf die neue Abfolge angepasst. AC-19: neuer Test, der `einrichten.sh --erzeugen` für die Beispielinstanz ausführt und prüft, dass `sbin/<instanz>-nginx-orte-installieren` existiert, keine `__…__`-Platzhalter enthält, mit `#!/usr/bin/python3 -I` beginnt, und dass die Ausgabe den Installationsbefehl nach `/usr/local/sbin/` und die sudoers-Zeile mit `NOPASSWD:` und dem Pfad des Hilfsprogramms nennt; `FR_NGINX_HELFER` und `FR_UNITS_HELFER` über `test_beispiel_einstellungen_sind_vollstaendig`.
- **`engine/tests/test_units_helfer.py` und `test_units.py`:** AC-21, dazu `units.py installieren` endet bei Ausgang 5 des Einheiten-Hilfsprogramms mit 5 (F004).
- **Nachbesserungen nach der Gegenprüfung (Abweichungen 7 und 8, F001–F006):** in `test_nginx_helfer.py` die Fälle `N-30 …` (acme-challenge, parametrisiert wie N-1 bis N-29) sowie `test_f002_…` (installierte Datei über 64 KiB: Ausgang 3) und `test_f003_…` (Fehler vor dem Ersetzen: 3, danach: 6); in `test_betrieb.py` `nginx_abgleichen` mit Attrappe, bei der `installieren` mit 5 endet und das zweite `pruefen` gleich ist (genau eine Meldung, beim zweiten Lauf keine, kein „installed from the template“); in `test_nginx.py` der übersprungene Versuch (`install skipped: other files differ`).
- **`engine/tests/test_nginx.py::test_doku_nennt_nginx_orte_hilfsprogramm`** (neu, AC-20): `docs/betrieb.md` enthält `nginx-orte-installieren` und `FR_NGINX_HELFER`; kein Satz, der `konnektor-orte.inc` nennt, enthält zugleich „von Hand“ oder „nie automatisch“. Der übrige Inhalt von AC-20 (Docstring, Hinweis in der Spec zu #206) per Durchsicht.
- Gesamtlauf: `engine/.venv/bin/python -m pytest -q engine/tests -n auto`, danach die Pflichtprüfungen der CI.
- Beide Reisetypen (ADR-0001): Betrieb ist reiseunabhängig; keine reisespezifischen Werte, alle Adressen und Namen kommen aus `einstellungen.env`.
- Live (nach dem Vorspulen, einmalig): siehe „Einmaliger Server-Schritt“.

## Prüfstelle ADR-0001 (kurz)

Betrieb, nicht Kern: Das Vorhaben berührt weder Grundformen der Reise-Ontologie noch Arten oder Merkmale, enthält nichts Reisespezifisches und nichts Instanzspezifisches in der Software (Pfade, Zonen, Benutzer kommen aus `einstellungen.env` und werden von `einrichten.sh` eingesetzt). Keine neue Fremdbibliothek (nur Standardbibliothek), keine Sprache im Code, keine sichtbaren Texte der Seite oder des Konnektors; Meldungen des Betriebs bleiben englisch wie die bisherigen. Kein Widerspruch zum Kern; die Entscheidung „nginx nie automatisch“ (#206/#316) wird für die Orte-Datei durch den Product Owner (9.11.2026) ausdrücklich abgelöst.

## Risiken

- **Sicherheit (hoch):** Jede nginx-Zeile wirkt als Root-konfigurierter Webserver. Gegenmaßnahmen: Grammatik des ganzen Solls, feste Ziele und Programme, Eingabe nur über stdin, selbst gelesenes Installiertes, `O_NOFOLLOW`, Sperre, Sicherung im Root-Ordner, `nginx -t` mit Rückweg; Gegenprüfung und `/security-review` vor dem Vorspulen.
- **Grammatik zu eng:** Eine künftige legitime Vorlagenänderung (neue Direktive) scheitert am Hilfsprogramm. Gewollt (Sicherheitsentscheidung des Product Owners, wie bei den Einheiten); die CI zeigt es im Test der echten Vorlage, die Instanz bleibt bei der Meldung und dem Handweg `nginx.py anwenden`. Eine Erweiterung der Grammatik ist eine eigene, geprüfte Änderung.
- **Neue Zone ohne `zone.conf`:** Nennt ein Ort eine Zone, die in der installierten `zone.conf` fehlt, fängt `nginx -t` das ab (Rückweg, Ausgang 4, einmalige Meldung); `zone.conf` bleibt Handweg. Dasselbe gilt für Reihenfolge-Abhängigkeiten zwischen den Dateien.
- **Rechtegrenze der Instanz:** Auf einem Server mit weiter sudo-Regel für den Dienstbenutzer (`NOPASSWD: ALL`) ist das Hilfsprogramm Schutz vor Fehlern, nicht vor einem kompromittierten Dienstbenutzer (siehe Abgrenzung); die Software baut die Grenze trotzdem richtig für Instanzen mit engen Regeln.
- **Reload scheitert:** Datei ist getestet und bleibt; Ausgang 5, Meldung; ein späterer Lauf findet „gleich“ (Ausgang 2) und lädt nicht erneut. Der Reload gehört dann zur Störungsbehebung (Meldung nennt es).
- **Zeitfenster:** Zwischen Ersetzen und Reload wirkt die alte Konfiguration weiter; kein Ausfall.
- **Gleichzeitige Sitzungen:** Sperre im Hilfsprogramm; `veroeffentlichen.sh` hat selbst eine Sperre.

## Einmaliger Server-Schritt nach dem Vorspulen

Wie bei #260 einmalig und bewusst; erledigt Claude selbst mit sudo, ohne Auftrag an den Product Owner: (1) `einrichten.sh --erzeugen` ausführen und `sbin/<instanz>-nginx-orte-installieren` nach `/usr/local/sbin/` installieren (root:root, 0755); (2) sudoers-Zeile für den Dienstbenutzer in einer Datei unter `/etc/sudoers.d/` anlegen und mit `visudo -c` prüfen; (3) `nginx.py installieren` einmal aufrufen: bringt `/info/` und alle weiteren neuen Orte der Vorlage auf die Instanz; danach `nginx.py pruefen` mit Ausgang 0, Abruf von `/info/pruefung.webp` mit Kopf `X-Frieda`, `nginx -t` grün, Sicherung im Root-Ordner vorhanden. Der Schritt ist im Issue #445 zu vermerken.

## Instanz-Tests

Ändert sich Verhalten von `veroeffentlichen.sh` und kommt ein neuer Umgebungswert (`FR_NGINX_HELFER`) dazu, laufen vor dem Vorspulen auch die Tests der einbindenden Instanzen mit dem Branch (Anleitung im Reisen-Repo der Instanz); die öffentliche CI kann private Tests nicht ausführen.

## Definition of Done

- [ ] Alle ACs grün; Tabelle N-1 bis N-29 als Tests
- [ ] Gesamte Testsuite und CI-Pflichtprüfungen (`tests (leer)`, `tests (instanz)`, `gitleaks`) grün; Instanz-Tests mit dem Branch grün
- [ ] Gegenprüfung (Adversary) und `/security-review` ohne offenes Finding
- [ ] `docs/betrieb.md`, `nginx.py`-Docstring und `docs/specs/fast/nginx-vorlage-206.md` angepasst
- [ ] Einmaliger Server-Schritt erledigt, `nginx.py pruefen` Ausgang 0, `/info/pruefung.webp` erreicht den Konnektor
- [ ] Issue #445 mit Stand und Server-Schritt kommentiert, erst bei allem Erledigten geschlossen

## Architektur-Entscheidung (ADR)

**ADR-Nr.:** keine neue. Die Entscheidung des Product Owners (9.11.2026, Variante b) und diese Spec lösen die Regel „nginx nie automatisch“ für die Orte-Datei ab; sie stehen im Issue #445 und in `docs/betrieb.md`.

## Abweichungen / offene Punkte

- Gegenüber der Analyse unverändert, mit folgenden Präzisierungen: (1) Ein Block darf einzeilig oder mehrzeilig stehen, weil die Vorlage beides verwendet; (2) die Gruppe der Regex steht ausdrücklich als `(?:…)?` in der Grammatik, `{`, `}`, `(`, `)` sind sonst nur als Block- und Gruppenzeichen zugelassen; (3) Kommentarzeilen dürfen Nicht-ASCII (Umlaute) enthalten, Steuerzeichen nie; (4) derselbe Ortskopf höchstens einmal, mindestens ein Block; (5) bis zu 20 Sicherungen im Root-Ordner bleiben; (6) die Sperre belegt ergibt Ausgang 3 (kein eigener Ausgang), das Hilfsprogramm nimmt keine Argumente.
- (7) Härtung nach der Gegenprüfung (F005): Kein Ort darf `/.well-known/acme-challenge` überdecken (Zertifikatsprüfung): Abgelehnt werden `=`- und `^~`-Pfade, die mit `/.well-known/acme-challenge` beginnen, und `^~`-Präfixe, die selbst Anfang dieses Pfads sind (etwa `/.well-known/` allein oder `/.well-known/a`). Test N-30.
- (8) Nach der Gegenprüfung (F002, F003): Ist die installierte Orte-Datei größer als 64 KiB, lehnt das Hilfsprogramm mit Ausgang 3 ab (nie gekürzt sichern oder vergleichen). Ein unerwarteter Fehler vor jeder Änderung (z. B. stdin nicht lesbar) endet mit Ausgang 3; Ausgang 6 nur, wenn das Ersetzen schon begonnen hat. Dazu (F001, F006): Endet `nginx.py installieren` mit einem Ausgang außer 0 und 2 (etwa 5, Datei installiert, Neuladen gescheitert) und ist die zweite Prüfung gleich, meldet `nginx_abgleichen` trotzdem einmal je Fingerabdruck (aus dem Ausgang); `Install attempt:` nennt nur die letzte Zeile der Ausgabe des Versuchs, bei übersprungenem Versuch `install skipped: other files differ …`.
- Keine offenen Produktfragen.

## Changelog

- 2026-11-09: Erstfassung (Teil 3 aus #445).
- 2026-11-09: Nachbesserungen nach Gegenprüfung (F001–F006)
