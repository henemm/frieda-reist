"""Startanweisungen gegen später angelegte const/let (frieda-reist#387), Hilfe für test_startreihenfolge.py.

Eine const/let/class steht erst ab ihrer Zeile bereit (Temporal Dead Zone), eine function schon ab dem Anfang des Skripts. Ruft
eine Anweisung auf oberster Ebene (sie läuft beim Laden) über beliebig viele Funktionen eine const/let/class auf, die erst weiter
unten angelegt wird, bricht der Start ab, und die Seite bleibt leer. `finde(js)` liefert solche Stellen.

Kein vollständiger JavaScript-Parser: Zeichenketten, Kommentare, Regexe und Template-Texte werden ausgeblendet, die oberste Ebene
nach Klammern zerlegt, Aufrufe über `name(` gefunden. Rückrufe von Ereignissen, Zeitgebern und Promises und alles hinter dem ersten
await einer async-Funktion gehören nicht zum Start. Fehlalarme sind möglich (zu viele Wege), übersehen werden nur Aufrufe, die
nicht als `name(` geschrieben sind."""
import re

IDENT = re.compile(r"[A-Za-z_$][\w$]*")
VOR_WERT = ("", "(", ",", "=", ":", "[", "!", "&", "|", "?", "{", "}", ";", "r", "+", "-", "*", "%", "<", ">", "~", "^")
WORTE_VOR_WERT = ("return", "typeof", "case", "in", "of", "else", "do", "void", "delete", "new", "throw", "yield", "await")
SPAET = re.compile(r"(addEventListener|setTimeout|setInterval|\.then|\.catch|\.finally|requestAnimationFrame|IntersectionObserver|"
                   r"MutationObserver|ResizeObserver|\.on|\.once|queueMicrotask)\s*\(")


def skript_der_vorlage(html):
    """Das eingebettete Skript (das letzte <script> ohne src) und die Zeilennummer seines Anfangs."""
    a = [m for m in re.finditer(r"<script>", html)][-1].end()
    return html[a:html.index("</script>", a)], html[:a].count("\n")


def ausblenden(js):
    """Zeichenketten, Kommentare, Regexe und Template-Texte durch Leerzeichen ersetzen (Zeilenumbrüche bleiben); ${…} bleibt Code."""
    out = list(js)
    n = len(js)
    stack, tiefe, last, i = [], 0, "", 0

    def leer(x, y):
        for k in range(x, y):
            if out[k] != "\n":
                out[k] = " "

    def vorlage(i):   # ab i bis zum nächsten ${ oder Ende der Template-Zeichenkette
        j = i
        while j < n:
            if js[j] == "\\":
                j += 2
                continue
            if js[j] == "`":
                leer(i, j + 1)
                return j + 1, False
            if js[j] == "$" and js[j + 1:j + 2] == "{":
                leer(i, j + 2)
                return j + 2, True
            j += 1
        return n, False

    while i < n:
        c = js[i]
        if js.startswith("//", i):
            j = js.find("\n", i)
            j = n if j < 0 else j
            leer(i, j)
            i = j
            continue
        if js.startswith("/*", i):
            j = js.index("*/", i) + 2
            leer(i, j)
            i = j
            continue
        if c in "\"'":
            j = i + 1
            while js[j] != c:
                j += 2 if js[j] == "\\" else 1
            leer(i, j + 1)
            i, last = j + 1, "s"
            continue
        if c == "`":
            i, innen = vorlage(i + 1)
            if innen:
                stack.append(tiefe)
                tiefe += 1
            last = "s"
            continue
        if c == "/" and last in VOR_WERT:   # Regex
            j, klasse = i + 1, False
            while j < n:
                ch = js[j]
                if ch == "\\":
                    j += 2
                    continue
                if ch == "[":
                    klasse = True
                elif ch == "]":
                    klasse = False
                elif (ch == "/" and not klasse) or ch == "\n":
                    break
                j += 1
            j += 1
            while j < n and js[j].isalpha():
                j += 1
            leer(i, j)
            i, last = j, "s"
            continue
        if c == "{":
            tiefe += 1
        elif c == "}":
            tiefe -= 1
            if stack and tiefe == stack[-1]:   # Ende von ${…}: der Template-Text geht weiter
                stack.pop()
                out[i] = " "
                i, innen = vorlage(i + 1)
                if innen:
                    stack.append(tiefe)
                    tiefe += 1
                last = "s"
                continue
        if not c.isspace():
            if c.isalnum() or c in "_$":
                j = i
                while j < n and (js[j].isalnum() or js[j] in "_$"):
                    j += 1
                last = "r" if js[i:j] in WORTE_VOR_WERT else "w"
                i = j
                continue
            last = c if c not in ")]" else ")"
        i += 1
    return "".join(out)


