# Frieda Reist als Produkt: Kern, AI first, Rollen, Ausbaustufen

Entschieden vom Product Owner am 26.10.2026 (Gespräch in Claude Code). Dieses Dokument ist das gemeinsame Verständnis, an dem sich Engine, Regeln und Arbeitspakete ausrichten.

**Der Kern steht seit dem 28.10.2026 in [`docs/adr/0001-kern.md`](adr/0001-kern.md)** und geht diesem Dokument vor: Frieda hält die Reise als Ontologie ohne Katalog von Arten und Merkmalen, der AI-Client ist der Arbeitsplatz für alles Unstrukturierte, der Konnektor ist die Tür, Frieda enthält keine eigene KI, die PWA ist Ansicht und Eingabefläche, Claude Code baut nur die Software. Was unten davon abweicht (etwa „die KI arbeitet ein“ als Teil des Kreislaufs, der Einarbeiten-Lauf in Paket D, die Prüfaufträge des Wächters in Paket E), beschreibt den Stand bis zum 28.10.2026 und wird mit den Paketen zu frieda-reist #85 angepasst.

## Zweck

Frieda ist die eine Quelle der Wahrheit für eine Reise, von der ersten Idee bis zum Nachschlagen unterwegs. Es ist ein generisches Produkt: Es soll beliebigen Reisegruppen dienen, nicht nur einem Haushalt. Die Claude-App (Desktop und Handy) ist der Ort, an dem alle die Reise mitgestalten. Die Webseite ist das Nachschlagewerk unterwegs, offline, mit Karte und Brett.

## Kern

1. **Reisemodell.** Bausteine mit festen IDs: Tage, Strecken, Orte, Unterkünfte. Alternativen sind Teil des Modells: Wahlstellen mit Optionen auf jeder Ebene, benannte Pläne. Verworfenes wird nie gelöscht, sondern bekommt einen Verlaufseintrag. Drumherum das Wissen (Dossiers, Geschichte, Praxis, Quellen) und das Offene (Fragen, Aufgaben, Wünsche, Rückmeldungen).
2. **Spielregeln.** Jede Aussage nennt ihre Herkunft, Annahmen sind markiert, Veränderliches trägt ein Prüfdatum. Organisator:innen entscheiden, mit Datum und Verlauf. Mitwirkende geben Eingaben. Die KI recherchiert, prüft, schlägt vor, arbeitet ein, baut und veröffentlicht, entscheidet aber nie. IDs werden nie neu vergeben.
3. **Kreislauf.** Eingabe über App oder Seite an eine ID, Eingang auf dem Server, Prüfung und Einarbeiten durch die KI, Veröffentlichung, Status mit Kommentar zurück an den Absender.

Technik (Python-Generator, HTML-Vorlage, Service Worker, nginx, systemd, Git) ist Mittel, nicht Kern.

## AI first

1. Das Gespräch ist die Haupttür. Jede Rolle redet mit der Reise, die Webseite ist Ansicht und Eingabefläche.
2. Das Modell ist für die KI gebaut: Reise, Personen, Rollen, Bausteine, Herkunft und Prüfdatum sind Felder mit Schema (`reise.yaml`, `routen.yaml`, Merkmale). Fließtext bleibt Fließtext.
3. Die Regeln prüft die Maschine (Rechte, Pflichtfelder, Konflikte); die KI bekommt nur eine kurze Verfassung.
4. Die KI handelt: Eingaben werden sofort eingearbeitet, Veränderliches wird überwacht, Fristen werden gemeldet, Optionen werden von selbst vorgeschlagen.
5. Die KI kennt die Menschen: je Person ein Profil, über Reisen hinweg, einsehbar und korrigierbar.

## Rollen

Rollen gelten je Reise, nicht je Person. Rechte sind gestuft, jede Stufe enthält die darunter:

| Rolle | Darf |
|---|---|
| `gast` | lesen (Mitreisende, die nur wissen wollen, was wann ist; Gäste) |
| `mitwirkend` | Wünsche, Rückmeldungen, Aufgaben, Antworten auf Fragen; auch für Nicht-Reisende (`reist: false`) |
| `organisator` | entscheiden (gewählt, verworfen, ersetzt), Status und Einstellungen der Reise setzen, Personen einladen |

Mehrere Organisator:innen sind möglich. Jede Entscheidung hat genau eine Person und ein Datum. Zwei verschiedene Entscheidungen an derselben Stelle überschreiben sich nicht: Die KI macht daraus eine offene Frage und meldet den Konflikt beiden (Regel `konflikt: offene_frage`). Die KI selbst ist die vierte Rolle: Assistent, schlägt vor, prüft, arbeitet ein, entscheidet nie.

