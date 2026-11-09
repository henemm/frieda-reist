# Adversary Dialog — fix-445-nginx-orte-meldung
Spec: docs/specs/betrieb/wegepruefung-ohne-alarm-445.md
Datum: 2026-11-09 15:05

## Checkliste
- [x] **AC-1:** Fehlt mindestens ein Konnektor-Pfad, gibt `wege_pruefen` die Warnzeile samt Pfadliste im Protokoll aus (Text unverändert) und ruft `FR_MELDEN` nicht auf.
- [x] **AC-2:** Sind alle Pfade da (auch nach 429 mit Wiederholung), bleibt die Ausgabe leer und es gibt keine Meldung (Verhalten unverändert).
- [x] **AC-3:** `wege_pruefen` endet unverändert mit Ausgang 0; kein Aufrufer (`deploy.sh`, `veroeffentlichen.sh`) bricht durch die Änderung.
- [x] **AC-4:** `monitor.sh` prüft die Konnektor-Pfade (Kopf `X-Frieda`) als Warnung; ein fehlender Pfad löst keinen kritischen Alarm aus und entprellt wie `check_frieda_seiten`.
- [x] **AC-5:** Live-Server (nginx nachziehen): in dieser Prüfung nicht Gegenstand, folgt als Live-Schritt nach dem Vorspulen.
- [x] **AC-6:** MQ-Nachrichten erledigen: Live-Schritt, nicht Gegenstand dieser Prüfung.
- [x] **AC-7:** `docs/betrieb.md` beschreibt den neuen Meldeweg (Warnung im Protokoll, Issue durch nginx-Abgleich, Teil-Check in `monitor.sh`).

## Dialog

### Runde 1
**Adversary:** Tests: `pytest -q test_betrieb.py test_nginx.py -n 3` -> 163 passed, 0 failed. `bash -n` für gemeinsam.sh und monitor.sh sauber.
- AC-1: In `wege_pruefen` (betrieb/gemeinsam.sh) kein `fr_melden` mehr, Warnzeilen textgleich; Test prüft `not meldungen.exists()`.
- AC-2: Test mit dreimal 429, dann Kopf: leere Ausgabe, keine Meldedatei, genau 4 Versuche.
- AC-3: Letztes Kommando ist `echo` (Ausgang 0); Aufrufer deploy.sh:123, veroeffentlichen.sh:244/:590 unverändert behandelt; kein anderer fr_melden-Pfad in wege_pruefen.
- AC-4: Pfadliste in monitor.sh identisch (9 Pfade), Präfix `frieda-reisen-` steht in NON_CRITICAL_PREFIXES, entprellt über Streak und alert_on_change; 429 gilt als "Ort da"; leere Antwort zählt als fehlend (nur Warnung).
- AC-7: docs/betrieb.md nennt den neuen Meldeweg.
- F001 (LOW): sehr lange Kommentarzeile in gemeinsam.sh.
- F002 (LOW): Pfadliste in monitor.sh muss manuell synchron gehalten werden, kein Test.
**Implementierer:** F001 behoben (Kommentar umbrochen, `bash -n` sauber). F002: im Kommentar von monitor.sh benannt; Test über Repo-Grenze nicht sinnvoll, akzeptiert.

### Runde 2
**Adversary:** Gegenprobe: Der monitor.sh-Check läuft im Status-Modus gegen den Live-Server und meldet alle Pfade erreichbar; der Umbruch des Kommentars ändert keinen Code. Keine weiteren Befunde.
**Implementierer:** keine Rückmeldung nötig.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Findings

Finding:
  ID: F001 (behoben)
  Severity: LOW
  Category: anti_pattern
  Code reference: betrieb/gemeinsam.sh:146
  Description: Kommentar zu einer sehr langen Zeile angewachsen.
  Spec requirement: keine
  Conflict: Lesbarkeit
  Remediation: umbrechen (erledigt)

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: henemm-infra scripts/monitor.sh check_frieda_konnektor_orte
  Description: Pfadliste doppelt geführt (gemeinsam.sh und monitor.sh), kein Test.
  Spec requirement: AC-4
  Conflict: mögliches Auseinanderlaufen
  Remediation: Kommentar nennt die Quelle; akzeptiert

## Verdict
**VERIFIED**

## Geprüfte Dateien

- sha256:31bfd7869978514318d9c031a8c50338fad91a1267631fa06b63055c31dc796a  betrieb/gemeinsam.sh

## Prüfbasis

- base: 23dd45fae1cf915a1e2f31ff44d13302e5d2e2b1
- blob:d0479be966f7f45e8a23854364830375b1e5c937  betrieb/gemeinsam.sh

## Geprüfte Dateien

- sha256:31bfd7869978514318d9c031a8c50338fad91a1267631fa06b63055c31dc796a  betrieb/gemeinsam.sh

## Prüfbasis

- base: 23dd45fae1cf915a1e2f31ff44d13302e5d2e2b1
- blob:d0479be966f7f45e8a23854364830375b1e5c937  betrieb/gemeinsam.sh
