# Planen im Gespräch

Du planst deine Reise, indem du mit Claude sprichst, in der Claude-App am Handy, am Rechner oder auf claude.ai. Frieda ist dabei die Tür zur Reise: Claude liest über den Konnektor (die Verbindung zwischen Claude und Frieda) aus der Reise und schreibt Ergebnisse geprüft zurück, statt dass Wissen in Chatverläufen, Notizen und Mails verstreut bleibt.

**Auf einen Blick:** Wo: Gespräch · Mein Konto (Verbinden) · Wer: alle Personen der Reise, je nach Rolle · Baustein: immer da

## Was du damit tun kannst

- Fragen zur Reise stellen und Antworten aus der Reise bekommen, mit Namen statt Kennungen.
- Recherchieren lassen und das Ergebnis eintragen: Unterkünfte, Strecken, Orte, Werte mit Herkunft und Prüfdatum, Wissen in eigenen Worten.
- Alternativen anlegen, vergleichen und als Organisator:in entscheiden.
- Buchungen mit Nummer, Frist und Stornoregel festhalten, den Beleg gleich mitgeben.
- Rückmeldungen, Fragen, Aufgaben und Wünsche der Mitreisenden ansehen und einarbeiten.
- Arten und Merkmale der Reise festlegen, also was zu einem Hotel, einer Hütte oder einer Zugfahrt bekannt sein muss.
- Nachsehen lassen, ob eine Änderung schon auf der Reiseseite steht, und wie die Stelle dort aussieht.
- Eine neue Reise anlegen und Personen per E-Mail-Adresse einladen.

## So geht's

### Voraussetzung und Verbinden

Du brauchst ein eigenes Claude-Konto, in dem eigene Konnektoren erlaubt sind. Bei Team- oder Firmenkonten muss der Admin das freigeben. Jede Person, die im Gespräch mitplanen will, braucht ein solches Konto; lesen und mitmachen auf der Reiseseite geht auch ohne Claude.

1. In der Claude-App: Einstellungen → Konnektoren → „Eigenen Konnektor hinzufügen“.
2. Name „Frieda“, als Adresse die Konnektor-Adresse deiner Frieda-Instanz (sie endet auf `/mcp`; Mein Konto zeigt sie unter „Mit Claude verbinden“ zum Kopieren).
3. Es öffnet sich Friedas Anmeldeseite: E-Mail-Adresse eingeben, den Code aus der Mail eintippen, dem Zugriff zustimmen.

Ein Konnektor gilt für alle deine Reisen. Wechselst du Gerät oder Claude-Konto, meldest du dich mit derselben Adresse an, und alles ist wieder da.

### Im Gespräch

> „Welche Unterkünfte stehen für die Nacht in Hohnstein zur Wahl?“

Claude liest die Wahlstelle und nennt Pension Burgblick und Gasthof Polenztal mit ihren Merkmalen, Dafür und Dagegen, und sagt dazu, dass Ida die Pension Burgblick schon gewählt hat und warum.

> „Der Gasthof Polenztal kostet jetzt 75 € pro Nacht, das steht auf seiner Website. Trag das ein.“

Claude lässt dich den Wortlaut kurz bestätigen und trägt den Wert mit Herkunft und Prüfdatum ein. Frieda prüft die Regeln und antwortet mit dem gesicherten Reise-Stand.

> „Ist das schon auf der Seite? Zeig mir, wie der zweite Tag am Handy aussieht.“

Claude prüft den Stand der Veröffentlichung und schaut sich die Stelle auf der Reiseseite als Bild an.

Die Werkzeuge, nach Themen (die Claude-App zeigt sie mit diesen englischen Namen):

| Thema | Werkzeuge | wofür |
|---|---|---|
| Lesen | `overview`, `show`, `search`, `open_questions`, `variants`, `attributes`, `people` | Überblick mit Meldungen, Volltext zu einer Stelle, Suche, offene Fragen, Alternativen, was an Merkmalen fehlt, Personen |
| Seite und Stand | `publish_status`, `page_view` | ob eine Änderung veröffentlicht ist; Bild der Reiseseite an einer Stelle, Handy oder Rechner |
| Planen und Eintragen | `item_create`, `item_update`, `day_create`, `day_update`, `knowledge_write`, `narrative_write`, `fixed_date_set` | Unterkünfte, Strecken, Orte, Aufenthalte und ihre Werte; Tage; Wissen und Lesetexte; feste Termine |
| Arten und Merkmale | `kind_define`, `attribute_define`, `kinds_adopt` | festlegen, was die Reise kennt und was zu jeder Sache bekannt sein muss |
| Buchungen | `booking_create`, `booking_update`, `receipt_add` | Buchung mit Nummer, Frist, Stornoregel; Beleg nachreichen |
| Entscheiden | `option_create`, `choice_create`, `plan_create`, `decide` | Alternativen anlegen, Pläne bündeln, Option wählen oder verwerfen |
| Zusammenarbeit | `feedback_give`, `feedback_list`, `feedback_resolve`, `tasks`, `task_create`, `question_create`, `question_answer`, `wishes`, `person_invite` | Rückmeldungen, Aufgaben, Fragen, Wünsche, Einladen |
| Reise verwalten | `trip_create`, `trip_update`, `trip_status_set`, `setting_set`, `icon_set` | neue Reise, Eckdaten, Status, Bausteine und Spielregeln, App-Symbol |
| Konto | `my_trips`, `language_set`, `calendar`, `my_profile`, `profile_entry_set`, `report_to_frieda` | deine Reisen, Sprache, Kalender-Abo, Profil, Meldung an den Betreiber |

