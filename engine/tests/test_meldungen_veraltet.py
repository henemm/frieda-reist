"""Tests für #687 und #693 Punkt 1: Meldungen ohne Reise gelten nur, solange es das Ding gibt, um das es geht.
Spec: docs/specs/konnektor/veraltete-meldungen-687.md. Alle Namen, Adressen und Reisen sind erfunden."""
import datetime
import sys
from contextlib import closing
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import anmeldung  # noqa: E402
import konten  # noqa: E402
import rueckmeldungen as rm  # noqa: E402
from conftest import mailcode, meldet, text  # noqa: E402
from test_anmeldung import BASIS, abruf, anmelden as seite_anmelden, welt  # noqa: E402,F401  (welt: Fixture)
from test_warteliste import bestaetigungswort, mails  # noqa: E402

IDA, KARL, TOM, LEA = (f"{n}@beispiel.invalid" for n in ("ida", "karl", "tom", "lea"))
REISE = "stadtwochenende"
TEIL = "konto.meldungen.text."


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Nur die Kontendatenbank: Ida und Tom sind Betreiber, Karl und Lea nicht."""
    monkeypatch.setenv("FR_KONTEN", str(tmp_path / "konten"))
    monkeypatch.setenv("FR_MAIL_DATEI", str(tmp_path / "mails.jsonl"))
    monkeypatch.setenv("FR_BASIS", BASIS)
    monkeypatch.setenv("RM_ABLAGE", str(tmp_path / "ablage"))
    for name in ("ida", "karl", "tom", "lea"):
        konto_anlegen(f"k-{name}", f"{name}@beispiel.invalid", name.capitalize())
    for kid in ("k-ida", "k-tom"):
        konten.recht_setzen(kid, "betreiber")
    return tmp_path


def konto_anlegen(kid, mail, name):
    with closing(konten.db()) as v, v:
        v.execute("INSERT INTO konten (id, email, name, angelegt, sprache) VALUES (?,?,?,?,?)",
                  (kid, mail, name, "2026-11-01T00:00:00+00:00", "de"))


def sichtbar(kid="k-ida"):
    """Kennungen der Meldungen, die das Konto sieht (Konnektor und Mein Konto lesen dieselbe Quelle)."""
    return {m["id"] for m in rm.meldungen_des_kontos(konten.konto(kid))}


def arten(kid="k-ida"):
    return sorted(m["art"] for m in rm.meldungen_des_kontos(konten.konto(kid)))


def ablegen(art, ziel="reise", an=("k-ida",), **kw):
    return rm.meldung_anlegen(rm.ordner_neu(anlegen=True), list(an), art, ziel, "Beispielwert", **kw)["id"]


def neue_reise(reise=REISE, an="k-karl"):
    return ablegen("neue_reise", reise, [an], teile=[(TEIL + "neue_reise", {"titel": "Stadtwochenende"})])


def bitten(kid="k-karl"):
    """Wie Mein Konto und trip_create_request: erst die Bitte, dann die Meldung an die Betreiber."""
    assert konten.reisen_anlegen_anfragen(kid) == "offen"
    anmeldung.betreiber_melden(konten.konto(kid))
    assert kid in {a["konto"] for a in konten.anfragen()}


def altmeldung(email, name="Karl"):
    """Bitte von vor #687: ohne Feld konto, die Adresse steht nur in t."""
    return ablegen("anfrage_reisen", teile=[(TEIL + "anfrage_reisen", {"name": name, "email": email})])


def warten(db, mail):
    """Adresse eintragen und bestätigen, danach die Meldung wie /warteliste/bestaetigen/."""
    konten.warteliste_eintragen(mail, sprache="de")
    e = konten.warteliste_bestaetigen(bestaetigungswort(mails(db / "mails.jsonl", mail)[-1]))
    anmeldung.betreiber_melden(None, "anfrage_warteliste", text("konto.betreiber.warteliste", email=e["email"]),
                               [(TEIL + "anfrage_warteliste", {"email": e["email"]})])


