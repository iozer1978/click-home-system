(function () {
    const dataNode = document.getElementById("tabModelsData");
    if (!dataNode) return;

    let models = [];
    try {
        models = JSON.parse(dataNode.textContent || "[]");
    } catch (err) {
        models = [];
    }

    const viewport = document.getElementById("swipeViewport");
    const modelName = document.getElementById("modelName");
    const modelSubtitle = document.getElementById("modelSubtitle");
    const heroImage = document.getElementById("heroImage");
    const detailsBtn = document.getElementById("detailsBtn");
    const quoteBtn = document.getElementById("quoteBtn");
    const specTags = document.getElementById("specTags");
    const galleryMain = document.getElementById("galleryMain");
    const galleryMini = document.getElementById("galleryMini");
    const galleryDots = document.getElementById("galleryDots");
    const galleryPrevBtn = document.getElementById("galleryPrevBtn");
    const galleryNextBtn = document.getElementById("galleryNextBtn");
    const modelDescription = document.getElementById("modelDescription");
    const paramGrid = document.getElementById("paramGrid");
    const featureGrid = document.getElementById("featureGrid");
    const floorplanWrap = document.getElementById("floorplanWrap");
    const lifestyleImage = document.getElementById("lifestyleImage");
    const leadModelName = document.getElementById("leadModelName");

    const filterCategory = document.getElementById("filterCategory");
    const filterSearch = document.getElementById("filterSearch");
    const filterBedrooms = document.getElementById("filterBedrooms");
    const filterBathrooms = document.getElementById("filterBathrooms");
    const filterFloors = document.getElementById("filterFloors");
    const filterArea = document.getElementById("filterArea");
    const clearFilters = document.getElementById("clearFilters");
    const prevHouseBtn = document.getElementById("prevHouseBtn");
    const nextHouseBtn = document.getElementById("nextHouseBtn");

    const iconPool = ["\u2302", "\u2699", "\u2733", "\u25a3", "\u2726", "\u2692", "\u25a9", "\u2b22", "\u2618"];

    let filtered = models.slice();
    let activeIndex = 0;
    let activeGalleryIndex = 0;

    function uniqImages(list) {
        const seen = new Set();
        const out = [];
        (list || []).forEach((url) => {
            if (!url) return;
            const normalized = String(url).split("?")[0].replace(/-\d+x\d+(?=\.)/i, "").toLowerCase();
            if (seen.has(normalized)) return;
            seen.add(normalized);
            out.push(url);
        });
        return out;
    }

    function numberValue(value) {
        const n = Number(value);
        return Number.isFinite(n) ? n : 0;
    }

    function getFilterState() {
        return {
            category: filterCategory.value || "all",
            q: (filterSearch.value || "").trim().toLowerCase(),
            bedrooms: numberValue(filterBedrooms.value),
            bathrooms: numberValue(filterBathrooms.value),
            floors: numberValue(filterFloors.value),
            areaMin: numberValue(filterArea.value),
        };
    }

    function updateQuery(filters) {
        const params = new URLSearchParams();
        if (filters.category && filters.category !== "all") params.set("category", filters.category);
        if (filters.q) params.set("q", filters.q);
        if (filters.bedrooms) params.set("bedrooms", String(filters.bedrooms));
        if (filters.bathrooms) params.set("bathrooms", String(filters.bathrooms));
        if (filters.floors) params.set("floors", String(filters.floors));
        if (filters.areaMin) params.set("area_min", String(filters.areaMin));
        const nextUrl = `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}`;
        history.replaceState({}, "", nextUrl);
    }

    function applyFilters() {
        const filters = getFilterState();
        filtered = models.filter((item) => {
            if (filters.category !== "all" && item.category !== filters.category) return false;
            if (filters.q && !`${item.model_name} ${item.short_description_he}`.toLowerCase().includes(filters.q)) return false;
            if (filters.bedrooms && numberValue(item.bedrooms) < filters.bedrooms) return false;
            if (filters.bathrooms && numberValue(item.bathrooms) < filters.bathrooms) return false;
            if (filters.floors && numberValue(item.floors) < filters.floors) return false;
            if (filters.areaMin && numberValue(item.area_m2) < filters.areaMin) return false;
            return true;
        });
        activeIndex = 0;
        updateQuery(filters);
        renderSlide();
    }

    function updateGallery(model) {
        const images = uniqImages(model.gallery_images && model.gallery_images.length ? model.gallery_images : [model.main_image]).slice(0, 8);
        if (activeGalleryIndex >= images.length) activeGalleryIndex = 0;
        galleryMain.src = images[activeGalleryIndex];
        galleryMain.alt = `גלריית ${model.model_name}`;

        galleryMini.innerHTML = "";
        galleryDots.innerHTML = "";

        images.forEach((img, idx) => {
            const miniBtn = document.createElement("button");
            miniBtn.type = "button";
            miniBtn.innerHTML = `<img src="${img}" alt="תמונה ${idx + 1}">`;
            miniBtn.addEventListener("click", function () {
                activeGalleryIndex = idx;
                updateGallery(model);
            });
            galleryMini.appendChild(miniBtn);

            const dot = document.createElement("span");
            if (idx === activeGalleryIndex) dot.classList.add("active");
            galleryDots.appendChild(dot);
        });
    }

    function nextGallery(model) {
        const images = (model.gallery_images && model.gallery_images.length ? model.gallery_images : [model.main_image]).slice(0, 8);
        if (!images.length) return;
        activeGalleryIndex = (activeGalleryIndex + 1) % images.length;
        updateGallery(model);
    }

    function prevGallery(model) {
        const images = (model.gallery_images && model.gallery_images.length ? model.gallery_images : [model.main_image]).slice(0, 8);
        if (!images.length) return;
        activeGalleryIndex = (activeGalleryIndex - 1 + images.length) % images.length;
        updateGallery(model);
    }

    function renderSlide() {
        const empty = filtered.length === 0;
        if (empty) {
            modelName.textContent = "לא נמצאו דגמים";
            modelSubtitle.textContent = "נסו לשנות את הפילטרים למעלה";
            heroImage.src = "/static/images/tab/placeholders/modular.svg";
            modelDescription.textContent = "הקטלוג כרגע ריק עבור הסינון הנבחר.";
            specTags.innerHTML = "";
            featureGrid.innerHTML = "";
            paramGrid.innerHTML = "";
            floorplanWrap.innerHTML = "";
            galleryMain.src = "/static/images/tab/placeholders/modular.svg";
            galleryMini.innerHTML = "";
            galleryDots.innerHTML = "";
            lifestyleImage.src = "/static/images/tab/placeholders/single-family.svg";
            if (leadModelName) leadModelName.value = "";
            return;
        }

        const model = filtered[activeIndex];
        const houseSlide = document.getElementById("houseSlide");
        houseSlide.classList.remove("animate-swap");
        requestAnimationFrame(() => houseSlide.classList.add("animate-swap"));
        const subtitle = model.subtitle_he || model.short_description_he || "בית מודרני חכם למשפחה קטנה";

        modelName.textContent = model.model_name_he || model.model_name;
        modelSubtitle.textContent = subtitle;
        heroImage.src = model.hero_image || model.main_image;
        heroImage.alt = `תמונת הירו ${model.model_name}`;
        const lenText = model.length_m ? `${model.length_m} מ'` : "לא צוין";
        const widthText = model.width_m ? `${model.width_m} מ'` : "לא צוין";
        const detailed = model.description_he || model.full_description_he;
        modelDescription.textContent = `${detailed} מידות הדגם: אורך ${lenText}, רוחב ${widthText}.`;
        lifestyleImage.src = model.lifestyle_image || model.main_image;
        lifestyleImage.alt = `אווירה עבור ${model.model_name}`;
        if (leadModelName) leadModelName.value = model.model_name;

        const specs = [
            `${model.bedrooms || 0} חדרי שינה`,
            `${model.bathrooms || 0} חדרי רחצה`,
            `${model.area_m2 || 0} מ"ר`,
            `${model.floors || 1} קומות`,
            `${model.kitchen_count || model.kitchens || 1} מטבחים`,
            `${model.living_rooms || 1} סלון`,
        ];
        specTags.innerHTML = specs.map((text) => `<span>${text}</span>`).join("");

        const features = (model.features_he && model.features_he.length ? model.features_he : ["תכנון חכם", "עיצוב מודרני", "איכות בנייה גבוהה"]).slice(0, 9);
        featureGrid.innerHTML = features
            .map((feature, idx) => `<article><span>${iconPool[idx % iconPool.length]}</span><p>${feature}</p></article>`)
            .join("");

        const params = [
            ["שטח כולל", `${model.area_m2 || 0} מ"ר`],
            ["אורך", lenText],
            ["רוחב", widthText],
            ["קטגוריה", model.category_label_he || "כללי"],
            ["חדרי שינה", String(model.bedrooms || 0)],
            ["חדרי רחצה", String(model.bathrooms || 0)],
        ];
        paramGrid.innerHTML = params.map((item) => `<dl class="param-item"><dt>${item[0]}</dt><dd>${item[1]}</dd></dl>`).join("");

        const plans = uniqImages(model.floorplan_images && model.floorplan_images.length ? model.floorplan_images : []).slice(0, 1);
        floorplanWrap.innerHTML = plans.length
            ? plans.map((img) => `<img class="floorplan-main" src="${img}" alt="שרטוט הדגם">`).join("")
            : `<p style="margin:0;color:#6b6459;">כרגע אין שרטוט זמין לדגם זה.</p>`;

        updateGallery(model);
    }

    function nextSlide() {
        if (!filtered.length) return;
        activeIndex = (activeIndex + 1) % filtered.length;
        activeGalleryIndex = 0;
        renderSlide();
    }

    function prevSlide() {
        if (!filtered.length) return;
        activeIndex = (activeIndex - 1 + filtered.length) % filtered.length;
        activeGalleryIndex = 0;
        renderSlide();
    }

    function bindSwipe() {
        let startX = 0;
        let startY = 0;
        let isTouching = false;

        viewport.addEventListener("touchstart", function (event) {
            const touch = event.changedTouches[0];
            startX = touch.clientX;
            startY = touch.clientY;
            isTouching = true;
        }, { passive: true });

        viewport.addEventListener("touchend", function (event) {
            if (!isTouching) return;
            isTouching = false;
            const touch = event.changedTouches[0];
            const dx = touch.clientX - startX;
            const dy = touch.clientY - startY;
            if (Math.abs(dx) < 45 || Math.abs(dx) < Math.abs(dy)) return;
            if (dx < 0) nextSlide();
            else prevSlide();
        }, { passive: true });
    }

    function bindActions() {
        [detailsBtn, quoteBtn].forEach((btn) => {
            btn.addEventListener("click", function () {
                document.getElementById("leadFormSection").scrollIntoView({ behavior: "smooth", block: "start" });
            });
        });

        document.querySelectorAll(".lead-trigger").forEach((btn) => {
            btn.addEventListener("click", function () {
                document.getElementById("leadFormSection").scrollIntoView({ behavior: "smooth", block: "start" });
                const firstInput = document.querySelector(".lead-form input[name='full_name']");
                if (firstInput) firstInput.focus();
            });
        });

        [filterCategory, filterSearch, filterBedrooms, filterBathrooms, filterFloors, filterArea].forEach((input) => {
            input.addEventListener("input", applyFilters);
            input.addEventListener("change", applyFilters);
        });

        clearFilters.addEventListener("click", function () {
            filterCategory.value = "all";
            filterSearch.value = "";
            filterBedrooms.value = "";
            filterBathrooms.value = "";
            filterFloors.value = "";
            filterArea.value = "";
            applyFilters();
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "ArrowLeft") nextSlide();
            if (event.key === "ArrowRight") prevSlide();
        });

        prevHouseBtn.addEventListener("click", prevSlide);
        nextHouseBtn.addEventListener("click", nextSlide);
        galleryPrevBtn.addEventListener("click", function () {
            if (!filtered.length) return;
            prevGallery(filtered[activeIndex]);
        });
        galleryNextBtn.addEventListener("click", function () {
            if (!filtered.length) return;
            nextGallery(filtered[activeIndex]);
        });
    }

    bindActions();
    bindSwipe();
    applyFilters();
})();
