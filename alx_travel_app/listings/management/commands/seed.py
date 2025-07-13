from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from listings.models import Role, Property, Booking, Payment, Review, Message
from faker import Faker
import random
from datetime import datetime, timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with sample data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding data...')
        self.create_roles()
        self.create_users()
        self.create_properties()
        self.create_bookings()
        self.create_payments()
        self.create_reviews()
        self.create_messages()
        self.stdout.write(self.style.SUCCESS('Successfully seeded database!'))

    def create_roles(self):
        roles = ['guest', 'host', 'admin']
        for role in roles:
            Role.objects.get_or_create(role_name=role)
        self.stdout.write('Created roles')

    def create_users(self):
        fake = Faker()
        
        # Create admin user
        admin_role = Role.objects.get(role_name='admin')
        admin = User.objects.create_user(
            email='khalfanathman12@gmail.com',
            first_name='Khalfan',
            last_name='Athman',
            password='Admin@123',
            role=admin_role
        )
        admin.is_admin = True
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        
        # Create hosts
        host_role = Role.objects.get(role_name='host')
        for _ in range(5):
            user = User.objects.create_user(
                email=fake.unique.email(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                password='host123',
                phone_number=fake.phone_number(),
                role=host_role
            )
        
        # Create guests
        guest_role = Role.objects.get(role_name='guest')
        for _ in range(20):
            user = User.objects.create_user(
                email=fake.unique.email(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                password='guest123',
                phone_number=fake.phone_number(),
                role=guest_role
            )
        
        self.stdout.write('Created users')

    def create_properties(self):
        fake = Faker()
        hosts = User.objects.filter(role__role_name='host')
        property_types = ['Apartment', 'House', 'Villa', 'Cottage', 'Cabin']
        
        for host in hosts:
            for _ in range(random.randint(1, 4)):  # Each host has 1-4 properties
                Property.objects.create(
                    host=host,
                    name=f"{random.choice(property_types)} in {fake.city()}",
                    description=fake.paragraph(nb_sentences=5),
                    location=fake.address(),
                    price_per_night=random.randint(50, 500)
                )
        self.stdout.write('Created properties')

    def create_bookings(self):
        fake = Faker()
        guests = User.objects.filter(role__role_name='guest')
        properties = Property.objects.all()
        statuses = ['pending', 'confirmed', 'canceled']
        
        for property in properties:
            for _ in range(random.randint(1, 5)):  # 1-5 bookings per property
                start_date = fake.date_between(start_date='-30d', end_date='+30d')
                end_date = start_date + timedelta(days=random.randint(1, 14))
                
                Booking.objects.create(
                    property=property,
                    user=random.choice(guests),
                    start_date=start_date,
                    end_date=end_date,
                    total_price=(end_date - start_date).days * property.price_per_night,
                    status=random.choice(statuses)
                )
        self.stdout.write('Created bookings')

    def create_payments(self):
        fake = Faker()
        bookings = Booking.objects.all()
        payment_methods = ['credit_card', 'paypal', 'stripe']
        
        for booking in bookings:
            if booking.status == 'confirmed':
                Payment.objects.create(
                    booking=booking,
                    amount=booking.total_price,
                    payment_method=random.choice(payment_methods)
                )
        self.stdout.write('Created payments')

    def create_reviews(self):
        fake = Faker()
        bookings = Booking.objects.filter(status='confirmed')
        
        for booking in bookings:
            if random.random() > 0.3:  # 70% chance of review
                Review.objects.create(
                    property=booking.property,
                    user=booking.user,
                    rating=random.randint(1, 5),
                    comment=fake.paragraph(nb_sentences=3)
                )
        self.stdout.write('Created reviews')

    def create_messages(self):
        fake = Faker()
        users = User.objects.all()
        
        for _ in range(50):
            sender, recipient = random.sample(list(users), 2)
            Message.objects.create(
                sender=sender,
                recipient=recipient,
                message_body=fake.paragraph(nb_sentences=2)
            )
        self.stdout.write('Created messages')
