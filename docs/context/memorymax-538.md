# Context: memorymax-538

## Request Summary
Die vier Dauerdienste der Instanz (Rückmeldedienst, Konnektor, Schreibweg, Push) laufen ohne Speichergrenze. Ein Speicherleck
in einem Dienst träfe den ganzen Server. Vorschlag im Issue: `MemoryMax=512M` für alle vier, dazu die Erlaubnisliste `ERLAUBT`
um `("Service", "MemoryMax")` mit engem Wertmuster ergänzen, damit der automatische Einheiten-Abgleich die Zeile installieren darf.

## Related Files
| File | Relevance |
|------|-----------|
| betrieb/vorlagen/{rueckmeldungen,konnektor,schreiben,push}.service | bekommen die neue Zeile |
| betrieb/units.py | `ERLAUBT` (Zeile 29), `DAUERDIENSTE`, Abgleich `abgleich()`; Kopfkommentar nennt die erlaubten Zeilen |
| betrieb/vorlagen/units-installieren.py | Hilfsprogramm mit Root-Rechten, eigenes `ERLAUBT` (Zeile 35), muss gleich sein |
| engine/tests/test_units.py | Zeile 117 prüft die Menge von `ERLAUBT` exakt; Zeile 223–228 Gleichheit mit dem Hilfsprogramm; Zeile 62 gesperrte Zeilen |
| engine/tests/test_units_helfer.py | Tests des Hilfsprogramms (ohne root) |
| engine/tests/test_betrieb.py | Prüfungen der Vorlagen (z. B. TimeoutStartSec Zeile 2142) |
| docs/betrieb.md | Abschnitt „Einheiten abgleichen (#260)“, Zeilen 418–443: Liste der erlaubten Zeilen, „neuer Eintrag ist Sicherheitsentscheidung des PO“, Helfer muss nach Änderung bewusst erneuert werden |
| betrieb/einrichten.sh | erzeugt Units und Helfer (Zeile 152), `--installieren` installiert Helfer/sudoers (Zeile 249) |
| engine/schreiben.py:5664–5693 | Schreibweg startet `veroeffentlichen.sh` per `Popen(start_new_session=True)` — läuft **in der cgroup des Schreibdienstes** |
| engine/konnektor.py:553–595 | Konnektor startet Node + Playwright-Chromium für `seite_ansehen` — ebenfalls in seiner cgroup |

## Existing Patterns
- Erlaubte Unit-Zeilen: Tupel (Abschnitt, Schlüssel) → enges Regex, identisch in `units.py` und Hilfsprogramm, Test erzwingt Gleichheit.
- `TimeoutStartSec` ist das Vorbild: Wert mit Einheit, Muster `^[1-9][0-9]{0,4}(?:s|min|h)?$`.
- Sandbox-Zeilen (Rechte) sind bewusst nicht in der Liste; nur „einschränkende“ Zeilen kämen in Frage.

## Messung auf dem Server (17.11.2026, Spitzenwerte der letzten 60 Tage aus dem Journal, „memory peak“)
| Dienst | aktuell | höchster Spitzenwert |
|--------|---------|----------------------|
| rueckmeldungen | 18 MiB | 42 MiB |
| push | 59 MiB | 73 MiB |
| konnektor | 45 MiB | **326 MiB** (Chromium für das Seitenbild) |
| schreiben | 66 MiB | **3,4 GiB** (angestoßenes Veröffentlichen mit pytest -n, Playwright, Bau — läuft in seiner cgroup) |

## Dependencies
- Upstream: systemd (MemoryMax wirkt auf die ganze cgroup inkl. Kindprozesse; bei Überschreitung OOM-Kill in der cgroup).
- Downstream: `veroeffentlichen.sh` nach grünem Lauf → `units.py pruefen/installieren` → Hilfsprogramm mit sudo.

## Existing Specs
- docs/specs/units-meldung-doppelte-liste-306.md (Einheiten-Abgleich, Meldung)

## Risks & Considerations
- **512M für alle vier ist falsch:** Der Schreibweg würde jedes angestoßene Veröffentlichen (bis 3,4 GiB) per OOM abschießen;
  der Konnektor liegt mit Chromium schon bei 326 MiB, bei großen Seiten knapp. Grenzen je Dienst nach Messung, oder das
  Veröffentlichen aus der cgroup des Schreibdienstes lösen (eigene Einheit/`systemd-run` braucht Rechte → gesperrt).
- **Henne-Ei:** Das installierte Hilfsprogramm hat die alte Erlaubnisliste. Solange es nicht erneuert ist, ist die neue Zeile eine
  gesperrte Abweichung (eine normale Meldung). Erneuern = Root-Schritt `einrichten.sh --installieren` (Claude hat sudo auf diesem
  Server; laut docs/betrieb.md „bewusst erneuern“). Bei anderen Instanzen ein einmaliger Schritt je Instanz.
- Neuer Eintrag in `ERLAUBT` ist laut docs/betrieb.md eine Sicherheitsentscheidung des Product Owners → Freigabe der Spec.
- Alternative ohne Erlaubnisliste: Zeile nur über `einrichten.sh --installieren` (gesperrte Abweichung bis zum Root-Schritt) —
  vermeidet die Sicherheitsentscheidung, aber jede künftige Wertänderung braucht wieder Root.
- `MemoryHigh` (weiche Drossel) statt/zusätzlich zu `MemoryMax` (harte Grenze) erwägen; Swap: `MemorySwapMax` bleibt offen.
- Wertmuster eng: z. B. `^[1-9][0-9]{0,4}[MG]$`, kein `infinity`, keine Prozentwerte.

## Analysis

### Type
Feature (Härtung des Betriebs)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| betrieb/vorlagen/{rueckmeldungen,konnektor,schreiben,push}.service | MODIFY | `MemoryHigh`, `MemoryMax`, `MemorySwapMax` je Dienst mit Kommentar (Spitze, Messdatum) |
| betrieb/units.py | MODIFY | `ERLAUBT` um drei Schlüssel, Kopfkommentar |
| betrieb/vorlagen/units-installieren.py | MODIFY | gleiche Einträge (Test erzwingt Gleichheit), Kopfkommentar |
| engine/tests/test_units.py | MODIFY | Z. 117 feste Namensliste erweitern; Wertmuster gut/schlecht |
| engine/tests/test_units_helfer.py | MODIFY | Helfer nimmt nur gültige Werte; installiert reine Grenz-Abweichung |
| engine/tests/test_betrieb.py | MODIFY | jede Dauerdienst-Vorlage trägt die Grenzen, High < Max; `veroeffentlichen.service` bleibt ohne Grenze |
| docs/betrieb.md | MODIFY | „Einheiten abgleichen (#260)“: erlaubte Zeilen; neuer Absatz „Speichergrenzen (#538)“ mit Werten und Nachmessen |
| docs/specs/betrieb/dienstrechte-552.md | MODIFY | Entscheidung 8: Abgrenzung, Ressourcengrenzen sind keine Sandbox-Werte |

Keine Änderung: einrichten.sh (kopiert Vorlagen per sed), messlauf-schreibweg.py, DAUERDIENSTE, veroeffentlichen.sh.

### Scope Assessment
- Files: ~9
- Estimated LoC: +150/-5
- Risk Level: LOW (nur einschränkende Zeilen; schlimmster Fall: ein Dienst wird bei echtem Leck neu gestartet)

### Befunde aus der Analyse
- Der Anstoß des Veröffentlichens (schreiben.py:5686, `Popen(start_new_session=True)`) bleibt in der cgroup von `schreiben`
  → 3,4 GiB Spitze gehören dem Veröffentlichen, nicht dem Schreibweg. Bei OOM-Kill: kein Fehler an den Aufrufer, `flock` frei,
  der Timer (alle 5 min) holt nach.
- Gesperrte Abweichung erzeugt in `veroeffentlichen.sh units_abgleichen` (~Z. 1315) genau eine normale Meldung, entprellt über
  Merker `units-gemeldet`, kein Alarm. Bei Ausgang 4 (gemischt) werden auch erlaubte Zeilen nicht installiert — Bestand, vertretbar.
- **Swap ist aktiv** (2 GiB Swapfile, 17.11.2026 zu 1,6 GiB belegt). In cgroup v2 begrenzt `MemoryMax` nur RAM; ein Leck wiche
  in den Swap aus und träfe den Server trotzdem. Deshalb zusätzlich `MemorySwapMax` je Dienst.
- Konnektor: Chromium-Enkel können als Waisen in der cgroup überleben (subprocess.run tötet nur das direkte Kind) — die Grenze fängt das.
- Nebenbefunde (nicht Teil von #538): Anstoß-Lauf erbt `NoNewPrivileges=yes` (bekannt, #465); ein Neustart von `schreiben`
  tötet ein laufendes angestoßenes Veröffentlichen mit (KillMode=control-group).

### Variantenvergleich
| Variante | Schutz | Risiko | Urteil |
|----------|--------|--------|--------|
| A 512M für alle (Issue-Vorschlag) | gut für 3 Dienste | Veröffentlichen aus dem Schreibweg würde bei jedem Speichern abgeschossen | verworfen |
| B Grenze je Dienst nach Messung | gut | gering | Basis |
| C B + `MemoryHigh` (weich vor hart) | gut, drosselt vor dem Kill | gering | **gewählt**, plus `MemorySwapMax` |
| D Veröffentlichen aus der cgroup lösen | am besten (schreiben dann eng) | mittel, neue Unit, Latenz | eigenes Folge-Issue |
| E nur gesperrte Zeile ohne ERLAUBT | gut | jede Wertänderung braucht Root | verworfen |

### Technical Approach
Variante C. Werte (Spitze 60 Tage, Faktor ≥ 3, außer schreiben):
| Dienst | Spitze | MemoryHigh | MemoryMax | MemorySwapMax |
|--------|--------|-----------|-----------|---------------|
| rueckmeldungen | 42 MiB | 192M | 256M | 128M |
| push | 73 MiB | 192M | 256M | 128M |
| konnektor | 326 MiB | 768M | 1G | 256M |
| schreiben | 3,4 GiB (Veröffentlichen) | 4G | 5G | 1G |
`schreiben` bleibt bewusst grob, bis das Folge-Issue #624 (D) das Veröffentlichen herauslöst; dann 512M.
ERLAUBT: `("Service","MemoryHigh")`, `("Service","MemoryMax")`, `("Service","MemorySwapMax")`, Muster `^[1-9][0-9]{0,4}[MG]$`
(kein `infinity`, kein Prozent, keine 0, kein K/T) — identisch in units.py und Helfer.
Abgrenzung zu dienstrechte-552 Entscheidung 8: Ressourcengrenzen schränken nur ein, öffnen keine Rechte; schlimmster Missbrauch
ist ein Neustart des Dienstes (Verfügbarkeit), nie mehr Zugriff.
Nach dem Ausliefern: einmal Root-Schritt `einrichten.sh --installieren` auf dieser Instanz (Claude), Nachweis per
`systemctl show -p MemoryHigh -p MemoryMax -p MemorySwapMax`; `units.py pruefen` endet mit 0.

### Dependencies
systemd cgroup v2 (Ubuntu 24.04, MemoryAccounting=yes, Swap-Accounting aktiv); veroeffentlichen.sh → units.py → Root-Helfer.

### Open Questions
- [ ] PO-Freigabe des neuen ERLAUBT-Eintrags (Sicherheitsentscheidung laut docs/betrieb.md) — kommt mit der Spec-Freigabe.
