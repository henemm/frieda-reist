# Mockups: „Meldungen an dich“ auf Mein Konto (#407)

Zur Spec `docs/specs/oberflaeche/meldungen-konto-407.md`, Analyse in `docs/context/meldungen-konto-407.md`.
Alle Daten sind erfunden (Ida und Karl aus der Beispielreise, Tom als Bittsteller, Adressen unter `example.org`).

| Datei | Zeigt |
|---|---|
| `ist.png` | Heute, nachgestellt: neue Reisen ohne Link, Adressen als Rohtext, „meine_reisen“ auf der Webseite, Prüfmeldungen einzeln |
| `soll-neu.png` | Soll: vier neue Meldungen mit Punkt, Zahlmarke „4 neu“, Marke je Art, Zeit relativ, Prüfungen gebündelt, „Gelesen (2)“ |
| `soll-gelesen.png` | Soll: alles gelesen, „Keine neuen Meldungen“, Gelesenes aufgeklappt |
| `soll-viele.png` | Soll: neun neue, die ersten fünf, dann „Alle 9 neuen zeigen“; Freischalten ohne Reise (nur Betreiber) |
| `soll-dunkel.png` | Soll in den dunklen Tokens |
| `mockup.html` | alle Rahmen nebeneinander, statisch, mit dem CSS aus `engine/anmeldung.py` und den neuen Regeln der Spec |

Neu erzeugen (vom Repo aus; `shots.js` braucht Playwright mit Chromium):

```bash
python3 docs/artifacts/meldungen-konto-407/mockup.py .
node docs/artifacts/meldungen-konto-407/shots.js docs/artifacts/meldungen-konto-407
```
