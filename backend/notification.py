from django.db.models import Q
from backend.fcm.messaging2 import send_fcm_message
from .models import FCMToken
import threading
import logging

logger = logging.getLogger(__name__)


def send_notification_to_students(course, resource_name, resource_type):
    """
    Send notification to all students enrolled in a course about a new resource

    Args:
        course: The Course object the resource was added to
        resource_name: Name of the new resource
        resource_type: Type of the resource (file, video, article, etc.)
    """
    try:
        # Get all active FCM tokens for students enrolled in this course
        tokens = FCMToken.objects.filter(
            Q(profile__courses=course) &
            Q(is_active=True) &
            Q(profile__is_active=True)
        ).values_list('token', flat=True).distinct()

        if not tokens:
            logger.info(
                f"No active FCM tokens found for course: {course.title}")
            return

        # Prepare notification message
        title = f"New {resource_type} in {course.title}"
        body = f"A new {resource_type.lower()} '{resource_name}' has been added to the course"

        # Prepare data payload for deep linking
        data = {
            "type": "new_resource",
            "course_id": str(course.id),
            "resource_type": resource_type,
            "title": title,
            "body": body
        }

        # Send to all tokens
        success_count = 0
        for token in tokens:
            try:
                send_fcm_message(token, title, body, data)
                success_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to send notification to token {token}: {str(e)}")
        log_notification_delivery(
            course, resource_name, success_count, len(tokens))

        return success_count

    except Exception as e:
        logger.error(f"Error in send_notification_to_students: {str(e)}")
        raise


def send_notification_to_students_async(course, resource_name, resource_type):
    """
    Send notifications asynchronously using a thread
    """
    thread = threading.Thread(
        target=send_notification_to_students,
        args=(course, resource_name, resource_type)
    )
    thread.daemon = True  # This thread won't prevent program exit
    thread.start()


def log_notification_delivery(course, resource, success_count, total_count):
    """
    Log notification delivery statistics
    """
    logger.info(
        f"Notification delivery for resource '{resource.name}' in course '{course.title}': "
        f"{success_count}/{total_count} successful"
    )


def send_news_notifications(head, news_type, description):
    """
    Send notification to all Active Profiles about a new News

    Args:
        head: News Title
        news_type: Type of the news (SVU, Education, General)
    """
    try:
        # Get all active FCM tokens for Active Profiles
        tokens = FCMToken.objects.filter(profile__is_active=True).values_list(
            'token', flat=True).distinct()

        if not tokens:
            logger.info(
                f"No active FCM tokens found")
            return

        # Prepare notification message
        title = f"News Just in - {news_type}"
        body = f"{head.lower()}:" + "\n" + f"{description.lower()} ....."
        # Send to all tokens
        success_count = 0
        for token in tokens:
            try:
                send_fcm_message(token, title, body)
                success_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to send notification to token {token}: {str(e)}")
        log_notification_delivery(
            news_type, head, success_count, len(tokens))

        return success_count

    except Exception as e:
        logger.error(f"Error in send_news_notifications: {str(e)}")
        raise
