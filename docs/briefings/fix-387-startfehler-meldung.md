---
spec_file: docs/specs/oberflaeche/startfehler-meldung-387.md
spec_sha256: 3a15b7b45370e5bc744fa94ba66a9feab9d120836b6231366178919f8ff730d1
spec_frozen_sha256: 307c79e4627a40ae343b52d984980671f220ce7882fde54704a050bcc9ef49f4
---

# PO-Briefing: fix-387-startfehler-meldung

- **Spec:** docs/specs/oberflaeche/startfehler-meldung-387.md
- **Issue:** #387
- **Erstellt:** 2026-11-10

## Was gebaut wird

Scheitert die Reiseseite beim Öffnen, sieht man eine verständliche Meldung mit Knopf „Neu laden“ statt eines leeren Bildschirms.

## Definition of Done

Eine absichtlich kaputt gemachte Testseite zeigt Meldung und Knopf in der Sprache der Reise, gesunde Seiten beider Beispielreisen zeigen sie nie.

## Wie geprüft wird

Automatische Browsertests an Wanderung und Stadtwochenende; nicht geprüft werden Geräte mit alter Seite im Zwischenspeicher oder abgeschaltetem JavaScript.

## Kritische Anmerkungen

- Die Überwachung, die Seiten im Browser lädt, ist nicht Teil dieser Lieferung, sondern ein getrenntes Issue; #387 bleibt bis dahin offen.
- Der Entwurf zu Aussehen und Wortlaut liegt Ihnen vor dem Bauen als Artefakt zur Zustimmung vor.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
