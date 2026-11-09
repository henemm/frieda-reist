# Adversary Dialog — feat-445-nginx-orte-automatisch
Spec: docs/specs/betrieb/nginx-orte-automatisch-445.md
Datum: 2026-11-09 17:44

## Checkliste
- [x] **AC-1:** PROVEN. Die aus der echten Vorlage mit `einrichten.sh --erzeugen` erzeugte Orte-Datei besteht die Grammatik und wird installiert. Beleg: `test_ac1_echte_vorlage_aus_einrichten_wird_installiert` (281 passed, adversary-test-output.txt); Code reference: betrieb/vorlagen/nginx-orte-installieren.py:247
- [x] **AC-2:** PROVEN. Regex-Ort ist `(?:konto|abmelden|authorize|gesund)?`; `test_ac2_vorlage_nutzt_nicht_fangende_gruppe_mit_gleicher_wirkung` grün; Code reference: betrieb/vorlagen/nginx-konnektor-orte.inc:68
- [x] **AC-3:** PROVEN. Neue `=`/`^~`-Orte, andere Burst-Werte und Kommentare werden ohne Änderung des Hilfsprogramms akzeptiert (Prüfskript: 'basis one-line', 'leading zeros burst', '^~ /info/', '^~ wellknown oauth-', Kommentare mit `;` und Klammern, 0 Abweichungen); Code reference: betrieb/vorlagen/nginx-orte-installieren.py:82
- [x] **AC-4:** PROVEN. 148 eigene Eingaben (Tab, Mehrfach-Leerzeichen, `;`/`}` in Kommentaren, Block mit Anweisung in der Kopfzeile, Zusatz-Tokens im Kopf, U+2028/U+0085/NBSP/BOM, `#` hinter Anweisung, include-Varianten, `^~ /.well-known/`-Tricks, `.`-Segmente, `^/$`, `(?:)`, `(?:a||b)`, Zahlen mit Vorzeichen, Vollbreiten-Ziffer): 0 Abweichungen vom Soll; Code reference: betrieb/vorlagen/nginx-orte-installieren.py:93
- [x] **AC-5:** PROVEN. include fehlt, include doppelt, jede Anweisung doppelt, doppelter Kopf (auch mit anderer Leerzeichenform) werden abgelehnt; Code reference: betrieb/vorlagen/nginx-orte-installieren.py:113
- [x] **AC-6:** PROVEN. Unverankert, ohne `$`, fangende/verschachtelte/zwei Gruppen, `*`, `+`, `??`, `.`, `~*`, `..`, `//` werden abgelehnt; Code reference: betrieb/vorlagen/nginx-orte-installieren.py:71
- [x] **AC-7:** PROVEN. Symlink, FIFO (kein Hängen dank O_NONBLOCK), Verzeichnis, fehlende Datei ergeben Ausgang 3; Eigentum unter geteuid()==0 per Test `test_ac7_als_root_fremdes_eigentum_lehnt_ab`; Code reference: betrieb/vorlagen/nginx-orte-installieren.py:147
- [x] **AC-8:** PROVEN. 64 KiB + 1, ungültiges UTF-8, jedes Argument, leere Eingabe: Ausgang 3; gleich: Ausgang 2 ohne Sicherung und Reload (auch als Skript ohne Root geprüft, kein Traceback); Code reference: betrieb/vorlagen/nginx-orte-installieren.py:295
- [x] **AC-9:** PROVEN. Sicherung im Root-Ordner vor dem Ersetzen, nach 25 Installationen bleiben 20, Sicherungsordner als Symlink abgelehnt, Fehler beim Schreiben (fchmod-Attrappe) und nur lesbarer Snippets-Ordner lassen keine temporäre Datei zurück; Code reference: betrieb/vorlagen/nginx-orte-installieren.py:173
- [x] **AC-10:** PROVEN (Randfall F002 siehe unten). Ausgänge 4, 5, 6 (beide Fälle), 3 bei Schreibfehler mit Attrappen nachgestellt, Sicherung bleibt und ist in stderr genannt; Code reference: betrieb/vorlagen/nginx-orte-installieren.py:274
- [x] **AC-11:** PROVEN. Sperre belegt: Ausgang 3 'busy', Datei unverändert; danach frei; Sperrdatei als Symlink abgelehnt; Code reference: betrieb/vorlagen/nginx-orte-installieren.py:254
- [x] **AC-12:** PROVEN. Unterprozesse bekommen genau `{PATH: /usr/sbin:/usr/bin:/sbin:/bin}`, stdin DEVNULL, Zeitgrenze 120 s, auch mit gesetztem PATH/PYTHONPATH; Zeitüberschreitung/FileNotFoundError ergeben False ohne Traceback; Code reference: betrieb/vorlagen/nginx-orte-installieren.py:226
- [x] **AC-13:** PROVEN. `test_installieren_nur_orte_abweichend_ruft_das_hilfsprogramm_mit_dem_soll`, `test_installieren_haengt_fr_sudo_vor_das_hilfsprogramm`, Vorgabepfad getestet; Code reference: betrieb/nginx.py:235
- [x] **AC-14:** PROVEN. Parametrisierter Test (zone, konnektor, orte_fehlt, fremde_zone): kein Aufruf, Ausgang 3; Code reference: betrieb/nginx.py:239
- [x] **AC-15:** PROVEN. Hilfsprogramm fehlt oder Ausgang 3/4/5/6/unbekannt: Ausgang 5 mit Meldung; Ausgang 2 in Ordnung; danach erneutes pruefen; Code reference: betrieb/nginx.py:254
- [x] **AC-16:** PROVEN für den Erfolgsfall (Ausgang 0 des Hilfsprogramms): eine Protokollzeile, Merker gelöscht; Code reference: betrieb/veroeffentlichen.sh:665
- [ ] **AC-17:** DISPROVEN. Scheitert der Versuch, die Datei ist danach aber gleich dem Soll (Hilfsprogramm-Ausgang 5 oder 6 Fall b), gibt es keine Meldung (Finding F001); Code reference: betrieb/veroeffentlichen.sh:665
- [x] **AC-18:** PROVEN. `test_veroeffentlichen_nginx_ohne_hilfsprogramm_meldet_einmal`, `test_installieren_ohne_hilfsprogramm_endet_mit_5_ohne_sudo` grün; Code reference: betrieb/nginx.py:243
- [x] **AC-19:** PROVEN. einrichten.sh erzeugt das Hilfsprogramm ohne Platzhalter und nennt Befehl und sudoers-Zeile; FR_NGINX_HELFER/FR_UNITS_HELFER in einstellungen.beispiel; Code reference: betrieb/einrichten.sh:106
- [x] **AC-20:** PROVEN. docs/betrieb.md nennt das Hilfsprogramm, Grammatik, Einmalschritt, Grenze; Docstring in nginx.py und Hinweis in nginx-vorlage-206.md vorhanden; `test_doku_nennt_nginx_orte_hilfsprogramm` grün; Code reference: betrieb/nginx.py:1
- [x] **AC-21:** PROVEN mit Lücke (F004). daemon-reload scheitert: kein Traceback, Ausgang 5, Datei bleibt; units.py behandelt Ausgang 5 über `returncode != 2` als Fehler; Code reference: betrieb/vorlagen/units-installieren.py:184

