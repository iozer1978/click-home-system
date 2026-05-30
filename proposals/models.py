from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
import uuid

STATUS_CHOICES = [
    ('DRAFT', _('טיוטה/נשלח ללקוח')),
    ('INTERESTED', _('לקוח מתעניין')), 
    ('SENT', _('נשלח ללקוח')),
    ('SIGNED', _('הוזמן וחתום')),
    ('DEPOSIT', _('שולם מקדמה')),
    ('PRODUCTION', _('בייצור')),
    ('SHIPPING', _('במשלוח')),
    ('COMPLETED', _('הושלם')),
    ('CANCELED', _('בוטל')),
]

class UsageType(models.Model):
    name = models.CharField(max_length=50, verbose_name="שם השימוש")
    def __str__(self): return self.name
    class Meta: verbose_name = "סוג שימוש"; verbose_name_plural = "סוגי שימוש"


class HouseType(models.Model):
    """סוג בית / קטגוריה לחיפוש (בתים מודולריים, בתי מכולות וכו')"""
    name = models.CharField(max_length=80, verbose_name="שם הסוג")
    order = models.IntegerField(default=0, verbose_name="סדר תצוגה")
    slug = models.SlugField(max_length=80, unique=True, allow_unicode=True, verbose_name="מזהה ל־URL")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "סוג בית"
        verbose_name_plural = "סוגי בתים"
        ordering = ['order', 'name']


class HouseMedia(models.Model):
    """מדיה של דגם — סדר התצוגה והמדיה הראשית לדף הדגם מוגדרים כאן."""
    MEDIA_TYPES = (("image", "תמונה"), ("video", "וידאו"))
    house = models.ForeignKey(
        "HouseModel", on_delete=models.CASCADE, related_name="media_files"
    )
    file = models.FileField(upload_to="house_media/", verbose_name="קובץ")
    media_type = models.CharField(
        max_length=10, choices=MEDIA_TYPES, default="image", verbose_name="סוג קובץ"
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="סדר בתצוגה",
        help_text="מספר נמוך יותר = מוצג ראשון בגלריה ובעמוד הבית.",
    )
    is_homepage_card = models.BooleanField(
        default=False,
        verbose_name="מדיה ראשית לדף הדגם",
        help_text="פריט אחד בלבד יכול להיות ראשי (תמונה או וידאו) עבור ה-Hero בדף הדגם.",
    )

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "מדיה לבית"
        verbose_name_plural = "מדיה לבית"

    def clean(self):
        super().clean()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_homepage_card:
            type(self).objects.filter(house_id=self.house_id).exclude(pk=self.pk).update(
                is_homepage_card=False
            )

    def __str__(self):
        return f"{self.house_id}: {self.file.name if self.file else '—'}"


