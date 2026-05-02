(function () {
  "use strict";

  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function pushAnalytics(eventName, params) {
    params = params || {};
    if (typeof window.gtag === "function") {
      window.gtag("event", eventName, params);
    }
    if (typeof window.fbq === "function") {
      window.fbq("trackCustom", eventName, params);
    }
  }

  function initMobileNav() {
    var header = document.querySelector("[data-site-header]");
    if (!header) return;

    var toggle = header.querySelector("[data-nav-toggle]");
    var backdrop = header.querySelector("[data-drawer-backdrop]");
    var drawerLinks = header.querySelectorAll(".site-nav a");

    function setOpen(open) {
      header.classList.toggle("is-open", open);
      document.body.classList.toggle("nav-open", open);
      if (toggle) {
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
      }
    }

    if (toggle) {
      toggle.addEventListener("click", function () {
        setOpen(!header.classList.contains("is-open"));
      });
    }

    if (backdrop) {
      backdrop.addEventListener("click", function () {
        setOpen(false);
      });
    }

    drawerLinks.forEach(function (link) {
      link.addEventListener("click", function () {
        if (window.matchMedia("(max-width: 1024px)").matches) {
          setOpen(false);
        }
      });
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && header.classList.contains("is-open")) {
        setOpen(false);
        if (toggle) toggle.focus();
      }
    });
  }

  function initFaqAccordion() {
    document.querySelectorAll("[data-faq-accordion] .faq-item__question").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var item = btn.closest(".faq-item");
        if (!item) return;
        var panel = item.querySelector(".faq-item__panel");
        var open = !item.classList.contains("is-open");
        var root = item.closest("[data-faq-accordion]");
        if (root && root.getAttribute("data-faq-single") !== "false") {
          root.querySelectorAll(".faq-item.is-open").forEach(function (o) {
            if (o !== item) {
              o.classList.remove("is-open");
              var ob = o.querySelector(".faq-item__question");
              var op = o.querySelector(".faq-item__panel");
              if (ob) ob.setAttribute("aria-expanded", "false");
              if (op) op.hidden = true;
            }
          });
        }
        item.classList.toggle("is-open", open);
        btn.setAttribute("aria-expanded", open ? "true" : "false");
        if (panel) panel.hidden = !open;
      });

      btn.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          btn.click();
        }
      });
    });
  }

  function initSmoothAnchors() {
    document.querySelectorAll('a[href^="#"]').forEach(function (a) {
      var id = a.getAttribute("href");
      if (!id || id === "#") return;
      a.addEventListener("click", function (e) {
        var target = document.querySelector(id);
        if (!target) return;
        e.preventDefault();
        if (!prefersReducedMotion()) {
          target.scrollIntoView({ behavior: "smooth", block: "start" });
        } else {
          target.scrollIntoView({ block: "start" });
        }
        try {
          history.replaceState(null, "", id);
        } catch (err) {}
      });
    });
  }

  function initAnalyticsClicks() {
    document.addEventListener(
      "click",
      function (e) {
        var wa = e.target.closest('a[href*="wa.me"], a.float-wa');
        if (wa) {
          pushAnalytics("whatsapp_click", { link_url: wa.href });
          return;
        }
        var tel = e.target.closest('a[href^="tel:"]');
        if (tel) {
          pushAnalytics("phone_click", { link_url: tel.href });
          return;
        }
        var quote = e.target.closest("[data-analytics-quote]");
        if (quote) {
          pushAnalytics("product_quote_click", {
            link_url: quote.href || "",
            text: (quote.textContent || "").trim(),
          });
        }
      },
      true
    );

    var params = new URLSearchParams(window.location.search);
    if (params.get("lead_ok") === "1" || window.location.hash === "#lead-success") {
      pushAnalytics("lead_form_submit", { status: "success" });
      if (params.get("lead_ok") === "1") {
        try {
          params.delete("lead_ok");
          var qs = params.toString();
          var path = window.location.pathname + (qs ? "?" + qs : "") + window.location.hash;
          history.replaceState(null, "", path);
        } catch (err) {}
      }
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    initMobileNav();
    initFaqAccordion();
    initSmoothAnchors();
    initAnalyticsClicks();
  });
})();
