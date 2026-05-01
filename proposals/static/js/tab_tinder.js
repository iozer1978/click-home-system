(function () {
    const raw = document.getElementById("tabModelsData");
    const inputModels = raw ? JSON.parse(raw.textContent || "[]") : [];
    const iconMap = {
        toilets: "/tab/icons/toilets.jpg/",
        bathrooms: "/tab/icons/bathrooms.jpg/",
        bedrooms: "/tab/icons/bedrooms.jpg/",
        kitchens: "/tab/icons/kitchen.jpg/",
        livingRooms: "/tab/icons/living-room.jpg/",
        parking: "/tab/icons/parking.jpg/",
        stairs: "/tab/icons/stairs.jpg/"
    };

    function toNumber(value) {
        if (value === null || value === undefined || value === "") return null;
        const n = Number(value);
        return Number.isFinite(n) ? n : null;
    }

    function normalizeImageKey(src) {
        if (!src) return "";
        return String(src).trim().toLowerCase().split("#")[0].split("?")[0];
    }

    function isBlockedBrandingImage(src) {
        const key = normalizeImageKey(src);
        if (!key) return true;
        const filename = key.split("/").pop() || key;
        const blockedTokens = [
            "smarthouse",
            "logo",
            "watermark"
        ];
        return blockedTokens.some((token) => filename.includes(token));
    }

    function dedupeImages(images) {
        const seen = new Set();
        return (images || []).filter((src) => {
            const key = normalizeImageKey(src);
            if (!key || isBlockedBrandingImage(src) || seen.has(key)) return false;
            seen.add(key);
            return true;
        });
    }

    function normalizeModel(model, idx) {
        const title = model.model_name_he || model.model_name || `דגם ${idx + 1}`;
        const categoryLabel = model.category_label_he || (
            model.category === "modular" ? "בתים מודולריים" :
            model.category === "adu" ? "ADU" : "בתים פרטיים"
        );
        const candidates = dedupeImages([
            model.hero_image,
            model.main_image,
            ...(model.gallery_images || []),
            ...(model.images || [])
        ]);
        const hero = candidates[0] || "/media/no-house.jpg";
        const galleryImages = candidates.length ? candidates : ["/media/no-house.jpg"];
        const floorplanImage = dedupeImages([
            model.floorplan_image,
            ...((model.floorplan_images || []))
        ])[0] || null;

        const bathrooms = toNumber(model.bathrooms);
        const floors = toNumber(model.floors);
        const stairs = toNumber(model.stairs);
        const computedStairs = stairs !== null ? stairs : (floors !== null && floors > 1 ? 1 : 0);

        return {
            id: model.id || `model-${idx + 1}`,
            slug: model.slug || `model-${idx + 1}`,
            title: title,
            subtitle: model.subtitle_he || model.short_description_he || model.short_description || categoryLabel,
            typeKey: model.category || "single-family",
            typeLabel: categoryLabel,
            description: model.full_description_he || model.description_he || model.long_description || model.short_description_he || "",
            features: (model.features_he || model.feature_bullets || []).filter(Boolean),
            heroImage: hero,
            galleryImages: galleryImages.length ? galleryImages : ["/media/no-house.jpg"],
            floorplanImage: floorplanImage,
            dimensions: {
                area: toNumber(model.area_m2),
                length: toNumber(model.length_m),
                width: toNumber(model.width_m)
            },
            specs: {
                bedrooms: toNumber(model.bedrooms),
                livingRooms: toNumber(model.living_rooms),
                bathrooms: bathrooms,
                toilets: toNumber(model.toilets) !== null ? toNumber(model.toilets) : bathrooms,
                parking: toNumber(model.parking) !== null ? toNumber(model.parking) : toNumber(model.garages),
                kitchens: toNumber(model.kitchens) !== null ? toNumber(model.kitchens) : toNumber(model.kitchen_count),
                stairs: computedStairs
            }
        };
    }

    const allModels = (inputModels || []).map(normalizeModel);
    const fallbackModel = normalizeModel({
        id: "fallback",
        model_name: "דגם תצוגה",
        category: "single-family",
        short_description_he: "אין כרגע נתונים זמינים",
        area_m2: 0,
        gallery_images: ["/media/no-house.jpg"]
    }, 0);

    const state = {
        allModels: allModels.length ? allModels : [fallbackModel],
        filteredModels: allModels.length ? allModels.slice() : [fallbackModel],
        activeHouseIndex: 0,
        activeImageIndex: 0,
        heroSwapTimer: null,
        filterState: {
            type: "all",
            bedrooms: 0,
            livingRooms: 0,
            bathrooms: 0,
            toilets: 0,
            parking: 0,
            kitchen: "any",
            stairs: "any",
            areaMin: 0,
            areaMax: 300
        }
    };

    const elements = {
        title: document.getElementById("currentHouseTitle"),
        heroStage: document.getElementById("heroStage"),
        heroImage: document.getElementById("heroImage"),
        heroPrevBtn: document.getElementById("heroPrevBtn"),
        heroNextBtn: document.getElementById("heroNextBtn"),
        heroDots: document.getElementById("heroDots"),
        heroThumbs: document.getElementById("heroThumbs"),
        dimensionsArea: document.getElementById("dimArea"),
        dimensionsLength: document.getElementById("dimLength"),
        dimensionsWidth: document.getElementById("dimWidth"),
        specIconsRow: document.getElementById("specIconsRow"),
        selectorTrack: document.getElementById("houseSelectorTrack"),
        requestQuoteBtn: document.getElementById("requestQuoteBtn"),
        openDetailsBtn: document.getElementById("openDetailsBtn"),
        openFloorplanBtn: document.getElementById("openFloorplanBtn"),
        floorplanQuickBtn: document.getElementById("floorplanQuickBtn"),
        leadModelName: document.getElementById("leadModelName"),
        modalRoot: document.getElementById("houseDetailsModal"),
        modalTitle: document.getElementById("detailsModalTitle"),
        modalImage: document.getElementById("detailsModalImage"),
        modalDescription: document.getElementById("detailsModalDescription"),
        modalSpecs: document.getElementById("detailsModalSpecs"),
        modalFeatures: document.getElementById("detailsModalFeatures"),
        modalCloseBtn: document.getElementById("detailsModalCloseBtn"),
        modalCtaBtn: document.getElementById("detailsModalCtaBtn"),
        quoteModalRoot: document.getElementById("quoteModal"),
        quoteModalCloseBtn: document.getElementById("quoteModalCloseBtn"),
        floorplanModalRoot: document.getElementById("floorplanModal"),
        floorplanModalImage: document.getElementById("floorplanModalImage"),
        floorplanModalCloseBtn: document.getElementById("floorplanModalCloseBtn"),
        filterTrigger: document.getElementById("filterDrawerTrigger"),
        filterOverlay: document.getElementById("filterOverlay"),
        filterPanel: document.getElementById("sideFilterPanel"),
        filterCloseBtn: document.getElementById("closeFilterPanelBtn"),
        filterType: document.getElementById("filterType"),
        filterBedrooms: document.getElementById("filterBedrooms"),
        filterLivingRoom: document.getElementById("filterLivingRoom"),
        filterBathrooms: document.getElementById("filterBathrooms"),
        filterToilets: document.getElementById("filterToilets"),
        filterParking: document.getElementById("filterParking"),
        filterKitchen: document.getElementById("filterKitchen"),
        filterStairs: document.getElementById("filterStairs"),
        filterAreaMin: document.getElementById("filterAreaMin"),
        filterAreaMax: document.getElementById("filterAreaMax"),
        filterAreaMinOut: document.getElementById("filterAreaMinOut"),
        filterAreaMaxOut: document.getElementById("filterAreaMaxOut"),
        resetFiltersBtn: document.getElementById("resetFiltersBtn"),
        applyAndCloseFiltersBtn: document.getElementById("applyAndCloseFiltersBtn")
    };

    function getActiveHouse() {
        return state.filteredModels[state.activeHouseIndex] || null;
    }

    function setActiveHouseByIndex(index) {
        if (!state.filteredModels.length) return;
        const safeIndex = Math.max(0, Math.min(index, state.filteredModels.length - 1));
        state.activeHouseIndex = safeIndex;
        state.activeImageIndex = 0;
        renderAll();
    }

    function setActiveImageByIndex(index) {
        const house = getActiveHouse();
        if (!house) return;
        const count = house.galleryImages.length;
        if (!count) return;
        const safeIndex = Math.max(0, Math.min(index, count - 1));
        const currentIndex = state.activeImageIndex;
        if (safeIndex === currentIndex) {
            snapBackHeroImage();
            return;
        }
        const direction = safeIndex > currentIndex ? "next" : "prev";
        animateHeroToImage(safeIndex, direction);
    }

    function transitionHeroImage(nextSrc, nextAlt, enterDirection) {
        const img = elements.heroImage;
        if (!img) return;
        const hadSrc = Boolean(img.getAttribute("src"));
        if (!hadSrc) {
            img.src = nextSrc;
            img.alt = nextAlt;
            img.classList.remove("swipe-next", "swipe-prev", "snap-back", "dragging", "changing");
            img.style.transform = "";
            img.style.opacity = "";
            return;
        }
        if (state.heroSwapTimer) {
            clearTimeout(state.heroSwapTimer);
            state.heroSwapTimer = null;
        }
        img.classList.remove("swipe-next", "swipe-prev", "snap-back", "dragging");
        img.classList.add("changing");
        state.heroSwapTimer = window.setTimeout(() => {
            img.src = nextSrc;
            img.alt = nextAlt;
            img.style.transform = "";
            img.style.opacity = "";
            img.classList.remove("changing");
            if (enterDirection) {
                const enterClass = enterDirection === "next" ? "swipe-prev" : "swipe-next";
                img.classList.add(enterClass);
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => img.classList.remove(enterClass));
                });
            }
            state.heroSwapTimer = null;
        }, 150);
    }

    function snapBackHeroImage() {
        const img = elements.heroImage;
        if (!img) return;
        img.classList.remove("swipe-next", "swipe-prev", "dragging");
        img.classList.add("snap-back");
        img.style.transform = "";
        img.style.opacity = "";
        window.setTimeout(() => img.classList.remove("snap-back"), 320);
    }

    function animateHeroToImage(targetIndex, direction) {
        const img = elements.heroImage;
        if (!img) return;
        img.classList.remove("snap-back", "dragging");
        img.classList.add(direction === "next" ? "swipe-next" : "swipe-prev");
        img.style.transform = "";
        img.style.opacity = "";
        window.setTimeout(() => {
            state.activeImageIndex = targetIndex;
            renderHeroGallery(direction);
        }, 150);
    }

    function HouseHeroGallery() {
        const gesture = {
            isDragging: false,
            startX: 0,
            currentX: 0,
            startTime: 0,
            pointerId: null,
            activeOffset: 0
        };

        function getHeroImages() {
            const house = getActiveHouse();
            return house && house.galleryImages.length ? house.galleryImages : ["/media/no-house.jpg"];
        }

        function applyHeroDragTransform(offsetPx) {
            const img = elements.heroImage;
            if (!img) return;
            img.classList.add("dragging");
            img.classList.remove("swipe-next", "swipe-prev", "snap-back", "changing");
            img.style.transform = `translateX(${offsetPx}px) scale(1.02)`;
            img.style.opacity = "1";
        }

        function startDrag(event) {
            if (event.target.closest("button")) return;
            gesture.isDragging = true;
            gesture.pointerId = event.pointerId;
            gesture.startX = event.clientX;
            gesture.currentX = event.clientX;
            gesture.startTime = performance.now();
            gesture.activeOffset = 0;
            elements.heroStage.classList.add("dragging");
            document.body.classList.add("no-select-drag");
            try {
                elements.heroStage.setPointerCapture(event.pointerId);
            } catch (err) {
                // Ignore if browser declines pointer capture.
            }
        }

        function moveDrag(event) {
            if (!gesture.isDragging) return;
            if (gesture.pointerId !== null && event.pointerId !== gesture.pointerId) return;
            const images = getHeroImages();
            const isAtFirst = state.activeImageIndex === 0;
            const isAtLast = state.activeImageIndex === images.length - 1;
            const rawDelta = event.clientX - gesture.startX;
            const pullingBeyondStart = isAtFirst && rawDelta > 0;
            const pullingBeyondEnd = isAtLast && rawDelta < 0;
            const resistance = (pullingBeyondStart || pullingBeyondEnd) ? 0.25 : 1;
            const offset = rawDelta * resistance;
            gesture.currentX = event.clientX;
            gesture.activeOffset = offset;
            applyHeroDragTransform(offset);
            event.preventDefault();
        }

        function endDrag(event) {
            if (!gesture.isDragging) return;
            if (gesture.pointerId !== null && event.pointerId !== gesture.pointerId) return;

            const elapsed = Math.max(1, performance.now() - gesture.startTime);
            const offset = gesture.activeOffset;
            const absOffset = Math.abs(offset);
            const velocity = absOffset / elapsed;
            const crossedThreshold = absOffset >= 50 || velocity >= 0.55;
            const direction = offset < 0 ? "next" : "prev";
            const images = getHeroImages();
            const targetIndex = direction === "next"
                ? state.activeImageIndex + 1
                : state.activeImageIndex - 1;
            const hasTarget = targetIndex >= 0 && targetIndex < images.length;

            elements.heroStage.classList.remove("dragging");
            document.body.classList.remove("no-select-drag");
            gesture.isDragging = false;
            gesture.pointerId = null;
            gesture.activeOffset = 0;
            try {
                if (event && typeof event.pointerId === "number") {
                    elements.heroStage.releasePointerCapture(event.pointerId);
                }
            } catch (err) {
                // Ignore if capture already released.
            }

            if (crossedThreshold && hasTarget) {
                animateHeroToImage(targetIndex, direction);
                return;
            }
            snapBackHeroImage();
        }

        function bind() {
            elements.heroPrevBtn.addEventListener("click", () => setActiveImageByIndex(state.activeImageIndex - 1));
            elements.heroNextBtn.addEventListener("click", () => setActiveImageByIndex(state.activeImageIndex + 1));
            elements.heroStage.addEventListener("pointerdown", startDrag);
            elements.heroStage.addEventListener("pointermove", moveDrag);
            elements.heroStage.addEventListener("pointerup", endDrag);
            elements.heroStage.addEventListener("pointercancel", endDrag);
        }

        bind();
    }

    function renderHeroGallery(enterDirection = null) {
        const house = getActiveHouse();
        if (!house) return;
        const images = house.galleryImages.length ? house.galleryImages : ["/media/no-house.jpg"];
        if (state.activeImageIndex > images.length - 1) state.activeImageIndex = 0;
        const currentImage = images[state.activeImageIndex];

        transitionHeroImage(currentImage, house.title, enterDirection);

        elements.heroDots.innerHTML = images.map((_, idx) => (
            `<button type="button" class="${idx === state.activeImageIndex ? "active" : ""}" data-dot-index="${idx}" aria-label="נקודה ${idx + 1}"></button>`
        )).join("");
        elements.heroDots.querySelectorAll("button").forEach((btn) => {
            btn.addEventListener("click", () => setActiveImageByIndex(Number(btn.dataset.dotIndex)));
        });

        elements.heroThumbs.innerHTML = images.map((img, idx) => (
            `<button type="button" class="thumbnail ${idx === state.activeImageIndex ? "active" : ""}" data-thumb-index="${idx}">
                <img src="${img}" alt="תצוגה ${idx + 1}">
            </button>`
        )).join("");
        elements.heroThumbs.querySelectorAll("button").forEach((btn) => {
            btn.addEventListener("click", () => setActiveImageByIndex(Number(btn.dataset.thumbIndex)));
        });
        const activeThumb = elements.heroThumbs.querySelector(".thumbnail.active");
        if (activeThumb) {
            activeThumb.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
        }
    }

    function HouseDimensionsCard() {}

    function renderDimensionsCard() {
        const house = getActiveHouse();
        if (!house) return;
        const area = house.dimensions.area;
        const length = house.dimensions.length;
        const width = house.dimensions.width;

        elements.dimensionsArea.textContent = area !== null ? `שטח בנוי: ${area} מ"ר` : "שטח בנוי: --";
        elements.dimensionsLength.textContent = length !== null ? `אורך: ${length} מ'` : "אורך: --";
        elements.dimensionsWidth.textContent = width !== null ? `רוחב: ${width} מ'` : "רוחב: --";
    }

    function HouseSpecsIcons() {}

    function renderSpecsIcons() {
        const house = getActiveHouse();
        if (!house) return;
        const rows = [
            { key: "toilets", label: "שירותים", value: house.specs.toilets },
            { key: "bathrooms", label: "חדרי רחצה", value: house.specs.bathrooms },
            { key: "bedrooms", label: "חדרי שינה", value: house.specs.bedrooms },
            { key: "kitchens", label: "מטבח", value: house.specs.kitchens },
            { key: "livingRooms", label: "חדר מגורים", value: house.specs.livingRooms },
            { key: "parking", label: "חניה", value: house.specs.parking },
            { key: "stairs", label: "מדרגות", value: house.specs.stairs }
        ].filter((item) => item.value !== null && item.value !== undefined);

        elements.specIconsRow.innerHTML = rows.map((item) => `
            <article class="spec-icon-item" data-spec="${item.key}">
                <img class="icon" src="${iconMap[item.key] || ""}" alt="${item.label}">
                <span class="value">${item.value}</span>
                <span class="label">${item.label}</span>
            </article>
        `).join("");
    }

    function HouseSelectorBar() {}

    function renderSelectorBar() {
        elements.selectorTrack.innerHTML = state.filteredModels.map((house, idx) => `
            <button type="button" class="${idx === state.activeHouseIndex ? "active" : ""}" data-house-index="${idx}">
                <img src="${house.heroImage}" alt="${house.title}">
                <span class="house-meta">
                    <strong>${house.title}</strong>
                    <span>שטח בנוי ${house.dimensions.area !== null ? house.dimensions.area : "--"} מ"ר</span>
                </span>
            </button>
        `).join("");

        elements.selectorTrack.querySelectorAll("button").forEach((btn) => {
            btn.addEventListener("click", () => setActiveHouseByIndex(Number(btn.dataset.houseIndex)));
        });

        bindSelectorDrag();
    }

    function bindSelectorDrag() {
        const track = elements.selectorTrack;
        if (track.dataset.dragBound === "true") return;
        track.dataset.dragBound = "true";
        let isPointerDown = false;
        let hasDragged = false;
        let startX = 0;
        let startScrollLeft = 0;

        track.addEventListener("pointerdown", (event) => {
            if (event.pointerType === "mouse" && event.button !== 0) return;
            isPointerDown = true;
            hasDragged = false;
            startX = event.clientX;
            startScrollLeft = track.scrollLeft;
            track.classList.add("dragging");
        });

        track.addEventListener("pointermove", (event) => {
            if (!isPointerDown) return;
            const delta = event.clientX - startX;
            if (Math.abs(delta) > 6) hasDragged = true;
            track.scrollLeft = startScrollLeft - delta;
        });

        function stopDragging(event) {
            if (!isPointerDown) return;
            isPointerDown = false;
            track.classList.remove("dragging");
            if (!hasDragged && event) {
                const targetButton = event.target.closest("button[data-house-index]");
                if (targetButton) {
                    setActiveHouseByIndex(Number(targetButton.dataset.houseIndex));
                }
            }
        }

        track.addEventListener("pointerup", stopDragging);
        track.addEventListener("pointercancel", stopDragging);
        track.addEventListener("pointerleave", stopDragging);
    }

    function HouseDetailsModal() {
        function close() {
            elements.modalRoot.setAttribute("hidden", "");
            document.body.style.overflow = "";
        }
        function open(targetHouse, preferredImage) {
            const house = targetHouse || getActiveHouse();
            if (!house) return;
            const specEntries = [
                ["שטח", house.dimensions.area !== null ? `${house.dimensions.area} מ"ר` : null],
                ["אורך", house.dimensions.length !== null ? `${house.dimensions.length} מ'` : null],
                ["רוחב", house.dimensions.width !== null ? `${house.dimensions.width} מ'` : null],
                ["חדרי שינה", house.specs.bedrooms],
                ["חדרי רחצה", house.specs.bathrooms],
                ["שירותים", house.specs.toilets],
                ["חניה", house.specs.parking],
                ["מטבח", house.specs.kitchens],
                ["מדרגות", house.specs.stairs]
            ].filter((row) => row[1] !== null && row[1] !== undefined && row[1] !== "");

            elements.modalTitle.textContent = house.title;
            elements.modalImage.src = preferredImage || house.floorplanImage || house.heroImage;
            elements.modalImage.alt = house.title;
            elements.modalDescription.textContent = house.description || house.subtitle || "";
            elements.modalSpecs.innerHTML = specEntries.map((row) => `<div>${row[0]}: ${row[1]}</div>`).join("");
            elements.modalFeatures.innerHTML = (house.features || []).slice(0, 12).map((item) => `<span>${item}</span>`).join("");
            elements.modalRoot.removeAttribute("hidden");
            document.body.style.overflow = "hidden";
        }

        elements.modalCloseBtn.addEventListener("click", close);
        elements.modalRoot.addEventListener("click", (event) => {
            if (event.target.hasAttribute("data-close-details")) close();
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && !elements.modalRoot.hasAttribute("hidden")) close();
        });

        return { open, close };
    }

    function QuoteModal() {
        function close() {
            elements.quoteModalRoot.setAttribute("hidden", "");
            document.body.style.overflow = "";
        }
        function open(targetHouse) {
            const house = targetHouse || getActiveHouse();
            if (house) elements.leadModelName.value = house.title;
            elements.quoteModalRoot.removeAttribute("hidden");
            document.body.style.overflow = "hidden";
        }

        elements.quoteModalCloseBtn.addEventListener("click", close);
        elements.quoteModalRoot.addEventListener("click", (event) => {
            if (event.target.hasAttribute("data-close-quote")) close();
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && !elements.quoteModalRoot.hasAttribute("hidden")) close();
        });

        return { open, close };
    }

    function FloorplanModal() {
        function close() {
            elements.floorplanModalRoot.setAttribute("hidden", "");
            document.body.style.overflow = "";
        }
        function open(targetHouse) {
            const house = targetHouse || getActiveHouse();
            if (!house) return;
            elements.floorplanModalImage.src = house.floorplanImage || house.heroImage;
            elements.floorplanModalImage.alt = `שרטוט הבית - ${house.title}`;
            elements.floorplanModalRoot.removeAttribute("hidden");
            document.body.style.overflow = "hidden";
        }

        elements.floorplanModalCloseBtn.addEventListener("click", close);
        elements.floorplanModalRoot.addEventListener("click", (event) => {
            if (event.target.hasAttribute("data-close-floorplan")) close();
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && !elements.floorplanModalRoot.hasAttribute("hidden")) close();
        });

        return { open, close };
    }

    function HouseActions(modalApi, quoteModalApi, floorplanModalApi) {
        function openQuoteModal() {
            const house = getActiveHouse();
            if (house) elements.leadModelName.value = house.title;
            quoteModalApi.open(house);
        }

        elements.requestQuoteBtn.addEventListener("click", openQuoteModal);
        elements.modalCtaBtn.addEventListener("click", () => {
            modalApi.close();
            openQuoteModal();
        });
        elements.openDetailsBtn.addEventListener("click", () => modalApi.open(getActiveHouse()));
        elements.openFloorplanBtn.addEventListener("click", () => {
            const house = getActiveHouse();
            if (!house) return;
            floorplanModalApi.open(house);
        });
        elements.floorplanQuickBtn.addEventListener("click", () => {
            const house = getActiveHouse();
            if (!house) return;
            floorplanModalApi.open(house);
        });
    }

    function buildNumericOptions(maxValue) {
        const max = Math.max(0, Number(maxValue || 0));
        const opts = [`<option value="0">ללא הגבלה</option>`];
        for (let i = 1; i <= max; i += 1) {
            opts.push(`<option value="${i}">לפחות ${i}</option>`);
        }
        return opts.join("");
    }

    function updateRangeOutputs() {
        elements.filterAreaMinOut.textContent = elements.filterAreaMin.value;
        elements.filterAreaMaxOut.textContent = elements.filterAreaMax.value;
    }

    function FilterControls() {
        const modelValues = state.allModels.map((m) => m.specs);
        const areaValues = state.allModels.map((m) => m.dimensions.area || 0);
        const maxArea = Math.max(80, ...areaValues, 0);
        const sliderMax = Math.ceil(maxArea / 10) * 10;

        const typeOptions = ['<option value="all">הכל</option>'];
        const typeMap = new Map();
        state.allModels.forEach((m) => {
            const key = m.typeKey || "single-family";
            const label = m.typeLabel || "בתים";
            if (!typeMap.has(key)) typeMap.set(key, label);
        });
        typeMap.forEach((label, key) => {
            typeOptions.push(`<option value="${key}">${label}</option>`);
        });
        elements.filterType.innerHTML = typeOptions.join("");

        const maxBedrooms = Math.max(...modelValues.map((v) => v.bedrooms || 0), 0);
        const maxLiving = Math.max(...modelValues.map((v) => v.livingRooms || 0), 0);
        const maxBathrooms = Math.max(...modelValues.map((v) => v.bathrooms || 0), 0);
        const maxToilets = Math.max(...modelValues.map((v) => v.toilets || 0), 0);
        const maxParking = Math.max(...modelValues.map((v) => v.parking || 0), 0);

        elements.filterBedrooms.innerHTML = buildNumericOptions(maxBedrooms);
        elements.filterLivingRoom.innerHTML = buildNumericOptions(maxLiving);
        elements.filterBathrooms.innerHTML = buildNumericOptions(maxBathrooms);
        elements.filterToilets.innerHTML = buildNumericOptions(maxToilets);
        elements.filterParking.innerHTML = buildNumericOptions(maxParking);

        elements.filterKitchen.innerHTML = `
            <option value="any">כל האפשרויות</option>
            <option value="yes">עם מטבח</option>
            <option value="no">ללא מטבח</option>
        `;
        elements.filterStairs.innerHTML = `
            <option value="any">כל האפשרויות</option>
            <option value="yes">עם מדרגות</option>
            <option value="no">ללא מדרגות</option>
        `;

        elements.filterAreaMin.max = String(sliderMax);
        elements.filterAreaMax.max = String(sliderMax);
        elements.filterAreaMin.value = "0";
        elements.filterAreaMax.value = String(sliderMax);
        updateRangeOutputs();
    }

    function getFilterStateFromControls() {
        const min = Number(elements.filterAreaMin.value || 0);
        const max = Number(elements.filterAreaMax.value || 0);
        return {
            type: elements.filterType.value || "all",
            bedrooms: Number(elements.filterBedrooms.value || 0),
            livingRooms: Number(elements.filterLivingRoom.value || 0),
            bathrooms: Number(elements.filterBathrooms.value || 0),
            toilets: Number(elements.filterToilets.value || 0),
            parking: Number(elements.filterParking.value || 0),
            kitchen: elements.filterKitchen.value || "any",
            stairs: elements.filterStairs.value || "any",
            areaMin: Math.min(min, max),
            areaMax: Math.max(min, max)
        };
    }

    function applyFilters() {
        state.filterState = getFilterStateFromControls();
        const f = state.filterState;
        state.filteredModels = state.allModels.filter((house) => {
            if (f.type !== "all" && house.typeKey !== f.type) return false;
            if (f.bedrooms > 0 && (house.specs.bedrooms || 0) < f.bedrooms) return false;
            if (f.livingRooms > 0 && (house.specs.livingRooms || 0) < f.livingRooms) return false;
            if (f.bathrooms > 0 && (house.specs.bathrooms || 0) < f.bathrooms) return false;
            if (f.toilets > 0 && (house.specs.toilets || 0) < f.toilets) return false;
            if (f.parking > 0 && (house.specs.parking || 0) < f.parking) return false;
            if (f.kitchen === "yes" && (house.specs.kitchens || 0) <= 0) return false;
            if (f.kitchen === "no" && (house.specs.kitchens || 0) > 0) return false;
            if (f.stairs === "yes" && (house.specs.stairs || 0) <= 0) return false;
            if (f.stairs === "no" && (house.specs.stairs || 0) > 0) return false;
            const area = house.dimensions.area || 0;
            if (area < f.areaMin || area > f.areaMax) return false;
            return true;
        });

        if (!state.filteredModels.length) {
            state.activeHouseIndex = 0;
            state.activeImageIndex = 0;
            renderEmptyState();
            return;
        }
        state.activeHouseIndex = Math.min(state.activeHouseIndex, state.filteredModels.length - 1);
        state.activeImageIndex = 0;
        renderAll();
    }

    function resetFilters() {
        elements.filterType.value = "all";
        elements.filterBedrooms.value = "0";
        elements.filterLivingRoom.value = "0";
        elements.filterBathrooms.value = "0";
        elements.filterToilets.value = "0";
        elements.filterParking.value = "0";
        elements.filterKitchen.value = "any";
        elements.filterStairs.value = "any";
        elements.filterAreaMin.value = "0";
        elements.filterAreaMax.value = elements.filterAreaMax.max;
        updateRangeOutputs();
        applyFilters();
    }

    function SideFilterPanel() {
        function open() {
            elements.filterOverlay.removeAttribute("hidden");
            elements.filterPanel.classList.add("open");
            elements.filterPanel.setAttribute("aria-hidden", "false");
            elements.filterTrigger.setAttribute("aria-expanded", "true");
        }
        function close() {
            elements.filterOverlay.setAttribute("hidden", "");
            elements.filterPanel.classList.remove("open");
            elements.filterPanel.setAttribute("aria-hidden", "true");
            elements.filterTrigger.setAttribute("aria-expanded", "false");
        }

        elements.filterTrigger.addEventListener("click", open);
        elements.filterCloseBtn.addEventListener("click", close);
        elements.filterOverlay.addEventListener("click", close);
        elements.applyAndCloseFiltersBtn.addEventListener("click", close);
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") close();
        });

        [
            elements.filterType, elements.filterBedrooms, elements.filterLivingRoom,
            elements.filterBathrooms, elements.filterToilets, elements.filterParking,
            elements.filterKitchen, elements.filterStairs
        ].forEach((control) => {
            control.addEventListener("change", applyFilters);
            control.addEventListener("input", applyFilters);
        });

        [elements.filterAreaMin, elements.filterAreaMax].forEach((rangeInput) => {
            rangeInput.addEventListener("input", () => {
                updateRangeOutputs();
                applyFilters();
            });
        });
        elements.resetFiltersBtn.addEventListener("click", resetFilters);

        return { open, close };
    }

    function renderEmptyState() {
        elements.title.textContent = "לא נמצאו תוצאות לסינון";
        elements.heroImage.src = "/media/no-house.jpg";
        elements.heroImage.alt = "אין תוצאות";
        elements.heroDots.innerHTML = "";
        elements.heroThumbs.innerHTML = "";
        elements.specIconsRow.innerHTML = "";
        elements.selectorTrack.innerHTML = `<div style="padding:14px;color:#7b7467;">אין כרגע דגמים התואמים את הסינון.</div>`;
        elements.leadModelName.value = "";
        elements.dimensionsArea.textContent = "שטח בנוי: --";
        elements.dimensionsLength.textContent = "אורך: --";
        elements.dimensionsWidth.textContent = "רוחב: --";
    }

    function renderAll() {
        const house = getActiveHouse();
        if (!house) {
            renderEmptyState();
            return;
        }
        elements.title.textContent = `${house.typeLabel} - ${house.title}`;
        elements.leadModelName.value = house.title;
        renderHeroGallery();
        renderDimensionsCard();
        renderSpecsIcons();
        renderSelectorBar();
    }

    function TabletCatalogPage() {
        HouseHeroGallery();
        HouseDimensionsCard();
        HouseSpecsIcons();
        HouseSelectorBar();
        FilterControls();
        const modalApi = HouseDetailsModal();
        const quoteModalApi = QuoteModal();
        const floorplanModalApi = FloorplanModal();
        HouseActions(modalApi, quoteModalApi, floorplanModalApi);
        SideFilterPanel();
        renderAll();
        if (document.body.dataset.openQuoteModal === "true") {
            quoteModalApi.open(getActiveHouse());
        }
    }

    TabletCatalogPage();
})();
