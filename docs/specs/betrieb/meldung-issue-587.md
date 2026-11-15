---
entity_id: meldung-issue-587
type: feature
created: 2026-11-15
updated: 2026-11-15
status: approved
workflow: meldung-issue-587
version: "1.0"
tags: [konten, konnektor, betreiber, datenschutz]
---

# Meldungen an Frieda sofort als Issue für die Entwicklung, ohne persönliche Daten (#587)

## Approval

- [x] Approved (Product Owner, 15.11.2026, Lösung im Text von #587)

## Purpose

Ein Wunsch aus der Claude-App (`report_to_frieda`, #530) lag nur in der Kontendatenbank und als Mail beim Betreiber; die
Entwicklung fand ihn nicht. Meldungen mit persönlichen Daten gehören weder ins öffentliche Software-Repo noch ins private
Reisen-Repo. Deshalb wird aus einer zweiten, von der Person freigegebenen Fassung ohne persönliche Daten sofort ein Issue.

## Umsetzung

- Neues Modul `engine/entwicklung.py` (nur Standardbibliothek, in `KN_MODULE` von `betrieb/deploy.sh`): `eingerichtet()`,
  `persoenliche_angaben(text, werte, namen)`, `issue_anlegen(titel, text, etiketten)`, `text_fuer_issue`. Der Aufruf an
  GitHub steckt in `_senden` und ist in den Tests ersetzt.
- `engine/konnektor.py`: Mit Einstellung bekommt `an_frieda_melden` das Feld `oeffentlicher_text` (`public_text`) und einen
  Satz in der Beschreibung; `angaben_des_kontos(k)` sammelt Konto-Name und -Adresse, Personen, Titel, Untertitel, Ordner,
  Orte und Unterkünfte aller Reisen des Kontos. Ein Treffer lehnt ab (`konnektor.an_frieda_melden.persoenlich`), ohne
  Zeile, ohne Zählung.
- `engine/konten.py`: `an_betreiber_melden(..., issue_anlegen=None)`; gelingt das Anlegen, ist die Zeile mit der Adresse
  abgehakt und es geht keine Mail; scheitert es, Mail wie bisher und Zeile `operator report <nr>: issue failed: …`.
  `betreiber_sprache()` wählt die Sprache für Etiketten und Fußtext.
- Ohne `FR_MELDUNGEN_REPO` und `FR_MELDUNGEN_TOKEN` ist das Werkzeug unverändert (Schema, Beschreibung, Ablauf).

## Abnahme

- Meldung in der Claude-App → Issue ohne persönliche Daten, Meldung privat abgehakt mit Verweis
  (`test_issue_wird_angelegt_und_meldung_abgehakt`, beide Beispielreisen).
- Name einer Mitreisenden, eigener Name, Reisetitel, Ordner, Ort, Unterkunft, Mail-Adresse → abgelehnt
  (`test_persoenliche_angaben_werden_abgelehnt`).
- Ohne Einstellung unverändert (`test_ohne_einstellung_unveraendert`, `test_ohne_einstellung_mail_wie_bisher`).
- Tests ohne Netz: `engine/tests/test_meldung_issue.py` ersetzt `_senden`; ein echter Aufruf macht jeden Test rot.
- Auf der Instanz: Zugangsschlüssel nach der Anleitung in #587 eintragen, eine Probe-Meldung aus der Claude-App.
