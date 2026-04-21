(function () {
    const raw = document.getElementById("tabModelsData");
    const models = raw ? JSON.parse(raw.textContent || "[]") : [];

    const card = document.getElementById("houseCard");
    const heroImage = document.getElementById("heroImage");
    const modelName = document.getElementById("modelName");
    const modelSubtitle = document.getElementById("modelSubtitle");
    const specGrid = document.getElementById("specGrid");
    const galleryMain = document.getElementById("galleryMain");
    const galleryDots = document.getElementById("galleryDots");
    const description = document.getElementById("modelDescription");
    const featureGrid = document.getElementById("featureGrid");
    const floorplanWrap = document.getElementById("floorplanWrap");
    const leadModelName = document.getElementById("leadModelName");
    const toggleBtn = document.getElementById("toggleDetailsBtn");
    const details = document.getElementById("detailsPanel");
    const likeBadge = document.getElementById("likeBadge");
    const nopeBadge = document.getElementById("nopeBadge");

    const filterCategory = document.getElementById("filterCategory");
    const filterSearch = document.getElementById("filterSearch");
    const filterBedrooms = document.getElementById("filterBedrooms");
    const filterBathrooms = document.getElementById("filterBathrooms");
    const filterToggleBtn = document.getElementById("filterToggleBtn");
    const filterPanel = document.getElementById("filterPanel");

    let filtered = models.slice();
    let activeIndex = 0;
    let galleryIndex = 0;
    let isAnimating = false;
    let gestureMode = null;

    function firstAvailableImage(model) {
        return model.hero_image || (model.gallery_images || [])[0] || model.floorplan_image || "/media/no-house.jpg";
    }

    function normalizeImageKey(src) {
        if (!src) return "";
        return String(src).trim().toLowerCase().split("#")[0].split("?")[0];
    }

    function cleanImages(model) {
        const heroKey = normalizeImageKey(model.hero_image);
        const list = (model.gallery_images || [])
            .filter(Boolean)
            .filter((src) => normalizeImageKey(src) !== heroKey);
        const seen = new Set();
        const deduped = list.filter((src) => {
            const key = normalizeImageKey(src);
            if (!key || seen.has(key)) return false;
            seen.add(key);
            return true;
        });
        if (deduped.length) return deduped;
        return model.hero_image ? [model.hero_image] : [];
    }

    function modelSpecs(model) {
        return [
            { label: "חדרי שינה", value: model.bedrooms || 0 },
            { label: "רחצה", value: model.bathrooms || 0 },
            { label: "מ״ר", value: model.area_m2 || 0 },
            { label: "קומות", value: model.floors || 1 },
            { label: "מטבחים", value: model.kitchens || 1 },
            { label: "סלונים", value: model.living_rooms || 1 }
        ];
    }

    function renderDots(images) {
        galleryDots.innerHTML = images
            .map((_, i) => `<i class="${i === galleryIndex ? "active" : ""}"></i>`)
            .join("");
    }

    function renderCard() {
        if (!filtered.length) {
            modelName.textContent = "לא נמצאו דגמים";
            modelSubtitle.textContent = "נסה לשנות סינון";
            heroImage.src = "/media/no-house.jpg";
            specGrid.innerHTML = "";
            galleryMain.src = "/media/no-house.jpg";
            galleryDots.innerHTML = "";
            description.textContent = "";
            featureGrid.innerHTML = "";
            floorplanWrap.innerHTML = "";
            leadModelName.value = "";
            return;
        }

        const model = filtered[activeIndex];
        const images = cleanImages(model);

        modelName.textContent = model.model_name || "דגם ללא שם";
        modelSubtitle.textContent = model.short_description || model.category_label || "";
        heroImage.src = firstAvailableImage(model);
        heroImage.alt = model.model_name || "";

        specGrid.innerHTML = modelSpecs(model)
            .map((spec) => `<div class="item"><span class="value">${spec.value}</span><span class="label">${spec.label}</span></div>`)
            .join("");

        galleryIndex = Math.min(galleryIndex, Math.max(images.length - 1, 0));
        galleryMain.src = images[galleryIndex] || firstAvailableImage(model);
        galleryMain.alt = model.model_name || "";
        renderDots(images);

        description.textContent = model.long_description || model.short_description || "";
        featureGrid.innerHTML = (model.feature_bullets || [])
            .slice(0, 8)
            .map((item) => `<span>${item}</span>`)
            .join("");

        floorplanWrap.innerHTML = model.floorplan_image
            ? `<img src="${model.floorplan_image}" alt="שרטוט ${model.model_name || ""}">`
            : "<p>אין כרגע שרטוט לדגם זה.</p>";

        leadModelName.value = model.model_name || "";
    }

    function animateSwipe(direction) {
        if (isAnimating || !filtered.length) return;
        isAnimating = true;
        const x = direction === "next" ? -420 : 420;
        card.style.transition = "transform .22s ease, opacity .22s ease";
        card.style.transform = `translateX(${x}px) rotate(${direction === "next" ? "-10deg" : "10deg"})`;
        card.style.opacity = "0";
        setTimeout(() => {
            if (!filtered.length) {
                isAnimating = false;
                return;
            }
            activeIndex = direction === "next"
                ? (activeIndex + 1) % filtered.length
                : (activeIndex - 1 + filtered.length) % filtered.length;
            galleryIndex = 0;
            card.style.transition = "none";
            card.style.transform = `translateX(${direction === "next" ? "300px" : "-300px"})`;
            renderCard();
            requestAnimationFrame(() => {
                card.style.transition = "transform .2s ease, opacity .2s ease";
                card.style.transform = "translateX(0) rotate(0)";
                card.style.opacity = "1";
                setTimeout(() => {
                    isAnimating = false;
                }, 220);
            });
        }, 210);
    }

    function setBadges(deltaX) {
        const intensity = Math.min(Math.abs(deltaX) / 130, 1);
        likeBadge.style.opacity = deltaX < 0 ? String(intensity) : "0";
        nopeBadge.style.opacity = deltaX > 0 ? String(intensity) : "0";
    }

    function applyFilters() {
        const cat = filterCategory.value;
        const q = (filterSearch.value || "").trim().toLowerCase();
        const beds = Number(filterBedrooms.value || 0);
        const baths = Number(filterBathrooms.value || 0);

        filtered = models.filter((m) => {
            if (cat && cat !== "all" && m.category !== cat) return false;
            if (beds && Number(m.bedrooms || 0) < beds) return false;
            if (baths && Number(m.bathrooms || 0) < baths) return false;
            if (q) {
                const haystack = `${m.model_name || ""} ${m.short_description || ""}`.toLowerCase();
                if (!haystack.includes(q)) return false;
            }
            return true;
        });
        activeIndex = 0;
        galleryIndex = 0;
        renderCard();
        if (window.matchMedia("(max-width: 979px)").matches && filterPanel && !filterPanel.hasAttribute("hidden")) {
            filterPanel.setAttribute("hidden", "");
            if (filterToggleBtn) filterToggleBtn.setAttribute("aria-expanded", "false");
        }
    }

    function syncStickyOffsets() {
        const navbar = document.querySelector(".navbar");
        const actions = document.querySelector(".actions");
        const navHeight = navbar ? navbar.offsetHeight : 94;
        const actionsHeight = actions ? actions.offsetHeight + 16 : 96;
        document.documentElement.style.setProperty("--nav-height", `${navHeight}px`);
        document.documentElement.style.setProperty("--actions-height", `${actionsHeight}px`);
    }

    document.getElementById("nextHouseBtn").addEventListener("click", () => animateSwipe("next"));
    document.getElementById("prevHouseBtn").addEventListener("click", () => animateSwipe("prev"));
    document.getElementById("galleryNextBtn").addEventListener("click", () => {
        const model = filtered[activeIndex];
        const images = cleanImages(model || {});
        if (!images.length) return;
        galleryIndex = (galleryIndex + 1) % images.length;
        galleryMain.src = images[galleryIndex];
        renderDots(images);
    });
    document.getElementById("galleryPrevBtn").addEventListener("click", () => {
        const model = filtered[activeIndex];
        const images = cleanImages(model || {});
        if (!images.length) return;
        galleryIndex = (galleryIndex - 1 + images.length) % images.length;
        galleryMain.src = images[galleryIndex];
        renderDots(images);
    });

    [filterCategory, filterSearch, filterBedrooms, filterBathrooms].forEach((input) => {
        input.addEventListener("input", applyFilters);
        input.addEventListener("change", applyFilters);
    });

    document.getElementById("clearFilters").addEventListener("click", () => {
        filterCategory.value = "all";
        filterSearch.value = "";
        filterBedrooms.value = "";
        filterBathrooms.value = "";
        applyFilters();
    });

    if (filterToggleBtn && filterPanel) {
        filterToggleBtn.addEventListener("click", () => {
            const isHidden = filterPanel.hasAttribute("hidden");
            if (isHidden) {
                filterPanel.removeAttribute("hidden");
                filterToggleBtn.setAttribute("aria-expanded", "true");
            } else {
                filterPanel.setAttribute("hidden", "");
                filterToggleBtn.setAttribute("aria-expanded", "false");
            }
            syncStickyOffsets();
        });
    }

    toggleBtn.addEventListener("click", () => {
        const hidden = details.hasAttribute("hidden");
        if (hidden) {
            details.removeAttribute("hidden");
            toggleBtn.textContent = "הסתר מידע מלא";
        } else {
            details.setAttribute("hidden", "");
            toggleBtn.textContent = "הצג מידע מלא";
        }
    });

    let dragging = false;
    let startX = 0;
    let currentX = 0;

    function onStart(x) {
        if (isAnimating) return;
        dragging = true;
        startX = x;
        currentX = x;
        gestureMode = null;
        card.style.transition = "none";
    }

    function onMove(x, yDelta) {
        if (!dragging) return;
        currentX = x;
        const delta = currentX - startX;
        if (!gestureMode) {
            const absX = Math.abs(delta);
            const absY = Math.abs(yDelta || 0);
            gestureMode = absX > absY ? "horizontal" : "vertical";
        }
        if (gestureMode !== "horizontal") return;
        card.style.transform = `translateX(${delta}px) rotate(${delta / 22}deg)`;
        setBadges(delta);
    }

    function onEnd() {
        if (!dragging || isAnimating) return;
        dragging = false;
        if (gestureMode === "vertical") {
            gestureMode = null;
            return;
        }
        const delta = currentX - startX;
        likeBadge.style.opacity = "0";
        nopeBadge.style.opacity = "0";
        if (Math.abs(delta) > 110) {
            animateSwipe(delta < 0 ? "next" : "prev");
            return;
        }
        card.style.transition = "transform .2s ease";
        card.style.transform = "translateX(0) rotate(0)";
        gestureMode = null;
    }

    const swipeTarget = document.querySelector(".hero") || card;
    let startY = 0;
    swipeTarget.addEventListener("touchstart", (e) => {
        startY = e.touches[0].clientY;
        onStart(e.touches[0].clientX);
    }, { passive: true });
    swipeTarget.addEventListener("touchmove", (e) => {
        onMove(e.touches[0].clientX, e.touches[0].clientY - startY);
    }, { passive: true });
    swipeTarget.addEventListener("touchend", onEnd, { passive: true });
    swipeTarget.addEventListener("mousedown", (e) => onStart(e.clientX));
    window.addEventListener("mousemove", (e) => onMove(e.clientX, 0));
    window.addEventListener("mouseup", onEnd);
    window.addEventListener("resize", syncStickyOffsets);

    renderCard();
    syncStickyOffsets();
    if (filterPanel && window.matchMedia("(min-width: 980px)").matches) {
        filterPanel.removeAttribute("hidden");
        if (filterToggleBtn) filterToggleBtn.setAttribute("aria-expanded", "true");
    }
})();
