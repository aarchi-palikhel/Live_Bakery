from django.core.management.base import BaseCommand
from core.email_utils import test_email_configuration


class Command(BaseCommand):
    help = 'Test email configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            help='Email address to send test email to',
            required=True
        )

    def handle(self, *args, **options):
        to_email = options['to']
        
        try:
            success = test_email_configuration(to_email)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'Test email sent successfully to {to_email}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed to send test email to {to_email}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to send email: {e}')
            )
            self.stdout.write(
                self.style.WARNING('Please check your email configuration in .env file')
            )