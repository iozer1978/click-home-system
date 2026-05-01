from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.management import call_command
from django.conf import settings
from pathlib import Path
import runpy
from .models import (
    HouseModel,
    HouseMedia,
    Quote,
    HouseUpgrade,
    UsageType,
    HouseType,
    ClientProfile,
    FAQ,
    EmailLog,
    ScheduledEmail,
    SupplierSubmission,
)
from .utils import queue_email, send_email_from_queue
from .models import TabHouse, TabHouseImage

admin.site.site_header = "Click Home Admin"
admin.site.site_title = "Click Home"
admin.site.index_title = "ניהול אתר"

class HouseMediaStackedInline(admin.StackedInline):
    model = HouseMedia
    extra = 1
    fields = (
        "thumbnail_preview",
        "file",
        "media_type",
        "sort_order",
        "is_homepage_card",
    )
    readonly_fields = ("thumbnail_preview",)
    ordering = ("sort_order", "id")
    @admin.display(description="תצוגה")
    def thumbnail_preview(self, obj):
        if not obj.file:
            return "—"
        try:
            url = obj.file.url
        except Exception:
            return "—"
        if obj.media_type == "video":
            return format_html(
                '<div class="house-media-thumb-lg">'
                '<video src="{}" muted playsinline></video></div>',
                url,
            )
        return format_html(
            '<div class="house-media-thumb-lg"><img src="{}" alt="" /></div>',
            url,
        )

class HouseUpgradeInline(admin.TabularInline):
    model = HouseUpgrade
    extra = 1


class TabHouseImageInline(admin.TabularInline):
    model = TabHouseImage
    extra = 1
    fields = ("preview", "image", "image_type", "sort_order")
    readonly_fields = ("preview",)
    ordering = ("image_type", "sort_order", "id")

    @admin.display(description="תצוגה")
    def preview(self, obj):
        if not obj.image:
            return "—"
        return format_html('<img src="{}" style="height:60px;border-radius:8px;border:1px solid #ddd;" />', obj.image.url)


@admin.register(HouseModel)
class HouseAdmin(admin.ModelAdmin):
    save_on_top = True
    view_on_site = True
    change_form_template = "admin/proposals/housemodel/change_form.html"
    list_display = (
        "title",
        "config_key",
        "get_house_types",
        "get_usages",
        "area_sqm",
        "price_estimate",
    )
    list_filter = ("house_types", "usage_types")
    search_fields = ("title", "config_key", "description")
    ordering = ("title",)
    inlines = [HouseMediaStackedInline, HouseUpgradeInline]
    filter_horizontal = ("house_types", "usage_types")
    fieldsets = (
        (
            "פרטים כלליים",
            {
                "fields": ("title", "config_key"),
            },
        ),
        (
            "תיאור ושיוך",
            {
                "fields": ("description", "house_types", "usage_types"),
            },
        ),
        (
            "מחיר ושטח",
            {
                "fields": ("area_sqm", "price_estimate"),
            },
        ),
        (
            "תוכן טכני",
            {
                "classes": ("wide",),
                "fields": ("specs", "internal_layout"),
            },
        ),
        (
            "שרטוט",
            {
                "fields": ("blueprint_image",),
            },
        ),
    )

    def get_usages(self, obj):
        return ", ".join([u.name for u in obj.usage_types.all()])

    def get_house_types(self, obj):
        return ", ".join([t.name for t in obj.house_types.all()])

    get_house_types.short_description = "סוגי בית"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj is not None:
            extra_context["house_public_url"] = request.build_absolute_uri(
                reverse("house_detail", args=[obj.pk])
            )
        return super().change_view(request, object_id, form_url, extra_context=extra_context)


