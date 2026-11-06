# Tests der Instanz mit dem Branch (AC-20)

Stand 2026-11-06, nach Rebase auf origin/main (7274cbd). Die Tests der einbindenden Instanz (`tests/` im Reisen-Repo) liefen in zwei
Kopien der Instanz im Sitzungs-Scratchpad: einmal mit dem Software-Stand `origin/main`, einmal mit dem Arbeitsstand von #353.

| Lauf | Ergebnis |
|---|---|
| Software `origin/main` | 14 failed, 4 passed |
| Software #353 | 13 failed, 5 passed |

- Kein Fehler kommt mit #353 hinzu (Vergleich der FAILED-Zeilen: „nur neu“ ist leer).
- Die 13 Fehler beider Läufe sind dieselben bekannten Fehler aus main (Bau der echten Reisen `<Reise A>` und `<Reise B>` bricht an
  `reise.yaml` ab, dazu zwei Prüfungen der Server-Einstellungen; ADR-0008, nicht von #353).
- Der zusätzliche Fehler im main-Lauf (`test_frieda_enthaelt_nichts_privates`) kommt vom Aufbau der Kopie: der main-Stand lag als
  ausgepacktes Archiv ohne Git vor, die Prüfung ruft `git ls-files` auf.