## Dialog

### Runde 1
**Adversary:** Grammatik angreifen. 148 Eingaben gegen `pruefe` (Prüfskript im Scratchpad, Ausgabe in adversary-test-output.txt): Tab und Mehrfach-Leerzeichen (akzeptiert, wie nginx), Kommentare mit Semikolon, Klammern und U+2028 (akzeptiert, nginx kennt nur LF), schließende Klammer mitten in der Zeile und zwei Blöcke je Zeile (akzeptiert, gleiche Zerlegung wie nginx), Anweisung in der Kopfzeile, Zusatz-Tokens im Kopf, `location` ohne Modifikator, `~*`, benannter Ort `@x` (alle abgelehnt), U+0085 und CR, VT, FF, DEL, NUL auch in Kommentaren (abgelehnt, Kategorie Cc), NBSP, BOM, Vollbreiten-Ziffer, U+2028 als Trenner außerhalb von Kommentaren (abgelehnt, nicht ASCII), Raute hinter Anweisung (abgelehnt), include mit `..`, `//`, Glob, `.bak`, Zusatzwort (abgelehnt), `^~ /.well-known`-Varianten ohne Segmentgrenze und mit `..` (abgelehnt), `=`-Pfade mit `.`, `..`, `//`, `%2e` (abgelehnt), Regex `^/$` (akzeptiert, so in der Spec), `(?:)`, `(?:a||b)`, `(?:|b)`, zwei oder verschachtelte Gruppen, `*`, `+`, `??` (abgelehnt), Zahlen mit Vorzeichen oder vier Ziffern, Vollbreite (abgelehnt), führende Nullen (akzeptiert, Muster 1 bis 3 Ziffern). Ergebnis: 0 Abweichungen von der Spec-Grammatik. Die Tokenzerlegung stimmt mit der von nginx für die erlaubten Zeichen überein; Zeichen, bei denen nginx anders trennen würde (Anführungszeichen, Backslash), sind vorher verboten. Keine Umgehung gefunden. Zwei Randbeobachtungen: `^~ /.well-known/acme-challenge/` ist grammatisch zulässig (F005), eine über 64 KiB große installierte Datei wird im Rückweg gekürzt (F002).
**Implementierer:** (Tests der Spec: 281 passed in den betroffenen Dateien; Gesamtlauf 2052 passed in test-green-output.txt.)

