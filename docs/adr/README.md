# Architektur-Entscheidungen (ADR)

Hier stehen die Entscheidungen, die die Software als Ganzes prägen, je eine Datei, fortlaufend nummeriert, nie gelöscht. Eine Entscheidung wird nicht umgeschrieben, sondern durch eine neue ersetzt, die auf die alte verweist (Status „ersetzt durch ADR-…“). Aufbau je Datei: Status, Kontext, Entscheidung, Begründung, Konsequenzen, Verlauf (nach Michael Nygard, „Documenting Architecture Decisions“, 2011); ADR-0001 hat dazu die Prüfstelle.

| Nr. | Titel | Status |
|---|---|---|
| [0001](0001-kern.md) | Der Kern von Frieda Reist: AI first, Reise-Ontologie ohne Katalog, Frieda ohne eigene KI | gilt |
| [0002](0002-atomic-design.md) | Oberfläche nach Atomic Design | gilt |
| [0003](0003-heimat.md) | Seitenordnung: jede Grundform hat genau eine Heimat | gilt |
| [0004](0004-lage.md) | Lage eines Aufenthalts: Adresse oder Koordinaten, Kartenlinks | gilt |
| [0005](0005-konten.md) | Konten und Anmeldung: eine Person, eine E-Mail-Adresse, ein Konnektor | gilt |

ADR-0001 ist zugleich die **Prüfstelle**: Jedes Issue, jedes Paket und jeder Pull Request beantwortet die zehn Fragen im Abschnitt „Prüfstelle“. Das PR-Template (`.github/pull_request_template.md`) enthält sie.
