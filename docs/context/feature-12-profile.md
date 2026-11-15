# Context: feature-12-profile (Issue #12, Paket F: Profile)

## Request Summary
Je Person ein reiseübergreifendes Profil (Vorlieben: Tempo, Essen, Unterkunftsarten, Budgetgefühl, Erlebtes). Der AI-Client schlägt Einträge über den Konnektor vor, eingetragen wird nur Bestätigtes; die Person sieht, ändert und löscht ihr Profil; Vorschläge an Wahlstellen nennen das Profil als Grund; Baustein `profile` schaltet die Nutzung je Reise.

## Festgelegt durch den Product Owner (Kommentar 1.11.2026)
- Ort: Tabelle in `konten.db` (außerhalb jeder Reise), je Eintrag Herkunft und Datum, wird mit dem Konto gelöscht.
- Schreiben: nur der AI-Client über den Konnektor (ADR-0001, kein KI-Lauf in Frieda), nur nach Bestätigung der Person.
- Lesen: nur die Person und ihr eigener AI-Client. Organisator:innen sehen nichts (Prüfpunkt „Sichtbarkeit einstellbar“ damit entschieden: nur die Person).
- Art. 9 DSGVO: Bestätigung = ausdrückliche Einwilligung; Hinweis gehört in den Datenschutztext.
- Meilenstein M6 „Später“: vor Beginn neu an ADR-0001 messen (in /20-analyse).

## Related Files
| Datei | Bedeutung |
|------|-----------|
| engine/konten.py | `SCHEMA` (neue Tabelle), `loeschen(kid)` (Profil mitlöschen, Tabellenliste um Z. 655), `zusammenfuehren` (Profil mitnehmen) |
| engine/konnektor.py | Konto-Werkzeuge ohne Reise: `frieda_werkzeuge(k)` (Z. 2257), `frieda_werkzeug(k, name, args)` (Z. 2358, Muster `an_frieda_melden`, `sprache_setzen`, `kalender`), `anleitung_frieda` (Z. 2293), `MEINE_REISEN` (Z. 2457) |
| engine/schnittstelle.py | Englische Außennamen der Werkzeuge/Felder; `"profiles": "profile"` für den Baustein schon da (Z. 150) |
| engine/texte_de.py / texte_en.py | Werkzeugbeschreibungen `konnektor.werkzeug.*`, Ausgaben, Anleitungssätze, Konto-Seite `konto.*`, Datenschutztext `recht.datenschutz.*` |
| engine/reise.py | `BAUSTEINE` enthält `profile`; `NOCH_NICHT_GEBAUT = {"profile": "Stufe 3"}` (Z. 41, Hinweis Z. 516) muss weg |
| engine/anmeldung.py | Mein Konto (`/konto`, Abschnitte als Karten, POST-Aktionen), Export `export_person` (Z. 939, person.json) muss das Profil enthalten, `EXPORT_PUNKTE`, Datenschutzseite `/datenschutz` |
| docs/produkt.md | Z. 27, 49, 156: „profile nicht gebaut“ → aktualisieren |
| docs/konnektor.md, docs/betrieb.md | Werkzeugliste, Datenschutz |
| docs/specs/betrieb/loeschen-381.md, export-498.md, rechtliches-383.md | Verwandte Specs (Löschen, Export, Datenschutz) |
| engine/tests/ (Konten, Konnektor, Export, test_englisch_schnittstelle.py) | Testmuster |

