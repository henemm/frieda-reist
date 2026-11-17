# Instanz-Tests mit dem Branch (AC-21)

Kopie des Reisen-Repos der Instanz (nur Arbeitsdateien), einmal mit der Software dieses Branches, einmal mit `origin/main`.
Ablauf je Kopie: `neu.py nachziehen` je Reise, `bauen.py` je Reise, `pytest -q -n auto tests`.

- Branch: alle Reisen umgestellt (`dinge:`) und gebaut, Exit 0, keine Fehlerzeilen. Tests: 2 failed, 16 passed.
- main: alle Reisen gebaut. Tests: 3 failed, 15 passed.
- Die Fehlschläge im Branch (`test_einstellungen_wie_auf_dem_server`, `test_volllauf_gr221`) schlagen auf main genauso fehl
  (Umgebung der Kopie bzw. bestehender Stand der Reise, unabhängig von #453). Kein Fehler gegenüber main hinzugekommen.
