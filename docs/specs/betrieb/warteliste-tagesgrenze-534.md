---
entity_id: warteliste-tagesgrenze-534
type: feature
created: 2026-11-12
updated: 2026-11-12
status: draft
workflow: feat-534-warteliste-tagesgrenze
version: "1.0"
tags: [konten, warteliste, betrieb, mail-kontingent, alpha, m5a]
---

# Warteliste: Tagesgrenze für neue Einträge (#534, Meilenstein M5a)

## Approval

- [ ] Approved

## Purpose

Der Mailversand der Instanz läuft über Resend im kostenlosen Tarif: 100 Mails pro Tag für alle Dienste zusammen (Entscheidung des Product Owners vom 12.11.2026 in #384; Spielraum etwa 80). Jeder Eintrag auf der Warteliste (#382) löst eine Bestätigungsmail aus. Ein LinkedIn-Beitrag zum Alpha-Start könnte an einem Tag so viele Einträge bringen, dass das Kontingent aufgebraucht ist und Anmeldecodes und andere Dienste keine Mail mehr bekommen.

Mit dieser Spec nimmt die Warteliste je Kalendertag (UTC) höchstens N Einträge an, die eine Bestätigungsmail auslösen (Vorgabe 20, einstellbar über `FR_GRENZE_WARTELISTE_TAG`). Darüber zeigt die Seite freundlich, dass heute alle Plätze vergeben sind, schickt keine Mail und speichert nichts. Der Betreiber bekommt einmal je Tag eine Meldung über Mein Konto (kein Telegram, es ist kein Ausfall). Technische Analyse: `docs/context/feat-534-warteliste-tagesgrenze.md`.

## Scope

- **Im Scope:**
  - `engine/instanz.py`: `VORGABE_GRENZE_WARTELISTE_TAG = 20` und `grenze_warteliste_tag()`.
  - `engine/konten.py`: Tagesbeginn, Zählung und Prüfung in `warteliste_eintragen`, Merker für die einmalige Betreiber-Meldung (`warteliste_tagesgrenze_merken`).
  - `engine/anmeldung.py`: Weg `/warteliste` (POST) zeigt die Ablehnung und legt einmal je Tag die Meldung an.
  - Texte in `engine/texte_de.py` und `engine/texte_en.py` (jede künftige `texte_<kürzel>.py` folgt `docs/sprachen.md`).
  - Tests in `engine/tests/test_warteliste.py`.
  - Doku: `docs/konten.md` (Abschnitt Warteliste und Tabelle der Umgebungswerte), `docs/betrieb.md` (Tabelle `FR_GRENZE_*`), `betrieb/einstellungen.beispiel`.
- **Nicht im Scope:**
  - Keine Grenze für Freigaben (`konten.freigeben`), Anmeldecodes, Einladungen oder die Meldung an den Betreiber (#530, hat eigene Grenzen).
  - Kein Telegram- oder MQ-Alarm; kein neuer Monitor-Check (der Resend-Teil-Check in `henemm-infra/scripts/monitor.sh` bleibt die Warnung für das Gesamtkontingent).
  - Keine Warteschlange für abgelehnte Adressen: Wer abgelehnt wird, trägt sich morgen erneut ein. Nichts wird gemerkt.
  - Keine Änderung der bestehenden Begrenzungen je Adresse und je IP (`JE_ADRESSE`, `JE_IP`) und der Höchstzahl unbestätigter Einträge (`WARTELISTE_MAX_UNBESTAETIGT`).
- **Kern (ADR-0001):** Konten und Betrieb, keine Ontologie. Keine Reise, keine Art, kein Merkmal betroffen; keine KI.
- **Instanzen:** Nichts Instanzspezifisches: Der Wert kommt wie `FR_GRENZE_REISEN` aus Umgebung oder Einstellungsdatei der Instanz. Keine echten Adressen in Spec, Tests und Beispielen.
- **Keine Umstellung in `neu.py nachziehen`:** Es wird nur die vorhandene Tabelle `versand` mit neuen Schlüsseln genutzt; kein Reisedatenformat, keine neue Tabelle, kein Handschritt nach dem Software-Wechsel.

## Source

- `engine/konten.py`: `_jetzt` (Z. 97), `_begrenzt` (Z. 281; löscht Zeilen in `versand`, die älter als 24 Stunden sind, zählt je Schlüssel im gleitenden Fenster), `WARTELISTE_MAX_UNBESTAETIGT` (Z. 75), `warteliste_eintragen` (Z. 834), `freigeben` (Z. 909), `loeschen` (Z. 593; räumt die Versand-Schlüssel je Adresse).
- `engine/instanz.py`: `VORGABE_GRENZE_REISEN` (Z. 158), `_grenze` (Z. 162), `grenze_reisen` (Z. 171), `grenze_schreiben` (Z. 176).
- `engine/anmeldung.py`: Weg `/warteliste` POST (Z. 1418 ff.; `KontoFehler` zeigt `warteliste_seite(email, satz)`, sonst immer `warteliste_hinweis("warteliste.gesendet")`), `warteliste_seite` (Z. 306), `betreiber_melden(k, art, text, teile)` (Z. 1589; Meldung an alle Betreiber über `rm.meldung_anlegen`; Beispiel `anfrage_warteliste` Z. 1440), `MELDUNG_WARM` (Z. 522; enthält `betrieb`).
- `engine/texte_de.py`, `engine/texte_en.py`: `konto.fehler.warteliste_voll` (de Z. 3522), `konto.betreiber.warteliste` (de Z. 3525), `konto.meldungen.text.anfrage_warteliste` (de Z. 1128, en Z. 1127), `konto.meldungen.art.betrieb` (en Z. 1145).
- `engine/tests/test_warteliste.py` (Fixture `umgebung` mit festem `_jetzt` und `FR_MAIL_DATEI`, Hilfen `mails`, `bestaetigungswort`), `engine/tests/test_texte.py` (Vollständigkeit der Sprachen, Ausnahmelisten nur kürzer).
- `docs/konten.md` (Abschnitt „Warteliste (#382, Alpha)“ ab Z. 135, Tabelle der Umgebungswerte ab Z. 167), `docs/betrieb.md` (Tabelle `FR_GRENZE_*` ab Z. 303), `betrieb/einstellungen.beispiel` (Z. 141 `FR_GRENZE_REISEN`).

## Implementation Details

### 1. Einstellung (`engine/instanz.py`)

- `VORGABE_GRENZE_WARTELISTE_TAG = 20` neben den anderen Vorgaben.
- `grenze_warteliste_tag()` gibt `_grenze("FR_GRENZE_WARTELISTE_TAG", VORGABE_GRENZE_WARTELISTE_TAG)` zurück. Ungültige Werte (leer, keine ganze Zahl, kleiner als 1) gelten wie bei den anderen Grenzen als nicht gesetzt und ergeben 20. Es gibt keine Möglichkeit, die Grenze mit 0 abzuschalten (Absicht: eine abgeschaltete Grenze wäre ein Fehlerbild, das erst am Tag des Beitrags auffiele).

### 2. Zählung und Prüfung (`engine/konten.py`)

- `_tagesbeginn()` liefert den Zeitstempel (Sekunden) der letzten Mitternacht UTC vor `_jetzt()` (also `jetzt - jetzt % 86400`; die Tage der UTC-Zeitrechnung haben genau 86400 Sekunden). Er nutzt `_jetzt()`, damit Tests die Zeit steuern können.
- Schlüssel in `versand`: `WARTELISTE_TAG = "warteliste-tag"` (eine Zeile je ausgelöster Bestätigungsmail, ohne Adresse, damit keine Adresse im Schlüssel steht) und `WARTELISTE_TAG_GEMELDET = "warteliste-tag-gemeldet"` (Merker, siehe Punkt 3).
- Eigene Zählung statt `_begrenzt`: `SELECT COUNT(*) FROM versand WHERE schluessel = 'warteliste-tag' AND zeit >= ?` mit `_tagesbeginn()`. Das gleitende 24-Stunden-Fenster von `_begrenzt` passt nicht zu „Kalendertag“. Die Zeilen des laufenden Tages bleiben erhalten, weil `_begrenzt` nur Zeilen löscht, die älter als 24 Stunden sind (der Tagesbeginn liegt höchstens 24 Stunden zurück).
- **Reihenfolge der Prüfungen in `warteliste_eintragen`:**
  1. Adresse prüfen (`adresse(roh)`, `KontoFehler` bei ungültiger Adresse).
  2. Mail eingerichtet (`konto.fehler.mail_nicht_eingerichtet`).
  3. Abgelaufene unbestätigte Einträge löschen.
  4. Begrenzung je Adresse und je IP (`konto.fehler.zu_viele_codes`), wie bisher.
  5. **Tagesgrenze (neu):** Ist die Zahl der Zeilen `warteliste-tag` seit Tagesbeginn größer oder gleich `instanz.grenze_warteliste_tag()`, wirft die Funktion `KontoFehler("konto.fehler.warteliste_tag_voll")`. Die Prüfung steht vor den `versand`-Zeilen der Adresse und der IP, vor jeder Unterscheidung nach dem Stand der Adresse und vor jedem Schreiben. Folge: Die Ablehnung gilt für jede Adresse gleich (auch für bereits bestätigte, freigegebene oder unbestätigte), verrät also nichts über den Stand, und die abgelehnte Anfrage speichert nichts (keine Zeile in `warteliste`, keine `versand`-Zeile der Adresse oder der IP; die Transaktion wird mit der Ausnahme zurückgerollt).
  6. `versand`-Zeilen der Adresse und der IP einfügen (wie bisher).
  7. Stand der Adresse: bestätigt oder freigegeben: Rückgabe ohne Mail, **keine** Zeile `warteliste-tag`.
  8. Unbestätigt vorhanden (erneute Mail): Eintrag aktualisieren, Zeile `warteliste-tag` einfügen.
  9. Neu: Prüfung `warteliste_voll` (Höchstzahl unbestätigter Einträge) wie bisher; wird abgelehnt, geht keine Mail raus und es wird **keine** Zeile `warteliste-tag` geschrieben. Sonst Eintrag anlegen und Zeile `warteliste-tag` einfügen.
- Die Zeile `warteliste-tag` wird in derselben Transaktion wie der Eintrag geschrieben, aber erst, wenn feststeht, dass eine Mail ausgelöst wird. Gezählt wird also jede Bestätigungsmail, auch die erneute an eine unbestätigte Adresse (sie kostet ebenfalls Kontingent), nicht aber Anfragen bestätigter Adressen, nicht Ablehnungen und nicht Freigaben (`freigeben` bleibt unverändert und schreibt keine Zeile `warteliste-tag`).
- Der Mailversand liegt wie bisher nach der Transaktion. Scheitert er, bleibt die Zeile `warteliste-tag` gezählt (vorsichtig für das Kontingent; vertretbar, weil ein Fehlschlag selten ist und die Grenze nur zu früh statt zu spät greift).

### 3. Einmalige Meldung an den Betreiber

- `konten.warteliste_tagesgrenze_merken()` gibt `True` genau einmal je UTC-Kalendertag zurück: In einer Transaktion (`with closing(db()) as v, v:`) wird geprüft, ob es eine Zeile `warteliste-tag-gemeldet` mit `zeit >= _tagesbeginn()` gibt; wenn nicht, wird sie eingefügt und `True` zurückgegeben, sonst `False`. Die Schreibsperre der Datenbank macht Prüfen und Einfügen atomar; zwei gleichzeitige abgelehnte Anfragen liefern genau einmal `True`.
- Der Merker liegt in `versand` und wird nach 24 Stunden von `_begrenzt` aufgeräumt, am neuen Tag zählt nur ein Eintrag ab dem neuen Tagesbeginn.
- Ort der Meldung ist `engine/anmeldung.py` (Weg `/warteliste` POST), weil `konten` die Module der Anmeldung nicht importiert. Wirft `warteliste_eintragen` `KontoFehler` mit dem Schlüssel `konto.fehler.warteliste_tag_voll` und gibt `konten.warteliste_tagesgrenze_merken()` `True` zurück, ruft der Weg `betreiber_melden(None, "betrieb", texte.t(texte.VORGABE_REISE, "konto.betreiber.warteliste_tagesgrenze", grenze=n), [("konto.meldungen.text.warteliste_tagesgrenze", {"grenze": n})])` auf, mit `n = instanz.grenze_warteliste_tag()`. Art `betrieb` ist vorhanden und warm und braucht keine Reise (kein Ziel-Link). Es gibt keinen Telegram- und keinen MQ-Aufruf. Die Meldung löst, wie jede Meldung der Art `betrieb`, die Benachrichtigung für Betreiber aus; einmal je Tag ist gewollt.
- Hat kein Betreiber-Konto (nicht gesperrt, Recht `betreiber`) zu melden, tut `betreiber_melden` nichts; das ist kein Fehler der Seite.
- Scheitert das Anlegen der Meldung mit einer Ausnahme, darf die Seite nicht mit einem Serverfehler antworten: Der Weg fängt die Ausnahme, schreibt sie in das Protokoll des Dienstes und zeigt trotzdem die Ablehnungsseite (die Besucherin hat mit dem Betreiberweg nichts zu tun).

### 4. Seite (`engine/anmeldung.py`)

- Bei `KontoFehler` zeigt der Weg wie bei den anderen Ablehnungen das Formular mit dem Satz (`warteliste_seite(email, x.text(sprache_der_seite()))`), Status 200. Die eingegebene Adresse bleibt im Feld, damit die Person morgen nur noch absenden muss.
- Der Satz sagt nicht, wie viele Plätze es gibt, und nennt keine Zahl.

### 5. Sichtbare Texte (de/en)

Alle Texte stehen im Katalog, nie im Code. `engine/texte_de.py` und `engine/texte_en.py` bekommen je drei neue Schlüssel; die Ausnahmelisten in `engine/tests/test_texte.py` bleiben unverändert (dürfen nur kürzer werden).

| Schlüssel | Deutsch | English |
|---|---|---|
| `konto.fehler.warteliste_tag_voll` | Heute sind alle Plätze vergeben. Bitte morgen wieder vorbeischauen. | All places are taken for today. Please come back tomorrow. |
| `konto.betreiber.warteliste_tagesgrenze` | Die Warteliste hat heute ihre Tagesgrenze von {grenze} Einträgen erreicht. Weitere Anmeldungen werden bis morgen (UTC) abgelehnt, damit das Mail-Kontingent reicht. | The waiting list reached its daily limit of {grenze} entries today. Further sign-ups are declined until tomorrow (UTC) so the mail allowance lasts. |
| `konto.meldungen.text.warteliste_tagesgrenze` | Die Warteliste hat heute ihre Tagesgrenze von {grenze} Einträgen erreicht; bis morgen (UTC) werden neue Anmeldungen abgelehnt. | The waiting list reached its daily limit of {grenze} entries today; new sign-ups are declined until tomorrow (UTC). |

Der Wortlaut der Seite „Heute sind alle Plätze vergeben, bitte morgen wieder“ stammt aus dem Issue und ist freundlich ergänzt. Die Seite braucht keinen neuen Baustein (ADR-0002): Es ist das vorhandene Formular mit dem Fehlersatz.

### 6. Doku

- `docs/konten.md`, Abschnitt Warteliste: Tagesgrenze, Grund (Mail-Kontingent der Instanz), was zählt und was nicht, Verhalten der Seite, Meldung an den Betreiber einmal je Tag; Tabelle der Umgebungswerte um `FR_GRENZE_WARTELISTE_TAG` (Vorgabe 20, ungültige oder nicht positive Werte gelten als nicht gesetzt).
- `docs/betrieb.md`: Zeile `FR_GRENZE_WARTELISTE_TAG` in der Tabelle `FR_GRENZE_*` (Vorgabe 20; Ort des Werts wie bei `FR_GRENZE_REISEN`; Hinweis auf das Kontingent von 100 Mails pro Tag für alle Dienste und auf den Resend-Teil-Check im Monitor).
- `betrieb/einstellungen.beispiel`: auskommentierte Zeile `#FR_GRENZE_WARTELISTE_TAG=20` mit einem Satz Erklärung.

## Expected Behavior

- **Input:** POST auf `/warteliste` mit einer Adresse.
- **Output:** Unter der Grenze verhält sich alles wie bisher (derselbe Satz `warteliste.gesendet`, Mail an neue und unbestätigte Adressen). Ab der Grenze erscheint für jede Adresse das Formular mit dem Satz „Heute sind alle Plätze vergeben. Bitte morgen wieder vorbeischauen.“.
- **Side effects:** Je ausgelöster Bestätigungsmail eine Zeile `warteliste-tag` in `versand`. Bei der ersten Ablehnung eines UTC-Tages eine Meldung der Art `betrieb` an alle Betreiber und der Merker `warteliste-tag-gemeldet`. Bei einer Ablehnung durch die Tagesgrenze: keine Mail, keine Zeile in `warteliste`, keine Versand-Zeile der Adresse oder der IP.

## Acceptance Criteria

- **AC-1:** Given `FR_GRENZE_WARTELISTE_TAG` ist nicht gesetzt / When `instanz.grenze_warteliste_tag()` aufgerufen wird / Then ist das Ergebnis 20. (Vorgabe)
- **AC-2:** Given `FR_GRENZE_WARTELISTE_TAG=3` / When `instanz.grenze_warteliste_tag()` aufgerufen wird / Then ist das Ergebnis 3. (Einstellbar)
- **AC-3:** Given `FR_GRENZE_WARTELISTE_TAG` ist `abc`, `0`, `-5` oder leer / When `instanz.grenze_warteliste_tag()` aufgerufen wird / Then ist das Ergebnis 20. (Ungültig)
- **AC-4:** Given die Grenze ist 2 / When drei verschiedene neue Adressen nacheinander eingetragen werden / Then bekommen die ersten beiden je eine Mail und je eine Zeile in `warteliste` und es gibt genau zwei Zeilen `warteliste-tag`. (Bis zur Grenze)
- **AC-5:** Given die Grenze ist 2 und zwei Mails sind heute ausgelöst / When eine dritte neue Adresse eingetragen wird / Then wirft `warteliste_eintragen` `KontoFehler("konto.fehler.warteliste_tag_voll")`, es geht keine Mail raus, es gibt keine Zeile in `warteliste` für diese Adresse und keine `versand`-Zeile mit dem Schlüssel `warteliste:<Adresse>` oder `warteliste-ip:<IP>` für diesen Versuch. (Grenze greift)
- **AC-6:** Given die Tagesgrenze ist erreicht / When die Seite `/warteliste` per POST mit einer neuen Adresse aufgerufen wird / Then antwortet sie mit Status 200 und dem Formular samt Satz `konto.fehler.warteliste_tag_voll` in der Sprache der Seite (de und en), nicht mit `warteliste.gesendet`, und die Adresse steht weiter im Feld. (Seite bei voller Grenze)
- **AC-7:** Given die Grenze war am Tag X erreicht / When die Uhr (`konten._jetzt`) über die nächste Mitternacht UTC gesetzt wird und eine neue Adresse eingetragen wird / Then wird sie angenommen und bekommt eine Mail; Zeilen des Vortags zählen nicht mehr. (Neuer Tag)
- **AC-8:** Given die Grenze ist erreicht um 23:59 UTC / When die Uhr auf 00:01 UTC des nächsten Tages (also zwei Minuten später) gesetzt wird / Then ist die Grenze wieder frei; und given 00:01 UTC mit erreichter Grenze, when die Uhr auf 23:59 UTC desselben Tages gesetzt wird, then bleibt sie erreicht. (Kalendertag, nicht gleitendes Fenster)
- **AC-9:** Given eine Adresse ist unbestätigt eingetragen / When sie sich erneut einträgt und dadurch eine zweite Mail bekommt / Then gibt es zwei Zeilen `warteliste-tag`, und bei erreichter Grenze wird auch die erneute Anfrage abgelehnt (keine zweite Mail, Eintrag unverändert). (Erneute Mail zählt)
- **AC-10:** Given eine Adresse ist bestätigt oder freigegeben und die Grenze ist nicht erreicht / When sie sich erneut einträgt / Then geht keine Mail raus und die Zahl der Zeilen `warteliste-tag` ändert sich nicht. (Bestätigte Adresse zählt nicht)
- **AC-11:** Given die Grenze ist erreicht / When dieselbe Anfrage einmal für eine neue, einmal für eine unbestätigte und einmal für eine bestätigte Adresse gestellt wird / Then ist die Antwort in allen drei Fällen dieselbe Ablehnung (`konto.fehler.warteliste_tag_voll`), und die Datenbank ändert sich in keinem Fall. (Ablehnung verrät nichts)
- **AC-12:** Given die Grenze ist erreicht / When `konten.freigeben(adresse)` für eine bestätigte Adresse aufgerufen wird / Then klappt die Freigabe (Mail „Du bist dabei“ geht raus) und die Zahl der Zeilen `warteliste-tag` ändert sich nicht. (Freigaben zählen nicht)
- **AC-13:** Given `WARTELISTE_MAX_UNBESTAETIGT` ist erreicht (im Test herabgesetzt) und die Tagesgrenze nicht / When eine neue Adresse mit `konto.fehler.warteliste_voll` abgelehnt wird / Then gibt es keine neue Zeile `warteliste-tag`. (Ablehnung wegen Höchstzahl zählt nicht)
- **AC-14:** Given eine Adresse hat die Begrenzung je Adresse erreicht und die Tagesgrenze ist ebenfalls erreicht / When sie sich einträgt / Then lautet die Ablehnung `konto.fehler.zu_viele_codes` (bestehende Begrenzung zuerst); given ungültige Adresse und erreichte Tagesgrenze, then lautet die Ablehnung wie bisher auf die ungültige Adresse. (Reihenfolge mit den bestehenden Grenzen)
- **AC-15:** Given die Grenze ist erreicht und ein Betreiber-Konto existiert / When am selben UTC-Tag fünf Anfragen abgelehnt werden / Then hat das Betreiber-Konto genau eine Meldung der Art `betrieb` zur Tagesgrenze (sichtbar bei `rm.meldungen_des_kontos`), mit der Grenze als Zahl im Text in der Sprache des Betreibers; am nächsten Tag mit erneut erreichter Grenze kommt genau eine weitere. (Meldung genau einmal je Tag)
- **AC-16:** Given die Grenze ist nicht erreicht / When Anfragen angenommen werden / Then entsteht keine Meldung zur Tagesgrenze; given die Grenze wurde mit der letzten angenommenen Anfrage genau erreicht und es gab noch keine Ablehnung, then gibt es auch noch keine Meldung. (Keine Meldung unter der Grenze und ohne Ablehnung)
- **AC-17:** Given zwei Aufrufe von `konten.warteliste_tagesgrenze_merken()` am selben Tag / When sie nacheinander laufen / Then liefert der erste `True` und der zweite `False`; nach Mitternacht UTC liefert der nächste Aufruf wieder `True`. (Atomarer Merker)
- **AC-18:** Given die Grenze wird erreicht / When die Meldung angelegt wird / Then wird weder `send.sh` von Claude MQ noch ein anderer Telegram-Weg aufgerufen (der Test prüft, dass nur `rueckmeldungen.meldung_anlegen` den Betreiber erreicht). (Kein Alarmweg)
- **AC-19:** Given kein Betreiber-Konto existiert / When die Grenze abgelehnt wird / Then antwortet die Seite trotzdem mit der Ablehnung (kein Fehler, kein Absturz). (Kein Betreiber vorhanden)
- **AC-20:** Given `betreiber_melden` wirft eine Ausnahme / When eine Anfrage wegen der Tagesgrenze abgelehnt wird / Then zeigt die Seite trotzdem die Ablehnung mit Status 200. (Fehler beim Melden)
- **AC-21:** Given der Katalog / When `engine/tests/test_texte.py` läuft / Then sind die drei neuen Schlüssel in `texte_de.py` und `texte_en.py` vorhanden, enthalten die Platzhalter `{grenze}` jeweils gleich, und die Ausnahmelisten sind nicht länger geworden. (Texte vollständig)
- **AC-22:** Given die Ablehnungsseite / When sie ausgegeben wird / Then enthält sie weder die Grenze noch die Zahl der Einträge des Tages. (Keine Zahl auf der Seite)
- **AC-23:** Given die Doku / When `docs/konten.md`, `docs/betrieb.md` und `betrieb/einstellungen.beispiel` gelesen werden / Then ist `FR_GRENZE_WARTELISTE_TAG` mit Vorgabe 20 beschrieben; `engine/tests/test_grenzen.py` prüft das wie bei den anderen `FR_GRENZE_*`-Werten. (Doku und Beispiel)
- **AC-24:** Given die Zeilen `warteliste-tag` und `warteliste-tag-gemeldet` enthalten keine Adresse / When ein Konto gelöscht oder exportiert wird (#381, #498) / Then bleibt deren Verhalten unverändert und es bleibt keine personenbezogene Zeile übrig. (Löschen und Export unberührt)

## Test Plan

In `engine/tests/test_warteliste.py` (Fixture `umgebung`, Uhr über `umgebung["uhr"]`, Grenze mit `monkeypatch.setenv("FR_GRENZE_WARTELISTE_TAG", ...)`):

- `test_grenze_vorgabe_einstellbar_und_ungueltig` (AC-1 bis 3, parametrisiert).
- `test_bis_zur_grenze_mails_und_zaehlzeilen` (AC-4).
- `test_grenze_greift_ohne_mail_und_ohne_speichern` (AC-5).
- `test_seite_zeigt_ablehnung_in_de_und_en` (AC-6, 22; über `abruf` aus `test_anmeldung`).
- `test_neuer_tag_gibt_frei` und `test_kalendertag_nicht_gleitendes_fenster` (AC-7, 8; Uhr auf 23:59 und 00:01 UTC).
- `test_erneute_mail_zaehlt` (AC-9).
- `test_bestaetigte_adresse_zaehlt_nicht` (AC-10).
- `test_ablehnung_fuer_jeden_stand_gleich` (AC-11).
- `test_freigaben_zaehlen_nicht` (AC-12).
- `test_ablehnung_wegen_hoechstzahl_zaehlt_nicht` (AC-13).
- `test_reihenfolge_mit_bestehenden_pruefungen` (AC-14).
- `test_betreiber_meldung_genau_einmal_je_tag` (AC-15, 16; Betreiber-Konto mit Recht `betreiber` in der Fixture, Meldungen über `rueckmeldungen.meldungen_des_kontos`).
- `test_merker_atomar_und_je_tag` (AC-17).
- `test_kein_alarmweg_nur_mein_konto` (AC-18).
- `test_ohne_betreiber_und_bei_meldefehler_antwortet_die_seite` (AC-19, 20).
- `test_texte_fuer_tagesgrenze_in_allen_sprachen` (AC-21 ergänzend zu `test_texte.py`).
- `test_loeschen_laesst_keine_adresse_zurueck` (AC-24).

Vor dem Vorspulen laufen zusätzlich `engine/tests/test_texte.py` und `engine/tests/test_anmeldung.py` sowie die Tests der einbindenden Instanzen mit dem Branch (neuer Fehlertext und neuer Umgebungswert; Anleitung im Reisen-Repo der Instanz). Die Zahlen und die Reihenfolge der Tests werden in der RED-Phase festgelegt.

## Was darf sich nicht ändern

- Unter der Grenze verhält sich die Warteliste genau wie bisher (Satz, Mail, Begrenzung je Adresse und IP, Höchstzahl unbestätigter Einträge).
- Die Seite verrät nie den Stand einer Adresse.
- Freigaben durch den Betreiber, Anmeldecodes und Einladungen sind von der Grenze nicht betroffen.
- Der Resend-Teil-Check im Monitor bleibt unverändert.

## Dependencies

- #382 (Warteliste), #530 (Meldung an den Betreiber über Mein Konto), #381 (Löschen räumt `versand`), #384 (Checkliste Alpha-Start).

## Definition of Done

- Alle Acceptance Criteria durch Tests abgedeckt und grün, ganze Testsuite ohne echte Reisen grün, Tests der einbindenden Instanz mit dem Branch grün.
- Texte in allen `texte_*.py`, Ausnahmelisten in `test_texte.py` nicht länger.
- Doku in `docs/konten.md`, `docs/betrieb.md`, `betrieb/einstellungen.beispiel` nachgezogen; auf der Instanz ausgeliefert.

## Offene Punkte

- keine

## Known Limitations

- Die Grenze zählt Bestätigungsmails der Warteliste, nicht das Gesamtkontingent: Mails anderer Dienste (Anmeldecodes, Einladungen, Meldungen an den Betreiber) und der andere Verbrauch bei Resend sind nicht eingerechnet. Das Gesamtkontingent beobachtet der Resend-Teil-Check im Monitor. Der Betreiber stellt die Grenze nach Bedarf ein.
- Scheitert der Mailversand nach dem Eintragen, bleibt die Zeile gezählt (bewusst zu vorsichtig).
- Ein Ansturm kann die Grenze in wenigen Minuten erreichen; danach sind alle Besucher bis Mitternacht UTC (1:00 Uhr MEZ, 2:00 Uhr MESZ) abgewiesen. Eine Warteschlange oder Vormerkung gibt es nicht (Produktentscheidung: einfach und kostenfrei).
- Ändert der Betreiber die Grenze mitten am Tag, gilt der neue Wert sofort für die schon gezählten Mails dieses Tages; der Merker der Meldung bleibt für den Tag bestehen (bei Erhöhung kommt am selben Tag keine zweite Meldung, wenn die neue Grenze erreicht wird).
- Die Tagesgrenze gilt für die ganze Instanz, nicht je Sprache oder Herkunft; ein einzelner Absender kann sie also für alle ausschöpfen. Je Adresse und je IP begrenzen die bestehenden Regeln die Häufigkeit, aber viele verschiedene Adressen von verschiedenen IP-Adressen können die Grenze erreichen. Ein Captcha ist nicht Teil dieser Spec.

## Changelog

- 2026-11-12: Spec erstellt (Entwurf, Version 1.0) nach Analyse `docs/context/feat-534-warteliste-tagesgrenze.md`.
