# Adversary Dialog — sicherheit-552-dienstrechte
Spec: docs/specs/betrieb/dienstrechte-552.md
Datum: 2026-11-13 13:01

## Checkliste
- [x] **Input:** Reisename (Helfer auf stdin), Anfragen an Konnektor und Rückmeldedienst wie bisher, `GET /<reise>/rolle?person=…` am Schreibweg (nur mit Dienstkopf).
- [x] **Output:** Helfer: Pfad des Bausteins oder Ausgang 2 bis 6; Rollenabfrage: Rolle aus dem aktuellen Stand oder `null`; abgelehnte Aktionen mit einer Meldung aus dem Textkatalog.
- [x] **Side effects:** Netzdienste und Schreibweg laufen in engerer Sandbox; Reise-Bausteine entstehen nur noch über den Helfer; Sperren liegen in `FR_DIENST`; `/token` und `/register` sind gedrosselt; Einladungen entstehen erst nach geprüftem Schreiben.
- [x] **AC-1:** (Netzdienste ohne Docker) GIVEN die Vorlagen von `konnektor`, `rueckmeldungen`, `push` WHEN sie erzeugt werden THEN enthält jede `NoNewPrivileges=yes` und `InaccessiblePaths=-/run/docker.sock`. Test: `test_betrieb.py::test_netzdienste_ohne_docker_und_sudo`.
- [x] **AC-2:** (Schreibweg-Sandbox) GIVEN die Vorlage `schreiben.service` WHEN sie erzeugt wird THEN stehen `ProtectSystem=strict`, `ProtectHome=read-only`, `InaccessiblePaths=-/run/docker.sock` und eine `ReadWritePaths=`-Liste darin, die genau die Ziele des Messlaufs (Schreibkopie, Bauordner mit `.git`, `FR_DIENST`, `FR_KONTEN`, Reisespeicher, Sperren, ggf. `gh`-Anmeldung) enthält. Test: `test_betrieb.py::test_schreiben_unit_sandbox`.
- [x] **AC-3:** (Messlauf) GIVEN die Instanz mit der neuen Unit WHEN `betrieb/messlauf-schreibweg.py` einen vollständigen Schreibvorgang samt Hochladen und Veröffentlichen ausführt THEN meldet er keinen verweigerten Schreibzugriff; das Protokoll des Laufs liegt unter `docs/artifacts/` (ohne Pfade der Instanz), das Issue verweist darauf. Test: `test_betrieb.py::test_messlauf_deckt_readwritepaths` (die Ziele, die `messlauf-schreibweg.py` prüft, und die `ReadWritePaths` der Vorlage sind dieselbe Liste). Ausnahme mit Begründung: Der Lauf selbst braucht systemd und die echte Instanz und läuft deshalb nicht in CI; er wird bei der Umstellung und nach jeder Änderung der Liste wiederholt, das Protokoll liegt unter `docs/artifacts/`.
- [x] **AC-4:** (Reise-Helfer, Grammatik) GIVEN der Helfer WHEN die Eingabe kein Reisename nach Muster ist (Großbuchstaben, `..`, `/`, Leerzeichen, zu lang, leer, Zeilenumbruch, Argument) THEN Ausgang 3, nichts verändert, `nginx` nicht aufgerufen. Test: `test_nginx_reise_helfer.py::test_eingabe_grammatik`.
- [x] **AC-5:** (Reise-Helfer, Token und Ersetzen) GIVEN eine Reise ohne Baustein WHEN der Helfer läuft THEN entsteht der Baustein (0640, root) mit einem neuen Token und die Ausgabe ist nur der Pfad; GIVEN ein vorhandener Baustein WHEN der Helfer erneut läuft THEN bleibt der Token gleich (Ausgang 2, wenn alles gleich, sonst Erneuerung mit gleichem Token). Test: `test_nginx_reise_helfer.py::test_token_bleibt`.
- [x] **AC-6:** (Reise-Helfer, Rückweg) GIVEN `nginx -t` scheitert WHEN der Helfer ersetzt hat THEN steht der alte Baustein wieder, kein Reload, Ausgang 4; scheitert auch der zweite `nginx -t` oder das Zurückschreiben, Ausgang 6, Sicherung bleibt; scheitert der Reload, Ausgang 5. Test: `test_nginx_reise_helfer.py::test_rueckweg_und_ausgaenge`.
- [x] **AC-7:** (Reise-Helfer, feste Umgebung) GIVEN gesetzte `PATH`, `PYTHON*` und ein vom Aufrufer geschriebener Eingabepfad WHEN der Helfer läuft THEN ändern sie nichts; Vorlage und Werte stammen nur aus der Datei. Der Lesemodus liefert nur den Pfad oder Ausgang 2, nie den Inhalt. Test: `test_nginx_reise_helfer.py::test_umgebung_fest`, `test_nginx_reise_helfer.py::test_lesemodus`.
- [x] **AC-8:** (kein sudo außer Helfern) GIVEN `betrieb/*.sh` und `betrieb/nginx.py` WHEN nach `sudo` gesucht wird THEN stehen nur `$FR_SUDO <Helfer>` und `systemctl restart` der eigenen Dienste darin; `freischalten.sh` und `nginx.py` laufen gegen eine Attrappe des Helfers und legen Baustein, Link und `seiten.json` wie bisher an. Test: `test_betrieb.py::test_nur_helfer_mit_sudo`, `test_nginx.py::test_reise_baustein_ueber_helfer`.
- [x] **AC-9:** (Einrichten) GIVEN `einrichten.sh --erzeugen` für die Beispielinstanz WHEN es läuft THEN gibt es Helfer und Karte-Skript ohne offene Platzhalter, die Ausgabe nennt Installationsbefehl und sudoers-Zeilen nur für Helfer, keinen `usermod -aG docker` für den Dienstbenutzer, aber Anlage und Gruppe von `<instanz>-karte`. Test: `test_betrieb.py::test_einrichten_helfer_und_karte`.
- [x] **AC-10:** (Kartendienst) GIVEN die Kartendienst-Einheiten WHEN sie erzeugt werden THEN läuft Docker nur unter `<instanz>-karte`, und `ExecStart` und `EnvironmentFile` liegen weder im Repo noch in einem Ordner des Dienstbenutzers; die Sperre gegen das Veröffentlichen wird nur lesend geöffnet. Test: `test_kartendienst.py::test_kartendienst_ohne_dienstbenutzer`.
- [x] **AC-11:** (Drossel) GIVEN die echte Orte-Vorlage WHEN sie die Grammatik des Orte-Helfers durchläuft THEN wird sie angenommen (Ausgang 0) und `/token` und `/register` tragen `limit_req zone=_mcp burst=40 nodelay`; `nginx.py pruefen` liest den installierten Baustein ohne sudo (für `FR_GRUPPE` lesbar, AC-21) und meldet bei der Instanz die Abweichung, `nginx.py installieren` behebt sie ohne Handschritt. Test: `test_nginx_helfer.py::test_echte_vorlage_mit_drossel`.
- [x] **AC-12:** (Sperren) GIVEN keine ausdrückliche Einstellung WHEN `gemeinsam.sh`, `kartendienst.sh` und `sperrdatei()` Sperren benennen THEN liegen sie in `FR_DIENST`; GIVEN `FR_SPERREN=/tmp` in einer Instanz WHEN `neu.py nachziehen` bzw. das Einrichten läuft THEN ist die Zeile weg (zweiter Lauf: keine Änderung). Test: `test_schreiben.py::test_sperrdatei_in_dienstordner`, `test_betrieb.py::test_sperren_nicht_in_tmp`, `test_neu.py::test_nachziehen_sperren`.
- [x] **AC-13:** (Einheiten nicht automatisch) GIVEN `ERLAUBT` in `units.py` und `units-installieren.py` WHEN die Listen verglichen werden THEN sind sie gleich und enthalten keine Sandbox- oder Benutzerzeile; GIVEN eine installierte Unit ohne die neuen Werte THEN meldet `units.py pruefen` eine gesperrte Abweichung (einmalige Meldung, kein Alarm). Test: `test_units.py::test_sandbox_nicht_in_erlaubnisliste`.
- [x] **AC-14:** (Rollenabfrage) GIVEN eine Person, die in `reise.yaml` Gast ist, im veröffentlichten Stand aber Organisator:in WHEN `GET /<reise>/rolle?person=…` am Schreibweg läuft THEN `gast`; ohne Kopf `X-Frieda-Dienst` 403; unbekannte Person `rolle: null`; die Abfrage ändert keinen Stand. Beide Arten (Speicher-Reise und Git-Reise) und beide Beispielreisen. Test: `test_schreiben.py::test_rolle_lesen`.
- [x] **AC-15:** (Einladen) GIVEN eine neue Person und der Schreibweg lehnt `person_schreiben` ab (Rolle der Einladenden in `reise.yaml` zu klein) WHEN `einladen` läuft THEN keine Mail, keine Zeile in `einladungen.json`, keine Konto-Verknüpfung; GIVEN er gelingt THEN erst `einladungen.json`, dann Mail; GIVEN eine vorhandene Person mit Konto-Verknüpfung und herabgestufter Einladender THEN abgelehnt. Test: `test_konnektor.py::test_einladen_erst_schreibweg`.
- [x] **AC-16:** (Rückmeldung erledigen) GIVEN eine herabgestufte Person WHEN `rueckmeldung_erledigen` läuft THEN abgelehnt, kein PATCH; GIVEN der Schreibweg ist eingerichtet, aber nicht erreichbar THEN „Rolle nicht prüfbar“, kein PATCH; GIVEN der Schreibweg ist nicht eingerichtet THEN gilt wie bisher der veröffentlichte Stand. Test: `test_konnektor.py::test_erledigen_rolle_aktuell`.
- [x] **AC-17:** (Wunsch einplanen) GIVEN eine herabgestufte Person WHEN die Seite `eingeplant` setzt THEN 403, Brett unverändert; GIVEN eine Organisator:in THEN geht es durch; Punkte und `erlebt` bleiben unverändert. Test: `test_rueckmeldungen.py::test_wunsch_einplanen_rolle_aktuell`.
- [x] **AC-18:** (Texte) GIVEN die neuen Meldungen WHEN `test_texte.py` läuft THEN stehen sie in `texte_de.py` und `texte_en.py`, die Ausnahmelisten wachsen nicht. Test: `test_texte.py::test_paritaet_schluessel_und_platzhalter` (vorhandener Test, deckt die neuen Schlüssel ab).
- [x] **AC-19:** (Doku) GIVEN `docs/betrieb.md` WHEN gelesen THEN beschreibt sie den neuen Helfer, den Kartendienst-Benutzer, die Sandbox, den Einmalschritt und die Warnung zum Admin-Benutzer; ein Test prüft die Nennung von `nginx-reise-installieren` und `<instanz>-karte` und dass keine sudoers-Zeile für `install`, `cat`, `rm`, `nginx` empfohlen wird. Test: `test_betrieb.py::test_doku_beschreibt_dienstrechte`.
- [x] **AC-20:** (Instanz umgestellt, Teil von „fertig“) GIVEN die Software ist ausgeliefert WHEN die Instanz mit `einrichten.sh --erzeugen` und `--installieren` umgestellt ist THEN gilt: die Units tragen die neuen Werte, die Helfer liegen in `/usr/local/sbin`, die sudoers-Datei nennt nur Helfer, der Kartendienst läuft unter `<instanz>-karte`, `units.py pruefen` und `nginx.py pruefen` enden mit 0, Veröffentlichen, Schreiben, Freischalten einer frischen Testreise und Kartenaktualisierung laufen durch, die Netzdienste erreichen den Docker-Socket nicht. Dazu gilt: die installierten nginx-Bausteine der Instanz tragen `0640 root:<FR_GRUPPE>` (AC-21), die Kartendaten liegen unter `/var/lib/<instanz>-kartendienst/` hinter dem Verweis (AC-22). Test: `test_betrieb.py::test_einrichten_installieren_attrappe` (der Installationsweg gegen umgelenkte Ziele). Ausnahme mit Begründung: Die Umstellung der echten Instanz braucht Root auf ihrem Server und lässt sich nicht in CI prüfen; der Nachweis sind die Ausgänge von `units.py pruefen` und `nginx.py pruefen` (0) und die Läufe oben, festgehalten im privaten Issue der Instanz. Erst dann wird #552 geschlossen.
- [x] **AC-21:** (nginx-Bausteine für die Gruppe lesbar, Entscheidung 9) GIVEN der Orte-Helfer, der Reise-Helfer oder `nginx.py anwenden` mit Root-Rechten WHEN sie einen Baustein der Instanz installieren THEN trägt er `0640 root:<FR_GRUPPE>`, eine fremde Datei in `conf.d` behält Modus und Besitz, und der Befehl in der Meldung von `nginx.py` nennt `FR_GRUPPE`; GIVEN installierte Bausteine WHEN `nginx.py pruefen` läuft THEN liest es sie ohne sudo und überspringt unlesbare fremde Dateien ohne Fehler; GIVEN vorhandene Bausteine mit altem Besitz WHEN `einrichten.sh --installieren` läuft THEN stellt es sie einmalig um (zweiter Lauf: keine Änderung). Test: `test_nginx.py::test_anwenden_installiert_mit_gruppe_der_instanz`, `test_nginx.py::test_befehl_nennt_die_gruppe`, `test_nginx.py::test_pruefen_liest_ohne_sudo_und_ueberspringt_unlesbare_fremde_dateien`, `test_nginx_helfer.py::test_orte_helfer_installiert_mit_gruppe_der_instanz`, `test_nginx_helfer.py::test_ac7_als_root_mit_root_eigentum_setzt_root_und_gruppe`, `test_nginx_reise_helfer.py::test_baustein_mit_gruppe_der_instanz`, `test_betrieb.py::test_einrichten_bausteine_lesbar_fuer_die_gruppe`.
- [x] **AC-22:** (Kartendaten im Zustandsordner, Entscheidung 10) GIVEN eine Instanz mit Kartendaten in `FR_KARTENDIENST_ORDNER` WHEN `einrichten.sh --installieren` den Umzug ausführt THEN liegen die Daten unter `/var/lib/<instanz>-kartendienst/` (Besitz `<instanz>-karte`) und `FR_KARTENDIENST_ORDNER` ist ein root-eigener Verweis dorthin; ohne Daten entsteht nur der Verweis; nach einem Abbruch zwischen Kopie und Löschen setzt ein zweiter Lauf sauber fort; ein fremder Verweis bleibt unverändert (Fehlermeldung, nichts verschoben); das Einspielen neuer Kartendaten schaltet hinter dem Verweis um, ohne Schreibrecht im Elternordner. Test: `test_kartendienst.py::test_kartendienst_daten_im_zustandsordner`, `test_kartendienst_skript.py::test_umzug_verschiebt_daten_und_legt_verweis_an`, `test_kartendienst_skript.py::test_umzug_ohne_daten_und_nach_abbruch`, `test_kartendienst_skript.py::test_umzug_fremder_verweis_aendert_nichts`, `test_kartendienst_skript.py::test_einspielen_schaltet_hinter_dem_verweis_um`.