### Runde 2
**Adversary:** Ablauf und Aufrufseite angreifen. Hilfsprogramm mit Attrappen für nginx -t und Reload: Erfolg (0, 0640, ein Test, ein Reload, eine Sicherung, keine temporäre Datei), nginx -t scheitert (4, alter Inhalt, kein Reload), beide nginx -t scheitern (6, alter Stand), Reload scheitert (5, neue Datei bleibt), os.replace im Rückweg scheitert (6, Sicherung bleibt, kein Reload, Pfad in stderr), fchmod scheitert (3, unverändert, keine temporäre Datei), Sperre belegt (3, danach frei), Symlink, FIFO, Verzeichnis, fehlende Datei (alle 3, ohne Hänger), gleich (2 ohne Sicherungsordner), Argument oder keine argv (3), 25 Installationen (20 Sicherungen), Sicherungsordner und Sperrdatei als Symlink (3), nur lesbarer Snippets-Ordner (3, unverändert), nginx fehlt (3, ohne Sicherung), testen wirft RuntimeError (6, Meldung, kein Traceback). Unterprozesse: feste Umgebung trotz gesetztem PATH und PYTHONPATH, Zeitgrenze und FileNotFoundError ergeben False. Als echtes Skript ohne Root: Argument, 70000 Bytes, ungültiges UTF-8, leer, `server {}`: Ausgang 3, nie ein Traceback. Danach nginx_abgleichen mit Attrappe als nginx.py: Das Hilfsprogramm endet mit 5 (Reload gescheitert), die Datei ist danach gleich dem Soll, das zweite pruefen endet mit 0. Ergebnis: keine Meldung, kein Merker, und das Protokoll sagt "installed from the template" (F001). Gleiches gilt für Ausgang 6 Fall (b): die ungetestete neue Datei liegt, pruefen sieht "gleich". Außerdem: stdin geschlossen ergibt Ausgang 6 statt 3 (F003); test_units.py hat keinen Test für units.py installieren mit Hilfsprogramm-Ausgang 5 (F004); die Meldung von nginx_abgleichen enthält bei mehreren Abweichungen die Abweichungsliste doppelt (F006).
**Implementierer:** (offen: F001 muss behoben werden, siehe Remediation)

## Findings

