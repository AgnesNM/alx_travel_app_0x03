from celery import shared_task
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from datetime import datetime, timedelta
import logging

# Get logger for this module
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_booking_confirmation_email(self, booking_id, user_email, user_name, listing_title, 
                                   check_in_date, check_out_date, total_price, 
                                   listing_location=None, host_name=None):
    """
    Send booking confirmation email asynchronously.
    
    Args:
        booking_id (int): The ID of the booking
        user_email (str): Email address of the user
        user_name (str): Full name of the user
        listing_title (str): Title of the booked listing
        check_in_date (str): Check-in date (YYYY-MM-DD format)
        check_out_date (str): Check-out date (YYYY-MM-DD format)
        total_price (str): Total price of the booking
        listing_location (str, optional): Location of the listing
        host_name (str, optional): Name of the host
    
    Returns:
        str: Success message or raises exception on failure
    """
    try:
        logger.info(f"Starting email task for booking {booking_id} to {user_email}")
        
        # Calculate number of nights
        try:
            check_in = datetime.strptime(check_in_date, '%Y-%m-%d').date()
            check_out = datetime.strptime(check_out_date, '%Y-%m-%d').date()
            nights = (check_out - check_in).days
        except ValueError:
            nights = 1  # Default fallback
        
        # Email subject
        subject = f'Booking Confirmation #{booking_id} - {listing_title}'
        
        # Email context for template rendering
        context = {
            'user_name': user_name,
            'booking_id': booking_id,
            'listing_title': listing_title,
            'listing_location': listing_location or 'Location not specified',
            'host_name': host_name or 'Host',
            'check_in_date': check_in_date,
            'check_out_date': check_out_date,
            'total_price': total_price,
            'nights': nights,
            'booking_date': timezone.now().strftime('%Y-%m-%d'),
            'company_name': 'ALX Travel App',
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@alxtravelapp.com'),
            'website_url': getattr(settings, 'WEBSITE_URL', 'https://alxtravelapp.com'),
        }
        
        try:
            # Render HTML email template
            html_message = render_to_string('emails/booking_confirmation.html', context)
            plain_message = strip_tags(html_message)
        except Exception as template_error:
            logger.warning(f"Template rendering failed, using fallback: {template_error}")
            # Fallback to simple text email if template fails
            plain_message = f"""
Dear {user_name},

Your booking has been confirmed!

Booking Details:
- Booking ID: {booking_id}
- Property: {listing_title}
- Location: {listing_location or 'Location not specified'}
- Check-in: {check_in_date}
- Check-out: {check_out_date}
- Number of nights: {nights}
- Total Price: ${total_price}

Thank you for choosing ALX Travel App!

Best regards,
ALX Travel App Team
            """.strip()
            html_message = None
        
        # Create email message
        if html_message:
            # Use EmailMultiAlternatives for HTML emails
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_email]
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
        else:
            # Use simple send_mail for text-only emails
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                fail_silently=False,
            )
        
        success_message = f"Booking confirmation email sent successfully to {user_email} for booking {booking_id}"
        logger.info(success_message)
        return success_message
        
    except Exception as exc:
        error_message = f"Error sending booking confirmation email for booking {booking_id}: {exc}"
        logger.error(error_message)
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying email task for booking {booking_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc, countdown=60)
        else:
            logger.error(f"Max retries exceeded for booking {booking_id} email task")
            raise exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_booking_reminder_email(self, booking_id, user_email, user_name, listing_title, 
                               check_in_date, listing_location=None):
    """
    Send booking reminder email (for check-in reminders).
    
    Args:
        booking_id (int): The ID of the booking
        user_email (str): Email address of the user
        user_name (str): Full name of the user
        listing_title (str): Title of the booked listing
        check_in_date (str): Check-in date (YYYY-MM-DD format)
        listing_location (str, optional): Location of the listing
    
    Returns:
        str: Success message or raises exception on failure
    """
    try:
        logger.info(f"Starting reminder email task for booking {booking_id} to {user_email}")
        
        # Email subject
        subject = f'Booking Reminder - Check-in Tomorrow: {listing_title}'
        
        # Email context
        context = {
            'user_name': user_name,
            'booking_id': booking_id,
            'listing_title': listing_title,
            'listing_location': listing_location or 'Location not specified',
            'check_in_date': check_in_date,
            'company_name': 'ALX Travel App',
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@alxtravelapp.com'),
        }
        
        try:
            # Render HTML email template
            html_message = render_to_string('emails/booking_reminder.html', context)
            plain_message = strip_tags(html_message)
        except Exception as template_error:
            logger.warning(f"Reminder template rendering failed, using fallback: {template_error}")
            # Fallback to simple text email
            plain_message = f"""
Dear {user_name},

This is a friendly reminder about your upcoming booking:

- Booking ID: {booking_id}
- Property: {listing_title}
- Location: {listing_location or 'Location not specified'}
- Check-in: {check_in_date}

We hope you have a wonderful stay!

Best regards,
ALX Travel App Team
            """.strip()
            html_message = None
        
        # Send email
        if html_message:
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_email]
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
        else:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                fail_silently=False,
            )
        
        success_message = f"Booking reminder email sent successfully to {user_email} for booking {booking_id}"
        logger.info(success_message)
        return success_message
        
    except Exception as exc:
        error_message = f"Error sending booking reminder email for booking {booking_id}: {exc}"
        logger.error(error_message)
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying reminder email task for booking {booking_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc, countdown=60)
        else:
            logger.error(f"Max retries exceeded for booking {booking_id} reminder email task")
            raise exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_booking_cancellation_email(self, booking_id, user_email, user_name, listing_title, 
                                   cancellation_reason=None):
    """
    Send booking cancellation email.
    
    Args:
        booking_id (int): The ID of the cancelled booking
        user_email (str): Email address of the user
        user_name (str): Full name of the user
        listing_title (str): Title of the cancelled listing
        cancellation_reason (str, optional): Reason for cancellation
    
    Returns:
        str: Success message or raises exception on failure
    """
    try:
        logger.info(f"Starting cancellation email task for booking {booking_id} to {user_email}")
        
        # Email subject
        subject = f'Booking Cancellation Confirmation #{booking_id}'
        
        # Email context
        context = {
            'user_name': user_name,
            'booking_id': booking_id,
            'listing_title': listing_title,
            'cancellation_reason': cancellation_reason or 'Not specified',
            'cancellation_date': timezone.now().strftime('%Y-%m-%d'),
            'company_name': 'ALX Travel App',
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@alxtravelapp.com'),
        }
        
        # Simple text email for cancellation
        plain_message = f"""
Dear {user_name},

Your booking has been cancelled as requested.

Booking Details:
- Booking ID: {booking_id}
- Property: {listing_title}
- Cancellation Date: {context['cancellation_date']}
- Reason: {cancellation_reason or 'Not specified'}

If you have any questions about this cancellation or need assistance with rebooking, 
please contact our support team at {context['support_email']}.

Thank you for using ALX Travel App.

Best regards,
ALX Travel App Team
        """.strip()
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )
        
        success_message = f"Booking cancellation email sent successfully to {user_email} for booking {booking_id}"
        logger.info(success_message)
        return success_message
        
    except Exception as exc:
        error_message = f"Error sending booking cancellation email for booking {booking_id}: {exc}"
        logger.error(error_message)
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying cancellation email task for booking {booking_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc, countdown=60)
        else:
            logger.error(f"Max retries exceeded for booking {booking_id} cancellation email task")
            raise exc


