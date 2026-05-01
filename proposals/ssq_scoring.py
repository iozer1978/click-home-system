from __future__ import annotations

from typing import Any

from .ssq_config import CRITICAL_RULES, RISK_LEVELS, SCORING_FIELDS, SECTION_WEIGHTS


def _is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return str(value).strip() != ""


def _safe_float(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return None


def _section_score(answers: dict[str, Any], section_key: str) -> float:
    fields = SCORING_FIELDS.get(section_key, [])
    if not fields:
        return 0.0
    filled = sum(1 for field in fields if _is_filled(answers.get(field)))
    return (filled / len(fields)) * 100.0


def _is_negative(value: Any) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return False
    negative_tokens = [
        "no",
        "none",
        "not available",
        "false",
        "n/a",
        "否",
        "不",
        "没有",
        "無",
        "无法",
        "不提供",
    ]
    return any(token in text for token in negative_tokens)


def _detect_critical_flags(answers: dict[str, Any], files: dict[str, list[dict[str, Any]]]) -> list[str]:
    flags: list[str] = []

    if not files.get("wall_section_upload"):
        flags.append("missing_full_wall_section")
    if not files.get("fire_test_reports_upload"):
        flags.append("missing_fire_test_report")
    if not _is_filled(answers.get("steel_grade")) and not files.get("steel_certificate_upload"):
        flags.append("missing_structural_steel_spec")
    if not files.get("certificates_uploads") and not files.get("thermal_report_upload") and not files.get("acoustic_report_upload"):
        flags.append("missing_certificates_or_tests")
    if not _is_filled(answers.get("external_board_type")) or not _is_filled(answers.get("insulation_type_assembly")):
        flags.append("missing_material_specification")
    third_party_text = answers.get("third_party_inspection_available")
    if _is_negative(third_party_text):
        flags.append("refuses_third_party_inspection")

    all_text_values = " ".join(str(value).strip().lower() for value in answers.values() if isinstance(value, str))
    if "high quality" in all_text_values and "mpa" not in all_text_values and "iso" not in all_text_values and "en " not in all_text_values:
        flags.append("claims_without_data")

    return sorted(set(flags))


def _risk_level(total_score: float, critical_flags: list[str]) -> str:
    if critical_flags:
        return "Critical Risk"
    for min_score, max_score, label in RISK_LEVELS:
        if min_score <= total_score <= max_score:
            return label
    return "Not recommended"


def _auto_comments(answers: dict[str, Any], files: dict[str, list[dict[str, Any]]], critical_flags: list[str]) -> list[str]:
    comments: list[str] = []

    if "missing_fire_test_report" in critical_flags:
        comments.append("Missing fire test report")
    if "missing_full_wall_section" in critical_flags:
        comments.append("No full wall assembly uploaded")
    if "refuses_third_party_inspection" in critical_flags:
        comments.append("No third-party inspection option")

    galvanization = str(answers.get("galvanization_level") or "").upper().strip()
    if galvanization and all(item not in galvanization for item in ("Z200", "Z275", "Z350")):
        comments.append("Steel galvanization below preferred level")

    if not critical_flags:
        documentation_count = sum(len(files.get(key, [])) for key in files.keys())
        if documentation_count >= 6:
            comments.append("Strong technical documentation")

    return comments


def calculate_submission_score(
    answers: dict[str, Any],
    files: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    section_scores: dict[str, float] = {}
    weighted_total = 0.0

    for section_key, weight in SECTION_WEIGHTS.items():
        if not weight:
            continue
        raw_score = _section_score(answers, section_key)
        section_scores[section_key] = round(raw_score, 2)
        weighted_total += (raw_score * weight) / 100

    # Threshold-based adjustments
    yield_strength = _safe_float(answers.get("yield_strength_mpa"))
    if yield_strength is not None and yield_strength < 300:
        weighted_total -= 3
        section_scores["structural_steel_quality"] = max(0.0, section_scores.get("structural_steel_quality", 0.0) - 10)

    steel_thickness = _safe_float(answers.get("profile_thickness_mm"))
    if steel_thickness is not None and steel_thickness < 1.2:
        weighted_total -= 2
        section_scores["structural_steel_quality"] = max(0.0, section_scores.get("structural_steel_quality", 0.0) - 5)

    wall_fire_rating = _safe_float(answers.get("wall_fire_rating_min"))
    if wall_fire_rating is not None and wall_fire_rating < 45:
        weighted_total -= 3
        section_scores["fire_resistance"] = max(0.0, section_scores.get("fire_resistance", 0.0) - 15)

    stc_value = _safe_float(answers.get("wall_stc_rating"))
    if stc_value is not None and stc_value < 45:
        weighted_total -= 1
        section_scores["acoustic_insulation"] = max(0.0, section_scores.get("acoustic_insulation", 0.0) - 8)

    critical_flags = _detect_critical_flags(answers, files)
    risk_level = _risk_level(weighted_total, critical_flags)
    comments = _auto_comments(answers, files, critical_flags)

    critical_labels = {key: label for key, label in CRITICAL_RULES}
    critical_items = [critical_labels.get(flag, flag) for flag in critical_flags]

    return {
        "score": max(0.0, round(weighted_total, 2)),
        "section_breakdown": section_scores,
        "risk_level": risk_level,
        "critical_flags": critical_flags,
        "critical_items": critical_items,
        "auto_comments": comments,
    }

