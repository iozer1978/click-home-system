from __future__ import annotations

import csv
import io
import json
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives, send_mail
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie

from .forms import SSQAdminLoginForm, SupplierSubmissionStatusForm
from .models import SupplierSubmission
from .ssq_config import (
    CHOICE_VALUE_LABELS,
    MANDATORY_FILE_FIELDS,
    QUESTION_LABELS,
    SECTION_DEFINITIONS,
    STATUS_CHOICES,
    TOOLTIP_TERMS,
)
from .ssq_scoring import calculate_submission_score

SESSION_ADMIN_KEY = "ssq_admin_authenticated"
MAX_FILE_SIZE = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
    ".dwg",
    ".dxf",
}

UPLOAD_FIELD_NAMES = [
    "certificates_uploads",
    "steel_certificate_upload",
    "structural_calculation_example_upload",
    "fire_test_reports_upload",
    "thermal_report_upload",
    "acoustic_report_upload",
    "water_moisture_report_upload",
    "wall_section_upload",
    "roof_section_upload",
    "floor_section_upload",
    "project_photos_upload",
    "project_videos_upload",
]

SERVER_MESSAGES = {
    "unsupported_file_type": {
        "en": "Unsupported file type: {filename}",
        "zh": "不支持的文件类型：{filename}",
        "he": "סוג קובץ לא נתמך: {filename}",
    },
    "file_too_large": {
        "en": "File too large (max 20MB): {filename}",
        "zh": "文件过大（最大 20MB）：{filename}",
        "he": "הקובץ גדול מדי (מקסימום 20MB): {filename}",
    },
    "submission_saved_email_failed": {
        "en": "Submission saved, but admin email could not be sent.",
        "zh": "提交已保存，但管理员邮件发送失败。",
        "he": "הטופס נשמר, אך שליחת המייל למנהל נכשלה.",
    },
    "missing_mandatory_uploads": {
        "en": "Missing mandatory documents: {items}",
        "zh": "缺少必填文件：{items}",
        "he": "חסרים מסמכים חובה: {items}",
    },
}

MANDATORY_UPLOAD_LABELS = {
    "certificates_uploads": {"en": "Certificates", "zh": "认证证书", "he": "תעודות"},
    "steel_certificate_upload": {"en": "Steel certificate", "zh": "钢材证书", "he": "תעודת פלדה"},
    "structural_calculation_example_upload": {"en": "Structural calculation example", "zh": "结构计算示例", "he": "דוגמת חישוב קונסטרוקטיבי"},
    "fire_test_reports_upload": {"en": "Fire test reports", "zh": "防火测试报告", "he": "דוחות בדיקת אש"},
    "thermal_report_upload": {"en": "Thermal report", "zh": "热工性能报告", "he": "דוח תרמי"},
    "acoustic_report_upload": {"en": "Acoustic report", "zh": "隔音性能报告", "he": "דוח אקוסטי"},
    "water_moisture_report_upload": {"en": "Water/moisture report", "zh": "防水防潮报告", "he": "דוח מים/לחות"},
    "wall_section_upload": {"en": "Full wall section drawing", "zh": "完整墙体构造图", "he": "שרטוט חתך קיר מלא"},
}

