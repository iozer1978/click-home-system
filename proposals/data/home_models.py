import re
import json
from pathlib import Path
from django.utils.text import slugify


CATEGORY_LABELS = {
    "all": "הכל",
    "single-family": "בתים פרטיים",
    "modular": "בתים מודולריים",
    "adu": "ADU",
}

_MODULAR_SLUGS = {"modular", "prefab", "light-mobile", "light-build", "ready"}
_ADU_SLUGS = {"housing-units", "compact", "mobile", "container"}
_SINGLE_FAMILY_SLUGS = {"large-family", "medium-small", "wood"}


def _safe_float(value):
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _extract_number(pattern, text):
    if not text:
        return None
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def _extract_length_width(specs):
    if not specs:
        return None, None

    length = re.search(r"(?:אורך|length)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)", specs, flags=re.IGNORECASE)
    width = re.search(r"(?:רוחב|width)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)", specs, flags=re.IGNORECASE)
    return _safe_float(length.group(1) if length else None), _safe_float(width.group(1) if width else None)


def _sanitize_public_text(text):
    if not text:
        return ""
    sanitized = re.sub(r"https?://\S+", "", text)
    sanitized = re.sub(r"\b(?:Linke\s*House|linke\s*house)\b", "Click Home", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"\b(?:DEEPBLUE|Deepblue|Deep Blue)\b", "Click Home", sanitized, flags=re.IGNORECASE)
    return " ".join(sanitized.split()).strip()


def _infer_specs(area_m2, specs_text, title_text):
    scan_text = f"{specs_text or ''}\n{title_text or ''}"
    bedrooms = _extract_number(r"(?:חדרי?\s*שינה|bedrooms?)\s*[:\-]?\s*(\d+)", scan_text)
    bathrooms = _extract_number(r"(?:מרחצאות|חדרי?\s*רחצה|bathrooms?)\s*[:\-]?\s*(\d+)", scan_text)
    floors = _extract_number(r"(?:קומות|floors?)\s*[:\-]?\s*(\d+)", scan_text) or 1
    garages = _extract_number(r"(?:מוסך|garages?)\s*[:\-]?\s*(\d+)", scan_text) or (1 if "מוסך" in scan_text else 0)

    if bedrooms is None:
        if area_m2 >= 130:
            bedrooms = 4
        elif area_m2 >= 85:
            bedrooms = 3
        elif area_m2 >= 45:
            bedrooms = 2
        else:
            bedrooms = 1

    if bathrooms is None:
        bathrooms = 2 if area_m2 >= 90 else 1

    return bedrooms, bathrooms, floors, garages


def _build_features(specs, layout):
    features = []
    for line in (specs or "").splitlines():
        cleaned = _sanitize_public_text(line).strip("•- ")
        if cleaned and len(cleaned) > 4:
            features.append(cleaned)
    for line in (layout or "").splitlines():
        cleaned = _sanitize_public_text(line).strip("•- ")
        if cleaned and len(cleaned) > 4:
            features.append(cleaned)
    if not features:
        features = [
            "תכנון חכם המאפשר ניצול מיטבי של החלל",
            "רמת גמר גבוהה עם דגש על נוחות יומיומית",
            "אפשרות להתאמות אישיות לפי צרכי המשפחה",
        ]
    return features[:5]


def _classify_category(type_slugs):
    type_set = set(type_slugs)
    if type_set.intersection(_MODULAR_SLUGS):
        return "modular"
    if type_set.intersection(_ADU_SLUGS):
        return "adu"
    if type_set.intersection(_SINGLE_FAMILY_SLUGS):
        return "single-family"
    return "single-family"


def _rewrite_descriptions(title, area_m2, category_he):
    short_description = f"דגם {title} מציע פתרון מגורים איכותי בסטנדרט גבוה המתאים ל-{category_he}."
    full_description = (
        f"{title} תוכנן עבור לקוחות שמחפשים איזון בין אסתטיקה, פרקטיקה ונוחות יומיומית. "
        f"הדגם כולל חללים מוארים, תכנון יעיל ושפה אדריכלית נקייה. "
        f"שטח משוער: כ-{area_m2} מ\"ר, עם אפשרות להתאמות לפי צרכי המשפחה והפרויקט."
    )
    return short_description, full_description


def normalize_house_model(house):
    type_objs = list(house.house_types.all())
    type_slugs = [t.slug for t in type_objs]
    category = _classify_category(type_slugs)
    category_label_he = CATEGORY_LABELS.get(category, CATEGORY_LABELS["single-family"])

    images = [m.file.url for m in house.media_files.filter(media_type="image") if getattr(m, "file", None)]
    drawings = [m.file.url for m in house.media_files.filter(media_type="image") if getattr(m, "file", None) and "draw" in m.file.name.lower()]
    if house.blueprint_image:
        drawings.insert(0, house.blueprint_image.url)

    main_image_obj = house.get_main_image()
    main_image = main_image_obj.url if main_image_obj else f"/static/images/tab/placeholders/{category}.svg"
    gallery_images = images[:6] if images else [main_image]
    floorplan_images = drawings[:4]

    area_m2 = int(house.area_sqm or 0)
    bedrooms, bathrooms, floors, garages = _infer_specs(area_m2, house.specs, house.title)
    length_m, width_m = _extract_length_width(house.specs)

    style_tags = [t.name for t in type_objs][:3]
    if not style_tags:
        style_tags = ["תכנון מודרני", "איכות פרימיום"]

    short_description_he, full_description_he = _rewrite_descriptions(house.title, area_m2, category_label_he)

    return {
        "id": f"house-{house.id}",
        "slug": slugify(house.title, allow_unicode=True) or f"house-{house.id}",
        "model_name": house.title,
        "category": category,
        "category_label_he": category_label_he,
        "short_description_he": short_description_he,
        "full_description_he": full_description_he,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "toilets": bathrooms,
        "living_rooms": 1,
        "kitchens": 1,
        "garages": garages,
        "floors": floors,
        "stairs": 1 if floors and floors > 1 else 0,
        "area_m2": area_m2,
        "length_m": length_m,
        "width_m": width_m,
        "style_tags": style_tags,
        "features_he": _build_features(house.specs, house.internal_layout),
        "main_image": main_image,
        "gallery_images": gallery_images,
        "floorplan_images": floorplan_images,
        "inquiry_cta_label": "אני רוצה פרטים",
        "internal_source_reference": {
            "config_key": house.config_key,
            "db_pk": house.id,
            "house_type_slugs": type_slugs,
        },
    }


