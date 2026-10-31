# Software nachziehen: gleiches Tor wie beim Veröffentlichen (#168)

## Anlass

Der Workflow „Software nachziehen“ (#161) prüfte `engine/tests tests` zusammen und sperrte bei jedem Rot. Am 31.10.2026
hielt ein Inhaltstest von GR 221 (Wahlstelle entschieden, Frage noch offen) den Stand 8799d15 auf. Solche Zustände
entstehen im Betrieb jederzeit über den Konnektor. Das Veröffentlichen behandelt rote `tests/` seit #142 nur als
Warnung. Das Nachziehen braucht dasselbe Tor, sonst kommt bei unstimmigem Inhalt keine Software in den Betrieb, auch
keine Fehlerbehebung.

## Tor

| Prüfung | Wirkung |
|---|---|
| `engine/tests` (Software) gegen den neuen Stand | rot sperrt |
| Bau jeder Reise (`reisen/*/reise.json`, wie `veroeffentlichen.sh`) mit `frieda/engine/bauen.py`, Ziel außerhalb des Repos | rot sperrt |
| `tests/` des Reisen-Repos | rot ist nur eine Warnung im Lauf (`::warning::`) |

Kein Issue und keine Nachricht für rote `tests/`: Das Veröffentlichen meldet sie schon einmal je Commit an den Betrieb.

## Prüfung der Tests in `tests/` (Reisen-Repo, Stand 31.10.2026)

Frage je Test: Heißt Rot „die Software passt nicht zu dieser Instanz, und der Bau fängt das nicht“?

- `test_reisen.py` (Volllauf, Pläne, Orte, Tracks, Konnektor): prüft fast nur Zahlen und Zustände des Inhalts. Stürzt
  die Software beim Bauen ab, fängt das der Bau jeder Reise. Warnung.
- `test_betrieb_instanz.py` (Einstellungen, Skripte, Meldeweg): Einzig `test_betriebsskripte_der_software` prüft die
  Passung zur Software. Er veraltet aber auf der Seite des Reisen-Repos (#230: erwartete das entfallene
  `arbeitskopie.sh`) und sperrte damals genau so. Warnung. Restrisiko: Fehlt ein Skript, das eine Unit aufruft,
  scheitert die Unit auf dem Server sichtbar (Monitor, Rot-Meldung).
- `test_frieda_privat.py`: Ein Fund in der öffentlichen Software ist mit dem Push schon öffentlich; das Sperren des
  Nachziehens hält nichts zurück. Warnung (der Test läuft weiter bei jedem Push in `tests.yml`).

Damit braucht es keine Markierung einzelner Tests.

## Akzeptanzkriterien

- **AC-1:** Der Schritt `tests` führt nur `engine/tests` aus (continue-on-error).
- **AC-2:** Ein Schritt `bau` baut jede Reise aus `reisen/*/reise.json` mit `frieda/engine/bauen.py` nach
  `$RUNNER_TEMP`, scheitert, sobald eine Reise nicht baut, und nennt sie (continue-on-error).
- **AC-3:** Ein Schritt `inhalt` führt `tests` aus, gibt bei Rot eine `::warning::` aus und endet grün. Er steht in
  keiner Bedingung von „Nach main übernehmen“ oder „Issue bei Testfehler“.
- **AC-4:** Übernommen wird nur bei `tests` und `bau` erfolgreich; das Issue entsteht, wenn einer der beiden scheitert,
  und der Text nennt das rote Tor.
- **AC-5:** `docs/betrieb.md` beschreibt das Tor beim Einrichten und in der Konvention für `tests/`.
- **AC-6:** Die Vorlage bleibt ohne Angaben einer Instanz (#161, AC-4).

## Einführung

Vorlage nach `.github/workflows/` des Reisen-Repos kopieren, dann den Workflow von Hand starten: Der neue Stand der
Software (dieser Commit) wird mit dem neuen Tor übernommen. #168 schließt nach diesem grünen Lauf.