## Existing Patterns
- Konto-Werkzeuge (ohne `reise`): Dict mit `@konnektor.werkzeug.*`-Beschreibung, in `frieda_werkzeuge` angehängt, in `frieda_werkzeug` per `if name == …` behandelt; Fehler über `konten.KontoFehler(...).text(sprache)`.
- Schreibende Werkzeuge: Schreibgrenze je Konto (`konten.schreibgrenze`/`schreiben_vormerken`, #380); Profil-Schreiben sollte sie mitnutzen.
- Anleitung: „Vor jedem Eintragen den Wortlaut bestätigen lassen“ ist Grundregel; Profil-Regel kommt in `anleitung_frieda` (kontoweit), je Reise nur bei eingeschaltetem Baustein `profile`.
- Löschen: eine Transaktion, `DELETE FROM <t> WHERE konto = ?` über die Tabellenliste; Export: person.json ohne Kennungen anderer.
- Zweisprachigkeit: jeder Text in texte_de und texte_en, Außennamen englisch (ADR-0006).

## Dependencies
- Upstream: konten.db (sqlite), texte, schnittstelle (Namensübersetzung), Konnektor-OAuth (Konto des Aufrufers).
- Downstream: Mein Konto, Export, Kontolöschung, Kontozusammenführung, Datenschutzseite, Anleitung des Konnektors, `reise.yaml`-Prüfung (Baustein-Hinweis).

## Risks & Considerations
- Besondere Daten (Art. 9): nie in Reise, Seite, Service Worker, Logs, Meldungen oder Export anderer; nie an Organisator:innen.
- Kern-Prüfung (ADR-0001): Software kennt nur die Form eines Profileintrags (Bereich/Text/Herkunft/Datum), keine festen Vorlieben-Kategorien als Engine-Wissen; Bereiche aus dem Issue (Tempo, Essen …) höchstens als Vorschlag in der Anleitung.
- Kontolöschung und Zusammenführung müssen die neue Tabelle kennen.
- Prüfpunkt „Vorschläge an Wahlstellen nennen das Profil“: Verhalten des AI-Clients, nur über die Anleitung steuerbar; prüfbar ist der Anleitungstext.
- „Mein Konto“ als Ort zum Ansehen/Ändern/Löschen ohne AI-Client (ADR-0003: eine Heimat).
- Deploy: Modulliste in betrieb/deploy.sh nur, falls ein neues Modul entsteht.

## Analysis

### Type
Feature

### Messung an ADR-0001 (M6: vor Beginn neu gemessen, 15.11.2026)
| Nr. | Ergebnis |
|---|---|
| 1 Ontologie | besteht: Profil hängt an der Person (Grundform Person), nicht an einer Reise; gleich für Wanderung (Ida/Karl) und Stadtwochenende (Tom/Lea) |
| 2 Kein Katalog | besteht nur mit freiem Feld `bereich` (Text); keine Kategorien (Tempo, Essen …) im Code, höchstens als Beispiel im Anleitungstext |
| 3 Keine KI | besteht: Frieda prüft nur Pflichtfelder/Längen/Eigentum |
| 4 Tür | Konto-Werkzeuge im Konnektor, in `docs/konnektor.md` dokumentiert |
| 5 Herkunft | `herkunft` Pflicht, `datum` setzt Frieda selbst; ohne Herkunft abgelehnt |
| 6 Rollen | keine Entscheidung; Eintrag nur mit `confirmed=true` (Beleg der Bestätigung im Gespräch, PO 1.11.: „eingetragen wird nur, was die Person im Gespräch bestätigt hat“) |
| 7 IDs/Verlauf | Profil ist Kontodatum, nicht Reise-Ontologie (wie Sitzungen); echtes Löschen einzelner Einträge ist DSGVO Art. 17 und durch PO-Entscheidung 1.11. („löschbar“, Prüfpunkt „ändern oder löschen“) gedeckt. Klarstellung als Verlaufszeile in ADR-0001 mit Verweis auf diese PO-Entscheidung, keine neue Ausnahme |
| 8 PWA | Profil erscheint nie auf der Reiseseite/im Service Worker; Heimat ist „Mein Konto“ (ADR-0003) |
| 9 Claude Code | besteht |
| 10 Doku | docs/konnektor.md, docs/produkt.md, Datenschutztext, ADR-0001 Verlauf |

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/konten.py | MODIFY | `SCHEMA`: Tabelle `profil` (id INTEGER PK AUTOINCREMENT, konto, bereich, text, herkunft NOT NULL, datum); `profil_liste/profil_setzen/profil_entfernen`; `loeschen()` Tabellentupel (Z. 655); `zusammenfuehren()` Einträge umhängen (Autoincrement → keine Nummernkollision) |
| engine/konnektor.py | MODIFY | Konto-Werkzeuge in `frieda_werkzeuge` (Z. 2257) / `frieda_werkzeug` (Z. 2358, Zweige VOR `reisen_des_kontos`): Lesen, Setzen (Schreibgrenze explizit, Z. 2412-Muster), Entfernen; kontoweiter Anleitungssatz in `anleitung_frieda` (Z. 2293); je Reise in `anleitung()` (~Z. 3016/3052) Satz je nach Baustein `profile` (an: nutzen und als Grund nennen; aus: nicht nutzen; `bausteine is None` = an) |
| engine/schnittstelle.py | MODIFY | englische Außennamen + deutsche Aliase; Werkzeug heißt `my_profile` (Alias `mein_profil`), um Verwechslung mit Baustein `profile` (Z. 150) zu vermeiden; `profile_entry_set`, `profile_entry_remove` |
| engine/texte_de.py, engine/texte_en.py | MODIFY | Werkzeug-/Feldbeschreibungen, Ausgaben, Fehler, Anleitungssätze, Karte „Mein Profil“, Export-Punkt, Datenschutz Art. 9 (`recht.datenschutz.*`, ~Z. 3546) |
| engine/anmeldung.py | MODIFY | `konto_seite` (Z. 1040) Karte „Mein Profil“ (ansehen, Text ändern, löschen; POST mit `WHERE konto=?`); `export_person` (Z. 939) + `EXPORT_PUNKTE` |
| engine/reise.py | MODIFY | `NOCH_NICHT_GEBAUT` leeren (Struktur bleibt) |
| engine/tests/test_profil.py | CREATE | Konten-Funktionen, Löschen mit Konto, Zusammenführen, Export, Mein Konto, Isolation (Karl sieht nichts von Ida, Organisator:in nichts von Mitreisenden), Konnektor-Werkzeuge DE/EN, Anleitung je Baustein, Schreibgrenze |
| engine/tests/test_grenzen.py (Z. 79), test_bauen.py (Z. 532), test_englisch_schnittstelle.py, test_oauth.py | MODIFY | erwartbare Anpassungen (freie Werkzeuge, Baustein-Hinweis, Werkzeuglisten) |
| docs/konnektor.md, docs/produkt.md (Z. 27, 49, 67, 156), docs/adr/0001-kern.md (Verlauf) | MODIFY | Doku |

### Scope Assessment
- Files: ~12 (davon 1 neu)
- Estimated LoC: Code +270, Texte ~40 Schlüssel je Sprache, Tests +250, Doku +30
- Risk Level: MEDIUM (besondere Daten nach Art. 9; Kontolöschung/-zusammenführung; sonst isoliert, kein neues Modul, `betrieb/deploy.sh` unberührt, keine Reisedaten-Formatänderung → `neu.py nachziehen` nichts nötig, Migration per `CREATE TABLE IF NOT EXISTS`)

### Technical Approach
Wie in Affected Files. Entscheidungen des Tech Leads:
- Baustein `profile` steuert nur die Nutzung je Reise über die Anleitung; die Daten liegen kontoweit, das Lesewerkzeug bleibt immer erreichbar (technisch ist Lesen je Reise nicht sperrbar, der AI-Client hat das Konto). Folgt direkt aus PO-Entscheidung „am Konto“.
- Bestätigung: Pflichtfeld `confirmed=true` + Herkunft, keine Zwischenstufe „vorgeschlagen“ (PO-Entscheidung 1.11.: Bestätigung im Gespräch = Einwilligung). Datenschutztext sagt das ausdrücklich.
- IDs: Autoincrement, nach außen `PR-<n>`; nie wiederverwendet.
- Art. 9: Profiltexte nie in Logs (stderr nur Kennung), Meldungen, Push, Reiseseite, Service Worker, Export anderer, Betreiber-Meldung.
- Schreibgrenze: Setzen zählt, Lesen und Entfernen nicht (Löschen darf nie durch eine Grenze verhindert werden).
- Grenzen: Länge `bereich`/`text` begrenzt, Anzahl Einträge je Konto begrenzt (Missbrauchsschutz, Wert in `instanz.py` als Vorgabe).
- Reihenfolge: konten.py → Konnektor + Schnittstelle + Texte → Anleitung → Mein Konto + Export → Datenschutz → Doku.
- „Erst zeigen, dann bauen“ (#436): Karte „Mein Profil“ auf Mein Konto und der neue Datenschutzabsatz werden in Phase 3 als Artefakt-Entwurf mit Beispieldaten (Ida) gezeigt, vor dem Bauen.

### Dependencies
Upstream: konten.db (sqlite), texte, schnittstelle, Konnektor-OAuth (Konto des Aufrufers), instanz.py (Grenzen). Downstream: Mein Konto, Export, Kontolöschung/-zusammenführung, Datenschutzseite, Anleitung des Konnektors, Baustein-Hinweis in der reise.yaml-Prüfung.

### Open Questions
- [x] Bedeutung Baustein `profile` bei kontoweiten Daten → Tech-Lead-Entscheidung oben (folgt aus PO 1.11.)
- [x] Bestätigung nur im Gespräch → PO 1.11. entschieden
- [ ] Entwurf „Mein Profil“ + Datenschutzabsatz dem PO zeigen (Phase 3, Freigabe der Spec)
