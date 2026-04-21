import json
import re
import urllib.request
from pathlib import Path


CATEGORY_SOURCES = {
    "single-family": {"url": "https://www.deepbluehome.com/singlefamilyhomes", "label_he": "בתים פרטיים"},
    "modular": {"url": "https://www.deepbluehome.com/modularhomes", "label_he": "בתים מודולריים"},
    "adu": {"url": "https://www.deepbluehome.com/adu", "label_he": "ADU"},
}


UA_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers=UA_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", "ignore")


def strip_html(text: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&amp;", "&").replace("&quot;", '"').replace("&#039;", "'")
    return " ".join(text.split()).strip()


def slugify_text(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower() or "model"


def sanitize_public_text(text: str) -> str:
    cleaned = text or ""
    cleaned = re.sub(r"\bDEEPBLUE(?:\s+SMARTHOUSE)?\b", "Click Home", cleaned, flags=re.I)
    cleaned = re.sub(r"\bDeepblue(?:\s+SmartHouse)?\b", "Click Home", cleaned, flags=re.I)
    cleaned = re.sub(r"\bDeep Blue\b", "Click Home", cleaned, flags=re.I)
    return cleaned.strip()


def translate_title_to_hebrew(title: str) -> str:
    text = title or ""
    replacements = {
        "Light steel frame": "שלד פלדה קלה",
        "light steel frame": "שלד פלדה קלה",
        "prefab house": "בית טרומי",
        "prefab homes": "בתים טרומיים",
        "prefabricated": "טרומי",
        "panelized house kits": "ערכות בנייה פנליות",
        "modular house design": "תכנון בית מודולרי",
        "modular": "מודולרי",
        "house": "בית",
    }
    for src, dst in replacements.items():
        text = re.sub(re.escape(src), dst, text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" -")
    if not text.startswith("דגם"):
        text = f"דגם {text}"
    return text


def extract_first_int(pattern: str, text: str, default: int = 0) -> int:
    match = re.search(pattern, text, flags=re.I)
    if not match:
        return default
    try:
        return int(float(match.group(1)))
    except (TypeError, ValueError):
        return default


def extract_first_float(pattern: str, text: str):
    match = re.search(pattern, text, flags=re.I)
    if not match:
        return None
    try:
        return round(float(match.group(1)), 2)
    except (TypeError, ValueError):
        return None


def get_meta_content(html: str, key: str):
    match = re.search(rf'<meta[^>]+{key}[^>]+content="([^"]+)"', html, flags=re.I)
    return match.group(1).strip() if match else ""


def parse_product_page(product_url: str):
    try:
        html = fetch_html(product_url)
    except Exception:
        return {}

    text = strip_html(html)
    og_image = get_meta_content(html, r'property="og:image"') or get_meta_content(html, r'name="twitter:image"')
    media_urls = re.findall(
        r'https://(?:www\.deepbluehome\.com/wp-content/uploads|static\.wixstatic\.com/media)/[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)',
        html,
        flags=re.I,
    )
    media_urls = [url.split("?")[0] for url in media_urls]
    media_urls = list(dict.fromkeys(media_urls))
    filtered_media = []
    for url in media_urls:
        lower = url.lower()
        if any(skip in lower for skip in ["logo", "icon", "avatar", "payment", "flag", "menu", "favicon"]):
            continue
        filtered_media.append(url)
    def normalized_key(url: str) -> str:
        last = url.split("/")[-1].lower()
        last = re.sub(r"-\d+x\d+(?=\.)", "", last)
        return last

    deduped_media = []
    seen_keys = set()
    for url in filtered_media:
        key = normalized_key(url)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped_media.append(url)
    media_urls = deduped_media

    floorplan_urls = []
    for marker in ["GROUND FLOOR", "FIRST FLOOR", "FLOOR PLAN", "Floor Plan", "floor plan"]:
        for match in re.finditer(marker, html, flags=re.I):
            start = max(0, match.start() - 900)
            end = min(len(html), match.end() + 900)
            window = html[start:end]
            window_urls = re.findall(
                r'https://(?:www\.deepbluehome\.com/wp-content/uploads|static\.wixstatic\.com/media)/[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)',
                window,
                flags=re.I,
            )
            for wurl in window_urls:
                clean = wurl.split("?")[0]
                if clean not in floorplan_urls:
                    floorplan_urls.append(clean)

    floorplan_urls = [url for url in floorplan_urls if any(x in url.lower() for x in ["floor", "plan", "layout", "ground", "first", "house2"])]

    title = ""
    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.S | re.I)
    if title_match:
        title = sanitize_public_text(strip_html(title_match.group(1)))

    area = extract_first_int(r"House Area\s*([0-9]+(?:\.[0-9]+)?)", text, default=0)
    if not area:
        area = extract_first_int(r"Total area[^\d]*([0-9]+(?:\.[0-9]+)?)", text, default=0)
    length_m = extract_first_float(r"House Length\s*([0-9]+(?:\.[0-9]+)?)", text)
    width_m = extract_first_float(r"House Width\s*([0-9]+(?:\.[0-9]+)?)", text)

    paragraphs = re.findall(r"(?:<p[^>]*>|</h1>)(.*?)(?:</p>|<h2|<h3)", html, flags=re.S | re.I)
    clean_paras = []
    for p in paragraphs:
        p_text = sanitize_public_text(strip_html(p))
        if len(p_text) > 85 and "copyright" not in p_text.lower():
            clean_paras.append(p_text)
    clean_paras = clean_paras[:4]

    list_items = [sanitize_public_text(strip_html(x)) for x in re.findall(r"<li[^>]*>(.*?)</li>", html, flags=re.S | re.I)]
    list_items = [x for x in list_items if 8 < len(x) < 120][:9]

    return {
        "title": title,
        "og_image": og_image,
        "media_urls": media_urls,
        "floorplan_urls": floorplan_urls,
        "area_m2": area,
        "length_m": length_m,
        "width_m": width_m,
        "paragraphs": clean_paras,
        "list_items": list_items,
    }


def build_hebrew_content(title, category_label_he, specs, product_details):
    area_m2 = specs["area_m2"]
    beds = specs["bedrooms"]
    baths = specs["bathrooms"]
    floors = specs["floors"]
    subtitle = f"בית מודרני בקטגוריית {category_label_he} עם תכנון חכם למשפחה קטנה."
    if beds >= 3:
        subtitle = f"דגם משפחתי מרווח בקטגוריית {category_label_he} עם זרימת חללים מוקפדת."

    base_description = (
        f"{title} מציע פתרון מגורים מתקדם עם תכנון מאוזן בין עיצוב, פרקטיות ונוחות יומיומית. "
        f"הדגם כולל חלוקה פנימית יעילה, חללים מוארים והתאמה מצוינת למגורים קבועים או להשקעה."
    )
    extra = (
        f"שטח משוער: כ-{area_m2} מ\"ר, {beds} חדרי שינה, {baths} חדרי רחצה ו-{floors} קומות. "
        f"המבנה מתוכנן לביצועים תרמיים טובים ולרמת גמר איכותית."
    )

    if product_details.get("paragraphs"):
        source_para = product_details["paragraphs"][0]
        source_para = re.sub(r"\s+", " ", source_para)
        # Non-literal Hebrew marketing rewrite from source context.
        base_description = (
            f"{title} פותח בגישה מודרנית המשלבת שלד פלדה קלה, תכנון מדויק ועמידות גבוהה לאורך זמן. "
            f"הדגם מדגיש ניצול נכון של החלל, נוחות מגורים יומיומית ואפשרות להתאמות לפרויקט."
        )
        if "energy" in source_para.lower() or "insulation" in source_para.lower():
            extra = (
                f"הדגש התכנוני כולל יעילות אנרגטית, מעטפת מבודדת ותחושת מרחב נעימה בכל עונות השנה. "
                f"הנתונים המרכזיים: {beds} חדרי שינה, {baths} חדרי רחצה, {floors} קומות וכ-{area_m2} מ\"ר."
            )

    features = [
        "תכנון מודרני פתוח",
        "חללים מוארים עם זרימת אוויר טבעית",
        "אפשרות לליווי התאמות אדריכליות",
        "מעטפת מתקדמת לנוחות תרמית",
        "בנייה מדויקת ברמת גמר גבוהה",
        "עמידות גבוהה לטווח ארוך",
        "קצב ביצוע מהיר יחסית",
        "תחזוקה נוחה לאורך שנים",
        "מענה מצוין למגורים או השקעה",
    ]
    if product_details.get("list_items"):
        features = []
        for item in product_details["list_items"][:9]:
            short_item = item.split(":")[-1].strip()
            short_item = re.sub(r"^[0-9]+\.\s*", "", short_item)
            if len(short_item) < 6:
                continue
            # Premium Hebrew rewrite style based on imported bullet semantics.
            if "precision" in short_item.lower():
                features.append("תכנון מדויק ברמת הנדסה גבוהה")
            elif "stability" in short_item.lower():
                features.append("יציבות מבנית גבוהה לאורך זמן")
            elif "lightweight" in short_item.lower():
                features.append("מערכת קלה לוגיסטית לביצוע יעיל")
            elif "weather" in short_item.lower():
                features.append("עמידות לתנאי מזג אוויר מאתגרים")
            elif "sustain" in short_item.lower() or "recycl" in short_item.lower():
                features.append("פתרון מתקדם עם חשיבה סביבתית")
            elif "fire" in short_item.lower():
                features.append("מרכיבי מעטפת עם דגש בטיחותי")
            else:
                features.append("סטנדרט תכנון וביצוע ברמה גבוהה")
        if not features:
            features = [
                "תכנון מודרני פתוח",
                "חללים מוארים עם זרימת אוויר טבעית",
                "אפשרות לליווי התאמות אדריכליות",
            ]
        while len(features) < 9:
            features.append("חוויית מגורים פרימיום")

    return subtitle, f"{base_description} {extra}", features[:9]


def parse_cards(category_html: str, category_key: str, category_label_he: str):
    cards = []
    card_chunks = [
        match.group(0)
        for match in re.finditer(
            r"<h3[^>]*>.*?</h3>.*?href=\"https://www\.deepbluehome\.com/[^\"]+\"[^>]*>Take a look</a>",
            category_html,
            flags=re.S,
        )
    ]

    for idx, chunk in enumerate(card_chunks, start=1):
        title_match = re.search(r"<h3[^>]*>(.*?)</h3>", chunk, flags=re.S)
        link_match = re.search(r'href="(https://www\.deepbluehome\.com/[^"]+)"[^>]*>Take a look</a>', chunk, flags=re.S)
        if not title_match or not link_match:
            continue

        title = sanitize_public_text(strip_html(title_match.group(1)))
        product_url = link_match.group(1).strip()

        spec_zone_match = re.search(r"</h3>(.*?)House Dimensions", chunk, flags=re.S)
        numbers = re.findall(r">\s*(\d+)\s*<", spec_zone_match.group(1) if spec_zone_match else "")
        beds = int(numbers[0]) if len(numbers) > 0 else 0
        baths = int(numbers[1]) if len(numbers) > 1 else 0
        living_rooms = int(numbers[2]) if len(numbers) > 2 else 1
        garages = int(numbers[3]) if len(numbers) > 3 else 0
        kitchens = int(numbers[4]) if len(numbers) > 4 else 1
        floors = int(numbers[5]) if len(numbers) > 5 else 1

        listing_image_match = re.search(r'https://static\.wixstatic\.com/media/[^\s"\']+', chunk)
        listing_image = listing_image_match.group(0) if listing_image_match else f"/static/images/tab/placeholders/{category_key}.svg"

        details = parse_product_page(product_url)
        hero_image = details.get("og_image") or listing_image
        media_urls = details.get("media_urls") or [hero_image]
        if hero_image and hero_image not in media_urls:
            media_urls.insert(0, hero_image)
        gallery_images = media_urls[:10] if media_urls else [hero_image]
        def is_floorplan(url: str) -> bool:
            filename = url.split("/")[-1].lower()
            return any(key in filename for key in ["floor", "plan", "layout", "ground", "first", "house2"])

        floorplan_candidates = [url for url in (details.get("floorplan_urls") or []) if is_floorplan(url)]
        floorplan_candidates.extend([url for url in media_urls if is_floorplan(url)])
        floorplan_candidates = list(dict.fromkeys(floorplan_candidates))

        # User requested one central floorplan-like image after main visuals.
        if len(gallery_images) >= 3:
            middle_idx = len(gallery_images) // 2
            floorplan_images = [gallery_images[middle_idx]]
        elif floorplan_candidates:
            floorplan_images = [floorplan_candidates[0]]
        else:
            floorplan_images = []

        area_guess = max(18, beds * 26 + living_rooms * 11 + baths * 6 + 16)
        area_m2 = details.get("area_m2") or area_guess
        length_m = details.get("length_m")
        width_m = details.get("width_m")

        specs = {
            "area_m2": area_m2,
            "bedrooms": beds,
            "bathrooms": baths,
            "floors": floors or 1,
        }
        subtitle_he, description_he, features_he = build_hebrew_content(
            title=title,
            category_label_he=category_label_he,
            specs=specs,
            product_details=details,
        )

        cards.append(
            {
                "id": f"deepblue-{category_key}-{idx:03d}",
                "slug": slugify_text(title),
                "model_name": title,
                "model_name_he": translate_title_to_hebrew(title),
                "subtitle_he": subtitle_he,
                "category": category_key,
                "category_label_he": category_label_he,
                "short_description_he": subtitle_he,
                "description_he": description_he,
                "full_description_he": description_he,
                "bedrooms": beds,
                "bathrooms": baths,
                "living_rooms": living_rooms,
                "kitchens": kitchens,
                "kitchen_count": kitchens,
                "garages": garages,
                "floors": floors or 1,
                "area_m2": area_m2,
                "length_m": length_m,
                "width_m": width_m,
                "style_tags": [category_label_he, "תכנון מודרני", "פרימיום"],
                "features_he": features_he,
                "hero_image": hero_image,
                "main_image": hero_image,
                "gallery_images": gallery_images,
                "floorplan_images": floorplan_images,
                "lifestyle_image": gallery_images[2] if len(gallery_images) > 2 else hero_image,
                "inquiry_cta_label": "אני רוצה פרטים",
                "internal_source_reference": {
                    "source_url": CATEGORY_SOURCES[category_key]["url"],
                    "product_url": product_url,
                },
            }
        )

    return cards


def main():
    all_models = []
    for category_key, config in CATEGORY_SOURCES.items():
        html = fetch_html(config["url"])
        models = parse_cards(html, category_key=category_key, category_label_he=config["label_he"])
        all_models.extend(models)
        print(f"{category_key}: {len(models)} models")

    output_path = Path(__file__).resolve().parents[1] / "proposals" / "data" / "deepblue_models.json"
    output_path.write_text(json.dumps(all_models, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {output_path} ({len(all_models)} total)")


if __name__ == "__main__":
    main()
