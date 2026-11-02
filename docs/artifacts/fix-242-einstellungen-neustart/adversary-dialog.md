# Adversary Dialog — fix-242-einstellungen-neustart
Spec: docs/specs/betrieb/veroeffentlichen-neustart-242.md
Datum: 2026-11-02 19:16

## Checkliste
- [x] **Input:** ein Lauf von `veroeffentlichen.sh`, dessen `git merge` die Einstellungsdatei ändert (oder `FR_EINSTELLUNGEN` zeigt auf eine Datei, die sich während des Laufs ändert).
- [x] **Output:** eine Protokollzeile über den Neustart, danach ein normaler Lauf mit den neuen Werten.
- [x] **Side effects:** höchstens ein `exec` je Lauf; keine neuen Dateien, keine neue Schnittstelle.
- [x] AC-1 bis AC-10 (siehe „Beweise je AC“)

Belege: `engine/.venv/bin/python -m pytest -q engine/tests/test_betrieb.py` → 95 passed; ganze Suite `engine/tests` → 964 passed, 0 failed. Eigene Zusatztests des Adversary (Scratchpad, nicht im Repo): 6 passed.

## Dialog

### Runde 1
**Adversary:** (1) Überleben abgeleitete Werte aus der Datei den `exec`?
**Implementierer:** Shell-Experiment mit `gemeinsam.sh`: Aufrufwerte (`FR_WURZEL`, `FR_TITEL`, `KN_BASIS`, leer gesetztes `FR_LEER`) bleiben, `_aufruf_namen` bleibt unverändert; aus der Datei stammende und abgeleitete Werte (`FR_ADRESSE`, `FR_KN_ADRESSE`, `FR_SEITEN`, `FR_DIENST`, `RM_ABLAGE`) werden neu gebildet.
Code reference: betrieb/gemeinsam.sh:17-27

**Adversary:** Im echten Lauf: kommen `FR_SEITEN`/`FR_DIENST`/`FR_KONNEKTOR` aus der Datei bei der Deploy-Attrappe neu an?
**Implementierer:** Eigener Test ohne `FR_DIENST` und `FR_KONNEKTOR` im Aufruf: Die Attrappe sieht `FR_SEITEN`, `FR_DIENST`, `KN_SEITEN`, `RM_ABLAGE`, `FR_KONNEKTOR` mit den neuen Werten. PASSED.
Code reference: betrieb/veroeffentlichen.sh:321-329

**Adversary:** (2) Werden Aufrufwerte oder `FR_WURZEL`/`FR_EINSTELLUNGEN` entfernt?
**Implementierer:** Nein. `compgen -e` erfasst vor dem ersten Einlesen alles Exportierte; `test_veroeffentlichen_wert_aus_dem_aufruf_gewinnt_auch_nach_dem_neustart` PASSED.
Code reference: betrieb/gemeinsam.sh:18, betrieb/gemeinsam.sh:24-25

**Adversary:** (3) Endlosschleife oder zweiter Neustart, auch nach `nachlauf()`?
**Implementierer:** Prüfsummen nach dem `exec` gleich, dazu der Merker `_neugestartet`. Eigener Test: Deploy kündigt einen weiteren Stand mit geänderter Datei an; je Lauf genau ein Neustart, danach Ende (Deploy-Protokoll v2,v2,v3,v3). `test_veroeffentlichen_startet_hoechstens_einmal_neu` PASSED.
Code reference: betrieb/veroeffentlichen.sh:321-329, betrieb/veroeffentlichen.sh:427

**Adversary:** (4) Relative `FR_EINSTELLUNGEN` und relativer `$0`?
**Implementierer:** Eigener Test mit relativem Skriptpfad und relativer Datei: Rückgabe 0, ein Neustart, neue Adresse sichtbar.
Code reference: betrieb/veroeffentlichen.sh:277-278, betrieb/veroeffentlichen.sh:324-328

