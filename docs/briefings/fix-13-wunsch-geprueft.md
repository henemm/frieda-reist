---
spec_file: docs/specs/fast/fix-13-wunsch-geprueft.md
spec_sha256: 89059c62b8d303cd59be4af968c70dde4e464dca9765673b89f7b96c75a8edf1
spec_frozen_sha256: de66f18c6132be7237a5fa8c36e98e2619d2595fe240864599d0c86530129fdd
---

# PO-Briefing: fix-13-wunsch-geprueft

- **Spec:** docs/specs/fast/fix-13-wunsch-geprueft.md
- **Issue:** #13
- **Erstellt:** 2026-11-15

## Was gebaut wird

Ein Wunsch, zu dem die KI einen Vorschlag eingetragen hat, steht im Wunsch-Brett und auf der Reiseseite unter „geprüft“.

## Definition of Done

Nach einem KI-Vorschlag zeigen Brett und Reiseseite den Wunsch unter „geprüft“; Bilanz und Kontingent bleiben gleich, Einplanen bleibt Organisator:innen vorbehalten.

## Wie geprüft wird

Automatische Tests prüfen Vorschlag, „passt nicht“, gewählte Option und die Reiseseite im Browser, auch ohne Netz Abgehaktes; ein manueller Durchlauf ergänzt sie.

## Kritische Anmerkungen

- Ursprungsanfrage nur als Auftragstext gelesen, nicht im Wortlaut des Issues; Deckung dadurch nur eingeschränkt geprüft.
- Die Prüfung selbst (Lage, Saison, Öffnungszeiten) bleibt unverändert und wird hier nicht neu getestet.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
