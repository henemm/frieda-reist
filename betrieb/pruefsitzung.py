#!/usr/bin/env python3
"""Prüfsitzung für Browser-Prüfungen der echten Seiten (docs/betrieb.md „Seiten prüfen“).

Der Weg, den Playwright für angemeldete Seiten empfiehlt: ein eigenes Konto mit den geringsten Rechten, die Sitzung außerhalb
des Browsers erzeugen und als Cookie einsetzen (storageState), statt die Anmeldung mit E-Mail und Code nachzuspielen. Die
Anmeldung selbst bleibt unangetastet, es gibt keine Hintertür im Dienst.

Das Prüfkonto ist kein Mitglied irgendeiner Reise und sieht nur, was eine fremde Person mit dem Link sieht. Die Sitzung gilt kurz
(Vorgabe 2 Stunden) und wird bei jedem Aufruf neu ausgestellt; ältere Prüfsitzungen werden dabei gelöscht.

Aufruf (als Dienstbenutzer, mit den Werten der Instanz, FR_KONTEN bzw. RM_SEITEN und FR_KN_ADRESSE):
  python3 frieda/betrieb/pruefsitzung.py <storage-state.json> [--stunden 2]
Die Datei ist ein Playwright-storageState (Rechte 600, nie ins Repo): browser.newContext({storageState: "<datei>"}).
"""
import argparse
import json
import os
import secrets
import sys
from contextlib import closing
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
import konten  # noqa: E402
import rueckmeldungen as rm  # noqa: E402

GERAET = "Prüfsitzung"


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("datei", help="Ausgabe: Playwright-storageState (JSON)")
    a.add_argument("--stunden", type=float, default=2, help="Gültigkeit der Sitzung (Vorgabe 2)")
    arg = a.parse_args()
    basis = os.environ.get("FR_KN_ADRESSE", "").rstrip("/") or konten.basis()
    host = urlparse(basis).hostname
    if not host:
        sys.exit("FR_KN_ADRESSE fehlt (Adresse der Seiten, z. B. https://frieda.example.org).")
    email = konten.adresse(f"pruefung@{host}")
    with closing(konten.db()) as v, v:
        z = v.execute("SELECT id FROM konten WHERE email = ?", (email,)).fetchone()
        kid = z["id"] if z else "K-" + secrets.token_hex(8)
        if not z:
            v.execute("INSERT INTO konten (id, email, name, angelegt) VALUES (?,?,?,?)",
                      (kid, email, "Prüfung", konten._datum()))
        v.execute("DELETE FROM sitzungen WHERE konto = ? AND geraet = ?", (kid, GERAET))
        token = konten._sitzung_anlegen(v, kid, GERAET)
        v.execute("UPDATE sitzungen SET ablauf = ? WHERE konto = ? AND geraet = ?",
                  (konten._jetzt() + arg.stunden * 3600, kid, GERAET))
    zustand = {"cookies": [{"name": rm.COOKIE, "value": token, "domain": host, "path": "/", "httpOnly": True,
                            "secure": True, "sameSite": "Lax", "expires": int(konten._jetzt() + arg.stunden * 3600)}],
               "origins": []}
    fd = os.open(arg.datei, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(zustand, f)
    print(f"Check session for {email} valid for {arg.stunden:g} hours: {arg.datei}")


if __name__ == "__main__":
    main()
