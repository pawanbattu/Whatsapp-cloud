from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User
from WhatsPanel.models.WhatsAppAdminUser import *
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


# ─── JWT Custom Serializer ────────────────────────────────────────────────────────
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds extra user info into the JWT payload and response."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        token['full_name'] = f"{user.first_name} {user.last_name}".strip()
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserProfileSerializer(self.user).data
        return data


# ─── User Profile Serializer ──────────────────────────────────────────────────────
class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email',
            'first_name', 'last_name', 'full_name',
            'is_active', 'date_joined', 'last_login',
        ]
        read_only_fields = ['id', 'email', 'is_active', 'date_joined', 'last_login']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppAdminUser
        fields = [
            'id', 'name', 'access_token',
            'templates_access_token', 'phone_number_id', 'waba_id',
            'app_id', 'webhook_verify_token', 'is_active', 'app_secret',
            'message_base_version', 'templates_base_version', 'oauth_base_version', 
            'domain', 'subscribed_fields'
        ]

        extra_kwargs = {
            'name': {'allow_blank': True, 'required': False},
            'access_token': {'allow_blank': True, 'required': False},
            'templates_access_token': {'allow_blank': True, 'required': False},
            'phone_number_id': {'allow_blank': True, 'required': False},
            'waba_id': {'allow_blank': True, 'required': False},
            'app_id': {'allow_blank': True, 'required': False},
            'webhook_verify_token': {'allow_blank': True, 'required': False},
            'app_secret' : {'allow_blank': True, 'required': False},
            'message_base_version' : {'allow_blank': False, 'required': True},
            'templates_base_version' : {'allow_blank': False, 'required': True},
            'oauth_base_version' : {'allow_blank': False, 'required': True},
            'domain' : {'allow_blank': False, 'required': True},
            'subscribed_fields' : {'allow_blank': False, 'required': True},
        }

    
    def validate_access_token(self, value):
        if value and len(value) > 500:
            raise serializers.ValidationError("Access token too long.")
        return value

    def validate_templates_access_token(self, value):
        if value and len(value) > 500:
            raise serializers.ValidationError("Templates access token too long.")
        return value

    def validate_phone_number_id(self, value):
        if value and len(value) > 100:
            raise serializers.ValidationError("Phone number ID too long.")
        return value

    # def validate_waba_id(self, value):
    #     if not value:
    #         raise serializers.ValidationError("WABA ID is required.")
    #     return value

    # def validate_app_id(self, value):
    #     if not value:
    #         raise serializers.ValidationError("App ID is required.")
    #     return value

    # def validate_webhook_verify_token(self, value):
    #     if not value:
    #         raise serializers.ValidationError("Webhook verify token is required.")
    #     return value

    def validate_is_active(self, value):
        if value not in [True, False, 0, 1]:
            raise serializers.ValidationError("is_active must be boolean.")
        return bool(value)

    def update(self, instance, validated_data):
        user = WhatsAppAdminUser.objects.filter(owner=instance).first()

        if user:
            for attr, value in validated_data.items():
                setattr(user, attr, value)
            user.save()
            return user
        else:
            return WhatsAppAdminUser.objects.create(owner=instance, **validated_data)
    def getUserData(self, instance):
        obj = WhatsAppAdminUser.objects.filter(owner=instance).first()
        return f"{obj.id}, {obj.name}, {obj.access_token}, {obj.templates_access_token}, {obj.phone_number_id}, {obj.waba_id},{obj.app_id}, {obj.webhook_verify_token}, {obj.is_active}, {obj.app_secret}, {obj.message_base_version}, {obj.templates_base_version}, {obj.oauth_base_version}"

    # def validate_username(self, value):
    #     user = self.context['request'].user
    #     if User.objects.exclude(pk=user.pk).filter(username=value).exists():
    #         raise serializers.ValidationError('This username is already taken.')
    #     return value


# ─── Register ─────────────────────────────────────────────────────────────────────
class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, required=False, default='')
    last_name = serializers.CharField(max_length=150, required=False, default='')
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('This username is already taken.')
        return value

    def validate_email(self, value):
        email = value.lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return email

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        try:
            validate_password(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


# ─── Email Verification ───────────────────────────────────────────────────────────
class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.UUIDField()


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


# ─── Forgot Password ──────────────────────────────────────────────────────────────
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower()


# ─── Reset Password ───────────────────────────────────────────────────────────────
class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match.'})

        from WhatsPanel.models import PasswordResetToken
        try:
            reset_token = PasswordResetToken.objects.select_related('user').get(
                token=attrs['token']
            )
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({'token': 'Invalid or expired reset token.'})

        if not reset_token.is_valid():
            raise serializers.ValidationError({'token': 'This token has expired or already been used.'})

        try:
            validate_password(attrs['new_password'], reset_token.user)
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})

        attrs['reset_token_obj'] = reset_token
        return attrs

    def save(self):
        reset_token = self.validated_data['reset_token_obj']
        user = reset_token.user
        user.set_password(self.validated_data['new_password'])
        user.save()
        reset_token.is_used = True
        reset_token.save()
        return user


# ─── Change Password ──────────────────────────────────────────────────────────────
class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match.'})
        try:
            validate_password(attrs['new_password'], self.context['request'].user)
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
