---
spec_file: docs/specs/betrieb/wackelige-browsertests-661.md
spec_sha256: 87278f599267bc22fd5607d17d8988b8b7a788be1f1c53be9bfffce9ad8d892f
spec_frozen_sha256: bf8b1308349c988430f8569d92028de59f9a4520589f9421a78d469286e596ee
---

# PO-Briefing: fix-661-seitenwechsel-warten

- **Spec:** docs/specs/betrieb/wackelige-browsertests-661.md
- **Issue:** #661 (zusammen mit #664)
- **Erstellt:** 2026-11-24

## Was gebaut wird

Der automatische Seitenrundgang wartet nach jedem Ansichtswechsel, bis die Seite fertig gezeichnet hat, und wird so nicht mehr zufällig rot.

## Definition of Done

Die zwei Wackeltests laufen auch bei künstlich verlangsamter Seite grün, ein echter Seitenfehler bleibt rot, und alle Pflichtprüfungen auf main sind grün.

## Wie geprüft wird

Neue Tests verlangsamen gezielt einzelne Wechsel und simulieren einen echten Fehler; der Beleg im WebKit-Browser entsteht nur in der CI, nicht lokal.

## Kritische Anmerkungen

- Bisherige grüne Läufe maßen teils die falsche Ansicht; gespeicherte Ansichten ändern sich, Erwartungen liefen damit noch nie, könnten echte Fehler zeigen.
- Ähnliche feste Wartezeiten in anderen Messskripten bleiben bewusst unberührt, wie im Issue-Kommentar vorgesehen.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
