from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth.models import User
from WhatsPanel.models.WhatsAppAdminUser import *
from rest_framework.exceptions import ValidationError as DRFValidationError
from WhatsPanel.models import EmailVerificationToken, PasswordResetToken
from rest_framework.response import Response
from django.db import transaction
import core.logger as logger
import traceback
from WhatsPanel.serializer.AuthSerializer import (
    RegisterSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
    EmailVerificationSerializer,
    ResendVerificationSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    PasswordChangeSerializer,
)
from core.email import (
    send_verification_email,
    send_password_reset_email,
    send_password_changed_email,
)
from core.utils import success_response, custom_exception_handler


# ─── Register ──────────────────────────────────────────────────────────────────────
class RegisterView(APIView):
    """
    POST /api/auth/register/
    Creates a built-in auth.User and sends a verification email.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = RegisterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

            # New users start inactive until email is verified
            user.is_active = False
            user.save(update_fields=['is_active'])

            token_obj = EmailVerificationToken.objects.create(user=user)
            send_verification_email(user, token_obj.token)

            return success_response(
                data=UserProfileSerializer(user).data,
                message='Registration successful. Check your email to activate your account.',
                status_code=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.app_logs("EXCEPTION", "RegisterView", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})


# ─── Login ─────────────────────────────────────────────────────────────────────────
class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Body: { username, password }  ← Django default field
    Returns access + refresh tokens with user data.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            if response.status_code == 200:
                return success_response(data=response.data, message='Login successful.')
            return response
        except Exception as e:
            logger.app_logs("EXCEPTION", "LoginView", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})


# ─── Logout ────────────────────────────────────────────────────────────────────────
class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Body: { refresh }
    Blacklists the refresh token so it can't be reused.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return success_response(
                message='Refresh token is required.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return success_response(message='Logged out successfully.')
        except TokenError:
            logger.app_logs("EXCEPTION", "LogoutView", {"error": str(traceback.format_exc()), "inputData": request})
            return success_response(
                message='Invalid or already blacklisted token.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )


# ─── Token Refresh ─────────────────────────────────────────────────────────────────
class TokenRefreshView(BaseTokenRefreshView):
    """
    POST /api/auth/token/refresh/
    Body: { refresh }
    Returns a new access token.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            if response.status_code == 200:
                return success_response(data=response.data)
            return response
        except Exception as e:
            logger.app_logs("EXCEPTION", "TokenRefreshView", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})

# ─── Email Verification ────────────────────────────────────────────────────────────
class VerifyEmailView(APIView):
    """
    POST /api/auth/verify-email/
    Body: { token }
    Activates the user account.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token_obj = EmailVerificationToken.objects.select_related('user').get(
                token=serializer.validated_data['token']
            )
        except EmailVerificationToken.DoesNotExist:
            return success_response(
                message='Invalid verification token.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if not token_obj.is_valid():
            return success_response(
                message='This link has expired or already been used.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = token_obj.user
        user.is_active = True
        user.save(update_fields=['is_active'])

        token_obj.is_used = True
        token_obj.save(update_fields=['is_used'])

        return success_response(message='Email verified. Your account is now active.')


class ResendVerificationView(APIView):
    """
    POST /api/auth/resend-verification/
    Body: { email }
    Anti-enumeration: always returns success.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = ResendVerificationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            email = serializer.validated_data['email'].lower()

            try:
                user = User.objects.get(email=email)
                if getattr(user, 'is_verified', False): 
                    success_response(message='Email is already verified.', status_code=status.HTTP_400_BAD_REQUEST,)
                if not user.is_active:
                    # Invalidate old tokens, issue a fresh one
                    EmailVerificationToken.objects.filter(user=user, is_used=False).update(is_used=True)
                    token_obj = EmailVerificationToken.objects.create(user=user)
                    send_verification_email(user, token_obj.token)
            except User.DoesNotExist:
                pass

            return success_response(
                message='If that email is registered, a verification link has been sent.'
            )
        except Exception as e:
            logger.app_logs("EXCEPTION", "ResendVerificationView", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})


# ─── Forgot Password ───────────────────────────────────────────────────────────────
class ForgotPasswordView(APIView):
    """
    POST /api/auth/forgot-password/
    Body: { email }
    Anti-enumeration: always returns success.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = ForgotPasswordSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            email = serializer.validated_data['email']

            try:
                user = User.objects.get(email=email)
                # Invalidate old unused tokens
                PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)
                token_obj = PasswordResetToken.objects.create(user=user)
                send_password_reset_email(user, token_obj.token)
            except User.DoesNotExist:
                pass

            return success_response(
                message='If that email is registered, a password reset link has been sent.'
            )
        except Exception as e:
            logger.app_logs("EXCEPTION", "ForgotPasswordView", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})


# ─── Validate Reset Token ──────────────────────────────────────────────────────────
class ValidateResetTokenView(APIView):
    """
    GET /api/auth/reset-password/validate/?token=<uuid>
    Lets the frontend check token validity before showing the reset form.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            token = request.query_params.get('token')
            if not token:
                return success_response(
                    data={'valid': False},
                    message='Token is required.',
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            try:
                token_obj = PasswordResetToken.objects.get(token=token)
                is_valid = token_obj.is_valid()
            except PasswordResetToken.DoesNotExist:
                is_valid = False

            return success_response(data={'valid': is_valid})
        except Exception as e:
            logger.app_logs("EXCEPTION", "ValidateResetTokenView", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})