@shared_task
def send_bulk_promotional_emails(user_emails, subject, message):
    """
    Send promotional emails to multiple users.
    
    Args:
        user_emails (list): List of email addresses
        subject (str): Email subject
        message (str): Email message
    
    Returns:
        dict: Results summary
    """
    logger.info(f"Starting bulk email task for {len(user_emails)} recipients")
    
    successful_sends = 0
    failed_sends = 0
    errors = []
    
    for email in user_emails:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            successful_sends += 1
            logger.debug(f"Promotional email sent successfully to {email}")
        except Exception as e:
            failed_sends += 1
            error_msg = f"Failed to send email to {email}: {e}"
            errors.append(error_msg)
            logger.error(error_msg)
    
    result = {
        'total_emails': len(user_emails),
        'successful_sends': successful_sends,
        'failed_sends': failed_sends,
        'errors': errors
    }
    
    logger.info(f"Bulk email task completed: {successful_sends} successful, {failed_sends} failed")
    return result


@shared_task
def cleanup_old_task_results():
    """
    Cleanup old task results (periodic maintenance task).
    This is a placeholder for any cleanup operations you might need.
    """
    logger.info("Running cleanup task for old email task results")
    # Add any cleanup logic here
    return "Cleanup completed successfully"


# Utility function to test email configuration
@shared_task
def test_email_configuration(test_email):
    """
    Test email configuration by sending a test email.
    
    Args:
        test_email (str): Email address to send test email to
    
    Returns:
        str: Success or error message
    """
    try:
        send_mail(
            subject='ALX Travel App - Email Configuration Test',
            message='This is a test email to verify your email configuration is working correctly.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[test_email],
            fail_silently=False,
        )
        
        success_message = f"Test email sent successfully to {test_email}"
        logger.info(success_message)
        return success_message
        
    except Exception as e:
        error_message = f"Failed to send test email to {test_email}: {e}"
        logger.error(error_message)
        raise e