def datei():
    return (rm.ordner_neu() / "meldungen.jsonl").read_bytes()


# ---------- Neue Reise (AC-1 bis AC-4) ----------

def test_neue_reise_vorgemerkt_verschwindet(db):
    konten.verknuepfen("k-karl", REISE, "karl")
    mid = neue_reise()
    assert sichtbar("k-karl") == {mid}
    konten.loeschung_vormerken(REISE, "k-karl")
    assert sichtbar("k-karl") == set()


def test_neue_reise_entfernt_verschwindet(db):
    konten.verknuepfen("k-karl", REISE, "karl")
    mid = neue_reise()
    assert sichtbar("k-karl") == {mid}
    konten.loeschung_vormerken(REISE, "k-karl")
    konten.loeschung_abschliessen(REISE)
    assert konten.loeschprotokoll() == [REISE] and sichtbar("k-karl") == set()


def test_neue_reise_zurueckgeholt_erscheint_wieder(db):
    konten.verknuepfen("k-karl", REISE, "karl")
    mid = neue_reise()
    vorher = datei()
    konten.loeschung_vormerken(REISE, "k-karl")
    assert sichtbar("k-karl") == set()
    assert datei() == vorher
    konten.loeschung_zurueckholen(REISE, "k-karl")
    assert sichtbar("k-karl") == {mid} and datei() == vorher


def test_neue_reise_ohne_mitgliedschaft_bleibt(db):
    """Maßstab ist die Vormerkung, nicht die Mitgliedschaft; eine andere vorgemerkte Reise ändert nichts."""
    bleibt, weg = neue_reise("winterwoche"), neue_reise()
    konten.loeschung_vormerken(REISE, None)
    assert bleibt in sichtbar("k-karl")
    assert weg not in sichtbar("k-karl")


# ---------- Bitte „Reisen anlegen“ (AC-5 bis AC-9, AC-13, AC-18, AC-21) ----------

def test_bitte_freigeschaltet_verschwindet(db):
    bitten()
    assert arten() == ["anfrage_reisen"]
    konten.freischalten("k-karl")
    assert arten() == []


def test_bitte_abgelehnt_verschwindet(db):
    bitten()
    assert arten() == ["anfrage_reisen"]
    konten.freischalten("k-karl", ja=False)
    assert arten() == []


def test_bitte_konto_geloescht_verschwindet(db):
    bitten()
    assert arten() == ["anfrage_reisen"]
    konten.loeschen("k-karl")
    assert konten.anfragen() == [] and arten() == []


def test_bitte_konten_zusammengefuehrt_verschwindet(db):
    bitten()
    assert arten() == ["anfrage_reisen"]
    konten.zusammenfuehren("k-karl", "k-lea")
    assert konten.anfragen() == [] and arten() == []


def test_offene_bitte_bleibt_sichtbar(db):
    """Nur die Meldung zur entschiedenen Bitte verschwindet, die zur offenen bleibt."""
    bitten("k-karl")
    bitten("k-lea")
    konten.freischalten("k-lea")
    [m] = rm.meldungen_des_kontos(konten.konto("k-ida"))
    assert m["art"] == "anfrage_reisen" and m["t"][0][1]["email"] == KARL


def test_adresse_geaendert_bitte_mit_feld_konto_bleibt(db):
    bitten()
    [roh] = rm.meldungen(rm.ordner_neu(), "k-ida")
    assert roh.get("konto") == "k-karl"
    neu = "karl.neu@beispiel.invalid"
    konten.code_anfordern(neu, zweck="adresse", konto="k-karl", sprache="de")
    konten.adresse_aendern("k-karl", neu, mailcode(mails(db / "mails.jsonl", neu)[-1]["text"]))
    assert konten.konto("k-karl")["email"] == neu and arten() == ["anfrage_reisen"]
    # das Feld entscheidet, auch wenn ein anderes Konto die alte Adresse trägt und selbst offen bittet
    konto_anlegen("k-karl2", KARL, "Karl")
    assert konten.reisen_anlegen_anfragen("k-karl2") == "offen"
    konten.freischalten("k-karl")
    assert arten() == []


