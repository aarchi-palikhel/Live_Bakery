from django.core.management.base import BaseCommand
import os

class Command(BaseCommand):
    help = 'Switch email backend between SMTP and console for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            'backend',
            choices=['smtp', 'console', 'file'],
            help='Email backend to switch to'
        )

    def handle(self, *args, **options):
        backend = options['backend']
        env_file = '.env'
        
        if not os.path.exists(env_file):
            self.stdout.write(self.style.ERROR("❌ .env file not found"))
            return
        
        # Read current .env file
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # Update EMAIL_BACKEND line
        updated_lines = []
        backend_found = False
        
        backend_configs = {
            'smtp': 'django.core.mail.backends.smtp.EmailBackend',
            'console': 'django.core.mail.backends.console.EmailBackend',
            'file': 'django.core.mail.backends.filebased.EmailBackend'
        }
        
        for line in lines:
            if line.startswith('EMAIL_BACKEND='):
                updated_lines.append(f'EMAIL_BACKEND={backend_configs[backend]}\n')
                backend_found = True
                self.stdout.write(f"✓ Updated EMAIL_BACKEND to {backend}")
            else:
                updated_lines.append(line)
        
        if not backend_found:
            # Add EMAIL_BACKEND if not found
            updated_lines.append(f'\nEMAIL_BACKEND={backend_configs[backend]}\n')
            self.stdout.write(f"✓ Added EMAIL_BACKEND={backend}")
        
        # Write updated .env file
        with open(env_file, 'w') as f:
            f.writelines(updated_lines)
        
        self.stdout.write(self.style.SUCCESS(f"✅ Email backend switched to: {backend}"))
        
        if backend == 'console':
            self.stdout.write("\n📧 Console Backend Active:")
            self.stdout.write("   - Emails will be printed to terminal/console")
            self.stdout.write("   - No actual emails will be sent")
            self.stdout.write("   - Perfect for testing email content")
            self.stdout.write("   - Restart Django server to apply changes")
            
        elif backend == 'file':
            self.stdout.write("\n📁 File Backend Active:")
            self.stdout.write("   - Emails will be saved as files")
            self.stdout.write("   - Check /tmp/app-messages directory")
            self.stdout.write("   - No actual emails will be sent")
            self.stdout.write("   - Restart Django server to apply changes")
            
        elif backend == 'smtp':
            self.stdout.write("\n📨 SMTP Backend Active:")
            self.stdout.write("   - Emails will be sent via SMTP")
            self.stdout.write("   - Using Gmail configuration")
            self.stdout.write("   - Check recipient's inbox and spam folder")
            self.stdout.write("   - Restart Django server to apply changes")
        
        self.stdout.write(f"\n🔄 Next steps:")
        self.stdout.write("1. Restart your Django development server")
        self.stdout.write("2. Login as a customer with email")
        self.stdout.write("3. Check the appropriate location for email output")
        
        if backend == 'console':
            self.stdout.write("4. Look for email content in your terminal")
        elif backend == 'smtp':
            self.stdout.write("4. Check your email inbox and spam folder")