class HouseModel(models.Model):
    SECTION_TITLE_CHOICES = [
        ("תיאור הדגם", "תיאור הדגם"),
        ("יתרונות הדגם", "יתרונות הדגם"),
        ("מאפיינים עיקריים", "מאפיינים עיקריים"),
        ("למה לבחור ב-APPLE?", "למה לבחור ב-APPLE?"),
        ("מפרט ויתרונות", "מפרט ויתרונות"),
        ("תכונות מרכזיות", "תכונות מרכזיות"),
    ]
    SHORT_DESCRIPTION_TEMPLATE_CHOICES = [
        ("", "בחירה ידנית"),
        ("בית מודולרי יוקרתי בעיצוב מודרני וחדשני.", "בית מודולרי יוקרתי בעיצוב מודרני וחדשני."),
        ("פתרון מגורים חכם, מהיר ואיכותי.", "פתרון מגורים חכם, מהיר ואיכותי."),
        ("מבנה מתקדם המתאים למגורים, אירוח ועסקים.", "מבנה מתקדם המתאים למגורים, אירוח ועסקים."),
        ("שילוב מושלם של עיצוב, נוחות ועמידות.", "שילוב מושלם של עיצוב, נוחות ועמידות."),
        ("בית מוכן להצבה עם גימור ברמה גבוהה.", "בית מוכן להצבה עם גימור ברמה גבוהה."),
    ]
    config_key = models.CharField(max_length=30, unique=True, blank=True, null=True, verbose_name="מזהה סנכרון (MODEL_01...)")
    title = models.CharField(max_length=100, verbose_name="שם הדגם")
    description = models.TextField(verbose_name="תיאור כללי (ראשי)")
    marketing_title = models.CharField(max_length=180, blank=True, verbose_name="כותרת שיווקית")
    hero_subtitle = models.CharField(max_length=255, blank=True, verbose_name="כותרת משנה לאזור הפתיחה")
    short_description_template = models.CharField(
        max_length=255,
        blank=True,
        choices=SHORT_DESCRIPTION_TEMPLATE_CHOICES,
        verbose_name="תיאור קצר (מתוך רשימה)",
    )
    short_description = models.CharField(max_length=255, blank=True, verbose_name="תיאור קצר שיווקי")
    full_description = models.TextField(blank=True, verbose_name="תיאור מלא שיווקי")
    description_section_title = models.CharField(
        max_length=80,
        blank=True,
        choices=SECTION_TITLE_CHOICES,
        verbose_name="כותרת מקטע תיאור",
    )
    highlights_section_title = models.CharField(
        max_length=80,
        blank=True,
        choices=SECTION_TITLE_CHOICES,
        verbose_name="כותרת מקטע יתרונות",
    )
    technical_section_title = models.CharField(max_length=80, blank=True, default="מפרט טכני", verbose_name="כותרת מקטע מפרט")
    extra_images_section_title = models.CharField(max_length=80, blank=True, default="תמונות נוספות", verbose_name="כותרת מקטע תמונות נוספות")
    usage_types = models.ManyToManyField(UsageType, verbose_name="סוגי שימוש מתאימים", blank=True)
    house_types = models.ManyToManyField(HouseType, verbose_name="סוגי בית", blank=True, related_name="houses")
    area_sqm = models.IntegerField(verbose_name="שטח במ\"ר", default=30)
    built_area_value = models.CharField(max_length=120, blank=True, default="מותאם לדגם", verbose_name="ערך שטח בנוי בפס הפיצ'רים")
    bedrooms_value = models.CharField(max_length=120, blank=True, default="מותאם לדגם", verbose_name="ערך חדרי שינה בפס הפיצ'רים")
    bathroom_value = models.CharField(max_length=120, blank=True, default="מותאם לדגם", verbose_name="ערך חדר רחצה בפס הפיצ'רים")
    living_room_value = models.CharField(max_length=120, blank=True, default="כלול בדגם", verbose_name="ערך סלון מרווח בפס הפיצ'רים")
    open_kitchen_value = models.CharField(max_length=120, blank=True, default="בהתאמה אישית", verbose_name="ערך מטבח פתוח בפס הפיצ'רים")
    porch_value = models.CharField(max_length=120, blank=True, default="אופציונלי", verbose_name="ערך מרפסת בפס הפיצ'רים")
    dimensions_text = models.TextField(blank=True, verbose_name="מידות")
    specs = models.TextField(verbose_name="מפרט טכני ומידות", blank=True)
    specifications = models.JSONField(default=dict, blank=True, verbose_name="מפרט מובנה (JSON)")
    internal_layout = models.TextField(verbose_name="חלוקה פנימית", blank=True)
    blueprint_image = models.ImageField(upload_to='blueprints/', verbose_name="תמונת שרטוט", blank=True, null=True)
    floor_plan_pdf = models.FileField(upload_to='blueprints/', verbose_name="קובץ שרטוט PDF", blank=True, null=True)
    hero_image = models.ImageField(upload_to='house_media/', verbose_name="תמונת Hero", blank=True, null=True)
    gallery_images = models.JSONField(default=list, blank=True, verbose_name="גלריה נוספת (URLs)")
    interior_images = models.JSONField(default=list, blank=True, verbose_name="גלריית פנים (URLs)")
    features = models.JSONField(default=list, blank=True, verbose_name="פיצ'רים / פס יתרונות")
    advantages = models.JSONField(default=list, blank=True, verbose_name="יתרונות הדגם")
    delivery_time = models.CharField(max_length=120, blank=True, verbose_name="זמן אספקה")
    warranty = models.CharField(max_length=120, blank=True, verbose_name="אחריות")
    construction_type = models.CharField(max_length=120, blank=True, verbose_name="סוג בנייה")
    contact_phone = models.CharField(max_length=30, blank=True, verbose_name="טלפון ליצירת קשר בדף הדגם")
    whatsapp_link = models.URLField(blank=True, verbose_name="קישור וואטסאפ בדף הדגם")
    related_models = models.ManyToManyField("self", symmetrical=False, blank=True, verbose_name="דגמים קשורים")
    price_estimate = models.IntegerField(verbose_name="מחיר מחירון", default=0)
    
    def __str__(self): return self.title

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("house_detail", kwargs={"pk": self.pk})

    def get_main_image(self):
        """תמונה לכרטיס בדף הבית: נבחרת ידנית; אחרת התמונה הראשונה לפי סדר."""
        images = self.media_files.filter(media_type="image")
        chosen = images.filter(is_homepage_card=True).first()
        if chosen:
            return chosen.file
        first_img = images.first()
        return first_img.file if first_img else None


