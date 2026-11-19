---
spec_file: docs/specs/betrieb/anmeldecode-mail-532.md
spec_sha256: b3abb452beaec6b5b7d91b23772e030ba957f77764b8daa6fce867997e534583
spec_frozen_sha256: 90a4a5c0ca53c6ea4d6377ab62cfb6010ea4744ad37b1968ad7108b45899f069
---

# PO-Briefing: anmeldecode-mail-532

- **Spec:** docs/specs/betrieb/anmeldecode-mail-532.md
- **Issue:** #532
- **Erstellt:** 2026-11-19

## Was gebaut wird

Die Anmeldecode-Mail kommt von „Frieda“, zeigt den Code vorn im Betreff und groß lesbar, mit Hinweis und Fuß.

## Definition of Done

Eine Test-Anmeldung liefert eine Mail mit Absender „Frieda“, Code im Betreff, lesbar in Hell- und Dunkelmodus, im Posteingang statt Spam.

## Wie geprüft wird

Automatische Tests prüfen Aufbau, Code, Fuß und Sicherheit; Aussehen, Dunkelmodus und Posteingang prüft nur die manuelle Abnahme auf der Instanz.

## Kritische Anmerkungen

- Der freigegebene Entwurf ist verloren; Claude zeigt den Wortlaut vor dem Ausliefern neu, Ihre Bestätigung steht noch aus.
- Alle anderen Mails (Warteliste, Einladung usw.) zeigen künftig ebenfalls „Frieda“ als Absendernamen, obwohl nur die Code-Mail verlangt war.
- Ein ungültig eingestellter Absender verhindert jetzt jeden Mailversand mit Fehlermeldung.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
