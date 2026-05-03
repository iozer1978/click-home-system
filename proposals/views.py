import re

from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse, Http404, FileResponse, HttpResponseRedirect
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q, Count, Sum
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.templatetags.static import static as static_url
import json
import base64
from pathlib import Path
from .models import Quote, HouseModel, HouseUpgrade, UsageType, HouseType, FAQ
from .forms import ClientRegisterForm
from .utils import queue_email, send_email_from_queue
from .data.home_models import get_tab_catalog, CATEGORY_LABELS


TAB_CATEGORY_OPTIONS = [
    {"value": "all", "label": CATEGORY_LABELS["all"]},
    {"value": "single-family", "label": CATEGORY_LABELS["single-family"]},
    {"value": "modular", "label": CATEGORY_LABELS["modular"]},
    {"value": "adu", "label": CATEGORY_LABELS["adu"]},
]

TAB_ICON_FILES = {
    "toilets.jpg": "Toilets.jpg",
    "bathrooms.jpg": "Bathrooms.jpg",
    "bedrooms.jpg": "Bedrooms.jpg",
    "kitchen.jpg": "Kitchen.jpg",
    "living-room.jpg": "Living room.jpg",
    "parking.jpg": "Parking.jpg",
    "stairs.jpg": "Stairs.jpg",
}

CONTACT_CARD_BASE = {
    "brand_name": "Click Home",
    "brand_tagline": "Building Your Dream",
    "company": "Click Home",
    "website": "https://www.click-home.co.il/en",
    "address_lines": [
        "4 Mordechai Kostelitz St.",
        "Sha'ar Hadera Towers, Israel",
        "3852901",
    ],
    "address_query": "4 Mordechai Kostelitz St, Sha'ar Hadera Towers, Israel 3852901",
    "maps_url": "https://maps.app.goo.gl/yzxENvM2A4Xq1qhy8",
    "company_section_title": "Smart & Advanced Construction Solutions",
    "company_points": [
        "Light Gauge Steel (LGS) Solutions",
        "Modular & Container Structures",
        "Residential, Hospitality & Public Sector Projects",
        "Extensions & Structural Additions",
    ],
}

CONTACT_CARD_PROFILES = {
    "itzik": {
        "slug": "itzik",
        "name": "Itzik Ozer",
        "title": "Founder & Director of Global Supplier Partnerships",
        "mobile_label": "Mobile",
        "mobile_tel": "+972542082082",
        "phone_label": "Phone",
        "phone_tel": "+97297902727",
        "whatsapp_url": "https://wa.me/972542082082",
        "wechat_id": "Itzik1903",
        "save_vcf_url": "/api/vcf/itzik",
    },
    "hagit": {
        "slug": "hagit",
        "name": "Hagit Mor Elmalan",
        "title": "Founder & CEO",
        "mobile_label": "Mobile",
        "mobile_tel": "+972503439999",
        "phone_label": "Phone",
        "phone_tel": "+97297902727",
        "whatsapp_url": "https://wa.me/972503439999",
        "wechat_id": "wxid_qrptybbvsg0kt22",
        "save_vcf_url": "/api/vcf/hagit",
    },
}


def _to_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _is_valid_israeli_mobile(phone_digits):
    """מספר נייד ישראלי: 05… או +972 / 972 עם ספרות מספיקות."""
    if not phone_digits or len(phone_digits) < 9:
        return False
    if phone_digits.startswith("05") and len(phone_digits) >= 10:
        return True
    if phone_digits.startswith("+972"):
        core = phone_digits[4:].lstrip("0")
        return core.startswith("5") and len(core) >= 9
    if phone_digits.startswith("972"):
        core = phone_digits[3:].lstrip("0")
        return core.startswith("5") and len(core) >= 9
    return False


