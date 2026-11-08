---
entity_id: rechtliches-383
type: feature
created: 2026-11-07
updated: 2026-11-07
status: draft
workflow: feature-383-datenschutz-impressum
version: "1.0"
tags: [datenschutz, impressum, alpha, m5a]
---

# Alpha: Datenschutz, Impressum und Alpha-Hinweis (#383, Meilenstein M5a)

## Approval

- [ ] Approved

## Purpose

Wer die Warteliste oder den Dienst nutzt, soll vorher die Datenschutzerklärung, das Impressum mit dem Betreiber und einen deutlichen Alpha-Hinweis (Fehler möglich, Daten können verloren gehen, Funktionen ändern sich) finden. Ohne diese Seiten darf der Dienst nicht öffentlich werden.

Die Software liefert nur die Form: drei öffentliche Seiten mit Texten je Sprache. Die Angaben zum Betreiber (Name, Anschrift, Kontakt) stammen aus den Einstellungen der Instanz, nie aus dem öffentlichen Repo. Die Texte sind ein Entwurf; die rechtliche Prüfung macht allein der Product Owner, nicht Claude.

## Ziel und Abgrenzung

- **Im Scope:**
  - Seiten `GET /datenschutz`, `GET /impressum`, `GET /alpha` im Anmeldedienst (`engine/anmeldung.py`), ohne Anmeldung lesbar, kein neues Modul.
  - Betreiberangaben aus den Einstellungen der Instanz: `FR_BETREIBER_NAME`, `FR_BETREIBER_ANSCHRIFT`, `FR_BETREIBER_KONTAKT`.
  - Leerfall: Das Impressum meldet „nicht eingerichtet“, statt leere Felder zu zeigen.
  - Zeile mit drei Links (neuer Baustein „Rechtszeile“) in der Fußzeile der Reiseseiten und als Link-Zeile (Baustein `fuss`) auf Warteliste, Anmeldeseiten, Einladungsseite und Mein Konto.
  - Texte in `engine/texte_de.py` und `engine/texte_en.py`.
  - nginx-Orte in `betrieb/vorlagen/nginx-konnektor-orte.inc`.
  - Einstellungen in `betrieb/einstellungen.beispiel` (erfundene Werte), Doku in `docs/betrieb.md`, `docs/design.md` und auf der Bausteinseite.
