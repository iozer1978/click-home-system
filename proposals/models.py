from django.core.exceptions import ValidationError
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
    """מדיה של דגם — סדר התצוגה ותמונת הכרטיס בדף הבית מוגדרים כאן."""
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
        verbose_name="תמונת כרטיס בדף הבית",
        help_text="רק תמונה אחת לכל בית — זו שתופיע ברשימת הדגמים בדף הראשי.",
    )

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "מדיה לבית"
        verbose_name_plural = "מדיה לבית"

    def clean(self):
        super().clean()
        if self.is_homepage_card and self.media_type != "image":
            raise ValidationError(
                {"is_homepage_card": "תמונת כרטיס לדף הבית זמינה רק לקבצי תמונה, לא לווידאו."}
            )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_homepage_card:
            type(self).objects.filter(house_id=self.house_id).exclude(pk=self.pk).update(
                is_homepage_card=False
            )

    def __str__(self):
        return f"{self.house_id}: {self.file.name if self.file else '—'}"


class HouseModel(models.Model):
    config_key = models.CharField(max_length=30, unique=True, blank=True, null=True, verbose_name="מזהה סנכרון (MODEL_01...)")
    title = models.CharField(max_length=100, verbose_name="שם הדגם")
    description = models.TextField(verbose_name="תיאור כללי (ראשי)")
    usage_types = models.ManyToManyField(UsageType, verbose_name="סוגי שימוש מתאימים", blank=True)
    house_types = models.ManyToManyField(HouseType, verbose_name="סוגי בית", blank=True, related_name="houses")
    area_sqm = models.IntegerField(verbose_name="שטח במ\"ר", default=30)
    specs = models.TextField(verbose_name="מפרט טכני ומידות", blank=True)
    internal_layout = models.TextField(verbose_name="חלוקה פנימית", blank=True)
    blueprint_image = models.ImageField(upload_to='blueprints/', verbose_name="תמונת שרטוט", blank=True, null=True)
    price_estimate = models.IntegerField(verbose_name="מחיר מחירון", default=0)
    
    def __str__(self): return self.title

    def get_main_image(self):
        """תמונה לכרטיס בדף הבית: נבחרת ידנית; אחרת התמונה הראשונה לפי סדר."""
        images = self.media_files.filter(media_type="image")
        chosen = images.filter(is_homepage_card=True).first()
        if chosen:
            return chosen.file
        first_img = images.first()
        return first_img.file if first_img else None


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