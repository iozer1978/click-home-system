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
    function animateOpen(item, panel) {
      if (!panel) return;
      panel.hidden = false;
      panel.style.maxHeight = "0px";
      panel.style.opacity = "0";
      requestAnimationFrame(function () {
        panel.style.maxHeight = panel.scrollHeight + "px";
        panel.style.opacity = "1";
      });
      item.classList.add("is-open");
    }

    function animateClose(item, panel) {
      if (!panel) return;
      panel.style.maxHeight = panel.scrollHeight + "px";
      panel.style.opacity = "1";
      requestAnimationFrame(function () {
        panel.style.maxHeight = "0px";
        panel.style.opacity = "0";
      });
      window.setTimeout(function () {
        if (!item.classList.contains("is-open")) {
          panel.hidden = true;
        }
      }, 360);
      item.classList.remove("is-open");
    }

    document.querySelectorAll("[data-faq-accordion] .faq-item__question").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var item = btn.closest(".faq-item");
        if (!item) return;
        var panel = item.querySelector(".faq-item__panel");
        var open = !item.classList.contains("is-open");
        var root = item.closest("[data-faq-accordion]");
        var beforeTop = btn.getBoundingClientRect().top;
        if (root && root.getAttribute("data-faq-single") !== "false") {
          root.querySelectorAll(".faq-item.is-open").forEach(function (o) {
            if (o !== item) {
              var ob = o.querySelector(".faq-item__question");
              var op = o.querySelector(".faq-item__panel");
              if (ob) ob.setAttribute("aria-expanded", "false");
              animateClose(o, op);
            }
          });
        }
        btn.setAttribute("aria-expanded", open ? "true" : "false");
        if (open) {
          animateOpen(item, panel);
        } else {
          animateClose(item, panel);
        }

        // Keep the clicked question visually anchored in place.
        // This prevents page jumps when large panels above collapse/open.
        requestAnimationFrame(function () {
          var afterTop = btn.getBoundingClientRect().top;
          var delta = afterTop - beforeTop;
          if (Math.abs(delta) > 1) {
            window.scrollBy(0, delta);
          }
        });
      });

      btn.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          btn.click();
        }
      });
    });

    document.querySelectorAll("[data-faq-accordion] .faq-item").forEach(function (item) {
      var panel = item.querySelector(".faq-item__panel");
      var btn = item.querySelector(".faq-item__question");
      if (!panel || !btn) return;
      if (item.classList.contains("is-open")) {
        panel.hidden = false;
        panel.style.maxHeight = panel.scrollHeight + "px";
        panel.style.opacity = "1";
        btn.setAttribute("aria-expanded", "true");
      } else {
        panel.style.maxHeight = "0px";
        panel.style.opacity = "0";
        panel.hidden = true;
        btn.setAttribute("aria-expanded", "false");
      }
    });
  }

  function escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function initFaqFromData() {
    var root = document.querySelector("[data-faq-component]");
    if (!root) return null;

    var list = root.querySelector("[data-faq-accordion]");
    var search = root.querySelector("[data-faq-search]");
    var data = Array.isArray(window.CLICK_HOME_FAQ_DATA) ? window.CLICK_HOME_FAQ_DATA : [];
    if (!list || !data.length) return null;

    function benefitCard(benefit) {
      return (
        '<div class="home-faq__benefit-card">' +
        '<div class="home-faq__benefit-title"><span class="home-faq__benefit-emoji">' + escapeHtml(benefit.icon || "") + "</span>" + escapeHtml(benefit.title || "") + "</div>" +
        (benefit.description ? '<p class="home-faq__benefit-desc">' + escapeHtml(benefit.description) + "</p>" : "") +
        "</div>"
      );
    }

    function render(items) {
      if (!items.length) {
        list.innerHTML = '<div class="faq-item faq-item--empty"><div class="faq-item__panel" style="display:block;">לא נמצאו תוצאות לחיפוש.</div></div>';
        return;
      }

      list.innerHTML = items
        .map(function (item, index) {
          var panelId = "faq-panel-" + (index + 1);
          var isOpen = index === 0;
          var intro = (item.introParagraphs || [])
            .map(function (paragraph) {
              return "<p>" + escapeHtml(paragraph) + "</p>";
            })
            .join("");
          var benefits = (item.benefits || []).map(benefitCard).join("");
          var highlights = (item.highlights || [])
            .map(function (hl) {
              return "<span>" + escapeHtml(hl) + "</span>";
            })
            .join("");

          return (
            '<div class="faq-item' + (isOpen ? " is-open" : "") + '">' +
            '<button type="button" class="faq-item__question" aria-expanded="' + (isOpen ? "true" : "false") + '" aria-controls="' + panelId + '">' +
            '<span class="home-faq__q-head">' + escapeHtml(item.title || "") + "</span>" +
            '<span class="faq-item__icon" aria-hidden="true"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></span>' +
            "</button>" +
            '<div class="faq-item__panel" id="' + panelId + '"' + (isOpen ? "" : " hidden") + ">" +
            intro +
            '<h3 class="home-faq__inner-title">יתרונות מרכזיים</h3>' +
            '<div class="home-faq__long-benefits">' +
            benefits +
            "</div>" +
            '<h3 class="home-faq__inner-title">סיכום מודגש</h3>' +
            '<div class="home-faq__highlight">' + escapeHtml(item.summary || "") + "</div>" +
            '<div class="home-faq__quick-highlights">' + highlights + "</div>" +
            "</div>" +
            "</div>"
          );
        })
        .join("");
    }

    render(data);
    initFaqAccordion();

    if (search) {
      search.addEventListener("input", function () {
        var query = (search.value || "").trim().toLowerCase();
        if (!query) {
          render(data);
          initFaqAccordion();
          return;
        }
        var filtered = data.filter(function (item) {
          var text =
            (item.title || "") +
            " " +
            (item.summary || "") +
            " " +
            (item.introParagraphs || []).join(" ") +
            " " +
            (item.highlights || []).join(" ") +
            " " +
            (item.benefits || [])
              .map(function (benefit) {
                return (benefit.icon || "") + " " + (benefit.title || "") + " " + (benefit.description || "");
              })
              .join(" ");
          return text.toLowerCase().indexOf(query) !== -1;
        });
        render(filtered);
        initFaqAccordion();
      });
    }

    return true;
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

  function initScrollReveal() {
    var items = document.querySelectorAll("[data-scroll-reveal]");
    if (!items.length) return;

    if (prefersReducedMotion() || typeof IntersectionObserver === "undefined") {
      items.forEach(function (item) {
        item.classList.add("is-visible");
      });
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.18, rootMargin: "0px 0px -6% 0px" }
    );

    items.forEach(function (item) {
      observer.observe(item);
    });
  }

  function initTestimonialsCarousel() {
    var root = document.querySelector("[data-testimonials-carousel]");
    if (!root) return;

    var track = root.querySelector(".home-testimonials__track");
    var slides = root.querySelectorAll("[data-slide]");
    var prevBtn = root.querySelector(".home-testimonials__nav--prev");
    var nextBtn = root.querySelector(".home-testimonials__nav--next");
    var dots = root.querySelectorAll("[data-dot]");
    if (!track || !slides.length) return;

    var index = 0;
    var autoplay = null;

    function slidesPerView() {
      if (window.innerWidth >= 1100) return 3;
      if (window.innerWidth >= 760) return 2;
      return 1;
    }

    function maxIndex() {
      return Math.max(0, slides.length - slidesPerView());
    }

    function updateDots() {
      var max = maxIndex();
      var safeIndex = Math.min(index, Math.max(0, max));
      dots.forEach(function (dot, dotIndex) {
        dot.classList.toggle("is-active", dotIndex === safeIndex);
      });
    }

    function update() {
      var clamped = Math.max(0, Math.min(index, maxIndex()));
      index = clamped;
      var firstSlide = slides[0];
      var gap = Number(window.getComputedStyle(track).columnGap.replace("px", "")) || Number(window.getComputedStyle(track).gap.replace("px", "")) || 0;
      var slideWidth = firstSlide ? firstSlide.getBoundingClientRect().width : 0;
      var offsetPx = (slideWidth + gap) * index;
      track.style.transform = "translateX(-" + offsetPx + "px)";
      updateDots();

      var disabled = maxIndex() === 0;
      if (prevBtn) prevBtn.disabled = disabled;
      if (nextBtn) nextBtn.disabled = disabled;
    }

    function go(step) {
      var max = maxIndex();
      if (max === 0) return;
      index += step;
      if (index > max) index = 0;
      if (index < 0) index = max;
      update();
    }

    function startAutoplay() {
      if (prefersReducedMotion()) return;
      stopAutoplay();
      autoplay = window.setInterval(function () {
        go(1);
      }, 6000);
    }

    function stopAutoplay() {
      if (!autoplay) return;
      window.clearInterval(autoplay);
      autoplay = null;
    }

    if (prevBtn) prevBtn.addEventListener("click", function () { go(-1); });
    if (nextBtn) nextBtn.addEventListener("click", function () { go(1); });
    dots.forEach(function (dot) {
      dot.addEventListener("click", function () {
        index = Number(dot.getAttribute("data-dot")) || 0;
        update();
      });
    });

    root.addEventListener("mouseenter", stopAutoplay);
    root.addEventListener("mouseleave", startAutoplay);
    root.addEventListener("focusin", stopAutoplay);
    root.addEventListener("focusout", startAutoplay);
    window.addEventListener("resize", update);

    update();
    startAutoplay();
  }

  function initProjectCardsSelect() {
    var root = document.querySelector("[data-project-options]");
    var select = document.querySelector("#lead-interest");
    if (!root || !select) return;

    var buttons = root.querySelectorAll("button[data-value]");
    if (!buttons.length) return;

    function setActive(value) {
      buttons.forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute("data-value") === value);
      });
    }

    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var value = btn.getAttribute("data-value") || "";
        select.value = value;
        setActive(value);
      });
    });

    select.addEventListener("change", function () {
      setActive(select.value);
    });

    setActive(select.value);
  }

  document.addEventListener("DOMContentLoaded", function () {
    initMobileNav();
    if (!initFaqFromData()) {
      initFaqAccordion();
    }
    initSmoothAnchors();
    initAnalyticsClicks();
    initScrollReveal();
    initTestimonialsCarousel();
    initProjectCardsSelect();
  });
})();
