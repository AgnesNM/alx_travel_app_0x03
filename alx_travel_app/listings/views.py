# listings/views.py
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg
from django.utils import timezone
from .models import User, Property, Booking, Review, Payment, Message, Notification
from .serializers import (
    PropertySerializer, PropertyListSerializer, BookingSerializer, 
    BookingListSerializer, ReviewSerializer, UserSerializer, 
    PaymentSerializer, MessageSerializer, NotificationSerializer
)
from .permissions import IsOwnerOrReadOnly, IsBookingOwnerOrPropertyHost


class PropertyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing property listings.
    
    Provides CRUD operations for properties with additional features:
    - Search by name, description, location
    - Filter by property type, price range, availability
    - Order by price, created date, rating
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Search fields
    search_fields = ['name', 'description', 'location']
    
    # Filter fields
    filterset_fields = {
        'property_type': ['exact'],
        'price_per_night': ['gte', 'lte'],
        'max_guests': ['gte'],
        'bedrooms': ['gte'],
        'bathrooms': ['gte'],
        'is_available': ['exact'],
        'location': ['icontains'],
    }
    
    # Ordering fields
    ordering_fields = ['price_per_night', 'created_at', 'name']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return PropertyListSerializer
        return PropertySerializer
    
    def get_queryset(self):
        queryset = Property.objects.select_related('host').prefetch_related('reviews', 'images')
        
        # Additional custom filters
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        location = self.request.query_params.get('location')
        available_from = self.request.query_params.get('available_from')
        available_to = self.request.query_params.get('available_to')
        
        if min_price:
            queryset = queryset.filter(price_per_night__gte=min_price)
        if max_price:
            queryset = queryset.filter(price_per_night__lte=max_price)
        if location:
            queryset = queryset.filter(location__icontains=location)
            
        # Filter by availability for specific dates
        if available_from and available_to:
            try:
                from datetime import datetime
                start_date = datetime.strptime(available_from, '%Y-%m-%d').date()
                end_date = datetime.strptime(available_to, '%Y-%m-%d').date()
                
                unavailable_properties = Booking.objects.filter(
                    status__in=['pending', 'confirmed'],
                    start_date__lt=end_date,
                    end_date__gt=start_date
                ).values_list('property_id', flat=True)
                queryset = queryset.exclude(property_id__in=unavailable_properties)
            except ValueError:
                pass  # Invalid date format, ignore filter
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """Check availability for a specific property"""
        property_obj = self.get_object()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from datetime import datetime
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        overlapping_bookings = property_obj.bookings.filter(
            status__in=['pending', 'confirmed'],
            start_date__lt=end_date,
            end_date__gt=start_date
        )
        
        is_available = not overlapping_bookings.exists() and property_obj.is_available
        
        return Response({
            'available': is_available,
            'start_date': start_date,
            'end_date': end_date,
            'price_per_night': property_obj.price_per_night
        })
    
    @action(detail=True, methods=['post'])
    def add_review(self, request, pk=None):
        """Add a review to a property"""
        property_obj = self.get_object()
        
        # Check if user has booked this property
        has_booking = property_obj.bookings.filter(
            user=request.user,
            status__in=['completed', 'confirmed']
        ).exists()
        
        if not has_booking:
            return Response(
                {'error': 'You can only review properties you have booked'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if user has already reviewed this property
        if property_obj.reviews.filter(user=request.user).exists():
            return Response(
                {'error': 'You have already reviewed this property'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ReviewSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(property=property_obj)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Get all reviews for a property"""
        property_obj = self.get_object()
        reviews = property_obj.reviews.all()
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing bookings.
    
    Provides CRUD operations for bookings with user-specific filtering.
    """
    permission_classes = [permissions.IsAuthenticated, IsBookingOwnerOrPropertyHost]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    
    filterset_fields = ['status', 'property']
    ordering_fields = ['start_date', 'end_date', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return BookingListSerializer
        return BookingSerializer
    
    def get_queryset(self):
        user = self.request.user
        # Users can see their own bookings and bookings for their properties
        return Booking.objects.filter(
            Q(user=user) | Q(property__host=user)
        ).select_related('user', 'property', 'property__host')
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a pending booking (host only)"""
        booking = self.get_object()
        
        if booking.property.host != request.user:
            return Response(
                {'error': 'Only the property host can confirm bookings'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if booking.status != 'pending':
            return Response(
                {'error': 'Only pending bookings can be confirmed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.status = 'confirmed'
        booking.save()
        
        # Create notification for guest
        from .utils import create_notification
        create_notification(
            user=booking.user,
            notification_type='booking_confirmed',
            title='Booking Confirmed',
            message=f'Your booking for {booking.property.name} has been confirmed.',
            booking=booking,
            property=booking.property
        )
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking"""
        booking = self.get_object()
        
        if booking.status not in ['pending', 'confirmed']:
            return Response(
                {'error': 'Only pending or confirmed bookings can be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.status = 'cancelled'
        booking.save()
        
        # Create notification for the other party
        if request.user == booking.user:
            # Guest cancelled, notify host
            recipient = booking.property.host
        else:
            # Host cancelled, notify guest
            recipient = booking.user
        
        from .utils import create_notification
        create_notification(
            user=recipient,
            notification_type='booking_cancelled',
            title='Booking Cancelled',
            message=f'Booking for {booking.property.name} has been cancelled.',
            booking=booking,
            property=booking.property
        )
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark a booking as completed (host only)"""
        booking = self.get_object()
        
        if booking.property.host != request.user:
            return Response(
                {'error': 'Only the property host can complete bookings'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if booking.status != 'confirmed':
            return Response(
                {'error': 'Only confirmed bookings can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if checkout date has passed
        if booking.end_date > timezone.now().date():
            return Response(
                {'error': 'Cannot complete booking before checkout date'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.status = 'completed'
        booking.save()
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing reviews.
    """
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    
    filterset_fields = ['property', 'rating']
    ordering_fields = ['rating', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Review.objects.select_related('user', 'property')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user management.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'user_id'
    
    def get_queryset(self):
        # Users can only see their own profile unless they're staff
        if self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(user_id=self.request.user.user_id)
    
    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        """Get or update current user profile"""
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        else:
            serializer = self.get_serializer(
                request.user, data=request.data, partial=request.method == 'PATCH'
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def properties(self, request, user_id=None):
        """Get properties owned by a user"""
        user = self.get_object()
        properties = user.properties.all()
        serializer = PropertyListSerializer(properties, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def bookings(self, request, user_id=None):
        """Get bookings made by a user"""
        user = self.get_object()
        bookings = user.bookings.all()
        serializer = BookingListSerializer(bookings, many=True)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages between users.
    """
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    
    filterset_fields = ['is_read', 'booking']
    ordering_fields = ['sent_at']
    ordering = ['-sent_at']
    
    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(
            Q(sender=user) | Q(recipient=user)
        ).select_related('sender', 'recipient', 'booking')
    
    @action(detail=False, methods=['get'])
    def conversations(self, request):
        """Get list of conversations for current user"""
        user = request.user
        
        # Get unique conversation partners
        sent_to = Message.objects.filter(sender=user).values_list('recipient', flat=True)
        received_from = Message.objects.filter(recipient=user).values_list('sender', flat=True)
        
        partner_ids = set(list(sent_to) + list(received_from))
        partners = User.objects.filter(user_id__in=partner_ids)
        
        conversations = []
        for partner in partners:
            # Get latest message with this partner
            latest_message = Message.objects.filter(
                Q(sender=user, recipient=partner) | Q(sender=partner, recipient=user)
            ).order_by('-sent_at').first()
            
            # Count unread messages from this partner
            unread_count = Message.objects.filter(
                sender=partner, recipient=user, is_read=False
            ).count()
            
            conversations.append({
                'partner': UserSerializer(partner).data,
                'latest_message': MessageSerializer(latest_message).data if latest_message else None,
                'unread_count': unread_count
            })
        
        return Response(conversations)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a message as read"""
        message = self.get_object()
        
        if message.recipient != request.user:
            return Response(
                {'error': 'You can only mark your own messages as read'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        message.is_read = True
        message.save()
        
        return Response({'status': 'Message marked as read'})


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user notifications.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    
    filterset_fields = ['notification_type', 'is_read']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        
        return Response({'status': 'Notification marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        self.get_queryset().update(is_read=True)
        return Response({'status': 'All notifications marked as read'})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing payments (read-only for now).
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    
    filterset_fields = ['status', 'payment_method']
    ordering_fields = ['payment_date', 'amount']
    ordering = ['-payment_date']
    
    def get_queryset(self):
        user = self.request.user
        # Users can see payments for their bookings or bookings of their properties
        return Payment.objects.filter(
            Q(booking__user=user) | Q(booking__property__host=user)
        ).select_related('booking', 'booking__user', 'booking__property')
