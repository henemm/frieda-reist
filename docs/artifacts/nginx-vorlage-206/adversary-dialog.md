# Adversary Dialog — nginx-vorlage-206
Spec: docs/specs/fast/nginx-vorlage-206.md
Datum: 2026-11-03

## Checkliste
- [x] AC-1: Die erzeugte Zonendatei lädt in einem echten nginx, hat genau die drei Zonen mit Instanz-Namen und geo/map mit leerem Schlüssel für eigene Adressen.
- [x] AC-2: Eine eigene Adresse wird nie mit 429 beantwortet, eine fremde (127.0.0.2) wird begrenzt.
- [x] AC-3: Die Orte nutzen die drei Zonen wie beschrieben, ohne doppelte Direktive.
- [x] AC-4: Die Lesefristen bleiben über dem längsten Schreibvorgang.
- [x] AC-5: nginx.py pruefen: 0 gleich oder nicht eingerichtet, 3 mit Befehl bei Abweichung, 1 bei Fehler; schreibt nie unter /etc.
- [x] AC-6: veroeffentlichen.sh meldet Ausgang 3 einmal je Fingerabdruck, bleibt bei Ausgang 1 grün, installiert nichts.
- [x] AC-7: Tests ohne echte Reisen grün, keine echten Adressen oder Pfade.

## Dialog

### Runde 1
**Adversary:** Erste unabhängige Gegenprüfung (implementation-validator, 3.11.2026): VERDICT AMBIGUOUS. F7 MEDIUM bis HIGH: Der Baustein hieß `<instanz>-konnektor.conf` und wäre vom Glob `<instanz>-*.conf` auch in andere Server-Blöcke (etwa den www-Block) eingebunden worden, die Orte stünden doppelt, `nginx -t` scheitert. F6 MEDIUM: Der ausgegebene Befehl installierte vor `nginx -t` und hatte keinen Rückweg. F5: Das Soll lag in einem vom Dienstbenutzer beschreibbaren Ordner und konnte zwischen Prüfen und Ausführen abweichen. F1/F2 LOW: Adressprüfung nur nach Zeichen, `0.0.0.0/0` möglich, Dateinamen-Erweiterung der Eingabe. F3 LOW: Hinweis zu vorgeschaltetem Proxy/realip. F8/F9 LOW: `Connection ""` fehlte in der .inc.
**Implementierer:** F7: Baustein heißt `<instanz>-konnektor-orte.inc` (Endung .inc, der Glob bindet ihn nicht ein; echter nginx-Test mit beiden Includes). F6 und F5: neues `nginx.py anwenden` erzeugt das Soll neu in einem Temp-Ordner, sichert die installierten Dateien, installiert, prüft mit `nginx -t`, lädt nur bei bestandener Prüfung neu und stellt sonst die Sicherung wieder her (Tests für Erfolg, Rückweg, vorher fehlende Datei). F1/F2: strenge Adressprüfung (IPv4/IPv6, kein /0, `set -f`), Tests. F3: Hinweis in docs/betrieb.md. F9: `Connection ""` in der .inc. F8 bleibt bewusst (Dienst leitet `/` auf Konto, war schon so).
Code reference: betrieb/nginx.py:84

### Runde 2
**Adversary:** Zweite unabhängige Gegenprüfung: VERDICT AMBIGUOUS, keine Datenzerstörung. Befund 1 MEDIUM: Die sudoers-Rechte des Betriebsbenutzers reichen für `install` nicht aus. Befund 2: Abbruch von Hand (Strg-C) zwischen Installation und Test ließ ungeprüfte Dateien liegen. Befund 4 LOW: Bash-Regex nimmt Unicode-Ziffern. Befund 3/5/6 LOW: Rechte beim Rückweg, Erstinstallation ohne Hinweis, unerreichbarer Absturz bei fehlender Soll-Datei.
**Implementierer:** Befund 1: `anwenden` ist als Befehl mit Root-Rechten gedacht (`sudo env … nginx.py anwenden`, bei Root ohne weiteres sudo, das Soll liegt in einem Temp-Ordner, nicht im Dienstordner); `pruefen` liest nur mit `sudo -n cat /etc/nginx/*`, was der Betriebsbenutzer bereits darf (live mit `sudo -l` geprüft). Doku angepasst. Befund 2: Rückweg bei jeder Ausnahme einschließlich Abbruch. Befund 4: `globasciiranges`, Test mit arabisch-indischen Ziffern. Befund 5: Hinweis „first installation“. Befund 3 (Rechte und Besitzer nicht einzeln wiederhergestellt) und 6 (nicht erreichbar) bleiben bewusst; Befund 3 steht in der Doku.
Code reference: betrieb/nginx.py:120

### Runde 3
**Adversary:** Dritte unabhängige Gegenprüfung auf die korrigierte Fassung: VERDICT VERIFIED, kein Befund MEDIUM oder höher. LOW: veraltete Doku zum Ort des Solls, Sicherungsordner über Symlink, der Befehl gibt nur vier Einstellungen weiter, Rechte beim Rückweg, unerreichbarer Fall fehlender Soll-Datei.
**Implementierer:** Doku zum Soll korrigiert, `anwenden` verweigert einen Symlink als Sicherungsordner (islink). Die übrigen drei LOW-Hinweise bleiben bewusst (Einstellungen gehören in die Einstellungsdatei der Instanz; Rechte sind dokumentiert; der Fall ist unerreichbar). Die ganze Suite lief grün (siehe suite.txt).
Code reference: betrieb/nginx.py:91

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict: VERIFIED

## Geprüfte Dateien

## Prüfbasis

## Geprüfte Dateien

- sha256:51cc89c2696283c2a6939820ac2eb3c0c97dbcc2ac9892df8466f8af5a03f206  betrieb/nginx.py

## Prüfbasis

- base: c403b6685dc8b6210ddbe455337e3e10a6315aa6
- blob:fa44601c8b386e547bf3688ac28252ff424daf33  betrieb/nginx.py
