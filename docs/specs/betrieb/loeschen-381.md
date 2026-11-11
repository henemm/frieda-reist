---
entity_id: loeschen-381
type: feature
created: 2026-11-11
updated: 2026-11-11
status: draft
workflow: alpha-381-loeschen
version: "1.0"
tags: [datenschutz, loeschen, konten, reisespeicher, alpha, m5a]
---

# Alpha: Löschen von Reise und Konto (#381, Meilenstein M5a)

## Approval

- [ ] Approved

## Purpose

Wer an der Alpha teilnimmt, soll seine Daten wieder loswerden können: Eine Organisator:in löscht eine ganze Reise, jede Person löscht ihr Konto. Eine Reise ist nach einer Schonfrist von 14 Tagen wirklich weg (alle Versionen, Verlauf, Fotos, GPX, Belege, Rückmeldungen, Seiten), ein gelöschtes Konto verschwindet aus allen Tabellen, und der eigene Name steht danach nirgends mehr, auch nicht im Verlauf fremder Reisen („gelöschte Person“). Ohne das wäre die öffentliche Alpha datenschutzrechtlich nicht vertretbar, und der Datenschutztext (#383) könnte keine Löschung zusagen.

Entscheidungen des Product Owners (10. und 11.11.2026, Issue #381 und Kontext `docs/context/alpha-381-loeschen.md`) sind in dieser Spec verbindlich: Link „Reise löschen …“ nur für Organisator:innen, zwei Bestätigungen, 14 Tage Schonfrist mit Knopf „Reise zurückholen“, sofortige Benachrichtigung aller anderen Mitglieder, Konto-Löschseite „Das bleibt, ohne deinen Namen“, Reisen nur mit der Person gehen mit Schonfrist mit, die letzte Organisator:in einer Reise mit anderen Mitgliedern muss die Rolle erst übergeben oder die Reise löschen. Export der Daten ist #498 und nicht Teil dieser Spec.

## Ziel und Abgrenzung

- **Im Scope:**
  - Tabelle `reise_loeschung` in der Kontendatenbank (Reise, wer, wann, Frist) und die Funktionen Vormerken, Zurückholen, Abfrage `reise_vorgemerkt(reise) -> bool`, Liste fälliger Löschungen.
  - Mein Konto: Link „Reise löschen …“ (nur Organisator:innen, nur Speicherreisen), zwei Bestätigungen, Block der vorgemerkten Reisen oben in „Meine Reisen“ mit Datum und Knopf „Reise zurückholen“.
  - Vorgemerkte Reise ist überall wie nicht vorhanden: Speicherliste, Konnektor, Schreibweg, Veröffentlichen, Wächter.
  - E-Mail und Meldung an alle anderen Mitglieder sofort beim Vormerken und eine zweite beim Zurückholen.
  - Endgültiges Entfernen im täglichen Lauf des Wächters, danach Speicher verdichten und neuen Schnappschuss ziehen; Löschprotokoll gegen Rückspielen alter Sicherungen.
  - Konto löschen vollständig über alle Tabellen der Kontendatenbank (auch Einladungen, Wartelisteneintrag, Anmeldeschlüssel), Sperre für die letzte Organisator:in, Mitgehen von Reisen nur mit dieser Person.
  - Pseudonymisieren: „gelöschte Person“ im Verlauf der Reisedaten, in den Inhalten aller Versionen (bekannte Herkunftsmuster) und in Dateien der Ablage.
  - Ausnahme vom Nur-Anhängen (ADR-0001, ADR-0009) genau für zwei Funktionen, fest im Code.
  - Texte in allen Sprachen (Seiten, Mails, Meldungen, Datenschutztext), Doku `docs/betrieb.md`, Vorgabe der Frist in `engine/instanz.py`.
  - Schnittstelle `konten.reise_vorgemerkt(reise) -> bool` für den Export (#498).
- **Nicht im Scope:**
  - Der Export der Daten („Meine Daten“, `konto.export.*`, #498). Der Export liefert für vorgemerkte und entfernte Reisen 404 und nutzt dafür nur `reise_vorgemerkt`.
  - Das Löschen von Reisen auf dem alten Weg (Git im privaten Reisen-Repo): bleibt Sache des Betreibers, der Link erscheint dort nicht.
  - Das Löschen einzelner Dinge in einer Reise (Frieda löscht nie, `docs/specs/konnektor/loeschwunsch.md`; sie verweist für ganze Reisen auf Mein Konto).
  - Die Aufbewahrung der Server-Sicherungen außerhalb der Software (Infra-Anteil: eigenes Issue in `henemm/henemm-infra`, Ziel höchstens 30 Tage).
  - Das Entfernen von Namen in frei geschriebenen Texten jenseits der bekannten Herkunftsmuster (siehe Verhalten, Abschnitt Pseudonymisieren).
- **Kern (ADR-0001):** Löschen betrifft Konten, Betrieb und die Ablage der Reisedaten, nicht die Reise-Ontologie. Keine neue Grundform, kein Typ, keine Art, kein Merkmal, keine KI. Der Verlauf (Frage 7) bleibt erhalten, nur der Name der Person darin wird ersetzt. ADR-0001 und ADR-0009 erhalten im ersten Teilschritt einen Absatz zur Ausnahme vom Nur-Anhängen.
- **Instanzen:** Die Frist (14 Tage) ist eine Vorgabe in `engine/instanz.py` (Wert aus `betrieb/einstellungen.env`, Vorgabe 14). Absender, Basisadresse und Pfade kommen wie bisher aus den Einstellungen. Nichts Instanzspezifisches in Engine, Betrieb oder Katalog; keine echten Reisen, Namen oder Pfade in Spec, Tests oder Beispielen.

## Source

- `engine/konten.py`: Schema (neue Tabelle `reise_loeschung`, Löschprotokoll), `reise_vormerken`, `reise_zurueckholen`, `reise_vorgemerkt`, `faellige_loeschungen`, `loeschen(kid)` (heute Z. 481, räumt Einladungen, `angelegte_reisen`, `schreibvorgaenge`, `oauth_*` und Warteliste nicht ab; Docstring „Verlauf behält Namen“ wird ersetzt), Mitgliedschaften (Z. 729 ff.), `mail_senden` (Z. 239).
- `engine/anmeldung.py`: `konto_seite`, `personen_block`, `loeschen_seite`, POST-Aktion `loeschen`, neue Seiten und Aktionen für Reise löschen und zurückholen, Datenschutzabschnitte.
- `engine/reisespeicher.py`: `reisen()` (Z. 447), `_db_ausnahme`, `reise_entfernen`, `namen_ersetzen`, Verdichten (`wal_checkpoint`, `VACUUM`), `sichern()` (Z. 900), `pruefen()` (Z. 850).
- `engine/konnektor.py`, `engine/schreiben.py`: vorgemerkte Reise wie nicht vorhanden.
- `engine/waechter.py`, `betrieb/waechter.sh`: täglicher Lauf (fällige Löschungen, Schonfrist-Reisen übersprungen, Löschprotokoll anwenden); `alle_reisen()` (Z. 413).
- `betrieb/veroeffentlichen.sh`: vorgemerkte Reise nicht bauen, Webordner sofort entfernen.
- `engine/instanz.py`: Vorgabe Frist.
- `engine/texte_de.py`, `engine/texte_en.py` und alle weiteren `engine/texte_<kürzel>.py`.
- `docs/adr/0001-kern.md`, `docs/adr/0009-reisespeicher.md`, `docs/betrieb.md`.
- `engine/tests/test_loeschen_reise.py`, `engine/tests/test_loeschen_konto.py` (neu).

## Verhalten

### Reise löschen: Vormerken und Zurückholen (Teilschritt A)
1. Unter den aufgeklappten Personen einer Reise auf Mein Konto steht der Link „Reise löschen …“. Er erscheint nur für Organisator:innen der Reise und nur, wenn die Reise im Reisespeicher liegt. Für Reisen auf dem alten Weg erscheint er nicht; stattdessen steht ein Satz, dass das Löschen erst nach der Umstellung möglich ist.
2. Bestätigung 1: Seite mit Erklärung (was gelöscht wird, 14 Tage Schonfrist, alle anderen Mitglieder werden benachrichtigt) und einem Haken „Ich weiß, dass …“. Ohne Haken geschieht nichts.
3. Bestätigung 2: Der exakte Reisename muss eingetippt werden (Abgleich nach Normalisierung von Leerraum und Groß-/Kleinschreibung). Erst dann wird die Reise vorgemerkt: Zeile in `reise_loeschung` mit Reise, auslösendem Konto (leer, wenn das Konto inzwischen gelöscht ist, Punkt 22), Zeitpunkt und Fristende (Zeitpunkt plus Frist aus `instanz.py`, in UTC gespeichert). Beide Schritte sind POST mit Herkunftsprüfung; ein GET ändert nie etwas.
4. Eine Reise, die schon vorgemerkt ist, lässt sich nicht erneut vormerken; die Fristanzeige bleibt die des ersten Vormerkens.
5. Oben in „Meine Reisen“ steht für jede vorgemerkte Reise ein Block mit Reisename, Datum des endgültigen Entfernens (mit Zeitzone, in der Zone der Person) und dem Knopf „Reise zurückholen“. Der Block ist für alle Mitglieder sichtbar, den Knopf sehen nur Organisator:innen der Reise.
6. „Reise zurückholen“ (POST, nur Organisator:innen, nur innerhalb der Frist) löscht die Zeile in `reise_loeschung`; die Reise ist danach in allen Teilen wieder vorhanden. Seiten werden beim nächsten Veröffentlichen neu gebaut.
7. Beim Vormerken geht sofort eine E-Mail (in der Sprache des Empfängers) und eine Meldung auf Mein Konto an alle anderen Mitglieder der Reise, nicht an die auslösende Person; beim Zurückholen geht dieselbe Benachrichtigung mit zweitem Text. Mail und Meldung nennen Reise, auslösende Person, Fristende mit Zone und bei der ersten den Weg zurück (nur für Organisator:innen). Bei Mailfehlern bleibt das Vormerken gültig; die Meldung auf Mein Konto entsteht immer.

### Vorgemerkt heißt unsichtbar (Teilschritt A2)
8. `reisespeicher.reisen()` liefert keine vorgemerkte Reise. Ebenso zählt sie nicht bei `my_trips` und bei keinem anderen Reise-Werkzeug des Konnektors: Jedes Werkzeug mit `reise=<vorgemerkt>` antwortet wie bei einer unbekannten Reise.
9. Der Schreibweg (`engine/schreiben.py`) lehnt jede Änderung an einer vorgemerkten Reise ab, ebenso Rückmeldungen, Belege und Einladungen zu ihr.
10. `betrieb/veroeffentlichen.sh` baut vorgemerkte Reisen nicht und entfernt den Webordner (`<FR_SEITEN>/<reise>`) sofort beim nächsten Lauf, die Seite liefert danach 404. Beim Zurückholen wird sie wieder gebaut.
11. `waechter.alle_reisen()` schließt vorgemerkte Reisen aus: keine Erinnerungen, keine Meldungen aus ihnen.
12. `konten.reise_vorgemerkt(reise) -> bool` ist die einzige Abfrage, die Export (#498) und andere Aufrufer nutzen. Vorgemerkte und schon entfernte Reisen gelten als vorgemerkt: Die Abfrage prüft `reise_loeschung` und das Löschprotokoll.

### Endgültiges Entfernen (Teilschritt A3)
13. Der tägliche Lauf des Wächters (`betrieb/waechter.sh`) holt `faellige_loeschungen` (Fristende erreicht) und entfernt je Reise: alle Versionen und Verlaufseinträge im Reisespeicher, ausgelagerte Medien der Reise (Fotos, GPX) in der inhaltsadressierten Ablage des Speichers nach Punkt 14, Belege und Rückmeldungen und Aufgaben in der Ablage der Instanz (`<FR_ABLAGE>/<reise>/`), den Webordner, den Bauordner (`<FR_DIENST>/bau/reisen/<reise>`) und die Stempel (`<FR_DIENST>/reise-stand/<reise>.*`).
14. Ausgelagerte Dateien der Ablage des Speichers sind inhaltsadressiert und können mehreren Reisen gehören. Sie werden erst gelöscht, nachdem die Zeilen im Commit entfernt sind, und nur, wenn keine Version irgendeiner anderen Reise mehr auf die Prüfsumme verweist. Prüfen und Entfernen laufen unter derselben Schreibsperre wie `ablage_ablegen`.
15. Vor dem Entfernen läuft `sichern()` (dieser Schnappschuss enthält die Reise noch und wird in Punkt 16 durch den frischen am selben Ort überschrieben); nach dem Entfernen läuft `pruefen()` über alle verbleibenden Reisen. Ist es nicht grün, bricht der Lauf mit Fehler ab, meldet über den Weg des Wächters für Störungen und löscht keine weitere Reise.
16. Danach folgen `PRAGMA wal_checkpoint(TRUNCATE)`, `VACUUM` (mit Timeout und Wiederholung bei Sperre) und ein neuer Schnappschuss `sichern()`, damit gelöschte Inhalte weder in freien Seiten noch im WAL noch im frischen Schnappschuss stehen. Die Reise wird danach aus `reise_loeschung` entfernt und im Löschprotokoll vermerkt.
17. Löschprotokoll: eine Tabelle in der Kontendatenbank mit nur Reisekennung und Datum der Löschung. Der tägliche Lauf entfernt jede Reise des Protokolls erneut, die nach dem Rückspielen einer alten Sicherung wieder im Speicher, in der Ablage oder im Webordner steht. Das Protokoll enthält keine Namen und keine Inhalte.

### Ausnahme vom Nur-Anhängen
18. Der Reisespeicher bleibt für jeden normalen Zugriff nur anhängend (Trigger gegen UPDATE und DELETE, Authorizer). Zwei Funktionen dürfen davon abweichen: `reise_entfernen(reise)` und `namen_ersetzen(...)`. Beide nutzen ausschließlich die private Verbindung `_db_ausnahme()` ohne Authorizer und arbeiten in genau einer `BEGIN IMMEDIATE`-Transaktion: Trigger entfernen, Zeilen löschen beziehungsweise umschreiben (bei Umschreiben Prüfsummen neu rechnen), Trigger aus `SCHEMA` neu anlegen, `COMMIT`. Das Schema wird dabei nicht migriert, und andere Verbindungen sehen die Trigger nie fehlen (DDL ist in SQLite transaktional). Bei jedem Fehler wird zurückgerollt und die Trigger bleiben bestehen.
19. Ein Quelltext-Test stellt sicher, dass genau diese beiden Funktionen `_db_ausnahme` nutzen und der Authorizer `VERBOTEN` unverändert bleibt. Fällt die Transaktionsvariante bei der Umsetzung durch (Trigger fehlen für andere Verbindungen, `pruefen` rot), wählt der Tech Lead die Alternative „Trigger mit `WHEN fr_ausnahme()` je Verbindung, fail-closed“ samt Umstellung in `neu.py nachziehen` und hält das im Issue fest.

### Konto löschen (Teilschritte B1 und B2)
20. Die Seite „Konto löschen“ zeigt „Das bleibt, ohne deinen Namen“ (Beiträge in Reisen anderer, Verlauf mit „gelöschte Person“) und „Das geht“ (Konto, Adresse, Anmeldungen, Geräte, Einladungen, Wartelisteneintrag, eigene Reisen) und listet die Reisen, die mit der Person gehen.
21. Sperre: Ist die Person die einzige Organisator:in einer Reise, in der es weitere Mitglieder gibt, lehnt `loeschen(kid)` ab („erst klären“): Die Rolle ist zu übergeben oder die Reise zu löschen. Die Seite nennt die betroffenen Reisen. Die Prüfung gilt für jeden Aufruf, nicht nur für die Seite.
22. Reisen, in denen die Person das einzige Mitglied ist, gehen mit: Sie werden wie bei „Reise löschen“ vorgemerkt (Schonfrist, Zurückholen nicht mehr möglich, weil kein Konto mehr da ist; das Entfernen erfolgt nach der Frist im täglichen Lauf, die Sichtbarkeit endet sofort). Reisen mit anderen Mitgliedern, in denen die Person nur Mitglied oder nicht letzte Organisator:in ist, bleiben unberührt. In `reise_loeschung` wird das auslösende Konto bei diesen Zeilen und bei allen früheren Zeilen, die das gelöschte Konto ausgelöst hat, geleert; Reise, Zeitpunkt und Fristende bleiben, damit der tägliche Lauf die Reise entfernt.
23. `loeschen(kid)` räumt in einer Transaktion alle Tabellen der Kontendatenbank ab, die das Konto, seine Adresse oder seinen Namen enthalten: Mitgliedschaften, Anfragen, Kalender-Abos, Push-Abos, Push-Einstellungen, Push-Warteschlange, gelesene Meldungen, Anmeldecodes und Sitzungen, Einladungen an oder von ihr (Adresse, Name), `angelegte_reisen`, `schreibvorgaenge`, `oauth_clients`, `oauth_codes`, `oauth_tokens` des Kontos, das Feld „auslösendes Konto“ in `reise_loeschung` (geleert nach Punkt 22, die Zeile selbst bleibt), den Wartelisteneintrag derselben Adresse, die Zählzeilen in `versand` mit ihrer Adresse (`adresse:…`, `warteliste:…`) und das Konto selbst. `push_schluessel` und `push_stand` enthalten nur Schlüssel des Servers, kein Konto, und bleiben unberührt. Ein Test vergleicht gegen die Tabellenliste des Schemas, damit eine künftige Tabelle nicht vergessen wird.
24. Der Personenschlüssel der Mitgliedschaft wird vor deren Löschung gelesen und ist die Zuordnung für das Pseudonymisieren.

### Pseudonymisieren
25. In jeder Reise, in der die Person Mitglied war, wird `vorgaenge.wer` (Verlauf) auf „gelöschte Person“ gesetzt, zugeordnet über den Personenschlüssel, nicht über eine Namenssuche. Der Text steht im Katalog je Sprache.
26. In den Inhalten aller Versionen der Reisedateien werden bekannte Herkunftsmuster ersetzt (die von `engine/schreiben.py` erzeugten Herkunftstexte, Entscheidungen mit Datum und Person, Fußzeile), und zwar der Name der Person als ganzes Wort in diesen Mustern. Danach werden die Prüfsummen der geänderten Versionen neu berechnet, `pruefen()` bleibt grün, und für die betroffene Reise wird ein Neubau erzwungen (Stempel `.gebaut` hängt an der Stand-Nummer, nicht am Inhalt).
27. In Dateien der Ablage der Instanz (Rückmeldungen, Aufgaben, Belege-Metadaten unter `<FR_ABLAGE>/<reise>/`) wird der Name in den bekannten Feldern ersetzt; Belegdateien selbst bleiben unverändert, soweit sie nicht der Person allein gehören.
28. Namen in frei geschriebenen Texten (Notizen, Wissen, Fragen, Antworten, Beschreibungen) werden nur dort ersetzt, wo ein bekanntes Muster greift; darüber hinaus nur näherungsweise. Der Datenschutztext sagt das ehrlich („Namen, die jemand in einen eigenen Text geschrieben hat, können wir nicht in jedem Fall finden; Organisator:innen können sie anpassen“).
29. Das Pseudonymisieren schreibt auch alte Versionen lebender Reisen anderer um. Es läuft in der zweiten Ausnahme-Funktion `namen_ersetzen`, nach `sichern()` und mit `pruefen()` als Abbruchkriterium; bei einem Fehler bleibt der alte Stand (Rollback).

### Sicherungen
30. Sicherungen enthalten Gelöschtes bis zu ihrer Rotation. Ziel: höchstens 30 Tage Aufbewahrung der Server-Sicherungen; die Software kann das nicht erzwingen. `docs/betrieb.md` und der Datenschutztext nennen die Frist; die Prüfung der Aufbewahrung ist ein eigenes Issue in `henemm/henemm-infra`. Nach dem Rückspielen einer Sicherung stellt das Löschprotokoll (Punkt 17) den gelöschten Stand wieder her.

### Prüfpunkt Going Live
31. Vor dem Going Live der Alpha müssen #350 (Umschaltung der Instanz auf den Reisespeicher) für alle Reisen der Alpha-Instanz erledigt sein und `reise_anlegen` neue Reisen direkt im Speicher anlegen; sonst ist „Reise löschen“ für sie nicht möglich. Das ist kein Teil dieser Umsetzung, sondern ein Prüfpunkt, der im Issue #381 vor dem Schließen abgehakt wird (bei Bedarf eigenes Issue).

## Was darf sich nicht ändern

- Alle anderen Reisen, ihre Versionen, Prüfsummen und Ablage-Dateien bleiben unberührt; Dateien mit fremden Verweisen werden nie gelöscht.
- Der Reisespeicher bleibt außerhalb der beiden Ausnahme-Funktionen nur anhängend; `pruefen()` ist nach jedem Löschen und Umschreiben grün.
- Frieda löscht weiterhin nichts; die Anleitung `konnektor.anleitung.loeschwunsch` verweist für ganze Reisen auf Mein Konto, ohne dass der Konnektor ein Löschwerkzeug bekommt.
- Der Datenschutztext (#383) sagt nur zu, was die Software tut (Löschen ja, Export nur, wenn #498 ausgeliefert ist).
- Bestehende Konten-, Anmelde-, Mitgliedschafts-, Warteliste-, Trennungs- und Speichertests bleiben grün.
- Beide Beispielreisen (`beispiel/reisen/beispielreise`, `beispiel/reisen/stadtwochenende`) funktionieren in jedem Schritt; nichts nimmt eine Wanderung als Regelfall an.

## Test Plan

Dateien `engine/tests/test_loeschen_reise.py` und `engine/tests/test_loeschen_konto.py`, nur erfundene Namen und Adressen, Mails über `FR_MAIL_DATEI`, eigene Datenbanken je Test, beide Beispielreisen parametrisiert (`beispielreise` mit Ida und Karl, `stadtwochenende` mit Tom und Lea), zusätzlich zwei Reisen mit gemeinsamer Ablagedatei.

Teilschritte C1 und A (ADR-Ergänzung, Vormerken):
- [ ] GIVEN eine Organisator:in einer Speicherreise WHEN sie Mein Konto öffnet THEN erscheint „Reise löschen …“; für Mitwirkende, Gäste und Reisen auf dem alten Weg erscheint er nicht.
- [ ] GIVEN Bestätigung 1 ohne Haken oder Bestätigung 2 mit falschem Reisenamen WHEN abgeschickt THEN wird nichts vorgemerkt; mit beiden richtigen wird eine Zeile mit Fristende (Vormerkzeitpunkt plus 14 Tage) angelegt.
- [ ] GIVEN eine vorgemerkte Reise WHEN „Reise zurückholen“ (Organisator:in, innerhalb der Frist) THEN ist sie wieder vorhanden; Nicht-Organisator:innen und eine abgelaufene Frist werden abgelehnt.
- [ ] GIVEN eine Reise mit drei Mitgliedern WHEN sie vorgemerkt und zurückgeholt wird THEN bekommen genau die zwei anderen je eine Mail und eine Meldung beim Vormerken und je eine zweite beim Zurückholen, in der Sprache des Empfängers; die auslösende Person bekommt keine.
- [ ] GIVEN eine vorgemerkte Reise WHEN „Meine Reisen“ geöffnet wird THEN steht der Block oben mit Datum samt Zeitzone, der Knopf nur für Organisator:innen.
- [ ] Quelltext-/Strukturtest: ADR-0001 und ADR-0009 enthalten den Absatz zur Ausnahme.

Teilschritte A2a und A2b (unsichtbar):
- [ ] GIVEN eine vorgemerkte Reise WHEN `reisen()`, `my_trips` und jedes Reise-Werkzeug des Konnektors (Test über die Werkzeugliste) aufgerufen werden THEN verhält sich die Reise wie unbekannt.
- [ ] GIVEN eine vorgemerkte Reise WHEN der Schreibweg, eine Rückmeldung oder eine Einladung versucht wird THEN wird abgelehnt.
- [ ] GIVEN `veroeffentlichen.sh` im Probelauf WHEN eine Reise vorgemerkt ist THEN wird nicht gebaut und der Webordner entfernt; nach dem Zurückholen wird wieder gebaut.
- [ ] GIVEN `waechter.alle_reisen()` WHEN eine Reise vorgemerkt ist THEN taucht sie nicht auf und erzeugt keine Erinnerung.
- [ ] `reise_vorgemerkt` ist wahr für vorgemerkte und für entfernte Reisen, falsch für alle anderen.

Teilschritt A3 (Entfernen):
- [ ] GIVEN eine Reise mit Fristende in der Vergangenheit WHEN der tägliche Lauf läuft THEN sind Versionen, Verlauf, Ablage-Ordner, Belege, Rückmeldungen, Webordner, Bauordner und Stempel weg; eine zweite, unbeteiligte Reise ist byteidentisch unverändert.
- [ ] GIVEN zwei Reisen mit derselben Ablagedatei WHEN die eine entfernt wird THEN bleibt die Datei; wird danach die zweite entfernt, ist sie weg.
- [ ] GIVEN eine Reise vor Fristende WHEN der Lauf läuft THEN bleibt alles bestehen.
- [ ] GIVEN eine entfernte Reise WHEN der Speicher mit `strings` oder Byte-Suche nach einem eindeutigen Testinhalt durchsucht wird (Datenbank, WAL, frischer Schnappschuss) THEN ist der Inhalt nirgends mehr zu finden.
- [ ] GIVEN eine zurückgespielte alte Sicherung mit einer entfernten Reise WHEN der Lauf läuft THEN wird sie anhand des Löschprotokolls erneut entfernt; das Protokoll enthält nur Kennung und Datum.
- [ ] GIVEN ein künstlicher Fehler beim Entfernen WHEN er auftritt THEN bleiben Trigger und Reisen unversehrt (Rollback), `pruefen()` ist grün.
- [ ] Quelltext-Test: genau `reise_entfernen` und `namen_ersetzen` nutzen `_db_ausnahme` (bzw. den Ausweichweg nach Punkt 19); der Authorizer und die Trigger im `SCHEMA` sind unverändert; nach beiden Funktionen existieren alle Trigger wieder.

Teilschritt B1 (Konto):
- [ ] GIVEN ein Konto mit Daten in allen Tabellen (Einladung, Warteliste, `oauth_*`, `angelegte_reisen`, `schreibvorgaenge`, Push) WHEN `loeschen` THEN ist in keiner Tabelle der Kontendatenbank mehr eine Spur (Test gegen die Tabellenliste des Schemas).
- [ ] GIVEN die einzige Organisator:in einer Reise mit weiteren Mitgliedern WHEN sie ihr Konto löscht THEN wird abgelehnt mit Nennung der Reise; nach Übergabe der Rolle oder Löschen der Reise klappt es.
- [ ] GIVEN eine Reise nur mit der Person WHEN sie ihr Konto löscht THEN ist die Reise sofort unsichtbar und nach Fristende entfernt.
- [ ] GIVEN eine Reise, in der die Person nur Mitglied ist WHEN sie ihr Konto löscht THEN bleibt die Reise bestehen.

Teilschritt B2 (Pseudonymisieren):
- [ ] GIVEN Beiträge der Person in Reisen anderer, über beide Beispielreisen WHEN das Konto gelöscht wird THEN steht in `vorgaenge.wer` und in den bekannten Herkunftsmustern aller Versionen „gelöschte Person“; ein gleichnamiges anderes Mitglied wird nicht verändert (Zuordnung über den Personenschlüssel).
- [ ] GIVEN umgeschriebene Versionen WHEN `pruefen()` THEN ist es grün, die Prüfsummen stimmen, und der Neubau wurde erzwungen.
- [ ] GIVEN der Name in einem Freitext außerhalb der Muster WHEN das Konto gelöscht wird THEN ist das Verhalten wie in Punkt 28 beschrieben dokumentiert (Test fixiert den Ist-Stand).
- [ ] GIVEN Ablage-Dateien (Rückmeldung, Aufgabe) mit dem Namen WHEN pseudonymisiert wird THEN ist der Name dort ersetzt.

Teilschritt C2 (Texte, Betrieb):
- [ ] `test_texte.py` bleibt grün (alle Schlüssel in allen Sprachen, Ausnahmelisten nicht länger), ebenso die Tests zum Datenschutztext (`test_rechtliches.py`, Abschnitte Verlauf, Belege, Sicherungen, Konto löschen) und die Betriebsdoku-Prüfungen.
- [ ] Bestehende Konten-, Anmelde-, Trennungs-, Speicher- und Wächtertests unverändert grün; `engine/.venv/bin/python -m pytest -q engine/tests -n 3` grün.

## Stufen

Reihenfolge zwingend, ein Workflow. Je Teilschritt höchstens fünf Code-Dateien (Engine-Module außer dem Textkatalog, Skripte unter `betrieb/`); die Dateien des Textkatalogs aller Sprachen und die Tests gehen im selben Teilschritt mit, damit jeder Stand für sich grün ist.
1. C1: ADR-0001 und ADR-0009 ergänzen (Ausnahme vom Nur-Anhängen).
2. A: Vormerken, Zurückholen und Benachrichtigen (`konten.py`, `anmeldung.py`, `instanz.py`; Texte, Tests).
3. A2a: Unsichtbar in Engine (`reisespeicher.reisen`, `konnektor.py`, `schreiben.py`).
4. A2b: Unsichtbar im Betrieb (`veroeffentlichen.sh` entfernt den Webordner, `waechter.py` und `waechter.sh` schließen aus).
5. A3: Endgültiges Entfernen im täglichen Lauf (`_db_ausnahme`, `reise_entfernen`, Verdichten, Löschprotokoll; `reisespeicher.py`, `konten.py`, `waechter.py`, `waechter.sh`).
6. B1: Konto löschen vollständig, Sperre, Mitgehen von Reisen (`konten.py`, `anmeldung.py`).
7. B2: Pseudonymisieren (`namen_ersetzen`, Ablage-Dateien, Neubau; `reisespeicher.py`, `konten.py`, `waechter.py`).
8. C2: Datenschutztext, `docs/betrieb.md`, `docs/konten.md`, Issue in `henemm-infra` für die Sicherungsfrist, Prüfpunkt Going Live.

## Architektur-Entscheidung (ADR)

**ADR-Nr.:** ADR-0001 und ADR-0009 (bestehend, werden im Teilschritt C1 ergänzt)

Rationale: Das Löschen weicht an zwei klar begrenzten Stellen vom Nur-Anhängen ab (Entfernen einer ganzen Reise, Ersetzen eines Personennamens). Das ist eine bewusste, dokumentierte Ausnahme, die dort steht, wo die Regel steht. Eine eigene neue ADR ist nicht nötig, weil keine neue Grundform, kein neuer Typ und keine neue Architektur entsteht; ADR-0005 (Konten) bleibt unverändert gültig.

## Dependencies

| Abhängigkeit | Art | Wirkung |
|---|---|---|
| `engine/reisespeicher.py` (Trigger, Authorizer, Ablage, `sichern`, `pruefen`) | Code | wird um die Ausnahme erweitert |
| `engine/konten.py`, `engine/anmeldung.py` | Code | Tabelle, Funktionen, Seiten |
| `engine/konnektor.py`, `engine/schreiben.py`, `engine/waechter.py` | Code | Unsichtbarkeit, Lauf |
| `betrieb/veroeffentlichen.sh`, `betrieb/waechter.sh` | Betrieb | Webordner, täglicher Lauf |
| `betrieb/sichern.sh` | nur Information, unverändert | sichert weiter den Schnappschuss, den `reisespeicher.sichern()` nach dem Entfernen neu schreibt |
| SQLite, Resend, systemd-Timer des Wächters | Fremd | Datenbanken, Mails, Auslöser |
| #350 (Umschaltung auf den Reisespeicher) | Voraussetzung | Löschen nur für Speicherreisen; Prüfpunkt Going Live |
| #498 (Export, Sitzung `frieda-reist-8c`) | Folgearbeit | nutzt `reise_vorgemerkt`; Abgrenzung der Texte auf Mein Konto abgesprochen |
| #383 (Datenschutz) | Gleichzeitig | Datenschutztext muss dem Verhalten entsprechen |
| #380, #382, #407 | Vorarbeit | Trennung der Konten, Warteliste (wird beim Konto-Löschen mit aufgeräumt), Meldungen auf Mein Konto |
| Issue in `henemm/henemm-infra` | Fremd, neu | Aufbewahrung der Server-Sicherungen höchstens 30 Tage |

## Scope

**Affected Files:**

| File | Change Type | Description |
|------|-------------|-------------|
| `docs/adr/0001-kern.md`, `docs/adr/0009-reisespeicher.md` | MODIFY | Ausnahme vom Nur-Anhängen |
| `engine/konten.py` | MODIFY | `reise_loeschung`, Vormerken, Zurückholen, `reise_vorgemerkt`, fällige Löschungen, Löschprotokoll, `loeschen` vollständig mit Sperre |
| `engine/anmeldung.py` | MODIFY | Link, zwei Bestätigungen, Schonfrist-Block, Konto-Löschseite |
| `engine/reisespeicher.py` | MODIFY | `reisen()` ohne Vorgemerkte, `_db_ausnahme`, `reise_entfernen`, `namen_ersetzen`, Verdichten |
| `engine/konnektor.py`, `engine/schreiben.py` | MODIFY | vorgemerkte Reise wie nicht vorhanden |
| `engine/waechter.py`, `betrieb/waechter.sh` | MODIFY | fällige Löschungen, Ausschluss, Löschprotokoll |
| `betrieb/veroeffentlichen.sh` | MODIFY | nicht bauen, Webordner entfernen |
| `engine/instanz.py` | MODIFY | Vorgabe Frist |
| `engine/texte_de.py`, `engine/texte_en.py` (und jede künftige `engine/texte_<kürzel>.py`) | MODIFY | Seiten, Mails, Meldungen, Datenschutzabschnitte |
| `docs/betrieb.md` | MODIFY | Datenschutz-Tabelle, Belege nicht mehr „nie gelöscht“, Sicherungsfrist, Wächterlauf |
| `docs/konten.md` | MODIFY | Konto löschen vollständig, Sperre letzte Organisator:in, Reise löschen mit Schonfrist |
| `engine/tests/test_loeschen_reise.py`, `engine/tests/test_loeschen_konto.py` | CREATE | Tests je Teilschritt |

**Estimated Changes:** 17 Dateien (davon die zwei Sprachdateien des Textkatalogs), in acht Teilschritten (je höchstens fünf Code-Dateien), etwa +1.700/−50 Zeilen, davon rund 40 % Tests. Risiko hoch (echtes Entfernen in einem Nur-Anhängen-Speicher).

## Acceptance Criteria

- **AC-1:** Given eine Organisator:in einer Speicherreise / When sie Mein Konto öffnet / Then steht unter den Personen der Link „Reise löschen …“; für Nicht-Organisator:innen und für Reisen auf dem alten Weg fehlt er.
- **AC-2:** Given Bestätigung 1 und 2 / When der Haken fehlt oder der Reisename nicht exakt eingetippt ist / Then wird nichts vorgemerkt; sonst wird die Reise mit Fristende nach 14 Tagen (Vorgabe in `instanz.py`) vorgemerkt.
- **AC-3:** Given eine vorgemerkte Reise / When ein Mitglied „Meine Reisen“ öffnet / Then steht der Block oben mit Datum samt Zeitzone, und nur Organisator:innen sehen „Reise zurückholen“; der Knopf macht die Reise vollständig wieder sichtbar.
- **AC-4:** Given eine Reise mit mehreren Mitgliedern / When sie vorgemerkt wird / Then erhalten alle anderen Mitglieder sofort Mail und Meldung, beim Zurückholen eine zweite, die auslösende Person keine.
- **AC-5:** Given eine vorgemerkte Reise / When `reisen()`, `my_trips` oder irgendein Reise-Werkzeug des Konnektors, der Schreibweg oder der Wächter sie ansprechen / Then verhält sie sich wie nicht vorhanden (keine Schreibung, keine Erinnerung).
- **AC-6:** Given eine vorgemerkte Reise / When `veroeffentlichen.sh` läuft / Then wird sie nicht gebaut und ihr Webordner ist entfernt (404); nach dem Zurückholen wird sie wieder gebaut.
- **AC-7:** Given Fristende erreicht / When der tägliche Lauf läuft / Then sind Versionen, Verlauf, Ablage-Dateien ohne fremde Verweise, Belege, Rückmeldungen, Webordner, Bauordner und Stempel der Reise entfernt, und alle anderen Reisen sind unverändert.
- **AC-8:** Given zwei Reisen mit gemeinsamer Ablagedatei / When die eine entfernt wird / Then bleibt die Datei bis auch die andere entfernt ist.
- **AC-9:** Given das Entfernen einer Reise / When der Lauf abgeschlossen ist / Then folgen `wal_checkpoint(TRUNCATE)`, `VACUUM` und ein neuer Schnappschuss, in DB, WAL und Schnappschuss findet eine Byte-Suche den Testinhalt nicht, und `pruefen()` ist grün.
- **AC-10:** Given eine zurückgespielte alte Sicherung / When der tägliche Lauf läuft / Then wird jede Reise des Löschprotokolls erneut entfernt; das Protokoll enthält nur Kennung und Datum.
- **AC-11:** Given der Quelltext / When der Test läuft / Then nutzen genau `reise_entfernen` und `namen_ersetzen` `_db_ausnahme`, jede in einer `BEGIN IMMEDIATE`-Transaktion mit Trigger-Neuanlage aus `SCHEMA` (oder, falls nach Punkt 19 gewählt, über den Ausweichweg mit `WHEN fr_ausnahme()`); bei einem Fehler bleibt alles beim Alten.
- **AC-12:** Given ein Konto mit Daten in allen Tabellen / When `loeschen` läuft / Then bleibt in keiner Tabelle der Kontendatenbank eine Spur (Einladungen, Wartelisteneintrag, `angelegte_reisen`, `schreibvorgaenge`, `oauth_*`, Zählzeilen in `versand` eingeschlossen; in `reise_loeschung` ist das auslösende Konto geleert).
- **AC-13:** Given die einzige Organisator:in einer Reise mit weiteren Mitgliedern / When sie ihr Konto löschen will / Then wird abgelehnt und die Reise genannt, bis Rolle übergeben oder Reise gelöscht ist.
- **AC-14:** Given eine Reise nur mit der Person / When sie ihr Konto löscht / Then geht die Reise mit Schonfrist mit (sofort unsichtbar, nach Fristende entfernt); Reisen mit anderen Mitgliedern bleiben bestehen.
- **AC-15:** Given Beiträge der Person in Reisen anderer / When das Konto gelöscht wird / Then steht im Verlauf und in den bekannten Herkunftsmustern aller Versionen „gelöschte Person“, zugeordnet über den Personenschlüssel (ein gleichnamiges anderes Mitglied bleibt), die Prüfsummen stimmen, `pruefen()` ist grün und ein Neubau ist erzwungen.
- **AC-16:** Given Namen in Freitexten außerhalb der Muster / When das Konto gelöscht wird / Then ist die Grenze im Datenschutztext ehrlich benannt und im Test als Ist-Stand festgehalten.
- **AC-17:** Given `konten.reise_vorgemerkt(reise)` / When der Export (#498) oder ein anderer Aufrufer fragt / Then ist das Ergebnis wahr für vorgemerkte und entfernte Reisen, sonst falsch.
- **AC-18:** Given alle sichtbaren Texte (Seiten, Mails, Meldungen, Datenschutztext) / When `test_texte.py` und die Tests zum Datenschutztext laufen / Then sind alle Schlüssel in allen Sprachen vorhanden, Ausnahmelisten nicht länger, und der Text sagt nur zu, was es gibt (Sicherungen höchstens 30 Tage als Ziel, Export nur nach #498).
- **AC-19:** Given beide Beispielreisen / When die Tests laufen / Then bestehen sie für Wanderung und Städtewochenende gleichermaßen, und alle bestehenden Tests bleiben grün.

## Definition of Done

- [ ] Alle Punkte des Test Plans sind als Tests umgesetzt und grün; `engine/tests` insgesamt grün (CI-Pflichtprüfungen `tests (leer)`, `tests (instanz)`, `gitleaks`).
- [ ] Alle 19 Acceptance Criteria sind durch Tests belegt.
- [ ] ADR-0001 und ADR-0009 enthalten die Ausnahme; die Prüfstelle (zehn Fragen) ist im PR beantwortet.
- [ ] Texte in allen Sprachen vollständig; Datenschutztext und `docs/betrieb.md` stimmen mit dem Verhalten überein (Belege nicht mehr „nie gelöscht“, Sicherungsfrist).
- [ ] Issue in `henemm/henemm-infra` für die Aufbewahrung der Server-Sicherungen (höchstens 30 Tage) angelegt und im Issue #381 verlinkt.
- [ ] Prüfpunkt Going Live (#350 erledigt, neue Reisen direkt im Speicher) im Issue #381 vermerkt, bei Bedarf als eigenes Issue.
- [ ] Die Tests der einbindenden Instanzen laufen mit dem Branch (CLAUDE.md, Regel zu Meldungstexten, Umgebungswerten und Dateiformaten).
- [ ] Der Entwurf der Seiten (Link, beide Bestätigungen, Schonfrist-Block, Konto-Löschseite) entspricht dem vom Product Owner am 11.11.2026 freigegebenen Entwurf.
- [ ] Issue #381 mit Nachweis kommentiert und erst nach der Auslieferung auf `main` und dem Entfernen eines echten Testfalls (Testreise) geschlossen.

## Offene Punkte

- Keine offenen Produktfragen. Technisch festgelegt: Form des Löschprotokolls (nur Reisekennung und Datum, Kontendatenbank), Ausnahme als Transaktionsvariante (Ausweichweg nach Punkt 19: Trigger mit `WHEN fr_ausnahme()`), Namen in Freitexten nur über bekannte Herkunftsmuster.
- Der Export (#498) entsteht parallel in einer anderen Sitzung; die Abgrenzung der Texte auf Mein Konto (Abschnitt „Meine Daten“ und `konto.export.*` gehören #498) ist abgesprochen.

## Changelog

- 2026-11-11: Erstfassung (Entwurf) für #381 mit den Entscheidungen des Product Owners vom 10. und 11.11.2026.
- 2026-11-11 (TDD RED): Schnittstelle in den Tests festgelegt (Kopf von `engine/tests/test_loeschen_reise.py` und `test_loeschen_konto.py`). Die Funktionen zum Vormerken heißen `loeschung_vormerken`, `loeschung_zurueckholen`, `loeschungen`, `loeschung_abschliessen`, `loeschprotokoll`, weil `konten.reise_vormerken` schon die Reisegrenze (#380) zählt; dazu `instanz.loeschfrist_tage()` (FR_LOESCHFRIST_TAGE), `konten.py vorgemerkt` für Skripte, `reisespeicher.verdichten()`, `waechter.loeschungen_ausfuehren()` und `waechter.py loeschen`. Ablage-Dateien werden beim Konto-Löschen sofort pseudonymisiert.
