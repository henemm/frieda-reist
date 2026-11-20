# Tests der Instanz mit diesem Stand (AC-6)

Stand 2026-11-20. Die Prüfungen der einbindenden Instanz (`<FR_DIENST>/instanz/tests`) liefen zweimal mit
`engine/.venv/bin/python -m pytest -q`: einmal mit `FR_WURZEL` = Arbeitsstand von #584, einmal mit dem Software-Klon der
Instanz (Stand `software-gut` = 7cfe5da, Basis dieses Branches).

| Lauf | Ergebnis |
|---|---|
| Software #584 (Arbeitsstand) | 3 passed |
| Software-Klon der Instanz (7cfe5da) | 3 passed |

Kein Fehler kommt hinzu; beide Läufe grün. Der Meldungstext der Umstellung ist unverändert.