def test_mehrere_betreiber_entscheidung_gilt_fuer_alle(db):
    bitten()
    assert arten("k-ida") == arten("k-tom") == ["anfrage_reisen"]
    konten.freischalten("k-karl")
    assert arten("k-ida") == arten("k-tom") == []


def test_testanfrage_wird_nicht_unterdrueckt(db):
    """#693 Punkt 2 (Product Owner, 24.11.2026): keine Ausnahme für Unteradressen des Testpostfachs."""
    konto_anlegen("k-probe", "frieda-test+probe@beispiel.invalid", "Probe")
    bitten("k-probe")
    warten(db, "frieda-test+warteliste@beispiel.invalid")
    assert arten() == ["anfrage_reisen", "anfrage_warteliste"]
    konten.freischalten("k-probe", ja=False)
    assert arten() == ["anfrage_warteliste"]
    konten.freigeben("frieda-test+warteliste@beispiel.invalid")
    assert arten() == []


# ---------- Warteliste (AC-10 bis AC-12) ----------

def test_wartelisten_eintrag_freigegeben_verschwindet(db):
    warten(db, "neu@beispiel.invalid")
    assert arten() == ["anfrage_warteliste"]
    assert konten.freigeben("neu@beispiel.invalid") is True
    assert arten() == []


def test_wartelisten_eintrag_geloescht_verschwindet(db):
    """Mit dem Konto geht auch sein Eintrag der Warteliste."""
    warten(db, LEA)
    assert arten() == ["anfrage_warteliste"]
    konten.loeschen("k-lea")
    assert konten.warteliste() == [] and arten() == []


def test_offener_wartelisten_eintrag_bleibt_sichtbar(db):
    warten(db, "neu@beispiel.invalid")
    warten(db, "fertig@beispiel.invalid")
    konten.freigeben("fertig@beispiel.invalid")
    [m] = rm.meldungen_des_kontos(konten.konto("k-ida"))
    assert m["t"][0][1] == {"email": "neu@beispiel.invalid"}


# ---------- Altmeldungen und unlesbare Daten (AC-14 bis AC-16) ----------

def test_altmeldung_ohne_feld_konto_ueber_adresse(db):
    konten.reisen_anlegen_anfragen("k-karl")
    mid = altmeldung("Karl@Beispiel.invalid")     # Groß- und Kleinschreibung zählt nicht
    assert sichtbar() == {mid}
    konten.freischalten("k-karl")
    assert sichtbar() == set()


def test_nicht_zuzuordnende_altmeldung_bleibt(db):
    """Nichts ohne Beleg verstecken; nach 14 Tagen fällt sie wie bisher weg."""
    alt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=20)
    bleiben = {ablegen("anfrage_reisen"), ablegen("anfrage_warteliste")}
    ablegen("anfrage_reisen", zeit=alt)
    zugeordnet = altmeldung("weg@beispiel.invalid")     # zuzuordnen, aber keine offene Bitte
    assert bleiben <= sichtbar()
    assert zugeordnet not in sichtbar() and sichtbar() == bleiben


UNLESBAR = [None, "", "Text", 7, {}, [], [None], ["x"], [[]], [["{s}"]], [["{s}", None]], [["{s}", "Text"]], [["{s}", {}]],
            [["{s}", {"email": None}]], [["{s}", {"email": 7}]], [["{s}", {"email": ["a"]}]], [[None, {"email": KARL}]],
            [[["x"], {"email": KARL}]]]