def build_tab_catalog(houses):
    return [normalize_house_model(house) for house in houses]


def _load_external_catalog():
    data_path = Path(__file__).resolve().parent / "deepblue_models.json"
    if not data_path.exists():
        return []
    try:
        payload = json.loads(data_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    cleaned = []
    for model in payload:
        model_copy = dict(model)
        model_copy["model_name"] = _sanitize_public_text(model_copy.get("model_name", "דגם"))
        model_copy["model_name_he"] = _sanitize_public_text(model_copy.get("model_name_he", ""))
        model_copy["subtitle_he"] = _sanitize_public_text(model_copy.get("subtitle_he", ""))
        model_copy["description_he"] = _sanitize_public_text(model_copy.get("description_he", ""))
        model_copy["short_description_he"] = _sanitize_public_text(model_copy.get("short_description_he", ""))
        model_copy["full_description_he"] = _sanitize_public_text(model_copy.get("full_description_he", ""))
        model_copy["features_he"] = [_sanitize_public_text(item) for item in model_copy.get("features_he", [])]
        cleaned.append(model_copy)
    return cleaned


def _build_admin_catalog():
    from proposals.models import TabHouse

    external_by_slug = {item.get("slug"): item for item in _load_external_catalog()}

    houses = (
        TabHouse.objects.filter(is_published=True)
        .prefetch_related("images", "house_types")
        .order_by("sort_order", "id")
    )
    catalog = []
    for house in houses:
        category_label = dict(TabHouse.CATEGORY_CHOICES).get(house.category, CATEGORY_LABELS["single-family"])
        grouped = {"hero": [], "gallery": [], "floorplan": [], "lifestyle": []}
        for image in house.images.all():
            if not image.image:
                continue
            grouped.setdefault(image.image_type, []).append(image.image.url)

        ext = external_by_slug.get(house.slug, {})

        hero_image = (
            grouped["hero"][:1]
            or grouped["gallery"][:1]
            or grouped["floorplan"][:1]
            or grouped["lifestyle"][:1]
            or ([ext.get("hero_image")] if ext.get("hero_image") else [])
            or ([ext.get("main_image")] if ext.get("main_image") else [])
            or [f"/static/images/tab/placeholders/{house.category}.svg"]
        )[0]
        gallery_images = grouped["gallery"] or ext.get("gallery_images") or [hero_image]
        floorplan_images = grouped["floorplan"][:1] or (ext.get("floorplan_images") or [])[:1]
        lifestyle_candidates = grouped["lifestyle"][:1]
        if not lifestyle_candidates and ext.get("lifestyle_image"):
            lifestyle_candidates = [ext.get("lifestyle_image")]
        if not lifestyle_candidates:
            lifestyle_candidates = gallery_images[:1] or [hero_image]
        lifestyle_image = lifestyle_candidates[0]

        features = [line.strip("•- ").strip() for line in (house.features_he or "").splitlines() if line.strip()]
        if not features:
            features = ["תכנון מודרני", "התאמה אישית", "בנייה באיכות גבוהה"]

        catalog.append(
            {
                "id": f"tab-house-{house.id}",
                "slug": house.slug,
                "model_name": house.model_name,
                "model_name_he": house.model_name,
                "subtitle_he": house.subtitle_he or f"דגם {house.model_name} לחוויית מגורים מתקדמת.",
                "category": house.category,
                "category_label_he": category_label,
                "short_description_he": house.subtitle_he or f"דגם {house.model_name} בקטגוריית {category_label}.",
                "description_he": house.description_he,
                "full_description_he": house.description_he,
                "bedrooms": house.bedrooms,
                "bathrooms": house.bathrooms,
                "toilets": house.bathrooms,
                "living_rooms": house.living_rooms,
                "kitchens": house.kitchen_count,
                "kitchen_count": house.kitchen_count,
                "garages": house.garages,
                "floors": house.floors,
                "stairs": 1 if house.floors and house.floors > 1 else 0,
                "area_m2": int(house.area_m2 or 0),
                "length_m": _safe_float(house.length_m),
                "width_m": _safe_float(house.width_m),
                "style_tags": [t.name for t in house.house_types.all()[:3]] or [category_label],
                "features_he": features[:9],
                "hero_image": hero_image,
                "main_image": hero_image,
                "gallery_images": gallery_images[:10],
                "floorplan_images": floorplan_images,
                "lifestyle_image": lifestyle_image,
                "inquiry_cta_label": house.inquiry_cta_label or "אני רוצה פרטים",
                "internal_source_reference": {"admin_tab_house_id": house.id},
            }
        )
    return catalog


def get_tab_catalog(houses):
    admin_catalog = _build_admin_catalog()
    if admin_catalog:
        return admin_catalog
    external_models = _load_external_catalog()
    if external_models:
        return external_models
    return build_tab_catalog(houses)