## Dialog

### Runde 1
**Adversary:** Nachprüfung der Befunde des ersten Durchgangs, mit Umgehungsversuchen.
- F001 (Kartendienst, Root-Weg): Die Einheit bindet `__KD_DATEN__` = `/var/lib/<instanz>-kartendienst/daten` ein, nicht mehr den Verweis. Das Karte-Skript ist eine root-eigene Kopie mit eingebackenem `FR_KARTENDIENST_ORDNER=<KD_DATEN>`, `FR_SPERREN=<KD_ZUSTAND>`, `KD_AUSZUEGE`; es liest keine Einstellungen. `readlink -f` greift nur bei Verweis, der eingebackene Wert ist ein echter Ordner. Der Elternordner (`dirname`) ist der Zustandsordner. Kein root- oder karte-Schritt folgt noch einem Pfad des Dienstbenutzers; einzige Berührung: die Sperre des Veröffentlichens wird nur lesend geöffnet. Umgehungsversuch: Dienstbenutzer ersetzt den Verweis (liegt in seinem Ordner); das wirkt nur auf lesende Konnektor-Zugriffe, nicht auf Docker. Beim Umzug selbst (root, einmalig) wird aber der Inhalt des alten, dem Dienstbenutzer gehörenden Ordners mit `cp -a` kopiert und mit `chown -R` auf den Karte-Benutzer umgestellt; Modusbits (setuid) bleiben, siehe F011.
- F002: `befehle | while ... bash -c ... || exit 1` bricht ab (Pipeline-Ausgang durch `pipefail` und `set -e`); getestet in `test_einrichten_installieren_attrappe` (Parametrisierung useradd und kartendienst-umzug.sh).
- F003: `rolle_vorab` läuft vor `_sperre` im PATCH-Zweig; `eingeplant in roh` ist genau die Bedingung für `wunsch_einplanen`, daher kein Weg ohne Abfrage (None nur bei fehlendem Schreibweg). Der Name wird in beiden Aufrufen gleich bestimmt.
- F004: `lesekopie` nimmt bei Git-Reisen die Schreibkopie, sonst die Wurzel; dieselbe Quelle wie `wer_pruefen`. `rolle_lesen` ist ohne Sperre, nur lesend; ohne Kopf 403 (`hmac.compare_digest`).
- F006: `install_befehl` setzt bei Root und Gruppe `-o/-g`; fremde Dateien: Nummern aus `stat`; Root ohne `FR_GRUPPE` gibt RuntimeError mit Katalogtext, beide Sprachen vorhanden (`test_texte` grün).
- F007: `find ... -name '<instanz>-*.conf' -exec grep -qF 'zone=<ZONE> '` stellt nur Dateien mit der Zone der Instanz um (Instanz x und x-test getrennt, weil die Zone den Instanznamen trägt).
- F008: `SPERREN_TMP` deckt Einrückung, `export`, einfache und doppelte Anführungszeichen, `/tmp/`, Kommentar, CRLF ab; atomar (mkstemp, fsync, chmod, chown, replace); Folgelauf ändert nichts. Nicht gedeckt: `//tmp`, `/tmp/.`, `/tmp;`, `declare -x`, siehe F012 (LOW).
- F010: `http.client.HTTPException` steht in der Ausnahmenliste von `rolle_aktuell`.
Bekannte Einschränkungen (nicht als Defekt gewertet): F005 (Messlauf-Protokoll) und F009 (alte Docker-Gruppe, sudoers der Bestandsinstanz) werden erst bei der Umstellung der echten Instanz nachgewiesen (AC-3, AC-20); die Software verhindert sie nicht (die Anleitung nennt keinen `usermod -aG docker` für den Dienstbenutzer mehr).
**Implementierer:** (nicht beteiligt, Kontext-Isolation)