HEBREW_QUESTION_LABELS = {
    "company_name": "שם החברה",
    "country": "מדינה",
    "city": "עיר",
    "website": "אתר אינטרנט",
    "contact_person": "איש קשר",
    "job_title": "תפקיד",
    "email": "אימייל",
    "phone_whatsapp": "טלפון / WhatsApp",
    "wechat_id": "מזהה WeChat",
    "years_in_business": "שנות פעילות",
    "employees_count": "מספר עובדים",
    "factory_address": "כתובת מפעל",
    "company_type": "סוג חברה",
    "main_products": "מוצרים עיקריים",
    "annual_capacity": "כושר ייצור שנתי",
    "export_markets": "שווקי יצוא",
    "main_supply_countries": "מדינות אספקה עיקריות",
    "israel_middle_east_experience": "ניסיון יצוא לישראל/מזרח תיכון",
    "product_type": "סוג מוצר",
    "complete_system_or_components": "מערכת מלאה או רכיבים בלבד",
    "architectural_drawings": "שרטוטים אדריכליים מלאים",
    "structural_drawings": "שרטוטים קונסטרוקטיביים",
    "shop_drawings": "שרטוטי ייצור",
    "adapt_israeli_requirements": "התאמה לדרישות מהנדס ישראלי",
    "building_size_range": "טווח גדלי מבנה",
    "floors_supported": "מספר קומות נתמך",
    "permanent_residential_use": "מתאים למגורים קבועים",
    "hot_climate_50": "מתאים לאקלים חם 45-50 מעלות",
    "coastal_suitability": "מתאים ללחות/קורוזיה ימית",
    "standards_compliance": "תקנים בינלאומיים",
    "iso_9001": "ISO 9001",
    "iso_14001": "ISO 14001",
    "ce_certificates": "תעודות CE",
    "third_party_lab_reports": "דוחות מעבדה צד ג'",
    "cert_scope": "היקף התעודות",
    "original_test_reports": "דוחות בדיקה מקוריים",
    "israeli_engineer_review": "ניתן לבדיקה על ידי מהנדס ישראלי",
    "israeli_standard_adaptation": "התאמה לתקנים ישראליים",
    "steel_type": "סוג פלדה",
    "steel_grade": "דרגת פלדה",
    "yield_strength_mpa": "חוזק Yield (MPa)",
    "profile_thickness_mm": "עובי פרופיל (מ\"מ)",
    "galvanization_level": "רמת גלוון",
    "profile_width": "רוחב פרופיל",
    "stud_spacing": "מרווח סטאדים",
    "openings_reinforcement": "חיזוק פתחים",
    "pre_punched_profiles": "פרופילים עם חורים מוכנים",
    "service_hole_spec": "מפרט חורי שירות",
    "screw_type_diameter": "סוג/קוטר ברגים",
    "anti_corrosion_protection": "הגנה מקורוזיה",
    "expected_design_life": "חיי תכנון צפויים",
    "wall_fire_rating_min": "דירוג אש לקיר (דקות)",
    "roof_fire_rating_min": "דירוג אש לגג",
    "floor_fire_rating_min": "דירוג אש לרצפה",
    "assembly_tested": "האם המכלול נבדק",
    "fire_test_standard": "תקן בדיקת אש",
    "fire_resistance_boards": "לוחות עמידות אש",
    "board_layers_count": "מספר שכבות לוחות",
    "non_combustible_materials": "חומרים בלתי דליקים",
    "toxic_smoke_tests": "בדיקות עשן רעיל",
    "wall_r_value": "R-value לקיר",
    "roof_r_value": "R-value לגג",
    "floor_r_value": "R-value לרצפה",
    "u_value": "U-value",
    "insulation_type": "סוג בידוד",
    "insulation_thickness": "עובי בידוד",
    "insulation_density": "צפיפות בידוד",
    "thermal_bridge_prevention": "מניעת גשרים תרמיים",
    "hot_climate_suitability": "התאמה לאקלים חם",
    "external_insulation_support": "תמיכה בבידוד חיצוני",
    "insulation_upgrade_support": "אפשרות שדרוג בידוד",
    "wall_stc_rating": "דירוג STC לקיר",
    "floor_acoustic_rating": "דירוג אקוסטי לרצפה",
    "roof_acoustic_performance": "ביצועים אקוסטיים לגג",
    "acoustic_test_report_available": "קיים דוח בדיקה אקוסטי",
    "internal_board_layers": "שכבות לוח פנימיות",
    "acoustic_insulation_type_density": "סוג/צפיפות בידוד אקוסטי",
    "exterior_board_weather_resistance": "עמידות לוחות חוץ למזג אוויר",
    "mold_resistant_materials": "עמידות לעובש",
    "wet_room_suitability": "התאמה לחדרים רטובים",
    "external_board_type": "סוג לוח חיצוני",
    "internal_board_type": "סוג לוח פנימי",
    "board_moisture_behavior": "התנהגות לוחות בלחות",
    "waterproof_membrane_included": "כולל ממברנת איטום",
    "vapor_barrier_included": "כולל מחסום אדים",
    "condensation_prevention_method": "שיטת מניעת עיבוי",
    "coastal_environment_suitability": "התאמה לסביבה ימית",
    "total_wall_thickness": "עובי קיר כולל",
    "wall_weight_per_m2": "משקל קיר למ\"ר",
    "external_cladding_type": "סוג חיפוי חוץ",
    "internal_board_type_assembly": "סוג לוח פנימי במכלול",
    "insulation_type_assembly": "סוג בידוד במכלול",
    "waterproof_layer": "שכבת איטום",
    "vapor_barrier_assembly": "מחסום אדים במכלול",
    "air_gap_layer": "שכבת אוויר/אוורור",
    "finishing_options": "אפשרויות גמר",
    "tile_stone_support": "תמיכה באריחים/אבן",
    "max_cladding_weight_per_m2": "משקל חיפוי מקסימלי למ\"ר",
    "factory_ownership": "בעלות על המפעל",
    "factory_size": "גודל מפעל",
    "monthly_production_capacity": "כושר ייצור חודשי",
    "qa_process": "תהליך בקרת איכות",
    "incoming_material_inspection": "בדיקת חומרים נכנסים",
    "in_process_inspection": "בדיקות במהלך הייצור",
    "final_inspection": "בדיקת איכות סופית",
    "third_party_inspection_available": "אפשרות בדיקת צד ג'",
    "production_photos_videos": "תמונות/סרטוני ייצור",
    "packing_list_before_shipment": "רשימת אריזה לפני משלוח",
    "component_labeling": "סימון רכיבים",
    "installation_manual_available": "חוברת התקנה זמינה",
    "spare_parts_list_available": "רשימת חלקי חילוף זמינה",
    "installation_drawings": "שרטוטי התקנה",
    "installation_manual": "מדריך התקנה",
    "online_training": "הדרכה אונליין",
    "site_supervisor": "אפשרות מפקח באתר",
    "local_team_install_after_training": "התקנת צוות מקומי לאחר הדרכה",
    "install_time_100_120sqm": "זמן התקנה ל-100-120 מ\"ר",
    "workers_required": "מספר עובדים נדרש",
    "required_tools_equipment": "כלים/ציוד נדרש",
    "foundation_requirements": "דרישות יסוד",
    "mep_coordination_support": "תמיכת תיאום מערכות",
    "future_extension_support": "תמיכה בהרחבות עתידיות",
    "production_lead_time": "זמן ייצור",
    "shipping_port_china": "נמל משלוח בסין",
    "packing_method": "שיטת אריזה",
    "shipping_anti_rust_protection": "הגנה נגד חלודה במשלוח",
    "shipping_moisture_protection": "הגנה מלחות במשלוח",
    "sqm_per_40hq": "מ\"ר למכולת 40HQ",
    "packing_optimization_per_project": "אופטימיזציית אריזה לפי פרויקט",
    "sequence_based_packing": "אריזה לפי סדר בנייה",
    "full_packing_list": "רשימת אריזה מלאה",
    "hs_codes_provided": "קודי HS מסופקים",
    "invoice_origin_certificate": "חשבונית ותעודת מקור",
    "price_per_sqm": "מחיר למ\"ר",
    "price_includes": "מה כלול במחיר",
    "price_excludes": "מה לא כלול במחיר",
    "moq": "MOQ",
    "payment_terms": "תנאי תשלום",
    "warranty_period": "תקופת אחריות",
    "warranty_coverage": "כיסוי אחריות",
    "incoterms": "Incoterms",
    "quotation_validity": "תוקף הצעת מחיר",
    "installation_cost_separate": "עלות התקנה בנפרד",
    "spare_parts_cost": "עלות חלקי חילוף",
    "sample_cost": "עלות דוגמית",
    "engineering_design_cost": "עלות הנדסה/תכנון",
    "mold_tooling_cost": "עלות תבניות/Tooling",
    "exclusive_distribution_support": "תמיכה בבלעדיות בישראל",
    "completed_projects_count": "מספר פרויקטים שהושלמו",
    "exported_countries": "מדינות יצוא",
    "residential_references": "רפרנסים למגורים",
    "hotel_public_references": "רפרנסים למלונאות/ציבורי",
    "customer_references": "המלצות לקוחות",
    "middle_east_hot_climate_projects": "פרויקטים במזרח התיכון/אקלים חם",
    "past_failures_and_resolution": "כשלים קודמים ופתרונות",
    "declaration_accuracy": "הצהרה: המידע מדויק",
    "declaration_missing_docs": "הצהרה: חוסר מסמכים עלול לפסול",
    "declaration_engineer_review": "הצהרה: מסכים לבדיקת מהנדסים",
    "declaration_more_docs": "הצהרה: ניתן לספק מסמכים נוספים",
}