def _validate_lead_minimal(post_data):
    """טופס ליד קצר (דף הבית) — שם + טלפון חובה; שאר השדות אופציונליים."""
    full_name = (post_data.get("full_name") or post_data.get("name") or "").strip()
    phone = (post_data.get("phone") or "").strip()
    email = (post_data.get("email") or "").strip()
    interest_type = (post_data.get("interest_type") or post_data.get("subject") or "").strip()
    message_text = (post_data.get("message") or "").strip()

    errors = {}
    if not full_name:
        errors["full_name"] = "יש להזין שם מלא."

    phone_digits = re.sub(r"[\s\-\u200f]", "", phone)
    if not _is_valid_israeli_mobile(phone_digits):
        errors["phone"] = "יש להזין מספר טלפון ישראלי תקין (למשל 05x-xxxxxxx או +972…)."

    if email:
        try:
            validate_email(email)
        except ValidationError:
            errors["email"] = "כתובת המייל אינה תקינה."

    cleaned = {
        "full_name": full_name[:100],
        "phone": phone[:30],
        "email": email[:255],
        "interest_type": (interest_type or "פנייה מהאתר")[:120],
        "message": (message_text or "—")[:1500],
        "model_name": (post_data.get("model_name") or "").strip()[:120],
    }
    return cleaned, errors


def _validate_lead_payload(post_data):
    full_name = (post_data.get("full_name") or post_data.get("name") or "").strip()
    phone = (post_data.get("phone") or "").strip()
    email = (post_data.get("email") or "").strip()
    interest_type = (post_data.get("interest_type") or post_data.get("subject") or "").strip()
    message_text = (post_data.get("message") or "").strip()
    model_name = (post_data.get("model_name") or "").strip()

    errors = {}
    if not full_name:
        errors["full_name"] = "יש להזין שם מלא."
    if not phone or len(phone) < 9:
        errors["phone"] = "יש להזין מספר טלפון תקין."
    if email:
        try:
            validate_email(email)
        except ValidationError:
            errors["email"] = "כתובת המייל אינה תקינה."
    if not interest_type:
        errors["interest_type"] = "יש לבחור סוג נכס."
    if not message_text:
        errors["message"] = "יש להזין הודעה."

    cleaned = {
        "full_name": full_name[:100],
        "phone": phone[:30],
        "email": email[:255],
        "interest_type": interest_type[:120],
        "message": message_text[:1500],
        "model_name": model_name[:120],
    }
    return cleaned, errors


def _send_lead_email(cleaned_data, source_label):
    subject = f"פנייה חדשה - Click Home ({source_label})"
    body = (
        f"שם מלא: {cleaned_data['full_name']}\n"
        f"טלפון: {cleaned_data['phone']}\n"
        f"מייל: {cleaned_data['email'] or 'לא הוזן'}\n"
        f"סוג נכס: {cleaned_data['interest_type']}\n"
        f"דגם נבחר: {cleaned_data['model_name'] or 'לא נבחר'}\n\n"
        f"הודעה:\n{cleaned_data['message']}\n"
    )
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        ["info@click-home.co.il"],
        fail_silently=False,
    )

DEFAULT_HOME_FAQS = [
    {
        "question": "מה זה בית יביל או מודולרי?",
        "answer": "מדובר במבנה שמיוצר במפעל בשליטה תעשייתית, מגיע לאתר מוכן לרוב שלב ההרכבה, ומקצר משמעותית את זמן הבנייה לעומת בנייה רטובה קלאסית.",
    },
    {
        "question": "האם ניתן להתאים את הדגם לצרכים שלי?",
        "answer": "בהחלט. ניתן לבחור שדרוגים, גימורים ולעיתים שינויי תכנון — הצוות שלנו ילווה אתכם בתהליך התאמה אישית ובשקיפות מחירים.",
    },
    {
        "question": "איך מתחילים תהליך והצעת מחיר?",
        "answer": "משאירים פרטים בטופס באתר או בוואטסאפ, נקבעת שיחת התאמה קצרה, ולאחר מכן נכין עבורכם הצעה מפורטת בהתאם לדגם ולשדרוגים שבחרתם.",
    },
]