### Runde 2
**Adversary:** Neue Angriffsflächen und Randfälle.
- Reise-Helfer (`nginx-reise-installieren.py`): Grammatik mit Zeichenende-Anker, höchstens ein Zeilenende, ASCII; feste Umgebung (`UMGEBUNG`, Start mit `-I`), Sperre, `O_NOFOLLOW`, root-Besitz geprüft, Rückweg 4/6, Token bleibt (`pfad_aus`). Keine Lücke gefunden. Namensüberschneidung zwischen Instanz x mit Reise test-foo und Instanz x-test mit Reise foo (gleicher Dateiname) ist vorbestehendes Schema, nicht neu.
- `nginx.py`: `lies` ohne sudo, fremde unlesbare Dateien übersprungen, eigene unlesbare gelten als Fehler (gewollt); vor der einmaligen Umstellung der Bausteine endet `pruefen` als Dienstbenutzer mit Fehler (AC-20, Übergang).
- Rollenprüfung: unbekannte Person bei eingerichtetem Schreibweg ergibt "nicht prüfbar" (kein Rückfall); ohne Schreibweg gilt der veröffentlichte Stand (AC-16). Suche nach Name nur ohne Schlüssel (vorbestehende Namensidentität).
- Karte-Skript: `exec 9<` auf `veroeffentlichen.lock` scheitert bei Dateimodus 600 (Umask 077 bei Handaufruf von `veroeffentlichen.sh`) und beendet den Lauf; unter systemd (Umask 022) 644, siehe F013 (LOW).
- Gezielte Tests: 636 passed (test_betrieb, test_kartendienst, test_kartendienst_skript, test_nginx, test_nginx_helfer, test_nginx_reise_helfer, test_units, test_texte, test_protokolle_ohne_pfade, test_neu) und 43 passed (Rolle, Einladen, Erledigen, Sperren, Einplanen, Kartenpunkte in schreiben, konnektor, rueckmeldungen); siehe adversary-test-output.txt.
**Implementierer:** (nicht beteiligt)

