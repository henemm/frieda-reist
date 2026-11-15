#!/usr/bin/env python3
"""Meldungen aus der Claude-App als Aufgabe für die Entwicklung (#587).

Meldet eine Person mit an_frieda_melden einen Fehler, Wunsch oder eine Frage zu Frieda und gibt dazu eine Fassung für die
Entwicklung mit (oeffentlicher_text / public_text), legt die Instanz daraus sofort ein Issue im Repo der Software an. Die
volle Fassung bleibt privat in der Kontendatenbank (konten.betreiber_meldungen).

Persönliche Daten prüft dieses Modul nur mit festen Regeln, ohne KI (ADR-0001): Mail-Adressen und eine Liste von Angaben,
die der Konnektor aus den Reisen des Kontos holt (Namen, Reisetitel, Ordner, Orte, Unterkünfte). Ein Treffer heißt
ablehnen; die Fassung schreibt Frieda im Client neu und stimmt sie mit der Person ab.

Einstellungen (beide nötig, sonst bleibt es bei Ablage und Mail an den Betreiber wie vor #587):
  FR_MELDUNGEN_REPO    Ziel-Repo als <besitzer>/<name> (Umgebung oder Einstellungsdatei der Instanz)
  FR_MELDUNGEN_TOKEN   Zugangsschlüssel für GitHub, nur mit dem Recht „Issues schreiben“ auf diesem Repo; geheim, nur
                       aus der Umgebung (beim Konnektor <FR_DIENST>/konten.env), nie aus einer Datei im Repo.
Nur Standardbibliothek: Der Konnektor läuft mit dem Python des Systems.
"""
import json
import os
import re
import urllib.error
import urllib.request

import instanz

API = "https://api.github.com"
REPO_FORM = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
TITEL_MAX = 80


class EntwicklungFehler(Exception):
    """Das Issue ließ sich nicht anlegen (Netz, Zugang, Antwort von GitHub). Die Meldung geht dann per Mail an den Betreiber."""


def repo():
    r = (instanz.wert("FR_MELDUNGEN_REPO") or "").strip()
    return r if REPO_FORM.match(r) else ""


def token():
    return (os.environ.get("FR_MELDUNGEN_TOKEN") or "").strip()


def eingerichtet():
    """Ziel-Repo und Zugangsschlüssel gesetzt? Ohne beides bleibt alles wie vor #587."""
    return bool(repo() and token())


def _muster(wert):
    teile = [re.escape(t) for t in wert.split()]
    return re.compile(r"(?<!\w)" + r"\s+".join(teile) + r"(?!\w)", re.IGNORECASE)


def suchwerte(werte):
    """Angaben -> Suchbegriffe: Leerraum vereinheitlicht, ohne Leeres und Einzelzeichen, ohne Doppelte."""
    return list(dict.fromkeys(" ".join(w.split()) for w in werte if isinstance(w, str) and len(w.strip()) >= 2))


def persoenliche_angaben(text, werte, namen=()):
    """Was in text an persönlichen Angaben steht: Mail-Adressen, jede Angabe aus werte als ganzes Wort (ohne Unterschied
    von Groß- und Kleinschreibung) und aus namen auch jeder einzelne Teil ab drei Zeichen. -> Liste der Treffer."""
    text = text if isinstance(text, str) else ""
    funde = MAIL.findall(text)
    teile = [t for n in namen if isinstance(n, str) for t in n.split() if len(t) >= 3]
    for w in suchwerte(list(werte) + list(namen) + teile):
        if _muster(w).search(text):
            funde.append(w)
    return list(dict.fromkeys(funde))


def _zaun(text):
    """Codeblock, dessen Zaun länger ist als jede Backtick-Folge im Text: keine Erwähnungen (@…), keine Bilder, kein HTML."""
    laengste = max((len(m) for m in re.findall(r"`+", text)), default=0)
    z = "`" * max(3, laengste + 1)
    return f"{z}text\n{text}\n{z}"


def _senden(url, kopf, daten):
    """POST an GitHub. -> (Status, Antwort als dict). Tests ersetzen diese Funktion; es geht nie ein echter Aufruf hinaus."""
    anfrage = urllib.request.Request(url, data=json.dumps(daten).encode("utf-8"), headers=kopf, method="POST")
    try:
        with urllib.request.urlopen(anfrage, timeout=15) as a:
            return a.status, json.loads(a.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as f:
        try:
            inhalt = json.loads(f.read().decode("utf-8") or "{}")
        except (ValueError, OSError):
            inhalt = {}
        return f.code, inhalt
    except (OSError, ValueError) as f:
        raise EntwicklungFehler(type(f).__name__) from f


def issue_anlegen(titel, text, etiketten):
    """Issue im Ziel-Repo anlegen. -> Adresse des Issues oder EntwicklungFehler. Lehnt GitHub nur die Etiketten ab (422),
    geht es ein zweites Mal ohne sie."""
    if not eingerichtet():
        raise EntwicklungFehler("nicht eingerichtet")
    titel = " ".join(titel.split())
    if len(titel) > TITEL_MAX:
        titel = titel[:TITEL_MAX - 1].rstrip() + "…"
    kopf = {"Authorization": "Bearer " + token(), "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "frieda-meldungen", "Content-Type": "application/json"}
    daten = {"title": titel, "body": text, "labels": [e for e in etiketten if e]}
    url = f"{API}/repos/{repo()}/issues"
    status, antwort = _senden(url, kopf, daten)
    if status == 422 and daten["labels"]:
        status, antwort = _senden(url, kopf, {k: v for k, v in daten.items() if k != "labels"})
    adresse = antwort.get("html_url") if isinstance(antwort, dict) else None
    if status != 201 or not isinstance(adresse, str) or not adresse.startswith("https://"):
        raise EntwicklungFehler(f"GitHub {status}")
    return adresse


def text_fuer_issue(oeffentlich, fuss):
    """Inhalt des Issues: die abgestimmte Fassung als Codeblock, darunter der Fußtext aus dem Katalog."""
    return _zaun(oeffentlich) + "\n\n" + fuss
