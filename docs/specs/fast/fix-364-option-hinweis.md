# Mini-Spec: Hinweistext schreiben.option_bauen.1 nennt alle Sorten einer Option (#364)

## Was ändert sich
- `engine/texte_de.py` (`schreiben.option_bauen.1`): Der Text nennt als Inhalt einer Option `unterkuenfte, strecken, aufenthalte, orte oder folge`.
- `engine/texte_en.py` (`schreiben.option_bauen.1`): dieselbe Ergänzung auf Englisch (`unterkuenfte, strecken, aufenthalte, orte or sequence`).
- Quelle der Namen ist die Prüfung in `engine/schreiben.py` (`option_bauen`) und der Text `schreiben.option_bauen.2`, der sie schon nennt.

## Was darf sich nicht ändern
- Das Verhalten von `option_bauen` (Annahme und Ablehnung von Optionen) bleibt gleich; es ändert sich nur ein Hinweistext.
- Der Schlüssel `schreiben.option_bauen.1` und seine Platzhalter bleiben gleich.
- Deutsch mit korrekten Umlauten; die Textkataloge DE und EN bleiben deckungsgleich in den Schlüsseln.

## Manuelle Test-Schritte
1. Eine Option ohne Inhalt an `option_create` der Beispielreise geben: Die Ablehnung nennt alle fünf Sorten.
2. Dasselbe mit englischer Sprache: dieselben Sorten, englisch formuliert.

## Inline-Test (wird während Implementierung geschrieben)
- [ ] Test: Der Text `schreiben.option_bauen.1` enthält in DE und EN `unterkuenfte`, `strecken`, `aufenthalte`, `orte` und die Folge.
