# ADR-0005: Konten und Anmeldung: eine Person, eine E-Mail-Adresse, ein Konnektor

Status: gilt · Entschieden vom Product Owner am 27.10.2026 (Paket J, Issue #43; Grundsätze in `docs/konten.md`) · Als ADR festgehalten am 29.10.2026 (Abgleich, `docs/abgleich-2026-10-29.md`)

Steht unter [ADR-0001](0001-kern.md): Der Konnektor ist die Tür; dieses ADR sagt, wer durch sie geht und woran Frieda die Person erkennt.

## Kontext

Bis Paket J erkannte Frieda Menschen nur an geheimen Links: je Reise und Person ein Link für die Claude-App, ein geheimer Link für die Webseite, ein Konto-Link zum Anlegen neuer Reisen. Wer einen Link verlor oder das Claude-Konto wechselte, stand draußen; über Reisen hinweg gab es keine Identität, und jede Entscheidung hing an einem Link statt an einer Person.

## Entscheidung

1. **Ein Konto je Mensch,** erkannt an der E-Mail-Adresse (höchstens ein Konto je Adresse), mit fester, unsichtbarer Kennung (`K-…`), auf die Mitgliedschaften und Verlauf verweisen. Anmelden ohne Passwort: ein sechsstelliger Code per Mail, zehn Minuten gültig, einmal, höchstens fünf Versuche.
2. **Ein Konnektor für alle Reisen** („Frieda“, `<FR_BASIS>/mcp`, OAuth 2.1 mit PKCE): Beim Verbinden meldet sich die Person an; jedes Reise-Werkzeug nennt die Reise. Links je Reise und Person bleiben als Übergang lesbar, werden aber nicht mehr ausgestellt.
3. **Einladen per E-Mail-Adresse** (`person_einladen` mit `email`): Die Rolle gilt sofort in `reise.yaml`, die Einladung kommt per Mail; eine Person, die schon in der Reise steht, wird so mit ihrem Konto verknüpft. `person_entfernen` nimmt sie heraus (Gast, reist nicht; niemand wird gestrichen).
4. **Die Rolle gehört zur Reise, die Identität zum Konto.** Rollen stehen weiter je Reise in `reise.yaml` (ADR-0001, Punkt 6); das Konto sagt nur, wer spricht. Jede Entscheidung, jeder Schreibvorgang und jeder Beleg hängt damit an einem Menschen, nicht an einem Link.
5. **Reisen anlegen** darf ein Konto erst nach Freischaltung durch den Betreiber (`reise_anlegen`, sonst `reisen_anlegen_anfragen`); Belege zu Buchungen hängt man nur angemeldet an (Product Owner 29.10.2026).

## Begründung

- Die Herkunft jeder Aussage und die Person jeder Entscheidung (ADR-0001, Fragen 5 und 6) brauchen eine Identität, die ein verlorener Link nicht bietet.
- Eine Adresse ohne Passwort ist für Mitreisende ohne technisches Interesse der kleinste Aufwand; der Code per Mail bleibt sicher genug für eine private Reisegruppe.
- Ein Konnektor für alle Reisen erspart je Reise einen Eintrag in der Claude-App und macht die Übernahme von Arten einer früheren Reise (`arten_uebernehmen`) überhaupt erst zuordenbar.

## Konsequenzen

- `engine/konten.py` (Konten, Mitgliedschaften), `engine/anmeldung.py` (Anmeldung im Web, Sitzung), `engine/oauth.py` (Konnektor), Betrieb mit eigener Adresse und Mailversand (`docs/betrieb.md`, `docs/konten.md`).
- `docs/konnektor.md` beschreibt beide Wege; der Link je Reise ist der Übergang, das Konto der Regelfall.
- Was eine Rolle darf, prüft weiter der Code (`engine/reise.py`); das Konto ändert daran nichts.

## Verlauf

- 27.10.2026: Grundsätze vom Product Owner entschieden (`docs/konten.md`), Pakete J1 bis J3 gebaut.
- 29.10.2026: Als ADR festgehalten (Abgleich), weil Paket J „die Tür“ aus ADR-0001 verändert hat.
