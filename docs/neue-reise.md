# Neue Reise anlegen (Paket H)

Eine neue Reise entsteht im Gespräch. Niemand legt Dateien von Hand an. Es gibt zwei Wege:

- **In Claude Code:** Die Person sagt „neue Reise“. Claude fragt Eckdaten und Personen ab und ruft `engine/neu.py reise` auf. Quellen wie Buchfotos, PDFs und Links übernimmt Claude danach in eigenen Worten.
- **In der Claude-App:** Über den persönlichen Konto-Link „Frieda – meine Reisen“, der zu einer Person und zu keiner Reise gehört (`docs/konnektor.md`), nutzt man das Werkzeug `reise_anlegen`. Der Dienst prüft die Angaben sofort und legt einen Auftrag an. Der Betrieb legt die Reise aus denselben Bausteinen an (`neu.aus_auftrag`), veröffentlicht sie und schaltet sie frei. Danach zeigt `meine_reisen` der Person die Links.

In beiden Fällen steht die Reise danach im Status `idee` und baut sofort: mit Eckdaten, Wissen, Wünschen und einer ersten offenen Frage.

## Was das Gespräch klärt

| Angabe | Pflicht | Hinweis |
|---|---|---|
| Titel | ja | kurz, z. B. „Winterwoche im Allgäu“; daraus und aus dem Jahr wird der Ordnername (`reise_pfad`) |
| Zeitraum | ja | erster und letzter Tag; steht in `reise.yaml` unter `zeitraum`, schon bevor es einen Plan gibt |
| Ziel | nein | Ort oder Gegend; erscheint im Untertitel |
| Personen | ja | je Person Vorname, Rolle (`reisend`, `einbringer`, `bestimmer`), ob sie mitreist; wer anlegt, ist Bestimmer |
| Bekanntes | nein | Ideen, schon Gebuchtes, Quellen; in eigenen Worten mit Herkunft |

Claude fragt nur nach Lücken und lässt vor dem Anlegen bestätigen, was genau angelegt wird.

## Vorlage

`engine/reisevorlage/` enthält, was jede Reise braucht. `neu.py` füllt die Platzhalter aus und schreibt `reise.yaml`, `reise.json` und `ids.yaml` selbst:

```
reise.yaml          Titel, Untertitel, Ordner, Zeitraum, Status idee mit Verlauf, Personen, Bausteine, Gruppen
reise.json          Zuordnung: W-01 Eckdaten (Plan), W-02 Überblick (Wissen), W-03 Quellen
ids.yaml            höchste vergebene Nummer je Art
CLAUDE.md           Eckdaten, Vorlieben, Entscheidungen der Reise
offene-fragen.md    F-01: Ideen sammeln, dann über den Rahmen entscheiden
plan/plan.md        Eckdaten; der Plan kommt mit der Planung
inhalt/wissen.md    Überblick und Quellen
kontext/herkunft.md wann, von wem und auf welchem Weg die Reise angelegt wurde
medien/             für Bilder, Karten, Tracks
```

Eingeschaltet sind `rueckmeldungen`, `fragen`, `aufgaben` und `wuensche`. `varianten`, `karte`, `tagesseiten` und `waechter` schaltet ein Bestimmer zu, wenn die Planung beginnt. Ein Routenmodell (`plan/routen.yaml`, Aufbau in `engine/routen.py` und in der Beispielreise) kommt mit der Planung dazu: Start und Ende, Orte, Strecken, Unterkünfte, Wahlstellen. Dafür wird in `reise.json` der Eintrag `routen` ergänzt.

## Quellen übernehmen

Bücher, Fotos von Buchseiten, PDFs und Links werden zu Wissensabschnitten:

1. Quelle lesen. Originale wie Fotos und PDFs bleiben außerhalb des Repos, im Reisen-Repo im Ordner `privat/`.
2. Je Thema einen Abschnitt anlegen: `engine/neu.py abschnitt <reise> --titel "…" --gruppe wissen|praxis|quelle [--datei inhalt/….md] [--text-datei <entwurf>]`. Das Skript hängt die Überschrift an, vergibt die nächste freie W-ID und trägt sie in `reise.json` ein.
3. Text in eigenen Worten schreiben, nie abschreiben. Jede Aussage nennt ihre Herkunft: Buch mit Seite, Link mit Lesedatum (Fußnote `[^n]`), Gespräch. Annahmen sind markiert. Veränderliches wie Öffnungszeiten und Preise bekommt ein Prüfdatum.
4. Die Quelle selbst in den Abschnitt „Quellen“ (W-03) eintragen.
5. Prüfen und bauen: `engine/neu.py pruefen <reise>`, dann `engine/bauen.py`.

Texte sind Markdown. Eigenes HTML lehnt der Generator ab (`docs/design.md`, Reisetexte).

## IDs

IDs werden nie neu vergeben. `engine/neu.py id <reise> <W|F|O|U|E|T|V>` gibt die nächste freie Nummer aus und vermerkt sie sofort in `ids.yaml`. Die Nummer liegt über der Marke und über jeder Nummer, die irgendwo in der Reise steht, auch im Verlauf von Verworfenem. Ein gelöschter Abschnitt gibt seine Nummer deshalb nicht frei. Für Reisen von vor Paket H entsteht `ids.yaml` beim ersten Aufruf.

## Prüfung vor dem Bau

`engine/neu.py pruefen <reise>` sagt in einfachen Worten, was zu beheben ist, mit Zeile und Spalte bei kaputtem YAML oder JSON. Es meldet auch Dateien, die `reise.json` nennt, die es aber nicht gibt, und alle Fehler des Generators. Ohne Befund: „In Ordnung: … baut ohne Fehler.“

## Freischalten im Betrieb

Damit die Reise erreichbar ist, braucht der Betrieb drei Dinge: die veröffentlichte Seite unter einem geheimen Link, eine Ablage für Rückmeldungen und einen Link für die Claude-App je Person (`konnektor.py zugang <reise> <person>`). Den Link zur Seite trägt er in `seiten.json` neben den Zugängen ein, damit `meine_reisen` ihn zeigt. Aufträge aus der App liegen in `<ablage>/_neu/`; der Betrieb arbeitet sie ohne KI ab, weil alles geprüft ist, und meldet der Person die Links über `rueckmeldungen.meldung_anlegen` in derselben Ablage. Auf dem eigenen Server geschieht das ohne Handarbeit mit `betrieb/` (`docs/betrieb.md`, Neue Reise freischalten). Den Konnektor trägt jede Person einmal selbst in der Claude-App ein (Einstellungen → Konnektoren → Eigenen Konnektor hinzufügen). Das kann kein Server für sie tun.

Das Einarbeiten stößt eine einzige Datei an: Jede neue Eingabe berührt `<ablage>/.neu` (`rueckmeldungen.anstossen` schreibt sie neu), und der Pfad-Wächter des Betriebs beobachtet nur sie. So braucht eine neue Reise keinen eigenen Eintrag dort.
