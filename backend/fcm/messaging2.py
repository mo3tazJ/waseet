# messaging.py
import json
from pathlib import Path
from google.oauth2 import service_account
from google.auth.transport import requests as google_requests
import requests
from django.conf import settings
import logging
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)

# Get project ID from Django settings or use default
PROJECT_ID = getattr(settings, 'FIREBASE_PROJECT_ID', 'alaa-e6e90')

BASE_URL = 'https://fcm.googleapis.com'
FCM_ENDPOINT = f'v1/projects/{PROJECT_ID}/messages:send'
FCM_URL = BASE_URL + '/' + FCM_ENDPOINT
SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']


# [START retrieve_access_token]
def _get_access_token():
    """Retrieve a valid access token that can be used to authorize requests.
    :return: Access token.
    """
    # Get credentials path from Django settings
    cred_file_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)

    if not cred_file_path:
        # Fallback to the original path logic
        cred_file_dir = Path(__file__).resolve().parent.parent.parent
        cred_file_path = cred_file_dir / 'alaa-firebase-adminsdk.json'

    try:
        credentials = service_account.Credentials.from_service_account_file(
            str(cred_file_path), scopes=SCOPES)
        request = google_requests.Request()
        credentials.refresh(request)
        return credentials.token
    except Timeout:
        logger.error("Timeout while getting access token from Google OAuth2")
        raise Exception("Timeout connecting to Google authentication service")
    except Exception as e:
        logger.error(f"Error getting access token: {str(e)}")
        raise


def _send_fcm_message(fcm_message):
    """Send HTTP request to FCM with given message.

    Args:
      fcm_message: JSON object that will make up the body of the request.
    """
    try:
        headers = {
            'Authorization': 'Bearer ' + _get_access_token(),
            'Content-Type': 'application/json; UTF-8',
        }

        response = requests.post(
            FCM_URL, data=json.dumps(fcm_message), headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes

        logger.info(
            'Message sent to Firebase for delivery, response: %s', response.text)
        return response.json()

    except Timeout:
        logger.error('Timeout while sending FCM message')
        raise Exception("Timeout connecting to Firebase service")
    except RequestException as e:
        logger.error('Unable to send message to Firebase: %s', str(e))
        if hasattr(e, 'response') and e.response is not None:
            logger.error('Response content: %s', e.response.text)
        raise
    except Exception as e:
        logger.error('Unexpected error sending FCM message: %s', str(e))
        raise


def _build_common_message(fcm_token, title, body, data=None):
    """Construct common notification message.

    Construct a JSON object that will be used to define the
    common parts of a notification message that will be sent
    to any app instance subscribed to the news topic.
    """
    message = {
        'message': {
            'token': fcm_token,
            'notification': {
                'title': title,
                'body': body
            }
        }
    }

    # Add custom data if provided
    if data:
        message['message']['data'] = data
    else:
        message['message']['data'] = {"type": "general"}
    # print(message)
    return message


def send_fcm_message(fcm_token, title, body, data=None):
    """Send an FCM message to a specific device.

    Args:
        fcm_token: The FCM token of the target device
        title: Notification title
        body: Notification body
        data: Optional custom data payload (dict)

    Returns:
        Response from FCM server
    """
    common_message = _build_common_message(fcm_token, title, body, data)
    logger.debug('FCM request body: %s', json.dumps(common_message, indent=2))

    return _send_fcm_message(common_message)


def send_fcm_to_topic(topic, title, body, data=None):
    """Send an FCM message to a topic.

    Args:
        topic: The topic to send to (e.g., "news")
        title: Notification title
        body: Notification body
        data: Optional custom data payload (dict)

    Returns:
        Response from FCM server
    """
    message = {
        'message': {
            'topic': topic,
            'notification': {
                'title': title,
                'body': body
            }
        }
    }

    # Add custom data if provided
    if data:
        message['message']['data'] = data

    logger.debug('FCM topic request body: %s', json.dumps(message, indent=2))

    return _send_fcm_message(message)

# For backward compatibility


# def sendFcm(fcm, title, body):
#     """Legacy function for backward compatibility"""
#     return send_fcm_message(fcm, title, body)