def home_page(request):
    houses = HouseModel.objects.prefetch_related("house_types", "media_files").all()
    type_slug = request.GET.get("type", "").strip()
    if type_slug:
        houses = houses.filter(house_types__slug=type_slug).distinct()
    faqs = FAQ.objects.filter(is_visible=True).order_by("order")
    house_types = HouseType.objects.all()
    featured_houses = (
        HouseModel.objects.filter(media_files__media_type="image")
        .distinct()
        .prefetch_related("media_files")[:4]
    )

    project_gallery_media = []
    for h in featured_houses:
        for m in h.media_files.all():
            if m.media_type == "image" and len(project_gallery_media) < 8:
                project_gallery_media.append((h.title, m))

    faqs_display = [{"question": f.question, "answer": f.answer} for f in faqs]
    if not faqs_display:
        faqs_display = list(DEFAULT_HOME_FAQS)

    hero_image_url = "/media/main-hero.jpg"
    hero_path = Path(settings.MEDIA_ROOT) / "main-hero.jpg"
    if not hero_path.exists():
        hero_image_url = None
        first_with_img = HouseModel.objects.prefetch_related("media_files").first()
        if first_with_img:
            main_img = first_with_img.get_main_image()
            if main_img:
                hero_image_url = main_img.url
        if not hero_image_url:
            hero_image_url = "/media/main-hero.jpg"

    canonical_url = request.build_absolute_uri(reverse("home"))
    host = f"{request.scheme}://{request.get_host()}"
    logo_abs = request.build_absolute_uri(static_url("site/img/logo_clickhome.png"))

    houses_for_schema = list(HouseModel.objects.all()[:10])
    item_list = [
        {
            "@type": "ListItem",
            "position": idx + 1,
            "name": h.title,
            "url": f"{host}{h.get_absolute_url()}",
        }
        for idx, h in enumerate(houses_for_schema)
    ]

    faq_schema_main = [
        {
            "@type": "Question",
            "name": item["question"],
            "acceptedAnswer": {"@type": "Answer", "text": item["answer"]},
        }
        for item in faqs_display
    ]

    structured_data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "name": "Click Home",
                "url": canonical_url,
                "logo": logo_abs,
                "email": "info@click-home.co.il",
                "telephone": "+972-50-3439999",
            },
            {
                "@type": "LocalBusiness",
                "name": "Click Home",
                "url": canonical_url,
                "telephone": "+972-50-3439999",
                "email": "info@click-home.co.il",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "התרופה 6, אזור התעשיה",
                    "addressLocality": "נתניה",
                    "postalCode": "4250477",
                    "addressCountry": "IL",
                },
            },
            {"@type": "WebSite", "name": "Click Home", "url": canonical_url, "inLanguage": "he-IL"},
            {"@type": "FAQPage", "mainEntity": faq_schema_main},
            {
                "@type": "ItemList",
                "name": "דגמי בתים מובילים",
                "itemListElement": item_list,
            },
        ],
    }

    return render(
        request,
        "home.html",
        {
            "houses": houses,
            "faqs": faqs,
            "faqs_display": faqs_display,
            "house_types": house_types,
            "active_type_slug": type_slug,
            "featured_houses": featured_houses,
            "project_gallery_media": project_gallery_media,
            "hero_image_url": hero_image_url,
            "canonical_url": canonical_url,
            "structured_data_json": json.dumps(structured_data, ensure_ascii=False),
        },
    )


@require_POST
def lead_submit(request):
    cleaned, errors = _validate_lead_minimal(request.POST)
    source = (request.POST.get("source") or "site").strip()[:80]
    wants_json = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if errors:
        if wants_json:
            return JsonResponse({"ok": False, "errors": errors}, status=400)
        for msg in errors.values():
            messages.error(request, msg)
        frag = "#lead" if source == "final" else ""
        return redirect(reverse("home") + frag)

    try:
        _send_lead_email(cleaned, source_label=f"ליד ({source})")
        messages.success(
            request,
            "תודה! קיבלנו את הפרטים וניצור איתכם קשר בהקדם.",
        )
        if wants_json:
            return JsonResponse({"ok": True})
    except Exception:
        messages.error(
            request,
            "הפנייה התקבלה אך הייתה בעיה בשליחת המייל. ננסה ליצור קשר בהקדם.",
        )
        if wants_json:
            return JsonResponse({"ok": False, "error": "mail"}, status=500)

    return HttpResponseRedirect(reverse("home") + "?lead_ok=1#lead-success")

def about_page(request): return render(request, 'about.html')

