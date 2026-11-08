# Adversary Dialog — fix-361-einstellungen-fail-closed
Spec: docs/specs/betrieb/einstellungen-fail-closed-361.md
Datum: 2026-11-08 19:55

## Checkliste
- [x] **Input:** Einstellungsdatei vorhanden, aber nicht lesbar; `FR_SPEICHERREISEN` nicht in der Umgebung.
- [x] **Output:** Schreibvorgang, `/gesund`, Buchungsabfrage: 503 mit Katalogtext; Seitenbau und Veröffentlichen brechen mit klarer Fehlermeldung ab. Kein Vorgang läuft über Git.
- [x] **Side effects:** Eine Protokollzeile auf stderr je abgewiesenem Vorgang. Nichts wird geschrieben, geholt oder gebaut.
- [x] **Unverändert:** Datei fehlt -> alles über Git. `FR_SPEICHERREISEN` in der Umgebung gilt weiter vor der Datei, auch bei unlesbarer Datei. Der Dienst startet und beantwortet Anfragen weiter; nur die vier Weichen lehnen ab.
- [x] **AC-1:** Given die Einstellungsdatei existiert, ist aber nicht lesbar, und `FR_SPEICHERREISEN` ist nicht in der Umgebung / When `instanz.speicherreisen()` aufgerufen wird / Then wird `EinstellungenNichtLesbar` ausgelöst (kein leeres Ergebnis).
- [x] **AC-2:** Given die Einstellungsdatei fehlt / When `speicherreisen()` aufgerufen wird / Then ist die Liste leer, ohne Ausnahme.
- [x] **AC-3:** Given `FR_SPEICHERREISEN` ist in der Umgebung gesetzt und die Datei ist unlesbar / When `speicherreisen()` aufgerufen wird / Then gilt der Umgebungswert, ohne Ausnahme.
- [x] **AC-4:** Given unlesbare Datei / When `einstellungen()` oder `wert()` gerufen wird / Then liefern sie weiter `{}` bzw. die Vorgabe (der Dienst fällt nicht ganz aus).
- [x] **AC-5:** Given unlesbare Datei / When ein Schreibvorgang für irgendeine Reise ankommt (`anwenden_extern`) / Then Antwort 503 mit dem Text `schreiben.dienst.einstellungen_nicht_lesbar`, Protokollzeile auf stderr, und weder `schreiben_git.vorgang` noch `vorgang_speicher` wird ausgeführt.
- [x] **AC-6:** Given unlesbare Datei / When `schreiben_git.vorgang` direkt gerufen wird / Then 503 vor jedem Holen aus Git.
- [x] **AC-7:** Given unlesbare Datei / When `GET /gesund` oder `GET /<reise>/buchung/<B>` kommt / Then 503 (`{"gesund": false}` bzw. Katalogtext).
- [x] **AC-8:** Given unlesbare Datei / When `stand.fuer_seite` aufgerufen wird / Then bricht es mit `EinstellungenNichtLesbar` ab und liefert nie einen Stand aus Git.
- [x] **AC-9:** Given fehlende Datei / When Schreibvorgang einer Git-Reise / Then läuft er wie bisher über Git.
- [x] **AC-10:** Given der Schlüssel `schreiben.dienst.einstellungen_nicht_lesbar` / When der Textkatalog geprüft wird / Then ist er in allen Sprachen vorhanden, die Ausnahmelisten in `test_texte.py` sind nicht länger geworden.
- [x] **AC-11:** Given `fr_einlesen` mit vorhandener, nicht lesbarer Datei / When es läuft / Then Abbruch mit Fehlermeldung auf stderr und Exit-Code ungleich 0; mit fehlender Datei Exit-Code 0 wie bisher.

## Dialog

### Runde 1
**Adversary:** VERDICT BROKEN. Der Python-Teil (instanz, schreiben, schreiben_git, stand) ist sauber, 282 Tests grün.
- F001 (HIGH, spec_violation/edge_case): `betrieb/software-nachziehen.sh` `speicherreisen_der_instanz` überspringt eine vorhandene, nicht lesbare Einstellungsdatei still (`[ -r ] || return 0`); `aus_dem_speicher` meldet dann „keine Speicher-Reise“, die Reisen würden als Reisen des alten Weges umgestellt. Das ist genau der stille Wechsel, den #361 verhindern soll.
- F002 (LOW, edge_case): `fr_einlesen` prüft `-e`; eine Symlink-Schleife gilt als „fehlt“ (rc 0), Python löst aus.

**Implementierer:** F001 behoben: Fehlt die Datei (weder `-e` noch `-L`), gibt es keine Speicher-Reisen; ist sie vorhanden, aber keine lesbare reguläre Datei, kommen Fehlermeldung und `return 1`, und `aus_dem_speicher` bricht mit `exit 1` ab. F002 behoben: `fr_einlesen` und die Weiche prüfen `-e` oder `-L`. Neue Tests in `test_betrieb.py` (`test_nachziehen_weiche_*`, `test_unlesbare_datei_ueber_symlink_schleife_bricht_ab`), nach dem Fix geschrieben, nicht davor. Lauf: 332 Tests grün. Nachtrag in der Spec unter Known Limitations (der Spec-Freeze erlaubt dort Änderungen, neue ACs nicht).

Code reference: betrieb/software-nachziehen.sh:78
Code reference: betrieb/gemeinsam.sh:63

