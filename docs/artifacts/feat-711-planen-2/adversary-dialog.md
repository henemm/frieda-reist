# Adversary Dialog — feat-711-planen-2
Spec: docs/specs/oberflaeche/funktionsseiten-711-planen-2.md
Datum: 2026-11-26 19:11

## Checkliste
- [x] AC-1: `/info/funktionen/alternativen/` und `/info/funktionen/buchungen/` liefern in DE und EN 200 mit allen Abschnitten aus dem Katalog und ihren Bildern (`test_unterseite[alternativen]`, `test_unterseite[buchungen]`, `test_unterseiten_planen`).
- [x] AC-2: Die Übersicht verlinkt beide Bereiche statt „Seite folgt“ (`test_uebersicht_alle_funktionen`).
- [x] AC-3: Texte und Bilder vollständig je Sprache in den Maßen von `erzeugen` (`test_texte_und_bilder_jeder_unterseite`); Ausnahmelisten in `test_texte.py` nicht länger; englische Fachwörter einheitlich (`test_texte`).
- [x] AC-4: Beispiele stimmen mit `beispiel/reisen/beispielreise` überein (Wahl V-01 mit drei Möglichkeiten, Hockstein, Bus nur mit Gepäck in der Pension Burgblick, Buchung HE-2027-0415 mit 30 € Anzahlung, S-Bahn von Karl, stornierte Buchung); jede Bildunterschrift beschreibt nur, was das Bild in DE und EN zeigt.

## Dialog

### Runde 1
**Adversary:** Tests selbst gefahren: `test_funktionsseiten_711.py`, `test_texte.py`, `test_englisch_schnittstelle.py`, `test_protokolle_ohne_pfade.py` mit `-n 4`: 109 passed, 0 failed, 0 übersprungen. Das Protokoll `test-run-output.txt` der Implementierung zeigt die größere Läufe: 127 passed. `test_texte.py` ist nicht verändert (`git diff HEAD --stat`), die Ausnahmelisten sind also nicht länger. Der Test `test_unterseiten_planen` ist nur um die zwei neuen Schlüssel erweitert (kein Abschwächen). Beide Unterseiten sind in `INFO_UNTERSEITEN` mit Bildern, Gesprächsrollen und Verweisen eingetragen, die Bilder in `BILDER` auf echte Anker der Beispielreise (V-01, B-01, B-02, zu-buchen). Alle zwölf Bilder (vergleich, wahl, zutun, buchung, bahnbuchung, zubuchen, je de und en) wurden angesehen.
Inhalt gegen `beispiel/reisen/beispielreise/plan/routen.yaml`: V-01 hat drei Optionen (a, b, c); Regeln von V-01.c (erfordert V-03.a Pension Burgblick, schließt V-02.b aus) stimmen mit dem Text überein; Pläne P-A und P-B mit den genannten Titeln; V-02 `wann: unterwegs`, Auslöser „nur bei trockenem Fels“; B-01 HE-2027-0415, 120 €, 30 € angezahlt, 90 € Rest, 3 € Kurtaxe, 15:00/11:00, Storno bis 11.5.2027; B-02 von Karl, Sparpreis, bezahlt, Frist „Ticket in die App laden“, für E-20 (S-Bahn nach Stadt Wehlen); B-03 storniert, „Zimmer doppelt gebucht“. Alles stimmt.
Inhaltstreue gegen `docs/funktionen/alternativen.md` und `buchungen.md`: Rollen, Konfliktregel, Kalender, Belege (10 MB, Freigabe), Erinnerungen, Nachlese-Sperre, „Frieda bucht nicht selbst“ sind korrekt wiedergegeben; keine erfundene Funktion gefunden. Kürzungen (etwa bei den Erinnerungen der Rückfall auf Organisator:innen) sind Auslassungen, keine Falschaussagen.
Bildunterschriften: wahl, zutun, buchung (Nummer mit Kopier-Knopf, Check-in/-out, vor Ort), bahnbuchung (gebucht, bezahlt, Nummer, Frist), zubuchen („Datum und Stand“) stimmen in DE und EN. Zwei Abweichungen als LOW, siehe Findings.
**Implementierer:** keine Antwort nötig; Befunde sind Hinweise.