Personen und Rollen stehen je Reise in `reisen/<reise>/reise.yaml` unter `personen:`. Wer nur einen Teil der Reise mitreist, bekommt `von` und `bis` (Datum); der Reiseüberblick zeigt dann „ab“ und „bis“. Der Konnektor-Link gehört zu einer Person (`konnektor.py zugang <reise> <person>`).

## Einstellungen je Reise (`reise.yaml`)

- **Bausteine, an oder aus** (`bausteine:`). Immer da: Plan, Wissen, Suche, Personen. Zuschaltbar: `varianten`, `karte`, `tagesseiten`, `rueckmeldungen`, `fragen`, `aufgaben`, `wuensche`, `waechter`, `profile`. Ein ausgeschalteter Baustein verschwindet aus Seite und App, seine Daten bleiben. (`waechter` ist seit Paket E gebaut, `profile` ist angelegt, aber noch nicht gebaut: Ausbaustufe 3.)
- **Spielregeln, mit Wert** (`regeln:`), Vorgaben in `engine/reise.py`: `entscheidungsweg` (direkt im Gespräch oder als Auftrag mit Prüfung), `konflikt` (offene_frage), `kontingent` beim Brett (Art `punkte` oder `anzahl`, `je_person`), `einladen` (organisator), `sammelzeit_minuten` vor dem Einarbeiten.
- **Darstellung** (`darstellung:`): Startreiter, Namen der Reiter, Tiefe der Ansicht, Gruppen, Mahnungen im Plan (`mahnungen: false` blendet den Kasten „Mahnung“ dort aus; berechnet wird sie weiter und steht im Konnektor).

Einstellungen setzt die Organisator:in, auch im Gespräch. Jede Änderung bekommt einen Verlaufseintrag. Die Zuordnung der Inhalte (Überschrift zu ID) bleibt getrennt davon in `reise.json`.

## Status einer Reise

Ausdrücklich gesetzt, nicht abgeleitet; die Organisator:in setzt ihn, die KI erinnert am Start- und Enddatum, wechselt aber nie selbst. Jede Stufe hat Datum und Verlauf, rückwärts geht auch.

| Status | Was gilt |
|---|---|
| `idee` | Eckdaten, Personen, Wünsche sammeln. Kein Plan nötig, keine Warnungen. |
| `planung` | Alles offen. Lücken und offene Wahlstellen sind normaler Zwischenstand. |
| `fest` | Plan gewählt, Buchen läuft. Offene Planungs-Wahlstellen werden zur Mahnung, Aufgabenfristen zählen, der Wächter prüft Veränderliches. |
| `unterwegs` | Seite startet mit „Heute“ und Karte, Unterwegs-Wahlstellen rücken vor, Wünsche werden abgehakt, Rückmeldungen sind Notizen vom Weg. |
| `danach` | Nachlese, Profile lernen aus Erlebtem, Plan schreibgeschützt. Ausbau später. |
| `archiv` | Nur noch lesen. |

### Was die Maschine daraus macht (Paket B, 26.10.2026)

Die Regeln stehen in `engine/reise.py` (`VERHALTEN`, `AKTIONEN`, `erlaubt`) und gelten an jeder Stelle, an der geschrieben wird: im Rückmeldedienst (HTTP, 403 mit Begründung) und im Konnektor (bei jedem Aufruf, nicht nur in der Werkzeugliste).

| Status | Schreiben | Seite und Konnektor |
|---|---|---|
| `idee` | alles | keine Warnungen des Plans |
| `planung` | alles | Lücken und offene Wahlstellen sind Zwischenstand; Aufgabenfristen zählen noch nicht |
| `fest` | alles | offene Planungs-Wahlstellen und ungeprüfte veränderliche Angaben der gewählten Optionen sind eine **Mahnung** (`route.mahnungen`); Aufgabenfristen zählen (überfällig) |
| `unterwegs` | alles | wie `fest`; die Seite startet mit „Heute“ und der Karte, Wahlstellen mit Auslöser stehen vorn |
| `danach` | Nachlese: Rückmeldungen, Aufgaben und Abhaken von Wünschen ja; neue Wünsche, Punkte, Alternativen, Aufträge nein | Plan schreibgeschützt |
| `archiv` | nichts | nur lesen |

Ein Auftrag an das Ziel `reise` (Status, Einstellungen) geht in jedem Status, damit ein:e Organisator:in eine gesperrte Reise wieder öffnen kann.

