# Neue Reise anlegen (Paket H)

Eine neue Reise entsteht im Gespräch in der Claude-App. Niemand legt Dateien von Hand an, und Claude Code schreibt keine Reiseinhalte (ADR-0001, Präzisierung 3).

- **In der Claude-App** (der einzige Weg für Reisen und ihre Inhalte): Über den Konnektor „Frieda“ (Konto mit E-Mail-Adresse, ADR-0005; der frühere Konto-Link „Frieda – meine Reisen“ ist der Übergang, `docs/konnektor.md`) nutzt man das Werkzeug `trip_create` (`reise_anlegen`) mit Titel, Zeitraum, Ziel, Sprache, Personen und einer Notiz zu dem, was schon bekannt ist. Der Schreibweg legt die Reise sofort an, der Betrieb schaltet sie frei, verknüpft sie mit dem Konto und lädt die übrigen Personen per Mail ein. Ein Konto ohne das Recht, Reisen anzulegen, hat statt dessen `trip_create_request` (`reisen_anlegen_anfragen`, `docs/konten.md`).
- **Erste Reise einer Instanz (Betreiber):** Solange eine Instanz keine Reise hat, laufen ihre Dienste noch nicht (`deploy.sh` braucht eine Reise, der Konnektor meldet sich erst mit einer freigeschalteten Reise gesund), und `trip_create` steht nicht zur Verfügung. Diese eine Reise legt der Betreiber mit `engine/neu.py reise` an: nur Titel, Zeitraum, Ziel, Sprache und Personen, kein Inhalt (`docs/betrieb.md`, Neue Instanz einrichten, Schritt 7). Alles Weitere entsteht danach in der Claude-App.

In beiden Fällen steht die Reise danach im Status `idee` und baut sofort: mit Eckdaten, Wissen, Wünschen und einer ersten offenen Frage.

## Was das Gespräch klärt

| Angabe | Pflicht | Hinweis |
|---|---|---|
| Titel | ja | kurz, z. B. „Winterwoche im Allgäu“; daraus und aus dem Jahr wird der Ordnername (`reise_pfad`) |
| Zeitraum | ja | erster und letzter Tag; steht in `reise.yaml` unter `zeitraum`, schon bevor es einen Plan gibt |
| Ziel | nein | Ort oder Gegend; steht in `reise.yaml` unter `ziel` und erscheint in den Eckdaten und im Untertitel |
| Sprache | nein | `de` oder `en` (weitere, sobald es eine Sprachdatei gibt); Vorgabe ist die Sprache des Kontos, beim Übergangs-Link die des Zugangs, bei `neu.py reise` Englisch. Die Seite startet in dieser Sprache, Kalender, Wächter-Meldungen und alles, was die Software in Dateien der Reise schreibt, folgen ihr. Der Inhalt der Reise bleibt in der Sprache, in der er geschrieben ist (ADR-0006). Später änderbar mit `setting_set` (`einstellung_setzen`, Parameter `language`). |
| Personen | ja | je Person Vorname, Rolle (`gast`, `mitwirkend`, `organisator`), ob sie mitreist, und die E-Mail-Adresse für die Einladung (nur in der App; Adressen kommen nie ins Repo); wer anlegt, ist Organisator:in |
| Bekanntes | nein | Ideen, schon Gebuchtes, Quellen; in eigenen Worten mit Herkunft |

Claude fragt nur nach Lücken und lässt vor dem Anlegen bestätigen, was genau angelegt wird.

## Vorlage

`engine/reisevorlage/` enthält, was jede Reise braucht. `neu.py` (für `trip_create` und `neu.py reise`) füllt die Platzhalter aus und schreibt `reise.yaml`, `reise.json` und `ids.yaml` selbst:

```
reise.yaml          Titel, Ziel, Ordner, Zeitraum, Status idee mit Verlauf (wann, von wem, auf welchem Weg angelegt),
                    Personen, Bausteine, Gruppen; Untertitel nur, wenn jemand einen eigenen setzt
reise.json          Zuordnung: W-01 Eckdaten (Plan, unter „eckdaten“), W-02 Überblick (Wissen), W-03 Quellen
ids.yaml            höchste vergebene Nummer je Art
offene-fragen.md    F-01: Ideen sammeln, dann über den Rahmen entscheiden
plan/plan.md        Abschnitt Eckdaten; der Plan kommt mit der Planung
plan/arten.yaml     die Arten der Reise, leer
inhalt/wissen.md    Überblick und Quellen
medien/             für Bilder, Karten, Tracks
```

