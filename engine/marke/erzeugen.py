"""Erzeugt aus frieda.svg die Bilddateien, die der Konnektor-Dienst unter Friedas Adresse ausliefert
(Favicon, App-Symbol, MCP-Icons). Nur nach einer Änderung am Symbol nötig; die Ergebnisse liegen im Repo,
damit der Dienst ohne CairoSVG und Pillow auskommt. Aufruf aus frieda/: engine/.venv/bin/python engine/marke/erzeugen.py"""
import io
from pathlib import Path

import cairosvg
from PIL import Image

HIER = Path(__file__).resolve().parent


def png(groesse):
    roh = cairosvg.svg2png(url=str(HIER / "frieda.svg"), output_width=groesse, output_height=groesse)
    return Image.open(io.BytesIO(roh)).convert("RGB")  # iOS mag keine Transparenz


if __name__ == "__main__":
    for g, name in ((32, "icon-32.png"), (180, "apple-touch-icon.png"), (192, "icon-192.png"), (512, "icon-512.png")):
        png(g).save(HIER / name, optimize=True)
    png(48).save(HIER / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