def contact_page(request): 
    faqs = FAQ.objects.filter(is_visible=True).order_by('order')
    success = False
    if request.method == 'POST':
        cleaned_data, errors = _validate_lead_payload(request.POST)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
        else:
            try:
                _send_lead_email(cleaned_data, source_label="עמוד צור קשר")
                messages.success(request, "ההודעה נשלחה בהצלחה! נחזור אליך בהקדם.")
                success = True
            except Exception:
                messages.error(request, "הפנייה נשמרה אך הייתה בעיה בשליחה. ננסה ליצור קשר בהקדם.")
    return render(request, 'contact.html', {'faqs': faqs, 'success': success})


def tab_page(request):
    houses_qs = HouseModel.objects.prefetch_related("house_types", "media_files").all()
    all_models = sorted(get_tab_catalog(houses_qs), key=lambda item: ((item.get("area_m2") or 0), item["model_name"]))

    selected_category = (request.GET.get("category") or "all").strip()
    search_term = (request.GET.get("q") or "").strip()
    bedrooms = _to_int(request.GET.get("bedrooms")) or ""
    bathrooms = _to_int(request.GET.get("bathrooms")) or ""
    floors = _to_int(request.GET.get("floors")) or ""
    area_min = _to_int(request.GET.get("area_min")) if request.GET.get("area_min") else ""
    area_max = _to_int(request.GET.get("area_max")) if request.GET.get("area_max") else ""

    lead_success = False
    lead_form = {
        "full_name": "",
        "phone": "",
        "email": "",
        "interest_type": "",
        "message": "",
        "model_name": "",
    }
    if request.method == "POST":
        cleaned_data, errors = _validate_lead_payload(request.POST)
        lead_form.update(cleaned_data)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
        else:
            try:
                _send_lead_email(cleaned_data, source_label="קטלוג טאבלט")
                messages.success(request, "תודה! קיבלנו את הפרטים וניצור איתכם קשר בהקדם.")
                lead_success = True
                lead_form = {k: "" for k in lead_form}
            except Exception:
                messages.error(request, "הבקשה התקבלה אך הייתה תקלה רגעית בשליחה. ניצור קשר בהקדם.")

    canonical_url = request.build_absolute_uri(reverse("tab"))
    og_image = request.build_absolute_uri(all_models[0]["main_image"]) if all_models else ""

    structured_data = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "קטלוג דגמי Click Home",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": idx + 1,
                "name": model["model_name"],
                "url": f"{canonical_url}#{model['slug']}",
            }
            for idx, model in enumerate(all_models[:24])
        ],
    }

    public_models_for_json = [
        {key: value for key, value in model.items() if key != "internal_source_reference"}
        for model in all_models
    ]

    return render(request, "tab_tinder.html", {
        "all_models_json": json.dumps(public_models_for_json, ensure_ascii=False),
        "categories": TAB_CATEGORY_OPTIONS,
        "initial_filters": {
            "category": selected_category,
            "q": search_term,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "floors": floors,
            "area_min": area_min,
            "area_max": area_max,
        },
        "lead_form": lead_form,
        "lead_success": lead_success,
        "canonical_url": canonical_url,
        "og_image": og_image,
        "structured_data_json": json.dumps(structured_data, ensure_ascii=False),
        "catalog_count": len(all_models),
    })


def tab_icon_asset(request, icon_name):
    safe_key = (icon_name or "").strip().lower()
    if safe_key not in TAB_ICON_FILES:
        raise Http404("Icon not found")
    icon_path = Path(settings.BASE_DIR) / "tab" / TAB_ICON_FILES[safe_key]
    if not icon_path.exists():
        raise Http404("Icon file missing")
    return FileResponse(icon_path.open("rb"), content_type="image/jpeg")

def catalog_page(request):
    houses = HouseModel.objects.all()
    type_slug = request.GET.get('type', '').strip()
    if type_slug:
        houses = houses.filter(house_types__slug=type_slug).distinct()
    house_types = HouseType.objects.all()
    return render(request, 'catalog.html', {
        'houses': houses,
        'house_types': house_types,
        'active_type_slug': type_slug,
    })

@xframe_options_sameorigin
def house_detail(request, pk):
    house = get_object_or_404(HouseModel, pk=pk)
    related_houses = HouseModel.objects.filter(~Q(pk=pk))[:3]
    is_fav = False
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        is_fav = house in request.user.profile.favorites.all()
    return render(request, 'house_detail.html', {'house': house, 'related_houses': related_houses, 'is_fav': is_fav})