### Runde 3
**Adversary:** Nachprüfung von F011, F012, F013 mit Umgehungsversuchen.
- F011: `find "$daten.umzug" -perm /6000 ! -type l -exec chmod ug-s {} +` läuft nach `cp -a` und `chown -R`, vor dem `mv` an den Zielort; die Daten liegen also nie mit setuid/setgid am Ziel. Erfasst Dateien und Ordner (`/6000`), Verweise werden ausgenommen (chmod würde ihnen folgen). Umgehung versucht: Dateikapazitäten (xattr `security.capability`) kann ein Nicht-Root nicht setzen, Hardlinks innerhalb des Baums liegen im selben Lauf. Keine Lücke. Test `test_umzug_entfernt_setuid_und_setgid` grün.
- F013: `betrieb/kartendienst.sh:78-79` fängt die Umleitung mit `{ exec 9<...; } 2>/dev/null || fehler "..."` ab, klare Meldung mit Abhilfe; `betrieb/veroeffentlichen.sh:1103` setzt nach dem Anlegen `chmod 644` (Fehler ignoriert, auch bei `VF_SPERRE`). Bestehende 600-Dateien werden beim nächsten Veröffentlichen umgestellt. Test grün.
- F012: `SPERREN_ZEILE` mit `_sperren_tmp` normalisiert (Schrägstriche, `os.path.normpath`). Geprüft: `//tmp`, `/tmp/.`, `/tmp/../tmp`, `declare -x`, Anführungszeichen mit Kommentar werden entfernt; `/tmpx`, `/var/tmp`, `/tmp#x` bleiben. Nicht erfasst bleibt `FR_SPERREN=/tmp;` (Zeile mit weiterem Befehl, bewusst nicht angefasst; hinweisfrei, praktisch irrelevant, INFO). Tests grün.
- Gezielter Lauf: 312 passed (test_kartendienst_skript, test_neu, test_kartendienst, test_betrieb, test_protokolle_ohne_pfade).
**Implementierer:** (nicht beteiligt)

