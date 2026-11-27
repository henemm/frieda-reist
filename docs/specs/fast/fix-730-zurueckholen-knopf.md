# Mini-Spec: fix-730-zurueckholen-knopf

Issue #730. Gemeldet vom Product Owner am 27.11.2026: Vorgemerkte Reisen stehen oben in „Deine Reisen“, aber ohne
„Reise zurückholen“, obwohl er dort Organisator ist. Er kann nicht reagieren.

## Ursache (auf der Instanz nur lesend nachgestellt)

`_person` (`engine/anmeldung.py`) liest die Personen aus der veröffentlichten Seite (Liste mit `schluessel`); gibt es
die Seite nicht mehr, liest es `reise.yaml` aus dem Reisespeicher. Dort sind die Personen eine Zuordnung
`{schluessel: {name, rolle, …}}`. Der Rückweg sucht darin wie in einer Liste, findet niemanden, die Rolle bleibt leer,
`ist_organisatorin` ist falsch, der Knopf fehlt. Da die Seite nach dem Vormerken abgebaut wird, trifft es jede
vorgemerkte Reise. Derselbe Rückweg speist den Hinweis aufs Zurückholen in der Löschmeldung und die Rolle im Datenexport.

## Was ändert sich

- `engine/anmeldung.py`, `_person`: Beim Rückweg über `reise.yaml` wird eine Zuordnung als Personen mit
  `schluessel` = Schlüssel der Zuordnung gelesen; eine Liste wie bisher.
- `engine/tests/test_loeschen_reise.py`: Test mit abgebauter Seite (kein Zustand der Seite, Reise nur im Speicher).

## Was darf sich nicht ändern

- Texte, Gestalt und Ort des Blocks, die Regel „Knopf nur für Organisator:innen und nur vor Fristende“.
- Verhalten, solange die Seite noch veröffentlicht ist.
- Kein Eingriff in Reisedaten oder Konten der Instanz.

## Acceptance Criteria

- AC-1: Ist die Seite einer vorgemerkten Reise abgebaut, zeigt „Mein Konto“ einer Organisator:in den Knopf
  „Reise zurückholen“; Zurückholen gelingt.
- AC-2: Eine Mitwirkende sieht in derselben Lage den Block ohne Knopf und kann nicht zurückholen.
- AC-3: Bestehende Tests zum Löschen und zum Export bleiben grün.
