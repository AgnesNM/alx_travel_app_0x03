# listings/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.role_name


class UserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None, phone_number=None, role=None):
        if not email:
            raise ValueError('Users must have an email address')
        
        email = self.normalize_email(email)
        
        # Create default guest role if no role specified
        if not role:
            role, created = Role.objects.get_or_create(role_name='guest')
        
        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            role=role
        )
        
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, first_name, last_name, password=None, **extra_fields):
        admin_role, created = Role.objects.get_or_create(role_name='admin')
        user = self.create_user(
            email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            role=admin_role
        )
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    username = None
    user_id = models.AutoField(primary_key=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = UserManager()
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_full_name(self):
        return self.full_name
    
    def get_short_name(self):
        return self.first_name


class Property(models.Model):
    PROPERTY_TYPES = [
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('condo', 'Condo'),
        ('villa', 'Villa'),
        ('studio', 'Studio'),
        ('loft', 'Loft'),
        ('cabin', 'Cabin'),
        ('townhouse', 'Townhouse'),
    ]
    
    property_id = models.AutoField(primary_key=True)
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='properties')
    name = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Additional fields for better API functionality
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES, default='apartment')
    max_guests = models.PositiveIntegerField(default=1)
    bedrooms = models.PositiveIntegerField(default=1)
    bathrooms = models.PositiveIntegerField(default=1)
    amenities = models.TextField(blank=True, help_text="Comma-separated list of amenities")
    is_available = models.BooleanField(default=True)
    
    # Image field for property photos (optional)
    image = models.ImageField(upload_to='properties/', blank=True, null=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['host'], name='idx_property_host'),
            models.Index(fields=['location'], name='idx_property_location'),
            models.Index(fields=['property_type'], name='idx_property_type'),
            models.Index(fields=['price_per_night'], name='idx_property_price'),
        ]
        ordering = ['-created_at']
        verbose_name_plural = "Properties"
    
    def __str__(self):
        return f"{self.name} in {self.location}"
    
    @property
    def average_rating(self):
        """Calculate average rating from reviews"""
        reviews = self.reviews.all()
        if reviews:
            return sum(review.rating for review in reviews) / len(reviews)
        return 0
    
    @property
    def review_count(self):
        """Get total number of reviews"""
        return self.reviews.count()
    
    def clean(self):
        """Validate property data"""
        if self.price_per_night <= 0:
            raise ValidationError("Price per night must be greater than 0")
        if self.max_guests <= 0:
            raise ValidationError("Maximum guests must be greater than 0")


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELED = 'canceled', 'Canceled'
        CANCELLED = 'cancelled', 'Cancelled'  # Alternative spelling for API compatibility
        COMPLETED = 'completed', 'Completed'
    
    booking_id = models.AutoField(primary_key=True)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    start_date = models.DateField()
    end_date = models.DateField()
    guests = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    special_requests = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['property'], name='idx_booking_property'),
            models.Index(fields=['user'], name='idx_booking_user'),
            models.Index(fields=['start_date'], name='idx_booking_start_date'),
            models.Index(fields=['end_date'], name='idx_booking_end_date'),
            models.Index(fields=['status'], name='idx_booking_status'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(start_date__lt=models.F('end_date')),
                name='check_start_date_before_end_date'
            ),
            models.UniqueConstraint(
                fields=['property', 'start_date', 'end_date'],
                name='unique_property_booking_dates'
            ),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Booking #{self.booking_id} for {self.property.name}"
    
    def clean(self):
        """Validate booking data"""
        if self.start_date >= self.end_date:
            raise ValidationError("Check-out date must be after check-in date")
        if self.start_date < timezone.now().date():
            raise ValidationError("Check-in date cannot be in the past")
        if hasattr(self, 'property') and self.guests > self.property.max_guests:
            raise ValidationError(f"Maximum {self.property.max_guests} guests allowed")
    
    @property
    def duration_days(self):
        """Calculate booking duration in days"""
        return (self.end_date - self.start_date).days
    
    @property
    def check_in_date(self):
        """Alias for start_date to maintain API compatibility"""
        return self.start_date
    
    @property
    def check_out_date(self):
        """Alias for end_date to maintain API compatibility"""
        return self.end_date


class Payment(models.Model):
    PAYMENT_METHODS = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    payment_id = models.AutoField(primary_key=True)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['booking'], name='idx_payment_booking'),
            models.Index(fields=['status'], name='idx_payment_status'),
            models.Index(fields=['payment_date'], name='idx_payment_date'),
        ]
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Payment #{self.payment_id} for Booking #{self.booking.booking_id}"


class Review(models.Model):
    review_id = models.AutoField(primary_key=True)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['property'], name='idx_review_property'),
            models.Index(fields=['user'], name='idx_review_user'),
            models.Index(fields=['rating'], name='idx_review_rating'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['property', 'user'],
                name='unique_user_property_review'
            ),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review by {self.user.email} for {self.property.name}"
    
    def clean(self):
        """Validate review data"""
        # Check if user has a completed booking for this property
        if not self.property.bookings.filter(
            user=self.user,
            status__in=['completed', 'confirmed']
        ).exists():
            raise ValidationError("You can only review properties you have booked")


class Message(models.Model):
    message_id = models.AutoField(primary_key=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    message_body = models.TextField()
    sent_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    
    # Optional: Link message to a specific booking
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='messages', blank=True, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['sender'], name='idx_message_sender'),
            models.Index(fields=['recipient'], name='idx_message_recipient'),
            models.Index(fields=['sent_at'], name='idx_message_sent_at'),
            models.Index(fields=['is_read'], name='idx_message_is_read'),
        ]
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"Message from {self.sender.email} to {self.recipient.email}"


# Additional model for property amenities (normalized approach)
class Amenity(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True)  # For storing icon class names
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Amenities"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class PropertyAmenity(models.Model):
    """Many-to-many relationship between Property and Amenity with additional fields"""
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    amenity = models.ForeignKey(Amenity, on_delete=models.CASCADE)
    is_highlighted = models.BooleanField(default=False)  # For featuring certain amenities
    
    class Meta:
        unique_together = ['property', 'amenity']
        verbose_name_plural = "Property Amenities"
    
    def __str__(self):
        return f"{self.property.name} - {self.amenity.name}"


# Additional model for property images
class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='properties/images/')
    caption = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'id']
    
    def __str__(self):
        return f"Image for {self.property.name}"


# Notification model for user notifications
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('booking_request', 'Booking Request'),
        ('booking_confirmed', 'Booking Confirmed'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('payment_received', 'Payment Received'),
        ('review_received', 'Review Received'),
        ('message_received', 'Message Received'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    
    # Optional: Link to related objects
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, blank=True, null=True)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read'], name='idx_notification_user_read'),
        ]
    
    def __str__(self):
        return f"Notification for {self.user.email}: {self.title}"
