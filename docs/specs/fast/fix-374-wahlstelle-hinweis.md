# Mini-Spec: Hinweistext schreiben.wahlstelle_anlegen.4 nennt alle Sorten einer Option (#374)

## Was ändert sich
- `engine/texte_de.py` (`schreiben.wahlstelle_anlegen.4`): Der Text nennt als Inhalt einer Option `unterkuenfte, strecken, aufenthalte, orte oder folge`.
- `engine/texte_en.py` (`schreiben.wahlstelle_anlegen.4`): dieselbe Ergänzung auf Englisch (`unterkuenfte, strecken, aufenthalte, orte or sequence`).
- Quelle der Namen ist die Prüfung in `engine/schreiben.py` (`option_bauen`) und der Text `schreiben.option_bauen.2`, der sie schon nennt; gleiche Lücke wie #364.

## Acceptance Criteria
- AC-1: `schreiben.wahlstelle_anlegen.4` nennt in der deutschen Fassung `unterkuenfte`, `strecken`, `aufenthalte`, `orte` und `folge`.
- AC-2: Dieselben Sorten stehen in der englischen Fassung (mit `sequence` statt `folge`).
- AC-3: Schlüssel, Platzhalter und das Verhalten von `wahlstelle_anlegen` bleiben unverändert; die Textkataloge DE und EN haben weiter dieselben Schlüssel.

## Was darf sich nicht ändern
- Das Verhalten von `wahlstelle_anlegen` (Annahme und Ablehnung) bleibt gleich; es ändert sich nur ein Hinweistext.
- Der Schlüssel `schreiben.wahlstelle_anlegen.4` und seine Platzhalter bleiben gleich.
- Deutsch mit korrekten Umlauten; die Textkataloge DE und EN bleiben deckungsgleich in den Schlüsseln.

## Manuelle Test-Schritte
1. `wahlstelle_anlegen` der Beispielreise ohne `optionen` aufrufen: Die Ablehnung nennt alle fünf Sorten.
2. Dasselbe mit englischer Sprache: dieselben Sorten, englisch formuliert.

## Inline-Test (wird während Implementierung geschrieben)
- [ ] Test: Der Text `schreiben.wahlstelle_anlegen.4` enthält in DE und EN `unterkuenfte`, `strecken`, `aufenthalte`, `orte` und die Folge (`test_wahlstelle_anlegen_hinweis_nennt_alle_sorten` in `engine/tests/test_texte.py`, schon rot).