@admin.register(TabHouse)
class TabHouseAdmin(admin.ModelAdmin):
    list_display = ("model_name", "category", "bedrooms", "bathrooms", "floors", "area_m2", "is_published", "sort_order")
    list_filter = ("category", "is_published", "house_types")
    search_fields = ("model_name", "slug", "description_he")
    ordering = ("sort_order", "model_name")
    filter_horizontal = ("house_types",)
    inlines = [TabHouseImageInline]
    prepopulated_fields = {"slug": ("model_name",)}
    change_list_template = "admin/proposals/tabhouse/change_list.html"
    fieldsets = (
        ("פרטים כלליים", {"fields": ("model_name", "slug", "subtitle_he", "category", "house_types", "is_published", "sort_order")}),
        ("מידע מהיר", {"fields": ("bedrooms", "bathrooms", "living_rooms", "kitchen_count", "garages", "floors", "area_m2", "length_m", "width_m")}),
        ("תוכן ותצוגה", {"fields": ("description_he", "features_he", "inquiry_cta_label")}),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "refresh-from-source/",
                self.admin_site.admin_view(self.refresh_from_source_view),
                name="tabhouse-refresh-from-source",
            )
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["refresh_from_source_url"] = reverse("admin:tabhouse-refresh-from-source")
        return super().changelist_view(request, extra_context=extra_context)

    def refresh_from_source_view(self, request):
        script_path = Path(settings.BASE_DIR) / "scripts" / "import_home_models.py"
        try:
            runpy.run_path(str(script_path), run_name="__main__")
            call_command("sync_tab_houses_from_json")
            self.message_user(request, "בוצע רענון מלא מהמקור וסנכרון לאדמין.", messages.SUCCESS)
        except Exception as exc:
            self.message_user(request, f"שגיאה ברענון מהמקור: {exc}", messages.ERROR)
        return HttpResponseRedirect("../")


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ('get_short_id', 'client_name', 'client_email', 'selected_house', 'status', 'deposit_percentage', 'has_callback_request', 'created_at')
    list_filter = ('has_callback_request', 'status', 'created_at')
    search_fields = ('client_name', 'client_email', 'id')
    readonly_fields = ('id', 'created_at', 'updated_at')
    filter_horizontal = ('selected_upgrades',)
    
    actions = ['send_quote_email_action']
    
    fields = ('user', 'client_name', 'client_phone', 'client_email', 'selected_house', 'quantity', 'selected_upgrades', 'deposit_percentage', 'final_price', 'status', 'has_callback_request', 'admin_notes', 'signature_image', 'id', 'created_at')

    def get_short_id(self, obj): return str(obj.id)[:8]
    get_short_id.short_description = "מס' הזמנה"

    def send_quote_email_action(self, request, queryset):
        sent_count = 0
        for quote in queryset:
            if quote.client_email:
                subject = f"הצעת מחיר / עדכון הזמנה: {quote.selected_house.title}"
                email_obj = queue_email(quote, subject)
                success, msg = send_email_from_queue(email_obj.id)
                if success:
                    sent_count += 1
        
        if sent_count > 0:
            self.message_user(request, f"נשלחו {sent_count} מיילים בהצלחה!", messages.SUCCESS)
        else:
            self.message_user(request, "לא נשלחו מיילים (אולי חסר מייל ללקוח?)", messages.WARNING)
            
    send_quote_email_action.short_description = "📧 שלח מייל הצעת מחיר/עדכון ללקוחות שנבחרו"

@admin.register(ScheduledEmail)
class ScheduledEmailAdmin(admin.ModelAdmin):
    list_display = ('subject', 'get_client', 'get_order_num', 'get_quote_status', 'scheduled_for', 'status_colored', 'send_now_button')
    list_filter = ('status', 'scheduled_for')
    actions = ['cancel_emails']
    readonly_fields = ('created_at', 'sent_at', 'pdf_preview')
    change_list_template = 'admin/change_list.html'
    ordering = ['-scheduled_for']

    def get_client(self, obj):
        return obj.quote.client_name if obj.quote else "-"
    get_client.short_description = "שם הלקוח"

    def get_order_num(self, obj):
        return str(obj.quote.id)[:8] if obj.quote else "-"
    get_order_num.short_description = "מס' הזמנה"

    def get_quote_status(self, obj):
        return obj.quote.get_status_display() if obj.quote else "-"
    get_quote_status.short_description = "סטטוס הזמנה"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [path('send-now/<int:email_id>/', self.admin_site.admin_view(self.send_email_view), name='send-email-now')]
        return custom_urls + urls

    def send_email_view(self, request, email_id):
        success, message = send_email_from_queue(email_id)
        if success: self.message_user(request, message, messages.SUCCESS)
        else: self.message_user(request, f"שגיאה בשליחה: {message}", messages.ERROR)
        return HttpResponseRedirect("../..")

    def status_colored(self, obj):
        colors = {'PENDING': 'orange', 'SENT': 'green', 'FAILED': 'red', 'CANCELLED': 'gray'}
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', colors.get(obj.status, "black"), obj.get_status_display())
    status_colored.short_description = "סטטוס מייל"

    # --- התיקון: הכפתור מופיע תמיד ---
    def send_now_button(self, obj):
        url = reverse('admin:send-email-now', args=[obj.id])
        
        if obj.status == 'SENT':
            label = "שלח שוב"
            bg_color = "#17a2b8" # כחול
        elif obj.status == 'PENDING':
            label = "שחרר ושגר כעת"
            bg_color = "#28a745" # ירוק
        else:
            label = "נסה לשלוח"
            bg_color = "#6c757d" # אפור

        return format_html(
            '<a class="button" href="{}" style="background-color: {}; color: white; padding: 5px 10px; border-radius: 4px; white-space: nowrap;">{}</a>',
            url, bg_color, label
        )
    send_now_button.short_description = "פעולות"

    def cancel_emails(self, request, queryset): queryset.update(status='CANCELLED')
    cancel_emails.short_description = "בטל שליחה למיילים שנבחרו"
    
    def pdf_preview(self, obj): return "אין קובץ (Web View Link Only)"

@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_email', 'phone')
    def get_email(self, obj): return obj.user.email


@admin.register(SupplierSubmission)
class SupplierSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "companyName",
        "country",
        "contactName",
        "email",
        "productType",
        "score",
        "riskLevel",
        "status",
        "createdAt",
    )
    list_filter = ("riskLevel", "status", "country", "productType", "createdAt")
    search_fields = ("companyName", "contactName", "email")
    readonly_fields = ("id", "createdAt", "updatedAt")
    fields = (
        "id",
        "companyName",
        "country",
        "contactName",
        "email",
        "phone",
        "website",
        "productType",
        "score",
        "riskLevel",
        "scoreBreakdown",
        "criticalFlags",
        "status",
        "adminNotes",
        "answers",
        "files",
        "language",
        "createdAt",
        "updatedAt",
    )

admin.site.register(UsageType)
admin.site.register(HouseType)
admin.site.register(FAQ)
admin.site.register(EmailLog)