- **Nicht im Scope:**
  - Das Löschen und Exportieren von Warteliste-Einträgen und Reisedaten (#381); die Erklärung formuliert es als „folgt“, nicht als Zusage.
  - Die rechtliche Prüfung und endgültige Formulierung (Product Owner).
  - Ein Telefonfeld, Cookie-Banner (der Dienst setzt nur das Sitzungs-Cookie der Anmeldung), Schließen der freien Anmeldung.
  - Eine Prüfung der Betreiberangaben in `neu.py pruefen`.
- **Kern (ADR-0001):** Die Seiten betreffen Betrieb und Konten, nicht die Reise-Ontologie. Keine neue Grundform, kein neuer Typ, keine KI, nichts Reisespezifisches. Betreiberangaben gehören der Instanz.
- **Instanzen:** Namen, Anschrift und Kontakt nie in Engine, Katalog, Vorlage oder Tests, nur über `instanz.wert`; die echten Werte liegen in `betrieb/einstellungen.env` des privaten Reisen-Repos.

## Source

- `engine/anmeldung.py`: Pfade in `ist_unsere` und `bearbeiten`, Seitenfunktionen mit `seite`/`karte`/`fuss`, Link-Zeile auf Warteliste, `/anmelden` (Adress- und Code-Seite), Einladungsseite, Mein Konto; Einbindung von `engine/instanz.py` (`wert`).
- `engine/texte_de.py`, `engine/texte_en.py`: Texte der drei Seiten, Linktexte, Hinweis „nicht eingerichtet“; `konto.datenschutz` verweist künftig auf die Erklärung, `warteliste.alpha` bleibt und verlinkt auf `/alpha`.
- `engine/vorlage.html`: `<footer id="fuss">`, `fussZeigen()`, Stile, Kopfkommentar.
- `betrieb/vorlagen/nginx-konnektor-orte.inc`, `betrieb/einstellungen.beispiel`.
- `docs/betrieb.md` (Tabelle „Datenschutz je Instanz“ als Quelle des Inhalts, Einstellungen, nginx-Hinweis), `docs/design.md`, Bausteinseite.

## Verhalten

### Seiten
1. `GET /datenschutz`, `GET /impressum`, `GET /alpha` antworten 200 ohne Anmeldung, in der Sprache des Kontos, sonst der des Browsers (`Accept-Language`), wie die übrigen Anmeldeseiten. Sie tragen `noindex` wie alle Seiten des Dienstes.
2. Andere Methoden (POST usw.) auf diesen Pfaden werden nicht verarbeitet: Der Dienst lehnt sie ab (kein 200, kein Seiteneffekt), Pfade außer den drei exakten (auch mit Anhang wie `/impressum/x`) gehören nicht dem Dienst.
3. Jede der drei Seiten trägt die Link-Zeile zu den beiden anderen und einen Weg zurück (Warteliste bzw. Anmeldung).

### Datenschutz
4. Der Text folgt der Tabelle „Datenschutz je Instanz“ in `docs/betrieb.md`: welche Daten (Adresse, Name, Sprache, Geräte, Reisedaten, Belege), wer sie sieht, wie lange sie bleiben, Weitergabe (Mail über einen Mail-Dienst, Karten, Anmeldung über die Claude-App), Sicherungen, Rechte.
5. Er sagt nur zu, was es gibt: Das Konto selbst löschen (Mein Konto) gilt als vorhanden. Löschen und Export des Warteliste-Eintrags und Export der Reisedaten stehen als „folgt“ da, ohne Termin. Hinweis auf die Namen im Verlauf der Reise, die bewusst stehen bleiben. Wer fragen oder Rechte ausüben will, wendet sich an den Kontakt aus dem Impressum.
6. Der Text nennt keine Betreiberangaben (nur den Verweis aufs Impressum).

### Impressum
7. Das Impressum zeigt Name, Anschrift und Kontakt aus `FR_BETREIBER_NAME`, `FR_BETREIBER_ANSCHRIFT`, `FR_BETREIBER_KONTAKT`. Alle drei sind Pflicht, ein Telefon ist nicht vorgesehen. Mehrzeilige Anschrift wird sicher dargestellt (Werte werden maskiert, Zeilenumbrüche erhalten).
8. Fehlt eine der drei Angaben (leer zählt als nicht gesetzt), antwortet die Seite trotzdem 200 und zeigt statt der Felder den Hinweis „Angaben zum Betreiber sind in dieser Instanz nicht eingerichtet“. Es erscheinen nie leere oder halb gefüllte Felder.
9. Die Warteliste und die Anmeldung werden dadurch nicht blockiert.

### Alpha-Hinweis
10. `/alpha` nennt deutlich: frühe Testphase, Fehler möglich, Daten können verloren gehen, Funktionen ändern sich, Voraussetzung eines bezahlten Claude-Kontos für den Konnektor. Der Satz `warteliste.alpha` bleibt auf der Warteliste und verlinkt auf `/alpha`.

### Verlinkung
11. Fußzeile der Reiseseiten: Eine Zeile mit drei Links (Datenschutz, Impressum, Alpha; Pfade ab der Wurzel, wie `/anmelden`) ist immer sichtbar. Ihre Texte kommen über `data-t` aus dem Katalog und folgen der gewählten Sprache. `fussZeigen()` blendet die Fußzeile damit nicht mehr aus, wenn Stand, Benachrichtigungen und Sprachen leer sind.
12. Auf Warteliste (auch Bestätigungs- und Hinweisseiten), `/anmelden` (Adress- und Code-Seite), Einladungsseite und Mein Konto steht dieselbe Link-Zeile als leise Zeile unter der Karte (Baustein `fuss`).
13. `konto.datenschutz` (Kurzsatz auf den Anmeldeseiten) verweist auf die Erklärung.

### Oberfläche (ADR-0002, ADR-0003)
14. Die Rechtszeile ist ein neuer Baustein „Rechtszeile“: Eintrag im Kopfkommentar der Vorlage, in den Stilen seiner Ebene, auf der Bausteinseite und in `docs/design.md`. Er zeigt keine Grundform der Reise, deshalb kein Eintrag in `ONTOLOGIE`. Heimat nach ADR-0003: Die Erklärung hat ihre Heimat nur auf `/datenschutz`, das Impressum nur auf `/impressum`, der Alpha-Hinweis nur auf `/alpha`; überall sonst steht nur der Link.

## Was darf sich nicht ändern

- Anmeldung, Codes, Einladungen, Warteliste, Konto und Kalender verhalten sich wie bisher (bestehende Tests grün); die Links ändern nur die Seiten, nicht die Abläufe.
- Reisedaten und Reisen bleiben unverändert; die Reiseseiten ändern sich nur in der Fußzeile.
- Betreiberangaben stehen nie im Katalog, nie im öffentlichen Repo und nie in Tests außer als erfundene Beispielwerte.
- `engine/tests/test_texte.py`: Ausnahmelisten dürfen nur kürzer werden.
- Die Modulliste in `betrieb/deploy.sh` bleibt unverändert (kein neues Modul).

## Test Plan

Neue Datei `engine/tests/test_rechtliches.py`, nur erfundene Werte (Name „Beispiel-Betreiber“, Anschrift „Musterweg 1, 12345 Beispielstadt“, Kontakt „kontakt@example.org“) über Umgebung bzw. Einstellungsdatei der Instanz:

- [ ] `GET /datenschutz`, `/impressum`, `/alpha` antworten 200 ohne Anmeldung, in Deutsch und Englisch (Sprache über `Accept-Language`, Kontosprache vor Browser).
- [ ] Impressum zeigt die drei erfundenen Angaben aus den Einstellungen; HTML in den Werten wird maskiert.
- [ ] Leerfall: Fehlt je eine der drei Angaben (nacheinander), antwortet das Impressum 200 mit dem Hinweis „nicht eingerichtet“ und zeigt keine der gesetzten Angaben als Feld; leerer String zählt als fehlend.
- [ ] Datenschutz und Alpha-Seite enthalten keine Betreiberangaben.
- [ ] Nur GET: `POST` auf alle drei Pfade wird abgelehnt (keine 200-Seite); `/impressum/x` und `/impressum.html` gehören nicht dem Dienst (`ist_unsere`).
- [ ] Die Seiten tragen die Link-Zeile mit den beiden anderen Seiten; Link-Zeile auch auf `/warteliste`, `/anmelden` (Adress- und Code-Seite), Einladungsseite und `/konto`.
- [ ] `warteliste.alpha` verlinkt auf `/alpha`; `konto.datenschutz` verweist auf die Erklärung.
- [ ] Vorlage: `#fuss` enthält die Rechtszeile mit den drei Pfaden und `data-t`-Schlüsseln, die im Katalog beider Sprachen stehen; `fussZeigen()` blendet die Fußzeile nicht aus, wenn die übrigen Teile leer sind (Textprüfung der Vorlage oder Browser-Probe, wie sie die bestehenden Vorlagentests vorsehen).
- [ ] Texte: Alle neuen Schlüssel in `texte_de.py` und `texte_en.py`, Pseudo-Sprache der Tests läuft durch, `test_texte.py` grün, Ausnahmelisten nicht länger.
- [ ] Datenschutztext sagt „folgt“ zu Löschen/Export der Warteliste und Export der Reisedaten und enthält kein Versprechen dazu (Schlüsselprüfung auf Formulierung).
- [ ] nginx: Die Vorlage enthält exakte Orte `= /datenschutz`, `= /impressum`, `= /alpha` mit Zone `__ZONE_KONTO__`; bestehender Vorlagentest (`test_nginx.py`, Orte nutzen die Zonen) bleibt grün, bei Bedarf Ergänzung.
- [ ] `betrieb/einstellungen.beispiel` nennt die drei Werte mit erfundenen Beispielwerten (kein echter Name/Adresse; bestehender Test auf Vorlagen ohne echte Adressen bleibt grün).
- [ ] Bestehende Tests (`test_anmeldung.py`, `test_warteliste.py`, Vorlagentests) unverändert grün.

## Architektur-Entscheidung (ADR)

**ADR-Nr.:** keine neue (ADR-0002 Atomic Design, ADR-0003 Heimat, ADR-0006 Mehrsprachigkeit, ADR-0005 Konten)

Keine neue Entscheidung nötig. Die Seiten nutzen den vorhandenen Anmeldedienst und seine Bausteine; der neue Baustein folgt den Regeln von ADR-0002. Die Prüfstelle von ADR-0001 ist bestanden: keine Grundform, keine KI, nichts Reisespezifisches.

## Dependencies

| Abhängigkeit | Art | Wirkung |
|---|---|---|
| `engine/anmeldung.py` (`seite`, `karte`, `fuss`, `ist_unsere`) | Code | wird erweitert |
| `engine/instanz.py` (`wert`) | Code | liest die Betreiberangaben, unverändert |
| `engine/vorlage.html` (`#fuss`, `fussZeigen()`) | Code | gilt für alle Reisen und Instanzen |
| `docs/betrieb.md`, Tabelle „Datenschutz je Instanz“ | Quelle | Inhalt der Erklärung |
| #382 (Warteliste) | Vorarbeit | verlinkt die neuen Seiten |
| #381 | Folgearbeit | Löschen/Export; Texte anpassen, wenn es vorher fertig wird |
| #384 | Folgearbeit | Probelauf |
| Sitzung `packliste` | Parallelarbeit | ändert `betrieb/deploy.sh` und `docs/betrieb.md`; vor dem Vorspulen neu aufsetzen |

## Auslieferung auf der Instanz

- Reisedaten ändern ihr Format nicht, deshalb ist keine Umstellung in `neu.py nachziehen` nötig; die Handschritt-Regel (CLAUDE.md, #250) ist damit erfüllt.
- Nach dem Vorspulen auf `main`: `nginx.py anwenden` (sonst 404 am Rand für die neuen Orte) und Neubau der Reiseseiten durch das Veröffentlichen (Fußzeile; geschieht automatisch über `veroeffentlichen.sh`/`deploy.sh`).
- Die drei Werte `FR_BETREIBER_*` trägt der Product Owner in `betrieb/einstellungen.env` des privaten Reisen-Repos ein (Daten der Person, nicht der Software). Bis dahin zeigt das Impressum den Hinweis „nicht eingerichtet“.
- Vor dem Vorspulen laufen die Tests der einbindenden Instanzen mit dem Branch (CLAUDE.md).

## Scope

**Affected Files:** `engine/anmeldung.py`, `engine/texte_de.py`, `engine/texte_en.py`, `engine/vorlage.html`, `betrieb/vorlagen/nginx-konnektor-orte.inc`, `betrieb/einstellungen.beispiel`, `docs/betrieb.md`, `docs/design.md`, Bausteinseite, `engine/tests/test_rechtliches.py` (neu), bei Bedarf `engine/tests/test_nginx.py`.

**Estimated Changes:** etwa +350 / -5 Zeilen (Hauptteil Texte DE/EN etwa 150, Code etwa 80, Tests etwa 100, Doku etwa 30). Risiko mittel: Die Fußzeile betrifft alle Reiseseiten, und der Text darf nichts zusagen, was es nicht gibt.

## Acceptance Criteria

- **AC-1:** Given die drei Pfade `/datenschutz`, `/impressum`, `/alpha` / When sie ohne Anmeldung per GET geöffnet werden / Then antworten sie 200 in der Sprache der Anfrage (Deutsch und Englisch), und POST auf sie wird abgelehnt.
- **AC-2:** Given gesetzte Betreiberangaben in den Einstellungen / When das Impressum geöffnet wird / Then zeigt es genau Name, Anschrift und Kontakt aus `FR_BETREIBER_NAME`, `FR_BETREIBER_ANSCHRIFT`, `FR_BETREIBER_KONTAKT` (maskiert), und sie stehen weder im Katalog noch in einer anderen Seite.
- **AC-3:** Given eine fehlende oder leere Betreiberangabe / When das Impressum geöffnet wird / Then antwortet es 200 mit dem Hinweis „nicht eingerichtet“ ohne leere Felder, und die Warteliste bleibt nutzbar.
- **AC-4:** Given Warteliste, Anmeldeseiten, Einladungsseite und Mein Konto / When sie angezeigt werden / Then enthalten sie die Link-Zeile zu Datenschutz, Impressum und Alpha-Hinweis.
- **AC-5:** Given eine gebaute Reiseseite in jeder Sprache / When sie geöffnet wird / Then zeigt die Fußzeile immer die Rechtszeile mit den drei Links, Texte aus dem Katalog.
- **AC-6:** Given die Datenschutzerklärung / When Löschen und Export genannt werden / Then ist nur das Konto-Löschen zugesagt, alles andere steht als „folgt“, und der Inhalt entspricht der Tabelle „Datenschutz je Instanz“.
- **AC-7:** Given alle sichtbaren Texte / When `test_texte.py` läuft / Then sind alle Schlüssel in `de` und `en` vorhanden, und die Ausnahmelisten sind nicht länger.
- **AC-8:** Given die nginx-Vorlage / When der Vorlagentest läuft / Then enthält sie die drei Orte mit der Konto-Zone.
- **AC-9:** Given Anmeldung, Warteliste, Konto, Kalender und Reisedaten / When die Seiten eingebaut sind / Then verhalten sie sich unverändert (bestehende Tests grün).

## Definition of Done

- [ ] Alle Punkte des Test Plans sind als Tests umgesetzt und grün; `engine/tests` insgesamt grün.
- [ ] Alle neun Acceptance Criteria sind durch Tests belegt.
- [ ] Texte in de und en vollständig, `test_texte.py` grün, Ausnahmelisten nicht länger.
- [ ] Baustein „Rechtszeile“ im Kopfkommentar der Vorlage, in den Stilen, auf der Bausteinseite und in `docs/design.md`.
- [ ] `docs/betrieb.md` ergänzt (die drei Einstellungen, nginx-Hinweis `nginx.py anwenden`), `betrieb/einstellungen.beispiel` mit erfundenen Werten.
- [ ] Die Tests der einbindenden Instanzen laufen mit dem Branch.
- [ ] Ausgeliefert auf `main`, auf der Instanz `nginx.py anwenden` ausgeführt, Reiseseiten neu gebaut, die drei Seiten mit `curl` geprüft.
- [ ] **Rechtliche Prüfung der Texte durch den Product Owner bestätigt.** Bis dahin bleibt Issue #383 offen; es wird mit Nachweis kommentiert und erst nach der Bestätigung geschlossen.

## Offene Punkte

- Rechtliche Prüfung der Texte (Datenschutz, Impressum, Alpha-Hinweis) durch den Product Owner; die Texte sind Entwurf.
- Werden Löschen und Export (#381) vor #383 fertig, sind die „folgt“-Sätze der Erklärung anzupassen.
- Die echten Betreiberangaben trägt der Product Owner in der Instanz ein; ohne sie bleibt das Impressum im Leerfall.
- `betrieb/deploy.sh` und `docs/betrieb.md` ändert auch die Sitzung `packliste`: nach deren Vorspulen neu aufsetzen.

## Changelog

- 2026-11-08: Abweichung bei der Auslieferung: Der Konnektor läuft mit `ProtectHome=yes` ohne `FR_WURZEL` und lädt nur `<FR_DIENST>/konten.env`. Die drei `FR_BETREIBER_*` stehen deshalb dort, nicht in `betrieb/einstellungen.env` (Abschnitt „Auslieferung“ ist insoweit überholt; Doku und Beispiel sind angepasst).
- 2026-11-07: Erstfassung (Entwurf) für #383 mit den Entscheidungen aus der Analyse (`docs/context/feature-383-datenschutz-impressum.md`).
