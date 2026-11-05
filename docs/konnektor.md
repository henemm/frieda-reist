# Konnektor: Reisen in der Claude-App

Mit dem Konnektor lässt sich eine Reise in jedem normalen Claude-Chat nutzen (App am Handy, Desktop, claude.ai). Claude liest dabei die Reise und kann Rückmeldungen abgeben. Technisch ist es ein MCP-Server: `engine/konnektor.py` auf dem eigenen Server, neben dem Rückmeldedienst.

## Grundsätze (24.10.2026)

- **Der Konnektor schreibt direkt in die Reise** (seit 29.10.2026, ADR-0001 Paket O-3): Frieda enthält keine KI; was im Gespräch festgelegt wird, prüfen Regeln im Code (`engine/schreiben.py`, siehe „Ontologie im Gespräch“) und schreiben es sofort in das Reisen-Repo. Bis zum 29.10.2026 änderte sich der Plan nur beim Einarbeiten durch Claude Code auf dem Server (Aufträge, Rückmeldungen); dieser Weg ist abgeschaltet.
- Nutzen dürfen ihn **alle Personen der Reise** (`reise.yaml personen`). Seit 26.10.2026 gehört ein Link zu einer Person; ihre Rolle entscheidet: `gast` liest, `mitwirkend` gibt Rückmeldungen, Wünsche, Vorschläge und Aufgaben und schreibt Werte, Dinge, Optionen, Fragen und Wissen (Eingaben), `organisator` entscheidet dazu, legt Arten und Merkmale fest, setzt Status und Einstellungen und lädt ein. Alte Links mit Rolle `mitreisend` gelten als `mitwirkend`.
- **Regelfall ist das Konto** (ADR-0005, Paket J3): Die Person meldet sich im Konnektor „Frieda“ mit ihrer E-Mail-Adresse an, ein Konnektor für alle Reisen. Die Links je Reise und Person in diesem Abschnitt sind der Übergang, werden nicht mehr ausgestellt und sind seit 1.11.2026 abgeschaltet (nginx antwortet 404); was unten über „den Link“ steht, gilt für das Konto ebenso (die Person steht fest).
- **Ein Link pro Reise und Person** (Übergang, abgeschaltet).
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
| `veroeffentlichung_pruefen` | alle | Reise-Stand vom Server (Epic #223): gesicherter und veröffentlichter Stand mit Zeit in der Zeitzone der Person, Zustand (wartet, wird gebaut, veröffentlicht, fehlgeschlagen mit Grund und dem Stand, der sichtbar bleibt), Dauer seit dem Sichern gegen das Ziel von 2 Minuten und für eine Nummer „enthalten: ja/nein“ (siehe „Reise-Stand“) |
| `rueckmeldung_geben` | alle | landet im selben Eingang wie die Rückmeldungen von der Webseite; Art `Wunsch` für Ideen ohne feste Stelle (ziel leer), sichtbar im Reiter „Wünsche“ |
| `aufgaben` | alle | Aufgaben, Standard nur offene; Filter nach Bezug, Zuständig, Status |
| `aufgabe_anlegen` | alle | neue Aufgabe, gilt sofort |
| `aufgabe_aendern` | alle | abhaken, Status, Felder, Kommentar in den Verlauf; gilt sofort |
| `wuensche` | alle | Wunsch-Brett: Wünsche nach Spalten mit Punkten, Vorschlag, eingeplant, erlebt; Bilanz je Person (Baustein `wuensche`) |
| `wunsch_aendern` | Mitwirkende, Organisator:innen | Punkte auf eigene Wünsche, abhaken (unterwegs und danach), einplanen (nur Organisator:innen mit persönlichem Link; auf der Webseite gibt es das nicht); gilt sofort, Regeln prüft der Rückmeldedienst (siehe `docs/produkt.md`, Wunsch-Brett) |
| `kategorien` | Alias | steht nicht mehr in `tools/list`; die Kartenkategorien sind Arten mit `gruppe` (siehe `docs/ontologie.md`); der Aufruf (englisch `categories`) zeigt sie weiter |
| `merkmale` | alle | welche Merkmale eine Alternative braucht (mit Hinweis zum Recherchieren und Nachfragen), was jede Option hat und was fehlt; zu einer Wahlstelle `V-…`, einer Strecke `E-…` oder einer Art (`art`); siehe `docs/alternativen.md` |
| `lage_eintragen` | Alias von `ding_aendern` | steht nicht mehr in `tools/list`; ein Aufruf (englisch `location_set`) kommt beim Schreibweg als `ding_aendern` mit `adresse` und `koordinaten` an und schreibt dasselbe wie vorher (Lage als typisiertes Merkmal; Herkunft Pflicht; bei einem Ort nur Koordinaten) |
| `ding_anlegen`, `ding_aendern` | Mitwirkende, Organisator:innen | **Seit ADR-0007 (Schritt c, #284) die Form:** `ding_anlegen` (`item_create`) nimmt nur `was`, `art`, `an` (Elternbezug), `titel`, `quelle`, `merkmale`, `hinweis`, `geprueft`; `ding_aendern` (`item_update`) dazu `ziel`, `grund`. Alles andere steht in `merkmale`: die Felder der Grundform (`ort`, `von`, `nach`, `zeit`, `frage`, `ausserhalb`), die festen typisierten Merkmale (`adresse`, `koordinaten`, `zeitraum`, `abfahrt`, `ankunft`, `buchungslink`, beim Ändern einer Strecke `gpx` als GPX-Text, siehe `docs/ontologie.md`) und die Merkmale der Art (wie `wert_eintragen`, auch an einer Option `V-…`). Die Herkunft (`quelle`, bei Veränderlichem `geprueft`) steht oben und gilt für alle Angaben; ohne `merkmale` ändert `quelle` die Herkunft des Dings selbst. Schreibt sofort nach `plan/routen.yaml`. Ein Aufenthalt kommt mit `tag_aendern` (`aufenthalte`) an seinen Tag oder mit `an` an ein anderes Ding (ADR-0007); ein Ort darf eine Art mit `grundform: ort` tragen (freiwillig, erst dann Merkmale) und mit `an: O-…` in genau einem anderen Ort liegen, nur für die Anzeige (ADR-0008); `zeige O-…` nennt Art, „liegt in“ und die Orte darin; `ding_aendern` auch den Buchungsstand `buchung` (die Art nur Organisator:innen). Die früheren Parameter (`ort`, `von`, `nach`, `ab`, `an` als Zeit, `beginn`, `ende`, `zeit`, `adresse`, `koordinaten`, `buchungslink`, `frage`, `ausserhalb`; englisch `place`, `from_place`, `to_place`, `departure`, `arrival` …) stehen nicht mehr im Schema, werden aber weiter angenommen. |
| `kartenansicht_setzen` | Organisator:innen, Baustein `karte` | Kartenansicht anlegen, ersetzen (gleicher Titel) oder entfernen: Titel und Auswahl aus Tagen, Strecken und Arten, dazu `uebersicht` (Arten, deren Übersicht unter der Karte dieser Ansicht steht, ADR-0007 Schritt e); steht in `plan/routen.yaml` (`karten_ansichten`); die Übersicht gibt es immer (#236) |
| `track_anhaengen` | Alias von `ding_aendern` | steht nicht mehr in `tools/list`; ein Aufruf (englisch `track_attach`) kommt als `ding_aendern` mit `gpx` an: GPX-Datei aus dem Gespräch (als Text, höchstens etwa 60 000 Zeichen) an eine Strecke hängen, liegt danach unter `medien/gpx/` und ersetzt die schematische Linie |
| `kartenpunkte_holen` | Organisator:innen, Baustein `karte` | Punkte aus OpenStreetMap längs einer Strecke: die Art der Reise (mit `gruppe: punkt`) und die OSM-Tags wählt die Person; Treffer bis `abstand_m` von der Linie werden **Dinge** (Aufenthalte `A-…` mit `an: <Strecke>`, Koordinaten, Quelle und Stand, OSM-Bezug); ein zweiter Aufruf aktualisiert dieselben Dinge, nichts wird gelöscht. Ohne passende Art Ablehnung mit Hinweis (Art zuerst mit `art_definieren` anlegen) |
| `option_anlegen`, `wahlstelle_anlegen` | Mitwirkende, Organisator:innen | Alternative als Option an eine Wahlstelle hängen (Status `vorgeschlagen`, Verlauf mit Person und Datum) oder eine neue Wahlstelle mit Optionen anlegen (`an` Tagen, Strecken, Unterkünften, Orten, Abschnitten; `planung` bekommt eine offene Frage mit); ersetzt `alternative_vorschlagen` |
| `frage_anlegen` | Mitwirkende, Organisator:innen | offene Frage F-… in `offene-fragen.md` anlegen (Baustein `fragen`) |
| `buchung_anlegen`, `buchung_aendern` | Mitwirkende, Organisator:innen | Buchung als eigenes Ding `B-…` (#76, 29.10.2026): für welche Unterkunft, welchen Aufenthalt oder welche Strecke (`fuer`), Status (angefragt, gebucht, storniert), Nummer, Anbieter, Preis, bezahlt, Frist mit `frist_was`, Stornoregel mit `storno_bis`, Herkunft (Pflicht); ändern mit Verlaufseintrag (Person, Datum, Grund), leerer Text entfernt ein Feld; Mitwirkende ändern nur eigene Buchungen (`wer`), Organisator:innen alle, Stornieren braucht einen Grund (Product Owner 29.10.2026). `zeige B-…` zeigt alles samt Belegen, `ueberblick` zählt und nennt die nächsten Fristen. Seit Issue #135 dazu: `personen` (die Reisenden dieser Buchung mit Angabe je Person, etwa Sitzplatz, Gepäck, Vielfliegernummer; nur Namen aus `reise.yaml`), `preise` (bei mehreren Dingen in `fuer` der Preis je Ding), `ab` mit `ab_was` (ab wann etwas geht, etwa der Online-Check-in; der Wächter erinnert am Tag). Seit Issue #166: `zahlung` (Zahlstand `offen`, `angezahlt`, `bezahlt`, `vor_ort`, `inklusive`, `erstattet`; englisch `open`, `deposit`, `paid`, `on_site`, `included`, `refunded`, gespeichert wird der deutsche Wert; `erstattet` nur bei `storniert`; Einzelheiten in `bezahlt`) und `merkmale` (Merkmale der Buchung, die die Art ihrer Dinge festlegt; `merkmale art` zeigt sie). Den **Beleg** gibt die Person beim Anlegen gleich mit (`beleg_text` als Abschrift oder `beleg_base64` mit `beleg_dateiname`; ein Schritt, der Schreibweg nennt die neue B-ID, der Konnektor legt den Beleg sofort in der Ablage ab), nachträglich mit `beleg_anlegen` oder angemeldet auf der Reiseseite; er liegt in der Ablage, nie im Repo, und ist nur für sie und Organisator:innen sichtbar, bis eine Organisator:in ihn freigibt |
| `beleg_anlegen` | Mitwirkende, Organisator:innen | Beleg nachträglich an eine Buchung `B-…` hängen, ohne die Reiseseite (Issue #135): als Abschrift (`text`, der Inhalt der Bestätigung oder Mail wörtlich, abgelegt als `.txt`) oder als Datei (`daten_base64`: PDF, JPEG, PNG, WebP, HEIC, höchstens 10 MB), mit `dateiname`. Der Konnektor schickt ihn an den Rückmeldedienst, den einzigen Schreiber der Ablage (`POST /<reise>/belege/<B-id>` mit Dienst-Header). Kennt die veröffentlichte Seite die Buchung noch nicht, fragt der Konnektor den Schreibweg (`GET /<reise>/buchung/<B-id>`, liest `origin/main`) und schickt dem Rückmeldedienst `X-Frieda-Buchung: im-repo`; so geht der Beleg sofort nach dem Anlegen. Sichtbar für die Person und Organisator:innen, freigeben geht auf der Reiseseite |
| `art_definieren` | Organisator:innen schreiben, Mitwirkende schlagen vor | eine Art der Reise anlegen oder ändern (Bezeichnung, Grundform, Farbe, Beschreibung, summiert); schreibt über den Schreibweg direkt in `plan/arten.yaml` (siehe „Ontologie im Gespräch“); nur bei Instanzen mit Schreibweg |
| `kategorie_definieren` | Alias von `art_definieren` | steht nicht mehr in `tools/list`; legt eine Art der Grundform `aufenthalt` mit `gruppe` an oder ändert sie (auch ohne Merkmale); `art_definieren` (`kind_define`) nimmt `gruppe`, `einzahl` und `nummeriert` selbst |
| `merkmal_definieren` | Organisator:innen schreiben, Mitwirkende schlagen vor | ein Merkmal einer Art anlegen oder ändern: umbenennen, Typ und Werte, veränderlich, Stufe (für die Person „nötig“, „gut zu wissen“, „zusätzlich“; Schlüssel `pflicht`, `empfohlen`, `angeboten`, beides wird angenommen; `aus` schaltet ab und wird nicht genannt), Hilfe, Frage, weitere Namen, ob der Wert nach der Buchung sichtbar bleibt (`nach_buchung`, z. B. Charakter; 31.10.2026); warnt vor einem ähnlichen vorhandenen Merkmal (`trotzdem` übergeht das). Mit `fuer: buchung` ein Merkmal der Buchungen dieser Art (#166: was erst durch das Buchen entsteht, etwa Ticketart; nur Name, Typ, Werte, Einheit, Hilfe, Frage) |
| `wert_eintragen` | Alias von `ding_aendern` | steht nicht mehr in `tools/list`; ein Aufruf (englisch `value_set`) kommt als `ding_aendern` mit `merkmal` und `wert` oder `werte` an und schreibt den Wert eines Merkmals der Art mit Herkunft und Prüfdatum wie vorher |
| `reise_status_setzen`, `einstellung_setzen` | Organisator:innen | Status der Reise mit Grund und Verlauf; Bausteine, Spielregeln und Sprache der Reise (`sprache`); schreibt sofort nach `reise.yaml` (ersetzt `auftrag_geben`). `tagesseiten` ist seit #214 kein Baustein mehr (Tagesseiten hat jede Reise); in einer älteren `reise.yaml` ist der Eintrag ohne Wirkung |
| `symbol_setzen` | Organisator:innen | App-Symbol der Reise (Seite, Homebildschirm, Konnektor) lesen, setzen, ersetzen oder entfernen (#252). Ohne Angaben: das aktuelle Symbol als SVG-Text (wenn es eines gibt) und eine Vorschau als Bild (`icon-192.png`, MCP-Inhalt `image`), damit die Claude-App es weiterentwickeln kann. Mit genau einem von `svg` (SVG als Text), `png_base64` (PNG, quadratisch, mindestens 512 Pixel) oder `entfernen` (danach gilt das Symbol aus dem Kurznamen); schreibt `medien/icon.svg` oder `medien/icon.png` über den Schreibweg, das alte Symbol bleibt im Verlauf. Siehe „Symbol“ |
| `entscheiden` | Organisator:innen | Option wählen, verwerfen oder ersetzen: sofort geprüft und mit Datum, Person und Grund in den Plan geschrieben (Paket C; seit O-3 direkt) |
| `tag_aendern` | Organisator:innen | Titel, Text, Nacht, Strecken, Wahlstellen und Aufenthalte ohne Nacht (`aufenthalte`) eines Tags ändern; schreibt sofort |
| `frage_beantworten` | Mitwirkende | Antwort auf eine offene Frage (F-…); hängt an der Frage, die Entscheidung bleibt bei der Organisator:in (Paket C) |
| `frage_schliessen` | Organisator:innen | Frage als geklärt oder entfallen eintragen, mit Ergebnis; schreibt sofort nach `offene-fragen.md` |
| `wissen_schreiben` | Mitwirkende, Organisator:innen | Wissen in eigenen Worten mit Herkunft: neuer W-Abschnitt (ID aus `ids.yaml`, Zuordnung in `reise.json`) oder Absatz unter einem vorhandenen; schreibt sofort; mit `uebersicht` (Arten) steht bei dem Abschnitt die Übersicht dieser Arten (ADR-0007 Schritt e, `docs/ontologie.md`) |
| `rueckmeldung_erledigen` | Organisator:innen | Rückmeldung oder Auftrag abschließen (uebernommen, verworfen, rueckfrage) mit Kommentar für die Seite; über den Rückmeldedienst, gilt sofort |
| `tag_anlegen` | Organisator:innen | neuen Tag anlegen (T-…) und in die Route stellen (nach, vor, am Ende oder ohne Route für eine Variante), mit Titel, Nacht, Strecken, Aufenthalten; schreibt sofort (Abgleich 29.10.2026) |
| `termin_setzen` | Organisator:innen | festen Termin der Reise anlegen (Datum, Titel, Ort, Herkunft Pflicht), ändern oder mit Grund entfernen (`fixpunkte` in `plan/routen.yaml`) |
| `wahlstelle_aendern` | Organisator:innen | Felder einer Wahlstelle: Titel, Text, `wann`, `art` (Art der Dinge), `an`, Frage, Stufen je Merkmal nur für diese Wahlstelle |
| `option_aendern` | Mitwirkende, Organisator:innen | Felder einer Option (Titel, Text, Dafür, Dagegen, Regeln, Auslöser, Inhalt, Herkunft) und favorisieren mit Grund (Vorschlag, keine Entscheidung; gewählt nur mit `entscheiden`) |
| `wissen_aendern` | Mitwirkende, Organisator:innen | einen W-Abschnitt berichtigen: Inhalt ersetzen (Herkunft Pflicht) oder umbenennen (ID bleibt), mit Grund; der Probebau lehnt ab, wenn andere Dateien Unterabschnitte oder Fußnoten daraus brauchen; mit `uebersicht` setzt oder (leere Liste) entfernt es die Übersicht der Arten bei dem Abschnitt |
| `lesetext_schreiben` | Mitwirkende, Organisator:innen | den Lesetext einer Etappe (Abschnitt Zusammenfassung unter `## E-… Name` im Etappen-Dossier, „Der Weg“) nach der Gliederung ihrer Art schreiben oder ersetzen, Herkunft Pflicht; fremde Stichworte lehnt der Schreibweg ab. Titel und Kennzahlen stehen an der Strecke: `item_create` und `item_update` mit `figures` in `attributes`, als Feld der Grundform wie `von` und `nach` (ADR-0007, kein eigener Parameter) (`kennzahlen`, Kennung → Wert: `gehzeit` h:mm, `aufstieg`, `abstieg` in m, `laenge` in km, englisch `walking_time`, `ascent`, `descent`, `length`; leerer Wert entfernt, #269) |
| `reise_aendern` | Organisator:innen | Eckdaten: Titel, Untertitel, Kurzname, Ziel (`target`), Zeitraum, mit Grund; ohne eigenen Untertitel entsteht er beim Bau aus Ziel und Zeitraum (#217); Verlauf in `reise.yaml` unter `verlauf`; Start und Ende des Plans setzt `start_ende_setzen` |
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

## Karte aus dem Plan (Epic #225, 2.11.2026)

Ist der Baustein `karte` an, baut Frieda die Karte aus allem mit Koordinaten: Orte (`punkt`), Unterkünfte und Aufenthalte (`punkt`, ADR-0004). Es braucht mindestens zwei Punkte; `plan/karte.yaml` ist nur noch eine Überschreibung für handgepflegte Karten (`docs/ontologie.md`, „Karte“). So entsteht eine Karte allein im Gespräch:

1. `einstellung_setzen` mit dem Baustein `karte`; die Antwort nennt den Kartenstatus.
2. Koordinaten recherchieren (der AI-Client, nicht der Server) und mit `lage_eintragen` oder gleich bei `ding_anlegen` (`koordinaten`) eintragen.
3. `ueberblick` zeigt den Kartenstatus: gebaut oder nicht, Grund, Zahl der Punkte, Einträge ohne Koordinaten mit Namen.
4. Ausschnitte mit `kartenansicht_setzen` (zum Beispiel je Fahrt ein Tag mit den Arten der Ladestopps), Tracks mit `track_anhaengen`, zusätzliche Punkte aus OpenStreetMap mit `kartenpunkte_holen`.

Name und Farbe eines Punkts kommen aus seiner Art (`plan/arten.yaml`); eine Kartenkategorie mit dem Schlüssel einer Art überschreibt sie nur. Alternativen (Unterkünfte und Aufenthalte, die nur in einer Option oder an einem Tag außerhalb des Plans stehen) erscheinen als Umriss. Strecken ohne GPX verbinden die Stationen eines Tags gestrichelt („schematisch“). Ein Aufenthalt ohne Tag (vor Ort gesammelt) steht auf der Karte und vollständig darunter, nicht im Tagesplan. Die Offline-Grundkarte holt das Veröffentlichen, wenn sich der Rahmen geändert hat (`werkzeuge/grundkarte_auto.py`, Zoom nach Fläche, Detailkarten bei langen Fahrten). Ein Kartenfehler lässt die Seite nicht ausfallen: Sie erscheint ohne Karte, der Kartenstatus nennt den Grund.

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

**Anleitung:** Beim Verbinden bekommt die KI Rolle, Reisestatus und die Grenzen der sprechenden Person (Mitwirkende:r: kann nicht entscheiden; Link ohne Person: kein Entscheiden und Einladen) und den Hinweis, dass Eingetragenes sofort gilt und die Seite es zeigt, sobald `veroeffentlichung_pruefen` für die Nummer aus der Antwort „enthalten: ja“ meldet (Ziel: 2 Minuten); erst dann sagt die KI, es sei auf der Seite.

**Löschwunsch (#145):** Frieda löscht nie. Sagt eine Person „lösch das“, wählt die KI nach der Anleitung (für jede Rolle) den passenden Weg, lässt kurz bestätigen, was genau und mit welchem Grund, und sagt danach in einem Satz, was geschah, dass nichts gelöscht ist und wie man es zurückholt. Eine Buchung wird storniert (`buchung_aendern`, Status `storniert` mit Grund; zurück mit Status `gebucht`). Eine Option einer Wahlstelle wird verworfen oder ersetzt (`entscheiden`, nur Organisator:innen; zurück mit `entscheiden`, Status `gewaehlt`). Eine Aufgabe entfällt (`aufgabe_aendern`, Status `entfaellt`; zurück mit Status `offen`). Eine offene Frage entfällt (`frage_schliessen`, Status `entfaellt`, nur Organisator:innen); ein Wiedereröffnen gibt es nicht, bei Bedarf wird eine neue Frage angelegt. Für Unterkünfte, Strecken, Orte, Wissen, Tage, Wahlstellen und Pläne gibt es keinen Löschweg (Ändern lässt den alten Wert im Verlauf); dasselbe gilt für Optionen, wenn Mitwirkende sprechen. Dann sagt die KI das ehrlich und bietet eine Rückmeldung an die Organisator:in an (`rueckmeldung_geben`). Die Werkzeugbeschreibungen nennen je ihren Weg, und die Antworten nach Stornieren, Verwerfen oder Ersetzen und nach `entfaellt` enden mit „Nicht gelöscht …“ und dem Rückholweg.

## Ontologie im Gespräch (ADR-0001, Paket O-3, Schritte 1 bis 6, 29.10.2026)

Welche Arten eine Reise hat (Hotel, Refugi, Ryokan, Zugfahrt, Reiseteil …) und was zu jeder Sache einer Art bekannt sein muss, legt die Reise im Gespräch fest (`docs/ontologie.md`). Dafür gibt es `art_definieren` und `merkmal_definieren`:

- **Organisator:innen** schreiben damit direkt: Der Konnektor schickt die Anfrage mit Person und Rolle an den **Schreibweg** (`engine/schreiben.py dienst`, nur auf 127.0.0.1, mit dem Dienst-Geheimnis). Der prüft mit `reise.yaml` der Reise noch einmal Rolle und Status (Aktion `ontologie`: Organisator:in, Status mit vollem Schreibrecht), die Form der Angaben (Grundform, Typ, Stufe, Werte bei `auswahl`, kein zweiter Name eines vorhandenen Merkmals), ändert `plan/arten.yaml`, baut die Reise zur Probe (der Generator prüft alles Übrige, etwa ob eingetragene Werte zu neuen Auswahlwerten passen), sichert die Änderung als Commit mit Person und Werkzeug nach `main` und stößt das Veröffentlichen an. Lehnt er ab, bleibt alles unverändert, und die Person bekommt den Grund. Die Antwort heißt dann „Eingetragen und gesichert“ und nennt beide Reise-Stände („Gesichert als Reise-Stand 43. Veröffentlicht ist Stand 42“); die Seite und die Werkzeuge `merkmale`/`zeige` zeigen den neuen Stand, sobald `veroeffentlichung_pruefen` für diese Nummer „enthalten: ja“ meldet (Ziel: 2 Minuten). Nur mit persönlichem Link: Jede Änderung gehört einer Person.
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

Ein Konnektor für alle Reisen einer Person (ADR-0005). Er ist seit der Umstellung der Regelfall und ersetzt die Konnektoren je Reise und den Konto-Link; die Links je Reise und Person waren der Übergang und sind seit 1.11.2026 abgeschaltet (nginx antwortet 404).
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
per Mail. Die Adressen stehen in der Anfrage (`einladen`) in `<konten>/neu/`, nie in den Reisedaten.

**Wer darf fragen:**
- Redirect-URIs: nur `https://claude.ai/api/mcp/auth_callback` (dazu `FR_OAUTH_REDIRECTS`) und Loopback mit
  beliebigem Port (Claude Code, MCP Inspector, mit Warnung auf der Zustimmungsseite)
- Clients per DCR oder per Client ID Metadata Document von einem freigegebenen Host (`FR_CIMD_HOSTS`, Vorgabe
  `claude.ai`)

## Konto-Link: meine Reisen und neue Reise (Paket H, 27.10.2026)

Eine neue Reise legt eine Person an, keine Reise. Deshalb gibt es neben den Links je Reise einen persönlichen **Konto-Link** („Frieda – meine Reisen“), angelegt vom Betreiber: `python3 engine/konnektor.py konto <schluessel> <Name>`. Wer einen hat, darf Reisen anlegen. In der Claude-App wird er wie jeder Konnektor eingetragen. Er hat zwei Werkzeuge:

| Werkzeug | Was |
|---|---|
| `meine_reisen` | die veröffentlichten Reisen, auf denen die Person dabei ist (Schlüssel oder Name in `reise.yaml`), mit Rolle, Status, Link zur Seite und ihrem Link für die Claude-App; davor die Meldungen an sie (mit Konto über alle ihre Reisen, je Zeile mit dem Titel der Reise), danach ihre angefragten neuen Reisen |
| `sprache_setzen` | Konto-Werkzeug (alle Rollen), Eingabe `sprache` (de, en …): stellt die Sprache des Kontos ein; sie gilt für Anleitung, Beschreibungen, Antworten, Kontoseiten und Mails (ADR-0006) |
| `reise_anlegen` | Eingaben `titel`, `von`, `bis` (JJJJ-MM-TT), optional `ziel`, `sprache` (Sprache der Reise, Vorgabe: Sprache des Kontos), `personen` (je `vorname`, `rolle`, `reist`, `notiz`), `notiz` (Bekanntes in eigenen Worten mit Herkunft) und `pfad`; wer anlegt, ist Organisator:innen der neuen Reise |

`reise_anlegen` lehnt sofort ab, wenn Angaben fehlen oder nicht passen oder wenn es den Ordnernamen schon gibt, als veröffentlichte Reise, als Ablage oder als offene Anfrage (`reise.neue_reise_pruefen`). Sonst bleibt die Anfrage mit `daten.neue_reise` als Beleg in `<konten>/neu/auftraege.jsonl` (gehört zu keiner Reise), und der Schreibweg legt die Reise sofort an (`neu.aus_auftrag`, die Notiz wird der Überblick, Probebau, Commit nach `main`). Das Veröffentlichen schaltet sie frei und schreibt der Person eine Meldung mit den Links nach `<konten>/neu/meldungen.jsonl` (`betrieb/zustellen.py`). Die Links zu den Seiten liest der Konnektor aus `KN_SEITENLINKS` (Standard `seiten.json` neben den Zugängen), die der Betrieb beim Freischalten schreibt. Den Stand der Anfragen zeigt `rueckmeldungen.py liste _neu`. Dieselbe Übersicht zeigt „Mein Konto“ im Web, die Startseite der Adresse (#41). Die Meldungen an ein Konto kommen für `meine_reisen`, Mein Konto und die Reiseseiten aus einer Quelle (`rueckmeldungen.meldungen_des_kontos`): die ohne Reise und die jeder Reise, in der das Konto Mitglied ist (#21 Stufe 1).

## Sprache (ADR-0006, Stand 31.10.2026)

Der Konnektor spricht die Sprache des Kontos: Anleitung, Beschreibungen der Werkzeuge, Ergebnisse, Bestätigungen und Fehler. Die Sprache stammt aus der Spalte `konten.sprache` (beim ersten Anmelden aus `Accept-Language`, sonst Englisch) und lässt sich auf der Kontoseite oder mit dem Konto-Werkzeug `language_set` (intern `sprache_setzen`, alle Rollen) ändern. Die Anleitung weist Claude an, in der Sprache der Person zu antworten („Reply in the person's language“).

Die **Reise** hat ihre eigene Sprache (`reise.yaml sprache`, Vorgabe `de`): `trip_create` hat den Parameter `language` (Vorgabe: Sprache des Kontos), `setting_set` ändert sie (nur Organisator:innen, mit Grund). Was die Software in Dateien der Reise schreibt (Verlaufseinträge, Herkunftszeilen, Commit-Nachrichten) und die Meldungen des Wächters und des Kalenders folgen der Reise, nicht dem Konto. Inhalte, die eine Person eingibt, werden nie übersetzt.

Eine neue Sprache ist eine Datei und braucht im Konnektor keine Änderung ([sprachen.md](sprachen.md)); `language_set` bietet sie ab sofort an. Die Tabellen der englischen Namen stehen unten („Englische Namen der Schnittstelle“).

## Einrichten (einmalig)

In einer Instanz erledigen das `betrieb/einrichten.sh`, `deploy.sh` und `freischalten.sh` (`docs/betrieb.md`). Von Hand:

1. Seite bauen und veröffentlichen, sodass `<seiten>/<reise>/daten.json` existiert. Der Konnektor braucht seine Module im selben Ordner (Liste `KN_MODULE` in `betrieb/deploy.sh`, dazu `rueckmeldungen.py`).
2. Den Dienst starten (`python3 engine/konnektor.py dienst`, z. B. als systemd-Dienst). Umgebung: `KN_SEITEN`, `KN_ZUGAENGE`, `KN_RUECKMELDEDIENST`, `KN_HOST`, `KN_PORT`, `KN_BASIS` (siehe Kopf von `engine/konnektor.py`).
3. Einen Reverse-Proxy mit HTTPS davorsetzen, mit Drossel; der Dienst steht an der Wurzel der Adresse (Vorlage `betrieb/vorlagen/nginx-konnektor-orte.inc`, #163).
   Soll `person_einladen` Links ausstellen, braucht der Dienst `KN_BASIS` und Schreibrecht auf den Ordner von `KN_ZUGAENGE` (bei systemd `ReadWritePaths`, siehe `betrieb/vorlagen/konnektor.service`; Einrichtung in `docs/betrieb.md`). Ohne beides lehnt das Werkzeug mit einem Hinweis ab.
4. Links anlegen:
   ```
   KN_BASIS=https://<domain> python3 engine/konnektor.py zugang <reise> <person>
   … zugang beispielreise karl
   … zugang beispielreise mitwirkend      # Link ohne feste Person, fragt nach dem Vornamen
   ```
   `zugang <reise> <person>` nimmt den Schlüssel aus `reise.yaml personen` der veröffentlichten Seite, alternativ eine Rolle. Jeder Aufruf gibt einen Link aus. `zugaenge` zeigt alle. Neue Links gelten sofort, ein Neustart ist nicht nötig. Ein Link wird gesperrt, indem man seinen Eintrag aus `zugaenge.json` löscht. Die Links kommen nie ins Repo.

## In der Claude-App eintragen

Einstellungen → Konnektoren → „Eigenen Konnektor hinzufügen“. Regelfall (ADR-0005): Name „Frieda“, URL `<FR_BASIS>/mcp`, dann anmelden mit der E-Mail-Adresse. Die frühere Einrichtung mit einem Link je Reise und Person gibt es nicht mehr. Danach kann man im Chat z. B. fragen: „Was steht an T-02 an?“, „Welche Fragen sind offen?“, „Gib als Rückmeldung zu U-02: …“.

Jede Person braucht ein eigenes Claude-Konto, in dem eigene Konnektoren erlaubt sind. Bei Team- oder Firmenkonten muss der Admin sie freigeben.

## Reise-Stand (Epic #223, 2.11.2026)

Jede Reise trägt eine fortlaufende Nummer neben dem Software-Release, etwa „Reise-Stand 42 · Frieda Release 357“. Sie zählt die Commits, die den Ordner der Reise ändern (`engine/stand.py`): Jeder gesicherte Schreibvorgang erhöht sie um 1, ein Software-Update lässt sie stehen, und Stand 43 enthält alles aus Stand 42.

- **Schreibantwort:** Jedes Werkzeug, das über den Schreibweg sichert, hängt an seine Antwort „Gesichert als Reise-Stand 43. Veröffentlicht ist Stand 42; ob Stand 43 auf der Seite ist, zeigt veroeffentlichung_pruefen.“ (zentral beim Aufruf, nicht je Werkzeug). Rückmeldungen, Aufgaben, Wünsche und Belege liegen in der Ablage, gelten sofort und ändern den Reise-Stand nicht.
- **`veroeffentlichung_pruefen`** (`publish_status`, optional `nummer`): liest den Stand auf dem Server, dieselbe Quelle wie `api/stand` der Seite, nie einen Speicher des Browsers. Zustände: wartet, wird gebaut, veröffentlicht, fehlgeschlagen (mit Grund und dem Stand, der sichtbar bleibt). Dazu die Dauer seit dem Sichern und das Ziel von 2 Minuten (Product Owner, E3, 2.11.2026); eine Überschreitung steht dabei.
- **So prüft Frieda:** Sie merkt sich die Nummer aus der Schreibantwort und ruft `veroeffentlichung_pruefen` auf. Bei „enthalten: ja“ meldet sie den Erfolg, bei „fehlgeschlagen“ den Grund. Erst dann sagt sie, die Änderung sei sichtbar.
- **So prüft die Person:** Frieda nennt die Nummer. Steht im Fuß der Seite dieselbe oder eine höhere, ist die Änderung da; bei einer niedrigeren zeigt der Hinweis „Neu: Reise-Stand 43. Aktualisieren“ den Weg.
- **Zeiten** nennt der Konnektor in der Zeitzone der Person mit Angabe der Zone („02.11.2026 09:47 (MEZ)“): die Zone des Geräts, mit dem die Person zuletzt Benachrichtigungen eingeschaltet hat, sonst `FR_ZEITZONE` der Instanz, sonst UTC (#227).

## Stand (26.10.2026)

Der `ueberblick` endet mit dem Abschnitt „Stand“: wann die Reise zuletzt veröffentlicht wurde (mit Zeitzone), welcher Reise-Stand auf der Seite ist, wann der Konnektor gestartet ist und mit welchem Code (Kurz-Hash von `konnektor.py`, `reise.py`, `rueckmeldungen.py`, `routen.py`). Liegt auf dem Server neuerer Code als der, mit dem der Dienst gestartet ist, steht dort, dass er einen Neustart braucht. So lässt sich in der App prüfen, ob das Veröffentlichen gelaufen ist, ohne auf den Server zu schauen. Der Rückmeldedienst wird dabei nicht geprüft.

## Symbol

Der Konnektor meldet beim Verbinden das Symbol der Reise (`serverInfo.icons`, dasselbe Bild wie das App-Symbol der Seite, `icon-32.png` und `icon-192.png` aus der veröffentlichten Seite, als Data-URI). So zeigt die Claude-App beim Konnektor das Symbol der Reise statt des allgemeinen der Domain. Ohne veröffentlichte Symbole entfällt das Feld. Ob und wie die App das Symbol anzeigt, entscheidet die App (Stand 26.10.2026 nicht überall gleich).

Das Symbol entsteht im Gespräch (#252): Die Claude-App entwirft es und gibt es mit `symbol_setzen` (`icon_set`) an Frieda, nur Organisator:innen. Ein SVG wird vor dem Schreiben geprüft und zur Probe gezeichnet; abgelehnt werden DTD und Entitäten, Skript, Ereignisattribute (`on…`), Links (`a`), eingebettete Inhalte (`foreignObject`, `iframe` …), Verweise nach außen (`href`, `url(…)`, `@import`, erlaubt sind nur `#id` und eingebettete PNG- oder JPEG-Bilder) und Formen, die nicht quadratisch sind. Ein PNG muss quadratisch sein und mindestens 512 Pixel haben. Beides höchstens 40 KB, damit die Anfrage mit Base64 unter den 64 KB von Konnektor, Schreibweg und nginx bleibt. Es gibt immer nur eines: `medien/icon.svg` geht vor `medien/icon.png`, der Schreibweg entfernt das jeweils andere. Der Generator rechnet daraus `icon-32`, `-180`, `-192` und `-512.png` (Durchsichtiges auf Weiß) und legt die Quelle als `symbol.svg` oder `symbol.png` neben die Seite (nicht vorab gespeichert); ein SVG nur, wenn es dieselbe Prüfung besteht. Von dort liest `symbol_setzen` ohne Angaben.

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
| `publish_status` | `veroeffentlichung_pruefen` |
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
| `icon_set` | `symbol_setzen` |
| `my_trips` | `meine_reisen` |
| `trip_create` | `reise_anlegen` |
| `trip_create_request` | `reisen_anlegen_anfragen` |
| `request_decide` | `anfrage_entscheiden` |
| `calendar` | `kalender` |
| `map_view_set` | `kartenansicht_setzen` |
| `track_attach` | `track_anhaengen` |
| `map_points_fetch` | `kartenpunkte_holen` |
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
| `strecke` | `leg` |
| `tage` | `days` |
| `gpx` | `gpx_text` |
| `osm` | `openstreetmap_tags` |
| `abstand_m` | `distance_m` |
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

- `ding_anlegen`, `ding_aendern`: `an` → `parent` (der Elternbezug, ADR-0007); die früheren englischen Namen `from_place`, `to_place`, `departure`, `arrival`, `place`, `start_time`, `end_time`, `time_text`, `address`, `coordinates`, `booking_link`, `question`, `outside` stehen nicht mehr im Schema und gelten weiter als Eingabe (`schnittstelle.PARAMETER_VERSTECKT`)
- Aliase von `item_update`: `value_set`, `location_set`, `track_attach` (deutsch `wert_eintragen`, `lage_eintragen`, `track_anhaengen`) sind nicht mehr in `tools/list`; Aufrufe kommen beim Schreibweg als `item_update` an (ADR-0006 Punkt 4, ADR-0007 Schritt c)
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
