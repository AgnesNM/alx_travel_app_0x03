# listings/serializers.py
from rest_framework import serializers
from .models import User, Role, Property, Booking, Review, Payment, Message, Amenity, PropertyImage, Notification


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['role_id', 'role_name']


class UserSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'user_id', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'role', 'created_at', 'is_active'
        ]
        read_only_fields = ['user_id', 'created_at']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    role_name = serializers.CharField(write_only=True, required=False, default='guest')
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone_number',
            'password', 'password_confirm', 'role_name'
        ]
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        role_name = validated_data.pop('role_name', 'guest')
        
        # Get or create role
        role, created = Role.objects.get_or_create(role_name=role_name)
        
        password = validated_data.pop('password')
        user = User.objects.create_user(
            password=password,
            role=role,
            **validated_data
        )
        return user


class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = ['id', 'image', 'caption', 'is_primary', 'order']


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ['id', 'name', 'icon', 'description']


class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Review
        fields = ['review_id', 'user', 'rating', 'comment', 'created_at']
        read_only_fields = ['review_id', 'created_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class PropertySerializer(serializers.ModelSerializer):
    host = UserSerializer(read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    images = PropertyImageSerializer(many=True, read_only=True)
    average_rating = serializers.ReadOnlyField()
    review_count = serializers.ReadOnlyField()
    
    # For API compatibility, map field names
    id = serializers.ReadOnlyField(source='property_id')
    title = serializers.CharField(source='name')
    price_per_night = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        model = Property
        fields = [
            'id', 'property_id', 'title', 'name', 'description', 'location',
            'price_per_night', 'property_type', 'max_guests', 'bedrooms',
            'bathrooms', 'amenities', 'is_available', 'host', 'reviews',
            'images', 'average_rating', 'review_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['property_id', 'host', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['host'] = self.context['request'].user
        # Handle the name/title mapping
        if 'name' in validated_data:
            validated_data['name'] = validated_data['name']
        return super().create(validated_data)
    
    def validate_price_per_night(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price per night must be greater than 0")
        return value


class BookingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    property = PropertySerializer(read_only=True)
    property_id = serializers.IntegerField(write_only=True, source='property.property_id')
    duration_days = serializers.ReadOnlyField()
    
    # For API compatibility, map field names
    id = serializers.ReadOnlyField(source='booking_id')
    listing = PropertySerializer(read_only=True, source='property')
    listing_id = serializers.IntegerField(write_only=True, source='property.property_id')
    check_in_date = serializers.DateField(source='start_date')
    check_out_date = serializers.DateField(source='end_date')
    
    class Meta:
        model = Booking
        fields = [
            'id', 'booking_id', 'listing', 'listing_id', 'property', 'property_id',
            'user', 'check_in_date', 'check_out_date', 'start_date', 'end_date',
            'guests', 'total_price', 'status', 'special_requests',
            'duration_days', 'created_at', 'updated_at'
        ]
        read_only_fields = ['booking_id', 'user', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
    
    def validate(self, data):
        # Extract property_id from nested structure
        property_data = data.get('property', {})
        property_id = property_data.get('property_id')
        
        if not property_id:
            raise serializers.ValidationError("Property ID is required")
        
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        guests = data.get('guests')
        
        try:
            property_obj = Property.objects.get(property_id=property_id)
        except Property.DoesNotExist:
            raise serializers.ValidationError("Property does not exist")
        
        if not property_obj.is_available:
            raise serializers.ValidationError("This property is not available")
        
        if guests > property_obj.max_guests:
            raise serializers.ValidationError(f"Maximum {property_obj.max_guests} guests allowed")
        
        if start_date >= end_date:
            raise serializers.ValidationError("Check-out date must be after check-in date")
        
        # Check for overlapping bookings
        overlapping_bookings = Booking.objects.filter(
            property=property_obj,
            status__in=['pending', 'confirmed'],
            start_date__lt=end_date,
            end_date__gt=start_date
        )
        if self.instance:
            overlapping_bookings = overlapping_bookings.exclude(booking_id=self.instance.booking_id)
        
        if overlapping_bookings.exists():
            raise serializers.ValidationError("Dates are not available")
        
        # Calculate total price
        duration = (end_date - start_date).days
        data['total_price'] = property_obj.price_per_night * duration
        data['property'] = property_obj
        
        return data


class PaymentSerializer(serializers.ModelSerializer):
    booking = BookingSerializer(read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'payment_id', 'booking', 'amount', 'payment_date',
            'payment_method', 'status', 'transaction_id'
        ]
        read_only_fields = ['payment_id', 'payment_date']


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)
    recipient_id = serializers.IntegerField(write_only=True, source='recipient.user_id')
    
    class Meta:
        model = Message
        fields = [
            'message_id', 'sender', 'recipient', 'recipient_id',
            'message_body', 'sent_at', 'is_read', 'booking'
        ]
        read_only_fields = ['message_id', 'sender', 'sent_at']
    
    def create(self, validated_data):
        validated_data['sender'] = self.context['request'].user
        
        # Extract recipient_id from nested structure
        recipient_data = validated_data.pop('recipient', {})
        recipient_id = recipient_data.get('user_id')
        
        if recipient_id:
            try:
                recipient = User.objects.get(user_id=recipient_id)
                validated_data['recipient'] = recipient
            except User.DoesNotExist:
                raise serializers.ValidationError("Recipient does not exist")
        
        return super().create(validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    booking = BookingSerializer(read_only=True)
    property = PropertySerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'notification_type', 'title', 'message',
            'is_read', 'created_at', 'booking', 'property'
        ]
        read_only_fields = ['id', 'user', 'created_at']


# Simplified serializers for list views (better performance)
class PropertyListSerializer(serializers.ModelSerializer):
    host = serializers.StringRelatedField()
    average_rating = serializers.ReadOnlyField()
    id = serializers.ReadOnlyField(source='property_id')
    title = serializers.CharField(source='name')
    
    class Meta:
        model = Property
        fields = [
            'id', 'property_id', 'title', 'name', 'location',
            'price_per_night', 'property_type', 'max_guests',
            'bedrooms', 'bathrooms', 'is_available', 'host',
            'average_rating', 'created_at'
        ]


class BookingListSerializer(serializers.ModelSerializer):
    property = PropertyListSerializer(read_only=True)
    user = serializers.StringRelatedField()
    id = serializers.ReadOnlyField(source='booking_id')
    check_in_date = serializers.DateField(source='start_date')
    check_out_date = serializers.DateField(source='end_date')
    
    class Meta:
        model = Booking
        fields = [
            'id', 'booking_id', 'property', 'user', 'check_in_date',
            'check_out_date', 'guests', 'total_price', 'status', 'created_at'
        ]
