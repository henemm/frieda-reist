# Context: Datenschutz, Impressum und Alpha-Hinweis (#383)

## Request Summary
Öffentliche Seiten „Datenschutz“, „Impressum“ und „Alpha-Hinweis“ als Form in der Software (Texte je Sprache, ADR-0006); die Angaben zum Betreiber kommen aus den Einstellungen der Instanz. Verlinkt von Warteliste, Anmeldung und Fußzeile der Reiseseiten. Die rechtliche Prüfung des Textes macht der Product Owner.

## Related Files
| Datei | Relevanz |
|---|---|
| `engine/anmeldung.py` | öffentliche Seiten (`ist_unsere`, `bearbeiten`), `seite`, `karte`, `fuss` (leise Zeilen unter der Karte), Warteliste-Seiten, Zeilen 208 und 568 nutzen `konto.datenschutz` |
| `engine/texte_de.py`, `engine/texte_en.py` | Textkatalog; vorhanden: `konto.datenschutz` (Kurzsatz), `warteliste.alpha`, `warteliste.voraussetzung` |
| `engine/instanz.py` | `wert(name)` liest Umgebung oder `betrieb/einstellungen.env` (nur Namen `FR_…`); hier kämen die Betreiberangaben her |
| `betrieb/einstellungen.beispiel` | dokumentiert alle Einstellungen, neue Werte gehören hier hinein |
| `betrieb/vorlagen/nginx-konnektor-orte.inc` | Pfade, die an den Dienst gehen (`/warteliste` usw.); neue Pfade brauchen eigene Orte |
| `engine/vorlage.html` Z. 978 | Fußzeile der Reiseseiten (`<footer id="fuss">`), per Skript befüllt |
| `engine/tests/test_anmeldung.py`, `test_warteliste.py`, `test_nginx.py`, `test_texte.py` | bestehende Tests; `test_nginx` prüft die Orte der Vorlagen, `test_texte` die Ausnahmelisten (nur kürzer) |
| `docs/betrieb.md` (Abschnitt „Datenschutz je Instanz“, Tabelle der Daten) | Grundlage für den Inhalt der Erklärung |
| `docs/design.md` | neue Bausteine eintragen (ADR-0002) |
| `docs/specs/betrieb/warteliste-382.md`, `docs/context/warteliste-382.md` | Vorbild für Spec und Kontext, Abgrenzung zu #381, #380 |

## Existing Patterns
- Öffentliche Seite: Funktion baut `seite(titel, karte(...), fuss(...))`, `ist_unsere` + `bearbeiten` leiten den Pfad, nginx-Ort in `nginx-konnektor-orte.inc` (Drossel nach Art der Seite).
- Sichtbare Texte nur im Katalog, beide Sprachen, nie im Code. Instanzwerte über `instanz.wert`, nichts Instanzspezifisches in der Software.
- Eine Grundform hat eine Heimat, sonst Link (ADR-0003); neue Bausteine in Kopfkommentar der Vorlage, Stile, Bausteinseite, `docs/design.md`.

## Dependencies
- Upstream: `instanz.wert` (Betreiberangaben), Textkatalog, `anmeldung.seite/karte/fuss`.
- Downstream: Warteliste- und Anmeldeseiten (Link), Fußzeile aller gebauten Reiseseiten (Vorlage, deshalb Änderung für alle Reisen, `deploy.sh` baut neu), nginx-Orte der Instanz (nach Änderung `nginx.py anwenden`, sonst 404 am Rand).

## Existing Specs
- `docs/specs/betrieb/warteliste-382.md` (Warteliste), ADR-0005 (Konten), ADR-0006 (Sprachen), ADR-0001 (Kern, Prüfstelle).

