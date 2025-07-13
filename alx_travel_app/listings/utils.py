
from django.core.mail import send_mail
from django.conf import settings
from .models import Booking, Notification
import logging

logger = logging.getLogger(__name__)


def send_booking_confirmation_email(booking):
    """Send booking confirmation email to guest"""
    try:
        subject = f'Booking Confirmation - {booking.property.name}'
        message = f'''
        Dear {booking.user.get_full_name()},
        
        Your booking has been confirmed!
        
        Property: {booking.property.name}
        Location: {booking.property.location}
        Check-in: {booking.start_date}
        Check-out: {booking.end_date}
        Guests: {booking.guests}
        Total Price: ${booking.total_price}
        
        Thank you for choosing our platform!
        
        Best regards,
        The Airbnb Clone Team
        '''
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [booking.user.email],
            fail_silently=False,
        )
        logger.info(f"Confirmation email sent to {booking.user.email}")
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {e}")


def send_booking_notification_email(booking):
    """Send booking notification email to host"""
    try:
        subject = f'New Booking Request - {booking.property.name}'
        message = f'''
        Dear {booking.property.host.get_full_name()},
        
        You have received a new booking request!
        
        Property: {booking.property.name}
        Guest: {booking.user.get_full_name()}
        Email: {booking.user.email}
        Phone: {booking.user.phone_number or 'Not provided'}
        Check-in: {booking.start_date}
        Check-out: {booking.end_date}
        Guests: {booking.guests}
        Total Price: ${booking.total_price}
        Special Requests: {booking.special_requests or 'None'}
        
        Please log in to your account to confirm or decline the booking.
        
        Best regards,
        The Airbnb Clone Team
        '''
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [booking.property.host.email],
            fail_silently=False,
        )
        logger.info(f"Booking notification email sent to {booking.property.host.email}")
    except Exception as e:
        logger.error(f"Failed to send booking notification email: {e}")


def send_cancellation_email(booking, cancelled_by):
    """Send booking cancellation email to relevant parties"""
    try:
        if cancelled_by == booking.user:
            # Guest cancelled, notify host
            recipient = booking.property.host
            subject = f'Booking Cancelled - {booking.property.name}'
            message = f'''
            Dear {recipient.get_full_name()},
            
            A booking for your property has been cancelled by the guest.
            
            Property: {booking.property.name}
            Guest: {booking.user.get_full_name()}
            Check-in: {booking.start_date}
            Check-out: {booking.end_date}
            
            The booking amount will be refunded according to your cancellation policy.
            
            Best regards,
            The Airbnb Clone Team
            '''
        else:
            # Host cancelled, notify guest
            recipient = booking.user
            subject = f'Booking Cancelled - {booking.property.name}'
            message = f'''
            Dear {recipient.get_full_name()},
            
            Unfortunately, your booking has been cancelled by the host.
            
            Property: {booking.property.name}
            Check-in: {booking.start_date}
            Check-out: {booking.end_date}
            
            You will receive a full refund within 3-5 business days.
            
            Best regards,
            The Airbnb Clone Team
            '''
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient.email],
            fail_silently=False,
        )
        logger.info(f"Cancellation email sent to {recipient.email}")
    except Exception as e:
        logger.error(f"Failed to send cancellation email: {e}")


def create_notification(user, notification_type, title, message, booking=None, property=None):
    """Create a notification for a user"""
    try:
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            booking=booking,
            property=property
        )
        logger.info(f"Notification created for user {user.email}: {title}")
        return notification
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
        return None


def calculate_booking_total(property_obj, start_date, end_date):
    """Calculate total price for a booking"""
    duration = (end_date - start_date).days
    if duration <= 0:
        raise ValueError("Invalid booking duration")
    
    total = property_obj.price_per_night * duration
    
    # Add any additional fees here (cleaning fee, service fee, etc.)
    # service_fee = total * 0.03  # 3% service fee
    # total += service_fee
    
    return total


def check_property_availability(property_obj, start_date, end_date, exclude_booking=None):
    """Check if a property is available for given dates"""
    if not property_obj.is_available:
        return False
    
    overlapping_bookings = Booking.objects.filter(
        property=property_obj,
        status__in=['pending', 'confirmed'],
        start_date__lt=end_date,
        end_date__gt=start_date
    )
    
    if exclude_booking:
        overlapping_bookings = overlapping_bookings.exclude(booking_id=exclude_booking.booking_id)
    
    return not overlapping_bookings.exists()


def get_user_booking_stats(user):
    """Get booking statistics for a user"""
    user_bookings = user.bookings.all()
    
    stats = {
        'total_bookings': user_bookings.count(),
        'pending_bookings': user_bookings.filter(status='pending').count(),
        'confirmed_bookings': user_bookings.filter(status='confirmed').count(),
        'completed_bookings': user_bookings.filter(status='completed').count(),
        'cancelled_bookings': user_bookings.filter(status__in=['cancelled', 'canceled']).count(),
        'total_spent': sum(booking.total_price for booking in user_bookings.filter(
            status__in=['confirmed', 'completed']
        ))
    }
    
    return stats


def get_host_property_stats(user):
    """Get property statistics for a host"""
    user_properties = user.properties.all()
    
    stats = {
        'total_properties': user_properties.count(),
        'active_properties': user_properties.filter(is_available=True).count(),
        'total_bookings': sum(prop.bookings.count() for prop in user_properties),
        'total_revenue': sum(
            booking.total_price for prop in user_properties 
            for booking in prop.bookings.filter(status__in=['confirmed', 'completed'])
        ),
        'average_rating': sum(prop.average_rating for prop in user_properties) / user_properties.count() 
                        if user_properties.count() > 0 else 0
    }
    
    return stats
