# Mini-Spec: Hinweis der Dinge ist Langtext (#601)

Lücke aus #594: Der `hinweis` von Unterkunft, Aufenthalt, Ort und Strecke steht nicht im Register `engine/textform.py`. Der Schreibweg plättet jeden Zeilenumbruch, die Seite zeigt `**fett**` und `1. … 2. …` roh in einer Zeile.

## Was ändert sich
- `engine/textform.py`: `FELDER["ding.hinweis"] = (LANG, 1000)`.
- `engine/schreiben.py`: `ding_anlegen` und `_ding_aendern_felder` lesen `hinweis` als Langtext (`textfeld="ding.hinweis"`): Zeilen und Listen bleiben, Überschriften und HTML werden abgelehnt.
- `engine/konnektor.py`: `hinweis` in DING_ANLEGEN/DING_AENDERN beschreibt sich über `textform.schema("ding.hinweis", …)`; in allen `engine/texte_*.py` ersetzt `konnektor.feld.ding_hinweis` den Text „eine Zeile“.
- `engine/kalender.py`: Der Kalender zeigt den Hinweis als Klartext ohne Auszeichnung.
- `engine/vorlage.html`: An der Heimat des Dings (Strecke, Aufenthalt, Unterkunft, Ort) steht der Hinweis als Langtext (Markdown); Kurzformen (Karte, Wissen-Popup, Suche, Titel-Ersatz) zeigen ihn ohne Sternchen.
- `docs/design.md`: Hinweis in der Liste der Langtext-Felder.

## Was darf sich nicht ändern
- Kein `nachziehen`: Der Hinweis bleibt ein String; bestehende einzeilige Hinweise sind gültiger Langtext.
- Bauen prüft den Hinweis nicht; alte Werte mit `<b>` oder `##` bleiben baubar.
- Kartenpunkte aus OpenStreetMap (`kartenpunkte_ablegen`, `neu.py`) bleiben unverändert.
- Gilt für beide Beispielreisen (Wanderung und Städtewochenende).

## Acceptance Criteria
- **AC-1:** `ding.hinweis` ist im Register als Langtext mit mindestens der bisherigen Länge (`MAX_TEXT`).
- **AC-2:** `ding_aendern` mit mehrzeiligem Hinweis (Fettes, nummerierte Liste) speichert den Text mit Zeilen, ohne Leerraum am Ende, in beiden Beispielreisen; die Reise baut.
- **AC-3:** `ding_anlegen` (Ort) speichert einen mehrzeiligen Hinweis unverändert.
- **AC-4:** Ein Hinweis mit Überschrift oder HTML wird mit Begründung abgelehnt.
- **AC-5:** Ein alter Hinweis mit `<b>` und `##` in den Reisedaten bleibt baubar.
- **AC-6:** Der Kalender zeigt den Hinweis ohne `**`, mit erhaltenen Zeilen der Liste.
- **AC-7:** Die Seite zeigt den Hinweis an der Heimat des Dings mit Fettem und nummerierter Liste; im Hauptbereich stehen nirgends Sternchen.

## Inline-Test
- [x] Abschnitt „Hinweis eines Dings“ in `engine/tests/test_textform.py`, Erweiterung `engine/tests/seiten_langtext.mjs`.