class HouseTechnicalSpec(models.Model):
    PRESET_CHOICES = [
        ("structure_type", "סוג המבנה"),
        ("built_area", "שטח בנוי"),
        ("external_dimensions", "מידות חיצוניות"),
        ("rooms_total", "מספר חדרים"),
        ("bedrooms_total", "מספר חדרי שינה"),
        ("bathrooms_total", "מספר חדרי רחצה"),
        ("living_room", "סלון"),
        ("kitchen", "מטבח"),
        ("porch", "מרפסת"),
        ("galvanized_steel_frame", "שלד פלדה מגולוונת"),
        ("insulated_walls", "קירות מבודדים"),
        ("thermal_insulation", "בידוד תרמי"),
        ("acoustic_insulation", "בידוד אקוסטי"),
        ("aluminum_windows", "חלונות אלומיניום"),
        ("double_glazing", "זכוכית כפולה"),
        ("entry_door", "דלת כניסה"),
        ("interior_doors", "דלתות פנים"),
        ("flooring", "ריצוף"),
        ("exterior_cladding", "חיפוי חוץ"),
        ("interior_cladding", "חיפוי פנים"),
        ("insulated_roof", "גג מבודד"),
        ("electrical_system", "מערכת חשמל"),
        ("plumbing_system", "מערכת אינסטלציה"),
        ("ac_preparation", "הכנה למיזוג אוויר"),
        ("equipped_bathroom", "חדר רחצה מאובזר"),
        ("equipped_kitchen", "מטבח מאובזר"),
        ("water_sewage_preparation", "הכנה למים וביוב"),
        ("internet_preparation", "הכנה לאינטרנט / תקשורת"),
        ("interior_lighting", "תאורת פנים"),
        ("exterior_lighting", "תאורת חוץ"),
        ("full_furniture_option", "אפשרות לריהוט מלא"),
        ("customization_option", "אפשרות להתאמה אישית"),
        ("delivery_time", "זמן אספקה"),
        ("installation_time", "זמן התקנה"),
        ("transport_type", "סוג הובלה"),
        ("need_crane", "צורך במנוף"),
        ("need_foundation", "צורך בהכנת תשתית / יסודות"),
        ("custom", "טקסט מותאם אישית"),
    ]
    house = models.ForeignKey(HouseModel, on_delete=models.CASCADE, related_name="technical_specs", verbose_name="דגם")
    is_enabled = models.BooleanField(default=False, verbose_name="להציג באתר (V)")
    preset_key = models.CharField(max_length=60, choices=PRESET_CHOICES, default="custom", verbose_name="פריט מובנה")
    label = models.CharField(max_length=120, blank=True, verbose_name="כותרת מותאמת (לפריט מותאם)")
    value = models.CharField(max_length=255, blank=True, verbose_name="ערך")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="סדר תצוגה")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "מפרט טכני"
        verbose_name_plural = "מפרט טכני"

    def __str__(self):
        return f"{self.house.title} - {self.display_label()}"

    def display_label(self):
        if self.preset_key == "custom":
            return self.label.strip() if self.label else "פריט מותאם"
        return self.get_preset_key_display()


