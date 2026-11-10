# Context: fix-449-rueckmeldung-kontext

## Request Summary
Eine Rückmeldung von der Seite soll einen kleinen, sprachneutralen Kontext mitbringen (Ansicht/Reiter, Abschnitt der Sprechblase, Reise-Stand), damit die Bearbeitung im AI-Client weiß, wo und worauf sich „das“ bezieht (#449).

## Related Files
| File | Relevance |
|------|-----------|
| engine/vorlage.html (`rmFormular`, `rmAbschicken`, `rmSpeichern`, `senden`, `ausgangSenden`, `rmEintrag`) | Absenden schickt nur `name, art, ziel, text, quelle`; `rmSpeichern` legt den Eintrag beim Speichern an (Offline-Ausgang `AUSGANG`), hier muss der Kontext festgehalten werden, `senden` reicht ihn weiter |
| engine/vorlage.html (`route`, `zeigeReiter`, Variable `reiter`, `location.hash`) | Quelle für Ansicht (Reiter, Hash) |
| engine/vorlage.html (`D.reise_stand.nummer`, `RS`) | Reise-Stand der Seite (auch offline) |
| engine/rueckmeldungen.py (`INHALT`, `LAENGE`, `pruefen`, Doppelt-Prüfung ~Z. 1316, Zeigen ~Z. 756/1451) | Prüfung und Ablage; `INHALT` gilt auch für die Doppelt-Erkennung und für `rueckmeldung_geben` |
| engine/konnektor.py (`liste_text` ~2363, `rueckmeldung_geben` ~3024, `rueckmeldung_senden`) | `feedback_list` zeigt Einträge; `feedback_give` baut den Eintrag aus `rm.INHALT` |
| engine/texte.py, engine/texte_*.py | Kontext-Beschriftungen in allen Sprachen (ADR-0006), Test `test_texte.py` |
| engine/schnittstelle.py | Alias-Tabellen (neue Parameter/Felder nur, wenn der Konnektor sie annimmt) |
| engine/sw.vorlage.js | Offline-Warteschlange liegt in der Seite (`AUSGANG`), nicht im Service Worker |

## Existing Patterns
- Eingabe wird in `pruefen` auf erlaubte Felder gekürzt, Längen in `LAENGE`, Muster `ZIEL_MUSTER`; alte Einträge ohne neues Feld bleiben gültig (`e.get(x, "")`).
- Sichtbare Texte nur im Katalog (`T("seite…")`, `tk("konnektor…")`), Ausnahmelisten in `test_texte.py` dürfen nur kürzer werden.
- Offline: `rmSpeichern` erzeugt den Eintrag `e` (mit `erstellt`, `lokal`) vor dem Senden; was dort in `e` steht, wandert unverändert in `AUSGANG` und wird später von `senden` verschickt. `senden` baut den Body aber aus festen Feldern: Kontext muss dort mit.

## Dependencies
- Upstream: Seite kennt Reiter/Hash/Reise-Stand; Dienst-Validierung.
- Downstream: `feedback_list`/`show` (Konnektor), `rm.eintraege` (Wächter/Erinnerer lesen Einträge), Doppelt-Erkennung über `INHALT`, Datenschutz-Export (#498) liest Einträge.

## Existing Specs
- ADR-0001 (Prüfstelle, Eingabefläche = Punkt 7), ADR-0006 (Mehrsprachigkeit), docs/sprachen.md.

## Risks & Considerations
- Doppelt-Erkennung: Kontext nicht in `INHALT` aufnehmen (sonst unterscheidet derselbe Text an anderer Stelle plötzlich nicht mehr), oder bewusst entscheiden.
- Kontext ist eine Eingabe von außen: nur feste Schlüssel, Länge und Muster prüfen, nichts Freies; ungültiger Kontext weist ab (Issue) bzw. wird verworfen: festlegen.
- Konnektor `feedback_give` (KI-Seite) hat keinen Kontext: Feld optional.
- Reise-Stand nur als Nummer (`D.reise_stand.nummer`), kein Zeitstempel (Bau soll deterministisch bleiben).
- Beide Beispielreisen: Wanderung (Tagesseiten, Varianten) und Städtewochenende (ohne Varianten): Ansichten unterscheiden sich.

## Analysis

### Type
Feature (Erweiterung der Eingabefläche, Punkt 7 der Prüfstelle; keine KI, nichts reisespezifisch)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/vorlage.html | MODIFY | Klick auf `[data-rm]` (Z. ~5459) hält Kontext fest: `ansicht` (Hash der Route, bereinigt), `abschnitt` (nächster Vorfahre mit fester Ebenen-Klasse, z. B. `ebene-weg`, `ebene-quellen`, `tagseite`, sonst leer), `stand` (`RS.nummer`). `rmFormular` merkt ihn im Dialog, `rmAbschicken`/`rmSpeichern` legen ihn in `e` (Offline-Ausgang), `senden` schickt `kontext` mit |
| engine/rueckmeldungen.py | MODIFY | `pruefen`: optionales Feld `kontext` (Objekt mit festen Schlüsseln `ansicht`, `abschnitt`, `stand`), Muster/Länge geprüft; ungültige Teile werden verworfen (Kontext ist Zusatz, kein Grund zur Abweisung); `INHALT` bleibt unverändert (Doppelt-Erkennung) |
| engine/konnektor.py | MODIFY | `liste_text` und Anzeige im Eintrag: Kontext lesbar (Katalogtexte); `feedback_give` unverändert (Kontext optional) |
| engine/texte.py, texte_*.py | MODIFY | neue Schlüssel für Beschriftung „Ansicht / Abschnitt / Stand“ in allen Sprachen; Seite-Schlüssel nur falls Anzeige in der Seite |
| engine/tests/ | CREATE/MODIFY | Tests: Formular sendet Kontext (Beispielreise Wanderung + Städtewochenende), Dienst nimmt gültigen an, verwirft ungültigen, alte Einträge ohne Kontext, Konnektor zeigt ihn, Offline: Kontext beim Speichern |

### Scope Assessment
- Files: ~5 (+ Tests)
- Estimated LoC: +120/-5
- Risk Level: LOW (additiv, alte Einträge bleiben gültig; Hauptrisiko: Doppelt-Erkennung und `senden` mit festen Feldern)

### Technical Approach
- Kontext als kleines Objekt `kontext: {ansicht, abschnitt, stand}`, rein aus festen Kennungen, nie Freitext/Sprache.
- Erfassung beim Klick der Sprechblase (nicht beim Absenden), damit Offline-Eintrag und Dialog denselben Ort tragen.
- Dienst: nur diese drei Schlüssel, je Muster `^[A-Za-z0-9][\w.\-]{0,79}$` (stand: Zahl); Abweichendes still verworfen, Rest bleibt. Ablage im Eintrag; `e.get("kontext")` für alte Einträge.
- Nicht in `INHALT` (sonst ändert sich die Doppelt-Erkennung).
- Konnektor: eine Zeile je Eintrag in `feedback_list` mit Katalogtext („Ort: Ansicht …, Abschnitt …, Stand …“).
- Datenschutz-Export (#498) liest Einträge unverändert mit, kein Personenbezug im Kontext.

### Dependencies
`rm.eintraege` (Wächter/Erinnerer), Doppelt-Prüfung ~Z. 1316, Export #498, `schnittstelle.py` nur falls `feedback_give` den Parameter bekäme (nicht vorgesehen).

### Open Questions
- [ ] Keine für den PO. Technisch entschieden: ungültiger Kontext wird verworfen statt abgewiesen (Rückmeldung geht nie verloren).