def anweisungen(code):
    """Anweisungen auf oberster Ebene als (Anfang, Ende)."""
    items, tiefe, start = [], 0, None
    weiter = re.compile(r"\s*(else\b|catch\b|finally\b|while\b|[.,)\]?:+\-*/=<>&|])")
    for i, c in enumerate(code):
        if tiefe == 0 and start is None and not c.isspace():
            start = i
        if c in "([{":
            tiefe += 1
        elif c in ")]}":
            tiefe -= 1
            if tiefe == 0 and c == "}":
                kopf = re.match(r"(async\s+)?(function|class|if|for|while|try|switch|do)\b|\{|\w+:\s*(for|while)", code[start:start + 40])
                if kopf and not weiter.match(code[i + 1:i + 40]):
                    items.append((start, i + 1))
                    start = None
        elif c == ";" and tiefe == 0:
            items.append((start, i + 1))
            start = None
    if start is not None and code[start:].strip():
        items.append((start, len(code)))
    return items


def ohne_rueckrufe(t):
    """Inhalt von Rückrufen, die erst später laufen, ausblenden."""
    o = list(t)
    for mm in SPAET.finditer(t):
        i, d = mm.end(), 1
        while i < len(t) and d:
            d += (t[i] in "([{") - (t[i] in ")]}")
            i += 1
        for k in range(mm.end(), i - 1):
            if o[k] != "\n":
                o[k] = " "
    return re.sub(r"\.on\w+\s*=\s*[^;]*", ".on=", "".join(o))


def finde(js):
    """Stellen, an denen eine Startanweisung eine später angelegte const/let/class erreicht: Liste von Texten
    „<Name> (Zeile a) wird von der Startanweisung in Zeile b erreicht über f <- g <- …“ (Zeilen relativ zum Skript)."""
    code = ausblenden(js)
    assert code.count("{") == code.count("}"), "Klammern gehen nicht auf: die Ausblendung hat sich verzählt"
    funcs, lexikalisch, startet = {}, {}, []
    for x, y in anweisungen(code):
        t = code[x:y]
        m = re.match(r"(?:async\s+)?function\s*\*?\s*([\w$]+)", t)
        if m:
            funcs[m.group(1)] = (x, y)
            continue
        m = re.match(r"(?:const|let)\s+([\w$]+)\s*=\s*(?:async\s+)?(?:\([^()]*\)|[\w$]+)\s*=>|(?:const|let)\s+([\w$]+)\s*=\s*(?:async\s+)?function\b", t)
        if m:   # const mit Funktion: der Rumpf läuft erst beim Aufruf, die Funktion steht aber erst ab ihrer Zeile bereit
            name = m.group(1) or m.group(2)
            lexikalisch[name] = x
            funcs[name] = (x, y)
            continue
        m = re.match(r"(?:const|let|class)\s+([\w$]+)", t)
        if m:
            lexikalisch[m.group(1)] = x
            startet.append((x, y, m.group(1)))
            continue
        m = re.match(r"(?:const|let)\s*([\[{][^=]*)=", t)
        if m:
            for name in IDENT.findall(m.group(1)):
                lexikalisch[name] = x
            startet.append((x, y, ""))
            continue
        if t.strip():
            startet.append((x, y, ""))

    for f, (x, y) in list(funcs.items()):   # async: synchron nur bis zum ersten await, der Rest kommt nach dem Ende des Skripts
        if re.match(r"(?:(?:const|let)\s+[\w$]+\s*=\s*)?async\b", code[x:y]) and code.find("await", x, y) >= 0:
            funcs[f] = (x, code.find("await", x, y))

    def text(x, y):
        return re.sub(r"\.\s*[\w$]+", ".", ohne_rueckrufe(code[x:y]))   # Eigenschaftszugriffe (.route) sind keine Namen

    def namen(x, y):
        return set(IDENT.findall(re.sub(r"([{,]\s*)[\w$]+(\s*:)", r"\1\2", text(x, y))))   # ohne Schlüssel von Objektliteralen

    def aufrufe(x, y):
        return set(re.findall(r"([A-Za-z_$][\w$]*)\s*\(", text(x, y)))

    def zeile(pos):
        return code[:pos].count("\n") + 1

    funde = {}
    for x, y, eigener in startet:
        kette = {f: None for f in aufrufe(x, y) if f in funcs}
        todo, gesehen = list(kette), set()
        while todo:
            f = todo.pop()
            if f in gesehen:
                continue
            gesehen.add(f)
            for g in aufrufe(*funcs[f]):
                if g in funcs and g not in kette:
                    kette[g] = f
                    todo.append(g)
        for g in (namen(x, y) - {eigener}):
            if lexikalisch.get(g, -1) > x:
                funde.setdefault(g, []).append((zeile(x), "direkt"))
        for f in kette:
            for g in namen(*funcs[f]):
                if lexikalisch.get(g, -1) > x:
                    weg, k = [], f
                    while k:
                        weg.append(k)
                        k = kette[k]
                    funde.setdefault(g, []).append((zeile(x), " <- ".join(weg)))
    return [f"{g} (Zeile {zeile(lexikalisch[g])}) wird von der Startanweisung in Zeile {min(l)[0]} erreicht über {min(l)[1][:160]}"
            for g, l in sorted(funde.items(), key=lambda kv: lexikalisch[kv[0]])]
