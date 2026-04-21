(function () {
    function bindGallerySwitches() {
        document.querySelectorAll(".showcase-card").forEach(function (card) {
            var mainImage = card.querySelector(".gallery-main");
            if (!mainImage) return;
            card.querySelectorAll(".thumb-switch").forEach(function (button) {
                button.addEventListener("click", function () {
                    var nextImage = button.getAttribute("data-image");
                    if (!nextImage) return;
                    mainImage.src = nextImage;
                });
            });
        });
    }

    function bindLeadButtons() {
        var leadInput = document.getElementById("lead_model_name");
        var leadSection = document.getElementById("lead-form");
        document.querySelectorAll(".card-lead-btn").forEach(function (button) {
            button.addEventListener("click", function () {
                if (leadInput) {
                    leadInput.value = button.getAttribute("data-model-name") || "";
                }
                if (leadSection) {
                    leadSection.scrollIntoView({ behavior: "smooth", block: "start" });
                    var field = document.getElementById("full_name");
                    if (field) field.focus();
                }
            });
        });
    }

    bindGallerySwitches();
    bindLeadButtons();
})();
