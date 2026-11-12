---
entity_id: packliste-431
type: module
created: 2026-11-12
updated: 2026-11-12
status: approved
version: "1.0"
tags: [vorlage, packliste, summen, sortieren, ausblenden, konnektor]
---

# Packliste: Summen je Merkmalswert, Sortieren, Packen nur meins und kompakt, Kategorien ausblenden (#431)

## Approval

- [x] Approved (Product Owner, 12.11.2026: Entwurf „Packliste neu“ mit Sortierung freigegeben)

## Purpose

Rückmeldung des Product Owners an einer echten Reise (8.11.2026): Kategorien lassen sich nicht ausblenden, „Am Körper“/„Rucksack“
stehen als Kategorien neben Kleidung, die Ansicht Packen ist zu „fluffig“ und „… packt“ steht an jeder Zeile. Entscheidungen in #431.

## Source

- **Files:** `engine/vorlage.html` (`packTabelle`, `packGruppe`, `gegenstandZeile`, `ansichtPackliste`, `packSumme`, neu `packAufteilung`,
  `packSortKopf`, `packKategorienWahl`), `engine/packliste.py` (`_bauen`, `packstand_zeilen`), `engine/routen.py` (Felder einer Art),
  `engine/schreiben.py` (`art_definieren`), `engine/konnektor.py` (Schema `art_definieren`, `packliste_text`), `engine/schnittstelle.py`,
  `engine/texte_de.py`, `engine/texte_en.py`, Beispielreise (`plan/arten.yaml`, `plan/packliste.yaml`), `docs/design.md`, ADR-0010.

## Verhalten

**V1 Summe aufteilen (Planen).** Über den Tabellen steht die Wahl „Summe aufteilen nach“ mit allen Merkmalen vom Typ `auswahl` der
sichtbaren Kategorien und „nicht aufteilen“. Vorgabe ist das erste Auswahl-Merkmal; die Wahl merkt sich das Gerät. Unter der
Gesamtsumme steht je Wert (in der Reihenfolge der Werte, „ohne Angabe“ zuletzt) die Summe der summierten Merkmale. Die Software kennt
kein Merkmal „Getragen“, nur Typ `auswahl` und Rolle `summe`. Ohne summiertes Merkmal oder ohne Auswahl-Merkmal fehlt die Wahl.

**V2 Sortieren (Planen).** Jede Spaltenüberschrift der Tabellen ist ein Knopf: erster Tipp aufsteigend, zweiter absteigend, dritter
ursprüngliche Reihenfolge. `aria-sort` am Kopf, Pfeil als Zeichen. Zahlen und Geld nach Betrag, Auswahl in der Reihenfolge der Werte,
Text alphabetisch; leere Werte stehen immer unten. Die Wahl gilt für alle Tabellen und merkt sich das Gerät.

**V3 Nur meins (Packen).** Umschalter „Nur meins“ / „Alle“ (Vorgabe nur meins, auf dem Gerät gemerkt), sobald der Name bekannt ist und
ein Gegenstand eine packende Person hat. Nur meins zeigt Gegenstände ohne `wer` und mit `wer` = ich, darunter der Hinweis, wie viele
Sachen anderer unter „Alle“ stehen. „Alle“ zeigt die Sachen der anderen mit ihrem Namen als kleines Etikett, ohne Haken.

**V4 Kompakte Zeile (Packen).** Haken, Titel, daneben klein die Werte der summierten Merkmale und als Etikett die Werte der
Auswahl-Merkmale mit Stufe `angeboten` (zusätzlich; so wird z. B. „Handgepäck“ einer Reise mit Flug sichtbar), außer dem Merkmal, nach dem
gruppiert wird. Kein „… packt“. Notiz und Bezug („gehört zu“) erscheinen erst nach Antippen des Titels (`aria-expanded`); der Titel
zeigt „· Notiz“, wenn es etwas aufzuklappen gibt. Zustands-Etiketten (wird nachgereicht, ungeprüft, Option verworfen) bleiben.
„… packt“ bleibt als Spalte in Planen.

**V5 Ausblenden für die Reise.** Eine Art mit Grundform `gegenstand` kann `ausgeblendet: true` tragen (nur diese Grundform, sonst
Baufehler). Organisator:innen setzen und lösen es mit `art_definieren` / `kind_define` (`ausgeblendet` / `hidden`); Mitwirkende
schlagen es vor (wie jede Änderung an Arten). Ausgeblendete Kategorien fehlen in Planen, Packen, den Summen der ganzen Liste, im
Packstand und in „Mitnehmen“; nichts wird gelöscht. Planen nennt sie in einer Zeile „Für die Reise ausgeblendet: Name (n)“ mit dem
Hinweis, wie man sie wieder einblendet. Der Konnektor zeigt sie weiter, markiert als ausgeblendet. Kein Formatwechsel: das Feld ist
freiwillig, `neu.py nachziehen` bleibt unverändert.

**V6 Ausblenden je Person (Packen).** Zeile „Für mich zeigen:“ mit einem Knopf je sichtbarer Kategorie (`aria-pressed`); eine
abgewählte Kategorie fehlt beim Packen auf diesem Gerät (gemerkt), ohne Server. Der Fortschritt zählt, was gezeigt wird.

**V7 Beispielreise.** Das bisherige Merkmal `raum` (am Körper, Tagesrucksack, Rucksack) heißt jetzt `getragen` („Getragen“); neu ist
`raum` = Ort zu Hause (Flur, Schlafzimmer, Bad, Küche, Keller). Neue Kategorie „Fotoausrüstung“ (ausgeblendet) mit der Kamera,
Merkmal „Im Zug“ (Stufe angeboten, Wert „griffbereit“) an der Trinkflasche, Karl packt Stirnlampe und Ladegerät. Alles erfunden.

## Tests

- `test_packliste.py`: Bau mit `ausgeblendet` (Kategorie markiert, Gesamtsumme ohne sie, Packstand ohne sie, Fehler bei anderer
  Grundform), `art_definieren` setzt und löst `ausgeblendet` und lehnt es für andere Grundformen ab, Konnektor-Text markiert die
  Kategorie, englischer Name `hidden`.
- `seiten_packliste.mjs` (Chromium und WebKit): Aufteilung je Wert, Sortieren auf/ab/zurück mit `aria-sort` und nach Neuladen,
  Hinweis auf Ausgeblendetes, Nur meins / Alle, kompakte Zeile ohne „packt“, Notiz auf Antippen, Etikett „griffbereit“, Kategorie
  für mich abwählen, Abhaken wie bisher, keine Überbreite am Handy.
