from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import HouseModel, HouseMedia, Quote, HouseUpgrade, UsageType, HouseType, ClientProfile, FAQ, EmailLog, ScheduledEmail
from .utils import queue_email, send_email_from_queue

admin.site.site_header = "Click Home Admin V2.0"

class HouseMediaInline(admin.TabularInline):
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
                '<video src="{}" muted playsinline style="max-height:72px;max-width:100px;'
                'object-fit:cover;border-radius:4px;vertical-align:middle;"></video>',
                url,
            )
        return format_html(
            '<img src="{}" alt="" style="max-height:72px;max-width:100px;object-fit:cover;'
            'border-radius:4px;vertical-align:middle;" />',
            url,
        )

class HouseUpgradeInline(admin.TabularInline):
    model = HouseUpgrade
    extra = 1

@admin.register(HouseModel)
class HouseAdmin(admin.ModelAdmin):
    list_display = ('config_key', 'title', 'get_house_types', 'get_usages', 'area_sqm', 'price_estimate')
    list_filter = ('house_types',)
    search_fields = ('title', 'config_key')
    inlines = [HouseMediaInline, HouseUpgradeInline]
    filter_horizontal = ('house_types', 'usage_types')
    def get_usages(self, obj): return ", ".join([u.name for u in obj.usage_types.all()])
    def get_house_types(self, obj): return ", ".join([t.name for t in obj.house_types.all()])
    get_house_types.short_description = "סוגי בית"

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

admin.site.register(UsageType)
admin.site.register(HouseType)
admin.site.register(FAQ)
admin.site.register(EmailLog)