@login_required
def create_quote(request, pk):
    house = get_object_or_404(HouseModel, pk=pk)
    user = request.user
    
    new_quote = Quote.objects.create(
        user=user, 
        client_name=f"{user.first_name} {user.last_name}" if user.first_name else user.username,
        client_phone=user.profile.phone, 
        client_email=user.email,
        selected_house=house, 
        quantity=1, 
        final_price=house.price_estimate, 
        status='INTERESTED'
    )
    
    if request.method == 'POST':
        selected_ids = request.POST.getlist('upgrades')
        if selected_ids:
            upgrades_objs = HouseUpgrade.objects.filter(id__in=selected_ids)
            new_quote.selected_upgrades.set(upgrades_objs)
        else:
            default_upgrades = house.upgrades.filter(is_included=True)
            new_quote.selected_upgrades.set(default_upgrades)
    else:
        default_upgrades = house.upgrades.filter(is_included=True)
        new_quote.selected_upgrades.set(default_upgrades)
        
    new_quote.save()

    try:
        subject = f"לקוח מתעניין חדש: {new_quote.client_name}"
        message = f"לקוח חדש יצר הצעת מחיר. שם: {new_quote.client_name}, דגם: {house.title}"
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, ['info@click-home.co.il'], fail_silently=True)
    except: pass

    return redirect('quote_edit', pk=new_quote.pk)

@login_required
def quote_edit(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    house = quote.selected_house
    all_upgrades = house.upgrades.all()

    if request.method == 'POST':
        selected_ids = request.POST.getlist('upgrades')
        quote.selected_upgrades.set(HouseUpgrade.objects.filter(id__in=selected_ids))
        try:
            qty = int(request.POST.get('quantity', 1))
            quote.quantity = max(1, qty)
        except: pass
        
        base_price = house.price_estimate
        upgrades_price = sum(u.price for u in quote.selected_upgrades.all())
        quote.final_price = (base_price + upgrades_price) * quote.quantity
        quote.save()
        
        if 'request_callback' in request.POST:
            quote.has_callback_request = True 
            quote.save()
            try:
                subject = f"📞 בקשה לשיחה מנציג: {quote.client_name}"
                body = f"הלקוח {quote.client_name} ({quote.client_phone}) ביקש שיחה."
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, ['info@click-home.co.il'], fail_silently=True)
                messages.success(request, "בקשתך התקבלה! נציג יחזור אליך בהקדם.")
            except: messages.warning(request, "הבקשה נרשמה, אך הייתה בעיה בשליחת ההתראה.")
            return redirect('quote_edit', pk=quote.pk)

        elif 'send_email' in request.POST:
            quote.status = 'SENT'
            quote.save()
            email_obj = queue_email(quote, f"הצעת מחיר לדגם: {house.title}")
            # כאן לא שולחים מיד, רק יוצרים בתור. המודל מטפל או האדמין משחרר.
            messages.success(request, f"ההצעה נשלחה בהצלחה ל-{quote.client_email}")
            return redirect('quote_edit', pk=quote.pk)
            
        elif 'go_to_sign' in request.POST:
            return redirect('view_quote', quote_id=quote.id)

    return render(request, 'quote_edit.html', {
        'quote': quote, 
        'all_upgrades': all_upgrades
    })

def view_quote(request, quote_id):
    quote = get_object_or_404(Quote, id=quote_id)
    
    if request.method == 'POST':
        signature_data = request.POST.get('signature_data')
        if signature_data:
            try:
                format, imgstr = signature_data.split(';base64,') 
                ext = format.split('/')[-1] 
                file_name = f"signature_{quote.id}.{ext}"
                data = ContentFile(base64.b64decode(imgstr), name=file_name)
                quote.signature_image = data
                quote.status = 'SIGNED'
                quote.is_signed = True
                quote.updated_at = timezone.now()
                quote.save()
                messages.success(request, "ההצעה נחתמה בהצלחה!")
                return redirect('view_quote', quote_id=quote.id)
            except: messages.error(request, "אירעה שגיאה בשמירת החתימה.")

        elif 'request_callback' in request.POST:
            quote.has_callback_request = True
            quote.save()
            try:
                send_mail(f"בקשת שיחה (מהלינק): {quote.client_name}", "הלקוח ביקש שיחה.", settings.DEFAULT_FROM_EMAIL, ['info@click-home.co.il'], fail_silently=True)
                messages.success(request, "בקשתך התקבלה! נציג יחזור אליך בהקדם.")
            except: messages.error(request, "שגיאה בשליחת הבקשה.")
            return redirect('view_quote', quote_id=quote.id)

    return render(request, 'quote_web_view.html', {'quote': quote})