## Risks & Considerations
- **Inhalt muss zum Verhalten passen:** Die Aussagen zu Löschen und Export (#381) sind noch nicht umgesetzt; die Erklärung darf nur zusagen, was es gibt (Konto löschen ja; Warteliste und Export folgen). Sonst Lücke zwischen Text und Verhalten.
- Betreiberangaben fehlen (leer) → Impressum darf nicht leer erscheinen: entweder Seite meldet „nicht eingerichtet“ oder der Dienst weigert die Anzeige; Entscheidung in der Spec.
- Anschrift im Impressum ist persönliche Angabe: sie liegt in `einstellungen.env` des privaten Reisen-Repos, nie im öffentlichen Repo; Tests mit erfundenen Werten.
- Fußzeile der Reiseseiten ist Vorlage für alle Reisen und Sprachen; Reiseseiten liegen auf derselben Adresse wie der Konnektor, Links als Pfade ab der Wurzel möglich (wie `/anmelden`).
- Neue nginx-Orte: ohne Anwenden auf dem Server liefern die Seiten 404; Doku und `nginx.py pruefen` abdecken.
- Rechtliche Prüfung nur durch den Product Owner (Prüfpunkt im Issue bleibt offen, Issue erst danach schließen).
- Parallele Sitzung `packliste` ändert `betrieb/deploy.sh` und `docs/betrieb.md`: nach dem Vorspulen ggf. neu aufsetzen.

## Analysis

### Type
Feature (Form in der Software; Betreiberangaben und rechtliche Prüfung gehören der Instanz bzw. dem Product Owner).

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/anmeldung.py` | MODIFY | Pfade `/datenschutz`, `/impressum`, `/alpha` in `ist_unsere` und `bearbeiten` (nur GET, ohne Anmeldung); Seitenfunktion mit Bausteinen `seite`/`karte`/`fuss`; Link-Zeile (`fuss`) auf Warteliste-, Adress- und Code-Seite, Einladungsseite und Mein Konto |
| `engine/texte_de.py`, `engine/texte_en.py` | MODIFY | Texte der drei Seiten (Abschnitte je Datenart nach `docs/betrieb.md`), Linktexte, Hinweis „Betreiberangaben nicht eingerichtet“; `konto.datenschutz` verweist künftig auf die Erklärung |
| `engine/instanz.py` | MODIFY (klein) | Zugriff auf Betreiberangaben `FR_BETREIBER_NAME`, `FR_BETREIBER_ANSCHRIFT`, `FR_BETREIBER_KONTAKT` über `wert()` (Name ggf. nur dort bündeln) |
| `betrieb/einstellungen.beispiel` | MODIFY | die drei Werte dokumentiert mit erfundenen Beispielwerten |
| `betrieb/vorlagen/nginx-konnektor-orte.inc` | MODIFY | neue Orte `= /datenschutz`, `= /impressum`, `= /alpha` (Drossel Konto-Zone), sonst 404 am Rand |
| `engine/vorlage.html` (+ Kopfkommentar, Stile) | MODIFY | Fußzeile `#fuss`: Zeile mit drei Links (Pfade ab Wurzel); Text über `data-t` aus dem Katalog; Änderung gilt für alle Reisen, `deploy.sh` baut neu |
| `docs/betrieb.md`, `docs/design.md`, Bausteinseite | MODIFY | Einstellungen, nginx-Hinweis (`nginx.py anwenden`), Baustein „Rechtszeile“ (ADR-0002); Tabelle „Datenschutz je Instanz“ bleibt Quelle des Inhalts |
| `engine/tests/test_anmeldung.py` (oder neu `test_rechtliches.py`), `test_nginx.py`, `test_texte.py` | MODIFY/CREATE | Seiten je Sprache, Betreiberangaben aus Einstellungen (erfundene Werte), Leerfall, Links vorhanden, Orte in nginx |

### Scope Assessment
- Files: ca. 10 (davon 2 neue Textblöcke, 1 optional neue Testdatei)
- Estimated LoC: +350/-5 (Hauptteil Texte DE/EN)
- Risk Level: MEDIUM — Code selbst einfach (GET-Seiten nach bekanntem Muster), aber die Fußzeile der Vorlage betrifft alle Reiseseiten, und der Text darf nichts zusagen, was es nicht gibt.

### Technical Approach
1. Drei GET-Seiten im bestehenden Anmeldedienst (kein neuer Dienst, kein neues Modul, `deploy.sh`-Liste bleibt), ohne Konto lesbar, Sprache wie die übrigen Seiten (Konto bzw. Accept-Language).
2. Texte nur im Katalog, beide Sprachen; Betreiberangaben nie im Katalog, sondern aus `instanz.wert`. Platzhalter im Text werden per `tx(..., name=…)` gefüllt.
3. Datenschutztext folgt der Tabelle „Datenschutz je Instanz“ in `docs/betrieb.md`. Zusagen nur für Vorhandenes: Konto selbst löschen ja; Löschen/Export der Warteliste und Export der Reisedaten als „folgt mit #381“ formuliert, nicht zugesagt. Wenn #381 vorher fertig wird, Text anpassen.
4. Leerfall Betreiberangaben: Impressum zeigt den Hinweis „nicht eingerichtet“ und die Seite antwortet 200 (kein verstecktes Fehlverhalten); ein Betriebstest/`nginx.py pruefen`-artiger Check in `neu.py pruefen` ist nicht Teil dieses Issues. Empfehlung: kein Blockieren der Warteliste.
5. Links: leise Zeile unter der Karte (bestehender Baustein `fuss`) auf allen Anmeldeseiten und der Warteliste; in der Reiseseite eine Zeile in `#fuss`, `fussZeigen()` berücksichtigt sie (die Fußzeile ist sonst versteckt, wenn leer).
6. Kein Impressum-Text rechtlich ausformuliert „als Rat“: Text ist Entwurf, Prüfpunkt „rechtliche Prüfung durch PO“ bleibt offen, Issue wird nicht geschlossen.

### Dependencies
- Upstream: `instanz.wert`, Textkatalog, `anmeldung.seite/karte/fuss`, `docs/betrieb.md` (Inhalt).
- Downstream: Warteliste (#382), Konto (#381 Löschen/Export ändert Aussagen), Probelauf #384; Instanz: `einstellungen.env` des Reisen-Repos braucht die drei Werte, nginx-Orte müssen mit `nginx.py anwenden` auf den Server (sonst 404), Reiseseiten müssen neu gebaut werden (Fußzeile).
- Parallele Sitzung `packliste` ändert `betrieb/deploy.sh`/`docs/betrieb.md`: vor dem Vorspulen neu aufsetzen.

### ADR-0001-Messung (Kern)
Keine neue Grundform der Reise, keine KI, nichts Reisespezifisches; Betreiberangaben gehören der Instanz. Kein Widerspruch zum Kern erkennbar.

### Open Questions
- [ ] Impressum bei leeren Betreiberangaben: Hinweis „nicht eingerichtet“ (Empfehlung) oder Seite 404? — Entscheidung in der Spec.
- [ ] Soll die Fußzeile der Reiseseiten die Links immer zeigen (Empfehlung) oder nur bei Anmeldung?
- [ ] Alpha-Hinweis als eigene Seite `/alpha` (Empfehlung, verlinkbar aus Warteliste) und zusätzlich als Satz auf der Warteliste (`warteliste.alpha` bleibt)?
- [ ] Wer von den Betreiberangaben ist Pflicht: Name, Anschrift, E-Mail (Empfehlung: alle drei; Telefon nur optional)? Rechtlich entscheidet der PO.
