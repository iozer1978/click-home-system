from django.urls import path, include
from . import views 

urlpatterns = [
    # English landing (www.click-home.co.il/en)
    path('en/', views.en_landing_home, name='en_landing'),
    path('en/compare/', views.en_landing_compare, name='en_landing_compare'),
    path('en/v1/', views.en_landing_v1, name='en_landing_v1'),
    path('en/v2/', views.en_landing_v2, name='en_landing_v2'),
    path('en/v3/', views.en_landing_v3, name='en_landing_v3'),

    # דפים ראשיים
    path('', views.home_page, name='home'),
    path('about/', views.about_page, name='about'),
    path('contact/', views.contact_page, name='contact'),
    path('models/', views.catalog_page, name='catalog'),
    path('tab/', views.tab_page, name='tab'),
    path('TAB/', views.tab_page, name='tab_upper'),
    path('register/', views.register, name='register'),
    
    # דפי מוצר
    path('house/<int:pk>/', views.house_detail, name='house_detail'),
    path('house/<int:pk>/create_quote/', views.create_quote, name='create_quote'),
    path('house/<int:pk>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    
    # --- שלב העריכה (הנתיב החדש) ---
    path('quote/edit/<uuid:pk>/', views.quote_edit, name='quote_edit'),

    # --- הלינק ללקוח (צפייה וחתימה) ---
    path('quote/web/<uuid:quote_id>/', views.view_quote, name='view_quote'),

    # ניהול הצעות (פנימי) - מחקנו את השורה של quote_detail שגרמה לשגיאה
    path('quote/<uuid:pk>/save_signature/', views.save_signature, name='save_signature'),
    
    # אזור אישי וניהול
    path('profile/', views.profile_dashboard, name='profile'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
]