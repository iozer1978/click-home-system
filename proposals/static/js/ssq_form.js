(function () {
    var form = document.getElementById("ssq-form");
    if (!form) return;

    var steps = Array.prototype.slice.call(document.querySelectorAll(".step"));
    var totalSteps = steps.length;
    var prevBtn = document.getElementById("prev-btn");
    var nextBtn = document.getElementById("next-btn");
    var submitBtn = document.getElementById("submit-btn");
    var progressValue = document.getElementById("progress-value");
    var stepCounter = document.getElementById("step-counter");
    var answersJson = document.getElementById("answers-json");
    var languageInput = document.getElementById("language-input");
    var languageButtons = Array.prototype.slice.call(document.querySelectorAll(".lang-btn"));
    var metaNode = document.getElementById("ssq-meta");
    var meta = {};
    var STORAGE_KEY = "ssq_form_autosave_v1";
    var currentStep = 0;

    if (metaNode) {
        try {
            meta = JSON.parse(metaNode.textContent || "{}");
        } catch (e) {
            meta = {};
        }
    }

    var i18n = {
        en: {
            title: "Supplier Qualification Form",
            subtitle: "Advanced construction systems and modular solutions supplier evaluation.",
            introTitle: "Why We Request This Form",
            introBody: "This supplier qualification form helps our engineering and sales teams evaluate technical compatibility, compliance, and market fit for your construction system. You are not required to complete every field, but the more information you provide, the faster and more accurately we can make qualification decisions and support future sales discussions with our clients regarding your products.",
            stepLabel: "Step",
            next: "Next",
            previous: "Previous",
            submit: "Submit Qualification"
        },
        zh: {
            title: "供应商资质评估表",
            subtitle: "先进建筑系统与模块化解决方案供应商评估。",
            introTitle: "为什么我们需要此表单",
            introBody: "此供应商资质表可帮助我们的工程与销售团队评估您体系的技术匹配性、合规性与市场适配度。您不必填写所有字段，但提供的信息越完整，我们就越能更快、更准确地完成准入评估，并在未来与客户沟通时更好地介绍您的产品。",
            stepLabel: "步骤",
            next: "下一步",
            previous: "上一步",
            submit: "提交评估"
        }
    };

    var stepTitlesZh = { 1: "第1步：公司信息", 2: "第2步：产品/建造体系", 3: "第3步：标准与认证", 4: "第4步：结构钢 / LGS 质量", 5: "第5步：防火性能", 6: "第6步：保温隔热", 7: "第7步：隔音性能", 8: "第8步：防潮防水防霉与耐候性", 9: "第9步：完整墙体/屋面/地面构造", 10: "第10步：生产与质量管理", 11: "第11步：安装与工程支持", 12: "第12步：物流与包装", 13: "第13步：商务条款", 14: "第14步：经验与案例", 15: "第15步：最终声明" };

    var staticTextZh = {
        "Israeli references: SI 2262, SI 412, SI 413, SI 414, SI 921/SI 755, SI 1045, SI 1004.": "以色列参考标准：SI 2262、SI 412、SI 413、SI 414、SI 921/SI 755、SI 1045、SI 1004。",
        "Full wall section upload is mandatory and critical for qualification.": "完整墙体构造图为强制要求，缺失将被判定为关键风险。",
        "By submitting, you allow our technical team to review this data for qualification purposes.": "提交即表示您同意我方技术团队为资质审核目的审阅本次提交资料。",
        "We confirm all answers are accurate.": "我们确认所有填写信息准确无误。",
        "We understand that missing documents may disqualify us.": "我们理解缺失文件可能导致资格取消。",
        "We agree the documentation may be reviewed by engineers and consultants.": "我们同意资料可由工程师和顾问审核。",
        "We can provide additional documentation upon request.": "我们可按要求补充提供更多资料。"
    };


    function each(list, callback) {
        for (var i = 0; i < list.length; i += 1) callback(list[i], i);
    }

    function setLanguage(lang) {
        lang = lang === "zh" ? "zh" : "en";
        var bundle = i18n[lang] || i18n.en;
        document.documentElement.lang = lang;
        document.documentElement.dir = "ltr";
        if (document.body) {
            document.body.classList.remove("lang-he");
        }
        languageInput.value = lang;
        each(languageButtons, function (btn) {
            if (btn.getAttribute("data-lang") === lang) btn.classList.add("is-active");
            else btn.classList.remove("is-active");
        });
        each(document.querySelectorAll("[data-i18n]"), function (element) {
            var key = element.getAttribute("data-i18n");
            if (bundle[key]) element.textContent = bundle[key];
        });
        nextBtn.textContent = bundle.next;
        prevBtn.textContent = bundle.previous;
        submitBtn.textContent = bundle.submit;
        try {
            translateDynamicFields(lang);
        } catch (err) {
            if (window.console && console.error) console.error("Language switch warning:", err);
        }
    }

    window.ssqSetLanguage = setLanguage;

    function translateDynamicFields(lang) {
        each(steps, function (step, index) {
            var titleNode = step.querySelector("h2");
            var stepNo;
            if (!titleNode) return;
            if (!titleNode.getAttribute("data-en-text")) {
                titleNode.setAttribute("data-en-text", titleNode.textContent.trim());
            }
            stepNo = index + 1;
            if (lang === "zh") titleNode.textContent = stepTitlesZh[stepNo] || titleNode.getAttribute("data-en-text");
            else titleNode.textContent = titleNode.getAttribute("data-en-text");
        });

        each(document.querySelectorAll(".hint, .declaration-text"), function (node) {
            var text = node.textContent.trim();
            var mapped;
            if (!node.getAttribute("data-en-text")) node.setAttribute("data-en-text", text);
            if (lang === "zh") {
                mapped = staticTextZh[node.getAttribute("data-en-text")];
                if (mapped) node.textContent = mapped;
            } else {
                node.textContent = node.getAttribute("data-en-text");
            }
        });

        var questionLabels = meta.question_labels || {};
        each(form.querySelectorAll("label"), function (labelNode) {
            var span = labelNode.querySelector("span");
            var field = labelNode.querySelector("input, select, textarea");
            var dict;
            var baseText;
            var translated;
            if (!span || !field || !field.name) return;
            if (!span.getAttribute("data-en-text")) span.setAttribute("data-en-text", span.textContent.trim());
            dict = questionLabels[field.name];
            baseText = span.getAttribute("data-en-text");
            if (!dict) {
                if (lang === "en") span.textContent = baseText;
                return;
            }
            if (lang === "zh") translated = dict.zh || dict.en || baseText;
            else translated = dict.en || baseText;
            if (baseText.indexOf("*") !== -1 && translated.indexOf("*") === -1) translated += " *";
            span.textContent = translated;
        });

        var choiceLabels = meta.choice_labels || {};
        each(form.querySelectorAll("select"), function (select) {
            var mapping;
            if (!select.name) return;
            mapping = choiceLabels[select.name] || {};
            each(select.options, function (option) {
                var optionMap;
                if (!option.getAttribute("data-en-text")) option.setAttribute("data-en-text", option.textContent);
                if (!option.value) {
                    option.textContent = lang === "zh" ? "请选择" : (lang === "he" ? "בחר" : "Select");
                    return;
                }
                optionMap = mapping[option.value];
                if (!optionMap) {
                    option.textContent = option.getAttribute("data-en-text");
                    return;
                }
                if (lang === "zh") option.textContent = optionMap.zh || optionMap.en || option.getAttribute("data-en-text");
                else option.textContent = optionMap.en || option.getAttribute("data-en-text");
            });
        });
    }

    function updateStepUI() {
        each(steps, function (step, index) {
            if (index === currentStep) step.classList.add("is-active");
            else step.classList.remove("is-active");
        });
        var progress = ((currentStep + 1) / totalSteps) * 100;
        progressValue.style.width = progress + "%";
        stepCounter.textContent = (currentStep + 1) + " / " + totalSteps;
        prevBtn.disabled = currentStep === 0;
        var isLast = currentStep === totalSteps - 1;
        nextBtn.style.display = isLast ? "none" : "inline-flex";
        submitBtn.style.display = isLast ? "inline-flex" : "none";
    }

    function validateStep(stepIndex) {
        var step = steps[stepIndex];
        var requiredFields = step.querySelectorAll("[required]");
        for (var i = 0; i < requiredFields.length; i += 1) {
            var field = requiredFields[i];
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
        var payload = {};
        each(form.querySelectorAll("input, select, textarea"), function (el) {
            if (!el.name || el.type === "file" || el.name === "answers_json") return;
            if (el.type === "checkbox") payload[el.name] = !!el.checked;
            else payload[el.name] = el.value;
        });
        payload._language = languageInput.value || "en";
        answersJson.value = JSON.stringify(payload);
    }

    function autosave() {
        var saveData = {};
        each(form.querySelectorAll("input, select, textarea"), function (el) {
            if (!el.name || el.type === "file" || el.name === "answers_json") return;
            if (el.type === "checkbox") saveData[el.name] = el.checked;
            else saveData[el.name] = el.value;
        });
        saveData.__step = currentStep;
        saveData.__lang = languageInput.value || "en";
        localStorage.setItem(STORAGE_KEY, JSON.stringify(saveData));
    }

    function restoreAutosave() {
        var saved = localStorage.getItem(STORAGE_KEY);
        var data;
        var stepInt;
        if (!saved) return;
        try {
            data = JSON.parse(saved);
            each(form.querySelectorAll("input, select, textarea"), function (el) {
                if (!el.name || el.type === "file" || el.name === "answers_json") return;
                if (typeof data[el.name] === "undefined") return;
                if (el.type === "checkbox") el.checked = !!data[el.name];
                else el.value = data[el.name];
            });
            stepInt = parseInt(data.__step, 10);
            if (!isNaN(stepInt) && stepInt >= 0 && stepInt < totalSteps) currentStep = stepInt;
            setLanguage(data.__lang || "en");
        } catch (e) {
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

    each(languageButtons, function (button) {
        button.addEventListener("click", function () {
            setLanguage(button.getAttribute("data-lang") || "en");
            autosave();
        });
    });

    restoreAutosave();
    setLanguage(languageInput.value || "en");
    updateStepUI();
})();
