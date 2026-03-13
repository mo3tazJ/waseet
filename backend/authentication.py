from rest_framework import authentication
from rest_framework import exceptions
from .models import FCMToken


class FCMTokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        # Get the token from the header
        auth_header = request.META.get('HTTP_AUTHORIZATION')

        if not auth_header:
            raise exceptions.AuthenticationFailed('Not Authorized')
            # return None

        # Check if the header is in the format "FCM <token>"
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != 'fcm':
                return None
        except ValueError:
            return None

        # Validate the token
        try:
            fcm_token = FCMToken.objects.get(token=token, is_active=True)
            return (fcm_token.profile, None)  # Return (user, None) tuple
        except FCMToken.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid FCM token')
