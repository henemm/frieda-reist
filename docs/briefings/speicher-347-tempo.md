---
spec_file: docs/specs/betrieb/speicher-347-tempo.md
spec_sha256: d0625b517ae427bf77e74bb31a15850a14bc6e1bdc81135ef8e18e7ec99bf38a
spec_frozen_sha256: 8894a8fd10c4f16b6d2d52939747871da94151b94681930d607899047bbbd1dd
---

# PO-Briefing: speicher-347-tempo

- **Spec:** docs/specs/betrieb/speicher-347-tempo.md
- **Issue:** #347
- **Erstellt:** 2026-11-06

## Was gebaut wird

Das Speichern von Änderungen an großen Reisen im Reisespeicher wird schneller, ohne dass sich Verhalten oder Datenformat ändern.

## Definition of Done

Der wiederholte Messlauf an der 110-MB-Testreise zeigt weniger als 5,4 Sekunden je Vorgang, die Zahlen stehen vorher/nachher im Issue, alle Tests sind grün.

## Wie geprüft wird

Tests belegen, dass das Ergebnis unverändert bleibt; die Geschwindigkeit selbst weist nur der manuelle Messlauf nach, nicht ein Test.

## Kritische Anmerkungen

- Git-Tempo (1,6 s) wird voraussichtlich verfehlt; erwartet sind etwa 2,5 s. Die Spec benennt das offen.
- Die abgewiesenen Anfragen (429) haben kein Abnahmekriterium; geprüft wird nur das Mittel je Vorgang.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
