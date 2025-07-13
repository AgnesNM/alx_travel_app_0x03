# listings/views.py (or wherever your BookingViewSet is defined)

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.utils import timezone
from django.db import transaction
from .models import Booking, Listing
from .serializers import BookingSerializer
from .tasks import send_booking_confirmation_email, send_booking_cancellation_email
import logging

logger = logging.getLogger(__name__)


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Create booking and trigger confirmation email."""
        with transaction.atomic():
            # Save the booking
            booking = serializer.save(user=self.request.user)
            
            # Get additional information for the email
            try:
                listing = booking.listing
                host_name = getattr(listing.host, 'get_full_name', lambda: listing.host.username)() if hasattr(listing, 'host') else 'Host'
                listing_location = getattr(listing, 'location', 'Location not specified')
                
                # Trigger email task asynchronously
                send_booking_confirmation_email.delay(
                    booking_id=booking.id,
                    user_email=self.request.user.email,
                    user_name=self.request.user.get_full_name() or self.request.user.username,
                    listing_title=listing.title,
                    check_in_date=booking.check_in_date.strftime('%Y-%m-%d'),
                    check_out_date=booking.check_out_date.strftime('%Y-%m-%d'),
                    total_price=str(booking.total_price),
                    listing_location=listing_location,
                    host_name=host_name
                )
                
                logger.info(f"Booking confirmation email task queued for booking {booking.id}")
                
            except Exception as e:
                # Log the error but don't fail the booking creation
                logger.error(f"Failed to queue email task for booking {booking.id}: {e}")
                # Optionally, you could queue a retry task or notify admins
    
    def create(self, request, *args, **kwargs):
        """Create a new booking with email notification."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Perform the creation (which triggers the email)
        self.perform_create(serializer)
        
        # Return success response
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                'success': True,
                'message': 'Booking created successfully. Confirmation email will be sent shortly.',
                'booking': serializer.data
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )
    
    def perform_destroy(self, instance):
        """Cancel booking and send cancellation email."""
        # Get booking info before deletion
        booking_id = instance.id
        user_email = instance.user.email
        user_name = instance.user.get_full_name() or instance.user.username
        listing_title = instance.listing.title
        
        # Delete the booking
        instance.delete()
        
        # Send cancellation email
        try:
            send_booking_cancellation_email.delay(
                booking_id=booking_id,
                user_email=user_email,
                user_name=user_name,
                listing_title=listing_title,
                cancellation_reason="Cancelled by user"
            )
            logger.info(f"Booking cancellation email task queued for booking {booking_id}")
        except Exception as e:
            logger.error(f"Failed to queue cancellation email task for booking {booking_id}: {e}")
    
    def destroy(self, request, *args, **kwargs):
        """Cancel a booking with email notification."""
        instance = self.get_object()
        self.perform_destroy(instance)
        
        return Response(
            {
                'success': True,
                'message': 'Booking cancelled successfully. Cancellation email will be sent shortly.'
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def resend_confirmation(self, request, pk=None):
        """Resend booking confirmation email."""
        booking = self.get_object()
        
        try:
            listing = booking.listing
            host_name = getattr(listing.host, 'get_full_name', lambda: listing.host.username)() if hasattr(listing, 'host') else 'Host'
            listing_location = getattr(listing, 'location', 'Location not specified')
            
            # Trigger email task
            task = send_booking_confirmation_email.delay(
                booking_id=booking.id,
                user_email=booking.user.email,
                user_name=booking.user.get_full_name() or booking.user.username,
                listing_title=listing.title,
                check_in_date=booking.check_in_date.strftime('%Y-%m-%d'),
                check_out_date=booking.check_out_date.strftime('%Y-%m-%d'),
                total_price=str(booking.total_price),
                listing_location=listing_location,
                host_name=host_name
            )
            
            return Response(
                {
                    'success': True,
                    'message': 'Confirmation email has been queued for resending.',
                    'task_id': task.id
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Failed to resend confirmation email for booking {booking.id}: {e}")
            return Response(
                {
                    'success': False,
                    'message': f'Failed to queue confirmation email: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def test_email(self, request):
        """Test email configuration (admin only)."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        test_email = request.data.get('email', request.user.email)
        
        try:
            from .tasks import test_email_configuration
            task = test_email_configuration.delay(test_email)
            
            return Response(
                {
                    'success': True,
                    'message': f'Test email queued for {test_email}',
                    'task_id': task.id
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'message': f'Failed to queue test email: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
