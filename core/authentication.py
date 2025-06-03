from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # Try to get the token from the cookie first
        access_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE'])
        
        if access_token:
            try:
                # Validate the token
                validated_token = AccessToken(access_token)
                return self.get_user(validated_token), validated_token
            except (InvalidToken, TokenError):
                return None
        
        # If no token in cookie, try the Authorization header
        return super().authenticate(request) 