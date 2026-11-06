# Mini-Spec: Test der Etappenlegende misst erst, wenn die Ebenenwahl ausgelegt ist (#369)

Grundlage: `docs/context/fix-369-legende-flake.md`.

## Was ändert sich
- `engine/tests/seiten_karte_legende.mjs`: Nach dem Klick auf den Schalter der Ebenenwahl der Etappenkarte wartet das Skript (`waitForFunction`, Zeitgrenze 5 s), bis die Liste aufgeklappt ist (`.leaflet-control-layers-expanded`) und mindestens eine Zeile (`label`) eine Breite über 0 hat. Danach misst es wie bisher.
- Läuft die Zeitgrenze ab (die Seite zeigt keine Ebenen), fängt das Skript das ab und misst trotzdem, damit der Test mit seiner bisherigen Meldung scheitert und nicht mit einem Abbruch des Skripts.

## Was darf sich nicht ändern
- Seite, Vorlage und Software bleiben unverändert; es ändert sich nur das Messskript des Tests.
- Keine feste Wartezeit, kein Überspringen oder Lockern der Prüfungen in `test_karte_legende.py` (Tippflächen von mindestens 44 px, Zeilen im Fenster, Schalter blendet Punkte aus und ein).
- Zeigt die Seite wirklich keine Ebenen, scheitert der Test weiter (kein falsches Grün).

## Manuelle Test-Schritte
1. `engine/.venv/bin/python -m pytest -q engine/tests/test_karte_legende.py` läuft in Chromium und WebKit, bei 390 und 1300 Breite, grün.
2. Den Lauf mit `-n 3` und unter Last mehrfach wiederholen (`--count` oder Schleife, mindestens fünfmal): keine Schwankung bei `[390-chromium]`.

## Inline-Test (wird während Implementierung geschrieben)
- [ ] Das Skript enthält den Wartepunkt zwischen Klick und Messung (statische Prüfung des Quelltexts in `test_karte_legende.py`, damit er nicht versehentlich verschwindet).
- [ ] Der vorhandene Test `test_legende_nach_arten` läuft in allen vier Fällen grün.
