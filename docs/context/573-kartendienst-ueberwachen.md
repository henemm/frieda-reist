# Context: 573-kartendienst-ueberwachen

## Request Summary
Fällt der eigene Kartendienst (Overpass bei Bedarf, #444) dauerhaft aus, springt der Schreibweg still auf den öffentlichen
Overpass-Dienst zurück. Seit #567 steht dafür eine Zeile im Journal, aber niemand wird gewarnt. Ziel: ein dauerhafter Ausfall
fällt als Warnung (🟡, entprellt, kein `high`-Alarm, kein Incident-Agent) in `henemm-infra/scripts/monitor.sh` auf.

## Related Files
| File | Relevance |
|------|-----------|
| `engine/schreiben.py:2265-2282` (`overpass_eigen`) | schreibt die Rückfall-Zeilen auf stderr: `Own map service failed (…), falling back to public` und `Own map service answered without elements, falling back to public` |
| `engine/schreiben.py:2235-2253` (`overpass_holen`) | Teilfrist eigener Dienst, danach Rest an den öffentlichen |
| `engine/tests/test_kartendienst.py` | Tests zu AC-6 (Rückfall mit Protokollzeile) |
| `betrieb/vorlagen/kartendienst/*` | Units: `<instanz>-kartendienst.socket` (lauscht auf 127.0.0.1), `-proxy.service` (systemd-socket-proxyd, endet nach Ruhezeit), `.service` (Container, StopWhenUnneeded), `-aktualisieren.service/.timer` |
| `henemm-infra/scripts/monitor.sh:266-269, 2220-2240, 2457` | vorhandener `check_frieda_kartendienst` (nur Alter von `abdeckung.json`, Warnung ab 40 Tagen, Check-ID `frieda-reisen-kartendienst`) |
| `henemm-infra/scripts/monitor.sh:162-199, 206-214, 337-380` | `NON_CRITICAL_PREFIXES` und `NO_AGENT_PREFIXES` enthalten `frieda-reisen-`; `alert_on_change` meldet nur beim Wechsel ok→fail und zurück |
| `henemm-infra/tests/test_monitor_frieda_schreiben.py` | Testmuster: `systemctl`/`curl` als Bash-Funktionen ersetzt, Check-Funktion per `sed` aus monitor.sh geladen |

## Existing Patterns
- Frieda-Checks in monitor.sh: eigene Funktion `check_frieda_*`, Check-ID mit Präfix `frieda-reisen-` → nicht kritisch, ohne
  Agent, entprellt über `alert_on_change`; Meldungstext 🟡 mit Hinweis auf `journalctl -u … -n 50`.
- Zustandsprüfung über `systemctl is-failed/is-active --quiet <unit>` (Schreibweg-Check).
- Journal-Auswertung: `journalctl -u <unit> --since … --no-pager` (Zeile 580).
- Ohne Einrichtung (keine `abdeckung.json`) ist der Kartendienst-Check still ok.

## Dependencies
- Upstream: Wortlaut der Protokollzeile in `overpass_eigen`; Unit-Namen `frieda-reisen-kartendienst*`; Journal des
  Schreibweg-Dienstes `frieda-reisen-schreiben` (dort läuft `kartenpunkte_holen` → `overpass_holen`).
- Downstream: Telegram-Warnung über `$NOTIFY` (einmal je Störung), Statusausgabe `monitor.sh --status`.

## Existing Specs
- `docs/specs/betrieb/eigener-kartendienst-444.md` (AC-6 Rückfall, Start bei Bedarf, Risiken)
- `docs/specs/betrieb/kartendienst-diagnose-567.md` (Known Limitations: Überwachung Out of Scope → dieses Issue)

## Risks & Considerations
- **Keine aktive Probe gegen den Socket:** Ein Aufruf startet Proxy und Container (rund 1,6 GiB beim Einspielen, Overpass im
  Betrieb deutlich darunter, aber spürbar); alle 5 Minuten würde der Dienst nie ruhen. Bereitschaft also nur passiv prüfen:
  Socket lauscht, Container- und Proxy-Unit nicht `failed`.
- **Häufung statt Einzelfall:** Ein einzelner Rückfall (Kaltstart, Zeitüberschreitung bei großer Abfrage) ist normal. Gewarnt
  wird erst ab einer Schwelle in einem Zeitfenster; ohne Abfragen gibt es keine Zeilen und keine Betroffenen.
- **Kopplung an den Wortlaut:** Ändert jemand die englische Zeile in `overpass_eigen`, verstummt der Check still. Gegenmittel:
  gemeinsames Präfix `Own map service` als Vertrag, in der Engine per Test festgehalten und im Kommentar benannt.
- Live-Stand 14.11.2026: Socket `listening`, Container/Proxy `inactive dead` (Ruhe), 0 Rückfall-Zeilen in 14 Tagen.
- Zwei Repos: Check und Test in `henemm-infra` (eigenes Issue dort), Vertrag/Test/Doku in `frieda-reist`.
- Instanzunabhängigkeit: Unit-Namen `frieda-reisen-*` stehen in monitor.sh schon fest (Infra-Repo, kein Verstoß gegen die
  Regel „nichts Instanzspezifisches in der Engine“).

## Analysis

### Type
Feature (Betriebsüberwachung, zwei Repos)

### Befunde aus der Prüfung (14.11.2026)
- Die Abfrage an den Kartendienst läuft im Prozess des **Schreibwegs** (`frieda-reisen-schreiben`, `schreiben.py:2317`
  `overpass_holen`), nicht im Konnektor; `docs/betrieb.md:500` sagt „Protokoll des Konnektors“ → richtigstellen.
- `server-monitor.service` läuft als `root` → `journalctl -u frieda-reisen-schreiben` ist lesbar.
- Ein gelungener Zugriff auf den eigenen Dienst hinterlässt heute **keine** Zeile. Allein aus Rückfall-Zeilen lässt sich nicht
  sagen, ob der Dienst nach einer Häufung wieder geht; eine Warnung könnte erst nach Ablauf des Zeitfensters enden.
- `alert_on_change` entprellt je Check-ID; zwei Bedingungen unter derselben ID überschreiben sich gegenseitig → eigene ID.
- Live: Socket `active`, Proxy/Container `inactive` (Ruhe), 0 Zeilen in 14 Tagen.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/schreiben.py` (`overpass_eigen`) | MODIFY | dritte Zeile bei Erfolg: `Own map service answered (<n> elements)`; Kommentar: Präfix `Own map service` ist Vertrag mit monitor.sh |
| `engine/tests/test_kartendienst.py` | MODIFY | Erfolgszeile festhalten; alle drei Formen beginnen mit `Own map service` (Vertrag) |
| `docs/betrieb.md` (Abschnitt Eigener Kartendienst) | MODIFY | Protokoll des Schreibwegs statt Konnektor; Erfolgszeile; Überwachung durch monitor.sh beschreiben |
| `docs/specs/betrieb/kartendienst-ueberwachen-573.md` | CREATE | Spec |
| `henemm-infra/scripts/monitor.sh` | MODIFY | neue Funktion `check_frieda_kartendienst_bereit`, Check-ID `frieda-reisen-kartendienst-bereit`, Aufruf in der Check-Liste |
| `henemm-infra/tests/test_monitor_frieda_kartendienst_bereit.py` | CREATE | Tests mit ersetzten `systemctl`/`journalctl` (Muster `test_monitor_frieda_schreiben.py`) |
| henemm-infra Issue | CREATE | Nachvollziehbarkeit des Infra-Anteils |

### Scope Assessment
- Files: 6 (3 frieda-reist Code/Tests/Doku + Spec, 2 henemm-infra)
- Estimated LoC: frieda-reist ca. +40/-3, henemm-infra ca. +60 Check, +120 Tests
- Risk Level: LOW — nur eine zusätzliche Protokollzeile im Engine-Code, Check ist Warnung (🟡), ohne Agent, entprellt

### Technical Approach (Entscheidung Tech Lead)
Passive Prüfung, nie eine aktive Probe gegen den Socket (würde Proxy und Container starten und die Ruhezeit verhindern).
Check `check_frieda_kartendienst_bereit` je Lauf:
1. Keine `abdeckung.json` → still ok (wie der vorhandene Check).
2. **Bereitschaft der Einheiten:** `frieda-reisen-kartendienst.socket` nicht `active` oder Proxy-/Container-Einheit `failed`
   → Warnung „eigener Kartendienst nicht bereit (<Einheit>)“. `inactive` bei Proxy/Container ist der Ruhezustand, kein Fehler.
3. **Verlauf der Zugriffe:** Zeilen mit `Own map service` aus dem Journal des Schreibwegs der letzten 24 h. Sind die letzten
   **3** Zugriffe alle Rückfälle → Warnung „eigener Kartendienst fiel bei den letzten 3 Abfragen aus, öffentlicher Dienst trägt
   – journalctl -u frieda-reisen-schreiben -n 50“, mit dem Grund der jüngsten Zeile (gekürzt). Ist die jüngste Zeile ein
   Erfolg, oder gibt es weniger als 3 Zugriffe → ok. Ein einzelner Rückfall (Kaltstart, große Abfrage) warnt nie.
4. Ende der Warnung: sobald ein Zugriff wieder gelingt (Erfolgszeile) oder keine Rückfälle mehr im Fenster liegen und die
   Einheiten bereit sind; `alert_on_change` sendet dann einmal ✅.
Schwelle 3 und Fenster 24 h als Variablen oben in monitor.sh (`FRIEDA_KARTEN_RUECKFALL_SCHWELLE`, `…_FENSTER`).
Engine: Erfolgszeile ist nötig, damit Punkt 3/4 „wieder gesund“ erkennen. Geringes Volumen (je Kartenabfrage eine Zeile,
Abfragen sind selten). Wortlaut englisch wie die übrigen Protokollzeilen, ohne Adresse.

### Dependencies
- Vertrag: Präfix `Own map service` und die Formen `failed (…)`, `answered without elements`, `answered (<n> elements)`.
- Unit-Namen `frieda-reisen-kartendienst{.socket,-proxy.service,.service}`, `frieda-reisen-schreiben`.
- Reihenfolge: zuerst Engine (Erfolgszeile) ausliefern, dann Check; der Check ist auch ohne Erfolgszeile sicher
  (er warnt dann nur länger, bis das Fenster abläuft).

### Open Questions
- keine Produktentscheidung offen (Schwelle/Fenster sind Betriebsdetails, Tech Lead).
