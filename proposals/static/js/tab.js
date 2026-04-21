(function () {
    const dataNode = document.getElementById("tabModelsData");
    const modal = document.getElementById("modelModal");
    const closeModalBtn = document.getElementById("closeModal");
    const backBtn = document.getElementById("modalBackButton");
    const leadBtn = document.getElementById("modalLeadButton");
    const cardTrack = document.getElementById("catalogTrack");

    if (!dataNode || !modal) {
        return;
    }

    let models = [];
    let activeModel = null;
    try {
        models = JSON.parse(dataNode.textContent || "[]");
    } catch (err) {
        models = [];
    }

    const byId = new Map(models.map((item) => [item.id, item]));
    const focusableSelector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    let lastFocusedElement = null;

    const elements = {
        title: document.getElementById("modalTitle"),
        category: document.getElementById("modalCategory"),
        description: document.getElementById("modalDescription"),
        mainImage: document.getElementById("modalMainImage"),
        thumbRow: document.getElementById("modalThumbRow"),
        specs: document.getElementById("modalSpecs"),
        floorplans: document.getElementById("modalFloorplans"),
    };

    function specTemplate(label, value) {
        return (
            '<dl class="spec-item">' +
            `<dt>${label}</dt>` +
            `<dd>${value ?? "לא צוין"}</dd>` +
            "</dl>"
        );
    }

    function buildThumb(imageUrl, imageAlt, onClick) {
        const button = document.createElement("button");
        button.type = "button";
        button.setAttribute("aria-label", imageAlt);
        const image = document.createElement("img");
        image.src = imageUrl;
        image.alt = imageAlt;
        image.loading = "lazy";
        image.decoding = "async";
        button.appendChild(image);
        button.addEventListener("click", onClick);
        return button;
    }

    function openModal(modelId) {
        const model = byId.get(modelId);
        if (!model) return;
        activeModel = model;

        lastFocusedElement = document.activeElement;
        elements.title.textContent = model.model_name;
        elements.category.textContent = model.category_label_he;
        elements.description.textContent = model.full_description_he;
        elements.mainImage.src = model.main_image;
        elements.mainImage.alt = `תמונה של דגם ${model.model_name}`;

        elements.thumbRow.innerHTML = "";
        const images = Array.isArray(model.gallery_images) && model.gallery_images.length
            ? model.gallery_images
            : [model.main_image];
        images.forEach((url, idx) => {
            const thumb = buildThumb(url, `תמונה ${idx + 1} עבור ${model.model_name}`, function () {
                elements.mainImage.src = url;
            });
            elements.thumbRow.appendChild(thumb);
        });

        elements.specs.innerHTML = [
            specTemplate("חדרי שינה", model.bedrooms),
            specTemplate("חדרי רחצה", model.bathrooms),
            specTemplate("קומות", model.floors),
            specTemplate("שטח", `${model.area_m2 || "-"} מ"ר`),
            specTemplate("אורך", model.length_m ? `${model.length_m} מ'` : "לא צוין"),
            specTemplate("רוחב", model.width_m ? `${model.width_m} מ'` : "לא צוין"),
            specTemplate("חניה", model.garages || 0),
            specTemplate("סגנון", (model.style_tags || []).join(", ") || "לא צוין"),
        ].join("");

        elements.floorplans.innerHTML = "";
        if (Array.isArray(model.floorplan_images) && model.floorplan_images.length) {
            model.floorplan_images.forEach((url, idx) => {
                const image = document.createElement("img");
                image.src = url;
                image.alt = `תכנית ${idx + 1} עבור ${model.model_name}`;
                image.loading = "lazy";
                image.decoding = "async";
                elements.floorplans.appendChild(image);
            });
        }

        modal.hidden = false;
        document.body.style.overflow = "hidden";
        closeModalBtn.focus();
    }

    function closeModal() {
        modal.hidden = true;
        document.body.style.overflow = "";
        if (lastFocusedElement && typeof lastFocusedElement.focus === "function") {
            lastFocusedElement.focus();
        }
    }

    function trapFocus(event) {
        if (event.key !== "Tab" || modal.hidden) return;
        const focusables = Array.from(modal.querySelectorAll(focusableSelector)).filter((el) => !el.disabled);
        if (!focusables.length) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    }

    document.querySelectorAll(".details-trigger").forEach((button) => {
        button.addEventListener("click", function () {
            openModal(button.dataset.modelId);
        });
    });

    document.querySelectorAll(".model-card").forEach((card) => {
        card.addEventListener("keydown", function (event) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openModal(card.dataset.modelId);
            }
        });
    });

    closeModalBtn.addEventListener("click", closeModal);
    backBtn.addEventListener("click", closeModal);
    modal.addEventListener("click", function (event) {
        if (event.target === modal) closeModal();
    });
    leadBtn.addEventListener("click", function () {
        const modelInput = document.getElementById("lead_model_name");
        if (modelInput) {
            modelInput.value = activeModel ? activeModel.model_name : "";
        }
        closeModal();
        const leadSection = document.getElementById("lead-form");
        if (leadSection) {
            leadSection.scrollIntoView({ behavior: "smooth", block: "start" });
            const firstInput = leadSection.querySelector("input, textarea, select");
            if (firstInput) firstInput.focus();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !modal.hidden) closeModal();
        trapFocus(event);
    });

    // Helps touch scroll feel smoother on cards
    if (cardTrack) {
        cardTrack.style.scrollBehavior = "smooth";
    }
})();