Finding:
  ID: F001
  Severity: HIGH
  Category: spec_violation
  Code reference: betrieb/veroeffentlichen.sh:665
  Description: nginx_abgleichen ruft `installieren` auf, merkt sich nur den Text und ignoriert den Ausgang. Danach entscheidet allein das zweite `pruefen` (Ausgang 0 gleich: Merker löschen, keine Meldung, Protokollzeile "installed from the template"). Endet das Hilfsprogramm mit 5 (Reload gescheitert, Datei installiert) oder mit 6 Fall (b) (Zurückschreiben scheiterte, ungetestete neue Datei liegt), ist die Orte-Datei gleich dem Soll, also schweigt der Lauf. Reproduktion: Attrappe nginx.py, bei der pruefen bis zum installieren mit 3 endet, installieren mit 5 endet und danach pruefen 0 liefert; nginx_abgleichen gibt nur "nginx locations of the connector installed from the template." aus (adversary-test-output.txt, Abschnitt F001).
  Spec requirement: AC-17 — "Bleibt eine Abweichung oder scheitert der Versuch, gibt es genau eine normale Meldung je Fingerabdruck"; Risiko "Reload scheitert" — "Ausgang 5, Meldung ... der Reload gehört dann zur Störungsbehebung (Meldung nennt es)"; Ablauf Schritt 8 — "der Aufrufer meldet Ausgang 6 wie jede andere Abweichung".
  Conflict: Das Neuladen ist gescheitert oder die Datei ist ungetestet, und niemand erfährt es. Ein späterer Lauf findet "gleich" (Ausgang 2) und lädt nie neu. Der neue Ort fehlt im laufenden nginx, oder der nächste Reload aus anderem Anlass (Zertifikatserneuerung) scheitert. Kein Test deckt "Versuch scheitert, danach gleich" ab: _nginx_attrappe kann nach installieren mit 5 nur "weiter abweichend" darstellen.
  Remediation: Den Ausgang von installieren auswerten. Bei Ausgang ungleich 0 und 2 eine normale Meldung senden, auch wenn das zweite pruefen 0 liefert, mit der Zeile "Install attempt: ..." und einem Fingerabdruck, der den Ausgang einschließt (einmal je Fehlerbild); "installed from the template" nur bei Ausgang 0 ausgeben. Test dazu: installieren endet mit 5, danach pruefen 0: genau eine Meldung, kein high, Ausgang 0.

Finding:
  ID: F002
  Severity: MEDIUM
  Category: edge_case
  Code reference: betrieb/vorlagen/nginx-orte-installieren.py:159
  Description: lies_installiert liest höchstens MAX_BYTES + 1 Byte und gibt das ohne Prüfung zurück. Ist die installierte Datei größer als 64 KiB, enthalten Sicherung und Rückweg die gekürzte Fassung (65537 Byte). Reproduktion: installierte Datei 70072 Byte, nginx -t scheitert mit der neuen, Rückweg: wiederhergestellte Datei hat 65537 Byte, Original 70072; die Sicherung ist ebenfalls gekürzt.
  Spec requirement: AC-10 — "Scheitert nginx -t, steht die alte Datei wieder (Inhalt gleich der Sicherung)"; AC-9 — Sicherung des Installierten.
  Conflict: Die alte Datei steht nicht wieder da, die Sicherung ist unbrauchbar. Voraussetzung ist eine von Hand auf über 64 KiB vergrößerte root-eigene Datei, im Normalbetrieb unwahrscheinlich.
  Remediation: In lies_installiert bei mehr als MAX_BYTES Byte ablehnen (Ausgang 3, "installed file too large").

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/vorlagen/nginx-orte-installieren.py:306
  Description: Ein Fehler vor jeder Änderung außerhalb von Abgelehnt (Beispiel: stdin geschlossen, sys.stdin ist None, AttributeError) wird vom allgemeinen `except Exception` mit Ausgang 6 ("Rückweg nicht gesichert") gemeldet, obwohl nichts verändert wurde.
  Spec requirement: Ausgänge — 3 für "vor dem Ersetzen gescheitert ... installierte Datei unverändert", 6 nur für den Rückweg.
  Conflict: Falsche Zuordnung: Der Aufrufer meldet "rollback not secured" für einen harmlosen Fall. Reproduktion: Hilfsprogramm mit geschlossenem fd 0 starten, Ausgang 6, "unexpected error: AttributeError". Unter sudo mit Pipe praktisch nicht erreichbar.
  Remediation: Das Lesen von stdin als Abgelehnt (3) behandeln; den allgemeinen Fang erst nach dem ersten Ersetzen mit 6 melden, davor mit 3.

