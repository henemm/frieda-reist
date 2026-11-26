# Kontext: feat-711-betrieb (Issue #711, Etappe 3, Gruppe „Konto und Betrieb“, Teil 2)

## Auftrag
Unterseite `betrieb` („Selbst betreiben“, Quelle `docs/funktionen/selbst-betreiben.md`), DE und EN, kurz; Zielgruppe sind
Leute, die einen eigenen Server betreiben wollen; die technische Anleitung `docs/betrieb.md` wird verlinkt. Teil 1:
`docs/context/feat-711-konto.md`. Dazu zwei Textfunde des Adversary aus Teil 1 (`sprachen.wer`, `sprachen.wie.1.text`).

## Betroffene Dateien
- `engine/anmeldung.py`: Eintrag in `INFO_UNTERSEITEN` mit `doku`; `unterseite` zeigt den Link.
- `engine/texte_de.py`, `engine/texte_en.py`: `info.bereich.betrieb.…`, zwei Korrekturen.
- `engine/tests/test_funktionsseiten_711.py`: Gruppe vollständig, Link zur Anleitung.
- `docs/design.md`: Form einer neuen Unterseite um `doku` ergänzt.

## Risiken
Die Texte sind HTML-escaped und können keinen Link tragen; deshalb das Feld `doku`. Die Adresse des Repos kommt aus
`instanz.QUELLCODE` (eine Instanz mit eigenem Fork bekommt ihren Link). Die Anleitung ist deutsch; der englische Linktext
sagt das.

## Analysis
Type: Feature (Inhalt in fertiger Form, ein kleiner optionaler Link). Risiko niedrig. Offene Fragen: keine.
