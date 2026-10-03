/* ==========================================================================
   GHDI 2026 — public site interactions
   Hero carousel (autoplay, arrows, dots, keyboard, swipe, reduced-motion)
   Card rail controls (arrows + disabled state)
   ========================================================================== */
(function () {
  "use strict";
  document.documentElement.classList.add("js");

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var HERO_INTERVAL = 6500;
  /* ------------------------------------------------------------ Hero */
  function initHero(root) {
    if (root.dataset.heroBound) return;
    root.dataset.heroBound = "1";

    // Publish the interval so the CSS progress bar animates in lockstep with
    // the JS timer instead of relying on a second hard-coded duration.
    root.style.setProperty("--ghdi-hero-interval", HERO_INTERVAL + "ms");

    var slides = Array.prototype.slice.call(root.querySelectorAll(".ghdi-hero__slide"));
    if (slides.length < 2) return;

    var dotsWrap = root.querySelector("[data-hero-dots]");
    var progress = root.querySelector(".ghdi-hero__progress span");
    var thumbs = Array.prototype.slice.call(root.querySelectorAll("[data-hero-go]"));
    var index = 0;
    var timer = null;

    // Build dot buttons
    if (dotsWrap && !dotsWrap.children.length) {
      slides.forEach(function (slide, i) {
        var dot = document.createElement("button");
        dot.type = "button";
        dot.className = "ghdi-hero__dot";
        dot.setAttribute("aria-label", "Go to slide " + (i + 1));
        dot.addEventListener("click", function () { show(i); });
        dotsWrap.appendChild(dot);
      });
    }

    function paint() {
      slides.forEach(function (slide, i) {
        var active = i === index;
        slide.classList.toggle("is-active", active);
        slide.setAttribute("aria-hidden", active ? "false" : "true");
        // Inactive slides stay in the DOM for the crossfade, so their links must
        // be pulled out of the tab order and the a11y tree.
        if ("inert" in slide) {
          slide.inert = !active;
        } else {
          Array.prototype.forEach.call(slide.querySelectorAll("a[href], button"), function (el) {
            el.tabIndex = active ? 0 : -1;
          });
        }
      });
      var counter = root.querySelector("[data-hero-current]");
      if (counter) counter.textContent = String(index + 1);
      if (dotsWrap) {
        Array.prototype.forEach.call(dotsWrap.children, function (dot, i) {
          var active = i === index;
          dot.classList.toggle("is-active", active);
          dot.setAttribute("aria-current", active ? "true" : "false");
        });
      }
      thumbs.forEach(function (thumb, i) {
        var active = i === index;
        thumb.classList.toggle("is-active", active);
        thumb.setAttribute("aria-current", active ? "true" : "false");
      });
      // No restartProgress() here — every paint() is followed by schedule(),
      // which owns the fill so the bar and the timer stay in lockstep.
    }

    function restartProgress() {
      if (!progress || reduceMotion) return;
      // Replay the fill from zero on every slide change.
      progress.style.animation = "none";
      // Force a reflow so the animation can be restarted reliably.
      void progress.offsetWidth;
      progress.style.animation = "";
    }

    function setPaused(paused) {
      root.classList.toggle("is-paused", paused);
    }

    function clear() {
      if (timer) { clearTimeout(timer); timer = null; }
      setPaused(true);
    }

    function schedule() {
      clear();
      if (reduceMotion) return;
      timer = setTimeout(function () { show(index + 1); }, HERO_INTERVAL);
      setPaused(false);
      // clear() also paused the CSS fill, so replay it from zero here. Without
      // this the bar resumes mid-animation while the timer restarts at full
      // length, so the two drift apart after the first hover or focus.
      restartProgress();
    }

    function show(n) {
      index = (n + slides.length) % slides.length;
      paint();
      schedule();
    }

    root.querySelectorAll("[data-hero-prev]").forEach(function (btn) {
      btn.addEventListener("click", function () { show(index - 1); });
    });
    root.querySelectorAll("[data-hero-next]").forEach(function (btn) {
      btn.addEventListener("click", function () { show(index + 1); });
    });

    // Thumbnail rail — jump straight to a slide.
    thumbs.forEach(function (thumb) {
      thumb.addEventListener("click", function () {
        var target = parseInt(thumb.getAttribute("data-hero-go"), 10);
        if (!isNaN(target)) { show(target); }
      });
    });

    // Pause on hover / focus. focusin/focusout both bubble, so they fire on
    // every move *within* the carousel too; only react when focus actually
    // enters or leaves the hero, otherwise tabbing between the controls
    // restarts the autoplay timer on every keypress.
    root.addEventListener("mouseenter", clear);
    root.addEventListener("mouseleave", schedule);
    root.addEventListener("focusin", clear);
    root.addEventListener("focusout", function (e) {
      if (e.relatedTarget && root.contains(e.relatedTarget)) return;
      schedule();
    });

    // Keyboard — only act when focus is inside the carousel, and never let the
    // arrow keys scroll the page underneath the hero.
    root.addEventListener("keydown", function (e) {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      e.preventDefault();
      if (e.key === "ArrowLeft") { show(index - 1); } else { show(index + 1); }
    });

    // Swipe
    var startX = null;
    root.addEventListener("pointerdown", function (e) { startX = e.clientX; });
    root.addEventListener("pointerup", function (e) {
      if (startX === null) return;
      var dx = e.clientX - startX;
      startX = null;
      if (Math.abs(dx) < 55) return;
      if (dx < 0) { show(index + 1); } else { show(index - 1); }
    });

    // Pause when tab is hidden
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) { clear(); } else { schedule(); }
    });

    paint();
    schedule();
  }

  /* ------------------------------------------------------------ Card rail */
  function initRail(rail) {
    if (rail.dataset.railBound) return;
    rail.dataset.railBound = "1";

    var track = rail.querySelector(".ghdi-rail__track");
    if (!track) return;

    var prev = rail.querySelector(".ghdi-rail__btn--prev");
    var next = rail.querySelector(".ghdi-rail__btn--next");

    function cardStep() {
      var card = track.querySelector(":scope > *");
      return card ? card.getBoundingClientRect().width + 24 : rail.clientWidth * 0.8;
    }

    function update() {
      var max = track.scrollWidth - track.clientWidth;
      if (prev) prev.disabled = track.scrollLeft <= 4;
      if (next) next.disabled = track.scrollLeft >= max - 4;
    }

    function go(dir) {
      // Proximity snapping re-snaps a smooth scroll back to the card it
      // started from, so suspend snapping for the duration of the animated
      // scroll and restore it when the scroll settles (scrollend, with a
      // timeout fallback for browsers without scrollend support).
      track.style.scrollSnapType = "none";
      var restore = function () { track.style.scrollSnapType = ""; };
      track.addEventListener("scrollend", restore, { once: true });
      setTimeout(restore, 700);
      track.scrollBy({ left: dir * cardStep(), behavior: reduceMotion ? "auto" : "smooth" });
    }

    if (prev) prev.addEventListener("click", function () { go(-1); });
    if (next) next.addEventListener("click", function () { go(1); });

    track.addEventListener("scroll", update, { passive: true });
    update();
  }

  /* --------------------------------------------------------------- topbar */
  /* Adds `.is-scrolled` to the public header once the page leaves the top. */
  function initTopbar() {
    var bar = document.getElementById("siteTopbar");
    if (!bar) return;
    var apply = function () {
      bar.classList.toggle("is-scrolled", window.pageYOffset > 24);
    };
    apply();
    window.addEventListener("scroll", apply, { passive: true });
  }

  /* ---------------------------------------------------------------- boot */
  /* Each initialiser is isolated so a failure in one never stops the others. */
  function safe(label, fn) {
    try {
      fn();
    } catch (err) {
      if (window.console && console.warn) console.warn("GHDI: " + label + " failed", err);
    }
  }

  function boot() {
    safe("hero carousel", function () {
      document.querySelectorAll(".ghdi-hero").forEach(initHero);
    });
    safe("card rail", function () {
      document.querySelectorAll(".ghdi-rail").forEach(initRail);
    });
    safe("scroll reveal", initReveal);
    safe("topbar", initTopbar);
  }

  /* ------------------------------------------------------ Scroll reveal */
  function initReveal() {
    var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var elements = Array.prototype.slice.call(document.querySelectorAll(
      "main > section, .reveal, .stat-count, .ghdi-media-card, .ghdi-story-card, .ghdi-event-card, .ghdi-theme-card"
    ));
    var siblingCounts = new Map();
    elements.forEach(function (el) {
      var animation = el.classList.contains("ghdi-theme-card") || el.classList.contains("stat-count") ? "zoom" :
        el.classList.contains("ghdi-event-card") ? "fade-right" : "fade-up";
      el.setAttribute("data-scroll-reveal", animation);
      var parent = el.parentElement;
      var order = siblingCounts.get(parent) || 0;
      siblingCounts.set(parent, order + 1);
      el.style.setProperty("--scroll-reveal-delay", Math.min(order, 4) * 75 + "ms");
    });

    function show(el) {
      el.classList.add("is-inview", "is-visible", "is-revealed");
    }

    if (reduceMotion || !window.IntersectionObserver) {
      elements.forEach(show);
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          show(entry.target);
          if (entry.target.classList.contains("stat-count")) {
            animateStat(entry.target);
          }
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.12,
      rootMargin: "0px 0px -48px 0px"
    });
    elements.forEach(function (el) { observer.observe(el); });
  }

  /* Animate a stat-count number from current value to target */
  function animateStat(el) {
    var target = parseFloat(el.getAttribute("data-target") || "0");
    var isFloat = el.getAttribute("data-target") && el.getAttribute("data-target").indexOf(".") > -1;
    var decimals = isFloat ? 1 : 0;
    var duration = 1800;
    var start = null;
    var valueSpan = el.querySelector(".value");
    if (!valueSpan) return;

    function step(timestamp) {
      if (!start) start = timestamp;
      var progress = Math.min((timestamp - start) / duration, 1);
      var ease = 1 - Math.pow(1 - progress, 3); // easeOutCubic
      var current = target * ease;

      if (isFloat) {
        valueSpan.textContent = current.toFixed(decimals);
      } else {
        valueSpan.textContent = Math.floor(current).toLocaleString();
      }

      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        // Format final value with locale separators
        if (isFloat) {
          valueSpan.textContent = target.toFixed(decimals);
        } else {
          valueSpan.textContent = Math.floor(target).toLocaleString();
        }
      }
    }

    valueSpan.textContent = "0";
    requestAnimationFrame(step);
  }

  /* ---------------------------------------------------------------- boot */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