Finding:
  ID: F004
  Severity: LOW
  Category: anti_pattern
  Code reference: betrieb/vorlagen/units-installieren.py:184
  Description: Der Code für AC-21 ist richtig (kein Traceback, Ausgang 5, Datei bleibt; units.py installieren wertet jeden Ausgang außer 0 und 2 als Fehler und endet mit 5). Der Teil "units.py installieren meldet das als Fehler (Ausgang 5)" hat aber keinen eigenen Test; test_units.py kennt nur "Hilfsprogramm fehlt".
  Spec requirement: AC-21 und Test Plan — "test_units_helfer.py und test_units.py: AC-21".
  Conflict: Der Test Plan nennt test_units.py; dort fehlt der Fall. Zusätzlich startet units.py nach Ausgang 5 den Dauerdienst nicht neu (nicht in geaendert), obwohl die Datei ersetzt ist; ein späterer Lauf findet "gleich".
  Remediation: Test mit Attrappe, die mit 5 endet: units.py installieren endet mit 5 und nennt "install failed (exit 5)". Ausgang 5 zusätzlich zum Neustart zählen oder das Verhalten dokumentieren.

Finding:
  ID: F005
  Severity: LOW
  Category: security
  Code reference: betrieb/vorlagen/nginx-orte-installieren.py:78
  Description: Die Grammatik lässt `location ^~ /.well-known/acme-challenge/` und `location ^~ /.well-known/` zu. Beide leiten dann zum Konnektor um und würden die Abrufe der Zertifikatsprüfung (HTTP-01) überdecken, falls ein Server-Block die Orte-Datei einbindet.
  Spec requirement: Grammatik — `^~` unter /.well-known/ ausdrücklich erlaubt.
  Conflict: Spec-konform, aber eine Fehlbelegung einer künftigen Vorlage würde das Erneuern von Zertifikaten stören. Kein Rechte-Gewinn, nur Verfügbarkeit.
  Remediation: Optional /.well-known/acme-challenge/ ausschließen oder als bekannte Restgefahr in docs/betrieb.md nennen.

Finding:
  ID: F006
  Severity: LOW
  Category: anti_pattern
  Code reference: betrieb/nginx.py:239
  Description: Weicht außer der Orte-Datei noch etwas ab, gibt installieren die vollständige Abweichungsliste samt "To fix"-Block aus (Ausgang 3). nginx_abgleichen hängt diese Ausgabe als "Install attempt: ..." an die Meldung, die dieselbe Liste schon enthält. Die Meldung ist dann doppelt so lang.
  Spec requirement: AC-17 — Meldung nennt das Ergebnis des Versuchs (kurz).
  Conflict: Rauschen, kein Fehlverhalten; die Abweichungsliste ist laut #306 bei den Einheiten bewusst nicht doppelt.
  Remediation: Bei "mehr als die Orte-Datei weicht ab" nur eine Zeile ausgeben (wie bei den Einheiten).

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: betrieb/vorlagen/nginx-orte-installieren.py:247
  Evidence: Echte Vorlage besteht die Grammatik und wird mit Ausgang 0 installiert; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: betrieb/vorlagen/nginx-orte-installieren.py:82
  Evidence: 148 Bypass-Eingaben, 0 Abweichungen; Zeichenprüfung (Cc, ASCII, VERBOTEN) und Tokenzerlegung vor der Block-Auswertung.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: betrieb/vorlagen/nginx-orte-installieren.py:173
  Evidence: Sicherung im Root-Ordner mit O_NOFOLLOW und O_EXCL, 20 bleiben, atomares mkstemp, fsync, replace, Aufräumen bei Fehler.
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: betrieb/nginx.py:235
  Evidence: Aufruf nur bei genau einem Befund der Orte-Datei "differs", Soll über stdin, FR_SUDO und FR_NGINX_HELFER angehängt.
  Status: CONFIRMED