def save_signature(request, pk): pass 
def register(request):
    if request.method == 'POST':
        form = ClientRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else: form = ClientRegisterForm()
    return render(request, 'register.html', {'form': form})

@login_required
def toggle_favorite(request, pk):
    house = get_object_or_404(HouseModel, pk=pk)
    if house in request.user.profile.favorites.all():
        request.user.profile.favorites.remove(house)
    else:
        request.user.profile.favorites.add(house)
    return redirect('home')

@login_required
def profile_dashboard(request):
    user = request.user
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        profile = user.profile
        profile.phone = request.POST.get('phone', profile.phone)
        profile.address = request.POST.get('address', profile.address)
        profile.save()
        messages.success(request, 'הפרטים עודכנו בהצלחה')
        return redirect('profile')

    my_quotes = Quote.objects.filter(user=user).order_by('-created_at')
    favorites = user.profile.favorites.all()
    return render(request, 'profile.html', {'quotes': my_quotes, 'favorites': favorites})

@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request): return render(request, 'dashboard.html', {})

# --- English CIHIE landing (static marketing pages) ---
def en_landing_home(request):
    """Canonical English landing — V1 architectural layout."""
    return render(request, 'en/v1_architectural.html')


def zh_landing_home(request):
    """Simplified Chinese landing — same layout as /en/, zh-Hans copy."""
    return render(request, "zh/v1_architectural_zh.html")

def en_landing_compare(request):
    return render(request, 'en/compare.html')

def en_landing_v1(request):
    return render(request, 'en/v1_architectural.html')

def en_landing_v2(request):
    return render(request, 'en/v2_industrial.html')

def en_landing_v3(request):
    return render(request, 'en/v3_china.html')


def _build_contact_card_context(profile_slug):
    profile = CONTACT_CARD_PROFILES[profile_slug].copy()
    context = {**CONTACT_CARD_BASE, **profile}
    return context


def en_itzik_card(request):
    return render(request, "en/contact_card.html", _build_contact_card_context("itzik"))


def en_hagit_card(request):
    return render(request, "en/contact_card.html", _build_contact_card_context("hagit"))


def en_contact_card_redirect(request, profile_slug):
    slug = (profile_slug or "").lower()
    if slug in CONTACT_CARD_PROFILES:
        return redirect(f"/en/{slug}", permanent=True)
    raise Http404("Profile not found")


def _build_vcf_payload(profile_slug):
    profile = _build_contact_card_context(profile_slug)
    first_name, last_name = profile["name"].split(" ", 1)
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{last_name};{first_name};;;",
        f"FN:{profile['name']}",
        f"ORG:{profile['company']}",
        f"TITLE:{profile['title']}",
        f"TEL;TYPE=CELL:{profile['mobile_tel']}",
        f"TEL;TYPE=WORK,VOICE:{profile['phone_tel']}",
        f"URL:{profile['website']}",
        "END:VCARD",
    ]
    return "\r\n".join(lines) + "\r\n", profile


def _vcf_response(profile_slug):
    payload, profile = _build_vcf_payload(profile_slug)
    response = HttpResponse(payload, content_type="text/vcard; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{profile_slug}.vcf"'
    response["Cache-Control"] = "no-store"
    return response


def vcf_itzik(request):
    return _vcf_response("itzik")


def vcf_hagit(request):
    return _vcf_response("hagit")


def vcf_redirect(request, profile_slug):
    slug = (profile_slug or "").lower()
    if slug in CONTACT_CARD_PROFILES:
        return redirect(f"/api/vcf/{slug}", permanent=True)
    raise Http404("Profile not found")