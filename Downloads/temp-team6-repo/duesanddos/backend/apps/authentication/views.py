from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests

from apps.authentication.serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
)
from apps.users.serializers import UserSerializer

User = get_user_model()

COOKIE_SETTINGS = {
    "httponly": True,
    "secure": settings.SIMPLE_JWT.get("AUTH_COOKIE_SECURE", False),
    "samesite": settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax"),
    "path": "/",
}


def set_auth_cookies(response, refresh_token_obj):
    access_token = str(refresh_token_obj.access_token)
    refresh_token = str(refresh_token_obj)
    access_lifetime = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]
    refresh_lifetime = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]

    response.set_cookie(
        settings.SIMPLE_JWT["AUTH_COOKIE"],
        access_token,
        max_age=int(access_lifetime.total_seconds()),
        **COOKIE_SETTINGS,
    )
    response.set_cookie(
        settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"],
        refresh_token,
        max_age=int(refresh_lifetime.total_seconds()),
        **COOKIE_SETTINGS,
    )


def clear_auth_cookies(response):
    response.delete_cookie(settings.SIMPLE_JWT["AUTH_COOKIE"])
    response.delete_cookie(settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"])


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user, context={"request": request}).data

        response = Response(
            {"user": user_data, "message": "Account created successfully."},
            status=status.HTTP_201_CREATED,
        )
        set_auth_cookies(response, refresh)
        return response


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user, context={"request": request}).data

        response = Response({"user": user_data, "message": "Login successful."})
        set_auth_cookies(response, refresh)
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"])
        response = Response({"message": "Logged out successfully."})

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass

        clear_auth_cookies(response)
        return response


class TokenRefreshCookieView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"])
        if not refresh_token:
            return Response(
                {"detail": "Refresh token not found."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            refresh = RefreshToken(refresh_token)
            response = Response({"message": "Token refreshed."})
            set_auth_cookies(response, refresh)
            return response
        except TokenError as e:
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()

        # Always return 200 to avoid email enumeration
        try:
            user = User.objects.get(email=email)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{settings.FRONTEND_DOMAIN}/reset-password?uid={uid}&token={token}"

            context = {
                "user": user,
                "reset_url": reset_url,
                "frontend_domain": settings.FRONTEND_DOMAIN.rstrip("/"),
            }
            text_message = render_to_string("emails/reset_password.txt", context)
            html_message = render_to_string("emails/reset_password.html", context)

            send_mail(
                subject="Reset your Dues & Do's password",
                message=text_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )
        except User.DoesNotExist:
            pass

        return Response(
            {"message": "If an account with that email exists, you'll receive a reset link shortly."}
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["new_password"])
        user.save()

        # Blacklist existing tokens by updating session hash
        # This invalidates all existing sessions for this user
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            tokens = OutstandingToken.objects.filter(user=user)
            for token in tokens:
                BlacklistedToken.objects.get_or_create(token=token)
        except Exception:
            pass

        response = Response({"message": "Password reset successfully. Please log in."})
        clear_auth_cookies(response)
        return response


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("credential")
        if not token:
            return Response({"detail": "No credential provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Specify the CLIENT_ID of the app that accesses the backend
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_OAUTH2_CLIENT_ID)

            # ID token is valid. Get the user's Google Account ID from the decoded token.
            email = idinfo.get("email")
            first_name = idinfo.get("given_name", "")
            last_name = idinfo.get("family_name", "")
            
            if not email:
                return Response({"detail": "Google token does not contain email."}, status=status.HTTP_400_BAD_REQUEST)

            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": f"{first_name} {last_name}".strip(),
                    "auth_provider": "google",
                    "email_verified": True,
                }
            )
            
            if created:
                user.set_unusable_password()
                user.save()

            refresh = RefreshToken.for_user(user)
            user_data = UserSerializer(user, context={"request": request}).data

            response = Response({
                "user": user_data, 
                "message": "Google login successful.",
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
            set_auth_cookies(response, refresh)
            return response
            
        except ValueError as e:
            # Invalid token
            print(f"Google Token Verification Failed: {e}")
            return Response({"detail": f"Invalid Google token: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
