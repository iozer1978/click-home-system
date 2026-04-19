from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.files.base import ContentFile
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q, Count, Sum
from django.contrib import messages
from django.utils import timezone
import base64
from .models import Quote, HouseModel, HouseUpgrade, UsageType, HouseType, FAQ
from .forms import ClientRegisterForm
from .utils import queue_email, send_email_from_queue

def home_page(request):
    houses = HouseModel.objects.all()
    type_slug = request.GET.get('type', '').strip()
    if type_slug:
        houses = houses.filter(house_types__slug=type_slug).distinct()
    faqs = FAQ.objects.filter(is_visible=True).order_by('order')
    house_types = HouseType.objects.all()
    return render(request, 'home.html', {
        'houses': houses,
        'faqs': faqs,
        'house_types': house_types,
        'active_type_slug': type_slug,
    })

def about_page(request): return render(request, 'about.html')

def contact_page(request): 
    faqs = FAQ.objects.filter(is_visible=True).order_by('order')
    success = False
    if request.method == 'POST':
        # TODO: חיבור לשליחת מייל או שמירת פנייה
        messages.success(request, "ההודעה נשלחה בהצלחה! נחזור אליך בהקדם.")
        success = True
    return render(request, 'contact.html', {'faqs': faqs, 'success': success})

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

def en_landing_compare(request):
    return render(request, 'en/compare.html')

def en_landing_v1(request):
    return render(request, 'en/v1_architectural.html')

def en_landing_v2(request):
    return render(request, 'en/v2_industrial.html')

def en_landing_v3(request):
    return render(request, 'en/v3_china.html')