# ─── Reset Password ────────────────────────────────────────────────────────────────
class ResetPasswordView(APIView):
    """
    POST /api/auth/reset-password/
    Body: { token, new_password, new_password_confirm }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = ResetPasswordSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            send_password_changed_email(user)
            return success_response(message='Password reset successful. You can now log in.')
        except Exception as e:
            logger.app_logs("EXCEPTION", "ResetPasswordView", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})


# ─── Change Password (authenticated) ──────────────────────────────────────────────
class PasswordChangeView(APIView):
    """
    POST /api/auth/change-password/
    Body: { old_password, new_password, new_password_confirm }
    Requires: Authorization: Bearer <access_token>
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            send_password_changed_email(request.user)
            return success_response(message='Password changed successfully.')
        except Exception as e:
            logger.app_logs("EXCEPTION", "PasswordChangeView", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})


# ─── User Profile ──────────────────────────────────────────────────────────────────
class UserProfileView(APIView):
    """
    GET   /api/auth/me/   → current user's profile
    PATCH /api/auth/me/   → update username / first_name / last_name
    Requires: Authorization: Bearer <access_token>
    """
    #permission_classes = [IsAuthenticated]

    def get(self, request):
        obj = WhatsAppAdminUser.objects.filter(owner=request.user).first()
        return success_response(data=UserUpdateSerializer(obj).data if obj else {})

    def patch(self, request):
        try:
            permission_classes = [IsAuthenticated]
            serializer = UserUpdateSerializer(
                request.user, data=request.data, partial=True, context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return success_response(
                data=UserProfileSerializer(request.user).data,
                message='Profile updated successfully.',
            )
        except DRFValidationError as e:
            logger.app_logs("EXCEPTION", "PasswordChangeView", {"error": str(traceback.format_exc()), "inputData": request})
            return Response({
                "status": "error",
                "error_code": 400,
                "message": "Validation failed",
                "errors": e.detail          
        }, status=status.HTTP_400_BAD_REQUEST)


# ─── Delete Account ────────────────────────────────────────────────────────────────
class DeleteAccountView(APIView):
    """
    DELETE /api/auth/me/delete/
    Body: { password }
    Permanently deletes the auth.User row (cascades to token tables).
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        try:
            password = request.data.get('password')
            if not password:
                return success_response(
                    message='Password confirmation is required.',
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if not request.user.check_password(password):
                return success_response(
                    message='Incorrect password.',
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            request.user.delete()
            return success_response(message='Account deleted successfully.')
        except Exception as e:
            logger.app_logs("EXCEPTION", "DeleteAccountView", {"error": str(traceback.format_exc()), "inputData": request})
            return custom_exception_handler(e, {'view': self, 'request': request})
        

# ─── Resend verification link ────────────────────────────────────────────────────────────────
# class ResendVerficationEmailView(APIView):
#     """
#     POST /api/auth/me/resendEmail/
#     """
#     permission_classes = [AllowAny]

#     def post(self, request):
#         try:
#             email = request.data.get('email')
#             if not email:
#                 return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
                
#             try:
#                 user = User.objects.get(email=email)
#             except User.DoesNotExist:
#                 return Response(
#                     {"message": "If an account exists, a new link has been sent."}, 
#                     status=status.HTTP_200_OK
#                 )
        
#             # Call your new function
#             success, message = self.resend_verification_email(user)
            
#             if not success:
#                 return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
                
#             return Response({"message": message}, status=status.HTTP_200_OK)
#         except Exception as e:
#             logger.app_logs("EXCEPTION", "ResendVerficationEmailView", {"error": str(traceback.format_exc()), "inputData": request})
#             return custom_exception_handler(e, {'view': self, 'request': request})

    
#     def resend_verification_email(self, user):
#         try:
#             # 1. (Optional but recommended) Prevent sending if already verified
#             # Replace 'is_verified' with whatever field your User model uses
#             if getattr(user, 'is_verified', False): 
#                 return False, "Email is already verified."

#             # Use a database transaction to ensure data integrity
#             with transaction.atomic():
#                 # 2. Delete all existing tokens for this user so old links stop working
#                 EmailVerificationToken.objects.filter(user=user).delete()
                
#                 # 3. Create the fresh token
#                 new_token_obj = EmailVerificationToken.objects.create(user=user)
                
#             # 4. Send the email (done outside the transaction block to avoid locking the DB while sending)
#             send_verification_email(user, new_token_obj.token)
            
#             return True, "Verification email sent successfully."
#         except Exception as e:
#             logger.app_logs("EXCEPTION", "resend_verification_email", {"error": str(traceback.format_exc()), "inputData": user})
#             return e