Rechte: Der Rückmeldedienst kennt die Rolle über den Namen aus `reise.yaml` (veröffentlichte `daten.json`). Eine bekannte Person mit Rolle `gast` kann nichts eintragen; ein unbekannter Name auf der Seite kommt über den geheimen Link und zählt als Mitwirkende:r. Zugänge je Person gibt es seit Paket C (siehe unten).

Bausteine: Ein ausgeschalteter Baustein verschwindet aus der Seite (Reiter, Knöpfe, Formulare), aus den Konnektor-Werkzeugen (Liste, Aufruf, Überblick, Anleitung) und blockiert das Schreiben im Dienst. Die Daten bleiben. Karte aus: `route.karte` wird auf der Seite nicht verwendet; Tagesseiten aus: die Etappen stehen wieder im Reiter „Etappen“.

Konflikt (`regeln.konflikt: offene_frage`): Ein Auftrag mit `entscheidung` (gewaehlt, verworfen, ersetzt) und `ziel` wird gegen die stehenden Entscheidungen im Plan und gegen offene Aufträge anderer Organisator:innen geprüft. Widerspruch heißt dasselbe Ziel verschieden entschieden oder zwei verschiedene Optionen derselben Wahlstelle gewählt. Dann bekommen die beteiligten Aufträge den Status `konflikt` (werden nicht eingearbeitet), `meldungen.jsonl` in der Ablage bekommt eine Meldung an alle beteiligten Organisator:innen (der Konnektor zeigt sie unter `rueckmeldungen`), und die KI legt eine offene Frage (F-…) an. Zustellung der Meldung auf weiteren Wegen folgt mit Paket E.

### Gespräch für alle (Paket C, 26.10.2026)

Details und Eingaben der Werkzeuge: `docs/konnektor.md`, Abschnitt „Entscheiden, Fragen beantworten, Einladen“.

- `entscheiden` (Organisator:in): Entscheidung über eine Option wird im selben Moment geprüft (Option, Status, Grund, Doppelungen, Konflikt mit anderen Organisator:innen) und seit 29.10.2026 (O-3) mit Datum, Person und Grund direkt in den Plan geschrieben; ein Konflikt wird offene Frage mit Meldung. `regeln.entscheidungsweg` ist ohne Wirkung (entfällt mit dem Abschalten des Einarbeitens). Status und Einstellungen der Reise setzen Organisator:innen mit `reise_status_setzen` und `einstellung_setzen`.
- `frage_beantworten` (Mitwirkende:r): Die Antwort hängt an der Frage; ob die Frage geklärt ist, entscheidet die Organisator:in.
- `person_einladen` (`regeln.einladen`): legt die Person mit Rolle an und stellt den Link aus, ohne Handarbeit auf dem Server. Rolle und Zugang gelten sofort (`einladungen.json`); seit O-3 steht die Person sofort in `reise.yaml`.
- Die Anleitung des Konnektors nennt die Rolle, den Reisestatus und die Grenzen der sprechenden Person.

### Wächter und Erinnerer (Paket E, 26.10.2026)

Details: `docs/waechter.md`. Neue Regeln mit Vorgabe: `waechter_frist_tage` (60), `erinnerung_vorlauf_tage` (3), `meldekanal` (`app`, `nachricht`).

- Der Wächter sucht veränderliche Angaben ohne oder mit altem Prüfdatum und gibt sie dem Einarbeiten als Prüfauftrag; Abweichungen werden als offene Frage gemeldet, nie still übernommen.
- Der Erinnerer meldet Fristen und „ab“-Termine an die Zuständigen und den fälligen Statuswechsel an die Organisator:innen; die KI wechselt den Status nie selbst.
- Beides gilt nur bei eingeschaltetem Baustein `waechter` und im Status `fest` oder `unterwegs`.
- Die Meldungen erscheinen in der Claude-App (Überblick) und als Sammelnachricht an den Betreiber. E-Mail an alle gibt es nicht; Meldungen auf dem Handy über die Webseite sind Issue #21.

### Wunsch-Brett (Paket G, 27.10.2026)

Wünsche sind Ideen ohne feste Stelle (ein Ort, ein Erlebnis, ein Essen). Das Brett ordnet sie in Spalten, die immer berechnet werden, nie gespeichert:

| Spalte | Wann |
|---|---|
| eingebracht | gesendet, noch nicht geprüft (oder Rückfrage) |
| geprüft | Claude hat ihn aufgenommen, oft mit Vorschlag „passt zu T-…“ oder einer Option an einer Wahlstelle |
| eingeplant | ein:e Organisator:in hat ihn in der Claude-App eingeplant oder die Option gewählt, die aus ihm entstand |
| erlebt | abgehakt, unterwegs oder in der Nachlese |
| passt nicht | Claude hat ihn geprüft und verworfen, mit Begründung |