Die Eckdaten (Zeitraum, Ziel, Personen, Status) stehen nur in `reise.yaml`. Der Generator stellt sie an den Anfang des Abschnitts, den `reise.json` unter `eckdaten` nennt, und baut den Untertitel aus Ziel und Zeitraum, wenn keiner gesetzt ist. So zeigen beide nach `trip_update`, `trip_status_set` oder `person_invite` den neuen Stand (#217). Was eine Person unter „Eckdaten“ in `plan/plan.md` schreibt, steht darunter. Reisen aus der früheren Vorlage (Eckdaten als Text, Untertitel als Kopie, `CLAUDE.md` und `kontext/herkunft.md`) bringt `engine/neu.py nachziehen` auf diesen Stand; die beiden Dateien nennt es nur, sie werden nicht mehr gebraucht.

Die Vorlage gibt es je Sprache (`engine/reisevorlage/de/`, `engine/reisevorlage/en/`); `neu.py` nimmt die der Reise (`sprache`), fehlt der Ordner einer Sprache, die englische. Überschriften, Spaltenköpfe der offenen Fragen, Monatsnamen und Rollenwörter folgen der Sprache der Reise; die Seite erkennt die Wörter aller Sprachen des Katalogs (`inhalt.*` in `engine/texte_<sprache>.py`), unabhängig von der Hülle.

Eingeschaltet sind `rueckmeldungen`, `fragen`, `aufgaben`, `wuensche` und `waechter` (seit 11.11.2026, #517; er arbeitet erst ab Status `fest`). `varianten` und `karte` schaltet ein:e Organisator:in zu, wenn die Planung beginnt. Tagesseiten hat jede Reise von Anfang an, sobald sie Tage hat (#214); der frühere Baustein `tagesseiten` ist kein Schalter mehr. Ein Routenmodell (`plan/routen.yaml`, Aufbau in `engine/routen.py` und in der Beispielreise) kommt mit der Planung dazu: Start und Ende, Orte, Strecken, Unterkünfte, Wahlstellen. Dafür wird in `reise.json` der Eintrag `routen` ergänzt. Dazu gehört `plan/arten.yaml`: die Arten der Reise (Hotel, Hütte, Zugfahrt, Reiseteil …) mit ihren Merkmalen, entwickelt im Gespräch (`docs/ontologie.md`; Anschauung in der Beispielreise). Die Vorlage legt sie leer an (siehe Liste oben).

## Die ersten Schritte im Gespräch

Nach dem Anlegen füllt sich die Reise im Gespräch, Schritt für Schritt und ohne Datei von Hand. Jeder Schritt ist ein Werkzeug des Konnektors (`docs/konnektor.md`); der Schreibweg prüft ihn, schreibt ihn in die Reise und baut sie (`engine/tests/test_neu.py`, `test_reise_aus_der_vorlage_im_gespraech_fuellen`). Eine sinnvolle Folge:

1. **Arten** der Reise klären (`kind_define`): Was für Unterkünfte und Strecken gibt es, etwa Hotel (Grundform Aufenthalt) und Zugfahrt (Bewegung), und was muss zu jeder bekannt sein (`attribute_define`, `docs/ontologie.md`).
2. **Orte, Unterkünfte, Strecken** anlegen (`item_create`), jeweils mit Herkunft. Orte der An- und Abreise außerhalb der Reisegegend mit `outside`.
3. **Start und Ende** des Plans setzen (`start_end_set`), dann die **Tage** (`day_create`) mit Nacht und Strecken. `plan/routen.yaml` entsteht schon mit dem ersten `item_create`; dabei kommen in `reise.json` der Eintrag `routen` und die Abschnitte Tagesplan und Unterkünfte dazu.
4. **Wissen** aus Quellen schreiben (`knowledge_write`, siehe unten), **Fragen** sammeln (`question_create`).
5. Sobald die Planung beginnt: Status `planung` (`trip_status_set`) und die Bausteine `varianten` und `karte` dazuschalten (`setting_set`); Alternativen mit `choice_create` und `option_create`.

## Quellen übernehmen

Bücher, Fotos von Buchseiten, PDFs und Links werden zu Wissensabschnitten, immer in der Claude-App: Claude liest die Quelle (Foto, PDF, Link im Chat) und schreibt mit `knowledge_write` (`wissen_schreiben`) einen neuen Abschnitt oder einen Absatz unter einem vorhandenen. Die W-ID vergibt der Dienst, er trägt den Abschnitt in `reise.json` ein und baut die Reise.

- Text in eigenen Worten, nie abgeschrieben. Die Herkunft (`source`) ist Pflicht und steht am Absatz: Buch mit Seite, Link mit Lesedatum, Gespräch. Annahmen sind markiert. Veränderliches wie Öffnungszeiten und Preise bekommt ein Prüfdatum.
- Die Quelle selbst kommt in den Abschnitt „Quellen“ (W-03).
- Originale wie Fotos und PDFs bleiben außerhalb des Repos.

Texte sind Markdown. Eigenes HTML lehnt der Generator ab (`docs/design.md`, Reisetexte).

## IDs

IDs werden nie neu vergeben. Der Schreibweg vergibt sie (`neu.naechste_id`, Arten W, F, O, U, A, E, T, V, B) und vermerkt jede Nummer sofort in `ids.yaml`. Die Nummer liegt über der Marke und über jeder Nummer, die irgendwo in der Reise steht, auch im Verlauf von Verworfenem. Ein gelöschter Abschnitt gibt seine Nummer deshalb nicht frei. Für Reisen von vor Paket H entsteht `ids.yaml` beim ersten Aufruf. Führt eine Reise in `ids.yaml` alle IDs als Liste je Art (`ids:`), kommt die neue ID dort dazu; Liste und Kommentare bleiben erhalten.

## Prüfung vor dem Bau

Der Schreibweg prüft jede Änderung, bevor er sie schreibt. Für den Betreiber sagt `engine/neu.py pruefen <reise>` in einfachen Worten, was zu beheben ist, mit Zeile und Spalte bei kaputtem YAML oder JSON. Es meldet auch Dateien, die `reise.json` nennt, die es aber nicht gibt, und alle Fehler des Generators. Ohne Befund: „In Ordnung: … baut ohne Fehler.“

## Freischalten im Betrieb

Damit die Reise erreichbar ist, braucht der Betrieb drei Dinge: die veröffentlichte Seite unter einem geheimen Link, eine Ablage für Rückmeldungen und die Verknüpfung der Personen mit ihrem Konto (Einladung per Mail, ADR-0005). Links je Person für die Claude-App gibt es nicht mehr (#421). Den Link zur Seite trägt er in `seiten.json` im Ordner des Konnektors ein, damit `meine_reisen` ihn zeigt. Die Anfrage aus der App bleibt in `<konten>/neu/` als Beleg (seit 29.10.2026, ADR-0001 O-3, legt der Schreibweg die Reise sofort an: `engine/schreiben.py reise_anlegen`); Sobald die Seite online ist, schaltet `betrieb/zustellen.py` (aus `veroeffentlichen.sh`) die Reise frei, verknüpft sie mit dem Konto der Person, die sie angelegt hat, lädt die übrigen per Mail ein und legt die Meldung „neue Reise“ an (`rueckmeldungen.meldung_anlegen`). Auf dem eigenen Server geschieht das ohne Handarbeit mit `betrieb/` (`docs/betrieb.md`, Neue Reise freischalten). Den Konnektor „Frieda“ trägt jede Person einmal selbst in der Claude-App ein (Einstellungen → Konnektoren → Eigenen Konnektor hinzufügen, URL `<FR_BASIS>/mcp`, dann anmelden mit der E-Mail-Adresse). Das kann kein Server für sie tun. Danach erscheint jede neue Reise der Person dort von selbst (`my_trips`).
