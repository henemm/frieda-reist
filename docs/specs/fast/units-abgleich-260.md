# Mini-Spec: units-abgleich-260

Issue #260, Option B (Product Owner, 3.11.2026). PR 1 von 3: Erkennung ohne Root. Die systemd-Einheiten der Instanz werden mit
den Vorlagen verglichen; Abweichungen werden gemeldet. Installiert wird in diesem PR nichts (das Hilfsprogramm mit Root-Rechten
folgt in PR 2, der einmalige Schritt auf dem Server in PR 3).

## Was ändert sich

- `betrieb/einrichten.sh`: neuer Modus `--erzeugen` schreibt Einheiten und nginx-Bausteine nach `EI_ZIEL`, ohne Prüfungen, ohne
  Ausgabe, ohne Änderung an `/etc` (die Ersetzung der Platzhalter bleibt an einer Stelle). Ausgang 1, wenn ein Platzhalter bleibt.
- `betrieb/units.py pruefen [--json]` (nur Standardbibliothek): erzeugt die Soll-Einheiten, vergleicht Zeile für Zeile mit
  `EI_SYSTEMD` (Vorgabe `/etc/systemd/system`) und teilt die Unterschiede in erlaubt und gesperrt. Erlaubt sind nur
  `Environment=` mit Namen `FR_`/`KN_`/`RM_` und engem Wertmuster sowie `TimeoutStartSec=`, beides im Abschnitt `[Service]`
  einer `.service`-Datei. Alles andere (User, ExecStart, Rechte, Timer, nicht installierte Einheit) ist gesperrt.
  Ausgang 0 gleich, 3 nur erlaubte Abweichungen, 4 auch gesperrte, 1 Fehler.
- `betrieb/veroeffentlichen.sh`: nach einem grünen Lauf ruft ein Schritt `units.py pruefen` auf. Bei Abweichung genau eine
  Meldung `fr_melden normal` je Fingerabdruck der Abweichung (kein Alarm, kein Abbruch, kein Einfluss auf den Heartbeat).
- `docs/betrieb.md`: Abschnitt „Einheiten abgleichen“ mit Erlaubnisliste und Bedeutung der Ausgänge.

## Was darf sich nicht ändern

- `einrichten.sh` ohne Argument und mit `--installieren` verhält sich wie bisher.
- Ein Fehler im Abgleich (Skript fehlt, Ausgang 1) stoppt das Veröffentlichen nie.
- Der Abgleich schreibt nichts nach `/etc`.

## Manuelle Test-Schritte

1. Auf dem Server `FR_WURZEL=/srv/frieda-reisen/_bau frieda/betrieb/units.py pruefen`: nennt genau die Abweichung
   `FR_DIENST`/`FR_ZEITZONE` in konnektor, push, rueckmeldungen (Stand 3.11.2026), Ausgang 3.

## Acceptance Criteria

- AC-1: `einrichten.sh --erzeugen` schreibt alle Einheiten ohne Ausgabe und ohne Änderung an `/etc`.
- AC-2: `units.py pruefen` endet mit 0 bei Gleichheit, 3 bei nur erlaubten und 4 bei gesperrten Abweichungen.
- AC-3: Gesperrt sind User, ExecStart, Rechte, Timer, fremde Umgebungsnamen, Werte mit Sonderzeichen und nicht installierte Einheiten.
- AC-4: `veroeffentlichen.sh` meldet eine Abweichung genau einmal je Fingerabdruck und bleibt dabei grün; ein Fehler im Abgleich stoppt nichts.

## Inline-Test (wird während Implementierung geschrieben)

- [ ] `test_betrieb.py`: `einrichten.sh --erzeugen` schreibt alle Einheiten, Ausgang 0; mit offenem Platzhalter Ausgang 1.
- [ ] `test_betrieb.py`: gleiche Einheiten → Ausgang 0; fehlende `Environment=FR_…`-Zeile und anderes `TimeoutStartSec` → 3.
- [ ] `test_betrieb.py`: geänderte `User=`, `ExecStart=`, `Environment=` mit `$`, Leerzeichen oder fremdem Namen, Timer-Änderung,
      fehlende installierte Einheit → 4 und kein Eintrag unter „erlaubt“.
- [ ] `test_betrieb.py`: `veroeffentlichen.sh` meldet eine Abweichung einmal je Fingerabdruck und bleibt dabei grün.
- [ ] `test_betrieb.py` (`test_veroeffentlichen_unit_abgleich_fehler_stoppt_nichts`): Endet der Abgleich mit Ausgang 1, läuft das
      Veröffentlichen grün durch, pingt den Heartbeat und schickt keine Meldung `high`.
- [ ] `test_units.py` (`test_einrichten_erzeugen_schreibt_nur_nach_ei_ziel`): `--erzeugen` legt Dateien nur unter `EI_ZIEL` an;
      `EI_SYSTEMD` bleibt unberührt (leer).
