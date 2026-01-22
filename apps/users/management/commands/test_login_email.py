from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.core.email_utils import send_template_email
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Test login notification email'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email address to send test to')

    def handle(self, *args, **options):
        email = options['email']
        
        # Create mock context for testing
        context = {
            'customer_name': 'Test User',
            'login_time': timezone.now(),
            'ip_address': '127.0.0.1',
            'user_agent': 'Test Browser',
            'bakery_name': 'Live Bakery',
        }
        
        self.stdout.write(f'Sending test login notification email to {email}...')
        
        success = send_template_email(
            to_email=email,
            subject="Login Notification - Live Bakery (Test)",
            template_name='emails/login_notification',
            context=context,
            fail_silently=False
        )
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Test email sent successfully to {email}')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'✗ Failed to send test email to {email}')
            )