#!/usr/bin/env python3
"""Links neuer Reisen zustellen (betrieb/veroeffentlichen.sh, docs/betrieb.md „Neue Reise freischalten“).

Eine neue Reise aus der Claude-App legt der Schreibweg sofort an (engine/schreiben.py reise_anlegen). Der Konnektor
merkt sie in <FR_KONNEKTOR>/neue-reisen-ausstehend.jsonl vor, je Zeile {ordner, aid, name, person}. Sobald ihre Seite
veröffentlicht ist, schaltet dieses Skript sie frei (freischalten.sh) und stellt der Person die Links zu: als Meldung in
meine_reisen, bei einem Konto als Verknüpfung mit der Reise und Einladungen per Mail. Links und Adressen stehen nie im
Protokoll. Was noch nicht veröffentlicht ist oder scheitert, bleibt für den nächsten Lauf stehen.

Die Logik steckt hier statt in der Shell, damit sie getestet werden kann (engine/tests/test_betrieb.py).
Aufruf:  zustellen.py <wurzel> <datei>   (mit dem Python der Software; <wurzel> ist das Reisen-Repo, engine/ darin
         die Software). Rückgabe 5, wenn etwas nicht zugestellt wurde.
Umgebung: RM_ABLAGE (Rückmelde-Ablage), KN_SEITEN (veröffentlichte Seiten).
"""
import json
import os
import subprocess
import sys
from pathlib import Path


def ausstehend(wurzel, datei, seiten=None, freischalten=None):
    """Links neuer Reisen zustellen, sobald die Seite veröffentlicht ist -> Zahl der Fehlschläge.
    Kam die Anfrage aus dem Konnektor „Frieda“ (konto_id, Paket J): kein App-Link, sondern das Konto wird mit der Reise
    verknüpft, und wer eine Adresse hat, bekommt die Einladung per Mail. Die Adressen stehen nur in der Anfrage in der
    Ablage, nie in dieser Datei oder im Protokoll; schon Eingeladene merkt sich der Eintrag (eingeladen)."""
    sys.path.insert(0, str(Path(wurzel) / "engine"))
    import konten  # noqa: E402
    import rueckmeldungen as rm  # noqa: E402
    import texte  # noqa: E402
    p = Path(datei)
    if not p.exists():
        return 0
    seiten = Path(seiten or os.environ["KN_SEITEN"])
    freischalten = freischalten or str(Path(__file__).resolve().with_name("freischalten.sh"))
    o_neu = rm.ordner_neu()
    auftraege = {a["id"]: a for a in rm.auftraege(o_neu)} if o_neu else {}
    rest, fehlschlaege = [], 0
    for zeile in p.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        daten = seiten / e["ordner"] / "daten.json"
        if not daten.exists():
            rest.append(zeile)
            continue
        auftrag = auftraege.get(e["aid"]) or {}
        mit_konto = bool(auftrag.get("konto_id"))
        sprache = ((auftrag.get("daten") or {}).get("neue_reise") or {}).get("sprache")   # Meldung und Einladung: Sprache der neuen Reise
        sprache = sprache if texte.gueltig(sprache or "") else texte.VORGABE_REISE
        aufruf = [freischalten, e["ordner"]] + ([] if mit_konto else ["--person", e["person"]])
        r = subprocess.run(aufruf, capture_output=True, text=True)
        links = dict(z.split(": ", 1) for z in r.stdout.splitlines() if z.startswith(("Seite: ", "Claude-App: ")))
        if r.returncode != 0 or not ({"Seite"} if mit_konto else {"Seite", "Claude-App"}) <= set(links):
            fehlschlaege += 1
            # Links sind geheim: nur die Fehlerzeilen ins Protokoll
            fehler = [z for z in (r.stdout + r.stderr).splitlines() if not z.startswith(("Seite: ", "Claude-App: "))]
            print(f"ERROR: {e['ordner']} not released: {' '.join(fehler)[-300:]}")
            rest.append(zeile)
            continue
        titel = (json.loads(daten.read_text(encoding="utf-8")).get("reise") or {}).get("titel", e["ordner"])
        if mit_konto:
            try:
                konten.verknuepfen(auftrag["konto_id"], e["ordner"], e["person"])
                eingeladen = set(e.get("eingeladen") or [])
                for x in auftrag.get("einladen") or []:
                    if x["schluessel"] in eingeladen:
                        continue
                    konten.einladen(e["ordner"], x["schluessel"], x["email"], x["rolle"], x["name"], e["name"],
                                    titel=titel, seite=links["Seite"], sprache=sprache)
                    eingeladen.add(x["schluessel"])
                    e["eingeladen"] = sorted(eingeladen)
            except konten.KontoFehler as f:
                fehlschlaege += 1
                print(f"ERROR: {e['ordner']}: account or invitation: {f}")
                rest.append(json.dumps(e, ensure_ascii=False))
                continue
            n = len(auftrag.get("einladen") or [])
            rm.meldung_anlegen(rm.ordner_neu(anlegen=True), [e["name"]], "neue_reise", e["ordner"],
                               texte.t(sprache, "dienst.zustellen.konto", titel=titel, seite=links["Seite"])
                               + (texte.t(sprache, "dienst.zustellen.einladungen_eine" if n == 1 else "dienst.zustellen.einladungen_viele", n=n)
                                  if n else ""), auftraege=[e["aid"]])
        else:
            rm.meldung_anlegen(rm.ordner_neu(anlegen=True), [e["name"]], "neue_reise", e["ordner"],
                               texte.t(sprache, "dienst.zustellen.app", titel=titel, seite=links["Seite"], link=links["Claude-App"]),
                               auftraege=[e["aid"]])
        print(f"Delivered: {e['ordner']} an {e['name']}")
    p.write_text("".join(z + "\n" for z in rest), encoding="utf-8")
    return fehlschlaege


def main(a):
    if len(a) != 2:
        print(__doc__)
        return 1
    return 5 if ausstehend(a[0], a[1]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