### Runde 2
**Adversary:** Gegenprobe der Randfälle. (1) Sprachgleichheit: Die englischen Bildtexte nennen „Letzter Tag: Weg zum Zug“ in Anführungszeichen unverändert, wie das Bild (Daten der Reise bleiben deutsch); EN-Bildschirmtexte „To do“, „To book“, „Details of the booking“, „Compare alternatives“ entsprechen den Beschriftungen in den Bildern. (2) Bild `zutun` zeigt „Zu entscheiden“ und „Unterwegs entscheiden“, Unterschrift „vor der Reise noch zu entscheiden … und was erst unterwegs“: passt. (3) Das Wahlbild zeigt „Fehlt noch“ auch bei einer entschiedenen Wahl; der Text sagt nur „Fehlt eine nötige Angabe, steht ‚Fehlt noch‘ dabei“, ohne einzuschränken: nicht falsch. (4) Keine absoluten Pfade im Protokoll; Test `test_protokolle_ohne_pfade` grün. (5) Keine Regressionen: die Änderungen sind rein additiv (zwei Wörterbucheinträge, vier Bildeinträge, Texte); die Übersicht und `INFO_GRUPPEN` führen die beiden Schlüssel schon seit HEAD, die Tests der Übersicht sind grün.
**Implementierer:** keine Antwort nötig.

### Runde 3
**Adversary:** Nachprüfung von F001 und F002. Neue Unterschrift `vergleich` (engine/texte_de.py:3971, engine/texte_en.py:3969): „drei Möglichkeiten zur Wahl, zwei davon nebeneinander im Vergleich, am Handy als Karten“. Das Bild zeigt „2 von 3 im Vergleich, höchstens 2 nebeneinander“, drei Auswahlknöpfe, zwei aktiv, Umschalter „Karten“: passt in DE und EN. Neue Unterschrift `buchung` (engine/texte_de.py:4008, engine/texte_en.py:4006): „Eine gebuchte Unterkunft: Nummer zum Kopieren, Check-in, Check-out und was vor Ort zu zahlen ist“. Das Bild zeigt den Buchungsblock einer Unterkunft mit Nummer und Kopier-Knopf, Check-in, Check-out, „Vor Ort zu zahlen“; kein Name behauptet: passt in DE und EN. Tests erneut: 109 passed, 0 failed, 0 übersprungen. Geändert sind laut `git diff HEAD --stat` weiter nur dieselben fünf Dateien, test_texte.py unverändert.
**Implementierer:** F001 und F002 behoben, nur zwei Unterschriften je Sprache.

## Findings

Finding:
  ID: F001 (in Runde 3 behoben)
  Severity: LOW
  Category: spec_violation
  Code reference: engine/texte_de.py:3971
  Description: Die Unterschrift „drei Möglichkeiten im Vergleich“ steht unter dem Bild `vergleich`; das Bild zeigt „2 von 3 im Vergleich, höchstens 2 nebeneinander“ (Knopf „Vergleich schließen 3“, drei Auswahlknöpfe, zwei davon aktiv).
  Spec requirement: AC-4 — die Bildunterschrift beschreibt nur, was das Bild zeigt
  Conflict: Drei Möglichkeiten stehen zur Wahl und im Vergleich bereit, verglichen werden im Bild aber zwei. Streng gelesen ungenau, sachlich nicht falsch; EN ebenso (engine/texte_en.py:3969).
  Remediation: „drei Möglichkeiten zur Wahl, zwei davon im Vergleich“ bzw. „three options, two of them in the comparison“.