**Adversary:** (5) Nicht lesbare Datei, `set -euo pipefail`-Fallen?
**Implementierer:** `einstellungen_summe` prüft mit `-r`; unlesbare und fehlende Datei: Rückgabe 0, kein Neustart. `compgen … || true` und `grep … || true` sind abgesichert.
Code reference: betrieb/veroeffentlichen.sh:61-64, betrieb/gemeinsam.sh:18, betrieb/gemeinsam.sh:24

**Adversary:** (6) Argumente mit Leerzeichen?
**Implementierer:** `exec "$0" "$@"` ist gequotet; Test mit `--immer "a b" c`: ein Neustart, Rückgabe 0.
Code reference: betrieb/veroeffentlichen.sh:328

**Adversary:** (8) Sperre (fd 9) beim `exec`?
**Implementierer:** Der neue Prozess nimmt die Sperre erneut (`exec 9>`, `flock -n 9`); Neustartläufe bauen und beenden sich normal. Der Merker `veroeffentlichen-nochmal` ist unkritisch, weil der Neustart den neuen Stand erst danach holt.
Code reference: betrieb/veroeffentlichen.sh:293-300

### Runde 2
**Adversary:** (7) Wirkung auf `deploy.sh`, `freischalten.sh`, `waechter.sh`, `einrichten.sh`, die `gemeinsam.sh` ebenfalls einlesen?
**Implementierer:** In Kindprozessen ist `_aufruf_namen` schon gesetzt und wird nicht neu gebildet; nur `veroeffentlichen.sh` ruft `fr_aufraeumen`. Kein Regressionsrisiko gefunden; Tests zu diesen Skripten grün.
Code reference: betrieb/gemeinsam.sh:17-20

**Adversary:** `_aufruf_namen` kommt veraltet aus einer Eltern-Shell.
**Implementierer:** Nur in einer Hand-Shell nach `source gemeinsam.sh` herstellbar, kein Rückschritt gegenüber vorher (F001, LOW).

**Adversary:** Zeitfenster zwischen Sourcen von `gemeinsam.sh` und der Prüfsumme „vorher“.
**Implementierer:** Millisekunden, durch die Sperre ausgeschlossen; der nächste Lauf holt es nach (F002, LOW).

**Adversary:** `exec` scheitert nach dem Aufräumen.
**Implementierer:** Der Lauf bricht ab, die Trap `nachlauf` leitet den Exit-Code weiter, der Timer wiederholt. Kein Datenverlust.

**Adversary:** Test 8 prüft nur per Textsuche.
**Implementierer:** Der Code verwendet `_aufruf_namen` und `_neugestartet` (ohne Präfix); der Test ist schwach, aber spec-konform (F003, LOW).

## Beweise je AC
- **AC-1 CONFIRMED.** `test_veroeffentlichen_uebernimmt_geaenderte_einstellungen_im_selben_lauf` PASSED. Code reference: betrieb/veroeffentlichen.sh:321-329, betrieb/gemeinsam.sh:22-27
- **AC-2 CONFIRMED.** `test_veroeffentlichen_wert_aus_dem_aufruf_gewinnt_auch_nach_dem_neustart` PASSED. Code reference: betrieb/gemeinsam.sh:17-20
- **AC-3 CONFIRMED.** `test_veroeffentlichen_unveraenderte_einstellungen_starten_nicht_neu` PASSED. Code reference: betrieb/veroeffentlichen.sh:323
- **AC-4 CONFIRMED.** `test_veroeffentlichen_startet_hoechstens_einmal_neu` PASSED, dazu Nachlauf-Experiment. Code reference: betrieb/veroeffentlichen.sh:323, betrieb/veroeffentlichen.sh:327, betrieb/veroeffentlichen.sh:427
- **AC-5 CONFIRMED.** `test_veroeffentlichen_neustart_behaelt_immer` PASSED. Code reference: betrieb/veroeffentlichen.sh:328
- **AC-6 CONFIRMED.** `test_veroeffentlichen_einstellungen_ausserhalb_des_repos_starten_nicht_neu` PASSED. Code reference: betrieb/veroeffentlichen.sh:277-278, betrieb/veroeffentlichen.sh:312
- **AC-7 CONFIRMED.** Test `…_ist_eine_aenderung[neu]` und `[entfernt]` PASSED. Code reference: betrieb/veroeffentlichen.sh:61-64
- **AC-8 CONFIRMED.** Merker `_aufruf_namen`, `_neugestartet` ohne `FR_`; `test_interne_merker_haben_kein_fr_praefix` und `test_beispiel_einstellungen_sind_vollstaendig` PASSED. Code reference: betrieb/gemeinsam.sh:17-24, betrieb/veroeffentlichen.sh:323-327
- **AC-9 CONFIRMED.** Zweig „Stand unverändert“ liegt vor dem Vorspulen; bisherige Tests grün (95/95). Code reference: betrieb/veroeffentlichen.sh:312-329
- **AC-10 CONFIRMED.** Suite 964 passed; `docs/betrieb.md` ergänzt. Code reference: betrieb/veroeffentlichen.sh:323-329

