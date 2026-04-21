from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from datetime import timedelta

def queue_email(quote, subject, template_name=None):
    from .models import ScheduledEmail
    email_obj = ScheduledEmail.objects.create(
        quote=quote,
        recipient=quote.client_email,
        subject=subject,
        pdf_content=None, 
        scheduled_for=timezone.now() + timedelta(minutes=2),
        status='PENDING'
    )
    return email_obj

def send_email_from_queue(scheduled_email_id):
    from .models import ScheduledEmail
    try:
        email_obj = ScheduledEmail.objects.get(id=scheduled_email_id)
        domain = "http://127.0.0.1:8001"
        quote_url = f"{domain}/quote/web/{email_obj.quote.id}/"
        quote = email_obj.quote

        # --- הגדרת תוכן המייל לפי סטטוס ---
        if quote.status == 'DEPOSIT':
            main_title = "אישור הזמנה וקבלה על מקדמה"
            button_text = "לחץ כאן לצפייה באישור ההזמנה"
            body_text = "אנו מודים לך על תשלום המקדמה. ההזמנה אושרה והועברה לייצור."
            
        elif quote.status == 'SIGNED':
            main_title = "הצעה חתומה התקבלה"
            button_text = "לחץ כאן לראות את הצעת המחיר החתומה"
            body_text = "קיבלנו את חתימתך בהצלחה. נציג מטעמנו ייצור קשר להמשך תהליך."
            
        # --- סטטוסים חדשים ---
        elif quote.status == 'PRODUCTION':
            main_title = "ההזמנה בייצור! 🔨"
            button_text = "לחץ כאן לצפייה בסטטוס ההזמנה"
            body_text = "אנחנו שמחים לבשר שההזמנה שלך נכנסה לייצור במפעל. אנחנו נמשיך לעדכן אותך בתהליך."
            
        elif quote.status == 'SHIPPING':
            main_title = "ההזמנה בדרך! 🚢"
            button_text = "לחץ כאן לצפייה בסטטוס ההזמנה"
            body_text = "אנחנו שמחים לבשר שההזמנה שלך בדרך לישראל. זה הזמן להתחיל להתרגש!"
            
        elif quote.status == 'COMPLETED':
            main_title = "הפרויקט הושלם! 🏠"
            button_text = "לחץ כאן לצפייה בסיכום ההזמנה"
            body_text = "אנחנו שמחים וגאים לבשר שהפרויקט הושלם בהצלחה. שמחנו לשרת אותך ונשמח לראות אותך בפרויקט הבא."
            
        elif quote.status == 'CANCELED':
            main_title = "הזמנה בוטלה"
            button_text = "לחץ כאן לצפייה בפרטי ההזמנה"
            body_text = "אנחנו מצטערים ומעדכנים אותך שהזמנתך בוטלה. נשמח לעמוד לשירותך בעתיד."
            
        else:
            main_title = f"הצעת מחיר לדגם {quote.selected_house.title}"
            button_text = "לחץ כאן לצפייה בהצעת המחיר שלך"
            body_text = "שמחים להגיש לך את הצעת המחיר המבוקשת."

        # בניית ה-HTML
        html_body = f"""
        <div style="direction: rtl; text-align: right; font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 20px;">
            <div style="background: white; padding: 20px; border-radius: 8px; border-top: 5px solid #C0A062;">
                <h2 style="color: #333;">שלום {quote.client_name},</h2>
                <h3 style="color: #C0A062;">{main_title}</h3>
                <p style="font-size: 16px; line-height: 1.5;">{body_text}</p>
                <br>
                <a href="{quote_url}" style="background-color: #C0A062; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                    {button_text}
                </a>
                <br><br>
                <p style="font-size: 12px; color: #777;">בברכה,<br>צוות Click Home</p>
            </div>
        </div>
        """

        email = EmailMultiAlternatives(
            subject=email_obj.subject,
            body=f"לצפייה במסמך: {quote_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email_obj.recipient],
            bcc=['info@click-home.co.il']
        )
        email.attach_alternative(html_body, "text/html")
        email.send()
        
        email_obj.status = 'SENT'
        email_obj.sent_at = timezone.now()
        email_obj.save()
        
        return True, "המייל נשלח בהצלחה!"

    except Exception as e:
        if 'email_obj' in locals():
            email_obj.status = 'FAILED'
            email_obj.error_message = str(e)
            email_obj.save()
        return False, str(e)