# Kontext: feat-711-konto (Issue #711, Etappe 3, Gruppe „Konto und Betrieb“, Teil 1)

## Auftrag
Unterseiten `konto` (Quelle `docs/funktionen/konto.md`) und `sprachen` (Quelle `docs/funktionen/sprachen.md`), DE und EN.
Teil 2 bringt `betrieb`; danach verweist GitHub auf die Webseite.

## Betroffene Dateien
- `engine/anmeldung.py`: zwei Einträge in `INFO_UNTERSEITEN`.
- `engine/texte_de.py`, `engine/texte_en.py`: `info.bereich.konto.…`, `info.bereich.sprachen.…`.
- `engine/info/erzeugen.py`: neues Bild `fuss` (Überblick, Ziel `#fuss`); vorhanden `mitreisende`, `tag`.
- `engine/tests/test_funktionsseiten_711.py`: `test_unterseiten_konto`.

## Risiken
Mein Konto braucht eine Anmeldung und lässt sich nicht aufnehmen; die Bilder zeigen den Fuß der Reiseseite (Sprachzeile für
Gäste, Datenschutz, Impressum) und die Mitreisenden. Im englischen Bild bleiben die Texte der Reise deutsch; genau das
erklärt die Seite „Sprachen“.

## Analysis
Type: Feature (Inhalt in fertiger Form, Muster Etappe 2). Risiko niedrig. Offene Fragen: keine.