## Findings (alle LOW, nicht blockierend)
- F001 (betrieb/gemeinsam.sh:17): veralteter `_aufruf_namen` aus einer Eltern-Shell; nur Hand-Shell nach `source`, kein Rückschritt.
- F002 (betrieb/veroeffentlichen.sh:312): Millisekunden-Fenster zwischen Sourcen und Prüfsumme „vorher“, durch Sperre ausgeschlossen.
- F003 (engine/tests/test_betrieb.py:430): Test 8 prüft nur per Textsuche; indirekt durch die Neustart-Tests belegt.

## Herkunft der Vorbedingungen
Kein Sprachprofil konfiguriert (`precondition_origins.default_lang`). Von Hand geprüft:

| Feld | Produktions-Schreibstellen | Bedingung davor | Test für diesen Weg |
|------|---------------------------|-----------------|---------------------|
| `_aufruf_namen` | `betrieb/gemeinsam.sh:18` | nur wenn noch nicht gesetzt (erster Prozess des Laufs, vor `fr_einlesen`) | `test_veroeffentlichen_uebernimmt_geaenderte_einstellungen_im_selben_lauf`, `test_veroeffentlichen_wert_aus_dem_aufruf_gewinnt_auch_nach_dem_neustart` |
| `_neugestartet` | `betrieb/veroeffentlichen.sh:326` (setzen), `betrieb/veroeffentlichen.sh:427` (löschen) | Setzen nur bei abweichender Prüfsumme und fehlendem Merker; Löschen nur, wenn während des Laufs ein neuer Stand ankam | `test_veroeffentlichen_startet_hoechstens_einmal_neu`; Nachlauf-Experiment des Adversary |

Code reference: betrieb/gemeinsam.sh:17-27
Code reference: betrieb/veroeffentlichen.sh:61-64
Code reference: betrieb/veroeffentlichen.sh:277-278
Code reference: betrieb/veroeffentlichen.sh:312
Code reference: betrieb/veroeffentlichen.sh:323-329
Code reference: betrieb/veroeffentlichen.sh:427
Code reference: engine/tests/test_betrieb.py:430

## Verdict
**VERIFIED**

Alle zehn ACs belegt, alle Angriffspunkte halten, drei LOW-Anmerkungen, keine Regression (Suite 964 passed).

## Geprüfte Dateien

- sha256:2a7f8db7f8aa1d4f0c8b7e19b154ce692b05a30deee4adf6723987b58adcfce0  betrieb/gemeinsam.sh
- sha256:87d117f1b0d507df41cf58c8b8e4c482da874c35b6f8b3d3fbd1ff2a662bc6eb  betrieb/veroeffentlichen.sh
- sha256:3b8654a60927e547e43f23dae69d0cc01ac340ddc97f7aa5d900c30346e64461  engine/tests/test_betrieb.py

## Prüfbasis

- base: 71bb27794a9d4c621637de872131940203399a60
- blob:e7c7088422d97a21ab593665891ff8dce3e4f5ec  betrieb/gemeinsam.sh
- blob:49903ede765021119f9a14672132d942034ad176  betrieb/veroeffentlichen.sh
- blob:5242c9988250c0cff5dd9550a0c516b36b4efb4b  engine/tests/test_betrieb.py
