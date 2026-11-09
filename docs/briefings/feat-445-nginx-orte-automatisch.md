---
spec_file: docs/specs/betrieb/nginx-orte-automatisch-445.md
spec_sha256: 571a8a20a4c0f96620366e6859841094961a890a6883b168ed037ce2fa3fde8f
spec_frozen_sha256: 925c650d2a637df371271edb46a10da9405a9a4d615d50f43400a95d2e53e1cb
---

# PO-Briefing: feat-445-nginx-orte-automatisch

- **Spec:** docs/specs/betrieb/nginx-orte-automatisch-445.md
- **Issue:** #445
- **Erstellt:** 2026-11-09

## Was gebaut wird

Neue Orte der Webserver-Vorlage richten sich beim Software-Wechsel selbst ein, ohne Handschritt.

## Definition of Done

Der Abgleich meldet keine Abweichung mehr, die Prüfbild-Adresse der Infoseite antwortet, und neue Orte kommen ohne Handarbeit an.

## Wie geprüft wird

Automatische Tests belegen, dass sichere Änderungen ankommen, unsichere abgelehnt werden und der Rückweg klappt; der Server-Schritt wird live kontrolliert.

## Kritische Anmerkungen

- Nur die Orte-Datei geht automatisch; die zwei anderen Webserver-Dateien bleiben bewusst Handarbeit.
- Nachträgliche Verschärfungen (Zertifikats-Pfad, Größengrenze, Meldung trotz Neuladefehler) haben Tests, aber keine eigenen Kriterien.
- Auf diesem Server erlaubt sudo ohnehin alles; das Hilfsprogramm schützt vor Fehlern, nicht vor Angriffen.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