- **Punkte** heißen „wie wichtig mir das ist“. Jede Person verteilt ihr Kontingent (`regeln.kontingent`, Vorgabe 10 Punkte) nur auf ihre eigenen Wünsche und darf umverteilen. Ein Wunsch, der nicht passt, gibt seine Punkte frei. Claude nutzt Punkte beim Prüfen als Priorität, nie als Entscheidung. Mit Art `anzahl` gibt es keine Punkte, dann begrenzt das Kontingent die Zahl offener Wünsche je Person.
- **Abhaken** (erlebt) dürfen alle Mitwirkenden, auch fremde Wünsche, im Status `unterwegs` und `danach`. Die Seite merkt sich Abgehaktes ohne Netz und reicht es nach; einen Haken zurücknehmen geht nur mit Netz. Wer abgehakt hat, steht mit Datum im Verlauf.
- **Einplanen** ist eine Entscheidung: nur ein:e Organisator:in, mit dem persönlichen Link in der Claude-App (auf der Webseite ist der Name nur eingetippt), ab Status `danach` nicht mehr. Die Seite zeigt, wer eingeplant hat. Claude schlägt nur vor (`plan/wuensche.yaml`: Bezug, Notiz mit Herkunft, Option), plant aber nie selbst ein.
- Die **Bilanz** je Person (Wünsche, eingeplant, erlebt, freie Punkte) sehen alle.
- Technik: Punkte, eingeplant und erlebt liegen live in `brett.json` der Rückmelde-Ablage, mit Verlauf; gelöscht wird nichts. Seite: Reiter „Wünsche“. Claude-App: `wuensche` und `wunsch_aendern`.

## Vorgaben für neue Reisen

- Konfliktregel: offene Frage, Meldung an alle beteiligten Organisator:innen.
- Einladen dürfen nur Organisator:innen.
- Sammelzeit vor dem Einarbeiten: 5 Minuten.
- Brett-Kontingent: Punkte, 10 je Person.
- Eigene Konnektoren gibt es nur in bezahlten Claude-Konten; jede Person, die mitgestalten soll, braucht so ein Konto (vor Stufe 1 noch einmal gegen den aktuellen Stand prüfen).

Die Rollen und Status der laufenden Reisen stehen in deren `reise.yaml`, die Entscheidungen dazu in der `CLAUDE.md` des Reisen-Repos.

## Ausbaustufen und Arbeitspakete

| Paket | Inhalt | Sitzungen |
|---|---|---|
| A Modell | Personen, Rollen, Rechte, Kontingente, Einstellungen, Status als Daten; Herkunft und Prüfdatum als Felder, wo Regeln wirken; feste Namen raus aus Engine, Konnektor, Regeln | 3 bis 4 |
| B Regeln im Code | Rechteprüfung beim Schreiben, Pflichtfelder, Konfliktmeldung, Verhalten je Status, Bausteine blenden sich aus | 1 bis 2 |
| C Gespräch für alle | Zugang je Person mit Rolle; Werkzeuge entscheiden, Frage beantworten, Person einladen; Entscheidung wird im Moment geprüft | 2 |
| D Sofort statt stündlich | Eingaben lösen das Einarbeiten aus (Sammelzeit), Veröffentlichung am Ende des Laufs | 2 |
| E Wächter und Erinnerer | Prüfung veränderlicher Angaben, Meldung von Fristen und „ab“-Terminen | 2 |
| F Profile | je Person, KI-gepflegt, einsehbar, reiseübergreifend | 2 |
| G Wunsch-Brett | Spalten, Kontingent, Verknüpfung mit Tag oder Ort, Bilanz je Person, Abhaken unterwegs | 2 bis 3 |
| H Neue Reise anlegen | Vorlage; Reise entsteht im Gespräch aus Eckdaten, Personen, Quellen | 2 |
| I Mehrere Haushalte | eigene Instanz je Reisegruppe; später | 5 oder mehr |

