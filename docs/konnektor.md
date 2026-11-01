# Konnektor: Reisen in der Claude-App

Mit dem Konnektor lässt sich eine Reise in jedem normalen Claude-Chat nutzen (App am Handy, Desktop, claude.ai). Claude liest dabei die Reise und kann Rückmeldungen abgeben. Technisch ist es ein MCP-Server: `engine/konnektor.py` auf dem eigenen Server, neben dem Rückmeldedienst.

## Grundsätze (24.10.2026)

- **Der Konnektor schreibt direkt in die Reise** (seit 29.10.2026, ADR-0001 Paket O-3): Frieda enthält keine KI; was im Gespräch festgelegt wird, prüfen Regeln im Code (`engine/schreiben.py`, siehe „Ontologie im Gespräch“) und schreiben es sofort in das Reisen-Repo. Bis zum 29.10.2026 änderte sich der Plan nur beim Einarbeiten durch Claude Code auf dem Server (Aufträge, Rückmeldungen); dieser Weg ist abgeschaltet.
- Nutzen dürfen ihn **alle Personen der Reise** (`reise.yaml personen`). Seit 26.10.2026 gehört ein Link zu einer Person; ihre Rolle entscheidet: `gast` liest, `mitwirkend` gibt Rückmeldungen, Wünsche, Vorschläge und Aufgaben und schreibt Werte, Dinge, Optionen, Fragen und Wissen (Eingaben), `organisator` entscheidet dazu, legt Arten und Merkmale fest, setzt Status und Einstellungen und lädt ein. Alte Links mit Rolle `mitreisend` gelten als `mitwirkend`.
- **Regelfall ist das Konto** (ADR-0005, Paket J3): Die Person meldet sich im Konnektor „Frieda“ mit ihrer E-Mail-Adresse an, ein Konnektor für alle Reisen. Die Links je Reise und Person in diesem Abschnitt sind der Übergang und werden nicht mehr ausgestellt; was unten über „den Link“ steht, gilt für das Konto ebenso (die Person steht fest).
- **Ein Link pro Reise und Person** (Übergang).
- Gehört der Link zu einer Person, steht der Name fest. Bei einem Link ohne Person (nur Rolle) fragt Claude einmal nach dem Vornamen.
- **Rückmeldungen** (`rueckmeldung_geben`, `frage_beantworten`, die Formulare der Webseite) sind Eingaben: Sie liegen in der Ablage der Reise, bis eine Organisator:in sie im AI-Client prüft, mit den Schreibwerkzeugen einträgt und mit `rueckmeldung_erledigen` abschließt (Kommentar für die Seite in einfachen Worten).
- **Aufgaben** (AG-01 …) darf jede:r über die App und über die Webseite sofort anlegen, ändern und abhaken. Eine Aufgabe hängt an einer oder mehreren IDs oder an der Reise allgemein. Sie hat Titel, Zuständig, Priorität, „ab wann möglich“, Frist, Notiz, Status (offen, in Arbeit, erledigt, entfällt) und einen Verlauf. Gelöscht wird nie.

## Was Claude damit kann