def test_unlesbares_t_wirft_nicht(db):
    def mit_schluessel(w, art):
        if isinstance(w, list):
            return [mit_schluessel(x, art) for x in w]
        return TEIL + art if w == "{s}" else w
    bleiben = {ablegen(art, extra={"t": mit_schluessel(w, art)}) for w in UNLESBAR for art in ("anfrage_reisen", "anfrage_warteliste")}
    zugeordnet = altmeldung("weg@beispiel.invalid")
    assert bleiben <= sichtbar()
    assert zugeordnet not in sichtbar()


def test_unlesbares_konto_wirft_nicht(db):
    """Ein falscher Typ im Feld konto wirft nicht und zählt als nicht gesetzt; ebenso ein fehlendes ziel."""
    bleiben = {ablegen("neue_reise", z) for z in (None, 7)}
    bleiben |= {ablegen("anfrage_reisen", extra={"konto": w}) for w in (None, "", ["x"], {"a": 1}, 7)}
    weg = neue_reise(an="k-ida")
    konten.loeschung_vormerken(REISE, None)
    assert bleiben <= sichtbar()
    assert weg not in sichtbar()


# ---------- Andere Arten, nur Filter beim Lesen (AC-17, AC-20) ----------

def test_andere_arten_unveraendert(db):
    bleiben = {ablegen("betrieb"), ablegen("loeschung"), ablegen("hinweis", REISE),
               ablegen("betrieb", teile=[(TEIL + "warteliste_tagesgrenze", {"grenze": 3})])}
    weg = neue_reise(an="k-ida")
    konten.loeschung_vormerken(REISE, None)
    assert bleiben <= sichtbar()
    assert weg not in sichtbar()


def test_filter_nur_beim_lesen(db):
    neue_reise(an="k-ida")
    bitten()
    warten(db, "neu@beispiel.invalid")
    vorher = datei()
    assert len(sichtbar()) == 3
    konten.loeschung_vormerken(REISE, None)
    konten.freischalten("k-karl")
    konten.freigeben("neu@beispiel.invalid")
    assert sichtbar() == set()
    assert datei() == vorher


def test_mengen_hoechstens_einmal_und_nur_bei_bedarf(db, monkeypatch):
    """Keine Abfrage je Meldung; ohne passende Art gar keine."""
    zaehler = dict.fromkeys(("vorgemerkte_reisen", "anfragen", "warteliste"), 0)

    def zaehlend(name, alt):
        def f(*a, **kw):
            zaehler[name] += 1
            return alt(*a, **kw)
        return f
    for name in zaehler:
        monkeypatch.setattr(konten, name, zaehlend(name, getattr(konten, name)))
    ablegen("betrieb")
    assert len(sichtbar()) == 1 and set(zaehler.values()) == {0}
    for _ in range(3):
        neue_reise("winterwoche", "k-ida")
        altmeldung(KARL)
        ablegen("anfrage_warteliste", teile=[(TEIL + "anfrage_warteliste", {"email": LEA})])
    sichtbar()
    assert zaehler == dict.fromkeys(zaehler, 1)


# ---------- Konnektor und Mein Konto (AC-19) ----------

