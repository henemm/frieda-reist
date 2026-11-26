# Kontext: feat-711-unterschriften (Issue #711, Etappe 3, Teil 3)

## Auftrag
Die Unterschriften der Bilder „Überblick“ (`reise`) und „Tag“ (`tag`) auf der Unterseite Reiseseite und auf der Infoseite
beschreiben nur, was die Handybilder zeigen, DE und EN. Dazu der LOW-Fund des Adversary aus Teil 2 (Betrieb, zwei Minuten).

## Was die Bilder zeigen (angesehen)
- `reise-de/en`: Titel „Beispielreise – Malerweg in vier Tagen“, Zeitraum, Reiter „Varianten“ mit Zähler („noch 185 Tage“),
  Anreise Do 13.5. mit dem Zug nach Dresden, „Karte vergrößern“, Karte mit Dresden, Stadt Wehlen, Bastei, Hohnstein und den
  Tagen 2 und 3; unten die Reiterleiste. Keine Zeitachse der Tage, keine Pläne.
- `tag-de/en`: Tag 2 · Fr 14.5. „Stadt Wehlen → Bastei → Hohnstein“, Pläne A und B, Übersicht, Zeitleiste mit Start Dresden,
  S-Bahn mit ab/an und Quelle, darunter „Buchung · gebucht“. Keine Nacht, kein Weg zum Lesen.

## Betroffene Dateien
`engine/texte_de.py`, `engine/texte_en.py`, `engine/tests/test_funktionsseiten_711.py`.

## Analysis
Type: Feature (Textkorrektur). Risiko niedrig. Offene Fragen: keine.