| Werkzeug | Wer | Was |
|---|---|---|
| `ueberblick` | alle | Eckdaten, Tagesplan mit IDs, Wahlstellen, Inhaltsverzeichnis, Meldungen an die Person (Wächter und Erinnerer, wenn der Baustein `waechter` an ist); ab Status `fest` die Mahnungen der Reise (offene Planungs-Wahlstellen, ungeprüfte veränderliche Angaben, fehlende Lage), seit 29.10.2026 nur noch hier und nicht mehr als Kasten auf der Seite |
| `zeige` | alle | Volltext zu einer ID (T-, E-, O-, U-, A-, B- mit Belegen, V-, P-, F-, W-) |
| `suche` | alle | Volltextsuche |
| `offene_fragen` | alle | F-Liste mit Frist und Status |
| `varianten` | alle | Pläne und Wahlstellen mit Dafür/Dagegen und Summen |
| `rueckmeldungen` | alle | bisherige Rückmeldungen mit Status und Antwort; bei Organisator:innen auch die alten Aufträge (bis 29.10.2026, nur noch Bestand); vorn die Meldungen an die Person (Konflikte, Fristen, Statuswechsel; siehe `docs/waechter.md`) |
| `rueckmeldung_geben` | alle | landet im selben Eingang wie die Rückmeldungen von der Webseite; Art `Wunsch` für Ideen ohne feste Stelle (ziel leer), sichtbar im Reiter „Wünsche“ |
| `aufgaben` | alle | Aufgaben, Standard nur offene; Filter nach Bezug, Zuständig, Status |
| `aufgabe_anlegen` | alle | neue Aufgabe, gilt sofort |
| `aufgabe_aendern` | alle | abhaken, Status, Felder, Kommentar in den Verlauf; gilt sofort |
| `wuensche` | alle | Wunsch-Brett: Wünsche nach Spalten mit Punkten, Vorschlag, eingeplant, erlebt; Bilanz je Person (Baustein `wuensche`) |
| `wunsch_aendern` | Mitwirkende, Organisator:innen | Punkte auf eigene Wünsche, abhaken (unterwegs und danach), einplanen (nur Organisator:innen mit persönlichem Link; auf der Webseite gibt es das nicht); gilt sofort, Regeln prüft der Rückmeldedienst (siehe `docs/produkt.md`, Wunsch-Brett) |
| `kategorien` | alle | die Kartenkategorien der Reise (`plan/kategorien.yaml`): Schlüssel, Name in der Legende, Farbe, Symbol, Gruppe und die art-Wörter der Punkte; vor `kategorie_definieren` |
| `merkmale` | alle | welche Merkmale eine Alternative braucht (mit Hinweis zum Recherchieren und Nachfragen), was jede Option hat und was fehlt; zu einer Wahlstelle `V-…`, einer Strecke `E-…` oder einer Art (`art`); siehe `docs/alternativen.md` |
| `lage_eintragen` | Mitwirkende, Organisator:innen | Lage einer Unterkunft oder eines Aufenthalts ohne Nacht (`A-…`): Adresse und/oder Koordinaten („Breite, Länge“), Herkunft Pflicht, Prüfdatum (Vorgabe heute); ADR-0004 |
| `ding_anlegen`, `ding_aendern` | Mitwirkende, Organisator:innen | Unterkunft, Aufenthalt ohne Nacht (`A-…`: Besichtigung, Essen, Besuch mit `zeit`), Strecke oder Ort anlegen (neue ID aus `ids.yaml`, Herkunft Pflicht, Merkmale gleich mit) und Felder ändern, auch den Buchungsstand `buchung` (die Art nur Organisator:innen); schreibt sofort nach `plan/routen.yaml`. Ein Aufenthalt kommt mit `tag_aendern` (`aufenthalte`) an seinen Tag |
| `option_anlegen`, `wahlstelle_anlegen` | Mitwirkende, Organisator:innen | Alternative als Option an eine Wahlstelle hängen (Status `vorgeschlagen`, Verlauf mit Person und Datum) oder eine neue Wahlstelle mit Optionen anlegen (`an` Tagen, Strecken, Unterkünften, Orten, Abschnitten; `planung` bekommt eine offene Frage mit); ersetzt `alternative_vorschlagen` |
| `frage_anlegen` | Mitwirkende, Organisator:innen | offene Frage F-… in `offene-fragen.md` anlegen (Baustein `fragen`) |
| `buchung_anlegen`, `buchung_aendern` | Mitwirkende, Organisator:innen | Buchung als eigenes Ding `B-…` (#76, 29.10.2026): für welche Unterkunft, welchen Aufenthalt oder welche Strecke (`fuer`), Status (angefragt, gebucht, storniert), Nummer, Anbieter, Preis, bezahlt, Frist mit `frist_was`, Stornoregel mit `storno_bis`, Herkunft (Pflicht); ändern mit Verlaufseintrag (Person, Datum, Grund), leerer Text entfernt ein Feld; Mitwirkende ändern nur eigene Buchungen (`wer`), Organisator:innen alle, Stornieren braucht einen Grund (Product Owner 29.10.2026). `zeige B-…` zeigt alles samt Belegen, `ueberblick` zählt und nennt die nächsten Fristen. Seit Issue #135 dazu: `personen` (die Reisenden dieser Buchung mit Angabe je Person, etwa Sitzplatz, Gepäck, Vielfliegernummer; nur Namen aus `reise.yaml`), `preise` (bei mehreren Dingen in `fuer` der Preis je Ding), `ab` mit `ab_was` (ab wann etwas geht, etwa der Online-Check-in; der Wächter erinnert am Tag). Seit Issue #166: `zahlung` (Zahlstand `offen`, `angezahlt`, `bezahlt`, `vor_ort`, `inklusive`, `erstattet`; englisch `open`, `deposit`, `paid`, `on_site`, `included`, `refunded`, gespeichert wird der deutsche Wert; `erstattet` nur bei `storniert`; Einzelheiten in `bezahlt`) und `merkmale` (Merkmale der Buchung, die die Art ihrer Dinge festlegt; `merkmale art` zeigt sie). Den **Beleg** gibt die Person beim Anlegen gleich mit (`beleg_text` als Abschrift oder `beleg_base64` mit `beleg_dateiname`; ein Schritt, der Schreibweg nennt die neue B-ID, der Konnektor legt den Beleg sofort in der Ablage ab), nachträglich mit `beleg_anlegen` oder angemeldet auf der Reiseseite; er liegt in der Ablage, nie im Repo, und ist nur für sie und Organisator:innen sichtbar, bis eine Organisator:in ihn freigibt |
| `beleg_anlegen` | Mitwirkende, Organisator:innen | Beleg nachträglich an eine Buchung `B-…` hängen, ohne die Reiseseite (Issue #135): als Abschrift (`text`, der Inhalt der Bestätigung oder Mail wörtlich, abgelegt als `.txt`) oder als Datei (`daten_base64`: PDF, JPEG, PNG, WebP, HEIC, höchstens 10 MB), mit `dateiname`. Der Konnektor schickt ihn an den Rückmeldedienst, den einzigen Schreiber der Ablage (`POST /<reise>/belege/<B-id>` mit Dienst-Header). Kennt die veröffentlichte Seite die Buchung noch nicht, fragt der Konnektor den Schreibweg (`GET /<reise>/buchung/<B-id>`, liest `origin/main`) und schickt dem Rückmeldedienst `X-Frieda-Buchung: im-repo`; so geht der Beleg sofort nach dem Anlegen. Sichtbar für die Person und Organisator:innen, freigeben geht auf der Reiseseite |
| `art_definieren` | Organisator:innen schreiben, Mitwirkende schlagen vor | eine Art der Reise anlegen oder ändern (Bezeichnung, Grundform, Farbe, Beschreibung, summiert); schreibt über den Schreibweg direkt in `plan/arten.yaml` (siehe „Ontologie im Gespräch“); nur bei Instanzen mit Schreibweg |
| `kategorie_definieren` | Organisator:innen schreiben, Mitwirkende schlagen vor | eine Kategorie der Kartenpunkte anlegen oder ändern (Schlüssel, Bezeichnung, Gruppe `punkt` oder `wissen`, Farbe, Symbol, nummeriert) und den Zusatz zu einem `art`-Wort der Punkte (Name, Symbol, Hinweis, Umriss); schreibt direkt in `plan/kategorien.yaml` (#128, O-7); ohne Kategorie lässt ein Punkt den Bau scheitern; nur bei Instanzen mit Schreibweg |
| `merkmal_definieren` | Organisator:innen schreiben, Mitwirkende schlagen vor | ein Merkmal einer Art anlegen oder ändern: umbenennen, Typ und Werte, veränderlich, Stufe (für die Person „nötig“, „gut zu wissen“, „zusätzlich“; Schlüssel `pflicht`, `empfohlen`, `angeboten`, beides wird angenommen; `aus` schaltet ab und wird nicht genannt), Hilfe, Frage, weitere Namen, ob der Wert nach der Buchung sichtbar bleibt (`nach_buchung`, z. B. Charakter; 31.10.2026); warnt vor einem ähnlichen vorhandenen Merkmal (`trotzdem` übergeht das). Mit `fuer: buchung` ein Merkmal der Buchungen dieser Art (#166: was erst durch das Buchen entsteht, etwa Ticketart; nur Name, Typ, Werte, Einheit, Hilfe, Frage) |
| `wert_eintragen` | Mitwirkende, Organisator:innen | einen Wert eines Merkmals an `U-…`, `E-…` oder einer Option `V-01.a` eintragen (auch mehrere je Datum mit `gilt`); schreibt sofort in `plan/routen.yaml`, ersetzt den Wert für dieselben Tage, der alte bleibt im Verlauf; Herkunft (`quelle`) ist Pflicht, bei veränderlichen Merkmalen auch `geprueft` |
| `reise_status_setzen`, `einstellung_setzen` | Organisator:innen | Status der Reise mit Grund und Verlauf; Bausteine, Spielregeln und Sprache der Reise (`sprache`); schreibt sofort nach `reise.yaml` (ersetzt `auftrag_geben`) |
| `entscheiden` | Organisator:innen | Option wählen, verwerfen oder ersetzen: sofort geprüft und mit Datum, Person und Grund in den Plan geschrieben (Paket C; seit O-3 direkt) |
| `tag_aendern` | Organisator:innen | Titel, Text, Nacht, Strecken, Wahlstellen und Aufenthalte ohne Nacht (`aufenthalte`) eines Tags ändern; schreibt sofort |
| `frage_beantworten` | Mitwirkende | Antwort auf eine offene Frage (F-…); hängt an der Frage, die Entscheidung bleibt bei der Organisator:in (Paket C) |
| `frage_schliessen` | Organisator:innen | Frage als geklärt oder entfallen eintragen, mit Ergebnis; schreibt sofort nach `offene-fragen.md` |
| `wissen_schreiben` | Mitwirkende, Organisator:innen | Wissen in eigenen Worten mit Herkunft: neuer W-Abschnitt (ID aus `ids.yaml`, Zuordnung in `reise.json`) oder Absatz unter einem vorhandenen; schreibt sofort |
| `rueckmeldung_erledigen` | Organisator:innen | Rückmeldung oder Auftrag abschließen (uebernommen, verworfen, rueckfrage) mit Kommentar für die Seite; über den Rückmeldedienst, gilt sofort |
| `tag_anlegen` | Organisator:innen | neuen Tag anlegen (T-…) und in die Route stellen (nach, vor, am Ende oder ohne Route für eine Variante), mit Titel, Nacht, Strecken, Aufenthalten; schreibt sofort (Abgleich 29.10.2026) |
| `termin_setzen` | Organisator:innen | festen Termin der Reise anlegen (Datum, Titel, Ort, Herkunft Pflicht), ändern oder mit Grund entfernen (`fixpunkte` in `plan/routen.yaml`) |
| `wahlstelle_aendern` | Organisator:innen | Felder einer Wahlstelle: Titel, Text, `wann`, `art` (Art der Dinge), `an`, Frage, Stufen je Merkmal nur für diese Wahlstelle |
| `option_aendern` | Mitwirkende, Organisator:innen | Felder einer Option (Titel, Text, Dafür, Dagegen, Regeln, Auslöser, Inhalt, Herkunft) und favorisieren mit Grund (Vorschlag, keine Entscheidung; gewählt nur mit `entscheiden`) |
| `wissen_aendern` | Mitwirkende, Organisator:innen | einen W-Abschnitt berichtigen: Inhalt ersetzen (Herkunft Pflicht) oder umbenennen (ID bleibt), mit Grund; der Probebau lehnt ab, wenn andere Dateien Unterabschnitte oder Fußnoten daraus brauchen |
| `lesetext_schreiben` | Mitwirkende, Organisator:innen | den Lesetext einer Etappe (Abschnitt Zusammenfassung, „Der Weg“) nach der Gliederung ihrer Art schreiben oder ersetzen, Herkunft Pflicht; fremde Stichworte lehnt der Schreibweg ab |
| `reise_aendern` | Organisator:innen | Eckdaten: Titel, Untertitel, Kurzname, Zeitraum, mit Grund; Verlauf in `reise.yaml` unter `verlauf`; Start und Ende des Plans setzt `start_ende_setzen` |
| `start_ende_setzen` | Organisator:innen | Start und Ende des Plans (`start`, `ende` in `plan/routen.yaml`): Datum und Ort, leerer Text entfernt das Ende; mit Grund, Verlauf in `reise.yaml`; ein neues Startdatum verschiebt die Daten aller Tage |
| `plan_anlegen`, `plan_aendern` | Organisator:innen | benannte Pläne P-… (feste Kombination von Optionen, „Varianten“): Kurzname, Titel, Farbe, Auswahl, Dafür, Dagegen; anlegen mit Herkunft |
| `merkmal_zusammenfuehren` | Organisator:innen | zwei Merkmale einer Art zusammenführen: Werte umhängen, das alte entfällt und wird weiterer Name des bleibenden; mit Grund |
| `arten_uebernehmen` | Organisator:innen | Arten einer anderen Reise derselben Person als Kopie übernehmen (nur fehlende, nur auf ausdrückliche Nachfrage; Product Owner 28.10.2026) |
| `wunsch_vorschlagen` | Mitwirkende, Organisator:innen | nach dem Prüfen eines Wunschs den Vorschlag eintragen (`plan/wuensche.yaml`: Stellen, Notiz mit Herkunft, Option); das Brett zeigt ihn unter „geprüft“ |
| `person_einladen` | je nach `regeln.einladen` (Vorgabe Organisator:innen) | legt eine Person mit Rolle an und stellt ihren persönlichen Link aus (Paket C); seit O-3 steht sie sofort in `reise.yaml` (`person_schreiben`), `person_entfernen` macht sie zum Gast, der nicht mitreist (niemand wird gestrichen) |

Schreibende Werkzeuge (`rueckmeldung_geben`, `frage_beantworten`, `aufgabe_*`, `wunsch_aendern`, die Werkzeuge des Schreibwegs) sehen nur Mitwirkende und Organisator:innen; `entscheiden`, `reise_status_setzen` und `einstellung_setzen` nur Organisator:innen, `person_einladen` wer `regeln.einladen` erreicht. Welche Werkzeuge es gibt und was sie dürfen, hängt zusätzlich vom Status der Reise und den eingeschalteten Bausteinen ab (Paket B, `docs/produkt.md`): `danach` sperrt neue Wünsche, Punkte und Alternativen (Abhaken geht noch), `archiv` alles Schreiben außer dem Status der Reise; ein ausgeschalteter Baustein nimmt seine Werkzeuge mit (`aufgaben`, `varianten`, `offene_fragen`, `rueckmeldungen`, `wuensche`). Geprüft wird bei jedem Aufruf, nicht nur in der Liste; der Dienst nennt den Grund.

**Hinweise (#142):** Erzeugt ein Eintrag über den Schreibweg eine neue Warnung des Baus, lehnt der Dienst ihn nicht ab: Der Eintrag gilt, und die Antwort nennt die neuen Warnungen unter `hinweise` (höchstens zehn Zeilen „Bezug: Text“, dann „und N weitere“), die der Konnektor der Person anzeigt. Schon vorher bestehende Warnungen erscheinen nicht noch einmal. Warnungen sperren auch das Veröffentlichen nie (`docs/betrieb.md`, „Was sperrt“).

Änderungsaufträge (`auftrag_geben`, Ablage `auftraege.jsonl`) gibt es seit 29.10.2026 nicht mehr: Alles, was früher ein Auftrag war, schreibt der Konnektor direkt (siehe „Ontologie im Gespräch“). Alte Aufträge bleiben unter `rueckmeldungen` lesbar und lassen sich mit `rueckmeldung_erledigen` abschließen.

Gelesen wird die veröffentlichte Seite (`<seiten>/<reise>/daten.json`). Der Konnektor zeigt also denselben Stand wie die Webseite nach dem letzten Veröffentlichen.

`zeige E-…` nennt auch die Gliederung des Lesetexts der Art (`plan/arten.yaml` `lesetext`, `docs/ontologie.md`), damit der AI-Client den Text am Anfang der Etappe in diesem Aufbau schreibt. `zeige` zu einer ID listet auch die Aufgaben, die daran hängen. `zeige AG-…` zeigt eine Aufgabe mit Verlauf, `ueberblick` die Zahl der offenen und die überfälligen Aufgaben.

Aufgaben liegen live in `<ablage>/<reise>/aufgaben.json`, nicht im Repo. Der Rückmeldedienst ist ihr einziger Schreiber (`GET/POST /<reise>/aufgaben`, `PATCH /<reise>/aufgaben/<AG-id>`). Der Konnektor und die Webseite schreiben beide über ihn. In Claude Code zeigt `python3 engine/rueckmeldungen.py aufgaben <reise> [--alle]` sie an.

## Entscheiden, Fragen beantworten, Einladen (Paket C, 26.10.2026)

**`entscheiden`** (nur Organisator:innen, Baustein `varianten`, nicht in `danach` und `archiv`): Eingaben sind `option` (V-01.b), `status` (`gewaehlt`, `verworfen`, `ersetzt`; bei `ersetzt` auch `ersetzt_durch`), `grund` und optional `quelle`. Nur mit persönlichem Link, denn jede Entscheidung gehört genau einer Person. Der Dienst prüft sofort und lehnt mit Begründung ab, wenn die Option oder Wahlstelle fehlt, der Status unbekannt ist, der Grund fehlt, die Option schon so entschieden ist, `ersetzt_durch` nicht zur selben Wahlstelle gehört oder dieselbe Entscheidung schon vorliegt. Hinweise, die nichts verhindern: bisher gewählte Option wird ersetzt, Wahlstelle ist danach offen, fehlende Merkmale, ungeprüfte veränderliche Angaben, Wahlstelle für unterwegs, Regeln zwischen Optionen (die gewählte setzt etwas voraus, das nicht im Plan steht, oder schließt etwas im Plan aus; die verworfene wird von einer Option im Plan vorausgesetzt; `docs/alternativen.md`). Widerspricht die Entscheidung einer anderen Organisator:in, gilt `regeln.konflikt` (Meldung an beide, offene Frage, nichts wird übernommen).

**Seit 29.10.2026 (ADR-0001, O-3 Schritt 4)** schreibt der Konnektor die Entscheidung über den Schreibweg direkt in `plan/routen.yaml`: Verlaufseintrag an der Option (Datum, Status, Person, Grund, bei `ersetzt` auch `durch`), bisher gewählte Optionen derselben Wahlstelle bekommen `ersetzt`, ebenso die übrigen noch nicht entschiedenen (Grund „nicht gewählt“, `durch` die gewählte; wird die gewählte später verworfen, sind sie wieder `vorgeschlagen`; Product Owner 31.10.2026), die Frage der Wahlstelle wird in `offene-fragen.md` als geklärt eingetragen, sobald an jeder Wahlstelle mit dieser Frage etwas gewählt ist; sonst bleibt sie offen, und die Antwort nennt, was noch zu entscheiden ist (Product Owner 29.10.2026). Verworfen ohne verbleibende Wahl öffnet sie wieder. Widerspricht die Entscheidung der einer anderen Organisator:in (`regeln.konflikt`), wird nichts geschrieben: Es entsteht eine offene Frage mit beiden Positionen, und alle beteiligten Organisator:innen bekommen eine Meldung. Die frühere Regel `regeln.entscheidungsweg` (direkt oder als Auftrag mit Prüfung durch Claude Code) ist entfallen; ohne eingerichteten Schreibweg geht Entscheiden nicht.

**`tag_aendern`** (nur Organisator:innen): Titel, Text, Nacht (`U-…`, `V-…`, `O-…` oder leer), Strecken (`E-…`, `V-…`), Wahlstellen unterwegs und Aufenthalte ohne Nacht (`aufenthalte: [A-…]`, Paket O-5) eines Tags ändern; so wird eine feste Unterkunft zur Wahl zwischen mehreren (Nacht = neue Wahlstelle). Der Generator prüft, ob der Plan aufgeht.

**`frage_beantworten`** (Mitwirkende und Organisator:innen, Bausteine `fragen` und `rueckmeldungen`): Die Antwort wird eine Rückmeldung der Art `Antwort` an die Frage und steht danach unter `zeige F-…`. Die Frage muss es geben und noch offen sein. Geklärt ist sie damit nicht: Das entscheidet ein:e Organisator:in.

**`person_einladen`** (`regeln.einladen`: `organisator` oder `mitwirkend`): Eingaben `vorname`, `rolle` (Standard `mitwirkend`), `reist`, `notiz`. Man kann höchstens die eigene Rolle vergeben. Der Dienst
1. stellt den persönlichen Link aus (`zugaenge.json`, Rechte 600) und gibt ihn dem Einladenden im Gespräch,
2. legt die Person live in `<ablage>/<reise>/einladungen.json` an, damit Rolle und Zugang sofort gelten (Konnektor und Rückmeldedienst kennen sie),
3. schreibt sie über den Schreibweg sofort nach `reise.yaml` (`personen`). Steht sie dort, gilt `reise.yaml`.

Gibt es die Person schon, bekommt sie nur einen weiteren Link; ihre Rolle ändert `person_einladen` mit anderer Rolle (nur Organisator:innen, sofort in `reise.yaml`). Einen Link zu sperren geht noch von Hand (Eintrag aus `zugaenge.json` löschen).

**Anleitung:** Beim Verbinden bekommt die KI Rolle, Reisestatus und die Grenzen der sprechenden Person (Mitwirkende:r: kann nicht entscheiden; Link ohne Person: kein Entscheiden und Einladen) und den Hinweis, dass Eingetragenes sofort gilt und die Seite es in wenigen Minuten zeigt.

**Löschwunsch (#145):** Frieda löscht nie. Sagt eine Person „lösch das“, wählt die KI nach der Anleitung (für jede Rolle) den passenden Weg, lässt kurz bestätigen, was genau und mit welchem Grund, und sagt danach in einem Satz, was geschah, dass nichts gelöscht ist und wie man es zurückholt. Eine Buchung wird storniert (`buchung_aendern`, Status `storniert` mit Grund; zurück mit Status `gebucht`). Eine Option einer Wahlstelle wird verworfen oder ersetzt (`entscheiden`, nur Organisator:innen; zurück mit `entscheiden`, Status `gewaehlt`). Eine Aufgabe entfällt (`aufgabe_aendern`, Status `entfaellt`; zurück mit Status `offen`). Eine offene Frage entfällt (`frage_schliessen`, Status `entfaellt`, nur Organisator:innen); ein Wiedereröffnen gibt es nicht, bei Bedarf wird eine neue Frage angelegt. Für Unterkünfte, Strecken, Orte, Wissen, Tage, Wahlstellen und Pläne gibt es keinen Löschweg (Ändern lässt den alten Wert im Verlauf); dasselbe gilt für Optionen, wenn Mitwirkende sprechen. Dann sagt die KI das ehrlich und bietet eine Rückmeldung an die Organisator:in an (`rueckmeldung_geben`). Die Werkzeugbeschreibungen nennen je ihren Weg, und die Antworten nach Stornieren, Verwerfen oder Ersetzen und nach `entfaellt` enden mit „Nicht gelöscht …“ und dem Rückholweg.

## Ontologie im Gespräch (ADR-0001, Paket O-3, Schritte 1 bis 6, 29.10.2026)

Welche Arten eine Reise hat (Hotel, Refugi, Ryokan, Zugfahrt, Reiseteil …) und was zu jeder Sache einer Art bekannt sein muss, legt die Reise im Gespräch fest (`docs/ontologie.md`). Dafür gibt es `art_definieren` und `merkmal_definieren`:

- **Organisator:innen** schreiben damit direkt: Der Konnektor schickt die Anfrage mit Person und Rolle an den **Schreibweg** (`engine/schreiben.py dienst`, nur auf 127.0.0.1, mit dem Dienst-Geheimnis). Der prüft mit `reise.yaml` der Reise noch einmal Rolle und Status (Aktion `ontologie`: Organisator:in, Status mit vollem Schreibrecht), die Form der Angaben (Grundform, Typ, Stufe, Werte bei `auswahl`, kein zweiter Name eines vorhandenen Merkmals), ändert `plan/arten.yaml`, baut die Reise zur Probe (der Generator prüft alles Übrige, etwa ob eingetragene Werte zu neuen Auswahlwerten passen), sichert die Änderung als Commit mit Person und Werkzeug nach `main` und stößt das Veröffentlichen an. Lehnt er ab, bleibt alles unverändert, und die Person bekommt den Grund. Die Antwort heißt dann „Eingetragen und gesichert“; die Seite und die Werkzeuge `merkmale`/`zeige` zeigen den neuen Stand nach dem Veröffentlichen (wenige Minuten). Nur mit persönlichem Link: Jede Änderung gehört einer Person.
- **Mitwirkende** schlagen damit vor: Es entsteht eine Rückmeldung der Art `Ergänzung` an die Art („Art festlegen – bezeichnung: Refugi; grundform: aufenthalt“), die Organisator:innen unter `rueckmeldungen` sehen und im Gespräch übernehmen können.
- Die Grundform einer Art lässt sich nicht ändern (neue Art anlegen); Schlüssel bleiben, nur die Bezeichnung ändert sich (IDs und Werte der Reise hängen am Schlüssel). Eine Bewegung „aus eigener Kraft“ (`summiert`) und eine Folge bekommen ihre berechneten Merkmale (Gehzeit, Länge, Höhenmeter; Tage, Gehzeit, Unterkünfte, Anschluss) beim Anlegen. Ein neues Merkmal, das einem vorhandenen ähnelt (gleicher Wortstamm, zweiter Name), wird erst mit `trotzdem` angelegt.
- Der Verlauf steht in der Geschichte des Repos (ein Commit je Änderung: Reise, Titel, Text, Person, Werkzeug, Datum). Arten einer früheren Reise derselben Person übernimmt der AI-Client nur auf ausdrückliche Nachfrage, als Kopie (Product Owner, 28.10.2026): `arten_uebernehmen` (seit 29.10.2026; der Konnektor prüft, dass die Person auf beiden Reisen dabei ist).
- **Werte** (Schritt 2, 29.10.2026): `wert_eintragen` schreibt einen Wert eines Merkmals an eine Unterkunft, Strecke oder Option (`plan/routen.yaml`, Form in `docs/alternativen.md`). Der Schreibweg nimmt die Merkmale, die der Generator an dieser Stelle kennt (Art des Dings, Ergänzungen der Wahlstelle), prüft Auswahlwerte, Zahlen und Daten und verlangt die **Herkunft** (`quelle`) jeder Angabe sowie bei veränderlichen Merkmalen das **Prüfdatum** (`geprueft`, nicht in der Zukunft); berechnete und abgeschaltete Merkmale lehnt er ab. Ein neuer Wert ersetzt den bisherigen für dieselben Tage (Einträge mit `gilt` je Datum bleiben nebeneinander), der alte steht im Commit („Preis pro Nacht „85 €“ → „95 €““). Die Datei wird mit ruamel.yaml rund geschrieben: Kommentare und Form bleiben, nur die geänderte Stelle unterscheidet sich. Mitwirkende schreiben Werte direkt (Eingaben, keine Entscheidungen); Mitwirkende ohne persönlichen Link nennen ihren Vornamen.
- **Dinge, Optionen, Wahlstellen, Fragen** (Schritt 3, 29.10.2026): `ding_anlegen` legt eine Unterkunft (Ort, Art, Herkunft, Merkmale), Strecke (von, nach, Art; dazu `ab` und `an` als Uhrzeit HH:MM am Tag der Strecke oder Zeitpunkt JJJJ-MM-TTTHH:MM+HH:MM mit Zeitzone, Issue #135; der Generator meldet, wenn die nächste Strecke des Tags abfährt, bevor diese ankommt) oder einen Ort an (`ausserhalb: true` für einen Ort der An- und Abreise außerhalb der Reisegegend, etwa den Flughafen daheim); die ID kommt aus `ids.yaml` der Reise (`neu.naechste_id`, nie neu vergeben). `ding_aendern` ändert Felder (Name, Ort, Hinweis, Quelle, Buchungslink, Frage; die Art nur Organisator:innen, weil sie bestimmt, welche Merkmale gelten), Merkmale ändert `wert_eintragen`. `option_anlegen` hängt eine Alternative an eine Wahlstelle, Status `vorgeschlagen` mit Verlauf (Datum, Person, Grund) und Herkunft; `erfordert`/`schliesst_aus` und Merkmale werden geprüft. `wahlstelle_anlegen` legt eine Wahlstelle mit Optionen an und hängt sie mit `an` an Tage, Strecken, Unterkünfte, Orte oder Abschnitte; eine Planungs-Wahlstelle ohne `frage` bekommt ihre offene Frage mit (`frage_anlegen` legt Fragen auch einzeln an). Den Plan selbst (welche Nacht welche Wahlstelle nutzt, Entscheidungen) ändern diese Werkzeuge nicht; das ist Schritt 4. `alternative_vorschlagen` ist entfallen.
- **Buchungen** (29.10.2026, #76): `buchung_anlegen` legt eine Buchung `B-…` an (ID aus `ids.yaml`), `buchung_aendern` ändert sie; beides für Mitwirkende und Organisator:innen (Aktion `buchung`: wer bucht, trägt ein; Mitwirkende ändern nur eigene Buchungen, Stornieren braucht einen Grund). Ob es die Dinge in `fuer` und die Buchung gibt, prüft der Schreibweg mit dem Repo, nicht der Konnektor mit der veröffentlichten Seite: So ist eine gerade angelegte Art, Strecke oder Buchung im selben Gespräch nutzbar, auch bevor die Seite neu gebaut ist (Issue #135; dasselbe gilt für `wert_eintragen`, `ding_aendern`, `option_anlegen`, `wahlstelle_anlegen`, `frage_anlegen`, `frage_schliessen`, `wissen_schreiben`, `tag_aendern`). Hinweise zu Merkmalen gibt der Konnektor nur, wenn die Seite die Art schon kennt. Der Schreibweg prüft Form, Daten, Status und Herkunft und schreibt `buchungen:` in `plan/routen.yaml`. Belege liest der Konnektor aus der Ablage (`engine/belege.py`), soweit die Person sie sehen darf.
- **Entscheiden und Plan** (Schritt 4, 29.10.2026): `entscheiden` schreibt den Verlaufseintrag direkt (siehe oben), `tag_aendern` den Plan eines Tags.
- **Wissen, Fragen, Rückmeldungen, Personen** (Schritt 5, 29.10.2026): `wissen_schreiben` legt einen W-Abschnitt an oder ergänzt einen (Herkunft am Absatz), `frage_schliessen` klärt eine Frage, `rueckmeldung_erledigen` setzt den Status einer Rückmeldung über den Rückmeldedienst (die KI im AI-Client arbeitet Rückmeldungen der Seite ein: Inhalt prüfen, mit den Werkzeugen eintragen, erledigen), `person_einladen`/`person_entfernen` schreiben die Person über das interne Werkzeug `person_schreiben` des Schreibwegs (kein Werkzeug der Claude-App) sofort nach `reise.yaml` (ausscheiden = Gast, reist nicht; der Verlauf nennt die Person weiter).
- **Status, Einstellungen, neue Reisen** (Schritt 6, 29.10.2026): `reise_status_setzen` (mit Grund und Verlauf, auch aus dem Archiv zurück) und `einstellung_setzen` (Bausteine, Spielregeln) schreiben `reise.yaml`; `reise_anlegen` legt die neue Reise sofort über den Schreibweg an (Werkzeug `reise_anlegen` auf Ebene des Repos), die Links kommen wie bisher, sobald die Seite online ist (`veroeffentlichen.sh`). `auftrag_geben` und die A-Ablage sind entfallen.
- **Abschalten** (letzter Schritt, 29.10.2026): Der Einarbeiten-Lauf auf dem Server (`einarbeiten.sh`, Pfad-Wächter, Timer, KI-Anweisung, Regeln `entscheidungsweg` und `sammelzeit_minuten`) ist entfernt. Der Überblick zeigt keinen Abschnitt „Einarbeiten“ mehr; die Anleitung sagt der KI, dass Eingetragenes sofort gilt.

Betrieb: `docs/betrieb.md`, Abschnitt „Schreibweg“. Ohne eingerichteten Schreibweg (`KN_SCHREIBDIENST` leer) gibt es die Schreibwerkzeuge nicht, die Anleitung nennt sie nicht, und `reise_anlegen` lehnt ab.

## Konnektor „Frieda“ mit Anmeldung (Paket J3, 27.10.2026)

Ein Konnektor für alle Reisen einer Person (ADR-0005). Er ist seit der Umstellung der Regelfall und ersetzt die Konnektoren je Reise und den Konto-Link; die Links bleiben als Übergang lesbar.
Die Adresse ist für alle gleich, `<FR_BASIS>/mcp`, und enthält kein Geheimnis.

**Anmelden:** Beim Hinzufügen in der Claude-App öffnet sich Friedas Anmeldeseite. Man gibt die E-Mail-Adresse und
den Code aus der Mail ein und stimmt dem Zugriff zu. Technisch ist das OAuth 2.1 mit PKCE (S256) und Refresh-Token mit
Rotation. Einzelheiten stehen in `engine/oauth.py` und [konten.md](konten.md).

**Werkzeuge:**
- `meine_reisen`
- `reise_anlegen`, wenn das Konto freigeschaltet ist; sonst `reisen_anlegen_anfragen`
- für den Betreiber `anfrage_entscheiden`
- `kalender` (#77): persönlicher Link, um alle eigenen Reisen im Kalender zu abonnieren (webcal:// für iPhone, Mac,
  Outlook; https:// für Google Kalender). `neu: true` stellt einen neuen Link aus, der alte gilt dann nicht mehr. Was im
  Kalender steht, Erinnerungen und welche Reisen stellt die Person auf „Mein Konto“ ein; dort gibt es auch den Download.
- alle Reise-Werkzeuge mit der Angabe `reise`. Bei nur einer Reise darf sie fehlen.

Die Rechte prüft der Konnektor je Reise wie bisher (Rolle aus `reise.yaml` und `einladungen.json`). Den Namen kennt
er aus dem Konto.

**Einladen:** `person_einladen` verlangt hier eine E-Mail-Adresse und verschickt die Einladung per Mail. Einen Link gibt
es nicht. Auch eine Person, die schon in der Reise steht, lässt sich so mit ihrem Konto verknüpfen.

**Entfernen:** `person_entfernen` (Organisator:in) nimmt eine Person heraus. Konto-Verknüpfung und alte Links enden sofort,
in `reise.yaml` wird sie über den Schreibweg zum Gast, der nicht mitreist (niemand wird gestrichen).

**Neue Reise:** Das Konto wird nach dem Anlegen mit der Reise verknüpft. Personen mit Adresse bekommen eine Einladung
per Mail. Die Adressen stehen in der Anfrage (`einladen`) in `<ablage>/_neu/`, nie in den Reisedaten.

**Wer darf fragen:**
- Redirect-URIs: nur `https://claude.ai/api/mcp/auth_callback` (dazu `FR_OAUTH_REDIRECTS`) und Loopback mit
  beliebigem Port (Claude Code, MCP Inspector, mit Warnung auf der Zustimmungsseite)
- Clients per DCR oder per Client ID Metadata Document von einem freigegebenen Host (`FR_CIMD_HOSTS`, Vorgabe
  `claude.ai`)

## Konto-Link: meine Reisen und neue Reise (Paket H, 27.10.2026)

Eine neue Reise legt eine Person an, keine Reise. Deshalb gibt es neben den Links je Reise einen persönlichen **Konto-Link** („Frieda – meine Reisen“), angelegt vom Betreiber: `python3 engine/konnektor.py konto <schluessel> <Name>`. Wer einen hat, darf Reisen anlegen. In der Claude-App wird er wie jeder Konnektor eingetragen. Er hat zwei Werkzeuge:

| Werkzeug | Was |
|---|---|
| `meine_reisen` | die veröffentlichten Reisen, auf denen die Person dabei ist (Schlüssel oder Name in `reise.yaml`), mit Rolle, Status, Link zur Seite und ihrem Link für die Claude-App; davor die Meldungen an sie, danach ihre angefragten neuen Reisen |
| `sprache_setzen` | Konto-Werkzeug (alle Rollen), Eingabe `sprache` (de, en …): stellt die Sprache des Kontos ein; sie gilt für Anleitung, Beschreibungen, Antworten, Kontoseiten und Mails (ADR-0006) |
| `reise_anlegen` | Eingaben `titel`, `von`, `bis` (JJJJ-MM-TT), optional `ziel`, `sprache` (Sprache der Reise, Vorgabe `de`), `personen` (je `vorname`, `rolle`, `reist`, `notiz`), `notiz` (Bekanntes in eigenen Worten mit Herkunft) und `pfad`; wer anlegt, ist Organisator:innen der neuen Reise |

`reise_anlegen` lehnt sofort ab, wenn Angaben fehlen oder nicht passen oder wenn es den Ordnernamen schon gibt, als veröffentlichte Reise, als Ablage oder als offene Anfrage (`reise.neue_reise_pruefen`). Sonst bleibt die Anfrage mit `daten.neue_reise` als Beleg in `<ablage>/_neu/auftraege.jsonl` (gehört zu keiner Reise), und der Schreibweg legt die Reise sofort an (`neu.aus_auftrag`, die Notiz wird der Überblick, Probebau, Commit nach `main`). Das Veröffentlichen schaltet sie frei und schreibt der Person eine Meldung mit den Links nach `<ablage>/_neu/meldungen.jsonl` (`betrieb/zustellen.py`). Die Links zu den Seiten liest der Konnektor aus `KN_SEITENLINKS` (Standard `seiten.json` neben den Zugängen), die der Betrieb beim Freischalten schreibt. Den Stand der Anfragen zeigt `rueckmeldungen.py liste _neu`. Eine persönliche Startseite im Web mit derselben Übersicht ist geplant (Issue #41).

## Sprache (ADR-0006, Stand 31.10.2026)

Der Konnektor spricht die Sprache des Kontos: Anleitung, Beschreibungen der Werkzeuge, Ergebnisse, Bestätigungen und Fehler. Die Sprache stammt aus der Spalte `konten.sprache` (beim ersten Anmelden aus `Accept-Language`, sonst Englisch) und lässt sich auf der Kontoseite oder mit dem Konto-Werkzeug `language_set` (intern `sprache_setzen`, alle Rollen) ändern. Die Anleitung weist Claude an, in der Sprache der Person zu antworten („Reply in the person's language“).

Die **Reise** hat ihre eigene Sprache (`reise.yaml sprache`, Vorgabe `de`): `trip_create` hat den Parameter `language` (Vorgabe: Sprache des Kontos), `setting_set` ändert sie (nur Organisator:innen, mit Grund). Was die Software in Dateien der Reise schreibt (Verlaufseinträge, Herkunftszeilen, Commit-Nachrichten) und die Meldungen des Wächters und des Kalenders folgen der Reise, nicht dem Konto. Inhalte, die eine Person eingibt, werden nie übersetzt.

Eine neue Sprache ist eine Datei und braucht im Konnektor keine Änderung ([sprachen.md](sprachen.md)); `language_set` bietet sie ab sofort an. Die Tabellen der englischen Namen stehen unten („Englische Namen der Schnittstelle“).

## Einrichten (einmalig)

In einer Instanz erledigen das `betrieb/einrichten.sh`, `deploy.sh` und `freischalten.sh` (`docs/betrieb.md`). Von Hand:

1. Seite bauen und veröffentlichen, sodass `<seiten>/<reise>/daten.json` existiert. Der Konnektor braucht seine Module im selben Ordner (Liste `KN_MODULE` in `betrieb/deploy.sh`, dazu `rueckmeldungen.py`).
2. Den Dienst starten (`python3 engine/konnektor.py dienst`, z. B. als systemd-Dienst). Umgebung: `KN_SEITEN`, `KN_ZUGAENGE`, `KN_RUECKMELDEDIENST`, `KN_HOST`, `KN_PORT`, `KN_BASIS` (siehe Kopf von `engine/konnektor.py`).
3. Einen Reverse-Proxy mit HTTPS davorsetzen, mit geheimem Pfad und Drossel.
   Soll `person_einladen` Links ausstellen, braucht der Dienst `KN_BASIS` und Schreibrecht auf den Ordner von `KN_ZUGAENGE` (bei systemd `ReadWritePaths`, siehe `betrieb/vorlagen/konnektor.service`; Einrichtung in `docs/betrieb.md`). Ohne beides lehnt das Werkzeug mit einem Hinweis ab.
4. Links anlegen:
   ```
   KN_BASIS=https://<domain>/<pfad> python3 engine/konnektor.py zugang <reise> <person>
   … zugang beispielreise karl
   … zugang beispielreise mitwirkend      # Link ohne feste Person, fragt nach dem Vornamen
   ```
   `zugang <reise> <person>` nimmt den Schlüssel aus `reise.yaml personen` der veröffentlichten Seite, alternativ eine Rolle. Jeder Aufruf gibt einen Link aus. `zugaenge` zeigt alle. Neue Links gelten sofort, ein Neustart ist nicht nötig. Ein Link wird gesperrt, indem man seinen Eintrag aus `zugaenge.json` löscht. Die Links kommen nie ins Repo.

## In der Claude-App eintragen

Einstellungen → Konnektoren → „Eigenen Konnektor hinzufügen“. Regelfall (ADR-0005): Name „Frieda“, URL `<FR_BASIS>/mcp`, dann anmelden mit der E-Mail-Adresse. Übergang: als Name den Titel der Reise, als URL den Link je Reise und Person, ohne Anmeldung. Danach kann man im Chat z. B. fragen: „Was steht an T-02 an?“, „Welche Fragen sind offen?“, „Gib als Rückmeldung zu U-02: …“.

Jede Person braucht ein eigenes Claude-Konto, in dem eigene Konnektoren erlaubt sind. Bei Team- oder Firmenkonten muss der Admin sie freigeben.

## Stand (26.10.2026)

Der `ueberblick` endet mit dem Abschnitt „Stand“: wann die Reise zuletzt veröffentlicht wurde, wann der Konnektor gestartet ist und mit welchem Code (Kurz-Hash von `konnektor.py`, `reise.py`, `rueckmeldungen.py`, `routen.py`). Liegt auf dem Server neuerer Code als der, mit dem der Dienst gestartet ist, steht dort, dass er einen Neustart braucht. So lässt sich in der App prüfen, ob das Veröffentlichen gelaufen ist, ohne auf den Server zu schauen. Der Rückmeldedienst wird dabei nicht geprüft.

## Symbol

Der Konnektor meldet beim Verbinden das Symbol der Reise (`serverInfo.icons`, dasselbe Bild wie das App-Symbol der Seite, `icon-32.png` und `icon-192.png` aus der veröffentlichten Seite, als Data-URI). So zeigt die Claude-App beim Konnektor das Symbol der Reise statt des allgemeinen der Domain. Ohne veröffentlichte Symbole entfällt das Feld. Ob und wie die App das Symbol anzeigt, entscheidet die App (Stand 26.10.2026 nicht überall gleich).

## Sicherheit

- Wer einen Link kennt, kann die Reise lesen und Rückmeldungen schicken. Das ist dasselbe Prinzip wie bei der Webseite. Ein Mitwirkenden-Link kann nicht entscheiden und keine Arten, Status oder Einstellungen setzen. Der Link gehört zu einer Person: Wer ihn weitergibt, gibt ihre Rolle weiter.
- Über den Konnektor ändern sich Aufgaben sowie alles, was die Schreibwerkzeuge eintragen, direkt (über den Schreibweg mit Rollen-, Status- und Formprüfung und einem Probebau, siehe „Ontologie im Gespräch“). Rückmeldungen sind Eingaben. Status `gewaehlt`/`verworfen` setzen nur Organisator:innen.
- Drossel im Reverse-Proxy. Der Dienst protokolliert weder Tokens noch Inhalte.
- Überwachung: `GET /gesund` (ohne Token) meldet `{"gesund": true}`, wenn die Zugänge lesbar und alle verlinkten Reisen veröffentlicht sind.

## Englische Namen der Schnittstelle (ADR-0006, Stand 31.10.2026)

`tools/list` zeigt die Werkzeuge mit englischen Namen und englischen Parameternamen. Die deutschen Namen bleiben als Aliase: ein Aufruf mit deutschem Namen, englischem Namen oder beidem gemischt (englisch gewinnt bei Doppelung) bewirkt dasselbe. Die Übersetzung geschieht nur am Rand des Konnektors (`engine/schnittstelle.py`); Schreibweg, Rückmeldedienst, Dateien der Reise und Tests darunter kennen nur die deutschen Namen. Datenwerte, ID-Präfixe und Dateinamen bleiben deutsch; für Datenwerte nimmt der Aufruf auch englische Aliase an (Tabelle unten), die Schemata nennen weiter den Datenwert.

| Englisch (`tools/list`) | Intern und Alias |
|---|---|
| `overview` | `ueberblick` |
| `show` | `zeige` |
| `search` | `suche` |
| `open_questions` | `offene_fragen` |
| `variants` | `varianten` |
| `feedback_list` | `rueckmeldungen` |
| `feedback_give` | `rueckmeldung_geben` |
| `feedback_resolve` | `rueckmeldung_erledigen` |
| `tasks` | `aufgaben` |
| `task_create` | `aufgabe_anlegen` |
| `task_update` | `aufgabe_aendern` |
| `wishes` | `wuensche` |
| `wish_update` | `wunsch_aendern` |
| `wish_propose` | `wunsch_vorschlagen` |
| `categories` | `kategorien` |
| `category_define` | `kategorie_definieren` |
| `attributes` | `merkmale` |
| `attribute_define` | `merkmal_definieren` |
| `attribute_merge` | `merkmal_zusammenfuehren` |
| `kind_define` | `art_definieren` |
| `kinds_adopt` | `arten_uebernehmen` |
| `value_set` | `wert_eintragen` |
| `location_set` | `lage_eintragen` |
| `item_create` | `ding_anlegen` |
| `item_update` | `ding_aendern` |
| `option_create` | `option_anlegen` |
| `option_update` | `option_aendern` |
| `choice_create` | `wahlstelle_anlegen` |
| `choice_update` | `wahlstelle_aendern` |
| `decide` | `entscheiden` |
| `plan_create` | `plan_anlegen` |
| `plan_update` | `plan_aendern` |
| `day_create` | `tag_anlegen` |
| `day_update` | `tag_aendern` |
| `fixed_date_set` | `termin_setzen` |
| `question_create` | `frage_anlegen` |
| `question_answer` | `frage_beantworten` |
| `question_close` | `frage_schliessen` |
| `knowledge_write` | `wissen_schreiben` |
| `knowledge_update` | `wissen_aendern` |
| `narrative_write` | `lesetext_schreiben` |
| `booking_create` | `buchung_anlegen` |
| `booking_update` | `buchung_aendern` |
| `receipt_add` | `beleg_anlegen` |
| `person_invite` | `person_einladen` |
| `person_remove` | `person_entfernen` |
| `trip_update` | `reise_aendern` |
| `trip_status_set` | `reise_status_setzen` |
| `setting_set` | `einstellung_setzen` |
| `my_trips` | `meine_reisen` |
| `trip_create` | `reise_anlegen` |
| `trip_create_request` | `reisen_anlegen_anfragen` |
| `request_decide` | `anfrage_entscheiden` |
| `calendar` | `kalender` |
| `language_set` | `sprache_setzen` |

Parameternamen (ein Wort hat überall dieselbe Übersetzung, außer wo unten eine Ausnahme steht):

| Intern und Alias | Englisch |
|---|---|
| `ab` | `available_from` |
| `ab_was` | `available_from_what` |
| `abschnitt` | `section` |
| `adresse` | `address` |
| `alle` | `all` |
| `an` | `at` |
| `antwort` | `answer` |
| `art` | `kind` |
| `art_bezeichnung` | `kind_label` |
| `art_hinweis` | `kind_hint` |
| `art_symbol` | `kind_symbol` |
| `art_umriss` | `kind_outline` |
| `arten` | `kinds` |
| `auch` | `aliases` |
| `aufenthalte` | `stays` |
| `ausloeser` | `trigger` |
| `ausserhalb` | `outside` |
| `auswahl` | `selection` |
| `bausteine` | `blocks` |
| `beginn` | `start_time` |
| `begriff` | `query` |
| `bei` | `booked_with` |
| `beleg_base64` | `receipt_base64` |
| `beleg_dateiname` | `receipt_filename` |
| `beleg_text` | `receipt_text` |
| `beschreibung` | `description` |
| `bezahlt` | `paid` |
| `bezeichnung` | `label` |
| `bezug` | `refs` |
| `bis` | `until` |
| `buchbar` | `bookable` |
| `buchung` | `booking` |
| `buchungslink` | `booking_link` |
| `datei` | `file` |
| `dateiname` | `filename` |
| `daten_base64` | `data_base64` |
| `datum` | `date` |
| `eingeplant` | `scheduled` |
| `einheit` | `unit` |
| `einzahl` | `singular` |
| `ende` | `end_time` |
| `entfernen` | `remove` |
| `erfordert` | `requires` |
| `ergebnis` | `result` |
| `erlauben` | `allow` |
| `erlebt` | `experienced` |
| `ersetzt_durch` | `replaced_by` |
| `farbe` | `colour` |
| `favorisiert` | `favoured` |
| `folge` | `sequence` |
| `frage` | `question` |
| `frist` | `deadline` |
| `frist_was` | `deadline_what` |
| `fuer` | `for` |
| `gebucht_am` | `booked_on` |
| `geprueft` | `checked` |
| `gilt` | `valid_for` |
| `grund` | `reason` |
| `grundform` | `basic_form` |
| `gruppe` | `group` |
| `hilfe` | `help` |
| `hinweis` | `hint` |
| `kategorie` | `category` |
| `kommentar` | `comment` |
| `koordinaten` | `coordinates` |
| `kurz` | `short` |
| `lesetext` | `reading_text` |
| `merkmal` | `attribute` |
| `merkmale` | `attributes` |
| `minus` | `cons` |
| `nach` | `after` |
| `nacht` | `night` |
| `neu` | `new` |
| `neuer_name` | `new_name` |
| `neuer_titel` | `new_title` |
| `notiz` | `note` |
| `nummer` | `number` |
| `nummeriert` | `numbered` |
| `ohne_route` | `without_route` |
| `optionen` | `options` |
| `ort` | `place` |
| `personen` | `people` |
| `pfad` | `path` |
| `plus` | `pros` |
| `preis` | `price` |
| `preise` | `prices` |
| `prioritaet` | `priority` |
| `punkte` | `points` |
| `quelle` | `source` |
| `regeln` | `rules` |
| `reist` | `travels` |
| `rolle` | `role` |
| `rubrik` | `heading` |
| `schliesst_aus` | `excludes` |
| `schluessel` | `key` |
| `siehe` | `see` |
| `sprache` | `language` |
| `storno` | `cancellation` |
| `storno_bis` | `cancellation_until` |
| `strecken` | `legs` |
| `stufe` | `level` |
| `stufen` | `levels` |
| `summiert` | `summed` |
| `titel` | `title` |
| `trotzdem` | `anyway` |
| `typ` | `type` |
| `unterkuenfte` | `accommodations` |
| `untertitel` | `subtitle` |
| `veraenderlich` | `changeable` |
| `von` | `from` |
| `von_reise` | `from_trip` |
| `vor` | `before` |
| `vorname` | `first_name` |
| `wahl` | `choices` |
| `wahlstelle` | `choice` |
| `wann` | `when` |
| `was` | `what` |
| `wert` | `value` |
| `werte` | `values` |
| `wunsch` | `wish` |
| `zeit` | `time_text` |
| `ziel` | `target` |
| `zustaendig` | `assignee` |
| `reise` | `trip` |

Ausnahmen je Werkzeug:

- `ding_anlegen`: `von` → `from_place`, `nach` → `to_place`, `ab` → `departure`, `an` → `arrival`
- `ding_aendern`: `von` → `from_place`, `nach` → `to_place`, `ab` → `departure`, `an` → `arrival`
- `aufgabe_anlegen`: `ab` → `earliest`
- `aufgabe_aendern`: `ab` → `earliest`
- `tag_aendern`: `nacht` → `night`, `wahl` → `choices`
- `buchung_anlegen`: `ab` → `available_from`
- `buchung_aendern`: `ab` → `available_from`

Englische Aliase für Datenwerte (nur bei Eingaben mit festen Werten):

| Englisch | Datenwert |
|---|---|
| `chosen` | `gewaehlt` |
| `rejected` | `verworfen` |
| `replaced` | `ersetzt` |
| `proposed` | `vorgeschlagen` |
| `favoured` | `favorisiert` |
| `organizer` | `organisator` |
| `organiser` | `organisator` |
| `contributor` | `mitwirkend` |
| `guest` | `gast` |
| `required` | `pflicht` |
| `recommended` | `empfohlen` |
| `optional` | `angeboten` |
| `off` | `aus` |
| `open` | `offen` |
| `in_progress` | `in_arbeit` |
| `done` | `erledigt` |
| `dropped` | `entfaellt` |
| `booked` | `gebucht` |
| `requested` | `angefragt` |
| `cancelled` | `storniert` |
| `resolved` | `geklaert` |
| `idea` | `idee` |
| `planning` | `planung` |
| `fixed` | `fest` |
| `travelling` | `unterwegs` |
| `after` | `danach` |
| `archive` | `archiv` |
| `comment` | `Kommentar` |
| `question` | `Frage` |
| `correction` | `Korrektur` |
| `addition` | `Ergänzung` |
| `answer` | `Antwort` |
| `wish` | `Wunsch` |

In Beschreibungen und Anleitungen ersetzt der Konnektor die Namen von Werkzeugen und eindeutigen Parametern durch die Namen aus `tools/list`; kurze Parameternamen, die zugleich deutsche Wörter sind (von, nach, an, ab, bei, vor, was, art), bleiben im Fließtext unverändert.