class HouseAdvantageItem(models.Model):
    PRESET_CHOICES = [
        ("fast_construction", "בנייה מהירה"),
        ("ready_to_place", "פתרון מגורים מוכן להצבה"),
        ("modern_luxury_design", "עיצוב מודרני ויוקרתי"),
        ("high_quality_materials", "איכות חומרים גבוהה"),
        ("advanced_insulation", "בידוד מתקדם לחיסכון באנרגיה"),
        ("low_maintenance", "תחזוקה נמוכה לאורך שנים"),
        ("fit_residential", "מתאים למגורים"),
        ("fit_guest_unit", "מתאים לצימר / יחידת אירוח"),
        ("fit_office", "מתאים למשרד"),
        ("fit_clinic", "מתאים לקליניקה"),
        ("fit_adu", "מתאים ליחידת דיור משלימה"),
        ("fit_rental", "מתאים להשכרה"),
        ("smart_space_usage", "ניצול חכם של החלל"),
        ("large_windows", "חלונות גדולים להכנסת אור טבעי"),
        ("luxury_look", "מראה יוקרתי ומזמין"),
        ("fast_installation", "התקנה מהירה באתר"),
        ("upgrade_option", "אפשרות לשדרוגים"),
        ("layout_change_option", "אפשרות לשינוי חלוקה פנימית"),
        ("weather_resistance", "עמידות גבוהה בתנאי מזג אוויר"),
        ("cost_effective", "פתרון חסכוני ביחס לבנייה רגילה"),
        ("factory_controlled", "ייצור מבוקר במפעל"),
        ("less_site_noise", "פחות לכלוך ורעש באתר"),
        ("fit_private_and_hospitality", "מתאים לקרקע פרטית / משק / מתחם אירוח"),
        ("easy_transport", "ניתן לשינוע והצבה מהירה"),
        ("fit_multi_usage", "מתאים למגוון שימושים פרטיים ועסקיים"),
        ("custom", "טקסט מותאם אישית"),
    ]
    house = models.ForeignKey(HouseModel, on_delete=models.CASCADE, related_name="advantage_items", verbose_name="דגם")
    is_enabled = models.BooleanField(default=False, verbose_name="להציג באתר (V)")
    preset_key = models.CharField(max_length=60, choices=PRESET_CHOICES, default="custom", verbose_name="יתרון מובנה")
    text = models.CharField(max_length=255, blank=True, verbose_name="טקסט מותאם (לפריט מותאם)")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="סדר תצוגה")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "יתרון / מאפיין"
        verbose_name_plural = "יתרונות / מאפיינים"

    def __str__(self):
        return f"{self.house.title} - {self.display_text()[:40]}"

    def display_text(self):
        if self.preset_key == "custom":
            return self.text.strip() if self.text else ""
        return self.get_preset_key_display()


class TabHouse(models.Model):
    CATEGORY_CHOICES = (
        ("single-family", "בתים פרטיים"),
        ("modular", "בתים מודולריים"),
        ("adu", "ADU"),
    )

    slug = models.SlugField(max_length=160, unique=True, verbose_name="Slug")
    model_name = models.CharField(max_length=180, verbose_name="שם הדגם")
    subtitle_he = models.CharField(max_length=255, blank=True, verbose_name="כותרת משנה")
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="single-family", verbose_name="קטגוריה ראשית")
    house_types = models.ManyToManyField(HouseType, blank=True, related_name="tab_houses", verbose_name="קטגוריות נוספות")

    bedrooms = models.PositiveIntegerField(default=0, verbose_name="חדרי שינה")
    bathrooms = models.PositiveIntegerField(default=0, verbose_name="חדרי רחצה")
    living_rooms = models.PositiveIntegerField(default=1, verbose_name="סלונים")
    kitchen_count = models.PositiveIntegerField(default=1, verbose_name="מטבחים")
    garages = models.PositiveIntegerField(default=0, verbose_name="חניות")
    floors = models.PositiveIntegerField(default=1, verbose_name="קומות")
    area_m2 = models.FloatField(default=0, verbose_name="שטח מ\"ר")
    length_m = models.FloatField(blank=True, null=True, verbose_name="אורך (מ')")
    width_m = models.FloatField(blank=True, null=True, verbose_name="רוחב (מ')")

    description_he = models.TextField(blank=True, verbose_name="תיאור מלא")
    features_he = models.TextField(
        blank=True,
        verbose_name="פיצ'רים (שורה לכל פיצ'ר)",
        help_text="כל שורה תוצג כיתרון נפרד בכרטיסים.",
    )
    inquiry_cta_label = models.CharField(max_length=80, default="אני רוצה פרטים", verbose_name="טקסט כפתור פנייה")
    is_published = models.BooleanField(default=True, verbose_name="מפורסם ב-/tab")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="סדר תצוגה")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "דגם /tab"
        verbose_name_plural = "דגמי /tab"

    def __str__(self):
        return self.model_name


