# Adversary Dialog — feat-711-planen
Spec: docs/specs/oberflaeche/funktionsseiten-711-planen-1.md
Datum: 2026-11-26 19:01

## Checkliste
- [x] AC-1: `/info/funktionen/wahrheit/` und `/info/funktionen/gespraech/` liefern in DE und EN 200 mit allen Abschnitten aus dem Katalog (`test_unterseite[wahrheit]`, `test_unterseite[gespraech]`).
- [x] AC-2: Die Übersicht verlinkt beide Bereiche statt „Seite folgt“ (`test_uebersicht_alle_funktionen`).
- [x] AC-3: Texte und Bilder vollständig je Sprache (`test_texte_und_bilder_jeder_unterseite`); Ausnahmelisten in `test_texte.py` nicht länger; englische Texte ohne deutsche Wörter (`test_englisch_schnittstelle`).
- [x] AC-4: Beispiele stimmen mit `beispiel/reisen/beispielreise` überein (Preise 85 €/70 €, 120 €/140 € am Samstag, Wahl der Pension Burgblick durch Ida, „nicht gebucht“); Bildunterschriften beschreiben nur, was das Bild zeigt.

## Dialog

### Runde 1
**Adversary:** Beweise verlangt für AC-1 bis AC-4. Angriffe: (a) fehlt ein Textschlüssel in einer Sprache? (b) steht ein deutsches Wort im englischen Katalog? (c) wurden Ausnahmelisten in `test_texte.py` verlängert? (d) passen Preise, Namen, Strecken zur Beispielreise? (e) behaupten die Texte etwas, das `docs/funktionen/reisemodell.md` oder `gespraech.md` nicht stützt? (f) beschreiben die Bildunterschriften mehr, als die Bilder zeigen?
**Implementierer:** Testlauf (ohne absolute Pfade): `110 passed in 71.87s` für test_funktionsseiten_711, test_texte, test_englisch_schnittstelle, test_englisch, test_englisch_werte, test_protokolle_ohne_pfade; zuvor im Workflow `125 passed` (`test-run-output.txt`). Der Diff gegen HEAD enthält keine Änderung an `engine/tests/test_texte.py`, die Ausnahmelisten sind also unverändert. `qa_gate.py --run` verweigert (kein `qa_gate.test_command` konfiguriert), deshalb direkt gelaufen, Ausgabe in `adversary-test-output.txt`.
**Adversary-Befund Runde 1:** Daten geprüft. Hotel am Elbufer 120 €, am 15.5.2027 140 € (`beispiel/reisen/beispielreise/plan/routen.yaml`, U-01); Pension Burgblick 85 € mit Frühstück, ohne Prüfdatum (U-02); Gasthof Polenztal 70 €, Abendessen im Haus, 15 Minuten Anstieg (U-03); V-03.a von Ida gewählt, „liegt am Weg" (V-03); Buchungen nur für U-01 und E-20, keine für U-02, also „nicht gebucht" zutreffend; S-Bahn Bad Schandau → Dresden (E-21) und Burg Hohnstein (O-03) vorhanden; Tag 2 „Stadt Wehlen → Bastei → Hohnstein" (T-02). Arten Malerweg: hotel, pension, gasthof, herberge, wandern, bahn, bus (`plan/arten.yaml`); Stadtwochenende: gastzimmer, essen, museum, bahn (`stadtwochenende/plan/arten.yaml`). Alles stimmt. Schlüssel „Zu buchen", „nicht gebucht", „Fehlt noch", „ungeprüft", „Mit Claude verbinden" existieren in `engine/texte_de.py`.

