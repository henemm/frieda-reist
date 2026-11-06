---
entity_id: warteliste-382
type: feature
created: 2026-11-06
updated: 2026-11-06
status: draft
workflow: warteliste-382
version: "1.0"
tags: [konten, warteliste, alpha, m5a]
---

# Alpha: Warteliste mit Freigabe (#382, Meilenstein M5a)

## Approval

- [ ] Approved

## Purpose

Zum Alpha-Start sollen Interessenten sich auf einer öffentlichen Seite mit ihrer E-Mail-Adresse eintragen. Der Betreiber sieht die bestätigten Einträge und gibt einzelne frei. Die Freigabe schickt eine Mail mit dem Weg zur Anmeldung und gibt dem Konto das Recht „Reisen anlegen“. Ohne Warteliste müsste der Betreiber Adressen von Hand sammeln und jedem einzeln schreiben.

Entscheidungen des Product Owners (6.11.2026): Die freie Anmeldung bleibt offen (docs/konten.md). Die Warteliste steuert nur, wer Reisen anlegen darf. Der Betreiber arbeitet mit einem Befehl und mit einem Abschnitt auf der Kontoseite.

## Ziel und Abgrenzung

- **Im Scope:**
  - Tabelle `warteliste` in der Kontendatenbank (Adresse, Sprache, Zeiten, Hash des Bestätigungswortes).
  - Öffentliche Seite `/warteliste` (Eintrag, Hinweis auf die Voraussetzung eines bezahlten Claude-Kontos) und `/warteliste/bestaetigen/<wort>` (Bestätigung).
  - Bestätigung der Adresse per Mail (Double-Opt-In).
  - Schutz vor Massen-Einträgen.
  - Befehle `konten.py warteliste` und `konten.py freigeben <email>`; Abschnitt „Warteliste“ auf `/konto` für Betreiber (Freigeben).
  - Freigabe: Mail an die Adresse (in der Sprache des Eintrags), Recht `reise_anlegen` sofort (Konto da) oder beim ersten Anmelden (Konto kommt später).
  - Meldung an die Betreiber bei einem neuen bestätigten Eintrag, auf demselben Weg wie die Bitte „Reisen anlegen“ (`betreiber_melden`).
  - Texte in `engine/texte_de.py` und `engine/texte_en.py`, nginx-Vorlage, Doku in `docs/betrieb.md` und `docs/konten.md`.