Confirmation:
  AC: AC-19
  Code reference: betrieb/einrichten.sh:106
  Evidence: Hilfsprogramm wird erzeugt, Platzhalterprüfung deckt sbin ab, Ausgabe nennt Befehl und sudoers-Zeile.
  Status: CONFIRMED

Confirmation:
  AC: AC-21
  Code reference: betrieb/vorlagen/units-installieren.py:184
  Evidence: neu_laden() liefert False: Meldung auf stderr und Ausgang 5; Test mit Ausgang 1, FileNotFoundError, Timeout grün.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: BROKEN
═══════════════════════════════════════
Finding F001: Scheitert das Neuladen (Hilfsprogramm-Ausgang 5) oder liegt nach Ausgang 6 Fall (b) eine ungetestete Datei, schweigt nginx_abgleichen, weil das zweite pruefen "gleich" meldet.
  Severity: HIGH
  Evidence: betrieb/veroeffentlichen.sh:665
  Reproduction: Attrappe nginx.py: pruefen endet bis zum Aufruf von installieren mit 3, installieren endet mit 5, danach pruefen mit 0; nginx_abgleichen gibt keine Meldung aus, löscht den Merker und schreibt "installed from the template" (adversary-test-output.txt, Abschnitt F001).
Finding F002: Installierte Datei über 64 KiB wird in Sicherung und Rückweg gekürzt.
  Severity: MEDIUM
  Evidence: betrieb/vorlagen/nginx-orte-installieren.py:159
  Reproduction: installierte Datei 70072 Byte, nginx -t scheitert; wiederhergestellt 65537 Byte.
Finding F003, F004, F005, F006 (alle LOW): siehe oben.

Die Grammatik des Root-Hilfsprogramms hielt 148 Bypass-Eingaben stand; Ablauf, Rückweg, Sperre, O_NOFOLLOW, feste Umgebung und Ausgang 6 sind wie spezifiziert. Der Fehler liegt auf der Aufrufseite von nginx_abgleichen.
Tests: 281 passed, 18 passed (test_betrieb, gefiltert), 0 failed, 0 übersprungen (Gesamtlauf 2052 passed in test-green-output.txt)
Edge cases: F001 bis F006 gefunden, keine Sicherheits-Umgehung
Regressions: keine gefunden
Checklist: 20/21 points proven, AC-17 disproven

## Geprüfte Dateien

- sha256:dd5dbfcea24228c6ea79301b9fd341b9a69adda64f4267ee7fc961e7a808c35c  betrieb/einrichten.sh
- sha256:7e72ee61701a0979dd0b29c0c0ee79fb686df0095946c2a54d4ab02498fe590f  betrieb/nginx.py
- sha256:f2493507463473500981f22ca877df72eb37110acbada08e398637e8184f425f  betrieb/veroeffentlichen.sh
- sha256:bb8ebfe3b310f2fda5ae9a924c0e8ce6f3eebeeb4de77afbe8fe77645a471298  betrieb/vorlagen/nginx-orte-installieren.py
- sha256:efac7411faab0764b06ee82c3c165f13f2e168ff02833f2b9bc42a68276f9dfd  betrieb/vorlagen/units-installieren.py

## Prüfbasis

- base: 89fe69951b8740bff574d514fe103cd6542bf2ed
- blob:792cf09dc4b445f5faddaab806e4a26b043aee4a  betrieb/einrichten.sh
- blob:bee07a08552ccaea13cf8d7b559a55acef64cff2  betrieb/nginx.py
- blob:c95ae08e6bc9b223de59435a82b0df01b405d1af  betrieb/veroeffentlichen.sh
- blob:3c55faf782777fc3007f689f1d982f4a6bb26ffc  betrieb/vorlagen/nginx-orte-installieren.py
- blob:9323b76e10d5d270b17f1d3d593d5b1c72dde35c  betrieb/vorlagen/units-installieren.py
