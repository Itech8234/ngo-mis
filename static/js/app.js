/* GHDI MIS — lightweight vanilla JS (Bootstrap 5; no HTMX/Alpine required).
   Handles: dropdowns, mobile drawer, search suggestions, offline banner, PWA SW,
   toast of Django messages, auto-dismiss alerts. */
(function () {
  "use strict";

  /* ---------- Offline / online banner and service worker ---------- */
  var banner = document.getElementById("offlineBanner");
  function syncOfflineState() {
    if (!banner) return;
    banner.classList.toggle("show", !navigator.onLine);
  }
  window.addEventListener("offline", syncOfflineState);
  window.addEventListener("online", syncOfflineState);
  syncOfflineState();

  if ("serviceWorker" in navigator && location.pathname !== "/offline/") {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function (err) {
        console.warn("Service worker registration failed:", err);
      });
    });
  }

  /* ---------- Dropdowns (notifications / quick actions / user menu) ---------- */
  document.addEventListener("click", function (e) {
    var trigger = e.target.closest("[data-dropdown]");
    if (trigger) {
      e.preventDefault();
      var menu = document.getElementById(trigger.getAttribute("data-dropdown"));
      document.querySelectorAll(".dropdown-menu[data-open]").forEach(function (openMenu) {
        if (openMenu !== menu) { openMenu.removeAttribute("data-open"); openMenu.hidden = true; }
      });
      if (menu) {
        var shouldOpen = menu.hidden;
        menu.hidden = !shouldOpen;
        menu.toggleAttribute("data-open", shouldOpen);
        trigger.setAttribute("aria-expanded", shouldOpen ? "true" : "false");
      }
      return;
    }
    if (e.target.closest(".dropdown-menu")) return;
    document.querySelectorAll(".dropdown-menu[data-open]").forEach(function (menu) {
      menu.removeAttribute("data-open");
      menu.hidden = true;
    });
    document.querySelectorAll("[data-dropdown][aria-expanded='true']").forEach(function (button) {
      button.setAttribute("aria-expanded", "false");
    });
  });

  /* ---------- Global search suggestions and submit ---------- */
  var searchInput = document.getElementById("globalSearchInput");
  var searchResults = document.getElementById("searchResults");
  var searchTimer = null;
  var searchRequest = null;
  if (searchInput && searchResults) {
    searchInput.setAttribute("aria-controls", "searchResults");
    searchInput.setAttribute("aria-expanded", "false");
    function hideSearchResults() {
      searchResults.hidden = true;
      searchInput.setAttribute("aria-expanded", "false");
    }
    searchInput.addEventListener("input", function () {
      var query = searchInput.value.trim();
      window.clearTimeout(searchTimer);
      if (searchRequest) { searchRequest.abort(); searchRequest = null; }
      if (query.length < 2) { hideSearchResults(); searchResults.innerHTML = ""; return; }
      searchTimer = window.setTimeout(function () {
        var controller = window.AbortController ? new AbortController() : null;
        searchRequest = controller;
        var endpoint = searchInput.getAttribute("data-suggest-url");
        fetch(endpoint + "?q=" + encodeURIComponent(query), {
          headers: { "X-Requested-With": "XMLHttpRequest" },
          signal: controller ? controller.signal : undefined
        }).then(function (response) {
          if (!response.ok) throw new Error("Search request failed");
          return response.text();
        }).then(function (html) {
          if (searchInput.value.trim() !== query) return;
          searchResults.innerHTML = html;
          searchResults.hidden = false;
          searchInput.setAttribute("aria-expanded", "true");
        }).catch(function (error) {
          if (error.name !== "AbortError") hideSearchResults();
        });
      }, 180);
    });
    searchInput.addEventListener("keydown", function (event) {
      if (event.key === "Escape") { hideSearchResults(); searchInput.blur(); }
    });
    document.addEventListener("click", function (event) {
      if (!event.target.closest(".topbar-search")) hideSearchResults();
    });
  }

  /* Clicking a notification: navigate to it; the read marker is set
     server-side by the follow-up request. */
  document.addEventListener("click", function (e) {
    var item = e.target.closest("[data-notif-url]");
    if (!item) return;
    // Let the browser navigate; the read-marker is set server-side by a follow-up
    var url = item.getAttribute("data-notif-url");
    if (url) {
      fetch(url, { method: "POST", headers: { "X-Requested-With": "XMLHttpRequest" } })
        .catch(function () {});
    }
  });

  /* ---------- Mobile drawer ---------- */
  var drawerBtns = document.querySelectorAll("[data-drawer-open]");
  var drawer = document.getElementById("mobileDrawer");
  var backdrop = document.getElementById("drawerBackdrop");
  var lastFocused = null;
  var FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';

  function setExpanded(open) {
    drawerBtns.forEach(function (btn) { btn.setAttribute("aria-expanded", open ? "true" : "false"); });
  }

  function openDrawer() {
    if (!drawer || !drawer.hidden) return;
    lastFocused = document.activeElement;
    drawer.hidden = false;
    if (backdrop) backdrop.hidden = false;
    // Preserve whatever the page had set so closing never clobbers it.
    document.body.style.overflow = "hidden";
    setExpanded(true);
    // Move focus into the drawer; prefer the close button, else the first link.
    var target = drawer.querySelector("[data-drawer-close]") || drawer.querySelector(FOCUSABLE);
    if (target) target.focus();
  }

  function closeDrawer() {
    if (!drawer || drawer.hidden) return;
    drawer.hidden = true;
    if (backdrop) backdrop.hidden = true;
    document.body.style.overflow = "";
    setExpanded(false);
    if (lastFocused && document.contains(lastFocused)) lastFocused.focus();
    lastFocused = null;
  }

  drawerBtns.forEach(function (btn) {
    btn.addEventListener("click", openDrawer);
  });
  if (backdrop) backdrop.addEventListener("click", closeDrawer);
  document.addEventListener("keydown", function (e) {
    if (!drawer || drawer.hidden) return;
    if (e.key === "Escape") { e.preventDefault(); closeDrawer(); return; }
    // Keep Tab cycling inside the drawer while it is open.
    if (e.key === "Tab") {
      var items = Array.prototype.filter.call(
        drawer.querySelectorAll(FOCUSABLE),
        function (el) { return el.offsetParent !== null; }
      );
      if (!items.length) return;
      var first = items[0];
      var last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  });
  document.addEventListener("click", function (e) {
    if (e.target.closest("[data-drawer-close]")) closeDrawer();
  });
  // Navigating away (e.g. a cached back-navigation) must not leave the page locked.
  window.addEventListener("pageshow", function (e) { if (e.persisted) closeDrawer(); });

  /* ---------- Close button on alerts ---------- */
  document.addEventListener("click", function (e) {
    var close = e.target.closest("[data-dismiss-alert]");
    if (close) {
      e.preventDefault();
      var alertEl = close.closest(".alert");
      if (alertEl) alertEl.remove();
    }
  });

  /* Auto-hide success alerts after 6s */
  document.querySelectorAll(".alert-success").forEach(function (el) {
    setTimeout(function () {
      el.style.transition = "opacity .4s";
      el.style.opacity = "0";
      setTimeout(function () { el.remove(); }, 450);
    }, 6000);
  });

  /* ---------- Confirm actions (destructive buttons) ---------- */
  document.addEventListener("click", function (e) {
    var el = e.target.closest("[data-confirm]");
    if (!el) return;
    var msg = el.getAttribute("data-confirm") || "Are you sure?";
    if (!window.confirm(msg)) {
      e.preventDefault();
      e.stopPropagation();
    }
  });

  /* ---------- Nav active state ---------- */
  var current = location.pathname;
  document.querySelectorAll("a[data-nav]").forEach(function (a) {
    var href = a.getAttribute("href") || "";
    if (current === href || (href.length > 3 && current.indexOf(href) === 0)) {
      a.classList.add("active");
    }
  });

  /* ---------- Mark all notifications read button ---------- */
  var markAll = document.querySelector("[data-mark-all-read]");
  if (markAll) {
    markAll.addEventListener("click", function (e) {
      e.preventDefault();
      var url = markAll.getAttribute("href");
      fetch(url, { method: "POST", headers: { "X-Requested-With": "XMLHttpRequest" } })
        .then(function () {
          var dots = document.querySelectorAll(".notif-dot");
          dots.forEach(function (d) { d.remove(); });
          var items = document.querySelectorAll(".dropdown-item .unread");
          items.forEach(function (i) { i.classList.remove("unread"); });
        })
        .catch(function () {});
    });
  }
})();