### Runde 2
**Adversary:** Zweiter, schärferer Durchgang auf Inhaltstreue und Bilder. Bild `wahl-de.webp` gesehen: Pension Burgblick mit „gewählt", „im Plan", Preis 85 € und Frühstück „inklusive" gepunktet unterstrichen mit „ungeprüft", Wahlstelle „Unterkunft in Hohnstein" „entschieden". Die Unterschrift `bild.wahl` behauptet nur Möglichkeit, gepunktete Werte mit Herkunft und „ungeprüft" gleich fehlendes Prüfdatum: gedeckt. Bild `tag-de.webp`: Tag 2 „Stadt Wehlen → Bastei → Hohnstein", S-Bahn Dresden → Stadt Wehlen mit Zeiten 08:12/08:40, „Quelle: Beispiel; Fahrplan nicht geprüft", darunter Zeile „Buchung": `bild.tag` (Tag 2, S-Bahn, Zeiten, Quelle, Buchung) gedeckt. Die EN-Bilder haben dieselbe Seitenstruktur; die Unterschriften sind gleichwertig übersetzt. Aussagen gegen Doku: Herkunftspflicht, Prüfdatum, „ungeprüft", 120/140 € (`reisemodell.md`, Abschnitt Herkunft und Prüfdatum); Vorlagen und Übernahme früherer Arten, „Erst Arten, dann der Plan", Frieda löscht nie, Reise-Stand 43/42, zwei Minuten, Rollen Gast/Mitwirkende/Organisator:in, Schreibschutz nach der Reise und Archiv (`reisemodell.md`, `lebenszyklus.md`); Konnektor-Schritte, Team-Admin, Wortlaut bestätigen, „keine eigene KI", „Claude entscheidet nie" (`gespraech.md`); Mahnung nur im Status „fest" (`erinnerungen.md`, `reisemodell.md`). Keine falsche Behauptung gefunden. Struktur: `INFO_UNTERSEITEN` hat beide Einträge, `wahrheit` und `gespraech` stehen schon in `INFO_GRUPPEN`; die „siehe"-Ziele (`gespraeche`, `konto`, `packliste`, `alternativen`, `buchungen`) sind bestehende Bereiche, `test_unterseite` fordert Vollständigkeit je Sprache und bestand.
**Implementierer:** Keine Einwände.

### Bewertung je Punkt
Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:1348
  Evidence: beide Einträge in INFO_UNTERSEITEN; test_unterseite[wahrheit] und [gespraech] grün (DE und EN, alle Abschnitte).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/anmeldung.py:1336
  Evidence: INFO_GRUPPEN führt wahrheit und gespraech; test_uebersicht_alle_funktionen grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/texte_en.py:3895
  Evidence: alle Schlüssel info.bereich.wahrheit.* und gespraech.* in DE und EN vorhanden (je 71 Zeilen im Diff); test_texte und test_englisch_schnittstelle grün; test_texte.py unverändert, Ausnahmelisten nicht länger.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/texte_de.py:3897
  Evidence: Preise, Namen, Wahl durch Ida, „nicht gebucht", Arten beider Beispielreisen stimmen mit den Beispieldaten überein; Bildunterschriften bild.wahl und bild.tag decken sich mit den angesehenen Bildern.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`). Die Änderung schreibt keine Datenfelder, sondern nur Textschlüssel und zwei Katalogeinträge; keine verdächtigen Schreibstellen.

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Tests: 110 passed, 0 failed, 0 übersprungen
Edge cases: alle geprüft, keine gebrochen
Regressions: keine gefunden
Checklist: 4/4 points proven

## Geprüfte Dateien

- sha256:d09a1775410a122367cdb05861a9d8304e78a4d1393c251d544800d25853ec32  engine/anmeldung.py
- sha256:6c0a50e8f9a3f72f5f358455c553c6dee70af61ae8c7927e0351724435f1affc  engine/texte_de.py
- sha256:2528ad763c5c04631b715b38bd33f5dcf94fab1946ad83304d4ffabeed3c1f7e  engine/texte_en.py

## Prüfbasis

- base: 3e187650f944183e7f7c2dbf496f8e2b029dbb17
- blob:5866b9ea5a4ac88767d42e5db85596e5fe5b1789  engine/anmeldung.py
- blob:eb5b6c13a53ecb428f855cbe3f658d2a9e760bd9  engine/texte_de.py
- blob:5cb7a6b67daeef6cb8baff30e9fbc690e09fff73  engine/texte_en.py
