# Adversary Dialog — feat-445-nginx-orte-automatisch
Spec: docs/specs/betrieb/nginx-orte-automatisch-445.md
Datum: 2026-11-09 18:47

## Checkliste
- [x] **AC-1:** Die aus der echten Vorlage mit `einrichten.sh --erzeugen` erzeugte Orte-Datei (Beispielinstanz) besteht die Grammatik und wird installiert (Ausgang 0, Datei hat danach den Soll-Inhalt, 0640, `nginx -t` und Reload wurden je einmal aufgerufen).
- [x] **AC-2:** Die Vorlage verwendet für den Regex-Ort eine nicht fangende Gruppe `(?:konto|abmelden|authorize|gesund)?`; Wirkung unverändert (derselbe Pfadsatz trifft, geprüft mit `re` gegen eine Liste Pfade).
- [x] **AC-3:** Ein neuer, grammatikgerechter Ort (neuer `=`- oder `^~`-Ort mit erlaubten Anweisungen) wird ohne Änderung des Hilfsprogramms akzeptiert; geänderte Burst-Werte und Kommentare ebenso.
- [x] **AC-4:** Jede Anweisung außerhalb der Whitelist und jede Verletzung der Zeichenregeln lehnt die ganze Eingabe mit Ausgang 3 ab; die installierte Datei bleibt unverändert, `nginx` wird nicht aufgerufen (Tabelle unten, alle Zeilen).
- [x] **AC-5:** Fehlt das `include` des eigenen Konnektor-Bausteins in einem Block oder steht es zweimal, wird abgelehnt; jede Anweisung höchstens einmal je Block; derselbe Ortskopf höchstens einmal.
- [x] **AC-6:** Der Ort einer Regex muss verankert und aus festen Wörtern mit höchstens einer nicht fangenden Gruppe bestehen; Pfade mit `..` oder `//` und unverankerte oder fangende Regex werden abgelehnt.
- [x] **AC-7:** Das Hilfsprogramm liest das Installierte selbst mit `O_NOFOLLOW`: Symlink, Nicht-Datei, fehlende Datei (und bei Root-Aufruf fremdes Eigentum) ergeben Ausgang 3.
- [x] **AC-8:** Eingaben über 64 KiB, ungültiges UTF-8 und jedes übergebene Argument ergeben Ausgang 3; ist die Eingabe gleich dem Installierten, endet es mit Ausgang 2 ohne Sicherung und ohne Reload.
- [x] **AC-9:** Vor jedem Ersetzen liegt die Sicherung des Installierten im Root-Ordner `<instanz>-nginx-sicherung` (nicht im Dienstordner), es bleiben die letzten 20; das Ersetzen ist atomar (temporäre Datei im Snippets-Ordner ohne Endung `.conf`/`.inc`, `fsync`, 0640, `os.replace`); bei einem Fehler im Schreiben bleibt keine temporäre Datei zurück.
- [x] **AC-10:** Scheitert `nginx -t`, steht die alte Datei wieder (Inhalt gleich der Sicherung), es gibt keinen Reload, Ausgang 4. Scheitert der Reload, bleibt die getestete neue Datei, Ausgang 5. Scheitert `nginx -t` auch nach dem Rückweg, steht die alte Datei, kein Reload, Ausgang 6; scheitert das Zurückschreiben (Attrappe für `os.replace` im Rückweg), kein Reload, Ausgang 6, die Sicherung ist noch vorhanden und in stderr genannt. Ein Fehler beim Schreiben der temporären Datei ergibt Ausgang 3, die installierte Datei ist unverändert.
- [x] **AC-11:** Läuft bereits ein Lauf (Sperre belegt), endet der zweite mit Ausgang 3 ohne Änderung.
- [x] **AC-12:** Pfade, Programme und Umgebung der Unterprozesse sind fest; eine gesetzte Umgebungsvariable (`PATH`, `PYTHON*`) ändert nichts (Test mit gesetzten Werten; Funktionen werden mit Parametern aufgerufen).
- [x] **AC-13:** `nginx.py installieren` ruft das Hilfsprogramm genau dann auf, wenn ausschließlich die Orte-Datei abweicht; es übergibt das Soll auf stdin und hängt `FR_SUDO` und `FR_NGINX_HELFER` (Vorgabe `/usr/local/sbin/<instanz>-nginx-orte-installieren`) richtig an.
- [x] **AC-14:** Weicht zusätzlich `konnektor.inc`, `zone.conf` oder eine fremde Zonendefinition ab, oder fehlt die Orte-Datei, wird das Hilfsprogramm nicht aufgerufen und die Abweichungen werden ausgegeben (Ausgang 3).
- [x] **AC-15:** Fehlt das Hilfsprogramm oder endet es mit 3, 4, 5 oder 6, endet `installieren` mit 5 und einer Meldung; Ausgang 2 des Hilfsprogramms gilt als in Ordnung. Nach Erfolg folgt ein erneutes `pruefen` (Ausgang 0).
- [x] **AC-16:** `nginx_abgleichen`: Nach erfolgreichem Installationsversuch gibt es nur eine Protokollzeile, keine Meldung, der Merker `nginx-gemeldet` wird gelöscht.
- [x] **AC-17:** `nginx_abgleichen`: Bleibt eine Abweichung oder scheitert der Versuch, gibt es genau eine normale Meldung je Fingerabdruck (nicht bei jedem Lauf), die auch das Ergebnis des Versuchs nennt; kein Alarm (`high` wird nie gesendet); Ausgang 0 (Veröffentlichen stoppt nie).
- [x] **AC-18:** Ohne installiertes Hilfsprogramm (Pfad aus `FR_NGINX_HELFER` nicht vorhanden): `nginx.py installieren` endet mit 5, ohne `sudo` aufzurufen; `nginx_abgleichen` sendet genau eine normale Meldung je Fingerabdruck, deren Text die Abweichungen und die Zeile `Install attempt: helper missing (<Pfad>)` enthält; kein `high`; Ausgang 0; beim zweiten Lauf mit gleichem Zustand keine weitere Meldung.
- [x] **AC-19:** `einrichten.sh --erzeugen` erzeugt `sbin/<instanz>-nginx-orte-installieren` ohne offene Platzhalter und nennt in der Ausgabe Installationsbefehl und sudoers-Zeile; `FR_NGINX_HELFER` steht in `einstellungen.beispiel`, ebenso das bisher fehlende `FR_UNITS_HELFER` (Lücke aus #260) (`test_beispiel_einstellungen_sind_vollstaendig` bleibt grün).
- [x] **AC-20:** `docs/betrieb.md` beschreibt Hilfsprogramm, Whitelist, Einmalschritt (Installieren, sudoers) und die Grenze (nur Orte-Datei; `konnektor.inc` und `zone.conf` bleiben `nginx.py anwenden`); die Sätze „von Hand übernommen / nie automatisch“ gelten nur noch für diese beiden Dateien. `nginx.py`-Docstring und `docs/specs/fast/nginx-vorlage-206.md` tragen den Hinweis auf die Änderung. Ein Doku-Test prüft, dass `docs/betrieb.md` das Hilfsprogramm `nginx-orte-installieren` nennt und die Orte-Datei nicht mehr als „von Hand“ zu übernehmen beschreibt.
- [x] **AC-21:** Scheitert `systemctl daemon-reload` im Einheiten-Hilfsprogramm, gibt es keinen Traceback, sondern eine Meldung auf stderr und Ausgang 5 (Datei bleibt installiert); `units.py installieren` meldet das als Fehler (Ausgang 5).

## Dialog

### Runde 1
**Adversary:** Gezielt F001 und F002 aus Iteration 1 angegriffen. F001: `nginx_abgleichen` mit Attrappe von `nginx.py` (Ausgang von installieren 0, 2, 5, 6, 1; zweite Pruefung gleich oder abweichend; je zwei Laeufe), Ausgabe in `adversary-test-output.txt`. F002: `lies_installiert` mit Dateien von genau 64 KiB und 64 KiB + 1 Byte durchgedacht (Leseschleife liest MAX_BYTES+1, `rest <= 0` heisst zu gross).
**Implementierer:** Die Korrektur steht im Code; Tests `test_veroeffentlichen_nginx_installiert_aber_reload_gescheitert_meldet_einmal` und `test_f002_installierte_datei_groesser_als_64_kib_wird_nicht_gekuerzt_gesichert` decken beide Faelle ab. 355 gezielte Tests gruen.
**Befund Adversary:** F001 behoben. Bei Ausgang 5, 6 oder 1 und gleicher zweiter Pruefung wird `rc=3` gesetzt und genau eine normale Meldung mit `Install attempt:` gesendet, Fingerabdruck aus dem festen Text mit dem Ausgang; Lauf 2 meldet nicht erneut, kein `high`, Ausgang 0. Die Protokollzeile `installed from the template` erscheint nur bei Ausgang 0 oder 2, nie bei 5/6/1. F002 behoben: Datei ueber 64 KiB wird abgelehnt statt gekuerzt gesichert, genau 64 KiB bleibt zulaessig.

### Runde 2
**Adversary:** Neue Luecken durch die Korrektur gesucht: (a) Entprellung: nach Ausgang 5 mit gleicher Pruefung loescht der Folgelauf (Zustand gleich) den Merker still, es gibt keine zweite Meldung; entsteht der gleiche Fehler spaeter neu, meldet es erneut (erwuenscht, ein neues Ereignis). (b) Ausgang 2 des Helfers bei abweichender erster Pruefung ist praktisch nicht erreichbar, wuerde aber als installiert protokolliert. (c) Ausgang 1 von `nginx.py installieren` (Erzeugungsfehler) mit anschliessend gleicher Pruefung bekommt den Text "not reloaded or not secured", der dann irrefuehrend ist. (d) `units-installieren.py`: daemon-reload scheitert gibt Ausgang 5 ohne Traceback (AC-21). (e) Runde-1-Belege fuer AC-1 bis AC-20 wiederverwendet, da Stellen unveraendert; Gesamtlauf der gezielten Tests gruen.
**Implementierer:** keine Rueckmeldung noetig, nur Hinweise niedriger Schwere.

## Findings

Finding:
  ID: F007
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:671
  Description: Endet `nginx.py installieren` mit 1 (Fehler) und ist die zweite Pruefung danach gleich, lautet der Meldetext "not reloaded or not secured", was fuer Ausgang 1 nicht stimmt.
  Spec requirement: AC-17 — genau eine normale Meldung, die das Ergebnis des Versuchs nennt
  Conflict: Die Meldung kommt genau einmal und nennt den Ausgang, nur die Erklaerung ist unscharf.
  Remediation: Text ohne Deutung oder Ausgang 1 getrennt erklaeren.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: betrieb/einrichten.sh:107
  Evidence: erzeugt das Hilfsprogramm aus der Vorlage; test_nginx_helfer (echte Vorlage) gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-2 bis AC-6, AC-8 bis AC-12
  Code reference: betrieb/vorlagen/nginx-orte-installieren.py:92
  Evidence: Grammatik `pruefe` und Installationsablauf (Zeile 260); F002-Korrektur Zeile 157 bis 179 (Leseschleife, Ablehnung ueber 64 KiB); Tests gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: betrieb/vorlagen/nginx-orte-installieren.py:160
  Evidence: O_NOFOLLOW, S_ISREG, Eigentuemerpruefung bei Root.
  Status: CONFIRMED

Confirmation:
  AC: AC-13 bis AC-15, AC-18
  Code reference: betrieb/nginx.py:239
  Evidence: `installieren` ruft den Helfer nur bei ausschliesslich abweichender Orte-Datei, 5 bei fehlendem Helfer oder Ausgang 3/4/5/6 (Zeile ~253 bis 268), Ausgabe `helper missing (<Pfad>)` ohne sudo-Aufruf.
  Status: CONFIRMED

Confirmation:
  AC: AC-16, AC-17, AC-18 (F001 behoben)
  Code reference: betrieb/veroeffentlichen.sh:662
  Evidence: Angriffsskript: Ausgang 5/6/1 bei gleicher zweiter Pruefung ergibt genau eine Meldung, Lauf 2 keine; Ausgang 0/2 nur Protokollzeile; nie high; Ausgang immer 0.
  Status: CONFIRMED

Confirmation:
  AC: AC-19
  Code reference: betrieb/einrichten.sh:141
  Evidence: Ausgabe nennt Installationsbefehl und sudoers-Zeile; Test gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-20
  Code reference: betrieb/nginx.py:3
  Evidence: Docstring mit Hinweis auf #445; Doku-Test gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-21
  Code reference: betrieb/vorlagen/units-installieren.py:124
  Evidence: neu_laden gibt False mit Meldung auf stderr, installieren gibt 5 (Zeile 184); test_units gruen.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED
Tests: 355 passed, 0 failed, 0 uebersprungen (gezielte Dateien); Gesamtlauf 2062 passed laut Vorlauf.
Edge cases: F001 und F002 behoben, nur F007 (LOW, Textschaerfe) offen.
Regressions: None found
Checklist: 21/21 points proven

## Geprüfte Dateien

- sha256:dd5dbfcea24228c6ea79301b9fd341b9a69adda64f4267ee7fc961e7a808c35c  betrieb/einrichten.sh
- sha256:acb87b37dbadb399d5a47c8bf2071b9c14f0765fa6ac8c27097d7737f00c2452  betrieb/nginx.py
- sha256:a3dd1aada577e36ac04b45925ad65c371959b23a7c0233056e00b2fa1d01887a  betrieb/veroeffentlichen.sh
- sha256:97c8550978e48d708a04d47d996d31672543158b470ffe1268485bb7410f0803  betrieb/vorlagen/nginx-orte-installieren.py
- sha256:efac7411faab0764b06ee82c3c165f13f2e168ff02833f2b9bc42a68276f9dfd  betrieb/vorlagen/units-installieren.py

## Prüfbasis

- base: 89fe69951b8740bff574d514fe103cd6542bf2ed
- blob:792cf09dc4b445f5faddaab806e4a26b043aee4a  betrieb/einrichten.sh
- blob:f99e3788a2e14996aee0eb7b9d36a38d0072565f  betrieb/nginx.py
- blob:9aa308bb3666368fb2e855b49a135be0361c1f00  betrieb/veroeffentlichen.sh
- blob:f57b33765615704db6fca0f5efe037e2720aefec  betrieb/vorlagen/nginx-orte-installieren.py
- blob:9323b76e10d5d270b17f1d3d593d5b1c72dde35c  betrieb/vorlagen/units-installieren.py
