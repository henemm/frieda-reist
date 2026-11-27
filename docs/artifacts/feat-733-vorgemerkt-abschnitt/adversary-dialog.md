# Adversary Dialog — feat-733-vorgemerkt-abschnitt
Spec: docs/specs/konto/vorgemerkt-abschnitt-733.md
Datum: 2026-11-27 15:01

## Checkliste
- [x] AC-1: Hat ein Konto vorgemerkte Reisen, steht auf „Mein Konto“ ein `<details>` ohne `open` mit dem Titel „Zum Löschen vorgemerkt (n)“ (n = Anzahl). Es steht nach der Reiseliste und nach dem Archiv; vor der Reiseliste steht nichts zu vorgemerkten Reisen.
- [x] AC-2: Im Abschnitt steht je vorgemerkter Reise eine Kachel mit dem Titel der Reise und dem Löschdatum samt Zone.
- [x] AC-3: Den Knopf „Reise zurückholen“ sehen nur Organisator:innen vor Fristende; Zurückholen wirkt wie bisher.
- [x] AC-4: Ohne vorgemerkte Reisen gibt es den Abschnitt nicht.
- [x] AC-5: Texte in allen Sprachdateien; `test_texte.py` und `test_design.py` grün.

## Dialog

### Runde 1
**Adversary:** Tests: test_loeschen_reise, test_bilder_konto, test_texte, test_design, test_anmeldung, test_export mit -n 3: 270 passed, 2 skipped, 0 failed. Angriffe: (a) Konto nur mit Vorgemerkten: engine/anmeldung.py:1134 unterdrueckt "keine Reisen" bei meine_vorgemerkten, Abschnitt erscheint trotzdem; (b) Fristende vorbei: kachel_vorbei, Knopf nur bei offen; (c) n = len(vorgemerkt) ueber alle eigenen Vorgemerkten; (d) Titel durch esc() geschleust, n ist int; (e) alte Schluessel block/block_vorbei: kein Rest-Verbraucher (grep, nur Kontextdoku nennt sie); (f) Englisch: alle drei neuen Schluessel vorhanden.
**Implementierer:** keine Gegenwehr noetig, Code stimmt.

### Runde 2
**Adversary:** Zweite Runde: Position. In konto_seite wird loeschen_block nach dem Archiv angehaengt (anmeldung.py:1139), vorher nichts; Test test_abschnitt_steht_nach_dem_archiv prueft Reihenfolge und dass vor dem Archiv kein class mit "vorgemerkt" steht. Leere Liste ergibt "" (anmeldung.py:844), AC-4. Gleichzeitig Reise mit Konto ohne reise_info (abgebaut): reise_titel wie bisher, #730 Test gruen. Keine Befunde. Rest: die Tests decken Fristende-vorbei und HTML-Escaping nicht gezielt ab (nur Codepfad gelesen) - kein Mangel der Implementierung.
**Implementierer:** -

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`). Die Aenderung schreibt keine Felder neu; Zeile frist/offen stammt aus konten.loeschungen() unveraendert.


Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:1139
  Evidence: details.archiv.vorgemerkt ohne open (anmeldung.py:860), angehaengt nach Liste und Archiv; Titel mit n.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/anmeldung.py:856
  Evidence: Kachel mit fettem esc(titel) und Datum samt Zone via frist_text/zone.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/anmeldung.py:855
  Evidence: Knopf nur wenn offen und ist_organisatorin; Zurueckholen-Zweig unveraendert, Test gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/anmeldung.py:844
  Evidence: leere Liste gibt "" zurueck.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/texte_de.py:4444
  Evidence: abschnitt, kachel, kachel_vorbei in DE; test_texte und test_design gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/texte_en.py:4442
  Evidence: dieselben drei Schluessel in EN.
  Status: CONFIRMED

## Verdict
VERDICT: VERIFIED

## Geprüfte Dateien

- sha256:b15f2fba2b7001e4e768383e8858d8c0c6d8a17444cd0b990eab298c0051d637  engine/anmeldung.py
- sha256:5674226620b3bc2cb5b60377038859cb24e8c8da424ee5b10ee7b9d4a5e56ad8  engine/texte_de.py
- sha256:ef16fab84bf31a0fe8381f3bdd55fbe6e9e806fc608e01d8f4266b34dbcd805a  engine/texte_en.py

## Prüfbasis

- base: 0bebd5f92d8f8a80bb8194f11c33f5f06bd58726
- blob:4caf15d7cdb027ccdfaf40ce6ce3a2167ec4e41f  engine/anmeldung.py
- blob:cfeb19472d46e9a988e7236ff8fc521499e2e54e  engine/texte_de.py
- blob:1ff31f4ee5e9f6fbf6820ba63584231ed37ac099  engine/texte_en.py

## Geprüfte Dateien

- sha256:b15f2fba2b7001e4e768383e8858d8c0c6d8a17444cd0b990eab298c0051d637  engine/anmeldung.py
- sha256:5674226620b3bc2cb5b60377038859cb24e8c8da424ee5b10ee7b9d4a5e56ad8  engine/texte_de.py
- sha256:ef16fab84bf31a0fe8381f3bdd55fbe6e9e806fc608e01d8f4266b34dbcd805a  engine/texte_en.py

## Prüfbasis

- base: 0bebd5f92d8f8a80bb8194f11c33f5f06bd58726
- blob:4caf15d7cdb027ccdfaf40ce6ce3a2167ec4e41f  engine/anmeldung.py
- blob:cfeb19472d46e9a988e7236ff8fc521499e2e54e  engine/texte_de.py
- blob:1ff31f4ee5e9f6fbf6820ba63584231ed37ac099  engine/texte_en.py
