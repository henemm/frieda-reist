/* Galerie der Erklärseiten unter /info/ (Infoseite und Funktionsseiten, #711). Ohne Skript führt jedes Bild zu seiner großen
 * Fassung; mit Skript öffnet ein Tipp die Großansicht PhotoSwipe 5 (MIT, engine/vendor/photoswipe-LICENSE, wie die Reiseseite,
 * #676). Das ES-Modul lädt erst beim ersten Öffnen (/info/photoswipe-…), die Stile stehen in der Seite (die CSP erlaubt nur
 * Stile in der Seite).
 *  Baustein bildReihe: .bilder.reihe[data-galerie] mit figure > a[data-breite][data-hoehe] > img und figcaption.
 *  Baustein unterschriftStreifen: die Unterschrift steht in einem eigenen undurchsichtigen Streifen unten, das Bild bekommt dort
 *  Platz (paddingFn), damit der Text nie auf dem Bild liegt; darunter klein „<Galerie> · Bild i von n“.
 * Texte kommen vom Server aus dem Katalog (data-texte), nie aus diesem Skript (ADR-0006). Kein Inline-Skript (CSP).
 * #706: Während des Öffnens kann „change“ ohne currSlide kommen; dann zieht openingAnimationEnd den Streifen nach.
 */
(function () {
  "use strict";
  const MODUL = "/info/photoswipe-5.4.4.esm.min.js";
  let laden = null, offen = false;

  function fuellen(vorlage, werte) {
    return String(vorlage || "").replace(/\{(\w+)\}/g, (m, k) => (k in werte ? String(werte[k]) : m));
  }

  function daten(reihe) {
    return [...reihe.querySelectorAll("figure > a")].map(l => {
      const bild = l.querySelector("img"), u = l.parentElement.querySelector("figcaption");
      return {src: l.getAttribute("href"), width: +l.dataset.breite, height: +l.dataset.hoehe, alt: bild ? bild.alt : "",
        element: l, msrc: bild && bild.complete && bild.naturalWidth ? bild.currentSrc : undefined,
        unterschrift: u ? u.textContent : ""};
    });
  }

  // rand.unten: Platz unter dem Bild für den Streifen, mindestens 112 px; er folgt der Höhe des Streifens (schmales Gerät, lange
  // Sprache, Fenster bei offener Großansicht verkleinert), damit der Text nie auf dem Bild liegt
  function streifen(pswp, t, galerie, rand) {
    pswp.ui.registerElement({name: "unterschrift", order: 9, isButton: false, appendTo: "root", className: "unterschrift-streifen",
      onInit: el => {
        el.setAttribute("aria-live", "polite");
        const zeigen = () => {
          const s = pswp.currSlide;
          if (!s || !s.data) return;      // #706: noch beim Öffnen
          const satz = document.createElement("span"), zahl = document.createElement("small");
          satz.textContent = s.data.unterschrift;
          zahl.textContent = fuellen(t.zaehler, {galerie, i: pswp.currIndex + 1, n: pswp.getNumItems()});
          el.replaceChildren(satz, zahl);
          passen();
        };
        const passen = () => {
          const hoehe = Math.max(112, Math.ceil(el.getBoundingClientRect().height));
          if (hoehe !== rand.unten) { rand.unten = hoehe; pswp.updateSize(true); }
        };
        pswp.on("resize", passen);
        ["change", "afterInit", "openingAnimationEnd"].forEach(n => pswp.on(n, zeigen));
        // während des Öffnens wirkt updateSize nicht; danach einmal mit dem gemessenen Rand neu einpassen
        pswp.on("openingAnimationEnd", () => { if (rand.unten > 112) pswp.updateSize(true); });
      }});
  }

  function oeffnen(reihe, link) {
    const t = JSON.parse(reihe.dataset.texte || "{}"), liste = daten(reihe);
    const index = Math.max(0, liste.findIndex(d => d.element === link));
    laden ||= import(MODUL).then(m => m.default, x => { laden = null; throw x; });
    offen = true;
    const rand = {unten: 112};
    return laden.then(PhotoSwipe => {
      const pswp = new PhotoSwipe({dataSource: liste, index, bgOpacity: 0.94, showHideAnimationType: "zoom",
        closeTitle: t.schliessen, zoomTitle: t.zoomen, arrowPrevTitle: t.vorheriges, arrowNextTitle: t.naechstes,
        errorMsg: t.ladefehler, indexIndicatorSep: " / ", paddingFn: () => ({top: 56, bottom: rand.unten, left: 8, right: 8})});
      pswp.on("uiRegister", () => streifen(pswp, t, reihe.dataset.galerie || "", rand));
      // #706: Blättern, solange die Großansicht aufgeht, ließ sie leer (Bild fehlt, Streifen zum vorigen Bild). Bis zum Ende des
      // Öffnens nimmt sie darum keine Tipps, Klicks und Gesten an; danach blättert sie wie gewohnt.
      let oeffnet = true;
      const sperre = e => { if (oeffnet) { e.stopPropagation(); e.preventDefault(); } };
      pswp.on("openingAnimationEnd", () => { oeffnet = false; });
      pswp.on("destroy", () => { offen = false; });
      pswp.init();
      ["pointerdown", "touchstart", "mousedown", "click"]
        .forEach(n => pswp.element.addEventListener(n, sperre, {capture: true, passive: false}));
    }).catch(() => { offen = false; location.href = link.getAttribute("href"); });   // ohne Modul: die große Fassung
  }

  document.addEventListener("click", e => {
    const link = e.target.closest && e.target.closest(".bilder.reihe[data-galerie] figure > a");
    if (!link || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    if (!offen) oeffnen(link.closest(".bilder.reihe"), link);
  });
})();