- **Nicht im Scope:**
  - Das Löschen und Exportieren von Einträgen (#381).
  - Datenschutzerklärung und Impressum (#383); die Seite verlinkt sie erst dort.
  - Eine Einladung zu einer Reise: Die Freigabe lädt zur Nutzung des Dienstes ein, nicht zu einer Reise. Reiseeinladungen (`einladen`) bleiben unverändert.
  - Das Schließen der freien Anmeldung.
- **Kern (ADR-0001):** Die Warteliste betrifft Konten und Betrieb, nicht die Reise-Ontologie. Sie führt keine Art, kein Merkmal und keine Grundform ein, und sie liegt in der Kontendatenbank, nicht in einer Reise.
- **Instanzen:** Absender, SMTP und Basisadresse kommen wie bei den Anmeldecodes aus `FR_ABSENDER`, `FR_SMTP_*` und `FR_BASIS`. Nichts Instanzspezifisches in Engine oder Vorlage.

## Source

- `engine/konten.py`: Tabelle und Funktionen `warteliste_eintragen`, `warteliste_bestaetigen`, `warteliste` (Liste), `freigeben`; Befehle; Recht beim ersten Anmelden in `anmelden`.
- `engine/anmeldung.py`: Seiten, Zeilen in `ist_unsere`, Abschnitt auf `/konto`, Meldung an Betreiber.
- `engine/texte_de.py`, `engine/texte_en.py`.
- `betrieb/vorlagen/nginx-konnektor-orte.inc`.
- `docs/betrieb.md`, `docs/konten.md`.

## Verhalten

### Eintrag
1. `GET /warteliste` zeigt Adressfeld, kurzen Text zur Alpha und die Voraussetzung (bezahltes Claude-Konto für den Konnektor, docs/produkt.md).
2. `POST /warteliste` mit Adresse (Herkunft wie bei `/anmelden` geprüft, sonst 403): Die Adresse wird normalisiert (`konten.adresse`), der Eintrag mit zufälligem Bestätigungswort angelegt (nur SHA-256 in der Datenbank), eine Mail mit Link geht an die Adresse.
3. Die Antwort ist immer dieselbe („Wir haben dir eine Mail geschickt“), ob die Adresse neu, schon eingetragen, schon bestätigt, schon freigegeben oder schon ein Konto ist. Bei schon Eingetragenen ohne Bestätigung geht die Mail erneut, sonst geht keine.
4. Ungültige Adresse: verständliche Ablehnung, nichts gespeichert.

### Bestätigung
5. `GET /warteliste/bestaetigen/<wort>` zeigt nur eine Seite mit Knopf (Mailprogramme rufen Links vorab auf); erst `POST` bestätigt. Gilt 7 Tage, einmal. Unbekanntes oder abgelaufenes Wort: Seite „Link gilt nicht mehr“ mit Weg zum neuen Eintrag.
6. Mit der Bestätigung wird der Eintrag für den Betreiber sichtbar und eine Meldung an die Betreiber angelegt.

### Schutz
7. Je Adresse höchstens 3 Mails in 15 Minuten, je IP höchstens 10 Einträge in der Stunde (die vorhandene Begrenzung `_begrenzt`).
8. Insgesamt höchstens 1000 unbestätigte Einträge zugleich; darüber lehnt die Seite ab („Gerade zu viel los, bitte später“). Unbestätigte Einträge werden nach 7 Tagen gelöscht.
9. Fehlt die Mail-Einrichtung, lehnt die Seite verständlich ab und speichert nichts.

### Betreiber
10. `konten.py warteliste` listet bestätigte, noch nicht freigegebene Einträge (älteste zuerst) und nennt die Zahl der unbestätigten.
11. `konten.py freigeben <email>` und der Knopf auf `/konto` (nur mit Recht `betreiber`, sonst Ablehnung) tun dasselbe: Eintrag als freigegeben markieren, Mail „Du bist dabei“ mit Link `<FR_BASIS>/anmelden` und Hinweis auf das Claude-Konto, Recht `reise_anlegen`.
12. Hat die Adresse schon ein Konto, wird das Recht sofort gesetzt. Sonst setzt `anmelden` es beim Anlegen des Kontos. Eine nicht bestätigte Adresse lässt sich nicht freigeben.
13. Zweite Freigabe derselben Adresse ändert nichts und schickt keine zweite Mail.

## Was darf sich nicht ändern

- Anmeldung, Codes, Einladungen zu Reisen und die Bitte „Reisen anlegen“ verhalten sich wie bisher (bestehende Tests grün).
- Antworten verraten nie, ob eine Adresse eingetragen ist oder ein Konto hat.
- Die Datenbank bleibt für den Betreiber allein lesbar; Bestätigungswörter liegen nur als SHA-256 darin.

## Test Plan

Datei `engine/tests/test_warteliste.py`, nur erfundene Adressen, Mails über `FR_MAIL_DATEI`, eigene Kontendatenbank je Test:

- [ ] Eintrag legt Zeile an und schickt Mail mit Link; Antwort gleich für neue, bekannte und bestätigte Adressen.
- [ ] Ungültige Adresse wird abgewiesen, nichts gespeichert.
- [ ] Doppelter Eintrag: kein zweiter Datensatz, Mail nur, solange unbestätigt.
- [ ] Bestätigung: GET ändert nichts, POST bestätigt; zweites Mal und abgelaufenes Wort (8 Tage) scheitern.
- [ ] Meldung an die Betreiber entsteht genau einmal bei der Bestätigung eines Eintrags, nicht beim bloßen Eintragen und nicht bei der Wiederholung.
- [ ] Begrenzung je Adresse und je IP; Obergrenze unbestätigter Einträge; Aufräumen nach 7 Tagen.
- [ ] Freigabe: nur bestätigte Einträge; Mail in der Sprache des Eintrags; Recht sofort bei vorhandenem Konto; Recht beim ersten Anmelden ohne Konto; zweite Freigabe ohne zweite Mail.
- [ ] Seite: `GET`/`POST /warteliste` mit falscher Herkunft 403; Abschnitt auf `/konto` nur für Betreiber; Freigeben ohne Recht abgelehnt.
- [ ] Befehle `warteliste` und `freigeben`.
- [ ] Texte: `test_texte.py` bleibt grün (alle Schlüssel in de und en, Ausnahmelisten nicht länger).
- [ ] nginx-Vorlage enthält die neuen Pfade (bestehender Vorlagentest).
- [ ] Bestehende Konten- und Anmeldetests unverändert grün.

## Stufen

Der Umfang liegt über 5 Dateien, deshalb zwei Stufen in einem Workflow, je ein Commit:
1. Modell: `konten.py`, Texte (Mails), `test_warteliste.py` (ohne Seiten), Befehle.
2. Seiten und Betrieb: `anmeldung.py`, Texte (Seiten), nginx-Vorlage, Doku, Tests der Seiten.

## Architektur-Entscheidung (ADR)

**ADR-Nr.:** ADR-0005 (bestehend, keine neue Entscheidung)

Keine neue Entscheidung nötig. Die Warteliste stützt sich auf ADR-0005 (Konten und Anmeldung, ohne Passwort, Begrenzung, Betreiber-Recht) und besteht die Prüfstelle von ADR-0001: Sie betrifft Konten und Betrieb, keine Grundform der Reise.

## Dependencies

| Abhängigkeit | Art | Wirkung |
|---|---|---|
| `engine/konten.py` (Mail, Begrenzung, `freischalten`, `anmelden`) | Code | wird erweitert |
| `engine/anmeldung.py` (Seiten, `/konto`, `betreiber_melden`) | Code | wird erweitert |
| ADR-0005, `docs/konten.md` | Entscheidung | Rahmen für Konten und Begrenzung |
| #348 (Sitzung `packliste`) | Parallelarbeit | ändert `betrieb/deploy.sh` und `docs/betrieb.md`; nach dessen Vorspulen neu aufsetzen |
| #381 | Folgearbeit | Löschen und Exportieren von Einträgen |
| #383 | Folgearbeit | Datenschutzerklärung und Impressum, Verlinkung von der Seite |
| #380 | Voraussetzung des Meilensteins | Trennung der Tester, unabhängig von diesem Issue |

## Scope

**Affected Files:** `engine/konten.py`, `engine/anmeldung.py`, `engine/texte_de.py`, `engine/texte_en.py`, `betrieb/vorlagen/nginx-konnektor-orte.inc`, `engine/tests/test_warteliste.py`, `docs/konten.md`, `docs/betrieb.md`.

**Estimated Changes:** etwa +450 Zeilen (Modell und Befehle etwa 150, Seiten etwa 120, Texte etwa 80, Tests etwa 250 ohne Zählung der Testdatei, Doku etwa 40). Aufteilung in zwei Stufen, siehe unten.

## Acceptance Criteria

- **AC-1:** Given die öffentliche Seite `/warteliste` / When eine gültige Adresse eingetragen wird / Then geht eine Bestätigungsmail an sie, und eine ungültige Adresse wird abgewiesen, ohne dass etwas gespeichert wird.
- **AC-2:** Given eine beliebige Adresse (neu, schon eingetragen, schon freigegeben oder mit Konto) / When sie sich einträgt / Then ist die Antwort der Seite dieselbe und verrät nichts über den Stand.
- **AC-3:** Given ein unbestätigter Eintrag / When der Link aus der Mail geöffnet wird / Then ändert sich nichts, und erst der Knopfdruck bestätigt; danach erscheint der Eintrag beim Betreiber und eine Meldung geht an die Betreiber.
- **AC-4:** Given Massen-Einträge / When die Grenzen je Adresse, je IP oder für unbestätigte Einträge erreicht sind / Then lehnt die Seite ab, und unbestätigte Einträge verfallen nach 7 Tagen.
- **AC-5:** Given bestätigte Einträge / When der Betreiber sie mit Befehl oder auf `/konto` ansieht und einen freigibt / Then klappt das nur mit Betreiber-Recht, ohne es wird abgelehnt.
- **AC-6:** Given ein freigegebener Eintrag / When die Freigabe erfolgt / Then geht eine Mail in der Sprache des Eintrags an die Adresse, und das Recht „Reisen anlegen“ gilt sofort bei vorhandenem Konto, sonst beim ersten Anmelden.
- **AC-7:** Given die bestehende Anmeldung, Codes, Reise-Einladungen und die Bitte „Reisen anlegen“ / When die Warteliste eingebaut ist / Then verhalten sie sich unverändert.

## Definition of Done

- [ ] Alle Punkte des Test Plans sind als Tests umgesetzt und grün; `engine/tests` insgesamt grün.
- [ ] Alle sieben Acceptance Criteria sind durch Tests belegt.
- [ ] Texte in de und en vollständig, `test_texte.py` grün, Ausnahmelisten nicht länger.
- [ ] Doku in `docs/betrieb.md` (Ablauf, Befehle, Einstellungen) und `docs/konten.md` (Grundsatz, Ablauf) ergänzt.
- [ ] Die nginx-Vorlage enthält die neuen Pfade; die Auslieferung braucht keinen Handschritt.
- [ ] Die Tests der einbindenden Instanzen laufen mit dem Branch (CLAUDE.md, Regel zu Meldungstexten und Umgebungswerten).
- [ ] Issue #382 mit Nachweis kommentiert und erst nach der Auslieferung auf `main` geschlossen.

## Offene Punkte

- Die Texte der Seite (Alpha-Hinweis) schreibt Stufe 2 nüchtern; die endgültigen Texte mit Datenschutz und Impressum folgen in #383.
- Die Modulliste `betrieb/deploy.sh` ändert sich nicht, solange kein neues Modul entsteht. Fügt #348 dort `reisespeicher.py` hinzu, ist nach dem Vorspulen von #348 neu aufzusetzen.

## Changelog

- 2026-11-06: Erstfassung (Entwurf) für #382, Entscheidungen des Product Owners zur offenen Anmeldung und zum Betreiber-Weg eingearbeitet.