HEBREW_CHOICE_LABELS = {
    "company_type": {
        "manufacturer": "יצרן",
        "trading_company": "חברת סחר",
        "both": "שניהם",
    },
    "product_type": {
        "lgs_cfs": "מערכת LGS / CFS",
        "modular_house": "בית מודולרי",
        "container_house": "בית קונטיינר",
        "hybrid_construction": "בנייה היברידית",
        "wall_panels": "פאנלים לקירות",
        "roofing_system": "מערכת גג",
        "insulation_system": "מערכת בידוד",
        "other": "אחר",
    },
    "incoterms": {
        "EXW": "EXW",
        "FOB": "FOB",
        "CIF": "CIF",
        "DDP": "DDP",
    },
}


def _admin_required(view_func):
    def _wrapped(request, *args, **kwargs):
        if not request.session.get(SESSION_ADMIN_KEY):
            return redirect("ssq_admin_login")
        return view_func(request, *args, **kwargs)

    return _wrapped


def _storage_root() -> Path:
    configured = getattr(settings, "SSQ_STORAGE_PATH", "") or os.environ.get("STORAGE_PATH", "")
    if configured:
        root = Path(configured)
    else:
        root = Path(settings.BASE_DIR) / "private_uploads" / "ssq"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_filename(name: str) -> str:
    base = Path(name).name.replace(" ", "_")
    return "".join(ch for ch in base if ch.isalnum() or ch in {"_", "-", "."})[:180]


