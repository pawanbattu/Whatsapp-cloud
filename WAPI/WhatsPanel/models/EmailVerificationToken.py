"""
Only token models live here.
User model = django.contrib.auth.models.User (built-in, no changes).
Tables used: auth_user, auth_user_groups, auth_user_user_permissions (all default Django).
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class EmailVerificationToken(models.Model):
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = 'email_verification_tokens'

    def __str__(self):
        return f"VerificationToken({self.user.email}, used={self.is_used})"

    def is_valid(self):
        from django.conf import settings
        from datetime import timedelta
        expiry_hours = getattr(settings, 'EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS', 48)
        expiry = self.created_at + timedelta(hours=expiry_hours)
        return not self.is_used and timezone.now() < expiry
