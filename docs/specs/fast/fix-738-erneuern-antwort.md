# Mini-Spec: fix-738-erneuern-antwort

Issue #738. Befund F003 aus der Prüfung zu #669 (niedrig, bestand schon vorher).

## Ursache

`Bruecke.erneuern` (`betrieb/testzugang.py`) behandelt nur HTTP ≠ 200 als `ErneuernFehler`. Antwortet `/token` mit
HTTP 200, aber der Körper ist kein JSON (`json.loads` → `ValueError`), kein Objekt (`TypeError`) oder ohne
`access_token`/`refresh_token` (`_tokens_uebernehmen` → `KeyError`), fliegt die Ausnahme ungefangen bis `main`. Die
Brücke endet mit Traceback und Exit 1 und ist für den Rest der Claude-Code-Sitzung weg.

## Was ändert sich

- `betrieb/testzugang.py`, `Bruecke.erneuern`: Eine unbrauchbare Antwort mit HTTP 200 wird zum `ErneuernFehler`
  (englische Meldung ohne Token-Inhalt, wie die bestehende), die Ablage bleibt unverändert. Den Rest erledigt der
  bestehende Weg aus #669: Antwort `-32603` mit der Anfrage-ID, die Brücke läuft weiter.
- `engine/tests/test_testzugang.py`: Test mit einem Endpunkt, der auf `/token` mit HTTP 200 und leerem Körper, `[]`
  oder `{}` antwortet.

## Was darf sich nicht ändern

- Gültige Erneuerung, Übernahme des Paars eines anderen Prozesses, HTTP ≠ 200, Kontoprüfung beim Start (anderes Konto
  oder Betreiber beendet die Brücke weiterhin).
- Kein Token und kein Antwortkörper in Fehlermeldungen oder auf stderr.

## Acceptance Criteria

- AC-1: Antwortet `/token` beim Erneuern mit HTTP 200 und leerem Körper, `[]` oder `{}`, beantwortet die Brücke jede
  Anfrage mit `-32603` und ihrer ID, läuft bis zum Ende der Eingabe weiter und endet mit Exit 0, ohne Traceback.
- AC-2: Die Ablage des Zugangs bleibt dabei unverändert (Refresh-Token nicht überschrieben).
- AC-3: Bestehende Tests des Testzugangs bleiben grün.