def _normalized_language(value: str | None) -> str:
    text = str(value or "").lower()
    if text.startswith("zh"):
        return "zh"
    if text.startswith("he"):
        return "he"
    return "en"


def _message(key: str, language: str, **kwargs) -> str:
    bundle = SERVER_MESSAGES.get(key, {})
    template = bundle.get(language) or bundle.get("en") or key
    return template.format(**kwargs)


def _validate_file(uploaded_file, language: str) -> str | None:
    extension = Path(uploaded_file.name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        return _message("unsupported_file_type", language, filename=uploaded_file.name)
    if uploaded_file.size > MAX_FILE_SIZE:
        return _message("file_too_large", language, filename=uploaded_file.name)
    return None


def _save_uploads(request, submission_id: uuid.UUID, language: str) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    file_map: dict[str, list[dict[str, Any]]] = {}
    errors: list[str] = []
    root = _storage_root()
    submission_root = root / str(submission_id)
    submission_root.mkdir(parents=True, exist_ok=True)

    for field_name in UPLOAD_FIELD_NAMES:
        items = request.FILES.getlist(field_name)
        stored_items: list[dict[str, Any]] = []
        for item in items:
            err = _validate_file(item, language)
            if err:
                errors.append(err)
                continue
            safe_name = _safe_filename(item.name)
            saved_name = f"{uuid.uuid4().hex}_{safe_name}"
            relative_path = Path(str(submission_id)) / field_name / saved_name
            target_path = root / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with target_path.open("wb+") as destination:
                for chunk in item.chunks():
                    destination.write(chunk)
            stored_items.append(
                {
                    "name": item.name,
                    "saved_name": saved_name,
                    "relative_path": str(relative_path).replace("\\", "/"),
                    "size": item.size,
                    "content_type": item.content_type,
                    "admin_url": reverse("ssq_admin_file", kwargs={"submission_id": submission_id, "file_key": field_name, "index": len(stored_items)}),
                }
            )
        if stored_items:
            file_map[field_name] = stored_items

    return file_map, errors


def _extract_answers(request) -> dict[str, Any]:
    payload = request.POST.get("answers_json", "").strip()
    if payload:
        try:
            data = json.loads(payload)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    # fallback if JS payload did not exist
    return {
        key: value
        for key, value in request.POST.items()
        if key not in {"csrfmiddlewaretoken", "answers_json"}
    }


def _mandatory_check(files_map: dict[str, list[dict[str, Any]]]) -> list[str]:
    missing = []
    for field in MANDATORY_FILE_FIELDS:
        if not files_map.get(field):
            missing.append(field)
    return missing


def _build_email_context(submission: SupplierSubmission) -> dict[str, Any]:
    display_answers = _localized_answers(submission)
    return {
        "submission": submission,
        "answers": submission.answers or {},
        "display_answers": display_answers,
        "files": submission.files or {},
        "score_breakdown": submission.scoreBreakdown or {},
        "critical_flags": submission.criticalFlags or [],
    }


def _question_label(field_name: str, language: str) -> str:
    entry = QUESTION_LABELS.get(field_name, {})
    if language == "zh":
        return entry.get("zh") or entry.get("en") or field_name.replace("_", " ").title()
    if language == "he":
        return HEBREW_QUESTION_LABELS.get(field_name) or entry.get("en") or field_name.replace("_", " ").title()
    return entry.get("en") or field_name.replace("_", " ").title()


def _choice_label(field_name: str, value: Any, language: str) -> str:
    if isinstance(value, list):
        mapped_values = [_choice_label(field_name, item, language) for item in value]
        return ", ".join([item for item in mapped_values if str(item).strip()])
    value_str = str(value)
    choices = CHOICE_VALUE_LABELS.get(field_name, {})
    choice = choices.get(value_str)
    if not choice:
        if language == "he":
            return HEBREW_CHOICE_LABELS.get(field_name, {}).get(value_str, value_str)
        return value_str
    if language == "zh":
        return choice.get("zh") or choice.get("en") or value_str
    if language == "he":
        return HEBREW_CHOICE_LABELS.get(field_name, {}).get(value_str, choice.get("en") or value_str)
    return choice.get("en") or value_str


def _localized_answers(submission: SupplierSubmission) -> list[dict[str, str]]:
    language = "zh" if (submission.language or "").lower().startswith("zh") else "en"
    answers = submission.answers or {}
    rows: list[dict[str, str]] = []
    for key, value in answers.items():
        if key.startswith("_"):
            continue
        if isinstance(value, bool):
            value_text = "Yes" if value else "No"
            if language == "zh":
                value_text = "是" if value else "否"
            elif language == "he":
                value_text = "כן" if value else "לא"
        else:
            value_text = _choice_label(key, value, language)
        rows.append({"key": key, "question": _question_label(key, language), "answer": value_text})
    return rows


def _send_admin_summary_email(submission: SupplierSubmission):
    context = _build_email_context(submission)
    html_body = render_to_string("emails/ssq_admin_summary.html", context)
    text_body = (
        f"Supplier submission received\n\n"
        f"Company: {submission.companyName}\n"
        f"Country: {submission.country}\n"
        f"Contact: {submission.contactName}\n"
        f"Email: {submission.email}\n"
        f"Score: {submission.score}\n"
        f"Risk: {submission.riskLevel}\n"
        f"Admin link: {reverse('ssq_admin_submission_detail', kwargs={'submission_id': submission.id})}\n"
    )
    recipient = "itzik@click-home.co.il"
    email = EmailMultiAlternatives(
        subject=f"New Supplier Qualification Submission - {submission.companyName}",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=False)


def _send_supplier_confirmation_email(submission: SupplierSubmission):
    language = _normalized_language(submission.language)
    context = {
        "submission": submission,
        "greeting": "Dear" if language == "en" else ("尊敬的" if language == "zh" else "שלום"),
        "message_line": (
            "Thank you for submitting your supplier qualification form. Our technical team will review the information and contact you if further details are required."
            if language == "en"
            else (
                "感谢您提交供应商资质评估表。我们的技术团队将审核您提供的信息，如需补充资料将与您联系。"
                if language == "zh"
                else "תודה על מילוי טופס סיווג הספקים. הצוות הטכני שלנו יבחן את הנתונים וניצור קשר אם יידרש מידע נוסף."
            )
        ),
        "closing": (
            "Best regards,\nClick Home Team"
            if language == "en"
            else ("此致敬礼，\nClick Home 团队" if language == "zh" else "בברכה,\nצוות Click Home")
        ),
    }
    html_body = render_to_string(
        "emails/ssq_supplier_confirmation.html",
        context,
    )
    body = (
        "Thank you for submitting your supplier qualification form. "
        "Our technical team will review the information and contact you if further details are required."
        if language == "en"
        else (
            "感谢您提交供应商资质评估表。我们的技术团队将审核信息，如需补充资料将与您联系。"
            if language == "zh"
            else "תודה על מילוי טופס סיווג ספקים. הצוות הטכני שלנו יעבור על המידע ויצור קשר במקרה הצורך."
        )
    )
    send_mail(
        "Supplier Qualification Submission Received"
        if language == "en"
        else ("供应商资质评估表提交确认" if language == "zh" else "אישור קבלת טופס סיווג ספק"),
        body,
        settings.DEFAULT_FROM_EMAIL,
        [submission.email],
        html_message=html_body,
        fail_silently=True,
    )


def _summary_payload() -> dict[str, Any]:
    question_labels = {}
    for key, entry in QUESTION_LABELS.items():
        question_labels[key] = {
            "en": entry.get("en", key),
            "zh": entry.get("zh", entry.get("en", key)),
            "he": HEBREW_QUESTION_LABELS.get(key, entry.get("en", key)),
        }
    choice_labels = {}
    for key, entry in CHOICE_VALUE_LABELS.items():
        choice_labels[key] = {}
        for value, labels in entry.items():
            choice_labels[key][value] = {
                "en": labels.get("en", value),
                "zh": labels.get("zh", labels.get("en", value)),
                "he": HEBREW_CHOICE_LABELS.get(key, {}).get(value, labels.get("en", value)),
            }
    return {
        "sections": [
            {
                "step": section.step,
                "key": section.key,
                "label_en": section.label_en,
                "label_zh": section.label_zh,
                "weight": section.weight,
            }
            for section in SECTION_DEFINITIONS
        ],
        "tooltips": TOOLTIP_TERMS,
        "statuses": [{"value": key, "label": label} for key, label in STATUS_CHOICES],
        "question_labels": question_labels,
        "choice_labels": choice_labels,
    }


@require_http_methods(["GET", "POST"])
def supplier_form(request):
    if request.method == "POST":
        answers = _extract_answers(request)
        language_code = _normalized_language(answers.get("_language") or request.POST.get("_language"))
        submission_id = uuid.uuid4()
        files_map, file_errors = _save_uploads(request, submission_id, language_code)
        if file_errors:
            for err in file_errors:
                messages.error(request, err)
            return render(
                request,
                "ssq/form.html",
                {"form_payload": json.dumps(_summary_payload(), ensure_ascii=False)},
            )

        scoring = calculate_submission_score(answers, files_map)
        missing_required_uploads = _mandatory_check(files_map)
        if missing_required_uploads:
            extra_flags = list(set(scoring["critical_flags"] + ["missing_certificates_or_tests"]))
            scoring["critical_flags"] = extra_flags
            scoring["risk_level"] = "Critical Risk"
            missing_labels = []
            for field_name in missing_required_uploads:
                label_entry = MANDATORY_UPLOAD_LABELS.get(field_name, {})
                missing_labels.append(label_entry.get(language_code) or label_entry.get("en") or field_name)
            messages.warning(
                request,
                _message("missing_mandatory_uploads", language_code, items=", ".join(missing_labels)),
            )

        submission_language = str(answers.get("_language", "en"))
        language_code = _normalized_language(submission_language)
        product_type_raw = answers.get("product_type", "")

        submission = SupplierSubmission.objects.create(
            id=submission_id,
            companyName=str(answers.get("company_name", "")).strip()[:255],
            country=str(answers.get("country", "")).strip()[:100],
            contactName=str(answers.get("contact_person", "")).strip()[:150],
            email=str(answers.get("email", "")).strip()[:255],
            phone=str(answers.get("phone_whatsapp", "")).strip()[:50],
            website=str(answers.get("website", "")).strip()[:200],
            productType=_choice_label("product_type", product_type_raw, language_code)[:120],
            answers=answers,
            files=files_map,
            score=scoring["score"],
            riskLevel=scoring["risk_level"],
            scoreBreakdown=scoring["section_breakdown"],
            criticalFlags=scoring["critical_flags"],
            status="new",
            adminNotes="\n".join(scoring["auto_comments"]),
            language=submission_language,
        )

        try:
            _send_admin_summary_email(submission)
        except Exception:
            messages.warning(request, _message("submission_saved_email_failed", language_code))
        _send_supplier_confirmation_email(submission)

        request.session["ssq_latest_submission_id"] = str(submission.id)
        return redirect("supplier_form_thank_you")

    return render(
        request,
        "ssq/form.html",
        {"form_payload": json.dumps(_summary_payload(), ensure_ascii=False)},
    )


@require_GET
def supplier_form_thank_you(request):
    return render(request, "ssq/thank_you.html")


@require_http_methods(["GET", "POST"])
@never_cache
@ensure_csrf_cookie
def admin_login(request):
    form = SSQAdminLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        provided = form.cleaned_data["password"]
        expected = os.environ.get("ADMIN_PASSWORD", getattr(settings, "ADMIN_PASSWORD", ""))
        if expected and provided == expected:
            request.session[SESSION_ADMIN_KEY] = True
            return redirect("ssq_admin_submissions")
        messages.error(request, "Invalid admin password.")
    return render(request, "admin/ssq/login.html", {"form": form})


@require_GET
def admin_logout(request):
    request.session.pop(SESSION_ADMIN_KEY, None)
    return redirect("ssq_admin_login")


@_admin_required
@require_GET
@never_cache
def admin_submissions(request):
    submissions = SupplierSubmission.objects.all()
    score_min = request.GET.get("score_min")
    score_max = request.GET.get("score_max")
    country = (request.GET.get("country") or "").strip()
    product_type = (request.GET.get("product_type") or "").strip()
    risk_level = (request.GET.get("risk_level") or "").strip()
    status = (request.GET.get("status") or "").strip()
    search = (request.GET.get("q") or "").strip()

    if score_min:
        submissions = submissions.filter(score__gte=score_min)
    if score_max:
        submissions = submissions.filter(score__lte=score_max)
    if country:
        submissions = submissions.filter(country__icontains=country)
    if product_type:
        submissions = submissions.filter(productType__icontains=product_type)
    if risk_level:
        submissions = submissions.filter(riskLevel=risk_level)
    if status:
        submissions = submissions.filter(status=status)
    if search:
        submissions = submissions.filter(
            Q(companyName__icontains=search) | Q(contactName__icontains=search) | Q(email__icontains=search)
        )

    paginator = Paginator(submissions, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "admin/ssq/submissions.html",
        {
            "page_obj": page_obj,
            "statuses": STATUS_CHOICES,
            "filters": {
                "score_min": score_min or "",
                "score_max": score_max or "",
                "country": country,
                "product_type": product_type,
                "risk_level": risk_level,
                "status": status,
                "q": search,
            },
            "risk_levels": sorted(set(SupplierSubmission.objects.values_list("riskLevel", flat=True))),
        },
    )


@_admin_required
@require_http_methods(["GET", "POST"])
@never_cache
@ensure_csrf_cookie
def admin_submission_detail(request, submission_id):
    submission = get_object_or_404(SupplierSubmission, id=submission_id)
    form = SupplierSubmissionStatusForm(request.POST or None, instance=submission)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Submission updated.")
        return redirect("ssq_admin_submission_detail", submission_id=submission.id)
    return render(
        request,
        "admin/ssq/submission_detail.html",
        {"submission": submission, "form": form, "display_answers": _localized_answers(submission)},
    )


@_admin_required
@require_GET
def admin_submission_file(request, submission_id, file_key, index):
    submission = get_object_or_404(SupplierSubmission, id=submission_id)
    files_list = (submission.files or {}).get(file_key, [])
    try:
        file_item = files_list[index]
    except (IndexError, TypeError):
        raise Http404("File not found")

    relative_path = file_item.get("relative_path")
    if not relative_path:
        raise Http404("File path missing")
    absolute_path = _storage_root() / relative_path
    if not absolute_path.exists():
        raise Http404("File not found")

    mime, _ = mimetypes.guess_type(str(absolute_path))
    return FileResponse(
        absolute_path.open("rb"),
        as_attachment=False,
        filename=file_item.get("name") or absolute_path.name,
        content_type=mime or "application/octet-stream",
    )


@_admin_required
@require_GET
def admin_submissions_csv(request):
    submissions = SupplierSubmission.objects.all()
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="supplier_submissions.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "Company Name",
            "Country",
            "Contact Person",
            "Email",
            "Product Type",
            "Final Score",
            "Risk Level",
            "Submission Date",
            "Status",
        ]
    )
    for item in submissions:
        writer.writerow(
            [
                item.companyName,
                item.country,
                item.contactName,
                item.email,
                item.productType,
                item.score,
                item.riskLevel,
                item.createdAt.isoformat(),
                item.status,
            ]
        )
    return response


