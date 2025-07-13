# listings/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Role, Property, Booking, Review, Payment, Message, 
    Amenity, PropertyImage, Notification
)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['role_id', 'role_name']
    search_fields = ['role_name']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['user_id', 'email', 'first_name', 'last_name', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'is_staff', 'created_at']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-created_at']
    readonly_fields = ['user_id', 'created_at']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone_number', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = [
        'property_id', 'name', 'location', 'property_type', 
        'price_per_night', 'host', 'is_available', 'created_at'
    ]
    list_filter = ['property_type', 'is_available', 'created_at', 'max_guests']
    search_fields = ['name', 'location', 'description', 'host__email']
    list_editable = ['is_available', 'price_per_night']
    readonly_fields = ['property_id', 'created_at', 'updated_at', 'average_rating']
    inlines = [PropertyImageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'location', 'host')
        }),
        ('Property Details', {
            'fields': ('property_type', 'max_guests', 'bedrooms', 'bathrooms', 'amenities')
        }),
        ('Pricing & Availability', {
            'fields': ('price_per_night', 'is_available')
        }),
        ('Media', {
            'fields': ('image',)
        }),
        ('System Info', {
            'fields': ('property_id', 'average_rating', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'booking_id', 'property', 'user', 'start_date', 
        'end_date', 'guests', 'status', 'total_price', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'start_date']
    search_fields = ['property__name', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['booking_id', 'created_at', 'updated_at', 'duration_days']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Booking Details', {
            'fields': ('property', 'user', 'start_date', 'end_date', 'guests')
        }),
        ('Pricing & Status', {
            'fields': ('total_price', 'status', 'special_requests')
        }),
        ('System Info', {
            'fields': ('booking_id', 'duration_days', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['review_id', 'property', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['property__name', 'user__email', 'comment']
    readonly_fields = ['review_id', 'created_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_id', 'booking', 'amount', 'payment_method', 
        'status', 'payment_date'
    ]
    list_filter = ['status', 'payment_method', 'payment_date']
    search_fields = ['booking__property__name', 'transaction_id']
    readonly_fields = ['payment_id', 'payment_date']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'sender', 'recipient', 'sent_at', 'is_read']
    list_filter = ['is_read', 'sent_at']
    search_fields = ['sender__email', 'recipient__email', 'message_body']
    readonly_fields = ['message_id', 'sent_at']


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'icon']
    search_fields = ['name']


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'property', 'caption', 'is_primary', 'order']
    list_filter = ['is_primary']
    search_fields = ['property__name', 'caption']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__email', 'title', 'message']
    readonly_fields = ['created_at']
