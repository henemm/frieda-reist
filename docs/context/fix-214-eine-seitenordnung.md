# Context: fix-214-eine-seitenordnung

## Request Summary

Issue #214: Die Seitenordnung aus ADR-0003 (Zeitachse in einer Spalte, Tagesseiten, eine Heimat je Grundform, „Zu tun“ mit Zu entscheiden und Zu buchen) soll für **alle** Reisen gelten. Den alten Plan-Zweig (`PLAN_DA`) gibt es danach nicht mehr. Freigabe der Richtung durch den Product Owner am 2.11.2026 („ja, so klingt es richtig“).

## Befund

Die neue Ordnung ist heute ein Zweig, der nur greift, wenn alle drei Bedingungen erfüllt sind (`engine/vorlage.html` 1055–1081):

```js
const PLAN_FEST = R.plaene.find(planFest);          // ein Plan, alle seine Optionen gewählt
const PLAN_TAGE = B("tagesseiten") ? PLAN_FEST : null;
const PLAN_DA   = !PLAN_TAGE || !!D.reise.tiefe;    // true = alte Seite
```

**Welchen Zweig die echten Reisen der Instanz nehmen** (Stand 2.11.2026, nur nach Reisetyp benannt, Daten privat):

| Reisetyp | Bausteine / Darstellung | Pläne | Zweig |
|---|---|---|---|
| Etappenwanderung | varianten, karte, tagesseiten | Plan fest | **neu** |
| Rundreise | varianten, karte, kein tagesseiten; `tiefe: true`, `plan_reiter` | Pläne, Plan-Baum | alt |
| Familienbesuch | karte, kein tagesseiten | keine | alt |
| Skiurlaub | keine Route-Bausteine | ? | alt |

→ Drei von vier echten Reisen zeigen die alte Seite. Abgenommen wurde nur an der ersten.

**Daten sind da:** `routen.py` `bauen()` liefert immer `tage` (der aktuelle Plan, auch ohne P-…), `summe`, `unterkuenfte` mit `naechte`, `aufenthalte`, `buchungen`; `plaene` ist leer, wenn die Reise keine benannten Pläne hat (Z. 1378, 1397–1428). Die Zeitachse (`ansichtReise(m, p)`, Z. 2913) erwartet ein Plan-Objekt `p` mit `tage`; ohne Plan ließe sich `{tage: R.tage, summe: R.summe, …}` übergeben.

## Related Files

