/* ==========================================================================
   GHDI shell UI. Requires static/js/bootstrap.bundle.min.js.
   - top page-load progress bar
   - dark / light theme toggle (persisted, respects prefers-color-scheme)
   - bootstrap toasts + auto-dismiss alerts
   ========================================================================== */
(function () {
  "use strict";

  var THEME_KEY = "ghdi-theme";

  function getStoredTheme() {
    try { return localStorage.getItem(THEME_KEY); } catch (e) { return null; }
  }

  function setStoredTheme(theme) {
    try { localStorage.setItem(THEME_KEY, theme); } catch (e) { /* ignore */ }
  }

  function preferredTheme() {
    var stored = getStoredTheme();
    if (stored === "dark" || stored === "light") { return stored; }
    return window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function syncToggleButtons(theme) {
    var dark = theme === "dark";
    var nodes = document.querySelectorAll("[data-ghdi-theme-toggle]");
    for (var i = 0; i < nodes.length; i++) {
      nodes[i].setAttribute("aria-pressed", dark ? "true" : "false");
      nodes[i].setAttribute("aria-label",
        dark ? "Switch to light mode" : "Switch to dark mode");
      var icon = nodes[i].querySelector("i");
      if (icon) {
        icon.className = dark ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
      }
    }
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-bs-theme", theme);
    setStoredTheme(theme);
    syncToggleButtons(theme);
  }

  window.ghdiApplyTheme = applyTheme;
  window.ghdiToggleTheme = function () {
    var current = document.documentElement.getAttribute("data-bs-theme");
    applyTheme(current === "dark" ? "light" : "dark");
  };

  /* ---------- progress bar ---------- */
  var bar = null;

  function progressBar() {
    if (bar) { return bar; }
    bar = document.getElementById("ghdi-progress");
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "ghdi-progress";
      bar.setAttribute("aria-hidden", "true");
      (document.body || document.documentElement).appendChild(bar);
    }
    return bar;
  }

  var pct = 0;
  var timer = null;

  function step() {
    pct += (92 - pct) * 0.12;
    progressBar().style.width = pct.toFixed(2) + "%";
  }

  function startProgress() {
    var el = progressBar();
    pct = 6;
    el.classList.remove("is-done");
    el.classList.add("is-active");
    step();
    if (timer) { clearInterval(timer); }
    timer = window.setInterval(step, 180);
  }

  /* ---------- Branded navigation transition ---------- */
  var navigationLoader = document.getElementById("navigationLoader");

  function showNavigationLoader() {
    if (!navigationLoader) return;
    navigationLoader.classList.add("is-active");
    navigationLoader.setAttribute("aria-hidden", "false");
    try { window.sessionStorage.setItem("ghdi-navigation-pending", "1"); } catch (error) {}
  }

  function hideNavigationLoader() {
    if (!navigationLoader) return;
    navigationLoader.classList.remove("is-active");
    navigationLoader.setAttribute("aria-hidden", "true");
    try { window.sessionStorage.removeItem("ghdi-navigation-pending"); } catch (error) {}
  }

  function isEligibleNavigation(anchor, event) {
    if (!anchor || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false;
    if (anchor.hasAttribute("download") || anchor.target === "_blank" || anchor.closest("[data-no-loader]")) return false;
    if (anchor.hasAttribute("data-bs-toggle") || anchor.hasAttribute("data-ghdi-theme-toggle")) return false;
    var rawHref = anchor.getAttribute("href") || "";
    if (!rawHref || rawHref.charAt(0) === "#" || /^(mailto:|tel:|javascript:|data:)/i.test(rawHref)) return false;
    try {
      var destination = new URL(anchor.href, window.location.href);
      if (destination.origin !== window.location.origin) return false;
      if (destination.pathname === window.location.pathname && destination.search === window.location.search && destination.hash) return false;
      return true;
    } catch (error) {
      return false;
    }
  }

  document.addEventListener("click", function (event) {
    var anchor = event.target.closest ? event.target.closest("a[href]") : null;
    if (!isEligibleNavigation(anchor, event)) return;
    showNavigationLoader();
    // Other handlers may cancel navigation (for example, a confirmation dialog).
    window.setTimeout(function () { if (event.defaultPrevented) hideNavigationLoader(); }, 0);
  });

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form || event.defaultPrevented || form.hasAttribute("data-no-loader") || form.target === "_blank" || form.method === "dialog") return;
    showNavigationLoader();
    window.setTimeout(function () { if (event.defaultPrevented) hideNavigationLoader(); }, 0);
  });

  window.addEventListener("pageshow", function (event) {
    if (event.persisted) hideNavigationLoader();
  });

  function finishProgress() {
    var el = progressBar();
    if (timer) { clearInterval(timer); timer = null; }
    el.classList.add("is-done");
    window.setTimeout(function () {
      el.classList.remove("is-active");
      el.classList.remove("is-done");
      el.style.width = "0";
    }, 420);
  }

  window.ghdiStartProgress = startProgress;
  window.ghdiFinishProgress = finishProgress;

  function isInternalLink(anchor) {
    var href = anchor.getAttribute("href") || "";
    if (!href || href.charAt(0) === "#") { return false; }
    if (/^(mailto:|tel:|javascript:|data:)/i.test(href)) { return false; }
    if (anchor.hasAttribute("download")) { return false; }
    if (anchor.getAttribute("target") === "_blank") { return false; }
    if (anchor.host && anchor.host !== window.location.host) { return false; }
    if (anchor.hasAttribute("data-bs-toggle") ||
        anchor.hasAttribute("data-ghdi-theme-toggle")) { return false; }
    return true;
  }

  document.addEventListener("click", function (event) {
    var toggle = event.target.closest
      ? event.target.closest("[data-ghdi-theme-toggle]") : null;
    if (toggle) {
      event.preventDefault();
      window.ghdiToggleTheme();
      return;
    }
    var anchor = event.target.closest ? event.target.closest("a[href]") : null;
    if (anchor && isInternalLink(anchor)) { startProgress(); }
  });

  document.addEventListener("submit", function (event) {
    if (event.target && event.target.getAttribute("data-ghdi-no-progress") === null) {
      startProgress();
    }
  });

  window.addEventListener("pageshow", finishProgress);
  window.addEventListener("pagehide", startProgress);

  /* ---------- bootstrap toasts ---------- */
  window.ghdiToast = function (message, variant) {
    var wrap = document.getElementById("ghdi-toasts");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.id = "ghdi-toasts";
      wrap.className = "toast-container position-fixed top-0 end-0 p-3";
      wrap.style.zIndex = "2500";
      document.body.appendChild(wrap);
    }
    var el = document.createElement("div");
    el.className = "toast align-items-center border-0 mb-2 text-bg-" +
      (variant || "dark");
    el.setAttribute("role", "alert");
    el.setAttribute("aria-live", "assertive");
    el.setAttribute("aria-atomic", "true");
    el.innerHTML = '<div class="d-flex"><div class="toast-body"></div>' +
      '<button type="button" class="btn-close btn-close-white me-2 m-auto" ' +
      'data-bs-dismiss="toast" aria-label="Close"></button></div>';
    el.querySelector(".toast-body").textContent = message;
    wrap.appendChild(el);
    if (window.bootstrap && window.bootstrap.Toast) {
      var toast = new window.bootstrap.Toast(el, { delay: 4200 });
      toast.show();
      el.addEventListener("hidden.bs.toast", function () { el.remove(); });
    } else {
      window.setTimeout(function () { el.remove(); }, 4200);
    }
  };

  function autoDismiss() {
    var nodes = document.querySelectorAll("[data-ghdi-autodismiss]");
    for (var i = 0; i < nodes.length; i++) {
      (function (el) {
        window.setTimeout(function () {
          el.style.transition = "opacity .4s ease";
          el.style.opacity = "0";
          window.setTimeout(function () { el.remove(); }, 450);
        }, 6000);
      })(nodes[i]);
    }
  }

  /* ---------- init ---------- */
  function init() {
    applyTheme(document.documentElement.getAttribute("data-bs-theme") ||
      preferredTheme());
    autoDismiss();
    // make every server-rendered bootstrap tooltip live
    if (window.bootstrap && window.bootstrap.Tooltip) {
      var tips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
      for (var i = 0; i < tips.length; i++) {
        new window.bootstrap.Tooltip(tips[i]);
      }
    }
  }

  // theme must be correct before first paint
  applyTheme(document.documentElement.getAttribute("data-bs-theme") ||
    preferredTheme());

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
