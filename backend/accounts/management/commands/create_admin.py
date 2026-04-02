from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Create default admin user'

    def handle(self, *args, **options):
        # Check if admin user already exists
        if User.objects.filter(username='admin').exists():
            self.stdout.write(self.style.WARNING('Admin user already exists'))
            return

        # Create admin user with specified credentials
        with transaction.atomic():
            user = User.objects.create_user(
                username='admin',
                password='admin',
                email='admin@example.com',
                first_name='Admin',
                last_name='User',
                is_staff=True,
                is_superuser=True,
                role='admin'
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created admin user: {user.username}'))
