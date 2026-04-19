from django import template
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site

register = template.Library()


@register.simple_tag(takes_context=True)
def safe_provider_login_url(context, provider_id):
    """מחזיר קישור התחברות ל־provider אם הוגדרה Social App (לאתר הנוכחי או כל אתר)."""
    request = context.get("request")
    if not request:
        return ""
    try:
        from allauth.socialaccount.models import SocialApp
        site = get_current_site(request)
        # קודם: אפליקציה שמשויכת לאתר הנוכחי
        app = SocialApp.objects.filter(provider=provider_id, sites=site).first()
        if not app:
            # fallback: אפליקציה ל־provider בלי site או עם site שמתאים
            app = SocialApp.objects.filter(provider=provider_id).first()
            if app and app.sites.exists() and site not in app.sites.all():
                app = None  # יש sites אבל האתר הנוכחי לא ברשימה
        if app:
            return reverse("socialaccount_login", kwargs={"provider_id": provider_id})
    except Exception:
        pass
    return ""
