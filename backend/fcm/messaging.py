import argparse
import json
import datetime
from pathlib import Path
from google.oauth2 import service_account
from google import *
import google.auth.transport.requests

# pip install google-auth
# pip install google-auth-oauthlib
# pip install requests


PROJECT_ID = 'alaa-e6e90'

BASE_URL = 'https://fcm.googleapis.com'
FCM_ENDPOINT = 'v1/projects/' + PROJECT_ID + '/messages:send'
FCM_URL = BASE_URL + '/' + FCM_ENDPOINT
SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']

# [START retrieve_access_token]
cred_file_dir = Path(__file__).resolve().parent.parent.parent
cred_file_path = cred_file_dir / 'alaa-firebase-adminsdk.json'


def _get_access_token():
    """Retrieve a valid access token that can be used to authorize requests.
    :return: Access token.
    """
    credentials = service_account.Credentials.from_service_account_file(
        cred_file_path, scopes=SCOPES)
    # credentials = service_account.Credentials.from_service_account_file(
    #   'sahab-5dcad-firebase-adminsdk-pds1o-032ca24d38_old.json', scopes=SCOPES)
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    return credentials.token
# [END retrieve_access_token]


def _send_fcm_message(fcm_message):
    """Send HTTP request to FCM with given message.

    Args:
      fcm_message: JSON object that will make up the body of the request.
    """
    # [START use_access_token]
    headers = {
        'Authorization': 'Bearer ' + _get_access_token(),
        'Content-Type': 'application/json; UTF-8',
    }
    # [END use_access_token]
    resp = google.auth.transport.requests.requests.post(FCM_URL, data=json.dumps(
        fcm_message), headers=headers)

    if resp.status_code == 200:
        print('Message sent to Firebase for delivery, response:')
        print(resp.text)
    else:
        print('Unable to send message to Firebase')
        print(resp.text)


def _build_common_message(fcm, title, body):
    """Construct common notifiation message.

    Construct a JSON object that will be used to define the
    common parts of a notification message that will be sent
    to any app instance subscribed to the news topic.
    """
    return {

        'message': {
            'token': fcm,
            'notification': {
                'title': title,
                'body': body
            },
            "data": {
                "type": "2",
            }
        },
    }


def sendFcm(fcm, title, body):
    parser = argparse.ArgumentParser()
    parser.add_argument('--message')
    # args = parser.parse_args()
    common_message = _build_common_message(fcm, title, body)
    print('FCM request body for message using common notification object:')
    print(json.dumps(common_message, indent=2))
    _send_fcm_message(common_message)
