# Altformen entfernen mit automatischer Umstellung (#267, Teil 3 von #215)

## Anlass

Die Software schleppt Altformen mit, die #215 als Aufräumen benennt: die alte Form einer Reise ohne `reise.yaml`
(`Reise.alt`), die Bestandssprache `de` für Reisen ohne `sprache` (`texte.BESTAND_REISE`) und Lesepfade für den früheren
Schlüssel `typ` sowie für Merkmalswerte ohne Liste (Letzteres prüft die Spec und stuft es als reguläre Lesetoleranz ein, nicht als Altform; Entscheidung 2). Jede Altform ist toter Code, ein Zweig mehr in Tests und Doku und ein
stilles Verlassen darauf, dass „es schon irgendwie gilt“ (ADR-0006: die Sprache soll ausdrücklich in der Datei stehen).

Product Owner (2.11.2026): „Ich möchte keine Software, die Handarbeit braucht.“ Altformen dürfen deshalb nur fallen, wo
keine Reise sie mehr nutzt oder wo die Software die Umstellung selbst mitbringt (`neu.py nachziehen`, Lauf „Software
nachziehen“, #250).

### Befund an den Daten (3.11.2026, lesend gegen `<Reisen-Repo>/reisen` und `beispiel/reisen`)

| Altform | Genutzt? | Folge |
|---|---|---|
| Reise ohne `reise.yaml` (`Reise.alt`) | Nein: alle 6 echten und beide Beispielreisen haben die Datei | entfernen; fehlende Datei = Baufehler |
| `sprache` fehlt in `reise.yaml` (Bestand `de`) | Ja: 4 von 6 echten Reisen (gr221, <Reise J>, skiurlaub-zillertal-2027, test-135); die Beispielreisen und die übrigen zwei Reisen tragen `sprache: de` | erst automatisch umstellen, dann den Fallback entfernen |
| `typ` statt `art` an Unterkunft und Nacht | Nein: kein `typ:` in den `routen.yaml` der echten Reisen und der Beispielreisen | Lesepfad im Bau kann fallen; `nachziehen` bleibt die Umstellung |
| Einzelwert statt Liste bei Merkmalen | Nein: 0 Skalare; die Listenform „Wert je Datum“ (gr221) ist die reguläre Form | bleibt (siehe Entscheidung 2) |
| `varianten_titel` | Ja (<Reise J>) | bleibt, ist keine Altform |

## Lösung

Vier Pull Requests in strikt dieser Reihenfolge. Jeder ist für sich grün und lieferbar; keiner verlangt einen Handschritt
in einer Reise oder Instanz.

### PR a: Reise ohne `reise.yaml` entfällt

- `engine/reise.py`: `Reise.alt` und alle Zweige darauf entfallen (Zeilen 353, 365–367, 379, 419, 480, 491, 549–570);
  `Reise` bekommt immer ein gelesenes `reise.yaml`. Der Kopf des Moduls nennt die alte Form nicht mehr.
- `engine/bauen.py` (Z. 286–296): Fehlt `reise.yaml`, bricht der Bau mit `BauFehler` ab, Text über den Katalog
  (`texte.satz`), wie bei `pruefung.bauen.datei_fehlt` für `reise.json`. Neuer Schlüssel `pruefung.bauen.reise_yaml_fehlt`
  in `texte_de.py` und `texte_en.py` (Pfad der Datei, Hinweis auf `docs/produkt.md`). Der Text `pruefung.reise.2` (alte
  Form) entfällt aus beiden Katalogen.
- Die Felder, die nur die alte Form aus `reise.json` las (Titel, Untertitel, `pfad`, `gruppen`, Regeln, Funktionen), bleiben
  in `reise.json` dort, wo andere Teile sie noch brauchen; die Spec ändert nur, dass `reise.yaml` Pflicht ist. Was nach dem
  Entfernen keinen Leser mehr hat, entfernt PR a mit (Prüfung per Suche, nicht per Vermutung).

### PR b: `nachziehen` trägt `sprache: de` ein

- `neu.py nachziehen` (ab Z. 425, bis vor `_zeilen_normal`) ergänzt in `reise.yaml` das Feld `sprache: de`, wenn es fehlt (oder leer ist). Der Wert
  ist ausdrücklich `de`: Das ist, was für diese Reisen bisher galt, die Umstellung ändert also kein Verhalten.
- Idempotent: Steht `sprache` schon, bleibt die Datei Byte für Byte gleich; ein zweiter Lauf ändert nichts.
  Kommentare und Form der Datei bleiben (ruamel, wie bei den übrigen Umstellungen). Das Feld steht an der Stelle, an der
  `neu.py` es bei neuen Reisen schreibt (Reihenfolge der Schlüssel wie in `neu.anlegen`).
- Meldung wie bei `typ → art`: eine Zeile in der Liste der Meldungen, über den Katalog in der Sprache der Reise
  (neuer Schlüssel `inhalt.nachziehen.sprache_eingetragen`, de/en, in `texte_de.py` und `texte_en.py` anzulegen), der Wortlaut nennt die gesetzte Sprache.
- Reihenfolge innerhalb von `nachziehen`: Das Eintragen läuft vor den Schritten, die `sprache_von` nutzen
  (`eckdaten_nachziehen`, `reste_nachziehen`). Weil der eingetragene Wert dem bisherigen Bestand `de` gleicht, ändert sich
  an deren Ergebnis nichts.
- Eine unbekannte Sprache im Feld bleibt unberührt und wird weiter vom Bau gemeldet (kein Überschreiben fremder Eingaben).
- Eine neu angelegte Reise hat nichts nachzuziehen (besteht schon als Test aus #250 und wird um `sprache` erweitert).
- Auslieferung: Der Lauf „Software nachziehen“ (#168/#250) stellt die vier Reisen der Instanz selbst um, im selben Commit
  wie der neue Software-Stand. Kein Handschritt.

### PR c: `BESTAND_REISE` entfällt (erst nach Nachweis, siehe Reihenfolge)

- `texte.BESTAND_REISE` entfällt. `Reise.sprache()` (reise.py Z. 385–392): fehlendes oder leeres `sprache` ist ein Fehler
  der Prüfung mit Katalogtext (`pruefung.reise.sprache_fehlt`, neuer Schlüssel, in `texte_de.py` und `texte_en.py` anzulegen, analog zu `reise_yaml_fehlt` in PR a; nennt die erlaubten Kürzel aus `texte.SPRACHEN` und
  den Satz „`neu.py nachziehen` trägt es ein“). Die Reise baut dann nicht, bis das Feld steht.
- `reise.sprache_von()` (Z. 220–230): ohne Feld `sprache` gilt nicht mehr der Bestand, sondern `texte.VORGABE_REISE`
  (der schon vorhandene Rückfall für unlesbare Dateien). Das trifft nur Dateien, die der Bau ohnehin ablehnt, und
  Dateien, die `nachziehen` gleich umstellt (siehe PR b: es schreibt das Feld, bevor es `sprache_von` nutzt).
- `neu.py` Z. 500: Die Ebene „Unterwegs nachschlagen“ nimmt den früheren Standardtext, der deutsch war. Er wird als
  Rest der Umstellung ausdrücklich aus dem Katalog `de` gelesen (`texte.t("de", …)` mit Kommentar „die frühere Vorgabe
  war deutsch, #217“), nicht über eine Konstante für den Bestand. Weil `nachziehen` das Feld `sprache` zuvor eingetragen
  hat, ist das gleichbedeutend mit „Sprache der Reise“, wenn diese `de` ist; bei anderen Sprachen bleibt der Text der
  alten Vorgabe, der er immer war.
- `schreiben.py` Z. 1998–1999 (`einstellung_setzen`): Eine Reise ohne Feld kommt nicht mehr vor (der Bau lehnt sie ab);
  der Vergleich nimmt `roh.get("sprache")`, ohne Ersatzwert; fehlt das Feld, gilt es als Änderung. Der Text
  `schreiben.antwort.einstellung.sprache` nennt für „von“ den neuen Katalogtext `schreiben.antwort.einstellung.sprache_ungesetzt` („nicht gesetzt“, neu, de/en).
- `texte.py` Z. 144 (`_einzeln`): Die Bedingung `kuerzel != BESTAND_REISE` entfällt. Sie schloss `de` vom Rückfall auf
  den Rand-Text aus; der zweite Teil der Bedingung („die Sprache hat keinen Text `wert.<wert>`“) trifft für `de` nie
  zu, solange `texte_de` alle Werte von `_RAND` enthält. Ein Test sichert genau das (jeder Schlüssel von `_RAND` hat
  einen Text in jeder gelieferten Sprache oder der Rückfall ändert für `de` nichts).
- `routen.STUFEN_WORTE`: siehe Entscheidung 1.
- `docs/betrieb.md`, `docs/sprachen.md`, Kopf von `reise.py`: Hinweise auf den Bestandsfall entfallen; die Regel lautet
  „`sprache` steht in jeder `reise.yaml`“.

### PR d: Lesepfade `typ` und Einzelwert

Nur entfernen, wo Befund und Umstellung es tragen (Entscheidung 2 und 3):

- `schreiben.py` Z. 1003–1004: nur ein Kommentar, der die Einzelform als Lesetoleranz benennt (Entscheidung 2); kein
  Verhalten ändert sich.
- `routen.py` Z. 829 (`art_von`) und Z. 1199 (`nacht`): Der Bau liest `typ` nicht mehr als Ersatz für `art`. Eine
  Unterkunft oder Nacht mit `typ:` und ohne `art:` bekommt den bestehenden Fehler `pruefung.routen.65` („art fehlt“), dessen Text um den Hinweis ergänzt wird (Text geändert, kein neuer Schlüssel; de/en), dass
  `neu.py nachziehen` den Schlüssel umstellt. Der Befund ist 0 Treffer in allen Reisen.
- `neu.py` Z. 313–365 (`arten_ableiten`, die den früheren `typ` als Quelle der Arten liest): bleibt, solange
  `nachziehen` und `arten-ableiten` aus Reisen mit `typ` herleiten müssen; PR d prüft jede Stelle einzeln und lässt jede
  stehen, die `nachziehen` selbst braucht. `typ_zu_art` in `nachziehen` bleibt in jedem Fall (es ist die Umstellung).
- Nicht gemeint und unverändert: `typ` als Datentyp einer Merkmalsdefinition (`text`, `geld`, `zahl`, `auswahl`, `link`
  in `arten.yaml`, `routen.py` Z. 776/883/972 u. a.). Das ist keine Altform.

## Entscheidungen zu den offenen Fragen

1. **Woher bezieht `STUFEN_WORTE` die Wörter, wenn `BESTAND_REISE` fällt?** Empfehlung: aus gar keiner Sprache, die
   Konstante entfällt. Geprüft im Code: `STUFEN_WORTE` wird nur an einer Stelle gelesen, `stufe_satz` (routen.py Z. 145),
   und dort nur als Mengenprüfung `s in STUFEN_WORTE`. Die Schlüssel (`pflicht`, `empfohlen`, `angeboten`, `aus`) sind
   sprachneutral und stehen schon als `STUFEN` in der Datei. Die Wörter selbst liest `stufe_schluessel` je Sprache aus dem
   Katalog (Z. 164–174), und `stufe_satz` holt sie mit `texte.satz("schreiben.stufe." + s)` in der Sprache der Person.
   Also: `STUFEN_WORTE` löschen und in `stufe_satz` `s in STUFEN` prüfen. Das braucht weder `VORGABE_REISE` noch eine
   Reise. Der Test `test_texte.py` Z. 127 (prüft den Inhalt der Konstante auf Deutsch) wird durch einen Test auf
   `stufe_satz` in beiden Sprachen ersetzt. Trade-off: Die Alternative „Wörter aus `VORGABE_REISE`“ hätte eine
   englische Konstante gebracht, die keiner liest; Löschen ist einfacher und folgt dem Grundsatz „Code kennt keine
   Sprache beim Namen“.
2. **Skalar-Pfad in `schreiben.py` Z. 1003–1004.** Geprüft: Die Zeilen lesen den vorhandenen Eintrag eines Merkmals aus der
   Datei (`alt = merkmale.get(k)`) und machen daraus eine Liste (`[alt]`, wenn keine Liste). Der Bau liest dieselbe Form
   (`routen.py` Z. 947: `v if isinstance(v, list) else [v]`). Gemeint ist also die Einzelform „ein Eintrag ohne Liste“,
   und die ist regulär; sie gilt für einen einzelnen Aussage-Eintrag (`{wert, quelle, geprueft}`) (der nackte Wert ist dagegen nur dann gültig, wenn er den Regeln von `wert_eintrag` genügt, siehe unten). Eine Umstellung wäre auch nicht möglich, weil ein nackter Wert keine Herkunft hat, die
   `nachziehen` erfinden dürfte (ADR-0001: keine erfundenen Aussagen). Empfehlung: beide Pfade bleiben, als
   Lesetoleranz der Einzelform, einmal im Kommentar so benannt; PR d (nicht PR c) ändert hier nichts außer dem Kommentar. Der
   nackte Wert wird beim Bau weiterhin von `wert_eintrag` abgelehnt, falls ihm die Herkunft fehlt (kein stilles Gelten).
3. **Reihenfolge b → c als Abnahmebedingung.** PR c wird erst vorgespult, wenn der Nachweis vorliegt (siehe unten).
   Der Nachweis ist lesend und wird im PR-Text festgehalten.

## Reihenfolge-Abnahmebedingung b → c

PR c darf erst auf `main`, wenn gleichzeitig gilt:

1. PR b ist auf `main`, und der Lauf „Software nachziehen“ im Reisen-Repo hat den neuen Software-Stand übernommen
   (Commit des Bots mit der Meldung zur Sprache je Reise).
2. Lesende Prüfung am Stand von `main` des Reisen-Repos: In jeder `reisen/*/reise.yaml` steht ein gültiges Feld
   `sprache` (Befehl im PR-Text: `grep -L '^sprache:' <Reisen-Repo>/reisen/*/reise.yaml` ohne Treffer, die Werte aus `grep -h '^sprache:'` sind Kürzel aus `texte.SPRACHEN`; der Probelauf des Baus mit dem Branch prüft die Gültigkeit endgültig).
   Gleiches gilt für jedes weitere Reisen-Repo, das die Software einbindet.
3. Der Bau jeder Reise mit dem Stand von PR c ist grün (Probelauf lokal mit dem Branch; `engine/tests` der einbindenden
   Instanz mit dem Branch).

Fehlt eine der Bedingungen, wird PR c nicht vorgespult, auch wenn die Tests der Software grün sind. Die Datei-Änderung in
den echten Reisen entsteht ausschließlich durch den Workflow, nie von Hand.

## Betroffene Dateien

| Datei | PR | Änderung |
|---|---|---|
| `engine/reise.py` | a, c | `alt`-Zweige entfernen; `sprache()` und `sprache_von()` ohne Bestand |
| `engine/bauen.py` | a | fehlende `reise.yaml` = `BauFehler` mit Katalogtext |
| `engine/neu.py` | b, c, d | `nachziehen` trägt `sprache` ein; Z. 500 ohne `BESTAND_REISE`; `typ`-Lesepfade prüfen |
| `engine/routen.py` | c, d | `STUFEN_WORTE` entfällt; `typ`-Rückfall in `art_von` und `nacht` entfällt |
| `engine/schreiben.py` | c | Z. 1998–1999 ohne `BESTAND_REISE` (Spur B) |
| `engine/schreiben.py` | d | Z. 1003–1004 nur Kommentar „Lesetoleranz der Einzelform“ (Spur B) |
| `engine/texte.py` | c | `BESTAND_REISE` und Bedingung in `_einzeln` entfallen |
| `engine/texte_de.py`, `engine/texte_en.py` | a, b, c, d | neue Texte; `pruefung.reise.2` entfällt |
| `engine/tests/…` | a–d | siehe unten |
| `docs/betrieb.md`, `docs/sprachen.md` | c | Bestandsfall streichen; Regel „`sprache` steht in jeder Reise“ |

Kein neues Python-Modul, daher keine Änderung an `betrieb/deploy.sh`.

## Geplante Tests

- PR a: `engine/tests/test_bauen.py`: `test_alte_form_ohne_reise_yaml` (Z. 400) wird zu „ohne `reise.yaml` bricht der Bau
  ab, Schlüssel `pruefung.bauen.reise_yaml_fehlt`, kein Bauergebnis“. Tests, die nur wegen der alten Form `reise.yaml`
  weglassen (`test_reise_yaml_alte_eckdaten_in_reise_json`, `test_alte_regeln_des_einarbeitens_bauen_weiter`), werden
  geprüft und auf die gültige Form umgestellt. `engine/tests/test_texte.py`: beide Kataloge haben den neuen Schlüssel,
  `pruefung.reise.2` ist weg.
- PR b: `engine/tests/test_neu.py`: Reise ohne `sprache` bekommt `de` und eine Meldung (beide Sprachen der Meldung);
  zweiter Lauf: Meldungen leer und alle Dateien der Reise vor und nach dem Lauf gleich; vorhandene Sprache (`de`, `en`)
  bleibt; unbekannte Sprache bleibt unberührt; Kommentare der Datei bleiben; neu angelegte Reise meldet nichts;
  Probelauf (`schreiben=False`) schreibt nichts, meldet aber. Ergänzung in `engine/tests/test_umstellung_250.py`: Reise
  mit allen Altformen (ohne `sprache`, mit `typ`, mit Resten der früheren Vorlage) wird in einem Lauf umgestellt und
  baut danach.
- PR c: `engine/tests/test_bauen.py` und `engine/tests/test_neu.py`: Reise ohne `sprache` bricht den Bau mit
  `pruefung.reise.sprache_fehlt`; nach `nachziehen` baut sie. `test_neu.py` Z. 360–370 (`test_rueckfall_ist_englisch…`):
  die Aussage über `BESTAND_REISE` entfällt, `VORGABE_REISE == "en"` bleibt. `engine/tests/test_texte.py` Z. 127 und
  Z. 370: Stufen-Test über `stufe_satz` in beiden Sprachen; die Liste der Wert-Schlüssel kommt aus `texte.VORGABE`
  statt aus `BESTAND_REISE`; Test zu `_einzeln` für `de`. `engine/tests/test_schreiben.py`: `einstellung_setzen` mit
  `sprache` für eine Reise mit Feld, Meldung unverändert. Ein Test sucht in `engine/` nach `BESTAND_REISE` ohne Treffer.
- PR d: `engine/tests/test_routen.py`: Unterkunft und Nacht mit `typ` und ohne `art` melden „art fehlt“ mit Hinweis auf
  `nachziehen`; mit `art` baut es; nach `nachziehen` baut die Reise mit `typ` (Ende-zu-Ende). `engine/tests/test_neu.py`:
  `typ_zu_art` unverändert grün. `engine/tests/test_schreiben.py`: Einzelform des Merkmals bleibt les- und schreibbar.
- Vor jedem Vorspulen: `engine/.venv/bin/python -m pytest -q engine/tests` grün ohne echte Reisen (CI auf dem vorgespulten
  Commit; die Suite braucht rund 20 Minuten, deshalb kleine, gebündelte PRs).

## Akzeptanzkriterien

- **AC-1 (a):** Fehlt `reise.yaml`, bricht der Bau mit einem `BauFehler` ab, dessen Text aus dem Katalog kommt (de und
  en vorhanden); `Reise.alt` und alle Zweige darauf sind aus dem Quelltext verschwunden (Suche nach `.alt` in
  `engine/reise.py` ohne Treffer).
- **AC-2 (a):** Beide Beispielreisen (`beispielreise`, `stadtwochenende`) und alle echten Reisen bauen unverändert; ihre
  gebauten Seiten sind vor und nach PR a gleich.
- **AC-3 (b):** `neu.py nachziehen` trägt in jeder `reise.yaml`, in der `sprache` fehlt oder leer ist, das Feld `sprache: de` ein und meldet es
  mit einer Zeile in der Sprache der Reise; in `reise.yaml` mit gültigem Feld ändert sich nichts, auch nicht in
  Kommentaren oder Reihenfolge.
- **AC-4 (b):** Ein zweiter Lauf von `nachziehen` direkt danach liefert keine Meldung und ändert keine Datei der Reise
  (Vergleich aller Dateien vor und nach dem Lauf).
- **AC-5 (b, manueller Nachweis am Reisen-Repo):** Der Lauf „Software nachziehen“ stellt die vier Reisen ohne `sprache` ohne Handschritt um; die
  Meldungen stehen im Commit des Bots (Verlauf, ADR-0001 Frage 7).
- **AC-6 (c, manueller Nachweis im PR-Text):** Die Abnahmebedingung b → c ist erfüllt und im PR-Text belegt (Commit des Bots, Ausgabe der lesenden
  Prüfung, grüner Bau aller Reisen mit dem Branch), bevor PR c vorgespult wird.
- **AC-7 (c):** `texte.BESTAND_REISE` kommt im Quelltext von `engine/` nicht mehr vor; eine `reise.yaml` ohne
  `sprache` bricht den Bau mit dem Katalogtext `pruefung.reise.sprache_fehlt`.
- **AC-8 (c):** `routen.STUFEN_WORTE` ist gelöscht; `stufe_satz` und `stufe_schluessel` liefern in Deutsch und Englisch
  dieselben Ergebnisse wie vorher.
- **AC-9 (c):** Meldungstexte, Seiten und Dateien beider Beispielreisen sind vor und nach PR c in beiden Sprachen
  (de, en und der Pseudo-Sprache der Tests) gleich; die Ausnahmelisten in `test_texte.py` sind nicht länger geworden.
- **AC-10 (d):** Der Bau liest `typ` nicht mehr als Ersatz für `art`; `nachziehen` stellt `typ` weiterhin um; die
  Datentypen der Merkmale (`typ: text|geld|…`) sind unberührt.
- **AC-11 (d):** Der Einzelwert-Pfad in `schreiben.py` Z. 1003–1004 bleibt als Lesetoleranz erhalten; kein Merkmalswert einer
  Reise wird dadurch verändert.
- **AC-12 (alle):** Jede Änderung am Format bringt ihre Umstellung in `neu.py nachziehen` mit, mit Test (CLAUDE.md,
  #250); der Nachweis, dass in keiner Reise und keiner Instanz ein Handschritt nötig war, ist manuell: der Commit des Bots
  und die lesende Prüfung aus der Abnahmebedingung stehen im PR-Text.
- **AC-13 (alle):** Vor dem Vorspulen jedes PR laufen die Tests der einbindenden Instanzen mit dem Branch; rot darf dort
  nur sein, was auf `main` ohne den Branch schon rot ist (Vergleichslauf der Instanz auf `main` zuerst, Ergebnis im PR-Text).

## Abgrenzung

- Nichts Reisespezifisches in Engine oder Texten; `sprache` bleibt Einstellung der Reise in `reise.yaml`.
- Datei-Änderungen in echten Reisen entstehen nur durch den Workflow „Software nachziehen“, nie von Hand und nie durch
  diese Sitzung.
- `varianten_titel` und die Listenform „Wert je Datum“ bleiben; sie sind keine Altformen.
- `typ` als Datentyp der Merkmalsdefinition bleibt.
- Kein Entfernen von `reise.json` als Datei oder von Feldern, die andere Teile lesen; Gegenstand ist nur die Pflicht zu
  `reise.yaml`.
- Keine neue Sprache, keine Änderung an den Wortlauten außerhalb der genannten Schlüssel.

## Hinweise zur Zusammenarbeit

- Spur B arbeitet an `schreiben.py`, `neu.py` und `konnektor.py`. PR b (neu.py), PR c (schreiben.py, neu.py) und PR d (neu.py, routen.py, schreiben.py) werden
  vorher per `ListAgents` und `SendMessage` angekündigt; vor dem Vorspulen auf `main` neu auf den aktuellen Stand setzen.
  Ein Issue-Kommentar in #267 hält die Übernahme fest.
- Die Meldungstexte und das Dateiformat (Feld `sprache`) ändern sich: Vor dem Vorspulen laufen die Tests des Reisen-Repos
  der Instanz mit dem Branch (Anleitung dort). Die öffentliche CI kann private Tests nicht ausführen.

## Prüfstelle ADR-0001 (kurz)

Das Vorhaben fügt keine Grundform und keine Art hinzu und kennt kein Reisedetail; es entfernt Software-Zweige und
bringt die Umstellung der Daten selbst mit. Frage 7 (Verlauf): die Umstellung steht im Commit des Bots. Die Frage
nach Wirkung auf beide Beispielreisen (Frage 1) ist durch die Abnahme unten beantwortet. Widerspruch zum Kern: keiner.

## Abnahme an beiden Beispielreisen

Für jeden PR: Bau von `beispiel/reisen/beispielreise` (Wanderung mit Varianten) und `beispiel/reisen/stadtwochenende`
(Wochenende ohne Wanderung) mit dem Branch, Vergleich der gebauten Seiten mit dem Stand von `main` (gleich), und je
Beispielreise ein Probelauf von `nachziehen` (keine Meldung). Zusätzlich je PR eine Testkopie mit der jeweiligen
Altform (PR a: ohne `reise.yaml`; PR b/c: ohne `sprache`; PR d: mit `typ`), die vor `nachziehen` meldet und danach
baut. Erfundene Testdaten, nie echte Reisen.