### Runde 2
**Adversary:** Re-Check: F001 und F002 sind behoben. `exit` wirkt in beiden Aufrufern (`umstellen`, `tor`) in der Hauptshell, vor dem Übernehmen; keine weiteren Weichen in `betrieb/` (`einstellungen_summe` in `veroeffentlichen.sh` betrifft nur die Änderungserkennung). Neuer Befund LOW, nicht blockierend: Ein Symlink ins Leere ist in der Shell ein Fehler, in Python „fehlt“; die Shell ist strenger, also auf der sicheren Seite. Ein eigener Laufzeitversuch des Adversary wurde vom Sicherheitshook blockiert (Dateiname der Einstellungsdatei); der Befund beruht auf Codeanalyse und den Tests (148 grün in test_betrieb und test_instanz).

**Implementierer:** Die Abweichung ist als Known Limitation in der Spec dokumentiert (Symlink ins Leere, NotADirectoryError). Keine weitere Änderung nötig.

Code reference: betrieb/software-nachziehen.sh:104
Code reference: engine/instanz.py:110
Code reference: engine/schreiben.py:5020
Code reference: engine/schreiben_git.py:174
Code reference: engine/texte_de.py:871
Code reference: engine/texte_en.py:870

Bestätigt in Runde 1 (AC-10): Der Schlüssel `schreiben.dienst.einstellungen_nicht_lesbar` steht in `texte_de.py` und `texte_en.py`, `test_texte.py` ist grün.

## Herkunft der Vorbedingungen

| Vorbedingung | Herkunft |
|---|---|
| Einstellungsdatei vorhanden, aber nicht lesbar | im Test künstlich hergestellt (Verzeichnis statt Datei, gepatchtes Lesen, `chmod 000`); im Betrieb Rechte- oder Dateisystemfehler |

Die Vorbedingung „Einstellungsdatei vorhanden, aber nicht lesbar“ wird in den Tests künstlich hergestellt (Verzeichnis statt Datei, gepatchtes Lesen, `chmod 000` außer unter root). Im Betrieb entsteht sie durch Rechte- oder Dateisystemfehler. Eine echte Instanz wurde nicht angefasst.

## Verdict
**VERIFIED**

## Geprüfte Dateien

- sha256:bd840127a7c5907d725d113d3f98fdbaa488e7a6039eefc3ca5e5e1fb74b51d8  betrieb/gemeinsam.sh
- sha256:bef22590c24dfa2a563ff0562e4012555ee8808a19857b126a3773023b9ae305  betrieb/software-nachziehen.sh
- sha256:9cb0404571a3d8a410b4a5ab22f3737124892b4783521a75e8759aece86d77bd  engine/instanz.py
- sha256:11b81fed78cf72225b91c8a18329abfc15711ab469e14ef124f335cc27aa93a6  engine/schreiben.py
- sha256:3c96832501db7ded06a92922a579341ba9555f9ea2cc232d53df72fc469b7272  engine/schreiben_git.py

## Prüfbasis

- base: 74f38e15e444ef8d860ae1981508c0f726e4a6bd
- blob:318645c0a4d9bba22256d822b85a5349b78331c9  betrieb/gemeinsam.sh
- blob:21f46040940ef4628432b0f481bcab3cc24a94f2  betrieb/software-nachziehen.sh
- blob:e07eec9e9ddbfc05fc990e7512b8ef6ba56ccc1b  engine/instanz.py
- blob:ea71fcb8bbe3a5dacbc9064479684e05241d5c77  engine/schreiben.py
- blob:08d617ebdf0ce0ade05fd83821bb4dbdf8373635  engine/schreiben_git.py

## Geprüfte Dateien

- sha256:bd840127a7c5907d725d113d3f98fdbaa488e7a6039eefc3ca5e5e1fb74b51d8  betrieb/gemeinsam.sh
- sha256:bef22590c24dfa2a563ff0562e4012555ee8808a19857b126a3773023b9ae305  betrieb/software-nachziehen.sh
- sha256:9cb0404571a3d8a410b4a5ab22f3737124892b4783521a75e8759aece86d77bd  engine/instanz.py
- sha256:11b81fed78cf72225b91c8a18329abfc15711ab469e14ef124f335cc27aa93a6  engine/schreiben.py
- sha256:3c96832501db7ded06a92922a579341ba9555f9ea2cc232d53df72fc469b7272  engine/schreiben_git.py
- sha256:7675472fee41a153a4c61570f7a42a89fea88d400bdd8e2e2329abca0efdb294  engine/texte_de.py
- sha256:1af0eb38b782cc5fb9c5335fac0c8f3867b54b3a6194d3db47b021750271728b  engine/texte_en.py

## Prüfbasis

- base: 74f38e15e444ef8d860ae1981508c0f726e4a6bd
- blob:318645c0a4d9bba22256d822b85a5349b78331c9  betrieb/gemeinsam.sh
- blob:21f46040940ef4628432b0f481bcab3cc24a94f2  betrieb/software-nachziehen.sh
- blob:e07eec9e9ddbfc05fc990e7512b8ef6ba56ccc1b  engine/instanz.py
- blob:ea71fcb8bbe3a5dacbc9064479684e05241d5c77  engine/schreiben.py
- blob:08d617ebdf0ce0ade05fd83821bb4dbdf8373635  engine/schreiben_git.py
- blob:3425b0a1b662aa931381a473522f3b3905481816  engine/texte_de.py
- blob:fcd93a78642c1b5fea64a27d7d0680c0afeaa9e3  engine/texte_en.py