class TabHouseImage(models.Model):
    IMAGE_TYPES = (
        ("hero", "תמונה ראשית"),
        ("gallery", "גלריה"),
        ("floorplan", "שרטוט"),
        ("lifestyle", "תמונת אווירה"),
    )
    tab_house = models.ForeignKey(TabHouse, on_delete=models.CASCADE, related_name="images", verbose_name="דגם")
    image = models.ImageField(upload_to="tab_houses/", verbose_name="תמונה")
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPES, default="gallery", verbose_name="סוג תמונה")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="סדר")

    class Meta:
        ordering = ["image_type", "sort_order", "id"]
        verbose_name = "תמונת דגם /tab"
        verbose_name_plural = "תמונות דגמי /tab"

    def __str__(self):
        return f"{self.tab_house.model_name} - {self.get_image_type_display()}"


class HouseUpgrade(models.Model):
    house = models.ForeignKey(HouseModel, on_delete=models.CASCADE, related_name='upgrades')
    name = models.CharField(max_length=100, verbose_name="שם השדרוג")
    price = models.IntegerField(verbose_name="מחיר תוספת")
    image = models.ImageField(upload_to='upgrades/', verbose_name="תמונת השדרוג (אופציונלי)", blank=True, null=True)
    is_included = models.BooleanField(default=False, verbose_name="מסומן כברירת מחדל?")
    def __str__(self): return self.name

class FAQ(models.Model):
    question = models.CharField(max_length=255, verbose_name="השאלה")
    answer = models.TextField(verbose_name="התשובה")
    order = models.IntegerField(default=0, verbose_name="סדר הופעה")
    is_visible = models.BooleanField(default=True, verbose_name="להציג באתר?")
    class Meta: verbose_name = "שאלה ותשובה"; verbose_name_plural = "שאלות ותשובות"; ordering = ['order']
    def __str__(self): return self.question

class Quote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='quotes', verbose_name="לקוח רשום (אופציונלי)")
    client_name = models.CharField(max_length=100, verbose_name="שם הלקוח", blank=True)
    client_phone = models.CharField(max_length=20, verbose_name="טלפון", blank=True)
    client_email = models.EmailField(verbose_name="מייל לקבלת ההצעה", blank=True)
    selected_house = models.ForeignKey(HouseModel, on_delete=models.SET_NULL, null=True, verbose_name="בחר דגם")
    selected_upgrades = models.ManyToManyField(HouseUpgrade, blank=True, verbose_name="שדרוגים שנבחרו")
    quantity = models.IntegerField(default=1, verbose_name="כמות יחידות")
    admin_notes = models.TextField(verbose_name="הערות להצעה (יופיעו במייל)", blank=True)
    final_price = models.IntegerField(verbose_name="מחיר סופי (סה\"כ)", default=0)
    deposit_percentage = models.IntegerField(default=30, verbose_name="אחוז מקדמה לתשלום")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', verbose_name="סטטוס הזמנה")
    has_callback_request = models.BooleanField(default=False, verbose_name="🔥 ממתין לשיחת נציג")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_signed = models.BooleanField(default=False)
    signature_image = models.ImageField(upload_to='signatures/', blank=True, null=True, verbose_name="קובץ חתימה")

    _original_status = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_status = self.status

    def get_deposit(self):
        return int(self.final_price * (self.deposit_percentage / 100))

    def save(self, *args, **kwargs):
        from .utils import queue_email
        is_new = self._state.adding
        status_changed = self.status != self._original_status

        # מילוי נתונים אוטומטי
        if self.user:
            if not self.client_name:
                self.client_name = f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
            if not self.client_email:
                self.client_email = self.user.email
            if not self.client_phone:
                try:
                    if hasattr(self.user, 'profile'):
                        self.client_phone = self.user.profile.phone
                except: pass

        super().save(*args, **kwargs)
        
        should_queue_email = status_changed or (is_new and self.status not in ['DRAFT', 'INTERESTED'])
        
        if should_queue_email and self.client_email:
            subject = ""
            if self.status == 'DEPOSIT': subject = f"אישור הזמנה וקבלה על מקדמה: {self.selected_house.title}"
            elif self.status == 'SIGNED': subject = f"הצעה חתומה: {self.client_name} - {self.selected_house.title}"
            elif self.status == 'PRODUCTION': subject = f"איזה כיף! ההזמנה שלך נכנסה לייצור: {self.selected_house.title}"
            elif self.status == 'SHIPPING': subject = f"עדכון משלוח: ההזמנה שלך בדרך לישראל 🚢"
            elif self.status == 'COMPLETED': subject = f"מזל טוב! הפרויקט הושלם בהצלחה 🏠"
            elif self.status == 'CANCELED': subject = f"עדכון לגבי הזמנתך - Click Home"
            elif self.status == 'SENT': subject = f"הצעת מחיר לדגם: {self.selected_house.title}"

            if subject:
                queue_email(self, subject)
        
        self._original_status = self.status

    def __str__(self): return f"{self.client_name} - {self.selected_house}"

