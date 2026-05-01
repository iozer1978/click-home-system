(function () {
    const form = document.getElementById("ssq-form");
    if (!form) return;

    const steps = Array.from(document.querySelectorAll(".step"));
    const totalSteps = steps.length;
    const prevBtn = document.getElementById("prev-btn");
    const nextBtn = document.getElementById("next-btn");
    const submitBtn = document.getElementById("submit-btn");
    const progressValue = document.getElementById("progress-value");
    const stepCounter = document.getElementById("step-counter");
    const answersJson = document.getElementById("answers-json");
    const languageInput = document.getElementById("language-input");
    const languageButtons = Array.from(document.querySelectorAll(".lang-btn"));
    const metaNode = document.getElementById("ssq-meta");
    const meta = metaNode ? JSON.parse(metaNode.textContent || "{}") : {};

    const STORAGE_KEY = "ssq_form_autosave_v1";
    let currentStep = 0;

    const i18n = {
        en: {
            title: "Supplier Qualification Form",
            subtitle: "Advanced construction systems and modular solutions supplier evaluation.",
            stepLabel: "Step",
            next: "Next",
            previous: "Previous",
            submit: "Submit Qualification",
        },
        zh: {
            title: "供应商资质评估表",
            subtitle: "先进建筑系统与模块化解决方案供应商评估。",
            stepLabel: "步骤",
            next: "下一步",
            previous: "上一步",
            submit: "提交评估",
        },
    };

    const stepTitlesZh = {
        1: "第1步：公司信息",
        2: "第2步：产品/建造体系",
        3: "第3步：标准与认证",
        4: "第4步：结构钢 / LGS 质量",
        5: "第5步：防火性能",
        6: "第6步：保温隔热",
        7: "第7步：隔音性能",
        8: "第8步：防潮防水防霉与耐候性",
        9: "第9步：完整墙体/屋面/地面构造",
        10: "第10步：生产与质量管理",
        11: "第11步：安装与工程支持",
        12: "第12步：物流与包装",
        13: "第13步：商务条款",
        14: "第14步：经验与案例",
        15: "第15步：最终声明",
    };
    const staticTextZh = {
        "Israeli references: SI 2262, SI 412, SI 413, SI 414, SI 921/SI 755, SI 1045, SI 1004.":
            "以色列参考标准：SI 2262、SI 412、SI 413、SI 414、SI 921/SI 755、SI 1045、SI 1004。",
        "Full wall section upload is mandatory and critical for qualification.":
            "完整墙体构造图为强制要求，缺失将被判定为关键风险。",
        "By submitting, you allow our technical team to review this data for qualification purposes.":
            "提交即表示您同意我方技术团队为资质审核目的审阅本次提交资料。",
        "We confirm all answers are accurate.":
            "我们确认所有填写信息准确无误。",
        "We understand that missing documents may disqualify us.":
            "我们理解缺失文件可能导致资格取消。",
        "We agree the documentation may be reviewed by engineers and consultants.":
            "我们同意资料可由工程师和顾问审核。",
        "We can provide additional documentation upon request.":
            "我们可按要求补充提供更多资料。",
    };

    function setLanguage(lang) {
        const bundle = i18n[lang] || i18n.en;
        languageInput.value = lang;
        languageButtons.forEach((btn) => {
            btn.classList.toggle("is-active", btn.dataset.lang === lang);
        });
        document.querySelectorAll("[data-i18n]").forEach((element) => {
            const key = element.dataset.i18n;
            if (bundle[key]) {
                element.textContent = bundle[key];
            }
        });
        nextBtn.textContent = bundle.next;
        prevBtn.textContent = bundle.previous;
        submitBtn.textContent = bundle.submit;
        translateDynamicFields(lang);
    }

    function translateDynamicFields(lang) {
        // Step titles
        steps.forEach((step, index) => {
            const titleNode = step.querySelector("h2");
            if (!titleNode) return;
            if (!titleNode.dataset.enText) {
                titleNode.dataset.enText = titleNode.textContent.trim();
            }
            const stepNo = index + 1;
            titleNode.textContent = lang === "zh" ? stepTitlesZh[stepNo] || titleNode.dataset.enText : titleNode.dataset.enText;
        });

        // Free static textual blocks
        document.querySelectorAll(".hint, .declarations label").forEach((node) => {
            const text = node.textContent.trim();
            if (!node.dataset.enText) {
                node.dataset.enText = text;
            }
            if (lang === "zh") {
                const mapped = staticTextZh[node.dataset.enText];
                if (mapped) {
                    node.textContent = mapped;
                }
            } else {
                node.textContent = node.dataset.enText;
            }
        });

        // Question labels by field name from backend map
        const questionLabels = meta.question_labels || {};
        Array.from(form.querySelectorAll("label")).forEach((labelNode) => {
            const span = labelNode.querySelector("span");
            const field = labelNode.querySelector("input, select, textarea");
            if (!span || !field || !field.name) return;
            if (!span.dataset.enText) {
                span.dataset.enText = span.textContent.trim();
            }
            const dict = questionLabels[field.name];
            if (!dict) {
                if (lang === "en") span.textContent = span.dataset.enText;
                return;
            }
            if (lang === "zh") {
                span.textContent = (dict.zh || dict.en || span.dataset.enText) + (span.dataset.enText.includes("*") ? " *" : "");
            } else {
                span.textContent = dict.en || span.dataset.enText;
                if (span.dataset.enText.includes("*") && !span.textContent.includes("*")) {
                    span.textContent += " *";
                }
            }
        });

        // Select option labels
        const choiceLabels = meta.choice_labels || {};
        Array.from(form.querySelectorAll("select")).forEach((select) => {
            if (!select.name) return;
            const mapping = choiceLabels[select.name] || {};
            Array.from(select.options).forEach((option) => {
                if (!option.dataset.enText) {
                    option.dataset.enText = option.textContent;
                }
                if (!option.value) {
                    option.textContent = lang === "zh" ? "请选择" : "Select";
                    return;
                }
                const optionMap = mapping[option.value];
                if (!optionMap) {
                    option.textContent = option.dataset.enText;
                    return;
                }
                option.textContent = lang === "zh" ? optionMap.zh || optionMap.en || option.dataset.enText : optionMap.en || option.dataset.enText;
            });
        });
    }

    function updateStepUI() {
        steps.forEach((step, index) => {
            step.classList.toggle("is-active", index === currentStep);
        });
        const progress = ((currentStep + 1) / totalSteps) * 100;
        progressValue.style.width = `${progress}%`;
        stepCounter.textContent = `${currentStep + 1} / ${totalSteps}`;
        prevBtn.disabled = currentStep === 0;
        const isLast = currentStep === totalSteps - 1;
        nextBtn.style.display = isLast ? "none" : "inline-flex";
        submitBtn.style.display = isLast ? "inline-flex" : "none";
    }

    function validateStep(stepIndex) {
        const step = steps[stepIndex];
        const requiredFields = Array.from(step.querySelectorAll("[required]"));
        for (const field of requiredFields) {
            if (field.type === "checkbox" && !field.checked) {
                field.focus();
                field.reportValidity();
                return false;
            }
            if (!field.value) {
                field.focus();
                field.reportValidity();
                return false;
            }
        }
        return true;
    }

    function serializeAnswers() {
        const payload = {};
        const elements = Array.from(form.querySelectorAll("input, select, textarea"));
        elements.forEach((el) => {
            if (!el.name || el.type === "file" || el.name === "answers_json") return;
            if (el.type === "checkbox") {
                payload[el.name] = !!el.checked;
            } else {
                payload[el.name] = el.value;
            }
        });
        payload._language = languageInput.value || "en";
        answersJson.value = JSON.stringify(payload);
    }

    function autosave() {
        const saveData = {};
        Array.from(form.querySelectorAll("input, select, textarea")).forEach((el) => {
            if (!el.name || el.type === "file" || el.name === "answers_json") return;
            if (el.type === "checkbox") {
                saveData[el.name] = el.checked;
            } else {
                saveData[el.name] = el.value;
            }
        });
        saveData.__step = currentStep;
        saveData.__lang = languageInput.value || "en";
        localStorage.setItem(STORAGE_KEY, JSON.stringify(saveData));
    }

    function restoreAutosave() {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (!saved) return;
        try {
            const data = JSON.parse(saved);
            Array.from(form.querySelectorAll("input, select, textarea")).forEach((el) => {
                if (!el.name || el.type === "file" || el.name === "answers_json") return;
                if (!(el.name in data)) return;
                if (el.type === "checkbox") {
                    el.checked = !!data[el.name];
                } else {
                    el.value = data[el.name];
                }
            });
            if (Number.isInteger(data.__step) && data.__step >= 0 && data.__step < totalSteps) {
                currentStep = data.__step;
            }
            setLanguage(data.__lang || "en");
        } catch (error) {
            localStorage.removeItem(STORAGE_KEY);
        }
    }

    prevBtn.addEventListener("click", function () {
        if (currentStep > 0) {
            currentStep -= 1;
            updateStepUI();
            autosave();
        }
    });

    nextBtn.addEventListener("click", function () {
        if (!validateStep(currentStep)) return;
        if (currentStep < totalSteps - 1) {
            currentStep += 1;
            updateStepUI();
            autosave();
        }
    });

    form.addEventListener("input", autosave);
    form.addEventListener("change", autosave);
    form.addEventListener("submit", function () {
        serializeAnswers();
        localStorage.removeItem(STORAGE_KEY);
    });

    languageButtons.forEach((button) => {
        button.addEventListener("click", function () {
            setLanguage(button.dataset.lang || "en");
            autosave();
        });
    });

    restoreAutosave();
    setLanguage(languageInput.value || "en");
    updateStepUI();
})();
