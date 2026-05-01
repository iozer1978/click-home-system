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
    },
    "file_too_large": {
        "en": "File too large (max 20MB): {filename}",
        "zh": "文件过大（最大 20MB）：{filename}",
    },
    "submission_saved_email_failed": {
        "en": "Submission saved, but admin email could not be sent.",
        "zh": "提交已保存，但管理员邮件发送失败。",
    },
    "missing_mandatory_uploads": {
        "en": "Missing mandatory documents: {items}",
        "zh": "缺少必填文件：{items}",
    },
}

MANDATORY_UPLOAD_LABELS = {
    "certificates_uploads": {"en": "Certificates", "zh": "认证证书"},
    "steel_certificate_upload": {"en": "Steel certificate", "zh": "钢材证书"},
    "structural_calculation_example_upload": {"en": "Structural calculation example", "zh": "结构计算示例"},
    "fire_test_reports_upload": {"en": "Fire test reports", "zh": "防火测试报告"},
    "thermal_report_upload": {"en": "Thermal report", "zh": "热工性能报告"},
    "acoustic_report_upload": {"en": "Acoustic report", "zh": "隔音性能报告"},
    "water_moisture_report_upload": {"en": "Water/moisture report", "zh": "防水防潮报告"},
    "wall_section_upload": {"en": "Full wall section drawing", "zh": "完整墙体构造图"},
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
    return "zh" if str(value or "").lower().startswith("zh") else "en"


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
    return entry.get("en") or field_name.replace("_", " ").title()


def _choice_label(field_name: str, value: Any, language: str) -> str:
    value_str = str(value)
    choices = CHOICE_VALUE_LABELS.get(field_name, {})
    choice = choices.get(value_str)
    if not choice:
        return value_str
    if language == "zh":
        return choice.get("zh") or choice.get("en") or value_str
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
        "greeting": "Dear" if language == "en" else "尊敬的",
        "message_line": (
            "Thank you for submitting your supplier qualification form. Our technical team will review the information and contact you if further details are required."
            if language == "en"
            else "感谢您提交供应商资质评估表。我们的技术团队将审核您提供的信息，如需补充资料将与您联系。"
        ),
        "closing": "Best regards,\nClick Home Team" if language == "en" else "此致敬礼，\nClick Home 团队",
    }
    html_body = render_to_string(
        "emails/ssq_supplier_confirmation.html",
        context,
    )
    body = (
        "Thank you for submitting your supplier qualification form. "
        "Our technical team will review the information and contact you if further details are required."
        if language == "en"
        else "感谢您提交供应商资质评估表。我们的技术团队将审核信息，如需补充资料将与您联系。"
    )
    send_mail(
        "Supplier Qualification Submission Received" if language == "en" else "供应商资质评估表提交确认",
        body,
        settings.DEFAULT_FROM_EMAIL,
        [submission.email],
        html_message=html_body,
        fail_silently=True,
    )


def _summary_payload() -> dict[str, Any]:
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
        "question_labels": QUESTION_LABELS,
        "choice_labels": CHOICE_VALUE_LABELS,
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
        product_type_raw = str(answers.get("product_type", "")).strip()

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

