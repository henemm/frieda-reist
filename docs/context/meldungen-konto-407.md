# Kontext: „Meldungen an dich“ auf Mein Konto (#407)

Workflow: `meldungen-konto-407`. Spec: `docs/specs/oberflaeche/meldungen-konto-407.md`. Mockups: `docs/artifacts/meldungen-konto-407/`.

Anlass: Ein Bildschirmfoto des Product Owners von Mein Konto am Handy (8.11.2026). Die Liste „Meldungen an dich“ besteht
dort fast nur aus Meldungen „Deine neue Reise … ist angelegt“, jede mit einer langen Adresse als Rohtext. Die echten
Inhalte des Fotos gehören nicht hierher; die Befunde unten sind mit den Beispielreisen nachgestellt
(`docs/artifacts/meldungen-konto-407/mockup.html`, Rahmen „Heute“).

## Wie es heute gebaut ist

| Stelle | Datei | Was sie tut |
|---|---|---|
| Anlegen | `rueckmeldungen.meldung_anlegen` | hängt eine Zeile an `meldungen.jsonl` der Reise (oder der Ablage `_neu` für Meldungen ohne Reise): `id`, `erstellt`, `an` (Namen), `art`, `ziel`, `text`, optional `schluessel`, `bezug`, `status_bei` |
| Wer legt an | `waechter.py` (`erinnerung`, `status`, `pruefung`, `betrieb`), `konnektor.py` (`konflikt`, `technik`), `betrieb/zustellen.py` (`neue_reise`), `anmeldung.betreiber_melden` (`anfrage_reisen`, Warteliste) | Der Text wird beim Anlegen fertig formuliert, in der Sprache der Reise oder der Vorgabe, mit Adressen darin |
| Was gilt | `rueckmeldungen.meldungen_aktuell` | 14 Tage (Konflikte immer), Erinnerungen zu erledigten Aufgaben fallen weg, Statusmeldungen nach dem Wechsel, Wächter-Meldungen ohne Baustein `waechter` |
| Eine Quelle | `rueckmeldungen.meldungen_des_kontos` | Meldungen ohne Reise (Name des Kontos) und je Mitgliedschaft die der Person; gibt nur `reise`, `id`, `erstellt`, `text`, `art` weiter |
| Mein Konto | `anmeldung.meldungen_abschnitt` | je Meldung eine Zeile: klein „Datum · Reise“, darunter der Text; mit Reise ein Link auf die Seite der Reise, ohne Reise kein Link |
| Reiseseite | `vorlage.html`, `fuerDich` | Hinweis „Für dich“ mit den neuesten drei, „Gelesen“ merkt sich der Browser (`localStorage`) |
| Push | `push.py` | nimmt `bezug` (AG-…) oder `ziel` als Sprungmarke: Tippen öffnet die Stelle |
| Konnektor | `konnektor.meldung_zeile`, `meine_reisen` | listet dieselben Meldungen als Text |

## Befunde

1. **Kein Link bei neuen Reisen.** `zustellen.py` legt die Meldung ohne Reise an (Ablage `_neu`), darum ist `reise` leer
   und die Zeile hat keinen Link. Die Reise steht aber in `ziel` (Ordner), und das Konto ist zu diesem Zeitpunkt schon
   Mitglied. Der Link wäre da, er wird nur nicht genutzt.
2. **Rohe Adressen im Text.** Die Seitenadresse samt geheimem Hash steht im Text. Sie bricht am Handy mitten im Hash um
   (`overflow-wrap:anywhere`) und macht die Zeile drei- bis viermal so hoch wie nötig. Antippen geht nicht.
3. **Werkzeugnamen auf der Webseite.** „… steht in meine_reisen“ ist für die Claude-App geschrieben. Auf Mein Konto
   heißt der Abschnitt „Meine Reisen“, und die Reise steht direkt darunter.
4. **Festgeschriebener Text.** Sprache und Adresse gelten so, wie sie beim Anlegen waren. Wechselt die Instanz ihre
   Adresse (auf dem Foto zeigt eine ältere Meldung auf eine andere Domain als die jüngeren) oder das Konto seine
   Sprache, stimmt die Meldung nicht mehr.
5. **Kein gemeinsamer Lesestand.** Die Reiseseite merkt „Gelesen“ je Browser, Mein Konto kennt kein Gelesen, Push und
   Konnektor ebenso wenig. Wer am Handy „Gelesen“ tippt, sieht dieselbe Meldung am Rechner wieder, und auf Mein Konto
   steht sie 14 Tage lang unverändert oben.
6. **Alle Arten sehen gleich aus.** Ein Konflikt zweier Organisator:innen oder eine überfällige Zahlung (zu tun) steht
   genauso da wie „Reise angelegt“ (zur Kenntnis). Nichts zeigt, was neu ist.
7. **Flut möglich.** Der Wächter legt bis zu 15 Prüfmeldungen je Lauf und Reise an. Sie stünden einzeln untereinander
   und schöben alles andere aus dem Bild; „Meine Reisen“ rutscht weit nach unten.
8. **Mein Konto führt nur zur Reise, Push zur Stelle.** Push nutzt `bezug`/`ziel` als Sprungmarke (`#AG-03`, `#T-02`),
   Mein Konto nicht. Dieselbe Meldung führt je nach Kanal an verschiedene Orte.
9. **Datum ohne Bezug.** „3.11.“ ohne Uhrzeit und ohne „heute“/„gestern“; bei mehreren Meldungen desselben Tages
   unklar, was zuletzt kam.

## Rahmen

- ADR-0001: Meldungen rechnen und melden, sie ändern nichts. Arten von Meldungen sind Begriffe der Software (Wächter,
  Konflikt, Zustellen), keine Arten der Reise-Ontologie; Frage 2 ist nicht berührt.
- ADR-0003: Die Heimat der Meldungen ist Mein Konto. Die Reiseseite zeigt nur den Hinweis „Für dich“ mit Link dorthin,
  Push und Konnektor sind Kanäle.
- ADR-0006: Sichtbare Texte in `texte_<sprache>.py`; der Code kennt keine Sprache beim Namen.
- Frieda löscht nie (#145). „Gelesen“ blendet aus, löscht aber nichts.
- `meldungen.jsonl` liegt in der Ablage der Instanz, nicht in der Reise. Eine neue, zusätzliche Spalte ist kein
  Formatwechsel der Reisedaten; alte Zeilen bleiben lesbar (#250: kein Handschritt).
