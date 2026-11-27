---
spec_file: docs/specs/fast/fix-669-bruecke-netzfehler.md
spec_sha256: fd6caebd746491cd756faa65430b9a64e316c204b94cf167a472b180eb7e7cb4
spec_frozen_sha256: 4569cc87e35c62b525b04447321f267cdea904cf3216c8747645f35e597daa51
---

# PO-Briefing: fix-669-bruecke-netzfehler

- **Spec:** docs/specs/fast/fix-669-bruecke-netzfehler.md
- **Issue:** #669
- **Erstellt:** 2026-11-27

## Was gebaut wird

Die Testzugang-Brücke bleibt bei Netz- oder Serverfehlern am Leben und meldet einen Fehler, statt sich zu beenden.

## Definition of Done

Ist die Instanz nicht erreichbar, antwortet die Brücke jeder Anfrage mit einem Fehler, läuft weiter und leitet nach Rückkehr wieder normal weiter.

## Wie geprüft wird

Automatische Tests decken Start ohne Verbindung, Ausfall mitten im Lauf, Serverfehler, gescheiterte Erneuerung und unveränderte Abbrüche ab; kein Test mit echter Instanz.

## Kritische Anmerkungen

- Zweiter Fund (Sperre nur für einen Konnektor) bewusst nicht geändert: aktuell gibt es keinen weiteren Konnektor, Erweiterung wäre eigenes Issue.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
