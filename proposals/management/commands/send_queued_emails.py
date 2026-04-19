from django.core.management.base import BaseCommand
from django.utils import timezone
from proposals.models import ScheduledEmail
from proposals.utils import send_email_from_queue
import time

class Command(BaseCommand):
    help = 'רץ למשך 59 דקות ובודק כל דקה אם יש מיילים לשליחה'

    def handle(self, *args, **options):
        self.stdout.write(f"Starting email scheduler at {timezone.now()}...")
        
        # הסקריפט ירוץ למשך 59 דקות ואז יעצור (כדי שהמשימה השעתית תפעיל אותו מחדש)
        end_time = time.time() + (59 * 60) 

        while time.time() < end_time:
            # 1. חיפוש מיילים שסטטוס שלהם "ממתין" וזמן השליחה שלהם עבר
            pending_emails = ScheduledEmail.objects.filter(
                status='PENDING',
                scheduled_for__lte=timezone.now()
            )
            
            # אם מצאנו מיילים, נדפיס הודעה
            if pending_emails.exists():
                self.stdout.write(f"Found {pending_emails.count()} emails to send.")
                
            for email in pending_emails:
                try:
                    self.stdout.write(f"Sending email ID {email.id} to {email.recipient}...")
                    send_email_from_queue(email.id)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error sending email {email.id}: {e}"))
            
            # 2. המתנה של 60 שניות עד הבדיקה הבאה
            time.sleep(60)
            
        self.stdout.write("Stopping scheduler (waiting for restart).")