Finding:
  ID: F002 (in Runde 3 behoben)
  Severity: LOW
  Category: spec_violation
  Code reference: engine/texte_en.py:4006
  Description: Die Unterschrift nennt „Hotel am Elbufer“; im sichtbaren Ausschnitt des Bildes `buchung` steht der Name nicht (nur „Altes Bürgerhaus am Fluss …“, der Kopf der Unterkunft ist abgeschnitten). Gilt für DE (engine/texte_de.py:4008) und EN.
  Spec requirement: AC-4 — die Unterschrift beschreibt nur, was das Bild zeigt
  Conflict: Der Hotelname ist aus den Daten richtig (U-01), aber im Bild nicht lesbar.
  Remediation: Ausschnitt des Bildes um den Kopf der Unterkunft erweitern oder Unterschrift ohne den Namen („Die gebuchte Nacht im Hotel: …“). Nicht blockierend.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:1352
  Evidence: Beide Einträge in `INFO_UNTERSEITEN` (Zeilen 1352 und 1354) mit Bildern, Gespräch und Verweisen; `test_unterseite[alternativen]`, `test_unterseite[buchungen]` und `test_unterseiten_planen` grün (109 passed).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/anmeldung.py:1336
  Evidence: `INFO_GRUPPEN` führt beide Schlüssel in der Gruppe „planen“; `test_uebersicht_alle_funktionen` grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/info/erzeugen.py:44
  Evidence: Vier neue Einträge in `BILDER` (Zeilen 44 bis 47), acht Dateien `*-de.webp`/`*-en.webp` vorhanden; Texte vollständig in engine/texte_de.py:3968 und engine/texte_en.py:3966 (gleiche Schlüsselmenge); `test_texte`, `test_englisch_schnittstelle` grün, `test_texte.py` unverändert.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/texte_de.py:4005
  Evidence: Alle Zahlen, Namen und Regeln der Beispiele stimmen mit `routen.yaml` überein (HE-2027-0415, 30 €, 90 € + 3 €, 11.5.2027, Karl/Sparpreis, B-03 doppelt gebucht; V-01 mit drei Optionen, V-01.c Regeln); englische Gegenstücke in engine/texte_en.py:4003. Bildunterschriften stimmen bis auf F001/F002 (LOW) mit den Bildern überein.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`). Die Änderung schreibt keine Feldwerte der Produktion, nur Texte, Konfigurationswörterbücher und Bilddateien; es gibt keine verdächtigen Zeilen.

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Umsetzung hat die Prüfung bestanden; die zwei LOW-Hinweise zu Bildunterschriften (F001, F002) sind in Runde 3 behoben und geprüft.
Tests: 109 passed, 0 failed, 0 übersprungen (eigener Lauf); 127 passed im Lauf der Implementierung
Edge cases: geprüft, keine kaputt
Regressions: keine
Checklist: 4/4 Punkte bewiesen

## Geprüfte Dateien

- sha256:12bb8b78bd18ad180a31b3bce200fd322c1f6dd70f13e409294d7983cb344174  engine/anmeldung.py
- sha256:0a1fa4482e874112fe6202f0daf0dbd147e16b5d6b5ce792c7d033bfd332753e  engine/info/erzeugen.py
- sha256:c4ed52274ac1e052721c64690cb7bfd04ae40ef5068bb33ab0ef90018a3b34a3  engine/texte_de.py
- sha256:961c715fd1aa74bde79e8d241bee0d1b9d5f2c16c35b71e11bbcf28d54c7b7c0  engine/texte_en.py

## Prüfbasis

- base: 3e187650f944183e7f7c2dbf496f8e2b029dbb17
- blob:54478269a6843f8350987cedbf720028c18ed34f  engine/anmeldung.py
- blob:75490db9e27f7c4bde8ec58da8d4207e1c8ec45a  engine/info/erzeugen.py
- blob:0f4cdeaa0f53970a1050f73e845a39ef146e0e73  engine/texte_de.py
- blob:58dd76f76dcf2baef1fd6f87a58c254b1b8cdaf0  engine/texte_en.py
