from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create demo users for testing role-based login'

    def handle(self, *args, **options):
        # Create demo customer
        try:
            customer, created = User.objects.get_or_create(
                username='democustomer',
                defaults={
                    'email': 'customer@demo.com',
                    'first_name': 'Demo',
                    'last_name': 'Customer',
                    'user_type': 'customer',
                    'delivery_address': '123 Demo Street, Demo City'
                }
            )
            if created:
                customer.set_password('demo123')
                customer.save()
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created demo customer: {customer.username} ({customer.email})')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Demo customer already exists: {customer.username}')
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating demo customer: {e}'))

        # Create demo staff
        try:
            staff, created = User.objects.get_or_create(
                username='demostaff',
                defaults={
                    'email': 'staff@demo.com',
                    'first_name': 'Demo',
                    'last_name': 'Staff',
                    'user_type': 'staff',
                    'primary_address': '456 Staff Avenue, Demo City'
                }
            )
            if created:
                staff.set_password('demo123')
                staff.save()
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created demo staff: {staff.username} ({staff.email})')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Demo staff already exists: {staff.username}')
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating demo staff: {e}'))

        # Create demo admin
        try:
            admin, created = User.objects.get_or_create(
                username='demoadmin',
                defaults={
                    'email': 'admin@demo.com',
                    'first_name': 'Demo',
                    'last_name': 'Admin',
                    'user_type': 'owner'
                }
            )
            if created:
                admin.set_password('demo123')
                admin.save()
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created demo admin: {admin.username} ({admin.email})')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Demo admin already exists: {admin.username}')
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating demo admin: {e}'))

        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('Demo users created successfully!'))
        self.stdout.write('\nYou can now test role-based login with:')
        self.stdout.write('\n🔹 Customer Login:')
        self.stdout.write('   Username: democustomer or customer@demo.com')
        self.stdout.write('   Password: demo123')
        self.stdout.write('   Select: Customer role')
        self.stdout.write('\n🔹 Staff Login:')
        self.stdout.write('   Username: demostaff or staff@demo.com')
        self.stdout.write('   Password: demo123')
        self.stdout.write('   Select: Staff role')
        self.stdout.write('\n🔹 Admin Login:')
        self.stdout.write('   Username: demoadmin or admin@demo.com')
        self.stdout.write('   Password: demo123')
        self.stdout.write('   Select: Admin/Owner role')
        self.stdout.write('\n' + '='*50)