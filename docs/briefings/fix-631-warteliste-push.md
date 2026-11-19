---
spec_file: docs/specs/betrieb/warteliste-push-631.md
spec_sha256: f2cc84124770aeb94bc3e445369f0d3c6b4ae34ed101679f2c4fa6e481a4c6c3
spec_frozen_sha256: f47a46269fecdf81f94577016efc5ec0d417982dc1143572c75c75a1387707b6
---

# PO-Briefing: fix-631-warteliste-push

- **Spec:** docs/specs/betrieb/warteliste-push-631.md
- **Issue:** #631
- **Erstellt:** 2026-11-19

## Was gebaut wird

Betreiber bekommen bestätigte Wartelisten-Einträge und Bitten „Reisen anlegen“ als Handy-Nachricht und, je nach Einstellung, in der Tagesmail.

## Definition of Done

Ein Probe-Eintrag auf der Warteliste und eine Probe-Bitte lösen je eine Nachricht am Betreiber-Handy aus; Altes wird nicht nachgeschickt.

## Wie geprüft wird

Automatische Tests decken Handy-Nachricht, Ruhezeit, Tagesmail und Einmaligkeit ab; der echte Handy-Empfang auf dem Server wird nur manuell abgenommen.

## Kritische Anmerkungen

- Zusatz ohne Auftrag: Auch „neue Reise“ und „Löschung“ lösen Nachrichten aus, vermutlich auch bei normalen Nutzern statt nur Betreibern.

## Freigabe-Frage

Sollen neben Warteliste und „Reisen anlegen“ auch Meldungen zu neuer Reise und Löschung als Handy-Nachricht kommen?

## Ampel

Ampel: rot