Stufe 1 „Rollen und sofort“: A, B, C, D. Stufe 2 „Wünsche und Wächter“: G, E. Stufe 3 „Lernen und neue Reisen“: F, H. Vorerst eine Instanz auf dem eigenen Server, der Code wird generisch. Die Software wird als „Ida Pfeiffer“ (AGPL-3.0) von den Reiseinhalten getrennt (Issue #78); Reiseinhalte bleiben privat.

## Stand

- 26.10.2026, Paket A begonnen: `reise.yaml` je Reise mit Status, Personen, Bausteinen, Regeln und Darstellung (`engine/reise.py` prüft); `entscheider` kommt aus den Personen; Konnektor kennt Rollen `bestimmer`, `einbringer`, `reisend` und Zugänge je Person; der Schalter `funktionen` in `reise.json` ist durch `bausteine` in `reise.yaml` ersetzt.
- 26.10.2026, Paket B: Rechte, Verhalten je Status, Bausteine und Konflikt werden im Code geprüft (siehe „Was die Maschine daraus macht“); Tests in `engine/tests/test_regeln.py`.
- 26.10.2026, Paket C: Werkzeuge `entscheiden`, `frage_beantworten`, `person_einladen`; beide Entscheidungswege getestet (`engine/tests/test_gespraech.py`). Offen: Links sperren geht noch von Hand.
- 27.10.2026, Paket H: neue Reise im Gespräch, in Claude Code (`engine/neu.py`) und in der Claude-App über einen persönlichen Konto-Link (`meine_reisen`, `reise_anlegen`); Vorlage `engine/reisevorlage/`, `zeitraum` in `reise.yaml`, IDs mit Marke in `ids.yaml`, Prüfung vor dem Bau, Anleitung `docs/neue-reise.md`.
- 26.10.2026, Paket E: Wächter und Erinnerer (`engine/waechter.py`, `docs/waechter.md`), Baustein `waechter`; Tests in `engine/tests/test_waechter.py` mit simuliertem Datum.
- 28.10.2026, Rollen umbenannt (#80): Gast (`gast`), Mitwirkende:r (`mitwirkend`), Organisator:in (`organisator`). Die alten Schlüssel `reisend`, `einbringer`, `bestimmer` und `mitreisend` liest der Code weiter (`reise.rolle_neu`), geschrieben werden nur die neuen.
- 28.10.2026, ADR-0001 und Pakete O-0 bis O-2 (#85, #88–#90): Der Kern steht in `docs/adr/0001-kern.md`. Die Software kennt nur noch die Grundformen der Reise-Ontologie und die Form eines Merkmals (`docs/ontologie.md`); Arten und Merkmale stehen je Reise in `plan/arten.yaml` (Stufen `pflicht`, `empfohlen`, `angeboten`, `aus`). Grundliste `engine/merkmale.yaml`, feste Übernachtungskategorien und die Synonymliste des Konnektors sind entfallen; `neu.py arten-ableiten` leitet die Arten einer bestehenden Reise aus ihren Daten ab. Offen: O-3 (Konnektor schreibt direkt, #91), O-4 (Wächter ohne KI, #92), O-5 (Seite nach Grundformen, #93), O-6 (Doku, #94).
- 29.10.2026, Paket O-3, Schritt 1 (#91): Schreibweg `engine/schreiben.py` (Dienst `<instanz>-schreiben`, eigene Arbeitskopie, Probebau, Commit nach `main`, Veröffentlichen) und die Konnektor-Werkzeuge `art_definieren`, `merkmal_definieren`: Organisator:innen legen Arten und Merkmale der Reise im Gespräch fest, Mitwirkende schlagen vor (`docs/konnektor.md`, „Ontologie im Gespräch“; `docs/betrieb.md`, „Schreibweg“). Schritt 2 (29.10.2026): `wert_eintragen` schreibt Werte an Unterkünften, Strecken und Optionen direkt nach `plan/routen.yaml` (Herkunft Pflicht, Prüfdatum bei Veränderlichem; ruamel.yaml hält Kommentare und Form der Datei). Schritt 3 (29.10.2026): `ding_anlegen`, `ding_aendern`, `option_anlegen`, `wahlstelle_anlegen`, `frage_anlegen` schreiben Unterkünfte, Strecken, Orte, Optionen (Status `vorgeschlagen`), Wahlstellen und offene Fragen direkt; `alternative_vorschlagen` entfällt. Schritt 4 (29.10.2026): `entscheiden` schreibt den Verlaufseintrag direkt (Frage geklärt, Konflikt wird offene Frage), `tag_aendern` ändert den Plan eines Tags. Schritt 5 (29.10.2026): `wissen_schreiben`, `frage_schliessen`, `rueckmeldung_erledigen` (über den Rückmeldedienst), Personen direkt in `reise.yaml` (`person_schreiben`; ausscheiden = Gast). Schritt 6 (29.10.2026): `reise_status_setzen`, `einstellung_setzen`, neue Reisen sofort über den Schreibweg; `auftrag_geben` und A-Ablage entfallen. Zuletzt das Abschalten des Einarbeitens.
