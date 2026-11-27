---
spec_file: docs/specs/betrieb/konto-loeschen-ablage-neu-694.md
spec_sha256: 239d28e6855efc8e5c5e22da6583b9b3a99a96d611370d4d9365c8084cb57ce9
spec_frozen_sha256: 60781c193c03df31fc72eb2a26f6f5980e8da064d6390772c64ec0a1c53a14ef
---

# PO-Briefing: fix-694-konto-loeschen-ablage-neu

- **Spec:** docs/specs/betrieb/konto-loeschen-ablage-neu-694.md
- **Issue:** #694
- **Erstellt:** 2026-11-27

## Was gebaut wird

Beim Löschen eines Kontos verschwinden Name und Adresse auch aus Anfrage-Meldungen, Aufträgen und ausstehenden neuen Reisen.

## Definition of Done

Nach dem Löschen findet eine Volltextsuche weder Name noch Adresse in der Ablage ohne Reise; fremde Einträge bleiben unverändert.

## Wie geprüft wird

Automatische Tests prüfen jeden Fall einschließlich Fehlerabbruch; nicht geprüft sind Namen in Statuskommentaren, freien Texten und bereits versandten Mails.

## Kritische Anmerkungen

- Namen in Statuskommentaren und bereits versandten Mails an Betreiber:innen bleiben bestehen; die Spec benennt das als Einschränkung.
- Zusätzlich zum Issue: Einladungen an die gelöschte Adresse werden aus fremden Aufträgen entfernt, und eine neue Dateisperre kommt dazu.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
