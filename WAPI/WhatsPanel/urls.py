from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from .views.messages import MessagesViewSet
from .views.templates import TemplatesViewSet
from .views.users import UsersViewSet
from .views.media import *
from .views.auth import *
from .views.ReceiveMessage import *
from .views.MessageStreamView import *
from rest_framework.routers import DefaultRouter


schema_view = get_schema_view(
    openapi.Info(
        title="WhatsApp Panel API",
        default_version='v1',
        description="API Documentation for WhatsApp panel",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/v1/users/health_check', UsersViewSet.as_view({'get': 'health_check'})),
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/users/Getuser', UsersViewSet.as_view({'get': 'Getuser'})),
    path('api/v1/users/PostFile/', UsersViewSet.as_view({'post': 'PostFile'})),
    path('api/v1/users/Createuser/', UsersViewSet.as_view({'post': 'Createuser'})),
    path('api/v1/users/Updateuser/<int:id>/', UsersViewSet.as_view({'patch': 'Updateuser'})),
    path('api/v1/users/Deleteuser/<int:id>/', UsersViewSet.as_view({'delete': 'Deleteuser'})),
    path('api/v1/users/refreshToken/', UsersViewSet.as_view({'get': 'refreshToken'})),
    path('api/v1/users/subscribefields/', UsersViewSet.as_view({'post': 'subcribeApps'})),
    path('api/v1/users/subscribeCallBackUrl/', UsersViewSet.as_view({'post': 'subscribeCallBackUrl'})),
    path('api/start-chunk-upload/', StartChunkUploadView.as_view()),
    path('api/upload-chunk/', UploadChunkView.as_view()),
    path('api/complete-chunk-upload/', CompleteChunkUploadView.as_view()),
    path('api/cancel-chunk-upload/', CancelChunkUploadView.as_view()),
    path('api/whatsapp/upload-handle/', WhatsAppMediaUploadView.as_view(), name='whatsapp-upload-handle'),
    path('api/upload-media/', WhatsAppMediaUploadView.as_view(), name='whatsapp-media-upload'),
    path('api/v1/messages/Getmessage/', MessagesViewSet.as_view({'get': 'Getmessage'})),
    path('api/v1/messages/Sendmessage/', MessagesViewSet.as_view({'post': 'Sendmessage'})),
    path('api/v1/messages/Schedulemessage/', MessagesViewSet.as_view({'post': 'Schedulemessage'})),
    path('api/v1/messages/<int:user_id>/mark-read/', MessagesViewSet.as_view({'post': 'markMessageAsRead'})),
    path('api/v1/messages/getMessagesByBatch/', MessagesViewSet.as_view({'get': 'Getconversations'}),name='messages-by-batch'),
    path('api/v1/stream/messages/<int:admin_id>/', MessageStreamView.as_view(), name='message_stream'),
    path('api/v1/messages/receiveMessages/<int:admin_id>/', ReceiveMessageView.as_view()),
    path('api/v1/messages/Sendreaction/', MessagesViewSet.as_view({'post': 'Sendreaction'})),
    path('api/v1/messages/GetSchedulemessage', MessagesViewSet.as_view({'get': 'GetSchedulemessage'})),
    path('api/v1/messages/DeleteSchedulemessage/<int:id>/', MessagesViewSet.as_view({'delete': 'DeleteSchedulemessage'})),
    path('api/v1/templates/Savetemplate/', TemplatesViewSet.as_view({'post': 'Savetemplate'})),
    path('api/v1/templates/Sendtemplate/', TemplatesViewSet.as_view({'post': 'Sendtemplate'})),
    path('api/v1/templates/Submittemplate/', TemplatesViewSet.as_view({'post': 'Submittemplate'})),
    path('api/v1/templates/Gettemplate', TemplatesViewSet.as_view({'get': 'Gettemplates'})),
    path('api/v1/templates/Synctemplate/', TemplatesViewSet.as_view({'post': 'Synctemplate'})),
    path('api/v1/templates/Deletetemplate/<str:template_name>/', TemplatesViewSet.as_view({'delete': 'Deletetemplate'})),
    path('api/v1/templates/Edittemplate/<int:template_id>/', TemplatesViewSet.as_view({'post': 'Edittemplate'})),
    path('api/v1/templates/Scheduletemplate/', TemplatesViewSet.as_view({'post': 'Scheduletemplate'})),

    # ── Registration & Login ─────────────────────────────────────────────────────
    path('api/v1/register/', RegisterView.as_view(), name='register'),
    path('api/v1/login/', LoginView.as_view(), name='login'),
    path('api/v1/logout/', LogoutView.as_view(), name='logout'),

    # ── Token ────────────────────────────────────────────────────────────────────
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # ── Email Verification ───────────────────────────────────────────────────────
    path('api/v1/verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('api/v1/resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),

    # ── Password Management ──────────────────────────────────────────────────────
    path('api/v1/forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('api/v1/reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('api/v1/reset-password/validate/', ValidateResetTokenView.as_view(), name='validate-reset-token'),
    path('api/v1/change-password/', PasswordChangeView.as_view(), name='change-password'),

    # ── Profile ──────────────────────────────────────────────────────────────────
    path('api/v1/me/', UserProfileView.as_view(), name='profile'),
    path('api/v1/me/delete/', DeleteAccountView.as_view(), name='delete-account'),
]
