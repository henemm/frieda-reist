---
entity_id: betreiber-meldung-530
type: feature
created: 2026-11-12
updated: 2026-11-12
status: draft
workflow: betreiber-meldung-530
version: "1.0"
tags: [konten, konnektor, betreiber, datenschutz, alpha, m5a]
---

# Alpha: Rückmeldung an den Betreiber aus der Claude-App (#530, Meilenstein M5a)

## Approval

- [ ] Approved

## Purpose

Zum Alpha-Start melden Tester Fehler, Wünsche und Fragen zu Frieda selbst (zur Software, nicht zu einer Reise) direkt dort, wo sie arbeiten: in der Claude-App. Heute landet `feedback_give` in der eigenen Reise des Testers; der Betreiber sieht solche Meldungen nie. Mit dieser Spec gibt es ein Konto-Werkzeug `report_to_frieda` (deutscher Alias `an_frieda_melden`). Die Meldung wird in der Kontendatenbank abgelegt, jedes Betreiber-Konto bekommt eine Mail mit der Adresse des Testers als Antwortadresse, und Betreiber sehen offene Meldungen bei `my_trips` und mit einem Befehl auf dem Server.

Entscheidung des Product Owners vom 12.11.2026 (Weg A, Kommentar in #384; er teilt einen LinkedIn-Beitrag, es gibt keine festen Tester, deshalb muss #530 vor dem Alpha-Start live sein). Technischer Plan: erster Kommentar von #530. Kontext und Analyse: `docs/context/betreiber-meldung-530.md`. Ein Entwurf der Umsetzung liegt außerhalb des Repos vor; sein Wortlaut der Texte ist unten übernommen, mit den dort genannten Abweichungen.

## Ziel und Abgrenzung

- **Im Scope:**
  - Konto-Werkzeug `report_to_frieda` / `an_frieda_melden` in `engine/konnektor.py` (`frieda_werkzeuge`, `frieda_werkzeug`) und `engine/schnittstelle.py` (`NAMEN`, `PARAMETER`).
  - Tabelle `betreiber_meldungen` und Funktionen in `engine/konten.py`; `mail_senden` bekommt den Parameter `antwort_an` (Reply-To).
  - Tagesgrenze je Konto, Mail an alle Betreiber-Konten, Verhalten bei Mailfehlern.
  - Betreiber-Sicht: Liste bei `my_trips`, Befehle `konten.py meldungen [--alle]` und `konten.py meldung-erledigt <nr> <issue>`.
  - Löschen des Kontos (#381) nimmt die Meldungen und den Versand-Schlüssel mit; Export (#498) enthält die eigenen Meldungen.
  - Datenschutzerklärung (`DATENSCHUTZ_ABSCHNITTE`), Alpha-Hinweis (Kontakt als Rückfall), Anleitungssatz in `anleitung_frieda`.
  - Texte in `engine/texte_de.py` und `engine/texte_en.py` (jede künftige `texte_<kürzel>.py` folgt `docs/sprachen.md`).
  - Doku: `docs/betrieb.md`, `docs/konnektor.md`, `docs/konten.md`.
  - Tests in `engine/tests/test_betreiber_meldung.py` (neu).
- **Nicht im Scope:**
  - Kein Bearbeiten von Meldungen in der Claude-App: Betreiber lesen und haken ab (Server-Befehl), mehr nicht. Keine Antwort-Funktion im Werkzeug; geantwortet wird per Mail an die Adresse des Testers.
  - Kein automatisches Anlegen von Issues durch die Software. Das Issue legt Claude (Tech Lead) bei der Bearbeitung an, **nur im privaten Reisen-Repo** der Instanz, nie im öffentlichen Repo (Testerdaten gehören nicht in ein öffentliches Repo). `konten.py meldung-erledigt` nimmt nur den Verweis darauf entgegen.
  - Kein Telegram- oder MQ-Alarm: Meldungen sind kein Ausfall (Regel der Instanz). Die Mail und die Liste bei `my_trips` sind der Weg.
  - Kein Anhang, keine Bilder, keine Antwort des Betreibers im Werkzeug, keine Seite im Web dafür.
  - Kein Wartelisten-Eintrag und keine Meldungen von Personen ohne Konto (sie nutzen den Kontakt aus dem Impressum).
  - Keine Änderung an `feedback_give`/`rueckmeldung_geben` (Rückmeldungen zu einer Reise bleiben dort) und an der Schreibgrenze.
  - Keine Änderung am Speicherformat der Reisen, am Reisespeicher und am Schreibweg.
  - `recht.datenschutz.folgt` bleibt, wie sie auf `main` steht (vom Export #498 geändert); der Entwurf berührt sie nicht.
- **Kern (ADR-0001):** Konten und Betrieb, keine Ontologie. Das Werkzeug kennt keine Art und kein Merkmal einer Reise, schreibt nichts in eine Reise und enthält keine KI; es legt eine Zeile in der Kontendatenbank ab und verschickt eine Mail. Die Texte stehen im Katalog (ADR-0006). Die Art der Meldung (Fehler, Wunsch, Frage) ist ein Wert des Werkzeugs, keine Art im Sinn der Reise-Ontologie.
- **Instanzen:** Nichts Instanzspezifisches: Betreiber sind die Konten mit dem Recht `betreiber`, der Kontakt kommt aus `FR_BETREIBER_KONTAKT` (`engine/instanz.py`, wie das Impressum), die Mailzustellung aus der Konfiguration der Instanz. Keine echten Reisen, Namen, Adressen oder Pfade in Spec, Tests und Beispielen.
- **Keine Umstellung in `neu.py nachziehen`:** Die Tabelle kommt über `CREATE TABLE IF NOT EXISTS` im `SCHEMA` von `konten.py` (wie alle Tabellen der Kontendatenbank, wird beim ersten Öffnen angelegt). Reisedaten, Reisespeicher und Dateiformat der Reisen sind nicht betroffen; es gibt also nichts nachzuziehen und keinen Handschritt nach dem Software-Wechsel.

## Source

Zeilennummern nach dem Stand von `alpha-384-probelauf` (mit Export #498).

- `engine/konten.py`: `SCHEMA` (Z. 109, Tabellen enden bei `loeschprotokoll` Z. 160, `versand` Z. 131), `mail_senden` (Z. 243, `FR_MAIL_DATEI`-Zweig und SMTP-Zweig), `_begrenzt` (Z. 267; Zählung in `versand`), `loeschen` (Z. 579; Tabellenliste Z. 612, Versand-Schlüssel Z. 605), `recht` (Z. 655), `liste` (Z. 1387), `main` (Z. 1431, CLI-Zweige), `_jetzt` (Z. 92), `_datum` (Z. 96).
- `engine/konnektor.py`: `KALENDER` (Z. 2203), `frieda_werkzeuge` (Z. 2227; Konto-Werkzeuge `KALENDER`, `sprache_setzen_werkzeug`), `reisen_des_kontos`, `anleitung_frieda` (Z. 2262, Hilfe `anl`), `meine_reisen_konto` (Z. 2280; Betreiber-Block für Freischaltungen am Ende), `frieda_werkzeug` (Z. 2321; Konto-Zweige `kalender` und `sprache_setzen` vor der Reise-Auswahl), `tk` (Z. 170), `sprache_setzen_werkzeug` (Z. 213).
- `engine/schnittstelle.py`: `NAMEN` (Z. 78: `"language_set": "sprache_setzen"`), `PARAMETER` (Z. 111).
- `engine/anmeldung.py`: `export_person` (Z. 939), `BETREIBER` (Z. 1187, Namen der Einstellungen), `DATENSCHUTZ_ABSCHNITTE` (Z. 1188), `ALPHA_PUNKTE` (Z. 1189), `datenschutz_inhalt` (Z. 1192; Abschnitte mit `.titel`/`.text`), `impressum_inhalt` (Z. 1207; liest `instanz.wert(name)` mit `.strip()`, leer zählt als fehlend), `alpha_inhalt` (Z. 1219), Hilfen `tx` (Z. 48), `th` (Z. 53), `link` (Z. 235), `esc`.
- `engine/instanz.py`: `wert(name, vorgabe)` (Z. 65).
- `engine/rueckmeldungen.py`: `ARTEN` (Z. 95; Vorbild für die großgeschriebenen Wörter Frage, Wunsch).
- `engine/texte_de.py`, `engine/texte_en.py`: `wert.*` (Z. 119–123 de, 118–122 en), `recht.datenschutz.konto_loeschen` (de Z. 3537, en Z. 3535), `recht.datenschutz.folgt` (nicht anfassen), `konto.export.punkt_4` (de Z. 3672, en Z. 3670), `konto.betreiber.*` (Freischaltungen, Vorbild für die Mail an Betreiber), `konnektor.anleitung.frieda.*`.
- `engine/tests/test_loeschen_konto.py` (prüft über `sqlite_master`, dass in keiner Tabelle eine Zeile des Kontos bleibt), `engine/tests/test_export.py` (Export der Kontoangaben), `engine/tests/test_rechtliches.py` (Datenschutz, Impressum, Alpha), `engine/tests/test_texte.py` (Vollständigkeit aller Sprachen, Ausnahmelisten nur kürzer, Pseudo-Sprache).
- `docs/betrieb.md` (Abschnitt „Datenschutz je Instanz“, Tabelle ab Z. 49), `docs/konnektor.md` (Konto-Werkzeuge, Tabelle der englischen Namen), `docs/konten.md` (Abschnitt „Betrieb“).

## Verhalten

### Konto-Werkzeug `report_to_frieda`

1. **Name und Alias.** Internes Werkzeug `an_frieda_melden`; `engine/schnittstelle.py` bekommt in `NAMEN` `"report_to_frieda": "an_frieda_melden"` und in `PARAMETER` `"zusammenhang": "context"`. Die Claude-App sieht den englischen Namen, deutsche Namen und Alias gelten ebenso (Tabelle in `docs/konnektor.md`).
2. **Sichtbarkeit.** Das Werkzeug steht in `konnektor.frieda_werkzeuge(k)` für **jedes** Konto, mit und ohne Reise, neben `KALENDER` und `sprache_setzen_werkzeug`. Es ist ein Konto-Werkzeug (keine Reise-Auswahl) und zählt **nicht** in die Schreibgrenze (`FR_GRENZE_SCHREIBEN`), weil es nichts in eine Reise schreibt.
3. **Parameter.**

   | Parameter (englisch/deutsch) | Pflicht | Inhalt |
   |---|---|---|
   | `text` | ja | Was passiert ist oder was sich die Person wünscht, in ihren Worten; getrimmt, 1 bis 2000 Zeichen |
   | `art` | ja | `Fehler`, `Wunsch` oder `Frage` (Aufzählung `konten.BETREIBER_MELDUNG_ARTEN`) |
   | `reise` / `trip` | nein | Kennung einer Reise **des Kontos**; als Aufzählung (`enum`) nur der eigenen Reisen im Schema (`reisen_des_kontos`); ohne Reise im Konto fehlt das Feld im Schema |
   | `zusammenhang` / `context` | nein | Was Frieda zuletzt tat, welches Werkzeug, welche Fehlermeldung; getrimmt, höchstens 2000 Zeichen |

   **Festlegung zur Art:** Die Werte sind großgeschrieben (`Fehler`, `Wunsch`, `Frage`), wie die Arten der Rückmeldungen (`rm.ARTEN`: `Frage`, `Wunsch`), und werden über den Katalog angezeigt (`wert.<Art>`). Der Issue-Text nennt sie kleingeschrieben (`fehler|wunsch|frage`); das ist die Schreibweise der Beschreibung, nicht der Daten. `wert.Frage` und `wert.Wunsch` gibt es schon (de Z. 119/123, en Z. 118/122); **neu** ist nur `wert.Fehler` (de „Fehler“, en „bug“). Der Entwurf ergänzt genau diesen einen Schlüssel; mehr ist nicht nötig. Die Datenwerte `Fehler`/`Wunsch`/`Frage` werden nie übersetzt (docs/sprachen.md, „Was nie übersetzt wird“), nur ihre Anzeige.
4. **Ablauf** (`frieda_werkzeug`, Zweig `an_frieda_melden` **vor** der Reise-Auswahl, wie `sprache_setzen` und `kalender`; die Prüfungen in dieser Reihenfolge):
   1. Ist `reise` gesetzt und nicht in `reisen_des_kontos(k)` (Mitgliedschaft des angemeldeten Kontos, nicht vorgemerkt): Fehlerantwort `konnektor.frieda_werkzeug.1` („Bei dieser Reise bist du nicht dabei (oder sie ist nicht veröffentlicht).“). Es wird nichts gespeichert, keine Mail geschickt und nichts über die Reise verraten.
   2. `konten.an_betreiber_melden(k, art, text, reise, zusammenhang)` (Punkt 6). `KontoFehler` wird zur Fehlerantwort in der Sprache des Kontos (`f.text(k["sprache"])`).
   3. Erfolg: `konnektor.an_frieda_melden.angekommen` mit der Nummer der Meldung.
5. **Anleitung.** `anleitung_frieda(k)` bekommt für jedes Konto, mit und ohne Reise, den Satz `konnektor.anleitung.frieda.melden` am Ende (mit `anl(sprache, "frieda.melden")`, eine Leerzeile davor): Fehler, Wünsche und Fragen zu Frieda selbst gehen mit dem Werkzeug an den Betreiber, nicht als Rückmeldung in die Reise; vorher den Wortlaut bestätigen lassen und den Zusammenhang mitschicken. Dieser Satz fehlt im Entwurf und kommt hier hinzu.

### Ablage und Mail (`engine/konten.py`)

6. **Tabelle** im `SCHEMA`: `betreiber_meldungen(id INTEGER PRIMARY KEY AUTOINCREMENT, konto TEXT NOT NULL, reise TEXT NOT NULL DEFAULT '', art TEXT NOT NULL, text TEXT NOT NULL, zusammenhang TEXT NOT NULL DEFAULT '', zeit REAL NOT NULL, issue TEXT)` (`CREATE TABLE IF NOT EXISTS`, keine Umstellung, siehe Abgrenzung). `issue` ist `NULL`, solange die Meldung offen ist.
7. **`an_betreiber_melden(k, art, text, reise=None, zusammenhang=None)`** gibt die Nummer (`id`) zurück oder wirft `KontoFehler`. Reihenfolge der Prüfungen: Text getrimmt leer → `konto.betreiber_meldung.leer`; Text oder Zusammenhang länger als `BETREIBER_MELDUNG_MAX` (2000) → `konto.betreiber_meldung.zu_lang` (mit `max`); `art` nicht in `BETREIBER_MELDUNG_ARTEN` → `konto.betreiber_meldung.art`; Tagesgrenze (Punkt 8) → `konto.betreiber_meldung.grenze`. Nur bei Erfolg aller Prüfungen entsteht eine Zeile. Eine Meldung ohne Zusammenhang und ohne Reise ist gültig.
8. **Tagesgrenze:** höchstens `JE_KONTO_MELDUNGEN = (10, 24 * 3600)` Meldungen je Konto und Tag, gezählt mit `_begrenzt` in der Tabelle `versand` unter dem Schlüssel `betreiber_meldung:<konto>`; jede angenommene Meldung trägt eine Zeile ein, abgelehnte (leer, zu lang, falsche Art) zählen nicht. Begründung: das gemeinsame Mailkontingent (Resend Free, 100 Mails/Tag für alle Dienste, bei der Instanz zuletzt 15–26 verbraucht, Spielraum rund 70). Die elfte Meldung eines Kontos am selben Tag wird mit `konto.betreiber_meldung.grenze` abgelehnt, weder gespeichert noch gemailt; das Konto eines anderen Testers ist davon unberührt.
9. **Mail an jedes Betreiber-Konto:** Betreiber sind alle nicht gesperrten Konten mit dem Recht `betreiber` in `konten.rechte` (wie bei den Freischaltungen, `konten.recht(k, "betreiber")`). Jedes bekommt eine Mail in seiner Sprache (`konten.sprache`, sonst `texte.VORGABE_REISE`) mit Betreff `konto.betreiber_meldung.mail_betreff` und Text `konto.betreiber_meldung.mail_text` (Nummer, Name und Adresse des Testers, Art, Reise oder „-“, Text, Zusammenhang oder „-“, Hinweis zum Abhaken). **Reply-To ist die Adresse des Testers**, damit „Antworten“ ihn erreicht: `mail_senden(an, betreff, text, antwort_an=None)` setzt im SMTP-Zweig den Kopf `Reply-To`; im `FR_MAIL_DATEI`-Zweig steht `antwort_an` als zusätzliches Feld in der JSON-Zeile (nur wenn gesetzt, sonst bleibt die Zeile wie bisher, bestehende Tests ändern sich nicht). Absender bleibt die Adresse der Instanz (nie die des Testers). Gibt es kein Betreiber-Konto, entsteht keine Mail; die Meldung bleibt gespeichert und der Tester bekommt „angekommen“ (Betreiber sehen sie, sobald es einen gibt, mit dem Befehl auf dem Server).
10. **Mailfehler verlieren nichts.** Die Zeile ist gespeichert, **bevor** Mails gehen, und die Mails laufen nach dem Abschluss der Transaktion. Wirft `mail_senden` `KontoFehler` (nicht eingerichtet, SMTP-Fehler), wird eine Zeile auf stderr geschrieben (`operator report <nr>: mail failed: <Schlüssel>`, ohne Text der Meldung und ohne Adressen) und die Schleife läuft für die übrigen Betreiber weiter. Der Tester bekommt trotzdem „angekommen“; der Betreiber sieht die Meldung bei `my_trips` und mit `konten.py meldungen`.
11. **`betreiber_meldungen(alle=False)`** liefert die Meldungen, älteste zuerst, jeweils mit Name und Adresse des Kontos (`LEFT JOIN konten`); ohne `alle` nur offene (`issue IS NULL`). **`betreiber_meldung_erledigt(nr, issue)`** setzt `issue` (getrimmt); ein leerer Verweis wirft `konto.betreiber_meldung.issue_fehlt` und ändert nichts; es gibt `False` zurück, wenn die Meldung nicht existiert. **`eigene_betreiber_meldungen(kid)`** liefert die Meldungen des Kontos für den Export (Punkt 16): `art`, `text`, `zusammenhang`, `reise`, `zeit`, `erledigt` (ja/nein, abgeleitet aus `issue`), **ohne** den Verweis auf das Issue (er führt in ein privates Repo und gehört dem Betreiber).
12. **Löschen des Kontos** (`loeschen(kid)`, #381): `betreiber_meldungen` kommt in die Tabellenliste der Transaktion (`DELETE … WHERE konto = ?`), und der Versand-Schlüssel `betreiber_meldung:<kid>` in die Löschung der `versand`-Zeilen (neben `adresse:<e>` und `warteliste:<e>`). `engine/tests/test_loeschen_konto.py` prüft über `sqlite_master`, dass in **keiner** Tabelle eine Zeile des Kontos bleibt, und deckt die neue Tabelle damit ohne Änderung ab (der Test bleibt grün und fängt ein Vergessen). Mails an Betreiber, die schon zugestellt wurden, liegen im Postfach des Betreibers und sind nicht Sache der Software (Satz dazu in der Datenschutzzeile, Punkt 21).

### Sicht des Betreibers

13. **Bei `my_trips`:** `meine_reisen_konto(k)` hängt für Konten mit dem Recht `betreiber` nach den Freischaltungs-Anfragen den Block der offenen Meldungen an: Kopfzeile `konnektor.meine_reisen.betreiber_meldungen` (Anzahl), dann je Meldung eine Zeile `konnektor.meine_reisen.betreiber_meldung` (Nummer, Art über `wert.<Art>`, Name, Adresse, Text auf eine Zeile verdichtet und auf 300 Zeichen gekürzt), höchstens die letzten 20. Ohne offene Meldungen entfällt der Block ganz. **Nicht-Betreiber sehen nie eine Liste**, auch nicht ihre eigenen Meldungen (die stehen nur in ihrem Export).
14. **CLI** (`python3 engine/konten.py …`, Ausgaben englisch wie die übrigen Befehle, Kopf der Datei dokumentiert sie):
    - `meldungen [--alle]`: je Meldung eine Kopfzeile `#<nr>  <Datum>  <Art>  <Adresse>  <Name>  trip: <Reise oder ->  issue: <Verweis oder open>`, darunter eingerückt der Text und, falls vorhanden, `context: …`. Ohne `--alle` nur offene.
    - `meldung-erledigt <nr> <issue>`: setzt den Verweis; Ausgabe `done` oder `no such report`; ohne `<issue>` oder mit nicht numerischer Nummer die übliche Aufrufhilfe; ein leerer Verweis → Fehler `issue_fehlt` (Punkt 11).
15. **Arbeitsablauf des Betreibers** (Betrieb, nicht Software): Claude liest `konten.py meldungen`, legt je Meldung ein GitHub-Issue **im privaten Reisen-Repo der Instanz** an (nie im öffentlichen Repo: Name, Adresse und Text eines Testers sind Personendaten) und hakt mit `meldung-erledigt <nr> <Issue>` ab. Der Verweis ist die Referenz auf dieses private Issue.

### Export, Datenschutz, Alpha-Hinweis (`engine/anmeldung.py`)

16. **Export (#498):** `export_person(k, reisen, reise_info)` bekommt das Feld `betreiber_meldungen` (Liste aus `konten.eigene_betreiber_meldungen(kid)`: `art`, `text`, `zusammenhang`, `reise`, `zeit` als ISO-8601-Zeichenkette UTC wie `erstellt`, `erledigt` als `true`/`false`; **ohne** `issue`, ohne `id`, ohne Konto). Nur Meldungen des angemeldeten Kontos kommen vor. Der Export verspricht „alles, was Frieda zu dir speichert“, also gehören sie hinein; ohne Meldungen ist die Liste leer. Alle bisherigen Felder von `person.json` bleiben gleich.
17. **Export-Text:** `konto.export.punkt_4` nennt die Meldungen (Wortlaut siehe „Sichtbare Texte“).
18. **Datenschutzerklärung:** `DATENSCHUTZ_ABSCHNITTE` bekommt `"betreiber_meldungen"` (Schlüssel `recht.datenschutz.betreiber_meldungen.titel` und `.text`), eingefügt nach `"belege"` und vor `"sicherungen"`; die Reihenfolge der übrigen Abschnitte bleibt. `recht.datenschutz.konto_loeschen` nennt zusätzlich „Meldungen an den Betreiber“. `recht.datenschutz.folgt`, `…export`, `…reise_loeschen`, `…namen_freitext` bleiben unverändert (Reihenfolge im Rechte-Block bleibt).
19. **Alpha-Hinweis (`/alpha`):** `alpha_inhalt()` nennt unter den Punkten, wie man Fehler und Wünsche meldet, als eigener Absatz (nicht in `ALPHA_PUNKTE`, weil der Satz einen Wert braucht):
    - Ist `FR_BETREIBER_KONTAKT` gesetzt (nach `instanz.wert("FR_BETREIBER_KONTAKT")` und `.strip()` nicht leer): `recht.alpha.melden` mit `{kontakt}` (maskiert, `esc`).
    - Sonst (fehlt oder leer): `recht.alpha.melden_impressum` mit einem Link auf `/impressum` (`th(..., impressum=link("/impressum", "recht.link.impressum"))`), also nie ein leerer Platzhalter und nie eine halbe Adresse. Das folgt der Regel des Impressums („fehlt einer, nur der Hinweis“), nur dass hier allein der Kontakt zählt.
    Der Satz steht nach den vier Punkten, in beiden Fällen auf der Seite `/alpha`.
20. **Datenschutzzeile `docs/betrieb.md`:** neue Zeile in der Tabelle „Datenschutz je Instanz“: Meldungen an den Betreiber (Text, Zusammenhang, Reise, Zeitpunkt, Konto) | nur der Betreiber (Mail an alle Betreiber-Konten, `konten.py meldungen`, `my_trips`); die Person selbst im Export | mit dem Konto (Konto löschen entfernt die Zeilen und die Zählzeilen); bereits zugestellte Mails im Postfach des Betreibers löscht dieser selbst | bis erledigt und höchstens bis zum Löschen des Kontos; eine Meldung, die schon zu einem Issue im privaten Reisen-Repo geführt hat, bleibt dort, bis der Betreiber sie auf Wunsch entfernt. Der Absatz „Quelle der Datenschutzerklärung“ bleibt gültig; der Satz „als ‚folgt‘ steht dort nur noch Löschen und Export eines Eintrags auf der Warteliste“ wird nicht angefasst.
21. **Datenschutztext** (`recht.datenschutz.betreiber_meldungen.text`, Wortlaut unten) sagt zu, was die Software tut: speichert, mailt, nur der Betreiber sieht es, bleibt bis zum Löschen des Kontos. Er verspricht nichts über das Postfach des Betreibers hinaus. **Zu klären vom Product Owner in der Rechtsprüfung** (nicht Teil dieser Spec): ob der Satz zur Aufbewahrung im privaten Issue in die Erklärung gehört; der Wortlaut ist ein Entwurf (siehe Alpha-Checkliste in #384, rechtliche Prüfung durch den Product Owner).

### Sichtbare Texte (de/en)

Alle Texte stehen im Katalog (`engine/texte_de.py` **und** `engine/texte_en.py`, nie im Code). Der Wortlaut ist der des Entwurfs, wörtlich übernommen. Abweichungen vom Entwurf und neue Schlüssel sind markiert. Der Wortlaut ist **zur Freigabe** (Regel „Erst zeigen, dann bauen“, #436): vor dem Ausliefern zeigt Claude dem Product Owner die neuen sichtbaren Texte (Datenschutz-Abschnitt, Alpha-Satz, Export-Punkt, Werkzeugbeschreibung) als Entwurf im Artefakt.

22. **Deutsch** (verbindlicher Wortlaut nach Freigabe):

    | Schlüssel | Deutsch |
    |---|---|
    | `wert.Fehler` | Fehler |
    | `konto.betreiber_meldung.leer` | Die Meldung ist leer. Bitte beschreibe, was passiert ist oder was du dir wünschst. |
    | `konto.betreiber_meldung.zu_lang` | Die Meldung ist zu lang (höchstens {max} Zeichen je Feld). Bitte kürzen. |
    | `konto.betreiber_meldung.art` | Bitte gib an, ob es ein Fehler, ein Wunsch oder eine Frage ist. |
    | `konto.betreiber_meldung.grenze` | Heute sind schon {n} Meldungen von diesem Konto angekommen. Morgen geht es wieder; Dringendes über den Kontakt im Impressum. |
    | `konto.betreiber_meldung.issue_fehlt` | Bitte den Verweis auf das Issue angeben. |
    | `konto.betreiber_meldung.mail_betreff` | Frieda: Meldung {nr} ({art}) |
    | `konto.betreiber_meldung.mail_text` | {name} ({email}) meldet aus der Claude-App:\n\nArt: {art}\nReise: {reise}\n\n{text}\n\nZusammenhang: {zusammenhang}\n\n„Antworten“ geht an {email}. Abhaken mit „konten.py meldung-erledigt {nr} <Issue>“. |
    | `konnektor.an_frieda_melden.angekommen` | Die Meldung ist beim Betreiber angekommen (Nummer {nr}). Er antwortet, wenn nötig, per Mail an die Adresse des Kontos. |
    | `konnektor.meine_reisen.betreiber_meldungen` | Offene Meldungen an den Betreiber ({n}; abhaken mit „konten.py meldung-erledigt“): |
    | `konnektor.meine_reisen.betreiber_meldung` | - Nr. {nr}, {art} von {name} ({email}): {text} |
    | `konnektor.werkzeug.an_frieda_melden` | Fehler, Wünsche und Fragen zu Frieda selbst (zur Software, nicht zu einer Reise) an den Betreiber dieser Instanz melden; er bekommt sie per Mail und kann der Person antworten. Für Rückmeldungen zu einer Reise gilt rueckmeldung_geben. Vorher den Wortlaut mit der Person abstimmen. Höchstens 10 Meldungen am Tag. |
    | `konnektor.werkzeug.an_frieda_melden.text` | Was passiert ist oder was sich die Person wünscht, in ihren Worten (höchstens 2000 Zeichen) |
    | `konnektor.werkzeug.an_frieda_melden.art` | Fehler, Wunsch oder Frage |
    | `konnektor.werkzeug.an_frieda_melden.zusammenhang` | Optional: was Frieda zuletzt getan hat, welches Werkzeug, welche Fehlermeldung (höchstens 2000 Zeichen) |
    | `konnektor.werkzeug.an_frieda_melden.reise` | Optional: die Reise, bei der es passiert ist |
    | `konnektor.anleitung.frieda.melden` | Fehler, Wünsche und Fragen zu Frieda selbst (nicht zur Reise) gehen mit an_frieda_melden an den Betreiber, nicht mit rueckmeldung_geben in die Reise. Vorher den Wortlaut bestätigen lassen und den Zusammenhang mitschicken (was du zuletzt getan hast, Fehlermeldung). |
    | `recht.datenschutz.betreiber_meldungen.titel` | Meldungen an den Betreiber |
    | `recht.datenschutz.betreiber_meldungen.text` | Meldest du in der Claude-App einen Fehler, einen Wunsch oder eine Frage zu Frieda, speichert Frieda den Text, den Zusammenhang, die Reise, falls du eine nennst, und den Zeitpunkt zu deinem Konto und schickt sie mit deinem Namen und deiner Adresse per Mail an den Betreiber. Nur der Betreiber sieht sie. Sie bleiben, bis du dein Konto löschst. |
    | `recht.datenschutz.konto_loeschen` (**aktueller Text von `main`** plus Ergänzung) | Dein Konto kannst du jederzeit selbst unter „Mein Konto“ löschen. Dann entfallen dein Konto, deine Mitgliedschaften, Anfragen, Abos, Einladungen, Meldungen an den Betreiber, dein Eintrag auf der Warteliste und deine Anmeldungen, auch die in der Claude-App; Reisen, in denen nur du bist, gehen mit. |
    | `recht.alpha.melden` | Fehler und Wünsche meldest du am einfachsten in der Claude-App: Sag Frieda, sie soll es an den Betreiber melden. Ohne Claude-App erreichst du ihn über {kontakt}. |
    | `recht.alpha.melden_impressum` (**neu, fehlt im Entwurf**) | Fehler und Wünsche meldest du am einfachsten in der Claude-App: Sag Frieda, sie soll es an den Betreiber melden. Ohne Claude-App findest du den Kontakt zum Betreiber im {impressum}. |
    | `konto.export.punkt_4` (**geändert**, bisher: „Deine Kontoangaben: Name, E-Mail-Adresse, Sprache, deine Reisen mit Rolle, deine Geräte und deine Einstellungen für Kalender und Benachrichtigungen.“) | Deine Kontoangaben: Name, E-Mail-Adresse, Sprache, deine Reisen mit Rolle, deine Geräte, deine Einstellungen für Kalender und Benachrichtigungen und deine Meldungen an den Betreiber. |

23. **Englisch** (sinngleich, Schreibweise wie die vorhandenen englischen Texte):

    | Schlüssel | English |
    |---|---|
    | `wert.Fehler` | bug |
    | `konto.betreiber_meldung.leer` | The report is empty. Please describe what happened or what you would like. |
    | `konto.betreiber_meldung.zu_lang` | The report is too long (at most {max} characters per field). Please shorten it. |
    | `konto.betreiber_meldung.art` | Please say whether it is a bug, a wish or a question. |
    | `konto.betreiber_meldung.grenze` | {n} reports from this account have already arrived today. Tomorrow it works again; for anything urgent use the contact in the legal notice. |
    | `konto.betreiber_meldung.issue_fehlt` | Please give the reference to the issue. |
    | `konto.betreiber_meldung.mail_betreff` | Frieda: report {nr} ({art}) |
    | `konto.betreiber_meldung.mail_text` | {name} ({email}) reports from the Claude app:\n\nKind: {art}\nTrip: {reise}\n\n{text}\n\nContext: {zusammenhang}\n\n“Reply” goes to {email}. Mark done with “konten.py meldung-erledigt {nr} <issue>”. |
    | `konnektor.an_frieda_melden.angekommen` | The report has reached the operator (number {nr}). If needed, the operator replies by email to the account's address. |
    | `konnektor.meine_reisen.betreiber_meldungen` | Open reports to the operator ({n}; mark done with “konten.py meldung-erledigt”): |
    | `konnektor.meine_reisen.betreiber_meldung` | - No. {nr}, {art} from {name} ({email}): {text} |
    | `konnektor.werkzeug.an_frieda_melden` | Report bugs, wishes and questions about Frieda itself (the software, not a trip) to the operator of this instance; the operator gets them by email and can reply to the person. For feedback on a trip use rueckmeldung_geben. Agree on the wording with the person first. At most 10 reports a day. |
    | `konnektor.werkzeug.an_frieda_melden.text` | What happened or what the person would like, in their words (at most 2000 characters) |
    | `konnektor.werkzeug.an_frieda_melden.art` | bug, wish or question |
    | `konnektor.werkzeug.an_frieda_melden.zusammenhang` | Optional: what Frieda did last, which tool, which error message (at most 2000 characters) |
    | `konnektor.werkzeug.an_frieda_melden.reise` | Optional: the trip where it happened |
    | `konnektor.anleitung.frieda.melden` | Bugs, wishes and questions about Frieda itself (not about the trip) go to the operator with an_frieda_melden, not into the trip with rueckmeldung_geben. Have the wording confirmed first and send the context along (what you did last, error message). |
    | `recht.datenschutz.betreiber_meldungen.titel` | Reports to the operator |
    | `recht.datenschutz.betreiber_meldungen.text` | If you report a bug, a wish or a question about Frieda in the Claude app, Frieda stores the text, the context, the trip if you name one, and the time with your account and sends them with your name and address by email to the operator. Only the operator sees them. They remain until you delete your account. |
    | `recht.datenschutz.konto_loeschen` | You can delete your account yourself at any time under “My account”. Your account, memberships, requests, subscriptions, invitations, reports to the operator, waiting list entry and sign-ins then end, including those in the Claude app; trips that only you are in go with it. |
    | `recht.alpha.melden` | The easiest way to report bugs and wishes is in the Claude app: ask Frieda to report it to the operator. Without the Claude app you can reach the operator via {kontakt}. |
    | `recht.alpha.melden_impressum` (neu) | The easiest way to report bugs and wishes is in the Claude app: ask Frieda to report it to the operator. Without the Claude app you find the operator's contact in the {impressum}. |
    | `konto.export.punkt_4` (geändert) | Your account details: name, email address, language, your trips with your role, your devices, your settings for calendar and notifications and your reports to the operator. |

24. **Regeln für die Texte:** Der Entwurf ändert `recht.datenschutz.folgt` **nicht**; sie bleibt, wie sie auf `main` steht (Export #498). Der Entwurf enthält für `recht.datenschutz.konto_loeschen` die Fassung vor dem Export; sie ist mit dem heutigen Stand von `main` identisch (nur `folgt` hat der Export geändert), die Tabelle oben ist der aktuelle Text plus die Ergänzung. `Antwort-Sätze` und Mail-Text enthalten den Befehl `konten.py meldung-erledigt` als Anleitung für den Betreiber; der Befehlsname bleibt unübersetzt (docs/sprachen.md, Befehle und Dateinamen). `{impressum}` in `recht.alpha.melden_impressum` ist HTML-Wert (`th`). Neue Schlüssel stehen in allen vorhandenen `texte_<sprache>.py` (heute de und en); die Pseudo-Sprache der Tests und die Ausnahmelisten in `engine/tests/test_texte.py` bleiben gleich oder werden kürzer, nie länger. Im Code stehen keine deutschen Literale (der Literal-Test von `test_texte.py` bleibt grün).

## Fehlerverhalten

25. **Leer, zu lang, falsche Art, Grenze:** `KontoFehler` mit dem Schlüssel aus Punkt 7; die Antwort an die Claude-App ist ein Fehler (`isError`) in der Sprache des Kontos; nichts wird gespeichert oder gemailt. Eine Grenze wird nicht „heimlich“ übergangen.
26. **Unbekannte oder fremde Reise:** Fehler `konnektor.frieda_werkzeug.1`; keine Zeile, keine Mail.
27. **Kein Betreiber-Konto vorhanden:** Meldung gespeichert, keine Mail, Tester bekommt „angekommen“ (Punkt 9).
28. **Mail nicht eingerichtet oder SMTP-Fehler:** Punkt 10 (Meldung bleibt, stderr-Zeile, „angekommen“). Ein Fehler beim Speichern selbst (SQLite) ist ein Programmfehler und führt wie bei den übrigen Konto-Werkzeugen zu einer allgemeinen Fehlerantwort; dann ist nichts gespeichert und es geht keine Mail.
29. **Gesperrtes Konto:** Gesperrte Konten kommen nicht durch die Anmeldung; die Prüfung im Werkzeug braucht nichts Eigenes. Gesperrte Betreiber-Konten bekommen keine Mail.
30. **Sicherheit:** Der Text der Meldung ist Nutzdaten der Person: Er wird nur gespeichert, in die Mail geschrieben und angezeigt, nie als Befehl oder Vorlage ausgewertet (feste Platzhalter im Katalog, `str.format` nur auf den Katalogtext, Werte nie als Formatzeichenkette; Zeilenumbrüche im Text sind in der Mail Teil des Textes, aber Betreff und Reply-To bekommen nur die Adresse des Kontos, nie Eingaben der Person; `art` ist aus der festen Aufzählung). Die Tabelle ist nur über das Konto-Werkzeug des angemeldeten Kontos beschreibbar; das Werkzeug nimmt keine Konto-Kennung entgegen. Betreiber-Ausgaben maskieren nichts im Klartext, geben aber Zeilenumbrüche im Text bei `my_trips` verdichtet aus (`" ".join(text.split())`).

## Was darf sich nicht ändern

- `feedback_give`/`rueckmeldung_geben` und alle Reise-Werkzeuge verhalten sich byteweise wie vorher; die Schreibgrenze zählt das neue Werkzeug nicht.
- `mail_senden` ohne `antwort_an`: Zeilen in `FR_MAIL_DATEI` und SMTP-Köpfe wie bisher (keine Reply-To-Zeile, kein neues JSON-Feld).
- `engine/neu.py` (`nachziehen`) und `betrieb/deploy.sh` bleiben unverändert: kein neues Modul, keine Umstellung der Reisedaten.
- `recht.datenschutz.folgt`, `…export`, `…reise_loeschen`, `…namen_freitext`, der Export (`person.json`-Felder außer dem neuen, ZIP, Reihenfolge) und die Löschseiten (#381).
- Die Freischaltungs-Anfragen bei `my_trips` (Reihenfolge und Text) bleiben; die Meldungen kommen danach.
- Beide Beispielreisen (`beispiel/reisen/beispielreise`, `beispiel/reisen/stadtwochenende`) funktionieren: Das Werkzeug kennt keine Wanderung als Regelfall; es ist an Konto und Reise-Auswahl unabhängig von der Art der Reise.

## Acceptance Criteria

- **AC-1 (Werkzeug für jedes Konto):** Für ein Konto mit Mitgliedschaft in `beispielreise`, eines mit Mitgliedschaft in `stadtwochenende`, eines mit beiden und eines ohne Reise listet `frieda_werkzeuge(k)` genau ein Werkzeug `an_frieda_melden` (englisch `report_to_frieda`); ohne Reise hat sein Schema keine Eigenschaft `reise`, mit Reisen ist `reise` eine Aufzählung genau der eigenen Reisen.
- **AC-2 (Alias):** In `schnittstelle.NAMEN` steht `report_to_frieda` ↔ `an_frieda_melden`, in `PARAMETER` `zusammenhang` ↔ `context`; ein Aufruf mit den englischen und mit den deutschen Namen und Parametern führt zum selben Ergebnis.
- **AC-3 (Meldung anlegen):** Gegeben ein Konto Ida (Mitglied von `beispielreise`), wenn `an_frieda_melden` mit `art=Fehler`, `text`, `reise=beispielreise`, `zusammenhang` aufgerufen wird, dann entsteht genau eine Zeile in `betreiber_meldungen` (`konto`, `reise`, `art`, `text`, `zusammenhang`, `zeit` gesetzt, `issue` `NULL`) und die Antwort ist `konnektor.an_frieda_melden.angekommen` mit der Nummer der Zeile, kein Fehler. Ohne `reise` und `zusammenhang` entsteht die Zeile mit leeren Feldern.
- **AC-4 (Mail an Betreiber mit Reply-To):** Gegeben zwei Betreiber-Konten (eines englisch, eines deutsch) und ein Nicht-Betreiber, wenn Ida meldet, dann enthält `FR_MAIL_DATEI` genau zwei Mails (nur an die Betreiber), jede in der Sprache ihres Empfängers (Betreff `konto.betreiber_meldung.mail_betreff`, Text mit Nummer, Name, Adresse, Art, Reise, Text und Zusammenhang), jede mit `antwort_an` gleich der Adresse von Ida. Im SMTP-Zweig trägt die Nachricht den Kopf `Reply-To: <Adresse von Ida>` und als Absender die Adresse der Instanz.
- **AC-5 (Fremde Reise abgelehnt):** Gegeben Idas Konto und eine Reise, in der sie nicht Mitglied ist (`stadtwochenende`), wenn sie `reise=stadtwochenende` meldet, dann Fehlerantwort `konnektor.frieda_werkzeug.1`, keine Zeile, keine Mail.
- **AC-6 (Pflicht und Grenzen der Felder):** Leerer oder nur aus Leerraum bestehender `text` → `konto.betreiber_meldung.leer`; `text` oder `zusammenhang` mit 2001 Zeichen → `konto.betreiber_meldung.zu_lang`, genau 2000 Zeichen ist erlaubt; `art` außerhalb der Aufzählung oder fehlend → `konto.betreiber_meldung.art`; in allen drei Fällen keine Zeile, keine Mail, kein Eintrag in `versand`.
- **AC-7 (Tagesgrenze):** Gegeben Idas Konto, wenn sie 10 Meldungen am selben Tag sendet, dann werden alle 10 angenommen, die elfte ergibt `konto.betreiber_meldung.grenze` (mit `n`=10), ohne Zeile und Mail; Tims Konto (anderes Konto) kann am selben Tag trotzdem melden; Zeilen in `versand` unter `betreiber_meldung:<konto>` sind älter als 24 Stunden nicht mehr gezählt (Zeit über das Mittel der Tests gesetzt).
- **AC-8 (Mailfehler verliert nichts):** Gegeben `mail_senden` wirft `KontoFehler` für einen Betreiber (SMTP nicht eingerichtet oder Fehler), dann ist die Zeile gespeichert, der Tester bekommt „angekommen“, der zweite Betreiber bekommt seine Mail trotzdem, auf stderr steht genau eine Zeile `operator report <nr>: mail failed: …` je gescheiterte Mail (ohne Text der Meldung, ohne Adresse); die Meldung erscheint bei `my_trips` des Betreibers und in `konten.py meldungen`. Gibt es gar kein Betreiber-Konto: Zeile gespeichert, keine Mail, „angekommen“.
- **AC-9 (Löschen entfernt alles):** Gegeben Ida hat gemeldet (Zeile und Schlüssel `betreiber_meldung:<konto>` in `versand`), wenn ihr Konto gelöscht wird (`konten.loeschen`), dann gibt es keine Zeile in `betreiber_meldungen` mit ihrem Konto und keinen `versand`-Schlüssel `betreiber_meldung:<konto>`; Meldungen anderer Konten bleiben. `test_loeschen_konto.py` bleibt grün (dessen Prüfung über `sqlite_master` erfasst die neue Tabelle ohne Änderung).
- **AC-10 (Betreiber sieht offene Meldungen):** Gegeben ein Betreiber-Konto und zwei offene Meldungen, dann enthält `meine_reisen_konto` nach den Freischaltungs-Anfragen die Kopfzeile mit der Anzahl und je Meldung eine Zeile mit Nummer, Art, Name, Adresse und verdichtetem, auf 300 Zeichen gekürztem Text (höchstens die letzten 20). Eine als erledigt abgehakte Meldung steht nicht mehr darin. Ohne offene Meldungen fehlt der Block ganz.
- **AC-11 (Nicht-Betreiber sieht keine Liste):** Gegeben Idas Konto (kein Betreiber) mit eigener offener Meldung, dann enthält `meine_reisen_konto` für sie weder Kopfzeile noch Meldungszeile.
- **AC-12 (CLI listet und hakt ab):** `konten.py meldungen` gibt offene Meldungen aus (Nummer, Datum, Art, Adresse, Name, `trip:`, `issue: open`, Text, bei Zusammenhang `context:`); `--alle` auch erledigte mit ihrem Verweis; `konten.py meldung-erledigt <nr> <issue>` setzt den Verweis und gibt `done` aus (danach fehlt die Meldung ohne `--alle`); eine unbekannte Nummer gibt `no such report`; ein leerer Verweis führt zu Fehler `issue_fehlt` und lässt die Meldung offen.
- **AC-13 (Export enthält die eigenen Meldungen):** Gegeben Ida und Karl haben je eine Meldung, davon Idas eine erledigt, dann enthält `person.json` von Ida (`export_person`) unter `betreiber_meldungen` genau ihre Meldung mit `art`, `text`, `zusammenhang`, `reise`, `zeit` und `erledigt`, aber ohne `issue`, ohne `id` und ohne Konto; Karls Meldung und seine Adresse kommen nirgends in Idas ZIP vor. Ohne Meldungen ist die Liste leer. Die bisherigen Felder von `person.json` sind unverändert.
- **AC-14 (Datenschutzseite):** `/datenschutz` (de und en) enthält den Abschnitt „Meldungen an den Betreiber“ / „Reports to the operator“ mit dem Wortlaut aus Punkt 22/23, an der Stelle nach „Belege“ und vor „Sicherungen“; `recht.datenschutz.konto_loeschen` nennt die Meldungen; der Rechte-Block (`…reise_loeschen`, `…namen_freitext`, `…export`, `…folgt`, `…kontakt`) ist unverändert in Wortlaut und Reihenfolge. `test_rechtliches.py` bleibt grün.
- **AC-15 (Alpha-Seite nennt den Weg):** `/alpha` (de und en) enthält den Satz aus `recht.alpha.melden` mit dem Wert von `FR_BETREIBER_KONTAKT`, wenn er gesetzt ist (maskiert: ein Wert mit `<` erscheint als Text, nicht als HTML); ist er nicht gesetzt oder nur Leerraum, steht stattdessen `recht.alpha.melden_impressum` mit einem Link `/impressum`, kein leerer Platzhalter und keine Zeichenfolge `{kontakt}`.
- **AC-16 (Anleitung):** `anleitung_frieda(k)` enthält für ein Konto mit Reisen und für eines ohne Reise den Satz `konnektor.anleitung.frieda.melden` in der Sprache des Kontos (de und en).
- **AC-17 (Export-Text):** `konto.export.punkt_4` nennt die Meldungen an den Betreiber (de und en); die Seite Mein Konto zeigt ihn so.
- **AC-18 (Texte vollständig):** Jeder Schlüssel aus Punkt 22/23 steht in `texte_de.py` und `texte_en.py` (gleiche Platzhalter); `wert.Fehler` existiert; `test_texte.py` (Parität, Platzhalter, Literal-Test, Ausnahmelisten nicht länger, Pseudo-Sprache) bleibt grün; `recht.datenschutz.folgt` ist byteweise wie auf `main`.
- **AC-19 (Nichts Weiteres ändert sich):** `betrieb/deploy.sh` und `neu.py` unverändert; `mail_senden` ohne `antwort_an` schreibt in `FR_MAIL_DATEI` dieselbe JSON-Zeile wie vorher (ohne `antwort_an`); die bestehenden Tests der Konten, des Konnektors und der Warteliste bleiben grün.
- **AC-20 (Abnahme auf der Instanz):** Nach dem Ausliefern (Prüfpunkte des Issues, nach dem Ausliefern, an einer eigenen Testreise/einem Testkonto der Instanz, nie an echten Reisen): (a) Probe der Mail: Eine Meldung über die Claude-App kommt beim Betreiber an und „Antworten“ adressiert den Tester; (b) Löschen: ein Testkonto mit Meldung wird gelöscht, `konten.py meldungen --alle` zeigt keine Zeile mehr; (c) Datenschutz: `/datenschutz` und `/alpha` auf der Instanz zeigen die neuen Texte; (d) Export des Testkontos enthält die Meldung. Ergebnis als Kommentar in #530.

## Test Plan

Datei `engine/tests/test_betreiber_meldung.py` (neu). Nur erfundene Daten: Ida und Karl (`beispielreise`), Tom und Lea (`stadtwochenende`), je ein Betreiber-Konto in `de` und `en`, ein Konto ohne Reise; Mails über `FR_MAIL_DATEI`, eigene Datenbank je Test (Muster der Fixtures aus `test_loeschen_konto.py`/`test_export.py`), Texte über `meldet(...)`/`text(...)` aus `conftest.py` statt kopierter Sätze, beide Beispielreisen parametrisiert. Die RED-Phase schreibt die Tests vor der Umsetzung.

Werkzeug und Konnektor:
- [ ] `test_werkzeug_in_liste_fuer_jedes_konto` (parametrisiert: Konto in `beispielreise`, in `stadtwochenende`, in beiden, ohne Reise): genau ein Werkzeug `an_frieda_melden`; Schema ohne `reise` bei Konto ohne Reise; `reise`-Aufzählung gleich den eigenen Reisen sonst; `art` ist eine Aufzählung der drei Arten; Pflichtfelder `text`, `art`. (AC 1)
- [ ] `test_alias_deutsch_englisch`: `schnittstelle.NAMEN`/`PARAMETER` enthalten die Paare; Aufruf mit `report_to_frieda`/`context` und mit `an_frieda_melden`/`zusammenhang` gleich. (AC 2)
- [ ] `test_meldung_wird_gespeichert_und_nummer_geantwortet` (beide Beispielreisen): Zeile mit allen Feldern, `issue` `NULL`, Antwort `angekommen` mit Nummer; ohne `reise`/`zusammenhang` leere Felder. (AC 3)
- [ ] `test_fremde_reise_abgelehnt`: Idas Meldung mit `reise=stadtwochenende` → Fehler `konnektor.frieda_werkzeug.1`, keine Zeile, keine Mail, kein `versand`-Eintrag. (AC 5)
- [ ] `test_leer_zu_lang_falsche_art`: Leer, nur Leerraum, 2000 Zeichen ok, 2001 Zeichen Text und Zusammenhang abgelehnt, falsche und fehlende Art; keine Zeile, kein `versand`-Eintrag. (AC 6)
- [ ] `test_zaehlt_nicht_in_schreibgrenze`: Viele Meldungen (bis zur Tagesgrenze) lassen `FR_GRENZE_SCHREIBEN` unberührt; eine Schreibwerkzeug-Anfrage danach wird nicht begrenzt. (Punkt 2)
- [ ] `test_anleitung_nennt_melden` (de und en, mit und ohne Reise). (AC 16)

Mail und Grenze:
- [ ] `test_mail_an_betreiber_mit_reply_to`: zwei Betreiber (de, en), ein Nicht-Betreiber, ein gesperrter Betreiber; Mails nur an die zwei, in deren Sprache, `antwort_an` = Adresse des Testers, Betreff und Text mit allen Feldern; Absender-/Betreff-Zeilen enthalten keine Eingaben des Testers außer der Nummer. (AC 4)
- [ ] `test_mail_senden_antwort_an_smtp`: SMTP-Zweig mit Spion (`smtplib.SMTP` ersetzt): `Reply-To` gesetzt; ohne `antwort_an` kein `Reply-To`, `FR_MAIL_DATEI`-Zeile ohne `antwort_an`. (AC 4, 19)
- [ ] `test_grenze_10_je_konto_und_tag`: zehn Meldungen ok, elfte `grenze` mit `n`=10; anderes Konto ok; Zeit der `versand`-Zeilen älter als 24 h zählt nicht; abgelehnte (leer, zu lang) zählen nicht. (AC 7)
- [ ] `test_mailfehler_verliert_meldung_nicht`: `mail_senden` wirft für den ersten Betreiber; Zeile bleibt, Antwort „angekommen“, zweiter Betreiber bekommt Mail, genau eine stderr-Zeile je Fehler ohne Text und Adresse (`capsys`); Meldung bei `my_trips` und in der CLI sichtbar. (AC 8)
- [ ] `test_ohne_betreiber_konto`: Zeile gespeichert, keine Mail, „angekommen“. (AC 8)

Löschen, Export, Betreiber-Sicht, CLI:
- [ ] `test_loeschen_entfernt_zeilen_und_versand_schluessel`: nach `konten.loeschen` keine Zeile des Kontos in `betreiber_meldungen`, kein Schlüssel `betreiber_meldung:<konto>` in `versand`, Meldungen anderer Konten bleiben. `test_loeschen_konto.py` bleibt unverändert grün (prüft über `sqlite_master` jede Tabelle). (AC 9)
- [ ] `test_export_enthaelt_eigene_meldungen_ohne_issue`: `export_person` für Ida: genau ihre Meldung, Felder `art`, `text`, `zusammenhang`, `reise`, `zeit`, `erledigt` (ja bei abgehakter), kein `issue`/`id`/`konto`; ZIP-Gesamtsuche über den Export (Muster `test_export.py`) findet Karls Meldung und Adresse nicht; leere Liste ohne Meldungen; bestehende Felder unverändert (Vergleich mit dem Stand ohne Meldungen). (AC 13)
- [ ] `test_betreiber_sieht_offene_meldungen_bei_my_trips`: Block mit Anzahl, Zeilen mit Nummer, Art, Name, Adresse, gekürztem verdichtetem Text, höchstens 20; abgehakte fehlt; Freischaltungs-Anfragen davor; ohne Meldungen kein Block. (AC 10)
- [ ] `test_nicht_betreiber_sieht_keine_liste`: Ida mit eigener Meldung: kein Block bei `my_trips`. (AC 11)
- [ ] `test_cli_meldungen_und_erledigt`: `konten.main(["meldungen"])` und `["meldungen", "--alle"]` (Ausgabe mit `capsys`), `["meldung-erledigt", nr, "<Issue>"]` → `done`; unbekannte Nummer → `no such report`; leerer Verweis → Fehler `issue_fehlt`, Meldung bleibt offen; nicht numerische Nummer → Aufrufhilfe. (AC 12)

Seiten und Texte:
- [ ] `test_datenschutz_nennt_meldungen` (de und en): Abschnitt vorhanden, Reihenfolge nach „Belege“ vor „Sicherungen“, `konto_loeschen` nennt die Meldungen, Rechte-Block und `folgt` unverändert (Vergleich mit `text("recht.datenschutz.folgt")`). (AC 14)
- [ ] `test_alpha_nennt_kontakt_mit_und_ohne_einstellung` (de und en): mit gesetztem `FR_BETREIBER_KONTAKT` (maskiert, Wert mit `<`/`&` erscheint als Text) der Satz mit Kontakt; ohne Wert und mit nur Leerraum der Satz mit Link `/impressum`, kein `{kontakt}` auf der Seite. (AC 15)
- [ ] `test_export_text_nennt_meldungen` (de und en). (AC 17)
- [ ] `test_texte_vollstaendig`: alle Schlüssel aus Punkt 22/23 in allen Sprachen aus `texte.SPRACHEN`, gleiche Platzhalter, `wert.Fehler` vorhanden; `folgt` unverändert. Der Lauf von `test_texte.py` (Parität, Literale, Ausnahmelisten nicht länger, Pseudo-Sprache) und `test_rechtliches.py` bleibt grün. (AC 18)
- [ ] `test_unveraendert`: `feedback_give` unverändert; `betrieb/deploy.sh` und `neu.py` nicht in der Änderung (Test zur Modulliste in `deploy.sh` bleibt grün). (AC 19)

Gesamt:
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests -n 3` grün; die bestehenden Tests unverändert grün.

**Instanz-Tests:** Die Schnittstelle (neues Konto-Werkzeug, neuer Parameter `antwort_an`, neue Texte) berührt, was die einbindenden Instanzen nutzen. Vor dem Vorspulen auf `main` laufen darum die Tests der einbindenden Instanzen mit dem Branch (Anleitung im privaten Reisen-Repo der Instanz, CLAUDE.md); die öffentliche CI führt private Tests nicht aus. Nach dem Ausliefern: Abnahme nach AC 20 auf der Instanz, Ergebnis im Issue.

## Dokumentation

- `docs/betrieb.md`: neue Zeile in der Tabelle „Datenschutz je Instanz“ (Punkt 20) und ein kurzer Absatz „Meldungen an den Betreiber (#530)“ in den Betriebsbefehlen: `konten.py meldungen [--alle]`, `konten.py meldung-erledigt <nr> <issue>`, wer die Mail bekommt (Konten mit Recht `betreiber`), Grenze 10 je Konto und Tag, Mailfehler und Wiederfinden, Issues nur im privaten Reisen-Repo. Der Satz „als ‚folgt‘ steht dort nur noch …“ bleibt.
- `docs/konnektor.md`: Zeile `report_to_frieda` in der Liste der Konto-Werkzeuge (neben `sprache_setzen`) und im Paar `report_to_frieda` ↔ `an_frieda_melden` sowie `context` ↔ `zusammenhang` in den Tabellen der englischen Namen.
- `docs/konten.md`: Abschnitt „Betrieb“ nennt die zwei Befehle und die Tabelle `betreiber_meldungen`; Hinweis, dass Löschen und Export sie mitnehmen.
- Kopf von `engine/konten.py` (Aufrufe) enthält die zwei neuen Befehle.
- Kein neues ADR: Konten und Betrieb, keine Grundform. Die Prüfstelle ADR-0001 (zehn Fragen): Keine Grundform und kein Merkmal berührt (Frage zu Arten und Merkmalen entfällt); nichts Reisespezifisches in der Engine; beide Beispielreisen unberührt; keine KI; Texte im Katalog; Daten des Kontos gehören der Kontendatenbank, nicht dem Reisen-Repo.

## Dependencies

| Abhängigkeit | Art | Wirkung |
|---|---|---|
| `konten.py` (`_begrenzt`, `versand`, `loeschen`, `recht`, `mail_senden`) | Code, geändert | Ablage, Tagesgrenze, Mail, Löschen |
| `konnektor.py` (`frieda_werkzeuge`, `frieda_werkzeug`, `meine_reisen_konto`, `anleitung_frieda`) | Code, geändert | Werkzeug, Betreiberliste, Anleitung |
| `anmeldung.py` (`DATENSCHUTZ_ABSCHNITTE`, `alpha_inhalt`, `export_person`) | Code, geändert | Rechtstexte, Export |
| `instanz.wert("FR_BETREIBER_KONTAKT")` | Einstellung, nur gelesen | Kontakt auf `/alpha` |
| #381 (Löschen), #498 (Export), #383 (Datenschutz), #382 (Warteliste, Betreiber-Recht) | Nachbarn auf `main` | Löschen und Export nehmen die Tabelle mit; `folgt` bleibt |
| SMTP (Resend) | Fremd | gemeinsames Kontingent 100 Mails/Tag, daher Grenze 10 je Konto und Tag |
| Private Reisen-Repo der Instanz | Betrieb | Instanz-Tests vor dem Vorspulen; Issues zu Meldungen nur dort |

## Architektur-Entscheidung (ADR)

**ADR-Nr.:** ADR-0001, ADR-0005 und ADR-0006 (bestehend, keine neue ADR)

Rationale: Die Meldungen gehören zum Konto und zum Betrieb, nicht zur Reise-Ontologie (ADR-0001: keine Grundform, kein Merkmal, keine KI). Ablage, Löschen und Export folgen den Konten (ADR-0005); alle sichtbaren Texte stehen im Katalog, Werkzeug- und Parameternamen englisch mit deutschem Alias (ADR-0006). Die ADRs werden nicht geändert.

## Scope

**Affected Files:**

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/konten.py` | MODIFY | Tabelle `betreiber_meldungen`, `an_betreiber_melden`, `betreiber_meldungen`, `betreiber_meldung_erledigt`, `eigene_betreiber_meldungen`, `mail_senden(..., antwort_an=None)`, `loeschen`, CLI `meldungen`, `meldung-erledigt` |
| `engine/konnektor.py` | MODIFY | Konto-Werkzeug `an_frieda_melden`, Behandlung vor der Reise-Auswahl, Betreiberliste in `meine_reisen_konto`, Satz in `anleitung_frieda` |
| `engine/schnittstelle.py` | MODIFY | `report_to_frieda` ↔ `an_frieda_melden`, `context` ↔ `zusammenhang` |
| `engine/anmeldung.py` | MODIFY | `DATENSCHUTZ_ABSCHNITTE`, `alpha_inhalt`, `export_person` |
| `engine/texte_de.py`, `engine/texte_en.py` | MODIFY | neue und geänderte Schlüssel laut „Sichtbare Texte“ |
| `engine/tests/test_betreiber_meldung.py` | CREATE | Tests nach Test Plan |
| `docs/betrieb.md`, `docs/konnektor.md`, `docs/konten.md` | MODIFY | Datenschutzzeile, Werkzeug, Befehle |

**Estimated Changes:** 10 Dateien (1 neu), etwa +350/−10 Zeilen inklusive Tests und Doku. Risiko mittel: neue Mail an Betreiber über das gemeinsame Mailkontingent; Löschen und Export müssen die neue Tabelle mitnehmen.

## Definition of Done

- [ ] Alle Punkte des Test Plans sind in `engine/tests/test_betreiber_meldung.py` umgesetzt und grün; `engine/tests` insgesamt grün (Pflichtprüfungen `tests (leer)`, `tests (instanz)`, `gitleaks`).
- [ ] Alle Acceptance Criteria sind durch Tests oder den Abnahmeschritt auf der Instanz belegt.
- [ ] Texte in allen Sprachen (de, en) vollständig; Ausnahmelisten in `test_texte.py` nicht länger; Datenschutztext stimmt mit dem Verhalten überein.
- [ ] Die sichtbaren Texte (Datenschutz-Abschnitt, Alpha-Satz, Export-Punkt) hat der Product Owner im Entwurf gesehen und freigegeben (Erst zeigen, dann bauen).
- [ ] Die Tests der einbindenden Instanzen laufen mit dem Branch, vor dem Vorspulen auf `main`.
- [ ] Doku ergänzt; `deploy.sh` unverändert (kein neues Modul).
- [ ] Nach dem Ausliefern: Probe-Meldung auf der Instanz, Mail kommt beim Betreiber mit Antwortadresse an, Meldung abgehakt; Ergebnis im Issue #530, Issue erst danach schließen.
- [ ] Die Prüfstelle (zehn Fragen, ADR-0001) ist im PR beantwortet.

## Changelog

- 2026-11-12: Entwurf der Spec (v1.0) aus Kontext, Plan (Kommentar in #530) und Entwurf der Umsetzung; Festlegungen: Arten großgeschrieben mit neuem `wert.Fehler`, `recht.alpha.melden_impressum` für den Rückfall, `recht.datenschutz.folgt` unberührt, Meldungen im Export ohne Issue-Verweis.
