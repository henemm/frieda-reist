---
spec_file: docs/specs/betrieb/dienstrechte-552.md
spec_sha256: 92c7e179eefbccd07c11bd8a9a4f08cc613951ad00749adbad7eb978f282e8a5
spec_frozen_sha256: 4533ba9f1e6d872c4447519a0177d6d4289762954148318994907382367bf8ad
---

# PO-Briefing: sicherheit-552-dienstrechte

- **Spec:** docs/specs/betrieb/dienstrechte-552.md
- **Issue:** #552
- **Erstellt:** 2026-11-13

## Was gebaut wird

Aus dem Netz erreichbare Dienste bekommen engere Rechte, und Rollen werden gegen den aktuellen Stand der Reise geprüft.

## Definition of Done

Die Instanz ist umgestellt, Veröffentlichen, Schreiben, neue Reise und Kartenaktualisierung laufen, und Netzdienste erreichen weder Root-Rechte noch Docker.

## Wie geprüft wird

Automatische Tests belegen jedes Kriterium; nur die Umstellung der echten Server-Instanz wird manuell nachgewiesen, nicht in der automatischen Prüfung.

## Kritische Anmerkungen

- Auf diesem Server ist der Dienstbenutzer zugleich Admin; die engeren Rechte schützen dort nur eingeschränkt (dokumentiert).
- Restrisiko Bauordner ist korrekt als Ihre Entscheidung vom 13.11. festgehalten, #555 geschlossen.
- Fällt der Schreibweg aus, sind Einladen, Erledigen und Einplanen vorübergehend gesperrt (gewollt).

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
