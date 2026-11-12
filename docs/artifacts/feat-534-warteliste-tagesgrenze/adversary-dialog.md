# Adversary Dialog — feat-534-warteliste-tagesgrenze
Spec: docs/specs/betrieb/warteliste-tagesgrenze-534.md
Datum: 2026-11-12 13:16

## Checkliste
- [x] **Input:** POST auf `/warteliste` mit einer Adresse.
- [x] **Output:** Unter der Grenze verhält sich alles wie bisher (derselbe Satz `warteliste.gesendet`, Mail an neue und unbestätigte Adressen). Ab der Grenze erscheint für jede Adresse das Formular mit dem Satz „Heute sind alle Plätze vergeben. Bitte morgen wieder vorbeischauen.“.
- [x] **Side effects:** Je ausgelöster Bestätigungsmail eine Zeile `warteliste-tag` in `versand`. Bei der ersten Ablehnung eines UTC-Tages eine Meldung der Art `betrieb` an alle Betreiber und der Merker `warteliste-tag-gemeldet`. Bei einer Ablehnung durch die Tagesgrenze: keine Mail, keine Zeile in `warteliste`, keine Versand-Zeile der Adresse oder der IP.
- [x] **AC-1:** Given `FR_GRENZE_WARTELISTE_TAG` ist nicht gesetzt / When `instanz.grenze_warteliste_tag()` aufgerufen wird / Then ist das Ergebnis 20. (Vorgabe)
- [x] **AC-2:** Given `FR_GRENZE_WARTELISTE_TAG=3` / When `instanz.grenze_warteliste_tag()` aufgerufen wird / Then ist das Ergebnis 3. (Einstellbar)
- [x] **AC-3:** Given `FR_GRENZE_WARTELISTE_TAG` ist `abc`, `0`, `-5` oder leer / When `instanz.grenze_warteliste_tag()` aufgerufen wird / Then ist das Ergebnis 20. (Ungültig)
- [x] **AC-4:** Given die Grenze ist 2 / When drei verschiedene neue Adressen nacheinander eingetragen werden / Then bekommen die ersten beiden je eine Mail und je eine Zeile in `warteliste` und es gibt genau zwei Zeilen `warteliste-tag`. (Bis zur Grenze)
- [x] **AC-5:** Given die Grenze ist 2 und zwei Mails sind heute ausgelöst / When eine dritte neue Adresse eingetragen wird / Then wirft `warteliste_eintragen` `KontoFehler("konto.fehler.warteliste_tag_voll")`, es geht keine Mail raus, es gibt keine Zeile in `warteliste` für diese Adresse und keine `versand`-Zeile mit dem Schlüssel `warteliste:<Adresse>` oder `warteliste-ip:<IP>` für diesen Versuch. (Grenze greift)
- [x] **AC-6:** Given die Tagesgrenze ist erreicht / When die Seite `/warteliste` per POST mit einer neuen Adresse aufgerufen wird / Then antwortet sie mit Status 200 und dem Formular samt Satz `konto.fehler.warteliste_tag_voll` in der Sprache der Seite (de und en), nicht mit `warteliste.gesendet`, und die Adresse steht weiter im Feld. (Seite bei voller Grenze)
- [x] **AC-7:** Given die Grenze war am Tag X erreicht / When die Uhr (`konten._jetzt`) über die nächste Mitternacht UTC gesetzt wird und eine neue Adresse eingetragen wird / Then wird sie angenommen und bekommt eine Mail; Zeilen des Vortags zählen nicht mehr. (Neuer Tag)
- [x] **AC-8:** Given die Grenze ist erreicht um 23:59 UTC / When die Uhr auf 00:01 UTC des nächsten Tages (also zwei Minuten später) gesetzt wird / Then ist die Grenze wieder frei; und given 00:01 UTC mit erreichter Grenze, when die Uhr auf 23:59 UTC desselben Tages gesetzt wird, then bleibt sie erreicht. (Kalendertag, nicht gleitendes Fenster)
- [x] **AC-9:** Given eine Adresse ist unbestätigt eingetragen / When sie sich erneut einträgt und dadurch eine zweite Mail bekommt / Then gibt es zwei Zeilen `warteliste-tag`, und bei erreichter Grenze wird auch die erneute Anfrage abgelehnt (keine zweite Mail, Eintrag unverändert). (Erneute Mail zählt)
- [x] **AC-10:** Given eine Adresse ist bestätigt oder freigegeben und die Grenze ist nicht erreicht / When sie sich erneut einträgt / Then geht keine Mail raus und die Zahl der Zeilen `warteliste-tag` ändert sich nicht. (Bestätigte Adresse zählt nicht)
- [x] **AC-11:** Given die Grenze ist erreicht / When dieselbe Anfrage einmal für eine neue, einmal für eine unbestätigte und einmal für eine bestätigte Adresse gestellt wird / Then ist die Antwort in allen drei Fällen dieselbe Ablehnung (`konto.fehler.warteliste_tag_voll`), und die Datenbank ändert sich in keinem Fall. (Ablehnung verrät nichts)
- [x] **AC-12:** Given die Grenze ist erreicht / When `konten.freigeben(adresse)` für eine bestätigte Adresse aufgerufen wird / Then klappt die Freigabe (Mail „Du bist dabei“ geht raus) und die Zahl der Zeilen `warteliste-tag` ändert sich nicht. (Freigaben zählen nicht)
- [x] **AC-13:** Given `WARTELISTE_MAX_UNBESTAETIGT` ist erreicht (im Test herabgesetzt) und die Tagesgrenze nicht / When eine neue Adresse mit `konto.fehler.warteliste_voll` abgelehnt wird / Then gibt es keine neue Zeile `warteliste-tag`. (Ablehnung wegen Höchstzahl zählt nicht)
- [x] **AC-14:** Given eine Adresse hat die Begrenzung je Adresse erreicht und die Tagesgrenze ist ebenfalls erreicht / When sie sich einträgt / Then lautet die Ablehnung `konto.fehler.zu_viele_codes` (bestehende Begrenzung zuerst); given ungültige Adresse und erreichte Tagesgrenze, then lautet die Ablehnung wie bisher auf die ungültige Adresse. (Reihenfolge mit den bestehenden Grenzen)
- [x] **AC-15:** Given die Grenze ist erreicht und ein Betreiber-Konto existiert / When am selben UTC-Tag fünf Anfragen abgelehnt werden / Then hat das Betreiber-Konto genau eine Meldung der Art `betrieb` zur Tagesgrenze (sichtbar bei `rm.meldungen_des_kontos`), mit der Grenze als Zahl im Text in der Sprache des Betreibers; am nächsten Tag mit erneut erreichter Grenze kommt genau eine weitere. (Meldung genau einmal je Tag)
- [x] **AC-16:** Given die Grenze ist nicht erreicht / When Anfragen angenommen werden / Then entsteht keine Meldung zur Tagesgrenze; given die Grenze wurde mit der letzten angenommenen Anfrage genau erreicht und es gab noch keine Ablehnung, then gibt es auch noch keine Meldung. (Keine Meldung unter der Grenze und ohne Ablehnung)
- [x] **AC-17:** Given zwei Aufrufe von `konten.warteliste_tagesgrenze_merken()` am selben Tag / When sie nacheinander laufen / Then liefert der erste `True` und der zweite `False`; nach Mitternacht UTC liefert der nächste Aufruf wieder `True`. (Atomarer Merker)
- [x] **AC-18:** Given die Grenze wird erreicht / When die Meldung angelegt wird / Then wird weder `send.sh` von Claude MQ noch ein anderer Telegram-Weg aufgerufen (der Test prüft, dass nur `rueckmeldungen.meldung_anlegen` den Betreiber erreicht). (Kein Alarmweg)
- [x] **AC-19:** Given kein Betreiber-Konto existiert / When die Grenze abgelehnt wird / Then antwortet die Seite trotzdem mit der Ablehnung (kein Fehler, kein Absturz). (Kein Betreiber vorhanden)
- [x] **AC-20:** Given `betreiber_melden` wirft eine Ausnahme / When eine Anfrage wegen der Tagesgrenze abgelehnt wird / Then zeigt die Seite trotzdem die Ablehnung mit Status 200. (Fehler beim Melden)
- [x] **AC-21:** Given der Katalog / When `engine/tests/test_texte.py` läuft / Then sind die drei neuen Schlüssel in `texte_de.py` und `texte_en.py` vorhanden, enthalten die Platzhalter `{grenze}` jeweils gleich, und die Ausnahmelisten sind nicht länger geworden. (Texte vollständig)
- [x] **AC-22:** Given die Ablehnungsseite / When sie ausgegeben wird / Then enthält sie weder die Grenze noch die Zahl der Einträge des Tages. (Keine Zahl auf der Seite)
- [x] **AC-23:** Given die Doku / When `docs/konten.md`, `docs/betrieb.md` und `betrieb/einstellungen.beispiel` gelesen werden / Then ist `FR_GRENZE_WARTELISTE_TAG` mit Vorgabe 20 beschrieben; `engine/tests/test_grenzen.py` prüft das wie bei den anderen `FR_GRENZE_*`-Werten. (Doku und Beispiel)
- [x] **AC-24:** Given die Zeilen `warteliste-tag` und `warteliste-tag-gemeldet` enthalten keine Adresse / When ein Konto gelöscht oder exportiert wird (#381, #498) / Then bleibt deren Verhalten unverändert und es bleibt keine personenbezogene Zeile übrig. (Löschen und Export unberührt)

## Dialog

### Runde 1
**Adversary:** Testlauf (`adversary-test-output.txt`): `test_warteliste.py`, `test_grenzen.py`, `test_texte.py`, `test_anmeldung.py`, `test_konten.py` mit `-n 3`: 220 passed, 0 failed, 0 übersprungen. Dann Prüfung jedes Punktes gegen den Code.

Confirmation:
  AC: AC-1, AC-2, AC-3
  Code reference: engine/instanz.py:160
  Evidence: `VORGABE_GRENZE_WARTELISTE_TAG = 20`; `grenze_warteliste_tag()` (engine/instanz.py:182-185) nutzt `_grenze`, das ungültige Werte (abc, 0, -5, leer) wie bei den anderen Grenzen als nicht gesetzt behandelt. Test `test_grenze_vorgabe_einstellbar_und_ungueltig` parametrisiert grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4, AC-9, AC-10, AC-13
  Code reference: engine/konten.py:876
  Evidence: Die Zählzeile wird nur am Ende des Zweigs geschrieben, der eine Mail auslöst (neu oder erneut an Unbestätigte). Bestätigte/freigegebene Adressen kehren vorher bei Zeile 865 zurück (keine Zeile). Die Ablehnung `warteliste_voll` wirft vor Zeile 876 (keine Zeile). Zugehörige Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-5, AC-11, AC-14
  Code reference: engine/konten.py:857
  Evidence: Reihenfolge: Adresse (adresse(roh)), Mail eingerichtet, DELETE Abgelaufene, `_begrenzt` je Adresse/IP (Z. 854), danach erst die Tagesgrenze (Z. 857-859), dann die INSERTs der Adress- und IP-Zeilen (Z. 860-862). Die Ausnahme verlässt `with closing(db()) as v, v`, die Transaktion wird zurückgerollt; die Prüfung steht vor jeder Unterscheidung nach dem Stand, die Ablehnung ist für jede Adresse gleich. Ungültige Adresse wirft zuerst, zu_viele_codes vor tag_voll. Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-6, AC-22
  Code reference: engine/anmeldung.py:1432
  Evidence: `except KontoFehler` liefert `antwort(200, warteliste_seite(email, x.text(sprache_der_seite())))`, Adresse bleibt im Feld. Der Satz in de/en (engine/texte_de.py:3524, engine/texte_en.py:3523) enthält keine Zahl; die Seite nennt weder die Grenze noch eine Tageszahl.
  Status: CONFIRMED

Confirmation:
  AC: AC-7, AC-8
  Code reference: engine/konten.py:103
  Evidence: `_tagesbeginn()` = `jetzt - jetzt % 86400` auf Basis von `_jetzt()`; gezählt wird `zeit >= Tagesbeginn` (Z. 857-858), kein gleitendes Fenster. `_begrenzt` löscht nur Zeilen älter als 24 h (Z. 292), der Tagesbeginn liegt höchstens 24 h zurück, die Zeilen des laufenden Tages bleiben erhalten. Randfall: Zeile exakt um 00:00:00 zählt zum neuen Tag (>=), korrekt.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/konten.py:876
  Evidence: `freigeben` wurde nicht verändert (Diff berührt es nicht) und schreibt keine `warteliste-tag`-Zeile; Test `test_freigaben_zaehlen_nicht` grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-15, AC-16, AC-17, AC-19
  Code reference: engine/konten.py:883
  Evidence: `warteliste_tagesgrenze_merken()` ist eine einzige Anweisung `INSERT ... SELECT ... WHERE NOT EXISTS` mit `rowcount == 1`; Aufruf nur im Ablehnungszweig (engine/anmeldung.py:1424-1426), also keine Meldung unter der Grenze und nicht bei der Anfrage, die die Grenze genau erreicht. `betreiber_melden` (engine/anmeldung.py:1598-1609) tut ohne Betreiber nichts (AC-19). Eigenversuch mit 20 Threads: genau ein True (`Counter({False: 19, True: 1})`).
  Status: CONFIRMED

Confirmation:
  AC: AC-18, AC-20
  Code reference: engine/anmeldung.py:1424
  Evidence: Der einzige Weg zum Betreiber ist `betreiber_melden` (rm.meldung_anlegen); kein send.sh, kein MQ in den geänderten Dateien (Grep). `except Exception` (Z. 1431) fängt jeden Fehler, schreibt nach stderr, und das `return antwort(200, ...)` in Z. 1432 liegt außerhalb des try: Status 200 bleibt.
  Status: CONFIRMED

Confirmation:
  AC: AC-21
  Code reference: engine/texte_de.py:3528
  Evidence: Drei Schlüssel in de (engine/texte_de.py:1129, 3524, 3528) und en (engine/texte_en.py:1128, 3523, 3527); `{grenze}` jeweils in den beiden Betreiber-Schlüsseln gleich; `test_texte.py` im Lauf grün, Ausnahmelisten unverändert (Diff ändert test_texte.py nicht).
  Status: CONFIRMED

Confirmation:
  AC: AC-21 (en)
  Code reference: engine/texte_en.py:3527
  Evidence: Englische Entsprechung mit `{grenze}` und gleichem Sinn wie de; Katalogtest grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-23
  Code reference: engine/instanz.py:182
  Evidence: `docs/konten.md`, `docs/betrieb.md`, `betrieb/einstellungen.beispiel` beschreiben `FR_GRENZE_WARTELISTE_TAG` mit Vorgabe 20 (Diff geprüft); `test_grenzen.py:198` prüft das per Regex. Vorgabe 20 stimmt mit instanz.py:160 überein.
  Status: CONFIRMED

Confirmation:
  AC: AC-24
  Code reference: engine/konten.py:76
  Evidence: Die Schlüssel `warteliste-tag` und `warteliste-tag-gemeldet` (engine/konten.py:76-77) sind konstant und ohne Adresse oder IP; `loeschen` (Z. 627-628) und der Export bleiben unverändert und finden dort nichts Personenbezogenes, das übrig bliebe. Der Export greift nicht auf `versand` zu (Grep, keine Treffer außerhalb konten.py).
  Status: CONFIRMED

Adversary-Angriffe in Runde 1 (alle ohne Befund): (a) Rückrollen der Ablehnung: `raise` in Z. 859 verlässt den `with`-Block, DELETE aus `_begrenzt` und der Abgelaufenen-Löschung werden mitgerollt, es bleibt nichts gespeichert. (b) Verrät die Ablehnung etwas? Nein, die Prüfung steht vor `SELECT bestaetigt` (Z. 863). (c) Merker-Verlust: Wirft `betreiber_melden` nach `merken()=True`, ist der Merker verbraucht und die Meldung dieses Tages geht verloren; die Spec (Abschnitt 3) fordert nur, dass die Seite nicht abstürzt, daher LOW.

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/anmeldung.py:1426
  Description: Der Merker wird vor dem Anlegen der Meldung gesetzt. Scheitert `betreiber_melden` (Ausnahme), ist der Merker für den Tag verbraucht und der Betreiber erfährt an diesem Tag nichts mehr von der Tagesgrenze.
  Spec requirement: AC-15 — genau eine Meldung je Tag; AC-20 verlangt nur, dass die Seite weiter 200 zeigt.
  Conflict: Kein Verstoß gegen die Spec (sie nennt keinen Wiederholungsversuch); nur Informationsverlust im Fehlerfall, der im Protokoll (stderr) steht.
  Remediation: Optional: Merker bei Ausnahme wieder entfernen. Nicht blockierend.

**Implementierer:** (nicht beteiligt)

### Runde 2
**Adversary:** Gezielter Angriff auf das vom Entwickler genannte Nebenläufigkeitsproblem (Zählung und Einfügen in einer Transaktion). Statt der Annahme habe ich es gemessen: 30 Threads rufen gleichzeitig `warteliste_eintragen` mit verschiedenen Adressen und IPs bei Grenze 5 auf (Skript im Scratchpad, nicht im Repo). Ergebnis: `Counter({'konto.fehler.warteliste_tag_voll': 25, 'ok': 5})`, genau 5 Zeilen `warteliste-tag`. Die Grenze wurde nicht überschritten.

Erklärung aus dem Code: Vor der Zählung (Z. 857) steht schon ein schreibender Befehl, `DELETE FROM warteliste ...` (engine/konten.py:850), und `_begrenzt` führt ebenfalls `DELETE FROM versand` aus (Z. 292). Der sqlite3-Treiber öffnet beim ersten DML-Befehl die Transaktion und hält ab dort die Schreibsperre; parallele Anfragen warten (Timeout 10 s, engine/konten.py:194). Zählung und Einfügen der Zählzeile laufen also faktisch serialisiert. Die Befürchtung des Entwicklers („um 1 überschreiten“) trifft damit nicht zu; selbst wenn sie zuträfe, verlangt die Spec Atomarität nur für den Merker (Abschnitt 3), das wäre kein Verstoß. Die Sicherheit hängt allerdings am implizit früheren DELETE (LOW, F002).

Weitere Angriffe: (1) `_begrenzt` löscht Zeilen < jetzt-24h; Zählzeilen des laufenden Tages sind jünger und bleiben. (2) Mailversand scheitert nach Commit: Zeile bleibt gezählt (Known Limitations); `mail_fehlgeschlagen` ist kein tag_voll-Fehler und löst keine Meldung aus (engine/anmeldung.py:1424). (3) Grenze mitten am Tag gesenkt: neuer Wert gilt sofort; dokumentiert. (4) 20 gleichzeitige Merker-Aufrufe: genau ein True. (5) AC-14, 2. Teil: ungültige Adresse wirft in Z. 848 vor allem anderen. (6) Doku „ungültige Werte gelten als nicht gesetzt“ deckt sich mit `_grenze`.

Finding:
  ID: F002
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/konten.py:857
  Description: Die Serialisierung von Zählung und Einfügen hängt nur implizit an dem davor stehenden `DELETE` (Z. 850), nicht an einer ausdrücklichen Schreibsperre (`BEGIN IMMEDIATE`). Ein Kommentar dazu fehlt.
  Spec requirement: AC-5 — die Grenze greift; Spec Abschnitt 3 fordert Atomarität nur für den Merker.
  Conflict: Kein Verstoß; nur Wartbarkeit. Gemessen wurde keine Überschreitung.
  Remediation: Kommentar ergänzen, dass die Sperre durch das vorherige DELETE besteht.

**Implementierer:** (nicht beteiligt)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Implementierung hat den Angriffen standgehalten.
Tests: 220 passed, 0 failed, 0 übersprungen (siehe adversary-test-output.txt)
Edge cases: Reihenfolge der Prüfungen, Rollback der Ablehnung, Kalendertag statt Fenster, Merker atomar (20 Threads: ein True), Grenze unter Last (30 Threads, Grenze 5: genau 5 angenommen), Meldefehler, Löschen: alle geprüft, nichts gebrochen
Regressions: Keine gefunden (bestehende Begrenzungen und Freigabe unverändert; test_anmeldung, test_konten, test_texte grün)
Checklist: 27/27 Punkte bewiesen (3 Expected-Behavior-Punkte und AC-1 bis AC-24)
Findings: F001 (LOW), F002 (LOW), beide nicht blockierend.

## Geprüfte Dateien

- sha256:114bda034784feec7525cc6942a532c39dafbecaeab0d768ba98333eabcc0ccf  engine/anmeldung.py
- sha256:9b5a672118d7eb50fbaa7857b495e899e012d22a876e7e9589c4dd04c2ed780d  engine/instanz.py
- sha256:9698d09713f744707a2f326a61f2d432782b24688fd322fd66a93e0994015eaf  engine/konten.py
- sha256:77af3bc0d95c43ffe09391499440f7c94f99d8942578c21b28534313ad99a21f  engine/texte_de.py
- sha256:dae4e3d2e579d3f45c0aa1ecb155094194720597b7ce3c99892582a0f2390431  engine/texte_en.py

## Prüfbasis

- base: 71b4bebacfd491c9d2654c85ed142db8fd71d18b
- blob:72e20c6799e544bfba6f76f922c4c75506cddc82  engine/anmeldung.py
- blob:cd864ce6e58f5107b61731738c1502460ff82ede  engine/instanz.py
- blob:6f0eddf7aee88724e404dd90a774fec35d120a39  engine/konten.py
- blob:fa3f0ed4fdd1f90894d2aebcf95515dd3838b723  engine/texte_de.py
- blob:375296e95544c4528f841f18f96785e86616d14c  engine/texte_en.py