@pytest.fixture
def lagen(welt):  # noqa: F811
    """Über die Seiten: Ida (Betreiberin) hat je Art eine gültige Meldung und eine, deren Ding entscheide() beendet."""
    u = welt()
    u.ida_keks, _ = seite_anmelden(u, IDA, "Ida")
    u.ida = konten.konto_per_email(IDA)["id"]
    konten.recht_setzen(u.ida, "betreiber")
    konten.verknuepfen(u.ida, "beispielreise", "ida")
    for mail, name in ((KARL, "Karl"), (TOM, "Tom")):
        keks, _ = seite_anmelden(u, mail, name)
        assert abruf(f"{u.kurl}/konto", "POST", {"aktion": "anfragen"}, cookie=keks)[0] == 303
    for mail in ("neu@beispiel.invalid", "fertig@beispiel.invalid"):
        abruf(f"{u.kurl}/warteliste", "POST", {"email": mail})
        wort = bestaetigungswort(mails(u.mails, mail)[-1])
        assert abruf(f"{u.kurl}/warteliste/bestaetigen/{wort}", "POST", {})[0] == 200
    for reise, titel in (("beispielreise", "Alte Runde"), ("winterwoche", "Winterwoche")):
        rm.meldung_anlegen(rm.ordner_neu(anlegen=True), [u.ida], "neue_reise", reise, f"Neu: {titel} (Beispielwert)",
                           teile=[(TEIL + "neue_reise", {"titel": titel})])

    def entscheide():
        wer = konten.konto_per_email(KARL)["id"]
        assert abruf(f"{u.kurl}/konto", "POST", {"aktion": "freischalten", "wer": wer}, cookie=u.ida_keks)[0] == 303
        konten.freigeben("fertig@beispiel.invalid")
        konten.loeschung_vormerken("beispielreise", u.ida)
    u.entscheide = entscheide
    return u


VERALTET = [("anfrage_reisen", {"name": "Karl", "email": KARL}), ("anfrage_warteliste", {"email": "fertig@beispiel.invalid"}),
            ("neue_reise", {"titel": "Alte Runde"})]
GUELTIG = [("anfrage_reisen", {"name": "Tom", "email": TOM}), ("anfrage_warteliste", {"email": "neu@beispiel.invalid"}),
           ("neue_reise", {"titel": "Winterwoche"})]


def test_wirkung_im_konnektor_my_trips(lagen):
    import konnektor as kn
    saetze = {"anfrage_reisen": "konto.betreiber.meldung", "anfrage_warteliste": "konto.betreiber.warteliste"}

    def satz(art, werte):
        return text(saetze[art], **werte) if art in saetze else f"Neu: {werte['titel']} (Beispielwert)"

    def meine():
        return kn.meine_reisen_konto(konten.konto(lagen.ida))
    t = meine()
    assert all(satz(*x) in t for x in VERALTET + GUELTIG)
    lagen.entscheide()
    t = meine()
    assert all(satz(*x) in t for x in GUELTIG)
    assert [x for x in VERALTET if satz(*x) in t] == []


def test_zahl_der_gelesenen_sinkt_im_konnektor(lagen):
    import konnektor as kn

    def zahl(n):
        return text("konnektor.ausgabe.meine_reisen.gelesen", n=n) in kn.meine_reisen_konto(konten.konto(lagen.ida))
    konten.gelesen_merken(lagen.ida, [m["id"] for m in rm.meldungen(rm.ordner_neu(), lagen.ida)])
    assert zahl(6)
    lagen.entscheide()
    assert zahl(3)


def test_wirkung_auf_mein_konto(lagen):
    def abschnitt():
        s, _, t = abruf(f"{lagen.kurl}/konto", cookie=lagen.ida_keks)
        assert s == 200 and 'id="meldungen"' in t
        return t.split('id="meldungen"', 1)[1].split('class="abschnitt"', 1)[0]

    def steht(t, art, werte):
        return meldet(t, TEIL + art) and text(TEIL + art, **werte) in t
    t = abschnitt()
    assert all(steht(t, *x) for x in VERALTET + GUELTIG)
    lagen.entscheide()
    t = abschnitt()
    assert all(steht(t, *x) for x in GUELTIG)
    assert [x for x in VERALTET if steht(t, *x)] == []


def test_veraltete_meldung_laesst_sich_nicht_mehr_oeffnen(lagen):
    [mid] = [m["id"] for m in rm.meldungen(rm.ordner_neu(), lagen.ida) if m["art"] == "anfrage_reisen" and KARL in m["text"]]
    lagen.entscheide()
    assert abruf(f"{lagen.kurl}/konto?meldung={mid}", cookie=lagen.ida_keks)[0] == 404
    assert mid not in konten.gelesen(lagen.ida)
