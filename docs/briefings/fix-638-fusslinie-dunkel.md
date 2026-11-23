---
spec_file: docs/specs/fast/fix-638-fusslinie-dunkel.md
spec_sha256: 5f025591ea9be51384c02adb9c22cb8c6fa425ab35fa500fe028278f2683160a
spec_frozen_sha256: 8c58857502cc45d2cb1f7f02c2154bee377fab4fa1deab2babaaf36bb93db6c2
---

# PO-Briefing: fix-638-fusslinie-dunkel

- **Spec:** docs/specs/fast/fix-638-fusslinie-dunkel.md
- **Issue:** #638
- **Erstellt:** 2026-11-23

## Was gebaut wird

Die Trennlinie über dem Fuß der Anmeldecode-Mail wird im Dunkelmodus dunkel statt hell.

## Definition of Done

Im Dunkelmodus ist die Linie dunkel wie der Kartenrand, im hellen Modus unverändert, und kein Text der Mail ändert sich.

## Wie geprüft wird

Ein automatischer Test prüft Klasse und Dunkelregel; die tatsächliche Optik im Mailprogramm bleibt Sichtprüfung anhand des Entwurfs.

## Kritische Anmerkungen

- Keine — Spec deckt die Anfrage ab, jede Anforderung hat einen Test.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
