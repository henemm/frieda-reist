# Kontext: fix-709-push-absender (#709)

## Anfrage

Der Product Owner bekam auf dem iPhone die Push-Nachricht „Deine neue Reise „…“ ist angelegt (Status Idee).“ mit
Titel „Frieda“ und darunter „from <Reise A>“. Frage: Warum steht die <Reise A> im Absender?

## Ursache (belegt)

- iOS schreibt unter eine Web-Push-Nachricht „from <Name>“: den Namen der Web-App auf dem Home-Bildschirm, deren
  Service Worker das Abo hält. Den Titel („Frieda“) setzt Frieda selbst.
- Bis 2.11.2026 schaltete man Push im Fuß jeder Reiseseite ein (`ea676e4`, #21). Solche Abos liegen in `push_abos`
  mit `reise = <Ordner>` und gehören der als App installierten Reiseseite (Manifest-Name = Kurzname der Reise).
- Seit Entscheidung A (2.11.2026, `7430aec`) schaltet man Push nur noch auf Mein Konto in der Frieda-App ein
  (`anmeldung.push_geraet_schalten`, Abo mit `reise = ""`, `seite = <basis>/konto`). Die Reiseseite abonniert
  nicht mehr (kein `pushManager` in `engine/vorlage.html`), der Dienst nimmt `POST /<reise>/push` aber weiter an
  (`engine/rueckmeldungen.py:1766`). Alte Reise-Abos bleiben, bis der Push-Dienst sie mit 404/410 ablehnt.
- `engine/push.py:355` `ziele(abos, reise)`: je Gerät (`geraet`, sonst `endpoint`) das Abo der betroffenen Reise,
  sonst das zuletzt aufgefrischte. Für Meldungen ohne Reise (#631, `reise = ""`) und für Meldungen einer anderen
  Reise kann so das Abo einer fremden Reiseseite gewählt werden → „from <Reise A>“.
- Die Gerätekennung (`rh-geraet` in `localStorage`) ist je Web-App eigen: Auf dem iPhone haben Frieda-App und eine
  installierte Reiseseite getrennte Speicher, also verschiedene Kennungen. Ein iPhone mit altem Reise-Abo und neuem
  Frieda-App-Abo zählt als zwei Geräte und bekommt jede Nachricht doppelt (auf dem Bildschirmfoto steht unter der
  Nachricht eine zweite).

## Betroffene Dateien

- `engine/push.py` — `ziele`, `zustellen`, `nachricht` (Titel ohne Reise: `push.titel_ohne_reise`)
- `engine/konten.py:1576` ff. — `push_abo_speichern`, `push_abos` (Reihenfolge `zuletzt DESC`)
- `engine/rueckmeldungen.py:1766` — Altweg `POST /<reise>/push` speichert weiter Reise-Abos
- `engine/anmeldung.py:496` — `push_geraet_schalten` (Abo der Frieda-App, `reise = ""`)
- `engine/tests/test_push.py:119` — `test_je_geraet_ein_abo_das_der_reise_zuerst`

## Bestehende Muster

- Auswahl je Gerät in `ziele`, Tests mit reinen Dicts.
- Meldungen ohne Reise: Spec #631 (`sammeln_ohne_reise`).

## Risiken

- Nachrichten gehen verloren, wenn ein Konto nur alte Reise-Abos hat und diese nicht mehr bedient werden.
- Doppelte Nachrichten, wenn Alt- und Neu-Abo auf demselben iPhone liegen.
- Keine Änderung am Datenformat der Reisen; `push_abos` liegt in der Kontendatenbank.

## Analysis

**Type:** Bug

**Affected Files:**
- `engine/push.py` (MODIFY): neue reine Hilfsfunktion `wirksam(abos)`: die Abos der Frieda-App (`reise == ""`), wenn das Konto mindestens eines hat, sonst alle; `zustellen` wählt die Ziele aus `wirksam(abos)`; `ziele` bleibt unverändert.
- `engine/anmeldung.py` (MODIFY): `push_karte` zählt Geräte über `push.wirksam(...)`, damit ein iPhone mit Alt- und Neu-Abo nicht als zwei Geräte erscheint.
- `engine/tests/test_push.py` (MODIFY): Fälle (a) nur App-Abos, (b) nur alte Reise-Abos (unverändert), (c) beides, Nachricht ohne Reise und zu Reise X → nur App-Abo, (d) App-Abo ohne Gerätekennung; `zustellen` mit Test-`senden`: genau ein Versand an das App-Abo, keiner an das alte; Gerätezahl auf Mein Konto.

**Scope/Risk:** 3 Dateien, ~10 LoC Code + ~40 LoC Tests. Risiko niedrig: keine Datenänderung, umkehrbar.

**Technical Approach:** Variante 2 der Bewertung. Hat ein Konto die Frieda-App mit Push (Entscheidung A, 2.11.2026), gehen alle Nachrichten nur noch über die Frieda-App: kein fremder Reisename als Absender, keine Doppelten. Konten ohne Frieda-App-Abo behalten den bisherigen Weg über alte Reise-Abos, damit niemand Nachrichten verliert. Verworfen: Variante 1 (Vorrang je Gerät) löst Doppelte und „from X“ bei Alt-Abo derselben Reise nicht, weil die Gerätekennung auf iOS je Web-App verschieden ist; Variante 3 (Alt-Abos löschen, Altweg sperren) ändert Daten und löst ohne Variante 2 nichts.

**Bewusste Folge:** Ein Gerät, das nur ein altes Reise-Abo hat, während dasselbe Konto auf einem anderen Gerät die Frieda-App mit Push nutzt, bekommt keine Push-Nachrichten mehr; dort Push in der Frieda-App einschalten. Das folgt Entscheidung A (Push nur noch in der Frieda-App) und betrifft nur Abos von vor dem 2.11.2026.

**Unverändert:** `seite_von` (Links), Mail-Rückfall in `einreihen`/Statushinweisen (`konten.push_abos` ungefiltert), Ruhezeit/Zeitzone (neuestes Abo), `push_abo_speichern`, Altweg `POST /<reise>/push`.

**Dependencies:** keine neuen. Kein Format der Reisedaten betroffen, kein `nachziehen` nötig.

**Open Questions:** keine.