@_admin_required
@require_GET
def admin_submission_pdf(request, submission_id):
    submission = get_object_or_404(SupplierSubmission, id=submission_id)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except Exception:
        text = render_to_string("admin/ssq/pdf_fallback.txt", {"submission": submission})
        return HttpResponse(text, content_type="text/plain")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="supplier_submission_{submission.id}.pdf"'
    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 40
    lines = [
        "Supplier Qualification Summary",
        f"Company: {submission.companyName}",
        f"Country: {submission.country}",
        f"Contact: {submission.contactName}",
        f"Email: {submission.email}",
        f"Product Type: {submission.productType}",
        f"Score: {submission.score}",
        f"Risk Level: {submission.riskLevel}",
        f"Status: {submission.get_status_display()}",
        f"Submitted At: {submission.createdAt.strftime('%Y-%m-%d %H:%M')}",
        "",
        "Critical Flags:",
    ]
    for line in lines:
        pdf.drawString(40, y, line)
        y -= 20
    for flag in submission.criticalFlags or []:
        pdf.drawString(60, y, f"- {flag}")
        y -= 18
    y -= 10
    pdf.drawString(40, y, "Score Breakdown:")
    y -= 20
    for section, value in (submission.scoreBreakdown or {}).items():
        if y < 60:
            pdf.showPage()
            y = height - 40
        pdf.drawString(60, y, f"{section}: {value}")
        y -= 18
    pdf.showPage()
    pdf.save()
    return response