### Runde 4 (Nachtrag 13.11.2026, Kommentar-Änderung)
**Adversary:** Unabhängiger Prüfer (implementation-validator), nur lesend. Gegenstand: `betrieb/vorlagen/schreiben.service`, zwei Kommentarzeilen („Nachfolger #555“ wird „Restrisiko angenommen (PO, 13.11.2026)“).
- Nur Kommentar: bewiesen. Beide Zeilen beginnen mit `#`, enthalten weder `__X__`-Platzhalter noch Zeilenfortsetzung; `units.py` (`zeilen()`, `abgleich()`) überspringt Kommentarzeilen, kein Code wertet Kommentare dieser Vorlage aus. Die erzeugte Unit bleibt gleich.
- Verweise auf #555 als offenen Nachfolger: keine mehr in `betrieb/`, `engine/`, `docs/`; übrig nur Nennungen als geschlossen (Spec, Briefing).
- Wortlaut passt zu Spec (Entscheidung 11, Known Limitation, Risiko).
- Läufe: `test_units.py` und `test_betrieb.py` 215 passed; Vollsuite 2712 passed.
**Implementierer:** (nicht beteiligt)

## Findings

Finding:
  ID: F011
  Severity: MEDIUM
  Category: security
  Code reference: betrieb/kartendienst-umzug.sh:39
  Description: Der einmalige Umzug kopiert den Inhalt des bisherigen, dem Dienstbenutzer gehörenden Datenordners mit `cp -a` (Zeile 38, erhält Modusbits) und stellt ihn als root mit `chown -R` auf den Karte-Benutzer um (Zeile 39). Root-chown löscht setuid/setgid-Bits nicht. Der Ordner ist 755 und für den Dienstbenutzer ausführbar.
  Spec requirement: AC-22 und Ziel #552: der Dienstbenutzer hat keinen Weg mehr zu Docker/Root; Kartendaten gehören dem Karte-Benutzer.
  Conflict: Ein vor dem Umzug vom Dienstbenutzer in den alten Ordner gelegtes setuid-Programm gehört danach dem Karte-Benutzer (Gruppe docker, also Root-Rechte) und lässt sich vom Dienstbenutzer ausführen: Der Weg Dienstbenutzer, karte, Root entsteht neu und überlebt das Entziehen der alten Docker-Gruppe. Setzt eine frühere Kompromittierung des Dienstbenutzers voraus (auf der Bestandsinstanz war er ohnehin in der Gruppe docker). Nicht durch einen Lauf bewiesen (kein Root im Test).
  Remediation: Nach der Kopie setuid/setgid entfernen (`find ... -perm /6000 -exec chmod ug-s {} +`) oder nur reguläre Dateien und Ordner mit festen Modi kopieren (`rsync --chmod=D755,F644`); Test mit angelegter setuid-Datei.

Finding:
  ID: F012
  Severity: LOW
  Category: edge_case
  Code reference: engine/neu.py:1075
  Description: `SPERREN_TMP` entfernt `FR_SPERREN=/tmp` nur in den dokumentierten Schreibweisen; `//tmp`, `/tmp/.`, `/tmp;` und `declare -x FR_SPERREN=/tmp` bleiben stehen (geprüft mit fullmatch).
  Spec requirement: AC-12: die Zeile `FR_SPERREN=/tmp` ist nach dem Nachziehen weg.
  Conflict: In diesen exotischen Schreibweisen liegen die Sperren weiter im gemeinsamen /tmp, ohne Meldung.
  Remediation: Wert vor dem Vergleich normalisieren oder eine Warnzeile ausgeben, wenn FR_SPERREN nach /tmp zeigt und nicht entfernt wurde.

Finding:
  ID: F013
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/kartendienst.sh:78
  Description: Die Sperre des Veröffentlichens wird mit `exec 9<` geöffnet; ist die Datei für den Karte-Benutzer nicht lesbar (Umask 077 bei Handaufruf; veroeffentlichen.sh legt sie mit `exec 9>` an), beendet der Rechtefehler den Lauf. Fail-closed, aber der Kartenlauf scheitert mit unklarer Meldung.
  Spec requirement: AC-10: die Sperre gegen das Veröffentlichen wird nur lesend geöffnet.
  Conflict: Lesendes Öffnen setzt Lesbarkeit für den Karte-Benutzer voraus, die nirgends erzwungen wird.
  Remediation: In veroeffentlichen.sh nach dem Anlegen `chmod 644` auf die Sperre oder in kartendienst.sh die Umleitung abfangen.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: betrieb/vorlagen/rueckmeldungen.service:26
  Evidence: NoNewPrivileges=yes und InaccessiblePaths=-/run/docker.sock in den Netzdienst-Vorlagen; test_netzdienste_ohne_docker_und_sudo grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: betrieb/vorlagen/schreiben.service:47
  Evidence: ProtectSystem=strict, ProtectHome=read-only, InaccessiblePaths, ReadWritePaths mit sechs Zielen; test_schreiben_unit_sandbox grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: betrieb/messlauf-schreibweg.py:44
  Evidence: SCHREIBZIELE identisch mit ReadWritePaths (test_messlauf_deckt_readwritepaths grün). Messlauf auf der echten Instanz bewusst offen (Ausnahme der Spec, F005).
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: betrieb/vorlagen/nginx-reise-installieren.py:86
  Evidence: reise_lesen, MUSTER mit Zeichenende-Anker, ASCII, Länge; test_eingabe_grammatik grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: betrieb/vorlagen/nginx-reise-installieren.py:289
  Evidence: installieren erzeugt den Token nur ohne Baustein, sonst pfad_aus; Ausgang 2 bei Gleichheit; test_token_bleibt grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: betrieb/vorlagen/nginx-reise-installieren.py:245
  Evidence: _wechseln: Ausgänge 4, 5, 6 wie spezifiziert; test_rueckweg_und_ausgaenge grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: betrieb/vorlagen/nginx-reise-installieren.py:53
  Evidence: UMGEBUNG fest, Start mit -I, Lesemodus gibt nur den Pfad aus (pfad_lesen); test_umgebung_fest und test_lesemodus grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: betrieb/nginx.py:324
  Evidence: Kein sudo außer Helfern und systemctl restart (Suche über betrieb/*.sh); mit Root-Rechten kein sudo davor; test_nur_helfer_mit_sudo und test_reise_baustein_ueber_helfer grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: betrieb/einrichten.sh:188
  Evidence: sudoers-Zeilen nur für drei Helfer und systemctl restart; Anlage von <instanz>-karte; test_einrichten_helfer_und_karte grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: betrieb/vorlagen/kartendienst/kartendienst.service:15
  Evidence: User=<instanz>-karte, ExecStart in /usr/bin, Daten aus __KD_DATEN__; Karte-Skript eingebacken (betrieb/einrichten.sh:177); Sperre nur lesend (betrieb/kartendienst.sh:78); test_kartendienst_ohne_dienstbenutzer grün (Einschränkung F013).
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: betrieb/vorlagen/nginx-orte-installieren.py:224
  Evidence: Orte-Helfer nimmt die echte Vorlage mit Drossel an; Gruppe wird vor jeder Änderung geprüft; test_echte_vorlage_mit_drossel grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/schreiben.py:5386
  Evidence: sperrdatei() nutzt FR_SPERREN oder FR_DIENST; gemeinsam.sh Vorgabe FR_DIENST (betrieb/gemeinsam.sh:124); sperren_nachziehen atomar und idempotent (engine/neu.py:1078); Tests grün (Einschränkung F012).
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: betrieb/vorlagen/schreiben.service:29
  Evidence: Sandbox- und Benutzerzeilen nicht in ERLAUBT; test_sandbox_nicht_in_erlaubnisliste und test_units grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-14
  Code reference: engine/schreiben.py:5815
  Evidence: _rolle: Kopf geprüft (403), Rolle aus der Lesekopie (engine/schreiben.py:5469) nach Schlüssel, null bei Unbekannten, ohne Sperre; test_rolle_lesen grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-15
  Code reference: engine/konnektor.py:2121
  Evidence: einladen_per_mail: person_sichern vor einladungen.json und Mail; Ablehnung ohne Nebenwirkung; vorhandene Person: rolle_aktuell_pruefen (engine/konnektor.py:2046); test_einladen_erst_schreibweg grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-16
  Code reference: engine/konnektor.py:3100
  Evidence: rolle_aktuell_pruefen vor dem PATCH; nicht prüfbar ergibt Meldung dienst.rolle_nicht_pruefbar, kein PATCH; ohne Schreibweg wie bisher (engine/rueckmeldungen.py:251, F010: HTTPException als nicht prüfbar); test_erledigen_rolle_aktuell grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-17
  Code reference: engine/rueckmeldungen.py:901
  Evidence: wunsch_einplanen nimmt die Rolle des aktuellen Stands (Abfrage vor _sperre, rolle_vorab Zeile 849), 403 bei Herabstufung, 503 bei nicht prüfbar; Punkte und erlebt unverändert; test_wunsch_einplanen_rolle_aktuell grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-18
  Code reference: engine/texte_de.py:1918
  Evidence: dienst.nginx.gruppe_fehlt und dienst.rolle_nicht_pruefbar in beiden Sprachen (engine/texte_en.py:1917); test_texte grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-18
  Code reference: engine/texte_en.py:1917
  Evidence: englische Fassung derselben Schlüssel (aus der Bestätigung oben, als eigene Zeile zitiert); test_texte grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-19
  Code reference: betrieb/einrichten.sh:224
  Evidence: Doku und Anleitung nennen nginx-reise-installieren und <instanz>-karte, keine sudoers-Zeile für install, cat, rm, nginx; test_doku_beschreibt_dienstrechte grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-20
  Code reference: betrieb/einrichten.sh:279
  Evidence: Installationsweg bricht bei der ersten fehlschlagenden Zeile ab; Weg gegen Attrappe getestet (test_einrichten_installieren_attrappe). Umstellung der echten Instanz laut Spec-Ausnahme offen (F005, F009: bekannte Einschränkung).
  Status: CONFIRMED

Confirmation:
  AC: AC-21
  Code reference: betrieb/nginx.py:167
  Evidence: install_befehl mit root:<Gruppe>, fremde Dateien behalten Besitz, Orte-Helfer und Reise-Helfer setzen die Gruppe (betrieb/vorlagen/nginx-orte-installieren.py:243, betrieb/vorlagen/nginx-reise-installieren.py:176), einrichten.sh stellt eigene Bausteine am Inhalt (zone=) um (betrieb/einrichten.sh:210); Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-22
  Code reference: betrieb/kartendienst-umzug.sh:33
  Evidence: Daten unter /var/lib/<instanz>-kartendienst/daten, root-eigener Verweis, fremder Verweis ergibt Fehler ohne Änderung, abbruchsicher; Einspielen schaltet im Zustandsordner um (betrieb/kartendienst.sh:26); Tests grün (Einschränkung F011).
  Status: CONFIRMED

Confirmation:
  AC: AC-22
  Code reference: betrieb/kartendienst-umzug.sh:41
  Evidence: F011 behoben: setuid/setgid werden vor dem Umbenennen am Ziel entfernt (`find -perm /6000 ! -type l -exec chmod ug-s`).
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: betrieb/kartendienst.sh:78
  Evidence: F013 behoben: unlesbare Sperre des Veröffentlichens ergibt klare Meldung; betrieb/veroeffentlichen.sh:1103 legt sie 644 an.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/neu.py:1085
  Evidence: F012 behoben: _sperren_tmp normalisiert den Wert (//tmp, /tmp/., declare -x); andere Orte bleiben.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: betrieb/vorlagen/schreiben.service:15
  Evidence: Runde 4: nur Kommentarzeilen geändert (Restrisiko angenommen, PO 13.11.2026); Unit-Inhalt und Abgleich unverändert, 215 Tests und Vollsuite grün.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED

F011, F012 und F013 sind behoben und halten gegen Umgehungsversuche; nichts Neues ab MEDIUM. Frühere Befunde F001 bis F010 halten (Runde 1); F005 und F009 bleiben als bekannte Einschränkung (Nachweis bei der Umstellung der echten Instanz). Gezielte Tests: 636 + 43 + 312 grün, 0 failed, 0 übersprungen. Checkliste: 22/22 Punkte belegt. Restnotiz INFO: `FR_SPERREN=/tmp;` mit Anhang wird nicht entfernt.

## Geprüfte Dateien

- sha256:6d018eddbffe37a3cf28bca7f60236ff64ee217fc714aa3325404eb0ca62e4d9  betrieb/einrichten.sh
- sha256:6554dc400e906f6bc65cea8f96c923c8bfd44f63cd24c06879e6d8bd80d9ec69  betrieb/kartendienst-umzug.sh
- sha256:b62b4aac0c027f5bc75e409a688d273e578b99e1396353c876f27e449fdafae6  betrieb/kartendienst.sh
- sha256:9fd377fcdee8fff712dcc52e1f48cdc3898f4e250e7565cbe350337fae2e879c  betrieb/messlauf-schreibweg.py
- sha256:ab8a57bb11c2ee7f70b5093672e8c72905cc36e26a083a50d032963b1bf4dcfe  betrieb/nginx.py
- sha256:869f4b4a21d7d2a32c939ba049bd06737fc78985d4f7fb20b6a7256026612c5b  betrieb/vorlagen/kartendienst/kartendienst.service
- sha256:dad84dad47474e8cbde00849a9ed3976ff2d78664639b1769e09c10cf789ca4a  betrieb/vorlagen/nginx-orte-installieren.py
- sha256:435a8625fb2aca1438f813e1b2406f5474e810d8307084888faeda94de79b1fc  betrieb/vorlagen/nginx-reise-installieren.py
- sha256:11d5055c4dde9de985af5b412ad8716d1b4e91e87cb7098f6f8c84d4257c5f03  betrieb/vorlagen/rueckmeldungen.service
- sha256:ad489134d9737963620c20e175674bb43b8ef0468b7fdd198a0ed3b7b5fe4dc8  betrieb/vorlagen/schreiben.service
- sha256:5bc32f326105de5d54841061b178e082b2a1ee854b2edba2e9e35c232e5cdbc9  engine/konnektor.py
- sha256:a69c58116e7c808d4d1d9cc1768f9456f7196eaf0adb6c52d7c0913d838a0ab0  engine/neu.py
- sha256:7681f15447c7626a512663f3260cb193a68629ec6a574a11f2b84af7fa1a8486  engine/rueckmeldungen.py
- sha256:6747bcd5a46a0952349775487ac4dc6a19d0393b81b01f706b3faf36f3a8c5f2  engine/schreiben.py
- sha256:38349565afe03dacb75d6b212f2b14f7d5148c14dc9d1e6baf1a22920650c461  engine/texte_de.py
- sha256:c3a5113fd6dbca12a3ae782f3d587250968c8230cbc8807aa2c0397543dd6927  engine/texte_en.py

## Prüfbasis

- base: c40f9b64fffcd354686138f9333aaed2c2344d8c
- blob:f0a12b58dabf918a59936cd0f6bd3bf8fe33ea20  betrieb/einrichten.sh
- blob:69d2b826fc391a5d0dd5ff1d916c34c17085b201  betrieb/kartendienst-umzug.sh
- blob:e9acaf3d067ff374a14e854896ac5e839471bee0  betrieb/kartendienst.sh
- blob:2703c460802620527f2ce14a61a386f1f57bd478  betrieb/messlauf-schreibweg.py
- blob:c95eeb9085c353a2a766acf551c5e7265dbae101  betrieb/nginx.py
- blob:ed132625d845516c5f1c759d3d5f2cb11e56c1bf  betrieb/vorlagen/kartendienst/kartendienst.service
- blob:1eef7063690147be49bb7f4e5979636cf040076d  betrieb/vorlagen/nginx-orte-installieren.py
- blob:e41baa7664c43a09a27b4bf7c451f77ff5b374e6  betrieb/vorlagen/nginx-reise-installieren.py
- blob:0ac1e2fded2d7bd36a12ce48e5f94d928227d641  betrieb/vorlagen/rueckmeldungen.service
- blob:9651fc9ecf63cf24543e825dd43559c574296cfc  betrieb/vorlagen/schreiben.service
- blob:5b24c7a09cc5a7d04c82466c6ff6b878ad13f7cf  engine/konnektor.py
- blob:2fcc624f96a5217f25da8444050735ed02ad1fb8  engine/neu.py
- blob:d6520a707234378de873a61d8885f57aedf8e860  engine/rueckmeldungen.py
- blob:9196d54c57f485f1ea084ca21c3ddf5cb654732b  engine/schreiben.py
- blob:c3cab23b8c45fc964516a08a98e652ec586e9fe0  engine/texte_de.py
- blob:b9c8ba4ed112ba09fd8636be15baaa1d1b0f82e7  engine/texte_en.py

## Geprüfte Dateien

- sha256:6d018eddbffe37a3cf28bca7f60236ff64ee217fc714aa3325404eb0ca62e4d9  betrieb/einrichten.sh
- sha256:6554dc400e906f6bc65cea8f96c923c8bfd44f63cd24c06879e6d8bd80d9ec69  betrieb/kartendienst-umzug.sh
- sha256:b62b4aac0c027f5bc75e409a688d273e578b99e1396353c876f27e449fdafae6  betrieb/kartendienst.sh
- sha256:9fd377fcdee8fff712dcc52e1f48cdc3898f4e250e7565cbe350337fae2e879c  betrieb/messlauf-schreibweg.py
- sha256:ab8a57bb11c2ee7f70b5093672e8c72905cc36e26a083a50d032963b1bf4dcfe  betrieb/nginx.py
- sha256:869f4b4a21d7d2a32c939ba049bd06737fc78985d4f7fb20b6a7256026612c5b  betrieb/vorlagen/kartendienst/kartendienst.service
- sha256:dad84dad47474e8cbde00849a9ed3976ff2d78664639b1769e09c10cf789ca4a  betrieb/vorlagen/nginx-orte-installieren.py
- sha256:435a8625fb2aca1438f813e1b2406f5474e810d8307084888faeda94de79b1fc  betrieb/vorlagen/nginx-reise-installieren.py
- sha256:11d5055c4dde9de985af5b412ad8716d1b4e91e87cb7098f6f8c84d4257c5f03  betrieb/vorlagen/rueckmeldungen.service
- sha256:1b0954eef33b4294ade2cf21abb94ae1552b600de307c9022b40aaf9e29c1428  betrieb/vorlagen/schreiben.service
- sha256:5bc32f326105de5d54841061b178e082b2a1ee854b2edba2e9e35c232e5cdbc9  engine/konnektor.py
- sha256:a69c58116e7c808d4d1d9cc1768f9456f7196eaf0adb6c52d7c0913d838a0ab0  engine/neu.py
- sha256:7681f15447c7626a512663f3260cb193a68629ec6a574a11f2b84af7fa1a8486  engine/rueckmeldungen.py
- sha256:6747bcd5a46a0952349775487ac4dc6a19d0393b81b01f706b3faf36f3a8c5f2  engine/schreiben.py
- sha256:38349565afe03dacb75d6b212f2b14f7d5148c14dc9d1e6baf1a22920650c461  engine/texte_de.py
- sha256:c3a5113fd6dbca12a3ae782f3d587250968c8230cbc8807aa2c0397543dd6927  engine/texte_en.py

## Prüfbasis

- base: c0bbdcb020a0a1a68f75376b8c3db81c96fe8a2e
- blob:f0a12b58dabf918a59936cd0f6bd3bf8fe33ea20  betrieb/einrichten.sh
- blob:69d2b826fc391a5d0dd5ff1d916c34c17085b201  betrieb/kartendienst-umzug.sh
- blob:e9acaf3d067ff374a14e854896ac5e839471bee0  betrieb/kartendienst.sh
- blob:2703c460802620527f2ce14a61a386f1f57bd478  betrieb/messlauf-schreibweg.py
- blob:c95eeb9085c353a2a766acf551c5e7265dbae101  betrieb/nginx.py
- blob:ed132625d845516c5f1c759d3d5f2cb11e56c1bf  betrieb/vorlagen/kartendienst/kartendienst.service
- blob:1eef7063690147be49bb7f4e5979636cf040076d  betrieb/vorlagen/nginx-orte-installieren.py
- blob:e41baa7664c43a09a27b4bf7c451f77ff5b374e6  betrieb/vorlagen/nginx-reise-installieren.py
- blob:0ac1e2fded2d7bd36a12ce48e5f94d928227d641  betrieb/vorlagen/rueckmeldungen.service
- blob:a49878faad0374ccadd8c75fbe86d3a3bbb28fbd  betrieb/vorlagen/schreiben.service
- blob:5b24c7a09cc5a7d04c82466c6ff6b878ad13f7cf  engine/konnektor.py
- blob:2fcc624f96a5217f25da8444050735ed02ad1fb8  engine/neu.py
- blob:d6520a707234378de873a61d8885f57aedf8e860  engine/rueckmeldungen.py
- blob:9196d54c57f485f1ea084ca21c3ddf5cb654732b  engine/schreiben.py
- blob:c3cab23b8c45fc964516a08a98e652ec586e9fe0  engine/texte_de.py
- blob:b9c8ba4ed112ba09fd8636be15baaa1d1b0f82e7  engine/texte_en.py