class ScheduledEmail(models.Model):
    STATUSES = (('PENDING', 'ממתין לשליחה'), ('SENT', 'נשלח'), ('FAILED', 'נכשל'), ('CANCELLED', 'בוטל ידנית'))
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='emails')
    recipient = models.EmailField(verbose_name="נמען")
    subject = models.CharField(max_length=255, verbose_name="נושא")
    pdf_content = models.BinaryField(verbose_name="תוכן ה-PDF", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUSES, default='PENDING', verbose_name="סטטוס")
    error_message = models.TextField(blank=True, verbose_name="שגיאה")
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(verbose_name="זמן שליחה מתוכנן")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="נשלח בפועל ב")
    class Meta: verbose_name = "מייל בתור (להשהייה)"; verbose_name_plural = "מיילים בתור / יוצאים"; ordering = ['scheduled_for']
    def __str__(self): return f"מייל ל-{self.recipient} ({self.status})"

class EmailLog(models.Model):
    recipient = models.EmailField(verbose_name="נמען")
    subject = models.CharField(max_length=255, verbose_name="נושא")
    status = models.CharField(max_length=20, choices=[('SENT', 'נשלח'), ('FAILED', 'נכשל')], verbose_name="סטטוס")
    error_message = models.TextField(verbose_name="שגיאה (אם יש)", blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="זמן שליחה")
    class Meta: verbose_name = "יומן מייל (ישן)"; verbose_name_plural = "יומן מיילים (ישן)"; ordering = ['-timestamp']

class ClientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, verbose_name="טלפון", blank=True)
    # --- שדה חדש ---
    address = models.CharField(max_length=255, verbose_name="כתובת מגורים", blank=True)
    favorites = models.ManyToManyField(HouseModel, blank=True, related_name='favorited_by', verbose_name="רשימת מועדפים")
    def __str__(self): return f"פרופיל של {self.user.username}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created: ClientProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try: instance.profile.save()
    except: ClientProfile.objects.create(user=instance)


class SupplierSubmission(models.Model):
    STATUS_CHOICES = [
        ("new", "New"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("need_more_info", "Need More Info"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    companyName = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    contactName = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    productType = models.CharField(max_length=120, blank=True)
    answers = models.JSONField(default=dict, blank=True)
    files = models.JSONField(default=dict, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    riskLevel = models.CharField(max_length=120, default="Not recommended")
    scoreBreakdown = models.JSONField(default=dict, blank=True)
    criticalFlags = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    adminNotes = models.TextField(blank=True)
    language = models.CharField(max_length=10, default="en")
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Supplier Submission"
        verbose_name_plural = "Supplier Submissions"
        ordering = ["-createdAt"]

    def __str__(self):
        return f"{self.companyName} ({self.score})"