Die vollständige Liste mit allen Feldern steht im [Konnektor](../konnektor.md#was-claude-damit-kann). Die deutschen Namen der Werkzeuge funktionieren weiter als zweiter Name.

### Eintragen, sichern, veröffentlichen

Was Claude einträgt, gilt sofort, sobald Frieda die Regeln geprüft hat. Jede Antwort nennt den Reise-Stand, eine fortlaufende Nummer der Reise: „Gesichert als Reise-Stand 43. Veröffentlicht ist Stand 42.“ Die Reiseseite wird danach neu gebaut, Ziel sind höchstens zwei Minuten. Erst wenn `publish_status` für diese Nummer „enthalten: ja“ meldet, sagt Claude, dass die Änderung auf der Seite steht. Du kannst selbst nachsehen: Im Fuß der Reiseseite steht der Reise-Stand; ist dort eine kleinere Nummer, zeigt die Seite „Neu: Reise-Stand 43. Aktualisieren“.

Gelesen wird der veröffentlichte Stand. Ist schon ein neuerer gesichert, sagt Claude das dazu.

### Die Seite sehen

Mit `page_view` sieht Claude die veröffentlichte Reiseseite an einer Stelle, als Bild am Handy (Vorgabe) oder am Rechner, und sagt in Worten, wo die Stelle steht: welcher Reiter, welche Ansicht, hinter welchen Klappen. Auf Wunsch kommt die ganze Ansicht in mehreren Teilen. Was nur angemeldet erscheint (Aufgaben, Rückmeldungen, Packstand), fehlt im Bild. Bevor Claude sagt, wie etwas aussieht, schaut es nach.

### Auf Mein Konto

Unter „Mit Claude verbinden“ stehen die Schritte und die Adresse zum Kopieren. Solange dein Konto noch nicht mit Claude verbunden ist, zeigt Mein Konto die Karte „Neu bei Frieda?“.

## Wer darf was

| Rolle | darf im Gespräch |
|---|---|
| Gast | lesen, Seite ansehen, Stand prüfen |
| Mitwirkende:r | dazu Rückmeldungen, Wünsche, Aufgaben, Antworten; Werte, Dinge, Optionen, Fragen, Wissen, Buchungen und Bilder eintragen; Arten und Merkmale vorschlagen |
| Organisator:in | dazu entscheiden, Arten und Merkmale festlegen, Tage ändern, Status und Einstellungen setzen, einladen, Rückmeldungen abschließen |

Claude bekommt beim Verbinden deine Rolle, den Status der Reise und deine Grenzen mit und hält sich daran. Geprüft wird trotzdem bei jedem Aufruf von Frieda selbst.

## Regeln und Grenzen

- **Frieda enthält keine eigene KI.** Recherche, Abwägen und Formulieren passieren in Claude. Frieda prüft nur Regeln: Rolle, Status der Reise, Herkunft, Konflikte, feste Kennungen ([ADR-0001](../adr/0001-kern.md)).
- **Herkunft ist Pflicht.** Ein Wert ohne Quelle wird abgelehnt, Veränderliches wie Preise oder Fahrpläne braucht ein Prüfdatum. Lehnt Frieda ab, nennt Claude dir den Grund.
- **Claude entscheidet nie.** Es schlägt vor, prüft und trägt ein; Entscheidungen trifft eine Organisator:in, mit Datum und Grund.
- **Frieda löscht nie.** Sagst du „lösch das“, wird eine Buchung storniert, eine Option verworfen, eine Aufgabe oder Frage entfällt, jeweils mit Grund und rückholbar. Für Unterkünfte, Strecken, Orte, Wissen und Tage gibt es keinen Löschweg; Claude sagt das ehrlich und bietet eine Rückmeldung an die Organisator:in an.
- **Hinweise sperren nicht.** Erzeugt ein Eintrag eine neue Warnung (etwa eine Lücke im Plan), gilt er trotzdem, und Claude nennt die Warnung.
- **Status und Bausteine wirken.** Im Status „danach“ gibt es keine neuen Wünsche, Punkte und Alternativen mehr, im Archiv nur noch Lesen. Ein ausgeschalteter Baustein nimmt seine Werkzeuge mit.
- **Sprache:** Claude spricht die Sprache deines Kontos (änderbar mit `language_set` oder auf Mein Konto). Die Reise hat ihre eigene Sprache; was jemand einträgt, wird nie übersetzt. Siehe [Sprachen](sprachen.md).
- **Grenzen der Instanz:** Je Konto gibt es eine Höchstzahl schreibender Aufrufe pro Stunde; wer sie erreicht, bekommt einen Satz mit der Wartezeit.

## Siehe auch

- [Gute Gespräche mit Frieda](gute-gespraeche.md): typische Abläufe mit Beispielsätzen
- [Reisemodell](reisemodell.md), [Alternativen und Entscheidungen](alternativen.md), [Buchungen](buchungen.md), [Zusammenarbeit](zusammenarbeit.md)
- [Reiseseite](reiseseite.md), [Konto und Anmeldung](konto.md), [Sprachen](sprachen.md)
- Referenz: [Konnektor](../konnektor.md), [Einrichten in der Claude-App](../konnektor.md#in-der-claude-app-eintragen), [Konten](../konten.md), [ADR-0001: Der Kern](../adr/0001-kern.md)