| Datei | Relevanz |
|---|---|
| `engine/vorlage.html` | Kern der Änderung. `PLAN_FEST`/`PLAN_TAGE`/`PLAN_DA` (1055–1081), Reiter (1083–1102), `abschnittInhalt` (1235–1246), `tagKarte` (1474–1507), `tagesplan` (1509–1520), `unterkuenfte`/`unterkunftZeilen` (1718–1735), `wegVerlauf` (1441–1457), `nachtZeile` (1347–1373), `wahlZeile` (1462–1472), Plan-Optionen (2035–2079), `ansichtStart`/`ansichtReise` (2912–3000), `TIEFE` und `ansichtPlanDetail` (3101, 3162–3190), Tagesseite `ansichtTag` (3330–3380), `nachtAbschnitt` (3298–3325), Zurück-Link (3346), `ansichtOffen` (3566–3575), Wahlen an Abschnitten (3594), Routing (4700–4730), Bausteinseite (3850–3900) |
| `docs/adr/0003-heimat.md` | Punkt 3 (Reiter nur ohne gewählten Plan) braucht einen Nachtrag |
| `docs/design.md` | „Spalten“ (Z. 109, zwei Spalten), „Seitenordnung“ (111–141), Tabellen mit „ohne Tagesseiten“ (31, 122–123, 186, 190) |
| `docs/adr/0001-kern.md` | Prüfstelle; Frage 1: an zwei Reisetypen durchgespielt |
| `docs/produkt.md`, `docs/neue-reise.md` | Baustein `tagesseiten` als zuschaltbar beschrieben (produkt.md 49, neue-reise.md 41, 51) |
| `engine/neu.py` | `BAUSTEINE_IDEE` (Z. 42) ohne `tagesseiten` |
| `engine/reise.py`, `engine/konnektor.py`, `engine/schreiben.py` | kennen den Baustein `tagesseiten` (Rechte, `setting_set`) — prüfen, ob er bleibt |
| `beispiel/reisen/beispielreise` | einzige Testreise: Varianten, Tagesseiten, Pläne; braucht eine zweite Form ohne Pläne |
| Tests | `test_seite.py` (161 ff. Buchung ohne Tagesseiten, 173 ff. #146 Storno mit `for o in s["b01"]`), `test_heimat_unterkunft.py` (nur gewählter Plan), `test_reiseueberblick.py` (Reiter, Zeitachse), `test_tagesplan.py` (77 ff., `tiefe`), `test_tagesseite.py`, `test_neu.py` (ohne Browser), `seiten_*.mjs` (`seiten_reise`, `seiten_variante`, `seiten_tagesplan`, `seiten_tagesseite`, `seiten_browser`), `test_b2_ansichten.py`, `sprachen_rundgang.mjs` |

## Existing Patterns

- **Heimat-Prüfung „erste Nacht“** gibt es schon auf der Tagesseite (`nachtAbschnitt`, 3315–3319): `erste === t.id` → volle `unterkunftKarte`, sonst `nachtZeile` mit Link. Dasselbe Muster fehlt im Tageskasten des alten Zweigs.
- **Buchung an ihrem ersten Ding:** `buchungenBei(id)` filtert `b.fuer[0] === id`. Fehler im alten Zweig: dasselbe Ding (Unterkunft) wird an mehreren Stellen voll gezeigt.
- **Heimat-Sprung** `heimat(id)` für `#U-…`/`#V-…` (ADR-0003 Konsequenzen) — muss ohne `PLAN_DA` eindeutig werden.
- **Testreise im Test kopieren und abwandeln** (`test_heimat_unterkunft.py`, `test_tagesplan.py`: `shutil.copytree` der Beispielreise, Ergänzungen als Beispielwert). Die Form ohne Pläne lässt sich so ableiten, ohne die Demo zu ändern.
- **Spec-Format:** `docs/specs/oberflaeche/tagesseite-plan.md` (#144).

## Dependencies

- **Upstream:** Routenmodell aus `routen.py` (`R.tage`, `R.plaene`, `R.unterkuenfte[].naechte`, `R.buchungen`, `R.wahlstellen[].an`), `D.reise.bausteine`, `D.reise.tiefe`, `D.reise.plan_reiter`, `D.reise.status`. Wird voraussichtlich nicht geändert.
- **Downstream:** Reiter und Routing der Seite (`#plan`, `#varianten`, `#offen`, Tages-IDs), Rücksprung `zurueckZurZeile`, Service Worker (Offline-Cache der Seite, keine Logikabhängigkeit), Bausteinseite `#bausteine`, Texte im Katalog (`texte_de.py`/`texte_en.py`, Schlüssel `seite.plan.*`, `seite.reiter.*`), Konnektor-Anleitung (`docs/konnektor.md`, `neue-reise.md`: „tagesseiten dazuschalten“).

## Existing Specs

- `docs/specs/oberflaeche/tagesseite-plan.md` (#144) — Nummer und Datum der Tagesseite aus `PLAN_FEST`; ohne `PLAN_FEST` „planabhängige Nummer, Planchips“. Muss mit dieser Änderung zusammenpassen.
- `docs/specs/oberflaeche/papierkorb-146.md` — stornierte Buchungen; der zugehörige Test verlangt die Buchung an jedem Ding voll.

## Risks & Considerations

- **Offene Fachfragen für die Spec (PO):**
  1. Was zeigt die Seite **vor** der Entscheidung, wenn es mehrere Pläne gibt? Vorschlag: Zeitachse des aktuellen Plans (`R.tage`) mit Marken „offen“/„vorläufig“, Vergleich der Pläne im Reiter „Pläne“.
  2. Bleibt der **Baustein `tagesseiten`**? Vorschlag: entfällt (Tagesseiten gehören zur Grundform Tag), Daten bleiben unberührt.
  3. Was braucht **`darstellung.tiefe`** (Rundreise mit Plan-Baum, `plan_reiter`, `ansichtPlanDetail`) noch? Betrifft eine laufende echte Reise.
- **Laufende echte Reisen ändern ihr Aussehen** (Rundreise, Familienbesuch, Skiurlaub). Abnahme an Fotos vorher/nachher je Reisetyp.
- **#144 (Tagesseiten-Nummer) und #146 (Storno)** hängen an `PLAN_FEST` bzw. am alten Zweig; deren Tests müssen weiter gelten oder bewusst angepasst werden.
- **Umfang:** `vorlage.html` hat ~4700 Zeilen, `PLAN_DA` steht an vielen Stellen. Risiko, dass ein Zweig übersehen wird; deshalb Zählprüfung „genau einmal vollständig“ und „keine doppelte ID“ für alle Fälle.
- **Parallele Sitzung** arbeitet an #202/#203 (`requirements.txt`, `tests.yml`, `veroeffentlichen.sh`) — nicht anfassen.
- **Öffentliches Repo:** keine Namen, Orte oder Daten echter Reisen in Spec, Tests oder Commits.

## Analysis

### Type
Bug (Verstoß gegen ADR-0003 in allen Reisen außer „Plan fest + Tagesseiten“), behoben durch einen Umbau: der alte Zweig `PLAN_DA` entfällt.

### Kernidee
Eine neue Größe `PLAN_ANSICHT` ist **der Plan der Zeitachse**. Sie ersetzt `PLAN_TAGE` (Z. 1072) und ist immer gesetzt:

| Fall | `PLAN_ANSICHT` |
|---|---|
| (a) keine Pläne | synthetisch: `{id: null, tage: R.tage, summe: R.summe, auswahl: [], warnungen: R.warnungen, kurz/titel: Reisename}` |
| (b) Pläne offen | Plan mit `aktuell === true` (`routen.py` ~1420), sonst wie (a) |
| (c) Plan fest | `PLAN_FEST` |
| (d) `darstellung.tiefe` | wie (b) bzw. (c); `tiefe` steuert die Startseite nicht mehr |

`PLAN_FEST` bleibt nur als „entschieden“: Tagesnummer/Datum (#144; 2747, 3339, 3392), Titel „Reise“ (1061), Mahnlogik (3560, 3874–3887). `ansichtStart` (2912) ruft immer `ansichtReise(m, PLAN_ANSICHT)`. `heimat()` (4614) bricht nicht mehr bei `!PLAN_TAGE` ab und ist die einzige Stelle, die die Heimat bestimmt; Routing 4707–4742 wird ohne `PLAN_DA`/`!TIEFE`-Zweige vereinheitlicht.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/vorlage.html` | MODIFY | `PLAN_ANSICHT` einführen; `PLAN_DA`, `PLAN_TAGE`, Reiter „Plan“, `tagesplan()`, `unterkuenfte()`, `ansichtPlan`, `ansichtRahmen`, `entscheidungen`, `fragenKarte` entfernen; Zweige 1083, 1086, 1097, 1100, 1102, 1241–1242, 1346–1372, 1441–1507, 2035–2079, 2343, 2803–2804, 3346–3347, 3357, 3372, 3457, 3570, 3594, 4615, 4707–4742 vereinheitlichen; `ZU_TUN` immer an; Kopfkommentar/Bausteinseite (3850–3900) |
| `engine/reise.py` | MODIFY | Baustein `tagesseiten` wird ignoriert (alte `reise.yaml` bleibt gültig); `plan_reiter` nach Entscheidung |
| `engine/neu.py` | MODIFY ggf. | `BAUSTEINE_IDEE` (Z. 42) nur, falls der Baustein bleibt |
| `engine/texte_de.py`, `texte_en.py` | MODIFY | nicht mehr genutzte Schlüssel `seite.plan.*` entfernen, Konnektor-Beschreibung `setting_set` ohne `tagesseiten` |
| `engine/tests/test_seite.py` | MODIFY | #146-Test und `test_buchung_hat_eine_heimat_auch_ohne_tagesseiten` auf „genau ein Ding voll“ |
| `engine/tests/test_heimat_unterkunft.py`, `test_tagesplan.py`, `test_reiseueberblick.py`, `test_tagesseite.py`, `test_b2_ansichten.py` | MODIFY | Fälle ohne Pläne / Pläne offen / `tiefe` |
| `engine/tests/test_eine_seitenordnung.py` (Name vorläufig) | CREATE | Zählprüfung „genau einmal vollständig“ je Grundform und „keine doppelte ID“ in allen vier Fällen; Testreise ohne Pläne per `copytree` der Beispielreise abgeleitet (Beispielwerte) |
| `engine/tests/seiten_*.mjs`, `sprachen_rundgang.mjs` | MODIFY/DELETE | `seiten_tagesplan.mjs` entfällt oder wird neu; Browser-Rundgang über eine frisch aus `reisevorlage` angelegte Reise |
| `docs/adr/0003-heimat.md` | MODIFY | Nachtrag zu Punkt 3: Reiter hängen nicht an „Plan gewählt“ |
| `docs/design.md` | MODIFY | „Spalten“ (Z. 109: keine zwei Spalten), „Seitenordnung“ (111–141), Tabellen „ohne Tagesseiten“ |
| `docs/produkt.md`, `docs/neue-reise.md`, `docs/konnektor.md` | MODIFY | Baustein `tagesseiten` nicht mehr als Schalter |
| `docs/specs/oberflaeche/tagesseite-plan.md` (#144) | MODIFY | Tagesnummer ohne Pläne aus `R.tage` |
| `docs/specs/oberflaeche/eine-seitenordnung-214.md` | CREATE | Spec (Phase 3) |

### Scope Assessment
- Dateien: ~20 (davon 1 Kern, Rest Tests/Docs)
- Geschätzte LoC: `vorlage.html` netto −150 bis −250; Tests +150 bis +250; Docs ±100
- Risk Level: **HIGH** — zentrale Seitenlogik, drei laufende echte Reisen ändern ihr Aussehen; Rundreise (`tiefe`, `plan_reiter`) ist das größte Einzelrisiko

### Technical Approach (Empfehlung)
Commits in dieser Reihenfolge:
1. Spec, ADR-0003-Nachtrag, design.md (PO-Freigabe).
2. Rote Tests: Testreise ohne Pläne; Zählprüfung und ID-Prüfung für (a)–(d); doppelte ID `nachtZeile`/`wahlZeile` (1365/1466) als eigener Test; Browser-Rundgang über frische Reise aus der Reisevorlage.
3. `PLAN_ANSICHT`, `heimat()`, Startseite, Routing.
4. Alten Zweig entfernen (`PLAN_DA`, `tagesplan`, `unterkuenfte`, Reiter „Plan“, `ansichtRahmen`).
5. Tests und Docs bereinigen; Baustein `tagesseiten` stilllegen.

Abnahme: Fotos vorher/nachher je Reisetyp (Rundreise zuerst), frische Testreise über den Konnektor; nie nur an der Wanderung.

### Dependencies
- Upstream unverändert: `routen.py` (`R.tage`, `R.summe`, `R.plaene[].aktuell`, `R.unterkuenfte[].naechte`, `R.buchungen`, `R.wahlstellen[].an`), `D.reise.*`.
- Downstream: `ETAPPE_TAG` (1073) und `ETAPPEN_REITER` (1075) setzen heute `PLAN_TAGE` voraus — mit `PLAN_ANSICHT` gelten Etappen auch bei offenen Plänen als „Tag mit Etappe“; das ändert Reiter „Etappen“ und Routing 4709. Texte im Katalog, Konnektor-Beschreibung.
- Nicht anfassen: parallele Arbeit an #202/#203 (`requirements.txt`, `tests.yml`, `veroeffentlichen.sh`).

### Befunde gegen den Plan
Keine, die ihn kippen. Zu beachten: (1) doppelte IDs verschwinden mit `PLAN_DA` nicht automatisch, eigener Test; (2) `entscheidungen`/`fragenKarte`/`ansichtRahmen` gehören zur alten Startseite und entfallen, „Offene Fragen“ steht schon in „Zu tun“.

### Open Questions (Entscheidung des PO bei der Spec-Freigabe, mit Empfehlung)
- [ ] **Ansicht vor der Entscheidung bei mehreren Plänen:** Empfehlung: Zeitachse des aktuellen Plans mit Marken „offen“, Vergleich ganzer Pläne im Reiter „Pläne“.
- [ ] **Baustein `tagesseiten`:** Empfehlung: entfällt als Schalter, Tagesseiten gehören zur Grundform Tag; der Wert in alten `reise.yaml` wird ignoriert, keine Datenmigration.
- [ ] **`darstellung.tiefe`:** Empfehlung: nur noch Plan-Baum im Reiter „Pläne“ (`ansichtPlanDetail`, 2194–2255, 2662, 3473), steuert nicht mehr Startseite, Tagesseiten oder Zurück-Link.
- [ ] **`darstellung.plan_reiter`** (Reiter „Plan“ mit Rahmenabschnitten, nur Rundreise): Empfehlung: die genannten Abschnitte wandern in den Reiter „Wissen“ (3457–3458 sieht `plan`-Abschnitte dort schon vor), `plan_reiter` wird ignoriert.
- [ ] **Etappen bei offenen Plänen** (`ETAPPE_TAG`, Reiter „Etappen“): Empfehlung: Zuordnung über `PLAN_ANSICHT`; in der Spec festlegen und an der Beispielreise mit offenem Plan prüfen.
